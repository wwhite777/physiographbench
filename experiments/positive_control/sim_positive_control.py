"""positive control E1 wrapper and matched forecast runner; frozen code is read-only.

The default CLI only generates data. Neural work requires run-cell and either
--smoke (one CPU epoch, <=24 patients) or a future explicitly chosen --full-run.
See DESIGN_E1.md for the pre-registered equations and interpretation limits.
"""
from __future__ import annotations

import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[2]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH

import argparse
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parent
PROJECT = RELEASE_ROOT
SCRATCH = RELEASE_SCRATCH
COHORT = PROJECT / 'data/cinc2019_cohort.npz'
BASE_SIM = PROJECT / 'sim'
SHARED_SIM = PROJECT / 'sim'
MATCHED_SIM = PROJECT / 'sim'
CHANNELS = ('MAP', 'HR', 'CO', 'CVP', 'UO', 'Lac')
ORGANS = {'cardiovascular': [0, 1, 2, 3], 'renal': [4], 'metabolic': [5]}
VARIANTS = ('admissible', 'reversed', 'random', 'dense', 'none', 'misspecified-1')
ARMS = (*VARIANTS, 'control_gru', 'control_gru_matched')
C, K, OUT_DT, HORIZON_H = 12, 24, 300., 6.
PARAMETERS = dict(
    source_tau_min=60., source_sd=1., source_loadings=[12., -3., .6, .3],
    reserve_tau_min=30., reserve_initial_sd=.25,
    drive_weights=[.60, .25, -.15, .30],
    drive_centers=[85., 5., 8., 0.], drive_scales=[15., 1.5, 4., .30],
    local_tau_min=90., local_sd=[.08, .15], offset_sd=[.12, .25],
    target_centers=[1.10, 3.20], target_loadings=[.45, -1.],
    target_lag_steps=[6, 9], target_tau_min=[10., 20.],
    clean_bounds=[[.05, 2.8], [.1, 10.]], noise_sd=[.08, .15])


def configure_scratch():
    """Keep library temporary/cache files in the one authorized private scratch."""
    SCRATCH.mkdir(parents=True, exist_ok=True)
    for key in ('TMPDIR', 'TMP', 'TEMP'):
        os.environ[key] = str(SCRATCH)
    os.environ['XDG_CACHE_HOME'] = str(SCRATCH / 'cache')
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
    sys.dont_write_bytecode = True


def owned_path(path):
    result = Path(path).resolve()
    if not (result.is_relative_to(ROOT) or result.is_relative_to(SCRATCH)):
        raise ValueError(f'Output must be inside {ROOT}: {result}')
    return result


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = owned_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as handle:
        handle.write(json.dumps(value, indent=2, allow_nan=False) + '\n')


def source_hashes():
    return {str(path): sha256(path) for path in (
        PROJECT / 'src/cvsim_hemodynamics_simulator.py',
        BASE_SIM / 'sim_policy_ext.py', SHARED_SIM / 'sim_policy_ext2.py',
        Path(__file__).resolve())}


@lru_cache(maxsize=1)
def clinical_rates():
    """Count observed entries only over valid hours; fit E1 rates on A-train."""
    if not COHORT.is_file():
        return json.loads((ROOT / 'clinical_observation_rates.json').read_text())
    result = {'path': str(COHORT), 'sha256': sha256(COHORT), 'cohorts': {}}
    with np.load(COHORT, allow_pickle=False) as packed:
        features = packed['features'].tolist()
        columns = [features.index(name) for name in ('Creatinine', 'BUN', 'Lactate')]
        for cohort, label, selection in (
                ('A', 'A_train', packed['train_idx']),
                ('A', 'A_all', None), ('B', 'B_all', None)):
            mask, lengths = packed[f'{cohort}_mask'], packed[f'{cohort}_length']
            if selection is not None:
                mask, lengths = mask[selection], lengths[selection]
            valid = np.arange(mask.shape[1])[None, :] < lengths[:, None]
            denominator = int(valid.sum())
            observed = mask[..., columns] > 0
            counts = (observed & valid[..., None]).sum(axis=(0, 1))
            union = int(((observed[..., 0] | observed[..., 1]) & valid).sum())
            result['cohorts'][label] = dict(
                n_patients=len(lengths), valid_hours=denominator,
                counts=dict(zip(('Creatinine', 'BUN', 'Lactate'), map(int, counts))),
                rates=dict(zip(('Creatinine', 'BUN', 'Lactate'),
                               (counts / denominator).tolist())),
                renal_union_count=union, renal_union_rate=union / denominator)
    return result


