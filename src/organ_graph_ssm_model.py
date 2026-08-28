"""organ_graph_ssm_model — PhysioGraph: prior-constrained organ-graph state-space model.

Each organ system is a compact diagonal state-space (LRU-style linear recurrent)
node. Organ latent states exchange messages only along a physiologically
admissible sparse edge set, gated per-patient (a mixture-of-experts at the
organ-graph level, described generically for anonymity). Time-varying treatment
controls are injected into the latent dynamics, so the same model both forecasts
trajectories (controls=0) and rolls out interventional counterfactuals (controls
set to an alternative treatment plan) via free-running g-computation rollout.

Design notes
------------
* Diagonal SSM node (stable complex pole per state channel) — a Linear Recurrent
  Unit; runs as a sequential scan (sequence length <= ~48 here, so cheap).
* Admissible directed organ edges encode known physiology (e.g. cardiovascular ->
  renal perfusion). Non-admissible edges are masked to zero — the sparsity that
  Theorem 3 ties to sample complexity / stability.
* Counterfactual rollout: encode context, then step the recurrence forward K steps
  feeding predictions (and future controls) back in.
"""
from __future__ import annotations

from dataclasses import dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F

# Admissible directed organ edges (source -> target), physiologically motivated.
# Organ order: 0 cardiovascular, 1 pulmonary, 2 renal, 3 metabolic.
ADMISSIBLE_EDGES = [
    (0, 2),  # cardiovascular -> renal     (MAP drives renal perfusion / GFR)
    (0, 1),  # cardiovascular -> pulmonary (cardiac output <-> gas exchange)
    (0, 3),  # cardiovascular -> metabolic (perfusion -> lactate clearance)
    (1, 0),  # pulmonary -> cardiovascular (oxygenation -> cardiac function)
    (1, 3),  # pulmonary -> metabolic      (gas exchange -> acid-base)
    (3, 0),  # metabolic -> cardiovascular (glucose / lactate -> cardiac demand)
    (2, 3),  # renal -> metabolic          (clearance -> electrolytes / acid-base)
    (2, 0),  # renal -> cardiovascular     (volume / electrolytes -> cardiac)
]


@dataclass
class PhysioGraphConfig:
    organ_dims: tuple = (4, 4, 3, 5)   # features per organ (cardio,pulm,renal,metab)
    n_static: int = 5
    n_control: int = 0                 # 0 for CinC forecasting; >0 for CVSim counterfactual
    d_model: int = 64
    d_state: int = 32                  # SSM state channels per organ
    n_layers: int = 2
    edges: tuple = tuple(ADMISSIBLE_EDGES)
    dropout: float = 0.1
    node_type: str = "ssm"            # "ssm" (diagonal LRU) or "gru" (GRU-cell backbone)

    @property
    def n_organs(self):
        return len(self.organ_dims)

    @property
    def n_feat(self):
        return sum(self.organ_dims)


