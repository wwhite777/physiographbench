"""Population replication reader; no fitting or model imports."""
from pathlib import Path
import os
import sys
sys.path.insert(0, os.environ.get('PHYSIOGRAPH_ROOT',str(Path(__file__).absolute().parents[2])))
import argparse
import json
import math
import statistics
from release_1_3_1 import ROOT, records as verified_records
CELLS=('none','admissible','shared_none','shared_admissible','control_gru')
SEEDS=(0,1,2,3)

T975 = {4: 3.182446305284263, 5: 2.7764451051977987}
THRESHOLD = .0040
RULE_VERBATIM = (
    'the pattern replicates in population p if (a) mean < 0 with its interval excluding zero '
    'AND (b) mean < 0.0040 AND |(c) mean| ≤ 0.0040 (the fixed thresholds). '
    'The paper may say the routing result holds across the five generated populations only '
    'if it replicates in all four new ones; otherwise it reports each population and names '
    'where it holds or fails.')
CONTRASTS = (
    'a_partitioned_admissible_minus_none',
    'b_shared_none_minus_shared_admissible',
    'c_shared_none_minus_control_gru',
    'd_interaction_shared_minus_partitioned',
)


def interval(values, scope):
    values = list(values)
    n = len(values)
    if n not in T975 or not all(math.isfinite(x) for x in values):
        raise ValueError('Require four or five finite values for Student t interval')
    mean, sd = statistics.mean(values), statistics.stdev(values)
    half = T975[n] * sd / math.sqrt(n)
    return dict(n=n, mean=mean, sd=sd, ci95=[mean - half, mean + half], values=values,
                signs=dict(negative=sum(v < 0 for v in values), zero=sum(v == 0 for v in values),
                           positive=sum(v > 0 for v in values)),
                sign_sequence=['-' if v < 0 else '+' if v > 0 else '0' for v in values],
                method=f'two-sided Student t 95%, df={n - 1}', scope=scope)


def replication_rule(contrasts):
    a, b, c, _ = (contrasts[name] for name in CONTRASTS)
    tests = dict(a_mean_negative=a['mean'] < 0,
                 a_interval_excludes_zero=a['ci95'][1] < 0,
                 b_mean_below_0_0040=b['mean'] < THRESHOLD,
                 absolute_c_mean_at_most_0_0040=abs(c['mean']) <= THRESHOLD)
    return dict(tests=tests, replicates=all(tests.values()))


def load_records(root=ROOT):
    records={}
    for key,(record,row) in verified_records('s1',root).items():
        records[key]=dict(value=record['metrics']['macro_nrmse_fixed'],metrics=record['metrics'],
                          path=row['path'],sha256=row['sha256'])
    return records

def summarize(records):
    expected = {(population, cell, seed) for population in range(5) for cell in CELLS for seed in SEEDS}
    if set(records) != expected:
        raise ValueError('Require exactly 100 identities: 80 new + 20 existing population-0 records')
    populations = []
    for population in range(5):
        arrays = {cell: [records[population, cell, seed]['value'] for seed in SEEDS] for cell in CELLS}
        a = [x - y for x, y in zip(arrays['admissible'], arrays['none'])]
        b = [x - y for x, y in zip(arrays['shared_none'], arrays['shared_admissible'])]
        c = [x - y for x, y in zip(arrays['shared_none'], arrays['control_gru'])]
        d = [-shared - partitioned for shared, partitioned in zip(b, a)]
        contrasts = {name: interval(values, 'Four pairs matched by training/split seed 0--3 within population')
                     for name, values in zip(CONTRASTS, (a, b, c, d))}
        populations.append(dict(population=population, training_seeds=list(SEEDS),
                                cells={cell: interval(v, 'Training/split seeds within one population')
                                       for cell, v in arrays.items()},
                                contrasts=contrasts, **replication_rule(contrasts)))
    new = populations[1:]
    synthetic = any(value.get('synthetic_test_fixture', False) for value in records.values())
    descriptive = {name: interval([row['contrasts'][name]['mean'] for row in populations],
                                  'DESCRIPTIVE: five population means, dataset seeds 0--4; n=5')
                   for name in (CONTRASTS[0], CONTRASTS[1], CONTRASTS[3])}
    return dict(decision='Frozen population replication rule (2026-11-13T06:56:39Z)',
                endpoint='metrics.macro_nrmse_fixed', validated_records=dict(new=80, existing=20),
                synthetic_test_fixture_present=synthetic, evidence_eligible=not synthetic,
                rule_verbatim=RULE_VERBATIM, threshold=THRESHOLD,
                contrast_definitions=dict(zip(CONTRASTS, (
                    'partitioned admissible − partitioned none',
                    'shared none − shared admissible',
                    'shared none − full-input Control-GRU',
                    '(admissible − none)shared − (admissible − none)partitioned'))),
                interval_scope='Pointwise paired t intervals; no multiplicity adjustment. '
                               'Within-population intervals describe training/split-seed variation.',
                fixed_reference='Frozen population 0, κ=1, full-population organ ranges, unchanged from E1B.',
                populations=populations, descriptive_five_population_summary=descriptive,
                replicating_new_populations=[row['population'] for row in new if row['replicates']],
                failing_new_populations=[row['population'] for row in new if not row['replicates']],
                routing_result_holds_across_five_generated_populations=all(row['replicates'] for row in new),
                reporting_rule='Report every population and every contrast whatever the outcome. '
                               'The across-five statement requires all four new populations to pass.',
                records=[dict(population=pop, cell=cell, seed=seed, **value)
                         for (pop, cell, seed), value in sorted(records.items())])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    try:
        result=summarize(load_records(args.root))
        text=json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n'
        if args.check:
            expected=args.root/'experiments/positive_control/artifacts/population_replication/summary.json'
            if text != expected.read_text(): raise ValueError('Population summary differs')
            print('PASS: 100 population records and published summary')
        else: print(text,end='')
    except (ValueError,KeyError,OSError,TypeError) as error:
        parser.exit(2,f'REFUSED: {error}\n')

if __name__=='__main__': main()
