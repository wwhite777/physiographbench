# Validation-selected epoch caps

Run `python3 -B analysis/cap_selection/cap_reanalysis.py --check` from the root.
It recomputes all 36 family/cap/seed records and 51 paired contrasts, validates
stopping and the original configuration grid, and requires exact regenerated
JSON/Markdown bytes. Default mode rewrites only its two analysis outputs.

The rule minimizes mean A-validation RMSE across seeds 0–3, with exact ties
resolved toward the smaller cap. It selects none=105, admissible=70, GRU-D=35.
A/B test outcomes never enter the rule. These historical outcomes were already
available, so this does not establish prospective blinding. The ten-seed extension
holds these caps fixed. Cap and cosine schedule change jointly. The archived
four-seed analysis and full qualifications are in [CAP_REANALYSIS.md](CAP_REANALYSIS.md).
The public v4 selected records are addressed through JSON pointers into
`results/v4/tuning_grid.json`; no duplicate selected-run files are needed.
