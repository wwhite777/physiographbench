"""Aggregate the shared H5 grid and legacy disclosure comparison separately."""
from __future__ import annotations

# Resolve all public modules and scratch from the release root.
import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[1]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH

import argparse
from collections import defaultdict
import csv
import itertools
import json
from pathlib import Path

import numpy as np

from sim_policy_ext2 import owned_path, write_json
from sim_grid_runner2 import MODELS, SIGMAS

CONFOUNDS = (0., .1, .25, .5, .75, 1.)
LEGACY_CONFOUNDS = (0., .5, 1.)
SEEDS = (0, 1, 2, 3)


def expected_cells():
    return ({('shared', *cell) for cell in itertools.product(CONFOUNDS, SIGMAS, MODELS, SEEDS)} |
            {('legacy', *cell) for cell in itertools.product(LEGACY_CONFOUNDS, (.03,), MODELS, SEEDS)})


def summary(values):
    present = np.asarray([value for value in values if value is not None], dtype=float)
    return dict(n=len(present), n_missing=len(values) - len(present),
                mean=float(present.mean()) if len(present) else None,
                std=(float(present.std(ddof=1)) if len(present) > 1 else
                     0. if len(present) else None))


def summarize_tree(values):
    first = next((value for value in values if value is not None), None)
    if isinstance(first, dict):
        return {key: summarize_tree([value.get(key) if value else None for value in values])
                for key in first if isinstance(first[key], (dict, float, int, bool))
                or first[key] is None}
    return summary(values)


def _load_runs(source):
    source = Path(source)
    paths = sorted(source.rglob('*.json')) if source.is_dir() else [source]
    runs = []
    for path in paths:
        obj = json.loads(path.read_text())
        candidates = obj.get('runs', []) if isinstance(obj, dict) else []
        if isinstance(obj, dict) and 'config' in obj and 'metrics' in obj:
            candidates = [obj]
        for candidate in candidates:
            if candidate.get('schema_version') == 2 and candidate['config']['task'] == 'counterfactual':
                runs.append(candidate)
    if not runs:
        raise ValueError(f'No simulator_controls counterfactual results found in {source}')
    if len({run['smoke'] for run in runs}) != 1:
        raise ValueError('Refusing to mix smoke and scientific result runs')
    seen = set()
    for run in runs:
        c = run['config']
        key = tuple(c[name] for name in ('cf_protocol', 'confound', 'sigma', 'model', 'seed'))
        if key in seen:
            raise ValueError(f'Duplicate training run: {key}')
        if run['cf_protocol'] != c['cf_protocol']:
            raise ValueError('Top-level and config counterfactual protocols differ')
        if run['dataset']['metadata']['cf_protocol'] != c['cf_protocol']:
            raise ValueError('Result and dataset counterfactual protocols differ')
        seen.add(key)
    return runs


