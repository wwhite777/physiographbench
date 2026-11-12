#!/usr/bin/env python3
"""Print or sequentially execute the 18 fixed-cap clinical extension fits."""
import argparse
import shlex
import subprocess
import sys
from n2_common import *

def plan():
    return [[sys.executable,'-B',str(ROOT/'experiments/shared_input_primary/n2_train.py'),
        '--family',family,'--seed',str(seed),'--device','cuda',
        '--output-dir',str(RUNS/family/f'seed{seed}')] for seed in range(4,10) for family in CAPS]

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    mode=ap.add_mutually_exclusive_group()
    mode.add_argument('--dry-run',action='store_true')
    mode.add_argument('--execute',action='store_true')
    args=ap.parse_args()
    commands=plan()
    if args.execute:
        verify(COHORT)
        for family in CAPS: chosen(family)
        for command in commands:
            dest=Path(command[-1])
            if dest.exists() or dest.is_symlink(): raise FileExistsError(dest)
        for command in commands: subprocess.run(command,cwd=ROOT,check=True)
    else:
        for command in commands: print(shlex.join(command))
if __name__=='__main__': main()
