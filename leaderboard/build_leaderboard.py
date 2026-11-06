#!/usr/bin/env python3
"""Build a deterministic, data-free index of the released clinical seed records."""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEEDS = {0, 1, 2, 3}
FIELDS = [
    "schema_version", "task", "series", "corpus", "split", "method", "seed",
    "protocol", "configuration", "checkpoint_id", "checkpoint_sha256",
    "checkpoint_status", "metric", "value", "comparison_status", "denominator",
    "run_record_path", "run_record_sha256", "original_run_record_path",
    "original_run_record_sha256",
]
JSON_FIELDS = {"configuration", "denominator"}
NULL_FIELDS = {"checkpoint_id", "checkpoint_sha256", "original_run_record_path",
               "original_run_record_sha256"}
TUNING = "results/v4/tuning_grid.json"
PERSISTENCE = "results/v4/per_organ_v4.json"
CINC2012 = "results/clinical_v4_v1/cinc2012/cinc2012_results.json"
SHARED = "experiments/shared_input_primary/artifacts/host"
LEARNED = "results/learned_graph_baselines_v1"
CLINICAL_MODELS = {"gru", "gru_med", "gru_large", "grud", "ncde", "odernn",
                   "graphgru", "physiograph", "physiograph_gru"}


def load(root, path):
    return json.loads((root / path).read_text(encoding="utf-8"))


def pointer(*parts):
    return "#/" + "/".join(str(p).replace("~", "~0").replace("/", "~1") for p in parts)


def resolve(root, location, documents=None):
    path, _, fragment = location.partition("#")
    target = (root / path).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError("Record path must stay inside the repository")
    if documents is None:
        obj = load(root, path)
    else:
        if path not in documents:
            documents[path] = load(root, path)
        obj = documents[path]
    if fragment:
        if not fragment.startswith("/"):
            raise ValueError("Expected a JSON Pointer fragment")
        for part in fragment[1:].split("/"):
            key = part.replace("~1", "/").replace("~0", "~")
            obj = obj[int(key)] if isinstance(obj, list) else obj[key]
    return obj


def configuration(record):
    keys = ["lr", "width", "sizes", "variant", "edges", "input_mode", "C", "K",
            "epochs_budget", "batch", "patience", "min_delta", "optimizer",
            "weight_decay", "scheduler", "scheduler_T_max", "gradient_clip", "n_params"]
    result = {key: record[key] for key in keys if key in record}
    if "config" in record:
        result.update(config=record["config"], architecture=record["architecture"],
                      training_protocol=record["protocol"])
    return result


def checkpoint(record):
    value = record["checkpoint"]
    if isinstance(value, dict):
        return value["path"], value["sha256"], "recorded_not_bundled"
    return value, record["checkpoint_sha256"], "recorded_not_bundled"


