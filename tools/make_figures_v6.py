#!/usr/bin/env python3
"""Build F5/F6 from hash-verified immutable JSON, with replayable provenance.

Run with the card's Python interpreter and -B. Use --out-dir to select a generated-output folder.
No training modules, network calls, input copies, or external commands are used.
"""
from pathlib import Path
import datetime as dt
import hashlib
import json
import os
import site
import sys

HERE = Path(__file__).absolute().parent
sys.path.insert(0, os.environ.get('PHYSIOGRAPH_ROOT', str(HERE.parent)))
from release_paths import ROOT, SCRATCH
from release_records import read as public_read
os.environ.setdefault('MPLCONFIGDIR', str(SCRATCH / 'mpl'))
sys.dont_write_bytecode = True
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.text import Text
import numpy as np

# This is the same already-installed PDF reader used by the v5 figure script.
sys.path.append(site.getusersitepackages())
import fitz

SOURCES = {
    'summary': Path('experiments/shared_input_primary/artifacts/host/e2_e4_summary.json'),
    'paired': Path('analysis/paired_statistics/paired_stats_v5.json'),
    'caps': Path('analysis/cap_selection/cap_reanalysis.json'),
}
DISTRIBUTION = public_read('manifests/distribution.json')
PINNED = {name: DISTRIBUTION[str(path)]['distributed_sha256'] for name,path in SOURCES.items()}
OUT = ROOT / 'runs/figures_v6'

def canonical(path):
    path = str(path)
    file, separator, fragment = path.partition('#')
    if Path(file).is_absolute(): file = str(Path(file).relative_to(ROOT)) if Path(file).is_relative_to(ROOT) else file.lstrip('/')
    return file + (separator + fragment if separator else '')

def distributed_hash(location, historical):
    key = canonical(location).partition('#')[0]
    item = DISTRIBUTION[key]
    if historical not in (item.get('original_sha256'), item['distributed_sha256']):
        raise ValueError(f'Unrecognized historical fingerprint: {key}')
    return item['distributed_sha256']

COLORS = ["#0072B2", "#D55E00", "#009E73"]
WIDTH = 3.33
ARM_LABELS = [
    ("admissible", "Admissible"),
    ("dense", "Dense"),
    ("reversed", "Reversed"),
    ("random_s0", "Random draw 1"),
    ("random_s1", "Random draw 2"),
    ("random_s2", "Random draw 3"),
    ("misspecified-1", "Misspecified"),
    ("none_norm", "No edges\n(normalised)"),
    ("none_pmatch", "No edges\n(parameter-matched)"),
]
FAMILIES = [("none", "Shared no edges"),
            ("admissible", "Shared admissible"), ("grud", "GRU-D")]

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 7,
    "axes.titlesize": 8, "axes.labelsize": 7,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7,
    "pdf.fonttype": 42, "ps.fonttype": 42,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.linewidth": 0.6, "lines.linewidth": 1.0,
    "xtick.major.width": 0.6, "ytick.major.width": 0.6,
})


def sha(path):
    return hashlib.sha256((ROOT / str(path).partition('#')[0]).read_bytes()).hexdigest()


def pointer(data, field):
    for part in field.lstrip("/").split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        data = data[int(part)] if isinstance(data, list) else data[part]
    return data


class Inputs:
    def __init__(self):
        self.data = {}
        self.hashes = {}
        for name, path in SOURCES.items():
            self.read(path, PINNED[name])
        self.e2 = self.data[str(SOURCES["summary"])]
        self.caps = self.data[str(SOURCES["caps"])]
        self.paired = self.data[str(SOURCES["paired"])]
        self.expected = {canonical(s["file"]): distributed_hash(s["file"], s["sha256"])
                         for s in self.e2["sources"].values() if canonical(s["file"]).partition("#")[0] in DISTRIBUTION}
        for s in self.caps["source_catalog"]:
            path, digest = s["source_file"], s["sha256"]
            assert path not in self.expected or self.expected[path] == digest
            self.expected[path] = digest

    def read(self, path, expected=None):
        path = canonical(path)
        if path not in self.data:
            digest = sha(path)
            assert expected is not None, ("Unpinned input", path)
            assert digest == expected, ("Input hash mismatch", path)
            self.hashes[path] = digest
            self.data[path] = public_read(path)
        if expected is not None:
            assert self.hashes[path] == expected
        return self.data[path]

    def raw(self, path):
        return self.read(path, self.expected[canonical(path)])


