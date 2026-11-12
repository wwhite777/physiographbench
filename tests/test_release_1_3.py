"""Data-free coverage, fixed selection, paired arithmetic and defect controls."""
from pathlib import Path
import importlib.util
import json
import os
import statistics
import sys
import tempfile
import unittest

ROOT=Path(os.environ.get('PHYSIOGRAPH_ROOT',Path(__file__).absolute().parents[1]))
sys.path.insert(0,str(ROOT))
from release_paths import SCRATCH
from release_records import read
sys.path.insert(0,str(ROOT/'tools'))
from verify_release_1_3 import verify_records
sys.path.insert(0,str(ROOT/'analysis/cap_selection'))
import cap_reanalysis as caps

def load(name,relative):
    spec=importlib.util.spec_from_file_location(name,ROOT/relative)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

class Release13(unittest.TestCase):
    def test_all_100_records_and_group_counts(self):
        self.assertEqual(verify_records(ROOT),100)

    def test_cap_choice_ignores_test_scores_and_resolves_exact_ties(self):
        import copy
        data=read('analysis/cap_selection/cap_reanalysis.json')
        rows=copy.deepcopy(data['family_cap_summaries'])
        self.assertEqual(caps.select_caps(rows),{'none':105,'admissible':70,'grud':35})
        for i,row in enumerate(rows):
            row['metrics']['A']['mean']=(-1)**i*1e30
            row['metrics']['B']['mean']=(-1)**(i+1)*1e30
        self.assertEqual(caps.select_caps(rows),data['selected_caps'])
        for row in rows: row['metrics']['A_validation']['mean']=1.0
        self.assertEqual(caps.select_caps(rows),dict.fromkeys(caps.FAMILIES,35))

    def test_missing_record_from_each_group_and_changed_bytes_are_rejected(self):
        manifest=read('manifests/release_1_3_records.json')
        with tempfile.TemporaryDirectory(dir=SCRATCH,prefix='record-view-') as folder:
            root=Path(folder)
            for relative in ['manifests/distribution.json','manifests/release_1_3_records.json']+[e['path'] for e in manifest['records']]:
                target=root/relative;target.parent.mkdir(parents=True,exist_ok=True);target.symlink_to(ROOT/relative)
            self.assertEqual(verify_records(root),100)
            for group in manifest['counts']:
                relative=next(e['path'] for e in manifest['records'] if e['group']==group)
                target=root/relative;target.unlink()
                with self.subTest(group=group),self.assertRaises((OSError,ValueError)): verify_records(root)
                target.symlink_to(ROOT/relative)
            relative=manifest['records'][0]['path'];target=root/relative;target.unlink();target.write_text('{}')
            with self.assertRaises(ValueError): verify_records(root)

    def test_ten_seed_contrasts_recompute_from_all_ten_pairs(self):
        sys.path.insert(0,str(ROOT/'experiments/shared_input_primary'))
        import read_n2
        records,catalog=read_n2.collect_records()
        data=read_n2.analyze(records,catalog)
        from scipy import stats
        for row in data['contrasts']:
            differences=[r['difference'] for r in row['observations']]
            for count,key in [(4,'four_seed'),(10,'ten_seed')]:
                values=differences[:count]
                mean=statistics.mean(values);half=stats.t.ppf(.975,count-1)*statistics.stdev(values)/count**.5
                result=row[key]
                self.assertAlmostEqual(result['mean_difference'],mean,places=14)
                for a,b in zip(result['ci95_paired_t'],[mean-half,mean+half]): self.assertAlmostEqual(a,b,places=14)
                self.assertEqual(sum(result['sign_count'].values()),count)

    def test_regime_gate_boundaries_and_seed_coverage(self):
        sys.path.insert(0,str(ROOT/'experiments/positive_control'))
        import read_e1b
        self.assertFalse(read_e1b.gate_tests(.004,0)['shared_edge_mean_below_0_0040'])
        self.assertTrue(read_e1b.gate_tests(0,.004)['shared_none_within_0_0040_of_gru'])
        self.assertFalse(read_e1b.gate_tests(0,-.00400001)['shared_none_within_0_0040_of_gru'])
        records=read_e1b.load_records()
        self.assertEqual(len(records),162)
        result=read_e1b.summarize(records)
        self.assertTrue(all(result['tests'].values()))
        for arm in ('dense','misspecified-1','control_gru_matched'):
            self.assertEqual({s for k,a,s in records if k==1 and a==arm},set(range(4)))

    def test_cinc2012_intervals_and_pooled_denominators(self):
        sys.path.insert(0,str(ROOT/'tools/cinc2012/shared_input'))
        import read_n3
        data=read_n3.rebuild()
        self.assertEqual(len(data['contrasts']),12)
        self.assertAlmostEqual(data['contrasts']['within/testB/admissible-minus-none']['mean'],-.0309333787,places=8)
        for arm in ('none','admissible'):
            for seed in range(4):
                r=read(f'results/clinical_v4_v1/cinc2012/shared_input/transfer/{arm}/seed{seed}/run.json')['results']
                n=sum(r[s]['observed_entries'] for s in ('testA','testB'))
                self.assertEqual(r['pooled']['observed_entries'],n)
                mse=sum(r[s]['pooled_masked_RMSE']**2*r[s]['observed_entries'] for s in ('testA','testB'))/n
                self.assertAlmostEqual(r['pooled']['pooled_masked_RMSE'],mse**.5,places=12)

if __name__=='__main__': unittest.main()
