"""Build the frozen cinc2012_cohort CinC-2012 forecasting protocol using only NumPy.

Values remain in physical/numerical source units, just as in the 2019 NPZ;
physiograph_data_loader applies the selected normalization at access time.
See results/cinc2012_cohort_v1/COHORT_REPORT.md for the unit discrepancies and static covariate mapping.
"""
from __future__ import annotations

# Resolve all public modules and scratch from the release root.
import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[1]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH

import argparse
import csv
import hashlib
import io
import json
from collections import Counter
from pathlib import Path
import platform
import sys
import zipfile

import numpy as np

ORGAN_GROUPS = {
    "cardiovascular": ["HR", "SBP", "MAP", "DBP"],
    "pulmonary": ["O2Sat", "Resp", "FiO2", "PaCO2"],
    "renal": ["Creatinine", "BUN", "Potassium"],
    "metabolic": ["Lactate", "Glucose", "HCO3", "WBC", "Temp"],
}
FEATURES = [f for group in ORGAN_GROUPS.values() for f in group]
ORGAN_NAMES = list(ORGAN_GROUPS)
ORGAN_SLICES = np.array([[0, 4], [4, 8], [8, 11], [11, 16]], np.int64)
SOURCES = [
    ("HR",), ("SysABP", "NISysABP"), ("MAP", "NIMAP"),
    ("DiasABP", "NIDiasABP"), ("SaO2",), ("RespRate",), ("FiO2",),
    ("PaCO2",), ("Creatinine",), ("BUN",), ("K",), ("Lactate",),
    ("Glucose",), ("HCO3",), ("WBC",), ("Temp",),
]
SOURCE_TO_FEATURE = {source: j for j, sources in enumerate(SOURCES) for source in sources}
STATIC_COLS = ["Age", "Gender", "Height", "Weight", "ICUType"]
TRANSFER_STATIC_COLS = ["Age", "Gender", "Unit1", "Unit2", "HospAdmTime"]
T_MAX = 48
SEED = 0
VAL_FRAC = 0.15

# The mapping is numeric identity. K is monovalent (mEq/L == mmol/L), and
# cells/nL == 10^3 cells/uL. FiO2 and Lactate have conflicting 2019 metadata;
# retain the frozen NPZ's empirical fraction and mmol/L-like numeric scales.
UNIT_ROWS = [
    ("beats/min", "beats/min", "beats/min", "identity"),
    ("mmHg", "mmHg", "mmHg", "identity; invasive preferred per hour"),
    ("mmHg", "mmHg", "mmHg", "identity; invasive preferred per hour"),
    ("mmHg", "mmHg", "mmHg", "identity; invasive preferred per hour"),
    ("% arterial SaO2", "% pulse oximetry", "%", "identity; FLAG different measurement modality"),
    ("breaths/min", "breaths/min", "breaths/min", "identity"),
    ("fraction (0-1)", "%", "fraction (0-1)", "FLAG metadata conflict; preserve empirical 2019 fraction scale, no x100"),
    ("mmHg", "mmHg", "mmHg", "identity"),
    ("mg/dL", "mg/dL", "mg/dL", "identity"),
    ("mg/dL", "mg/dL", "mg/dL", "identity"),
    ("mEq/L", "mmol/L", "mmol/L", "x1; monovalent potassium"),
    ("mmol/L", "mg/dL", "mmol/L-like frozen numeric scale", "FLAG metadata conflict; preserve numerical scale, no x9.008"),
    ("mg/dL", "mg/dL", "mg/dL", "identity; no glucose x18 or /18"),
    ("mmol/L", "mmol/L", "mmol/L", "identity"),
    ("cells/nL", "10^3 cells/uL", "10^3 cells/uL", "x1; 1 nL = 0.001 uL"),
    ("deg C", "deg C", "deg C", "identity; no Fahrenheit transform"),
]


