#!/usr/bin/env python3
"""hourly_calibration hourly ridge coupling using coupling_index's numerical probe functions unchanged.

Attribution: coupling_index.py, coupling_index-coupling-index-build (2026-11-04).
Its window construction, ridge selection/prediction, stay SSE aggregation and
bootstrap are imported by path. The small orchestration below mirrors its
run_probe so this task can retain stay errors without changing coupling_index's ROOT guard.
"""
from __future__ import annotations

# Resolve all public modules and scratch from the release root.
import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[1]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH

import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
import numpy as np
import scipy
import torch

from generate_hourly import ROOT, PROJECT, WRAPPER, SOURCE, EXPECTED, owned, save_json, sha256

coupling_index = PROJECT / 'tools'
PROBE_PATH = coupling_index / 'coupling_index.py'
CINC_PATH = ROOT / 'runs/coupling/coupling_index.json'
KAPPAS = ('0', '0.1', '0.25', '0.5', '0.75', '1.0')
CHANNELS = ('MAP', 'HR', 'CO', 'CVP', 'UO', 'Lac')
ORGANS = ('cardiovascular', 'renal', 'metabolic')
GROUPS = ([0, 1, 2, 3], [4], [5])
spec = importlib.util.spec_from_file_location('coupling_index_hourly_probe', PROBE_PATH)
probe = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = probe  # dataclasses resolves the registered module.
spec.loader.exec_module(probe)


def patient_indices(n=400):
    if n != 400:
        raise ValueError('Task requires exactly 400 patients')
    order = np.random.default_rng(0).permutation(n)
    return dict(A_train=order[:280], A_val=order[280:340], B=order[340:])


def build_windows(values):
    """Exactly coupling_index simulator normalization: train float64 mean, std + 1e-6."""
    indices = patient_indices(len(values))
    training = values[indices['A_train']].astype(np.float64)
    mean, std = training.mean((0, 1)), training.std((0, 1)) + 1e-6
    splits = {
        name: probe.make_windows(values[ix], np.ones_like(values[ix]),
                                 np.full(len(ix), values.shape[1]), mean, std, ids=ix)
        for name, ix in indices.items()}
    return splits, indices, mean, std


def channel_statistics(values, mean, std, start_hour):
    """Population variance (ddof=0), not variance of a pooled mixed-unit organ."""
    raw = values.astype(np.float64)
    n, t, _ = raw.shape
    result = {}
    for organ, channels in zip(ORGANS, GROUPS):
        channels = list(channels)
        x = raw[:, :, channels]
        variance = x.var((0, 1))
        normalized = ((x - mean[channels]) / std[channels]).astype(np.float32).astype(np.float64)
        result[organ] = dict(
            channel_order=[CHANNELS[c] for c in channels],
            raw_mean_by_channel=x.mean((0, 1)).tolist(),
            raw_variance_by_channel=variance.tolist(),
            normalized_target_variance_by_channel=normalized.var((0, 1)).tolist(),
            raw_min_by_channel=x.min((0, 1)).tolist(),
            raw_max_by_channel=x.max((0, 1)).tolist(),
            mean_within_patient_variance_by_channel=x.var(1).mean(0).tolist(),
            constant_channels=[CHANNELS[c] for c, v in zip(channels, variance) if v == 0],
            denominator=dict(patients=n, windows_per_patient=t, windows=n * t,
                             entries=n * t * len(channels), entries_per_channel=n * t,
                             first_hour=start_hour, last_hour=start_hour + t - 1, variance_ddof=0))
    return result


