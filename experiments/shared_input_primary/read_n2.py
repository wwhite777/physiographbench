#!/usr/bin/env python3
"""Paired ten-seed N2 contrasts, with four-seed values beside them.

Refuses partial/invalid generations before computing or printing any result.
Negative lhs-minus-rhs pooled masked RMSE favors the lhs. The experimental unit
is the training seed; patients are not treated as independent training replicates.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from n2_common import CAPS, ROOT, HOST, read, verify, clinical, location, chosen
import numpy as np
sys.path.insert(0, str(ROOT / 'analysis/cap_selection'))
from cap_reanalysis import power_design


def paired_summary(values, design):
    values = np.asarray(values, dtype=np.float64)
    n = design['n_pairs']
    if values.shape != (n,) or not np.isfinite(values).all():
        raise ValueError('invalid paired observations')
    mean = float(values.mean())
    sd = float(values.std(ddof=1))
    se = sd / math.sqrt(n)
    half = design['critical_t'] * se
    return dict(n_pairs=n, df=n - 1, mean_difference=mean,
                ci95_paired_t=[mean - half, mean + half], paired_sd_sample=sd,
                standard_error=se,
                sign_count=dict(negative=int((values < 0).sum()),
                                zero=int((values == 0).sum()), positive=int((values > 0).sum())),
                mdd_80pct_alpha05=(design['mdd_multiplier'] * sd if sd > 0 else None),
                mdd_note=None if sd > 0 else 'undefined: zero estimated paired SD')


def collect_records(root=HOST):
    records, catalog = {}, []
    for family in CAPS:
        chosen(family)
        for seed in range(10):
            loc = location(family, seed, root)
            path = ROOT / loc.partition('#')[0]
            verify(path)
            record = clinical(read(loc), seed, CAPS[family])
            if family != 'grud' and (record['arm'] != family or record['input_mode'] != 'shared'):
                raise ValueError('Wrong shared arm')
            if family == 'grud' and record['model'] != 'grud': raise ValueError('Wrong reference family')
            records[family,seed] = record
            catalog.append(dict(family=family,cap=CAPS[family],seed=seed,path=loc,sha256=__import__('hashlib').sha256(path.read_bytes()).hexdigest()))
    return records,catalog


def analyze(records, catalog):
    designs = {str(n): power_design(n) for n in (4, 10)}
    rows = []
    for lhs, rhs in (('admissible', 'none'), ('none', 'grud'), ('admissible', 'grud')):
        for split in ('A', 'B'):
            observations = [dict(seed=seed,
                                 lhs=records[lhs, seed][split]['pooled_masked_RMSE'],
                                 rhs=records[rhs, seed][split]['pooled_masked_RMSE'])
                            for seed in range(10)]
            for item in observations:
                item['difference'] = item['lhs'] - item['rhs']
            values = [item['difference'] for item in observations]
            rows.append(dict(contrast=f'{lhs}@{CAPS[lhs]} minus {rhs}@{CAPS[rhs]}',
                             split=split, metric='pooled_masked_RMSE', observations=observations,
                             four_seed=paired_summary(values[:4], designs['4']),
                             ten_seed=paired_summary(values, designs['10'])))
    return dict(task='experiments-shared_input_primary', status='complete', selected_caps=CAPS,
                sign_convention='lhs minus rhs; negative favors lhs',
                interval='paired t interval, two-sided 95%; df=9 for ten seeds, df=3 for four',
                mdd='80% power, two-sided alpha=.05; exact historical-experiment noncentral-t inversion via historical-experiment; estimated paired SD',
                power_designs=designs, contrasts=rows, source_catalog=catalog,
                families={family:{split:{str(n):dict(mean=float(np.mean([records[family,s][split]['pooled_masked_RMSE'] for s in range(n)])),sample_sd=float(np.std([records[family,s][split]['pooled_masked_RMSE'] for s in range(n)],ddof=1))) for n in (4,10)} for split in ('A','B')} for family in CAPS})


def table(result):
    lines = ['All 30 selected-cap records passed distributed-byte, identity, scope and stopping checks. Omitted curves, weights and error arrays are not replayed.',
             'Pooled masked RMSE; lhs minus rhs, negative favors lhs. Signs are negative/zero/positive.',
             '95% paired t intervals: df=3 for four seeds, df=9 for ten. MDD80: 80% power at two-sided alpha=0.05, historical-experiment noncentral-t method.',
             '', '| Contrast | Split | 4 seeds: mean [95% CI] | Signs | MDD80 | 10 seeds: mean [95% CI] | Signs | MDD80 |',
             '|---|---|---|---|---|---|---|---|']
    for row in result['contrasts']:
        cells = [row['contrast'], row['split']]
        for key in ('four_seed', 'ten_seed'):
            s = row[key]
            low, high = s['ci95_paired_t']
            signs = s['sign_count']
            mdd = s['mdd_80pct_alpha05']
            cells += [f"{s['mean_difference']:+.6f} [{low:+.6f}, {high:+.6f}]",
                      '/'.join(str(signs[k]) for k in ('negative', 'zero', 'positive')),
                      'undefined (zero SD)' if mdd is None else f'{mdd:.6f}']
        lines.append('| ' + ' | '.join(cells) + ' |')
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true', help='print full precision JSON and source hashes')
    args = parser.parse_args(argv)
    try:
        records, catalog = collect_records()
        result = analyze(records, catalog)
    except (ValueError, KeyError, OSError) as error:
        parser.exit(2, f'REFUSED: {error}\n')
    print(json.dumps(result, indent=2, allow_nan=False) if args.json else table(result), end='\n' if args.json else '')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
