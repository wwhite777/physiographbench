#!/usr/bin/env python3
"""Fixed-graph GraFITi/t-PatchGNN ablations on frozen CinC-2019 A/B.

The default --grid preview prints exactly 24 commands: two models, three graphs,
four seeds. Each fit evaluates BOTH A-test and external B, without training on B.
GraFITi needs receiver-specific time states; see ABLATION_DESIGN.md.
"""
from __future__ import annotations

import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[2]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH

import argparse
from pathlib import Path
import shlex
import sys
import time

from e5_common import (ROOT, PROJECT, GraFITiAdapter, TPatchGNNAdapter, command_line,
                       evaluate_mse, fit, owned_path, pooled_mse, save_checkpoint,
                       seed_runtime, sha256, utc_now, write_json)
import numpy as np
import torch
from torch.nn import functional as F
from torch.utils.data import DataLoader, Subset

from organ_graph_ssm_model import ADMISSIBLE_EDGES
from physiograph_data_loader import make_loaders
from port_utils_v3 import query_mse

MODELS = ('grafiti', 'tpatchgnn')
GRAPHS = ('physiological', 'random', 'complete')
ORGAN_SLICES = ((0, 4), (4, 8), (8, 11), (11, 16))
EXPECTED_FEATURES = ['HR', 'SBP', 'MAP', 'DBP', 'O2Sat', 'Resp', 'FiO2', 'PaCO2',
                     'Creatinine', 'BUN', 'Potassium', 'Lactate', 'Glucose', 'HCO3', 'WBC', 'Temp']


def graph_support(kind, seed=0):
    """A[receiver,source]; self + within-organ links + lifted organ arrows."""
    physiological = torch.zeros(16, 16, dtype=torch.bool)
    for start, stop in ORGAN_SLICES:
        physiological[start:stop, start:stop] = True
    for source, receiver in ADMISSIBLE_EDGES:
        sa, sb = ORGAN_SLICES[source]
        ra, rb = ORGAN_SLICES[receiver]
        physiological[ra:rb, sa:sb] = True
    if kind == 'physiological':
        return physiological
    if kind == 'complete':
        return torch.ones_like(physiological)
    if kind != 'random':
        raise ValueError(f'Unknown graph: {kind}')
    # Same incoming degree for EVERY receiver, including a retained self loop.
    rng = np.random.default_rng(seed)
    random = torch.eye(16, dtype=torch.bool)
    for receiver in range(16):
        candidates = np.delete(np.arange(16), receiver)
        degree = int(physiological[receiver].sum()) - 1
        random[receiver, rng.choice(candidates, degree, replace=False)] = True
    return random


def normalized_adjacency(support):
    weights = support.to(torch.float32)
    return weights / weights.sum(-1, keepdim=True).clamp_min(1)


class FixedTPatchGNN(TPatchGNNAdapter):
    def __init__(self, support):
        super().__init__()  # Retain the published PhysioNet architecture sizes.
        self.register_buffer('fixed_adjacency', normalized_adjacency(support))
        # These dictionaries/gates/projections are bypassed, not secretly learned.
        for parameter in self.inherent_embeddings.parameters():
            parameter.requires_grad_(False)
        for block in self.blocks:
            for module in (*block.dynamic_embeddings, *block.gates):
                module.requires_grad_(False)
        self.config['adjacency'] = 'fixed row-normalized A[receiver,source]; A @ H'

    def encode_context(self, batch):
        states = self.patch_tokens(batch)
        graphs = []
        for index, block in enumerate(self.blocks):
            batch_size, variables, patches, width = states.shape
            sequence = (states + self.positions).reshape(batch_size * variables, patches, width)
            temporal = block.temporal(sequence).reshape_as(states).transpose(1, 2)
            graph = self.fixed_adjacency.expand(batch_size, patches, -1, -1)
            updated = block.propagate(temporal, graph).transpose(1, 2)
            states = updated if index == 0 else states + updated
            graphs.append(graph)
        return self.flatten_head(states.flatten(start_dim=-2)), graphs


