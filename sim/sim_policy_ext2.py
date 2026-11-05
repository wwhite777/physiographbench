"""Future-switch CVSim targets, extending simulator_grid without changing its module.

The factual schedule and random draws are frozen. Shared targets branch from the
factual state at C*out_dt; legacy targets receive their dose since warm-up.
Full trajectories support history checks; counterfactual_target stores [C:C+K].
"""
from __future__ import annotations

# Resolve all public modules and scratch from the release root.
import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[1]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH

import argparse
from dataclasses import fields, replace
import json
from pathlib import Path
import shlex
import sys
import time
import types

import numpy as np

ROOT = RELEASE_ROOT
simulator_grid_ROOT = RELEASE_ROOT / 'sim'
sys.dont_write_bytecode = True
sys.path.insert(0, str(simulator_grid_ROOT))
import sim_policy_ext as previous  # noqa: E402

frozen = previous.frozen
SOURCE = previous.SOURCE
CHANNELS, ORGANS, POLICY_NOTE = previous.CHANNELS, previous.ORGANS, previous.POLICY_NOTE
overlap_diagnostics = previous.overlap_diagnostics
sha256 = previous.sha256
DT, WARMUP_S = .5, 180.
PROTOCOLS = ('shared', 'legacy')


def owned_path(path):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError(f'Output must be inside {ROOT}: {path}')
    return path


def write_json(path, value):
    path = owned_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def code_hashes():
    return {str(path): sha256(path) for path in
            (SOURCE, Path(previous.__file__), Path(__file__))}


def manifest_path(path):
    return Path(path).with_suffix('.manifest.json')


def shared_history_schedule(factual, dose, switch_s):
    """Keep every factual knot before the switch, then hold dose constant."""
    before = factual.vaso_t < switch_s
    return replace(factual,
                   vaso_t=np.r_[factual.vaso_t[before], switch_s],
                   vaso_v=np.r_[factual.vaso_v[before], float(dose)])


def _record_jobs(kappa, confound, sigma, seed, n_patients, horizon_h, out_dt):
    jobs = []

    class RecordingCVSim(frozen.CVSim):
        def simulate(self, sch, dt=.05, out_dt=60., y0=None, warmup_s=120.):
            jobs.append((self.p, sch, self.initial_state() if y0 is None else y0.copy(),
                         dt, out_dt, warmup_s))
            ticks = np.arange(0, int(sch.horizon_s / dt) + 1,
                              max(1, int(round(out_dt / dt)))) * dt / 60
            return {key: ticks if key == 't_min' else np.zeros(len(ticks))
                    for key in ('t_min', *CHANNELS, 'sepsis', 'vaso')}

    namespace = dict(frozen.make_counterfactual_dataset.__globals__,
                     np=previous._PolicyNumpy(sigma), CVSim=RecordingCVSim)
    generator = types.FunctionType(frozen.make_counterfactual_dataset.__code__, namespace,
                                   argdefs=frozen.make_counterfactual_dataset.__defaults__)
    data = generator(n_patients=n_patients, horizon_h=horizon_h, out_dt=out_dt,
                     seed=seed, out_path=None, confound=confound, coupling=kappa)
    return data, jobs


def _integrate_shared_jobs(jobs, factual_schedules, switch_s):
    """Branch at the factual state, including the RK4 step ending at the switch.

    Using the switched schedule for that preceding step would let its endpoint
    RK4 stage see the new dose before branching. Use the factual schedule for
    the whole preceding step, then the switched schedule starting at switch_s.
    Factual lanes retain exactly simulator_grid's integrator and schedule at all times.
    """
    sim = previous._BatchCVSim()
    sim.p = types.SimpleNamespace(**{
        field.name: np.array([getattr(job[0], field.name) for job in jobs])
        for field in fields(frozen.Hemodynamics) if field.name != 'baro_on'})
    sim.p.baro_on = True
    before = previous._BatchSchedule(factual_schedules)
    after = previous._BatchSchedule([job[1] for job in jobs])
    warm = previous._BatchSchedule([
        frozen.InterventionSchedule(horizon_s=WARMUP_S,
                                    vaso_v=np.array([s.vaso(0.)]),
                                    sepsis_v=np.array([s.sepsis(0.)]))
        for s in factual_schedules])
    y = np.stack([job[2] for job in jobs], axis=1)
    dt, out_dt, warmup_s = jobs[0][3:]
    for i in range(int(warmup_s / dt)):
        y = sim._rk4(i * dt, y, warm, dt)
    records = []
    stride = max(1, int(round(out_dt / dt)))
    n = int(jobs[0][1].horizon_s / dt)
    for i in range(n + 1):
        t = i * dt
        schedule = before if t < switch_s else after
        if i % stride == 0:
            records.append(np.stack(sim._observe(t, y, schedule)[1:], axis=-1))
        if i < n:
            y = sim._rk4(t, y, schedule, dt)
    return np.stack(records, axis=1)


