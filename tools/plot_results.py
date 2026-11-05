#!/usr/bin/env python3
"""Draw data plots directly from frozen numerical evidence, with no refitting."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from release_paths import ROOT
import argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from summarize_results import calculate,load

COLORS=['#0072B2','#D55E00','#009E73','#CC79A7']


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out-dir',type=Path,default=ROOT/'runs/figures')
    args=ap.parse_args();args.out_dir.mkdir(parents=True,exist_ok=True)
    findings,_=calculate()
    plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    def save(fig,name):
        fig.tight_layout()
        for ext in ['png','pdf','svg']:fig.savefig(args.out_dir/f'{name}.{ext}',dpi=180,bbox_inches='tight')
        plt.close(fig)
    models=['grud','physiograph_gru','t-PatchGNN','GraFITi']
    labels=['GRU-D','Organ GRU','t-PatchGNN','GraFITi']
    fig,axes=plt.subplots(1,2,figsize=(10,4),sharey=True)
    for ax,split in zip(axes,'AB'):
        vals=[findings['clinical'][m][split] for m in models]
        for x,v,color in zip(range(4),vals,COLORS):
            ax.errorbar(x,v['mean'],yerr=v['sd_sample'],fmt='o',color=color,capsize=4)
        ax.set_xticks(range(4),labels,rotation=20);ax.set_title(f'Clinical {split}');ax.set_ylim(.70,.85)
        ax.set_ylabel('Pooled observed-entry RMSE')
    save(fig,'clinical')
    cells=load('sim_grids_v1/h3_grid_with_controls.json')['cells']
    fig,ax=plt.subplots(figsize=(7,4))
    for variant,label,color in zip(['control_gru_matched','none','admissible'],['Monolithic GRU (matched)','Factorised, no edges','Factorised, physiological edges'],COLORS):
        cs=sorted([c for c in cells if c['variant']==variant],key=lambda c:c['kappa'])
        ax.errorbar([c['kappa'] for c in cs],[c['metrics']['macro_nrmse_fixed']['mean'] for c in cs],
            yerr=[c['metrics']['macro_nrmse_fixed']['std'] for c in cs],marker='o',label=label,color=color,capsize=3)
    ax.set_xlabel('Coupling κ');ax.set_ylabel('Macro NRMSE, fixed reference ranges');ax.legend(fontsize=9)
    save(fig,'simulator_controls')
    cells=[c for c in load('sim_grids_v1/h5_grid.json')['cells'] if c['cf_protocol']=='shared' and c['model']=='control_gru']
    cs=sorted({c['confound'] for c in cells});ss=sorted({c['sigma'] for c in cells})
    fig,axes=plt.subplots(1,3,figsize=(11,4),constrained_layout=True)
    for ax,channel in zip(axes,['MAP','UO','Lac']):
        image=np.asarray([[next(c for c in cells if c['confound']==cv and c['sigma']==sv)['metrics']['direction_accuracy']['per_channel'][channel]['mean'] for sv in ss] for cv in cs])
        im=ax.imshow(image,vmin=0,vmax=1,cmap='viridis',aspect='auto')
        ax.set_xticks(range(len(ss)),ss);ax.set_yticks(range(len(cs)),cs)
        ax.set_title(channel);ax.set_xlabel('Assignment noise σ');ax.set_ylabel('Severity dependence c')
    fig.colorbar(im,ax=axes,label='Adjacent-dose direction accuracy')
    # Colorbar uses constrained layout, so avoid a conflicting tight_layout call.
    for ext in ['png','pdf','svg']:fig.savefig(args.out_dir/f'direction_recovery.{ext}',dpi=180,bbox_inches='tight')
    plt.close(fig)
    fig,ax=plt.subplots(figsize=(6,4))
    ax.plot([6,12,24],[findings['horizon_external_gaps'][f'C12_K{k}']['gap'] for k in [6,12,24]],'o-',color=COLORS[1])
    ax.axhline(0,color='0.5',linewidth=1);ax.set_xlabel('Forecast horizon (hours)')
    ax.set_ylabel('Organ-GRU minus GRU-D external RMSE');ax.set_xticks([6,12,24])
    save(fig,'horizon_gap')
    hourly=load('coupling_index_v1/simulator_hourly/sim_hourly_index.json')
    fig,ax=plt.subplots(figsize=(7,4))
    for split,color in [('A_val',COLORS[0]),('B',COLORS[1])]:
        points=sorted(hourly['datasets'].values(),key=lambda x:x['kappa'])
        valid=[p for p in points if p['ridge']['splits'][split]['mean_off_diagonal']['value'] is not None]
        vals=[p['ridge']['splits'][split]['mean_off_diagonal'] for p in valid]
        y=np.asarray([x['value'] for x in vals])
        low=y-np.asarray([x['lower_95'] for x in vals]);high=np.asarray([x['upper_95'] for x in vals])-y
        ax.errorbar([p['kappa'] for p in valid],y,yerr=[low,high],marker='o',label=split,color=color,capsize=3)
    ax.set_xlabel('Simulator coupling κ');ax.set_ylabel('Hourly ridge cross-organ predictive gain')
    ax.legend();ax.set_title('Undefined zero-coupling mean is omitted')
    save(fig,'hourly_coupling')
    print(f'Wrote five figure families to {args.out_dir}')

if __name__=='__main__':
    main()
