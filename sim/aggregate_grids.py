"""Aggregate cell JSONs; preserve seed pairing and label incomplete smoke grids."""
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

from sim_policy_ext import owned_path, write_json
from sim_grid_runner import MODELS, VARIANTS

KAPPAS = (0., .1, .25, .5, .75, 1.)
CONFOUNDS = KAPPAS
SIGMAS = (0., .08, .15)
SEEDS = (0, 1, 2, 3)


def summary(values):
    values = np.asarray(values, dtype=float)
    return dict(n=len(values), mean=float(values.mean()),
                std=float(values.std(ddof=1)) if len(values) > 1 else 0.)


def summarize_tree(values):
    first = values[0]
    if isinstance(first, dict):
        return {key: summarize_tree([value[key] for value in values])
                for key in first if isinstance(first[key], (dict, float, int, bool))}
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
            if candidate.get('schema_version') == 1 and 'config' in candidate:
                runs.append(candidate)
    if not runs:
        raise ValueError(f'No cell results found in {source}')
    if len({run['smoke'] for run in runs}) != 1:
        raise ValueError('Refusing to mix smoke and scientific result runs')
    seen = set()
    for run in runs:
        c = run['config']
        key = ((c['task'], c['kappa'], c['variant'], c['seed']) if c['task'] == 'forecast'
               else (c['task'], c['confound'], c['sigma'], c['model'], c['seed']))
        if key in seen:
            raise ValueError(f'Duplicate training run: {key}')
        seen.add(key)
    return runs


