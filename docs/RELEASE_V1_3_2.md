# PhysioGraphBench 1.3.2

Released 2026-11-13. This patch initializes the release 1.3.1 tests with the
shared `release_paths.SCRATCH` convention: the three temporary-directory
controls use repository `.scratch/` when `TMPDIR` is unset and respect an
explicit `TMPDIR`. The [documented no-fitting checks](../REPRODUCE.md#release-131-population-replication-and-post-hoc-companion)
therefore run directly without Makefile environment setup. There is no
scientific change: data, saved results, reader calculations, thresholds and
scientific conclusions are unchanged. Version metadata and `SHA256SUMS`
are updated for this patch.
