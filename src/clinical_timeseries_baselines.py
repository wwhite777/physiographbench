"""clinical_timeseries_baselines — comparison models for CinC trajectory forecasting.

Four families, all exposing the same ``rollout(batch, horizon) -> (B,K,F)`` API as
PhysioGraph so the runner is model-agnostic:
  * clinical time-series : GRU, GRU-D (Che et al. decay)
  * irregular time-series: Neural CDE (torchcde), ODE-RNN (torchdiffeq, rk4)
  * temporal graph       : GraphGRU (learned feature-graph attention + GRU)
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

try:
    import torchcde
    HAVE_CDE = True
except Exception:
    HAVE_CDE = False
try:
    from torchdiffeq import odeint
    HAVE_ODE = True
except Exception:
    HAVE_ODE = False


class _ARDecoder(nn.Module):
    """Shared autoregressive decoder: GRUCell seeded by an encoder hidden state."""

    def __init__(self, n_feat, n_static, d_hidden):
        super().__init__()
        self.cell = nn.GRUCell(n_feat + n_static, d_hidden)
        self.out = nn.Linear(d_hidden, n_feat)

    def rollout(self, h0, static, y0, horizon):
        h = h0; y = y0
        preds = []
        for _ in range(horizon):
            h = self.cell(torch.cat([y, static], -1), h)
            y = self.out(h)
            preds.append(y)
        return torch.stack(preds, 1)


def _enc_input(batch):
    """[values*mask, mask, static_broadcast] -> (B,T,2F+S)."""
    v, m, s = batch["values"], batch["mask"], batch["static"]
    B, T, Fdim = v.shape
    return torch.cat([v * m, m, s.unsqueeze(1).expand(B, T, -1)], -1), Fdim, s.shape[-1]


class GRUForecaster(nn.Module):
    def __init__(self, n_feat, n_static, d_hidden=128, **kw):
        super().__init__()
        self.gru = nn.GRU(2 * n_feat + n_static, d_hidden, batch_first=True)
        self.dec = _ARDecoder(n_feat, n_static, d_hidden)

    def rollout(self, batch, horizon):
        x, Fdim, _ = _enc_input(batch)
        _, h = self.gru(x)
        return self.dec.rollout(h[-1], batch["static"], batch["values"][:, -1], horizon)

    def forward(self, batch, horizon=12):
        return self.rollout(batch, horizon)


class GRUD(nn.Module):
    """GRU-D: input + hidden exponential decay toward empirical mean on missingness."""

    def __init__(self, n_feat, n_static, d_hidden=128, **kw):
        super().__init__()
        self.Fdim = n_feat
        self.g_x = nn.Linear(n_feat, n_feat)
        self.g_h = nn.Linear(n_feat, d_hidden)
        self.cell = nn.GRUCell(2 * n_feat + n_static, d_hidden)
        self.dec = _ARDecoder(n_feat, n_static, d_hidden)
        self.d_hidden = d_hidden

    def rollout(self, batch, horizon):
        v, m, s = batch["values"], batch["mask"], batch["static"]
        B, T, Fd = v.shape
        h = v.new_zeros(B, self.d_hidden)
        last = v[:, 0].clone()
        delta = torch.zeros_like(v[:, 0])
        for t in range(T):
            mt = m[:, t]; xt = v[:, t]
            delta = torch.where(mt > 0, torch.zeros_like(delta), delta + 1.0)
            gamma_x = torch.exp(-F.relu(self.g_x(delta)))
            gamma_h = torch.exp(-F.relu(self.g_h(delta)))
            last = torch.where(mt > 0, xt, last)
            x_hat = mt * xt + (1 - mt) * (gamma_x * last)
            h = gamma_h * h
            h = self.cell(torch.cat([x_hat, mt, s], -1), h)
        return self.dec.rollout(h, s, v[:, -1], horizon)

    def forward(self, batch, horizon=12):
        return self.rollout(batch, horizon)


class NeuralCDEForecaster(nn.Module):
    """Neural Controlled Differential Equation encoder (torchcde) + AR decoder."""

    def __init__(self, n_feat, n_static, d_hidden=96, **kw):
        super().__init__()
        self.ch = 1 + 2 * n_feat                     # time + values + mask channels
        self.z0 = nn.Linear(self.ch, d_hidden)
        self.func = _CDEFunc(d_hidden, self.ch)
        self.dec = _ARDecoder(n_feat, n_static, d_hidden)
        self.d_hidden = d_hidden

    def rollout(self, batch, horizon):
        v, m, s = batch["values"], batch["mask"], batch["static"]
        B, T, Fd = v.shape
        tt = torch.linspace(0, 1, T, device=v.device).unsqueeze(0).expand(B, T).unsqueeze(-1)
        path = torch.cat([tt, v * m, m], -1)         # (B,T,ch)
        coeffs = torchcde.natural_cubic_coeffs(path)
        X = torchcde.CubicSpline(coeffs)
        z0 = self.z0(X.evaluate(X.interval[0]))
        zt = torchcde.cdeint(X=X, func=self.func, z0=z0, t=X.interval,
                             method="rk4", options={"step_size": 1.0 / max(T - 1, 1)})
        h = zt[:, -1]
        return self.dec.rollout(h, s, v[:, -1], horizon)

    def forward(self, batch, horizon=12):
        return self.rollout(batch, horizon)


class _CDEFunc(nn.Module):
    def __init__(self, d_hidden, ch):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(d_hidden, d_hidden), nn.Tanh(),
                                 nn.Linear(d_hidden, d_hidden * ch))
        self.d_hidden, self.ch = d_hidden, ch

    def forward(self, t, z):
        return self.net(z).view(z.shape[0], self.d_hidden, self.ch)


class ODERNNForecaster(nn.Module):
    """ODE-RNN: ODE flow of the hidden state between steps + GRU update at obs."""

    def __init__(self, n_feat, n_static, d_hidden=96, **kw):
        super().__init__()
        self.flow = nn.Sequential(nn.Linear(d_hidden, d_hidden), nn.Tanh(),
                                  nn.Linear(d_hidden, d_hidden))
        self.cell = nn.GRUCell(2 * n_feat + n_static, d_hidden)
        self.dec = _ARDecoder(n_feat, n_static, d_hidden)
        self.d_hidden = d_hidden

    def _ode(self, t, h):
        return self.flow(h)

    def rollout(self, batch, horizon):
        v, m, s = batch["values"], batch["mask"], batch["static"]
        B, T, Fd = v.shape
        h = v.new_zeros(B, self.d_hidden)
        tspan = torch.tensor([0.0, 1.0], device=v.device)
        for t in range(T):
            if HAVE_ODE:
                h = odeint(self._ode, h, tspan, method="rk4")[-1]
            else:
                h = h + self.flow(h)
            h = self.cell(torch.cat([v[:, t] * m[:, t], m[:, t], s], -1), h)
        return self.dec.rollout(h, s, v[:, -1], horizon)

    def forward(self, batch, horizon=12):
        return self.rollout(batch, horizon)


class GraphGRUForecaster(nn.Module):
    """Temporal-graph baseline: learned attention over feature-nodes + GRU over time."""

    def __init__(self, n_feat, n_static, d_hidden=96, d_node=16, **kw):
        super().__init__()
        self.Fdim = n_feat; self.d_node = d_node
        self.embed = nn.Linear(2, d_node)            # [value, mask] per feature-node
        self.q = nn.Linear(d_node, d_node); self.k = nn.Linear(d_node, d_node)
        self.v_ = nn.Linear(d_node, d_node)
        self.gru = nn.GRU(n_feat * d_node + n_static, d_hidden, batch_first=True)
        self.dec = _ARDecoder(n_feat, n_static, d_hidden)

    def rollout(self, batch, horizon):
        v, m, s = batch["values"], batch["mask"], batch["static"]
        B, T, Fd = v.shape
        node = torch.stack([v, m], -1)               # (B,T,F,2)
        z = self.embed(node)                         # (B,T,F,dn)
        q, k, val = self.q(z), self.k(z), self.v_(z)
        att = torch.softmax(torch.einsum("btfd,btgd->btfg", q, k) / self.d_node ** 0.5, -1)
        z = z + torch.einsum("btfg,btgd->btfd", att, val)
        seq = torch.cat([z.reshape(B, T, -1), s.unsqueeze(1).expand(B, T, -1)], -1)
        _, h = self.gru(seq)
        return self.dec.rollout(h[-1], s, v[:, -1], horizon)

    def forward(self, batch, horizon=12):
        return self.rollout(batch, horizon)


REGISTRY = {
    "gru": GRUForecaster, "grud": GRUD, "ncde": NeuralCDEForecaster,
    "odernn": ODERNNForecaster, "graphgru": GraphGRUForecaster,
}


def build_baseline(name, n_feat=16, n_static=5, d_hidden=128):
    if name == "ncde" and not HAVE_CDE:
        raise RuntimeError("torchcde not available")
    return REGISTRY[name](n_feat=n_feat, n_static=n_static, d_hidden=d_hidden)


if __name__ == "__main__":
    B, C, Fd = 8, 12, 16
    batch = dict(values=torch.randn(B, C, Fd), mask=(torch.rand(B, C, Fd) > 0.4).float(),
                 static=torch.randn(B, 5))
    for name in REGISTRY:
        try:
            mdl = build_baseline(name)
            out = mdl(batch, horizon=12)
            n = sum(p.numel() for p in mdl.parameters()) / 1e6
            print(f"  {name:9s} ok  params={n:.2f}M  out={tuple(out.shape)}")
            assert out.shape == (B, 12, Fd)
        except Exception as e:
            print(f"  {name:9s} FAILED: {e}")
    print("[baselines] smoke test done")