class LRUNode(nn.Module):
    """Diagonal complex linear-recurrent (state-space) node.

    x_k = lambda * x_{k-1} + B u_k ;  y_k = Re(C x_k) + D u_k
    lambda = exp(-exp(nu) + i*theta) is stable (|lambda| < 1) by construction.
    """

    def __init__(self, d_in, d_model, d_state, dropout=0.1):
        super().__init__()
        self.N = d_state
        # stable pole parameterisation
        self.nu = nn.Parameter(torch.log(torch.rand(d_state) * 0.9 + 0.05))
        self.theta = nn.Parameter(torch.rand(d_state) * 6.283)
        self.B_re = nn.Parameter(torch.randn(d_in, d_state) / d_in ** 0.5)
        self.B_im = nn.Parameter(torch.randn(d_in, d_state) / d_in ** 0.5)
        self.C_re = nn.Parameter(torch.randn(d_state, d_model) / d_state ** 0.5)
        self.C_im = nn.Parameter(torch.randn(d_state, d_model) / d_state ** 0.5)
        self.D = nn.Parameter(torch.randn(d_in, d_model) / d_in ** 0.5)
        self.norm = nn.LayerNorm(d_model)
        self.drop = nn.Dropout(dropout)
        # nonlinear position-wise mixing (the FFN that makes S4/S5/Mamba blocks expressive)
        self.ff = nn.Sequential(nn.Linear(d_model, 2 * d_model), nn.GELU(),
                                nn.Dropout(dropout), nn.Linear(2 * d_model, d_model))
        self.norm2 = nn.LayerNorm(d_model)

    def _lam(self):
        mag = torch.exp(-torch.exp(self.nu))            # in (0,1)
        return mag * torch.cos(self.theta), mag * torch.sin(self.theta)

    def step(self, u, state):
        """One recurrence step. u:(B,d_in), state:(xr,xi) each (B,N). Returns y,(xr,xi)."""
        lam_r, lam_i = self._lam()
        xr, xi = state
        br = u @ self.B_re; bi = u @ self.B_im
        nxr = lam_r * xr - lam_i * xi + br
        nxi = lam_r * xi + lam_i * xr + bi
        y = nxr @ self.C_re - nxi @ self.C_im + u @ self.D
        y = self.norm(self.drop(y))
        y = self.norm2(y + self.ff(y))               # nonlinear FFN with residual
        return y, (nxr, nxi)

    def forward(self, u_seq):
        """u_seq:(B,T,d_in) -> y_seq:(B,T,d_model), final_state."""
        B, T, _ = u_seq.shape
        xr = u_seq.new_zeros(B, self.N); xi = u_seq.new_zeros(B, self.N)
        ys = []
        for t in range(T):
            y, (xr, xi) = self.step(u_seq[:, t], (xr, xi))
            ys.append(y)
        return torch.stack(ys, 1), (xr, xi)

    def init_state(self, B, device):
        return (torch.zeros(B, self.N, device=device), torch.zeros(B, self.N, device=device))


class GRUNode(nn.Module):
    """GRU-cell organ node: a drop-in replacement for the diagonal-SSM node, used to
    test whether the organ-graph idea survives with a stronger short-sequence backbone.
    Same step/forward/init_state interface as LRUNode; state is the GRU hidden vector."""

    def __init__(self, d_in, d_model, d_state, dropout=0.1):
        super().__init__()
        self.cell = nn.GRUCell(d_in, d_model)
        self.norm = nn.LayerNorm(d_model)
        self.drop = nn.Dropout(dropout)
        self.ff = nn.Sequential(nn.Linear(d_model, 2 * d_model), nn.GELU(),
                                nn.Dropout(dropout), nn.Linear(2 * d_model, d_model))
        self.norm2 = nn.LayerNorm(d_model)
        self.d_model = d_model

    def step(self, u, state):
        h = self.cell(u, state)
        y = self.norm(self.drop(h))
        y = self.norm2(y + self.ff(y))
        return y, h

    def forward(self, u_seq):
        B, T, _ = u_seq.shape
        h = u_seq.new_zeros(B, self.d_model)
        ys = []
        for t in range(T):
            y, h = self.step(u_seq[:, t], h)
            ys.append(y)
        return torch.stack(ys, 1), h

    def init_state(self, B, device):
        return torch.zeros(B, self.d_model, device=device)


class OrganGraphCoupling(nn.Module):
    """Per-patient gated message passing along admissible organ edges."""

    def __init__(self, cfg: PhysioGraphConfig):
        super().__init__()
        self.cfg = cfg
        src = torch.tensor([e[0] for e in cfg.edges])
        dst = torch.tensor([e[1] for e in cfg.edges])
        self.register_buffer("src", src)
        self.register_buffer("dst", dst)
        self.msg = nn.ModuleList([nn.Linear(cfg.d_model, cfg.d_model) for _ in cfg.edges])
        # per-edge scalar gate from [h_src, h_dst] (the per-patient coupling activation)
        self.gate = nn.ModuleList([nn.Linear(2 * cfg.d_model, 1) for _ in cfg.edges])
        self.norm = nn.LayerNorm(cfg.d_model)

    def forward(self, H):
        """H:(B,O,d_model) -> updated (B,O,d_model). Returns also per-edge gate (B,E)."""
        B, O, d = H.shape
        if len(self.cfg.edges) == 0:                  # single-organ config: no coupling
            return H, H.new_zeros(B, 0)
        agg = torch.zeros_like(H)
        gates = []
        for e, (s, t) in enumerate(self.cfg.edges):
            hs, ht = H[:, s], H[:, t]
            g = torch.sigmoid(self.gate[e](torch.cat([hs, ht], -1)))   # (B,1)
            m = g * torch.tanh(self.msg[e](hs))
            agg[:, t] = agg[:, t] + m
            gates.append(g.squeeze(-1))
        H = self.norm(H + agg)
        return H, torch.stack(gates, -1)


