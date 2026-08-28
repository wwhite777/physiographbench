"""physiograph_result_figures — exact-data figures for the paper (house style).

Three MPR figures, each drawn from saved result JSON (no mock data ever):
  exp1  forecasting: internal (A) vs external (B) RMSE per model
  exp2  learned organ graph with edge-stability shading (bootstrap over patients)
  exp3  CVSim counterfactual: predicted vs true MAP dose-response + per-dose RMSE

Style: white background, flat, high-contrast, no overlapping components. The organ
graph uses large circled node numbers + a side legend (no free text inside the
panel). Figures are written under result/figure/exp{1,2,3}/.
"""
from __future__ import annotations

import os
import argparse
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Circle

# Repository root. Defaults to the parent of src/; override with the
# PHYSIOGRAPH_ROOT environment variable to relocate data/result trees.
REPO_ROOT = Path(os.environ.get("PHYSIOGRAPH_ROOT", Path(__file__).resolve().parents[1]))

plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
    "font.size": 12, "axes.spines.top": False, "axes.spines.right": False,
    "axes.linewidth": 1.0, "figure.dpi": 140,
})
FIGROOT = REPO_ROOT / "result/figure"
BLUE, GREY, RED, GREEN = "#1f6fb4", "#9aa7b4", "#d1495b", "#2a9d8f"


def _save(fig, exp, name):
    d = FIGROOT / exp; d.mkdir(parents=True, exist_ok=True)
    p = d / name; fig.savefig(p, bbox_inches="tight"); plt.close(fig)
    print(f"[fig] wrote {p}"); return p


def fig_forecasting(json_path, K=12):
    # prefer multi-seed means (includes capacity-controlled GRUs) if available
    stats_path = Path(json_path).parent / "forecast_seed_stats.json"
    if stats_path.exists():
        agg = json.load(open(stats_path))["aggregate"]
        names = sorted([n for n in agg if n != "ncde"], key=lambda n: agg[n]["A_mean"])
        A = [agg[n]["A_mean"] for n in names]; B = [agg[n]["B_mean"] for n in names]
    else:
        R = json.load(open(json_path))["results"]
        names = sorted(R, key=lambda n: R[n]["A_test"][f"RMSE@{K}"])
        A = [R[n]["A_test"][f"RMSE@{K}"] for n in names]
        B = [R[n]["B_external"][f"RMSE@{K}"] for n in names]
    x = np.arange(len(names)); w = 0.38
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    c_int = [BLUE if n.startswith("physiograph") else GREY for n in names]
    c_ext = [GREEN if n.startswith("physiograph") else "#c8d2dc" for n in names]
    ax.bar(x - w / 2, A, w, label="Internal (Hospital A)", color=c_int, edgecolor="black", linewidth=0.6)
    ax.bar(x + w / 2, B, w, label="External (Hospital B)", color=c_ext, edgecolor="black", linewidth=0.6)
    ax.set_xticks(x); ax.set_xticklabels([n.replace("physiograph", "PhysioGraph") for n in names],
                                         rotation=20, ha="right")
    ax.set_ylabel(f"Forecast RMSE @ {K} h (normalised)")
    ax.legend(frameon=False, loc="upper left")
    ax.set_title("Multi-organ trajectory forecasting (lower is better)", fontsize=12)
    return _save(fig, "exp1", "forecasting_internal_external.png")


def fig_counterfactual(json_path):
    R = json.load(open(json_path))["results"]
    doses = R["physiograph"]["doses"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.5, 4.0))
    # left: dose-response of MAP
    ax1.plot(doses, R["physiograph"]["true_map_by_dose"], "-o", color="black",
             label="CVSim ground truth", linewidth=2.2, zorder=3)
    ax1.plot(doses, R["physiograph"]["pred_map_by_dose"], "--s", color=BLUE,
             label="PhysioGraph", linewidth=2.0)
    if "control_gru" in R:
        ax1.plot(doses, R["control_gru"]["pred_map_by_dose"], ":^", color=RED,
                 label="Control-GRU", linewidth=2.0)
    ax1.set_xlabel("Counterfactual vasopressor dose (mcg/kg/min)")
    ax1.set_ylabel("Mean MAP response (mmHg)")
    ax1.legend(frameon=False, loc="best"); ax1.set_title("Counterfactual dose-response")
    # right: per-dose RMSE
    x = np.arange(len(doses)); w = 0.38
    ax2.bar(x - w / 2, R["physiograph"]["per_dose_rmse"], w, color=BLUE, label="PhysioGraph",
            edgecolor="black", linewidth=0.6)
    if "control_gru" in R:
        ax2.bar(x + w / 2, R["control_gru"]["per_dose_rmse"], w, color=RED, label="Control-GRU",
                edgecolor="black", linewidth=0.6)
    ax2.set_xticks(x); ax2.set_xticklabels([str(d) for d in doses])
    ax2.set_xlabel("Counterfactual dose"); ax2.set_ylabel("Counterfactual RMSE")
    ax2.legend(frameon=False); ax2.set_title("Counterfactual error by dose")
    return _save(fig, "exp3", "cvsim_counterfactual.png")


# organ layout for the graph schematic
ORGAN_POS = {0: (0.0, 1.0), 1: (1.0, 0.4), 2: (-1.0, 0.4), 3: (0.0, -0.7)}
ORGAN_ABBR = {0: "Cardiovascular", 1: "Pulmonary", 2: "Renal", 3: "Metabolic"}