def convert_observation(parameter, value):
    """Convert a valid 2012 reading to the frozen 2019 numerical convention.

    All selected conversions are numerical identity; the two conflicting unit
    declarations remain flagged rather than guessing from individual readings.
    This deliberately does not rescale, clip, or repair clinical outliers.
    """
    if parameter not in SOURCE_TO_FEATURE:
        raise KeyError(parameter)
    return float(value)


def parse_patient(text):
    """Bin one CSV record; pressure fallback is applied separately each hour.

    Length is the final hour containing any valid time-series observation plus
    one, or zero with no time series. Unselected channels also establish the
    source timeline, just as rows do in 2019. Exactly 48:00 is outside [0,48).
    """
    rows = csv.DictReader(io.StringIO(text))
    sums = {s: np.zeros(T_MAX, np.float64) for s in SOURCE_TO_FEATURE}
    counts = {s: np.zeros(T_MAX, np.int64) for s in SOURCE_TO_FEATURE}
    static = np.full(len(STATIC_COLS), -1, np.float32)
    static_seen = set()
    audit = Counter()
    record_id = None
    last_any_hour = -1
    for row in rows:
        hour, minute = map(int, row["Time"].split(":"))
        if hour < 0 or not 0 <= minute < 60:
            raise ValueError(f"invalid timestamp: {row['Time']}")
        parameter, value = row["Parameter"], float(row["Value"])
        if parameter == "RecordID":
            if record_id is not None:
                raise ValueError("multiple RecordID rows")
            record_id = int(value)
        # Use the first 00:00 descriptor, even if it is unknown. Weight may
        # recur as a time series: later measurements never fill the static.
        if parameter in STATIC_COLS and hour == minute == 0:
            if parameter in static_seen:
                audit[f"duplicate_static_{parameter}"] += 1
            else:
                static_seen.add(parameter)
                if np.isfinite(value) and value >= 0:
                    static[STATIC_COLS.index(parameter)] = value
        is_time_series = (parameter not in STATIC_COLS and parameter != "RecordID") or (
            parameter == "Weight" and (hour > 0 or minute > 0))
        if is_time_series:
            if hour < T_MAX and np.isfinite(value) and value >= 0:
                last_any_hour = max(last_any_hour, hour)
        if parameter not in SOURCE_TO_FEATURE:
            continue
        audit["mapped_rows"] += 1
        if hour >= T_MAX:
            audit["mapped_outside_grid"] += 1
            continue
        if not np.isfinite(value) or value < 0:
            audit[f"invalid_{parameter}"] += 1
            continue
        sums[parameter][hour] += convert_observation(parameter, value)
        counts[parameter][hour] += 1
        audit[f"accepted_{parameter}"] += 1
    if record_id is None:
        raise ValueError("missing RecordID")
    values = np.zeros((T_MAX, len(FEATURES)), np.float32)
    mask = np.zeros_like(values)
    for j, sources in enumerate(SOURCES):
        for source in sources:
            choose = (mask[:, j] == 0) & (counts[source] > 0)
            values[choose, j] = sums[source][choose] / counts[source][choose]
            mask[choose, j] = 1
            audit[f"selected_hours_{source}"] += int(choose.sum())
    observed_hours = np.flatnonzero(mask.any(axis=1))
    mapped_length = int(observed_hours[-1] + 1) if observed_hours.size else 0
    return dict(values=values, mask=mask, static=static,
                static_mask=(static >= 0).astype(np.float32), length=last_any_hour + 1,
                record_id=record_id, mapped_length=mapped_length,
                audit=audit)


