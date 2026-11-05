"""CPU integration checks using synthetic inputs and workspace scratch only."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from release_paths import ROOT, SCRATCH
import json
import tempfile
import unittest
import numpy as np
import torch
from organ_graph_ssm_model import build_model
from clinical_timeseries_baselines import REGISTRY, build_baseline
from registry_tpatchgnn import build_adapter as tpatch
from registry_v3 import build_adapter as grafiti
from crn_full_v2 import CRNFull, grad_reverse
import sim_policy_ext as legacy
import sim_policy_ext2 as shared
from v4_protocol import make_data, train_run
from cinc2019_cohort_preprocessor import FEATURES, STATIC_COLS, parse_patient
from cinc2012_cohort_preprocessor import parse_patient as parse_2012


def batch():
    torch.manual_seed(7)
    present = (torch.rand(2, 12, 16) > .4).float()
    present[:, :, 7] = 0
    return dict(values=torch.randn(2, 12, 16), mask=present, static=torch.randn(2, 5))


def synthetic_cohort(path):
    rng = np.random.default_rng(9)
    payload = {}
    for cohort in 'AB':
        n = 8
        for key, a in dict(values=rng.normal(size=(n, 48, 16)).astype('f4'),
            mask=np.ones((n, 48, 16), 'f4'), static=np.zeros((n, 5), 'f4'),
            sepsis=np.zeros((n, 48), 'f4'), length=np.full(n, 48, 'i4')).items():
            payload[f'{cohort}_{key}'] = a
    payload.update(train_idx=np.arange(4), val_idx=np.arange(4, 6), test_idx=np.arange(6, 8),
        norm_mean=np.zeros(16, 'f4'), norm_std=np.ones(16, 'f4'), features=np.asarray(FEATURES),
        organ_slices=np.asarray([[0,4],[4,8],[8,11],[11,16]]),
        organ_names=np.asarray(['cardiovascular','pulmonary','renal','metabolic']))
    np.savez_compressed(path, **payload)


class Smoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def test_all_recurrent_baselines_have_finite_cpu_outputs(self):
        for name in REGISTRY:
            with self.subTest(model=name):
                model = build_baseline(name)
                out = model(batch(), horizon=6)
                self.assertEqual(tuple(out.shape), (2, 6, 16))
                self.assertTrue(torch.isfinite(out).all())

    def test_graph_ports_have_finite_gradients_and_expected_parameter_counts(self):
        for make, name, count in [(tpatch, 'tpatchgnn', 357682), (grafiti, 'grafiti', 43400)]:
            with self.subTest(model=name):
                model = make(name)
                self.assertEqual(sum(p.numel() for p in model.parameters()), count)
                out = model(batch(), horizon=6)
                self.assertEqual(tuple(out.shape), (2, 6, 16))
                self.assertTrue(torch.isfinite(out).all())
                out.square().mean().backward()
                grads = [p.grad for p in model.parameters() if p.grad is not None]
                self.assertTrue(grads and all(torch.isfinite(g).all() for g in grads))
                self.assertTrue(any(g.abs().sum() > 0 for g in grads))

    def test_crn_inference_does_not_read_future_outcomes(self):
        model = CRNFull(lamb=1, legacy_zero=False).eval()
        b = dict(values=torch.randn(2,12,6), mask=torch.ones(2,12,6), static=torch.randn(2,1),
                 control_ctx=torch.rand(2,12,1), control_future=torch.rand(2,6,1),
                 target=torch.randn(2,6,6))
        first = model(b,6)
        b['target'].fill_(999)
        second = model(b,6)
        torch.testing.assert_close(first,second)
        self.assertTrue(torch.isfinite(first).all())
        x=torch.ones(2,requires_grad=True)
        grad_reverse(x,.5).sum().backward()
        torch.testing.assert_close(x.grad,torch.full((2,),-.5))

    def test_shared_history_branch_and_legacy_factual_identity(self):
        settings=dict(kappa=.5,confound=.5,sigma=.15,seed=3,n_patients=4,
                      horizon_h=.05,out_dt=30.)
        previous=legacy.make_dataset_grid(**settings,out_path=None)
        new=shared.make_dataset_grid(**settings,out_path=None,C=2,K=3,cf_protocol='shared')
        np.testing.assert_array_equal(previous['factual'],new['factual'])
        for dose in range(len(new['cf_doses'])):
            np.testing.assert_array_equal(new['counterfactual'][:,dose,:2],new['factual'][:,:2,:6])
        np.testing.assert_array_equal(new['counterfactual_target'],new['counterfactual'][:,:,2:5])

    def test_cohort_2019_parser_and_mask(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as d:
            p=Path(d)/'synthetic.txt'
            columns=FEATURES+STATIC_COLS+['SepsisLabel']
            row=['80']*len(columns); row[0]='NaN'
            p.write_text('|'.join(columns)+'\n'+('|'.join(row)+'\n')*8)
            parsed=parse_patient(p)
            self.assertEqual(parsed['length'],8)
            self.assertEqual(parsed['mask'][0,0],0)
            self.assertEqual(parsed['values'][0,0],0)
            self.assertEqual(parsed['mask'][0,1],1)

    def test_cohort_2012_hourly_fallback_and_source_length(self):
        text = "Time,Parameter,Value\n00:00,RecordID,100001\n00:01,MAP,80\n00:40,MAP,100\n00:05,NIMAP,40\n01:00,NIMAP,70\n30:00,Unselected,1\n"
        parsed = parse_2012(text)
        self.assertEqual(parsed['values'][0,2],90)
        self.assertEqual(parsed['values'][1,2],70)
        self.assertEqual(parsed['length'],31)
        self.assertEqual(parsed['mapped_length'],2)

    def test_payload_verifier_accepts_good_and_rejects_corrupted_array(self):
        import hashlib
        from replay_simulators import verify
        a = np.arange(6, dtype=np.float32).reshape(2,3)
        expected = {'arrays':{'x':{'dtype':str(a.dtype), 'shape':list(a.shape),
                     'sha256':hashlib.sha256(a.tobytes()).hexdigest()}}}
        with tempfile.TemporaryDirectory(dir=SCRATCH) as d:
            path = Path(d)/'fixture.npz'
            np.savez_compressed(path,x=a)
            self.assertEqual(verify(path,expected),1)
            np.savez_compressed(path,x=a+1)
            with self.assertRaises(ValueError): verify(path,expected)

    def test_selected_training_checkpoint_and_statistics_on_synthetic_cohort(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as d:
            path=Path(d)/'cohort.npz';synthetic_cohort(path)
            out=Path(d)/'fit'
            result=train_run('gru',.001,'small',0,out,npz=path,epochs=1,batch=4,device='cpu')
            self.assertEqual(result['status'],'complete')
            self.assertEqual(result['A']['n_stays'],2)
            self.assertTrue((out/'checkpoint.pt').is_file())
            with np.load(out/'errors_A.npz') as e:
                self.assertTrue(np.isfinite(e['sse']).all())
            from host_driver_v2 import plan
            jobs=plan(ROOT/'runs/test_plan',device='cpu')
            self.assertEqual(jobs['counts']['total_fits'],310)
            self.assertEqual(len({j['id'] for j in jobs['jobs']}),len(jobs['jobs']))

if __name__ == '__main__':
    unittest.main()