class PhysioGraph(nn.Module):
    def __init__(self, cfg: PhysioGraphConfig):
        super().__init__()
        self.cfg = cfg
        self.slices = []
        o = 0
        for d in cfg.organ_dims:
            self.slices.append((o, o + d)); o += d
        in_extra = cfg.n_static + cfg.n_control
        # per-organ input projection: [values, mask] for that organ + static + control
        self.in_proj = nn.ModuleList([
            nn.Linear(2 * d + in_extra, cfg.d_model) for d in cfg.organ_dims])
        Node = GRUNode if cfg.node_type == "gru" else LRUNode
        self.nodes = nn.ModuleList([
            nn.ModuleList([Node(cfg.d_model, cfg.d_model, cfg.d_state, cfg.dropout)
                           for _ in range(cfg.n_organs)])
            for _ in range(cfg.n_layers)])
        self.couplers = nn.ModuleList([OrganGraphCoupling(cfg) for _ in range(cfg.n_layers)])
        # decoders: per-organ map d_model -> organ feature dim
        self.dec = nn.ModuleList([nn.Linear(cfg.d_model, d) for d in cfg.organ_dims])
        self.step_proj = nn.ModuleList([
            nn.Linear(2 * d + in_extra, cfg.d_model) for d in cfg.organ_dims])

    # -- organ input assembly --
    def _organ_inputs(self, values, mask, static, control, t_slice=None):
        B, T, _ = values.shape
        extra = [static.unsqueeze(1).expand(B, T, -1)]
        if self.cfg.n_control and control is not None:
            extra.append(control)
        extra = torch.cat(extra, -1) if extra else None
        outs = []
        for (a, b) in self.slices:
            parts = [values[..., a:b], mask[..., a:b]]
            if extra is not None:
                parts.append(extra)
            outs.append(torch.cat(parts, -1))
        return outs  # list of (B,T,2*d+extra)

    def encode(self, values, mask, static, control=None):
        """Run the layered organ-SSM + graph coupling over the context window."""
        organ_in = self._organ_inputs(values, mask, static, control)
        H = [self.in_proj[i](organ_in[i]) for i in range(self.cfg.n_organs)]  # (B,T,d)
        states = []
        last_gate = None
        for L in range(self.cfg.n_layers):
            new_states = []
            seqs = []
            for i in range(self.cfg.n_organs):
                y, st = self.nodes[L][i](H[i])
                seqs.append(y); new_states.append(st)
            # couple all timesteps at once (vectorised over T)
            stacked = torch.stack(seqs, 2)            # (B,T,O,d)
            B, T, O, d = stacked.shape
            coupled, gate = self.couplers[L](stacked.reshape(B * T, O, d))
            coupled = coupled.reshape(B, T, O, d)
            last_gate = gate.reshape(B, T, -1)        # (B,T,E)
            H = [coupled[:, :, i] for i in range(O)]
            states.append(new_states)
        return H, states, last_gate

    def rollout(self, values, mask, static, control_ctx=None, control_future=None,
                horizon=12):
        """Encode context then free-run ``horizon`` steps; returns predictions (B,H,F)."""
        cfg = self.cfg
        H, states, _ = self.encode(values, mask, static, control_ctx)
        # last predicted observation = last context values
        y_prev = values[:, -1].clone()               # (B,F)
        B = values.shape[0]
        preds = []
        for h in range(horizon):
            ctrl = control_future[:, h] if (cfg.n_control and control_future is not None) else None
            extra = [static]
            if ctrl is not None:
                extra.append(ctrl)
            extra = torch.cat(extra, -1)
            # assemble per-organ step input (use mask=1, we feed predictions)
            organ_step = []
            for (a, b) in self.slices:
                organ_step.append(torch.cat([y_prev[:, a:b], torch.ones_like(y_prev[:, a:b]),
                                             extra], -1))
            cur = [self.step_proj[i](organ_step[i]) for i in range(cfg.n_organs)]
            for L in range(cfg.n_layers):
                outs = []
                for i in range(cfg.n_organs):
                    y, st = self.nodes[L][i].step(cur[i], states[L][i])
                    states[L][i] = st; outs.append(y)
                Hc = torch.stack(outs, 1)             # (B,O,d)
                Hc, _ = self.couplers[L](Hc)
                cur = [Hc[:, i] for i in range(cfg.n_organs)]
            # decode each organ
            y_next = torch.zeros_like(y_prev)
            for i, (a, b) in enumerate(self.slices):
                y_next[:, a:b] = self.dec[i](cur[i])
            preds.append(y_next)
            y_prev = y_next
        return torch.stack(preds, 1)                  # (B,horizon,F)

    def forward(self, batch, horizon=12):
        return self.rollout(
            batch["values"], batch["mask"], batch["static"],
            batch.get("control_ctx"), batch.get("control_future"), horizon)

    def edge_gates(self, values, mask, static, control=None):
        """Mean per-edge gate over the context (for edge-stability analysis)."""
        _, _, g = self.encode(values, mask, static, control)  # (B,T,E)
        return g.mean(dim=1)  # (B,E)

    def n_params(self):
        return sum(p.numel() for p in self.parameters())


