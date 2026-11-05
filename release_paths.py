"""Repository paths shared by the portable experiment entry points."""
from pathlib import Path
import os
import sys

ROOT = Path(os.environ.get('PHYSIOGRAPH_ROOT', Path(__file__).resolve().parent)).resolve()
SCRATCH = Path(os.environ.get('TMPDIR', ROOT / '.scratch')).resolve()
SCRATCH.mkdir(parents=True, exist_ok=True)
os.environ['TMPDIR'] = str(SCRATCH)
os.environ.setdefault('MPLCONFIGDIR', str(SCRATCH / 'matplotlib'))
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.dont_write_bytecode = True
for folder in ('src', 'tools', 'sim', 'baselines'):
    sys.path.insert(0, str(ROOT / folder))
