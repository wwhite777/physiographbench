"""Scientific acceptance tests: timing, policy isolation, labels and score counts."""
import json
from pathlib import Path
import shlex
import subprocess

import numpy as np
import pytest
import torch

import sim_policy_ext3 as e3
import sim_grid_runner3 as runner


@pytest.mark.parametrize('n', [50, 400])
@pytest.mark.parametrize('seed', [0, 1, 2, 3])
def test_policy_sweeps_hold_declared_quantities(n, seed):
    base, _, _ = e3.record_policy(family='legacy', n_patients=n, seed=seed)
    severity = base['severity']
    groups, _ = e3.severity_groups(severity)
    support, dependence = [], []
    for point in range(5):
        s, sp = e3.assign_policy(severity, family='support_only', point=point, seed=seed)
        d, dp = e3.assign_policy(severity, family='dependence_only', point=point, seed=seed)
        support.append((s, sp['statistics']))
        dependence.append((d, dp['statistics']))
        assert abs(sp['statistics']['spearman'] - .30) < .02
        assert abs(dp['statistics']['spearman'] - e3.DEPENDENCE_TARGETS[point]) < .02
        for g in range(3):
            # Exact finite-sample conditional distribution, stronger than a width check.
            np.testing.assert_array_equal(np.sort(d[groups == g]),
                                          np.sort(dependence[0][0][groups == g]))
            assert dp['statistics']['terciles'][g]['q05'] == pytest.approx(.025, abs=1e-6)
            assert dp['statistics']['terciles'][g]['q95'] == pytest.approx(.475, abs=1e-6)
            assert sp['statistics']['terciles'][g]['width_05_95'] == pytest.approx(
                .45 * e3.SUPPORT_WIDTHS[point], abs=1e-6)
    assert np.ptp([stats['pearson'] for _, stats in support]) < .02
    assert np.ptp([stats['spearman'] for _, stats in support]) < 1e-12
    assert all(dependence[i][1]['spearman'] < dependence[i + 1][1]['spearman'] for i in range(4))
    for doses, _ in support:
        np.testing.assert_array_equal(np.argsort(doses, kind='stable'),
                                      np.argsort(support[-1][0], kind='stable'))


def test_policy_changes_preserve_frozen_patient_draws():
    legacy, jobs0, _ = e3.record_policy(family='legacy', n_patients=12)
    changed, jobs1, _ = e3.record_policy(family='support_only', point=2, n_patients=12)
    np.testing.assert_array_equal(legacy['severity'], changed['severity'])
    for a, b in zip(jobs0, jobs1):
        assert a[0] == b[0]
        np.testing.assert_array_equal(a[1].sepsis_t, b[1].sepsis_t)
        np.testing.assert_array_equal(a[1].sepsis_v, b[1].sepsis_v)
        np.testing.assert_array_equal(a[2], b[2])
    assert not np.array_equal(legacy['factual_dose'], changed['factual_dose'])


@pytest.fixture(scope='module')
def onset_dataset():
    # The default 6-h horizon and true 4320-s onset are exercised, not shortened.
    return e3.make_dataset_grid(family='support_only', point=2, n_patients=12)


def test_onset_history_controls_and_scored_target(onset_dataset):
    data = onset_dataset
    checks = e3.verify_shared_history(data)
    assert checks['n_treated_alternative_samples_before_factual_onset'] == 0
    assert checks['first_scored_min'] == 75
    assert checks['n_scored_times'] == 21
    np.testing.assert_array_equal(data['score_indices'], np.arange(15, 36))
    np.testing.assert_array_equal(data['counterfactual_target'], data['counterfactual'][:, :, 15:36])
    assert np.isfinite(data['factual']).all() and np.isfinite(data['counterfactual']).all()


def test_schedule_boundary_at_exact_off_grid_onset():
    _, jobs, _ = e3.record_policy(family='legacy', n_patients=12)
    factual = jobs[0][1]
    for dose in [0., .05, .1, .2, .4]:
        alternative = e3.previous.shared_history_schedule(factual, dose, 4320.)
        for time in [0., 3600., 4200., np.nextafter(4320., -np.inf)]:
            assert alternative.vaso(time) == 0
        assert alternative.vaso(4320.) == dose
        assert alternative.vaso(21600.) == dose


