"""Paper-text implementation of GraFITi Eqs. (5)--(13), on hourly windows.

    FF: "a separate fully connected layer in each case" (p.4).
    alpha: "a non-linear activation" (p.4); this port chooses LeakyReLU(0.1).

The negative branch preserves signed forecasts and gradients through the scalar
final edge update. This is the only model change from v2; see METHODS.md.

The PDF requires scalar final graph states but leaves the width transition
unspecified. Before the last graph layer, separate affine maps convert node and
edge embeddings to scalars. Eq. (9) then uses its *input scalar query* as the
residual; it never substitutes the learned attention-query projection. All graph
layers retain four internal attention heads by default. See the METHODS.md
for this dimensional completion and the frozen cohort/optimizer adaptations.
"""
from __future__ import annotations

# Resolve all public modules and scratch from the release root.
import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[1]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH

import math

import torch
from torch import nn

from port_utils_v3 import context, masked_softmax


class _IncidentAttention(nn.Module):
    """Eq. (9), with conventional per-head MHA over incident (node, edge) pairs."""

    def __init__(self, width, heads, attention_dim=None):
        super().__init__()
        attention_dim = width if attention_dim is None else attention_dim
        if width < 1 or heads < 1 or attention_dim % heads:
            raise ValueError('Require positive query width and divisible attention width')
        self.width, self.heads = width, heads
        self.attention_dim = attention_dim
        self.query = nn.Linear(width, attention_dim)
        self.key = nn.Linear(2 * width, attention_dim)
        self.value = nn.Linear(2 * width, attention_dim)
        # No output bias: the empty incident set has exactly zero MHA message.
        self.output = nn.Linear(attention_dim, width, bias=False)
        self.feedforward = nn.Linear(width, width)

    def forward(self, nodes, incident, present):
        batch, count, neighbors = incident.shape[:3]
        head_width = self.attention_dim // self.heads
        q = self.query(nodes).reshape(batch, count, self.heads, head_width)
        k = self.key(incident).reshape(batch, count, neighbors, self.heads, head_width)
        v = self.value(incident).reshape_as(k)
        scores = (q.unsqueeze(2) * k).sum(-1) / math.sqrt(head_width)
        weights = masked_softmax(scores, present.unsqueeze(-1), dim=2)
        aggregate = (weights.unsqueeze(-1) * v).sum(2).reshape(batch, count, -1)
        hidden = torch.nn.functional.leaky_relu(nodes + self.output(aggregate), negative_slope=0.1)
        return torch.nn.functional.leaky_relu(hidden + self.feedforward(hidden), negative_slope=0.1)


class _GraphLayer(nn.Module):
    """Algorithm 1: shared node MAB and synchronous edge update, Eq. (13)."""

    def __init__(self, width, heads, attention_dim):
        super().__init__()
        self.mab = _IncidentAttention(width, heads, attention_dim)
        self.edge_update = nn.Linear(3 * width, width)

    def forward(self, channels, times, edges, present):
        time_on_edges = times.unsqueeze(2).expand_as(edges)
        channel_on_edges = channels.unsqueeze(1).expand_as(edges)
        channel_incident = torch.cat([time_on_edges, edges], -1).transpose(1, 2)
        time_incident = torch.cat([channel_on_edges, edges], -1)
        next_channels = self.mab(channels, channel_incident, present.transpose(1, 2))
        next_times = self.mab(times, time_incident, present)
        next_edges = torch.nn.functional.leaky_relu(edges + self.edge_update(torch.cat(
            [channel_on_edges, time_on_edges, edges], -1)), negative_slope=0.1) * present.unsqueeze(-1)
        return next_channels, next_times, next_edges


class GraFITiAdapter(nn.Module):
    """64/4/2 is inside the paper's search ranges; no optimal-tuple claim.

    n_layers counts all graph layers, including the final scalar graph layer.
    Internal attention width remains latent_dim in that layer, with attn_head
    conventional heads and an output projection into the scalar query space.
    Static inputs are unused, as in the paper's metadata limitation (§6.5).
    """

    def __init__(self, n_feat=16, n_static=5, latent_dim=64, attn_head=4,
                 n_layers=2, time_scale=24.0):
        super().__init__()
        if (latent_dim < 1 or attn_head < 1 or latent_dim % attn_head or
                n_layers < 1 or n_feat < 1 or time_scale <= 0):
            raise ValueError('Require positive sizes, divisible head width and positive time_scale')
        self.n_feat, self.n_static = n_feat, n_static
        self.time_scale = time_scale
        self.config = dict(n_feat=n_feat, n_static=n_static, latent_dim=latent_dim,
                           attn_head=attn_head, n_layers=n_layers, time_scale=time_scale,
                           activation='LeakyReLU(negative_slope=0.1; paper leaves alpha unspecified)',
                           graph_widths=[latent_dim] * (n_layers - 1) + [1],
                           scalar_transition='affine node/edge maps before final graph layer')
        self.channel_embedding = nn.Linear(n_feat, latent_dim)
        self.time_embedding = nn.Linear(1, latent_dim)
        self.edge_embedding = nn.Linear(2, latent_dim)
        self.scalar_nodes = nn.Linear(latent_dim, 1)
        self.scalar_edges = nn.Linear(latent_dim, 1)
        self.layers = nn.ModuleList([
            _GraphLayer(width, attn_head, latent_dim)
            for width in self.config['graph_widths']])

    def initial_graph(self, batch, horizon):
        values, observed = context(batch, self.n_feat)
        if horizon < 1:
            raise ValueError('horizon must be positive')
        batch_size, length, features = values.shape
        future = values.new_zeros(batch_size, horizon, features)
        raw = torch.cat([values, future], 1)
        present = torch.cat([observed, torch.ones_like(future, dtype=torch.bool)], 1)
        # Eq. (3): observed=1, query=0, query value=0.
        indicator = torch.cat([observed, torch.zeros_like(future, dtype=torch.bool)], 1)
        edges = self.edge_embedding(torch.stack([raw, indicator.to(raw.dtype)], -1))
        edges = edges * present.unsqueeze(-1)
        times = torch.arange(length + horizon, device=values.device, dtype=values.dtype)
        times = times / self.time_scale
        time_nodes = torch.sin(self.time_embedding(times.reshape(1, -1, 1)))
        time_nodes = time_nodes.expand(batch_size, -1, -1)
        identities = torch.eye(features, device=values.device, dtype=values.dtype)
        channels = self.channel_embedding(identities).unsqueeze(0).expand(batch_size, -1, -1)
        return channels, time_nodes, edges, present

    def graph_states(self, batch, horizon):
        channels, times, edges, present = self.initial_graph(batch, horizon)
        for index, layer in enumerate(self.layers):
            if index == len(self.layers) - 1:
                channels = self.scalar_nodes(channels)
                times = self.scalar_nodes(times)
                edges = self.scalar_edges(edges) * present.unsqueeze(-1)
            channels, times, edges = layer(channels, times, edges, present)
        return channels, times, edges

    def rollout(self, batch, horizon):
        _, _, edges = self.graph_states(batch, horizon)
        # Eq. (7): scalar query edges directly; no endpoint readout head.
        return edges[:, batch['values'].shape[1]:, :, 0]

    def forward(self, batch, horizon=12):
        return self.rollout(batch, horizon)
