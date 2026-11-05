#!/usr/bin/env python3
"""Observed-entry pooled RMSE within each organ, for both cohorts and every model."""
from __future__ import annotations

# Resolve all public modules and scratch from the release root.
import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[1]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH
import argparse
import json
from pathlib import Path

from v4_protocol import HERE, PROJECT, ALL_MODELS, collect_errors, make_data, metrics, sha256, write_json
import numpy as np


def organ_seed_summary():
    runs = [json.loads(p.read_text()) for p in sorted((PROJECT / "result/seeds").glob("forecast_seed[0-3].json"))]
    out = {}
    for name in ALL_MODELS:
        for split, key in (("A", "A_test"), ("B", "B_external")):
            for organ in ("cardiovascular", "pulmonary", "renal", "metabolic"):
                vals = {r["config"]["seed"]: r["results"][name][key][f"RMSE_{organ}"]
                        for r in runs if name in r["results"] and f"RMSE_{organ}" in r["results"][name][key]}
                out.setdefault(name, {}).setdefault(split, {})[organ] = dict(
                    n_seeds=len(vals), per_seed=vals,
                    mean=float(np.mean(list(vals.values()))) if vals else None,
                    sd_sample=float(np.std(list(vals.values()), ddof=1)) if len(vals) > 1 else None)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stats", type=Path, default=HERE / "stats_v4.json")
    ap.add_argument("--out", type=Path, default=HERE / "per_organ_v4.json")
    ap.add_argument("--series-root", type=Path)
    args = ap.parse_args(argv)
    tables = {}
    if args.series_root:
        meta = None
        for file in sorted((args.series_root / "selected").glob("*/seed*/run.json")):
            run = json.loads(file.read_text())
            label, model = f"seed{run['seed']}", run["model"]
            if run["status"] != "complete":
                tables.setdefault(label, {})[model] = dict(status=run["status"])
                continue
            meta = run["data"]
            row = dict(status="complete", run=str(file), sha256=sha256(file), splits={})
            for split in ("A", "B"):
                with np.load(file.parent / f"errors_{split}.npz") as archive:
                    row["splits"][split] = metrics(dict(archive), meta["organ_names"])
            tables.setdefault(label, {})[model] = row
        if meta is None:
            raise ValueError("no completed runs")
        loaders, pm = make_data(C=meta["C"], K=meta["K"], max_stays=meta["max_stays"], min_length=meta["min_length"])
        if pm["split_stay_indices"] != meta["split_stay_indices"]:
            raise ValueError("persistence cohort differs")
        baseline = {split: metrics(collect_errors(None, loader, K=meta["K"], organ_slices=meta["organ_slices"]), meta["organ_names"])
                    for split, loader in zip(("A", "B"), loaders[2:])}
        for rows in tables.values():
            rows["persistence"] = dict(status="complete", trained=False, splits=baseline)
    else:
        raw = json.loads(args.stats.read_text())
        meta = raw["data"]
        for label, models in raw["checkpoints"].items():
            for name, item in models.items():
                row = dict(checkpoint=item.get("checkpoint"), checkpoint_sha256=item.get("checkpoint_sha256"), splits={})
                for split, source in item["splits"].items():
                    if sha256(source["error_file"]) != source["sha256"]:
                        raise ValueError(f"error artifact changed: {source['error_file']}")
                    with np.load(source["error_file"]) as archive:
                        row["splits"][split] = metrics(dict(archive), meta["organ_names"])
                tables.setdefault(label, {})[name] = row
    selected_summary = {}
    if args.series_root:
        for model in ALL_MODELS:
            for split in ("A", "B"):
                for organ in meta["organ_names"]:
                    vals = {label: rows[model]["splits"][split]["organs"][organ]["RMSE"]
                            for label, rows in tables.items() if model in rows and rows[model].get("status") == "complete"}
                    good = [v for v in vals.values() if v is not None]
                    selected_summary.setdefault(model, {}).setdefault(split, {})[organ] = dict(
                        per_seed=vals, n_finite_seeds=len(good),
                        mean=float(np.mean(good)) if good else None,
                        sd_sample=float(np.std(good, ddof=1)) if len(good) > 1 else None)
    write_json(args.out, dict(schema_version=4, scope="smoke" if meta["max_stays"] is not None else "full",
        claim_status="descriptive errors only; consult frozen headline gate before any new ordering claim",
        definition="sqrt(sum squared error / sum mask), pooled across stays, hours and variables WITHIN the organ",
        units="A-train standard deviation units; not physical measurement units", data=meta,
        table=tables, legacy_seed_summary=organ_seed_summary(), selected_seed_summary=selected_summary,
        limits=["Null RMSE means no observations or nonfinite predictions; it never means zero error.",
                "Averaging organ RMSE does not recover overall pooled RMSE.",
                "Frozen checkpoints have no recoverable seed identity; seed summaries come separately from frozen JSONs."]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
