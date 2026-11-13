"""Paired stay-cluster bootstrap of the twenty selected-cap fits, CPU only."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import sys
import numpy as np

ROOT=Path(os.environ.get('PHYSIOGRAPH_ROOT',Path(__file__).absolute().parents[2]))
sys.path.insert(0,str(ROOT))
from read_post_hoc import load

SEEDS={'A':20261112,'B':20261113}
RESAMPLES=2000

def build(root=ROOT):
    manifest=load('analysis/post_hoc/stay_manifest.json',root)
    result={}
    for row in manifest['files']:
        split=row['split'];path=root/row['path']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:raise ValueError('Changed stay statistics')
        with np.load(path,allow_pickle=False) as z:
            count=z['count'].astype(np.float64)
            sse={a:z[a+'_sse'].astype(np.float64) for a in ('none','admissible')}
        if count.ndim!=1 or not np.isfinite(count).all() or np.any(count<0):raise ValueError('Invalid counts')
        valid=count>0
        for v in sse.values():
            if v.shape!=(10,len(count)) or not np.isfinite(v).all() or np.any(v<0) or np.any(v[:,~valid]):raise ValueError('Invalid stay SSE')
        n=int(valid.sum());values={a:v[:,valid] for a,v in sse.items()};eligible=len(count);count=count[valid]
        rng=np.random.default_rng(SEEDS[split])
        draws=np.empty((RESAMPLES,10));pooled_draws=np.empty(RESAMPLES)
        for start in range(0,RESAMPLES,16):
            stop=min(start+16,RESAMPLES)
            index=rng.integers(0,n,size=(stop-start,n))
            denominator=count[index].sum(axis=1)
            roots={a:np.sqrt(v[:,index].sum(axis=2)/denominator[None,:]) for a,v in values.items()}
            draws[start:stop]=(roots['admissible']-roots['none']).T
            total={a:v[:,index].sum(axis=(0,2)) for a,v in values.items()}
            pooled_draws[start:stop]=np.sqrt(total['admissible']/(10*denominator))-np.sqrt(total['none']/(10*denominator))
        points=np.sqrt(values['admissible'].sum(axis=1)/count.sum())-np.sqrt(values['none'].sum(axis=1)/count.sum())
        mean_draws=draws.mean(axis=1)
        result[split]=dict(n_eligible_stays=eligible,n_evaluable_stays=n,n_zero_target_stays=eligible-n,n_observed_targets=int(count.sum()),seed=SEEDS[split],resamples=RESAMPLES,
                          point=float(points.mean()),ci95_percentile=np.quantile(mean_draws,[.025,.975]).tolist(),bootstrap_sd=float(mean_draws.std(ddof=1)),
                          per_seed=[dict(seed=s,point=float(points[s]),ci95_percentile=np.quantile(draws[:,s],[.025,.975]).tolist()) for s in range(10)],
                          bootstrap_mean_draws=mean_draws.tolist(),per_seed_draws_sha256=hashlib.sha256(draws.astype('<f8').tobytes()).hexdigest(),
                          root_after_pooling_all_seed_target_cells=dict(point=float(np.sqrt(values['admissible'].sum()/(10*count.sum()))-np.sqrt(values['none'].sum()/(10*count.sum()))),ci95_percentile=np.quantile(pooled_draws,[.025,.975]).tolist()))
    if set(result)!=set(SEEDS):raise ValueError('Require both clinical splits')
    return dict(bootstrap=result,method='Paired nonparametric stay-cluster bootstrap; NumPy PCG64, 2000 resamples, common stay sample across arms and all ten seeds, float64 summation, linear 2.5/97.5 percentiles.',estimand='Mean over ten seeds of the admissible-minus-none pooled RMSE difference; take each root before averaging seeds.',limitations='Conditional on fitted checkpoints and selected caps; no fitting or seed resampling. Stays are clusters, not identified persons. Repeated admissions and hospital sampling are outside this interval.')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    try:
        text=json.dumps(build(args.root),indent=2,ensure_ascii=False,allow_nan=False)+'\n'
        if args.check:
            if text!=(args.root/'analysis/post_hoc/stay_bootstrap.json').read_text():raise ValueError('Published bootstrap differs')
            print('PASS: stay-cluster bootstrap')
        else:print(text,end='')
    except (ValueError,KeyError,OSError,TypeError) as error:parser.exit(2,f'REFUSED: {error}\n')

if __name__=='__main__':main()
