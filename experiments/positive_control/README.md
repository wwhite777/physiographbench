# Positive control for prescribed edges

This synthetic experiment adds a delayed cardiovascular reserve drive to renal
and metabolic targets. Only context inputs are masked; dense noisy synthetic
labels supply supervision. Normalized root mean squared error (NRMSE) divides
each organ's root mean squared error by its fixed reference range, then averages
the three organs. The reference is the 400-patient, seed-0, κ = 1 dataset.

The pre-registered criterion requires all three comparator gaps (none, reversed,
random minus admissible) at κ = 1 to have a positive mean and a two-sided 95%
paired Student-t interval wholly above zero; each comparator's four-seed mean
gap must be non-decreasing at κ = 0, 0.5, 1, and the oracle must qualify. There
is no trend tolerance or comparator substitution. The oracle requires at least
5% gain at κ = 1 and at most 2% positive gain at κ = 0, as specified in
[DESIGN_E1.md](DESIGN_E1.md). All registered conditions pass in the saved results.

The original design hash
`2da026b680606b650e05638e4cb9ce1686feb6d35a8d181ee662a65fed0a09e6`
was registered at 2026-11-05T13:32:20.210412+00:00, before implementation and before
any oracle or neural results. [DESIGN_REGISTRATION.json](DESIGN_REGISTRATION.json)
preserves that original fingerprint; the distribution inventory records the
sanitized design's separate fingerprint. These two fingerprints serve different
purposes and need not match.

Run from the repository root in the environment described by the top-level README:

```bash
bash experiments/positive_control/run_host_e1.sh --dry-run
python3 -B experiments/positive_control/oracle_check.py --help
PHYSIOGRAPH_NO_TRAINING=1 python3 -B -m unittest discover -s experiments/positive_control/tests -v
```

The plan prints **99 commands: 3 dataset generations and 96 fits** (3 coupling
levels × 8 arms × 4 seeds), at 60 epochs per fit. Use `--execute` to run the
printed grid into the fresh `runs/full/` directory, or choose a fresh
`--output-root` below this experiment. The released records in `artifacts/full/`
are preserved. A single generation command is:

```bash
python3 -B experiments/positive_control/sim_positive_control.py generate --kappa 1 --n-patients 400 --seed 0 --out experiments/positive_control/runs/generated/kappa_1.npz
```

All three synthetic datasets are included (under 6 MB total). Their numeric
array members are unchanged; embedded string provenance is relocated, with
archive hashes in `manifests/distribution.json`. A frozen clinical observation
rate snapshot lets synthetic generation and tests run without downloading
clinical data. If `data/cinc2019_cohort.npz` is present, rates are counted from it.
The snapshot contains counts/rates, with no patient records.

The oracle's κ = 1 renal and metabolic gains are 0.209625 and 0.289632.
The full 96-fit inventory, nine paired comparison cells, fixed ranges and
limitations are in [E1_READING.md](artifacts/full/E1_READING.md) and
[e1_summary.json](artifacts/full/e1_summary.json). This artificial positive
control does not establish clinical benefit or revise the original regime's null.
