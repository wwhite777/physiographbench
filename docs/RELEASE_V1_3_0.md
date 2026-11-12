# PhysioGraphBench 1.3.0

Released 2026-11-12. This update adds 100 scalar run records and portable code
for validation-selected clinical caps, ten-seed contrasts, shared-input
CinC-2012, and input access × edges in the synthetic sensitivity regime.
Original scientific records remain immutable; new records change JSON strings
only for distribution. The [transformation inventory](../manifests/TRANSFORMATIONS.md)
and [100-record manifest](../manifests/release_1_3_records.json) separate original
and distributed fingerprints. No patient records, weights or residual arrays
are added. Synthetic datasets are read in place from the existing release.

The [README](../README.md#results-added-in-130) reports the scoped results and
qualifications. In the generated sensitivity regime, prescribed edges help
when they are the only route to information a node lacks; shared inputs add
nothing measurable. The validation-selected clinical organ model trails GRU-D;
CinC-2012 edge differences remain unestablished. These are neither equivalence
claims nor evidence of clinical benefit. Caps and cosine schedules vary jointly.

The 476-row clinical leaderboard covers 234 source identities. It retains its
CSV columns, record structure, schema version and metric; only the seed enum
expands to 0–9. Required seed sets depend on the selected-cap group. Four
historical GRU-D fits occur in two series but remain one fit each. The earlier
140-checkpoint archive covers only its original four-seed series.

## Reproduction

```bash
python3 -B tools/verify_release_1_3.py
python3 -B analysis/cap_selection/cap_reanalysis.py --check
python3 -B experiments/shared_input_primary/read_n2.py
python3 -B tools/cinc2012/shared_input/read_n3.py
python3 -B experiments/positive_control/read_e1b.py
python3 -B leaderboard/build_leaderboard.py --check
python3 -B -m unittest discover -s tests -p test_release_1_3.py -v
sha256sum -c SHA256SUMS
```

All commands above use saved records without importing PyTorch. They check
record completeness, public fingerprints, numerical validity, selection and
paired arithmetic. Original hashes identify historical inputs and are never
silently rewritten to fit new public bytes. The readers do not replay omitted
clinical error arrays or saved weights. Synthetic record validation checks
saved configuration, completion and metric algebra, without refitting.

`tools/make_figure_f5.py` and `tools/make_figure_f6.py` reproduce F5/F6 with
full-precision value ledgers and vector-PDF/font checks. They use NumPy,
Matplotlib and PyMuPDF; `requirements-figures.txt` declares this optional figure environment.
F5 is the original 35-epoch four-seed forest plot; F6 is the four-seed cap
sensitivity with A-validation-selected markers. They retain their scientific
meaning and do not depict the new ten-seed clinical summaries.

Training planners and smoke prerequisites are described in the affected
experiment READMEs. Clinical training needs rebuilt cohorts and source
checkpoints; the synthetic extension needs only the three shipped datasets.
The initial training selection and exact source hashes remain documented.
CPU model smoke validation requires PyTorch and is separate from this release's
data-free checks. The MIT license and approved author list are unchanged.
