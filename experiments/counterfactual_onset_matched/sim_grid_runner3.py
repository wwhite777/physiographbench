"""CPU E3 fits with onset-aware plans, repaired CRN-lite and auditable scores."""
from __future__ import annotations

import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[2]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent
SCRATCH = RELEASE_SCRATCH
for name in ('TMPDIR', 'TMP', 'TEMP'):
    os.environ[name] = str(SCRATCH)
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.dont_write_bytecode = True
SCRATCH.mkdir(parents=True, exist_ok=True)

import numpy as np
import torch
from torch import nn

import sim_policy_ext3 as generator
from sim_grid_runner import build_model
from sim_grid_runner2 import support_for_patients
from cvsim_counterfactual_runner import CRNLite, grad_reverse, load_cvsim

MODELS = ('control_gru', 'crn_lite', 'physiograph_gru', 'physiograph', 'crn_continuous')
EFFECT_TOLERANCES = np.array([.1, .1, .01, .05, .01, .01])


class RepairedCRNLite(CRNLite):
    """Same backbone/head, auxiliary label is assigned eventual factual dose."""
    def aux_loss(self, batch):
        assigned = batch['assigned_factual_dose']
        if assigned.shape != (len(batch['values']), 1):
            raise ValueError('Assigned dose must have shape (batch,1)')
        prediction = self.treat_head(grad_reverse(self._h, self.lamb))
        return .5 * (prediction - assigned).square().mean()


def make_batches(data, indices, C, K, device, batch_size=128):
    normalized = (data['obs'] - data['mean']) / data['std']
    for start in range(0, len(indices), batch_size):
        ix = indices[start:start + batch_size]
        values = torch.as_tensor(normalized[ix, :C], device=device)
        yield dict(values=values, mask=torch.ones_like(values),
            control_ctx=torch.as_tensor(data['vaso'][ix, :C], device=device),
            control_future=torch.as_tensor(data['vaso'][ix, C:C + K], device=device),
            assigned_factual_dose=torch.as_tensor(data['assigned_dose'][ix, None], device=device),
            target=torch.as_tensor(normalized[ix, C:C + K], device=device),
            static=torch.zeros(len(ix), 1, device=device))


def train_standard(model, data, C, K, *, epochs, lr):
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    history = []
    for epoch in range(epochs):
        model.train()
        total, outcome_total, aux_total, count = 0., 0., 0., 0
        for batch in make_batches(data, data['tr'], C, K, 'cpu'):
            optimizer.zero_grad(set_to_none=True)
            prediction = model(batch, K)
            outcome = (prediction - batch['target']).square().mean()
            aux = model.aux_loss(batch) if isinstance(model, RepairedCRNLite) else outcome.new_zeros(())
            loss = outcome + aux
            if not torch.isfinite(loss):
                raise ValueError('Nonfinite training loss')
            loss.backward()
            if any(p.grad is not None and not torch.isfinite(p.grad).all() for p in model.parameters()):
                raise ValueError('Nonfinite training gradient')
            nn.utils.clip_grad_norm_(model.parameters(), 1.)
            optimizer.step()
            n = len(batch['values'])
            total += float(loss.detach()) * n
            outcome_total += float(outcome.detach()) * n
            aux_total += float(aux.detach()) * n
            count += n
        history.append(dict(epoch=epoch, loss=total / count,
            factual_mse=outcome_total / count, auxiliary_mse_times_half=aux_total / count))
        if epoch % 5 == 0 or epoch == epochs - 1:
            print(json.dumps(history[-1]), flush=True)
    return history


@torch.no_grad()
def predict_alternatives(model, data, C, K):
    model.eval()
    predictions = []
    seconds = data['t_min'][C:C + K].astype(float) * 60
    active = torch.as_tensor(seconds >= data['switch_s'])
    for batch in make_batches(data, data['te'], C, K, 'cpu'):
        # No eventual factual assignment is available to inference.
        batch.pop('assigned_factual_dose')
        batch.pop('target')
        doses = []
        for dose in data['doses']:
            plan = torch.zeros(len(batch['values']), K, 1)
            plan[:, active, 0] = float(dose)
            batch['control_future'] = plan
            doses.append(model(batch, K).cpu().numpy() * data['std'] + data['mean'])
        predictions.append(np.stack(doses, axis=1))
    prediction = np.concatenate(predictions)
    return prediction, data['cf'][data['te'], :, C:C + K]


