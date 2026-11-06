import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parents[1]))
from release_paths import SCRATCH
SCRATCH.mkdir(parents=True, exist_ok=True)
for name in ('TMPDIR', 'TEMP', 'TMP'):
    os.environ[name] = str(SCRATCH)
