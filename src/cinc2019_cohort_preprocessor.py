"""cinc2019_cohort_preprocessor — build the organ-grouped ICU forecasting cohort.

Parses the PhysioNet/CinC-2019 sepsis challenge ``.psv`` files (one patient per
file, hourly rows) into compact per-patient multivariate irregular time series
with missingness masks, grouped into four organ systems. ``training_setA`` and
``training_setB`` originate from two different hospital systems, giving a built-in
internal (A) -> external (B) generalization split with no credentialed data.

No treatment columns exist in CinC-2019, so this cohort drives the forecasting,
cross-cohort, and organ-edge-recovery results; interventional counterfactuals
come from the CVSim simulator instead.

Output per split: a compressed npz with padded values/masks, lengths, statics,
sepsis label sequence, and the hospital id. Normalisation statistics are fit on
the A-train split only and reused everywhere (no external-cohort leakage).
"""
from __future__ import annotations

# Resolve all public modules and scratch from the release root.
import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[1]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH

import argparse
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

# ---- 16 curated variables grouped into 4 organ systems (order matters) ----
ORGAN_GROUPS = {
    "cardiovascular": ["HR", "SBP", "MAP", "DBP"],
    "pulmonary":      ["O2Sat", "Resp", "FiO2", "PaCO2"],
    "renal":          ["Creatinine", "BUN", "Potassium"],
    "metabolic":      ["Lactate", "Glucose", "HCO3", "WBC", "Temp"],
}
FEATURES = [v for grp in ORGAN_GROUPS.values() for v in grp]   # 16, grouped
ORGAN_OF = {v: k for k, grp in ORGAN_GROUPS.items() for v in grp}
ORGAN_NAMES = list(ORGAN_GROUPS)
# index slice (start,end) of each organ within the 16-dim feature vector
_o = 0
ORGAN_SLICES = {}
for _k, _g in ORGAN_GROUPS.items():
    ORGAN_SLICES[_k] = (_o, _o + len(_g)); _o += len(_g)

STATIC_COLS = ["Age", "Gender", "Unit1", "Unit2", "HospAdmTime"]
T_MAX = 48          # cap ICU stay length (hours) for padded storage
MIN_LOS = 8         # need enough context + horizon


def _col_index(header):
    cols = header.strip().split("|")
    return {c: i for i, c in enumerate(cols)}


def parse_patient(path):
    """Return per-patient dict, or None if the stay is too short / unreadable."""
    try:
        with open(path) as fh:
            header = fh.readline()
            idx = _col_index(header)
            rows = [ln.strip().split("|") for ln in fh if ln.strip()]
    except OSError:
        return None
    if len(rows) < MIN_LOS:
        return None
    arr = np.array(rows, dtype=np.float32)        # (T, 41) with NaN for missing
    T = min(arr.shape[0], T_MAX)
    arr = arr[:T]

    vals = np.full((T_MAX, len(FEATURES)), np.nan, np.float32)
    for j, f in enumerate(FEATURES):
        vals[:T, j] = arr[:, idx[f]]
    mask = (~np.isnan(vals)).astype(np.float32)
    vals = np.nan_to_num(vals, nan=0.0)

    static = np.array([_safe(arr[0, idx[c]]) for c in STATIC_COLS], np.float32)
    sep = np.zeros(T_MAX, np.float32)
    sep[:T] = np.nan_to_num(arr[:, idx["SepsisLabel"]], nan=0.0)
    ever_sepsis = float(sep.max() > 0)
    return dict(values=vals, mask=mask, static=static, sepsis=sep,
                length=T, ever_sepsis=ever_sepsis)


def _safe(x):
    return 0.0 if np.isnan(x) else float(x)


def build_split(set_dir, hospital_id, max_patients=None, workers=16):
    files = sorted(Path(set_dir).glob("*.psv"))
    if max_patients:
        files = files[:max_patients]
    out = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for rec in ex.map(parse_patient, [str(f) for f in files], chunksize=64):
            if rec is not None:
                out.append(rec)
    if not out:
        raise RuntimeError(f"no usable patients in {set_dir}")
    pack = dict(
        values=np.stack([r["values"] for r in out]),     # (N,T_MAX,16)
        mask=np.stack([r["mask"] for r in out]),
        static=np.stack([r["static"] for r in out]),
        sepsis=np.stack([r["sepsis"] for r in out]),
        length=np.array([r["length"] for r in out], np.int32),
        ever_sepsis=np.array([r["ever_sepsis"] for r in out], np.float32),
        hospital=np.full(len(out), hospital_id, np.int32),
    )
    return pack


def fit_norm_stats(values, mask):
    """Per-feature mean/std over observed entries only (mask==1)."""
    m = mask.astype(bool)
    mean = np.zeros(values.shape[-1], np.float32)
    std = np.ones(values.shape[-1], np.float32)
    for j in range(values.shape[-1]):
        v = values[..., j][m[..., j]]
        if v.size > 10:
            mean[j] = v.mean()
            std[j] = v.std() + 1e-6
    return mean, std


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data_root", default=str(RELEASE_ROOT / 'data'))
    ap.add_argument("--out", default=str(RELEASE_ROOT / 'data/cinc2019_cohort.npz'))
    ap.add_argument("--max_patients", type=int, default=0)
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--val_frac", type=float, default=0.15)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    mp = args.max_patients or None

    root = Path(args.data_root)
    print("[prep] parsing setA (internal hospital) ...")
    A = build_split(root / "training_setA", 0, mp, args.workers)
    print(f"[prep]   A: {len(A['length'])} patients, sepsis rate {A['ever_sepsis'].mean():.3f}")
    print("[prep] parsing setB (external hospital) ...")
    B = build_split(root / "training_setB", 1, mp, args.workers)
    print(f"[prep]   B: {len(B['length'])} patients, sepsis rate {B['ever_sepsis'].mean():.3f}")

    # internal train/val/test split on A; B is held out entirely as external test
    rng = np.random.default_rng(args.seed)
    nA = len(A["length"])
    perm = rng.permutation(nA)
    n_test = int(0.15 * nA); n_val = int(args.val_frac * nA)
    test_idx, val_idx, train_idx = perm[:n_test], perm[n_test:n_test + n_val], perm[n_test + n_val:]

    mean, std = fit_norm_stats(A["values"][train_idx], A["mask"][train_idx])
    print("[prep] norm stats fit on A-train. feature means:",
          {FEATURES[j]: round(float(mean[j]), 1) for j in range(len(FEATURES))})

    np.savez_compressed(
        args.out,
        A_values=A["values"], A_mask=A["mask"], A_static=A["static"],
        A_sepsis=A["sepsis"], A_length=A["length"], A_ever_sepsis=A["ever_sepsis"],
        B_values=B["values"], B_mask=B["mask"], B_static=B["static"],
        B_sepsis=B["sepsis"], B_length=B["length"], B_ever_sepsis=B["ever_sepsis"],
        train_idx=train_idx, val_idx=val_idx, test_idx=test_idx,
        norm_mean=mean, norm_std=std,
        features=np.array(FEATURES), organ_names=np.array(ORGAN_NAMES),
        organ_slices=np.array([ORGAN_SLICES[o] for o in ORGAN_NAMES]),
    )
    sz = Path(args.out).stat().st_size / 1e6
    print(f"[prep] wrote {args.out} ({sz:.0f} MB) | "
          f"A train/val/test = {len(train_idx)}/{len(val_idx)}/{len(test_idx)}, "
          f"B external = {len(B['length'])}")


if __name__ == "__main__":
    main()