def build_records(root=ROOT):
    rows, source_runs, hashes = [], set(), {}
    tuning = load(root, TUNING)
    clinical = tuning["selected_runs"]
    if set(clinical) != CLINICAL_MODELS:
        raise ValueError("Clinical model inventory differs from the reported series")
    persistence_document = load(root, PERSISTENCE)
    persistence = persistence_document["table"]
    documents = {TUNING: tuning, PERSISTENCE: persistence_document}
    learned = {}

    def add(series, corpus, split, method, seed, config, ckpt, location,
            source_run, original_path=None, original_hash=None, status="recorded",
            metric_key="pooled_masked_RMSE", denominator_location=None):
        metrics = resolve(root, location, documents)
        counts = resolve(root, denominator_location or location, documents)
        path = location.partition("#")[0]
        if path not in hashes:
            hashes[path] = hashlib.sha256((root / path).read_bytes()).hexdigest()
        value = metrics[metric_key]
        if value is not None and not math.isfinite(value):
            raise ValueError(f"Nonfinite metric: {location}")
        rows.append(dict(
            schema_version=1, task="multivariate_forecasting", series=series,
            corpus=corpus, split=split, method=method, seed=int(seed),
            protocol=("tools/cinc2012/README.md" if corpus == "CinC-2012" else
                      "experiments/shared_input_primary/README.md" if series in
                      {"shared_input_primary", "training_budget"} else "tools/v4_protocol.py"),
            configuration=config, checkpoint_id=ckpt[0], checkpoint_sha256=ckpt[1],
            checkpoint_status=ckpt[2], metric="pooled_RMSE@12", value=value,
            comparison_status=status,
            denominator=dict(observed_target_entries=counts["observed_entries"],
                             stays=counts["n_stays"], zero_target_stays=counts["zero_target_stays"],
                             source=denominator_location or location),
            run_record_path=location, run_record_sha256=hashes[path],
            original_run_record_path=original_path, original_run_record_sha256=original_hash,
        ))
        source_runs.add(source_run)

    for model, runs in sorted(clinical.items()):
        for seed, run in sorted(runs.items()):
            base = TUNING + pointer("selected_runs", model, seed)
            for split in ["A", "B"]:
                add("clinical_selected", "CinC-2019", split, model, seed,
                    configuration(run), checkpoint(run), base + "/" + split, base,
                    original_path=f"runs/clinical/selected/{model}/seed{seed}/run.json",
                    status="excluded_unresolved_replay" if model == "ncde" and split == "B" else "recorded")

    for seed_key, records in sorted(persistence.items()):
        seed = int(seed_key.removeprefix("seed"))
        base = PERSISTENCE + pointer("table", seed_key, "persistence")
        for split in ["A", "B"]:
            add("clinical_persistence", "CinC-2019", split, "persistence", seed,
                {"trained": False, "C": 12, "K": 12}, (None, None, "not_applicable"),
                base + "/splits/" + split, base)

    for directory in ["tpatchgnn", "grafiti_v3"]:
        paths = sorted((root / LEARNED / directory).glob("cinc_*_s*.json"))
        if len(paths) != 4:
            raise ValueError(f"Expected four learned-graph records: {directory}")
        for path in paths:
            rel = path.relative_to(root).as_posix()
            run = load(root, rel)
            seed, model = run["config"]["seed"], run["model"]
            learned[model, seed] = (run, rel)
            for split, key in [("A", "A_test"), ("B", "B_external")]:
                counts = PERSISTENCE + pointer("table", f"seed{seed}", "persistence", "splits", split)
                add("clinical_learned_graph", "CinC-2019", split, model, seed,
                    configuration(run), checkpoint(run), rel + pointer(key), rel,
                    metric_key="RMSE@12", denominator_location=counts)

    for stage, series in [("arms", "shared_input_primary"), ("budget", "training_budget")]:
        paths = sorted((root / SHARED / stage).rglob("run.json"))
        if len(paths) != {"arms": 40, "budget": 24}[stage]:
            raise ValueError(f"Incomplete shared-input stage: {stage}")
        for path in paths:
            rel = path.relative_to(root).as_posix()
            run = load(root, rel)
            if run["scope"] != "full" or run["status"] != "complete":
                raise ValueError(f"Incomplete or small-scope record: {rel}")
            for split in ["A", "B"]:
                add(series, "CinC-2019", split, run["model"] + ":" + run["arm"], run["seed"],
                    configuration(run), checkpoint(run), rel + pointer(split), rel,
                    original_path=rel)

    summary = load(root, CINC2012)
    inputs = {entry["path"]: entry for entry in summary["inputs"]}
    if (summary["status"] != "complete" or summary["scope"] != "full" or
            summary["completed_runs"] != 88 or len(inputs) != 88 or
            set(summary["protocols"]) != {"transfer", "within"}):
        raise ValueError("Incomplete CinC-2012 source inventory")
    for protocol, protocol_record in sorted(summary["protocols"].items()):
        if set(protocol_record["models"]) != CLINICAL_MODELS | {"grafiti", "tpatchgnn"}:
            raise ValueError("CinC-2012 model inventory differs from the reported series")
        for model, model_record in sorted(protocol_record["models"].items()):
            expected_splits = {"testA", "testB", "pooled"} if protocol == "transfer" else {"testB"}
            if set(model_record["splits"]) != expected_splits:
                raise ValueError(f"Incomplete CinC-2012 splits: {protocol}/{model}")
            for split, split_record in sorted(model_record["splits"].items()):
                for seed, metrics in sorted(split_record["per_seed"].items()):
                    original_path = f"runs/cinc2012/{protocol}/{model}/seed{seed}/run.json"
                    original = inputs[original_path]
                    if model in {"grafiti", "tpatchgnn"}:
                        source, config_source = learned[model, int(seed)]
                    else:
                        source = clinical[model][seed]
                        config_source = TUNING + pointer("selected_runs", model, seed)
                    config = configuration(source)
                    config.update(configuration_source=config_source, C=12, K=12,
                                  normalization="frozen_2019" if protocol == "transfer" else "set_a_training",
                                  training_performed=protocol == "within")
                    if protocol == "transfer":
                        identity = checkpoint(source)
                        identity = (identity[0], identity[1], "source_2019_record_not_bundled")
                    else:
                        identity = (None, None, "not_recorded_in_summary")
                    location = CINC2012 + pointer("protocols", protocol, "models", model,
                                                  "splits", split, "per_seed", seed)
                    add("cinc2012_" + protocol, "CinC-2012", split, model, seed, config,
                        identity, location, original_path, original_path, original["sha256"])

    rows.sort(key=lambda row: (row["series"], row["corpus"], row["method"],
                              row["configuration"].get("epochs_budget", 35), row["seed"], row["split"]))
    validate_records(rows)
    return rows, len(source_runs)