def target_probabilities(hourly_matched=False):
    train = clinical_rates()['cohorts']['A_train']
    probabilities = np.array([train['renal_union_rate'], train['rates']['Lactate']])
    if hourly_matched:
        probabilities = 1. - (1. - probabilities) ** (1. / 12.)
    return probabilities


def _rng(seed, stream):
    return np.random.default_rng(np.random.SeedSequence([seed, stream]))


def _ou(seed, stream, n_patients, n_times, tau_min, sd):
    draws = _rng(seed, stream).normal(size=(n_patients, n_times))
    result = np.empty_like(draws)
    result[:, 0] = sd * draws[:, 0]
    decay = np.exp(-OUT_DT / 60. / tau_min)
    innovation = sd * np.sqrt(1. - decay ** 2)
    for t in range(1, n_times):
        result[:, t] = decay * result[:, t - 1] + innovation * draws[:, t]
    return result


def base_cardiovascular(n_patients, seed=0):
    """Integrate factual lanes only, using frozen sampling and RK4 unchanged."""
    configure_scratch()
    sys.path.insert(0, str(SHARED_SIM))
    import sim_policy_ext2 as shared
    sources = {str(path): sha256(path) for path in (
        PROJECT / 'src/cvsim_hemodynamics_simulator.py',
        BASE_SIM / 'sim_policy_ext.py', SHARED_SIM / 'sim_policy_ext2.py')}
    config = dict(n_patients=n_patients, seed=seed, horizon_h=HORIZON_H,
                  out_dt=OUT_DT, kappa=0., confound=1., sigma=.03, sources=sources)
    key = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:20]
    path = SCRATCH / f'base_cv_{key}.npz'
    manifest_path = path.with_suffix('.json')
    if path.exists():
        manifest = json.loads(manifest_path.read_text())
        if manifest['config'] != config or manifest['sha256'] != sha256(path):
            raise ValueError('Base cardiovascular cache failed integrity validation')
        with np.load(path, allow_pickle=False) as packed:
            return {name: packed[name] for name in packed.files}
    start = time.perf_counter()
    placeholders, jobs = shared._record_jobs(0., 1., .03, seed, n_patients,
                                             HORIZON_H, OUT_DT)
    stride = 1 + len(placeholders['cf_doses'])
    factual_jobs = jobs[::stride]
    trajectories = shared.previous._integrate_jobs(factual_jobs)
    result = dict(cardiovascular=trajectories[..., :4],
                  controls=trajectories[..., 7:8], t_min=placeholders['t_min'])
    if not all(np.isfinite(value).all() for value in result.values()):
        raise ValueError('Frozen cardiovascular integration produced nonfinite values')
    np.savez_compressed(path, **result)
    write_json(manifest_path, dict(config=config, sha256=sha256(path),
                                  integration_seconds=time.perf_counter() - start))
    return result


