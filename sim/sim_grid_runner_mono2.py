"""One matched CVSim training run, following the frozen H3/H5 protocol.

Forecasting uses organ GRUs for all six graph variants. Width, initialization
of shared parameters, split, optimizer and training budget are matched. Parameter
counts differ only through the selected edge modules and are reported explicitly.
Training uses the frozen train-split z scores; fixed kappa=1 ranges are evaluation
denominators. Sepsis/severity is never supplied as a model input.
"""
from __future__ import annotations

# Resolve all public modules and scratch from the release root.
import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[1]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import torch
from torch import nn

from sim_policy_ext import (CHANNELS, ORGANS, POLICY_NOTE, ROOT, make_dataset_grid,
                            overlap_diagnostics, owned_path, sha256, write_json)
from cvsim_counterfactual_runner import (CRNLite, ControlGRU, load_cvsim,
                                         make_batches, train)
from organ_graph_ssm_model import OrganGraphCoupling, PhysioGraph, PhysioGraphConfig

VARIANTS = ('admissible', 'reversed', 'random', 'dense', 'none', 'misspecified-1')
MODELS = ('physiograph', 'physiograph_gru', 'control_gru', 'crn_lite')
ADMISSIBLE = ((0, 1), (0, 2))  # simulator order: cardiovascular, renal, metabolic
DENSE = tuple((s, t) for s in range(3) for t in range(3) if s != t)


class _MatchedCoupling(OrganGraphCoupling):
    """Retain the same non-edge operations when the message sum is zero."""
    def __init__(self, original, cfg, indices):
        nn.Module.__init__(self)
        self.cfg = cfg
        self.msg = nn.ModuleList([original.msg[i] for i in indices])
        self.gate = nn.ModuleList([original.gate[i] for i in indices])
        self.norm = original.norm
        self.register_buffer('src', torch.tensor([s for s, _ in cfg.edges], dtype=torch.long))
        self.register_buffer('dst', torch.tensor([t for _, t in cfg.edges], dtype=torch.long))

    def forward(self, hidden):
        if not self.cfg.edges:
            return self.norm(hidden), hidden.new_zeros(hidden.shape[0], 0)
        return super().forward(hidden)


def graph_edges(variant, seed):
    if variant == 'admissible':
        return ADMISSIBLE
    if variant == 'reversed':
        return tuple((t, s) for s, t in ADMISSIBLE)
    if variant == 'random':
        indices = np.random.default_rng(seed).choice(len(DENSE), len(ADMISSIBLE), replace=False)
        return tuple(DENSE[i] for i in sorted(indices))
    if variant == 'dense':
        return DENSE
    if variant == 'none':
        return ()
    if variant == 'misspecified-1':
        return ((0, 2), (1, 2))  # remove cardiovascular->renal, add renal->metabolic
    raise ValueError(variant)


def build_model(model, variant='admissible', seed=0, d_model=64, d_state=32, n_layers=2,
                control_gru_hidden=96):
    torch.manual_seed(seed)
    if model == 'control_gru':
        if not isinstance(control_gru_hidden, int) or control_gru_hidden < 1:
            raise ValueError('control_gru_hidden must be a positive integer')
        return ControlGRU(n_obs=6, d=control_gru_hidden)
    if model == 'crn_lite':
        return CRNLite(n_obs=6, d=96, lamb=.5)
    if model not in MODELS:
        raise ValueError(model)
    selected = graph_edges(variant, seed)
    cfg = PhysioGraphConfig(organ_dims=(4, 1, 1), n_static=1, n_control=1,
                            edges=DENSE, d_model=d_model, d_state=d_state,
                            n_layers=n_layers,
                            node_type='gru' if model == 'physiograph_gru' else 'ssm')
    # Initialize a common dense model, then select edge modules. This holds shared
    # parameter values and the post-initialization RNG state fixed across variants.
    result = PhysioGraph(cfg)
    result.cfg = replace(cfg, edges=selected)
    indices = [DENSE.index(edge) for edge in selected]
    result.couplers = nn.ModuleList([
        _MatchedCoupling(coupler, result.cfg, indices) for coupler in result.couplers])
    return result


def organ_ranges(target):
    return {organ: float(np.max(target[..., indices]) - np.min(target[..., indices])) + 1e-6
            for organ, indices in ORGANS.items()}


