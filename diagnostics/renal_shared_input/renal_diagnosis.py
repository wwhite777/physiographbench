#!/usr/bin/env python3
"""CPU checkpoint replay and renal error strata for frozen CinC-2019 A-test/B."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

from renal_protocol import (HERE, PROJECT, finite_float, make_data, persistence,
                            sha256, write_json)
from shared_input_variant import check_sources
import numpy as np
import torch
from organ_graph_ssm_model import build_model
from physiograph_training_runner import build_any

MODELS = ("persistence", "grud", "physiograph_gru", "physiograph")
STRATA = ("all", "0", "1–3", "≥4")
RENAL = slice(8, 11)
COHORT_SHA256 = "d52d8131323fc7a3838ae4fe523c2edbc02d2daa781de1859e7d184897dfb51f"


def stratum_masks(context_entries):
    return {"all": np.ones(len(context_entries), dtype=bool),
            "0": context_entries == 0,
            "1–3": (context_entries >= 1) & (context_entries <= 3),
            "≥4": context_entries >= 4}


@torch.no_grad()
def collect_renal(model, loader):
    if model is not None:
        model.eval()
    keys = ("stay_index", "context_entries", "last_hour_entries", "seen_variables",
            "renal_sse", "renal_count", "feature_sse", "feature_count")
    out = {k: [] for k in keys}
    for b in loader:
        if torch.any(b["values"][b["mask"] == 0] != 0):
            raise ValueError("frozen loader did not zero missing context values")
        pred = persistence(b, 12) if model is None else model(b, horizon=12)
        if not torch.isfinite(pred).all():
            raise ValueError("nonfinite predictions in checkpoint replay")
        m = b["target_mask"][:, :, RENAL]
        sq = (pred[:, :, RENAL] - b["target"][:, :, RENAL]).square() * m
        ctx = b["mask"][:, :, RENAL]
        tensors = dict(stay_index=b["stay_index"], context_entries=ctx.sum((1, 2)),
                       last_hour_entries=ctx[:, -1].sum(1),
                       seen_variables=(ctx.sum(1) > 0).sum(1),
                       renal_sse=sq.sum((1, 2)), renal_count=m.sum((1, 2)),
                       feature_sse=sq.sum(1), feature_count=m.sum(1))
        for k, v in tensors.items():
            out[k].append(v.cpu().numpy())
    return {k: np.concatenate(v) for k, v in out.items()}


def aggregate(errors):
    rows = {}
    for label, selected in stratum_masks(errors["context_entries"]).items():
        count = int(errors["renal_count"][selected].sum(dtype=np.float64))
        sse = float(errors["renal_sse"][selected].sum(dtype=np.float64))
        rows[label] = dict(n_stays=int(selected.sum()),
                           n_with_renal_targets=int((errors["renal_count"][selected] > 0).sum()),
                           n_without_renal_targets=int((errors["renal_count"][selected] == 0).sum()),
                           renal_target_entries=count, renal_sse=sse,
                           RMSE=finite_float(np.sqrt(sse / count)) if count else None,
                           context_entries=int(errors["context_entries"][selected].sum()),
                           possible_context_entries=int(selected.sum()) * 12 * 3,
                           final_hour_renal_entries=int(errors["last_hour_entries"][selected].sum()))
        rows[label]["features"] = {}
        for i, feature in enumerate(("Creatinine", "BUN", "Potassium")):
            n = int(errors["feature_count"][selected, i].sum(dtype=np.float64))
            ss = float(errors["feature_sse"][selected, i].sum(dtype=np.float64))
            rows[label]["features"][feature] = dict(target_entries=n, sse=ss,
                RMSE=finite_float(np.sqrt(ss / n)) if n else None)
    return rows


def load_checkpoint(model_name, seed, selected_root, data_meta):
    directory = selected_root / model_name / f"seed{seed}"
    run_file, checkpoint = directory / "run.json", directory / "checkpoint.pt"
    run = json.loads(run_file.read_text())
    if run["status"] != "complete" or run["scope"] != "full":
        raise ValueError(f"not a complete full run: {run_file}")
    if sha256(checkpoint) != run["checkpoint_sha256"]:
        raise ValueError(f"checkpoint hash differs: {checkpoint}")
    saved = torch.load(checkpoint, map_location="cpu", weights_only=True)
    for key, expected in (("model", model_name), ("seed", seed), ("C", 12), ("K", 12),
                          ("variant", "admissible"), ("cohort_sha256", COHORT_SHA256)):
        if saved[key] != expected:
            raise ValueError(f"checkpoint identity differs in {key}: {checkpoint}")
    if run["data"]["split_stay_indices"] != data_meta["split_stay_indices"]:
        raise ValueError(f"split membership differs: {run_file}")
    for name in ("organ_graph_ssm_model.py", "physiograph_data_loader.py",
                 "physiograph_training_runner.py", "clinical_timeseries_baselines.py"):
        entry = json.loads((PROJECT / "manifests/distribution.json").read_text())["src/" + name]
        expected = run["source_sha256"][name]
        current = sha256(PROJECT / "src" / name)
        if current != entry["distributed_sha256"] or expected not in (current, entry["original_sha256"]):
            raise ValueError(f"source differs from checkpoint: {name}")
    sizes = saved["sizes"]
    if sizes != run["sizes"]:
        raise ValueError("run/checkpoint sizes differ")
    if model_name.startswith("physiograph"):
        model = build_model("cinc", d_model=sizes["d_model"], d_state=sizes["d_state"],
                             n_layers=sizes["n_layers"], edges="admissible",
                             node_type="gru" if model_name.endswith("_gru") else "ssm")
    else:
        model = build_any(model_name, 5, **sizes)
    model.load_state_dict(saved["state_dict"], strict=True)
    provenance = dict(run=str(run_file.resolve().relative_to(PROJECT)), run_sha256=sha256(run_file),
                      checkpoint=str(checkpoint.resolve().relative_to(PROJECT)), checkpoint_sha256=sha256(checkpoint),
                      sizes=sizes, lr=run["lr"], width=run["width"], variant=saved["variant"])
    return model, run, provenance


def summarize_seed_rows(rows):
    # Denominators are one common cohort, never multiplied by the seed count.
    first = rows[0]
    for row in rows[1:]:
        for key in ("n_stays", "n_with_renal_targets", "n_without_renal_targets",
                    "renal_target_entries", "context_entries", "possible_context_entries"):
            if row[key] != first[key]:
                raise ValueError(f"seed denominator differs in {key}")
    values = [r["RMSE"] for r in rows if r["RMSE"] is not None]
    return {**{k: first[k] for k in ("n_stays", "n_with_renal_targets", "n_without_renal_targets",
                                    "renal_target_entries", "context_entries", "possible_context_entries")},
            "n_seeds": len(rows), "n_finite_seeds": len(values),
            "mean_RMSE": float(np.mean(values)) if values else None,
            "sd_RMSE": float(np.std(values, ddof=1)) if len(values) > 1 else None,
            "mean_sse": float(np.mean([r["renal_sse"] for r in rows]))}


def excess_decomposition(summary, split, model, reference):
    cells = summary[split]
    total_count = cells[model]["all"]["renal_target_entries"]
    total_excess = cells[model]["all"]["mean_sse"] - cells[reference]["all"]["mean_sse"]
    result = {}
    for label in STRATA[1:]:
        delta = cells[model][label]["mean_sse"] - cells[reference][label]["mean_sse"]
        result[label] = dict(excess_sse=delta,
            contribution_to_overall_MSE_difference=delta / total_count,
            fraction_of_total_signed_excess=delta / total_excess if total_excess else None)
    return result


CODE_PATH = """## Frozen code-path reading