def generate(n_patients=400, kappa=1., seed=0, probabilities=None, out=None):
    """Return masked observations, dense synthetic labels, and separate audit arrays.

    Only values, mask, and controls are input candidates. Diagnostics are never
    included by prepare_data or batches. All random streams are paired in kappa.
    """
    if n_patients < 4 or not np.isfinite(kappa) or not 0 <= kappa <= 1 or seed < 0:
        raise ValueError('Require >=4 patients, kappa in [0,1], and nonnegative seed')
    if out is not None and owned_path(out).exists():
        raise FileExistsError(out)
    start = time.perf_counter()
    base = base_cardiovascular(n_patients, seed)
    n_times = len(base['t_min'])
    source = _ou(seed, 1, n_patients, n_times, 60., 1.)
    cv = base['cardiovascular'] + source[..., None] * np.array([12., -3., .6, .3])
    driver = (.60 * (cv[..., 0] - 85.) / 15. + .25 * (cv[..., 2] - 5.) / 1.5
              - .15 * (cv[..., 3] - 8.) / 4. + .30 * base['controls'][..., 0] / .30)
    reserve = np.empty((n_patients, n_times))
    reserve[:, 0] = _rng(seed, 2).normal(0., .25, n_patients)
    decay = np.exp(-5. / 30.)
    for t in range(1, n_times):
        reserve[:, t] = decay * reserve[:, t - 1] + (1. - decay) * driver[:, t - 1]
    offsets = _rng(seed, 3).normal(size=(n_patients, 2)) * np.array([.12, .25])
    local = np.stack([_ou(seed, 4, n_patients, n_times, 90., .08),
                      _ou(seed, 5, n_patients, n_times, 90., .15)], axis=-1)
    equilibrium = np.array([1.10, 3.20]) + offsets[:, None, :] + local
    for j, (lag, loading) in enumerate(zip((6, 9), (.45, -1.))):
        delayed = reserve[:, np.maximum(np.arange(n_times) - lag, 0)]
        equilibrium[..., j] += kappa * loading * delayed
    targets = np.empty_like(equilibrium)
    targets[:, 0] = equilibrium[:, 0]
    target_decay = np.exp(-5. / np.array([10., 20.]))
    for t in range(1, n_times):
        targets[:, t] = (target_decay * targets[:, t - 1]
                         + (1. - target_decay) * equilibrium[:, t - 1])
    bounded = np.clip(targets, [.05, .1], [2.8, 10.])
    clipped = np.mean(targets != bounded, axis=(0, 1))
    noisy = bounded + _rng(seed, 6).normal(size=bounded.shape) * np.array([.08, .15])
    truth = np.concatenate([cv, noisy], axis=-1).astype(np.float32)
    uniforms = _rng(seed, 7).uniform(size=bounded.shape)
    probabilities = (target_probabilities() if probabilities is None
                     else np.asarray(probabilities, dtype=float))
    if (probabilities.shape != (2,) or not np.isfinite(probabilities).all()
            or np.any((probabilities < 0) | (probabilities > 1))):
        raise ValueError('Require two finite target observation probabilities in [0,1]')
    mask = np.ones_like(truth, dtype=bool)
    mask[..., 4:] = uniforms < probabilities
    metadata = dict(
        schema_version=1, regime='E1', n_patients=n_patients, kappa=float(kappa),
        seed=seed, horizon_h=HORIZON_H, out_dt=OUT_DT, C=C, K=K,
        parameters=PARAMETERS, target_probabilities=probabilities.tolist(),
        clinical_rates=clinical_rates(), source_sha256=source_hashes(),
        clean_clipped_fraction=clipped.tolist(),
        realized_observation_fractions=mask.mean(axis=(0, 1)).tolist(),
        supervision='Dense noisy synthetic labels; only context inputs are masked.',
        generation_seconds=time.perf_counter() - start)
    result = dict(values=np.where(mask, truth, 0.).astype(np.float32), mask=mask,
                  truth=truth, controls=base['controls'].astype(np.float32),
                  t_min=base['t_min'], channels=np.array(CHANNELS),
                  audit_reserve=reserve, audit_source=source,
                  audit_mask_uniforms=uniforms,
                  metadata_json=np.array(json.dumps(metadata)))
    if out is not None:
        path = owned_path(out)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(path, **result)
        write_json(path.with_suffix('.manifest.json'), dict(
            metadata=metadata, output_sha256=sha256(path),
            command_line=[sys.executable, *sys.argv]))
    return result


def remask(data, probabilities):
    """Nested observation sensitivity; never change labels or physical dynamics."""
    probabilities = np.asarray(probabilities, dtype=float)
    if probabilities.shape != (2,) or not np.isfinite(probabilities).all() or np.any(
            (probabilities < 0) | (probabilities > 1)):
        raise ValueError('Invalid target observation probabilities')
    result = dict(data)
    mask = np.ones_like(data['mask'])
    mask[..., 4:] = data['audit_mask_uniforms'] < probabilities
    result['mask'] = mask
    result['values'] = np.where(mask, data['truth'], 0.).astype(np.float32)
    metadata = json.loads(str(data['metadata_json']))
    metadata['target_probabilities'] = probabilities.tolist()
    metadata['realized_observation_fractions'] = mask.mean(axis=(0, 1)).tolist()
    result['metadata_json'] = np.array(json.dumps(metadata))
    return result


def patient_split(n_patients, seed):
    permutation = np.random.default_rng(seed).permutation(n_patients)
    boundary = int(.7 * n_patients)
    return permutation[:boundary], permutation[boundary:]