def trajectory_diagnostics(values):
    """Ranges and fixed, explicitly descriptive long-horizon checks."""
    raw = values.astype(np.float64)
    n, t, f = raw.shape
    late = raw[:, -12:]
    span = np.ptp(late, axis=1)
    scale = np.maximum(1.0, np.abs(late.mean(1)))
    near_flat = span <= 1e-4 * scale
    return dict(
        channel_order=list(CHANNELS),
        global_min_by_channel=raw.min((0, 1)).tolist(),
        global_max_by_channel=raw.max((0, 1)).tolist(),
        denominator=dict(patients=n, observations_per_patient=t,
                         entries=n * t * f, entries_per_channel=n * t),
        hourly=dict(hours=list(range(t)), mean_by_hour_channel=raw.mean(0).tolist(),
                    min_by_hour_channel=raw.min(0).tolist(), max_by_hour_channel=raw.max(0).tolist(),
                    denominator=dict(patients_per_hour=n, entries_per_hour_channel=n)),
        final_12_observations=dict(
            hours=list(range(t - 12, t)),
            median_within_patient_range_by_channel=np.median(span, axis=0).tolist(),
            max_within_patient_range_by_channel=span.max(0).tolist(),
            exactly_flat_patients_by_channel=(span == 0).sum(0).tolist(),
            near_flat_patients_by_channel=near_flat.sum(0).tolist(),
            near_flat_rule='within-patient range <= 1e-4 * max(1, abs(patient late mean)); descriptive only',
            denominator=dict(patients=n, observations_per_patient=12, entries_per_channel=n * 12)),
        limits=dict(lactate_floor=0.05, lactate_at_floor_entries=int((raw[:, :, 5] <= 0.05 + 1e-7).sum()),
                    lactate_floor_denominator=dict(patients=n, entries=n * t),
                    heart_rate_ceiling=180, heart_rate_at_ceiling_entries=int((raw[:, :, 1] == 180).sum()),
                    heart_rate_ceiling_denominator=dict(patients=n, entries=n * t),
                    nonpositive_map_entries=int((raw[:, :, 0] <= 0).sum()),
                    nonpositive_map_denominator=dict(patients=n, entries=n * t)),
        interpretation='Check global ranges and within-patient late variation before treating long trajectories as informative physiological dynamics. No lactate upper clamp exists in the frozen source.')


def run_ridge(splits, dataset_name, artifacts=None, resamples=1000):
    """coupling_index run_probe orchestration, with owned stay-error persistence."""
    n = len(ORGANS)
    own = {k: np.zeros((w.n_stays, n)) for k, w in splits.items() if k != 'A_train'}
    added = {k: np.zeros((w.n_stays, n, n)) for k, w in splits.items() if k != 'A_train'}
    counts = {k: np.zeros((w.n_stays, n)) for k, w in splits.items() if k != 'A_train'}
    fits = {}
    for j, target in enumerate(GROUPS):
        fits[ORGANS[j]] = {}
        for source in [None] + [i for i in range(n) if i != j]:
            channels = list(target) + ([] if source is None else list(GROUPS[source]))
            model, fit = probe.fit_ridge(splits['A_train'], splits['A_val'], channels, target)
            label = 'own' if source is None else f'own_plus_{ORGANS[source]}'
            fits[ORGANS[j]][label] = fit
            for split, w in splits.items():
                if split == 'A_train':
                    continue
                prediction = probe.predict_ridge(model, w, channels)
                se, ct = probe.error_by_stay(prediction, w, target)
                if source is None:
                    own[split][:, j] = se
                    counts[split][:, j] = ct
                    added[split][:, j, j] = se
                else:
                    added[split][:, source, j] = se
                    np.testing.assert_array_equal(ct, counts[split][:, j])
            print(f'{dataset_name} ridge target={ORGANS[j]} {label}', flush=True)
    result = dict(fits=fits, splits={})
    for split, w in splits.items():
        if split == 'A_train':
            continue
        summary = probe.summarize(own[split], added[split], counts[split], w,
                                  list(ORGANS), n_resamples=resamples, seed=913)
        if artifacts is not None:
            path = owned(Path(artifacts) / f'{dataset_name}_ridge_{split}_stay_errors.npz')
            path.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(path, own_sse=own[split], added_sse=added[split],
                                counts=counts[split], stay_ids=w.ids, organ_names=np.asarray(ORGANS))
            summary['stay_error_artifact'] = str(path.relative_to(ROOT))
            summary['stay_error_sha256'] = sha256(path)
        result['splits'][split] = summary
    return result


def check_manifest(path):
    path = Path(path)
    data = json.loads(path.read_text())
    if sha256(data['output_path']) != data['output_sha256']:
        raise ValueError(f'Output hash mismatch: {path}')
    for code, expected in data['code_sha256'].items():
        if sha256(code) != expected:
            raise ValueError(f'Code hash mismatch: {code}')
    for key, expected in dict(confound=1, sigma=.03, seed=0, n_patients=400,
                              horizon_h=36, out_dt=3600).items():
        if data[key] != expected:
            raise ValueError(f'Manifest setting mismatch {key}: {path}')
    return data


