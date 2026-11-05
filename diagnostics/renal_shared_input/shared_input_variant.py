#!/usr/bin/env python3
"""renal_diagnostic no-edge PhysioGraph-GRU: partitioned versus shared dynamic inputs.

Registry: physiograph_gru_factorised_partitioned and
physiograph_gru_factorised_shared. Both retain four organ-specific output heads,
GRU nodes, static inputs, rollout rules, and the selected v4 hyperparameters.
The shared mode changes both context and forecast-step projections to consume
16 values + 16 masks + 5 static features. It is not parameter-count matched.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import time

from renal_protocol import (HERE, PROJECT, collect_errors, finite_float,
                            make_data, metrics, runtime, save_errors, seed_all,
                            sha256, to_device, write_json)
import torch
from torch import nn
from organ_graph_ssm_model import PhysioGraph, PhysioGraphConfig

INPUT_MODES = ("partitioned", "shared")
SELECTION_SHA256 = "b5fff1d5de043d6c4b39cebc3bab9d48b0f378b24ac9d962344f0c8386055292"
FROZEN_SOURCES = {
    "organ_graph_ssm_model.py": "3426f8aa61ddcac3740ca4a0d799c25a421d91950cf773c957b68513232ac615",
    "physiograph_data_loader.py": "380a6058448f927c7265130a88b6272c438b2cbe8956d22ced28922583c19ba3",
    "physiograph_training_runner.py": "6adcdf67cf95d8b00b20aa0a01206f8a49987ed3fbfc2c131f4e9b346172347e",
}


def check_sources():
    for name, expected in FROZEN_SOURCES.items():
        if sha256(PROJECT / "src" / name) != expected:
            raise ValueError(f"frozen source changed: {name}")


class InputModePhysioGraph(PhysioGraph):
    """Keep the output partition; independently switch the dynamic input scope."""

    def __init__(self, cfg, input_mode="partitioned"):
        if input_mode not in INPUT_MODES:
            raise ValueError(input_mode)
        if cfg.edges or cfg.node_type != "gru" or cfg.n_control:
            raise ValueError("renal_diagnostic control requires no edges, GRU nodes, no controls")
        super().__init__(cfg)
        self.input_mode = input_mode
        self.node_input_widths = (tuple(cfg.organ_dims) if input_mode == "partitioned"
                                  else (cfg.n_feat,) * cfg.n_organs)
        if input_mode == "shared":
            # Construct the frozen base first so paired seeds have identical
            # recurrent/head weights; replace only the two input projections.
            width = 2 * cfg.n_feat + cfg.n_static
            self.in_proj = nn.ModuleList([
                nn.Linear(width, cfg.d_model) for _ in range(cfg.n_organs)])
            self.step_proj = nn.ModuleList([
                nn.Linear(width, cfg.d_model) for _ in range(cfg.n_organs)])

    def _organ_inputs(self, values, mask, static, control=None, t_slice=None):
        if self.input_mode == "partitioned":
            return super()._organ_inputs(values, mask, static, control, t_slice)
        B, T, _ = values.shape
        full = torch.cat([values, mask, static[:, None].expand(B, T, -1)], -1)
        return [full for _ in range(self.cfg.n_organs)]

    def rollout(self, values, mask, static, control_ctx=None, control_future=None,
                horizon=12):
        if self.input_mode == "partitioned":
            return super().rollout(values, mask, static, control_ctx,
                                   control_future, horizon)
        # Frozen rollout (src lines 248–280), with only input assembly widened.
        cfg = self.cfg
        _, states, _ = self.encode(values, mask, static, control_ctx)
        y_prev = values[:, -1].clone()
        preds = []
        for _ in range(horizon):
            organ_step = self._organ_inputs(y_prev[:, None],
                                           torch.ones_like(y_prev[:, None]), static)
            cur = [self.step_proj[i](organ_step[i][:, 0])
                   for i in range(cfg.n_organs)]
            for L in range(cfg.n_layers):
                outs = []
                for i in range(cfg.n_organs):
                    y, st = self.nodes[L][i].step(cur[i], states[L][i])
                    states[L][i] = st
                    outs.append(y)
                Hc, _ = self.couplers[L](torch.stack(outs, 1))
                cur = [Hc[:, i] for i in range(cfg.n_organs)]
            y_next = torch.zeros_like(y_prev)
            for i, (a, b) in enumerate(self.slices):
                y_next[:, a:b] = self.dec[i](cur[i])
            preds.append(y_next)
            y_prev = y_next
        return torch.stack(preds, 1)


def selected_config(selection_file=PROJECT / "results/v4/selection.json"):
    selection_file = Path(selection_file)
    if sha256(selection_file) != SELECTION_SHA256:
        raise ValueError("selection.json differs from frozen v4 selection")
    s = json.loads(selection_file.read_text())["models"]["physiograph_gru"]
    if s["status"] != "selected":
        raise ValueError("physiograph_gru has no selected configuration")
    return s


def build_variant(input_mode, sizes=None):
    sizes = sizes or selected_config()["sizes"]
    cfg = PhysioGraphConfig(organ_dims=(4, 4, 3, 5), n_static=5,
                            n_control=0, d_model=sizes["d_model"],
                            d_state=sizes["d_state"], n_layers=sizes["n_layers"],
                            edges=(), node_type="gru")
    return InputModePhysioGraph(cfg, input_mode)


def control_jobs():
    return [dict(input_mode=mode, seed=seed,
                 registry_id=f"physiograph_gru_factorised_{mode}",
                 run_id=f"{mode}/seed{seed}")
            for mode in INPUT_MODES for seed in range(4)]


def train_control(input_mode, seed, output_dir, *, npz=None, epochs=35,
                  batch=128, device="cpu", max_stays=None):
    """clinical_protocol train_run protocol; only the model factory/identity metadata differ.

    Same Adam, decay, cosine schedule, clip, min_delta, patience and validation
    selection. A/B are evaluated only after selection. 35 is an epoch cap.
    """
    if not 1 <= epochs <= 35:
        raise ValueError("epoch budget must be between 1 and 35")
    if max_stays is not None and not 4 <= max_stays <= 64:
        raise ValueError("smoke cap must be 4–64 total stays")
    if input_mode not in INPUT_MODES or seed not in range(4):
        raise ValueError("unregistered mode or seed")
    check_sources()
    selection = selected_config()
    lr, width, sizes = selection["lr"], selection["width"], selection["sizes"]
    output_dir = Path(output_dir).resolve()
    if not output_dir.is_relative_to(PROJECT):
        raise ValueError("output must stay inside the repository")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"refusing to overwrite a run: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    seed_all(seed)
    loaders, meta = make_data(npz, 12, 12, batch, seed, max_stays)
    if meta["cohort_sha256"] != "d52d8131323fc7a3838ae4fe523c2edbc02d2daa781de1859e7d184897dfb51f":
        raise ValueError("cohort differs from frozen CinC-2019 data")
    model = build_variant(input_mode, sizes).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, epochs)
    curve_path = output_dir / "curve.csv"
    best_val, best_state, stale, best_epoch = float("inf"), None, 0, None
    failure = None
    started = time.monotonic()
    with curve_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=("epoch", "train_masked_mse", "val_RMSE", "lr", "gradient_norm_max", "improved", "seconds"))
        writer.writeheader()
        for ep in range(epochs):
            model.train()
            tot_sse = tot_n = grad_max = 0.0
            used_lr = opt.param_groups[0]["lr"]
            for batch_data in loaders[0]:
                b = to_device(batch_data, device)
                opt.zero_grad(set_to_none=True)
                pred = model(b, horizon=12)
                n = b["target_mask"].sum()
                if n == 0:
                    continue
                sse = ((pred - b["target"]).square() * b["target_mask"]).sum()
                loss = sse / n
                if not torch.isfinite(loss):
                    failure = f"nonfinite training loss at epoch {ep + 1}"
                    break
                loss.backward()
                gn = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                if not torch.isfinite(gn):
                    failure = f"nonfinite gradient at epoch {ep + 1}"
                    break
                grad_max = max(grad_max, float(gn))
                opt.step()
                tot_sse += float(sse.detach())
                tot_n += float(n)
            val_errors = collect_errors(model, loaders[1], 12, device, meta["organ_slices"])
            val = metrics(val_errors, meta["organ_names"])["pooled_masked_RMSE"]
            if val is None:
                failure = failure or f"nonfinite validation at epoch {ep + 1}"
            improved = failure is None and val < best_val - 1e-4
            if improved:
                best_val, best_epoch, stale = val, ep + 1, 0
                best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            else:
                stale += 1
            writer.writerow(dict(epoch=ep + 1, train_masked_mse=tot_sse / tot_n if tot_n else "",
                                 val_RMSE=val if val is not None else "", lr=used_lr,
                                 gradient_norm_max=grad_max, improved=improved,
                                 seconds=time.monotonic() - started))
            f.flush()
            print(f"{input_mode} seed={seed} epoch={ep+1} val={val} failure={failure}", flush=True)
            sched.step()
            if failure or stale >= 8:
                break
    registry_id = f"physiograph_gru_factorised_{input_mode}"
    result = dict(schema_version=1, diagnostic="renal_shared_input",
                  scope="smoke" if max_stays is not None else "full",
                  model="physiograph_gru", registry_id=registry_id, input_mode=input_mode,
                  seed=seed, lr=lr, width=width, sizes=sizes, variant="none", edges=[],
                  node_input_widths=list(model.node_input_widths),
                  projection_input_widths=[p.in_features for p in model.in_proj],
                  C=12, K=12, epochs_budget=epochs, epochs_completed=ep + 1,
                  best_epoch=best_epoch, validation_RMSE=finite_float(best_val),
                  status="failed" if failure or best_state is None else "complete", failure=failure,
                  patience=8, min_delta=1e-4, optimizer="Adam", weight_decay=1e-5,
                  scheduler="CosineAnnealingLR", gradient_clip=1.0,
                  n_params=sum(p.numel() for p in model.parameters()),
                  curve=str(curve_path.relative_to(PROJECT)), data=meta, runtime=runtime(),
                  selection=selection, selection_sha256=SELECTION_SHA256,
                  source_sha256={p.name: sha256(p) for p in sorted((PROJECT / "src").glob("*.py"))},
                  extension_sha256={p.name: sha256(p) for p in (Path(__file__), HERE / "renal_protocol.py")},
                  seconds=time.monotonic() - started)
    if result["status"] == "complete":
        model.load_state_dict(best_state)
        checkpoint = output_dir / "checkpoint.pt"
        torch.save(dict(state_dict=best_state, model="physiograph_gru", sizes=sizes,
                        variant="none", registry_id=registry_id, input_mode=input_mode,
                        seed=seed, C=12, K=12, cohort_sha256=meta["cohort_sha256"]), checkpoint)
        result["checkpoint"] = str(checkpoint.relative_to(PROJECT))
        result["checkpoint_sha256"] = sha256(checkpoint)
        for split, loader in zip(("A", "B"), loaders[2:]):
            errors = collect_errors(model, loader, 12, device, meta["organ_slices"])
            save_errors(output_dir / f"errors_{split}.npz", errors)
            result[split] = metrics(errors, meta["organ_names"])
    write_json(output_dir / "run.json", result)
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input_mode", choices=INPUT_MODES)
    ap.add_argument("--seed", type=int, choices=range(4), default=0)
    ap.add_argument("--epochs", type=int, default=35)
    ap.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    ap.add_argument("--batch", type=int, default=128)
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--max-stays", type=int)
    ap.add_argument("--npz", type=Path, default=PROJECT / "data/cinc2019_cohort.npz")
    ap.add_argument("--output-dir", type=Path)
    ap.add_argument("--plan", action="store_true")
    args = ap.parse_args(argv)
    if args.plan:
        print(json.dumps(control_jobs(), indent=2))
        return 0
    if args.input_mode is None:
        ap.error("--input_mode is required for a fit")
    torch.set_num_threads(args.threads)
    dest = args.output_dir or PROJECT / "runs/renal_shared_input" / args.input_mode / f"seed{args.seed}"
    result = train_control(args.input_mode, args.seed, dest, npz=args.npz,
                           epochs=args.epochs, batch=args.batch, device=args.device,
                           max_stays=args.max_stays)
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
