#!/usr/bin/env python3
"""Post-hoc edge ablation on the shared-input GRU backbone.

Six frozen v4 edge sets, four paired training seeds, one selected configuration,
no retuning. Every organ gets all 16 values, 16 masks and five static features
in context and forecast feedback; organ-specific outputs are retained.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
# Import the local helper FIRST: the renal diagnostic module then reuses it without selecting
# renal diagnostic scratch. All helper function/class definitions are unchanged from renal diagnostic.
from renal_protocol import (HERE, PROJECT, collect_errors, finite_float,
                            make_data, metrics, runtime, save_errors, seed_all,
                            sha256, to_device, write_json)
import torch
from torch import nn
from organ_graph_ssm_model import (ADMISSIBLE_EDGES, PhysioGraph,
                                   PhysioGraphConfig, _resolve_edges)

VARIANTS = ("none", "admissible", "dense", "reversed", "random", "misspecified-1")
INPUT_MODES = ("shared",)
RENAL_DIR = HERE.parent / "renal_shared_input"
RENAL_SOURCE_SHA256 = {
    "shared_input_variant.py": "455598a74ab63751b4949be2fd2736bd11688e63d39aa02006e30b86cc19a5f6",
    "renal_protocol.py": "7b24528c92d6d578940d76297cc41689ad58a8566d981b39dc533b31f2a9e85c",
}
EDGE_RUN_SHA256 = {
    "none": "14cd812eea88ae995d39c9bb1d2e9f44783312db03ef1ad4d144aa10e17ed666",
    "admissible": "88ff086bee7e3b739408b2883080839ba3dd33cd399b50262befacc3156545b5",
    "dense": "bf04c405124650b41c4bc1c4c0868e11520c2c6807e3bca52d0c1e2be3f8daf8",
    "reversed": "a0084705ba5829b69a886a36bf8788daa6a7c260535e096ecd79fef2a3938af0",
    "random": "40c44b3ceef121624bb90c310e53dd18bcae518cceb5c67334efb0cad6ebc4da",
    "misspecified-1": "3f8025ace8d7e03bff0b93aa64be086df95cb9e05a73a973d16eab292fdec922",
}


def check_renal_sources():
    for name, expected in RENAL_SOURCE_SHA256.items():
        if sha256(RENAL_DIR / name) != expected:
            raise ValueError(f"frozen renal diagnostic source changed: {name}")


check_renal_sources()
_spec = importlib.util.spec_from_file_location(
    "renal_shared_input_variant", RENAL_DIR / "shared_input_variant.py")
_renal = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_renal)
selected_config = _renal.selected_config
SELECTION_SHA256 = _renal.SELECTION_SHA256


def frozen_edge_run(variant, seed=0):
    if variant not in VARIANTS or seed not in range(4):
        raise ValueError("unregistered variant or seed")
    root = PROJECT / "results/v4"
    # Admissible reuses the selected v4 fits; other arms live under variants/.
    if variant == "admissible":
        return root / "selected/physiograph_gru" / f"seed{seed}/run.json"
    return root / "variants/physiograph_gru" / variant / f"seed{seed}/run.json"


_missing_record_messages = set()
EDGE_CHECKS_SHA256 = "2470e5bc80a85a9a43417e621849d0f7262362b0ec35216a4d013c99edf1a4c9"


def edges_for(variant):
    """Require ordered equality to the bundled frozen edge-check record.

    Full v4 run records are optional inputs at the paths returned by
    frozen_edge_run(). When supplied, their original byte hashes and identity
    are checked too. The random graph is fixed independently of training seed.
    """
    record_path = frozen_edge_run(variant)
    checks_path = HERE / "EDGE_CHECKS.json"
    if sha256(checks_path) != EDGE_CHECKS_SHA256:
        raise ValueError("bundled EDGE_CHECKS.json changed")
    checks = json.loads(checks_path.read_text())["checks"]
    record = next(r for r in checks if r["variant"] == variant and r["seed"] == 0)
    if record["sha256"] != EDGE_RUN_SHA256[variant]:
        raise ValueError(f"frozen edge record changed: {record_path}")
    if record_path.exists():
        if sha256(record_path) != EDGE_RUN_SHA256[variant]:
            raise ValueError(f"frozen edge record changed: {record_path}")
        full_record = json.loads(record_path.read_text())
        if (full_record["status"] != "complete" or full_record["variant"] != variant
                or full_record["seed"] != 0 or full_record["edges"] != record["edges"]):
            raise ValueError(f"wrong frozen edge record identity: {record_path}")
    elif variant not in _missing_record_messages:
        print("Optional full-record check: not distributed: "
              + str(record_path.relative_to(PROJECT))
              + "; checking ordered edges against bundled EDGE_CHECKS.json.", file=sys.stderr)
        _missing_record_messages.add(variant)
    if variant == "misspecified-1":
        edges = tuple(e for e in ADMISSIBLE_EDGES if e != (0, 2)) + ((1, 2),)
    else:
        edges = _resolve_edges("full" if variant == "dense" else variant)
    if [list(e) for e in edges] != record["edges"]:
        raise ValueError(f"edge-list equality failed for {variant}: {record_path}")
    return edges


def check_sources():
    check_renal_sources()
    _renal.check_sources()
    for variant in VARIANTS:
        edges_for(variant)


class SharedInputEdgePhysioGraph(_renal.InputModePhysioGraph):
    """Reuse renal diagnostic's input assembly and rollout, permitting the frozen edge sets."""

    def __init__(self, cfg, input_mode="shared"):
        if input_mode != "shared" or cfg.node_type != "gru" or cfg.n_control:
            raise ValueError("edge diagnostic requires shared input, GRU nodes, no controls")
        # renal diagnostic's constructor rejects edges. This is its same construction order,
        # with that restriction lifted: frozen base first, shared projections last.
        PhysioGraph.__init__(self, cfg)
        self.input_mode = input_mode
        self.node_input_widths = (cfg.n_feat,) * cfg.n_organs
        width = 2 * cfg.n_feat + cfg.n_static
        self.in_proj = nn.ModuleList([
            nn.Linear(width, cfg.d_model) for _ in range(cfg.n_organs)])
        self.step_proj = nn.ModuleList([
            nn.Linear(width, cfg.d_model) for _ in range(cfg.n_organs)])