def build_split(zip_path):
    """Read members directly from the ZIP, in sorted filename order."""
    records = []
    audit = Counter()
    with zipfile.ZipFile(zip_path) as archive:
        names = sorted(n for n in archive.namelist() if n.endswith(".txt"))
        for name in names:
            record = parse_patient(archive.read(name).decode("utf-8"))
            if Path(name).stem != str(record["record_id"]):
                raise ValueError(f"RecordID disagrees with filename: {name}")
            records.append(record)
            audit.update(record["audit"])
    if not records:
        raise ValueError(f"no records in {zip_path}")
    ids = np.array([r["record_id"] for r in records], np.int64)
    if len(np.unique(ids)) != len(ids):
        raise ValueError(f"duplicate RecordID in {zip_path}")
    return dict(
        values=np.stack([r["values"] for r in records]),
        mask=np.stack([r["mask"] for r in records]),
        static=np.stack([r["static"] for r in records]),
        static_mask=np.stack([r["static_mask"] for r in records]),
        length=np.array([r["length"] for r in records], np.int32),
        record_id=ids,
        mapped_length=np.array([r["mapped_length"] for r in records], np.int32),
        # Compatibility placeholders; these are not negative sepsis labels.
        sepsis=np.zeros((len(records), T_MAX), np.float32),
        ever_sepsis=np.zeros(len(records), np.float32),
        audit=audit,
    )


def make_split_indices(n):
    perm = np.random.default_rng(SEED).permutation(n)
    n_val = int(VAL_FRAC * n)
    return perm[n_val:], perm[:n_val], np.empty(0, np.int64)


def fit_norm_stats(values, mask):
    """Match the 2019 observed-entry estimator, including its small-n rule."""
    m = mask.astype(bool)
    mean = np.zeros(values.shape[-1], np.float32)
    std = np.ones(values.shape[-1], np.float32)
    for j in range(values.shape[-1]):
        v = values[..., j][m[..., j]]
        if v.size > 10:
            mean[j] = v.mean()
            std[j] = v.std() + 1e-6
    return mean, std


def transfer_statics(static):
    """Align semantics with 2019; never feed height into a unit indicator."""
    out = np.zeros_like(static)
    out[:, :2] = np.where(static[:, :2] >= 0, static[:, :2], 0)
    out[:, 2] = static[:, 4] == 3  # 2019 Unit1: medical ICU
    out[:, 3] = static[:, 4] == 4  # 2019 Unit2: surgical ICU
    # HospAdmTime is unavailable: 0 is the frozen 2019 missing-value encoding.
    return out


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def make_payload(A, B, reference):
    if list(reference["features"]) != FEATURES:
        raise ValueError("2019 feature order changed")
    if list(reference["organ_names"]) != ORGAN_NAMES or not np.array_equal(reference["organ_slices"], ORGAN_SLICES):
        raise ValueError("2019 organ groups changed")
    tr, va, te = make_split_indices(len(A["length"]))
    mean, std = fit_norm_stats(A["values"][tr], A["mask"][tr])
    payload = {}
    for label, split in [("A", A), ("B", B)]:
        for key in ["values", "mask", "static", "sepsis", "length", "ever_sepsis", "record_id", "static_mask", "mapped_length"]:
            payload[f"{label}_{key}"] = split[key]
    payload.update(
        train_idx=tr, val_idx=va, test_idx=te,
        norm_mean=mean, norm_std=std,
        norm_mean_within2012=mean, norm_std_within2012=std,
        norm_mean_transfer2019=reference["norm_mean"].copy(),
        norm_std_transfer2019=reference["norm_std"].copy(),
        transfer_A_test_idx=np.arange(len(A["length"]), dtype=np.int64),
        transfer_B_test_idx=np.arange(len(B["length"]), dtype=np.int64),
        features=np.array(FEATURES), organ_names=np.array(ORGAN_NAMES),
        organ_slices=reference["organ_slices"].copy(),
        static_cols=np.array(STATIC_COLS),
        units=np.array([row[2] for row in UNIT_ROWS]),
        unit_flags=np.array([row[3] for row in UNIT_ROWS]),
        protocol=np.array("within2012_A85val15_Btest"),
        sepsis_labels_available=np.array(False),
        seed=np.array(SEED, np.int64),
    )
    for key in ["norm_mean_transfer2019", "norm_std_transfer2019"]:
        if payload[key].shape != (16,) or not np.isfinite(payload[key]).all():
            raise ValueError(f"invalid {key}")
    if np.any(payload["norm_std_transfer2019"] <= 0):
        raise ValueError("non-positive reference standard deviation")
    return payload


