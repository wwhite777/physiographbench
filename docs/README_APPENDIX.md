# Preserved scientific appendix

[APPENDIX_MOVED_TO_REPOSITORY.tex](APPENDIX_MOVED_TO_REPOSITORY.tex) retains the
scientific appendix text, equations, numerical tables, explanations and
qualifications from the earlier full source. It is a historical reference
fragment, starting at the appendix boundary; the earlier main article,
front matter and typesetting setup are outside this file. It is not a
standalone build project: citations, figures and references to sections outside
the fragment depend on the original surrounding document.

Use the current [README](../README.md),
[release notes](RELEASE_V1_1_1.md),
[shared-input primary records](../experiments/shared_input_primary/README.md)
and [leaderboard](../leaderboard/README.md) for current interpretation. In
particular, the shared-input model is now the primary organ comparison, the
CinC-2019 CDE B replay remains unresolved, and the small nonzero simulator gap
at coupling 0.75 is not a demonstrated tie or equivalence. The retained older
wording and tables are evidence history; they do not supersede these corrections.
Weights and patient-level arrays are not included even where historical prose
describes their creation. The repository's current citation metadata and
checksum manifest control release identification and distributed-file integrity.

Public-release transformations were limited to:

- Extracting the appendix portion, without the earlier main text or front matter.
- Removing private trace/source comments, while preserving rendered equations
  and numerical table entries, including scientific file/line explanations in
  the body text.
- Removing the sentence about incomplete contact/funding and release preparation.
- Rewording a determinism-record label as a determinism check, and describing
  earlier reported results without internal document-process wording.
- Replacing prospective hosting/identifier language with a pointer to current
  repository release metadata, and rewording the environment-versus-typesetting
  sentence as an experiment-versus-release-check distinction.
- Omitting the final process-only release/build-status subsection, which named
  private source/build files and submission preparation. The scientific sections
  on cohort replay, clinical runs, environment and simulator/adapter records
  immediately before it remain. The hourly simulator extension is labelled
  exploratory while retaining its lack of physiological calibration.

The separate [shared-input arm inventory](../experiments/shared_input_primary/E2_arm_inventory.json)
preserves all 40 arm/seed objects, including directed edge lists, parameter
counts, in/out degrees and Jaccard overlaps. Its private selection/probe lineage
was replaced by the public selection record path and its distributed-file hash;
organ index order and edge orientation are stated explicitly.
