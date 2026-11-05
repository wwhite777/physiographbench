"""One full-CRN policy cell, retaining simulator_grid/simulator_controls data and evaluation functions."""
from __future__ import annotations

# Resolve all public modules and scratch from the release root.
import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[1]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

from port_utils_v2 import PROJECT, ROOT, SCRATCH, owned_path, sha256, write_json

sys.dont_write_bytecode = True
os.environ['TMPDIR'] = str(SCRATCH)
sys.path.insert(0, str(PROJECT / 'src'))
sys.path.insert(0, str(RELEASE_ROOT / 'sim'))

import numpy as np
import torch

import sim_policy_ext2 as generator
from sim_grid_runner import direction_metrics, error_metrics, organ_ranges, predict
from sim_grid_runner2 import support_direction_metrics, support_for_patients
from cvsim_counterfactual_runner import load_cvsim
from crn_full_v2 import CRNFull, train_crn


def dataset(*, confound, sigma, n_patients, dataset_seed=0, cf_protocol='shared',
            C=12, K=24, horizon_h=6., out_dt=300.):
    config = dict(kappa=1., confound=float(confound), sigma=float(sigma),
                  seed=dataset_seed, n_patients=n_patients, cf_protocol=cf_protocol,
                  C=C, K=K, horizon_h=float(horizon_h), out_dt=float(out_dt))
    lineage = generator.code_hashes()
    key = hashlib.sha256(json.dumps(dict(config=config, lineage=lineage),
                                   sort_keys=True).encode()).hexdigest()[:20]
    path = ROOT / 'artifacts/datasets' / f'{key}.npz'
    manifest_path = path.with_suffix('.manifest.json')
    if path.exists():
        manifest = json.loads(manifest_path.read_text())
        if (manifest['config'] != config or manifest['lineage'] != lineage or
                manifest['sha256'] != sha256(path)):
            raise ValueError(f'Stale or mismatched generated dataset: {path}')
    else:
        # out_path=None exercises the already verified generator in memory. We
        # write its returned arrays ourselves; no other evidence root is written.
        packed = generator.make_dataset_grid(**config, out_path=None)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(path, **packed)
        write_json(manifest_path, dict(config=config, lineage=lineage,
                                       sha256=sha256(path)))
    return path


