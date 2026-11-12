#!/usr/bin/env python3
"""Reconstruct seed summaries and contrasts from all 16 shared-input records.

This checks saved scalar records, not omitted residual arrays or weights.
Intervals describe training-seed variation conditional on fixed cohorts.
"""
import argparse
import json
import math
from pathlib import Path
from n3_common import *
from release_records import read, verify, clinical
import numpy as np
def paired_interval(first, second):
    from scipy.stats import t
    import numpy as np
    if set(first) != {str(s) for s in range(4)} or set(second) != set(first):
        raise ValueError("A paired interval requires exactly seeds 0..3 in each arm")
    differences = np.array([first[str(s)] - second[str(s)] for s in range(4)], dtype=np.float64)
    if not np.isfinite(differences).all():
        raise ValueError("Nonfinite paired difference")
    mean, sd = float(differences.mean()), float(differences.std(ddof=1))
    half = float(t.ppf(.975, 3)) * sd / math.sqrt(4)
    return dict(n=4, df=3, mean=mean, paired_sd=sd, confidence=.95,
        lower=mean-half, upper=mean+half, method="paired Student t", ddof=1,
        per_seed={str(s): float(differences[s]) for s in range(4)},
        signs=dict(negative=int((differences < 0).sum()), zero=int((differences == 0).sum()),
                   positive=int((differences > 0).sum())))


def rebuild(root=RECORD_ROOT):
    base=read('results/clinical_v4_v1/cinc2012/cinc2012_results.json')
    records={}
    for protocol,arm,seed in identities():
        path=run_dir(root,protocol,arm,seed)/'run.json'
        verify(path)
        r=clinical(json.loads(path.read_text()),seed,CAPS[arm])
        if (r['protocol'],r['arm'],r['model'],r['input_mode'])!=(protocol,arm,MODEL,'shared'):
            raise ValueError('Incorrect shared CinC-2012 identity')
        splits={'testB'} if protocol=='within' else {'testA','testB','pooled'}
        if set(r['results'])!=splits: raise ValueError('Incomplete evaluation splits')
        for m in r['results'].values():
            if m['pooled_masked_RMSE']<0 or m['nonfinite_predictions']!=0 or m['observed_entries']<=0:
                raise ValueError('Invalid saved metric')
        records[protocol,arm,seed]=r
    result={'status':'complete','scope':'saved scalar reconstruction; no residual replay','contrasts':{},'families':{}}
    for protocol in ('within','transfer'):
        splits=('testB',) if protocol=='within' else ('testA','testB','pooled')
        for split in splits:
            metrics={arm:{str(s):records[protocol,arm,s]['results'][split]['pooled_masked_RMSE'] for s in range(4)} for arm in CAPS}
            metrics['grud']={s:m['pooled_masked_RMSE'] for s,m in base['protocols'][protocol]['models']['grud']['splits'][split]['per_seed'].items()}
            for arm,values in metrics.items():
                v=list(values.values());result['families'][f'{protocol}/{split}/{arm}']={'mean':float(np.mean(v)),'sample_sd':float(np.std(v,ddof=1)),'per_seed':values}
            for lhs,rhs in (('admissible','none'),('none','grud'),('admissible','grud')):
                result['contrasts'][f'{protocol}/{split}/{lhs}-minus-{rhs}']=paired_interval(metrics[lhs],metrics[rhs])
    # Rebuild the complete historical table and append the new shared-input
    # rows. All summaries average per-seed metrics with sample SD (ddof=1).
    from copy import deepcopy
    protocols=deepcopy(base['protocols'])
    def summary(values):
        values=list(values)
        return dict(n=len(values),mean=float(np.mean(values)),sd=float(np.std(values,ddof=1)))
    for protocol,section in protocols.items():
        for model,model_record in section['models'].items():
            for split,cell in model_record['splits'].items():
                values=cell['per_seed']
                if set(values)!={str(s) for s in range(4)}: raise ValueError('Incomplete legacy seeds')
                rebuilt=summary(m['pooled_masked_RMSE'] for m in values.values())
                if not math.isclose(rebuilt['mean'],cell['RMSE']['mean'],abs_tol=1e-12): raise ValueError('Legacy mean differs from seeds')
                if not math.isclose(rebuilt['sd'],cell['RMSE']['sd'],abs_tol=1e-12): raise ValueError('Legacy SD differs from seeds')
        for arm in CAPS:
            row={'seeds_present':list(range(4)),'splits':{}}
            for split in records[protocol,arm,0]['results']:
                values={str(s):records[protocol,arm,s]['results'][split] for s in range(4)}
                organs=next(iter(values.values()))['organs']
                row['splits'][split]=dict(per_seed=values,RMSE=summary(m['pooled_masked_RMSE'] for m in values.values()),
                    organs={o:summary(m['organs'][o]['RMSE'] for m in values.values()) for o in organs})
            section['models'][f'physiograph_gru_shared_{arm}_cap{CAPS[arm]}']=row
    result['protocols']=protocols
    return result

def render_table(result):
    lines=['| Protocol | Model | Split | Target | Mean RMSE | Sample SD | Seeds |',
           '|---|---|---|---|---:|---:|---:|']
    for protocol,section in sorted(result['protocols'].items()):
        for model,row in sorted(section['models'].items()):
            for split,cell in sorted(row['splits'].items()):
                targets={'pooled':cell['RMSE'],**cell['organs']}
                for target,metric in targets.items():
                    lines.append(f"| {protocol} | {model} | {split} | {target} | {metric['mean']:.6f} | {metric['sd']:.6f} | 4 |")
    return '\n'.join(lines)+'\n'

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,default=RECORD_ROOT)
    ap.add_argument('--table',action='store_true',help='print all historical and shared-input table rows')
    args=ap.parse_args()
    try: result=rebuild(args.root)
    except (ValueError,OSError,KeyError) as error: ap.exit(2,f'REFUSED: {error}\n')
    print(render_table(result) if args.table else json.dumps(result,indent=2,allow_nan=False))
if __name__=='__main__': main()
