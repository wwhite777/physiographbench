"""cvsim_counterfactual_runner — counterfactual validity under hidden confounding.

Trains on FACTUAL CVSim trajectories (a vasopressor policy confounded by latent
sepsis severity) and evaluates whether a model can predict the response to an
*alternative* constant dose -- the held-out ground-truth counterfactual the
simulator provides. Sepsis severity is never given to the model, so this is a
genuine confounded counterfactual problem (Theorem 2's setting).

Compares PhysioGraph's control-driven g-computation rollout against a plain
control-aware GRU (no confounding adjustment). Saves per-dose counterfactual RMSE
and the predicted-vs-true MAP dose-response arrays for the figure.
"""
from __future__ import annotations

import os
import argparse
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

from organ_graph_ssm_model import PhysioGraph, PhysioGraphConfig

# Repository root. Defaults to the parent of src/; override with the
# PHYSIOGRAPH_ROOT environment variable to relocate data/result trees.
REPO_ROOT = Path(os.environ.get("PHYSIOGRAPH_ROOT", Path(__file__).resolve().parents[1]))

OBS = ["MAP", "HR", "CO", "CVP", "UO", "Lac"]
# organ grouping of observables for per-organ counterfactual error
ORGAN_CHANNELS = {"cardiovascular": [0, 1, 2, 3], "renal": [4], "metabolic": [5]}


class ControlGRU(nn.Module):
    """Control-aware GRU: encodes (obs,control) context, decodes given future control."""

    def __init__(self, n_obs=4, n_ctrl=1, d=96):
        super().__init__()
        self.enc = nn.GRU(n_obs + n_ctrl, d, batch_first=True)
        self.cell = nn.GRUCell(n_obs + n_ctrl, d)
        self.out = nn.Linear(d, n_obs)

    def rollout(self, batch, horizon):
        v, cc, cf = batch["values"], batch["control_ctx"], batch["control_future"]
        _, h = self.enc(torch.cat([v, cc], -1)); h = h[-1]
        y = v[:, -1]; preds = []
        for k in range(horizon):
            h = self.cell(torch.cat([y, cf[:, k]], -1), h)
            y = self.out(h); preds.append(y)
        return torch.stack(preds, 1)

    def forward(self, batch, horizon):
        return self.rollout(batch, horizon)


class _GradReverse(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x, lamb):
        ctx.lamb = lamb
        return x.view_as(x)

    @staticmethod
    def backward(ctx, g):
        return -ctx.lamb * g, None


def grad_reverse(x, lamb=1.0):
    return _GradReverse.apply(x, lamb)


class CRNLite(nn.Module):
    """Counterfactual Recurrent Network (lite): a GRU encoder made treatment-invariant
    by an adversarial gradient-reversal head that tries to predict the (confounded)
    treatment from the representation. Balancing the representation removes the
    treatment-policy signal, which is the mechanism CRN/RMSN use to deconfound."""

    def __init__(self, n_obs=6, n_ctrl=1, d=96, lamb=0.5):
        super().__init__()
        self.enc = nn.GRU(n_obs + n_ctrl, d, batch_first=True)
        self.cell = nn.GRUCell(n_obs + n_ctrl, d)
        self.out = nn.Linear(d, n_obs)
        self.treat_head = nn.Sequential(nn.Linear(d, d), nn.ReLU(), nn.Linear(d, 1))
        self.lamb = lamb
        self._h = None

    def rollout(self, batch, horizon):
        v, cc, cf = batch["values"], batch["control_ctx"], batch["control_future"]
        _, h = self.enc(torch.cat([v, cc], -1)); h = h[-1]
        self._h = h                                   # stash balanced rep for aux_loss
        y = v[:, -1]; preds = []
        for k in range(horizon):
            h = self.cell(torch.cat([y, cf[:, k]], -1), h)
            y = self.out(h); preds.append(y)
        return torch.stack(preds, 1)

    def aux_loss(self, batch):
        """Adversarial balancing: encoder is pushed to NOT encode the treatment policy."""
        treat = batch["control_ctx"].mean(1)          # (B,1) factual dose proxy
        pred_t = self.treat_head(grad_reverse(self._h, self.lamb))
        return 0.5 * ((pred_t - treat) ** 2).mean()

    def forward(self, batch, horizon):
        return self.rollout(batch, horizon)


def build_pg(d_model=64, d_state=32, n_layers=2, node_type="ssm"):
    # 3 organs: cardiovascular (MAP,HR,CO,CVP), renal (UO), metabolic (Lac);
    # admissible edges carry the intervention effect cardio -> renal, cardio -> metabolic
    cfg = PhysioGraphConfig(organ_dims=(4, 1, 1), n_static=1, n_control=1,
                            edges=((0, 1), (0, 2)),
                            d_model=d_model, d_state=d_state, n_layers=n_layers, node_type=node_type)
    return PhysioGraph(cfg)


