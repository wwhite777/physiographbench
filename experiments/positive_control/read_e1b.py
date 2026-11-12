"""Read all 96 E1 + 66 E1b records before evaluating the unchanged D-016 gate."""
from __future__ import annotations
import os as _os
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, _os.environ.get('PHYSIOGRAPH_ROOT', str(_Path(__file__).absolute().parents[2])))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH


import argparse
import json
import math
from pathlib import Path
import statistics
import sys

import e1b_protocol as protocol

# Two-sided Student t(.975, n-1), matching E1's paired-seed method.
CRITICAL_T = {4: 3.182446305284263, 10: 2.2621571628540993}
THRESHOLD = .0040


def interval(values):
    values = list(values)
    n = len(values)
    if n not in CRITICAL_T or not all(math.isfinite(x) for x in values):
        raise ValueError('Intervals require four or ten finite seed values')
    mean, sd = statistics.mean(values), statistics.stdev(values)
    half = CRITICAL_T[n] * sd / math.sqrt(n)
    return dict(n=n, mean=mean, sd=sd, ci95=[mean - half, mean + half],
                seed_values=values, method=f'Student t, paired seeds for differences, df={n - 1}')


def load_records(new_root=protocol.RECORD_ROOT, e1_root=protocol.E1_ROOT):
    new_jobs, old_jobs = protocol.jobs(new_root), protocol.e1_jobs(e1_root)
    missing_new = [str(job['out']) for job in new_jobs if not job['out'].is_file()]
    missing_old = [str(job['out']) for job in old_jobs if not job['out'].is_file()]
    if missing_new or missing_old:
        raise ValueError(
            f'INCOMPLETE: missing {len(missing_new)}/66 new and {len(missing_old)}/96 E1 records; '
            'no verdict or result table is available.\n'
            + '\n'.join(missing_new + missing_old))
    protocol.check_frozen_inputs()
    datasets = dict.fromkeys(protocol.KAPPAS)
    records = {}
    for job in [*old_jobs, *new_jobs]:
        try:
            record = json.loads(job['out'].read_text())
            protocol.validate_record(record, job, datasets[job['kappa']], datasets[1.])
        except (ValueError, KeyError, TypeError, AssertionError) as exc:
            raise ValueError(f'INVALID record {job["out"]}: {exc}') from exc
        key = (job['kappa'], job['arm'], job['seed'])
        records[key] = dict(value=record['metrics']['macro_nrmse_fixed'],
                            path=str(job['out']), sha256=protocol.sha256(job['out']))
    return records


def gate_tests(edge_effect, gru_difference):
    # Do not re-estimate a quarter of the new partitioned effect: D-016 froze
    # the absolute cutoff at .0040. Intervals are reported, not added as gates.
    return dict(shared_edge_mean_below_0_0040=edge_effect < THRESHOLD,
                shared_none_within_0_0040_of_gru=abs(gru_difference) <= THRESHOLD)


def summarize(records):
    def values(kappa, arm, seeds):
        return [records[kappa, arm, s]['value'] for s in seeds]

    def difference(kappa, left, right, seeds):
        return interval(a - b for a, b in zip(values(kappa, left, seeds),
                                              values(kappa, right, seeds)))

    comparisons = {}
    for n in (4, 10):
        seeds = range(n)
        comparisons[str(n)] = {
            'shared_none_minus_shared_admissible':
                difference(1., 'shared_none', 'shared_admissible', seeds),
            'shared_none_minus_control_gru':
                difference(1., 'shared_none', 'control_gru', seeds),
            'partitioned_none_minus_admissible':
                difference(1., 'none', 'admissible', seeds),
        }
    primary = comparisons['10']
    tests = gate_tests(primary['shared_none_minus_shared_admissible']['mean'],
                       primary['shared_none_minus_control_gru']['mean'])
    table = []
    for kappa in protocol.KAPPAS:
        row = dict(kappa=kappa, seeds=[0, 1, 2, 3], arms={})
        for access, arms in (('partitioned', ('none', 'admissible')),
                             ('shared', protocol.SHARED_ARMS)):
            row['arms'][access] = {arm: interval(values(kappa, arm, range(4))) for arm in arms}
        row['edge_effects_none_minus_admissible'] = {
            'partitioned': difference(kappa, 'none', 'admissible', range(4)),
            'shared': difference(kappa, 'shared_none', 'shared_admissible', range(4)),
        }
        row['interaction_partitioned_effect_minus_shared_effect'] = interval(
            records[kappa, 'none', s]['value'] - records[kappa, 'admissible', s]['value']
            - records[kappa, 'shared_none', s]['value']
            + records[kappa, 'shared_admissible', s]['value'] for s in range(4))
        table.append(row)
    ten_seed = {
        'arms': {arm: interval(values(1., arm, range(10))) for arm in protocol.TEN_SEED_ARMS},
        'comparators_minus_partitioned_admissible': {
            arm: difference(1., arm, 'admissible', range(10))
            for arm in ('none', 'reversed', 'random', 'control_gru')},
        'arms_minus_partitioned_none': {
            arm: difference(1., arm, 'none', range(10)) for arm in protocol.TEN_SEED_ARMS},
        'shared_admissible_minus_shared_none': difference(1., 'shared_admissible', 'shared_none', range(10)),
        'not_extended': dict.fromkeys(('dense', 'misspecified-1', 'control_gru_matched'),
                                    'Only seeds 0--3 exist; no ten-seed interval is estimable.'),
    }
    if all(tests.values()):
        verdict = 'D-016 thesis supported in this sensitivity regime'
    elif not tests['shared_edge_mean_below_0_0040']:
        verdict = 'D-016 thesis not supported: edges help beyond information access in this regime'
    else:
        verdict = 'D-016 thesis not supported: shared none is not within 0.0040 of the monolithic GRU'
    return dict(
        decision='D-016 and addendum 1', validated_records=dict(e1=96, new=66),
        endpoint='metrics.macro_nrmse_fixed', threshold=THRESHOLD,
        sign='Differences are the named left arm minus right arm; positive none-minus-admissible favors edges.',
        interval_scope='Split/initialization seeds on one generated population (dataset seed 0); not patient-population uncertainty.',
        within_interpretation='Absolute paired mean shared_none-minus-control_gru <= 0.0040.',
        gate_uses='Ten-seed means only; fixed 0.0040 cutoff; intervals do not change the rule.',
        tests=tests, verdict=verdict, paired_comparisons_by_seed_count=comparisons,
        input_access_by_edges_four_seed_table=table, kappa_1_ten_seed_intervals=ten_seed,
        records=[dict(kappa=k, arm=a, seed=s, **record)
                 for (k, a, s), record in sorted(records.items())])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--new-root', type=Path, default=protocol.RECORD_ROOT)
    parser.add_argument('--e1-root', type=Path, default=protocol.E1_ROOT)
    parser.add_argument('--out', type=Path, help='Optional new JSON file inside historical-experiment; refuses overwrite')
    args = parser.parse_args(argv)
    try:
        result = summarize(load_records(args.new_root, args.e1_root))
        if args.out is not None:
            protocol.write_json(args.out, result)
    except (ValueError, OSError, KeyError, TypeError, AssertionError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