def make_transfer_payload(within):
    """Loader-compatible evaluation view: consume testA and testB only.

    make_loaders always constructs a shuffled train loader, which rejects an
    empty dataset. Its train/val indices remain nonempty compatibility handles;
    they overlap testA and must NEVER be used to fit or select transfer models.
    """
    transfer = dict(within)
    transfer.update(
        norm_mean=within["norm_mean_transfer2019"],
        norm_std=within["norm_std_transfer2019"],
        test_idx=within["transfer_A_test_idx"],
        static_cols=np.array(TRANSFER_STATIC_COLS),
        protocol=np.array("transfer2019_EVALUATION_ONLY_use_testA_and_testB"),
        training_allowed=np.array(False),
    )
    for split in ["A", "B"]:
        transfer[f"{split}_static2012"] = within[f"{split}_static"]
        transfer[f"{split}_static"] = transfer_statics(within[f"{split}_static"])
        # Availability for Unit1/Unit2 means ICUType was recorded; 0 is a
        # known false indicator, whereas HospAdmTime is unavailable everywhere.
        m = np.zeros_like(within[f"{split}_static_mask"])
        m[:, :2] = within[f"{split}_static_mask"][:, :2]
        m[:, 2:4] = within[f"{split}_static_mask"][:, 4:5]
        transfer[f"{split}_static_mask"] = m
    return transfer


def describe_split(split):
    length, mask = split["length"], split["mask"]
    eligible = length >= 24
    return dict(
        stays=len(length), eligible24=int(eligible.sum()),
        no_mapped_measurements=int((split["mapped_length"] == 0).sum()),
        no_time_series=int((length == 0).sum()),
        length_min=int(length.min()), length_max=int(length.max()),
        length_differs_from_mapped=int((length != split["mapped_length"]).sum()),
        observed_hours=mask.sum(axis=(0, 1)).astype(int).tolist(),
        observed_stays=mask.any(axis=1).sum(axis=0).astype(int).tolist(),
        within_length_denominator=int(length.sum()),
        eligible24_observed_cells=mask[eligible, :24].sum(axis=(0, 1)).astype(int).tolist(),
        no_context_12=int((mask[eligible, :12].sum(axis=(1, 2)) == 0).sum()),
        no_target_12=int((mask[eligible, 12:24].sum(axis=(1, 2)) == 0).sum()),
        static_missing=(split["static_mask"] == 0).sum(axis=0).astype(int).tolist(),
        audit=dict(sorted(split["audit"].items())),
    )


def write_manifest(path, A, B, train_idx, val_idx):
    membership = np.full(len(A["length"]), "train", dtype="U5")
    membership[val_idx] = "val"
    with open(path, "w") as stream:
        stream.write("set\trow_index\trecord_id\twithin_role\tlength\teligible_C12_K12\tmapped_length\n")
        for label, split in [("A", A), ("B", B)]:
            for i, record_id in enumerate(split["record_id"]):
                role = membership[i] if label == "A" else "test"
                stream.write(f"{label}\t{i}\t{record_id}\t{role}\t{split['length'][i]}\t{int(split['length'][i] >= 24)}\t{split['mapped_length'][i]}\n")


