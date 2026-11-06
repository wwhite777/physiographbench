"""E3 onset-matched CVSim wrapper and controlled policy families.

Upstream sampling, physiology, numerical integration and source files are retained.
Only factual dose assignment and the alternative intervention schedule are wrapped.
"""
from __future__ import annotations

import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[2]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH

import argparse
from dataclasses import replace
import json
from pathlib import Path
import shlex
import sys
import time

import numpy as np
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parent
PROJECT = RELEASE_ROOT
sys.dont_write_bytecode = True
sys.path.insert(0, str(PROJECT / 'sim'))
import sim_policy_ext2 as previous

frozen = previous.frozen
CHANNELS, ORGANS = previous.CHANNELS, previous.ORGANS
sha256 = previous.sha256
ONSET_S = 4320.
TEMPORAL_SWITCH_S = 3600.
SUPPORT_WIDTHS = (.10, .25, .50, .75, 1.)
DEPENDENCE_TARGETS = (0., .075, .15, .225, .30)
RANK_TARGET = .30
CORRELATION_BAND = .02
SUPPORT_BAND = 1e-6
FAMILIES = ('support_only', 'dependence_only', 'legacy')
PROTOCOLS = ('onset_matched', 'temporal_extrapolation')
POLICY_VERSION = 'E3-affine-support-fixed-tercile-multisets-v1'


def owned_path(path):
    path = Path(path).resolve()
    if not (path.is_relative_to(ROOT) or path.is_relative_to(RELEASE_SCRATCH)) or path == ROOT:
        raise ValueError(f'Output must be inside {ROOT}: {path}')
    return path


def write_json(path, value):
    path = owned_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def code_hashes():
    paths = [Path(__file__), Path(previous.__file__),
             Path(previous.previous.__file__), previous.SOURCE]
    return {str(p): sha256(p) for p in paths}


def distribution(values):
    values = np.asarray(values, dtype=np.float64).reshape(-1)
    counts, edges = np.histogram(values, np.linspace(0., .5, 11))
    return dict(n=int(values.size), n_unique=int(np.unique(values).size),
                min=float(values.min()), max=float(values.max()),
                mean=float(values.mean()), std=float(values.std()),
                quantiles=np.quantile(values, [0, .05, .25, .5, .75, .95, 1]).tolist(),
                histogram_counts=counts.tolist(), histogram_edges=edges.tolist())


def severity_groups(severity):
    cuts = np.quantile(severity, [1 / 3, 2 / 3])
    groups = np.searchsorted(cuts, severity, side='right')
    if any(np.count_nonzero(groups == g) < 2 for g in range(3)):
        raise ValueError('Each severity tercile needs at least two distinct patients')
    return groups, cuts


def rank_corr(severity, dose):
    return float(np.corrcoef(rankdata(severity), rankdata(dose))[0, 1])


def policy_statistics(severity, dose):
    severity, dose = np.asarray(severity), np.asarray(dose)
    groups, cuts = severity_groups(severity)
    terciles = []
    grid = np.array([0., .05, .1, .2, .4])
    for g in range(3):
        selected = dose[groups == g].astype(np.float64)
        low, high = np.quantile(selected, [.05, .95])
        terciles.append(dict(tercile=g, n=len(selected), q05=float(low), q95=float(high),
                             width_05_95=float(high - low), min=float(selected.min()),
                             max=float(selected.max()),
                             supported_grid=((grid >= low) & (grid <= high)).tolist(),
                             distribution=distribution(selected)))
    return dict(spearman=rank_corr(severity, dose),
                pearson=float(np.corrcoef(severity, dose)[0, 1]),
                severity_cutpoints=cuts.tolist(), terciles=terciles,
                support_fraction=float(np.mean([t['supported_grid'] for t in terciles])),
                target_distribution=distribution(dose))


def _fixed_multiset_assignment(severity, seed, target):
    """Permute [0,.5] quantiles inside each tercile; calibrate global Spearman.

    A score z_i + a*r_i determines a patient's dose rank in its own tercile.
    r_i is the within-tercile severity rank, centered and variance standardized.
    Bisection selects a, without changing any tercile's dose multiset.
    """
    groups, _ = severity_groups(severity)
    z = np.random.default_rng(np.random.SeedSequence([seed, 2703])).normal(size=len(severity))
    local_rank = np.empty(len(severity))
    for g in range(3):
        ix = np.flatnonzero(groups == g)
        r = rankdata(severity[ix])
        local_rank[ix] = (r - r.mean()) / r.std()

    def at(coefficient):
        result = np.empty(len(severity))
        for g in range(3):
            ix = np.flatnonzero(groups == g)
            order = np.argsort(z[ix] + coefficient * local_rank[ix], kind='stable')
            result[ix[order]] = np.linspace(0., .5, len(ix))
        return result, rank_corr(severity, result)

    lo, hi = -1e6, 1e6
    candidates = [(*at(lo), lo), (*at(hi), hi)]
    for _ in range(64):
        mid = (lo + hi) / 2
        dose, rho = at(mid)
        candidates.append((dose, rho, mid))
        if rho < target:
            lo = mid
        else:
            hi = mid
    dose, rho, coefficient = min(candidates, key=lambda item: abs(item[1] - target))
    if abs(rho - target) > CORRELATION_BAND:
        raise ValueError(f'Cannot attain rank target {target}: achieved {rho}')
    return dose, coefficient


