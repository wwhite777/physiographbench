"""Save a labelled temporal set and compare it with the onset-matched diagnostic."""

import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[2]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH
import json

import numpy as np

import sim_policy_ext3 as e3
from sim_grid_runner3 import dataset


if __name__ == '__main__':
    config = dict(family='legacy', point=0, confound=0., sigma=0., seed=0,
                  n_patients=12, kappa=1., out_dt=300., C=12, K=24,
                  cf_protocol='onset_matched')
    onset_path, _ = dataset(config)
    temporal_path = e3.ROOT / 'artifacts/protocol_checks/temporal_extrapolation_c0_sigma0.npz'
    if not temporal_path.exists():
        e3.make_dataset_grid(**dict(config, cf_protocol='temporal_extrapolation'), out_path=temporal_path)
    e3.validate_manifest(temporal_path)
    with np.load(onset_path) as onset, np.load(temporal_path) as temporal:
        onset_checks = e3.verify_shared_history(onset)
        temporal_checks = e3.verify_shared_history(temporal)
        np.testing.assert_array_equal(onset['factual'], temporal['factual'])
        np.testing.assert_array_equal(onset['severity'], temporal['severity'])
        np.testing.assert_array_equal(onset['factual_dose'], temporal['factual_dose'])
        assert onset_checks['n_treated_alternative_samples_before_factual_onset'] == 0
        assert temporal_checks['n_treated_alternative_samples_before_factual_onset'] == 144
        assert json.loads(str(temporal['metadata_json']))['cf_protocol'] == 'temporal_extrapolation'
    report = dict(factual_identical_across_protocols=True,
                  onset=dict(path=str(onset_path), sha256=e3.sha256(onset_path), checks=onset_checks),
                  temporal=dict(path=str(temporal_path), sha256=e3.sha256(temporal_path), checks=temporal_checks))
    e3.write_json(e3.ROOT / 'PROTOCOL_CHECKS.json', report)
    print(json.dumps(report))
