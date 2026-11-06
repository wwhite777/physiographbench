# Distribution transformations

The distribution inventory stores original and distributed SHA-256 independently.
Original hashes identify the immutable input bytes. They are not overwritten by
hashes of edited files. The public distribution has its own `SHA256SUMS`.

1. The organ model, original clinical baseline module and base simulator are
   copied without byte changes. Other source files retain their numerical
   functions and hyperparameters while entry points resolve the root from
   `PHYSIOGRAPH_ROOT` or this checkout. The `release_paths` bootstrap registers
   the four public module folders and resolves scratch from `TMPDIR`.
2. Private absolute path literals become paths relative to the release root.
   Former separate workspaces become `src/`, `tools/`, `sim/` and `baselines/`.
   Current outputs go under `runs/` and generated data under `data/`. Scientific
   JSON path strings are mapped to their public destinations; the associated
   original hashes continue to describe the original files.
3. Descriptive strings are scrubbed of private identifiers, internal roles and
   publication-status metadata. Floating-point/integer/Boolean/null values and
   array order are preserved. JSON indentation and Unicode escaping can change.
   Internal reviews, workflow records and paper documents are excluded.
4. The 2012 builder no longer requires two unused source files from an upstream
   checkout solely to hash them. Those original unit-reference hashes remain in
   the frozen build summary. Neither file is imported or redistributed. Parsing,
   hourly averaging, unit choices, cohort arrays and normalization are unchanged.
5. Historical preflight checks tied to an unavailable overwritten checkpoint pair
   become distribution-source and cohort-integrity checks in the public clinical
   drivers. The historical exception remains in the frozen run manifest. Clinical
   plans, selection rules, budgets and training/evaluation equations are retained.
6. The CDE diagnostic accepts both the historical state dictionary and the v4
   checkpoint envelope, reading its saved model sizes and `state_dict`. This
   enables diagnosis of a newly trained checkpoint without changing inference
   equations. Its frozen diagnostic carries the current external-divergence
   interpretation separately from its original numerical observations.
7. Simulator metadata includes paths, timing and source fingerprints, so a new
   archive hash can differ after packaging. Every non-metadata array has a separate
   frozen dtype, shape and payload hash. The coupling-index input check verifies
   these payloads and the distributed loader source instead of expecting obsolete
   whole-archive fingerprints. The 2019 cohort still requires its exact hash.
8. New helpers enumerate the experiment sequence, replay and verify datasets,
   rebuild tables, draw data plots, and run synthetic CPU integration checks.
   They do not alter the frozen numeric evidence. Newly generated public files
   are identified as additions in the inventory rather than assigned invented
   original hashes.

The per-file inventory and private build record distinguish modified copies from
new helpers. Full cohort byte checks and selected full-size simulator array checks
validate the computation after these changes; they do not constitute a new
independent scientific review or a repeat of the complete training series.

9. The supplied overview replaces the earlier conceptual image without changing
   the supplied PNG bytes. CinC-2012 table bytes are also unchanged. The added
   CinC-2012 JSONs map private paths to relative historical locators and the
   interpreter to `python3`; numbers, Boolean/null values, hashes and array order
   are unchanged. Historical source locators under `historical_sources/cinc2012/`
   identify original files that are not bundled. Commands in the frozen manifest
   are historical records, not newly validated portable entry points. The result
   interpretation retains the scientific discussion and removes internal role,
   workflow and paper-insertion annotations. This does not constitute a new
   training run or an independent scientific review.

10. The renal shared-input diagnostic includes both no-edge arms at four paired
    seeds, their full curves, the original checkpoint-replay summary, and the
    subsequent shared-input interpretation. All archived numbers, booleans,
    nulls, array order and original fingerprints are retained. Only paths and
    descriptive workflow labels are changed. The optional checkpoint replay
    accepts original fingerprints through this inventory while also requiring
    the live distributed source hash. The fixed configuration checks use the
    distributed selection and source hashes. Its CPU tests use a synthetic
    cohort and inference only; they do not require patient data or fit models.
    Internal task labels inherited in comments, strings and one directory name
    become scientific descriptive labels, with references updated consistently.

