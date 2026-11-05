"""Shared, explicit protocol for clinical_protocol; frozen src/ is imported but never edited."""
from __future__ import annotations

# Resolve all public modules and scratch from the release root.
import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[1]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH

import csv
import hashlib
import json
import os
from pathlib import Path
import random
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PROJECT = RELEASE_ROOT
SCRATCH = RELEASE_SCRATCH
SCRATCH.mkdir(parents=True, exist_ok=True)
os.environ["TMPDIR"] = str(SCRATCH)
import tempfile
tempfile.tempdir = str(SCRATCH)
sys.path.insert(0, str(PROJECT / "src"))

import numpy as np
import torch
from torch.utils.data import DataLoader
from physiograph_data_loader import ForecastWindows
from physiograph_training_runner import build_any
from organ_graph_ssm_model import ADMISSIBLE_EDGES, _resolve_edges, build_model

MODELS = ("gru", "gru_med", "gru_large", "grud", "ncde", "odernn", "graphgru",
          "physiograph", "physiograph_gru")
ALL_MODELS = ("persistence",) + MODELS
LRS = (5e-4, 1e-3, 2e-3)
WIDTHS = ("small", "large")
DESIGNS = ((12, 6), (12, 12), (12, 24), (24, 12), (24, 24))
VARIANTS = ("none", "admissible", "dense", "reversed", "random", "misspecified-1")
SIZES_FROZEN = dict(d_hidden=128, d_model=96, d_state=48, n_layers=2)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def finite_float(value):
    value = float(value)
    return value if np.isfinite(value) else None


def runtime():
    import scipy
    import clinical_timeseries_baselines as cb
    return dict(python=sys.version, numpy=np.__version__, torch=torch.__version__,
                scipy=scipy.__version__, torchcde=cb.HAVE_CDE, torchdiffeq=cb.HAVE_ODE)


