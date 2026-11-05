"""Frozen clinical data/evaluation helpers for the renal diagnostic.

Numerical definitions match tools/v4_protocol.py. Paths and scratch use
the common release bootstrap; original fingerprints remain in the inventory.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import random
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from release_paths import ROOT as PROJECT, SCRATCH

os.environ["TEMP"] = str(SCRATCH)
os.environ["TMP"] = str(SCRATCH)
import tempfile
tempfile.tempdir = str(SCRATCH)
import numpy as np
import torch
from torch.utils.data import DataLoader
from physiograph_data_loader import ForecastWindows

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
