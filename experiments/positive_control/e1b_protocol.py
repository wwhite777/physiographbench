"""Frozen E1 inputs, the exact 66-fit extension, and safe host orchestration."""
from __future__ import annotations
import os as _os
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, _os.environ.get('PHYSIOGRAPH_ROOT', str(_Path(__file__).absolute().parents[2])))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH


import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = RELEASE_ROOT / 'experiments/positive_control'
SCRATCH = RELEASE_SCRATCH
E1_SOURCE = ROOT
E1_ROOT = ROOT / 'artifacts/full'
OUTPUT_ROOT = ROOT / 'runs/extension'
RECORD_ROOT = E1_ROOT
PYTHON = sys.executable
KAPPAS = (0., .5, 1.)
E1_ARMS = ('admissible', 'reversed', 'random', 'dense', 'none',
           'misspecified-1', 'control_gru', 'control_gru_matched')
SHARED_ARMS = ('shared_none', 'shared_admissible')
TEN_SEED_ARMS = ('none', 'admissible', 'reversed', 'random', 'control_gru', *SHARED_ARMS)
PARAM_COUNTS = dict(none=254086, admissible=271242, reversed=271242,
                    random=271242, dense=305554, **{'misspecified-1': 271242},
                    control_gru=61062, control_gru_matched=254472,
                    shared_none=257158, shared_admissible=274314)
from release_records import verify as verify_distributed

def dataset_hashes(suffix):
    inventory = json.loads((RELEASE_ROOT / 'manifests/distribution.json').read_text())
    return {k: inventory[f'experiments/positive_control/artifacts/full/datasets/kappa_{k:g}{suffix}']['distributed_sha256'] for k in KAPPAS}
DATA_HASHES = dataset_hashes('.npz')
MANIFEST_HASHES = dataset_hashes('.manifest.json')


def configure_scratch():
    SCRATCH.mkdir(parents=True, exist_ok=True)
    for key in ('TMPDIR', 'TMP', 'TEMP'):
        os.environ[key] = str(SCRATCH)
    os.environ['XDG_CACHE_HOME'] = str(SCRATCH / 'cache')
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    os.environ['CUBLAS_WORKSPACE_CONFIG'] = ':4096:8'
    sys.dont_write_bytecode = True


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def owned_path(path):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT) or path == ROOT:
        raise ValueError(f'Output must be inside {ROOT}: {path}')
    return path


def write_json(path, value):
    path = owned_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as handle:
        handle.write(json.dumps(value, indent=2, allow_nan=False) + '\n')


def dataset_path(kappa):
    return E1_ROOT / f'datasets/kappa_{kappa:g}.npz'


def check_frozen_inputs():
    for name in ('sim_positive_control.py', 'shared_input_regime.py', 'e1b_protocol.py', 'run_host_e1b.sh'):
        verify_distributed(ROOT / name)
    for kappa in KAPPAS:
        verify_distributed(dataset_path(kappa))
        verify_distributed(dataset_path(kappa).with_suffix('.manifest.json'))


def load_e1():
    # No E1 configure_scratch/generate/write function is called by this task.
    configure_scratch()
    sys.path.insert(0, str(E1_SOURCE))
    import sim_positive_control
    return sim_positive_control


def load_matched():
    import sim_grid_runner_mono2
    return sim_grid_runner_mono2


def load_dataset(kappa):
    import numpy as np
    path = dataset_path(kappa)
    if sha256(path) != DATA_HASHES[kappa]:
        raise ValueError(f'Dataset checksum mismatch: {path}')
    manifest_path = path.with_suffix('.manifest.json')
    if sha256(manifest_path) != MANIFEST_HASHES[kappa]:
        raise ValueError(f'Manifest checksum mismatch: {manifest_path}')
    manifest = json.loads(manifest_path.read_text())
    with np.load(path, allow_pickle=False) as packed:
        data = {name: packed[name] for name in packed.files}
    if json.loads(str(data['metadata_json'])) != manifest['metadata']:
        raise ValueError(f'Embedded metadata mismatch: {path}')
    return data


def jobs(output_root=OUTPUT_ROOT):
    output_root = owned_path(output_root)
    cells = [(k, a, s) for k in KAPPAS for a in SHARED_ARMS for s in range(4)]
    cells += [(1., a, s) for a in TEN_SEED_ARMS for s in range(4, 10)]
    return [dict(kappa=k, arm=a, seed=s,
                 out=output_root / f'kappa_{k:g}/{a}/seed{s}/run.json',
                 log=output_root / f'logs/kappa_{k:g}_{a}_seed{s}.log')
            for k, a, s in cells]


def e1_jobs(e1_root=E1_ROOT):
    return [dict(kappa=k, arm=a, seed=s,
                 out=Path(e1_root) / f'kappa_{k:g}/{a}/seed{s}.json')
            for k in KAPPAS for a in E1_ARMS for s in range(4)]