def validate_records(rows):
    """Check coverage and scientific invariants; optional full schema check is separate."""
    identities, groups = set(), defaultdict(set)
    for row in rows:
        identity = (row["series"], row["method"], row["seed"], row["split"],
                    row["configuration"].get("epochs_budget", 35))
        if identity in identities:
            raise ValueError(f"Duplicate evaluation: {identity}")
        identities.add(identity)
        groups[identity[:2] + identity[3:]].add(row["seed"])
        counts = row["denominator"]
        if counts["observed_target_entries"] <= 0 or counts["stays"] <= 0:
            raise ValueError("Empty evaluation denominator")
        if not 0 <= counts["zero_target_stays"] <= counts["stays"]:
            raise ValueError("Invalid zero-target stay count")
        if row["value"] is None or not math.isfinite(row["value"]) or row["value"] < 0:
            raise ValueError("Expected a finite archived RMSE")
    for group, seeds in groups.items():
        if seeds != SEEDS:
            raise ValueError(f"Expected seeds 0–3 for {group}: {seeds}")


def csv_text(rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
                         if key in JSON_FIELDS else "" if key in NULL_FIELDS and value is None else value
                         for key, value in row.items()})
    return stream.getvalue()


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != FIELDS:
            raise ValueError("CSV header does not match the record contract")
        rows = []
        for raw in reader:
            row = dict(raw)
            for key in JSON_FIELDS:
                row[key] = json.loads(row[key])
            for key in NULL_FIELDS:
                row[key] = row[key] or None
            for key in ["schema_version", "seed"]:
                row[key] = int(row[key])
            row["value"] = float(row["value"])
            rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Compare existing CSV bytes; do not write")
    parser.add_argument("--validate-schema", action="store_true", help="Also validate decoded CSV rows with installed jsonschema")
    args = parser.parse_args()
    rows, source_count = build_records()
    destination = ROOT / "leaderboard/LEADERBOARD.csv"
    expected = csv_text(rows).encode("utf-8")
    if args.check:
        if destination.read_bytes() != expected:
            raise SystemExit("FAIL: CSV differs from the released source records")
    else:
        destination.write_bytes(expected)
    decoded = read_csv(destination)
    if decoded != rows:
        raise SystemExit("FAIL: CSV round trip changed a record")
    if args.validate_schema:
        from jsonschema import Draft202012Validator
        schema = load(ROOT, "leaderboard/RECORD_SCHEMA.json")
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        for row in decoded:
            validator.validate(row)
        print(f"Schema PASS: {len(decoded)} decoded CSV rows")
    print(f"Source run identities: {source_count}; shipped split records: {len(rows)}; CSV rows: {len(decoded)}")
    for series, count in sorted(Counter(row["series"] for row in rows).items()):
        print(f"{series}: {count} rows")
    denominators = Counter((row["corpus"], row["split"], row["denominator"]["observed_target_entries"],
                            row["denominator"]["stays"], row["denominator"]["zero_target_stays"]) for row in rows)
    for (corpus, split, entries, stays, zero), count in sorted(denominators.items()):
        print(f"{corpus}/{split}: {count} rows; observed target entries={entries}; stays={stays}; zero-target stays={zero}")
    print("Excluded unresolved replay rows:", sum(row["comparison_status"] != "recorded" for row in rows))


if __name__ == "__main__":
    main()
