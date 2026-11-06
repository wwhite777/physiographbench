# Learned-graph validation and fixed-graph ablations

This folder contains a GraFITi PhysioNet-2012 reproduction attempt and fixed
physiological, random and complete graphs for GraFITi and t-PatchGNN on
CinC-2019. The published protocol, released-code choices and known differences
are documented in [PROTOCOL_GRAFITI_P12.md](PROTOCOL_GRAFITI_P12.md) and
[ABLATION_DESIGN.md](ABLATION_DESIGN.md).

From the repository root:

```bash
bash experiments/learned_graph_validation/run_host_e5.sh --dry-run
python3 -B experiments/learned_graph_validation/grafiti_p12_reproduce.py --dry-run
PHYSIOGRAPH_NO_TRAINING=1 python3 -B -m unittest discover -s experiments/learned_graph_validation/tests -v
```

These print **24 ablation commands + 1 reproduction command**. Prepare the
CinC-2019 cohort and the original PhysioNet-2012 archives at
`data/cinc2012/set-{a,b,c}.zip` using the top-level data instructions.
The P12 dry-run reports missing archives without opening or downloading them.
Use `run_host_e5.sh --run` for the ablations and `grafiti_p12_reproduce.py --run`
for the reproduction. Fresh outputs go under this folder's `runs/` directory.

P12 uses 37 time-series channels, 36 observed hours and the next three stored
steps. The single seed's test mean squared error (MSE) is **0.302702**, versus
the published **0.286 ± 0.001**; the absolute gap is **0.016702**. The published
spread is descriptive, and a one-seed attempt cannot reproduce its variability.
The saved original target placeholder is retained as historical metadata;
the protocol addendum and [E5_READING.md](artifacts/E5_READING.md) supply the target.

The fixed-graph experiment has 2 models × 3 graphs × 4 seeds = 24 saved JSON
records at 35 epochs. Its full per-organ results, learned-graph references,
paired contrasts and runtime qualifications are in
[e5_summary.json](artifacts/e5_summary.json). The learned GraFITi reference
A-test RMSE mean is **0.748258**. Checkpoints and inference recovery arrays
are excluded; the frozen aggregate values and recovery qualifications remain.
Set `PHYSIOGRAPH_NO_TRAINING=1` to skip the one optimizer-step test when checking
the rest of the suite without training.