def fig_organ_graph(edge_json):
    E = json.load(open(edge_json))
    edges = E["edges"]; gate_mean = E["gate_mean"]; gate_cv = E["gate_cv"]
    fig, ax = plt.subplots(figsize=(6.2, 6.0)); ax.axis("off")
    ax.set_xlim(-1.7, 1.7); ax.set_ylim(-1.5, 1.6)
    gmax = max(gate_mean) + 1e-6
    for (s, t), gm, cv in zip(edges, gate_mean, gate_cv):
        x0, y0 = ORGAN_POS[s]; x1, y1 = ORGAN_POS[t]
        stab = max(0.15, 1.0 - min(cv, 1.0))            # stability shading
        lw = 1.0 + 6.0 * gm / gmax
        arr = FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>",
                              mutation_scale=16, lw=lw, color=BLUE, alpha=stab,
                              shrinkA=22, shrinkB=22, connectionstyle="arc3,rad=0.08")
        ax.add_patch(arr)
    for i, (x, y) in ORGAN_POS.items():
        ax.add_patch(Circle((x, y), 0.18, facecolor="white", edgecolor="black", lw=1.6, zorder=5))
        ax.text(x, y, str(i + 1), ha="center", va="center", fontsize=15, fontweight="bold", zorder=6)
    # legend mapping numbers -> organs (text outside the graph area)
    for i in range(4):
        ax.text(-1.65, 1.5 - 0.16 * i, f"({i+1}) {ORGAN_ABBR[i]}", fontsize=10, va="top")
    ax.text(0.0, -1.42, "edge width ∝ coupling strength   ·   opacity ∝ bootstrap stability",
            ha="center", fontsize=9, color=GREY)
    return _save(fig, "exp2", "learned_organ_graph.png")


def fig_tradeoff():
    """Multi-objective: external accuracy vs. cross-cohort robustness (exact seed means)."""
    sp = FIGROOT.parent / "forecast_seed_stats.json"
    if not sp.exists():
        return
    agg = json.load(open(sp))["aggregate"]
    names = [n for n in agg if n not in ("ncde", "persistence")]
    fig, ax = plt.subplots(figsize=(6.6, 4.4))
    for n in names:
        x, y = agg[n]["B_mean"], agg[n]["degr_mean"]
        pg = n.startswith("physiograph")
        c = BLUE if pg else (GREEN if n in ("gru", "grud") else GREY)
        ax.scatter(x, y, s=170, c=c, edgecolor="black", zorder=3, alpha=0.85)
        lab = n.replace("physiograph_gru", "PG-GRU").replace("physiograph", "PG-SSM")
        ax.annotate(lab, (x, y), fontsize=8, xytext=(0, 9), textcoords="offset points", ha="center")
    ax.invert_xaxis()
    ax.set_xlabel("External RMSE@12  (better →)")
    ax.set_ylabel("Cross-cohort drop %  (↓ better)")
    ax.set_title("Robustness vs. accuracy: PhysioGraph trades accuracy for relative robustness")
    return _save(fig, "exp4", "tradeoff.png")


def compute_edge_stability(ckpt, npz, C=12, K=12, gpu=1, n_boot=20, out=None):
    """Load a trained PhysioGraph, compute per-edge gate mean + bootstrap CV on A-test."""
    import torch
    from physiograph_data_loader import make_loaders
    from organ_graph_ssm_model import build_model, ADMISSIBLE_EDGES
    device = torch.device(f"cuda:{gpu}" if torch.cuda.is_available() else "cpu")
    _, _, testA, _, meta = make_loaders(npz, C, K, batch_size=256)
    model = build_model("cinc", d_model=96, d_state=48, n_layers=2).to(device)
    model.load_state_dict(torch.load(ckpt, map_location=device)); model.eval()
    gates = []
    with torch.no_grad():
        for b in testA:
            b = {k: (v.to(device) if hasattr(v, "to") else v) for k, v in b.items()}
            g = model.edge_gates(b["values"], b["mask"], b["static"])   # (B,E)
            gates.append(g.cpu().numpy())
    G = np.concatenate(gates)                          # (N,E)
    mean = G.mean(0)
    rng = np.random.default_rng(0)
    boot = np.stack([G[rng.integers(0, len(G), len(G))].mean(0) for _ in range(n_boot)])
    cv = (boot.std(0) / (mean + 1e-6))
    res = dict(edges=[list(e) for e in ADMISSIBLE_EDGES],
               gate_mean=[float(x) for x in mean], gate_cv=[float(x) for x in cv])
    if out:
        json.dump(res, open(out, "w"), indent=2); print(f"[fig] wrote {out}")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--which", default="all")
    ap.add_argument("--forecast_json", default=str(REPO_ROOT / "result/cinc_forecasting.json"))
    ap.add_argument("--cf_json", default=str(REPO_ROOT / "result/cvsim_counterfactual.json"))
    ap.add_argument("--edge_json", default=str(REPO_ROOT / "result/edge_stability.json"))
    ap.add_argument("--K", type=int, default=12)
    a = ap.parse_args()
    if a.which in ("all", "forecast") and Path(a.forecast_json).exists():
        fig_forecasting(a.forecast_json, a.K)
    if a.which in ("all", "cf") and Path(a.cf_json).exists():
        fig_counterfactual(a.cf_json)
    if a.which in ("all", "graph") and Path(a.edge_json).exists():
        fig_organ_graph(a.edge_json)
    if a.which in ("all", "tradeoff"):
        fig_tradeoff()


if __name__ == "__main__":
    main()
