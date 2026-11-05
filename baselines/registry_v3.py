"""grafiti_baseline integration point; no src mutation and no upstream imports."""

# Resolve all public modules and scratch from the release root.
import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[1]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH
from grafiti_adapter_v3 import GraFITiAdapter

REGISTRY = {'grafiti': GraFITiAdapter}
PORT_STATUS = {'grafiti': 'paper adaptation; see METHODS.md'}


def build_adapter(name, n_feat=16, n_static=5, **runner_sizes):
    """Keep the declared 64/4/2 choice within the paper's search ranges."""
    return REGISTRY[name](n_feat=n_feat, n_static=n_static)
