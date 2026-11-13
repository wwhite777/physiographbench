"""Device-matched adjacency reader; no fitting or model imports."""
from pathlib import Path
import os
import sys
sys.path.insert(0,os.environ.get('PHYSIOGRAPH_ROOT',str(Path(__file__).absolute().parents[2])))
import argparse
import json
import math
import statistics
from release_1_3_1 import ROOT, records as verified_records
SEEDS=(0,1,2,3)

T_CRITICAL = 3.1824463052837064


def paired(left, right):
    if len(left) != 4 or len(right) != 4:
        raise ValueError('Exactly four seed pairs are required')
    differences = [a - b for a, b in zip(left, right)]
    if not all(math.isfinite(x) for x in differences):
        raise ValueError('Nonfinite paired difference')
    mean, sd = statistics.mean(differences), statistics.stdev(differences)
    se = sd / math.sqrt(4)
    return dict(seed_order=list(SEEDS), n_pairs=4, df=3,
                left_values=left, right_values=right, paired_differences=differences,
                mean_difference=mean, sample_sd_difference=sd, standard_error=se,
                confidence_level=.95, t_critical=T_CRITICAL,
                ci95=[mean - T_CRITICAL * se, mean + T_CRITICAL * se],
                signs=['-' if x < 0 else '+' if x > 0 else '0' for x in differences],
                sign_count=dict(negative=sum(x < 0 for x in differences),
                                zero=sum(x == 0 for x in differences),
                                positive=sum(x > 0 for x in differences)))


def build_reading(root=ROOT):
    records=verified_records('s3',root)
    def values(role,model,graph,split):
        field='RMSE@12' if role=='cpu' else 'RMSE'
        return [records[role,model,graph,seed][0][split][field] for seed in SEEDS]
    arms,contrasts,effects=[],[],[]
    for model in ('grafiti','tpatchgnn'):
        for split in ('A_test','B_external'):
            cuda=values('cuda',model,'learned',split)
            cpu=values('cpu',model,'learned',split)
            effects.append(dict(model=model,split=split,**paired(cuda,cpu)))
            for arm,data in [('learned_CPU_original',cpu),('learned_CUDA',cuda)]+[(g,values('fixed',model,g,split)) for g in ('physiological','random','complete')]:
                arms.append(dict(model=model,split=split,arm=arm,seed_order=list(SEEDS),values=data,mean=statistics.mean(data),sample_sd=statistics.stdev(data)))
            for graph in ('physiological','random','complete'):
                fixed=values('fixed',model,graph,split)
                contrasts.append(dict(model=model,graph=graph,split=split,original=paired(fixed,cpu),device_matched=paired(fixed,cuda)))
    return dict(metric='Pooled observed-target RMSE at 12 hours',
                qualification='Pointwise seed-paired t intervals, not equivalence tests. The operational CUDA refit also changes metric reduction from float32 to float64 and t-PatchGNN threads from six to four. Fixed GraFITi changes the receiving-variable time-state representation.',
                arms=arms,fixed_minus_learned=contrasts,device_effect=effects,
                sources=[row for record,row in records.values()])

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    try:
        result=build_reading(args.root)
        text=json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n'
        if args.check:
            expected=args.root/'experiments/learned_graph_validation/artifacts/learned_cuda_summary.json'
            if text != expected.read_text(): raise ValueError('Adjacency summary differs')
            print('PASS: 40 adjacency records and published summary')
        else: print(text,end='')
    except (ValueError,KeyError,OSError,TypeError) as error:
        parser.exit(2,f'REFUSED: {error}\n')

if __name__=='__main__': main()