def fixed_attention_finish(mab, nodes, aggregate):
    """Retain v3 value/output/FF maps and both activated raw-Q residuals."""
    hidden = F.leaky_relu(nodes + mab.output(aggregate), negative_slope=.1)
    return F.leaky_relu(hidden + mab.feedforward(hidden), negative_slope=.1)


def fixed_grafiti_layer(layer, channels, times, edges, present, adjacency):
    """Synchronous updates; times has one state per (time, receiver channel).

    Avoid materializing (batch,time,receiver,source,width) incident tensors.
    Source-channel attention uses the prescribed weights in every head. The
    channel node still learns attention over its own temporal incident edges.
    """
    mab = layer.mab
    channel_on_edges = channels[:, None].expand_as(edges)
    source_values = mab.value(torch.cat([channel_on_edges, edges], -1))
    observed = present.to(source_values.dtype)
    denominator = torch.einsum('rs,bts->btr', adjacency, observed)
    aggregate_times = torch.einsum('rs,bts,btsd->btrd', adjacency, observed, source_values)
    aggregate_times = aggregate_times / denominator.clamp_min(1e-30).unsqueeze(-1)
    next_times = fixed_attention_finish(mab, times, aggregate_times)

    next_channels = mab(channels, torch.cat([times, edges], -1).transpose(1, 2),
                        present.transpose(1, 2))
    next_edges = F.leaky_relu(edges + layer.edge_update(torch.cat(
        [channel_on_edges, times, edges], -1)), negative_slope=.1) * observed.unsqueeze(-1)
    return next_channels, next_times, next_edges


class FixedGraFITi(GraFITiAdapter):
    def __init__(self, support):
        super().__init__()
        self.register_buffer('fixed_adjacency', normalized_adjacency(support))
        self.config.update(adjacency='fixed organ/variable conditional incidence weights',
                           time_states='one copy per receiving variable to prevent shared-time bypass',
                           temporal_attention='retained learned attention over this variable\'s present edges')

    def graph_states(self, batch, horizon):
        channels, times, edges, present = self.initial_graph(batch, horizon)
        times = times[:, :, None].expand_as(edges)
        for index, layer in enumerate(self.layers):
            if index == len(self.layers) - 1:
                channels = self.scalar_nodes(channels)
                times = self.scalar_nodes(times)
                edges = self.scalar_edges(edges) * present.unsqueeze(-1)
            channels, times, edges = fixed_grafiti_layer(
                layer, channels, times, edges, present, self.fixed_adjacency)
        return channels, times, edges


def build_model(model, graph, seed):
    support = graph_support(graph, seed)
    return (FixedGraFITi if model == 'grafiti' else FixedTPatchGNN)(support)


