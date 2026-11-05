"""Owned extensions to the frozen CVSim; no source module is modified.

The card's equation is used literally: sigma is the TOTAL policy noise SD.
The frozen source instead uses SD=0.03, so its policy is reproduced at sigma=0.03,
not sigma=0. The RNG draw is retained even at sigma=0 to preserve patient draws.

The vectorized backend calls the frozen generator to record its simulation jobs,
then integrates those jobs together using its original RHS and RK4 functions.
Only scalar max is replaced by numpy.maximum for independent batch lanes.
Use backend='scalar' to run the unbatched frozen implementation for comparison.
"""
from __future__ import annotations

# Resolve all public modules and scratch from the release root.
import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[1]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH

import argparse
from dataclasses import fields
import hashlib
import json
from pathlib import Path
import sys
import time
import types

import numpy as np

ROOT = RELEASE_ROOT
PROJECT = Path(str(RELEASE_ROOT / '.'))
SOURCE = PROJECT / 'src/cvsim_hemodynamics_simulator.py'
sys.dont_write_bytecode = True
sys.path.insert(0, str(PROJECT / 'src'))
import cvsim_hemodynamics_simulator as frozen  # noqa: E402

CHANNELS = ('MAP', 'HR', 'CO', 'CVP', 'UO', 'Lac')
ORGANS = {'cardiovascular': [0, 1, 2, 3], 'renal': [4], 'metabolic': [5]}
POLICY_NOTE = ('sigma is total noise SD; frozen policy has SD=0.03. '
               'sigma=0 follows the card equation but cannot equal frozen doses.')


def owned_path(path):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError(f'Output must be inside {ROOT}: {path}')
    return path


def write_json(path, value):
    path = owned_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class _PolicyRNG:
    def __init__(self, rng, sigma):
        self.rng, self.sigma = rng, sigma

    def uniform(self, *args, **kwargs):
        return self.rng.uniform(*args, **kwargs)

    def normal(self, loc, scale):
        # This is the frozen generator's sole normal draw, the factual dose noise.
        if loc != 0 or scale != 0.03:
            raise ValueError('Frozen policy changed: recheck the RNG adapter')
        return self.rng.normal(loc, self.sigma)


class _PolicyNumpy:
    def __init__(self, sigma):
        self.sigma = sigma

    def __getattr__(self, name):
        if name == 'random':
            return types.SimpleNamespace(
                default_rng=lambda seed: _PolicyRNG(np.random.default_rng(seed), self.sigma))
        return getattr(np, name)


def _batched_function(function):
    namespace = dict(function.__globals__, max=np.maximum)
    return types.FunctionType(function.__code__, namespace, function.__name__,
                              function.__defaults__)


class _BatchSchedule:
    """Exact searchsorted(side='right') for each schedule, including equal knots."""
    def __init__(self, schedules):
        self.arrays = {}
        for name in ('vaso', 'fluid', 'sepsis'):
            lengths = np.array([len(getattr(s, name + '_t')) for s in schedules])
            width = int(lengths.max())
            knots = np.full((len(schedules), width), np.inf)
            values = np.zeros_like(knots)
            for i, schedule in enumerate(schedules):
                n = lengths[i]
                knots[i, :n] = getattr(schedule, name + '_t')
                values[i, :n] = getattr(schedule, name + '_v')
            self.arrays[name] = knots, values, lengths

    def _at(self, name, t):
        knots, values, lengths = self.arrays[name]
        lo, hi = np.zeros_like(lengths), lengths.copy()
        rows = np.arange(len(lengths))
        # Binary search matches the frozen np.searchsorted even for short-horizon
        # schedules whose onset+1800 knot exceeds the final horizon knot.
        for _ in range(knots.shape[1].bit_length()):
            active = lo < hi
            mid = (lo + hi) // 2
            right = knots[rows, np.minimum(mid, knots.shape[1] - 1)] <= t
            lo = np.where(active & right, mid + 1, lo)
            hi = np.where(active & ~right, mid, hi)
        return values[rows, np.maximum(lo - 1, 0)]

    def vaso(self, t):
        return self._at('vaso', t)

    def fluid(self, t):
        return self._at('fluid', t)

    def sepsis(self, t):
        return self._at('sepsis', t)


class _BatchCVSim:
    _rhs = _batched_function(frozen.CVSim._rhs)
    _rk4 = _batched_function(frozen.CVSim._rk4)
    _observe = types.FunctionType(
        frozen.CVSim._observe.__code__,
        dict(frozen.CVSim._observe.__globals__, max=np.maximum, float=lambda x: x))
    _pressures = frozen.CVSim._pressures


def _integrate_jobs(jobs):
    sim = _BatchCVSim()
    sim.p = types.SimpleNamespace(**{
        field.name: np.array([getattr(job[0], field.name) for job in jobs])
        for field in fields(frozen.Hemodynamics) if field.name != 'baro_on'})
    sim.p.baro_on = True  # sample_patient always uses the frozen default True.
    schedules = [job[1] for job in jobs]
    schedule = _BatchSchedule(schedules)
    y = np.stack([job[2] for job in jobs], axis=1)
    dt, out_dt, warmup_s = jobs[0][3:]
    warm = _BatchSchedule([
        frozen.InterventionSchedule(horizon_s=warmup_s,
                                    vaso_v=np.array([s.vaso(0.0)]),
                                    sepsis_v=np.array([s.sepsis(0.0)]))
        for s in schedules])
    for i in range(int(warmup_s / dt)):
        y = sim._rk4(i * dt, y, warm, dt)
    stride = max(1, int(round(out_dt / dt)))
    records = []
    n = int(schedules[0].horizon_s / dt)
    for i in range(n + 1):
        t = i * dt
        if i % stride == 0:
            records.append(np.stack(sim._observe(t, y, schedule)[1:], axis=-1))
        if i < n:
            y = sim._rk4(t, y, schedule, dt)
    return np.stack(records, axis=1)  # (jobs, T, 8)


