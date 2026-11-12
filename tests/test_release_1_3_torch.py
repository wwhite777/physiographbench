"""CPU model integration checks for hosts with the declared PyTorch environment.

These checks perform inference and invalid-argument checks, without fitting.
"""
from pathlib import Path
import importlib.util
import os
import sys
import unittest
ROOT=Path(os.environ.get('PHYSIOGRAPH_ROOT',Path(__file__).absolute().parents[1]))
sys.path.insert(0,str(ROOT))
from release_paths import SCRATCH
import torch

class Release13Models(unittest.TestCase):
    def test_ten_seed_shared_body_preserves_model_counts_and_input_access(self):
        sys.path.insert(0,str(ROOT/'experiments/shared_input_primary'))
        from n2_common import load_shared, chosen
        module=load_shared()
        torch.set_num_threads(1)
        batch=dict(values=torch.randn(2,12,16),mask=torch.ones(2,12,16),static=torch.zeros(2,5))
        for arm,count in [('none',778384),('admissible',930464)]:
            torch.manual_seed(4)
            net=module.build_arm(arm,chosen(arm)['sizes'])
            self.assertEqual(sum(p.numel() for p in net.parameters()),count)
            self.assertEqual(list(net.node_input_widths),[16]*4)
            self.assertEqual([p.in_features for p in net.in_proj],[37]*4)
            with torch.no_grad(): value=net(batch,horizon=2)
            self.assertEqual(tuple(value.shape),(2,2,16))
            self.assertTrue(torch.isfinite(value).all())

    def test_cinc2012_training_reuses_shared_factory_and_extended_cap_guard(self):
        sys.path.insert(0,str(ROOT/'tools/cinc2012/shared_input'))
        import n3_runtime
        choice=n3_runtime.selected_config()
        net=n3_runtime.training.build('physiograph_gru_shared',choice['sizes'],'none')
        self.assertEqual(sum(p.numel() for p in net.parameters()),778384)
        with self.assertRaisesRegex(ValueError,'105'):
            n3_runtime.training.train_run('physiograph_gru_shared',.001,'large',0,SCRATCH/'invalid-cap',epochs=106)

    def test_regime_shared_context_and_feedback_projection_widths(self):
        sys.path.insert(0,str(ROOT/'experiments/positive_control'))
        import shared_input_regime as regime
        for arm,count in [('shared_none',257158),('shared_admissible',274314)]:
            net=regime.build_model(arm,0)
            self.assertEqual(sum(p.numel() for p in net.parameters()),count)
            self.assertEqual([p.in_features for p in net.in_proj],[14]*3)
            self.assertEqual([p.in_features for p in net.step_proj],[14]*3)
            with torch.no_grad():
                value=net.rollout(torch.randn(2,12,6),torch.ones(2,12,6),torch.zeros(2,1),torch.zeros(2,12,1),torch.zeros(2,2,1),horizon=2)
            self.assertEqual(tuple(value.shape),(2,2,6))
            self.assertTrue(torch.isfinite(value).all())

if __name__=='__main__': unittest.main()
