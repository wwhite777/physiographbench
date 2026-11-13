"""No-model reproduction and fail-closed controls for release 1.3.1."""
from pathlib import Path
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(os.environ.get('PHYSIOGRAPH_ROOT',Path(__file__).absolute().parents[1]))
sys.path.insert(0,str(ROOT))
from release_paths import SCRATCH
from release_1_3_1 import records

def module(name,relative):
    spec=importlib.util.spec_from_file_location(name,ROOT/relative)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

class Release131(unittest.TestCase):
    def test_population_summary_and_frozen_rule(self):
        reader=module('population_reader','experiments/positive_control/read_s1.py')
        result=reader.summarize(reader.load_records(ROOT))
        target=json.loads((ROOT/'experiments/positive_control/artifacts/population_replication/summary.json').read_text())
        self.assertEqual(result,target)
        self.assertEqual(result['replicating_new_populations'],[1,2,3,4])
        a,b,c,d=reader.CONTRASTS
        boundary={a:dict(mean=-1,ci95=[-2,-.1]),b:dict(mean=.004),c:dict(mean=.004),d:{}}
        self.assertFalse(reader.replication_rule(boundary)['replicates'])
        boundary[b]['mean']=.003999
        self.assertTrue(reader.replication_rule(boundary)['replicates'])
        boundary[c]['mean']=.00400001
        self.assertFalse(reader.replication_rule(boundary)['replicates'])

    def test_device_matched_summary(self):
        reader=module('adjacency_reader','experiments/learned_graph_validation/read_s3.py')
        result=reader.build_reading(ROOT)
        self.assertEqual(result,json.loads((ROOT/'experiments/learned_graph_validation/artifacts/learned_cuda_summary.json').read_text()))
        self.assertEqual(len(result['sources']),40)
        self.assertEqual(len(result['fixed_minus_learned']),12)

    def test_every_post_hoc_json(self):
        sys.path.insert(0,str(ROOT/'analysis/post_hoc'))
        reader=module('post_hoc_reader','analysis/post_hoc/read_post_hoc.py')
        for mode in reader.MODES:
            with self.subTest(table=mode):
                self.assertEqual(reader.build(mode,ROOT),json.loads((ROOT/f'analysis/post_hoc/{mode}.json').read_text()))

    def test_bootstrap_reproduces_all_draws_and_estimands(self):
        sys.path.insert(0,str(ROOT/'analysis/post_hoc'))
        reader=module('cluster_reader','analysis/post_hoc/stay_bootstrap.py')
        actual=reader.build(ROOT)
        self.assertEqual(actual,json.loads((ROOT/'analysis/post_hoc/stay_bootstrap.json').read_text()))
        self.assertEqual(actual['bootstrap']['A']['seed'],20261112)
        self.assertEqual(actual['bootstrap']['B']['seed'],20261113)

    def record_view(self,root,group):
        manifest=json.loads((ROOT/'manifests/release_1_3_1_inputs.json').read_text())
        paths=['manifests/release_1_3_1_inputs.json']+[r['path'] for r in manifest['records'] if r['group']==group]
        if group=='s1':paths += [r['path'] for r in manifest['populations']]
        for name in paths:
            target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.symlink_to(ROOT/name)
        return next(r['path'] for r in manifest['records'] if r['group']==group and (r.get('population',0)>0 if group=='s1' else r['role']=='cuda'))

    def test_missing_record_prevents_result_from_both_readers(self):
        for group,relative in [('s1','experiments/positive_control/read_s1.py'),('s3','experiments/learned_graph_validation/read_s3.py')]:
            with self.subTest(group=group),tempfile.TemporaryDirectory(dir=SCRATCH,prefix='missing-') as folder:
                root=Path(folder);name=self.record_view(root,group)
                self.assertTrue(records(group,root))
                (root/name).unlink()
                result=subprocess.run([sys.executable,'-B',str(ROOT/relative),'--root',str(root)],capture_output=True,text=True)
                self.assertEqual(result.returncode,2,result.stderr)
                self.assertEqual(result.stdout,'')

    def test_changed_record_and_unlisted_duplicate_are_rejected(self):
        for group in ('s1','s3'):
            with self.subTest(group=group),tempfile.TemporaryDirectory(dir=SCRATCH,prefix='changed-') as folder:
                root=Path(folder);name=self.record_view(root,group);path=root/name
                original=path.readlink();path.unlink();path.write_text('{}\n')
                with self.assertRaises(ValueError):records(group,root)
                path.unlink();path.symlink_to(original)
                duplicate=path.parent/'duplicate.json';duplicate.symlink_to(original)
                with self.assertRaises(ValueError):records(group,root)

    def test_post_hoc_missing_source_is_rejected(self):
        reader=module('post_hoc_control','analysis/post_hoc/read_post_hoc.py')
        index=json.loads((ROOT/'analysis/post_hoc/inputs.json').read_text())
        for mode,key in [('cap_matrix','cap/none/35'),('equal_organ','selected/none'),('clinical_2x2','clinical/partitioned_none'),('input_access','simulator/none'),('treatment','treatment/control_gru/0')]:
            with self.subTest(mode=mode),tempfile.TemporaryDirectory(dir=SCRATCH,prefix='post-missing-') as folder:
                root=Path(folder)
                required={'manifests/distribution.json','SHA256SUMS','analysis/post_hoc/inputs.json'}
                required.update(loc.partition('#')[0] for paths in index.values() for loc in paths)
                for name in required:
                    target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.symlink_to(ROOT/name)
                (root/index[key][0].partition('#')[0]).unlink()
                with self.assertRaises(OSError):reader.build(mode,root)

    def test_official_attempt_remains_a_failure_record(self):
        folder=ROOT/'experiments/learned_graph_validation/official_code'
        record=json.loads((folder/'grafiti_fold0.json').read_text())
        self.assertEqual(record['status'],'TRAINING_FAILED')
        self.assertEqual(record['exit_code'],1)
        self.assertIn("KeyError: 'Time'",(folder/'grafiti_fold0.log').read_text())
        import hashlib
        self.assertEqual(hashlib.sha256((folder/'grafiti_fold0.log').read_bytes()).hexdigest(),record['_distribution']['distributed_log_sha256'])

if __name__=='__main__':unittest.main()