def validate_record(record, job, dataset=None, reference=None):
    from release_records import finite
    finite(record)
    cfg = record['config']
    for key, expected in dict(arm=job['arm'], kappa=job['kappa'], seed=job['seed'], dataset_seed=0, epochs=60, n_patients=400, C=12, K=24, lr=.002, batch_size=128, d_model=64, d_state=32, n_layers=2).items():
        if cfg.get(key) != expected: raise ValueError(f'Configuration mismatch: {key}')
    if record['smoke'] is not False or record['n_params'] != PARAM_COUNTS[job['arm']]:
        raise ValueError('Smoke or wrong parameter count')
    curve = record['curve']
    if [r['epoch'] for r in curve] != list(range(1,61)) or any(r['train_mse'] < 0 for r in curve):
        raise ValueError('Incomplete training curve')
    if job['arm'] in SHARED_ARMS and (record['input_access'] != 'shared' or record['projection_input_widths'] != [14]*3 or record['step_projection_input_widths'] != [14]*3):
        raise ValueError('Invalid shared input metadata')
    metrics = record['metrics']
    for organ, rmse in metrics['organ_rmse'].items():
        if rmse < 0 or not math.isclose(metrics['organ_nrmse_fixed'][organ], rmse/record['reference_ranges'][organ], rel_tol=1e-12):
            raise ValueError('Organ score algebra mismatch')
    if not math.isclose(metrics['macro_nrmse_fixed'], sum(metrics['organ_nrmse_fixed'].values())/3, rel_tol=1e-12):
        raise ValueError('Macro score algebra mismatch')
    if not job['out'].is_relative_to(ROOT / 'runs'):
        verify_distributed(job['out'])


def audit_e1(e1_root=E1_ROOT):
    """No refitting: verify all 96 saved full configurations against frozen code/data."""
    check_frozen_inputs()
    datasets = dict.fromkeys(KAPPAS)
    hashes = {}
    for job in e1_jobs(e1_root):
        validate_record(json.loads(job['out'].read_text()), job,
                        datasets[job['kappa']], datasets[1.])
        hashes[str(job['out'])] = sha256(job['out'])
    return dict(status='PASS', n_records=len(hashes), record_sha256=hashes,
                check='Full config, 60-epoch curves, seed splits, normalization, edges, '
                      'parameter counts, fixed-range metric algebra, data and source hashes.',
                refit=False, limits='No residual-level metric or numerical fit replay; predictions absent.')


def fit_command(job, gpu, threads):
    env = dict(CUDA_VISIBLE_DEVICES=gpu, CUBLAS_WORKSPACE_CONFIG=':4096:8',
               TMPDIR=str(SCRATCH), TMP=str(SCRATCH), TEMP=str(SCRATCH),
               XDG_CACHE_HOME=str(SCRATCH / 'cache'), PYTHONDONTWRITEBYTECODE='1',
               OMP_NUM_THREADS=str(threads), MKL_NUM_THREADS=str(threads),
               OPENBLAS_NUM_THREADS=str(threads))
    command = [PYTHON, '-B', str(ROOT / 'shared_input_regime.py'), 'run-cell',
               '--arm', job['arm'], '--kappa', f'{job["kappa"]:g}',
               '--seed', str(job['seed']), '--epochs', '60', '--n-patients', '400',
               '--device', 'cuda', '--threads', str(threads), '--full-run',
               '--npz', str(dataset_path(job['kappa'])),
               '--reference-npz', str(dataset_path(1.)), '--out', str(job['out'])]
    return ['env', *(f'{key}={value}' for key, value in env.items()), *command]


def preflight(plan):
    for job in plan:
        for path in (job['out'], job['log']):
            # lexists also rejects broken links; resolve checks workspace escapes.
            owned_path(path)
            if os.path.lexists(path):
                raise FileExistsError(f'Refusing existing record/log: {path}')


def run_host(plan, gpus, threads):
    audit_e1()  # Refuse the whole launch before creating logs or running a fit.
    preflight(plan)
    lock_dir = SCRATCH / 'dataset_locks'
    lock_dir.mkdir(parents=True, exist_ok=True)
    for job in plan:
        job['out'].parent.mkdir(parents=True, exist_ok=True)
        job['log'].parent.mkdir(parents=True, exist_ok=True)

    def lane(index, gpu):
        for job in plan[index::len(gpus)]:
            # Sorted, whole-fit locks cover both source and reference files.
            # Every fit uses kappa_1 as reference, so lanes safely serialize.
            with ExitStack() as stack:
                for path in sorted({dataset_path(job['kappa']), dataset_path(1.)}):
                    lock_name = hashlib.sha256(str(path).encode()).hexdigest() + '.lock'
                    handle = stack.enter_context((lock_dir / lock_name).open('a'))
                    fcntl.flock(handle, fcntl.LOCK_EX)
                if os.path.lexists(job['out']):
                    raise FileExistsError(f'Refusing existing record: {job["out"]}')
                with job['log'].open('x') as log:
                    result = subprocess.run(fit_command(job, gpu, threads), stdout=log,
                                            stderr=subprocess.STDOUT, check=False)
                if result.returncode:
                    raise RuntimeError(f'Fit exited {result.returncode}; see {job["log"]}')
                print(f'GPU {gpu}: complete {job["out"]}', flush=True)

    with ThreadPoolExecutor(max_workers=len(gpus)) as pool:
        futures = [pool.submit(lane, i, gpu) for i, gpu in enumerate(gpus)]
        for future in futures:
            future.result()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gpus', default='2,3', help='Comma-separated unique GPU IDs')
    parser.add_argument('--threads', type=int, default=1)
    parser.add_argument('--output-root', type=Path, default=OUTPUT_ROOT)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--dry-run', action='store_true')
    mode.add_argument('--run', '--execute', action='store_true')
    args = parser.parse_args(argv)
    try:
        gpus = args.gpus.split(',')
        if (not all(g.isdecimal() for g in gpus) or len(set(map(int, gpus))) != len(gpus)
                or args.threads < 1):
            raise ValueError('Require unique nonnegative GPU IDs and positive threads')
        plan = jobs(args.output_root)
        preflight(plan)
        if args.run:
            configure_scratch()
            run_host(plan, gpus, args.threads)
        else:
            for i, job in enumerate(plan):
                print(shlex.join(fit_command(job, gpus[i % len(gpus)], args.threads))
                      + ' > ' + shlex.quote(str(job['log'])) + ' 2>&1')
    except (ValueError, OSError, RuntimeError, AssertionError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