def assign_policy(severity, *, family, point=0, seed=0):
    if family not in FAMILIES[:2] or point not in range(5):
        raise ValueError('Controlled family requires a point in 0..4')
    target = RANK_TARGET if family == 'support_only' else DEPENDENCE_TARGETS[point]
    base, coefficient = _fixed_multiset_assignment(np.asarray(severity), seed, target)
    width = SUPPORT_WIDTHS[point] if family == 'support_only' else 1.
    dose = (.25 + width * (base - .25)).astype(np.float32)
    stats = policy_statistics(severity, dose)
    if abs(stats['spearman'] - target) > CORRELATION_BAND:
        raise ValueError('Stored float32 policy violates the correlation band')
    for tercile in stats['terciles']:
        if abs(tercile['width_05_95'] - .45 * width) > SUPPORT_BAND:
            raise ValueError('Stored policy violates the support-width band')
    return dose, dict(family=family, point=point, width=width,
                       rank_target=target, score_coefficient=coefficient,
                       policy_version=POLICY_VERSION, statistics=stats)


def record_policy(*, family='support_only', point=0, confound=0., sigma=0.,
                  seed=0, n_patients=400, kappa=1., out_dt=300.):
    """Record frozen patient/sepsis draws without running the ODE."""
    data, jobs = previous._record_jobs(kappa, confound, sigma, seed, n_patients, 6., out_dt)
    if family == 'legacy':
        policy = dict(family=family, confound=confound, sigma=sigma,
                      equation='clip(c*0.5*severity + (1-c)*Uniform(0,0.5) + Normal(0,sigma),0,0.5)',
                      statistics=policy_statistics(data['severity'], data['factual_dose']))
    else:
        data['factual_dose'], policy = assign_policy(data['severity'], family=family,
                                                     point=point, seed=seed)
    return data, jobs, policy


def verify_shared_history(data):
    metadata = json.loads(str(data['metadata_json']))
    seconds = data['t_min'].astype(float) * 60
    switch = metadata['switch_s']
    before = seconds < switch
    factual = data['factual'][..., :6]
    expected = np.broadcast_to(factual[:, None, before], data['counterfactual'][:, :, before].shape)
    np.testing.assert_array_equal(data['counterfactual'][:, :, before], expected)
    controls = data['counterfactual_control']
    if np.count_nonzero(controls[:, :, before]):
        raise ValueError('Alternative treatment before the switch')
    after = seconds >= switch
    np.testing.assert_array_equal(controls[:, :, after], np.broadcast_to(
        data['cf_doses'][None, :, None], controls[:, :, after].shape))
    if np.count_nonzero(data['factual'][:, seconds < ONSET_S, 6]):
        raise ValueError('Factual treatment before 4320 s')
    target_times = data['target_t_min'].astype(float) * 60
    if not np.all(target_times > switch):
        raise ValueError('Scored targets must be strictly after the intervention')
    return dict(protocol=metadata['cf_protocol'], switch_s=switch,
                n_pre_switch_samples=int(before.sum()), history_identical=True,
                n_treated_alternative_samples_before_switch=0,
                n_treated_alternative_samples_before_factual_onset=int(
                    np.count_nonzero(controls[:, :, seconds < ONSET_S])),
                first_scored_min=float(data['target_t_min'][0]),
                n_scored_times=len(target_times))


