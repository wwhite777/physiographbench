# PhysioGraphBench v1.2.0 — reachable E3 rerun evidence and cohort composition

Release date: 2026-11-06. This release adds the four replacement E3 run records,
their reading and summary, a complete effective inventory, and the aggregate
cohort-composition companion. It preserves all original run records, source
code, tests, frozen readings, numeric result files and previously shipped arrays.
Version 1.1.2 remains the preceding documentation release. No new release-specific
archival DOI or remote publication is asserted here; the concept DOI and earlier
version records retain their existing roles.

## E3 evidence and lineage

All paths below are relative to the repository root. The files are available
under `experiments/counterfactual_onset_matched/artifacts/host/`:

- `E3_READING_RERUN_ADDENDUM.md`: the current-archive rerun interpretation and
  every affected printed table, before and after.
- `e3_summary_rerun.json`: full-precision effective rows, aggregates, paired
  contrasts, endpoint trends and original/replacement reconciliation.
- `main_rerun/`: four `run.json` files only, at the family/point/model/seed paths
  enumerated in the experiment README. No weights, predictions or logs are added.
- `E3_EFFECTIVE_INVENTORY.json`: 160 effective records (156 original plus four
  replacements), their public SHA-256 hashes and archive-identity metadata;
  four superseded originals remain separately listed and retained in `main/`.

The replacements are support point 1 CRN-lite seed 3, support point 1
PhysioGraph state-space model seed 1, support point 2 PhysioGraph-GRU seed 0,
and dependence point 4 CRN-lite seed 3. Select effective records from the
inventory rather than pooling both physical trees. The experiment folder has
192 retained run records: 160 effective main records, 28 unchanged diagnostic
and matched-control records, and four superseded originals.

Broader measured support still gives much better direction recovery at fixed
measured rank dependence; the tested modest dependence range gives a smaller
descriptive decline with wide seed uncertainty; repaired CRN-lite has no
consistent exact-direction advantage over Control-GRU. Shared-anchor exact
RMSE equality changes to 15/16 pairs, and one nominal state-space-minus-Control
heart-rate RMSE interval becomes positive. These qualifications and their
full-precision values are in the addendum and summary. Original fits used one
CPU thread and re-fits used two, so archive and thread effects are not isolated.

The effective 160-record grid matches the current source archive hashes.
Earlier mismatched records and their hashes remain historical provenance;
the unavailable earlier training arrays are not retroactively certified.
Recorded archive/manifest validation comes from the rerun evidence; the
packaging checks do not regenerate those archives or claim independent
scientific review. Earlier frozen readings and historical sections of
REPRODUCE.md describe their original snapshot; the new addendum governs
the effective main-grid reconciliation. The matched randomized-dose
diagnostics in the earlier addendum are unchanged.

Sanitization uses the same path and descriptive-label transformation as the
existing public `main/` records. Numerical values, ordering and original
hashes are preserved. Summary `source.sha256` and other historical digests
identify pre-distribution bytes; the effective inventory and `SHA256SUMS`
identify the sanitized public files. Unbundled archive, binary, log, execution
and historical-research locators remain provenance descriptions, not promised
downloads. The unchanged artifact verifier assumes 188 records and can check
a scratch effective view that omits the four superseded originals; the release
tree retains all originals.

## Cohort composition and compute

`docs/COHORT_COMPOSITION.json` supplies aggregate counts and observed-target
entry denominators for CinC-2019 A/B and CinC-2012 set-a/set-b. Distributed-row
counts are 20,336 / 20,000 / 4,000 / 4,000; eligible counts are 15,837 / 14,824 /
3,989 / 3,993. Eligibility requires at least 24 hourly observations. Target
coverage counts observed entries at hours 12–23, stratified by available age,
sex and care-unit descriptors. No patient rows or identifiers are included.
Its source locators map to the rebuild paths in REPRODUCE.md and its source
archive hashes match `manifests/cohorts.json`.

The four re-fits add 100.63263659738004 CPU job-seconds (100.6 when rounded)
outside the preserved 1,509-fit compute snapshot; `docs/COMPUTE.md` gives each
timer. Packaging adds no training executions. These totals remain recorded-cost
subtotals rather than lifetime compute.

The root README, experiment README, compute note, reproduction version line
and citation version are updated. Data-source attribution uses the public
PhysioNet/CinC dataset labels. `SHA256SUMS` is regenerated over every file
except itself in the established two-space format. All other existing files
retain their exact preceding bytes; no executable or ignore pattern changes.
