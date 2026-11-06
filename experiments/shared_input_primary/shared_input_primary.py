#!/usr/bin/env python3
"""D-014 / shared-input experiment: shared-input retuning, edge/capacity arms, and budget controls.

One grid cell per --stage grid command; the sixth recorded cell writes
selection_shared.json. Arms and shared-input budget runs require that selection.
Only --max-stays 4..64 permits shortened smoke epoch caps.
"""
from __future__ import annotations

import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[2]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH

import argparse
import csv
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import time
import traceback

sys.dont_write_bytecode = True
# Load the local, definition-identical helper BEFORE either frozen extension.
from renal_protocol import (HERE, PROJECT, collect_errors, finite_float, make_data,
                            metrics, runtime, save_errors, seed_all, sha256,
                            to_device, write_json)
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from organ_graph_ssm_model import ADMISSIBLE_EDGES, OrganGraphCoupling
from physiograph_training_runner import build_any

TASK = "shared-input experiment-shared-input-primary-runner-build"
LRS = (0.0005, 0.001, 0.002)
WIDTHS = ("small", "large")
ARMS = ("none", "none_norm", "none_pmatch", "admissible", "dense", "reversed",
        "random_s0", "random_s1", "random_s2", "misspecified-1")
BUDGET_MODELS = ("none", "admissible", "grud")
COHORT_SHA256 = "d52d8131323fc7a3838ae4fe523c2edbc02d2daa781de1859e7d184897dfb51f"
EDGE_DIR = PROJECT / "diagnostics/shared_input_edges"
FROZEN_INPUTS = {
    PROJECT / 'diagnostics/shared_input_edges/shared_input_edge_variant.py': '55f68ff935d6ad643e8141dbd57a47d9f54ad9f8359cffa775ae8199e024f56c',
    PROJECT / 'diagnostics/shared_input_edges/renal_protocol.py': 'c808fd4947056ef5188297dd51e43b691b43986de7241bfdd6cb90d424bfdef1',
    PROJECT / 'diagnostics/shared_input_edges/EDGE_CHECKS.json': '2470e5bc80a85a9a43417e621849d0f7262362b0ec35216a4d013c99edf1a4c9',
    PROJECT / 'src/clinical_timeseries_baselines.py': 'b913bdc177e4c7c47d5a647aa06e1e2e21d4e02c4e1fb5fe310e0e0f39218de2',
}
# Load the distributed diagnostic with its own helper, then restore this runner's helper.
# This prevents a cached helper from selecting the wrong experiment directory.
_local_helper = sys.modules['renal_protocol']
_helper_spec = importlib.util.spec_from_file_location('renal_protocol', EDGE_DIR / 'renal_protocol.py')
_edge_helper = importlib.util.module_from_spec(_helper_spec)
sys.modules['renal_protocol'] = _edge_helper
_helper_spec.loader.exec_module(_edge_helper)
try:
    _spec = importlib.util.spec_from_file_location('released_shared_edges', EDGE_DIR / 'shared_input_edge_variant.py')
    _shared_edges = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_shared_edges)
finally:
    sys.modules['renal_protocol'] = _local_helper
V4_SELECTION = PROJECT / 'results/v4/selection.json'


def check_sources():
    for path, digest in FROZEN_INPUTS.items():
        if sha256(path) != digest:
            raise ValueError(f'distributed input changed: {path}')
    _shared_edges.check_sources()
    if sha256(V4_SELECTION) != _shared_edges.SELECTION_SHA256:
        raise ValueError('frozen v4 selection changed')


def sizes_for(width):
    if width not in WIDTHS:
        raise ValueError(width)
    return dict(d_hidden=128 if width == "small" else 256,
                d_model=64 if width == "small" else 96, d_state=48, n_layers=2)


def config_id(lr, width):
    return f"lr{lr:g}_{width}"


def grid_jobs():
    return [dict(lr=lr, width=w, cfg=config_id(lr, w), seed=0, sizes=sizes_for(w))
            for lr in LRS for w in WIDTHS]