def make_dataset_grid(*, family='support_only', point=0, confound=0., sigma=0.,
                      seed=0, n_patients=400, kappa=1., out_dt=300., C=12, K=24,
                      cf_protocol='onset_matched', out_path=None):
    if family not in FAMILIES or cf_protocol not in PROTOCOLS:
        raise ValueError('Unknown family or protocol')
    if not np.isfinite([kappa, confound, sigma, out_dt]).all() or not (
            0 <= kappa <= 1 and 0 <= confound <= 1 and sigma >= 0 and out_dt > 0):
        raise ValueError('Invalid finite generation settings')
    if n_patients < 12 or C < 1 or K < 1 or not float(out_dt / previous.DT).is_integer():
        raise ValueError('Require >=12 patients, positive C/K and 0.5-s aligned sampling')
    switch = ONSET_S if cf_protocol == 'onset_matched' else TEMPORAL_SWITCH_S
    if (C - 1) * out_dt >= switch or (C + K - 1) * out_dt > 21600:
        raise ValueError('Context must precede the switch; rollout must fit the 6-h horizon')
    indices = np.arange(C, C + K)
    score_indices = indices[indices * out_dt > switch]
    if not len(score_indices):
        raise ValueError('No post-intervention scored sample')
    path = owned_path(out_path) if out_path is not None else None
    if path is not None and (path.suffix != '.npz' or path.exists() or path.with_suffix('.manifest.json').exists()):
        raise ValueError('Require a new .npz destination and manifest')
    start = time.perf_counter()
    data, jobs, policy = record_policy(family=family, point=point, confound=confound,
        sigma=sigma, seed=seed, n_patients=n_patients, kappa=kappa, out_dt=out_dt)
    group_size = 1 + len(data['cf_doses'])
    factual_schedules = []
    switched = []
    for i, job in enumerate(jobs):
        patient, lane = divmod(i, group_size)
        original = jobs[patient * group_size][1]
        factual = (original if family == 'legacy' else replace(original,
            vaso_v=np.array([0., data['factual_dose'][patient], data['factual_dose'][patient]])))
        factual_schedules.append(factual)
        alternative = factual if lane == 0 else previous.shared_history_schedule(
            factual, data['cf_doses'][lane - 1], switch)
        switched.append((job[0], alternative, *job[2:]))
    trajectories = previous._integrate_shared_jobs(switched, factual_schedules, switch)
    grouped = trajectories.astype(np.float32).reshape(n_patients, group_size, len(data['t_min']), 8)
    data['factual'] = grouped[:, 0][..., [0, 1, 2, 3, 4, 5, 7, 6]].copy()
    data['counterfactual'] = grouped[:, 1:, :, :6].copy()
    data['counterfactual_control'] = grouped[:, 1:, :, 7].copy()
    data['score_indices'] = score_indices
    data['counterfactual_target'] = data['counterfactual'][:, :, score_indices].copy()
    data['target_t_min'] = data['t_min'][score_indices].copy()
    metadata = dict(schema_version=3, family=family, point=point, confound=confound,
        sigma=sigma, seed=seed, n_patients=n_patients, kappa=kappa, out_dt=out_dt,
        C=C, K=K, horizon_h=6., cf_protocol=cf_protocol, switch_s=switch,
        factual_dose_onset_s=ONSET_S, integration_dt=previous.DT,
        warmup_s=previous.WARMUP_S, score_indices=score_indices.tolist(), policy=policy,
        scoring='Strictly post-switch samples inside the C:C+K rollout; pre-switch samples excluded.',
        boundary_note='Frozen RK4: the whole step ending at switch uses the factual schedule, '
                      'including its endpoint stage; all branches share that state (historical_experiment convention).',
        code_sha256=code_hashes())
    data['metadata_json'] = np.array(json.dumps(metadata, allow_nan=False))
    metadata['history_checks'] = verify_shared_history(data)
    data['metadata_json'] = np.array(json.dumps(metadata, allow_nan=False))
    if not all(np.isfinite(data[key]).all() for key in ('factual', 'counterfactual')):
        raise ValueError('Nonfinite simulator trajectory')
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(path, **data)
        write_json(path.with_suffix('.manifest.json'), dict(metadata=metadata,
            output_sha256=sha256(path), command_line=shlex.join([sys.executable, *sys.argv]),
            generation_wall_seconds=time.perf_counter() - start))
    return data


def validate_manifest(path):
    path = Path(path)
    manifest = json.loads(path.with_suffix('.manifest.json').read_text())
    if manifest['output_sha256'] != sha256(path) or manifest['metadata']['code_sha256'] != code_hashes():
        raise ValueError('Stale, modified or code-mismatched E3 dataset')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--family', choices=FAMILIES, default='support_only')
    parser.add_argument('--point', type=int, default=0)
    parser.add_argument('--confound', type=float, default=0.)
    parser.add_argument('--sigma', type=float, default=0.)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--n_patients', type=int, default=400)
    parser.add_argument('--kappa', type=float, default=1.)
    parser.add_argument('--out_dt', type=float, default=300.)
    parser.add_argument('--C', type=int, default=12)
    parser.add_argument('--K', type=int, default=24)
    parser.add_argument('--cf_protocol', choices=PROTOCOLS, default='onset_matched')
    parser.add_argument('--out', dest='out_path', required=True)
    data = make_dataset_grid(**vars(parser.parse_args()))
    print(json.dumps(json.loads(str(data['metadata_json'])), allow_nan=False))


if __name__ == '__main__':
    main()
