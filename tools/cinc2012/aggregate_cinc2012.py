#!/usr/bin/env python3
"""Re-derive pooled RMSE from per-stay errors, then summarize seed RMSEs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from cinc2012_common import RUN_ROOT, MODELS, owned_path, sha256, v4, verify_input, write_json
import numpy as np


def error_metrics(path, organs):
    with np.load(path, allow_pickle=False) as archive:
        errors = {k: archive[k] for k in archive.files}
    n = len(errors["stay_index"])
    if (errors["sse"].shape != (n,) or errors["count"].shape != (n,)
            or errors["organ_sse"].shape != (n, len(organs))
            or errors["organ_count"].shape != (n, len(organs))):
        raise ValueError(f"Wrong per-stay error shapes: {path}")
    if len(np.unique(errors["stay_index"])) != n:
        raise ValueError(f"Repeated stay within one set: {path}")
    if any(not np.isfinite(a).all() for a in errors.values()) or errors["nonfinite"].sum():
        raise ValueError(f"Nonfinite saved errors: {path}")
    if np.any(errors["sse"] < 0) or np.any(errors["count"] < 0):
        raise ValueError(f"Negative error sum/count: {path}")
    if not np.array_equal(errors["organ_count"].sum(1), errors["count"]):
        raise ValueError(f"Organ target counts do not sum to overall counts: {path}")
    if not np.allclose(errors["organ_sse"].sum(1), errors["sse"], rtol=2e-6, atol=1e-6):
        raise ValueError(f"Organ SSE does not sum to overall SSE: {path}")
    return errors, v4.metrics(errors, organs)


def stats(values):
    values = list(values)
    if not values or any(v is None for v in values):
        return dict(n=len(values), mean=None, sd=None, ddof=1)
    a = np.asarray(values, np.float64)
    return dict(n=len(values), mean=float(a.mean()), sd=float(a.std(ddof=1)) if len(a) > 1 else None, ddof=1)


def display(summary):
    if summary["mean"] is None:
        return "unavailable"
    if summary["sd"] is None:
        return f"{summary['mean']:.6f} (n={summary['n']}; sd unavailable)"
    return f"{summary['mean']:.6f} ± {summary['sd']:.6f}"


def aggregate(root, *, out_json=None, out_table=None,
              allow_partial=False):
    root = owned_path(root)
    out_json = owned_path(out_json or root / "cinc2012_results.json")
    out_table = owned_path(out_table or root / "TABLE_CINC2012.md")
    records = {p: {m: {} for m in MODELS} for p in ("transfer", "within")}
    inventory, missing, metadata = [], [], {}
    scope = None
    for protocol in records:
        for model in MODELS:
            for seed in range(4):
                file = root / protocol / model / f"seed{seed}/run.json"
                if not file.is_file():
                    missing.append(f"{protocol}/{model}/seed{seed}")
                    continue
                record = json.loads(file.read_text())
                if (record["protocol"], record["model"], record["seed"], record["status"],
                        record["C"], record["K"]) != (protocol, model, seed, "complete", 12, 12):
                    raise ValueError(f"Failed or wrong run identity: {file}")
                if record["scope"] not in ("smoke", "full"):
                    raise ValueError(f"Unknown run scope: {file}")
                if scope is None:
                    scope = record["scope"]
                if record["scope"] != scope:
                    raise ValueError("Never mix smoke and full results")
                meta = record["data"]
                if protocol in metadata:
                    for key in ("counts", "eligible_counts", "retained_counts", "cohort_sha256",
                                "split_stay_indices", "split_record_ids", "organ_names", "organ_slices",
                                "norm_mean", "norm_std"):
                        if metadata[protocol][key] != meta[key]:
                            raise ValueError(f"Model/seed data mismatch for {key}: {file}")
                metadata[protocol] = meta
                expected_splits = ("testA", "testB", "pooled") if protocol == "transfer" else ("testB",)
                if set(record["results"]) != set(expected_splits):
                    raise ValueError(f"Unexpected test metrics (within must omit testA): {file}")
                errors, summaries, error_sources = [], {}, []
                for split in expected_splits:
                    if split == "pooled":
                        joined = {key: np.concatenate([e[key] for e in errors]) for key in errors[0]}
                        metric = v4.metrics(joined, meta["organ_names"])
                    else:
                        source = file.parent / f"errors_{split}.npz"
                        err, metric = error_metrics(source, meta["organ_names"])
                        if err["stay_index"].tolist() != meta["split_stay_indices"][split]:
                            raise ValueError(f"Error stay IDs mismatch: {source}")
                        if metric["n_stays"] != meta["counts"][split]:
                            raise ValueError(f"Error stay count mismatch: {source}")
                        errors.append(err)
                        error_sources.append(dict(path=str(source), sha256=sha256(source)))
                    if metric != record["results"][split]:
                        raise ValueError(f"Saved metrics disagree with re-derived errors: {file} {split}")
                    summaries[split] = metric
                records[protocol][model][str(seed)] = summaries
                inventory.append(dict(path=str(file), sha256=sha256(file), errors=error_sources))
    if not inventory:
        raise ValueError(f"No completed runs found under {root}")
    if not allow_partial and (missing or scope != "full"):
        raise ValueError(f"Full scientific summary requires all 88 full runs; missing={len(missing)}, scope={scope}. Use --allow-partial for a labelled diagnostic.")
    protocols = {}
    for protocol, models in records.items():
        if protocol not in metadata:
            continue
        meta = metadata[protocol]
        outputs = {}
        for model, seeds in models.items():
            splits = {}
            for split in (("testA", "testB", "pooled") if protocol == "transfer" else ("testB",)):
                per_seed = {s: r[split] for s, r in seeds.items()}
                splits[split] = dict(per_seed=per_seed,
                    RMSE=stats(r["pooled_masked_RMSE"] for r in per_seed.values()),
                    organs={organ: stats(r["organs"][organ]["RMSE"] for r in per_seed.values())
                            for organ in meta["organ_names"]})
            outputs[model] = dict(seeds_present=[int(s) for s in seeds], splits=splits)
        protocols[protocol] = dict(data=meta, models=outputs)
    complete = not missing and scope == "full"
    result = dict(schema_version=1, root=str(root), scope=scope,
                  status="complete" if complete else "diagnostic_partial",
                  completed_runs=len(inventory), expected_runs=88, missing_runs=missing,
                  metric="pooled masked RMSE@12, normalized feature units",
                  pooling="Sum squared errors / sum observed target entries; combine sets before square root",
                  seed_summary="Arithmetic mean and sample standard deviation (ddof=1) of per-seed RMSE; expected seeds 0..3",
                  scientific_conclusion_available=complete, protocols=protocols, inputs=inventory)
    write_json(out_json, result)
    write_table(owned_path(out_table), result)
    return result


def denominators(protocol, meta):
    e, r, c = meta["eligible_counts"], meta["retained_counts"], meta["counts"]
    labels = ("testA", "testB") if protocol == "transfer" else ("train", "val", "testA", "testB")
    parts = [f"{s}: {e[s]:,}/{r[s]:,} eligible/retained; {c[s]:,} used" for s in labels]
    if protocol == "transfer":
        parts.append(f"pooled: {e['testA']+e['testB']:,}/{r['testA']+r['testB']:,} eligible/retained; {c['testA']+c['testB']:,} used")
    return "Eligible-stay denominators (length ≥24 h): " + "; ".join(parts) + "."


def write_table(path, result):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# CinC-2012 transfer and within-corpus RMSE@12", "",
             f"Status: **{result['status']}**; scope: **{result['scope']}**; {result['completed_runs']}/88 runs.", "",
             "Each seed's RMSE pools squared errors over observed target entries. Transfer pooled RMSE combines set-a and set-b numerators and denominators before taking the square root. The displayed mean ± sd is across seeds (sample sd, ddof=1). An absent sd is unavailable, not zero.", "",
             "Transfer uses frozen CinC-2019 checkpoints and A-train normalization; both 2012 sets are test sets. Within-corpus uses 2012 A-train normalization and the fixed 2019-selected configurations. Its test_idx/testA is empty by design; only set-b is evaluated.", "",
             "The 2012 sets are not asserted to be different hospitals. This second corpus overlaps the CinC-2019 set-A hospital system; arterial SaO2 substitutes for pulse-oximetry O2Sat. See the frozen cohort report for static mapping and unit qualifications.", ""]
    if not result["scientific_conclusion_available"]:
        lines += ["**Diagnostic only: incomplete and/or smoke runs cannot establish corpus-level model orderings.**", ""]
    for protocol, section in result["protocols"].items():
        meta, models = section["data"], section["models"]
        splits = ("testA", "testB", "pooled") if protocol == "transfer" else ("testB",)
        lines += [f"## {protocol.capitalize()}", "", denominators(protocol, meta), "",
                  "| Model | Seeds | " + " | ".join(f"{s} RMSE@12" for s in splits) + " |",
                  "|---|---:|" + "---:|" * len(splits)]
        for model, row in models.items():
            lines.append(f"| {model} | {len(row['seeds_present'])}/4 | " + " | ".join(display(row["splits"][s]["RMSE"]) for s in splits) + " |")
        lines += [""]
        for split in splits:
            lines += [f"### {protocol.capitalize()} {split}: per-organ pooled RMSE@12", "",
                      denominators(protocol, meta), "",
                      "| Model | " + " | ".join(meta["organ_names"]) + " |",
                      "|---|" + "---:|" * len(meta["organ_names"])]
            for model, row in models.items():
                lines.append(f"| {model} | " + " | ".join(display(row["splits"][split]["organs"][o]) for o in meta["organ_names"]) + " |")
            lines += [""]
        lines += [f"### {protocol.capitalize()}: individual seeds", "", denominators(protocol, meta), "",
                  "| Model | Seed | Set | Used eligible stays | Observed target entries | RMSE@12 |",
                  "|---|---:|---|---:|---:|---:|"]
        for model, row in models.items():
            for split in splits:
                for seed, m in row["splits"][split]["per_seed"].items():
                    value = f"{m['pooled_masked_RMSE']:.9f}" if m["pooled_masked_RMSE"] is not None else "unavailable"
                    lines.append(f"| {model} | {seed} | {split} | {m['n_stays']} | {m['observed_entries']} | {value} |")
        lines += [""]
    path.write_text("\n".join(lines))


def reconstruct_table(source, destination):
    """Recompute seed summaries from shipped records; no data or inference."""
    verify_input(source)
    result = json.loads(Path(source).read_text())
    if (result["status"], result["scope"], result["completed_runs"]) != ("complete", "full", 88):
        raise ValueError("Table reconstruction requires the complete archived summary")
    for section in result["protocols"].values():
        if set(section["models"]) != set(MODELS):
            raise ValueError("Archived model inventory differs from the protocol")
        for model in section["models"].values():
            for split in model["splits"].values():
                seeds = split["per_seed"]
                if set(seeds) != {"0", "1", "2", "3"}:
                    raise ValueError("Archived seed inventory differs from the protocol")
                rmse = stats(row["pooled_masked_RMSE"] for row in seeds.values())
                organs = {organ: stats(row["organs"][organ]["RMSE"] for row in seeds.values())
                          for organ in section["data"]["organ_names"]}
                if split["RMSE"] != rmse or split["organs"] != organs:
                    raise ValueError("Archived summaries disagree with the per-seed metrics")
                split.update(RMSE=rmse, organs=organs)
    write_table(owned_path(destination), result)
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=RUN_ROOT)
    ap.add_argument("--out-json", type=Path)
    ap.add_argument("--out-table", type=Path)
    ap.add_argument("--from-summary", type=Path, help="reconstruct a table from distributed per-seed summary records; no training or error archives")
    ap.add_argument("--allow-partial", action="store_true", help="diagnostic only; retain all missing model/seed cells")
    args = ap.parse_args(argv)
    if args.from_summary:
        if args.out_json or args.allow_partial:
            ap.error("--from-summary uses --out-table only and requires the complete frozen summary")
        result = reconstruct_table(args.from_summary, args.out_table or RUN_ROOT / "TABLE_CINC2012.md")
    else:
        result = aggregate(args.root, out_json=args.out_json, out_table=args.out_table, allow_partial=args.allow_partial)
    print(json.dumps({k: result[k] for k in ("status", "scope", "completed_runs", "expected_runs")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
