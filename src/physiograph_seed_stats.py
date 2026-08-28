"""physiograph_seed_stats — variance + significance for the headline forecasting table.

(1) Aggregates per-seed result JSONs into mean +/- std per model (M1).
(2) Runs a paired significance test for the headline comparison both ACROSS SEEDS
    and ACROSS TEST WINDOWS (the stronger test): per-window masked errors for two
    trained checkpoints, paired Wilcoxon signed-rank + a bootstrap 95% CI of the
    mean per-window difference. This is what tells a reviewer the 0.749-vs-0.774
    ordering is real, not noise.
"""
from __future__ import annotations

import os
import argparse
import glob
import json
from pathlib import Path

import numpy as np
import torch
from scipy import stats

from physiograph_data_loader import make_loaders
from physiograph_training_runner import build_any

# Repository root. Defaults to the parent of src/; override with the
# PHYSIOGRAPH_ROOT environment variable to relocate data/result trees.
REPO_ROOT = Path(os.environ.get("PHYSIOGRAPH_ROOT", Path(__file__).resolve().parents[1]))


def aggregate_seeds(seed_glob, K=12):
    files = sorted(glob.glob(seed_glob))
    runs = [json.load(open(f))["results"] for f in files]
    models = sorted({m for r in runs for m in r})
    agg = {}
    for m in models:
        A = [r[m]["A_test"][f"RMSE@{K}"] for r in runs if m in r]
        Bx = [r[m]["B_external"][f"RMSE@{K}"] for r in runs if m in r]
        dg = [r[m]["degradation_pct"] for r in runs if m in r]
        npar = next(r[m]["n_params"] for r in runs if m in r)
        agg[m] = dict(n_seeds=len(A), n_params=npar,
                      A_mean=float(np.mean(A)), A_std=float(np.std(A)),
                      B_mean=float(np.mean(Bx)), B_std=float(np.std(Bx)),
                      degr_mean=float(np.mean(dg)), degr_std=float(np.std(dg)),
                      A_vals=[round(x, 4) for x in A])
    return agg, len(files)


def paired_seed_test(seed_glob, a, b, K=12):
    runs = [json.load(open(f))["results"] for f in sorted(glob.glob(seed_glob))]
    xa = np.array([r[a]["A_test"][f"RMSE@{K}"] for r in runs if a in r and b in r])
    xb = np.array([r[b]["A_test"][f"RMSE@{K}"] for r in runs if a in r and b in r])
    if len(xa) < 2:
        return None
    t, p = stats.ttest_rel(xa, xb)
    return dict(a=a, b=b, n=len(xa), a_mean=float(xa.mean()), b_mean=float(xb.mean()),
                mean_diff=float((xa - xb).mean()), t=float(t), p_value=float(p))


@torch.no_grad()
def per_window_errors(model, loader, device, K):
    model.eval(); out = []
    for bch in loader:
        bch = {k: (v.to(device) if torch.is_tensor(v) else v) for k, v in bch.items()}
        pred = model(bch, horizon=K)
        m = bch["target_mask"]; t = bch["target"]
        se = ((pred - t) ** 2 * m).sum(dim=(1, 2)) / m.sum(dim=(1, 2)).clamp(min=1)
        out.append(se.cpu().numpy())
    return np.concatenate(out)


def per_window_test(npz, ckpt_a, ckpt_b, name_a, name_b, C=12, K=12, gpu=2, n_boot=2000):
    device = torch.device(f"cuda:{gpu}" if torch.cuda.is_available() else "cpu")
    _, _, testA, _, meta = make_loaders(npz, C, K, batch_size=256)

    def load(name, ckpt):
        m = build_any(name, 5, 128, 96, 48, 2).to(device)
        m.load_state_dict(torch.load(ckpt, map_location=device)); return m
    ea = per_window_errors(load(name_a, ckpt_a), testA, device, K)
    eb = per_window_errors(load(name_b, ckpt_b), testA, device, K)
    n = min(len(ea), len(eb)); ea, eb = ea[:n], eb[:n]
    diff = np.sqrt(ea) - np.sqrt(eb)                  # per-window RMSE difference
    w, p = stats.wilcoxon(ea, eb)
    rng = np.random.default_rng(0)
    boot = np.array([diff[rng.integers(0, n, n)].mean() for _ in range(n_boot)])
    return dict(name_a=name_a, name_b=name_b, n_windows=int(n),
                rmse_a=float(np.sqrt(ea.mean())), rmse_b=float(np.sqrt(eb.mean())),
                mean_window_diff=float(diff.mean()),
                ci95=[float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
                wilcoxon_p=float(p),
                a_better_frac=float((diff < 0).mean()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed_glob", default=str(REPO_ROOT / "result/seeds/forecast_seed*.json"))
    ap.add_argument("--npz", default=str(REPO_ROOT / "data/cinc2019_cohort.npz"))
    ap.add_argument("--gpu", type=int, default=2)
    ap.add_argument("--out", default=str(REPO_ROOT / "result/forecast_seed_stats.json"))
    a = ap.parse_args()
    agg, nf = aggregate_seeds(a.seed_glob)
    print(f"[stats] aggregated {nf} seeds")
    for m, s in sorted(agg.items(), key=lambda kv: kv[1]["A_mean"]):
        print(f"  {m:16s} {s['n_params']/1e6:5.2f}M  A {s['A_mean']:.3f}±{s['A_std']:.3f}  "
              f"B {s['B_mean']:.3f}±{s['B_std']:.3f}  degr {s['degr_mean']:.1f}±{s['degr_std']:.1f}%")
    tests = {}
    for a_, b_ in [("physiograph_gru", "grud"), ("physiograph_gru", "gru_med"),
                   ("physiograph", "grud")]:
        r = paired_seed_test(a.seed_glob, a_, b_)
        if r:
            tests[f"{a_}_vs_{b_}_seeds"] = r
            print(f"  paired(seeds) {a_} vs {b_}: diff {r['mean_diff']:+.4f} p={r['p_value']:.3f}")
    # stronger across-window test for the headline pair, using final checkpoints
    ck = str(REPO_ROOT / "ckpt")
    try:
        pw = per_window_test(a.npz, f"{ck}/physiograph_gru.pt", f"{ck}/grud.pt",
                             "physiograph_gru", "grud", gpu=a.gpu)
        tests["physiograph_gru_vs_grud_windows"] = pw
        print(f"  paired(windows) physiograph_gru vs grud: GRU-D better by "
              f"{-pw['mean_window_diff']:+.4f} RMSE, 95% CI {pw['ci95']}, Wilcoxon p={pw['wilcoxon_p']:.2e}")
    except Exception as e:
        print(f"  per-window test skipped: {e}")
    json.dump({"aggregate": agg, "tests": tests}, open(a.out, "w"), indent=2)
    print(f"[stats] wrote {a.out}")


if __name__ == "__main__":
    main()