def copy_cinc():
    source = json.loads(CINC_PATH.read_text())
    cohort = source['datasets']['cinc2019']
    return dict(source_path=str(CINC_PATH), source_sha256=sha256(CINC_PATH),
                organ_order=cohort['organs'], organ_channels=cohort['organ_channels'],
                normalization=cohort['normalization'], splits=cohort['splits'],
                means={name: {split: summary['mean_off_diagonal']
                              for split, summary in result['splits'].items()}
                       for name, result in cohort['probes'].items()},
                copied_verbatim=True,
                comparison_note='CinC uses four organs and 12 directed pairs; simulator uses three organs and six pairs. CinC B is an external hospital; simulator B is a same-generator patient holdout. Missingness and channel coverage differ. The hourly estimator is shared; the measurement systems are not equivalent.')


def assess_calibration(result):
    points = sorted(result['datasets'].values(), key=lambda d: d['kappa'])
    assessment = {}
    for split in ('A_val', 'B'):
        defined = [d for d in points if d['ridge']['splits'][split]['mean_off_diagonal']['value'] is not None]
        curve = [d['ridge']['splits'][split]['mean_off_diagonal']['value'] for d in defined]
        reference = result['cinc']['means']['ridge'][split]['value']
        assessment[split] = dict(
            defined_kappas=[d['kappa'] for d in defined],
            undefined_kappas=[d['kappa'] for d in points if d['ridge']['splits'][split]['mean_off_diagonal']['value'] is None],
            strictly_decreasing_across_defined_kappas=bool(len(curve) > 1 and np.all(np.diff(curve) < 0)),
            cinc_below_all_defined_simulator_points=bool(curve and reference < min(curve)),
            denominator=dict(kappa_points_requested=len(points), kappa_points_defined=len(defined)),
            mean_values_and_denominators='See datasets.*.ridge.splits and cinc.means.ridge; no means are averaged across kappa.')
    invalid_map = {
        str(d['kappa']): dict(entries=d['trajectory_diagnostics']['limits']['nonpositive_map_entries'],
                             denominator=d['trajectory_diagnostics']['limits']['nonpositive_map_denominator'])
        for d in points}
    result['interpretation'].update(
        status='no_defensible_kappa_placement', split_assessment=assessment,
        long_horizon_assessment=dict(
            status='physiologically_degenerate' if any(v['entries'] > 0 for v in invalid_map.values()) else 'inspect_ranges',
            nonpositive_map_entries_by_kappa=invalid_map,
            evidence='Nonpositive MAP is nonphysiological; late cardiac-output and lactate flatness is reported per kappa in trajectory_diagnostics.'),
        conclusion='The requested hourly estimator was computed, but its mean is undefined at kappa=0 and the long trajectories enter nonphysiological states. CinC cannot defensibly be assigned kappa approximately zero from this calibration. A graph-model benefit threshold is not measured by this task.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'sim_hourly_index.json')
    parser.add_argument('--kappas', nargs='+', choices=KAPPAS, default=list(KAPPAS))
    args = parser.parse_args()
    owned(args.out)
    start = time.monotonic()
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    inputs = [WRAPPER, SOURCE, PROBE_PATH, CINC_PATH,
              PROJECT / 'README.md',
              PROJECT / 'REPRODUCE.md']
    hashes = {str(p): sha256(p) for p in inputs}
    for path, expected in EXPECTED.items():
        if hashes[str(path)] != expected:
            raise ValueError(f'Input hash mismatch: {path}')
    result = dict(
        task='hourly_calibration-sim-hourly-calibration-build', status='running',
        started_utc=datetime.now(timezone.utc).isoformat(),
        source_sha256=sha256(__file__), input_sha256=hashes,
        attribution=dict(path=str(PROBE_PATH), sha256=hashes[str(PROBE_PATH)],
                         imported_functions=['make_windows', 'fit_ridge', 'predict_ridge',
                                             'error_by_stay', 'summarize'],
                         orchestration='run_ridge mirrors coupling_index run_probe; only owned persistence differs'),
        definition='1 - pooled_masked_RMSE(own_plus_source) / pooled_masked_RMSE(own)',
        matrix_orientation='source rows, target columns',
        settings=dict(history_hours=12, forecast_hours=1, stride_hours=1,
                      target_hours=list(range(12, 37)), all_simulator_entries_observed=True,
                      simulator_observation_mask=1, bootstrap_resamples=1000, bootstrap_seed=913,
                      ridge_alpha_grid=list(probe.ALPHAS),
                      inputs='normalized values then observation masks; flatten 12 hourly rows',
                      normalization='per-channel training-patient float64 mean and std + 1e-6 over all 37 observations; coupling_index simulator convention',
                      split='seed-0 default_rng permutation, 280 A_train / 60 A_val / 60 B patients',
                      validation_note='A_val selects alpha and is also reported; B is an untouched same-generator patient holdout',
                      bootstrap_note='paired patient-cluster percentile intervals, frozen fits; all windows of each resampled patient retained',
                      constant_target_note='Zero own RMSE gives null cells. Full mean is null if any of its six off-diagonal cells is undefined; no epsilon or partial mean is substituted.',
                      omitted_features=['vaso', 'sepsis'], probes=['ridge']),
        environment=dict(python=sys.version, executable=sys.executable,
                         numpy=np.__version__, scipy=scipy.__version__, torch=torch.__version__,
                         device='cpu', blas_threads=os.environ.get('OPENBLAS_NUM_THREADS'), torch_threads=1),
        cinc=copy_cinc(), datasets={},
        interpretation=dict(status='descriptive_calibration_only',
                            source_derived_caveats=[
                                'Cardiovascular dynamics and treatment/sepsis schedules do not depend on kappa in the frozen source; only the renal observation and metabolic production term change.',
                                'UO(kappa) = 1.12 + kappa * (UO(1) - 1.12). For kappa > 0, per-channel normalization nearly removes this affine amplitude change (apart from the 1e-6 scale offset and float32 storage).',
                                'The frozen capillary leak remains active to hour 36 without compensating fluids; the requested long horizon can reach nonphysiological states. Inspect measured ranges rather than assuming extension of the six-hour calibration is valid.'],
                            reasons=['An index-to-kappa mapping requires a defined, sufficiently ordered curve.',
                                     'The scalar means average different organ/channel sets in simulator and CinC.',
                                     'This task does not measure a graph model advantage threshold.',
                                     'Predictive gain is not a causal coupling estimate.']))
    save_json(args.out, result)
    for kappa in args.kappas:
        path = ROOT / f'data/sim_hourly/hourly_k{kappa}.npz'
        manifest_path = path.with_suffix('.manifest.json')
        manifest = check_manifest(manifest_path)
        if manifest['kappa'] != float(kappa):
            raise ValueError(f'Kappa mismatch: {manifest_path}')
        with np.load(path, allow_pickle=False) as data:
            values = data['factual'][:, :, :6].copy()
            times = data['t_min'].astype(np.float64) / 60
            np.testing.assert_array_equal(times, np.arange(37))
            assert values.shape == (400, 37, 6)
            assert np.isfinite(values).all()
            np.testing.assert_array_equal(data['channels'], CHANNELS)
        splits, indices, mean, std = build_windows(values)
        dataset = dict(
            kappa=float(kappa), input_path=str(path), input_sha256=sha256(path),
            manifest_path=str(manifest_path), manifest_sha256=sha256(manifest_path),
            all_entries_observed=True, observation_mask=1,
            organs=list(ORGANS), organ_channels={o: [CHANNELS[c] for c in g] for o, g in zip(ORGANS, GROUPS)},
            split_indices={k: ix.tolist() for k, ix in indices.items()},
            normalization=dict(mean=mean.tolist(), std=std.tolist(),
                               denominator=dict(patients=280, observations_per_patient=37,
                                                entries_per_channel=280 * 37, total_entries=280 * 37 * 6)),
            splits={k: w.denominator() for k, w in splits.items()},
            trajectory_diagnostics=trajectory_diagnostics(values),
            target_statistics={k: channel_statistics(values[ix, 12:], mean, std, 12)
                               for k, ix in indices.items()})
        dataset['ridge'] = run_ridge(splits, f'hourly_k{kappa}', ROOT / 'artifacts')
        result['datasets'][f'hourly_k{kappa}'] = dataset
        save_json(args.out, result)
    result['input_integrity_verified'] = all(sha256(p) == h for p, h in hashes.items())
    if not result['input_integrity_verified']:
        raise ValueError('Read-only inputs changed during analysis')
    result['status'] = 'complete' if len(result['datasets']) == len(KAPPAS) else 'partial_requested_subset'
    if result['status'] == 'complete':
        assess_calibration(result)
    result['finished_utc'] = datetime.now(timezone.utc).isoformat()
    result['elapsed_seconds'] = time.monotonic() - start
    save_json(args.out, result)


if __name__ == '__main__':
    main()