def aggregate(source, h5_path, overlap_path, require_complete=False):
    runs = _load_runs(source)
    groups = defaultdict(list)
    policies = defaultdict(list)
    for run in runs:
        c = run['config']
        policy = tuple(c[name] for name in ('cf_protocol', 'confound', 'sigma'))
        groups[(*policy, c['model'])].append(run)
        policies[policy].append(run)
    if len({run['normalization']['reference_sha256'] for run in runs}) != 1:
        raise ValueError('H5 runs use different fixed normalization references')
    for policy, group in policies.items():
        signatures = {tuple(r['config'][key] for key in (
            'kappa', 'variant', 'dataset_seed', 'epochs', 'n_patients', 'C', 'K', 'lr',
            'd_model', 'd_state', 'n_layers', 'horizon_h', 'out_dt')) + (r['dataset']['sha256'],)
            for r in group}
        if len(signatures) != 1:
            raise ValueError(f'H5 data or training configuration unmatched at {policy}')
        for seed in {r['config']['seed'] for r in group}:
            same_seed = [r for r in group if r['config']['seed'] == seed]
            if len({tuple(r['dataset']['test_indices']) for r in same_seed}) != 1:
                raise ValueError(f'Unmatched test splits at {policy}, seed={seed}')
    output = dict(schema_version=2, task='counterfactual', smoke=runs[0]['smoke'],
                  warning='SMOKE ONLY; not scientific evidence.' if runs[0]['smoke'] else None,
                  uncertainty='Sample std over training seeds (ddof=1); singleton std=0 is a placeholder. '
                              'This is not patient sampling uncertainty. Null restricted accuracies are '
                              'excluded from means and counted in n_missing.',
                  expected_training_seeds=list(SEEDS), expected_run_count=432, cells=[])
    for (protocol, confound, sigma, model), group in sorted(groups.items()):
        group.sort(key=lambda r: r['config']['seed'])
        output['cells'].append(dict(
            cf_protocol=protocol, confound=confound, sigma=sigma, model=model,
            seeds=[r['config']['seed'] for r in group],
            metrics=summarize_tree([r['metrics'] for r in group]),
            support_restricted_by_seed=[dict(
                seed=r['config']['seed'], **r['metrics']['support_restricted_direction_accuracy'])
                for r in group],
            target_variance=summarize_tree([r['target_variance'] for r in group]),
            n_params=summary([r['n_params'] for r in group])))
    seen = {tuple(r['config'][name] for name in
                  ('cf_protocol', 'confound', 'sigma', 'model', 'seed')) for r in runs}
    expected = expected_cells()
    output.update(observed_run_count=len(seen), complete=seen == expected,
                  missing_cells=[list(cell) for cell in sorted(expected - seen)],
                  unexpected_cells=[list(cell) for cell in sorted(seen - expected)],
                  protocols={})
    for protocol in ('shared', 'legacy'):
        wanted = {cell for cell in expected if cell[0] == protocol}
        actual = {cell for cell in seen if cell[0] == protocol}
        output['protocols'][protocol] = dict(expected_run_count=len(wanted),
                                            observed_run_count=len(actual), complete=actual == wanted)
    if require_complete and (not output['complete'] or output['smoke']):
        raise ValueError('Full scientific H5 aggregation requires 384 shared + 48 legacy nonsmoke runs')
    write_json(h5_path, output)
    columns = ['smoke', 'cf_protocol', 'confound', 'sigma', 'dataset_seed',
               'dataset_sha256', 'n_patients', 'corr_severity_dose',
               'severity_cut_1', 'severity_cut_2', 'tercile', 'tercile_n',
               'dose_q05', 'dose_q25', 'dose_q50', 'dose_q75', 'dose_q95',
               'supported_low', 'supported_high', 'fraction_grid_supported',
               'support_0', 'support_005', 'support_01', 'support_02', 'support_04']
    rows = []
    for (protocol, confound, sigma), group in sorted(policies.items()):
        run = group[0]
        c, diagnostic = run['config'], run['overlap']
        for tercile in diagnostic['terciles']:
            row = dict(smoke=run['smoke'], cf_protocol=protocol, confound=confound, sigma=sigma,
                       dataset_seed=c['dataset_seed'], dataset_sha256=run['dataset']['sha256'],
                       n_patients=diagnostic['n_patients'],
                       corr_severity_dose=diagnostic['corr_severity_dose'],
                       severity_cut_1=diagnostic['severity_cutpoints'][0],
                       severity_cut_2=diagnostic['severity_cutpoints'][1],
                       tercile=tercile['tercile'], tercile_n=tercile['n_patients'],
                       supported_low=tercile['supported_dose_range'][0],
                       supported_high=tercile['supported_dose_range'][1],
                       fraction_grid_supported=tercile['fraction_grid_supported'])
            row.update({column: tercile['dose_quantiles'][q] for column, q in zip(
                ('dose_q05', 'dose_q25', 'dose_q50', 'dose_q75', 'dose_q95'),
                ('5', '25', '50', '75', '95'))})
            row.update(dict(zip(columns[-5:], tercile['supported_grid'])))
            rows.append(row)
    path = owned_path(overlap_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    return dict(h5_runs=len(seen), overlap_rows=len(rows), smoke=output['smoke'],
                complete=output['complete'], protocols=output['protocols'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--in', dest='source', required=True)
    parser.add_argument('--out', nargs=2, metavar=('H5_JSON', 'OVERLAP_CSV'), required=True)
    parser.add_argument('--require_complete', action='store_true')
    args = parser.parse_args()
    print(json.dumps(aggregate(args.source, *args.out, require_complete=args.require_complete)))


if __name__ == '__main__':
    main()