def test_alternative_equal_to_factual_retains_entire_trajectory():
    # Integrate the existing scalar schedule and identical branch in batch at
    # the actual onset. This checks lane selection and RK4 boundary semantics.
    _, jobs, _ = e3.record_policy(family='legacy', n_patients=12)
    factual = jobs[0]
    dose = factual[1].vaso(4320.)
    alternative = (factual[0], e3.previous.shared_history_schedule(factual[1], dose, 4320.), *factual[2:])
    result = e3.previous._integrate_shared_jobs([factual, alternative], [factual[1]] * 2, 4320.)
    np.testing.assert_array_equal(result[0], result[1])
    ordinary = e3.previous.previous._integrate_jobs([factual])
    np.testing.assert_array_equal(result[:1], ordinary)


def test_temporal_extrapolation_is_separate():
    data = e3.make_dataset_grid(family='legacy', confound=0., sigma=0.,
                               n_patients=12, cf_protocol='temporal_extrapolation')
    metadata = json.loads(str(data['metadata_json']))
    assert metadata['switch_s'] == 3600.
    assert metadata['cf_protocol'] == 'temporal_extrapolation'
    checks = e3.verify_shared_history(data)
    assert checks['n_treated_alternative_samples_before_factual_onset'] > 0
    assert checks['first_scored_min'] == 65


def test_repaired_label_changes_aux_loss_and_reverses_only_encoder_gradient():
    torch.manual_seed(2)
    model = runner.RepairedCRNLite(n_obs=6, d=8, lamb=1.)
    # Give the head a known nonconstant response and measure its treatment signal.
    model._h = torch.randn(4, 8, requires_grad=True)
    batch = dict(values=torch.zeros(4, 12, 6), control_ctx=torch.zeros(4, 12, 1),
                 assigned_factual_dose=torch.tensor([[0.], [.1], [.3], [.5]]))
    loss = model.aux_loss(batch)
    loss.backward()
    reverse = model._h.grad.clone()
    head_reverse = [p.grad.clone() for p in model.treat_head.parameters()]
    model.zero_grad()
    model._h.grad = None
    model.lamb = -1.  # Test the GRL identity gradient for comparison only.
    ordinary = model.aux_loss(batch)
    ordinary.backward()
    torch.testing.assert_close(model._h.grad, -reverse)
    for a, b in zip(head_reverse, model.treat_head.parameters()):
        torch.testing.assert_close(a, b.grad)
    changed = dict(batch, assigned_factual_dose=torch.zeros(4, 1))
    assert not torch.isclose(loss, model.aux_loss(changed))
    model._h.grad = None
    model.lamb = 0.
    model.aux_loss(batch).backward()
    assert torch.count_nonzero(model._h.grad) == 0