def make_dataset_grid(kappa, confound, sigma, seed, n_patients, out_path,
                      *, horizon_h=6.0, out_dt=300.0, backend='vectorized'):
    """Generate a cell using the card's policy and the frozen sampling/integration.

    Defaults preserve the frozen 6-hour horizon, 300-second sampling, 0.5-second
    RK4 integration and 180-second warmup. Vectorization changes neither these
    settings nor the per-patient random-number stream.
    """
    if not 0 <= kappa <= 1 or not 0 <= confound <= 1 or sigma < 0:
        raise ValueError('Require 0 <= kappa, confound <= 1 and sigma >= 0')
    if n_patients < 3 or horizon_h <= 0 or out_dt <= 0:
        raise ValueError('Require >=3 patients and positive horizon/sample interval')
    if backend not in ('scalar', 'vectorized'):
        raise ValueError(backend)
    path = owned_path(out_path) if out_path is not None else None
    start = time.perf_counter()
    namespace = dict(frozen.make_counterfactual_dataset.__globals__, np=_PolicyNumpy(sigma))
    jobs = []
    if backend == 'vectorized':
        class RecordingCVSim(frozen.CVSim):
            def simulate(self, sch, dt=0.05, out_dt=60.0, y0=None, warmup_s=120.0):
                jobs.append((self.p, sch, self.initial_state() if y0 is None else y0.copy(),
                             dt, out_dt, warmup_s))
                ticks = np.arange(0, int(sch.horizon_s / dt) + 1,
                                  max(1, int(round(out_dt / dt)))) * dt / 60
                return {key: ticks if key == 't_min' else np.zeros(len(ticks))
                        for key in ('t_min', *CHANNELS, 'sepsis', 'vaso')}
        namespace['CVSim'] = RecordingCVSim
    generator = types.FunctionType(frozen.make_counterfactual_dataset.__code__, namespace,
                                   argdefs=frozen.make_counterfactual_dataset.__defaults__)
    data = generator(n_patients=n_patients, horizon_h=horizon_h, out_dt=out_dt,
                     seed=seed, out_path=None, confound=confound, coupling=kappa)
    if jobs:
        trajectories = _integrate_jobs(jobs).astype(np.float32)
        grouped = trajectories.reshape(n_patients, 1 + len(data['cf_doses']),
                                       len(data['t_min']), 8)
        # _observe returns (..., sepsis, vaso); packed factual stores (..., vaso, sepsis).
        data['factual'] = grouped[:, 0][..., [0, 1, 2, 3, 4, 5, 7, 6]].copy()
        data['counterfactual'] = grouped[:, 1:, :, :6].copy()
    metadata = dict(kappa=kappa, confound=confound, sigma=sigma, seed=seed,
                    n_patients=n_patients, horizon_h=horizon_h, out_dt=out_dt,
                    backend=backend, policy_note=POLICY_NOTE,
                    source_sha256=sha256(SOURCE), elapsed_seconds=time.perf_counter() - start)
    data['metadata_json'] = np.array(json.dumps(metadata))
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(path, **data)
    return data


def overlap_diagnostics(npz_path):
    """Conditional support summaries; these do not certify identification."""
    with np.load(npz_path) as data:
        severity = data['severity'].astype(float)
        dose = data['factual_dose'].astype(float)
        metadata = json.loads(str(data['metadata_json'])) if 'metadata_json' in data else {}
    if len(severity) < 3:
        raise ValueError('Severity terciles require at least 3 patients')
    cutpoints = np.quantile(severity, [1 / 3, 2 / 3])
    groups = np.searchsorted(cutpoints, severity, side='right')
    grid = np.array([0., .05, .1, .2, .4])
    result = dict(n_patients=len(dose),
                  corr_severity_dose=float(np.corrcoef(severity, dose)[0, 1])
                  if np.std(dose) > 0 and np.std(severity) > 0 else None,
                  severity_cutpoints=cutpoints.tolist(), dose_grid=grid.tolist(),
                  metadata=metadata, terciles=[])
    for tercile in range(3):
        selected = dose[groups == tercile]
        if not len(selected):
            raise ValueError('An empty severity tercile prevents support diagnostics')
        quantiles = np.quantile(selected, [.05, .25, .5, .75, .95])
        supported = (grid >= quantiles[0]) & (grid <= quantiles[-1])
        result['terciles'].append(dict(
            tercile=tercile + 1, n_patients=len(selected),
            severity_range=[float(severity[groups == tercile].min()),
                            float(severity[groups == tercile].max())],
            dose_quantiles=dict(zip(('5', '25', '50', '75', '95'), quantiles.tolist())),
            supported_dose_range=[float(quantiles[0]), float(quantiles[-1])],
            supported_grid=supported.tolist(), fraction_grid_supported=float(supported.mean())))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kappa', type=float, default=1.)
    parser.add_argument('--confound', '--c', type=float, default=1.)
    parser.add_argument('--sigma', type=float, default=0.)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--n_patients', type=int, default=400)
    parser.add_argument('--horizon_h', type=float, default=6.)
    parser.add_argument('--out_dt', type=float, default=300.)
    parser.add_argument('--backend', choices=['scalar', 'vectorized'], default='vectorized')
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    make_dataset_grid(args.kappa, args.confound, args.sigma, args.seed, args.n_patients,
                      args.out, horizon_h=args.horizon_h, out_dt=args.out_dt,
                      backend=args.backend)
    print(json.dumps(overlap_diagnostics(args.out), allow_nan=False))


if __name__ == '__main__':
    main()
