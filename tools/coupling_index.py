#!/usr/bin/env python3
"""Stay-clustered predictive coupling probes; CPU only, no source/data changes.

CI(source -> target) = 1 - RMSE(own + source) / RMSE(own).
Rows are sources; columns are targets. Targets and losses use observed entries
only. Histories contain normalized, re-masked values AND observation indicators.
Every valid rolling window is used, with no cross-stay windows or target leakage.
"""
from __future__ import annotations

# Resolve all public modules and scratch from the release root.
import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[1]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time

import numpy as np
from scipy.linalg import solve
import torch
from torch import nn

ROOT = RELEASE_ROOT
PROJECT = RELEASE_ROOT
ALPHAS = (0.01, 0.1, 1.0, 10.0, 100.0, 1000.0)
EXPECTED = {
    "cinc2019_cohort.npz": "d52d8131323f",
    "physiograph_data_loader.py": "a45411d7635f",
    "h3_k0.npz": "1f4b2b8a3f8a", "h3_k0.1.npz": "a33c796b5f72",
    "h3_k0.25.npz": "4be5a8a34c5c", "h3_k0.5.npz": "722c530e7de4",
    "h3_k0.75.npz": "d88c2dd54607", "h3_k1.0.npz": "8e0b1d24d406",
    "reference_k1_c1_sigma003.npz": "a8c39268633f",
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def owned(path):
    p = Path(path).resolve()
    if not p.is_relative_to(ROOT):
        raise ValueError(f"output must be inside {ROOT}: {p}")
    return p


def save_json(path, obj):
    p = owned(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w") as f:
        json.dump(obj, f, indent=2, allow_nan=False)
        f.write("\n")


@dataclass
class Windows:
    x: np.ndarray  # samples, history, 2 * features (values then masks)
    y: np.ndarray
    mask: np.ndarray
    stay: np.ndarray  # local index including eligible stays without observed targets
    ids: np.ndarray
    n_input_stays: int

    @property
    def n_stays(self):
        return len(self.ids)

    def denominator(self, channels=None):
        channels = list(range(self.y.shape[1])) if channels is None else channels
        m = self.mask[:, channels]
        counts = np.bincount(self.stay, weights=m.sum(1), minlength=self.n_stays)
        return dict(stays_in_split=self.n_input_stays, stays_with_valid_history=self.n_stays,
                    stays_with_observed_target=int((counts > 0).sum()),
                    windows=int(len(self.y)), windows_with_observed_target=int((m.sum(1) > 0).sum()),
                    observed_target_entries=int(m.sum()),
                    observed_target_entries_by_channel=m.sum(0).astype(int).tolist())


def make_windows(values, mask, lengths, mean, std, ids=None, history=12):
    """Array index q predicts q from [q-history, q); the latest input is q-1."""
    values = np.asarray(values, np.float32)
    mask = np.asarray(mask, np.float32)
    lengths = np.minimum(np.asarray(lengths), values.shape[1])
    ids = np.arange(len(values)) if ids is None else np.asarray(ids)
    keep = lengths >= history + 1
    eligible = np.flatnonzero(keep)
    if not len(eligible):
        raise ValueError("no stay provides a complete history and a future target")
    norm = np.where(mask.astype(bool), (values - mean) / std, 0).astype(np.float32)
    v = np.concatenate([norm, mask], axis=-1)
    local, target = [], []
    for i, j in enumerate(eligible):
        q = np.arange(history, int(lengths[j]))
        local.extend([i] * len(q))
        target.extend(q)
    local = np.asarray(local, np.int64)
    target = np.asarray(target, np.int64)
    raw = eligible[local]
    context = target[:, None] - np.arange(history, 0, -1)[None, :]
    x = np.ascontiguousarray(v[raw[:, None], context])
    return Windows(x, norm[raw, target], mask[raw, target], local, ids[eligible], len(values))


def feature_indices(channels, n_features):
    return list(channels) + [n_features + c for c in channels]


def selected_inputs(w, channels):
    return np.ascontiguousarray(w.x[:, :, feature_indices(channels, w.y.shape[1])])


def error_by_stay(pred, w, target):
    target = list(target)
    m = w.mask[:, target]
    error = np.square(pred.astype(np.float64) - w.y[:, target].astype(np.float64)) * m
    return np.bincount(w.stay, weights=error.sum(1), minlength=w.n_stays), np.bincount(
        w.stay, weights=m.sum(1), minlength=w.n_stays)


def masked_rmse(pred, y, mask):
    n = mask.sum()
    if not n:
        raise ValueError("no observed target entries")
    return float(np.sqrt((np.square(pred.astype(np.float64) - y) * mask).sum() / n))


def fit_ridge(train, val, channels, target, alphas=ALPHAS):
    """Output-specific masked normal equations, unpenalized intercept, float64.

    Objective per output: sum_observed (y-Xb)^2 + alpha * ||b_nonintercept||^2.
    A single alpha for all channels of this target is selected by pooled A-val RMSE.
    """
    target = list(target)
    x = selected_inputs(train, channels).reshape(len(train.y), -1).astype(np.float64)
    xv = selected_inputs(val, channels).reshape(len(val.y), -1).astype(np.float64)
    x = np.column_stack([x, np.ones(len(x))])
    xv = np.column_stack([xv, np.ones(len(xv))])
    grams, rhs = [], []
    for c in target:
        keep = train.mask[:, c].astype(bool)
        if not keep.any():
            raise ValueError(f"no training observations for target channel {c}")
        xc = x[keep]
        grams.append(xc.T @ xc)
        rhs.append(xc.T @ train.y[keep, c].astype(np.float64))
    models, scores = [], []
    penalty = np.eye(x.shape[1]); penalty[-1, -1] = 0
    for alpha in alphas:
        coef = np.column_stack([solve(g + alpha * penalty, r, assume_a="pos")
                                for g, r in zip(grams, rhs)])
        pred = xv @ coef
        models.append(coef)
        scores.append(masked_rmse(pred, val.y[:, target], val.mask[:, target]))
    best = int(np.argmin(scores))
    meta = dict(alpha=float(alphas[best]), alpha_grid=list(alphas),
                validation_rmse_by_alpha=scores, selection="minimum pooled masked A_val RMSE; ties first alpha",
                train_denominator=train.denominator(target), validation_denominator=val.denominator(target))
    return models[best], meta


def predict_ridge(coef, w, channels, batch_size=16384):
    preds = []
    ix = feature_indices(channels, w.y.shape[1])
    for start in range(0, len(w.y), batch_size):
        x = np.ascontiguousarray(w.x[start:start + batch_size, :, ix]).reshape(
            -1, w.x.shape[1] * len(ix)).astype(np.float64)
        preds.append(x @ coef[:-1] + coef[-1])
    return np.concatenate(preds)


class GRUProbe(nn.Module):
    def __init__(self, n_inputs, n_outputs):
        super().__init__()
        self.gru = nn.GRU(n_inputs, 32, num_layers=1, batch_first=True)
        self.head = nn.Linear(32, n_outputs)

    def forward(self, x):
        _, h = self.gru(x)
        return self.head(h[-1])


def fit_gru(train, channels, target, seed=0, epochs=5, batch_size=2048):
    torch.manual_seed(seed)
    target = list(target)
    x = torch.from_numpy(selected_inputs(train, channels))
    y = torch.from_numpy(np.ascontiguousarray(train.y[:, target]))
    m = torch.from_numpy(np.ascontiguousarray(train.mask[:, target]))
    # A window with no observed target has zero loss; omitting it changes no labels.
    observed = torch.nonzero(m.sum(1) > 0, as_tuple=True)[0]
    model = GRUProbe(x.shape[-1], len(target))
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    generator = torch.Generator().manual_seed(seed)
    losses = []
    for epoch in range(epochs):
        order = observed[torch.randperm(len(observed), generator=generator)]
        se, count = 0.0, 0
        model.train()
        for idx in order.split(batch_size):
            optimizer.zero_grad(set_to_none=True)
            pred = model(x[idx])
            loss_sum = ((pred - y[idx]).square() * m[idx]).sum()
            n = m[idx].sum()
            (loss_sum / n).backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            se += float(loss_sum.detach()); count += int(n)
        losses.append(dict(epoch=epoch + 1, training_mse=se / count,
                           observed_target_entries=count, stays=train.denominator(target)["stays_with_observed_target"]))
    return model.eval(), dict(seed=seed, epochs=epochs, hidden_width=32, layers=1,
                             batch_size=batch_size, learning_rate=0.001, optimizer="Adam",
                             gradient_norm_cap=1.0, training_losses=losses,
                             checkpoint="final epoch; no validation early stopping",
                             train_denominator=train.denominator(target))


def predict_gru(model, w, channels, batch_size=4096):
    preds = []
    ix = feature_indices(channels, w.y.shape[1])
    with torch.no_grad():
        for start in range(0, len(w.y), batch_size):
            x = torch.from_numpy(np.ascontiguousarray(w.x[start:start + batch_size, :, ix]))
            preds.append(model(x).numpy())
    return np.concatenate(preds)


def ci_ratio(own_sse, added_sse, counts):
    if counts <= 0 or own_sse <= 0:
        return np.nan
    # Identical observed targets mean the counts cancel in the ratio of RMSEs.
    return float(1 - np.sqrt(added_sse / own_sse))


def finite_list(array):
    a = np.asarray(array)
    if a.ndim == 0:
        return float(a) if np.isfinite(a) else None
    return [finite_list(row) for row in a]


def summarize(own, added, counts, w, organs, n_resamples=1000, seed=913):
    """Paired nonparametric cluster bootstrap; frozen fits, all windows per stay.

    own/counts: stays x targets; added: stays x sources x targets.
    Each draw resamples the SAME stays for all matrix cells and recomputes RMSE
    ratios and the unweighted arithmetic mean across defined off-diagonal cells.
    """
    n = len(organs)
    point = np.full((n, n), np.nan)
    rmse_own = np.sqrt(own.sum(0) / counts.sum(0))
    rmse_added = np.sqrt(added.sum(0) / counts.sum(0)[None, :])
    for i in range(n):
        for j in range(n):
            point[i, j] = ci_ratio(own[:, j].sum(), added[:, i, j].sum(), counts[:, j].sum())
    off = ~np.eye(n, dtype=bool)
    defined = off & np.isfinite(point)
    complete_mean = int(defined.sum()) == n * (n - 1)
    draws = np.full((n_resamples, n, n), np.nan)
    mean_draws = np.full(n_resamples, np.nan)
    rng = np.random.default_rng(seed)
    for r in range(n_resamples):
        ix = rng.integers(0, w.n_stays, size=w.n_stays)
        so, sa, ct = own[ix].sum(0), added[ix].sum(0), counts[ix].sum(0)
        for i in range(n):
            for j in range(n):
                draws[r, i, j] = ci_ratio(so[j], sa[i, j], ct[j])
        if complete_mean and np.isfinite(draws[r][off]).all():
            mean_draws[r] = draws[r][defined].mean()
    lower, upper = np.full((n, n), np.nan), np.full((n, n), np.nan)
    for i in range(n):
        for j in range(n):
            valid = draws[:, i, j][np.isfinite(draws[:, i, j])]
            if len(valid):
                lower[i, j], upper[i, j] = np.quantile(valid, [.025, .975])
    valid_mean = mean_draws[np.isfinite(mean_draws)]
    den = dict(stays_available=w.n_stays, stays_in_split=w.n_input_stays,
               stays_with_observed_target_by_column=(counts > 0).sum(0).astype(int).tolist(),
               observed_target_entries_by_column=counts.sum(0).astype(int).tolist(),
               windows=len(w.y), resamples_requested=n_resamples,
               resamples_valid_by_cell=np.isfinite(draws).sum(0).tolist())
    return dict(
        row_order=organs, column_order=organs,
        matrix=dict(value=finite_list(point), lower_95=finite_list(lower), upper_95=finite_list(upper),
                    rmse_own_by_column=finite_list(rmse_own), rmse_own_plus_source=finite_list(rmse_added),
                    denominator=den, diagonal="same fitted own-only model; exactly zero when denominator is positive",
                    undefined="null if own RMSE is zero or no observed targets"),
        mean_off_diagonal=dict(value=finite_list(point[off].mean() if complete_mean else np.nan),
                               lower_95=finite_list(np.quantile(valid_mean, .025) if len(valid_mean) else np.nan),
                               upper_95=finite_list(np.quantile(valid_mean, .975) if len(valid_mean) else np.nan),
                               denominator={**den, "ordered_pairs_defined": int(defined.sum()),
                                            "ordered_pairs_possible": n * (n - 1),
                                            "resamples_valid": len(valid_mean)},
                               aggregation="unweighted mean across all directed off-diagonal cells; null if any cell is undefined"),
        bootstrap=dict(method="paired stay-cluster percentile; pooled masked RMSE recomputed in each resample",
                       confidence_level=.95, seed=seed, resamples=n_resamples,
                       includes_training_uncertainty=False, includes_hyperparameter_selection_uncertainty=False))


def run_probe(splits, organs, groups, probe, seed=0, resamples=1000, batch_size=2048,
              artifacts=None, dataset_name="dataset"):
    train, val = splits["A_train"], splits["A_val"]
    n = len(organs)
    own = {k: np.zeros((w.n_stays, n)) for k, w in splits.items() if k != "A_train"}
    added = {k: np.zeros((w.n_stays, n, n)) for k, w in splits.items() if k != "A_train"}
    counts = {k: np.zeros((w.n_stays, n)) for k, w in splits.items() if k != "A_train"}
    fits = {}
    for j, target in enumerate(groups):
        fits[organs[j]] = {}
        # One own-only fit, reused for all incoming edges and the diagonal.
        for source in [None] + [i for i in range(n) if i != j]:
            channels = list(target) + ([] if source is None else list(groups[source]))
            model_seed = seed + j * 100  # paired initialization seed within target
            start = time.monotonic()
            if probe == "ridge":
                model, fit = fit_ridge(train, val, channels, target)
                predict = predict_ridge
            elif probe == "gru":
                model, fit = fit_gru(train, channels, target, seed=model_seed, batch_size=batch_size)
                predict = predict_gru
            else:
                raise ValueError(probe)
            label = "own" if source is None else f"own_plus_{organs[source]}"
            fits[organs[j]][label] = fit
            for split, w in splits.items():
                if split == "A_train":
                    continue
                prediction = predict(model, w, channels)
                se, ct = error_by_stay(prediction, w, target)
                if source is None:
                    own[split][:, j] = se
                    counts[split][:, j] = ct
                    added[split][:, j, j] = se
                else:
                    added[split][:, source, j] = se
                    assert np.array_equal(ct, counts[split][:, j])
            print(f"{dataset_name} {probe} target={organs[j]} {label} "
                  f"seconds={time.monotonic() - start:.2f}", flush=True)
    out = dict(fits=fits, splits={})
    for split, w in splits.items():
        if split == "A_train":
            continue
        out["splits"][split] = summarize(own[split], added[split], counts[split], w, organs,
                                         n_resamples=resamples, seed=913 + seed)
        if artifacts:
            p = owned(Path(artifacts) / f"{dataset_name}_{probe}_{split}_stay_errors.npz")
            np.savez_compressed(p, own_sse=own[split], added_sse=added[split], counts=counts[split],
                                stay_ids=w.ids, organ_names=np.asarray(organs))
            out["splits"][split]["stay_error_artifact"] = str(p.relative_to(ROOT))
            out["splits"][split]["stay_error_sha256"] = sha256(p)
    return out


def load_cinc(path):
    with np.load(path, allow_pickle=False) as d:
        organs = d["organ_names"].tolist()
        groups = [list(range(int(a), int(b))) for a, b in d["organ_slices"]]
        mean, std = d["norm_mean"], d["norm_std"]
        tr, va, te = d["train_idx"], d["val_idx"], d["test_idx"]
        assert not set(tr) & set(va) and not set(tr) & set(te) and not set(va) & set(te)
        av, am, al = d["A_values"], d["A_mask"], d["A_length"]
        splits = {name: make_windows(av[ix], am[ix], al[ix], mean, std, ids=ix)
                  for name, ix in (("A_train", tr), ("A_val", va))}
        splits["B"] = make_windows(d["B_values"], d["B_mask"], d["B_length"], mean, std)
        meta = dict(organs=organs, organ_channels={o: [d["features"][c].item() for c in g]
                                                  for o, g in zip(organs, groups)},
                    normalization=dict(mean=mean.tolist(), std=std.tolist(), source="stored A-train observed-entry statistics",
                                       denominator={"stays": len(tr), "observed_entries_by_channel": am[tr].sum((0, 1)).astype(int).tolist()}),
                    splits={k: w.denominator() for k, w in splits.items()},
                    unused_A_test_stays=len(te),
                    history_hours=12, forecast_hours=1, sliding_stride_hours=1,
                    stored_horizon_hours=av.shape[1])
    return splits, organs, groups, meta


def inspect_simulator(path):
    with np.load(path, allow_pickle=False) as d:
        t = d["t_min"].astype(float)
        metadata = json.loads(str(d["metadata_json"].item()))
        return dict(path=str(path), sha256=sha256(path), metadata=metadata,
                    patients=int(d["factual"].shape[0]), samples_per_patient=len(t),
                    duration_hours=float((t[-1] - t[0]) / 60),
                    sample_interval_minutes=float(np.diff(t)[0]),
                    organs={"cardiovascular": ["MAP", "HR", "CO", "CVP"], "renal": ["UO"], "metabolic": ["Lac"]},
                    literal_12_hour_history_eligible_stays=0,
                    status="unavailable_under_literal_definition",
                    reason="Six-hour trajectories cannot supply twelve-hour histories; three organs cannot form a four-organ matrix.")


def load_simulator_diagnostic(path, seed=0):
    """Explicit NON-LITERAL 12-sample / next-sample comparison, never hourly."""
    with np.load(path, allow_pickle=False) as d:
        v = d["factual"][:, :, :6].copy()
    # Patient split is fixed across kappa: A_train=70%, A_val=15%, B=15%.
    # B is a random holdout of the SAME simulator, not an external hospital.
    perm = np.random.default_rng(seed).permutation(len(v))
    ntr, nva = int(.7 * len(v)), int(.15 * len(v))
    indices = {"A_train": perm[:ntr], "A_val": perm[ntr:ntr + nva], "B": perm[ntr + nva:]}
    # Float64 accumulation preserves exact centering for a constant float32
    # channel. Float32 accumulation otherwise creates a spurious nonzero offset
    # and a nonzero variance, destabilizing a ratio with near-zero own-only error.
    training_values = v[indices["A_train"]].astype(np.float64)
    mean = training_values.mean((0, 1))
    std = training_values.std((0, 1)) + 1e-6
    splits = {k: make_windows(v[ix], np.ones_like(v[ix]), np.full(len(ix), v.shape[1]),
                              mean, std, ids=ix) for k, ix in indices.items()}
    organs = ["cardiovascular", "renal", "metabolic"]
    groups = [list(range(4)), [4], [5]]
    meta = dict(status="diagnostic_only_definition_differs", history_samples=12, history_minutes=60,
                forecast_samples=1, forecast_minutes=5, organs=organs,
                excluded_channels=["vaso", "sepsis"],
                split_definition="fixed seeded 70/15/15 patient split; B is same-simulator holdout, not external hospital",
                split_seed=seed, splits={k: w.denominator() for k, w in splits.items()},
                normalization=dict(mean=mean.tolist(), std=std.tolist(),
                                   accumulation="float64; constant channels center exactly to zero",
                                   denominator={"stays": ntr, "observed_entries_per_channel": int(ntr * v.shape[1])}),
                target_variance_by_channel=dict(value=v[indices["A_train"]].astype(np.float64).var((0, 1)).tolist(),
                                                denominator={"stays": ntr, "observations_per_channel": int(ntr * v.shape[1])}))
    meta["constant_target_channels"] = [name for name, var in zip(
        ["MAP", "HR", "CO", "CVP", "UO", "Lac"], meta["target_variance_by_channel"]["value"]) if var == 0]
    meta["constant_target_note"] = (
        "CI is undefined at zero own-only RMSE; GRU ratios on constant targets reflect residual fitting error, not physiological coupling. "
        "The full off-diagonal mean is null if any constituent CI is undefined.")
    return splits, organs, groups, meta


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=PROJECT)
    parser.add_argument("--out", type=Path, default=ROOT / "coupling_index.json")
    parser.add_argument("--datasets", choices=["cinc", "simulator", "all"], default="all")
    parser.add_argument("--probes", nargs="+", choices=["ridge", "gru"], default=["ridge", "gru"])
    parser.add_argument("--simulator-mode", choices=["literal", "diagnostic"], default="literal")
    parser.add_argument("--resamples", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=2048)
    a = parser.parse_args()
    owned(a.out)
    torch.set_num_threads(a.threads)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    if a.resamples != 1000:
        raise ValueError("task-card run requires exactly 1000 bootstrap resamples")
    artifacts = ROOT / "artifacts"
    artifacts.mkdir(exist_ok=True)
    simdir = a.project / "data/sim_forecast"
    simpaths = [simdir / f"h3_k{k}.npz" for k in ("0", "0.1", "0.25", "0.5", "0.75", "1.0")]
    reference = simdir / "reference_k1_c1_sigma003.npz"
    cincpath = a.project / "data/cinc2019_cohort.npz"
    input_paths = [cincpath, a.project / "src/physiograph_data_loader.py", *simpaths, reference]
    hashes = {str(p): sha256(p) for p in input_paths}
    from replay_simulators import verify as verify_simulator
    distribution = json.loads((ROOT / "manifests/distribution.json").read_text())
    simulator_inputs = json.loads((ROOT / "manifests/simulator_datasets.json").read_text())["datasets"]
    by_name = {Path(item["path"]).name: item for item in simulator_inputs if item["group"] == "forecast"}
    for p in input_paths:
        if p.suffix == ".py":
            expected = distribution[str(p.relative_to(ROOT))]["distributed_sha256"]
            if hashes[str(p)] != expected:
                raise ValueError(f"distributed source hash mismatch: {p}")
        elif p.name == "cinc2019_cohort.npz":
            if not hashes[str(p)].startswith(EXPECTED[p.name]):
                raise ValueError(f"cohort hash mismatch: {p}")
        else:
            verify_simulator(p, by_name[p.name])
    result = dict(task="coupling_index-coupling-index-build", started_utc=datetime.now(timezone.utc).isoformat(),
                  source_sha256=sha256(__file__),
                  definition="1 - masked_RMSE(own_plus_source) / masked_RMSE(own)",
                  matrix_orientation="source rows, target columns",
                  input_sha256=hashes,
                  environment=dict(python=os.sys.version, numpy=np.__version__, torch=torch.__version__,
                                   device="cpu", torch_threads=a.threads, seed=a.seed),
                  settings=dict(ridge_alpha_grid=list(ALPHAS), gru_width=32, gru_layers=1, gru_epochs=5,
                                gru_batch_size=a.batch_size, bootstrap_resamples=a.resamples,
                                features="normalized masked values followed by binary observation masks",
                                target="next observed hour; score only recorded target entries",
                                window_weighting="pooled observed target entries; long stays contribute more windows",
                                uncertainty="evaluation stays only; no refit bootstrap; A-val is used for ridge selection"),
                  datasets={}, simulator_inputs=[inspect_simulator(p) for p in simpaths],
                  simulator_reference=inspect_simulator(reference),
                  interpretation=dict(status="no_direct_kappa_placement",
                                      reason="Literal simulator definition unavailable; simulator and cohort organs, sampling, missingness and split domains differ. Predictive CI alone does not identify causal coupling or isolate a model failure."))
    result["simulator_curve"] = dict(
        status="unavailable_under_literal_definition",
        definition="12-hour history, next-hour target",
        points=[dict(kappa=s["metadata"]["kappa"], value=None, lower_95=None, upper_95=None,
                     probes_requested=a.probes,
                     denominator=dict(input_stays=s["patients"], stays_with_12_hour_history=0,
                                      scored_target_entries=0, bootstrap_resamples=0),
                     reason=s["reason"]) for s in result["simulator_inputs"]])
    start = time.monotonic()
    if a.datasets in ("cinc", "all"):
        splits, organs, groups, meta = load_cinc(cincpath)
        meta["probes"] = {}
        result["datasets"]["cinc2019"] = meta
        for probe in a.probes:
            meta["probes"][probe] = run_probe(splits, organs, groups, probe, a.seed, a.resamples,
                                              a.batch_size, artifacts, "cinc2019")
            save_json(a.out, result)
        del splits
    if a.datasets in ("simulator", "all") and a.simulator_mode == "diagnostic":
        result["simulator_diagnostic_curve"] = {}
        for p in simpaths:
            splits, organs, groups, meta = load_simulator_diagnostic(p, seed=a.seed)
            name = p.stem
            meta["probes"] = {}
            result["datasets"][name] = meta
            result["simulator_diagnostic_curve"][name] = dict(
                kappa=next(s["metadata"]["kappa"] for s in result["simulator_inputs"] if s["path"] == str(p)),
                status="12-sample history, 5-minute forecast; not the literal hourly index", probes={})
            for probe in a.probes:
                out = run_probe(splits, organs, groups, probe, a.seed, a.resamples,
                                a.batch_size, artifacts, name)
                meta["probes"][probe] = out
                result["simulator_diagnostic_curve"][name]["probes"][probe] = {
                    split: out["splits"][split]["mean_off_diagonal"] for split in ("A_val", "B")}
                save_json(a.out, result)
            del splits
    # All scientific inputs must remain byte-identical throughout the run.
    after = {str(p): sha256(p) for p in input_paths}
    assert hashes == after, "input data changed during execution"
    result["input_integrity_verified"] = True
    result["finished_utc"] = datetime.now(timezone.utc).isoformat()
    result["elapsed_seconds"] = time.monotonic() - start
    assert result["source_sha256"] == sha256(__file__), "analysis source changed during execution"
    save_json(a.out, result)
    print(f"saved {a.out}; seconds={result['elapsed_seconds']:.2f}", flush=True)


if __name__ == "__main__":
    main()
