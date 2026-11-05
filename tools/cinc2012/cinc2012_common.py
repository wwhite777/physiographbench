"""Portable CinC-2012 protocol, frozen cohort checks and checkpoint reconstruction."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from release_paths import ROOT as PROJECT, SCRATCH

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["TMPDIR"] = str(SCRATCH)
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
tempfile.tempdir = str(SCRATCH)
sys.path.insert(0, str(PROJECT / "src"))

import numpy as np
import torch
from torch.utils.data import DataLoader
from physiograph_data_loader import ForecastWindows

COHORT = PROJECT / "data/cinc2012"
WITHIN_NPZ = COHORT / "cinc2012_cohort.npz"
TRANSFER_NPZ = COHORT / "cinc2012_transfer.npz"
REFERENCE_NPZ = PROJECT / "data/cinc2019_cohort.npz"
SELECTION = PROJECT / "results/v4/selection.json"
RUN_ROOT = PROJECT / "runs/cinc2012"
LEARNED_MODELS = ("tpatchgnn", "grafiti")


def owned_path(path):
    path = Path(path).resolve()
    if not path.is_relative_to(PROJECT / "runs"):
        raise ValueError(f"Generated outputs must be inside this repository's runs directory: {path}")
    return path


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, data):
    path = owned_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def verify_input(path):
    """Verify distributed sources/selection or a complete frozen cohort archive."""
    path = Path(path).resolve()
    if path.suffix == ".npz":
        inventory = json.loads((PROJECT / "manifests/cohorts.json").read_text())
        matches = [entry["sha256"] for name, entry in inventory.items()
                   if Path(name).name == path.name]
        expected = matches[0] if len(matches) == 1 else None
    else:
        inventory = json.loads((PROJECT / "manifests/distribution.json").read_text())
        relative = str(path.relative_to(PROJECT)) if path.is_relative_to(PROJECT) else ""
        expected = inventory.get(relative, {}).get("distributed_sha256")
    if expected is None or not path.is_file() or sha256(path) != expected:
        raise ValueError(f"Missing, unregistered or changed frozen input: {path}")


for _source in ("physiograph_data_loader.py", "physiograph_training_runner.py",
                "clinical_timeseries_baselines.py", "organ_graph_ssm_model.py"):
    verify_input(PROJECT / "src" / _source)
verify_input(PROJECT / "tools/v4_protocol.py")
import v4_protocol as v4
sys.path.insert(0, str(HERE))
MODELS = v4.MODELS + LEARNED_MODELS


def selected_config(model, path=SELECTION):
    verify_input(path)
    choice = json.loads(Path(path).read_text())["models"][model]
    if choice["status"] != "selected" or choice["sizes"] != v4.sizes_for(model, choice["width"]):
        raise ValueError(f"Missing/inconsistent selected configuration: {model}")
    return choice


def checkpoint_for(model, seed):
    if model in v4.MODELS:
        return PROJECT / "runs/clinical/selected" / model / f"seed{seed}/checkpoint.pt"
    return PROJECT / "runs/learned_graphs" / model / f"cinc_{model}_s{seed}.pt"


def build_learned(model):
    root = PROJECT / "baselines"
    sources = [root / ("tpatchgnn_adapter.py" if model == "tpatchgnn" else "grafiti_adapter_v3.py")]
    if model == "grafiti":
        sources.append(root / "port_utils_v3.py")
    for source in sources:
        verify_input(source)
    # Import the distributed adapters without their separate training runners.
    sys.path.insert(0, str(root))
    if model == "tpatchgnn":
        from tpatchgnn_adapter import TPatchGNNAdapter
        return TPatchGNNAdapter(context_length=12)
    from grafiti_adapter_v3 import GraFITiAdapter
    return GraFITiAdapter()


def load_checkpoint(model, seed, path=None, device="cpu", selection=SELECTION):
    path = Path(path or checkpoint_for(model, seed)).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Missing CinC-2019 checkpoint: {path}. Run the clinical and learned_graphs suites in REPRODUCE.md first.")
    verify_input(REFERENCE_NPZ)
    payload = torch.load(path, map_location="cpu", weights_only=True)
    if model in v4.MODELS:
        choice = selected_config(model, selection)
        for key, expected in dict(model=model, seed=seed, C=12, K=12,
                                  sizes=choice["sizes"], variant="admissible").items():
            if payload[key] != expected:
                raise ValueError(f"Checkpoint {key} mismatch: {path}")
        if payload["cohort_sha256"] != sha256(REFERENCE_NPZ):
            raise ValueError("Checkpoint was not trained on frozen CinC-2019")
        record = json.loads((path.parent / "run.json").read_text())
        if (record["status"], record["scope"], record["checkpoint_sha256"]) != ("complete", "full", sha256(path)):
            raise ValueError("Transfer requires a completed full CinC-2019 fit and matching checkpoint hash")
        net = v4.build(model, choice["sizes"], payload["variant"])
        state = payload["state_dict"]
        config = dict(lr=choice["lr"], width=choice["width"], sizes=choice["sizes"],
                      variant=payload["variant"])
    else:
        source_run = path.with_suffix(".json")
        record = json.loads(source_run.read_text())
        if (record["model"], record["config"]["seed"], record["config"]["C"],
                record["config"]["K"]) != (model, seed, 12, 12):
            raise ValueError("Learned-graph checkpoint identity mismatch")
        if record["checkpoint"]["sha256"] != sha256(path):
            raise ValueError("Learned-graph checkpoint hash mismatch")
        if record["smoke"] or record["input"]["sha256"] != sha256(REFERENCE_NPZ):
            raise ValueError("Transfer requires a full learned-graph fit on frozen CinC-2019")
        net = build_learned(model)
        if record["architecture"] != net.config:
            raise ValueError("Learned-graph architecture mismatch")
        config = record["architecture"]
        state = payload
    net.load_state_dict(state, strict=True)
    net.to(device)
    return net, dict(path=str(path), sha256=sha256(path), config=config)


class StayWindows(ForecastWindows):
    """Keep the frozen normalization/window implementation and original row IDs."""
    def __init__(self, data, cohort, indices):
        arrays = [data[f"{cohort}_{key}"] for key in ("values", "mask", "static", "sepsis", "length")]
        super().__init__(*arrays, np.full(len(arrays[0]), cohort == "B", np.int32),
                         mean=data["norm_mean"], std=data["norm_std"], C=12, K=12)
        self.idx = np.asarray(indices, dtype=np.int64)

    def __getitem__(self, index):
        item = super().__getitem__(index)
        item["stay_index"] = int(self.idx[index])
        return item


def make_data(npz, protocol, batch=128, seed=0, max_stays=None):
    if protocol not in ("transfer", "within"):
        raise ValueError(protocol)
    if batch < 1:
        raise ValueError("batch must be positive")
    if max_stays is not None and not (8 <= max_stays <= 64):
        raise ValueError("smoke max_stays is a TOTAL cap between 8 and 64; omit for full runs")
    verify_input(npz)
    with np.load(npz, allow_pickle=False) as archive:
        data = {key: archive[key] for key in archive.files}
    verify_input(REFERENCE_NPZ)
    with np.load(REFERENCE_NPZ, allow_pickle=False) as reference:
        for key in ("features", "organ_names", "organ_slices"):
            if not np.array_equal(data[key], reference[key]):
                raise ValueError(f"Frozen feature/organ layout mismatch: {key}")
        for key in ("norm_mean", "norm_std"):
            expected = reference[key] if protocol == "transfer" else data[key + "_within2012"]
            if not np.array_equal(data[key], expected):
                raise ValueError(f"{protocol} normalization mismatch: {key}")
    if protocol == "transfer":
        if bool(data["training_allowed"]) or not np.array_equal(data["test_idx"], np.arange(4000)):
            raise ValueError("Transfer requires evaluation-only artifact and every set-A row")
        specs = [("testA", "A", data["test_idx"]), ("testB", "B", np.arange(4000))]
        limits = [max_stays // 2, max_stays - max_stays // 2] if max_stays else [None, None]
        static_cols = ["Age", "Gender", "Unit1", "Unit2", "HospAdmTime"]
        expected_counts = dict(testA=3989, testB=3993)
    else:
        if len(data["test_idx"]) or "training_allowed" in data:
            raise ValueError("Within protocol requires the artifact with empty test_idx")
        if len(np.intersect1d(data["train_idx"], data["val_idx"])):
            raise ValueError("Within train/validation overlap")
        specs = [("train", "A", data["train_idx"]), ("val", "A", data["val_idx"]),
                 ("testB", "B", np.arange(4000))]
        limits = [max_stays // 2, max_stays // 8, max_stays - max_stays // 2 - max_stays // 8] if max_stays else [None] * 3
        static_cols = ["Age", "Gender", "Height", "Weight", "ICUType"]
        expected_counts = dict(train=3390, val=599, testB=3993)
    if data["static_cols"].tolist() != static_cols:
        raise ValueError("Wrong static descriptor layout for the protocol")
    loaders, full_counts, retained_counts, ids, record_ids = {}, {}, {}, {}, {}
    for (label, cohort, indices), limit in zip(specs, limits):
        indices = np.asarray(indices, dtype=np.int64)
        retained_counts[label] = len(indices)
        eligible = indices[data[f"{cohort}_length"][indices] >= 24]
        full_counts[label] = len(eligible)
        if limit is not None:
            eligible = np.random.default_rng(0).permutation(eligible)[:limit]
        ds = StayWindows(data, cohort, eligible)
        loaders[label] = DataLoader(ds, batch_size=batch, shuffle=label == "train", num_workers=0,
                                    generator=torch.Generator().manual_seed(seed))
        ids[label] = eligible.tolist()
        record_ids[label] = data[f"{cohort}_record_id"][eligible].tolist()
    if full_counts != expected_counts:
        raise ValueError(f"CinC-2012 eligible counts changed: {full_counts}")
    meta = dict(C=12, K=12, features=data["features"].tolist(),
                organ_names=data["organ_names"].tolist(), organ_slices=data["organ_slices"].tolist(),
                cohort_path=str(Path(npz).resolve()), cohort_sha256=sha256(npz),
                retained_counts=retained_counts, eligible_counts=full_counts,
                counts={k: len(v.dataset) for k, v in loaders.items()},
                split_stay_indices=ids, split_record_ids=record_ids,
                norm_mean=data["norm_mean"].tolist(), norm_std=data["norm_std"].tolist(),
                normalization="frozen CinC-2019 A-train" if protocol == "transfer" else "CinC-2012 set-A train only",
                static_cols=static_cols, max_stays=max_stays,
                testA_empty_by_design=protocol == "within", sepsis_labels_available=False)
    if protocol == "within":
        for key in ("counts", "eligible_counts", "retained_counts", "split_stay_indices", "split_record_ids"):
            meta[key]["testA"] = [] if key.startswith("split_") else 0
    print(f"[{protocol}] eligible stays={meta['eligible_counts']}; used={meta['counts']}", flush=True)
    return loaders, meta


def output_dir(root, protocol, model, seed):
    dest = owned_path(Path(root) / protocol / model / f"seed{seed}")
    if dest.exists() and any(dest.iterdir()):
        raise FileExistsError(f"Preserve existing completed/partial run: {dest}")
    return dest


def evaluate_split(model, loader, meta, device, dest, split):
    errors = v4.collect_errors(model, loader, 12, device, meta["organ_slices"])
    if errors["nonfinite"].sum() or not np.isfinite(errors["sse"]).all():
        raise ValueError(f"Nonfinite predictions/errors in {split}")
    v4.save_errors(owned_path(dest / f"errors_{split}.npz"), errors)
    return errors, v4.metrics(errors, meta["organ_names"])


def runtime_sources():
    paths = [PROJECT / "tools/v4_protocol.py", PROJECT / "src/physiograph_data_loader.py",
             PROJECT / "src/clinical_timeseries_baselines.py", PROJECT / "src/organ_graph_ssm_model.py",
             PROJECT / "baselines/tpatchgnn_adapter.py", PROJECT / "baselines/grafiti_adapter_v3.py",
             PROJECT / "baselines/port_utils_v3.py", *sorted(HERE.glob("*.py"))]
    return {str(p.relative_to(PROJECT)): sha256(p) for p in paths}


def setup_device(device, threads):
    if threads < 1:
        raise ValueError("threads must be positive")
    torch.set_num_threads(threads)
    selected = torch.device(device)
    if selected.type not in ("cpu", "cuda"):
        raise ValueError("Use an explicit cpu or cuda device")
    if selected.type == "cuda":
        torch.cuda.set_device(selected)
    return str(selected)
