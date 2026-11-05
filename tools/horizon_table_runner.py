#!/usr/bin/env python3
"""Fixed-context horizon experiments, with the same >=48 h cohort in all five cells."""
from __future__ import annotations

# Resolve all public modules and scratch from the release root.
import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[1]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH
import argparse
import json
from pathlib import Path

from v4_protocol import HERE, MODELS, DESIGNS, add_data_args, write_json, sha256
from tuning_grid_runner import selected_run
import numpy as np
import torch


def horizon_jobs(models=MODELS):
    return [dict(model=m, C=C, K=K, seed=s) for C, K in DESIGNS for m in models for s in range(4)]


def summarize(root, models=MODELS):
    root = Path(root)
    table, membership = {}, None
    for C, K in DESIGNS:
        cell = {}
        for model in models:
            runs = []
            for seed in range(4):
                file = root / "horizons" / f"C{C}_K{K}" / model / f"seed{seed}/run.json"
                r = json.loads(file.read_text())
                runs.append(dict(seed=seed, path=str(file), sha256=sha256(file), status=r["status"],
                                 A=r.get("A"), B=r.get("B")))
                if r["status"] == "complete":
                    ids = r["data"]["split_stay_indices"]
                    if membership is not None and membership != ids:
                        raise ValueError("horizon cohort changed")
                    membership = ids
            cell[model] = dict(runs=runs)
            for split in ("A", "B"):
                vals = [r[split]["pooled_masked_RMSE"] for r in runs
                        if r["status"] == "complete" and r[split]["pooled_masked_RMSE"] is not None]
                cell[model][split] = dict(n_seeds=len(vals), mean=float(np.mean(vals)) if vals else None,
                    sd_sample=float(np.std(vals, ddof=1)) if len(vals) > 1 else None,
                    status="complete" if len(vals) == 4 else "incomplete")
        table[f"C{C}_K{K}"] = cell
    write_json(root / "horizon_table_v4.json", dict(schema_version=4, designs=DESIGNS, table=table,
        policy="Use >=48 h stays for training, validation and both tests in ALL five designs; A-train normalization remains frozen.",
        selection="Reuse C12/K12 tuning selection; no horizon-specific retuning. Fresh fits for each horizon/seed.",
        split_stay_indices=membership,
        limits=["C12/K12 horizon row uses the common >=48 h cohort and is distinct from Table 1's >=24 h cohort.",
                "Errors pool all K target hours; they are not errors only at the final hour.",
                "No conclusion about an entire length-unrestricted ICU population follows from this common cohort."]))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=("run", "summarize", "plan"))
    ap.add_argument("--root", type=Path, default=HERE / "artifacts/smoke")
    ap.add_argument("--model", choices=MODELS)
    ap.add_argument("--models", default=",".join(MODELS))
    ap.add_argument("--C", type=int, default=12)
    ap.add_argument("--K", type=int, default=12)
    ap.add_argument("--seed", type=int, choices=range(4), default=0)
    ap.add_argument("--epochs", type=int, default=35)
    ap.add_argument("--device", default="cpu")
    add_data_args(ap)
    args = ap.parse_args(argv)
    torch.set_num_threads(args.threads)
    models = tuple(args.models.split(","))
    if len(set(models)) != len(models) or any(m not in MODELS for m in models):
        ap.error("invalid models")
    if args.action == "plan":
        print(json.dumps(horizon_jobs(models), indent=2))
    elif args.action == "summarize":
        summarize(args.root, models)
    else:
        if args.model is None or (args.C, args.K) not in DESIGNS:
            ap.error("need --model and a registered (C,K) pair")
        dest = args.root / "horizons" / f"C{args.C}_K{args.K}" / args.model / f"seed{args.seed}"
        curve = args.root / "curves/horizons" / f"C{args.C}_K{args.K}" / f"{args.model}_seed{args.seed}.csv"
        selected_run(args, C=args.C, K=args.K, dest=dest, curve=curve, min_length=48)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
