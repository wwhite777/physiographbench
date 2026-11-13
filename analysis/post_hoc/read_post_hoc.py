"""Recompute post-hoc tables from distributed scalar records, without fitting."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import os
import sys

ROOT=Path(os.environ.get('PHYSIOGRAPH_ROOT',Path(__file__).absolute().parents[2]))
sys.path.insert(0,str(ROOT))
import numpy as np
from scipy.stats import t
from release_records import read

ORGANS=('cardiovascular','pulmonary','renal','metabolic')
MODES=('cap_matrix','equal_organ','clinical_2x2','input_access','treatment')

def load(location,root=ROOT):
    file=str(location).partition('#')[0]
    inventory=read('manifests/distribution.json',root)
    expected=inventory.get(file,{}).get('distributed_sha256')
    if expected is None:
        checksums={name.lstrip('*'):h for h,name in
                   (line.split(maxsplit=1) for line in (root/'SHA256SUMS').read_text().splitlines())}
        expected=checksums[file]
    if hashlib.sha256((root/file).read_bytes()).hexdigest()!=expected:
        raise ValueError(f'Changed distributed record: {file}')
    return read(location,root)

def stats(values):
    x=np.asarray(values,dtype=np.float64)
    if x.ndim!=1 or len(x)<2 or not np.isfinite(x).all():
        raise ValueError('Require finite paired observations')
    mean=float(x.mean());sd=float(x.std(ddof=1))
    half=float(t.ppf(.975,len(x)-1)*sd/math.sqrt(len(x)))
    return dict(n=len(x),mean=mean,sd=sd,ci95=[mean-half,mean+half],
                signs=dict(negative=int((x<0).sum()),zero=int((x==0).sum()),positive=int((x>0).sum())),values=x.tolist())

def metric(d,split,macro=False):
    return sum(d[split]['organs'][o]['RMSE'] for o in ORGANS)/4 if macro else d[split]['pooled_masked_RMSE']

def build(mode,root=ROOT):
    index=load('analysis/post_hoc/inputs.json',root)
    def group(name,n):
        locations=index[name]
        if len(locations)!=n or len(set(locations))!=n:
            raise ValueError(f'Incomplete or duplicate group: {name}')
        records=[load(loc,root) for loc in locations]
        for seed,record in enumerate(records):
            if record['seed']!=seed or record['status']!='complete':
                raise ValueError('Wrong clinical identity or completion')
        return records
    if mode=='cap_matrix':
        records={(arm,cap):group(f'cap/{arm}/{cap}',4) for arm in ('none','admissible','grud') for cap in (35,70,105)}
        means={a:{str(c):float(np.mean([d.get('A_validation',{}).get('pooled_masked_RMSE',d['validation_RMSE']) for d in records[a,c]])) for c in (35,70,105)} for a in ('none','admissible','grud')}
        selected={a:min((35,70,105),key=lambda c:(means[a][str(c)],c)) for a in means}
        rows=[]
        for ac in (35,70,105):
            for nc in (35,70,105):
                for split in ('A','B'):
                    rows.append(dict(admissible_cap=ac,none_cap=nc,split=split,same_cap=ac==nc,statistics=stats([metric(a,split)-metric(n,split) for a,n in zip(records['admissible',ac],records['none',nc])])))
        margins=[]
        for arm,chosen in selected.items():
            for other in (35,70,105):
                if chosen==other:continue
                val=lambda d:d.get('A_validation',{}).get('pooled_masked_RMSE',d['validation_RMSE'])
                margins.append(dict(family=arm,chosen_cap=chosen,other_cap=other,selection_margin_other_minus_chosen=means[arm][str(other)]-means[arm][str(chosen)],statistics=stats([val(a)-val(b) for a,b in zip(records[arm,chosen],records[arm,other])])))
        selected_records={a:group('selected/'+a,10) for a in ('none','admissible')}
        return dict(selected_caps=selected,validation_means=means,validation_selection=margins,cap_pairings=rows,
                    selected_ten_seed={s:stats([metric(a,s)-metric(n,s) for a,n in zip(selected_records['admissible'],selected_records['none'])]) for s in ('A','B')},
                    any_matched_cap_interval_favours_edges=any(r['statistics']['ci95'][1]<0 for r in rows if r['same_cap']),any_pairing_interval_favours_edges=any(r['statistics']['ci95'][1]<0 for r in rows))
    if mode=='equal_organ':
        records={a:group('selected/'+a,10) for a in ('none','admissible','grud')}
        return dict(definition='Equal mean of four per-organ RMSEs within seed, in A-training-SD units; then summarize seeds. Not simulator range-normalized NRMSE.',
                    arms={a:{s:stats([metric(d,s,True) for d in records[a]]) for s in ('A','B')} for a in records},
                    paired={s:stats([metric(a,s,True)-metric(n,s,True) for a,n in zip(records['admissible'],records['none'])]) for s in ('A','B')})
    if mode=='clinical_2x2':
        records={k:group('clinical/'+k,4) for k in ('partitioned_none','partitioned_admissible','shared_none','shared_admissible')}
        rows=[]
        for split in ('A','B'):
            for left,right in (('partitioned_admissible','partitioned_none'),('shared_admissible','shared_none'),('shared_none','partitioned_none'),('shared_admissible','partitioned_admissible')):
                rows.append(dict(split=split,label=left+' − '+right,statistics=stats([metric(a,split)-metric(b,split) for a,b in zip(records[left],records[right])])))
            values=[]
            for seed in range(4):
                v={k:metric(d[seed],split) for k,d in records.items()}
                values.append(v['shared_admissible']-v['shared_none']-v['partitioned_admissible']+v['partitioned_none'])
            rows.append(dict(split=split,label='(admissible − none)shared − (admissible − none)partitioned',statistics=stats(values)))
        return dict(cells={k:{s:stats([metric(d,s) for d in v]) for s in ('A','B')} for k,v in records.items()},contrasts=rows,
                    qualification='Common historical configuration selected on partitioned inputs, no retuning. Sharing adds 18,432 projection parameters; edges add 152,080. Information and capacity are not isolated.')
    if mode=='input_access':
        cells={}
        for arm in ('none','admissible','shared_none','shared_admissible','control_gru'):
            locations=index['simulator/'+arm]
            if len(locations)!=10 or len(set(locations))!=10: raise ValueError('Incomplete simulator seeds')
            cells[arm]=[]
            for seed,loc in enumerate(locations):
                d=load(loc,root);cfg=d['config']
                if (cfg['arm'],cfg['seed'],cfg['dataset_seed'],cfg['kappa'],d['smoke'])!=(arm,seed,0,1,False):
                    raise ValueError('Wrong simulator identity')
                cells[arm].append(d['metrics']['macro_nrmse_fixed'])
        interaction=[(cells['shared_admissible'][s]-cells['shared_none'][s])-(cells['admissible'][s]-cells['none'][s]) for s in range(10)]
        return dict(interaction_n10=stats(interaction),interaction_n4=stats(interaction[:4]),
                    shared_none_minus_admissible=stats([a-b for a,b in zip(cells['shared_none'],cells['shared_admissible'])]),
                    qualification='Paired split/initialization seeds on population 0; pointwise intervals, no equivalence or clinical inference.')
    if mode=='treatment':
        rows=[];values={}
        thresholds=dict(zip(('MAP','HR','CO','CVP','UO','Lac'),(.1,.1,.01,.05,.01,.01)))
        for model in ('control_gru','crn_lite','physiograph_gru','physiograph'):
            values[model]={}
            for point in (0,4):
                for seed,loc in enumerate(index[f'treatment/{model}/{point}']):
                    d=load(loc,root);cfg=d['config']
                    if (cfg['family'],cfg['point'],cfg['model'],cfg['seed'],d['finite'],d['smoke'])!=('dependence_only',point,model,seed,True,False):
                        raise ValueError('Wrong treatment endpoint')
                    direction=d['metrics']['direction_accuracy']
                    if direction['tolerances']!=thresholds:raise ValueError('Changed thresholds')
                    counts={}
                    for name in ('exact','effect_tolerance'):
                        c=direction[name]['post_effect'];n=c['denominator'];correct=c['n_correct']
                        if not 0<=correct<=n or n<=0 or abs(c['accuracy']-correct/n)>1e-14:raise ValueError('Invalid score counts')
                        counts[name]=dict(n_correct=correct,denominator=n,accuracy=correct/n)
                        values[model][point,seed,name]=correct/n
                    rows.append(dict(model=model,point=point,seed=seed,path=loc,counts=counts))
        differences={m:{score:stats([values[m][4,s,score]-values[m][0,s,score] for s in range(4)]) for score in ('exact','effect_tolerance')} for m in values}
        return dict(thresholds=thresholds,rows=rows,endpoint4_minus_endpoint0=differences,
                    definition='Adjacent-dose predicted and true signs; exact excludes zero true effects. Thresholded class is zero when abs(effect)<=threshold, separately for truth and prediction; only nonzero thresholded truth enters the denominator. Cutoffs are numerical sensitivity values, not clinical thresholds.',
                    scope='Means of four per-seed ratios, no pooling of cells as independent replicates. Effective rerun replaces CRN-lite endpoint4 seed3. Reads saved verified counts; does not replay unbundled trajectories.')
    raise ValueError('Unknown table')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('table',choices=MODES)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    try:
        result=build(args.table,args.root)
        text=json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n'
        if args.check:
            if text!=(args.root/f'analysis/post_hoc/{args.table}.json').read_text():raise ValueError('Published JSON differs')
            print('PASS:',args.table)
        else:print(text,end='')
    except (ValueError,KeyError,OSError,TypeError) as error:
        parser.exit(2,f'REFUSED: {error}\n')

if __name__=='__main__':main()
