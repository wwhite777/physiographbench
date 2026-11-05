#!/usr/bin/env python3
"""Trace Neural CDE on external B, without fitting or updating on external outcomes."""
from __future__ import annotations

# Resolve all public modules and scratch from the release root.
import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[1]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH
import argparse
import json
import math
from pathlib import Path

from v4_protocol import (HERE, PROJECT, add_data_args, build, make_data, sha256,
                         finite_float, write_json)
import numpy as np
import torch
import torchcde


def interpolation(batch, explicit_grid=False):
    v, m = batch["values"], batch["mask"]
    T = v.shape[1]
    physical = torch.linspace(0, 1, T, device=v.device)
    path = torch.cat([physical[None, :, None].expand(v.shape[0], -1, -1), v * m, m], -1)
    if explicit_grid:
        coeffs = torchcde.natural_cubic_coeffs(path, t=physical)
        X = torchcde.CubicSpline(coeffs, t=physical)
    else:
        coeffs = torchcde.natural_cubic_coeffs(path)
        X = torchcde.CubicSpline(coeffs)
    return X, coeffs, physical


def probe(model, batch, explicit_grid=False, K=12):
    model.eval()
    model.zero_grad(set_to_none=True)
    X, coeffs, physical = interpolation(batch, explicit_grid)
    step_size = 1.0 / (batch["values"].shape[1] - 1)
    t0, t1 = (float(x) for x in X.interval)
    row = dict(mode="explicit_0_1_grid" if explicit_grid else "frozen_default_index_grid",
               spline_grid=X.grid_points.tolist(), time_channel=physical.tolist(),
               rk4_step_size=step_size, nominal_solver_steps=math.ceil((t1 - t0) / step_size - 1e-6),
               coefficients_nonfinite=int((~torch.isfinite(coeffs)).sum()), status="complete")
    try:
        z0 = model.z0(X.evaluate(X.interval[0]))
        zt = torchcde.cdeint(X=X, func=model.func, z0=z0, t=X.interval, method="rk4", options={"step_size": step_size})
        pred = model.dec.rollout(zt[:, -1], batch["static"], batch["values"][:, -1], K)
        target, mask = batch["target"], batch["target_mask"]
        loss = ((pred - target).square() * mask).sum() / mask.sum().clamp(min=1)
        row.update(loss=finite_float(loss.detach()), predictions_nonfinite=int((~torch.isfinite(pred)).sum()),
                   latent_nonfinite=int((~torch.isfinite(zt)).sum()),
                   latent_abs_max=finite_float(zt.detach().abs().max()),
                   prediction_abs_max=finite_float(pred.detach().abs().max()))
        loss.backward()
        grads = [(name, p.grad.detach()) for name, p in model.named_parameters() if p.grad is not None]
        row["gradient_nonfinite"] = sum(int((~torch.isfinite(g)).sum()) for _, g in grads)
        row["gradient_norm"] = finite_float(torch.sqrt(sum(g.double().square().sum() for _, g in grads)))
        row["parameter_gradients"] = {name: dict(norm=finite_float(g.double().norm()),
            nonfinite=int((~torch.isfinite(g)).sum())) for name, g in grads}
        if row["loss"] is None or row["predictions_nonfinite"] or row["gradient_nonfinite"]:
            row["status"] = "nonfinite"
    except Exception as e:
        row.update(status="exception", error=f"{type(e).__name__}: {e}")
    return row


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    add_data_args(ap)
    ap.set_defaults(batch=8, max_stays=64)
    ap.add_argument("--checkpoint", type=Path, default=PROJECT / "runs/clinical/selected/ncde/seed0/checkpoint.pt")
    ap.add_argument("--out", type=Path, default=HERE / "ncde_diagnosis.md")
    ap.add_argument("--trace", type=Path, default=HERE / "artifacts/ncde_trace.json")
    ap.add_argument("--frozen-stats", type=Path, default=HERE / "stats_v4.json",
                    help="when available, use verified full-B errors to include worst cases in the fixed-size probe")
    args = ap.parse_args(argv)
    torch.set_num_threads(args.threads)
    state = torch.load(args.checkpoint, map_location="cpu", weights_only=True)
    model = build("ncde", state.get("sizes"))
    model.load_state_dict(state.get("state_dict", state))
    loaders, meta = make_data(args.npz, batch=args.batch, max_stays=args.max_stays)
    full_B = None
    if args.frozen_stats.is_file():
        cached = json.loads(args.frozen_stats.read_text())
        record = cached.get("checkpoints", {}).get("frozen_unattributed", {}).get("ncde", {})
        source = record.get("splits", {}).get("B")
        if source and record.get("checkpoint_sha256") == sha256(args.checkpoint):
            if sha256(source["error_file"]) != source["sha256"] or cached["data"]["cohort_sha256"] != meta["cohort_sha256"]:
                raise ValueError("cached B errors do not match the frozen cohort/artifact")
            with np.load(source["error_file"]) as archive:
                e = dict(archive)
            valid = (e["count"] > 0) & np.isfinite(e["sse"])
            rmse = np.sqrt(e["sse"][valid] / e["count"][valid])
            ids = e["stay_index"][valid]
            worst = ids[np.argsort(rmse)[::-1][:len(loaders[3].dataset) // 2]]
            random_ids = loaders[3].dataset.idx
            random_ids = random_ids[~np.isin(random_ids, worst)]
            loaders[3].dataset.idx = np.concatenate([worst, random_ids])[:meta["counts"]["B"]]
            meta["split_stay_indices"]["B"] = loaders[3].dataset.idx.tolist()
            full_B = dict(n_stays=len(e["count"]), n_evaluable_stays=int(valid.sum()),
                nonfinite_predictions=int(e["nonfinite"].sum()),
                pooled_masked_RMSE=source["metrics"]["pooled_masked_RMSE"],
                window_RMSE_percentiles={str(q):float(np.percentile(rmse, q)) for q in (50,90,95,99,100)},
                worst_stay_indices_in_probe=worst.tolist(), error_sha256=source["sha256"],
                selection="half of B probe from worst frozen-checkpoint window RMSEs; remainder from fixed random subset")
    trace = []
    # Both forward and backward are diagnostic. No optimizer or parameter updates on B.
    for batch_index, batch in enumerate(loaders[3]):
        for explicit in (False, True):
            row = probe(model, batch, explicit)
            row.update(batch_index=batch_index, stay_indices=batch["stay_index"].tolist())
            trace.append(row)
            print(json.dumps({k: row.get(k) for k in ("batch_index", "mode", "status", "loss", "gradient_norm")}), flush=True)
    result = dict(schema_version=4, checkpoint=str(args.checkpoint), checkpoint_sha256=sha256(args.checkpoint),
                  data=meta, trace=trace, full_B_frozen_error_summary=full_B, external_B_updates=0,
                  purpose="diagnosis only; explicit grid is a numerical comparison, not a newly tuned baseline")
    write_json(args.trace, result)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Neural controlled differential equation (CDE) diagnosis", "", f"Checkpoint SHA-256: `{result['checkpoint_sha256']}`.", "",
        f"CPU probe on {meta['counts']['B']} external B stays. "
        + ("Half are the worst windows from verified full-B frozen-checkpoint errors; the rest come from a fixed random subset. " if full_B else "A seed-independent fixed random subset is used. ")
        + "This purposive diagnostic subset does not estimate population performance. No optimizer or updates on B.", "",
        "The frozen model puts a time **channel** from 0 to 1 in the path, but supplies no time **grid** to natural_cubic_coeffs/CubicSpline. "
        "The default spline grid therefore runs from 0 to C−1. For context length C=12, the fourth-order Runge–Kutta (RK4) step is 1/11 over [0,11], nominally 121 steps. "
        "The diagnostic comparison passes the same explicit [0,1] grid to both coefficient construction and spline evaluation, using the same 1/11 step (11 steps). "
        "A time channel and a spline parameter grid need not agree: a change of path parameter is valid for a CDE in continuous time. "
        "Holding this numerical step size fixed gives different integration resolution under the two parameterizations. "
        "The comparison does not by itself prove why a trained model diverged. Neither trace changes the frozen model or the registered tuning runs.", "",
        "| Batch | Grid | Loss on B | Gradient norm | Nonfinite predictions | Nonfinite gradients | Status |", "|---|---|---:|---:|---:|---:|---|"]
    for r in trace:
        lines.append(f"| {r['batch_index']} | {r['mode']} | {r.get('loss')} | {r.get('gradient_norm')} | {r.get('predictions_nonfinite')} | {r.get('gradient_nonfinite')} | {r['status']} |")
    if full_B:
        lines += ["", f"The already-computed full-B frozen-checkpoint evaluation covers {full_B['n_stays']} eligible stays, "
            f"with pooled masked RMSE {full_B['pooled_masked_RMSE']:.6f} and {full_B['nonfinite_predictions']} nonfinite predictions. "
            f"Per-window RMSE percentiles are `{json.dumps(full_B['window_RMSE_percentiles'])}`. "
            "These cached full-cohort errors motivate the worst-case probe; they are not evidence that the historical training trajectory has been recovered. "
            "The observed failure mode is a tail of large finite errors and gradients; the frozen evaluation did not reproduce nonfinite predictions."]
    lines += ["", "The loss averages squared error over observed targets in A-train-normalized units. Gradients are measured before any clipping. "
        "The trace JSON includes the exact grid, solver step, maximum latent/prediction magnitudes, parameter-wise gradients, and counts of not-a-number (NaN) and infinite (Inf) values. "
        "A finite subset probe cannot establish numerical stability on all B stays or during full training. "
        "Historical training losses/gradients were not saved, so this is a frozen-checkpoint diagnosis rather than a reconstruction of its training trajectory.", "",
        f"Trace: `{args.trace}` (SHA-256 `{sha256(args.trace)}`)."]
    args.out.write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
