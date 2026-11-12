"""historical-experiment: E1 with shared context/feedback inputs, and its seeds 4--9 extension.

E1_SOURCE is imported unchanged. Only the organ input projections and their input
assembly change in shared arms; E1 node, edge, optimizer, loss and score code is
reused. Full fits belong to the maintainer's host launch, not the CPU worker.
"""
from __future__ import annotations
import os as _os
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, _os.environ.get('PHYSIOGRAPH_ROOT', str(_Path(__file__).absolute().parents[2])))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH


import argparse
import json
from pathlib import Path
import sys
import time

import e1b_protocol as protocol

protocol.configure_scratch()
import numpy as np
import torch
from torch import nn

e1 = protocol.load_e1()
matched = protocol.load_matched()
from organ_graph_ssm_model import PhysioGraph


class SharedInputPhysioGraph(PhysioGraph):
    """Keep E1's dense-initialized matched modules; widen only input access.

Both context and forecast-feedback projections receive all six values and six
masks, the unchanged zero static feature, and the unchanged prescribed control.
Output heads still decode their own organ channels. Forecast masks are ones,
as in E1 and the clinical shared-input model.
"""

    def __init__(self, original):
        nn.Module.__init__(self)
        self.cfg, self.slices = original.cfg, original.slices
        self.nodes, self.couplers, self.dec = original.nodes, original.couplers, original.dec
        width = 2 * self.cfg.n_feat + self.cfg.n_static + self.cfg.n_control
        self.in_proj = nn.ModuleList([
            nn.Linear(width, self.cfg.d_model) for _ in range(self.cfg.n_organs)])
        self.step_proj = nn.ModuleList([
            nn.Linear(width, self.cfg.d_model) for _ in range(self.cfg.n_organs)])

    def _organ_inputs(self, values, mask, static, control=None, t_slice=None):
        batch, times, _ = values.shape
        parts = [values, mask, static[:, None].expand(batch, times, -1)]
        if self.cfg.n_control and control is not None:
            parts.append(control)
        full = torch.cat(parts, -1)
        return [full for _ in range(self.cfg.n_organs)]

    def rollout(self, values, mask, static, control_ctx=None, control_future=None, horizon=12):
        # E1 rollout, with only the per-step input assembly widened. Encoding
        # inherits PhysioGraph.encode, which calls our shared _organ_inputs.
        cfg = self.cfg
        _, states, _ = self.encode(values, mask, static, control_ctx)
        y_prev = values[:, -1].clone()
        predictions = []
        for h in range(horizon):
            ctrl = (control_future[:, h:h + 1]
                    if cfg.n_control and control_future is not None else None)
            organ_step = self._organ_inputs(y_prev[:, None],
                                           torch.ones_like(y_prev[:, None]), static, ctrl)
            cur = [self.step_proj[i](organ_step[i][:, 0]) for i in range(cfg.n_organs)]
            for layer in range(cfg.n_layers):
                outs = []
                for i in range(cfg.n_organs):
                    y, state = self.nodes[layer][i].step(cur[i], states[layer][i])
                    states[layer][i] = state
                    outs.append(y)
                coupled, _ = self.couplers[layer](torch.stack(outs, 1))
                cur = [coupled[:, i] for i in range(cfg.n_organs)]
            y_next = torch.zeros_like(y_prev)
            for i, (a, b) in enumerate(self.slices):
                y_next[:, a:b] = self.dec[i](cur[i])
            predictions.append(y_next)
            y_prev = y_next
        return torch.stack(predictions, 1)


def build_model(arm, seed):
    if arm not in (*protocol.E1_ARMS, *protocol.SHARED_ARMS):
        raise ValueError(f'Unknown arm: {arm}')
    variant = arm.removeprefix('shared_')
    is_organ = variant in e1.VARIANTS
    original = matched.build_model(
        'physiograph_gru' if is_organ else 'control_gru',
        variant if is_organ else 'admissible', seed, 64, 32, 2,
        201 if arm == 'control_gru_matched' else 96)
    return SharedInputPhysioGraph(original) if arm in protocol.SHARED_ARMS else original


