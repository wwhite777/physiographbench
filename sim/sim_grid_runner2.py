"""simulator_grid matched training with protocol-specific future targets and support metrics."""
from __future__ import annotations

# Resolve all public modules and scratch from the release root.
import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[1]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import torch

from sim_policy_ext2 import (CHANNELS, ORGANS, POLICY_NOTE, ROOT, PROTOCOLS,
    make_dataset_grid, overlap_diagnostics, owned_path, sha256, write_json,
    validate_manifest, manifest_path, code_hashes)
from sim_grid_runner import (VARIANTS, MODELS, build_model, graph_edges, organ_ranges,
    error_metrics, direction_metrics, predict)
from cvsim_counterfactual_runner import load_cvsim, train

SIGMAS = (0., .08, .15, .25)


def support_for_patients(severity, factual_doses, doses, indices):
    """Empirical full-dataset tercile support, selected for evaluation patients."""
    cutpoints = np.quantile(severity, [1 / 3, 2 / 3])
    groups = np.searchsorted(cutpoints, severity, side='right')
    supported, ranges = [], []
    for tercile in range(3):
        selected = factual_doses[groups == tercile]
        if not len(selected):
            raise ValueError('An empty severity tercile prevents support restriction')
        low, high = np.quantile(selected, [.05, .95])
        ranges.append([float(low), float(high)])
        supported.append((doses >= low) & (doses <= high))
    supported = np.asarray(supported)
    return supported[groups[indices]], dict(
        severity_cutpoints=cutpoints.tolist(), supported_dose_ranges=ranges,
        supported_grid=supported.tolist(),
        n_supported_tercile_dose_cells=int(supported.sum()),
        n_tercile_dose_cells=int(supported.size),
        fraction_grid_supported_by_tercile=supported.mean(axis=1).tolist(),
        all_terciles_full_support=bool(supported.all()))


def support_direction_metrics(prediction, truth, supported):
    """simulator_grid exact-sign accuracy over supported patient/adjacent-dose pairs.

    A metric cell is a patient x adjacent pair x time x channel. Every numerator
    and denominator counts these cells; pair and tercile/dose counts also appear.
    No supported pairs produces null accuracy, never a zero or a perfect score.
    """
    if prediction.shape != truth.shape or supported.shape != prediction.shape[:2]:
        raise ValueError('Expected matching (patients,doses,time,channels) and support')
    correct = np.sign(np.diff(prediction, axis=1)) == np.sign(np.diff(truth, axis=1))
    selected = supported[:, :-1] & supported[:, 1:]
    cells = correct[selected]  # (supported patient/pairs, time, channel)
    used, total = int(cells.size), int(correct.size)
    return dict(
        cell_mean=float(cells.mean()) if used else None,
        n_correct_cells=int(cells.sum()), n_cells=used, n_cells_denominator=total,
        fraction_cells_used=used / total,
        n_patient_adjacent_pairs=int(selected.sum()),
        n_patient_adjacent_pairs_denominator=int(selected.size),
        per_channel={c: float(cells[..., i].mean()) if used else None
                     for i, c in enumerate(CHANNELS)},
        per_organ={o: float(cells[..., ix].mean()) if used else None
                   for o, ix in ORGANS.items()},
        zero_sign_rule='Exact numpy.sign equality; zero counts as a third sign.',
        cell_definition='patient x adjacent dose pair x evaluated time x channel',
        support_rule='Both doses inside the patient severity tercile empirical 5-95% factual-dose range.')


def _dataset(path, *, kappa, confound, sigma, seed, n_patients, horizon_h, out_dt, cf_protocol, C, K):
    config = dict(kappa=float(kappa), confound=float(confound), sigma=float(sigma), seed=seed,
                  n_patients=n_patients, horizon_h=float(horizon_h), out_dt=float(out_dt),
                  cf_protocol=cf_protocol, C=C, K=K)
    if path is None:
        key = hashlib.sha256(json.dumps(dict(config, code_sha256=code_hashes()), sort_keys=True).encode()).hexdigest()[:20]
        path = ROOT / 'artifacts/datasets' / f'{key}.npz'
    else:
        path = Path(path).resolve()
    if not path.exists():
        make_dataset_grid(**config, out_path=path)
    manifest = validate_manifest(path)
    with np.load(path) as packed:
        if packed['factual'].shape[0] != n_patients:
            raise ValueError(f'{path}: patient count differs from --n_patients')
        metadata = json.loads(str(packed['metadata_json'])) if 'metadata_json' in packed else {}
        if not metadata:
            raise ValueError(f'{path}: missing generation metadata')
        if metadata:
            for name, value in config.items():
                if metadata[name] != value or manifest[name] != value:
                    raise ValueError(f'{path}: {name}={metadata[name]} but requested {value}')
            if metadata['source_sha256'] != sha256(
                    str(RELEASE_ROOT / 'src/cvsim_hemodynamics_simulator.py')):
                raise ValueError('Cached dataset uses a different simulator')
    return path, metadata


