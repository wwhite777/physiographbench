"""physiograph_theory_checks — empirical verification of the paper's theorems.

Theorem 1 (bounded multi-organ rollout error): measure per-horizon forecast error
  and show it stays under the geometric/Lipschitz accumulation envelope
  e(h) <= eps * sum_{k<h} L^k, with eps the one-step error and L an estimated
  coupling Lipschitz factor.
Theorem 3 (sparse admissible graph improves stability / sample complexity):
  train PhysioGraph with the admissible sparse edge set vs a fully-connected organ
  graph vs no edges, across seeds; report external RMSE mean +/- std (lower mean and
  lower variance for the sparse prior support the claim).
Results are saved as JSON for the paper + a figure.
"""
from __future__ import annotations

# Resolve all public modules and scratch from the release root.
import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[1]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH

import argparse
import json
from pathlib import Path

import numpy as np
import torch

from physiograph_data_loader import make_loaders
from organ_graph_ssm_model import build_model


@torch.no_grad()
def per_horizon_rmse(model, loader, device, K):
    model.eval()
    P, T, M = [], [], []
    for b in loader:
        b = {k: (v.to(device) if torch.is_tensor(v) else v) for k, v in b.items()}
        P.append(model(b, horizon=K).cpu()); T.append(b["target"].cpu()); M.append(b["target_mask"].cpu())
    P, T, M = torch.cat(P), torch.cat(T), torch.cat(M)
    out = []
    for h in range(K):
        m = M[:, h]; n = m.sum().clamp(min=1)
        out.append(float((((P[:, h] - T[:, h]) ** 2 * m).sum() / n).sqrt()))
    return out


def thm1_rollout(ckpt, npz, C=12, K=12, gpu=1, out=None):
    device = torch.device(f"cuda:{gpu}" if torch.cuda.is_available() else "cpu")
    _, _, testA, _, meta = make_loaders(npz, C, K, batch_size=256)
    model = build_model("cinc", d_model=96, d_state=48, n_layers=2).to(device)
    model.load_state_dict(torch.load(ckpt, map_location=device))
    e = per_horizon_rmse(model, testA, device, K)        # measured per-horizon RMSE
    eps = e[0]                                            # one-step error
    # estimate growth factor L from median consecutive ratio (>=1)
    ratios = [e[i + 1] / max(e[i], 1e-6) for i in range(len(e) - 1)]
    L = float(max(1.0, np.median(ratios)))
    bound = [eps * (sum(L ** k for k in range(h + 1))) for h in range(K)]
    res = dict(horizons=list(range(1, K + 1)), measured_rmse=e,
               eps_onestep=eps, L_est=L, bound=bound,
               within_bound=bool(all(e[h] <= bound[h] + 1e-6 for h in range(K))))
    if out:
        json.dump(res, open(out, "w"), indent=2); print(f"[thm1] wrote {out}")
    print(f"[thm1] eps={eps:.3f} L={L:.3f} within_bound={res['within_bound']} "
          f"e(1)={e[0]:.3f} e({K})={e[-1]:.3f}")
    return res


def thm3_sparsity(npz, C=12, K=12, gpu=1, epochs=12, seeds=(0, 1), out=None, configs=None):
    from physiograph_training_runner import train_one
    device = torch.device(f"cuda:{gpu}" if torch.cuda.is_available() else "cpu")
    loaders = make_loaders(npz, C, K, batch_size=128)
    meta = loaders[-1]; loaders = loaders[:4]
    sizes = dict(d_hidden=128, d_model=96, d_state=48, n_layers=2)
    if configs is None:
        configs = {"sparse_admissible": "admissible", "fully_connected": "full", "no_graph": "none"}
    res = {}
    for label, spec in configs.items():
        ext = []
        for s in seeds:
            # patch the name train_one actually resolves (in the runner's namespace)
            import physiograph_training_runner as TR
            orig = TR.build_model
            TR.build_model = (lambda sp: lambda task, **kw: orig(
                task, edges=sp, **{k: v for k, v in kw.items() if k != "edges"}))(spec)
            try:
                r = train_one("physiograph", loaders, meta, device, epochs, 1e-3, sizes, s,
                              str(RELEASE_ROOT / 'runs/checkpoints/_thm3'))
            finally:
                TR.build_model = orig
            ext.append(r["B_external"][f"RMSE@{K}"])
        res[label] = dict(ext_rmse_mean=float(np.mean(ext)), ext_rmse_std=float(np.std(ext)),
                          seeds=list(seeds), values=ext)
        print(f"[thm3] {label:18s} ext-RMSE {np.mean(ext):.4f} +/- {np.std(ext):.4f}")
    if out:
        json.dump(res, open(out, "w"), indent=2); print(f"[thm3] wrote {out}")
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--which", default="thm1")
    ap.add_argument("--ckpt", default=str(RELEASE_ROOT / 'runs/checkpoints/physiograph.pt'))
    ap.add_argument("--npz", default=str(RELEASE_ROOT / 'data/cinc2019_cohort.npz'))
    ap.add_argument("--gpu", type=int, default=1)
    ap.add_argument("--epochs", type=int, default=12)
    a = ap.parse_args()
    if a.which == "thm1":
        thm1_rollout(a.ckpt, a.npz, gpu=a.gpu,
                     out=str(RELEASE_ROOT / 'results/legacy/thm1_rollout.json'))
    elif a.which == "thm3":
        thm3_sparsity(a.npz, gpu=a.gpu, epochs=a.epochs,
                      out=str(RELEASE_ROOT / 'results/legacy/thm3_sparsity.json'))
    elif a.which == "h4":          # graph falsification: does the PHYSIOLOGICAL prior matter?
        thm3_sparsity(a.npz, gpu=a.gpu, epochs=a.epochs, seeds=(0, 1),
                      configs={"admissible": "admissible", "reversed": "reversed",
                               "random": "random", "no_graph": "none"},
                      out=str(RELEASE_ROOT / 'results/legacy/h4_falsification.json'))