def calculate(operation, args):
    if operation == "subtract":
        return args[0] - args[1]
    if operation == "mean":
        return float(np.mean(np.asarray(args, dtype=float)))
    if operation == "sample_sd":
        return float(np.std(np.asarray(args, dtype=float), ddof=1))
    if operation == "t_half_width":
        sd, critical_t, n = args
        return float(critical_t * sd / np.sqrt(n))
    if operation == "lower_bound":
        return args[0] - args[1]
    if operation == "upper_bound":
        return args[0] + args[1]
    if operation == "negative":
        return -args[0]
    if operation == "multiply":
        return args[0] * args[1]
    raise ValueError(operation)


class Ledger:
    """Every data coordinate is a source field or an explicit arithmetic node."""
    def __init__(self, inputs):
        self.inputs = inputs
        self.nodes = {}
        self.lookup = {}
        self.equalities = []

    def source(self, path, field):
        path = canonical(path)
        key = (path, field)
        if key not in self.lookup:
            self.inputs.raw(path) if path not in self.inputs.data else None
            name = f"v{len(self.nodes) + 1:04d}"
            self.nodes[name] = {
                "value": pointer(self.inputs.data[path], field),
                "source_file": path, "source_field": field,
                "source_sha256": self.inputs.hashes[path],
            }
            self.lookup[key] = name
        return self.lookup[key]

    def derived(self, operation, *ids):
        name = f"v{len(self.nodes) + 1:04d}"
        self.nodes[name] = {"value": calculate(operation, [self.value(i) for i in ids]),
                            "operation": operation, "inputs": list(ids)}
        return name

    def value(self, name):
        return self.nodes[name]["value"]

    def same(self, left, right, reason):
        assert self.value(left) == self.value(right), (reason, self.value(left), self.value(right))
        self.equalities.append({"left": left, "right": right, "reason": reason,
                                "comparison": "exact equality; no rounding or tolerance"})

    def interval(self, mean, sd, n, t):
        half = self.derived("t_half_width", sd, t, n)
        return [self.derived("lower_bound", mean, half),
                self.derived("upper_bound", mean, half)]


def common(ledger):
    return (ledger.source(SOURCES["caps"], "/power_designs/4/n_pairs"),
            ledger.source(SOURCES["caps"], "/power_designs/4/critical_t"))