def _counts(correct, selected):
    n = int(selected.sum())
    return dict(accuracy=float(correct[selected].mean()) if n else None,
                n_correct=int(correct[selected].sum()), denominator=n)


def direction_accuracy(prediction, truth, *, supported=None, tolerances=EFFECT_TOLERANCES):
    """Adjacent-dose cells; report exact nonzero and zero effects separately.

    Call with scored, strictly post-switch times. Effect tolerance is applied to
    physical-unit adjacent-dose differences, identically to truth and prediction.
    """
    prediction, truth = np.asarray(prediction), np.asarray(truth)
    if prediction.shape != truth.shape or prediction.ndim != 4 or prediction.shape[-1] != 6:
        raise ValueError('Expected matching (patient,dose,time,6) arrays')
    if not np.isfinite(prediction).all() or not np.isfinite(truth).all():
        raise ValueError('Direction scores require finite inputs')
    tolerance = np.asarray(tolerances, dtype=float)
    if tolerance.shape != (6,) or not np.isfinite(tolerance).all() or np.any(tolerance < 0):
        raise ValueError('Require six finite nonnegative effect tolerances')
    predicted_delta = np.diff(prediction.astype(np.float64), axis=1)
    true_delta = np.diff(truth.astype(np.float64), axis=1)
    selected = np.ones(true_delta.shape, dtype=bool)
    if supported is not None:
        supported = np.asarray(supported, dtype=bool)
        if supported.shape != prediction.shape[:2]:
            raise ValueError('Support must have shape (patient,dose)')
        selected &= (supported[:, :-1] & supported[:, 1:])[..., None, None]
    exact = np.sign(predicted_delta) == np.sign(true_delta)
    nonzero = true_delta != 0
    true_class = np.where(np.abs(true_delta) <= tolerance, 0, np.sign(true_delta))
    predicted_class = np.where(np.abs(predicted_delta) <= tolerance, 0, np.sign(predicted_delta))
    tolerant = true_class == predicted_class
    result = dict(cell_definition='patient x adjacent dose pair x scored post-switch time x channel',
        n_total_cells=int(true_delta.size), n_selected_cells=int(selected.sum()),
        exact=dict(all=_counts(exact, selected),
                   post_effect=_counts(exact, selected & nonzero),
                   zero_effect=_counts(exact, selected & ~nonzero)),
        effect_tolerance=dict(all=_counts(tolerant, selected),
            post_effect=_counts(tolerant, selected & (true_class != 0)),
            zero_effect=_counts(tolerant, selected & (true_class == 0))),
        tolerances=dict(zip(generator.CHANNELS, tolerance.tolist())),
        tolerance_units=['mmHg', 'beats/min', 'L/min', 'mmHg', 'mL/min', 'mmol/L'],
        per_channel={})
    for i, channel in enumerate(generator.CHANNELS):
        scope = selected[..., i]
        result['per_channel'][channel] = dict(
            exact_post_effect=_counts(exact[..., i], scope & nonzero[..., i]),
            exact_zero_effect=_counts(exact[..., i], scope & ~nonzero[..., i]),
            tolerance_post_effect=_counts(tolerant[..., i], scope & (true_class[..., i] != 0)),
            tolerance_zero_effect=_counts(tolerant[..., i], scope & (true_class[..., i] == 0)))
    return result