def prepare_data(dataset, seed=0):
    """Allowlist model-accessible data; no private state enters the data loader."""
    train, test = patient_split(len(dataset['values']), seed)
    labels = dataset['truth'].astype(np.float32)
    mean = labels[train].reshape(-1, 6).mean(0)
    std = labels[train].reshape(-1, 6).std(0) + 1e-6
    return dict(values=dataset['values'], mask=dataset['mask'], truth=labels,
                controls=dataset['controls'], mean=mean, std=std, tr=train, te=test)


def batches(data, indices, device, batch_size=128):
    import torch
    for start in range(0, len(indices), batch_size):
        selected = indices[start:start + batch_size]
        mask = data['mask'][selected, :C]
        normalized = ((data['values'][selected, :C] - data['mean']) / data['std'])
        values = np.where(mask, normalized, 0.)
        yield dict(
            values=torch.tensor(values, device=device),
            mask=torch.tensor(mask, dtype=torch.float32, device=device),
            control_ctx=torch.tensor(data['controls'][selected, :C], device=device),
            control_future=torch.tensor(data['controls'][selected, C:C + K], device=device),
            static=torch.zeros(len(selected), 1, device=device),
            target=torch.tensor((data['truth'][selected, C:C + K] - data['mean'])
                                / data['std'], device=device))


def load_dataset(path, n_patients, kappa):
    path = owned_path(path)
    manifest = json.loads(path.with_suffix('.manifest.json').read_text())
    if manifest['output_sha256'] != sha256(path):
        raise ValueError(f'Dataset checksum mismatch: {path}')
    with np.load(path, allow_pickle=False) as packed:
        data = {name: packed[name] for name in packed.files}
    metadata = json.loads(str(data['metadata_json']))
    if (metadata['source_sha256'] != source_hashes() or metadata['n_patients'] != n_patients
            or metadata['kappa'] != kappa or metadata['seed'] != 0
            or metadata['target_probabilities'] != target_probabilities().tolist()):
        raise ValueError(f'Dataset does not match registered configuration/code: {path}')
    return data