def forest_data(inputs):
    ledger = Ledger(inputs)
    n, t = common(ledger)
    primary_cap = ledger.source(SOURCES["summary"], "/selection/record/epochs_budget")
    panels = []
    for split in ["A", "B"]:
        rows = []
        for arm, label in ARM_LABELS:
            pairs, deltas = [], []
            for seed in inputs.caps["definitions"]["seeds"]:
                values = []
                for name in [arm, "none"]:
                    candidates = [r for r in inputs.e2["arm_rows"]
                                  if r["arm"] == name and r["seed"] == seed]
                    assert len(candidates) == 1
                    path = ROOT / candidates[0]["source"]
                    run = inputs.raw(path)
                    assert run["seed"] == seed and run["input_mode"] == "shared"
                    assert run["status"] == "complete" and run["failure"] is None
                    ledger.same(ledger.source(path, "/epochs_budget"), primary_cap,
                                "All forest arms use the primary 35-epoch cap")
                    values.append(ledger.source(path, f"/{split}/pooled_masked_RMSE"))
                delta = ledger.derived("subtract", *values)
                deltas.append(delta)
                pairs.append({"seed": seed, "arm_value_id": values[0],
                              "reference_value_id": values[1], "difference_value_id": delta})
            mean = ledger.derived("mean", *deltas)
            sd = ledger.derived("sample_sd", *deltas)
            ci = ledger.interval(mean, sd, n, t)
            # historical-experiment aggregate fields are rounded; never use them as plot inputs.
            saved = [r for r in inputs.e2["arm_paired_differences"]
                     if r["target"] == arm and r["reference"] == "none"
                     and r["organ"] is None and r["split"] == {"A": "A_test", "B": "B"}[split]]
            assert len(saved) == 1
            for field, value in [("mean", ledger.value(mean)),
                                 ("ci95_low", ledger.value(ci[0])),
                                 ("ci95_high", ledger.value(ci[1]))]:
                assert abs(saved[0][field] - value) <= 0.5 * 10 ** -inputs.e2["reporting"]["decimals"]
            rows.append({"arm": arm, "label": label, "mean": ledger.value(mean),
                         "ci95": [ledger.value(i) for i in ci],
                         "value_ids": {"mean": mean, "ci95_low": ci[0], "ci95_high": ci[1]},
                         "seed_pairs": pairs})
        matches = [(i, c) for i, c in enumerate(inputs.caps["paired_contrasts"])
                   if c["contrast"] == "admissible@35 minus none@35" and c["metric"] == split]
        assert len(matches) == 1
        index, contrast = matches[0]
        prefix = f"/paired_contrasts/{index}"
        for key, suffix in [("mean", "/mean_difference"), ("ci95_low", "/ci95_paired_t/0"),
                            ("ci95_high", "/ci95_paired_t/1")]:
            ledger.same(rows[0]["value_ids"][key], ledger.source(SOURCES["caps"], prefix + suffix),
                        "historical-experiment admissible contrast matches full-precision historical-experiment field")
        mdd = ledger.source(SOURCES["caps"], prefix + "/mdd_80pct_alpha05_n4")
        lower = ledger.derived("negative", mdd)
        multiplier = ledger.source(SOURCES["paired"], "/methods/mdd_multiplier")
        sd = ledger.source(SOURCES["caps"], prefix + "/paired_sd_sample")
        ledger.same(mdd, ledger.derived("multiply", multiplier, sd),
                    "historical-experiment planning multiplier applied to current historical-experiment paired SD")
        zero = ledger.derived("subtract", mdd, mdd)
        panels.append({"cohort": split, "rows": rows, "mdd": ledger.value(mdd),
                       "mdd_band": [ledger.value(lower), ledger.value(mdd)],
                       "mdd_value_ids": [lower, mdd], "zero": ledger.value(zero),
                       "zero_value_id": zero})
    caption = (
        "Shared-input edge arms at the 35-epoch configuration. Points show each arm minus "
        "the raw no-edges reference in pooled observed-entry root mean squared error (RMSE) "
        "at the 12-hour horizon, in cohort-A training standard-deviation units; negative is better. "
        "Whiskers are pointwise 95% paired Student t intervals over four matched training seeds "
        "(3 degrees of freedom). Shading is plus/minus the admissible-minus-none minimum detectable "
        "difference (MDD), using exact two-sided noncentral-t inversion at 80% power and alpha=0.05 "
        "with the observed four-pair standard deviation. MDD is a planning sensitivity estimate, "
        "not an equivalence margin. Intervals describe training-seed variation conditional on the "
        "fixed cohorts, do not estimate patient or hospital sampling uncertainty, and are unadjusted "
        "for multiple contrasts. Raw no edges bypasses coupling normalisation; the normalised and "
        "parameter-matched no-edges controls change different aspects of the model. Random draws "
        "1-3 map to random_s0, random_s1 and random_s2; Misspecified maps to misspecified-1."
    )
    return ledger, {"figure": "F5_forest_arms", "caption": caption, "panels": panels,
                    "configuration_cap": ledger.value(primary_cap),
                    "configuration_cap_value_id": primary_cap,
                    "x_label": "arm minus no edges (pooled RMSE); negative is better"}


