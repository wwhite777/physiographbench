# PhysioGraphBench v1.1.1 documentation update

This update synchronizes reader-facing claims with the v5 findings. It preserves
the v1.1.0 code, results, protocols, tests, citation metadata and historical
provenance files. The only binary change is the README overview PNG, rendered
from the supplied v5 pipeline PDF at 150 dpi. No training or new result is
claimed. The concept DOI is
[10.5281/zenodo.23976171](https://doi.org/10.5281/zenodo.23976171); the v1.1.0
record is [10.5281/zenodo.23992302](https://doi.org/10.5281/zenodo.23992302).
A separate v1.1.1 archive record of the code is not asserted here. The 140 selected
per-seed checkpoints are published as a separate Zenodo checkpoints record,
[10.5281/zenodo.23993257](https://doi.org/10.5281/zenodo.23993257), with a manifest, loading script and README.

## Which records support the current claims?

| Current interpretation | Released evidence |
|---|---|
| Shared-input primary, 35-epoch comparison, graph controls and separate 70/105-epoch budgets | [Primary reading](../experiments/shared_input_primary/artifacts/host/E2_E4_READING.md) and adjacent summary JSON |
| Registered prescribed-edge sensitivity PASS and its artificial-regime scope | [Positive-control reading](../experiments/positive_control/artifacts/full/E1_READING.md) and registration |
| Onset-matched support/dependence policies, repaired CRN target and matched randomised-dose estimator comparison | [Policy reading](../experiments/counterfactual_onset_matched/artifacts/host/E3_READING.md) and [addendum](../experiments/counterfactual_onset_matched/artifacts/host/E3_READING_ADDENDUM.md) |
| GraFITi published-protocol gap and fixed-adjacency ablations | [Learned-graph reading](../experiments/learned_graph_validation/artifacts/E5_READING.md) |
| Post-hoc renal input finding and historical fixed-configuration edges | [Renal reading](../diagnostics/renal_shared_input/SHARED_INPUT_READING.md), [edge reading](../diagnostics/shared_input_edges/SHARED_INPUT_EDGES_READING.md) |
| Paired intervals, historical simulator's nearly equal means and missing-array limits | [Paired-statistics report](../analysis/paired_statistics/PAIRED_STATS_v5.md) |
| Measured cost, 113.11 GPU job-hours and 16.17 CPU job-hours over 1,509 timed fits and 45 evaluation jobs | [Compute accounting](COMPUTE.md); recorded subtotals, excluding unrecorded failed attempts and tuning dead ends |

The primary shared-input series has its own A-validation selection. The earlier
fixed-configuration renal and edge diagnostics were post-hoc, after results and
reviews were seen, and retain their capacity/input-access qualifications. Their
numbers are not a primary-table ranking. The 70-epoch budget control is a
separate comparison with same-cap GRU-D; its intervals include zero for none,
while admissible edges do not close the gap. No primary clinical edge set is
consistently better than none. The positive-control PASS concerns one generated
population, four training/split seeds and artificial hidden-state drive/delays;
it does not establish clinical edge benefit.

The dependence-only family spans rank correlation 0–0.30. Severe deterministic
dependence is tested only in the legacy grid, which jointly changes support.
The historical audit records four dataset-hash discrepancies across three
training archives. Earlier training arrays are unavailable; matching saved
predictions and test truth does not establish their identity. The discrepancies
remain a provenance limitation. External CinC-2019 neural CDE checkpoint replay
is unresolved; finite saved errors remain diagnostic and outside confirmed
rankings.

## Integrity and historical display boundary

`SHA256SUMS` is regenerated in the established repository-relative format and
covers every current distribution file except itself. The historical
`manifests/distribution.json` remains unchanged: hashes and sizes for edited
Markdown and the overview PNG identify v1.1.0 bytes. Its original fingerprints
are not replaced. `manifests/readme_trace.json` remains a v1.1.0 record; `CITATION.cff` states
version 1.1.1 with the unchanged concept DOI; this README and these notes state
the current documentation version and claim sources.

The legacy table generator and plotting tool reconstruct frozen v4 displays.
`make findings` invokes summarizer `--check`, which also requires the old README
table verbatim and therefore rejects this updated README. The current README
and REPRODUCE use the existing exporter without that obsolete README check,
then compare the exported JSON values with `results/findings.json`. Their partitioned-input headline and older labels do not
regenerate the v5 primary README table or override the qualified interpretations
in the current documentation. Frozen diagnostic prose and numerical records
retain their original bytes, including older CDE labels. Consult the current
README and experiment READMEs for the corrected status. No checkpoint replay
repair or historical training-provenance replication is claimed by this update.

Public de-identified data and synthetic stress tests do not establish clinical
treatment effects, decision benefit or subgroup fairness. Re-identification and
treatment use are outside scope. Preserve upstream data attribution and licences;
the simulator is not patient-specific advice.
