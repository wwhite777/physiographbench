#!/usr/bin/env python3
"""Render measured coupling matrices and optional simulator diagnostics.

Titles identify the statistic and split; they make no scientific conclusion.
"""
from __future__ import annotations

# Resolve all public modules and scratch from the release root.
import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[1]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH

import argparse
import json
import os
from pathlib import Path

ROOT = RELEASE_ROOT
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".engineering-tmp/coupling_index-coupling-index-build/matplotlib"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=ROOT / "coupling_index.json")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "figures")
    a = ap.parse_args()
    out = a.out_dir.resolve()
    if not out.is_relative_to(ROOT):
        raise ValueError("figure outputs must remain inside this task directory")
    out.mkdir(parents=True, exist_ok=True)
    with a.input.open() as f:
        d = json.load(f)
    if "cinc2019" in d["datasets"]:
        cinc = d["datasets"]["cinc2019"]
        probes = [p for p in ("ridge", "gru") if p in cinc["probes"]]
        panels = [(probe, split) for probe in probes for split in ("A_val", "B")]
        arrays = [np.asarray(cinc["probes"][p]["splits"][s]["matrix"]["value"], dtype=float)
                  for p, s in panels]
        limit = max(.01, max(np.nanmax(np.abs(v)) for v in arrays))
        fig, axes = plt.subplots(len(probes), 2, figsize=(12.2, 5 * len(probes)), squeeze=False,
                                 layout="constrained")
        labels = [o.capitalize() for o in cinc["organs"]]
        for ax, (probe, split), values in zip(axes.flat, panels, arrays):
            cell = cinc["probes"][probe]["splits"][split]
            im = ax.imshow(values, cmap="RdBu_r", vmin=-limit, vmax=limit)
            ax.set_xticks(range(len(labels)), labels, rotation=25, ha="right")
            ax.set_yticks(range(len(labels)), labels)
            ax.set_xlabel("Target organ"); ax.set_ylabel("Source organ")
            den = cell["matrix"]["denominator"]
            ax.set_title(f"CinC-2019 · {probe.upper()} · {split.replace('_', '-')}\n"
                         f"{den['stays_available']:,} eligible stays; {den['resamples_requested']:,} bootstrap resamples")
            lo, hi = cell["matrix"]["lower_95"], cell["matrix"]["upper_95"]
            for i in range(len(labels)):
                for j in range(len(labels)):
                    if np.isfinite(values[i, j]):
                        text = f"{values[i, j]:.3f}\n[{lo[i][j]:.3f}, {hi[i][j]:.3f}]"
                        color = "white" if abs(values[i, j]) > .6 * limit else "black"
                    else:
                        text, color = "undefined", "black"
                    ax.text(j, i, text, ha="center", va="center", fontsize=8, color=color)
        fig.colorbar(im, ax=axes, label="Predictive coupling index (95% stay-bootstrap intervals in cells)", shrink=.65)
        for suffix in ("png", "pdf"):
            fig.savefig(out / f"cinc_coupling_matrices.{suffix}", dpi=180)
        plt.close(fig)
    curve = d.get("simulator_diagnostic_curve", {})
    if curve:
        entries = sorted(curve.values(), key=lambda v: v["kappa"])
        fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), layout="constrained")
        for ax, probe in zip(axes, ("ridge", "gru")):
            for split, marker in (("A_val", "o"), ("B", "s")):
                rows = [e for e in entries if probe in e["probes"]]
                if not rows:
                    continue
                x = np.asarray([e["kappa"] for e in rows])
                stats = [e["probes"][probe][split] for e in rows]
                y = np.asarray([v["value"] for v in stats], float)
                lo = np.asarray([v["lower_95"] for v in stats], float)
                hi = np.asarray([v["upper_95"] for v in stats], float)
                # Percentile intervals need not contain their point estimate.
                n_stays = stats[0]["denominator"]["stays_available"]
                split_label = "Validation" if split == "A_val" else "Holdout"
                ax.plot(x, y, marker=marker, label=f"{split_label} ({n_stays} stays)")
                ax.fill_between(x, lo, hi, alpha=.18)
            ax.set_title(f"Simulator · {probe.upper()}\n12 samples of history; next 5-minute sample")
            ax.set_xlabel("Simulator κ"); ax.set_ylabel("Mean off-diagonal predictive coupling index")
            ax.set_xlim(-.025, 1.025)
            ax.set_xticks([0, .1, .25, .5, .75, 1])
            ax.axhline(0, color="gray", lw=.7)
            ax.legend(); ax.grid(alpha=.2)
        fig.supxlabel("Three organs; same-simulator patient holdouts; shading: 95% stay-bootstrap intervals (1,000 resamples).\n"
                      "At κ=0 urine output is constant; the ridge mean is undefined and GRU ratios describe residual fitting error.\n"
                      "Sampling differs from the hourly CinC calculation.", fontsize=9)
        for suffix in ("png", "pdf"):
            fig.savefig(out / f"simulator_diagnostic_curve.{suffix}", dpi=180)
        plt.close(fig)
    print(f"figures saved to {out}")


if __name__ == "__main__":
    main()
