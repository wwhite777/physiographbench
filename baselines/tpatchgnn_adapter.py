"""Paper-based t-PatchGNN for the frozen hourly CinC forecasting batch API.

This is a new implementation, with no runtime imports from the upstream project.
Equation numbers refer to Zhang et al., paper 2024; see METHODS.md for choices
that the equations leave unspecified and for the CinC protocol adaptations.
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
from torch.nn import functional as F


class ContinuousTimeEmbedding(nn.Module):
    """One affine coordinate followed by learned sinusoidal coordinates (Eq. 3)."""

    def __init__(self, dimension):
        super().__init__()
        self.affine = nn.Linear(1, dimension)

    def forward(self, time):
        coordinates = self.affine(time.unsqueeze(-1))
        return torch.cat((coordinates[..., :1], coordinates[..., 1:].sin()), dim=-1)


class TransformablePatchEncoder(nn.Module):
    """Time-aware filters normalized over observed members of each patch."""

    def __init__(self, width, time_dimension):
        super().__init__()
        self.channels = width - 1
        self.input_dimension = time_dimension + 1
        self.filter_network = nn.Sequential(
            nn.Linear(self.input_dimension, self.channels), nn.ReLU(),
            nn.Linear(self.channels, self.channels), nn.ReLU(),
            nn.Linear(self.channels, self.channels * self.input_dimension))
        # The paper omits the post-convolution activation/bias; the released
        # implementation resolves this detail as an affine offset then ReLU.
        self.offset = nn.Parameter(torch.randn(self.channels))

    def forward(self, observations, present):
        # (..., members, input_dimension); missing padding is excluded even when
        # an entire patch is empty. It cannot act as an observed zero value.
        observations = torch.where(present.unsqueeze(-1), observations, 0.)
        raw = self.filter_network(observations).unflatten(
            -1, (self.channels, self.input_dimension))
        membership = present[..., None, None]
        raw = raw.masked_fill(~membership, torch.finfo(raw.dtype).min)
        weights = raw.softmax(dim=-3) * membership
        weights = weights / weights.sum(dim=-3, keepdim=True).clamp_min(
            torch.finfo(weights.dtype).tiny)
        convolved = (weights * observations.unsqueeze(-2)).sum(dim=(-3, -1))
        features = F.relu(convolved + self.offset)
        patch_present = present.any(dim=-1, keepdim=True).to(features.dtype)
        return torch.cat((features, patch_present), dim=-1)


class AdaptivePatchBlock(nn.Module):
    """Patch Transformer (Eq. 8), gated graph (9–10), graph polynomial (11)."""

    def __init__(self, width, graph_dimension, heads, graph_hops,
                 transformer_layers, feedforward_width, dropout):
        super().__init__()
        layer = nn.TransformerEncoderLayer(
            width, heads, dim_feedforward=feedforward_width, dropout=dropout,
            activation='relu', batch_first=True, norm_first=False)
        self.temporal = nn.TransformerEncoder(
            layer, transformer_layers, enable_nested_tensor=False)
        self.dynamic_embeddings = nn.ModuleList(
            nn.Linear(width, graph_dimension) for _ in range(2))
        self.gates = nn.ModuleList(
            nn.Linear(width + graph_dimension, 1) for _ in range(2))
        self.hop_projections = nn.ModuleList(
            nn.Linear(width, width, bias=False) for _ in range(graph_hops + 1))
        self.graph_offset = nn.Parameter(torch.zeros(width))

    def adjacency(self, patch_states, inherent_embeddings):
        # States are (batch, patches, variables, width). Each sample and patch
        # obtains its own directed row-normalized graph; no target data enter it.
        embeddings = []
        for inherent, dynamic, gate in zip(
                inherent_embeddings, self.dynamic_embeddings, self.gates):
            baseline = inherent.expand(*patch_states.shape[:-1], -1)
            strength = F.relu(torch.tanh(gate(torch.cat(
                (patch_states, baseline), dim=-1))))
            embeddings.append(baseline + strength * dynamic(patch_states))
        affinities = embeddings[0] @ embeddings[1].transpose(-1, -2)
        return F.relu(affinities).softmax(dim=-1)

    def propagate(self, patch_states, adjacency):
        propagated = patch_states
        combined = self.hop_projections[0](propagated)
        for projection in self.hop_projections[1:]:
            propagated = adjacency @ propagated
            combined = combined + projection(propagated)
        return F.relu(combined + self.graph_offset)

    def forward(self, states, positions, inherent_embeddings):
        batch_size, variables, patches, width = states.shape
        sequence = (states + positions).reshape(batch_size * variables, patches, width)
        temporal_states = self.temporal(sequence).reshape_as(states).transpose(1, 2)
        graph = self.adjacency(temporal_states, inherent_embeddings)
        return self.propagate(temporal_states, graph).transpose(1, 2), graph


class TPatchGNNAdapter(nn.Module):
    """PhysioNet architecture, with hourly context and dense future queries.

    The context length fixes the flattening head at construction. The default
    C=12 gives windows [0,8) and [8,16), with only hours 8–11 in the latter.
    Static covariates have no branch in the paper and are accepted but unused.
    """

    def __init__(self, n_feat=16, n_static=5, context_length=12, patch_hours=8,
                 width=64, time_dimension=10, graph_dimension=10, heads=1,
                 graph_hops=1, blocks=1, transformer_layers=1,
                 feedforward_width=2048, dropout=.1, time_scale=24.):
        super().__init__()
        integer_sizes = (n_feat, context_length, patch_hours, width, time_dimension,
                         graph_dimension, heads, blocks, transformer_layers,
                         feedforward_width)
        if any(not isinstance(x, int) or x < 1 for x in integer_sizes):
            raise ValueError('Architecture sizes must be positive integers')
        if width < 2 or width % heads or graph_hops < 0 or time_scale <= 0:
            raise ValueError('Require width >=2 divisible by heads, hops >=0, time_scale >0')
        self.n_feat, self.n_static = n_feat, n_static
        self.context_length, self.patch_hours = context_length, patch_hours
        self.time_scale = time_scale
        patch_count = math.ceil(context_length / patch_hours)
        self.config = dict(
            n_feat=n_feat, n_static=n_static, context_length=context_length,
            patch_hours=patch_hours, stride_hours=patch_hours, patch_count=patch_count,
            width=width, time_dimension=time_dimension, graph_dimension=graph_dimension,
            heads=heads, graph_hops=graph_hops, blocks=blocks,
            transformer_layers=transformer_layers, feedforward_width=feedforward_width,
            dropout=dropout, time_scale=time_scale, static_used=False,
            graph_orientation='A @ H (paper Eq. 11)')
        self.time_embedding = ContinuousTimeEmbedding(time_dimension)
        self.patch_encoder = TransformablePatchEncoder(width, time_dimension)
        self.inherent_embeddings = nn.ParameterList(
            nn.Parameter(torch.randn(n_feat, graph_dimension)) for _ in range(2))
        self.blocks = nn.ModuleList(
            AdaptivePatchBlock(width, graph_dimension, heads, graph_hops,
                               transformer_layers, feedforward_width, dropout)
            for _ in range(blocks))
        # Standard sinusoidal order encoding, generated without a length cap.
        index = torch.arange(width, dtype=torch.float32)
        angles = torch.arange(patch_count, dtype=torch.float32)[:, None] / (
            10000. ** (2 * torch.div(index, 2, rounding_mode='floor') / width))
        positions = torch.where(index.remainder(2) == 0, angles.sin(), angles.cos())
        self.register_buffer('positions', positions)
        self.flatten_head = nn.Linear(patch_count * width, width)
        self.query_head = nn.Sequential(
            nn.Linear(width + time_dimension, width), nn.ReLU(),
            nn.Linear(width, width), nn.ReLU(), nn.Linear(width, 1))

    def patch_tokens(self, batch):
        values, mask = batch['values'], batch['mask']
        if (values.ndim != 3 or values.shape != mask.shape
                or values.shape[1:] != (self.context_length, self.n_feat)):
            raise ValueError('Expected values/mask shaped (batch, context_length, n_feat)')
        observed = mask > 0
        values = torch.where(observed, values, 0.)
        padded_length = self.positions.shape[0] * self.patch_hours
        padding = padded_length - self.context_length
        values = F.pad(values, (0, 0, 0, padding))
        observed = F.pad(observed, (0, 0, 0, padding))
        hours = torch.arange(padded_length, device=values.device, dtype=values.dtype)
        embedded_times = self.time_embedding(hours / self.time_scale)
        time_features = embedded_times[None, :, None, :].expand(*values.shape, -1)
        observations = torch.cat((time_features, values.unsqueeze(-1)), dim=-1)
        # Packing uses the hourly grid already supplied by the frozen loader.
        # Masked reductions are algebraically identical to ragged member lists.
        observations = observations.unflatten(1, (-1, self.patch_hours)).permute(0, 3, 1, 2, 4)
        observed = observed.unflatten(1, (-1, self.patch_hours)).permute(0, 3, 1, 2)
        return self.patch_encoder(observations, observed)

    def encode_context(self, batch):
        states = self.patch_tokens(batch)
        graphs = []
        for index, block in enumerate(self.blocks):
            updated, graph = block(states, self.positions, self.inherent_embeddings)
            states = updated if index == 0 else states + updated
            graphs.append(graph)
        return self.flatten_head(states.flatten(start_dim=-2)), graphs

    def rollout(self, batch, horizon):
        if not isinstance(horizon, int) or horizon < 1:
            raise ValueError('horizon must be a positive integer')
        encoded, _ = self.encode_context(batch)
        hours = torch.arange(self.context_length, self.context_length + horizon,
                             device=encoded.device, dtype=encoded.dtype)
        query_times = self.time_embedding(hours / self.time_scale)
        query_times = query_times.expand(*encoded.shape[:2], horizon, -1)
        context = encoded.unsqueeze(-2).expand(-1, -1, horizon, -1)
        return self.query_head(torch.cat((context, query_times), dim=-1)).squeeze(-1).transpose(1, 2)

    def forward(self, batch, horizon=12):
        return self.rollout(batch, horizon)
