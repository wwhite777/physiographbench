"""Pre-neural E1 ridge check, patient-held-out gains, and observation-rate lens."""
from __future__ import annotations

import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[2]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH

import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np

from sim_positive_control import (
    C, K, ROOT, clinical_rates, generate, patient_split, remask, sha256,
    source_hashes, target_probabilities, write_json)

ALPHA = 10.
GAIN_THRESHOLD = .05
NULL_MAX_GAIN = .02


def features(data, channel, augmented=False):
    """Only target history and shared controls; optionally source *context*."""
    parts = [data['values'][:, :C, channel], data['mask'][:, :C, channel],
             data['controls'][:, :C + K, 0]]
    if augmented:
        parts.extend([data['values'][:, :C, :4].reshape(len(data['values']), -1),
                      data['mask'][:, :C, :4].reshape(len(data['values']), -1)])
    return np.concatenate(parts, axis=1).astype(np.float64)


def ridge_predict(x_train, y_train, x_test, alpha=ALPHA):
    """Training-only feature standardization, unpenalized intercept, fixed alpha."""
    mean = x_train.mean(axis=0)
    scale = x_train.std(axis=0)
    scale[scale < 1e-8] = 1.
    train = (x_train - mean) / scale
    test = (x_test - mean) / scale
    y_mean = y_train.mean(axis=0)
    coefficients = np.linalg.solve(train.T @ train + alpha * np.eye(train.shape[1]),
                                   train.T @ (y_train - y_mean))
    return test @ coefficients + y_mean


def score(truth, prediction):
    squared = (truth - prediction) ** 2
    denominator = float(((truth - truth.mean()) ** 2).sum())
    return dict(rmse=float(np.sqrt(squared.mean())),
                r2=1. - float(squared.sum()) / denominator if denominator else None)


def bootstrap_gain(truth, local, augmented, seed=187, repeats=1000):
    """Patient resampling conditional on these fitted models; no neural claims."""
    local_mse = ((truth - local) ** 2).mean(axis=1)
    augmented_mse = ((truth - augmented) ** 2).mean(axis=1)
    draws = np.random.default_rng(seed).integers(0, len(truth), (repeats, len(truth)))
    gains = 1. - np.sqrt(augmented_mse[draws].mean(1) / local_mse[draws].mean(1))
    return np.quantile(gains, [.025, .975]).tolist()


def evaluate(data, reference_ranges, split_seed=0, uncertainty=True):
    train, test = patient_split(len(data['values']), split_seed)
    results = {}
    for name, channel in (('renal', 4), ('metabolic', 5)):
        labels = data['truth'][:, C:C + K, channel].astype(np.float64)
        predictions = {}
        for kind, augmented in (('local', False), ('source_augmented', True)):
            x = features(data, channel, augmented)
            predictions[kind] = ridge_predict(x[train], labels[train], x[test])
        local = score(labels[test], predictions['local'])
        source = score(labels[test], predictions['source_augmented'])
        results[name] = dict(
            local=local, source_augmented=source,
            delta_r2=source['r2'] - local['r2'],
            rmse_absolute_reduction=local['rmse'] - source['rmse'],
            rmse_relative_reduction=1. - source['rmse'] / local['rmse'],
            n_test_patients=len(test), n_target_cells=int(labels[test].size),
            local_features=features(data, channel).shape[1],
            augmented_features=features(data, channel, True).shape[1])
        if uncertainty:
            results[name]['relative_reduction_patient_bootstrap_95_ci'] = bootstrap_gain(
                labels[test], predictions['local'], predictions['source_augmented'])
    macro = {kind: float(np.mean([results[name][kind]['rmse'] / reference_ranges[name]
                                 for name in results]))
             for kind in ('local', 'source_augmented')}
    macro['rmse_relative_reduction'] = 1. - macro['source_augmented'] / macro['local']
    return dict(per_organ=results, target_macro_nrmse_fixed=macro,
                n_train=len(train), n_test=len(test),
                train_indices=train.tolist(), test_indices=test.tolist())