def cap_data(inputs):
    ledger = Ledger(inputs)
    n, t = common(ledger)
    panels = []
    for split in ["A", "B"]:
        series = []
        for family, label in FAMILIES:
            points = []
            for index, summary in enumerate(inputs.caps["family_cap_summaries"]):
                if summary["family"] != family:
                    continue
                prefix = f"/family_cap_summaries/{index}"
                cap = ledger.source(SOURCES["caps"], prefix + "/cap")
                mean = ledger.source(SOURCES["caps"], prefix + f"/metrics/{split}/mean")
                sd = ledger.source(SOURCES["caps"], prefix + f"/metrics/{split}/sample_sd")
                samples = []
                run_rows = [(i, r) for i, r in enumerate(inputs.caps["run_records"])
                            if r["family"] == family and r["cap"] == summary["cap"]]
                assert [r["seed"] for _, r in run_rows] == inputs.caps["definitions"]["seeds"]
                for ri, run in run_rows:
                    record = run["metrics"][split]
                    value = ledger.source(record["source_file"], record["source_field"])
                    saved = ledger.source(SOURCES["caps"], f"/run_records/{ri}/metrics/{split}/value")
                    ledger.same(value, saved, "historical-experiment metric equals raw run field at full precision")
                    ledger.same(ledger.source(record["source_file"], "/epochs_budget"), cap,
                                "Plotted cap equals the original run budget")
                    samples.append(value)
                ledger.same(mean, ledger.derived("mean", *samples),
                            "historical-experiment mean recomputed from all four original run fields")
                ledger.same(sd, ledger.derived("sample_sd", *samples),
                            "historical-experiment sample SD recomputed from all four original run fields")
                ci = ledger.interval(mean, sd, n, t)
                points.append({"cap": ledger.value(cap), "mean": ledger.value(mean),
                               "ci95": [ledger.value(i) for i in ci],
                               "value_ids": {"cap": cap, "mean": mean,
                                             "ci95_low": ci[0], "ci95_high": ci[1]},
                               "run_metric_value_ids": samples})
            points.sort(key=lambda p: p["cap"])
            assert [p["cap"] for p in points] == inputs.caps["definitions"]["caps"]
            selection_index, selection = next((i, r) for i, r in enumerate(inputs.caps["cap_selection"])
                                               if r["family"] == family)
            candidates = []
            for ci, candidate in enumerate(selection["candidates"]):
                vals = [ledger.source(r["source_file"], r["source_field"])
                        for r in candidate["derived_from"]]
                candidate_mean = ledger.source(SOURCES["caps"],
                    f"/cap_selection/{selection_index}/candidates/{ci}/mean_A_validation_RMSE")
                ledger.same(candidate_mean, ledger.derived("mean", *vals),
                            "Cap selection replays the four original A-validation fields")
                candidates.append((ledger.value(candidate_mean), candidate["cap"]))
            selected = ledger.source(SOURCES["caps"], "/selected_caps/" + family)
            assert ledger.value(selected) == min(candidates)[1]
            selection_field = ledger.source(SOURCES["caps"], f"/cap_selection/{selection_index}/selected_cap")
            ledger.same(selected, selection_field, "Selected cap agrees across historical-experiment records")
            point = next(p for p in points if p["cap"] == ledger.value(selected))
            series.append({"family": family, "label": label, "points": points,
                           "selected_cap": ledger.value(selected), "selected_cap_value_id": selected,
                           "selected_mean_value_id": point["value_ids"]["mean"]})
        panels.append({"cohort": split, "series": series})
    caption = (
        "Test pooled observed-entry root mean squared error (RMSE) at the 12-hour horizon "
        "versus training cap, in cohort-A training standard-deviation units. Lines show the "
        "arithmetic mean of four per-run pooled RMSEs; whiskers are pointwise 95% Student t "
        "intervals over the four training seeds (3 degrees of freedom), not intervals for "
        "pairwise model differences. Outer rings mark each family's cap selected by minimum "
        "mean cohort-A validation RMSE across the four seeds (exact ties choose the smaller cap): "
        + ", ".join(f"{label}, {inputs.caps['selected_caps'][family]} epochs" for family, label in FAMILIES)
        + ". The cap also sets the cosine learning-rate schedule period; these cap-specific fits "
        "do not isolate training duration. Checkpoints within each fit are validation-selected. "
        "A/B test scores do not enter cap selection, but were already available before the "
        "retrospective selection analysis. Intervals describe training-seed variation conditional "
        "on fixed cohorts, do not estimate patient or hospital sampling uncertainty, and are "
        "unadjusted for multiple comparisons."
    )
    return ledger, {"figure": "F6_budget_caps", "caption": caption, "panels": panels,
                    "x_label": "Training cap (epochs)", "y_label": "Test pooled RMSE"}