11. The CinC-2012 drivers now import the distributed clinical protocol and graph
    adapters directly. Private input inventories become distribution-source and
    cohort-hash checks; locally generated transfer checkpoints require matching
    full-fit records, identities and cohort hashes. Repository-relative commands
    in `cinc2012_commands.json` preserve all 88 historical jobs and their settings.
    The launcher uses the current interpreter and configurable CPU/CUDA lanes;
    outputs and regenerated tables use `runs/`. The training loops, data splits,
    normalization, eligibility, validation selection and metric arithmetic remain
    unchanged. The new data-free reconstruction mode rechecks seed summaries;
    the CPU smoke fits one 64-stay, single-epoch within-corpus GRU and reports the
    absent source-checkpoint prerequisite for transfer. Frozen results, including
    numeric JSON leaves and original fingerprints, are copied without changes.

12. Round-4 experiment distribution adds the positive control, shared-input
    primary/budget experiments, onset-matched counterfactuals, learned-graph
    validation, paired-statistics records and measured compute accounting.
    Copied JSON keeps every numeric, Boolean and null token byte-identical in
    its original traversal order. Only string tokens are relocated/reworded;
    original fingerprints are historical and remain unchanged, except each
    positive-control dataset manifest's output fingerprint, which identifies
    its distributed archive. Both archive fingerprints remain in this inventory.
    Historical private root prefixes become repository-relative paths. Selected
    experiment sources map to their experiments/ or analysis/ directory;
    simulator dependencies map to sim/, graph adapters to baselines/, clinical
    diagnostics to diagnostics/ and existing aggregate tables to results/.
    Unbundled provenance is retained as a historical locator and does not imply
    that those files ship. No original result or scientific number is replaced.

    The three positive-control NPZ archives replace only metadata_json.npy.
    All other uncompressed NPY members, including dtype, shape and payload,
    remain byte-identical. The embedded metadata changes only JSON strings.
    The clinical observation-rate snapshot is extracted from the original
    κ=1 metadata and lets the synthetic generator operate without patient data.
    The registered design fingerprint and its pre-result UTC timestamp remain
    original; the sanitized design has a separate distributed fingerprint.

    Python entry points add the common release bootstrap and use the existing
    src/, sim/, tools/ and baselines/ modules. The shared-input runner loads the
    prior edge diagnostic with its own helper to preserve correct module-local
    paths, then restores the primary runner's helper. Source integrity checks
    use distributed code fingerprints while run records preserve original ones.
    Training, model construction, graph draws, split, selection and scoring
    equations are retained. Launchers default to fresh runs/ output directories,
    accept --dry-run, resolve from the repository root and preserve preflight
    refusal of existing outputs. A separately named matched-control group lists
    the four addendum Control-GRU fits; the default counterfactual plan stays
    at 184 fits. The E5 planners print a portable python3 command. No training
    or external data access occurs merely to enumerate plans.

    Paired-statistics --verify recomputes saved paired t arithmetic and MDD
    power without checking unavailable historical bytes. --dry-run inventories
    prerequisites. Full historical recomputation is explicit through
    --source-root and requires the omitted original error/prediction inputs.
    --check-original-inputs checks original fingerprints only when those bytes
    are supplied. The public counterfactual artifact verifier checks the 188
    complete, finite run records and the command plans; it does not pretend to
    inspect omitted private smoke or prediction archives. The original
    scientific missing-array and dataset-hash qualifications remain in place.

    New test path assertions use the release layout and frozen edge-check
    records where full clinical run records are optional. The inherited smoke
    fitting test and three experiment fitting tests gain an environment guard:
    PHYSIOGRAPH_NO_TRAINING=1 reports explicit skips. All other scientific test
    assertions are retained. pytest is added to the pinned verification
    requirements. Package READMEs, notes, the release section and citation
    version/date are documentation additions; the MIT license is unchanged.