def check(n_patients=400, kappas=(0., 1.), split_seed=0, dataset_seed=0,
          lens=True, out=None):
    start = time.perf_counter()
    kappas = tuple(float(kappa) for kappa in kappas)
    if len(set(kappas)) != len(kappas) or any(k not in (0., .5, 1.) for k in kappas):
        raise ValueError('Use distinct registered kappa values from {0,0.5,1}')
    if n_patients < 4:
        raise ValueError('Need at least four patients')
    datasets = {1.: generate(n_patients, 1., dataset_seed)}
    reference = datasets[1.]['truth']
    ranges = {name: float(np.ptp(reference[..., channel])) + 1e-6
              for name, channel in (('renal', 4), ('metabolic', 5))}
    cells = []
    for kappa in kappas:
        data = datasets.get(kappa)
        if data is None:
            data = generate(n_patients, kappa, dataset_seed)
            datasets[kappa] = data
        cell = evaluate(data, ranges, split_seed)
        cell['kappa'] = kappa
        cell['generation_metadata'] = json.loads(str(data['metadata_json']))
        cells.append(cell)
        print(json.dumps(dict(kappa=kappa, n_patients=n_patients,
                              gains={name: value['rmse_relative_reduction']
                                     for name, value in cell['per_organ'].items()})), flush=True)
    endpoint = next((cell for cell in cells if cell['kappa'] == 1.), None)
    null = next((cell for cell in cells if cell['kappa'] == 0.), None)
    endpoint_pass = (endpoint is not None
                     and all(value['rmse_relative_reduction'] >= GAIN_THRESHOLD
                             for value in endpoint['per_organ'].values())
                     and endpoint['target_macro_nrmse_fixed']['rmse_relative_reduction']
                     >= GAIN_THRESHOLD)
    null_pass = (null is not None
                and all(value['rmse_relative_reduction'] <= NULL_MAX_GAIN
                        for value in null['per_organ'].values()))
    qualification = dict(
        material_gain_threshold=GAIN_THRESHOLD, kappa_zero_max_positive_gain=NULL_MAX_GAIN,
        endpoint_pass=endpoint_pass, null_pass=null_pass,
        qualification_set=(n_patients == 400 and split_seed == 0 and dataset_seed == 0
                           and endpoint is not None and null is not None),
        passed=bool(endpoint_pass and null_pass and n_patients == 400
                    and split_seed == 0 and dataset_seed == 0))
    observation_lens = None
    if lens:
        train_rate = float(target_probabilities()[0])
        sweep = []
        for probability in (0., .01, .035, .05, train_rate, .10, .25, .50, 1.):
            cell = evaluate(remask(datasets[1.], [probability, probability]),
                            ranges, split_seed, uncertainty=False)
            sweep.append(dict(common_target_probability=probability,
                              per_organ=cell['per_organ'],
                              target_macro_nrmse_fixed=cell['target_macro_nrmse_fixed']))
        hourly = target_probabilities(hourly_matched=True)
        observation_lens = dict(
            interpretation='Oracle-only; common-p sweep is per five-minute row, not hourly.',
            common_probability_sweep=sweep,
            largest_tested_probability_meeting_5pct={
                organ: max((cell['common_target_probability'] for cell in sweep
                            if cell['per_organ'][organ]['rmse_relative_reduction'] >= .05),
                           default=None) for organ in ('renal', 'metabolic')},
            hourly_matched=dict(probabilities=hourly.tolist(),
                                evaluation=evaluate(remask(datasets[1.], hourly),
                                                    ranges, split_seed)))
    result = dict(
        schema_version=1, task='positive control E1 pre-neural oracle',
        config=dict(n_patients=n_patients, kappas=list(kappas), split_seed=split_seed,
                    dataset_seed=dataset_seed, alpha=ALPHA, C=C, K=K,
                    target_probabilities=target_probabilities().tolist()),
        clinical_rates=clinical_rates(), reference_ranges=ranges, cells=cells,
        qualification=qualification, observation_lens=observation_lens,
        uncertainty='1000 held-out-patient bootstrap draws, fixed fits; no refitting uncertainty.',
        source_sha256={**source_hashes(), str(Path(__file__).resolve()): sha256(__file__)},
        design_sha256=sha256(ROOT / 'DESIGN_E1.md'),
        versions=dict(python=sys.version.split()[0], numpy=np.__version__),
        elapsed_seconds=time.perf_counter() - start)
    if out is not None:
        write_json(out, result)
    print(json.dumps(dict(qualification=qualification,
                          elapsed_seconds=result['elapsed_seconds']), allow_nan=False), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--n-patients', type=int, default=400)
    parser.add_argument('--kappas', type=float, nargs='+', default=[0., 1.])
    parser.add_argument('--split-seed', type=int, default=0)
    parser.add_argument('--dataset-seed', type=int, default=0)
    parser.add_argument('--no-lens', dest='lens', action='store_false')
    parser.add_argument('--out', required=True)
    check(**vars(parser.parse_args()))


if __name__ == '__main__':
    main()
