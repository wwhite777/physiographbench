#!/usr/bin/env python3
"""Owned output adapter for simulator_grid's read-only simulator wrapper.

Calls make_dataset_grid(out_path=None) and saves the returned arrays here. The
wrapper's output-root guard is left intact. No frozen module is changed on disk.
"""
from __future__ import annotations

# Resolve all public modules and scratch from the release root.
import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[1]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import sys
import time

sys.dont_write_bytecode = True
ROOT = RELEASE_ROOT
PROJECT = Path(str(RELEASE_ROOT / '.'))
WRAPPER = PROJECT / 'sim/sim_policy_ext.py'
SOURCE = PROJECT / 'src/cvsim_hemodynamics_simulator.py'
EXPECTED = {p: json.loads((ROOT / 'manifests/distribution.json').read_text())[str(p.relative_to(ROOT))]['distributed_sha256'] for p in (WRAPPER, SOURCE)}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def owned(path):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError(f'Output must be inside {ROOT}: {path}')
    return path


def save_json(path, data):
    path = owned(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kappa', type=float, required=True)
    parser.add_argument('--confound', type=float, default=1.0)
    parser.add_argument('--sigma', type=float, default=0.03)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--n_patients', type=int, default=400)
    parser.add_argument('--horizon_h', type=float, default=36.0)
    parser.add_argument('--out_dt', type=float, default=3600.0)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--deadline-utc', type=float, required=True,
                        help='Unix time; checked cooperatively within integration')
    args = parser.parse_args()
    output = owned(args.out)
    manifest = output.with_suffix('.manifest.json')
    if output.exists() or manifest.exists():
        raise FileExistsError(f'Refusing to replace generated evidence: {output}')
    hashes = {str(path): sha256(path) for path in EXPECTED}
    for path, expected in EXPECTED.items():
        if hashes[str(path)] != expected:
            raise ValueError(f'Frozen source hash mismatch: {path}')
    hashes[str(Path(__file__).resolve())] = sha256(__file__)
    spec = importlib.util.spec_from_file_location('simulator_grid_sim_policy', WRAPPER)
    wrapper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wrapper)

    # Instrument the imported batched integrator, leaving its numerical step
    # unchanged. This checks the task deadline without signaling any process.
    original_step = wrapper._BatchCVSim._rk4
    steps = 0
    started = time.monotonic()
    started_utc = datetime.now(timezone.utc).isoformat()

    def monitored_step(self, t, y, schedule, dt):
        nonlocal steps
        if steps % 7200 == 0:
            if time.time() >= args.deadline_utc:
                raise TimeoutError('Task wall-time deadline reached during integration')
            print(f'kappa={args.kappa:g} steps={steps} simulation_hour={t / 3600:.2f} '
                  f'elapsed_seconds={time.monotonic() - started:.1f}', flush=True)
        steps += 1
        return original_step(self, t, y, schedule, dt)

    wrapper._BatchCVSim._rk4 = monitored_step
    print(f'START kappa={args.kappa:g} patients={args.n_patients}', flush=True)
    data = wrapper.make_dataset_grid(
        args.kappa, args.confound, args.sigma, args.seed, args.n_patients, None,
        horizon_h=args.horizon_h, out_dt=args.out_dt, backend='vectorized')
    import numpy as np
    if not np.isfinite(data['factual']).all() or not np.isfinite(data['counterfactual']).all():
        raise ValueError('Nonfinite simulator output')
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output, **data)
    settings = dict(kappa=args.kappa, confound=args.confound, sigma=args.sigma,
                    seed=args.seed, n_patients=args.n_patients,
                    horizon_h=args.horizon_h, out_dt=args.out_dt)
    record = dict(
        schema_version=1, task='hourly_calibration-sim-hourly-calibration-build', **settings,
        c=args.confound, horizon_s=args.horizon_h * 3600,
        warmup_s=180.0, integration_dt=0.5, backend='vectorized',
        command_line=shlex.join([sys.executable, '-B', str(Path(__file__).resolve()), *sys.argv[1:]]),
        generation_command_line=shlex.join([sys.executable, '-B', str(Path(__file__).resolve()), *sys.argv[1:]]),
        generation_args=settings, code_sha256=hashes, source_sha256=hashes[str(SOURCE)],
        source_integrity_verified=all(sha256(p) == h for p, h in hashes.items()),
        output_path=str(output), output_sha256=sha256(output),
        generation_wall_seconds=time.monotonic() - started,
        started_utc=started_utc, finished_utc=datetime.now(timezone.utc).isoformat(),
        environment=dict(python=sys.version, executable=sys.executable,
                         numpy=np.__version__, device='cpu', threads=1),
        shapes={k: list(v.shape) for k, v in data.items()},
        storage_note='Unchanged simulator_grid make_dataset_grid called with out_path=None; returned arrays saved in this owned workspace.',
        deadline_note='Imported RK4 method wrapped only to print progress and check wall deadline; numerical step is unchanged.',
        schedule=dict(factual_dose_onset_hours=0.2 * args.horizon_h,
                      sepsis_onset_hours_range=[0, 0.25 * args.horizon_h],
                      sepsis_final_knot_offset_hours=0.5,
                      counterfactuals='five full trajectories, not used by hourly probe'),
        all_entries_observed=True, observation_mask=1)
    save_json(manifest, record)
    print(f'DONE {output} sha256={record["output_sha256"]} '
          f'seconds={record["generation_wall_seconds"]:.1f}', flush=True)


if __name__ == '__main__':
    main()