def error_metrics(prediction, target, fixed_ranges, cell_ranges):
    rmse = {organ: float(np.sqrt(np.mean(
        (prediction[..., indices].astype(np.float64) - target[..., indices]) ** 2)))
            for organ, indices in ORGANS.items()}
    fixed = {organ: rmse[organ] / fixed_ranges[organ] for organ in ORGANS}
    local = {organ: rmse[organ] / cell_ranges[organ] for organ in ORGANS}
    return dict(organ_rmse=rmse, organ_nrmse_fixed=fixed, organ_nrmse_per_kappa=local,
                macro_nrmse_fixed=float(np.mean(list(fixed.values()))),
                macro_nrmse_per_kappa=float(np.mean(list(local.values()))))


def direction_metrics(prediction, truth):
    """Inputs (patients, doses, time, channel); exact sign, including zero ties."""
    predicted_delta = np.diff(prediction, axis=1)
    true_delta = np.diff(truth, axis=1)
    correct = np.sign(predicted_delta) == np.sign(true_delta)
    by_channel = {channel: float(correct[..., i].mean()) for i, channel in enumerate(CHANNELS)}
    by_organ = {organ: float(correct[..., indices].mean()) for organ, indices in ORGANS.items()}
    # Reproduce the paper: extreme-dose difference of population/time means for
    # MAP, UO and Lac, one representative channel per organ (three signs total).
    response_pred = prediction.mean(axis=(0, 2), dtype=np.float64)
    response_true = truth.mean(axis=(0, 2), dtype=np.float64)
    signs = {channel: bool(np.sign(response_pred[-1, i] - response_pred[0, i]) ==
                          np.sign(response_true[-1, i] - response_true[0, i]))
             for channel, i in (('MAP', 0), ('UO', 4), ('Lac', 5))}
    return dict(cell_mean=float(correct.mean()), per_channel=by_channel, per_organ=by_organ,
                n_cells=int(correct.size),
                true_zero_change_fraction=float((true_delta == 0).mean()),
                predicted_zero_change_fraction=float((predicted_delta == 0).mean()),
                zero_sign_rule='Exact numpy.sign equality; zero counts as a third sign.',
                population_sign_correct=signs,
                population_mean=float(np.mean(list(signs.values()))),
                n_correct_population_signs=int(sum(signs.values())),
                predicted_population_response_by_dose=response_pred.tolist(),
                true_population_response_by_dose=response_true.tolist())


@torch.no_grad()
def predict(model, data, C, K, device, counterfactual=False):
    model.eval()
    predictions = []
    for batch in make_batches(data, data['te'], C, K, device):
        if counterfactual:
            by_dose = []
            for dose in data['doses']:
                batch['control_future'] = torch.full(
                    (len(batch['values']), K, 1), float(dose), device=device)
                by_dose.append(model(batch, K).cpu().numpy() * data['std'] + data['mean'])
            predictions.append(np.stack(by_dose, axis=1))
        else:
            predictions.append(model(batch, K).cpu().numpy() * data['std'] + data['mean'])
    if counterfactual:
        truth = data['cf'][data['te'], :, C:C + K]
    else:
        truth = data['obs'][data['te'], C:C + K]
    return np.concatenate(predictions), truth


def _dataset(path, *, kappa, confound, sigma, seed, n_patients, horizon_h, out_dt):
    config = dict(kappa=float(kappa), confound=float(confound), sigma=float(sigma), seed=seed,
                  n_patients=n_patients, horizon_h=float(horizon_h), out_dt=float(out_dt))
    if path is None:
        key = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:20]
        path = ROOT / 'artifacts/datasets' / f'{key}.npz'
    else:
        path = Path(path).resolve()
    if not path.exists():
        make_dataset_grid(**config, out_path=path)
    with np.load(path) as packed:
        if packed['factual'].shape[0] != n_patients:
            raise ValueError(f'{path}: patient count differs from --n_patients')
        metadata = json.loads(str(packed['metadata_json'])) if 'metadata_json' in packed else {}
        if metadata:
            for name, value in config.items():
                if metadata[name] != value:
                    raise ValueError(f'{path}: {name}={metadata[name]} but requested {value}')
            if metadata['source_sha256'] != sha256(
                    str(RELEASE_ROOT / 'src/cvsim_hemodynamics_simulator.py')):
                raise ValueError('Cached dataset uses a different simulator')
    return path, metadata