def load_cvsim(path, C, seed=0):
    d = np.load(path, allow_pickle=True)
    fac = d["factual"].astype(np.float32)         # (N,T,8) MAP,HR,CO,CVP,UO,Lac,vaso,sepsis
    cf = d["counterfactual"].astype(np.float32)   # (N,D,T,6)
    doses = d["cf_doses"].astype(np.float32)
    obs = fac[..., :6]; vaso = fac[..., 6:7]
    # normalise observables with train stats
    rng = np.random.default_rng(seed); N = obs.shape[0]
    perm = rng.permutation(N); ntr = int(0.7 * N)
    tr, te = perm[:ntr], perm[ntr:]
    mean = obs[tr].reshape(-1, 6).mean(0); std = obs[tr].reshape(-1, 6).std(0) + 1e-6
    return dict(obs=obs, vaso=vaso, cf=cf, doses=doses, mean=mean, std=std,
                tr=tr, te=te, T=obs.shape[1])


def _norm(x, m, s):
    return (x - m) / s


def make_batches(D, idx, C, K, device, bs=128):
    obs = _norm(D["obs"], D["mean"], D["std"]); vaso = D["vaso"]
    out = []
    for i in range(0, len(idx), bs):
        j = idx[i:i + bs]
        cv = torch.tensor(obs[j, :C], device=device)
        out.append(dict(
            values=cv, mask=torch.ones_like(cv),
            control_ctx=torch.tensor(vaso[j, :C], device=device),
            control_future=torch.tensor(vaso[j, C:C + K], device=device),
            target=torch.tensor(obs[j, C:C + K], device=device),
            static=torch.zeros(len(j), 1, device=device)))
    return out


def train(model, D, C, K, device, epochs, lr):
    model.to(device); opt = torch.optim.Adam(model.parameters(), lr=lr)
    for ep in range(epochs):
        model.train(); batches = make_batches(D, D["tr"], C, K, device)
        tot = 0
        for b in batches:
            opt.zero_grad()
            pred = model(b, K)
            loss = ((pred - b["target"]) ** 2).mean()
            if hasattr(model, "aux_loss"):            # CRN-lite adversarial balancing
                loss = loss + model.aux_loss(b)
            loss.backward(); nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step(); tot += float(loss)
        if ep % 5 == 0 or ep == epochs - 1:
            print(f"    epoch {ep:3d} factual_mse {tot/len(batches):.4f}", flush=True)
    return model


@torch.no_grad()
def eval_counterfactual(model, D, C, K, device):
    """For each test patient and dose, rollout under constant dose; compare to truth."""
    model.eval()
    obs = _norm(D["obs"], D["mean"], D["std"]); cf = D["cf"]; doses = D["doses"]
    te = D["te"]; mean, std = D["mean"], D["std"]
    per_dose_rmse = []
    chan = {c: {"pred": [], "true": []} for c in ("MAP", "UO", "Lac")}
    organ_se = {o: [0.0, 0] for o in ORGAN_CHANNELS}     # sum-sq-err, count per organ
    for di, dose in enumerate(doses):
        P, Tt = [], []
        for i in range(0, len(te), 128):
            j = te[i:i + 128]
            cv = torch.tensor(obs[j, :C], device=device)
            b = dict(values=cv, mask=torch.ones_like(cv),
                     control_ctx=torch.tensor(D["vaso"][j, :C], device=device),
                     control_future=torch.full((len(j), K, 1), float(dose), device=device),
                     static=torch.zeros(len(j), 1, device=device))
            pred = model(b, K).cpu().numpy() * std + mean   # denormalise
            truth = cf[j, di, C:C + K, :]
            P.append(pred); Tt.append(truth)
        P = np.concatenate(P); Tt = np.concatenate(Tt)
        per_dose_rmse.append(float(np.sqrt(((P - Tt) ** 2).mean())))
        for c, idx in (("MAP", 0), ("UO", 4), ("Lac", 5)):
            chan[c]["pred"].append(float(P[..., idx].mean()))
            chan[c]["true"].append(float(Tt[..., idx].mean()))
        for o, idxs in ORGAN_CHANNELS.items():
            organ_se[o][0] += float(((P[..., idxs] - Tt[..., idxs]) ** 2).sum())
            organ_se[o][1] += P[..., idxs].size
    organ_rmse = {o: float(np.sqrt(se / max(n, 1))) for o, (se, n) in organ_se.items()}
    # per-organ NRMSE (normalise by ground-truth range) -> fixes the scale-confounded "Overall"
    truth_te = cf[te]
    organ_range = {o: float(truth_te[..., idxs].max() - truth_te[..., idxs].min()) + 1e-6
                   for o, idxs in ORGAN_CHANNELS.items()}
    organ_nrmse = {o: organ_rmse[o] / organ_range[o] for o in ORGAN_CHANNELS}
    # directionality: does the predicted dose-response slope have the correct SIGN?
    sign_correct = {}
    for c in ("MAP", "UO", "Lac"):
        ps = chan[c]["pred"][-1] - chan[c]["pred"][0]
        ts = chan[c]["true"][-1] - chan[c]["true"][0]
        sign_correct[c] = bool(np.sign(ps) == np.sign(ts))
    return dict(doses=[float(x) for x in doses],
                per_dose_rmse=per_dose_rmse,
                overall_rmse=float(np.mean(per_dose_rmse)),
                organ_rmse=organ_rmse, organ_nrmse=organ_nrmse,
                macro_nrmse=float(np.mean(list(organ_nrmse.values()))),
                sign_correct=sign_correct,
                n_correct_signs=int(sum(sign_correct.values())),
                pred_map_by_dose=chan["MAP"]["pred"], true_map_by_dose=chan["MAP"]["true"],
                pred_uo_by_dose=chan["UO"]["pred"], true_uo_by_dose=chan["UO"]["true"],
                pred_lac_by_dose=chan["Lac"]["pred"], true_lac_by_dose=chan["Lac"]["true"])


