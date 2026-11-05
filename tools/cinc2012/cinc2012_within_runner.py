#!/usr/bin/env python3
"""Final-mode extension: fixed selected config, CinC-2012 train/val, testB only."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import time

from cinc2012_common import (RUN_ROOT, MODELS, LEARNED_MODELS, WITHIN_NPZ, SELECTION,
    selected_config, build_learned, make_data, output_dir, evaluate_split, runtime_sources,
    setup_device, v4, write_json, sha256)
import torch


def within_data_for_v4(npz=None, C=12, K=12, batch=128, seed=0, max_stays=None, min_length=0):
    if (C, K, min_length) != (12, 12, 0):
        raise ValueError("This protocol fixes C=K=12 and the frozen length>=24 filter")
    loaders, meta = make_data(npz or WITHIN_NPZ, "within", batch, seed, max_stays)
    return [loaders["train"], loaders["val"], None, loaders["testB"]], meta


def train_learned(model, seed, dest, npz, epochs, device, max_stays, batch):
    """Device-enabled learned-graph optimization with the original losses."""
    v4.seed_all(seed)
    torch.use_deterministic_algorithms(True)
    net = build_learned(model).to(device)
    loaders, meta = make_data(npz, "within", batch, seed, max_stays)
    if model == "grafiti":
        from port_utils_v3 import query_mse as loss_fn
    else:
        from physiograph_training_runner import masked_mse as loss_fn
    optimizer = torch.optim.Adam(net.parameters(), lr=.001, weight_decay=1e-5)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, epochs)
    best_val, best_state, stale, best_epoch = float("inf"), None, 0, None
    history = []
    dest.mkdir(parents=True, exist_ok=True)
    with (dest / "curve.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("epoch", "train_loss", "val_RMSE", "lr", "improved"))
        writer.writeheader()
        for ep in range(epochs):
            net.train()
            total = 0.
            lr = optimizer.param_groups[0]["lr"]
            for batch_data in loaders["train"]:
                b = v4.to_device(batch_data, device)
                optimizer.zero_grad(set_to_none=True)
                pred = net(b, horizon=12)
                loss = loss_fn(pred, b["target"], b["target_mask"])
                if not torch.isfinite(loss):
                    raise ValueError("Nonfinite learned-graph training loss")
                loss.backward()
                gn = torch.nn.utils.clip_grad_norm_(net.parameters(), 1.)
                if not torch.isfinite(gn):
                    raise ValueError("Nonfinite learned-graph gradient")
                optimizer.step()
                total += float(loss.detach())
            scheduler.step()
            errors = v4.collect_errors(net, loaders["val"], 12, device, meta["organ_slices"])
            val = v4.metrics(errors, meta["organ_names"])["pooled_masked_RMSE"]
            if val is None or errors["nonfinite"].sum():
                raise ValueError("Nonfinite learned-graph validation")
            improved = val < best_val - 1e-4
            if improved:
                best_val, best_epoch, stale = val, ep + 1, 0
                best_state = {k: v.detach().cpu().clone() for k, v in net.state_dict().items()}
            else:
                stale += 1
            row = dict(epoch=ep + 1, train_loss=total / len(loaders["train"]), val_RMSE=val,
                       lr=lr, improved=improved)
            history.append(row)
            writer.writerow(row)
            stream.flush()
            print(f"{model} seed={seed} epoch={ep+1} val={val}", flush=True)
            if stale >= 8:
                break
    if best_state is None:
        raise ValueError("No finite learned-graph validation checkpoint")
    net.load_state_dict(best_state)
    checkpoint = dest / "checkpoint.pt"
    torch.save(dict(state_dict=best_state, model=model, seed=seed, C=12, K=12,
                    architecture=net.config, cohort_sha256=meta["cohort_sha256"]), checkpoint)
    result = dict(model=model, seed=seed, status="complete", lr=.001, architecture=net.config,
                  C=12, K=12, epochs_budget=epochs, epochs_completed=len(history), best_epoch=best_epoch,
                  validation_RMSE=best_val, optimizer="Adam", weight_decay=1e-5,
                  scheduler="CosineAnnealingLR", patience=8, min_delta=1e-4, gradient_clip=1.,
                  loss="mean observed queries per nonempty example, then mean examples" if model == "grafiti" else "pooled masked MSE per batch",
                  checkpoint=str(checkpoint), checkpoint_sha256=sha256(checkpoint), data=meta,
                  n_params=sum(p.numel() for p in net.parameters()))
    return net, loaders["testB"], result


def run(model, seed, *, npz=WITHIN_NPZ, out_root=RUN_ROOT, device="cpu",
        selection=SELECTION, epochs=35, max_stays=None, batch=128, threads=2):
    if not 1 <= epochs <= 35 or (max_stays is None and epochs != 35):
        raise ValueError("Full runs use the 35-epoch cap; shorter runs require the smoke stay cap")
    if batch != 128:
        raise ValueError("Batch size is frozen at 128 for every model")
    started = time.monotonic()
    device = setup_device(device, threads)
    dest = output_dir(out_root, "within", model, seed)
    if model in LEARNED_MODELS:
        net, test_b, result = train_learned(model, seed, dest, npz, epochs, device, max_stays, batch)
    else:
        choice = selected_config(model, selection)
        # The original final-mode path calls train_run with these same options.
        # Replace only its data provider and disable its generic A/B test loop.
        original_data = v4.make_data
        v4.make_data = within_data_for_v4
        try:
            result = v4.train_run(model, choice["lr"], choice["width"], seed, dest,
                                  npz=npz, epochs=epochs, batch=batch, device=device,
                                  max_stays=max_stays, evaluate_tests=False)
        finally:
            v4.make_data = original_data
        result.update(selection_file=str(selection.resolve()), selection_sha256=sha256(selection))
        if result["status"] != "complete":
            result.update(protocol="within", results={})
            write_json(dest / "run.json", result)
            raise RuntimeError(f"Within fit failed: {result.get('failure')}")
        net = v4.build(model, result["sizes"], result["variant"]).to(device)
        checkpoint = torch.load(dest / "checkpoint.pt", map_location="cpu", weights_only=True)
        net.load_state_dict(checkpoint["state_dict"], strict=True)
        loaders, _ = make_data(npz, "within", batch, seed, max_stays)
        test_b = loaders["testB"]
    _, test_metrics = evaluate_split(net, test_b, result["data"], device, dest, "testB")
    result.update(schema_version=1, protocol="within", scope="smoke" if max_stays else "full",
                  device=device, batch=batch, training_performed=True,
                  evaluation_note="test_idx/testA is empty by design; evaluate set-b (testB) only",
                  results=dict(testB=test_metrics), source_sha256=runtime_sources(),
                  runtime=v4.runtime(), seconds=time.monotonic() - started)
    write_json(dest / "run.json", result)
    print(f"{model} seed={seed} testB RMSE@12={test_metrics['pooled_masked_RMSE']}", flush=True)
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", choices=MODELS, required=True)
    ap.add_argument("--seed", type=int, choices=range(4), required=True)
    ap.add_argument("--npz", type=Path, default=WITHIN_NPZ)
    ap.add_argument("--out_root", "--out-root", type=Path, default=RUN_ROOT)
    ap.add_argument("--selection", type=Path, default=SELECTION)
    ap.add_argument("--device", required=True)
    ap.add_argument("--epochs", type=int, default=35)
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--batch", type=int, default=128)
    ap.add_argument("--max-stays", type=int, help="smoke only: total across train/val/testB, 8..64")
    run(**vars(ap.parse_args(argv)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