def draw_forest(data):
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH, 3.55), sharey=True)
    fig.subplots_adjust(left=0.345, right=0.965, bottom=0.19, top=0.92, wspace=0.34)
    bounds = [v for p in data["panels"] for r in p["rows"] for v in r["ci95"]]
    bounds += [v for p in data["panels"] for v in p["mdd_band"]]
    limit = max(abs(v) for v in bounds) * 1.12
    artists = []
    for index, (ax, panel) in enumerate(zip(axes, data["panels"])):
        band = ax.fill_betweenx([-0.65, len(panel["rows"]) - 0.45],
                                *panel["mdd_band"], color=COLORS[index], alpha=0.10, lw=0, zorder=0)
        assert sorted(set(band.get_paths()[0].vertices[:, 0])) == panel["mdd_band"]
        zero = ax.axvline(panel["zero"], color="#555555", lw=0.65, ls=(0, (3, 2)), zorder=1)
        assert list(zero.get_xdata()) == [panel["zero"], panel["zero"]]
        for y, row in enumerate(panel["rows"]):
            # Draw saved endpoints directly; avoid subtract/add roundoff in errorbar().
            whisker, = ax.plot(row["ci95"], [y, y], color=COLORS[index], lw=1.0)
            ax.plot(row["ci95"], [y, y], "|", color=COLORS[index], ms=3.2, mew=0.75)
            dot, = ax.plot([row["mean"]], [y], "o", color=COLORS[index], ms=3.1)
            assert list(whisker.get_xdata()) == row["ci95"]
            assert dot.get_xdata()[0] == row["mean"]
            artists.append({"cohort": panel["cohort"], "arm": row["arm"],
                            "mean_and_ci_equal_saved_values_exactly": True})
        ax.set_title(f"({chr(97 + index)}) Cohort {panel['cohort']}", pad=7)
        ax.set_xlim(-limit, limit)
        ax.set_xticks([-0.01, 0, 0.01], ["−0.01", "0", "0.01"])
        ax.set_yticks(range(len(panel["rows"])), [r["label"] for r in panel["rows"]])
        ax.set_ylim(len(panel["rows"]) - 0.45, -0.65)
        ax.tick_params(axis="y", length=0, pad=5)
        ax.spines["left"].set_visible(False)
        ax.grid(axis="y", color="#E5E7EB", lw=0.4, zorder=0)
        ax.set_axisbelow(True)
    # Preserve the requested wording, with a line break to fit a single column.
    fig.text(0.5, 0.078, "arm minus no edges (pooled RMSE);\nnegative is better",
             ha="center", va="center", fontsize=7, linespacing=1.25)
    fig.text(0.5, 0.014, "Shading: ± minimum detectable difference", ha="center", fontsize=7)
    return fig, artists


