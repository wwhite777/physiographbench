#!/usr/bin/env python3
"""Rebuild readable tables and the README's numerical findings from frozen JSON."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from release_paths import ROOT
import argparse
import csv
import json
import os
import statistics


def load(relative):
    return json.loads((ROOT/'results'/relative).read_text())


def summary(values):
    values=list(values)
    return dict(n=len(values),mean=statistics.mean(values),sd_sample=statistics.stdev(values) if len(values)>1 else 0.)


def flatten(value,prefix=''):
    out={}
    for key,v in value.items():
        key=f'{prefix}.{key}' if prefix else key
        if isinstance(v,dict):out.update(flatten(v,key))
        elif isinstance(v,(int,float,bool)) or v is None:out[key]=v
    return out


def calculate():
    tuning=load('v4/tuning_grid.json')
    clinical={}
    for model,runs in tuning['selected_runs'].items():
        clinical[model]={}
        for split in 'AB':
            values=[r[split]['pooled_masked_RMSE'] for r in runs.values() if r['status']=='complete']
            clinical[model][split]=dict(status='diverged',value=None) if model=='ncde' and split=='B' else summary(values)
    for folder,model in [('tpatchgnn','t-PatchGNN'),('grafiti_v3','GraFITi')]:
        runs=[json.loads(p.read_text()) for p in sorted((ROOT/'results/learned_graph_baselines_v1'/folder).glob('cinc*.json'))]
        assert len(runs)==4,(folder,len(runs))
        clinical[model]={split:summary(r[label]['RMSE@12'] for r in runs) for split,label in [('A','A_test'),('B','B_external')]}
    stats=load('v4/stats_v4.json')
    paired={split:{k:stats['selected_seed_uncertainty'][split]['grud'][k] for k in ['mean_gap','sd_sample']} for split in 'AB'}
    h3=load('sim_grids_v1/h3_grid_with_controls.json')['cells']
    h5=load('sim_grids_v1/h5_grid.json')['cells']
    horizon=load('v4/horizon_table_v4.json')['table']
    gaps={}
    for design,models in horizon.items():
        vals={m:summary(r['B']['pooled_masked_RMSE'] for r in models[m]['runs'] if r['status']=='complete') for m in ['grud','physiograph_gru']}
        gaps[design]=dict(gap=vals['physiograph_gru']['mean']-vals['grud']['mean'],**vals)
    ci=load('coupling_index_v1/coupling_index.json')['datasets']['cinc2019']['probes']['ridge']['splits']['A_val']['mean_off_diagonal']
    decomposition={c['variant']:c['metrics']['macro_nrmse_fixed']['mean'] for c in h3 if c['kappa']==1. and c['variant'] in ['control_gru_matched','none','admissible']}
    findings=dict(clinical=clinical,paired_stay_gaps=paired,simulator_k1=decomposition,horizon_external_gaps=gaps,
                  coupling_A_val={k:ci[k] for k in ['value','lower_95','upper_95']},
                  cohort=load('cohort_replay_v1/REPLAY_RESULTS.json')['counts'])
    tables={
        'clinical':[dict(model=model,split=split,**vals) for model,splits in clinical.items() for split,vals in splits.items()],
        'horizons':[dict(design=design,**flatten(vals)) for design,vals in gaps.items()],
        'sim_forecast':[dict(kappa=c['kappa'],variant=c['variant'],**flatten(c['metrics'])) for c in h3],
        'sim_policy':[dict(protocol=c['cf_protocol'],confound=c['confound'],sigma=c['sigma'],model=c['model'],**flatten(c['metrics'])) for c in h5]}
    variants=load('v4/variant_ablation_v4.json')['table']
    tables['variants']=[dict(model=m,variant=v,split=s,**summary(r[s]['pooled_masked_RMSE'] for r in cell['runs'] if r['status']=='complete'))
        for m,vs in variants.items() for v,cell in vs.items() for s in 'AB']
    organs=load('v4/per_organ_v4.json')['selected_seed_summary']
    tables['organs']=[dict(model=m,split=s,organ=o,**summary(x for x in cell['per_seed'].values() if x is not None))
        for m,ss in organs.items() for s,os in ss.items() for o,cell in os.items() if not(m=='ncde' and s=='B')]
    tables['crn']=[dict(file=str(p.relative_to(ROOT)),**flatten(json.loads(p.read_text())['config']),**flatten(json.loads(p.read_text())['metrics']))
        for folder in ['crn_v2_policy_grid','crn_v2_lambda_sweep'] for p in sorted((ROOT/'results/learned_graph_baselines_v1'/folder).glob('*.json'))]
    tables['coupling']=[]
    for relative in ['coupling_index_v1/coupling_index.json','coupling_index_v1/simulator_hourly/sim_hourly_index.json']:
        data=load(relative)
        for dataset,record in data['datasets'].items():
            probes=record.get('probes',{'ridge':record['ridge']} if 'ridge' in record else {})
            for probe,pr in probes.items():
                for split,sc in pr['splits'].items():
                    tables['coupling'].append(dict(dataset=dataset,probe=probe,split=split,**flatten(sc['mean_off_diagonal'])))
    return findings,tables


def readme_table(findings):
    rows=['| Model | Internal A | External B | Frozen source |','|---|---:|---:|---|']
    for model,label,source in [('grud','GRU-D','[selected runs](results/v4/tuning_grid.json)'),
        ('physiograph_gru','PhysioGraph-GRU','[selected runs](results/v4/tuning_grid.json)'),
        ('t-PatchGNN','t-PatchGNN','[four runs](results/learned_graph_baselines_v1/tpatchgnn/)'),
        ('GraFITi','GraFITi','[four runs](results/learned_graph_baselines_v1/grafiti_v3/)')]:
        vals=findings['clinical'][model]
        cells=[f'{vals[s]["mean"]:.4f} ± {vals[s]["sd_sample"]:.4f}' for s in 'AB']
        rows.append(f'| {label} | {cells[0]} | {cells[1]} | {source} |')
    return '\n'.join(rows)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out-dir',type=Path,help='write JSON, Markdown and eight CSV tables')
    ap.add_argument('--check',action='store_true',help='compare the derived findings and README clinical table')
    args=ap.parse_args()
    findings,tables=calculate()
    block=readme_table(findings)
    if args.check:
        expected=load('findings.json')
        if findings!=expected:raise ValueError('derived findings differ from results/findings.json')
        readme=(ROOT/'README.md').read_text()
        if block not in readme:raise ValueError('README clinical table differs from frozen results')
        snippets=[]
        for split in 'AB':
            gap=findings['paired_stay_gaps'][split]
            snippets.append(f"{gap['mean_gap']:.4f} ± {gap['sd_sample']:.4f}")
            assert abs(findings['clinical']['gru_med'][split]['mean']-findings['clinical']['grud'][split]['mean']) < .002
        snippets.extend(f"{value:.4f}" for value in findings['simulator_k1'].values())
        snippets.extend(f"+{findings['horizon_external_gaps'][f'C12_K{k}']['gap']:.3f}" for k in [6,12,24])
        ci=findings['coupling_A_val']
        snippets.append(f"+{ci['value']:.4f} [{ci['lower_95']:.4f}, {ci['upper_95']:.4f}]")
        snippets.append(f"{sum(c['found'] for c in findings['cohort'].values()):,}")
        for snippet in snippets:
            if snippet not in readme:raise ValueError(f'README finding differs: {snippet}')
        trace=json.loads((ROOT/'manifests/readme_trace.json').read_text())
        assert all(value < .003 for value in trace['variants']['mean_span'].values())
        print('Frozen findings, clinical table and all computed README display values: PASS')
    if args.out_dir:
        args.out_dir.mkdir(parents=True,exist_ok=True)
        (args.out_dir/'findings.json').write_text(json.dumps(findings,indent=2,allow_nan=False)+'\n')
        table_block=block.replace('](results/', ']('+os.path.relpath(ROOT/'results',args.out_dir.resolve())+'/')
        (args.out_dir/'clinical.md').write_text(table_block+'\n')
        for name,rows in tables.items():
            columns=list(dict.fromkeys(k for row in rows for k in row))
            with (args.out_dir/f'{name}.csv').open('w',newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=columns);writer.writeheader();writer.writerows(rows)
    elif not args.check:
        print(block)

if __name__=='__main__':
    main()