def build_variant(variant, input_mode="shared", sizes=None):
    sizes = sizes or selected_config()["sizes"]
    cfg = PhysioGraphConfig(organ_dims=(4, 4, 3, 5), n_static=5,
                            n_control=0, d_model=sizes["d_model"],
                            d_state=sizes["d_state"], n_layers=sizes["n_layers"],
                            edges=edges_for(variant), node_type="gru")
    return SharedInputEdgePhysioGraph(cfg, input_mode)


def variant_jobs():
    return [dict(variant=variant, input_mode="shared", seed=seed,
                 registry_id=f"physiograph_gru_shared_edges_{variant}",
                 run_id=f"{variant}/seed{seed}")
            for variant in VARIANTS for seed in range(4)]


def train_variant(variant, seed, output_dir, *, input_mode="shared", npz=None, epochs=35,
                  batch=128, device="cpu", max_stays=None):
    """renal diagnostic train_control protocol; only the model factory/identity metadata differ.

    Same Adam, decay, cosine schedule, clip, min_delta, patience and validation
    selection. A/B are evaluated only after selection. 35 is an epoch cap.
    """
    if not 1 <= epochs <= 35:
        raise ValueError("epoch budget must be between 1 and 35")
    if max_stays is not None and not 4 <= max_stays <= 64:
        raise ValueError("smoke cap must be 4–64 total stays")
    if input_mode not in INPUT_MODES or variant not in VARIANTS or seed not in range(4):
        raise ValueError("unregistered input mode, variant or seed")
    if batch < 1:
        raise ValueError("batch must be positive")
    check_sources()
    selection = selected_config()
    lr, width, sizes = selection["lr"], selection["width"], selection["sizes"]
    output_dir = Path(output_dir).resolve()
    if not output_dir.is_relative_to(PROJECT):
        raise ValueError("output must stay inside the repository")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite a run: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=False)
    seed_all(seed)
    loaders, meta = make_data(npz, 12, 12, batch, seed, max_stays)
    if meta["cohort_sha256"] != "d52d8131323fc7a3838ae4fe523c2edbc02d2daa781de1859e7d184897dfb51f":
        raise ValueError("cohort differs from frozen CinC-2019 data")
    model = build_variant(variant, input_mode, sizes).to(device)
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
            print(f"{variant} {input_mode} seed={seed} epoch={ep+1} val={val} failure={failure}", flush=True)
            sched.step()
            if failure or stale >= 8:
                break
    registry_id = f"physiograph_gru_shared_edges_{variant}"
    result = dict(schema_version=1, diagnostic="shared_input_edges",
                  scope="smoke" if max_stays is not None else "full",
                  model="physiograph_gru", registry_id=registry_id, input_mode=input_mode,
                  seed=seed, lr=lr, width=width, sizes=sizes, variant=variant,
                  edges=[list(e) for e in model.cfg.edges],
                  post_hoc=True, retuned=False,
                  batch=batch, device=str(device), threads=torch.get_num_threads(),
                  cublas_workspace_config=os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
                  random_edge_seed=0 if variant == "random" else None,
                  frozen_edge_record=dict(path=str(frozen_edge_run(variant).relative_to(PROJECT)),
                                          sha256=EDGE_RUN_SHA256[variant], ordered_equality=True),
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
                  extension_sha256={str(p.relative_to(PROJECT)): sha256(p) for p in (
                      Path(__file__), HERE / "renal_protocol.py",
                      RENAL_DIR / "shared_input_variant.py", RENAL_DIR / "renal_protocol.py")},
                  seconds=time.monotonic() - started)
    if result["status"] == "complete":
        model.load_state_dict(best_state)
        checkpoint = output_dir / "checkpoint.pt"
        torch.save(dict(state_dict=best_state, model="physiograph_gru", sizes=sizes,
                        variant=variant, edges=[list(e) for e in model.cfg.edges],
                        registry_id=registry_id, input_mode=input_mode,
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
    ap.add_argument("--variant", choices=VARIANTS)
    ap.add_argument("--input_mode", choices=INPUT_MODES, default="shared")
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
        check_sources()
        selected_config()
        print(json.dumps(variant_jobs(), indent=2))
        return 0
    if args.variant is None:
        ap.error("--variant is required for a fit")
    if args.threads < 1 or args.batch < 1:
        ap.error("--threads and --batch must be positive")
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    torch.set_num_threads(args.threads)
    dest = args.output_dir or PROJECT / "runs/shared_input_edges" / args.variant / f"seed{args.seed}"
    result = train_variant(args.variant, args.seed, dest, input_mode=args.input_mode,
                           npz=args.npz, epochs=args.epochs, batch=args.batch,
                           device=args.device, max_stays=args.max_stays)
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