def draw_caps(data):
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH, 2.95))
    fig.subplots_adjust(left=0.16, right=0.97, bottom=0.235, top=0.765, wspace=0.42)
    markers, styles = ["o", "s", "^"], ["-", "--", "-."]
    artists = []
    for index, (ax, panel) in enumerate(zip(axes, data["panels"])):
        for j, series in enumerate(panel["series"]):
            points = series["points"]
            xs, ys = [p["cap"] for p in points], [p["mean"] for p in points]
            line, = ax.plot(xs, ys, color=COLORS[j], marker=markers[j], ls=styles[j],
                            ms=3, mew=0.65, lw=0.95)
            assert list(line.get_xdata()) == xs and list(line.get_ydata()) == ys
            for point in points:
                whisker, = ax.plot([point["cap"]] * 2, point["ci95"], color=COLORS[j], lw=0.8)
                ax.plot([point["cap"]] * 2, point["ci95"], "_", color=COLORS[j], ms=3, mew=0.7)
                assert list(whisker.get_ydata()) == point["ci95"]
            selected = next(p for p in points if p["cap"] == series["selected_cap"])
            ring, = ax.plot([selected["cap"]], [selected["mean"]], "o", ms=7.1,
                            mfc="none", mec=COLORS[j], mew=1.0, zorder=5)
            assert ring.get_xdata()[0] == series["selected_cap"]
            assert ring.get_ydata()[0] == selected["mean"]
            artists.append({"cohort": panel["cohort"], "family": series["family"],
                            "x_y_ci_and_selected_marker_equal_saved_values_exactly": True})
        ax.set_title(f"({chr(97 + index)}) Cohort {panel['cohort']}", pad=6)
        caps = [p["cap"] for p in panel["series"][0]["points"]]
        ax.set_xticks(caps)
        padding = (max(caps) - min(caps)) * 0.11
        ax.set_xlim(min(caps) - padding, max(caps) + padding)
        low = min(p["ci95"][0] for s in panel["series"] for p in s["points"])
        high = max(p["ci95"][1] for s in panel["series"] for p in s["points"])
        pad = (high - low) * 0.13
        ax.set_ylim(low - pad, high + pad)
        ax.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(4))
        ax.yaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter("%.3f"))
        ax.grid(axis="y", color="#E5E7EB", lw=0.45)
        ax.set_axisbelow(True)
        ax.tick_params(pad=2, length=2.5)
    fig.text(0.025, 0.50, data["y_label"], rotation=90, va="center", ha="center", fontsize=7)
    fig.text(0.56, 0.11, data["x_label"], ha="center", fontsize=7)
    legend = [Line2D([], [], color=COLORS[j], marker=markers[j], ls=styles[j], ms=3,
                     label=label) for j, (_, label) in enumerate(FAMILIES)]
    fig.legend(handles=legend, loc="upper center", bbox_to_anchor=(0.5, 1.005),
               ncol=2, frameon=False, handlelength=1.9, columnspacing=1.2,
               handletextpad=0.5, labelspacing=0.4)
    fig.text(0.5, 0.022, "Outer ring: validation-selected cap", ha="center", fontsize=7)
    return fig, artists


def verify_ledger(data, inputs):
    # Reload every immutable source, so this does not just inspect the build cache.
    files = {n["source_file"] for n in data["values"].values() if "source_file" in n}
    source = {}
    for path in sorted(files):
        assert sha(path) == inputs.hashes[path]
        source[path] = public_read(path)
    direct = derived = 0
    replay = {}
    for name, node in data["values"].items():
        if "source_file" in node:
            value = pointer(source[node["source_file"]], node["source_field"])
            assert node["source_sha256"] == inputs.hashes[node["source_file"]]
            direct += 1
        else:
            value = calculate(node["operation"], [replay[i] for i in node["inputs"]])
            derived += 1
        assert value == node["value"], (name, value, node["value"])
        replay[name] = value
    for equality in data["exact_crosschecks"]:
        assert replay[equality["left"]] == replay[equality["right"]]
    plotted = 0
    for panel in data["panels"]:
        if "rows" in panel:
            for row in panel["rows"]:
                for key, value in [("mean", row["mean"]), ("ci95_low", row["ci95"][0]),
                                   ("ci95_high", row["ci95"][1])]:
                    assert value == replay[row["value_ids"][key]]
                    plotted += 1
            for value, name in zip(panel["mdd_band"], panel["mdd_value_ids"]):
                assert value == replay[name]
                plotted += 1
            assert panel["zero"] == replay[panel["zero_value_id"]]
            plotted += 1
        else:
            for series in panel["series"]:
                for point in series["points"]:
                    for key, value in [("cap", point["cap"]), ("mean", point["mean"]),
                                       ("ci95_low", point["ci95"][0]), ("ci95_high", point["ci95"][1])]:
                        assert value == replay[point["value_ids"][key]]
                        plotted += 1
                assert series["selected_cap"] == replay[series["selected_cap_value_id"]]
                selected = next(p for p in series["points"] if p["cap"] == series["selected_cap"])
                assert selected["mean"] == replay[series["selected_mean_value_id"]]
                plotted += 2
    return {"status": "PASS", "direct_source_fields_exact": direct,
            "arithmetic_nodes_replayed_exactly": derived,
            "crosschecks_exact": len(data["exact_crosschecks"]),
            "plotted_numeric_coordinates_exact": plotted, "source_files_rehashed": len(files),
            "comparison": "Full-precision Python/JSON numeric equality, no tolerance or rounding"}