def run(out, *, confound=1., sigma=.15, seed=0, dataset_seed=0, n_patients=400,
        epochs=60, lr=.002, C=12, K=24, threads=1, smoke=False,
        cf_protocol='shared', lamb=1., legacy_zero=True):
    out = owned_path(out)
    if smoke and (n_patients > 24 or epochs > 4):
        raise ValueError('CRN smoke is limited to <=24 patients and <=4 total epochs')
    if n_patients < 4 or threads < 1 or epochs < (1 if lamb == 0 and legacy_zero else 2):
        raise ValueError('Invalid patient, epoch or thread count')
    start = time.perf_counter()
    torch.set_num_threads(threads)
    torch.use_deterministic_algorithms(True)
    path = dataset(confound=confound, sigma=sigma, n_patients=n_patients,
                   dataset_seed=dataset_seed, cf_protocol=cf_protocol, C=C, K=K)
    # Retain simulator_controls's explicitly frozen legacy c=1,sigma=.03 metric reference.
    reference_path = dataset(confound=1., sigma=.03, n_patients=n_patients,
                             dataset_seed=dataset_seed, cf_protocol='legacy', C=C, K=K)
    data = load_cvsim(path, C, seed)
    if C + K > data['T']:
        raise ValueError('Requested target exceeds the generated trajectory')
    with np.load(path) as packed:
        metadata = json.loads(str(packed['metadata_json']))
        support, support_info = support_for_patients(
            packed['severity'], packed['factual_dose'], packed['cf_doses'], data['te'])
        np.testing.assert_array_equal(packed['counterfactual_target'],
                                      packed['counterfactual'][:, :, C:C + K])
    with np.load(reference_path) as packed:
        fixed_ranges = organ_ranges(packed['counterfactual'])
    np.random.seed(seed)
    torch.manual_seed(seed)
    model = CRNFull(lamb=lamb, legacy_zero=legacy_zero)
    data_seconds = time.perf_counter() - start
    train_start = time.perf_counter()
    history = train_crn(model, data, C, K, epochs=epochs, lr=lr)
    train_seconds = time.perf_counter() - train_start
    prediction, truth = predict(model, data, C, K, torch.device('cpu'), counterfactual=True)
    if not np.isfinite(prediction).all():
        raise ValueError('Nonfinite counterfactual predictions')
    metrics = error_metrics(prediction, truth, fixed_ranges, organ_ranges(data['cf'][data['te']]))
    metrics['direction_accuracy'] = direction_metrics(prediction, truth)
    metrics['support_restricted_direction_accuracy'] = support_direction_metrics(prediction, truth, support)
    metrics['support_restricted_direction_accuracy']['support'] = support_info
    checkpoint = out.with_suffix('.pt')
    predictions_path = out.with_suffix('.predictions.npz')
    out.parent.mkdir(parents=True, exist_ok=True)
    torch.save(dict(state_dict=model.state_dict(), config=model.config), checkpoint)
    np.savez_compressed(predictions_path, prediction=prediction, truth=truth,
                        test_indices=data['te'], doses=data['doses'])
    result = dict(schema_version=1, smoke=smoke,
                  model='crn_lite_lambda0_compatibility' if model.is_legacy else 'crn_full_continuous_dose_adaptation',
                  cf_protocol=cf_protocol,
                  config=dict(confound=confound, sigma=sigma, seed=seed, dataset_seed=dataset_seed,
                              n_patients=n_patients, epochs=epochs, lr=lr, C=C, K=K,
                              threads=threads, device='cpu', lamb=lamb, legacy_zero=legacy_zero),
                  architecture=model.config, n_params=sum(p.numel() for p in model.parameters()),
                  metrics=metrics, training_history=history,
                  overlap=generator.overlap_diagnostics(path),
                  dataset=dict(path=str(path), sha256=sha256(path), metadata=metadata,
                               train_indices=data['tr'].tolist(), test_indices=data['te'].tolist()),
                  normalization=dict(mean=data['mean'].tolist(), std=data['std'].tolist(),
                                     reference_path=str(reference_path), reference_sha256=sha256(reference_path),
                                     fixed_ranges=fixed_ranges,
                                     fixed_scope='Legacy c=1,sigma=.03, all patients/doses/times; simulator_controls denominator',
                                     training_scope='Factual training-patient observations, all times; frozen simulator_grid'),
                  checkpoint=dict(path=str(checkpoint), sha256=sha256(checkpoint)),
                  predictions=dict(path=str(predictions_path), sha256=sha256(predictions_path)),
                  timing=dict(data_seconds=data_seconds, train_seconds=train_seconds,
                              elapsed_seconds=time.perf_counter() - start),
                  protocol_notes=[
                      'Two stages divide the total epoch budget equally, with the extra epoch in decoder fitting.',
                      'Adam lr=.002, batch=128, clip norm=1; no validation selection, matching the simulator_grid training protocol.',
                      'Appendix E logistic schedule uses literal 1-based epoch p, restarted per stage; lambda max is recorded.',
                      'Encoder sees all factual one-step transitions; decoder sees every eligible factual split.',
                      'Decoder fitting uses observed outcome feedback; evaluation uses predicted outcome feedback.',
                      'Both losses sum time; outcome loss also sums coordinates; lambda max=1 uses this scale.',
                      'Endpoint-indexed simulator dose[j+1] is paper A_j for outcome Y_{j+1}; no data shift.',
                      'Decoder hidden state is the encoder balanced representation directly; cell memory starts at zero.',
                      'Ordinary representation dropout is a declared deviation; no uncertainty claim.',
                      'Categorical balancing uses 10 fixed equal-width dose bins; outcome heads receive continuous dose.',
                      'Current planned treatment is excluded from its balanced representation.',
                      'Hidden severity/sepsis are never model inputs; overlap alone does not prove sequential exchangeability.',
                      'Shared-history context doses are zero; fitting on the full factual trajectory includes later nonzero doses.',
                      'The lambda=0 compatibility model is CRN-lite, not the full-CRN no-balancing ablation.'])
    write_json(out, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    parser.add_argument('--confound', type=float, default=1.)
    parser.add_argument('--sigma', type=float, default=.15)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--dataset_seed', type=int, default=0)
    parser.add_argument('--n_patients', type=int, default=400)
    parser.add_argument('--epochs', type=int, default=60)
    parser.add_argument('--lr', type=float, default=.002)
    parser.add_argument('--C', type=int, default=12)
    parser.add_argument('--K', type=int, default=24)
    parser.add_argument('--threads', type=int, default=1)
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--cf_protocol', choices=('shared', 'legacy'), default='shared')
    parser.add_argument('--lamb', type=float, default=1.)
    parser.add_argument('--full_zero', dest='legacy_zero', action='store_false',
                        help='Keep the full architecture at lambda=0; not the CRN-lite regression contract')
    run(**vars(parser.parse_args()))


if __name__ == '__main__':
    main()