def dataset(config, path=None):
    if path is None:
        key = hashlib.sha256(json.dumps(dict(config=config, hashes=generator.code_hashes()),
                                        sort_keys=True).encode()).hexdigest()[:20]
        path = ROOT / 'artifacts/datasets' / f'{key}.npz'
    path = generator.owned_path(path)
    if not path.exists():
        generator.make_dataset_grid(**config, out_path=path)
    manifest = generator.validate_manifest(path)
    metadata = manifest['metadata']
    for name, value in config.items():
        if metadata[name] != value:
            raise ValueError(f'Dataset setting mismatch for {name}')
    return path, metadata


def run_cell(*, output_dir, family='support_only', point=0, model='control_gru',
             seed=0, dataset_seed=0, n_patients=400, epochs=60, lamb=.5,
             confound=0., sigma=0., cf_protocol='onset_matched', threads=1,
             C=12, K=24, lr=.002, npz=None, smoke=False):
    started = time.perf_counter()
    out = generator.owned_path(output_dir)
    if out.exists():
        raise ValueError(f'Refusing existing run directory: {out}')
    if model not in MODELS or epochs < 1 or threads < 1 or not np.isfinite([lamb, lr]).all() or lamb < 0 or lr <= 0:
        raise ValueError('Invalid model or training settings')
    if smoke and (n_patients > 50 or epochs > 2):
        raise ValueError('E3 smoke is limited to <=50 patients and <=2 epochs')
    torch.set_num_threads(threads)
    torch.use_deterministic_algorithms(True)
    config = dict(family=family, point=point, confound=confound, sigma=sigma,
                  seed=dataset_seed, n_patients=n_patients, kappa=1., out_dt=300.,
                  C=C, K=K, cf_protocol=cf_protocol)
    path, metadata = dataset(config, npz)
    data = load_cvsim(path, C, seed)
    with np.load(path) as packed:
        data.update(assigned_dose=packed['factual_dose'].copy(), t_min=packed['t_min'].copy(),
                    switch_s=metadata['switch_s'])
        score_offsets = packed['score_indices'] - C
        history_checks = generator.verify_shared_history(packed)
        np.testing.assert_array_equal(packed['counterfactual_target'],
                                      packed['counterfactual'][:, :, packed['score_indices']])
        supported, support_info = support_for_patients(packed['severity'],
                                packed['factual_dose'], packed['cf_doses'], data['te'])
    target_stats = {split: generator.distribution(data['assigned_dose'][ix])
                   for split, ix in (('all', np.arange(n_patients)), ('train', data['tr']), ('test', data['te']))}
    if min(value['n_unique'] for value in target_stats.values()) < 2:
        raise ValueError('Assigned factual-dose balancing target is constant in a split')
    print('assigned_factual_dose ' + json.dumps(target_stats, allow_nan=False), flush=True)
    torch.manual_seed(seed)
    np.random.seed(seed)
    if model == 'crn_lite':
        instance = RepairedCRNLite(n_obs=6, d=96, lamb=lamb)
    elif model == 'crn_continuous':
        sys.path.insert(0, str(RELEASE_ROOT / 'baselines'))
        from crn_full_v2 import CRNFull, train_crn
        # Keep the two-stage architecture at lambda=0; never use CRN-lite compatibility.
        instance = CRNFull(lamb=lamb, legacy_zero=False)
    else:
        instance = build_model(model, seed=seed)
    data_seconds = time.perf_counter() - started
    training_start = time.perf_counter()
    if model == 'crn_continuous':
        history = train_crn(instance, data, C, K, epochs=epochs, lr=lr)
    else:
        history = train_standard(instance, data, C, K, epochs=epochs, lr=lr)
    training_seconds = time.perf_counter() - training_start
    full_prediction, full_truth = predict_alternatives(instance, data, C, K)
    if not np.isfinite(full_prediction).all() or any(not torch.isfinite(p).all() for p in instance.parameters()):
        raise ValueError('Nonfinite smoke/run output')
    prediction, truth = full_prediction[:, :, score_offsets], full_truth[:, :, score_offsets]
    rmse = {channel: float(np.sqrt(np.mean((prediction[..., i].astype(float) - truth[..., i]) ** 2)))
            for i, channel in enumerate(generator.CHANNELS)}
    metrics = dict(rmse_by_channel=rmse,
        direction_accuracy=direction_accuracy(prediction, truth),
        support_restricted_direction_accuracy=direction_accuracy(prediction, truth, supported=supported))
    out.mkdir(parents=True)
    checkpoint = out / 'model.pt'
    predictions = out / 'predictions.npz'
    torch.save(dict(model=model, state_dict=instance.state_dict(), lamb=lamb), checkpoint)
    np.savez_compressed(predictions, prediction=prediction, truth=truth,
        rollout_prediction=full_prediction, rollout_truth=full_truth,
        test_indices=data['te'], score_indices=np.array(metadata['score_indices']), doses=data['doses'])
    source_paths = [Path(__file__), generator.PROJECT / 'src/cvsim_counterfactual_runner.py',
                    generator.PROJECT / 'src/organ_graph_ssm_model.py',
                    ROOT.parent / 'BASE_SIM-sim-controls-build/sim_grid_runner.py']
    if model == 'crn_continuous':
        source_paths.append(ROOT.parent / 'historical_experiment/crn_full_v2.py')
    result = dict(schema_version=3, smoke=smoke,
        config=dict(config, model=model, seed=seed, dataset_seed=dataset_seed, epochs=epochs,
                    lamb=lamb, lr=lr, threads=threads, device='cpu'),
        n_params=sum(p.numel() for p in instance.parameters()), metrics=metrics,
        training_history=history, finite=True, history_checks=history_checks,
        balancing_target=dict(quantity='assigned eventual factual dose', distribution=target_stats,
                              used_as_input=False, auxiliary_multiplier=.5 if model == 'crn_lite' else None),
        support=support_info,
        dataset=dict(path=str(path), sha256=generator.sha256(path), metadata=metadata,
                     train_indices=data['tr'].tolist(), test_indices=data['te'].tolist()),
        normalization=dict(mean=data['mean'].tolist(), std=data['std'].tolist(),
                           scope='Factual training patients, all times; unchanged BASE_SIM loader'),
        code_sha256={str(p): generator.sha256(p) for p in source_paths},
        artifacts={str(p): generator.sha256(p) for p in (checkpoint, predictions)},
        timing=dict(data_seconds=data_seconds, training_seconds=training_seconds,
                    total_seconds=time.perf_counter() - started),
        notes=['All predictions use only factual context and the specified alternative plan.',
               'Full rollout includes the untreated prefix; scores use strictly post-switch samples.',
               'CRN-lite MSE balancing probes conditional mean assignment signal; it does not prove independence or identification.',
               'Continuous-dose CRN keeps historical_experiment adaptation, stage split, loss and dropout; lambda=0 retains the same full architecture.',
               'Physical-unit RMSE is reported; no new fixed-range NRMSE denominator is introduced.'])
    generator.write_json(out / 'run.json', result)
    print(json.dumps(dict(output_dir=str(out), finite=True, model=model,
                         post_effect=metrics['direction_accuracy']['exact']['post_effect']), allow_nan=False))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--family', choices=generator.FAMILIES, default='support_only')
    parser.add_argument('--point', type=int, default=0)
    parser.add_argument('--model', choices=MODELS, default='control_gru')
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--dataset_seed', type=int, default=0)
    parser.add_argument('--n_patients', type=int, default=400)
    parser.add_argument('--epochs', type=int, default=60)
    parser.add_argument('--lamb', type=float, default=.5)
    parser.add_argument('--confound', type=float, default=0.)
    parser.add_argument('--sigma', type=float, default=0.)
    parser.add_argument('--cf_protocol', choices=generator.PROTOCOLS, default='onset_matched')
    parser.add_argument('--threads', type=int, default=1)
    parser.add_argument('--C', type=int, default=12)
    parser.add_argument('--K', type=int, default=24)
    parser.add_argument('--lr', type=float, default=.002)
    parser.add_argument('--npz')
    parser.add_argument('--smoke', action='store_true')
    run_cell(**vars(parser.parse_args()))


if __name__ == '__main__':
    main()
