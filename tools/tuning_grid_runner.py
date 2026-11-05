#!/usr/bin/env python3
"""Six configurations per architecture; validation-only selection then four seeds."""
from __future__ import annotations

# Resolve all public modules and scratch from the release root.
import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[1]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH
import argparse
import json
from pathlib import Path
import traceback

from v4_protocol import (HERE, MODELS, LRS, WIDTHS, add_data_args, config_id,
                         sizes_for, train_run, write_json, sha256)
import torch


def grid_jobs(models=MODELS):
    return [dict(model=m, lr=lr, width=w, cfg=config_id(lr, w), seed=0, sizes=sizes_for(m, w))
            for m in models for lr in LRS for w in WIDTHS]


def select(root, models=MODELS):
    root = Path(root)
    selected, inventory = {}, []
    for model in models:
        candidates = []
        for job in grid_jobs((model,)):
            file = root / "grid" / model / job["cfg"] / "seed0/run.json"
            if not file.is_file():
                raise ValueError(f"grid incomplete; cannot select: {file}")
            r = json.loads(file.read_text())
            if (r["model"], r["lr"], r["width"], r["seed"]) != (model, job["lr"], job["width"], 0):
                raise ValueError(f"wrong grid identity: {file}")
            inventory.append(dict(path=str(file), sha256=sha256(file), status=r["status"]))
            if r["status"] == "complete" and r.get("validation_RMSE") is not None:
                candidates.append((r["validation_RMSE"], job["cfg"], job, file))
        if not candidates:
            selected[model] = dict(status="blocked", reason="all six configurations failed")
            continue
        # Deterministic tie break by configuration ID, never by an A/B test metric.
        val, cfg, job, source = min(candidates, key=lambda r: (r[0], r[1]))
        selected[model] = dict(status="selected", lr=job["lr"], width=job["width"],
                               cfg=cfg, sizes=job["sizes"], validation_RMSE=val,
                               grid_run=str(source), grid_run_sha256=sha256(source))
    result = dict(schema_version=4, criterion="minimum A-validation pooled masked RMSE; cfg lexical tie break",
                  grid_seed=0, selected_seeds=[0, 1, 2, 3], epochs_budget=35,
                  grid=inventory, models=selected,
                  width_definition={m: {w: sizes_for(m, w) for w in WIDTHS} for m in models})
    write_json(root / "selection.json", result)
    return result


def run_safely(name, lr, width, seed, dest, **kwargs):
    """Numerical failure is an observed run outcome; infrastructure errors stay visible."""
    try:
        return train_run(name, lr, width, seed, dest, **kwargs)
    except FileExistsError:
        raise
    except Exception as e:
        traceback.print_exc()
        result = dict(schema_version=4, model=name, lr=lr, width=width, seed=seed,
                      status="failed", failure=f"{type(e).__name__}: {e}",
                      validation_RMSE=None, C=kwargs.get("C", 12), K=kwargs.get("K", 12),
                      variant=kwargs.get("variant", "admissible"))
        write_json(Path(dest) / "run.json", result)
        return result


def selected_run(args, *, C=12, K=12, variant="admissible", dest=None, curve=None, min_length=0):
    selection_file = args.root / "selection.json"
    selection = json.loads(selection_file.read_text())["models"][args.model]
    dest = Path(dest or args.root / "selected" / args.model / f"seed{args.seed}")
    if selection["status"] != "selected":
        if (dest / "run.json").exists():
            raise FileExistsError(dest)
        result = dict(schema_version=4, model=args.model, seed=args.seed, C=C, K=K, variant=variant,
                      status="blocked", reason=selection["reason"])
    else:
        curve = curve or args.root / "curves/selected" / f"{args.model}_{selection['cfg']}_seed{args.seed}.csv"
        result = run_safely(args.model, selection["lr"], selection["width"], args.seed, dest,
                           npz=args.npz, C=C, K=K, epochs=args.epochs, batch=args.batch,
                           device=args.device, max_stays=args.max_stays, variant=variant,
                           min_length=min_length, curve_path=curve)
    result.update(selection_file=str(selection_file.resolve()), selection_sha256=sha256(selection_file))
    write_json(dest / "run.json", result)
    return result


def summarize(root, models=MODELS):
    root = Path(root)
    selection = json.loads((root / "selection.json").read_text())
    grid = [dict(job, result=json.loads((root / "grid" / job["model"] / job["cfg"] / "seed0/run.json").read_text()))
            for job in grid_jobs(models)]
    selected = {m: {str(seed): json.loads((root / "selected" / m / f"seed{seed}/run.json").read_text())
                    for seed in range(4)} for m in models}
    write_json(root / "tuning_grid.json", dict(schema_version=4, selection=selection, grid=grid,
        selected_runs=selected, limitations=["Equal grid count and epoch cap do not imply equal wall time or parameter count.",
                                            "Failed cells remain in the inventory and are excluded from validation selection."]))


def parser():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=("run", "select", "final", "summarize", "plan"))
    ap.add_argument("--root", type=Path, default=HERE / "artifacts/smoke")
    ap.add_argument("--model", choices=MODELS)
    ap.add_argument("--models", default=",".join(MODELS))
    ap.add_argument("--lr", type=float, choices=LRS)
    ap.add_argument("--width", choices=WIDTHS)
    ap.add_argument("--seed", type=int, choices=range(4), default=0)
    ap.add_argument("--epochs", type=int, default=35)
    ap.add_argument("--device", default="cpu")
    add_data_args(ap)
    return ap


def main(argv=None):
    ap = parser()
    args = ap.parse_args(argv)
    models = tuple(args.models.split(","))
    if not models or any(m not in MODELS for m in models) or len(set(models)) != len(models):
        ap.error("models must be distinct registered architectures")
    torch.set_num_threads(args.threads)
    if args.action == "plan":
        print(json.dumps(grid_jobs(models), indent=2))
    elif args.action == "select":
        select(args.root, models)
    elif args.action == "summarize":
        summarize(args.root, models)
    elif args.action == "final":
        if not args.model:
            ap.error("final needs --model")
        selected_run(args)
    else:
        if args.model is None or args.lr is None or args.width is None or args.seed != 0:
            ap.error("grid run needs --model, --lr, --width and seed 0")
        cfg = config_id(args.lr, args.width)
        run_safely(args.model, args.lr, args.width, 0,
                   args.root / "grid" / args.model / cfg / "seed0",
                   npz=args.npz, epochs=args.epochs, batch=args.batch, device=args.device,
                   max_stays=args.max_stays, evaluate_tests=False,
                   curve_path=args.root / "curves/grid" / f"{args.model}_{cfg}_seed0.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