def aggregate(source, h3_path, h5_path, overlap_path, require_complete=False):
    runs = _load_runs(source)
    h3_groups, h5_groups = defaultdict(list), defaultdict(list)
    for run in runs:
        c = run['config']
        if c['task'] == 'forecast':
            h3_groups[(c['kappa'], c['variant'])].append(run)
        else:
            h5_groups[(c['confound'], c['sigma'], c['model'])].append(run)
    common = dict(schema_version=1, smoke=runs[0]['smoke'],
                  warning='SMOKE ONLY; not scientific evidence.' if runs[0]['smoke'] else None,
                  uncertainty='Sample std over training seeds (ddof=1); singleton std=0 is a placeholder. This is not patient sampling uncertainty.',
                  expected_training_seeds=list(SEEDS))
    h3 = dict(common, task='forecast', cells=[], expected_run_count=144)
    h5 = dict(common, task='counterfactual', cells=[], expected_run_count=288)
    forecast_runs = [run for run in runs if run['config']['task'] == 'forecast']
    # The fixed reference must really be fixed across the complete H3 experiment.
    if len({run['normalization']['reference_sha256'] for run in forecast_runs}) > 1:
        raise ValueError('H3 runs use different normalization references')
    for kappa in {key[0] for key in h3_groups}:
        same_kappa = [r for r in forecast_runs if r['config']['kappa'] == kappa]
        signatures = {
            tuple(r['config'][key] for key in ('model', 'dataset_seed', 'confound', 'sigma',
                                               'epochs', 'n_patients', 'C', 'K', 'lr',
                                               'd_model', 'd_state', 'n_layers', 'horizon_h', 'out_dt'))
            + (r['dataset']['sha256'],)
            for r in same_kappa}
        if len(signatures) != 1:
            raise ValueError(f'H3 data or training configuration is unmatched at kappa={kappa}')
    counterfactual_runs = [run for run in runs if run['config']['task'] == 'counterfactual']
    if len({run['normalization']['reference_sha256'] for run in counterfactual_runs}) > 1:
        raise ValueError('H5 runs use different normalization references')
    for confound, sigma in {key[:2] for key in h5_groups}:
        same_policy = [r for r in counterfactual_runs
                       if (r['config']['confound'], r['config']['sigma']) == (confound, sigma)]
        signatures = {
            tuple(r['config'][key] for key in ('kappa', 'variant', 'dataset_seed', 'epochs',
                                               'n_patients', 'C', 'K', 'lr', 'd_model',
                                               'd_state', 'n_layers', 'horizon_h', 'out_dt'))
            + (r['dataset']['sha256'],)
            for r in same_policy}
        if len(signatures) != 1:
            raise ValueError(f'H5 data or training configuration is unmatched at c={confound}, sigma={sigma}')
    for (kappa, variant), group in sorted(h3_groups.items()):
        group.sort(key=lambda r: r['config']['seed'])
        baseline = {r['config']['seed']: r for r in h3_groups.get((kappa, 'none'), [])}
        paired = []
        for run in group:
            seed = run['config']['seed']
            if seed in baseline:
                other = baseline[seed]
                if (run['dataset']['sha256'] != other['dataset']['sha256'] or
                        run['dataset']['test_indices'] != other['dataset']['test_indices']):
                    raise ValueError('Cannot pair different datasets or test splits')
                difference = {key: run['metrics'][key] - other['metrics'][key]
                              for key in ('macro_nrmse_fixed', 'macro_nrmse_per_kappa')}
                for metric in ('organ_nrmse_fixed', 'organ_nrmse_per_kappa'):
                    difference[metric] = {o: value - other['metrics'][metric][o]
                                          for o, value in run['metrics'][metric].items()}
                paired.append(dict(seed=seed, difference=difference))
        h3['cells'].append(dict(
            kappa=kappa, variant=variant, seeds=[r['config']['seed'] for r in group],
            edges_by_seed={str(r['config']['seed']): r['graph']['edges'] for r in group},
            n_params=summary([r['n_params'] for r in group]),
            metrics=summarize_tree([r['metrics'] for r in group]),
            target_variance=summarize_tree([r['target_variance'] for r in group]),
            organ_ranges=summarize_tree([dict(
                fixed=r['normalization']['fixed_ranges'],
                per_kappa=r['normalization']['per_kappa_ranges'],
                full_cell=r['normalization']['full_cell_ranges']) for r in group]),
            paired_vs_none=dict(
                interpretation='variant minus none; negative NRMSE difference favors variant.',
                per_seed=paired,
                summary=summarize_tree([p['difference'] for p in paired]) if paired else {},
                unpaired_seeds=[r['config']['seed'] for r in group if r['config']['seed'] not in baseline])))
    for (confound, sigma, model), group in sorted(h5_groups.items()):
        group.sort(key=lambda r: r['config']['seed'])
        h5['cells'].append(dict(confound=confound, sigma=sigma, model=model,
                               seeds=[r['config']['seed'] for r in group],
                               metrics=summarize_tree([r['metrics'] for r in group]),
                               target_variance=summarize_tree([r['target_variance'] for r in group]),
                               n_params=summary([r['n_params'] for r in group])))
    h3_seen = {(r['config']['kappa'], r['config']['variant'], r['config']['seed']) for r in forecast_runs}
    h5_seen = {(r['config']['confound'], r['config']['sigma'], r['config']['model'], r['config']['seed'])
               for r in runs if r['config']['task'] == 'counterfactual'}
    for output, seen, expected in (
            (h3, h3_seen, set(itertools.product(KAPPAS, VARIANTS, SEEDS))),
            (h5, h5_seen, set(itertools.product(CONFOUNDS, SIGMAS, MODELS, SEEDS)))):
        output['observed_run_count'] = len(seen)
        output['missing_cells'] = [list(cell) for cell in sorted(expected - seen)]
        output['unexpected_cells'] = [list(cell) for cell in sorted(seen - expected)]
        output['complete'] = seen == expected
    if require_complete and (not h3['complete'] or not h5['complete'] or common['smoke']):
        raise ValueError('Full scientific aggregation requires 144+288 nonsmoke runs')
    write_json(h3_path, h3)
    write_json(h5_path, h5)
    columns = ['smoke', 'confound', 'sigma', 'dataset_seed', 'dataset_sha256', 'n_patients',
               'corr_severity_dose', 'severity_cut_1', 'severity_cut_2', 'tercile', 'tercile_n',
               'dose_q05', 'dose_q25', 'dose_q50', 'dose_q75', 'dose_q95',
               'supported_low', 'supported_high', 'fraction_grid_supported',
               'support_0', 'support_005', 'support_01', 'support_02', 'support_04']
    rows, overlap_seen = [], set()
    for run in sorted(runs, key=lambda r: (r['config']['confound'], r['config']['sigma'])):
        c = run['config']
        if c['task'] != 'counterfactual':
            continue
        key = (c['confound'], c['sigma'], run['dataset']['sha256'])
        if key in overlap_seen:
            continue
        overlap_seen.add(key)
        diagnostic = run['overlap']
        for tercile in diagnostic['terciles']:
            row = dict(smoke=run['smoke'], confound=c['confound'], sigma=c['sigma'],
                       dataset_seed=c['dataset_seed'], dataset_sha256=run['dataset']['sha256'],
                       n_patients=diagnostic['n_patients'],
                       corr_severity_dose=diagnostic['corr_severity_dose'],
                       severity_cut_1=diagnostic['severity_cutpoints'][0],
                       severity_cut_2=diagnostic['severity_cutpoints'][1],
                       tercile=tercile['tercile'], tercile_n=tercile['n_patients'],
                       supported_low=tercile['supported_dose_range'][0],
                       supported_high=tercile['supported_dose_range'][1],
                       fraction_grid_supported=tercile['fraction_grid_supported'])
            row.update({column: tercile['dose_quantiles'][quantile]
                        for column, quantile in zip(columns[11:16], ('5', '25', '50', '75', '95'))})
            row.update(dict(zip(columns[-5:], tercile['supported_grid'])))
            rows.append(row)
    path = owned_path(overlap_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    return dict(h3_runs=len(h3_seen), h5_runs=len(h5_seen), overlap_rows=len(rows),
                smoke=common['smoke'], h3_complete=h3['complete'], h5_complete=h5['complete'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--in', dest='source', required=True)
    parser.add_argument('--out', nargs=3, metavar=('H3_JSON', 'H5_JSON', 'OVERLAP_CSV'), required=True)
    parser.add_argument('--require_complete', action='store_true')
    args = parser.parse_args()
    print(json.dumps(aggregate(args.source, *args.out, require_complete=args.require_complete)))


if __name__ == '__main__':
    main()
