#!/usr/bin/env python3
"""Validation-cap selection: deterministic CPU reanalysis of existing records; no fits or inference.

Requires the existing Python, NumPy and SciPy installation. Reads inputs in place.
Default: write cap_reanalysis.json and CAP_REANALYSIS.md beside this script.
--check: recompute both in memory and require byte-identical existing outputs.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import platform

import numpy as np
import scipy
from scipy import optimize, stats

HERE = Path(__file__).absolute().parent
import sys
sys.path.insert(0, str(Path(os.environ.get('PHYSIOGRAPH_ROOT', HERE.parents[1]))))
from release_paths import ROOT as PROJECT, SCRATCH
from release_records import read as public_read, verify as verify_distributed
HOST = PROJECT / 'experiments/shared_input_primary/artifacts/host'
V4 = PROJECT / 'results/v4'
METHOD = PROJECT / 'analysis/paired_statistics'
SEEDS = (0, 1, 2, 3)
CAPS = (35, 70, 105)
FAMILIES = ('none', 'admissible', 'grud')
METRIC_FIELDS = {'A': '/A/pooled_masked_RMSE', 'B': '/B/pooled_masked_RMSE',
                 'A_validation': '/A_validation/pooled_masked_RMSE'}
LABELS = {'none': 'Shared none', 'admissible': 'Shared admissible', 'grud': 'GRU-D',
          'gru': 'GRU', 'gru_med': 'GRU-med', 'gru_large': 'GRU-large',
          'graphgru': 'GraphGRU', 'odernn': 'ODE-RNN', 'ncde': 'Neural CDE',
          'physiograph': 'PhysioGraph-SSM, partitioned',
          'physiograph_gru': 'PhysioGraph-GRU, partitioned',
          'tpatchgnn': 't-PatchGNN', 'grafiti': 'GraFITi', 'persistence': 'Persistence'}
PINS = {}  # Distributed inputs are checked individually by Evidence.register.



def digest(path):
    return hashlib.sha256((PROJECT / str(path).partition('#')[0]).read_bytes()).hexdigest()


def at_pointer(value, pointer):
    for part in pointer.split('/')[1:]:
        part = part.replace('~1', '/').replace('~0', '~')
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


class Evidence:
    def __init__(self):
        self.sources = {}
        self.cache = {}

    def register(self, path, role='run_record'):
        key = str(path)
        if Path(key.partition('#')[0]).is_absolute():
            key = str(Path(key.partition('#')[0]).relative_to(PROJECT)) + ('#' + key.partition('#')[2] if '#' in key else '')
        path = PROJECT / key.partition('#')[0]
        if key not in self.sources:
            verify_distributed(path)
            self.sources[key] = dict(source_file=key, sha256=digest(path),
                                     bytes=path.stat().st_size, role=role)
        return key

    def read(self, path, role='run_record'):
        key = self.register(path, role)
        if key not in self.cache:
            self.cache[key] = public_read(key)
        return self.cache[key]

    def obs(self, path, pointer):
        key = self.register(path)
        return dict(value=at_pointer(self.read(path), pointer), source_file=key,
                    source_field=pointer)


def power_design(n):
    """Invert two-sided noncentral-t power, following the pinned historical-experiment method."""
    df = n - 1
    critical = float(stats.t.ppf(0.975, df))

    def power(ncp):
        return float(stats.nct.cdf(-critical, df, ncp) + stats.nct.sf(critical, df, ncp))

    # historical-experiment uses this bracket because this SciPy build can return NaN at ncp=10.
    ncp = float(optimize.brentq(lambda x: power(x) - 0.8, 0.0, 8.0, xtol=1e-13))
    return dict(n_pairs=n, df=df, alpha_two_sided=0.05, target_power=0.8,
                critical_t=critical, noncentrality=ncp,
                mdd_multiplier=ncp / math.sqrt(n), verified_power=power(ncp))


def paired_summary(differences, design):
    values = np.asarray(differences, dtype=np.float64)
    assert values.shape == (4,) and np.isfinite(values).all()
    mean = float(values.mean())
    sd = float(values.std(ddof=1))
    se = sd / math.sqrt(len(values))
    half = design['critical_t'] * se
    return dict(n_pairs=len(values), df=len(values) - 1,
                mean_difference=mean, paired_sd_sample=sd, standard_error=se,
                ci95_paired_t=[mean - half, mean + half],
                sign_count=dict(negative=int((values < 0).sum()),
                                zero=int((values == 0).sum()), positive=int((values > 0).sum())),
                mdd_80pct_alpha05_n4=design['mdd_multiplier'] * sd if sd > 0 else None,
                ci_excludes_zero=bool(mean - half > 0 or mean + half < 0) if sd > 0 else None)


def select_caps(summaries):
    # Only A-validation is an argument to the ranking key. No tolerance/rounding.
    return {family: min((r for r in summaries if r['family'] == family),
                        key=lambda r: (r['metrics']['A_validation']['mean'], r['cap']))['cap']
            for family in FAMILIES}


def embedded_curve_check(record):
    """Replay improvement/stopping from the saved curve, without model execution."""
    curve = record['training_curve']
    assert [r['epoch'] for r in curve] == list(range(1, record['epochs_completed'] + 1))
    best, best_epoch, stale = math.inf, None, 0
    for row in curve:
        assert stale < record['patience'], 'curve continues after patience exhausted'
        improved = row['val_RMSE'] < best - record['min_delta']
        assert row['improved'] == improved
        if improved:
            best, best_epoch, stale = row['val_RMSE'], row['epoch'], 0
        else:
            stale += 1
    assert best_epoch == record['best_epoch']
    assert best == record['validation_RMSE']
    assert stale == record['epochs_completed'] - record['best_epoch']
    return stale


def run_row(evidence, path, row_id, family, cap, seed):
    record = evidence.read(path)
    assert record['seed'] == seed and record['epochs_budget'] == cap
    assert record['scope'] == 'full' and record['status'] == 'complete' and record['failure'] is None
    assert record['C'] == record['K'] == 12
    assert record['model'] == ('grud' if family == 'grud' else 'physiograph_gru_shared')
    if family != 'grud':
        assert record['arm'] == family and record['input_mode'] == 'shared'
    fields = ['seed', 'model', 'lr', 'width', 'sizes', 'C', 'K', 'epochs_budget',
              'epochs_completed', 'best_epoch', 'patience', 'min_delta', 'status', 'failure',
              'scheduler', 'validation_RMSE', 'n_params', 'data/cohort_sha256']
    if 'scheduler_T_max' in record:
        fields.append('scheduler_T_max')
        assert record['scheduler_T_max'] == cap
    observations = {field: evidence.obs(path, '/' + field) for field in fields}
    metrics = {}
    for metric, pointer in METRIC_FIELDS.items():
        # Historical v4 run schema stores this same pooled validation score as a scalar.
        if metric == 'A_validation' and 'A_validation' not in record:
            assert family == 'grud' and cap == 35
            pointer = '/validation_RMSE'
        metrics[metric] = evidence.obs(path, pointer)
        assert math.isfinite(metrics[metric]['value'])
    assert metrics['A_validation']['value'] == record['validation_RMSE']
    done, best, patience = record['epochs_completed'], record['best_epoch'], record['patience']
    assert 1 <= best <= done <= cap
    stale = done - best
    if 'training_curve' in record:
        stale = embedded_curve_check(record)
    if done < cap:
        assert stale == patience, 'early completion must exhaust patience'
    assert stale <= patience
    return dict(id=row_id, family=family, cap=cap, seed=seed, source_file=evidence.register(path),
                metrics=metrics, fields=observations,
                epochs_completed=done, best_epoch=best,
                early_stop_before_cap=done < cap,
                reached_cap=done == cap, patience_exhausted=stale >= patience,
                stopping_evidence=('embedded training_curve replay plus completion/best/patience fields'
                                   if 'training_curve' in record else
                                   'complete status and epochs_completed/best_epoch/patience fields'),
                derived_from=['/epochs_completed', '/epochs_budget', '/best_epoch', '/patience', '/status'])


def aggregate(family, cap, rows):
    selected = [r for r in rows if r['family'] == family and r['cap'] == cap]
    assert [r['seed'] for r in selected] == list(SEEDS)
    metrics = {}
    for metric in METRIC_FIELDS:
        values = [r['metrics'][metric]['value'] for r in selected]
        metrics[metric] = dict(mean=float(np.mean(values)), sample_sd=float(np.std(values, ddof=1)),
                               derived_from=[r['metrics'][metric] for r in selected],
                               formula='arithmetic mean of four per-run pooled masked RMSEs; sample SD ddof=1')
    return dict(family=family, cap=cap, n_seeds=len(selected), seeds=list(SEEDS),
                metrics=metrics, epochs_completed=[r['epochs_completed'] for r in selected],
                mean_epochs_completed=float(np.mean([r['epochs_completed'] for r in selected])),
                best_epochs=[r['best_epoch'] for r in selected],
                early_stop_before_cap_count=sum(r['early_stop_before_cap'] for r in selected),
                reached_cap_count=sum(r['reached_cap'] for r in selected),
                patience_exhausted_at_cap_count=sum(r['reached_cap'] and r['patience_exhausted'] for r in selected),
                derived_from=[r['id'] for r in selected])


def contrast(rows_by_key, row_id, group, lhs, rhs, metric, design):
    observations = []
    for seed in SEEDS:
        left = rows_by_key[(*lhs, seed)]
        right = rows_by_key[(*rhs, seed)]
        lobs, robs = left['metrics'][metric], right['metrics'][metric]
        observations.append(dict(seed=seed, lhs_run_id=left['id'], rhs_run_id=right['id'],
                                 lhs=lobs, rhs=robs, difference=lobs['value'] - robs['value']))
    return dict(id=row_id, group=group, lhs_family=lhs[0], lhs_cap=lhs[1],
                rhs_family=rhs[0], rhs_cap=rhs[1], metric=metric,
                contrast=f'{lhs[0]}@{lhs[1]} minus {rhs[0]}@{rhs[1]}',
                observations=observations,
                derivation='paired seed-index lhs minus rhs; mean +/- t(.975,3)*sample_sd/sqrt(4)',
                **paired_summary([r['difference'] for r in observations], design))


def v4_stopping_rows(evidence, tuning):
    result = []
    for model, config in tuning['selection']['models'].items():
        assert config['status'] == 'selected'
        seeds = []
        for seed in SEEDS:
            path = str(V4 / 'tuning_grid.json') + f'#/selected_runs/{model}/{seed}'
            record = evidence.read(path)
            assert record['seed'] == seed and record['model'] == model
            assert record['status'] == 'complete' and record['failure'] is None
            assert record['epochs_budget'] == 35 and record['scope'] == 'full'
            assert all(record[k] == config[k] for k in ('lr', 'width', 'sizes'))
            assert all(record[k] == tuning['selected_runs'][model][str(seed)][k]
                       for k in ('epochs_budget', 'epochs_completed', 'best_epoch', 'lr', 'width', 'sizes',
                                 'patience', 'min_delta', 'validation_RMSE', 'status', 'failure'))
            done, best, patience = (record[k] for k in ('epochs_completed', 'best_epoch', 'patience'))
            assert 1 <= best <= done <= 35
            assert done - best <= patience
            if done < 35:
                assert done - best == patience
            seeds.append(dict(seed=seed, epochs_completed=done, best_epoch=best,
                              early_stop_before_cap=done < 35, reached_cap=done == 35,
                              patience_exhausted=done - best == patience,
                              fields={k: evidence.obs(path, '/' + k) for k in
                                      ('seed', 'epochs_budget', 'epochs_completed', 'best_epoch',
                                       'patience', 'min_delta', 'status', 'failure', 'lr', 'width', 'sizes')}))
        result.append(stopping_aggregate(model, seeds, 'validation-selected v4 configuration',
                                         evidence.obs(V4 / 'tuning_grid.json', '/selection/models/' + model)))
    return result


def stopping_aggregate(model, seeds, setting, configuration):
    return dict(model=model, label=LABELS[model], setting=setting, cap=35,
                n_seeds=len(seeds), selected_configuration=configuration,
                seeds=seeds, epochs_completed=[s['epochs_completed'] for s in seeds],
                best_epochs=[s['best_epoch'] for s in seeds],
                early_stop_before_cap_count=sum(s['early_stop_before_cap'] for s in seeds),
                reached_cap_count=sum(s['reached_cap'] for s in seeds),
                patience_exhausted_at_cap_count=sum(s['reached_cap'] and s['patience_exhausted'] for s in seeds),
                cap_reached_before_patience_count=sum(s['reached_cap'] and not s['patience_exhausted'] for s in seeds),
                derivation='count per-seed completed<cap; complete status and completed-best==patience validate early stops')


def learned_stopping_rows(evidence):
    """Additional Table 1 records located by the pinned paired_stats.py primary_series."""
    result = []
    for model, subdir in (('tpatchgnn', 'tpatchgnn'), ('grafiti', 'grafiti_v3')):
        seeds = []
        for seed in SEEDS:
            path = (PROJECT / 'results/learned_graph_baselines_v1' /
                    subdir / f'cinc_{model}_s{seed}.json')
            record = evidence.read(path)
            assert record['model'] == model and not record['smoke']
            assert record['config']['seed'] == seed and record['config']['epochs'] == 35
            assert record['config']['C'] == record['config']['K'] == 12
            history = record['training_history']
            assert [r['epoch'] for r in history] == list(range(len(history)))
            best, best_epoch, stale = math.inf, None, 0
            patience, delta = record['protocol']['patience'], record['protocol']['min_delta']
            for i, row in enumerate(history):
                assert stale < patience
                if row['val_rmse'] < best - delta:
                    best, best_epoch, stale = row['val_rmse'], i + 1, 0
                else:
                    stale += 1
                assert row['best_val_rmse'] == best
            assert best == record['val_RMSE'] and len(history) <= 35
            assert len(history) == 35 or stale == patience
            seeds.append(dict(seed=seed, epochs_completed=len(history), best_epoch=best_epoch,
                              early_stop_before_cap=len(history) < 35, reached_cap=len(history) == 35,
                              patience_exhausted=stale >= patience,
                              fields={k: evidence.obs(path, '/' + k) for k in
                                      ('config/seed', 'config/epochs', 'config/lr', 'protocol/patience',
                                       'protocol/min_delta', 'training_history', 'val_RMSE')},
                              derivation='completed=len(training_history); saved epoch is zero-based; replay min_delta/patience'))
        result.append(stopping_aggregate(model, seeds, 'paper settings; no tuning grid', None))
    return result


def build():
    evidence = Evidence()
    for path, prefix in PINS.items():
        evidence.register(path, 'pinned_input')
        assert evidence.sources[str(path.relative_to(PROJECT))]['sha256'].startswith(prefix), f'pin mismatch: {path}'
    protocol = PROJECT / 'tools/v4_protocol.py'
    evidence.register(protocol, 'validation_scalar_schema_definition')
    designs = {str(n): power_design(n) for n in (4, 10)}
    tuning = evidence.read(V4 / 'tuning_grid.json')
    rows = []
    for family in FAMILIES:
        for cap in CAPS:
            for seed in SEEDS:
                if cap == 35:
                    root = V4 / 'selected/grud' if family == 'grud' else HOST / 'arms' / family
                    path = (str(V4 / 'tuning_grid.json') + f'#/selected_runs/grud/{seed}' if family == 'grud' else root / f'seed{seed}/run.json')
                else:
                    path = HOST / f'budget/{family}/epochs{cap}/seed{seed}/run.json'
                rows.append(run_row(evidence, path, f'R{len(rows) + 1:03d}', family, cap, seed))
    by_key = {(r['family'], r['cap'], r['seed']): r for r in rows}
    # All main comparisons condition on exactly the same saved cohort and split lists.
    ref = evidence.read(rows[0]['source_file'])
    for row in rows:
        record = evidence.read(row['source_file'])
        assert record['data']['split_stay_indices'] == ref['data']['split_stay_indices']
        assert record['data']['cohort_sha256'] == ref['data']['cohort_sha256']
        family_ref = evidence.read(by_key[(row['family'], 35, 0)]['source_file'])
        assert all(record[k] == family_ref[k] for k in
                   ('lr', 'width', 'sizes', 'optimizer', 'weight_decay', 'scheduler', 'patience', 'min_delta'))
    summaries = [aggregate(family, cap, rows) for family in FAMILIES for cap in CAPS]
    selected = select_caps(summaries)
    selected_details = []
    for family in FAMILIES:
        candidates = [s for s in summaries if s['family'] == family]
        ranked = sorted(candidates, key=lambda s: (s['metrics']['A_validation']['mean'], s['cap']))
        selected_details.append(dict(family=family, selected_cap=selected[family],
                                     candidates=[dict(cap=s['cap'], mean_A_validation_RMSE=s['metrics']['A_validation']['mean'],
                                                      derived_from=s['metrics']['A_validation']['derived_from']) for s in candidates],
                                     runner_up_cap=ranked[1]['cap'],
                                     runner_up_minus_selected_validation=ranked[1]['metrics']['A_validation']['mean'] -
                                                                        ranked[0]['metrics']['A_validation']['mean'],
                                     exact_tie_count=sum(s['metrics']['A_validation']['mean'] ==
                                                         ranked[0]['metrics']['A_validation']['mean'] for s in candidates)))
    # Meaningful selection controls: held-out values cannot alter choices; exact ties use smaller caps.
    adversarial = copy.deepcopy(summaries)
    for i, row in enumerate(adversarial):
        for metric in ('A', 'B'):
            row['metrics'][metric]['mean'] = (-1 if i % 2 else 1) * 1e100
    assert select_caps(adversarial) == selected
    tied = copy.deepcopy(summaries)
    for row in tied:
        row['metrics']['A_validation']['mean'] = 1.0
    assert select_caps(tied) == {family: min(CAPS) for family in FAMILIES}
    comparisons = []

    def add(group, lhs, rhs, metric):
        row = contrast(by_key, f'C{len(comparisons) + 1:03d}', group, lhs, rhs, metric, designs['4'])
        comparisons.append(row)

    for cap in CAPS:
        for metric in ('A', 'B'):
            add('admissible_minus_none_same_cap', ('admissible', cap), ('none', cap), metric)
    for family in FAMILIES:
        for later, earlier in ((70, 35), (105, 70), (105, 35)):
            for metric in METRIC_FIELDS:
                add('cap_to_cap', (family, later), (family, earlier), metric)
    for cap in CAPS:
        for family in ('none', 'admissible'):
            for metric in ('A', 'B'):
                add('versus_grud_same_cap', (family, cap), ('grud', cap), metric)
    for lhs, rhs in (('admissible', 'none'), ('none', 'grud'), ('admissible', 'grud')):
        for metric in ('A', 'B'):
            add('family_selected_caps', (lhs, selected[lhs]), (rhs, selected[rhs]), metric)
    planning = []
    for row in comparisons:
        if row['lhs_family'] != 'admissible' or row['rhs_family'] != 'none':
            continue
        if row['group'] not in ('family_selected_caps', 'admissible_minus_none_same_cap'):
            continue
        sd = row['paired_sd_sample']
        planning.append(dict(contrast_id=row['id'], contrast=row['contrast'], metric=row['metric'],
                             primary=row['group'] == 'family_selected_caps',
                             observed_sd_n_pairs=4, observed_paired_sd=sd,
                             planned_n_pairs=10, planned_additional_pairs_if_retaining_original_four=6,
                             mdd_80pct_alpha05_n10=designs['10']['mdd_multiplier'] * sd,
                             derived_from=dict(contrast=row['id'], field='paired_sd_sample'),
                             formula='n10 noncentral-t multiplier * observed n4 sample paired SD'))
    stopping = v4_stopping_rows(evidence, tuning) + learned_stopping_rows(evidence)
    stopping.append(dict(model='persistence', label='Persistence', setting='deterministic; no fitted epochs',
                         cap=None, n_seeds=None, epochs_completed=None, best_epochs=None,
                         early_stop_before_cap_count=None, reached_cap_count=None,
                         patience_exhausted_at_cap_count=None, cap_reached_before_patience_count=None,
                         source='No fit/selected configuration; Table 1 persistence reference',
                         not_applicable_reason='Persistence does not train.'))
    assert {r['model'] for r in stopping} == {
        'gru', 'gru_med', 'gru_large', 'grud', 'ncde', 'odernn', 'graphgru',
        'physiograph', 'physiograph_gru', 'tpatchgnn', 'grafiti', 'persistence'}
    grid = []
    for path in sorted((HOST / 'grid').glob('*/seed0/run.json')):
        record = evidence.read(path)
        assert record['seed'] == 0 and record['status'] == 'complete' and record['epochs_budget'] == 35
        grid.append(dict(configuration=path.parent.parent.name,
                         validation=evidence.obs(path, '/A_validation/pooled_masked_RMSE'),
                         epochs_completed=evidence.obs(path, '/epochs_completed')))
    assert len(grid) == 6
    grid_winner = min(grid, key=lambda r: (r['validation']['value'], r['configuration']))
    arm0 = by_key[('none', 35, 0)]
    assert grid_winner['validation']['value'] == arm0['metrics']['A_validation']['value']
    grid_record = evidence.read(grid_winner['validation']['source_file'])
    assert all(grid_record[k] == ref[k] for k in ('lr', 'width', 'sizes'))
    # Resolve all embedded observations and prove that no registered input changed during the analysis.
    for source in evidence.sources.values():
        assert digest(source['source_file']) == source['sha256']
    data = dict(
        schema_version=1, task='analysis-cap_selection', decision='D-016 / N1',
        status='COMPLETE_EXISTING_RECORD_REANALYSIS',
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        environment=dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__),
        definitions=dict(metric='Pooled masked RMSE over observed target entries at the 12-hour horizon; A-training SD units',
                         metrics=METRIC_FIELDS, seeds=list(SEEDS), caps=list(CAPS),
                         orientation='arm/later cap minus reference/earlier cap; negative is better',
                         ci='pointwise two-sided paired Student t interval, df=n-1; no multiplicity adjustment',
                         selection='per family min(mean seed0-3 A-validation RMSE, cap); exact ties choose smaller cap; no A/B test scores',
                         early_stop='complete run ending strictly before cap, with patience exhausted; best_epoch<cap alone does not suffice',
                         sd='sample SD, ddof=1; summaries average per-run pooled RMSEs, not pooled predictions across seeds',
                         validation_alias=dict(family='grud', cap=35, source_field='/validation_RMSE',
                                               reason='v4 schema has no A_validation block; v4_protocol.py computes metrics(val_errors)[pooled_masked_RMSE] and stores best_val as validation_RMSE',
                                               definition_source=str(protocol.relative_to(PROJECT)),
                                               definition_locations='train_run: val_errors from loaders[1], val=metrics(...)[pooled_masked_RMSE], result.validation_RMSE=best_val')),
        power_designs=designs, source_catalog=sorted(evidence.sources.values(), key=lambda r: r['source_file']),
        run_records=rows, family_cap_summaries=summaries,
        cap_selection=selected_details, selected_caps=selected, paired_contrasts=comparisons,
        ten_pair_mdd=planning, other_Table_1_stopping=stopping,
        shared_configuration_grid=dict(cells=grid, selected_configuration=grid_winner['configuration'],
                                       rule='seed0 minimum A-validation RMSE, lexical configuration tie break',
                                       note='Configuration audit only. Grid seed0 and none35 seed0 are one outcome, never extra seed pairs.'),
        verification=dict(pinned_hash_prefixes_match=True, main_runs_complete=len(rows),
                          same_saved_cohort_and_split_indices=True, family_hyperparameters_frozen_across_caps=True,
                          embedded_main_curves_replayed=sum('training_curve' in evidence.read(r['source_file']) for r in rows),
                          old_grud35_scalar_validation_rows=sum(r['metrics']['A_validation']['source_field'] == '/validation_RMSE' for r in rows),
                          selected_v4_records_match_tuning_snapshot=True,
                          learned_adapter_histories_replayed=8, heldout_adversarial_selection_control=True,
                          exact_tie_smaller_cap_control=True, all_source_hashes_rechecked=True,
                          paired_contrast_rows=len(comparisons), source_files=len(evidence.sources)),
        limitations=[
            'Fresh cap-specific fits also change cosine schedule; cap contrasts do not isolate training duration.',
            'Cap selection uses only A-validation, but the existing A/B scores had been available before D-016; no claim of prospective blinding.',
            'Selected-cap contrasts compare different caps for each family and therefore combine topology with schedule/budget differences.',
            'Four training-seed pairs condition on fixed clinical cohorts; intervals do not estimate patient/hospital sampling uncertainty.',
            'Intervals are pointwise and unadjusted across this collection; no familywise significance claim.',
            'MDD treats observed n4 paired SD as a planning population SD, is uncertain, is not observed power or an equivalence margin.',
            'n10 MDD means ten total pairs, not ten additional pairs. No new seeds were fit here.',
            'Other Table 1 stopping is for selected runs, not all tuning-grid cells; learned adapters use paper settings.',
            'Learned adapter records were added for stopping metadata only, using locations explicitly identified in pinned paired_stats.py.',
            'Neural CDE B replay remains unresolved in the current manuscript; no new B metric/ranking claim is made here.',
            'Self-verification is reproducibility verification, not an independent scientific audit.',
        ])
    return data


def number(value):
    return 'NA' if value is None else f'{value:.9g}'


def signed(value):
    return f'{value:+.9g}'


def contrast_table(rows):
    lines = ['| ID | Contrast | Cohort/metric | Mean difference | Paired SD | 95% paired t CI | Signs −/0/+ | MDD, n=4 |',
             '|---|---|---|---:|---:|---|---|---:|']
    for row in rows:
        lo, hi = row['ci95_paired_t']
        signs = row['sign_count']
        lines.append(f"| {row['id']} | {row['contrast']} | {row['metric']} | {signed(row['mean_difference'])} | "
                     f"{number(row['paired_sd_sample'])} | [{signed(lo)}, {signed(hi)}] | "
                     f"{signs['negative']}/{signs['zero']}/{signs['positive']} | {number(row['mdd_80pct_alpha05_n4'])} |")
    return '\n'.join(lines)


def markdown(data):
    selected = data['selected_caps']
    family_selected = [r for r in data['paired_contrasts'] if r['group'] == 'family_selected_caps']
    lines = [
        '# historical-experiment cap reanalysis — existing records, D-016 / N1', '',
        f"The specified validation rule selects **shared none: {selected['none']} epochs; shared admissible: "
        f"{selected['admissible']} epochs; GRU-D: {selected['grud']} epochs**. These are the family-specific caps "
        'to carry into N2 if the maintainer applies D-016. No new fits, checkpoint inference or input changes were performed.', '',
        'The complete machine-readable evidence is in `cap_reanalysis.json`; `cap_reanalysis.py` regenerates both that file '
        'and this report. Markdown displays nine significant digits. JSON retains binary64 values without display rounding. '
        'Every raw observation supplies an repository-relative source location and JSON pointer; derived entries link their observations or run/contrast IDs. '
        'The source catalog supplies SHA-256 hashes. All four task-card hash prefixes match.', '',
        '## Definitions and interpretation', '',
        'Root mean squared error (RMSE) is the pooled masked error over observed target entries over the 12-hour forecast, '
        'in A-training standard-deviation units. Each mean averages the four saved per-seed RMSEs. A is the internal test holdout; '
        'B is the external holdout; A-validation alone selects the cap. Seeds pair by index 0–3 on exactly the same saved clinical splits. '
        'Differences are arm minus reference, or later cap minus earlier cap, so negative is better.', '',
        'The paired sample standard deviation (SD) uses divisor n−1. The 95% confidence interval (CI) is mean difference ± '
        't(0.975,3) × paired SD / √4. These are pointwise, unadjusted seed intervals, conditional on the fixed cohorts and the selected caps; '
        'they do not quantify patient/hospital sampling uncertainty or account for cap-selection uncertainty. '
        'They rely on independent, normally distributed seed differences.', '',
        'Minimum detectable difference (MDD) is the effect magnitude giving 80% power in a two-sided α=0.05 paired t test '
        'under the plug-in observed paired SD. It is obtained by noncentral-t inversion, as specified in the pinned historical-experiment method. '
        'It is an uncertain planning sensitivity estimate, not observed power, an equivalence margin or proof that a null effect is absent.', '',
        '**Historical validation schema:** the four 35-epoch GRU-D records have no `A_validation` block. Their scalar '
        '`validation_RMSE` is the saved A-validation pooled masked RMSE: the v4 protocol takes '
        '`metrics(val_errors)["pooled_masked_RMSE"]` from the validation loader and stores the selected `best_val` in that field. '
        'The JSON records this exact source pointer and the protocol definition; it does not invent a missing nested field. '
        'All 32 newer main records have the nested field and an exactly matching scalar.', '',
        '**Stopping:** an early stop here means completed epochs strictly below the cap, with complete status and exhausted patience. '
        'A best checkpoint before the cap alone is insufficient. Main embedded curves are replayed against patience/minimum improvement; '
        'the historical records are checked using completed, best and patience fields. A run can exhaust patience exactly at its cap; '
        'that is separately counted and is not a stop before the cap.', '',
        '## Family means and completion', '',
        'All epoch lists follow seed order 0, 1, 2, 3. Early stops and reached-cap counts have denominator four.', '',
        '| Family | Cap | A mean ± sample SD | B mean ± sample SD | A-validation mean ± sample SD | Completed epochs | Best epochs | Stops before cap | Reached cap |',
        '|---|---:|---|---|---|---|---|---:|---:|',
    ]
    for row in data['family_cap_summaries']:
        metric_text = [f"{number(row['metrics'][m]['mean'])} ± {number(row['metrics'][m]['sample_sd'])}"
                       for m in METRIC_FIELDS]
        lines.append(f"| {LABELS[row['family']]} | {row['cap']} | " + ' | '.join(metric_text) + ' | ' +
                     ', '.join(map(str, row['epochs_completed'])) + ' | ' + ', '.join(map(str, row['best_epochs'])) +
                     f" | {row['early_stop_before_cap_count']}/4 | {row['reached_cap_count']}/4 |")
    lines += ['', '## Validation-only cap selection', '',
              '| Family | Mean validation @35 | @70 | @105 | Selected cap | Runner-up minus selected validation |',
              '|---|---:|---:|---:|---:|---:|']
    for row in data['cap_selection']:
        lines.append(f"| {LABELS[row['family']]} | " +
                     ' | '.join(number(c['mean_A_validation_RMSE']) for c in row['candidates']) +
                     f" | {row['selected_cap']} | {number(row['runner_up_minus_selected_validation'])} |")
    lines += ['', 'Ranking uses the unrounded mean and an exact tie → smaller-cap rule. No tolerance is added, '
              'and the early-stopping minimum-improvement threshold is not reused as a cap-selection threshold. '
              'No family has an exact tie. Shared none therefore selects 105 even though its A/B test means are worse than at 70. '
              'Shared admissible selects 70 even though its A/B test means are worse than at 35. '
              'The rule is supplied by D-016; these records and their test outcomes already existed, so this reanalysis does not establish '
              'prospective blinding or erase earlier result exposure.', '',
              '## Contrasts at each family’s selected cap', '',
              contrast_table(family_selected), '',
              'These compare admissible@70 with none@105 and both with GRU-D@35. They estimate the differences between '
              'the validation-selected family procedures, with topology, cap and schedule differences combined. '
              'Use the common-cap tables below to assess topology at matched caps. An interval containing zero does not establish equivalence.', '',
              '## Admissible minus none at each common cap', '',
              contrast_table([r for r in data['paired_contrasts'] if r['group'] == 'admissible_minus_none_same_cap']), '',
              '## Within-family cap changes', '',
              'A-validation changes are included alongside A/B changes so the cap decision can be inspected. '
              'Every contrast uses the same seed indices at the two caps.', '',
              contrast_table([r for r in data['paired_contrasts'] if r['group'] == 'cap_to_cap']), '',
              '## Organ families minus GRU-D at each common cap', '',
              contrast_table([r for r in data['paired_contrasts'] if r['group'] == 'versus_grud_same_cap']), '',
              '## Other Table 1 models: selected-run stopping at 35', '',
              'These are the four selected runs for each model, rather than counts across its tuning grid. '
              'GRU-D is repeated as a reference. The two learned graph adapters are run at paper settings; '
              'their records are located by the pinned `paired_stats.py` Table 1 source mapping. '
              'Only their saved training metadata are used here. Their histories have zero-based epoch labels; '
              'the completed count is history length, and best epochs below are converted to one-based labels.', '',
              '| Model | Selected setting | Completed epochs | Best epochs | Stops before 35 | Reached 35 | Patience exhausted exactly at 35 | Reached cap before patience |',
              '|---|---|---|---|---:|---:|---:|---:|']
    for row in data['other_Table_1_stopping']:
        if row['model'] == 'persistence':
            lines.append('| Persistence | No fit | NA | NA | NA | NA | NA | NA |')
            continue
        conf = row['selected_configuration']
        setting = (f"lr={number(conf['value']['lr'])}, {conf['value']['width']}" if conf else 'Paper settings')
        lines.append(f"| {row['label']} | {setting} | " + ', '.join(map(str, row['epochs_completed'])) +
                     ' | ' + ', '.join(map(str, row['best_epochs'])) +
                     f" | {row['early_stop_before_cap_count']}/4 | {row['reached_cap_count']}/4 | "
                     f"{row['patience_exhausted_at_cap_count']}/4 | {row['cap_reached_before_patience_count']}/4 |")
    lines += ['', 'The 35-epoch cap can limit the selected GRU, GRU-med, GRU-D, partitioned PhysioGraph-GRU/SSM '
              'and both learned adapters; these have runs reaching the cap before patience expires. ODE-RNN is mixed across seeds. '
              'Selected GraphGRU, GRU-large and Neural CDE runs all stop before 35. '
              'Reaching a cap before patience is exhausted identifies where the available budget may bind; it does not prove that '
              'a longer cap improves validation or test error. GraFITi seed 0 exhausts patience exactly on completed epoch 35, '
              'so its other three seeds, rather than all four, reach the cap before patience. '
              'Neural CDE’s external-score replay remains unresolved; this stopping audit makes no new external ranking claim.', '',
              '## Ten-pair MDD planning', '',
              f"Noncentral-t multipliers are {number(data['power_designs']['4']['mdd_multiplier'])} × observed paired SD "
              f"for n=4 and {number(data['power_designs']['10']['mdd_multiplier'])} × observed paired SD for n=10. "
              'The primary estimate uses admissible@70 minus none@105, each at its own selected cap. '
              'Because there is no single shared selected cap, the common-cap estimates are also supplied explicitly. '
              'Ten means ten total seed pairs; retaining the original four would require six additional pairs. '
              'The selected-cap n=10 SD estimate comes from four existing cross-cap pairs and is not independently estimated from ten runs.', '',
              '| Contrast ID | Contrast | Metric | Planning role | Observed paired SD (4 pairs) | MDD (10 total pairs) |',
              '|---|---|---|---|---:|---:|']
    for row in data['ten_pair_mdd']:
        lines.append(f"| {row['contrast_id']} | {row['contrast']} | {row['metric']} | "
                     f"{'Primary: each selected cap' if row['primary'] else 'Common-cap sensitivity'} | "
                     f"{number(row['observed_paired_sd'])} | {number(row['mdd_80pct_alpha05_n10'])} |")
    lines += ['', '## Plain-language reading', '',
              'The lowest validation error does not identify the lowest test error in these records. '
              'In particular, the selected no-edge cap is 105, despite better A/B test means at 70. '
              'Replacing the specified choice with 70 after looking at A/B would change the selection rule. '
              'For admissible, validation chooses 70 while the 35-epoch A/B scores are better. '
              'The 35-epoch GRU-D reference has the best validation mean among its three caps.', '',
              'At each family’s selected cap, the no-edge and admissible organ models both have higher mean A and B errors '
              'than GRU-D@35. Their pointwise paired intervals versus GRU-D exclude zero in the positive direction. '
              'Admissible@70 minus none@105 has positive mean differences of +0.00189237 A and +0.00239584 B, '
              'with both paired intervals containing zero and signs 1/0/3 on each cohort. '
              'These selected-procedure comparisons cannot isolate a physiological-edge effect because the caps differ. '
              'The common-cap comparisons show that the admissible-minus-none ordering depends on the cap. '
              'Neither the four-seed evidence nor the MDD calculation establishes equivalence or generalization to new hospitals.', '',
              'All longer-cap runs are fresh fits with cosine period equal to the cap. A larger cap also changes early stopping '
              'and the learning-rate trajectory, so the observed changes cannot be attributed only to additional training epochs. '
              'The selected-run stopping audit also shows why a blanket statement that every baseline converged before 35 is unsupported.', '',
              '## Reproduction and handoff', '',
              'Run `python3 cap_reanalysis.py` in this workspace to regenerate the JSON and Markdown. '
              'Run `python3 cap_reanalysis.py --check` for an in-memory, byte-for-byte reproduction check with all pinned hashes '
              'and source fields rechecked. Python/NumPy/SciPy versions and full source hashes are recorded in the JSON. '
              'The six-cell shared configuration grid is audited separately by validation only; its seed-0 winner duplicates '
              'none@35 seed 0 and is never counted as a fifth replicate.', '',
              'This data-free reconstruction checks the distributed records and numerical summaries; it does not replay omitted predictions or checkpoints.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Recompute in memory; require exact existing outputs')
    args = parser.parse_args()
    os.environ['TMPDIR'] = str(SCRATCH)
    data = build()
    encoded = json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + '\n'
    rendered = markdown(data)
    for name, content in (('cap_reanalysis.json', encoded), ('CAP_REANALYSIS.md', rendered)):
        path = HERE / name
        if args.check:
            assert path.read_bytes() == content.encode(), f'non-reproducible output: {name}'
        else:
            path.write_text(content)
        print(f"{'VERIFIED' if args.check else 'WROTE'} {name} bytes={len(content.encode())} sha256={hashlib.sha256(content.encode()).hexdigest()}")
    print('SELECTED_CAPS ' + json.dumps(data['selected_caps'], sort_keys=True))
    print(f"PASS: {len(data['run_records'])} main runs, {len(data['paired_contrasts'])} paired contrasts, "
          f"{len(data['source_catalog'])} input files")


if __name__ == '__main__':
    main()
