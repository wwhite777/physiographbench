#!/usr/bin/env python3
"""Fetch the three open inputs used by the CinC-2012 cohort builder."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from release_paths import ROOT
import argparse
import hashlib
import urllib.request

BASE = 'https://physionet.org/files/challenge-2012/1.0.0/'
FILES = {
    'set-a.zip': '1433638192fda622e8bb11a4559b8af2dbb1c69f0e1c3b5b606cc12aabd0a4c5',
    'set-b.zip': '54094c39631797af554ad4233164e004a699521351bd2f2bed50d6564ebc56dc',
    'Outcomes-a.txt': '2613ea60ccda29f87571a7d6b09ad130858a8ccd66325bd073365925026883c2',
}

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=ROOT / 'data/cinc2012')
    args = ap.parse_args()
    args.root.mkdir(parents=True, exist_ok=True)
    for name, expected in FILES.items():
        out = args.root / name
        if not out.exists():
            part = out.with_suffix(out.suffix + '.part')
            urllib.request.urlretrieve(BASE + name, part)
            if hashlib.sha256(part.read_bytes()).hexdigest() != expected:
                raise ValueError(f'Input hash mismatch: {name}; partial file retained')
            part.rename(out)
        if hashlib.sha256(out.read_bytes()).hexdigest() != expected:
            raise ValueError(f'Input hash mismatch: {name}')
        print(f'{expected}  {out}')

if __name__ == '__main__':
    main()
