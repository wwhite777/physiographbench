"""physiograph_training_runner — train/eval forecasting models on the CinC cohort.

Model-agnostic: trains PhysioGraph or any baseline with masked-MSE multi-step
forecasting, then reports internal (A-test) and external (B) RMSE/MAE at 6 h and
12 h plus per-organ RMSE and the cross-cohort degradation that the paper headlines.
Everything is seeded; results + checkpoints are written under result/ and ckpt/.

Usage:
  python physiograph_training_runner.py --models physiograph,grud,ncde,gru --epochs 40
"""
from __future__ import annotations

# Resolve all public modules and scratch from the release root.
import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[1]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH

import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

from physiograph_data_loader import make_loaders, masked_metrics
from clinical_timeseries_baselines import build_baseline, REGISTRY
from organ_graph_ssm_model import build_model


def seed_all(s):
    np.random.seed(s); torch.manual_seed(s); torch.cuda.manual_seed_all(s)


def build_any(name, n_static, d_hidden, d_model, d_state, n_layers):
    if name == "physiograph":
        return build_model("cinc", d_model=d_model, d_state=d_state, n_layers=n_layers, node_type="ssm")
    if name == "physiograph_gru":
        return build_model("cinc", d_model=d_model, d_state=d_state, n_layers=n_layers, node_type="gru")
    if name == "gru_med":      # capacity-controlled GRU (~0.7M, matches PhysioGraph scale)
        return build_baseline("gru", n_feat=16, n_static=n_static, d_hidden=320)
    if name == "gru_large":    # capacity-controlled GRU (~1.0M, exceeds PhysioGraph)
        return build_baseline("gru", n_feat=16, n_static=n_static, d_hidden=512)
    return build_baseline(name, n_feat=16, n_static=n_static, d_hidden=d_hidden)


def masked_mse(pred, target, tmask):
    n = tmask.sum().clamp(min=1)
    return ((pred - target) ** 2 * tmask).sum() / n


@torch.no_grad()
def persistence_eval(loader, K, organ_slices, organ_names):
    """Carry-forward last-observed value baseline (no training) — a sanity reference."""
    P, T, M = [], [], []
    for b in loader:
        v, m = b["values"], b["mask"]                    # (B,C,F)
        B, C, Fdim = v.shape
        last = torch.zeros(B, Fdim)
        for t in range(C):                               # carry forward last observed
            mt = m[:, t]; last = torch.where(mt > 0, v[:, t], last)
        pred = last.unsqueeze(1).expand(B, K, Fdim)
        P.append(pred); T.append(b["target"]); M.append(b["target_mask"])
    P, T, M = torch.cat(P), torch.cat(T), torch.cat(M)
    return masked_metrics(P, T, M, horizons=(6, K), organ_slices=organ_slices,
                          organ_names=organ_names)


@torch.no_grad()
def evaluate(model, loader, device, K, organ_slices, organ_names):
    model.eval()
    P, T, M = [], [], []
    for b in loader:
        b = {k: (v.to(device) if torch.is_tensor(v) else v) for k, v in b.items()}
        pred = model(b, horizon=K)
        P.append(pred.cpu()); T.append(b["target"].cpu()); M.append(b["target_mask"].cpu())
    P, T, M = torch.cat(P), torch.cat(T), torch.cat(M)
    return masked_metrics(P, T, M, horizons=(6, K), organ_slices=organ_slices,
                          organ_names=organ_names)


