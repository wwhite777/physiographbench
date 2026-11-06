# Distribution and historical provenance

This folder includes code, registered protocols, scalar/run records and authored
readings. Historical numbers, Boolean/null leaves, ordering and fingerprints in
copied JSON records are preserved. String paths and internal workflow labels
are relocated for distribution. `manifests/distribution.json` at the repository
root records original/distributed hashes and the exact per-file transformations.
`SHA256SUMS` checks the delivered bytes.

An original fingerprint in a run record identifies the historical source or
archive. It is not replaced by the sanitized file's fingerprint. The separate
distribution inventory relates both. Historical references to unbundled logs,
weights, error arrays and patient data document the original experiment and do
not imply those files are distributed or that a new fit/replay was performed.
Run the documented entry points from the repository root. Existing scientific
limitations, protocol differences and missing-evidence statements are retained.
This packaging check does not constitute independent scientific review.
