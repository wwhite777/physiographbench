# PhysioGraphBench v1.1.2 wording correction

Version 1.1.2 changes documentation only and is archived as
[10.5281/zenodo.23996559](https://doi.org/10.5281/zenodo.23996559). Code, results, tests, records and the
leaderboard are byte-identical to v1.1.1, and v1.1.1 preserves the v1.1.0 code
and results. The concept DOI is
[10.5281/zenodo.23976171](https://doi.org/10.5281/zenodo.23976171); the selected
per-seed checkpoints are in the separate record
[10.5281/zenodo.23993257](https://doi.org/10.5281/zenodo.23993257).

## What changed

Earlier text said that the remaining no-edge gap versus GRU-D at the 35-epoch
cap is "largely a training budget effect". The records do not support that
attribution. From the 35-epoch to the 70-epoch cap, the no-edge model improves
(A 0.7559 → 0.7496, B 0.8088 → 0.8070) while the same-cap GRU-D reference worsens
(A 0.7458 → 0.7489, B 0.8059 → 0.8096). On B the GRU-D change is the larger part
of the narrowing. The cap, the cosine learning-rate schedule and early stopping
change together, so the budget series is a sensitivity analysis of those
training choices, not an isolated attribution to training duration.

The README and the shared-input experiment README now state the two components
and this qualification. The values are the four-seed means of the released
records indexed in [the leaderboard](../leaderboard/LEADERBOARD.csv)
(series `shared_input_primary`, `clinical_selected` and `training_budget`).
The frozen reading [E2_E4_READING.md](../experiments/shared_input_primary/artifacts/host/E2_E4_READING.md)
keeps its original bytes.