def run_cell(*, arm, kappa, seed, epochs, n_patients, device, threads,
             out, npz=None, reference_npz=None, smoke=False, full_run=False):
    """Masked-input adaptation of H3's matched model and optimizer protocol."""
    if smoke == full_run:
        raise ValueError('Choose exactly one of --smoke or future --full-run')
    if smoke and (epochs != 1 or n_patients > 24 or device != 'cpu'):
        raise ValueError('positive control smoke permits exactly one CPU epoch and <=24 patients')
    if full_run and (epochs != 60 or n_patients != 400):
        raise ValueError('Registered full runs require 60 epochs and 400 patients')
    if arm not in ARMS or threads < 1 or seed not in range(4) or kappa not in (0., .5, 1.):
        raise ValueError('Unregistered arm, threads, seed, or kappa')
    output = owned_path(out)
    if output.exists():
        raise FileExistsError(output)
    configure_scratch()
    import torch
    sys.path.insert(0, str(MATCHED_SIM))
    from sim_grid_runner_mono2 import build_model, graph_edges, error_metrics, organ_ranges
    torch.set_num_threads(threads)
    torch.use_deterministic_algorithms(True)
    start = time.perf_counter()
    dataset = (generate(n_patients, kappa, seed=0) if npz is None
               else load_dataset(npz, n_patients, kappa))
    reference = (generate(n_patients, 1., seed=0) if reference_npz is None
                 else load_dataset(reference_npz, n_patients, 1.))
    data = prepare_data(dataset, seed)
    variant = arm if arm in VARIANTS else 'admissible'
    model_name = 'physiograph_gru' if arm in VARIANTS else 'control_gru'
    hidden = 201 if arm == 'control_gru_matched' else 96
    model = build_model(model_name, variant, seed, 64, 32, 2, hidden)
    count = sum(p.numel() for p in model.parameters())
    model.to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=.002)
    train_start = time.perf_counter()
    curve = []
    for epoch in range(epochs):
        model.train()
        losses = []
        for batch in batches(data, data['tr'], device):
            optimizer.zero_grad()
            prediction = model(batch, K)
            loss = ((prediction - batch['target']) ** 2).mean()
            if not torch.isfinite(loss):
                raise ValueError('Nonfinite training loss')
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
            optimizer.step()
            losses.append(float(loss.detach()))
        curve.append(dict(epoch=epoch + 1, train_mse=float(np.mean(losses))))
        if epoch % 5 == 0 or epoch == epochs - 1:
            print(json.dumps(curve[-1]), flush=True)
    train_seconds = time.perf_counter() - train_start
    model.eval()
    predictions = []
    with torch.no_grad():
        for batch in batches(data, data['te'], device):
            predictions.append(model(batch, K).cpu().numpy() * data['std'] + data['mean'])
    prediction = np.concatenate(predictions)
    if not np.isfinite(prediction).all():
        raise ValueError('Nonfinite evaluation predictions')
    truth = data['truth'][data['te'], C:C + K]
    fixed_ranges = organ_ranges(reference['truth'])
    result = dict(
        schema_version=1, smoke=smoke,
        config=dict(arm=arm, kappa=kappa, seed=seed, dataset_seed=0, epochs=epochs,
                    n_patients=n_patients, device=device, threads=threads, C=C, K=K,
                    lr=.002, batch_size=128, d_model=64, d_state=32, n_layers=2,
                    control_gru_hidden=hidden),
        metrics=error_metrics(prediction, truth, fixed_ranges,
                              organ_ranges(data['truth'][data['te']])),
        n_params=count, edges=[list(e) for e in graph_edges(variant, seed)]
        if arm in VARIANTS else [],
        dataset_metadata=json.loads(str(dataset['metadata_json'])),
        dataset_path=str(owned_path(npz)) if npz is not None else None,
        dataset_sha256=sha256(npz) if npz is not None else None,
        reference_path=str(owned_path(reference_npz)) if reference_npz is not None else None,
        reference_sha256=sha256(reference_npz) if reference_npz is not None else None,
        reference_ranges=fixed_ranges,
        normalization=dict(mean=data['mean'].tolist(), std=data['std'].tolist(),
                           scope='Dense labels from training patients, all saved times'),
        split=dict(train=data['tr'].tolist(), test=data['te'].tolist()),
        curve=curve, timing=dict(train_seconds=train_seconds,
                                total_seconds=time.perf_counter() - start),
        versions=dict(numpy=np.__version__, torch=torch.__version__),
        source_sha256={**source_hashes(), **{str(p): sha256(p) for p in (
            MATCHED_SIM / 'sim_grid_runner_mono2.py', PROJECT / 'src/organ_graph_ssm_model.py',
            PROJECT / 'src/cvsim_counterfactual_runner.py')}},
        caveats=['Dense synthetic target supervision; masked context only.',
                 'Frozen monolithic controls do not consume explicit masks.',
                 'Smoke metrics do not test the registered neural success criterion.'])
    write_json(output, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    generation = commands.add_parser('generate')
    generation.add_argument('--kappa', type=float, required=True)
    generation.add_argument('--n-patients', type=int, default=400)
    generation.add_argument('--seed', type=int, default=0)
    generation.add_argument('--out', required=True)
    runner = commands.add_parser('run-cell')
    runner.add_argument('--arm', choices=ARMS, required=True)
    runner.add_argument('--kappa', type=float, required=True)
    runner.add_argument('--seed', type=int, default=0)
    runner.add_argument('--epochs', type=int, default=60)
    runner.add_argument('--n-patients', type=int, default=400)
    runner.add_argument('--device', choices=('cpu', 'cuda'), default='cpu')
    runner.add_argument('--threads', type=int, default=1)
    runner.add_argument('--npz')
    runner.add_argument('--reference-npz')
    runner.add_argument('--out', required=True)
    mode = runner.add_mutually_exclusive_group(required=True)
    mode.add_argument('--smoke', action='store_true')
    mode.add_argument('--full-run', action='store_true')
    args = vars(parser.parse_args())
    command = args.pop('command')
    if command == 'generate':
        data = generate(**args)
        metadata = json.loads(str(data['metadata_json']))
        print(json.dumps(metadata, indent=2, allow_nan=False))
    else:
        result = run_cell(**args)
        print(json.dumps(dict(config=result['config'], smoke=result['smoke'],
                              macro_nrmse_fixed=result['metrics']['macro_nrmse_fixed']),
                         allow_nan=False))


if __name__ == '__main__':
    main()
