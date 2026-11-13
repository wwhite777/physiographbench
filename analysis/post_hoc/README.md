# Post-hoc numerical companions

These secondary analyses were assembled after the primary results were known.
They reproduce arithmetic from released records without fitting, inference or
PyTorch. `inputs.json` names every source file or JSON pointer; record hashes
are checked against the distribution inventory or root checksum list. A missing
input prevents any result. Outputs are deterministic JSON, printed by default:

```bash
for table in cap_matrix equal_organ clinical_2x2 input_access treatment; do
  python3 -B analysis/post_hoc/read_post_hoc.py "$table" --check
done
python3 -B analysis/post_hoc/stay_bootstrap.py --check
```

`cap_matrix.json` contains all nine admissible-cap versus none-cap pairings,
each on A and B with seeds 0–3, selected ten-seed contrasts, validation means
and validation margins. Caps 105/70/35 for none/admissible/GRU-D minimize mean
A-validation RMSE over the original four seeds, breaking exact ties toward the
smaller cap. Test results do not enter selection. Cap and cosine schedule vary
jointly; this does not isolate training duration. `equal_organ.json` averages
the four organ RMSEs equally within each seed before summarizing ten seeds.
Its units use A-training SDs, without simulator range normalization.

`clinical_2x2.json` uses four common-configuration seeds of partitioned/shared
input access crossed with none/admissible edges. It reproduces all four
pairwise contrasts and their interaction. The configuration was selected on
partitioned inputs; sharing adds 18,432 projection parameters and edges add
152,080. The comparison cannot isolate information access from capacity.
`input_access.json` reports the synthetic κ=1 interaction for seeds 0–3 and
0–9, and shared none minus shared admissible. All these seed intervals are
pointwise Student t intervals with sample SD, conditional on the frozen
cohorts/population. They do not establish equivalence or patient-level benefit.

`treatment.json` contrasts dependence endpoint4 minus endpoint0 for each of
four models and four seeds. Exact scoring compares adjacent-dose effect signs,
excluding zero true effects. Thresholded scoring maps abs(effect)≤τ to zero
separately for truth and predictions, then excludes zero thresholded truth.
The cutoffs are MAP 0.1 mmHg, HR 0.1 beats/min, CO 0.01 L/min, CVP 0.05 mmHg,
UO 0.01 mL/min and lactate 0.01 mmol/L. They are numerical sensitivity cutoffs,
not clinical thresholds. Endpoint contrasts average per-seed ratios. Saved
counts were independently verified against trajectories before release; this
reader reconstructs the table from those counts and does not replay omitted
trajectories. Exact endpoint intervals span zero for all four models;
thresholded changes are negative in all four seeds and their intervals exclude
zero. These simulated secondary results do not identify real treatment effects.

## Stay-cluster bootstrap

`stay_A.npz` and `stay_B.npz` contain `none_sse` and `admissible_sse`, shaped
10×n_stays in seed order 0–9, and a common `count` vector. SSE means the sum of
squared prediction errors per stay over observed target cells. Counts are
identical across arms/seeds and were checked before extraction. No stay indices,
raw observations, labels, trajectories or model weights are distributed.
`stay_manifest.json` records array and archive hashes, shapes, dtypes and all
forty original archive fingerprints. Float32 archived SSE values are represented
exactly as float64; historical fingerprints are not distributed-byte hashes.

The bootstrap uses NumPy PCG64 seeds **20261112 for A** and **20261113 for B**,
**2000** resamples of n evaluable stays with replacement. A draw resamples the
same stays jointly across both arms and all ten seeds. Zero-target stays are
excluded after checking zero SSE. For each arm and seed, the script sums SSE
and target counts across sampled stays, takes the pooled RMSE root, subtracts
none from admissible, then averages those ten differences. It reports linear
2.5/97.5 percentile intervals, draw SD, all 2000 mean draws per cohort, per-seed
intervals and a fingerprint of the full draw matrix. A separate root after
pooling all seed-target cells is labeled as a different estimand.

The procedure conditions on the twenty fitted checkpoints and selected caps;
it does not refit or resample training seeds. Stays are independent clusters
for this calculation, not identified people. Multiple admissions and hospital
sampling are outside the interval. The exact RNG, batch size 16, summation
order and NumPy linear quantiles are fixed in `stay_bootstrap.py`. No inference
is required to regenerate `stay_bootstrap.json` from these sufficient statistics.
