"""Append monolithic Control-GRU cells to H3, preserving checked seed pairing.

The H3 summary does not contain absolute metrics per seed, so its sibling runs/
directory supplies the original none runs. Smoke cells may be appended for code
validation, but are never paired with scientific baseline runs.
"""
from __future__ import annotations

# Resolve all public modules and scratch from the release root.
import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[1]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH

import argparse
from collections import defaultdict
import copy
import itertools
import json
from pathlib import Path

import numpy as np

from sim_policy_ext import owned_path, sha256, write_json

ROOT = RELEASE_ROOT
H3_DEFAULT = Path(str(RELEASE_ROOT / 'runs/sim_forecast/h3_grid_partial.json'))
KAPPAS = (0., .1, .25, .5, .75, 1.)
SEEDS = (0, 1, 2, 3)
MATCH_CONFIG = ('task', 'kappa', 'seed', 'dataset_seed', 'confound', 'sigma',
                'epochs', 'n_patients', 'C', 'K', 'lr', 'd_model', 'd_state',
                'n_layers', 'horizon_h', 'out_dt', 'threads')
NRMSE = ('macro_nrmse_fixed', 'macro_nrmse_per_kappa',
         'organ_nrmse_fixed', 'organ_nrmse_per_kappa')


def summary(values):
    values = np.asarray(values, dtype=float)
    if not np.isfinite(values).all():
        raise ValueError('Nonfinite metric or parameter count')
    return dict(n=len(values), mean=float(values.mean()),
                std=float(values.std(ddof=1)) if len(values) > 1 else 0.)


def summarize_tree(values):
    first = values[0]
    if isinstance(first, dict):
        return {key: summarize_tree([value[key] for value in values])
                for key in first if isinstance(first[key], (dict, float, int, bool))}
    return summary(values)


def difference(run, baseline):
    return {key: ({organ: value - baseline['metrics'][key][organ]
                   for organ, value in run['metrics'][key].items()}
                  if isinstance(run['metrics'][key], dict)
                  else run['metrics'][key] - baseline['metrics'][key])
            for key in NRMSE}


def check_pair(run, baseline):
    for key in MATCH_CONFIG:
        if run['config'][key] != baseline['config'][key]:
            raise ValueError(f'Unmatched training configuration: {key}')
    for key in ('sha256', 'train_indices', 'test_indices', 'n_train', 'n_test'):
        if run['dataset'][key] != baseline['dataset'][key]:
            raise ValueError(f'Unmatched dataset or patient split: {key}')
    for key in ('reference_sha256', 'fixed_ranges', 'per_kappa_ranges',
                'full_cell_ranges', 'training_mean', 'training_std', 'range_epsilon',
                'fixed_range_scope', 'per_kappa_range_scope', 'training'):
        if run['normalization'][key] != baseline['normalization'][key]:
            raise ValueError(f'Unmatched normalization: {key}')


def _load_mono(source):
    source = Path(source)
    paths = sorted(source.glob('*.json')) if source.is_dir() else [source]
    runs, seen = [], set()
    for path in paths:
        run = json.loads(path.read_text())
        c = run['config']
        if (run.get('schema_version') != 1 or run.get('monolithic_control') is not True
                or c['task'] != 'forecast' or c['model'] != 'control_gru'):
            raise ValueError(f'Expected explicitly enabled monolithic forecast: {path}')
        key = (c['kappa'], c['seed'])
        if key not in set(itertools.product(KAPPAS, SEEDS)):
            raise ValueError(f'Unexpected monolithic cell: {key}')
        if key in seen:
            raise ValueError(f'Duplicate monolithic run: {key}')
        seen.add(key)
        runs.append((path, run))
    if not runs:
        raise ValueError(f'No monolithic runs found in {source}')
    if len({run['smoke'] for _, run in runs}) != 1:
        raise ValueError('Refusing to mix smoke and scientific monolithic runs')
    if len({run['normalization']['reference_sha256'] for _, run in runs}) != 1:
        raise ValueError('Monolithic runs use different normalization references')
    return runs


