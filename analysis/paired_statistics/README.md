# Paired statistics from frozen results

The saved analysis contains **641 paired contrasts**, **8 Holm families of
9 comparisons**, **64 paired bootstrap rows**, and **108 direction-decomposition
cells**. A paired contrast takes the difference between models with the same
training/split seed. Four-seed Student-t intervals and two-sided p values use
three degrees of freedom. Minimum detectable difference (MDD) inverts the
noncentral t distribution at 80% power and 5% significance using the observed
paired standard deviation as a planning value.

From the repository root:

```bash
python3 -B analysis/paired_statistics/paired_stats.py --dry-run
python3 -B analysis/paired_statistics/paired_stats.py --verify
```

`--verify` independently recalculates the stored paired t intervals, p values
and MDD power from the four recorded differences. It checks all 641 contrast
rows and the saved inventory dimensions, without fitting models. Original
input fingerprints are historical; the public byte manifest verifies the
distributed files. This mode does not reconstruct bootstraps from patient
arrays or claim that every historical input is bundled.

The full calculation functions remain available with `--source-root PATH`.
That path must supply the complete historical result tree at the released
relative locators, including the error arrays required for patient bootstrap
recomputation. Use `--verify --check-original-inputs --source-root PATH` only
with original bytes; relocated public JSON files have separate distributed
fingerprints. No patient error or prediction arrays are shipped.

Read [PAIRED_STATS_v5.md](PAIRED_STATS_v5.md) and
[paired_stats_v5.json](paired_stats_v5.json). The original status is
`PARTIAL_DIRECTION_ARRAYS_BLOCKED`: exact first-target-excluded and
effect-tolerance historical direction scores are unidentified without the
missing original per-cell predictions. Saved truth datasets and a small smoke
prediction file cannot replace full-grid predictions. This limitation is
preserved; nominal exploratory intervals do not resolve multiplicity or
patient-population uncertainty.
