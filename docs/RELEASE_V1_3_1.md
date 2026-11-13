# PhysioGraphBench 1.3.1

Released 2026-11-13. This update adds 80 population-replication records, four
synthetic population archives with manifests, eight device-matched learned-CUDA
records, post-hoc numerical companions and one failed official-code attempt.
Historical result records and fingerprints remain unchanged. Distribution
fingerprints separately identify sanitized bytes; `SHA256SUMS` covers the
complete distribution except itself.

The routing result meets its frozen rule in all four new populations and may
therefore be described across five generated populations, each with four paired
training/split seeds. The rule uses partitioned edge benefit and two fixed mean
thresholds; it is not equivalence or a general population guarantee. New S1
records lack logged runtime dtype, with only source/data evidence for float32.
The original positive-control criterion and population-0 ten-seed analysis
retain their original scope and are not retroactively redefined.

Matched learned-CUDA comparisons retain all original CPU contrasts. t-PatchGNN
A random/complete fixed-minus-learned intervals remain above zero; A physiological
now includes zero. All matched external-B and GraFITi intervals include zero.
CUDA refitting, precision reduction and thread settings change jointly, and
fixed GraFITi retains its receiving-variable time-state change. These are not
isolated hardware effects or equivalence tests.

The post-hoc companion supplies the cap matrix and validation margins,
equal-organ score, clinical 2×2, synthetic interaction, treatment dependence
endpoints and paired stay-cluster bootstrap, with deterministic JSON targets.
Released per-stay SSE/count arrays omit identifiers and trajectories. The
bootstrap conditions on fitted checkpoints and selected caps. Thresholded
treatment results are numerical sensitivity analyses on simulated outcomes.

The separate official-code GraFITi P12 fold0 attempt exited during
dataset/encoder construction with `KeyError: 'Time'` before fitting. Its cause
was not diagnosed. The full sanitized log and record supply no benchmark score.

See [REPRODUCE.md](../REPRODUCE.md#release-131-population-replication-and-post-hoc-companion)
for the no-fitting checks. New readers reject absent/changed records and compare
their full deterministic JSON to released outputs. No clinical data, checkpoints,
upstream vendor checkout or unpublished manuscript is added. `CITATION.cff`
uses version 1.3.1 and the concept DOI, without inventing a new version DOI.