All source paths are relative to the repository root. The source hashes
are checked before replay. These observations apply to the implementation being
evaluated, not to every possible organ-graph architecture.

- **Correct renal indexing and output width.** The CinC configuration is
  `(4, 4, 3, 5)` (`src/organ_graph_ssm_model.py:321–325`). Cumulative slices are
  built at `src/organ_graph_ssm_model.py:189–192`; the cohort identifies columns
  8–10 as Creatinine, BUN and Potassium. Input and output ordering agree.
- **Values and masks, with static information.** Normalization uses A-train mean
  and standard deviation and remasks missing values to zero
  (`src/physiograph_data_loader.py:25–41`). The context projection consumes
  `2*d + n_static + n_control` channels
  (`src/organ_graph_ssm_model.py:193–196`). Its renal width is 3 values + 3 masks +
  5 static features = 11; the learned projection maps this to `d_model`.
  `_organ_inputs` selects only that organ's values and masks and appends static
  features (`src/organ_graph_ssm_model.py:209–221`). Thus an empty renal context
  has zero renal values and masks, **but still has static features and learned
  projection biases**, and can receive messages. It is not an entirely zero node.
- **No explicit elapsed-time channel.** The loader returns values, masks, static
  data and targets (`src/physiograph_data_loader.py:33–44`); the organ model never
  constructs a time-since-last-observation variable. Recurrence can learn mask
  history, but this is not an explicit decay input. In contrast, GRU-D constructs
  `delta`, decays inputs/hidden states, and retains last observations inside its
  encoder (`src/clinical_timeseries_baselines.py:79–94`).