def layout_check(fig):
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    width, height = fig.get_size_inches()
    hidden = set()
    for ax in fig.axes:
        for axis, limits in [(ax.xaxis, ax.get_xlim()), (ax.yaxis, ax.get_ylim())]:
            for tick in axis.get_major_ticks():
                if not min(limits) <= tick.get_loc() <= max(limits):
                    hidden.update([id(tick.label1), id(tick.label2)])
    text = []
    for artist in fig.findobj(Text):
        if id(artist) in hidden or not artist.get_visible() or not artist.get_text().strip():
            continue
        box = artist.get_window_extent(renderer)
        bounds = [float(v / fig.dpi) for v in [box.x0, box.y0, box.x1, box.y1]]
        assert min(bounds[:2]) >= 0 and bounds[2] <= width and bounds[3] <= height, (artist.get_text(), bounds)
        assert artist.get_fontsize() >= 7
        text.append({"text": artist.get_text(), "font_pt": artist.get_fontsize(),
                     "bounds_inches": bounds})
    overlaps = []
    for i, left in enumerate(text):
        for right in text[i + 1:]:
            a, b = left["bounds_inches"], right["bounds_inches"]
            dx = min(a[2], b[2]) - max(a[0], b[0])
            dy = min(a[3], b[3]) - max(a[1], b[1])
            if dx > 0.5 / 72 and dy > 0.5 / 72:
                overlaps.append([left["text"], right["text"]])
    assert not overlaps, overlaps
    return {"column_width_inches": float(width), "height_inches": float(height),
            "minimum_font_pt": min(t["font_pt"] for t in text),
            "clipped_text": [], "overlapping_text": [], "text": text}