def train_one(name, loaders, meta, device, epochs, lr, sizes, seed, ckpt_dir):
    seed_all(seed)
    train_dl, val_dl, testA_dl, testB_dl = loaders
    K = meta["K"]; organ_slices = meta["organ_slices"]; organ_names = meta["organ_names"]
    model = build_any(name, len(meta["mean"]) and 5, **sizes).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, epochs)

    best_val = float("inf"); best_state = None; patience = 0
    for ep in range(epochs):
        model.train(); tot = 0.0; nb = 0
        for b in train_dl:
            b = {k: (v.to(device) if torch.is_tensor(v) else v) for k, v in b.items()}
            opt.zero_grad()
            pred = model(b, horizon=K)
            loss = masked_mse(pred, b["target"], b["target_mask"])
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step(); tot += float(loss); nb += 1
        sched.step()
        val = evaluate(model, val_dl, device, K, organ_slices, organ_names)[f"RMSE@{K}"]
        if val < best_val - 1e-4:
            best_val = val; best_state = {k: v.detach().cpu().clone()
                                          for k, v in model.state_dict().items()}; patience = 0
        else:
            patience += 1
        if ep % 5 == 0 or ep == epochs - 1:
            print(f"    [{name}] epoch {ep:3d} train_mse {tot/nb:.4f} val_RMSE@{K} {val:.4f} "
                  f"best {best_val:.4f}", flush=True)
        if patience >= 8:
            print(f"    [{name}] early stop @ epoch {ep}"); break

    if best_state:
        model.load_state_dict(best_state)
    Path(ckpt_dir).mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), Path(ckpt_dir) / f"{name}.pt")
    a = evaluate(model, testA_dl, device, K, organ_slices, organ_names)
    b = evaluate(model, testB_dl, device, K, organ_slices, organ_names)
    degr = (b[f"RMSE@{K}"] - a[f"RMSE@{K}"]) / a[f"RMSE@{K}"] * 100
    return dict(model=name, n_params=int(n_params), val_RMSE=best_val,
                A_test=a, B_external=b, degradation_pct=float(degr))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz", default=str(RELEASE_ROOT / 'data/cinc2019_cohort.npz'))
    ap.add_argument("--models", default="physiograph,grud,ncde,odernn,graphgru,gru")
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--C", type=int, default=12); ap.add_argument("--K", type=int, default=12)
    ap.add_argument("--batch", type=int, default=128); ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--gpu", type=int, default=1)
    ap.add_argument("--d_hidden", type=int, default=128)
    ap.add_argument("--d_model", type=int, default=96); ap.add_argument("--d_state", type=int, default=48)
    ap.add_argument("--n_layers", type=int, default=2); ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--train_frac", type=float, default=1.0)
    ap.add_argument("--out", default=str(RELEASE_ROOT / 'results/legacy/cinc_forecasting.json'))
    args = ap.parse_args()

    device = torch.device(f"cuda:{args.gpu}" if torch.cuda.is_available() else "cpu")
    print(f"[run] device={device} train_frac={args.train_frac}")
    train_dl, val_dl, testA_dl, testB_dl, meta = make_loaders(
        args.npz, args.C, args.K, args.batch, num_workers=4, train_frac=args.train_frac)
    print(f"[run] windows train/val/A-test/B-ext = "
          f"{meta['n_train']}/{meta['n_val']}/{meta['n_testA']}/{meta['n_testB']} "
          f"(C={args.C},K={args.K})")
    sizes = dict(d_hidden=args.d_hidden, d_model=args.d_model,
                 d_state=args.d_state, n_layers=args.n_layers)
    results = {}
    # persistence reference (no training)
    pa = persistence_eval(testA_dl, args.K, meta["organ_slices"], meta["organ_names"])
    pb = persistence_eval(testB_dl, args.K, meta["organ_slices"], meta["organ_names"])
    results["persistence"] = dict(model="persistence", n_params=0, A_test=pa, B_external=pb,
                                  degradation_pct=float((pb[f"RMSE@{args.K}"] - pa[f"RMSE@{args.K}"])
                                                        / pa[f"RMSE@{args.K}"] * 100))
    print(f"[run] persistence: A RMSE@{args.K}={pa[f'RMSE@{args.K}']:.4f} "
          f"B={pb[f'RMSE@{args.K}']:.4f}")
    for name in args.models.split(","):
        name = name.strip()
        if name not in ("physiograph", "physiograph_gru", "gru_med", "gru_large") and name not in REGISTRY:
            print(f"[run] skip unknown {name}"); continue
        t0 = time.time()
        print(f"[run] === training {name} ===", flush=True)
        try:
            r = train_one(name, (train_dl, val_dl, testA_dl, testB_dl), meta, device,
                          args.epochs, args.lr, sizes, args.seed, str(RELEASE_ROOT / 'runs/checkpoints'))
            r["train_seconds"] = round(time.time() - t0, 1)
            results[name] = r
            print(f"[run] {name}: A RMSE@{args.K}={r['A_test'][f'RMSE@{args.K}']:.4f} "
                  f"B={r['B_external'][f'RMSE@{args.K}']:.4f} degr={r['degradation_pct']:.1f}% "
                  f"({r['train_seconds']}s, {r['n_params']/1e6:.2f}M)", flush=True)
        except Exception as e:
            print(f"[run] {name} FAILED: {e}")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump({"config": vars(args), "results": results}, open(args.out, "w"), indent=2)
    print(f"[run] wrote {args.out}")
    # quick leaderboard
    if results:
        print("\n  model         params   A-RMSE@%d  B-RMSE@%d  degr%%" % (args.K, args.K))
        for n, r in sorted(results.items(), key=lambda kv: kv[1]["A_test"][f"RMSE@{args.K}"]):
            print(f"  {n:12s} {r['n_params']/1e6:5.2f}M   "
                  f"{r['A_test'][f'RMSE@{args.K}']:.4f}    {r['B_external'][f'RMSE@{args.K}']:.4f}   "
                  f"{r['degradation_pct']:5.1f}")


if __name__ == "__main__":
    main()
