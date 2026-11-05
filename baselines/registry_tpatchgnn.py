"""Local registration with the learned_graph_baselines build_adapter interface; no upstream imports."""

# Resolve all public modules and scratch from the release root.
import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[1]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH
from tpatchgnn_adapter import TPatchGNNAdapter

REGISTRY = {'tpatchgnn': TPatchGNNAdapter}
PORT_STATUS = {'tpatchgnn': 'paper adaptation; see METHODS.md'}


def build_adapter(name, n_feat=16, n_static=5, **runner_sizes):
    # Preserve published architecture sizes rather than shared recurrent sizes.
    context_length = runner_sizes.get('context_length', 12)
    return REGISTRY[name](n_feat=n_feat, n_static=n_static, context_length=context_length)
