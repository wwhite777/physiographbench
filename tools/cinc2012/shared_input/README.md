# Shared-input CinC-2012

This extension adds 8 within-corpus fits and 8 evaluations of selected 2019
checkpoints (two arms × seeds 0–3). Within-corpus uses set-a training/validation
and set-b test. Transfer uses the frozen 2019 normalization and reports set-a,
set-b and pooled observed-entry RMSE. Caps 105/70 and lr=0.001 come from the
2019 validation-selected shared-input family. They differ from the historical
partitioned protocol's cap 35 and lr=0.0005.

```bash
python3 -B tools/cinc2012/shared_input/read_n3.py
python3 -B tools/cinc2012/shared_input/read_n3.py --table
python3 -B tools/cinc2012/shared_input/host_driver_n3.py --dry-run
```

Within-corpus mean ± sample SD RMSE is none@105 0.8228 ± 0.0099 and
admissible@70 0.7919 ± 0.0243, versus GRU-D 0.7684. Admissible − none is
−0.0309 [−0.0685, +0.0066]. The organ model trails GRU-D in within-corpus
mean error; the edge contrast is not established, with wide intervals and high
seed variance. Transferred pooled RMSE is 0.8320/0.8336 versus GRU-D 0.8273;
admissible − none is +0.0016 [−0.0034, +0.0067]. Intervals are pointwise
paired t intervals over four seeds and do not establish equivalence.

Rebuild the two 2012 cohorts as in the parent README. For transfer, reproduce the
original 2019 shared-input budget checkpoints under
`experiments/shared_input_primary/runs/host/budget/ARM/epochsCAP/seedN/`.
`host_driver_n3.py --run --devices 0,1` executes the 16 jobs with one sequential
process lane per selected GPU. Its preflight checks both corpora, public source
hashes and all source checkpoints before creating outputs in
`runs/cinc2012_shared/`. Existing destinations are refused. CPU smokes are
explicit via `run_n3.py --max-stays 16 --epochs 1 --device cpu` for within-corpus;
transfer smoke retains the selected checkpoint cap and needs its checkpoint.

All 16 released records are `run.json` only under
`results/clinical_v4_v1/cinc2012/shared_input/`. The reader checks their distributed
bytes, identity, completion and metrics, then reconstructs summaries and paired
contrasts. The --table mode includes all historical models and the two new
shared-input models, including their per-organ summaries. It does not rederive omitted
per-stay errors or evaluate omitted weights.