- **Cross-organ information is restricted to messages in the frozen model.**
  Separate organ encoders run before coupling
  (`src/organ_graph_ssm_model.py:223–242`). Gated source-to-target messages are
  added to each target's state (`src/organ_graph_ssm_model.py:168–182`); the
  admissible direct renal incoming edge is cardiovascular→renal
  (`src/organ_graph_ssm_model.py:31–40`). Indirect paths can act across layers or
  forecast steps. Output heads map each organ state only to its own variables
  (`src/organ_graph_ssm_model.py:203–206,274–277`), with no concatenated global
  hidden state or direct nonrenal input to the renal decoder.
- **Forecast boundary behavior is a plausible general limitation.** The initial
  feedback is the final context row, not the last observed value per variable
  (`src/organ_graph_ssm_model.py:249–251`). A missing final-hour renal value is
  consequently zero. The first forecast input marks all feedback entries as one
  (`src/organ_graph_ssm_model.py:260–265`), just as later predicted inputs are
  marked one. The encoded context still carries its true masks, but the forecast
  input does not distinguish this initial missing zero from an observed mean.
  This affects every organ and is not evidence of a renal indexing bug. Plain
  GRU and GRU-D also initialize their autoregressive decoder from the final
  remasked row (`src/clinical_timeseries_baselines.py:58–61,94`); persistence
  explicitly retains last observed values
  (`tools/v4_protocol.py:162–166`).
  Both control modes preserve
  this boundary rule rather than confounding input scope with an imputation fix.
- **Messages update outputs, not recurrent cells in place.** Stored context
  recurrent states precede coupling (`src/organ_graph_ssm_model.py:233–242`);
  rollout takes these states and re-applies messages at every future step
  (`src/organ_graph_ssm_model.py:249,266–273`). Lower-layer context messages can
  enter the next layer; the final coupled context output is not itself used as
  a recurrent state. This is shared architectural behavior, not a renal-only
  branch. It remains unchanged in the controls.

## Minimal host control and interpretation limits

`shared_input_variant.py` registers `physiograph_gru_factorised_partitioned` and
`physiograph_gru_factorised_shared`. Both have **no edges**, four organ heads and
the selected PhysioGraph-GRU configuration: learning rate 0.0005, `large`,
`d_model=96`, `d_state=48`, two layers, dropout 0.1. Context C=12, horizon K=12,
seeds 0–3. Each fit retains the clinical_protocol 35-epoch cap, patience 8, validation-selected
checkpoint, Adam/weight decay, cosine scheduler and gradient clipping. No mode is
retuned and no test score selects a configuration.

In partitioned mode the dynamic value widths are 4/4/3/5; in shared mode every
organ receives all 16 values and their 16 masks. The actual preprojection widths
including masks and static features are 13/13/11/15 versus 37/37/37/37; recurrent
cell inputs remain `d_model=96`. Both context and forecast-step inputs are widened.
There are no graph messages, but shared forecast feedback carries all organs'
previous predictions, so shared-input does not imply independent forecast
trajectories. Static inputs, output heads and all boundary/mask rules are kept.
The widened projections add parameters; this is a structural input-access
control, not a parameter-matched or elapsed-time control. Common recurrent/head
initial weights are identical for paired seeds, with fresh widened projections.