def _resolve_edges(spec):
    """Edge-prior specs, including falsification controls (H4).
    'admissible' physiological prior; 'full' all directed; 'none' empty; 'reversed'
    admissible edges with flipped direction; 'shuffled' admissible under a permuted
    organ labelling; 'random' a fixed random directed set of the same sparsity."""
    if spec in (None, "admissible"):
        return tuple(ADMISSIBLE_EDGES)
    if spec == "full":
        return tuple((i, j) for i in range(4) for j in range(4) if i != j)
    if spec == "none":
        return tuple()
    if spec == "reversed":
        return tuple((t, s) for (s, t) in ADMISSIBLE_EDGES)
    if spec == "shuffled":
        perm = [2, 0, 3, 1]                           # fixed organ-label permutation
        return tuple((perm[s], perm[t]) for (s, t) in ADMISSIBLE_EDGES)
    if spec == "random":
        import numpy as np
        rng = np.random.default_rng(0)
        allp = [(i, j) for i in range(4) for j in range(4) if i != j]
        idx = rng.choice(len(allp), size=len(ADMISSIBLE_EDGES), replace=False)
        return tuple(allp[k] for k in sorted(idx))
    return tuple(spec)


def build_model(task="cinc", d_model=64, d_state=32, n_layers=2, edges=None, node_type="ssm"):
    if task == "cinc":
        cfg = PhysioGraphConfig(organ_dims=(4, 4, 3, 5), n_control=0, edges=_resolve_edges(edges),
                                d_model=d_model, d_state=d_state, n_layers=n_layers,
                                node_type=node_type)
    elif task == "cvsim":
        # single cardiovascular organ with 4 observables + 2 controls (vaso, fluid)
        cfg = PhysioGraphConfig(organ_dims=(4,), n_static=1, n_control=2,
                                edges=tuple(), d_model=d_model, d_state=d_state,
                                n_layers=n_layers)
    else:
        raise ValueError(task)
    return PhysioGraph(cfg)


if __name__ == "__main__":
    torch.manual_seed(0)
    # smoke test: CinC forecasting model
    m = build_model("cinc", d_model=48, d_state=24, n_layers=2)
    B, Tc, F_ = 8, 24, 16
    batch = dict(values=torch.randn(B, Tc, F_), mask=torch.ones(B, Tc, F_),
                 static=torch.randn(B, 5))
    out = m(batch, horizon=12)
    print(f"[cinc] params={m.n_params()/1e6:.2f}M  pred={tuple(out.shape)}  "
          f"gate={tuple(m.edge_gates(batch['values'],batch['mask'],batch['static']).shape)}")
    assert out.shape == (B, 12, 16)
    # smoke test: CVSim counterfactual model
    mc = build_model("cvsim", d_model=48, d_state=24, n_layers=1)
    bc = dict(values=torch.randn(B, 12, 4), mask=torch.ones(B, 12, 4),
              static=torch.randn(B, 1), control_ctx=torch.randn(B, 12, 2),
              control_future=torch.randn(B, 24, 2))
    oc = mc(bc, horizon=24)
    print(f"[cvsim] params={mc.n_params()/1e6:.2f}M  pred={tuple(oc.shape)}")
    assert oc.shape == (B, 24, 4)
    print("[model] smoke test PASSED")
