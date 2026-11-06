"""Policy-only checks (no ODE or training) plus inventory of the 24 legacy sets."""

import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[2]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH
import argparse
import csv
import json
from pathlib import Path

import numpy as np

import sim_policy_ext3 as e3


def verify(n_patients=400, seeds=(0, 1, 2, 3), include_legacy=True, output_prefix=None):
    rows, details = [], []
    for seed in seeds:
        base, _, _ = e3.record_policy(family='legacy', seed=seed, n_patients=n_patients)
        severity = base['severity']
        by_family = {}
        for family in e3.FAMILIES[:2]:
            points = []
            for point in range(5):
                dose, policy = e3.assign_policy(severity, family=family, point=point, seed=seed)
                stats = policy['statistics']
                points.append((dose, stats))
                row = dict(family=family, point=point, dataset_seed=seed, n=n_patients,
                    target_rank=policy['rank_target'], spearman=stats['spearman'], pearson=stats['pearson'],
                    width=policy['width'], support_fraction=stats['support_fraction'],
                    dose_min=float(dose.min()), dose_max=float(dose.max()),
                    dose_mean=float(dose.mean()), dose_std=float(dose.std()), n_unique=len(np.unique(dose)),
                    **{f'tercile{g}_q{q}': stats['terciles'][g][f'q{q}']
                       for g in range(3) for q in ('05', '95')})
                rows.append(row)
                details.append(dict(**row, policy=policy))
            by_family[family] = points
        support = by_family['support_only']
        assert max(s['pearson'] for _, s in support) - min(s['pearson'] for _, s in support) <= e3.CORRELATION_BAND
        assert max(abs(s['spearman'] - e3.RANK_TARGET) for _, s in support) <= e3.CORRELATION_BAND
        assert all(support[i][1]['support_fraction'] <= support[i + 1][1]['support_fraction'] for i in range(4))
        dependence = by_family['dependence_only']
        assert all(dependence[i][1]['spearman'] < dependence[i + 1][1]['spearman'] for i in range(4))
        assert all(dependence[i][1]['pearson'] < dependence[i + 1][1]['pearson'] for i in range(4))
        groups, _ = e3.severity_groups(severity)
        for g in range(3):
            for dose, stats in dependence:
                np.testing.assert_array_equal(np.sort(dose[groups == g]),
                                              np.sort(dependence[0][0][groups == g]))
                assert abs(stats['terciles'][g]['q05'] - .025) < e3.SUPPORT_BAND
                assert abs(stats['terciles'][g]['q95'] - .475) < e3.SUPPORT_BAND
    legacy = []
    if include_legacy:
        directory = e3.PROJECT / 'runs/sim_policy/data'
        paths = sorted(directory.glob('shared_*.npz'))
        assert len(paths) == 24
        for path in paths:
            with np.load(path) as packed:
                stats = e3.policy_statistics(packed['severity'], packed['factual_dose'])
                metadata = json.loads(str(packed['metadata_json']))
            legacy.append(dict(path=str(path), sha256=e3.sha256(path),
                               confound=metadata['confound'], sigma=metadata['sigma'], statistics=stats))
    report = dict(n_patients=n_patients, seeds=list(seeds), verified=True, policy_version=e3.POLICY_VERSION,
                  rank_band=e3.CORRELATION_BAND, support_absolute_band=e3.SUPPORT_BAND,
                  controlled_cells=details, legacy_diagnostic=legacy)
    if output_prefix is not None:
        prefix = e3.owned_path(output_prefix)
        e3.write_json(prefix.with_suffix('.json'), report)
        with prefix.with_suffix('.csv').open('w') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        lines = ['| family | point | seed | Spearman | Pearson | width | supported grid fraction | assigned dose std | unique |',
                 '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
        lines += [f"| {r['family']} | {r['point']} | {r['dataset_seed']} | {r['spearman']:.6f} | {r['pearson']:.6f} | {r['width']:.2f} | {r['support_fraction']:.3f} | {r['dose_std']:.6f} | {r['n_unique']} |" for r in rows]
        lines += ['', 'Full per-cell quantiles, ten-bin distributions and all 24 hashed legacy cells are in the accompanying JSON.',
                  'Support is an empirical 5–95% dose interval in a severity tercile; it does not certify identification.']
        prefix.with_suffix('.md').write_text('\n'.join(lines) + '\n')
    print('family point seed rank_target spearman pearson q05 q95 assigned_std assigned_unique histogram')
    for row, detail in zip(rows, details):
        counts = detail['policy']['statistics']['target_distribution']['histogram_counts']
        print(row['family'], row['point'], row['dataset_seed'], row['target_rank'],
              f"{row['spearman']:.6f}", f"{row['pearson']:.6f}",
              f"{row['tercile0_q05']:.6f}", f"{row['tercile0_q95']:.6f}",
              f"{row['dose_std']:.6f}", row['n_unique'], counts)
    print(f'verified {len(rows)} controlled policy cells; inventoried {len(legacy)} legacy datasets')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--n_patients', type=int, default=400)
    parser.add_argument('--seeds', type=int, nargs='+', default=[0, 1, 2, 3])
    parser.add_argument('--no-legacy', action='store_true')
    parser.add_argument('--output-prefix', default=str(e3.ROOT / 'artifacts/policy_statistics'))
    args = parser.parse_args()
    if not args.no_legacy:
        parser.error("legacy archives are not bundled; use --no-legacy or regenerate runs/sim_policy/data first")
    verify(args.n_patients, args.seeds, False, args.output_prefix)