def edges_for(arm):
    if arm not in ARMS:
        raise ValueError(arm)
    if arm in ("none_norm", "none_pmatch"):
        return _shared_edges.edges_for("none")
    if arm.startswith("random_s"):
        draw_seed = int(arm[-1])
        dense = _shared_edges.edges_for("dense")
        indices = np.random.default_rng(draw_seed).choice(len(dense), len(ADMISSIBLE_EDGES), replace=False)
        edges = tuple(dense[i] for i in sorted(indices))
        if draw_seed == 0 and edges != _shared_edges.edges_for("random"):
            raise ValueError("random_s0 differs from frozen v4 random")
        return edges
    return _shared_edges.edges_for(arm)


def edge_evidence(arm):
    edges = edges_for(arm)
    admissible = set(_shared_edges.edges_for("admissible"))
    overlap = len(set(edges) & admissible)
    union = len(set(edges) | admissible)
    return dict(edges=[list(e) for e in edges],
                random_edge_seed=int(arm[-1]) if arm.startswith("random_s") else None,
                admissible_intersection=overlap, admissible_union=union,
                jaccard_with_admissible=overlap / union)


class NormalisationRetainingCoupling(OrganGraphCoupling):
    """Simulator _MatchedCoupling's empty branch, preserving original LayerNorm."""

    def __init__(self, original):
        nn.Module.__init__(self)
        self.cfg = original.cfg
        if self.cfg.edges:
            raise ValueError("none_norm requires an empty edge set")
        self.msg = nn.ModuleList([])
        self.gate = nn.ModuleList([])
        self.norm = original.norm
        self.register_buffer("src", torch.tensor([], dtype=torch.long))
        self.register_buffer("dst", torch.tensor([], dtype=torch.long))

    def forward(self, hidden):
        # Exactly sim_grid_runner._MatchedCoupling's no-edge operation:
        # norm(hidden + zero_message_sum) == norm(hidden).
        return self.norm(hidden), hidden.new_zeros(hidden.shape[0], 0)


class WidenedProjection(nn.Module):
    """An active nonlinear widening of a shared-input projection; no dummy weights.

    base(x) + down(GELU(up(x) + partial_bias)). A partial bias stores exactly
    n_bias live entries; the remaining hidden units have a fixed zero bias.
    """

    def __init__(self, base, hidden, n_bias):
        super().__init__()
        self.base = base
        self.in_features, self.out_features = base.in_features, base.out_features
        self.up = nn.Linear(self.in_features, hidden, bias=False)
        self.hidden_bias = nn.Parameter(torch.zeros(n_bias))
        self.down = nn.Linear(hidden, self.out_features, bias=False)

    def forward(self, x):
        z = self.up(x)
        bias = F.pad(self.hidden_bias, (0, z.shape[-1] - self.hidden_bias.numel()))
        return self.base(x) + self.down(F.gelu(z + bias))