@torch.no_grad()
def eval_factual_forecast(model, D, C, K, device):
    """H3: forecast the factual multi-organ trajectory; per-organ NRMSE (no confounding)."""
    model.eval()
    obs = _norm(D["obs"], D["mean"], D["std"]); te = D["te"]; mean, std = D["mean"], D["std"]
    P, T = [], []
    for i in range(0, len(te), 128):
        j = te[i:i + 128]
        cv = torch.tensor(obs[j, :C], device=device)
        b = dict(values=cv, mask=torch.ones_like(cv),
                 control_ctx=torch.tensor(D["vaso"][j, :C], device=device),
                 control_future=torch.tensor(D["vaso"][j, C:C + K], device=device),
                 static=torch.zeros(len(j), 1, device=device))
        P.append(model(b, K).cpu().numpy() * std + mean)
        T.append(D["obs"][j, C:C + K])
    P, T = np.concatenate(P), np.concatenate(T)
    organ_nrmse = {}
    for o, idxs in ORGAN_CHANNELS.items():
        rng_ = float(D["obs"][te][..., idxs].max() - D["obs"][te][..., idxs].min()) + 1e-6
        organ_nrmse[o] = float(np.sqrt(((P[..., idxs] - T[..., idxs]) ** 2).mean())) / rng_
    return dict(organ_nrmse=organ_nrmse, macro_nrmse=float(np.mean(list(organ_nrmse.values()))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz", default=str(REPO_ROOT / "data/cvsim_counterfactual.npz"))
    ap.add_argument("--C", type=int, default=12); ap.add_argument("--K", type=int, default=24)
    ap.add_argument("--epochs", type=int, default=60); ap.add_argument("--lr", type=float, default=2e-3)
    ap.add_argument("--gpu", type=int, default=1); ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=str(REPO_ROOT / "result/cvsim_counterfactual.json"))
    ap.add_argument("--task", default="counterfactual", choices=["counterfactual", "forecast"])
    args = ap.parse_args()
    device = torch.device(f"cuda:{args.gpu}" if torch.cuda.is_available() else "cpu")
    torch.manual_seed(args.seed); np.random.seed(args.seed)
    D = load_cvsim(args.npz, args.C, args.seed)
    print(f"[cf] task={args.task} {D['obs'].shape[0]} patients, T={D['T']}, device={device}")

    if args.task == "forecast":         # H3: organ-graph vs unstructured, factual forecasting
        specs = [("physiograph_gru", lambda: build_pg(node_type="gru")),
                 ("control_gru", lambda: ControlGRU(n_obs=6))]
    else:
        specs = [("physiograph", lambda: build_pg()),
                 ("physiograph_gru", lambda: build_pg(node_type="gru")),
                 ("control_gru", lambda: ControlGRU(n_obs=6)),
                 ("crn_lite", lambda: CRNLite(n_obs=6))]
    results = {}
    for name, mk in specs:
        print(f"[cf] === training {name} ===", flush=True)
        m = train(mk(), D, args.C, args.K, device, args.epochs, args.lr)
        if args.task == "forecast":
            r = eval_factual_forecast(m, D, args.C, args.K, device)
            print(f"[cf] {name}: forecast macroNRMSE={r['macro_nrmse']:.3f} "
                  f"(cardio={r['organ_nrmse']['cardiovascular']:.3f} "
                  f"renal={r['organ_nrmse']['renal']:.3f} metab={r['organ_nrmse']['metabolic']:.3f})", flush=True)
        else:
            r = eval_counterfactual(m, D, args.C, args.K, device)
            print(f"[cf] {name}: macroNRMSE={r['macro_nrmse']:.3f} overall={r['overall_rmse']:.3f} | "
                  f"correct_signs={r['n_correct_signs']}/3 {r['sign_correct']}", flush=True)
        r["n_params"] = int(sum(p.numel() for p in m.parameters()))
        results[name] = r
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump({"config": vars(args), "results": results}, open(args.out, "w"), indent=2)
    print(f"[cf] wrote {args.out}")


if __name__ == "__main__":
    main()
