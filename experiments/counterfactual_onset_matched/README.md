# Counterfactual policies with matched intervention onset

Factual and alternative dose schedules begin at the same 72-minute onset.
The support-only family varies dose support while holding dependence fixed;
the dependence-only family varies severity/dose association while preserving
the dose multisets within severity terciles. A counterfactual recurrent network
(CRN) comparator uses the eventual assigned dose as its balancing target.

From the repository root:

```bash
bash experiments/counterfactual_onset_matched/run_host_e3.sh --dry-run
python3 -B -m pytest -p no:cacheprovider experiments/counterfactual_onset_matched/tests -q
python3 -B experiments/counterfactual_onset_matched/verify_policies.py --no-legacy --output-prefix experiments/counterfactual_onset_matched/runs/policy_statistics
```

The default core plan prints **184 commands: 160 main fits and 24 continuous-dose
CRN diagnostics**. Omit `--dry-run` to execute into a fresh `runs/host/` directory.
The additional `--group matched-control` plan prints four Control-GRU fits on
the identical randomized-dose archive used by the diagnostics. The released
records contain **188 runs: 160 main + 24 CRN + 4 matched controls**.

Each main family has five points, four models and four training/split seeds.
Models fit for 60 epochs; the CRN diagnostic sweeps λ = 0, 0.25, 1 at 60 and 120
epochs. Shared history and onset checks are independent of fitted scores.
Policy statistics for 50 and 400 patients are included under `artifacts/`.
The original legacy synthetic archives are not included; regenerate them using
the released simulator tools if the optional legacy policy inventory is needed.

Direction accuracy compares adjacent-dose effect signs. The main endpoint uses
21 post-onset samples, rather than pre-onset trivial equalities. In the matched
randomized-dose diagnostic there are **60,480 exact post-effect cells per seed**.
Control-GRU seed accuracies are **0.992063, 0.972073, 0.973644, 0.985136**;
all six CRN λ/budget arms have lower exact and tolerance post-effect accuracy
in all four seed pairs. This is a conditional synthetic benchmark result.

Read [DESIGN_E3.md](DESIGN_E3.md), [E3_READING.md](artifacts/host/E3_READING.md),
[E3_READING_ADDENDUM.md](artifacts/host/E3_READING_ADDENDUM.md) and the adjacent
summary JSON files for every run, paired interval, physical-unit error and
qualification. Three historical main-grid dataset paths had differing recorded
archive hashes. Their earlier arrays were unavailable; matching historical
arrays is not established. That provenance qualification is preserved.
No prediction archives or checkpoints are distributed.
