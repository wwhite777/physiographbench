#!/usr/bin/env python3
"""Print or execute the complete frozen experiment sequence; all outputs go to runs/."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from release_paths import ROOT
import argparse
import itertools
import json
import shlex
import subprocess
from host_driver_v2 import plan as clinical_plan

KAPPAS = ('0', '0.1', '0.25', '0.5', '0.75', '1.0')
SEEDS = range(4)


def commands(suite, device='cpu', threads=1):
    py = sys.executable
    jobs = []
    def add(script, *args):
        jobs.append([py, '-B', str(ROOT / script), *map(str,args)])
    if suite in ('all', 'clinical'):
        jobs.extend(j['command'] for j in clinical_plan(ROOT/'runs/clinical',device)['jobs'])
    if suite in ('all', 'sim_forecast'):
        add('tools/replay_simulators.py','--group','forecast','--run')
        for k,variant,seed in itertools.product(KAPPAS,('admissible','reversed','random','dense','none','misspecified-1'),SEEDS):
            add('sim/sim_grid_runner.py','--task','forecast','--kappa',k,'--variant',variant,
                '--model','physiograph_gru','--confound',1,'--sigma',.03,'--seed',seed,
                '--dataset_seed',0,'--n_patients',400,'--epochs',60,'--lr',.002,
                '--C',12,'--K',24,'--d_model',64,'--d_state',32,'--n_layers',2,
                '--device',device,'--threads',threads,'--npz',ROOT/f'data/sim_forecast/h3_k{k}.npz',
                '--reference_npz',ROOT/'data/sim_forecast/reference_k1_c1_sigma003.npz',
                '--out',ROOT/f'runs/sim_forecast/runs/h3_k{k}_{variant}_s{seed}.json')
        add('sim/aggregate_grids.py','--in',ROOT/'runs/sim_forecast/runs','--out',
            ROOT/'runs/sim_forecast/h3_grid.json',ROOT/'runs/sim_forecast/unused_h5.json',ROOT/'runs/sim_forecast/unused_overlap.csv')
        for matched in (False,True):
            label='sim_matched' if matched else 'sim_mono'
            for k,seed in itertools.product(KAPPAS,SEEDS):
                extra=['--control_gru_hidden',201] if matched else []
                add('sim/sim_grid_runner_mono2.py' if matched else 'sim/sim_grid_runner_mono.py',
                    '--task','forecast','--kappa',k,'--variant','none','--model','control_gru',
                    '--allow_monolithic_control',*extra,'--confound',1,'--sigma',.03,'--seed',seed,
                    '--dataset_seed',0,'--n_patients',400,'--epochs',60,'--lr',.002,
                    '--C',12,'--K',24,'--d_model',64,'--d_state',32,'--n_layers',2,
                    '--horizon_h',6,'--out_dt',300,'--device',device,'--threads',threads,
                    '--npz',ROOT/f'data/sim_forecast/h3_k{k}.npz',
                    '--reference_npz',ROOT/'data/sim_forecast/reference_k1_c1_sigma003.npz',
                    '--out',ROOT/f'runs/{label}/runs/h3_k{k}_control_gru_s{seed}.json')
            add('sim/aggregate_mono2.py' if matched else 'sim/aggregate_mono.py',
                '--in',ROOT/f'runs/{label}/runs','--h3',
                ROOT/('runs/sim_mono/h3_grid_with_mono.json' if matched else 'runs/sim_forecast/h3_grid.json'),
                '--baseline_runs',ROOT/'runs/sim_forecast/runs','--out',
                ROOT/f'runs/{label}'/('h3_grid_with_controls.json' if matched else 'h3_grid_with_mono.json'),
                '--require_complete')
    if suite in ('all','sim_policy'):
        add('tools/replay_simulators.py','--group','policy','--run')
        for protocol in ('shared','legacy'):
            cs=KAPPAS if protocol=='shared' else ('0','0.5','1.0')
            sigmas=('0','0.08','0.15','0.25') if protocol=='shared' else ('0.03',)
            for c,sigma,model,seed in itertools.product(cs,sigmas,('physiograph','physiograph_gru','control_gru','crn_lite'),SEEDS):
                add('sim/sim_grid_runner2.py','--task','counterfactual','--kappa',1,
                    '--cf_protocol',protocol,'--confound',c,'--sigma',sigma,'--model',model,
                    '--variant','admissible','--seed',seed,'--dataset_seed',0,'--n_patients',400,
                    '--epochs',60,'--lr',.002,'--C',12,'--K',24,'--d_model',64,'--d_state',32,'--n_layers',2,
                    '--device','cpu','--threads',threads,
                    '--npz',ROOT/f'data/sim_policy/{protocol}_c{c}_sigma{sigma}.npz',
                    '--reference_npz',ROOT/'data/sim_policy/legacy_c1.0_sigma0.03.npz',
                    '--out',ROOT/f'runs/sim_policy/runs/h5_{protocol}_c{c}_sigma{sigma}_{model}_s{seed}.json')
        add('sim/aggregate_grids2.py','--in',ROOT/'runs/sim_policy/runs','--out',
            ROOT/'runs/sim_policy/h5_grid.json',ROOT/'runs/sim_policy/overlap_table.csv','--require_complete')
    if suite in ('all','learned_graphs'):
        for model,script in [('tpatchgnn','cinc_port_runner_tp.py'),('grafiti','cinc_port_runner_v3.py')]:
            for seed in SEEDS:
                add('baselines/'+script,'--model',model,'--npz',ROOT/'data/cinc2019_cohort.npz',
                    '--seed',seed,'--epochs',35,'--batch_size',128,'--lr',.001,'--C',12,'--K',12,
                    '--threads',threads,'--out',ROOT/f'runs/learned_graphs/{model}/cinc_{model}_s{seed}.json')
    if suite in ('all','crn'):
        cells=list(itertools.product(KAPPAS,('0','0.08','0.15')))
        schedules=[(c,s,1.,60,seed,'policy') for (c,s),seed in itertools.product(cells,SEEDS)]
        schedules += [(c,s,lamb,60,seed,'sweep') for (c,s),lamb,seed in itertools.product([('0','0'),('0','0.25'),('1.0','0.25')],(0.,.25,1.),SEEDS)]
        schedules += [('0','0',0.,120,seed,'long') for seed in SEEDS]
        for c,s,lamb,epochs,seed,arm in schedules:
            add('baselines/crn_policy_runner_v2.py','--confound',c,'--sigma',s,'--lamb',lamb,
                '--full_zero','--cf_protocol','shared','--seed',seed,'--dataset_seed',0,'--n_patients',400,
                '--epochs',epochs,'--lr',.002,'--C',12,'--K',24,'--threads',threads,
                '--out',ROOT/f'runs/crn/{arm}_c{c}_s{s}_lambda{lamb}_ep{epochs}_seed{seed}.json')
    if suite in ('all','coupling'):
        add('tools/coupling_index.py','--datasets','all','--simulator-mode','diagnostic',
            '--threads',threads,'--out',ROOT/'runs/coupling/coupling_index.json')
        add('tools/replay_simulators.py','--group','hourly','--run')
        add('tools/sim_hourly_index.py','--out',ROOT/'runs/coupling/sim_hourly_index.json')
    return jobs


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--suite',choices=['all','clinical','sim_forecast','sim_policy','learned_graphs','crn','coupling'],default='all')
    ap.add_argument('--device',default='cpu')
    ap.add_argument('--threads',type=int,default=1)
    ap.add_argument('--run',action='store_true')
    ap.add_argument('--manifest',type=Path)
    args=ap.parse_args()
    jobs=commands(args.suite,args.device,args.threads)
    if args.manifest:
        args.manifest.parent.mkdir(parents=True,exist_ok=True)
        args.manifest.write_text(json.dumps({'suite':args.suite,'commands':jobs},indent=2)+'\n')
    for i,command in enumerate(jobs):
        print(shlex.join(command),flush=True)
        if args.run:
            log=ROOT/f'runs/logs/{args.suite}_{i:04d}.log'
            log.parent.mkdir(parents=True,exist_ok=True)
            with log.open('x') as stream:
                subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,check=True)

if __name__=='__main__':
    main()
