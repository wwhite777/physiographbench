"""Data-free record integrity and explicit repository-relative locations."""
from pathlib import Path
import hashlib
import json
import math
import os

ROOT = Path(os.environ.get("PHYSIOGRAPH_ROOT", Path(__file__).absolute().parent))

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read(location, root=ROOT):
    path, _, fragment = str(location).partition("#")
    if Path(path).is_absolute() or ".." in Path(path).parts:
        raise ValueError("Expected a repository-relative record location")
    obj = json.loads((root / path).read_text())
    if fragment:
        for part in fragment.lstrip("/").split("/"):
            key = part.replace("~1", "/").replace("~0", "~")
            obj = obj[int(key)] if isinstance(obj, list) else obj[key]
    return obj

def verify(path, root=ROOT):
    path = Path(path)
    if not path.is_absolute(): path = root / path
    relative = path.relative_to(root).as_posix()
    inventory = read("manifests/distribution.json", root)
    expected = inventory.get(relative, {}).get("distributed_sha256")
    if expected is None and path.suffix == '.npz':
        expected = read('manifests/cohorts.json',root).get(relative,{}).get('sha256')
    if expected is None or digest(path) != expected:
        raise ValueError(f"Missing or changed distributed input: {relative}")
    return path

def finite(value):
    if isinstance(value, dict):
        for v in value.values(): finite(v)
    elif isinstance(value, list):
        for v in value: finite(v)
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Nonfinite numerical record field")

def clinical(record, seed, cap):
    finite(record)
    if record.get("seed") != seed or record.get("status") != "complete" or record.get("failure") is not None:
        raise ValueError("Incomplete or incorrect clinical identity")
    if record.get("scope", "full") != "full" or record["epochs_budget"] != cap:
        raise ValueError("Wrong clinical scope or cap")
    if "epochs_completed" in record:
        done, best = record["epochs_completed"], record["best_epoch"]
        patience = record.get("patience", 8)
        if not 1 <= best <= done <= cap or done-best > patience or (done < cap and done-best != patience):
            raise ValueError("Invalid completion or stopping fields")
    return record