def run_cell(*, arm, kappa, seed, epochs, n_patients, device, threads, out,
             npz=None, reference_npz=None, smoke=False, full_run=False):
    if smoke == full_run:
        raise ValueError('Choose exactly one of --smoke or --full-run')
    if (arm not in (*protocol.E1_ARMS, *protocol.SHARED_ARMS)
            or seed not in range(10) or kappa not in protocol.KAPPAS or threads < 1):
        raise ValueError('Unregistered arm, seed, kappa or threads')
    if device not in ('cpu', 'cuda'):
        raise ValueError('Require cpu or cuda device')
    if smoke and (epochs != 1 or not 4 <= n_patients <= 24 or device != 'cpu'):
        raise ValueError('Smoke requires one CPU epoch and 4--24 patients')
    if full_run and (epochs != 60 or n_patients != 400):
        raise ValueError('Full runs require 60 epochs and 400 patients')
    if full_run and (kappa, arm, seed) not in {
            (j['kappa'], j['arm'], j['seed']) for j in protocol.jobs()}:
        raise ValueError('Fit is outside the registered 66-cell extension')
    output = protocol.owned_path(out)
    if output.exists() or Path(out).is_symlink():
        raise FileExistsError(f'Refusing existing record: {out}')
    for path, expected in ((npz, protocol.dataset_path(kappa)),
                           (reference_npz, protocol.dataset_path(1.))):
        if path is not None and Path(path).resolve() != expected:
            raise ValueError('Only the frozen E1 dataset/reference paths are allowed')
    protocol.check_frozen_inputs()
    torch.set_num_threads(threads)
    torch.use_deterministic_algorithms(True)
    start = time.perf_counter()
    dataset = protocol.load_dataset(kappa)
    reference = dataset if kappa == 1. else protocol.load_dataset(1.)
    if smoke:
        # No generation or disk cache: use a small in-memory prefix of the same
        # frozen population. These explicitly marked records cannot enter a gate.
        dataset = dict(dataset)
        for name, value in dataset.items():
            if value.ndim and value.shape[0] == 400:
                dataset[name] = value[:n_patients]
    data = e1.prepare_data(dataset, seed)
    model = build_model(arm, seed)
    count = sum(p.numel() for p in model.parameters())
    model.to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=.002)
    train_start = time.perf_counter()
    curve = []
    for epoch in range(epochs):
        model.train()
        losses = []
        for batch in e1.batches(data, data['tr'], device):
            optimizer.zero_grad()
            prediction = model(batch, e1.K)
            loss = ((prediction - batch['target']) ** 2).mean()
            if not torch.isfinite(loss):
                raise ValueError('Nonfinite training loss')
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
            optimizer.step()
            losses.append(float(loss.detach()))
        curve.append(dict(epoch=epoch + 1, train_mse=float(np.mean(losses))))
        if epoch % 5 == 0 or epoch == epochs - 1:
            print(json.dumps(curve[-1]), flush=True)
    train_seconds = time.perf_counter() - train_start
    model.eval()
    predictions = []
    with torch.no_grad():
        for batch in e1.batches(data, data['te'], device):
            predictions.append(model(batch, e1.K).cpu().numpy() * data['std'] + data['mean'])
    prediction = np.concatenate(predictions)
    if not np.isfinite(prediction).all():
        raise ValueError('Nonfinite evaluation predictions')
    truth = data['truth'][data['te'], e1.C:e1.C + e1.K]
    fixed_ranges = matched.organ_ranges(reference['truth'])
    variant = arm.removeprefix('shared_')
    sources = {**e1.source_hashes(), **{str(p): e1.sha256(p) for p in (
        e1.MATCHED_SIM / 'sim_grid_runner_mono2.py', e1.PROJECT / 'src/organ_graph_ssm_model.py',
        e1.PROJECT / 'src/cvsim_counterfactual_runner.py')}}
    organ_model = variant in e1.VARIANTS
    result = dict(
        schema_version=1, smoke=smoke,
        config=dict(arm=arm, kappa=kappa, seed=seed, dataset_seed=0, epochs=epochs,
                    n_patients=n_patients, device=device, threads=threads, C=e1.C, K=e1.K,
                    lr=.002, batch_size=128, d_model=64, d_state=32, n_layers=2,
                    control_gru_hidden=201 if arm == 'control_gru_matched' else 96),
        metrics=matched.error_metrics(prediction, truth, fixed_ranges,
                                      matched.organ_ranges(data['truth'][data['te']])),
        n_params=count, edges=[list(edge) for edge in matched.graph_edges(variant, seed)]
        if organ_model else [],
        dataset_metadata=json.loads(str(dataset['metadata_json'])),
        dataset_path=str(protocol.dataset_path(kappa)), dataset_sha256=protocol.DATA_HASHES[kappa],
        reference_path=str(protocol.dataset_path(1.)), reference_sha256=protocol.DATA_HASHES[1.],
        reference_ranges=fixed_ranges,
        normalization=dict(mean=data['mean'].tolist(), std=data['std'].tolist(),
                           scope='Dense labels from training patients, all saved times'),
        split=dict(train=data['tr'].tolist(), test=data['te'].tolist()),
        curve=curve, timing=dict(train_seconds=train_seconds,
                                total_seconds=time.perf_counter() - start),
        versions=dict(numpy=np.__version__, torch=torch.__version__), source_sha256=sources,
        e1b_source_sha256={str(p): protocol.sha256(p) for p in (
            Path(__file__).resolve(), protocol.ROOT / 'e1b_protocol.py',
            protocol.ROOT / 'run_host_e1b.sh')},
        input_access='shared' if arm in protocol.SHARED_ARMS else (
            'partitioned' if organ_model else 'monolithic_full_values_without_masks'),
        projection_input_widths=[p.in_features for p in model.in_proj] if organ_model else [],
        step_projection_input_widths=[p.in_features for p in model.step_proj] if organ_model else [],
        smoke_population_indices=list(range(n_patients)) if smoke else None,
        cublas_workspace_config=protocol.os.environ['CUBLAS_WORKSPACE_CONFIG'],
        caveats=['Dense synthetic target supervision; masked context only.',
                 'Frozen monolithic controls do not consume explicit masks.',
                 'Smoke uses an in-memory population prefix; its scores are not evidence.',
                 'Shared inputs include predicted feedback in forecast, as in clinical E2.'])
    protocol.write_json(output, result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    runner = commands.add_parser('run-cell')
    runner.add_argument('--arm', choices=(*protocol.E1_ARMS, *protocol.SHARED_ARMS), required=True)
    runner.add_argument('--kappa', type=float, choices=protocol.KAPPAS, required=True)
    runner.add_argument('--seed', type=int, choices=range(10), required=True)
    runner.add_argument('--epochs', type=int, default=60)
    runner.add_argument('--n-patients', type=int, default=400)
    runner.add_argument('--device', choices=('cpu', 'cuda'), default='cpu')
    runner.add_argument('--threads', type=int, default=1)
    runner.add_argument('--npz', type=Path)
    runner.add_argument('--reference-npz', type=Path)
    runner.add_argument('--out', type=Path, required=True)
    mode = runner.add_mutually_exclusive_group(required=True)
    mode.add_argument('--smoke', action='store_true')
    mode.add_argument('--full-run', action='store_true')
    args = vars(parser.parse_args(argv))
    args.pop('command')
    result = run_cell(**args)
    print(json.dumps(dict(config=result['config'], smoke=result['smoke'],
                          macro_nrmse_fixed=result['metrics']['macro_nrmse_fixed']), allow_nan=False))


if __name__ == '__main__':
    main()