def test_prediction_has_untreated_prefix_and_no_assigned_label():
    class PlanRecorder(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.plans = []

        def forward(self, batch, horizon):
            assert 'assigned_factual_dose' not in batch and 'target' not in batch
            self.plans.append(batch['control_future'].numpy().copy())
            return torch.zeros(len(batch['values']), horizon, 6)

    data = dict(obs=np.zeros((2, 73, 6), np.float32), vaso=np.zeros((2, 73, 1), np.float32),
        cf=np.zeros((2, 5, 73, 6), np.float32), doses=np.array([0., .05, .1, .2, .4]),
        mean=np.zeros(6, np.float32), std=np.ones(6, np.float32),
        assigned_dose=np.array([.1, .4], np.float32), te=np.arange(2),
        switch_s=4320., t_min=np.arange(73) * 5.)
    recorder = PlanRecorder()
    runner.predict_alternatives(recorder, data, 12, 24)
    for dose, plan in zip(data['doses'], recorder.plans):
        assert np.count_nonzero(plan[:, :3]) == 0
        np.testing.assert_array_equal(plan[:, 3:], np.full_like(plan[:, 3:], dose))


def test_score_zero_nonzero_tolerance_and_empty_support_denominators():
    truth = np.zeros((1, 3, 2, 6))
    truth[:, 1, 0] = 1.
    truth[:, 2, 0] = 1.  # pair 0 has effect; pair 1 is zero at t=0.
    truth[:, 1, 1] = .005
    truth[:, 2, 1] = .01  # 12 small nonzero cells at t=1.
    prediction = truth.copy()
    prediction[:, 1:, 1] *= -1
    metrics = runner.direction_accuracy(prediction, truth, tolerances=np.full(6, .01))
    assert metrics['n_total_cells'] == 24
    assert metrics['exact']['post_effect'] == dict(accuracy=6 / 18, n_correct=6, denominator=18)
    assert metrics['exact']['zero_effect'] == dict(accuracy=1., n_correct=6, denominator=6)
    assert metrics['effect_tolerance']['post_effect']['denominator'] == 6
    assert metrics['effect_tolerance']['zero_effect']['denominator'] == 18
    assert metrics['effect_tolerance']['all']['accuracy'] == 1.
    empty = runner.direction_accuracy(prediction, truth, supported=np.zeros((1, 3), bool))
    assert empty['n_selected_cells'] == 0
    assert empty['exact']['post_effect']['accuracy'] is None
    selected = runner.direction_accuracy(prediction, truth, supported=np.array([[1, 1, 0]], bool))
    assert selected['n_selected_cells'] == 12
    with pytest.raises(ValueError, match='finite'):
        runner.direction_accuracy(prediction * np.nan, truth)


@pytest.mark.parametrize('group,count', [('core', 184), ('lite-lambda', 120),
                                        ('temporal', 160), ('legacy', 384)])
def test_host_dry_run_groups(group, count):
    command = ['bash', str(e3.ROOT / 'run_host_e3.sh'), '--dry-run', '--group', group]
    before = set(e3.ROOT.rglob('run.json'))
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    lines = result.stdout.splitlines()
    assert len(lines) == count
    destinations = []
    for line in lines:
        args = shlex.split(line)
        destinations.append(args[args.index('--output-dir') + 1])
        if 'crn_continuous' in args:
            assert args[args.index('--family') + 1] == 'legacy'
            assert args[args.index('--confound') + 1] == '0'
            assert args[args.index('--sigma') + 1] == '0'
            assert args[args.index('--cf_protocol') + 1] == 'onset_matched'
    assert len(set(destinations)) == count
    assert set(e3.ROOT.rglob('run.json')) == before
    if group == 'core':
        assert sum('--model crn_continuous' in line for line in lines) == 24
        assert sum('--family support_only' in line for line in lines) == 80
        assert sum('--family dependence_only' in line for line in lines) == 80


def test_output_path_and_generation_validation():
    with pytest.raises(ValueError, match='inside'):
        e3.owned_path('/tmp/e3-output.npz')
    with pytest.raises(ValueError, match='Context'):
        e3.make_dataset_grid(n_patients=12, C=20)
    with pytest.raises(ValueError, match='No post'):
        e3.make_dataset_grid(n_patients=12, C=12, K=2)


def test_continuous_crn_lambda_zero_retains_full_architecture():
    import sys
    sys.path.insert(0, str(e3.RELEASE_ROOT / 'baselines'))
    from crn_full_v2 import CRNFull
    models = [CRNFull(lamb=lamb, legacy_zero=False) for lamb in (0., .25, 1.)]
    assert all(not model.is_legacy for model in models)
    assert len({sum(p.numel() for p in model.parameters()) for model in models}) == 1
    assert all(hasattr(model, 'encoder') and hasattr(model, 'decoder') for model in models)


def test_host_preflights_existing_destination_and_rejects_escaping_root():
    # Private scratch avoids touching any host-plan destination.
    scratch = runner.SCRATCH / 'preflight-test'
    occupied = scratch / 'main/support_only/point0/control_gru/seed0'
    occupied.mkdir(parents=True, exist_ok=True)
    script = str(e3.ROOT / 'run_host_e3.sh')
    result = subprocess.run(['bash', script, '--dry-run', '--output-root', str(scratch)],
                            capture_output=True, text=True)
    assert result.returncode == 2 and 'existing run' in result.stderr
    assert result.stdout == ''
    result = subprocess.run(['bash', script, '--dry-run', '--output-root', '/tmp/e3'],
                            capture_output=True, text=True)
    assert result.returncode == 2 and 'inside counterfactual experiment' in result.stderr