def save_figure(ledger, data, fig, artists, inputs):
    data.update({
        "schema_version": 1, "task": "tools", "kit_version": 6,
        "values": ledger.nodes, "exact_crosschecks": ledger.equalities,
        "provenance_format": (
            "value_ids link each plotted numeric coordinate to values. Direct nodes give an "
            "repository-relative source_file, JSON Pointer source_field, source_sha256 and unrounded value. "
            "Arithmetic nodes give their operation and input value IDs; they are necessary "
            "because the original historical-experiment summary rounds aggregate statistics. Layout coordinates, "
            "ticks, padding and categorical row positions are display settings, not observations."
        ),
        "methods": {"confidence": inputs.paired["methods"]["confidence"],
                    "n_seeds": inputs.caps["power_designs"]["4"]["n_pairs"],
                    "df": inputs.caps["power_designs"]["4"]["df"],
                    "critical_t": inputs.caps["power_designs"]["4"]["critical_t"],
                    "interval_formula": "mean +/- critical_t * sample_sd / sqrt(n_seeds)",
                    "sample_sd": "ddof=1", "font_family": "DejaVu Sans", "pdf_fonttype": 42},
        "layout": layout_check(fig),
        "artist_checks": artists,
        "input_note": "historical-experiment shared_edges contrasts use historical historical-experiment runs and are not plotted. "
                      "historical-experiment supplies the MDD planning multiplier only; historical-experiment supplies current historical-experiment MDDs.",
        "style_reference": "DejaVu Sans; 7-point minimum; 3.33-inch vector PDFs",
    })
    data["source_catalog"] = [{"source_file": path, "sha256": inputs.hashes[path]}
                              for path in sorted({n["source_file"] for n in ledger.nodes.values()
                                                  if "source_file" in n})]
    base = OUT / data["figure"]
    fixed_date = dt.datetime(2026, 11, 12, tzinfo=dt.timezone.utc)
    fig.savefig(base.with_suffix(".pdf"), metadata={"Author": "", "Title": data["figure"],
                "CreationDate": fixed_date, "ModDate": fixed_date})
    fig.savefig(base.with_suffix(".png"), dpi=300)
    path = base.with_suffix(".data.json")
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    # Check the serialized data, not just the in-memory object.
    exact = verify_ledger(json.loads(path.read_text()), inputs)
    with fitz.open(base.with_suffix(".pdf")) as pdf:
        assert len(pdf) == 1
        page = pdf[0]
        fonts = page.get_fonts(full=True)
        assert fonts and all(f[1] == "ttf" and "DejaVuSans" in f[3] for f in fonts), fonts
        assert all(pdf.extract_font(f[0])[3] for f in fonts)
        assert not page.get_images(full=True), "PDF contains raster objects"
        spans = [s for b in page.get_text("dict")["blocks"] if "lines" in b
                 for line in b["lines"] for s in line["spans"] if s["text"].strip()]
        minimum = min(s["size"] for s in spans)
        assert minimum >= 7 - 1e-5, minimum
        assert abs(page.rect.width / 72 - WIDTH) < 1e-6
        pdf_check = {"one_page": True, "raster_image_objects": 0,
                     "fonts": [list(f) for f in fonts], "all_fonts_embedded_truetype": True,
                     "minimum_extracted_font_pt": minimum,
                     "page_points": [page.rect.width, page.rect.height]}
    plt.close(fig)
    return {"status": "PASS", "values": exact, "layout": data["layout"],
            "pdf": pdf_check, "artist_coordinates_exact": True,
            "artifacts": [{"file": base.with_suffix(ext).name,
                           "sha256": sha(base.with_suffix(ext)),
                           "bytes": base.with_suffix(ext).stat().st_size}
                          for ext in [".pdf", ".png", ".data.json"]]}


def main():
    import argparse
    global OUT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--figure',choices=('F5','F6','all'),default='all')
    parser.add_argument('--out-dir',type=Path,default=OUT)
    args=parser.parse_args()
    OUT=args.out_dir
    OUT.mkdir(parents=True,exist_ok=True)
    inputs = Inputs()
    checks = {}
    selected=[(forest_data,draw_forest),(cap_data,draw_caps)]
    if args.figure!='all': selected=[selected[0 if args.figure=='F5' else 1]]
    for builder, draw in selected:
        ledger, data = builder(inputs)
        fig, artists = draw(data)
        checks[data["figure"]] = save_figure(ledger, data, fig, artists, inputs)
        print(data["figure"], checks[data["figure"]]["values"])
    output = {
        "task": "tools", "status": "PASS",
        "verified_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "script": {"file": "tools/make_figures_v6.py", "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
        "runtime": {"python": sys.version, "executable": "python3",
                    "numpy": np.__version__, "matplotlib": matplotlib.__version__,
                    "pdf_reader": fitz.VersionBind, "backend": matplotlib.get_backend()},
        "pinned_inputs": [{"file": str(path), "sha256": PINNED[name]}
                          for name, path in SOURCES.items()],
        "figures": checks,
        "verification_scope": "Author reproducibility and artifact checks; not an independent scientific review.",
        
    }
    (OUT / "CHECKS.json").write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print("PASS: full-precision provenance replay, exact artist coordinates, >=7 pt text, "
          "3.33-inch vector PDFs, embedded DejaVu Sans TrueType fonts")


if __name__ == "__main__":
    main()
