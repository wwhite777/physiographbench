"""physiograph_data_loader — forecasting windows + masked metrics for the CinC cohort.

Turns the organ-grouped cohort npz into a causal forecasting task: given the first
``C`` hours of a stay, predict the next ``K`` hours of all 16 organ variables.
Values are normalised with A-train statistics and re-masked so missing entries are
zero. Hospital A provides train/val/internal-test; hospital B is the external test
(the cross-cohort generalisation split). All metrics are computed only over
observed target entries (mask==1), as is standard for irregularly sampled ICU data.
"""
from __future__ import annotations

# Resolve all public modules and scratch from the release root.
import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[1]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset


class ForecastWindows(Dataset):
    def __init__(self, values, mask, static, sepsis, length, hospital,
                 mean, std, C=12, K=12):
        keep = length >= (C + K)
        self.idx = np.where(keep)[0]
        self.v = values; self.m = mask; self.s = static
        self.sep = sepsis; self.hosp = hospital
        self.C, self.K = C, K
        self.mean = mean.astype(np.float32); self.std = std.astype(np.float32)

    def __len__(self):
        return len(self.idx)

    def _norm(self, v, m):
        return ((v - self.mean) / self.std) * m

    def __getitem__(self, i):
        j = self.idx[i]; C, K = self.C, self.K
        v = self.v[j]; m = self.m[j]
        ctx_v = self._norm(v[:C], m[:C]); ctx_m = m[:C]
        tgt_v = self._norm(v[C:C + K], m[C:C + K]); tgt_m = m[C:C + K]
        return {
            "values": torch.from_numpy(ctx_v), "mask": torch.from_numpy(ctx_m),
            "static": torch.from_numpy(self.s[j]),
            "target": torch.from_numpy(tgt_v), "target_mask": torch.from_numpy(tgt_m),
            "hospital": int(self.hosp[j]),
            "sepsis": float(self.sep[j, :C + K].max() > 0),
        }


def make_loaders(npz_path, C=12, K=12, batch_size=128, num_workers=4, train_frac=1.0):
    d = np.load(npz_path, allow_pickle=True)
    mean, std = d["norm_mean"], d["norm_std"]
    tr, va, te = d["train_idx"], d["val_idx"], d["test_idx"]
    if train_frac < 1.0:                              # low-data sweep (H2): subsample A-train
        rng = np.random.default_rng(0)
        tr = rng.permutation(tr)[:max(8, int(len(tr) * train_frac))]

    def sub(split_idx):
        return (d["A_values"][split_idx], d["A_mask"][split_idx], d["A_static"][split_idx],
                d["A_sepsis"][split_idx], d["A_length"][split_idx],
                np.zeros(len(split_idx), np.int32))

    def loader(arrs, shuffle):
        ds = ForecastWindows(*arrs, mean=mean, std=std, C=C, K=K)
        return DataLoader(ds, batch_size=batch_size, shuffle=shuffle,
                          num_workers=num_workers, drop_last=False), len(ds)

    train_dl, n_tr = loader(sub(tr), True)
    val_dl, n_va = loader(sub(va), False)
    testA_dl, n_ta = loader(sub(te), False)
    extB = (d["B_values"], d["B_mask"], d["B_static"], d["B_sepsis"],
            d["B_length"], np.ones(len(d["B_length"]), np.int32))
    testB_dl, n_tb = loader(extB, False)
    meta = dict(features=list(d["features"]), organ_names=list(d["organ_names"]),
                organ_slices=d["organ_slices"], mean=mean, std=std,
                n_train=n_tr, n_val=n_va, n_testA=n_ta, n_testB=n_tb, C=C, K=K)
    return train_dl, val_dl, testA_dl, testB_dl, meta


def masked_metrics(pred, target, tmask, horizons=(6, 12), organ_slices=None,
                   organ_names=None):
    """pred/target/tmask: (N,K,F). Returns dict of masked RMSE/MAE/NRMSE (normalised units).

    Because inputs are already in normalised units (std=1 per feature), RMSE here is
    effectively NRMSE; we report both names for clarity and a per-organ RMSE table.
    """
    out = {}
    for H in horizons:
        p, t, m = pred[:, :H], target[:, :H], tmask[:, :H]
        n = m.sum().clamp(min=1)
        se = ((p - t) ** 2 * m).sum() / n
        ae = ((p - t).abs() * m).sum() / n
        out[f"RMSE@{H}"] = float(se.sqrt())
        out[f"MAE@{H}"] = float(ae)
    # per-organ RMSE at the longest horizon
    if organ_slices is not None:
        H = max(horizons)
        for oi, (a, b) in enumerate(organ_slices):
            p, t, m = pred[:, :H, a:b], target[:, :H, a:b], tmask[:, :H, a:b]
            n = m.sum().clamp(min=1)
            name = organ_names[oi] if organ_names else f"organ{oi}"
            out[f"RMSE_{name}"] = float((((p - t) ** 2 * m).sum() / n).sqrt())
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz", default=str(RELEASE_ROOT / 'data/cinc2019_cohort.npz'))
    ap.add_argument("--C", type=int, default=12); ap.add_argument("--K", type=int, default=12)
    a = ap.parse_args()
    tr, va, ta, tb, meta = make_loaders(a.npz, a.C, a.K, batch_size=64)
    print("windows:", {k: meta[k] for k in ("n_train", "n_val", "n_testA", "n_testB")})
    b = next(iter(tr))
    print("batch:", {k: tuple(v.shape) if torch.is_tensor(v) else v
                     for k, v in b.items() if torch.is_tensor(v)})
    print("organs:", meta["organ_names"], "features:", meta["features"])