def make_dataset_grid(kappa, confound, sigma, seed, n_patients, out_path,
                      *, horizon_h=6., out_dt=300., cf_protocol='shared', C=12, K=24,
                      command_line=None):
    if cf_protocol not in PROTOCOLS:
        raise ValueError(cf_protocol)
    if (not 0 <= kappa <= 1 or not 0 <= confound <= 1 or sigma < 0 or
            not np.isfinite([kappa, confound, sigma, horizon_h, out_dt]).all()):
        raise ValueError('Require finite settings, kappa/c in [0,1], sigma >=0')
    if n_patients < 3 or C < 1 or K < 1 or horizon_h <= 0 or out_dt <= 0:
        raise ValueError('Require >=3 patients and positive C/K/horizon/out_dt')
    if not float(out_dt / DT).is_integer():
        raise ValueError('out_dt must be an integer multiple of the frozen 0.5 s step')
    if (C + K - 1) * out_dt > horizon_h * 3600:
        raise ValueError('The horizon does not contain the complete [C:C+K] target')
    path = owned_path(out_path) if out_path is not None else None
    if path is not None and path.suffix != '.npz':
        raise ValueError('Dataset output must have suffix .npz')
    start = time.perf_counter()
    switch_s = C * out_dt
    if cf_protocol == 'legacy':
        data = previous.make_dataset_grid(kappa, confound, sigma, seed, n_patients, None,
                                          horizon_h=horizon_h, out_dt=out_dt)
    else:
        data, jobs = _record_jobs(kappa, confound, sigma, seed, n_patients,
                                  horizon_h, out_dt)
        group_size = 1 + len(data['cf_doses'])
        factual_schedules = [jobs[i - i % group_size][1] for i in range(len(jobs))]
        switched = []
        for i, job in enumerate(jobs):
            schedule = (job[1] if i % group_size == 0 else shared_history_schedule(
                factual_schedules[i], data['cf_doses'][i % group_size - 1], switch_s))
            switched.append((job[0], schedule, *job[2:]))
        trajectories = _integrate_shared_jobs(switched, factual_schedules, switch_s)
        grouped = trajectories.astype(np.float32).reshape(
            n_patients, group_size, len(data['t_min']), 8)
        data['factual'] = grouped[:, 0][..., [0, 1, 2, 3, 4, 5, 7, 6]].copy()
        data['counterfactual'] = grouped[:, 1:, :, :6].copy()
    data['counterfactual_target'] = data['counterfactual'][:, :, C:C + K].copy()
    data['target_t_min'] = data['t_min'][C:C + K].copy()
    onset_s = .2 * horizon_h * 3600
    metadata = dict(kappa=float(kappa), confound=float(confound), c=float(confound),
                    sigma=float(sigma), seed=seed, n_patients=n_patients,
                    horizon_h=float(horizon_h), horizon_s=horizon_h * 3600,
                    out_dt=float(out_dt), warmup_s=WARMUP_S, integration_dt=DT,
                    C=C, K=K, switch_s=switch_s, cf_protocol=cf_protocol,
                    backend='vectorized', factual_dose_onset_s=onset_s,
                    zero_dose_throughout_context=bool(switch_s <= onset_s),
                    context_note=('At H=6 h, C=12 and out_dt=300 s, t_C=3600 s '
                                  'precedes the factual dose onset at 4320 s; '
                                  'dose is zero throughout context and warm-up.'),
                    target_interval_s=[switch_s, (C + K) * out_dt],
                    target_storage='counterfactual_target; full counterfactual retained for history checks',
                    boundary_note='The RK4 step ending at t_C uses the factual schedule; '
                                  'the new dose applies from t_C, including direct observation effects.',
                    policy_note=POLICY_NOTE, source_sha256=sha256(SOURCE),
                    code_sha256=code_hashes())
    data['metadata_json'] = np.array(json.dumps(metadata))
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(path, **data)
        manifest = dict(metadata, schema_version=2,
                        command_line=command_line or shlex.join([sys.executable, *sys.argv]),
                        generation_command_line=shlex.join([
                            sys.executable, '-B', str(Path(__file__).resolve()),
                            '--kappa', str(kappa), '--confound', str(confound),
                            '--sigma', str(sigma), '--seed', str(seed),
                            '--n_patients', str(n_patients), '--horizon_h', str(horizon_h),
                            '--out_dt', str(out_dt), '--cf_protocol', cf_protocol,
                            '--C', str(C), '--K', str(K), '--out', str(path)]),
                        generation_args=dict(kappa=kappa, confound=confound, sigma=sigma,
                                             seed=seed, n_patients=n_patients,
                                             horizon_h=horizon_h, out_dt=out_dt,
                                             cf_protocol=cf_protocol, C=C, K=K),
                        output_path=str(path), output_sha256=sha256(path),
                        generation_wall_seconds=time.perf_counter() - start)
        write_json(manifest_path(path), manifest)
    return data


def validate_manifest(path):
    """Reject missing, stale, or code-mismatched cached datasets."""
    manifest = json.loads(manifest_path(path).read_text())
    if manifest['output_sha256'] != sha256(path):
        raise ValueError(f'{path}: manifest output SHA-256 mismatch')
    if manifest['code_sha256'] != code_hashes():
        raise ValueError(f'{path}: manifest code SHA-256 mismatch')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kappa', type=float, default=1.)
    parser.add_argument('--confound', '--c', type=float, default=1.)
    parser.add_argument('--sigma', type=float, default=0.)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--n_patients', type=int, default=400)
    parser.add_argument('--horizon_h', type=float, default=6.)
    parser.add_argument('--out_dt', type=float, default=300.)
    parser.add_argument('--cf_protocol', choices=PROTOCOLS, default='shared')
    parser.add_argument('--C', type=int, default=12)
    parser.add_argument('--K', type=int, default=24)
    parser.add_argument('--out', required=True)
    args = vars(parser.parse_args())
    args['out_path'] = args.pop('out')
    make_dataset_grid(**args)
    print(json.dumps(overlap_diagnostics(args['out_path']), allow_nan=False))


if __name__ == '__main__':
    main()
