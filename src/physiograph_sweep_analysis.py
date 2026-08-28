"""physiograph_sweep_analysis — analyse the Tier-2 'when?' sweeps (H1 horizon, H2 low-data).

Reads the per-setting result JSONs and reports, for the headline pair (PhysioGraph-GRU
vs. GRU-D), how the accuracy gap moves with training-set size or horizon -- the test
of whether the physiological graph prior helps in any regime. Emits a figure.
"""
from __future__ import annotations

import os
import argparse
import glob
import json
import re
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Repository root. Defaults to the parent of src/; override with the
# PHYSIOGRAPH_ROOT environment variable to relocate data/result trees.
REPO_ROOT = Path(os.environ.get("PHYSIOGRAPH_ROOT", Path(__file__).resolve().parents[1]))

FIG = REPO_ROOT / "result/figure"
BLUE, GREEN, GREY, RED = "#1f6fb4", "#2a9d8f", "#9aa7b4", "#d1495b"


def _load(path, K=12):
    R = json.load(open(path))["results"]
    return {m: (R[m]["A_test"][f"RMSE@{K}"], R[m]["B_external"][f"RMSE@{K}"])
            for m in R if m != "persistence"}


def analyse_h2(globpat, K=12, out_json=None):
    rows = []
    for f in glob.glob(globpat):
        frac = float(re.search(r"frac([0-9.]+)\.json", f).group(1))
        R = _load(f, K)
        rows.append((frac, R))
    rows.sort()
    fracs = [r[0] for r in rows]
    models = ["physiograph_gru", "grud", "gru"]
    series = {m: [r[1].get(m, (np.nan, np.nan))[1] for r in rows] for m in models}  # external B
    gap = [series["physiograph_gru"][i] - series["grud"][i] for i in range(len(fracs))]
    res = dict(fracs=fracs, external_B={m: series[m] for m in models}, pg_minus_grud=gap)
    # figure
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.5, 4.0))
    for m, c, lab in [("grud", GREEN, "GRU-D"), ("gru", GREY, "GRU"),
                      ("physiograph_gru", BLUE, "PhysioGraph-GRU")]:
        ax1.plot(fracs, series[m], "-o", color=c, label=lab, linewidth=2)
    ax1.set_xscale("log"); ax1.set_xlabel("Training fraction of hospital A")
    ax1.set_ylabel("External (B) RMSE@12"); ax1.legend(frameon=False)
    ax1.set_title("Low-data regime")
    ax2.axhline(0, color="black", lw=0.8)
    ax2.plot(fracs, gap, "-o", color=RED, linewidth=2)
    ax2.fill_between(fracs, gap, 0, where=[g < 0 for g in gap], color=GREEN, alpha=0.25)
    ax2.set_xscale("log"); ax2.set_xlabel("Training fraction")
    ax2.set_ylabel("PhysioGraph-GRU − GRU-D  (RMSE)")
    ax2.set_title("Does the prior ever win? (below 0 = PhysioGraph better)")
    d = FIG / "exp5"; d.mkdir(parents=True, exist_ok=True)
    fig.savefig(d / "h2_lowdata.png", bbox_inches="tight"); plt.close(fig)
    print(f"[h2] gap (PG-GRU minus GRU-D) by fraction:")
    for fr, g in zip(fracs, gap):
        flag = "  <-- PhysioGraph WINS" if g < 0 else ""
        print(f"    frac {fr:<5} external gap {g:+.4f}{flag}")
    if out_json:
        json.dump(res, open(out_json, "w"), indent=2)
    return res


def analyse_h1(globpat, out_json=None):
    rows = []
    for f in glob.glob(globpat):
        mt = re.search(r"C(\d+)_K(\d+)\.json", f)
        C, K = int(mt.group(1)), int(mt.group(2))
        R = json.load(open(f))["results"]
        pg = R["physiograph_gru"]["B_external"][f"RMSE@{K}"]
        gd = R["grud"]["B_external"][f"RMSE@{K}"]
        rows.append(dict(C=C, K=K, pg=pg, grud=gd, gap=pg - gd))
    rows.sort(key=lambda r: (r["C"], r["K"]))
    print("[h1] horizon sweep (external RMSE@K):")
    for r in rows:
        flag = "  <-- PhysioGraph WINS" if r["gap"] < 0 else ""
        print(f"    C={r['C']} K={r['K']}: PG {r['pg']:.3f} GRU-D {r['grud']:.3f} gap {r['gap']:+.4f}{flag}")
    if out_json:
        json.dump(rows, open(out_json, "w"), indent=2)
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--which", default="h2")
    ap.add_argument("--glob", default=str(REPO_ROOT / "result/sweeps/h2_frac*.json"))
    a = ap.parse_args()
    if a.which == "h2":
        analyse_h2(a.glob, out_json=str(REPO_ROOT / "result/h2_lowdata.json"))
    elif a.which == "h1":
        analyse_h1(a.glob, out_json=str(REPO_ROOT / "result/h1_horizon.json"))
