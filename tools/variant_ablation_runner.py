#!/usr/bin/env python3
"""Graph controls: the admissible rows reference the actual Table 1 runs."""
from __future__ import annotations

# Resolve all public modules and scratch from the release root.
import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[1]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH
import argparse
import json
from pathlib import Path

from v4_protocol import HERE, VARIANTS, add_data_args, edges_for, sha256, write_json
from tuning_grid_runner import selected_run
import numpy as np
import torch

BACKBONES = ("physiograph", "physiograph_gru")


def variant_jobs():
    return [dict(model=m, variant=v, seed=s, reused=v == "admissible")
            for m in BACKBONES for v in VARIANTS for s in range(4)]


def source_run(root, model, variant, seed):
    if variant == "admissible":
        return Path(root) / "selected" / model / f"seed{seed}/run.json"
    return Path(root) / "variants" / model / variant / f"seed{seed}/run.json"


def summarize(root):
    root = Path(root)
    table = {}
    for model in BACKBONES:
        for variant in VARIANTS:
            runs = []
            for seed in range(4):
                file = source_run(root, model, variant, seed)
                r = json.loads(file.read_text())
                base_file = source_run(root, model, "admissible", seed)
                base = json.loads(base_file.read_text())
                if r["status"] == "complete" and base["status"] == "complete":
                    for key in ("sizes", "lr", "width", "C", "K", "selection_sha256"):
                        if r[key] != base[key]:
                            raise ValueError(f"variant differs in {key}: {file}")
                    if r["data"]["split_stay_indices"] != base["data"]["split_stay_indices"]:
                        raise ValueError("ablation membership differs")
                runs.append(dict(seed=seed, path=str(file), sha256=sha256(file),
                                 reused_table1=variant == "admissible", status=r["status"],
                                 A=r.get("A"), B=r.get("B"), n_params=r.get("n_params")))
            cell = dict(edges=edges_for(variant), runs=runs)
            for split in ("A", "B"):
                vals = [r[split]["pooled_masked_RMSE"] for r in runs
                        if r["status"] == "complete" and r[split]["pooled_masked_RMSE"] is not None]
                cell[split] = dict(n_seeds=len(vals), mean=float(np.mean(vals)) if vals else None,
                    sd_sample=float(np.std(vals, ddof=1)) if len(vals) > 1 else None,
                    status="complete" if len(vals) == 4 else "incomplete")
            table.setdefault(model, {})[variant] = cell
    write_json(root / "variant_ablation_v4.json", dict(schema_version=4, table=table,
        protocol="Same selected widths/lr, optimizer, seeds 0–3, split and 35-epoch budget as Table 1; no per-variant retuning.",
        reconciliation="Admissible runs point to selected/<model>/seed<k>/run.json; no duplicate training or separately rounded source.",
        misspecified_1="Replace cardiovascular->renal (0,2) by pulmonary->renal (1,2); seven original edges retained, count fixed at eight.",
        random="Frozen source resolver: eight of twelve directed non-self edges, NumPy default_rng(0), fixed for all training seeds.",
        limits=["Graph variants allocate different parameter counts; these are structural ablations, not equal-parameter controls.",
                "The reversed edge set overlaps six of eight original edges; it is not disjoint from the physiological prior."]))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=("run", "summarize", "plan"))
    ap.add_argument("--root", type=Path, default=HERE / "artifacts/smoke")
    ap.add_argument("--model", choices=BACKBONES, default="physiograph_gru")
    ap.add_argument("--variant", choices=VARIANTS, default="admissible")
    ap.add_argument("--seed", type=int, choices=range(4), default=0)
    ap.add_argument("--epochs", type=int, default=35)
    ap.add_argument("--device", default="cpu")
    add_data_args(ap)
    args = ap.parse_args(argv)
    torch.set_num_threads(args.threads)
    if args.action == "plan":
        print(json.dumps(variant_jobs(), indent=2))
    elif args.action == "summarize":
        summarize(args.root)
    elif args.variant == "admissible":
        file = source_run(args.root, args.model, args.variant, args.seed)
        if not file.exists():
            raise ValueError(f"Table 1 run missing; train via tuning_grid_runner final: {file}")
        print(f"reused Table 1 run: {file} sha256={sha256(file)}")
    else:
        dest = source_run(args.root, args.model, args.variant, args.seed).parent
        curve = args.root / "curves/variants" / args.model / args.variant / f"seed{args.seed}.csv"
        selected_run(args, variant=args.variant, dest=dest, curve=curve)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