def seed_all(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True


def config_id(lr, width):
    return f"lr{lr:g}_{width}"


def sizes_for(name, width):
    """Two distinct capacities for each named architecture; never ignored aliases."""
    if width not in WIDTHS:
        raise ValueError(width)
    scale = 1 if width == "small" else 2
    base_hidden = {"gru_med": 320, "gru_large": 512}.get(name, 128)
    return dict(d_hidden=base_hidden * scale, d_model=64 if scale == 1 else 96,
                d_state=48, n_layers=2)


def edges_for(variant):
    if variant == "misspecified-1":
        # Replace exactly one edge, holding edge count fixed. No outcome-based choice.
        return tuple(e for e in ADMISSIBLE_EDGES if e != (0, 2)) + ((1, 2),)
    if variant not in VARIANTS:
        raise ValueError(variant)
    return _resolve_edges("full" if variant == "dense" else variant)


def build(name, sizes=None, variant="admissible"):
    sizes = dict(SIZES_FROZEN if sizes is None else sizes)
    if name in ("physiograph", "physiograph_gru"):
        return build_model("cinc", d_model=sizes["d_model"], d_state=sizes["d_state"],
                           n_layers=sizes["n_layers"], edges=edges_for(variant),
                           node_type="gru" if name.endswith("_gru") else "ssm")
    # The old build_any hard-codes gru_med/large. Route capacity aliases to GRU
    # with the explicit selected width, so the six grid cells really differ.
    if name in ("gru_med", "gru_large"):
        if sizes == SIZES_FROZEN:
            return build_any(name, 5, **sizes)
        name = "gru"
    return build_any(name, 5, **sizes)


class StayWindows(ForecastWindows):
    def __init__(self, arrays, split, C, K, min_length=0, limit=None):
        super().__init__(*arrays[:6], mean=arrays[6], std=arrays[7], C=C, K=K)
        length = arrays[4]
        self.idx = np.asarray(split, dtype=np.int64)
        self.idx = self.idx[length[self.idx] >= max(C + K, min_length)]
        if limit is not None:
            # Same stays for every model and seed, independent of training RNG.
            self.idx = np.random.default_rng(0).permutation(self.idx)[:limit]

    def __getitem__(self, i):
        item = super().__getitem__(i)
        item["stay_index"] = int(self.idx[i])
        return item


def make_data(npz=None, C=12, K=12, batch=128, seed=0, max_stays=None,
              min_length=0):
    """One stay/window. max_stays caps the TOTAL across all four splits."""
    npz = Path(npz or PROJECT / "data/cinc2019_cohort.npz")
    with np.load(npz, allow_pickle=True) as archive:
        d = {k: archive[k] for k in archive.files}
    if max_stays is not None and max_stays < 4:
        raise ValueError("max_stays must allow at least one stay per split")
    limits = [None] * 4 if max_stays is None else [max_stays // 4] * 4
    datasets = []
    split_ids = [d["train_idx"], d["val_idx"], d["test_idx"], np.arange(len(d["B_length"]))]
    for i, (cohort, ids) in enumerate(zip(("A", "A", "A", "B"), split_ids)):
        a = tuple(d[f"{cohort}_{key}"] for key in ("values", "mask", "static", "sepsis", "length"))
        a += (np.full(len(a[0]), cohort == "B", dtype=np.int32), d["norm_mean"], d["norm_std"])
        datasets.append(StayWindows(a, ids, C, K, min_length, limits[i]))
    if any(len(ds) == 0 for ds in datasets):
        raise ValueError("empty eligible split")
    loaders = [DataLoader(ds, batch_size=batch, shuffle=i == 0, num_workers=0,
                          generator=torch.Generator().manual_seed(seed))
               for i, ds in enumerate(datasets)]
    ids = {label: ds.idx.tolist() for label, ds in zip(("train", "val", "A", "B"), datasets)}
    meta = dict(C=C, K=K, organ_slices=d["organ_slices"].tolist(),
                organ_names=d["organ_names"].tolist(), features=d["features"].tolist(),
                split_stay_indices=ids, counts={k: len(v) for k, v in ids.items()},
                cohort_sha256=sha256(npz), min_length=min_length, max_stays=max_stays)
    return loaders, meta


def to_device(batch, device):
    return {k: v.to(device) if torch.is_tensor(v) else v for k, v in batch.items()}


def persistence(batch, K):
    last = torch.zeros_like(batch["values"][:, 0])
    for t in range(batch["values"].shape[1]):
        last = torch.where(batch["mask"][:, t] > 0, batch["values"][:, t], last)
    return last[:, None].expand(-1, K, -1)


@torch.no_grad()
def collect_errors(model, loader, K=12, device="cpu", organ_slices=None):
    """Float32 prediction/error arithmetic as frozen code; float64 summation in reports."""
    if model is not None:
        model.eval()
    out = {k: [] for k in ("stay_index", "sse", "count", "sae", "organ_sse", "organ_count", "nonfinite")}
    for batch in loader:
        b = to_device(batch, device)
        pred = persistence(b, K) if model is None else model(b, horizon=K)
        m, target = b["target_mask"], b["target"]
        sq = (pred - target).square() * m
        ae = (pred - target).abs() * m
        out["stay_index"].append(batch["stay_index"].numpy())
        for k, v in (("sse", sq.sum((1, 2))), ("count", m.sum((1, 2))), ("sae", ae.sum((1, 2))),
                     ("nonfinite", (~torch.isfinite(pred)).sum((1, 2)))):
            out[k].append(v.cpu().numpy())
        slices = organ_slices if organ_slices is not None else [(0, target.shape[-1])]
        out["organ_sse"].append(torch.stack([sq[:, :, a:z].sum((1, 2)) for a, z in slices], 1).cpu().numpy())
        out["organ_count"].append(torch.stack([m[:, :, a:z].sum((1, 2)) for a, z in slices], 1).cpu().numpy())
    return {k: np.concatenate(v) for k, v in out.items()}


def metrics(errors, organ_names):
    count = errors["count"].sum(dtype=np.float64)
    out = dict(n_stays=len(errors["count"]), observed_entries=int(count),
               zero_target_stays=int((errors["count"] == 0).sum()),
               nonfinite_predictions=int(errors["nonfinite"].sum()),
               pooled_masked_RMSE=finite_float(np.sqrt(errors["sse"].sum(dtype=np.float64) / count)) if count else None,
               pooled_masked_MAE=finite_float(errors["sae"].sum(dtype=np.float64) / count) if count else None)
    out["organs"] = {}
    for i, name in enumerate(organ_names):
        n = errors["organ_count"][:, i].sum(dtype=np.float64)
        out["organs"][name] = dict(observed_entries=int(n), RMSE=finite_float(
            np.sqrt(errors["organ_sse"][:, i].sum(dtype=np.float64) / n)) if n else None)
    return out


def save_errors(path, errors):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **errors)


def add_data_args(ap):
    ap.add_argument("--npz", type=Path, default=PROJECT / "data/cinc2019_cohort.npz")
    ap.add_argument("--batch", type=int, default=128)
    ap.add_argument("--max-stays", type=int, help="smoke cap across train/val/A/B combined")
    ap.add_argument("--threads", type=int, default=2)


def train_run(name, lr, width, seed, output_dir, *, npz=None, C=12, K=12,
              epochs=35, batch=128, device="cpu", max_stays=None,
              variant="admissible", min_length=0, curve_path=None, evaluate_tests=True):
    """One independent fit. Tests are evaluated only after validation selects state."""
    if not 1 <= epochs <= 35:
        raise ValueError("epoch budget must be between 1 and 35")
    if max_stays is not None and max_stays > 64:
        raise ValueError("smoke cap must be <=64 stays; omit the cap for a full host run")
    output_dir = Path(output_dir)
    if (output_dir / "run.json").exists() or (output_dir / "checkpoint.pt").exists():
        raise FileExistsError(f"refusing to overwrite a completed/partial run: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    seed_all(seed)
    loaders, meta = make_data(npz, C, K, batch, seed, max_stays, min_length)
    sizes = sizes_for(name, width)
    model = build(name, sizes, variant).to(device)
    # ODE fallback changes the architecture: fail explicitly rather than switch silently.
    import clinical_timeseries_baselines as cb
    if name == "odernn" and not cb.HAVE_ODE:
        raise RuntimeError("torchdiffeq required for registered ODE-RNN")
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, epochs)
    curve_path = Path(curve_path or output_dir / "curve.csv")
    curve_path.parent.mkdir(parents=True, exist_ok=True)
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
                pred = model(b, horizon=K)
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
            val_errors = collect_errors(model, loaders[1], K, device, meta["organ_slices"])
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
            print(f"{name} {width} lr={lr:g} seed={seed} epoch={ep+1} val={val} failure={failure}", flush=True)
            sched.step()
            if failure or stale >= 8:
                break
    result = dict(schema_version=4, scope="smoke" if max_stays is not None else "full",
                  model=name, seed=seed, lr=lr, width=width,
                  sizes=sizes, variant=variant, edges=list(edges_for(variant)) if name.startswith("physiograph") else None,
                  C=C, K=K, epochs_budget=epochs, epochs_completed=ep + 1,
                  best_epoch=best_epoch, validation_RMSE=finite_float(best_val),
                  status="failed" if failure or best_state is None else "complete", failure=failure,
                  patience=8, min_delta=1e-4, optimizer="Adam", weight_decay=1e-5,
                  scheduler="CosineAnnealingLR", gradient_clip=1.0, n_params=sum(p.numel() for p in model.parameters()),
                  curve=str(curve_path.resolve()), data=meta, runtime=runtime(),
                  source_sha256={p.name: sha256(p) for p in sorted((PROJECT / "src").glob("*.py"))},
                  seconds=time.monotonic() - started)
    if result["status"] == "complete":
        model.load_state_dict(best_state)
        checkpoint = output_dir / "checkpoint.pt"
        torch.save(dict(state_dict=best_state, model=name, sizes=sizes, variant=variant,
                        seed=seed, C=C, K=K, cohort_sha256=meta["cohort_sha256"]), checkpoint)
        result["checkpoint"] = str(checkpoint.resolve())
        result["checkpoint_sha256"] = sha256(checkpoint)
        for split, loader in zip(("A", "B"), loaders[2:] if evaluate_tests else ()):
            errors = collect_errors(model, loader, K, device, meta["organ_slices"])
            save_errors(output_dir / f"errors_{split}.npz", errors)
            result[split] = metrics(errors, meta["organ_names"])
    write_json(output_dir / "run.json", result)
    return result
