#!/usr/bin/env python3
"""Frozen 2019 checkpoint inference on both CinC-2012 test sets; no fitting."""
from __future__ import annotations

import argparse
from pathlib import Path
import time

from cinc2012_common import (RUN_ROOT, MODELS, TRANSFER_NPZ, SELECTION, load_checkpoint,
    make_data, output_dir, evaluate_split, runtime_sources, setup_device, v4, write_json)
import numpy as np


def run(model, seed, *, npz=TRANSFER_NPZ, out_root=RUN_ROOT, device="cpu",
        checkpoint=None, selection=SELECTION, max_stays=None, batch=128, threads=2):
    started = time.monotonic()
    if batch != 128:
        raise ValueError("Batch size is frozen at 128 for every model")
    device = setup_device(device, threads)
    dest = output_dir(out_root, "transfer", model, seed)
    v4.seed_all(seed)
    net, checkpoint_info = load_checkpoint(model, seed, checkpoint, device, selection)
    loaders, meta = make_data(npz, "transfer", batch, seed, max_stays)
    results, errors = {}, []
    for split, loader in loaders.items():
        err, results[split] = evaluate_split(net, loader, meta, device, dest, split)
        errors.append(err)
    # Sum error numerators/observed-label denominators across sets, never RMSEs.
    pooled = {key: np.concatenate([e[key] for e in errors]) for key in errors[0]}
    results["pooled"] = v4.metrics(pooled, meta["organ_names"])
    result = dict(schema_version=1, protocol="transfer", scope="smoke" if max_stays else "full",
                  model=model, seed=seed, status="complete", C=12, K=12, device=device, batch=batch,
                  training_performed=False, checkpoint=checkpoint_info, data=meta, results=results,
                  source_sha256=runtime_sources(), runtime=v4.runtime(), seconds=time.monotonic() - started)
    write_json(dest / "run.json", result)
    print(f"{model} seed={seed} RMSE@12: " + str({k: v['pooled_masked_RMSE'] for k, v in results.items()}), flush=True)
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", choices=MODELS, required=True)
    ap.add_argument("--seed", type=int, choices=range(4), required=True)
    ap.add_argument("--npz", type=Path, default=TRANSFER_NPZ)
    ap.add_argument("--out_root", "--out-root", type=Path, default=RUN_ROOT)
    ap.add_argument("--checkpoint", type=Path)
    ap.add_argument("--selection", type=Path, default=SELECTION)
    ap.add_argument("--device", required=True)
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--batch", type=int, default=128)
    ap.add_argument("--max-stays", type=int, help="smoke only: total across both sets, 8..64")
    run(**vars(ap.parse_args(argv)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