def widen_projections(model):
    """Match admissible's exact count at fixed recurrent width/layers.

    Each edge/layer contributes d*d + 3*d + 1 message/gate parameters.
    There are eight projections (four context + four feedback), with p=37
    inputs. H new hidden units add H*(p+d) weights and b live biases.
    Choose H=ceil(delta/(p+d+1)), b=delta-H*(p+d), then distribute H and b
    separately by quotient/remainder across those eight projections.
    """
    cfg = model.cfg
    d, p = cfg.d_model, 2 * cfg.n_feat + cfg.n_static
    delta = len(ADMISSIBLE_EDGES) * cfg.n_layers * (d * d + 3 * d + 1)
    hidden_total = math.ceil(delta / (p + d + 1))
    bias_total = delta - hidden_total * (p + d)
    n = 2 * cfg.n_organs
    hidden = [hidden_total // n + (i < hidden_total % n) for i in range(n)]
    biases = [bias_total // n + (i < bias_total % n) for i in range(n)]
    if not all(0 <= b <= h for b, h in zip(biases, hidden)):
        raise ValueError("exact projection widening is unavailable")
    base_count = model.n_params()
    for i, (h, b) in enumerate(zip(hidden, biases)):
        group = model.in_proj if i < cfg.n_organs else model.step_proj
        j = i % cfg.n_organs
        group[j] = WidenedProjection(group[j], h, b)
    achieved = model.n_params()
    if achieved != base_count + delta:
        raise AssertionError("projection widening parameter mismatch")
    return dict(rule="H=ceil(delta/(p+d+1)); b=delta-H*(p+d); quotient/remainder over context then feedback projections",
                projection_input=p, recurrent_width=d, added_parameters=delta,
                total_hidden=hidden_total, total_hidden_biases=bias_total,
                hidden_widths=hidden, hidden_bias_counts=biases,
                base_n_params=base_count, admissible_n_params=base_count + delta,
                achieved_n_params=achieved, exact=True)


def build_arm(arm, sizes):
    # The frozen factory preserves shared-edge diagnostic's module construction order and rollout.
    base_arm = "none" if arm in ("none_norm", "none_pmatch") else arm
    if base_arm.startswith("random_s"):
        cfg = _shared_edges.PhysioGraphConfig(organ_dims=(4, 4, 3, 5), n_static=5,
                n_control=0, d_model=sizes["d_model"], d_state=sizes["d_state"],
                n_layers=sizes["n_layers"], edges=edges_for(arm), node_type="gru")
        model = _shared_edges.SharedInputEdgePhysioGraph(cfg)
    else:
        model = _shared_edges.build_variant(base_arm, sizes=sizes)
    model.pmatch = None
    if arm == "none_norm":
        model.couplers = nn.ModuleList([NormalisationRetainingCoupling(c) for c in model.couplers])
    if arm == "none_pmatch":
        model.pmatch = widen_projections(model)
    return model


def owned_path(path):
    path = Path(path)
    resolved = path.resolve()
    if not (resolved.is_relative_to(HERE) or resolved.is_relative_to(RELEASE_SCRATCH)) or resolved == HERE:
        raise ValueError("output must stay inside shared-input experiment workspace, below its root")
    return resolved


def fresh_path(path):
    # lexists semantics also refuse dangling destination symlinks.
    path = Path(path)
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"refusing an existing destination: {path}")
    return owned_path(path)


def frozen_selected(model):
    check_sources()
    s = json.loads(V4_SELECTION.read_text())["models"][model]
    if s["status"] != "selected":
        raise ValueError(f"v4 has no selected {model} config")
    return {k: s[k] for k in ("status", "lr", "width", "cfg", "sizes", "validation_RMSE", "grid_run", "grid_run_sha256")}


def select_grid(root):
    """Require all six records; select exclusively by A-validation and cfg ID."""
    root = owned_path(root)
    inventory, candidates, protocols = [], [], []
    for job in grid_jobs():
        path = root / "grid" / job["cfg"] / "seed0/run.json"
        if not path.is_file():
            raise ValueError(f"grid incomplete; cannot select: {path}")
        r = json.loads(path.read_text())
        identity = (r["task"], r["stage"], r["arm"], r["seed"], r["lr"], r["width"], r["sizes"])
        if identity != (TASK, "grid", "none", 0, job["lr"], job["width"], job["sizes"]):
            raise ValueError(f"wrong grid identity: {path}")
        protocols.append((r["scope"], r["epochs_budget"], r["batch"],
                          r["data"]["cohort_sha256"], r["data"]["max_stays"]))
        inventory.append(dict(path=str(path), sha256=sha256(path), record=r))
        val = r.get("validation_RMSE")
        if r["status"] == "complete" and val is not None and math.isfinite(val):
            candidates.append((val, job["cfg"], job, path))
    if len(set(protocols)) != 1:
        raise ValueError("grid cells have inconsistent scopes/budgets/batches/cohorts")
    scope, epochs, batch, cohort, max_stays = protocols[0]
    if cohort != COHORT_SHA256 or (scope == "full" and epochs != 35):
        raise ValueError("grid does not follow the frozen protocol")
    if candidates:
        val, cfg, job, source = min(candidates, key=lambda c: (c[0], c[1]))
        chosen = dict(status="selected", **job, validation_RMSE=val,
                      grid_run=str(source), grid_run_sha256=sha256(source))
    else:
        chosen = dict(status="blocked", reason="all six configurations failed")
    return dict(schema_version=1, task=TASK, decision_id="D-014", scope=scope,
                criterion="minimum A-validation pooled masked RMSE; cfg lexical tie break",
                grid_seed=0, selected_seeds=[0, 1, 2, 3], epochs_budget=epochs,
                batch=batch, cohort_sha256=cohort, max_stays=max_stays,
                selected=chosen, grid=inventory,
                width_definition={w: sizes_for(w) for w in WIDTHS})


def maybe_write_selection(root):
    if not all((root / "grid" / j["cfg"] / "seed0/run.json").is_file() for j in grid_jobs()):
        return None
    path = fresh_path(root / "selection_shared.json")
    result = select_grid(root)
    with path.open("x") as f:
        f.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(f"GRID selection: {path} {result['selected']}", flush=True)
    return result


def read_shared_selection(path, *, max_stays, batch):
    path = Path(path)
    # Recompute validation-only choice and verify all six immutable run hashes.
    s = json.loads(path.read_text())
    expected = select_grid(path.parent)
    if s != expected:
        raise ValueError("shared selection or its grid records changed")
    if s["selected"]["status"] != "selected":
        raise ValueError("shared-input grid has no selected configuration")
    if s["max_stays"] != max_stays or s["batch"] != batch:
        raise ValueError("selection scope/stay cap/batch differs from requested run")
    return s["selected"], dict(path=str(path.resolve()), sha256=sha256(path), scope=s["scope"])


def train_run(stage, arm, seed, output_dir, *, lr, width, epochs, batch=128,
              device="cpu", max_stays=None, npz=None, selection=None):
    """The shared-edge diagnostic training rule, with longer cosine periods for E4 budgets."""
    if stage not in ("grid", "arms", "budget") or arm not in ARMS + ("grud",):
        raise ValueError("unregistered stage/arm")
    if seed not in range(4) or lr not in LRS or width not in WIDTHS or batch < 1:
        raise ValueError("invalid seed/configuration/batch")
    if max_stays is not None and not 4 <= max_stays <= 64:
        raise ValueError("smoke cap must be 4–64 total stays")
    if max_stays is None:
        if epochs not in ((70, 105) if stage == "budget" else (35,)):
            raise ValueError("full runs require 35 epochs, or budget 70/105")
    elif not 1 <= epochs <= (105 if stage == "budget" else 35):
        raise ValueError("invalid smoke epoch cap")
    if stage == "grid" and (arm != "none" or seed != 0):
        raise ValueError("grid requires none at seed 0")
    if stage == "arms" and arm not in ARMS:
        raise ValueError("invalid edge/capacity arm")
    if stage == "budget" and arm not in BUDGET_MODELS:
        raise ValueError("budget requires none, admissible, or grud")
    check_sources()
    output_dir = fresh_path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    sizes = sizes_for(width)
    seed_all(seed)
    curve_path, curve = output_dir / "curve.csv", []
    result = dict(schema_version=1, task=TASK, decision_id="D-014", stage=stage,
                  scope="smoke" if max_stays is not None else "full",
                  model="grud" if arm == "grud" else "physiograph_gru_shared",
                  arm=arm, variant=arm, seed=seed, lr=lr, width=width, sizes=sizes,
                  input_mode="shared", edges=[] if arm == "grud" else edge_evidence(arm)["edges"],
                  C=12, K=12, epochs_budget=epochs, epochs_completed=0, best_epoch=None,
                  validation_RMSE=None, A_validation=None, A=None, B=None,
                  status="failed", failure=None, n_params=None,
                  patience=8, min_delta=1e-4, optimizer="Adam", weight_decay=1e-5,
                  scheduler="CosineAnnealingLR", scheduler_T_max=epochs, gradient_clip=1.0,
                  selection_criterion="A-validation pooled masked RMSE only",
                  selection=selection, retuned=arm != "grud", post_hoc=stage == "arms",
                  batch=batch, device=str(device), threads=torch.get_num_threads(),
                  cublas_workspace_config=os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
                  curve=str(curve_path), training_curve=curve,
                  data=dict(cohort_sha256=COHORT_SHA256, max_stays=max_stays),
                  source_sha256={p.name: sha256(p) for p in sorted((PROJECT / "src").glob("*.py"))},
                  extension_sha256={str(p.relative_to(PROJECT)): sha256(p) for p in
                      (Path(__file__), HERE / "renal_protocol.py", EDGE_DIR / "shared_input_edge_variant.py",
                       _shared_edges.RENAL_DIR / "shared_input_variant.py")})
    started = time.monotonic()
    best_val, best_state, stale = float("inf"), None, 0
    try:
        loaders, meta = make_data(npz, 12, 12, batch, seed, max_stays)
        result["data"] = meta
        if meta["cohort_sha256"] != COHORT_SHA256:
            raise ValueError("cohort differs from frozen CinC-2019 data")
        model = (build_any("grud", n_static=5, **sizes) if arm == "grud"
                 else build_arm(arm, sizes)).to(device)
        result["n_params"] = sum(p.numel() for p in model.parameters())
        if arm != "grud":
            result.update(edge_evidence(arm), pmatch=model.pmatch,
                          node_input_widths=list(model.node_input_widths),
                          projection_input_widths=[p.in_features for p in model.in_proj],
                          coupling_normalisation="retained with zero message sum" if arm == "none_norm"
                              else "frozen OrganGraphCoupling (empty edges bypass LayerNorm)")
            print("ARM evidence:", json.dumps({k: result[k] for k in
                  ("arm", "edges", "random_edge_seed", "jaccard_with_admissible", "n_params", "pmatch")}), flush=True)
        opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)
        sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, epochs)
        with curve_path.open("x", newline="") as f:
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
                        result["failure"] = f"nonfinite training loss at epoch {ep + 1}"
                        break
                    loss.backward()
                    gn = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                    if not torch.isfinite(gn):
                        result["failure"] = f"nonfinite gradient at epoch {ep + 1}"
                        break
                    grad_max = max(grad_max, float(gn))
                    opt.step()
                    tot_sse += float(sse.detach())
                    tot_n += float(n)
                val_errors = collect_errors(model, loaders[1], 12, device, meta["organ_slices"])
                val = metrics(val_errors, meta["organ_names"])["pooled_masked_RMSE"]
                if val is None:
                    result["failure"] = result["failure"] or f"nonfinite validation at epoch {ep + 1}"
                improved = result["failure"] is None and val < best_val - 1e-4
                if improved:
                    best_val, result["best_epoch"], stale = val, ep + 1, 0
                    best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
                else:
                    stale += 1
                row = dict(epoch=ep + 1, train_masked_mse=tot_sse / tot_n if tot_n else None,
                           val_RMSE=val, lr=used_lr, gradient_norm_max=grad_max,
                           improved=improved, seconds=time.monotonic() - started)
                curve.append(row)
                writer.writerow(row)
                f.flush()
                result["epochs_completed"] = ep + 1
                print(f"{stage} {arm} {width} lr={lr:g} seed={seed} epoch={ep+1} val={val} failure={result['failure']}", flush=True)
                sched.step()
                if result["failure"] or stale >= 8:
                    break
        result["validation_RMSE"] = finite_float(best_val)
        if result["failure"] is None and best_state is not None:
            result["status"] = "complete"
            model.load_state_dict(best_state)
            checkpoint = output_dir / "checkpoint.pt"
            torch.save(dict(state_dict=best_state, model=result["model"], arm=arm,
                            sizes=sizes, seed=seed, lr=lr, width=width, edges=result["edges"],
                            C=12, K=12, cohort_sha256=meta["cohort_sha256"]), checkpoint)
            result.update(checkpoint=str(checkpoint), checkpoint_sha256=sha256(checkpoint))
            # Holdouts never enter checkpoint or configuration selection.
            for split, loader in zip(("A_validation", "A", "B"), loaders[1:]):
                errors = collect_errors(model, loader, 12, device, meta["organ_slices"])
                save_errors(output_dir / f"errors_{split}.npz", errors)
                result[split] = metrics(errors, meta["organ_names"])
        elif result["failure"] is None:
            result["failure"] = "no finite validation-selected checkpoint"
    except Exception as e:
        traceback.print_exc()
        result.update(status="failed", failure=f"{type(e).__name__}: {e}")
    result.update(seconds=time.monotonic() - started, runtime=runtime())
    write_json(output_dir / "run.json", result)
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage", choices=("grid", "arms", "budget"), required=True)
    ap.add_argument("--arm", choices=ARMS)
    ap.add_argument("--model", choices=BUDGET_MODELS, help="budget model: none/admissible are shared-input")
    ap.add_argument("--lr", type=float, choices=LRS)
    ap.add_argument("--width", choices=WIDTHS)
    ap.add_argument("--seed", type=int, choices=range(4), default=0)
    ap.add_argument("--epochs", type=int, default=35)
    ap.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--batch", type=int, default=128)
    ap.add_argument("--max-stays", type=int)
    ap.add_argument("--npz", type=Path, default=PROJECT / "data/cinc2019_cohort.npz")
    ap.add_argument("--output-root", type=Path, default=HERE / "artifacts/host")
    ap.add_argument("--output-dir", type=Path)
    ap.add_argument("--selection", type=Path)
    args = ap.parse_args(argv)
    if args.threads < 1 or args.batch < 1:
        ap.error("--threads and --batch must be positive")
    root = owned_path(args.output_root)
    selection_path = args.selection or root / "selection_shared.json"
    if args.stage == "grid":
        if args.lr is None or args.width is None or args.seed != 0 or args.arm or args.model:
            ap.error("grid requires --lr, --width, seed 0, and no --arm/--model")
        # Never append grid cells beneath a completed selection.
        fresh_path(root / "selection_shared.json")
        arm, lr, width, selection = "none", args.lr, args.width, None
        dest = root / "grid" / config_id(lr, width) / "seed0"
        if args.output_dir and Path(args.output_dir).resolve() != dest.resolve():
            ap.error("grid --output-dir must equal the canonical output-root/grid/CFG/seed0")
    else:
        if args.lr is not None or args.width is not None:
            ap.error("arms/budget read their selected configuration; no --lr/--width")
        if args.stage == "arms":
            if args.arm is None or args.model is not None:
                ap.error("arms requires --arm and no --model")
            arm = args.arm
        else:
            if args.model is None or args.arm is not None:
                ap.error("budget requires --model and no --arm")
            arm = args.model
        if arm == "grud":
            chosen = frozen_selected("grud")
            selection = dict(path=str(V4_SELECTION), sha256=_shared_edges.SELECTION_SHA256, selected=chosen)
        else:
            chosen, selection = read_shared_selection(selection_path, max_stays=args.max_stays, batch=args.batch)
        lr, width = chosen["lr"], chosen["width"]
        dest = (root / "arms" / arm / f"seed{args.seed}" if args.stage == "arms" else
                root / "budget" / arm / f"epochs{args.epochs}" / f"seed{args.seed}")
    dest = args.output_dir or dest
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    torch.set_num_threads(args.threads)
    result = train_run(args.stage, arm, args.seed, dest, lr=lr, width=width,
                       epochs=args.epochs, batch=args.batch, device=args.device,
                       max_stays=args.max_stays, npz=args.npz, selection=selection)
    if args.stage == "grid":
        maybe_write_selection(root)
        # A failed cell remains in the six-cell inventory, as in the v4 grid.
        return 0
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