def run_cell(*, task='forecast', kappa=1., variant='admissible', confound=1., sigma=.03,
             model='physiograph_gru', seed=0, dataset_seed=0, epochs=60, n_patients=400,
             device='cpu', out=None, npz=None, reference_npz=None, C=12, K=24,
             lr=.002, d_model=64, d_state=32, n_layers=2, horizon_h=6., out_dt=300.,
             threads=1, smoke=False, allow_monolithic_control=False, control_gru_hidden=96):
    start = time.perf_counter()
    if task not in ('forecast', 'counterfactual'):
        raise ValueError(task)
    if task == 'forecast' and model != 'physiograph_gru' and not (
            allow_monolithic_control and model == 'control_gru'):
        raise ValueError('The matched H3 graph grid uses physiograph_gru for every variant')
    if task == 'counterfactual' and variant != 'admissible':
        raise ValueError('The H5 model grid uses the admissible variant')
    if not isinstance(control_gru_hidden, int) or control_gru_hidden < 1:
        raise ValueError('control_gru_hidden must be a positive integer')
    if epochs < 1 or n_patients < 4 or C < 1 or K < 1 or threads < 1:
        raise ValueError('Require epochs/C/K/threads >=1 and n_patients >=4')
    if smoke and (epochs > 3 or n_patients > 24):
        raise ValueError('Smoke is limited to <=3 epochs and <=24 patients')
    if out is not None:
        owned_path(out)
    torch.set_num_threads(threads)
    torch.use_deterministic_algorithms(True)
    device = torch.device(device)
    path, metadata = _dataset(npz, kappa=kappa, confound=confound, sigma=sigma,
                              seed=dataset_seed, n_patients=n_patients,
                              horizon_h=horizon_h, out_dt=out_dt)
    # A single reference policy is used across all kappa AND policy cells/seeds.
    ref_path, ref_metadata = _dataset(
        reference_npz, kappa=1., confound=1., sigma=.03, seed=dataset_seed,
        n_patients=n_patients, horizon_h=horizon_h, out_dt=out_dt)
    data = load_cvsim(path, C, seed)
    if C + K > data['T']:
        raise ValueError(f'C+K={C + K} exceeds T={data["T"]}')
    with np.load(ref_path) as reference:
        ref_target = reference['factual'][..., :6] if task == 'forecast' else reference['counterfactual']
        fixed_ranges = organ_ranges(ref_target)
    cell_truth = data['obs'] if task == 'forecast' else data['cf']
    cell_ranges = organ_ranges(cell_truth[data['te']])  # frozen H3/H5 denominator scope
    generation_seconds = time.perf_counter() - start
    instance = build_model(model, variant, seed, d_model, d_state, n_layers, control_gru_hidden)
    n_params = int(sum(p.numel() for p in instance.parameters()))
    train_start = time.perf_counter()
    train(instance, data, C, K, device, epochs, lr)
    train_seconds = time.perf_counter() - train_start
    evaluation_start = time.perf_counter()
    cf_prediction, cf_truth = predict(instance, data, C, K, device, counterfactual=True)
    if task == 'forecast':
        prediction, truth = predict(instance, data, C, K, device)
    else:
        prediction, truth = cf_prediction, cf_truth
    if not np.isfinite(prediction).all() or not np.isfinite(cf_prediction).all():
        raise ValueError('Nonfinite predictions: this run is not an evaluable result')
    metrics = error_metrics(prediction, truth, fixed_ranges, cell_ranges)
    metrics['direction_accuracy'] = direction_metrics(cf_prediction, cf_truth)
    config = dict(task=task, kappa=kappa, variant=variant, confound=confound, sigma=sigma,
                  model=model, seed=seed, dataset_seed=dataset_seed, epochs=epochs,
                  n_patients=n_patients, device=str(device), C=C, K=K, lr=lr,
                  d_model=d_model, d_state=d_state, n_layers=n_layers,
                  control_gru_hidden=control_gru_hidden,
                  horizon_h=horizon_h, out_dt=out_dt, threads=threads)
    result = dict(schema_version=1, smoke=smoke, config=config, metrics=metrics,
                  variant_label='control_gru_matched' if model == 'control_gru' else variant,
                  monolithic_control=(task == 'forecast' and model == 'control_gru'),
                  n_params=n_params,
                  architecture=dict(organ_dims=[4, 1, 1], graph_dropout=.1,
                                    control_gru_hidden=control_gru_hidden, crn_lite_hidden=96,
                                    crn_lite_gradient_reversal_lambda=.5,
                                    crn_lite_aux_mse_multiplier=.5),
                  graph=dict(organ_order=list(ORGANS), edges=[list(e) for e in graph_edges(variant, seed)]
                             if model.startswith('physiograph') else [],
                             n_edges=len(graph_edges(variant, seed)) if model.startswith('physiograph') else 0,
                             initialization='Dense initialization then selection of edge modules; shared parameters match.'),
                  dataset=dict(path=str(path), sha256=sha256(path), metadata=metadata,
                               n_train=len(data['tr']), n_test=len(data['te']),
                               train_indices=data['tr'].tolist(), test_indices=data['te'].tolist()),
                  normalization=dict(
                      reference_path=str(ref_path), reference_sha256=sha256(ref_path),
                      reference_metadata=ref_metadata, fixed_ranges=fixed_ranges,
                      per_kappa_ranges=cell_ranges, full_cell_ranges=organ_ranges(cell_truth),
                      fixed_range_scope='All patients and all time steps in the kappa=1 reference; task-specific factual/counterfactual targets.',
                      per_kappa_range_scope='Test patients, all time steps; matches frozen runner.',
                      range_epsilon=1e-6,
                      training='Frozen per-cell training-split mean and std+1e-6; only metric ranges are held fixed.',
                      training_mean=data['mean'].tolist(), training_std=data['std'].tolist()),
                  target_variance=dict(
                      scope='Evaluated held-out target cells, including dose axis for counterfactual.',
                      per_channel={c: float(np.var(truth[..., i].astype(np.float64)))
                                   for i, c in enumerate(CHANNELS)},
                      per_organ={o: float(np.var(truth[..., ix].astype(np.float64)))
                                 for o, ix in ORGANS.items()},
                      full_cell_per_channel={c: float(np.var(cell_truth[..., i].astype(np.float64)))
                                             for i, c in enumerate(CHANNELS)}),
                  overlap=overlap_diagnostics(path), policy_note=POLICY_NOTE,
                  protocol_notes=[
                      'Factual training, 70/30 patient split, no validation selection; Adam, gradient norm cap 1, frozen batch size 128.',
                      'Coupling LayerNorm is retained for all variants, including none (zero messages); frozen source bypasses it for none. This holds non-edge operations fixed.',
                      'Hidden sepsis and severity are excluded; inputs are six observations, dose and zero static feature.',
                      'Counterfactual truth receives constant dose from t=0; model context is factual, as in frozen H5. This context/truth mismatch limits causal interpretation.',
                      'Direction accuracy is evaluated on counterfactual rollouts even for forecast runs; forecast NRMSE uses factual truth.',
                      'CRN-lite uses gradient reversal lambda=0.5 and auxiliary MSE multiplier 0.5; it is not a full CRN positive control.'],
                  elapsed_seconds=time.perf_counter() - start,
                  timing=dict(data_seconds=generation_seconds, train_seconds=train_seconds,
                              evaluation_seconds=time.perf_counter() - evaluation_start))
    if out is not None:
        write_json(out, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task', choices=['forecast', 'counterfactual'], required=True)
    parser.add_argument('--kappa', type=float, default=1.)
    parser.add_argument('--variant', choices=VARIANTS, default='admissible')
    parser.add_argument('--confound', '--c', type=float, default=1.)
    parser.add_argument('--sigma', type=float, default=.03)
    parser.add_argument('--model', choices=MODELS, default='physiograph_gru')
    parser.add_argument('--allow_monolithic_control', action='store_true',
                        help='Explicitly permit the monolithic Control-GRU forecast comparison.')
    parser.add_argument('--control_gru_hidden', type=int, default=96,
                        help='Control-GRU hidden width; use 201 for the capacity-matched grid.')
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--dataset_seed', type=int, default=0)
    parser.add_argument('--epochs', type=int, default=60)
    parser.add_argument('--n_patients', type=int, default=400)
    parser.add_argument('--device', default='cpu')
    parser.add_argument('--out', required=True)
    parser.add_argument('--npz')
    parser.add_argument('--reference_npz')
    parser.add_argument('--C', type=int, default=12)
    parser.add_argument('--K', type=int, default=24)
    parser.add_argument('--lr', type=float, default=.002)
    parser.add_argument('--d_model', type=int, default=64)
    parser.add_argument('--d_state', type=int, default=32)
    parser.add_argument('--n_layers', type=int, default=2)
    parser.add_argument('--horizon_h', type=float, default=6.)
    parser.add_argument('--out_dt', type=float, default=300.)
    parser.add_argument('--threads', type=int, default=1)
    parser.add_argument('--smoke', action='store_true')
    result = run_cell(**vars(parser.parse_args()))
    print(json.dumps(dict(out=result['config'], smoke=result['smoke'],
                          variant_label=result['variant_label'],
                          macro_nrmse_fixed=result['metrics']['macro_nrmse_fixed']), allow_nan=False))


if __name__ == '__main__':
    main()
