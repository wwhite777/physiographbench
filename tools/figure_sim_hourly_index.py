#!/usr/bin/env python3
"""Plot simulator hourly ridge index versus kappa alongside CinC ridge bands."""

# Resolve all public modules and scratch from the release root.
import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[1]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from generate_hourly import ROOT, save_json, sha256


def main():
    source = ROOT / 'sim_hourly_index.json'
    result = json.loads(source.read_text())
    points = sorted(result['datasets'].values(), key=lambda d: d['kappa'])
    x = np.array([d['kappa'] for d in points])
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.6), sharey=True)
    metadata = dict(source_path=str(source), source_sha256=sha256(source), panels={})
    for ax, split, title in zip(axes, ('A_val', 'B'), ('Validation (A_val)', 'Holdout (B)')):
        summaries = [d['ridge']['splits'][split]['mean_off_diagonal'] for d in points]
        values = np.array([s['value'] if s['value'] is not None else np.nan for s in summaries])
        lower = np.array([s['lower_95'] if s['lower_95'] is not None else np.nan for s in summaries])
        upper = np.array([s['upper_95'] if s['upper_95'] is not None else np.nan for s in summaries])
        band = result['cinc']['means']['ridge'][split]
        ax.axhspan(band['lower_95'], band['upper_95'], color='#ca6f28', alpha=.18,
                   label='CinC-2019 ridge: 95% interval')
        ax.axhline(band['value'], color='#ad571d', lw=1.5)
        ax.fill_between(x, lower, upper, color='#206798', alpha=.18)
        ax.plot(x, values, 'o-', color='#206798', lw=1.6,
                label='Simulator ridge: 95% interval')
        ax.axhline(0, color='0.55', lw=.7, ls=':')
        undefined = [f'{d["kappa"]:g}' for d, s in zip(points, summaries) if s['value'] is None]
        if undefined:
            ax.text(.97, .96, 'Undefined mean at κ = ' + ', '.join(undefined) + '\n(constant renal target)',
                    transform=ax.transAxes, ha='right', va='top', fontsize=8)
        ax.set_title(title)
        ax.set_xlabel('Simulator κ')
        ax.set_xlim(-.025, 1.025)
        ax.set_xticks(x)
        ax.grid(alpha=.17)
        metadata['panels'][split] = dict(
            simulator=[dict(kappa=d['kappa'], **s) for d, s in zip(points, summaries)],
            cinc=band)
    axes[0].set_ylabel('Mean directed off-diagonal coupling index')
    axes[1].legend(loc='lower right', fontsize=8)
    fig.text(.5, .025,
             '12-hour history → next-hour target; 1,000 patient-bootstrap resamples.\n'
             'Simulator: 3 organs / 6 pairs, 60 evaluation patients per split; CinC: 4 organs / 12 pairs.\n'
             'Simulator B is a patient holdout; CinC B is an external hospital. See figure metadata for entry counts.',
             ha='center', va='bottom', fontsize=8)
    fig.tight_layout(rect=(0, .17, 1, 1))
    output = ROOT / 'figures'
    output.mkdir(exist_ok=True)
    for suffix in ('png', 'pdf'):
        fig.savefig(output / f'sim_hourly_index.{suffix}', dpi=180)
    plt.close(fig)
    save_json(output / 'sim_hourly_index.metadata.json', metadata)
    print('Wrote figures/sim_hourly_index.png, .pdf, .metadata.json')


if __name__ == '__main__':
    main()