def run_cell(*, task='forecast', kappa=1., variant='admissible', confound=1., sigma=.03,
             model='physiograph_gru', seed=0, dataset_seed=0, epochs=60, n_patients=400,
             device='cpu', out=None, npz=None, reference_npz=None, C=12, K=24,
             lr=.002, d_model=64, d_state=32, n_layers=2, horizon_h=6., out_dt=300.,
             threads=1, smoke=False, cf_protocol='shared'):
    start = time.perf_counter()
    if cf_protocol not in PROTOCOLS:
        raise ValueError(cf_protocol)
    if str(device) != 'cpu':
        raise ValueError('simulator_controls is CPU only')
    if task not in ('forecast', 'counterfactual'):
        raise ValueError(task)
    if task == 'forecast' and model != 'physiograph_gru':
        raise ValueError('The matched H3 graph grid uses physiograph_gru for every variant')
    if task == 'counterfactual' and variant != 'admissible':
        raise ValueError('The H5 model grid uses the admissible variant')
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
                              horizon_h=horizon_h, out_dt=out_dt,
                              cf_protocol=cf_protocol, C=C, K=K)
    # Preserve simulator_grid's single kappa=1, c=1, sigma=.03 LEGACY fixed-range
    # reference across both protocols. It is one of the three disclosure datasets;
    # it sets only metric denominators, never shared-history evaluation targets.
    ref_path, ref_metadata = _dataset(
        reference_npz, kappa=1., confound=1., sigma=.03, seed=dataset_seed,
        n_patients=n_patients, horizon_h=horizon_h, out_dt=out_dt,
        cf_protocol='legacy', C=C, K=K)
    data = load_cvsim(path, C, seed)
    if C + K > data['T']:
        raise ValueError(f'C+K={C + K} exceeds T={data["T"]}')
    with np.load(ref_path) as reference:
        ref_target = reference['factual'][..., :6] if task == 'forecast' else reference['counterfactual']
        fixed_ranges = organ_ranges(ref_target)
    cell_truth = data['obs'] if task == 'forecast' else data['cf']
    cell_ranges = organ_ranges(cell_truth[data['te']])  # frozen H3/H5 denominator scope
    generation_seconds = time.perf_counter() - start
    instance = build_model(model, variant, seed, d_model, d_state, n_layers)
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
    with np.load(path) as packed:
        np.testing.assert_array_equal(packed['counterfactual_target'],
                                      packed['counterfactual'][:, :, C:C + K])
        support, support_info = support_for_patients(
            packed['severity'], packed['factual_dose'], packed['cf_doses'], data['te'])
    metrics['support_restricted_direction_accuracy'] = support_direction_metrics(
        cf_prediction, cf_truth, support)
    metrics['support_restricted_direction_accuracy']['support'] = support_info
    config = dict(task=task, cf_protocol=cf_protocol, kappa=kappa, variant=variant, confound=confound, sigma=sigma,
                  model=model, seed=seed, dataset_seed=dataset_seed, epochs=epochs,
                  n_patients=n_patients, device=str(device), C=C, K=K, lr=lr,
                  d_model=d_model, d_state=d_state, n_layers=n_layers,
                  horizon_h=horizon_h, out_dt=out_dt, threads=threads)
    result = dict(schema_version=2, cf_protocol=cf_protocol, smoke=smoke, config=config, metrics=metrics,
                  n_params=n_params,
                  architecture=dict(organ_dims=[4, 1, 1], graph_dropout=.1,
                                    control_gru_hidden=96, crn_lite_hidden=96,
                                    crn_lite_gradient_reversal_lambda=.5,
                                    crn_lite_aux_mse_multiplier=.5),
                  graph=dict(organ_order=list(ORGANS), edges=[list(e) for e in graph_edges(variant, seed)]
                             if model.startswith('physiograph') else [],
                             n_edges=len(graph_edges(variant, seed)) if model.startswith('physiograph') else 0,
                             initialization='Dense initialization then selection of edge modules; shared parameters match.'),
                  dataset=dict(path=str(path), sha256=sha256(path), metadata=metadata,
                               manifest_path=str(manifest_path(path)),
                               manifest_sha256=sha256(manifest_path(path)),
                               n_train=len(data['tr']), n_test=len(data['te']),
                               train_indices=data['tr'].tolist(), test_indices=data['te'].tolist()),
                  normalization=dict(
                      reference_path=str(ref_path), reference_sha256=sha256(ref_path),
                      reference_metadata=ref_metadata, reference_cf_protocol='legacy',
                      fixed_ranges=fixed_ranges,
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
                      ('Shared history: factual warm-up and schedule before C*out_dt; constant alternative dose from C*out_dt. Factual dose remains zero throughout the default context.' if cf_protocol == 'shared' else 'Legacy: alternative dose since warm-up; factual model context differs from target history.'),
                      'Fixed NRMSE denominators retain the simulator_grid legacy c=1, sigma=.03 reference across both protocols.',
                      'Support uses each severity tercile empirical 5-95% factual-dose range over all generated patients; retain adjacent pairs only when both doses are supported.',
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
    parser.add_argument('--cf_protocol', choices=PROTOCOLS, default='shared')
    parser.add_argument('--task', choices=['forecast', 'counterfactual'], required=True)
    parser.add_argument('--kappa', type=float, default=1.)
    parser.add_argument('--variant', choices=VARIANTS, default='admissible')
    parser.add_argument('--confound', '--c', type=float, default=1.)
    parser.add_argument('--sigma', type=float, default=.03)
    parser.add_argument('--model', choices=MODELS, default='physiograph_gru')
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
                          macro_nrmse_fixed=result['metrics']['macro_nrmse_fixed']), allow_nan=False))


if __name__ == '__main__':
    main()