`bash diagnostics/renal_shared_input/run.sh --device cuda` enumerates the eight
full fits. CPU tests check inference and protocol agreement without training.
The completed archived fits are interpreted in
`diagnostics/renal_shared_input/SHARED_INPUT_READING.md`.
An improvement would support a role for access to cross-organ input, subject to
the changed projection capacity; it would not establish that partitioning is the
sole cause. A lack of improvement would leave optimization, rollout boundary
behavior and missingness representation as unresolved alternatives. The saved
admissible-edge runs and this no-edge control answer different comparisons.

CinC-2012's within-corpus table reports PhysioGraph-GRU 0.823867 ± 0.015241 and
SSM seeds near 0.82–0.83 and 0.89. Its renal standard deviations are much smaller
(GRU 0.001175, SSM 0.002474), while other organs vary more
(`results/clinical_v4_v1/cinc2012/TABLE_CINC2012.md`,
“Within” tables). This CinC-2019 replay does not diagnose or resolve the separate
CinC-2012 seed behavior; inferring a common renal mechanism would exceed the data.
"""


def fmt(value, digits=6):
    return "NA" if value is None else f"{value:.{digits}f}"


def write_report(result, output_dir):
    summary = result["summary"]
    lines = ["# renal_diagnostic renal checkpoint diagnosis", "",
             "## Decision evidence", "",
             "Checkpoint replay reproduces the frozen pooled renal errors within the stated "
             "CPU tolerance. No renal-specific indexing or omitted-mask defect was found in "
             "the traced path. Input restriction and forecast-boundary handling are concrete "
             "mechanistic limitations; causal attribution awaits the eight full host controls.", ""]
    for split in ("A", "B"):
        s = summary[split]["persistence"]["all"]
        rate = s["context_entries"] / s["possible_context_entries"]
        lines.append(f"{split}: {s['context_entries']:,}/{s['possible_context_entries']:,} renal context "
                     f"entries observed ({100*rate:.2f}%); {s['n_stays']:,} eligible stays, "
                     f"{s['n_with_renal_targets']:,} with renal targets, "
                     f"{s['renal_target_entries']:,} observed renal target entries.")
    lines += ["", "For hospital B, the signed excess squared-error decomposition relative to "
              "persistence assigns the following fractions to stays with zero renal context entries "
              "(a negative fraction means that group offsets excess elsewhere):"]
    for model in MODELS[2:]:
        d = result["excess_decomposition"]["B"][model]["persistence"]["0"]
        share = d["fraction_of_total_signed_excess"]
        lines.append(f"- {model}: {100*share:.2f}% of total signed excess SSE "
                     f"({d['excess_sse']:+.3f}); "
                     f"{d['contribution_to_overall_MSE_difference']:+.6f} in overall MSE units.")
    lines += ["", "These fractions decompose squared error, not RMSE. They describe the evaluated "
              "stays and do not identify a causal effect of missingness. The hypothesis that "
              "stays with no observed renal context principally drive the excess is therefore "
              "unsupported: nearly all excess occurs in stays with at least one observed renal "
              "entry. This does not establish whether the models underuse those observations "
              "because of input partitioning, rollout handling, or optimization.", "",
              "## Estimand and denominators", "",
              "One deterministic window per stay: the first 12 context hours forecast the next 12 "
              "hours. A denotes A-test; B denotes the external hospital. Renal variables are "
              "Creatinine, BUN and Potassium (columns 8–10). Observed context entries count all "
              "ones across the 12×3 renal context mask; bins are 0, 1–3 and ≥4, chosen before replay. "
              "Every eligible stay appears in one bin, including stays with no renal targets.", "",
              "RMSE@12 = sqrt(sum of squared normalized errors / observed renal target entries), "
              "pooled over stays, hours and the three variables within each bin. Units are A-train "
              "standard deviations. Predictions/error arithmetic and within-stay reduction use "
              "float32 as in clinical_protocol; sums across stays use float64. The table gives the mean and "
              "sample SD of four checkpoint-specific pooled RMSEs, not mean stay RMSE. Persistence "
              "is one deterministic calculation, not four independent seeds. Denominators are "
              "shared across seeds and models and are never multiplied by four. An empty target "
              "denominator is NA, never zero error.", "",
              "## Stratified renal table", "",
              "| Split | Model | Context entries | Seeds | Stays | Stays with renal targets | Stays without renal targets | Renal target entries | RMSE mean ± sample SD |",
              "|---|---|---|---:|---:|---:|---:|---:|---:|"]
    for split in ("A", "B"):
        for model in MODELS:
            for label in STRATA:
                cell = summary[split][model][label]
                score = fmt(cell["mean_RMSE"])
                if cell["sd_RMSE"] is not None:
                    score += " ± " + fmt(cell["sd_RMSE"])
                lines.append(f"| {split} | {model} | {label} | {cell['n_seeds']} | "
                             f"{cell['n_stays']} | {cell['n_with_renal_targets']} | "
                             f"{cell['n_without_renal_targets']} | {cell['renal_target_entries']} | {score} |")
    lines += ["", "## Renal deficit relative to frozen references", "",
              "Differences below subtract the comparator's mean pooled RMSE from the model's "
              "mean pooled RMSE. References come from `selected_seed_summary` in "
              "`per_organ_v4.json`; CPU replay is verified against every individual seed.", "",
              "| Split | Model | Renal RMSE | Minus persistence | Minus GRU-D |",
              "|---|---|---:|---:|---:|"]
    for split in ("A", "B"):
        for model in MODELS[2:]:
            r = result["reference_deficits"][split][model]
            lines.append(f"| {split} | {model} | {r['model_mean']:.6f} | "
                         f"{r['minus_persistence']:+.6f} | {r['minus_grud']:+.6f} |")
    lines += ["", "## Where the excess squared error occurs", "",
              "SSE is the sum of squared errors. Model SSE is averaged over seeds before "
              "subtracting the comparator. The MSE contribution divides each bin's signed excess "
              "SSE by the **overall** renal target denominator; contributions add to the overall "
              "MSE difference. Fractions can be negative or exceed 100% when bins offset each other.", "",
              "| Split | Model | Comparator | Context entries | Excess SSE | Contribution to overall MSE difference | Fraction of signed total excess |",
              "|---|---|---|---|---:|---:|---:|"]
    for split in ("A", "B"):
        for model in MODELS[2:]:
            for reference in ("persistence", "grud"):
                for label, d in result["excess_decomposition"][split][model][reference].items():
                    fraction = d["fraction_of_total_signed_excess"]
                    lines.append(f"| {split} | {model} | {reference} | {label} | "
                                 f"{d['excess_sse']:+.3f} | {d['contribution_to_overall_MSE_difference']:+.6f} | "
                                 f"{100*fraction:+.2f}% |")
    lines += ["", "## Replay reconciliation", "",
              f"Maximum absolute difference from a frozen per-seed renal RMSE: "
              f"{result['max_reference_RMSE_difference']:.3g}; required tolerance "
              f"{result['replay_tolerance']:.1g}. Checkpoint SHA256, recorded source hashes, model/seed "
              "identity, cohort SHA256 and every split's stay membership were checked. "
              "Per-stay replay errors are saved in `artifacts/diagnosis/`; full per-seed strata, "
              "feature summaries and provenance are in `renal_diagnosis.json`.", "", CODE_PATH]
    (output_dir / "RENAL_DIAGNOSIS.md").write_text("\n".join(lines) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--npz", type=Path, default=PROJECT / "data/cinc2019_cohort.npz")
    ap.add_argument("--selected-root", type=Path, default=PROJECT / "runs/clinical/selected")
    ap.add_argument("--reference", type=Path, default=PROJECT / "results/v4/per_organ_v4.json")
    ap.add_argument("--output-dir", type=Path, default=PROJECT / "runs/renal_shared_input_diagnosis")
    ap.add_argument("--batch", type=int, default=128)
    ap.add_argument("--threads", type=int, default=2)
    args = ap.parse_args(argv)
    output_dir = args.output_dir.resolve()
    if not output_dir.is_relative_to(PROJECT):
        ap.error("output must stay inside the repository")
    output_dir.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(args.threads)
    check_sources()
    started = time.monotonic()
    loaders, meta = make_data(args.npz, C=12, K=12, batch=args.batch)
    if meta["cohort_sha256"] != COHORT_SHA256:
        raise ValueError("cohort differs from frozen input")
    if meta["features"][8:11] != ["Creatinine", "BUN", "Potassium"]:
        raise ValueError("renal feature order differs")
    reference = json.loads(args.reference.read_text())
    expected = reference["selected_seed_summary"]
    result = dict(diagnostic="renal_shared_input", schema_version=1,
                  device="cpu", C=12, K=12, data=meta, seeds=[0, 1, 2, 3],
                  reference=str(args.reference.resolve().relative_to(PROJECT)), reference_sha256=sha256(args.reference),
                  per_seed={s: {m: {} for m in MODELS} for s in ("A", "B")},
                  provenance={}, replay_tolerance=1e-5)
    max_diff = 0.0
    for name in MODELS:
        for seed in ([0] if name == "persistence" else range(4)):
            if name == "persistence":
                model, run = None, None
            else:
                model, run, provenance = load_checkpoint(name, seed, args.selected_root, meta)
                result["provenance"][f"{name}/seed{seed}"] = provenance
            for split, loader in zip(("A", "B"), loaders[2:]):
                errors = collect_renal(model, loader)
                rows = aggregate(errors)
                target_count = reference["table"]["seed0"]["persistence"]["splits"][split]["organs"]["renal"]["observed_entries"]
                if rows["all"]["renal_target_entries"] != target_count:
                    raise ValueError("frozen renal target denominator differs")
                exp = expected[name][split]["renal"]["per_seed"][f"seed{seed}"]
                delta = abs(rows["all"]["RMSE"] - exp)
                max_diff = max(max_diff, delta)
                if delta > result["replay_tolerance"]:
                    raise ValueError(f"replay RMSE mismatch: {name} seed{seed} {split}: {delta}")
                if run is not None:
                    if abs(rows["all"]["RMSE"] - run[split]["organs"]["renal"]["RMSE"]) > result["replay_tolerance"]:
                        raise ValueError("run.json per-organ RMSE differs")
                    with np.load(args.selected_root / name / f"seed{seed}" / f"errors_{split}.npz") as saved:
                        if not np.array_equal(saved["stay_index"], errors["stay_index"]):
                            raise ValueError("saved error stay order differs")
                        if not np.array_equal(saved["organ_count"][:, 2], errors["renal_count"]):
                            raise ValueError("saved per-stay target counts differ")
                        rows["all"]["max_abs_saved_stay_sse_difference"] = float(np.max(
                            np.abs(saved["organ_sse"][:, 2] - errors["renal_sse"])))
                result["per_seed"][split][name][str(seed)] = rows
                dest = output_dir / "artifacts/diagnosis" / name / f"seed{seed}"
                dest.mkdir(parents=True, exist_ok=True)
                np.savez_compressed(dest / f"renal_errors_{split}.npz", **errors)
                print(f"{name} seed{seed} {split}: renal={rows['all']['RMSE']:.9f}; "
                      f"reference difference={delta:.3g}", flush=True)
    result["summary"] = {s: {m: {label: summarize_seed_rows([r[label] for r in seeds.values()])
                               for label in STRATA}
                              for m, seeds in models.items()}
                         for s, models in result["per_seed"].items()}
    result["reference_deficits"] = {s: {m: dict(
        model_mean=expected[m][s]["renal"]["mean"],
        minus_persistence=expected[m][s]["renal"]["mean"] - expected["persistence"][s]["renal"]["mean"],
        minus_grud=expected[m][s]["renal"]["mean"] - expected["grud"][s]["renal"]["mean"])
        for m in MODELS[2:]} for s in ("A", "B")}
    result["excess_decomposition"] = {s: {m: {ref: excess_decomposition(result["summary"], s, m, ref)
        for ref in ("persistence", "grud")} for m in MODELS[2:]} for s in ("A", "B")}
    result["max_reference_RMSE_difference"] = max_diff
    result["seconds"] = time.monotonic() - started
    result["source_sha256"] = {p.name: sha256(p) for p in (
        PROJECT / "src/organ_graph_ssm_model.py", PROJECT / "src/physiograph_data_loader.py",
        PROJECT / "src/physiograph_training_runner.py", HERE / "renal_diagnosis.py", HERE / "renal_protocol.py")}
    write_json(output_dir / "renal_diagnosis.json", result)
    write_report(result, output_dir)
    print(f"Wrote {output_dir / 'RENAL_DIAGNOSIS.md'} in {result['seconds']:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