def write_report(path, A, B, within, summary):
    a, b = summary["A"], summary["B"]
    tr, va = within["train_idx"], within["val_idx"]
    lines = [
        "# cinc2012_cohort CinC-2012 cohort report", "",
        "Built from the maintainer-supplied archives, offline, on CPU. All 8,000 records are retained; forecasting eligibility is separate from cohort inclusion. No forecasting models were fitted and no model-ranking claim is made here.", "",
        "## Counts and temporal protocol", "",
        "| Partition | Retained | Eligible at C+K=24 | Ineligible |",
        "|---|---:|---:|---:|",
        f"| A train | {len(tr)} | {int((A['length'][tr] >= 24).sum())} | {int((A['length'][tr] < 24).sum())} |",
        f"| A validation | {len(va)} | {int((A['length'][va] >= 24).sum())} | {int((A['length'][va] < 24).sum())} |",
        f"| B test | {b['stays']} | {b['eligible24']} | {b['stays'] - b['eligible24']} |",
        f"| Total | {a['stays'] + b['stays']} | {a['eligible24'] + b['eligible24']} | {8000 - a['eligible24'] - b['eligible24']} |", "",
        "A and B each contain 4,000 distinct stays and their RecordID sets are disjoint. Sorted archive-member filenames determine row order. With numpy.random.default_rng(0).permutation(4000), the first 600 indices are validation and the remaining 3,400 are training. This retains the 2019 RNG and seed rule while honoring this card's 85/15 split, rather than the 2019 70/15/15 split. B is never used for fitting normalization. These 2012 challenge sets are not asserted to be different hospitals; the unchanged loader's hospital=0/1 field identifies set A/B only.", "",
        "Each hour h=0,...,47 contains the arithmetic mean of valid observations in [h,h+1). There is no interpolation or forward fill. Multiple observations, including duplicate timestamps, receive equal weight. For each pressure variable in each hour, invasive observations are averaged if present; otherwise noninvasive observations are averaged. The two measurement methods are never pooled within an hour. Missing values are zero with mask=0; true zero readings retain mask=1. Nonfinite and negative readings are invalid under the 2012 documentation's nonnegative-value rule. No other outlier cleaning or unit inference from individual readings is applied.", "",
        "Length is the last hour with any valid time-series observation plus one, using both mapped and unselected source channels, including later Weight observations. Admission descriptors do not establish temporal coverage; a descriptor-only stay has length zero. This follows the source timeline rather than truncating it to the selected variables, consistent with the 2019 use of source rows for length. Thus length>=24 is a recorded-coverage criterion, not a clinical length-of-stay estimate. An observation at exactly 48:00 is excluded, consistent with the specified half-open grid.", "",
        f"A/B contain {a['no_mapped_measurements']}/{b['no_mapped_measurements']} stays with no mapped observations, including {a['no_time_series']}/{b['no_time_series']} descriptor-only stays; lengths range {a['length_min']}–{a['length_max']} / {b['length_min']}–{b['length_max']}. Source-timeline length differs from mapped-variable length in {a['length_differs_from_mapped']}/{b['length_differs_from_mapped']} stays. Both are in the NPZ and COHORT_MANIFEST.tsv for audit. Two stays become 24-hour eligible solely through unselected channels: A RecordID 132988 has mapped length 23, and B RecordID 150611 has mapped length 16. The loader retains these under the specified length rule.", "",
        f"Among length-eligible stays, A/B have {a['no_context_12']}/{b['no_context_12']} with no observations in hours 0–11 and {a['no_target_12']}/{b['no_target_12']} with no observations in hours 12–23. The unchanged loader uses only length eligibility; these stays are retained.", "",
        "## Observation rates", "",
        "The main denominator is 4,000 x 48 = 192,000 padded stay-hours per set and feature. 'Within length' uses the sum of source-timeline lengths (including empty hours before the last observed hour). '24h eligible' uses eligible stays x 24. These are measured hourly cells after pressure fallback, not raw sample counts.", "",
        "| Feature | A observed hours | A / 192000 | B observed hours | B / 192000 | A within length | B within length | A 24h eligible | B 24h eligible | A/B stays ever observed |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for j, f in enumerate(FEATURES):
        rates = []
        for s in [a, b]:
            rates.append((s["observed_hours"][j] / s["within_length_denominator"],
                          s["eligible24_observed_cells"][j] / (s["eligible24"] * 24)))
        lines.append(f"| {f} | {a['observed_hours'][j]} | {a['observed_hours'][j]/192000:.4%} | {b['observed_hours'][j]} | {b['observed_hours'][j]/192000:.4%} | {rates[0][0]:.4%} | {rates[1][0]:.4%} | {rates[0][1]:.4%} | {rates[1][1]:.4%} | {a['observed_stays'][j]}/{b['observed_stays'][j]} |")
    lines += ["", "All 16 mapped variables are present in both sets. Sparse SaO2 is retained as specified; no substitute channel is introduced.", "", "## Unit decisions and evidence limits", "",
        "Unit descriptions were checked against the local GraFITi/tsdm PhysioNet dataset modules listed in BUILD_SUMMARY.json, with their hashes, and against numerical distributions in the frozen 2019 NPZ. These are local secondary transcriptions, not a fresh primary-source verification. Network access was prohibited; the official PhysioNet pages were not fetched. The two conflicting declarations below remain explicitly unresolved. The effective scales describe compatibility with the frozen NPZ; numerical agreement alone does not prove physical units.", "",
        "| Target feature | 2012 source(s) | 2012 declared unit | 2019 locally declared unit | Stored numerical convention | Decision |",
        "|---|---|---|---|---|---|",
    ]
    for f, sources, row in zip(FEATURES, SOURCES, UNIT_ROWS):
        lines.append(f"| {f} | {' else '.join(sources)} | {' | '.join(row)} |")
    lines += ["", "All applied transforms have numeric multiplier 1 and offset 0. Potassium and WBC require a change of unit notation with no numeric change. Glucose is mg/dL in both sources; temperature is degrees Celsius in both. No percent conversion is applied to SaO2.", "",
        "The local 2019 documentation calls FiO2 '%' and lactate 'mg/dL', but the frozen array is fraction-valued for FiO2 and mmol/L-like for lactate. Multiplying the 2012 values by 100 or 9.008 would force the transfer inputs away from the frozen training scale. This build preserves the observed numerical convention and flags the documentation conflict. A maintainer should verify primary-source provenance before claiming complete physical-unit harmonization; any revised lactate scale is a protocol change requiring a regenerated transfer artifact. SaO2 and O2Sat also differ in measurement modality (arterial versus pulse oximetry), even though both use percent; this mandated mapping is a limitation of the transfer comparison.", "",
        "Frozen 2019 A observed-value checks (quantiles 1%, 50%, 99%; all A rows, not just A train):", "",
        "| Variable | q01 | median | q99 | Frozen A-train mean | Frozen A-train std |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for f, dist in summary["reference_distributions"].items():
        lines.append(f"| {f} | {dist['q01']:.6g} | {dist['median']:.6g} | {dist['q99']:.6g} | {dist['train_mean']:.6g} | {dist['train_std']:.6g} |")
    lines += ["", "## Static descriptors and unavailable labels", "",
        "The within-2012 static vector is [Age (years), Gender (0 female, 1 male), Height (cm), Weight (kg), ICUType (1 coronary care, 2 cardiac surgery recovery, 3 medical ICU, 4 surgical ICU)]. These are raw admission descriptors, without standardization or one-hot expansion. Unknown values remain -1, with separate A_static_mask/B_static_mask metadata. Only the first 00:00 descriptor is used; later weight observations never fill missing admission weight. Set B record 149509 repeats weight at 00:00 (70.8 then 70.4); the first value, 70.8, is used.", "",
        "| Descriptor | A missing | B missing |", "|---|---:|---:|",
    ]
    for j, f in enumerate(STATIC_COLS):
        lines.append(f"| {f} | {a['static_missing'][j]} | {b['static_missing'][j]} |")
    lines += ["", "The transfer artifact instead supplies [Age, Gender, Unit1, Unit2, HospAdmTime], matching the semantic layout consumed by the 2019 models. Unit1 is 1 for ICUType=3, Unit2 is 1 for ICUType=4; other ICU types yield 0/0. Unavailable HospAdmTime and unknown Age/Gender use zero, matching the 2019 preprocessor's missing-value encoding. Original 2012 statics remain in A_static2012/B_static2012. ICU-type mapping is an explicit approximation: 2012 unit types are not the 2019 hospital administrative identifiers. The models consume statics, so the raw [Height, Weight, ICUType] slots must not be passed into a 2019 checkpoint.", "",
        "2012 does not supply the 2019 SepsisLabel sequence. A_sepsis/B_sepsis and A_ever_sepsis/B_ever_sepsis are zero placeholders solely for loader compatibility, and sepsis_labels_available=False. They must not be interpreted as known nonseptic labels or used for sepsis-stratified conclusions. Outcomes-a.txt is hashed for provenance but is not used: mortality is not a sepsis label.", "",
        "## Normalization and loader use", "",
        "cinc2012_cohort.npz contains every original 2019 NPZ key with matching dtypes and trailing shapes, plus explicit protocol metadata, record IDs and both normalizations. A_* is set A and B_* is set B. Stored values are unnormalized. norm_mean/norm_std and norm_mean_within2012/norm_std_within2012 are fitted only on the 3,400 A-train stays, over observed hourly means, using exactly the 2019 estimator (population std + 1e-6; fallback mean=0/std=1 if <=10 cells). Eligible-window filtering happens later in the loader, as in 2019. norm_mean_transfer2019/norm_std_transfer2019 are exact copies of the frozen 2019 statistics, not re-estimates.", "",
        "For the within-2012 run call make_loaders('cinc2012_cohort.npz', C=12, K=12, num_workers=0). Train on the first loader, select with the second, and evaluate on the fourth (testB). The third loader (testA) is intentionally empty because this card allocates all of A to train/validation. The generic training runner assumes a nonempty testA, so it must not be used blindly as a within-2012 evaluation wrapper.", "",
        "For frozen-checkpoint transfer call make_loaders('cinc2012_transfer.npz', C=12, K=12, num_workers=0) and evaluate both the third and fourth loaders, comprising all eligible A and B stays. Combine masked error numerators and observed-target denominators across both sets; do not average set RMSEs. Transfer testA includes all 4,000 A indices. The unchanged make_loaders always creates a shuffled training loader and rejects an empty training dataset, so transfer train/val indices are retained only as compatibility handles and overlap testA. training_allowed=False records this restriction. Never fit or select a transfer model on those first two loaders; use the already frozen 2019 checkpoint. The primary artifact also stores transfer_A_test_idx/transfer_B_test_idx for direct evaluation without this view.", "",
        "## Parsing audit", "",
        "| Item | A | B |", "|---|---:|---:|",
        f"| Mapped raw rows | {a['audit']['mapped_rows']} | {b['audit']['mapped_rows']} |",
        f"| Mapped rows outside [0,48) | {a['audit']['mapped_outside_grid']} | {b['audit']['mapped_outside_grid']} |",
        f"| Invalid negative/nonfinite Temp readings inside grid | {a['audit'].get('invalid_Temp',0)} | {b['audit'].get('invalid_Temp',0)} |",
    ]
    for sources in SOURCES[1:4]:
        for s in sources:
            lines.append(f"| Selected hourly cells from {s} | {a['audit'].get('selected_hours_'+s,0)} | {b['audit'].get('selected_hours_'+s,0)} |")
    lines += ["", "All invalid mapped readings are negative temperatures (A: 23 at -17.8 and 1 at -12.5; B: 16 at -17.8 and 1 at -12.8). They are masked rather than interpreted as valid Celsius observations. Zeros and positive outliers, including extreme WBC readings, are retained under the no-additional-cleaning protocol. Detailed counters, input hashes and environment are in BUILD_SUMMARY.json; per-record split and length membership is in COHORT_MANIFEST.tsv.", "",
        "## Verification", "",
        "Run python3 -m unittest discover -s tests -v for the two-stay fixture, unit decisions, split/no-leakage behavior, static mapping, and artifact invariants. The optional loader test calls the unchanged project make_loaders when torch is installed and uses num_workers=0. The project environment supplied torch for the delivered validation; see TESTS.log and RECEIPT.md for actual results. System Python lacks torch and skips only that integration test.", "",
    ]
    path.write_text("\n".join(lines))


def main():
    here = Path(__file__).resolve().parent
    project = RELEASE_ROOT
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-root", type=Path, default=project / "data/cinc2012")
    ap.add_argument("--reference", type=Path, default=project / "data/cinc2019_cohort.npz")
    ap.add_argument("--out-dir", type=Path, default=project / "data/cinc2012")
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    A, B = [build_split(args.data_root / f"set-{s}.zip") for s in "ab"]
    if len(A["length"]) != 4000 or len(B["length"]) != 4000:
        raise ValueError("the frozen cinc2012_cohort protocol requires 4000 stays in each set")
    if np.intersect1d(A["record_id"], B["record_id"]).size:
        raise ValueError("overlapping RecordID between A and B")
    with np.load(args.reference, allow_pickle=False) as ref:
        within = make_payload(A, B, ref)
        missing = set(ref.files) - set(within)
        if missing:
            raise ValueError(f"missing original 2019 NPZ keys: {missing}")
        for key in ref.files:
            if ref[key].dtype != within[key].dtype or ref[key].shape[1:] != within[key].shape[1:]:
                raise ValueError(f"2019 schema mismatch: {key}")
        ref_values, ref_mask = ref["A_values"], ref["A_mask"]
        distributions = {}
        for f in ["FiO2", "Lactate", "Glucose", "Temp", "WBC", "Potassium"]:
            j = FEATURES.index(f)
            obs = ref_values[..., j][ref_mask[..., j].astype(bool)]
            q = np.quantile(obs, [.01, .5, .99])
            distributions[f] = dict(q01=float(q[0]), median=float(q[1]), q99=float(q[2]),
                                    train_mean=float(ref["norm_mean"][j]), train_std=float(ref["norm_std"][j]))
        del ref_values, ref_mask
    paths = [args.data_root / "set-a.zip", args.data_root / "set-b.zip",
             args.data_root / "Outcomes-a.txt", args.reference,
             project / "src/cinc2019_cohort_preprocessor.py",
             project / "src/physiograph_data_loader.py"]
    hashes = {str(p): sha256(p) for p in paths if p.is_file()}
    summary = dict(A=describe_split(A), B=describe_split(B),
                   reference_distributions=distributions, input_sha256=hashes,
                   python=sys.version, executable=sys.executable,
                   numpy=np.__version__, platform=platform.platform(), seed=SEED,
                   train_count=len(within["train_idx"]), val_count=len(within["val_idx"]),
                   train_eligible24=int((A["length"][within["train_idx"]] >= 24).sum()),
                   val_eligible24=int((A["length"][within["val_idx"]] >= 24).sum()))
    for name, payload in [("cinc2012_cohort.npz", within),
                          ("cinc2012_transfer.npz", make_transfer_payload(within))]:
        output = args.out_dir / name
        np.savez_compressed(output, **payload)
        print(f"wrote {output} ({output.stat().st_size:,} bytes)", flush=True)
    write_manifest(args.out_dir / "COHORT_MANIFEST.tsv", A, B, within["train_idx"], within["val_idx"])
    write_report(args.out_dir / "COHORT_REPORT.md", A, B, within, summary)
    (args.out_dir / "BUILD_SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"retained A/B={len(A['length'])}/{len(B['length'])}; eligible24={summary['A']['eligible24']}/{summary['B']['eligible24']}")


if __name__ == "__main__":
    main()