def run(args):
    started, start_clock = time.perf_counter(), utc_now()
    owned_path(args.out)
    if args.epochs != (1 if args.smoke else 35):
        raise ValueError('CinC protocol: 35 maximum epochs; smoke: one epoch')
    if args.batch_size < 1:
        raise ValueError('batch size must be positive')
    seed_runtime(args.seed, args.threads, args.device)
    train, val, test_a, test_b, meta = make_loaders(
        args.npz, C=12, K=12, batch_size=args.batch_size, num_workers=0)
    if meta['features'] != EXPECTED_FEATURES or not np.array_equal(meta['organ_slices'], ORGAN_SLICES):
        raise ValueError('The frozen 16-feature organ layout is required')
    loaders = [train, val, test_a, test_b]
    if args.smoke:
        loaders = [DataLoader(Subset(loader.dataset, range(min(limit, len(loader.dataset)))),
                              batch_size=args.batch_size, shuffle=i == 0, num_workers=0)
                   for i, (loader, limit) in enumerate(zip(loaders, (32, 8, 8, 16)))]
    model = build_model(args.model, args.graph, args.seed)
    history, best_epoch = fit(
        model, *loaders[:2], device=args.device, horizon=12, epochs=args.epochs,
        lr=.001, weight_decay=1e-5, optimizer_name='Adam', schedule='cosine',
        patience=8, min_delta=1e-4,
        loss_fn=query_mse if args.model == 'grafiti' else pooled_mse, clip=1.)
    result = dict(task='learned-graph experiment', command=command_line(), smoke=args.smoke,
                  started_utc=start_clock, finished_utc=utc_now(),
                  config={**vars(args), 'npz': str(args.npz), 'out': str(args.out)},
                  architecture=model.config,
                  n_params=sum(p.numel() for p in model.parameters()),
                  n_trainable_params=sum(p.numel() for p in model.parameters() if p.requires_grad),
                  graph=dict(kind=args.graph, seed=args.seed, orientation='receiver,source',
                             support=graph_support(args.graph, args.seed).int().tolist(),
                             weights=model.fixed_adjacency.cpu().tolist()),
                  protocol=dict(C=12, K=12, optimizer='Adam', lr=.001, weight_decay=1e-5,
                                scheduler='CosineAnnealingLR(T_max=epochs)', clip_norm=1.,
                                patience=8, min_delta_rmse=1e-4,
                                normalization='Frozen CinC-2019 A-train mean/std',
                                train_loss='example-weighted query MSE' if args.model == 'grafiti'
                                else 'pooled observed-cell MSE',
                                split_counts=[len(loader.dataset) for loader in loaders]),
                  best_epoch=best_epoch, training_history=history,
                  validation=evaluate_mse(model, loaders[1], args.device, 12),
                  A_test=evaluate_mse(model, loaders[2], args.device, 12),
                  B_external=evaluate_mse(model, loaders[3], args.device, 12),
                  input=dict(path=str(args.npz), sha256=sha256(args.npz)),
                  elapsed_seconds=time.perf_counter() - started)
    result['checkpoint'] = save_checkpoint(args.out.with_suffix('.pt'), model)
    result['finished_utc'] = utc_now()
    result['elapsed_seconds'] = time.perf_counter() - started
    write_json(args.out, result)
    print('RESULT ' + str(args.out), flush=True)
    return result


def portable_command(command):
    return ['python3' if i == 0 else
            str(Path(arg).relative_to(PROJECT)) if Path(arg).is_absolute() and Path(arg).is_relative_to(PROJECT)
            else arg for i, arg in enumerate(command)]


def grid_commands(args):
    commands = []
    for model in MODELS:
        for graph in GRAPHS:
            for seed in range(4):
                commands.append([sys.executable, '-B', str(ROOT / 'learned_adjacency_ablation.py'),
                                 '--run', '--model', model, '--graph', graph, '--seed', str(seed),
                                 '--epochs', '35', '--batch-size', '128', '--device', args.device,
                                 '--threads', str(args.threads), '--npz', str(args.npz),
                                 '--out', str(ROOT / f'runs/e5/{model}_{graph}_s{seed}.json')])
    return [portable_command(command) for command in commands]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--grid', action='store_true')
    mode.add_argument('--dry-run', action='store_true')
    mode.add_argument('--run', action='store_true')
    mode.add_argument('--smoke', action='store_true')
    parser.add_argument('--model', choices=MODELS)
    parser.add_argument('--graph', choices=GRAPHS)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--epochs', type=int)
    parser.add_argument('--batch-size', type=int, default=128)
    parser.add_argument('--device', choices=('cpu', 'cuda'), default='cpu')
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--npz', type=Path, default=PROJECT / 'data/cinc2019_cohort.npz')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    args.epochs = args.epochs if args.epochs is not None else (1 if args.smoke else 35)
    if args.run or args.smoke:
        if not (args.model and args.graph and args.out):
            parser.error('--run/--smoke require --model, --graph and --out')
        print('COMMAND ' + command_line(), flush=True)
        run(args)
    else:
        for command in grid_commands(args):
            print(shlex.join(command))


if __name__ == '__main__':
    main()