def aggregate(source, h3_path=H3_DEFAULT, out=ROOT / 'artifacts/full_grid/h3_grid_with_mono.json',
              baseline_runs=None, require_complete=False):
    owned_path(out)
    h3_path = Path(h3_path).resolve()
    baseline_runs = Path(baseline_runs) if baseline_runs else h3_path.parent / 'runs'
    h3 = json.loads(h3_path.read_text())
    if h3.get('task') != 'forecast' or h3.get('schema_version') != 1:
        raise ValueError('Expected the schema-1 H3 forecast grid')
    if any(c.get('model') == 'control_gru' or c['variant'] == 'control_gru'
           for c in h3['cells']):
        raise ValueError('H3 already contains monolithic cells')
    runs = _load_mono(source)
    groups = defaultdict(list)
    for path, run in runs:
        groups[run['config']['kappa']].append(run)

    # Read the absolute seed values, and verify they reproduce the supplied H3
    # summary before using them. Never infer paired differences from cell means.
    none_cells = {c['kappa']: c for c in h3['cells'] if c['variant'] == 'none'}
    baselines, baseline_paths = {}, []
    for kappa in sorted(groups):
        if kappa not in none_cells:
            raise ValueError(f'No none baseline at kappa={kappa}')
        cell = none_cells[kappa]
        group = []
        for seed in cell['seeds']:
            # simulator_grid uses the literal file suffix 0, .1, .25, .5, .75, 1.0.
            tag = '1.0' if kappa == 1 else f'{kappa:g}'
            path = baseline_runs / f'h3_k{tag}_none_s{seed}.json'
            baseline = json.loads(path.read_text())
            c = baseline['config']
            if (c['task'], c['kappa'], c['variant'], c['model'], c['seed']) != (
                    'forecast', kappa, 'none', 'physiograph_gru', seed):
                raise ValueError(f'Incorrect none baseline identity: {path}')
            if baseline['smoke'] != h3['smoke']:
                raise ValueError('Baseline smoke status differs from H3')
            if not baseline['smoke'] and baseline['n_params'] != 254086:
                raise ValueError('Scientific none baseline must have 254,086 parameters')
            baselines[kappa, seed] = baseline
            baseline_paths.append(path)
            group.append(baseline)
        reconstructed = summarize_tree([r['metrics'] for r in group])
        for metric in NRMSE:
            if reconstructed[metric] != cell['metrics'][metric]:
                raise ValueError(f'None seed metrics differ from H3 summary: {kappa}, {metric}')
        if summary([r['n_params'] for r in group]) != cell['n_params']:
            raise ValueError(f'None parameter counts differ from H3 summary: {kappa}')

    output = copy.deepcopy(h3)
    mono_smoke = runs[0][1]['smoke']
    output['smoke'] = bool(h3['smoke'] or mono_smoke)
    if output['smoke']:
        output['warning'] = ('SMOKE VALIDATION ONLY; appended control cells are not scientific '
                             'evidence. Smoke and scientific runs are never paired.')
    paired_count = 0
    for kappa, group in sorted(groups.items()):
        group.sort(key=lambda r: r['config']['seed'])
        paired, unpaired = [], []
        for run in group:
            seed = run['config']['seed']
            baseline = baselines.get((kappa, seed))
            if baseline is None or run['smoke'] != baseline['smoke']:
                if not run['smoke']:
                    raise ValueError(f'No matching scientific none run: kappa={kappa}, seed={seed}')
                unpaired.append(seed)
                continue
            check_pair(run, baseline)
            paired.append(dict(seed=seed, difference=difference(run, baseline)))
        paired_count += len(paired)
        output['cells'].append(dict(
            kappa=kappa, variant='control_gru', model='control_gru',
            monolithic_control=True, smoke=mono_smoke,
            seeds=[r['config']['seed'] for r in group],
            edges_by_seed={str(r['config']['seed']): [] for r in group},
            n_params=summary([r['n_params'] for r in group]),
            none_n_params=copy.deepcopy(none_cells[kappa]['n_params']),
            metrics=summarize_tree([r['metrics'] for r in group]),
            target_variance=summarize_tree([r['target_variance'] for r in group]),
            organ_ranges=summarize_tree([dict(
                fixed=r['normalization']['fixed_ranges'],
                per_kappa=r['normalization']['per_kappa_ranges'],
                full_cell=r['normalization']['full_cell_ranges']) for r in group]),
            paired_vs_none=dict(
                interpretation='control_gru minus none; positive NRMSE difference favors organ-wise factorisation.',
                per_seed=paired,
                summary=summarize_tree([p['difference'] for p in paired]) if paired else {},
                unpaired_seeds=unpaired,
                unpaired_reason='Smoke/scientific status differs or no baseline seed.' if unpaired else None)))
    seen = {(r['config']['kappa'], r['config']['seed']) for _, r in runs}
    expected = set(itertools.product(KAPPAS, SEEDS))
    missing = sorted(expected - seen)
    output['baseline_grid'] = {key: copy.deepcopy(h3[key]) for key in (
        'smoke', 'complete', 'observed_run_count', 'expected_run_count', 'missing_cells', 'unexpected_cells')}
    output['monolithic'] = dict(
        expected_run_count=24, observed_run_count=len(runs), paired_run_count=paired_count,
        missing_cells=[list(key) for key in missing], complete=seen == expected and not mono_smoke)
    output['expected_run_count'] = h3['expected_run_count'] + 24
    output['observed_run_count'] = h3['observed_run_count'] + len(runs)
    output['missing_cells'] += [[kappa, 'control_gru', seed] for kappa, seed in missing]
    output['complete'] = bool(h3['complete'] and seen == expected and paired_count == 24
                              and not output['smoke'])
    output['provenance'] = dict(
        h3_summary=dict(path=str(h3_path), sha256=sha256(h3_path)),
        none_runs=[dict(path=str(p.resolve()), sha256=sha256(p)) for p in baseline_paths],
        monolithic_runs=[dict(path=str(p.resolve()), sha256=sha256(p)) for p, _ in runs])
    if require_complete and not output['complete']:
        raise ValueError('Complete scientific aggregation requires matched 144 H3 + 24 monolithic nonsmoke runs')
    write_json(out, output)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--in', dest='source', default=ROOT / 'artifacts/full_grid/runs_mono')
    parser.add_argument('--h3', dest='h3_path', type=Path, default=H3_DEFAULT)
    parser.add_argument('--baseline_runs', type=Path)
    parser.add_argument('--out', type=Path, default=ROOT / 'artifacts/full_grid/h3_grid_with_mono.json')
    parser.add_argument('--require_complete', action='store_true')
    args = parser.parse_args()
    result = aggregate(**vars(args))
    print(json.dumps(dict(out=str(args.out), smoke=result['smoke'], grid_complete=result['complete'],
                          **result['monolithic'])))


if __name__ == '__main__':
    main()
