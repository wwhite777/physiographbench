#!/usr/bin/env python3
"""maintainer fetcher (2026-11-04): CinC-2019 training sets from the public S3 mirror (physionet-open), listed with ListObjectsV2,
downloaded 24-way with retries; skips existing non-empty files; verifies every file is non-empty and starts with the header line."""

# Resolve all public modules and scratch from the release root.
import sys as _release_sys
from pathlib import Path as _ReleasePath
_release_sys.path.insert(0, str(_ReleasePath(__file__).resolve().parents[1]))
from release_paths import ROOT as RELEASE_ROOT, SCRATCH as RELEASE_SCRATCH
import os, sys, time, urllib.request, urllib.parse, xml.etree.ElementTree as ET, concurrent.futures as cf
BUCKET = 'https://physionet-open.s3.amazonaws.com'
ROOT = str(RELEASE_ROOT / 'data')
def list_keys(prefix):
    keys, token = [], None
    while True:
        q = {'list-type': '2', 'prefix': prefix, 'max-keys': '1000'}
        if token: q['continuation-token'] = token
        url = BUCKET + '/?' + urllib.parse.urlencode(q)
        for attempt in range(5):
            try:
                xml = urllib.request.urlopen(url, timeout=60).read(); break
            except Exception as e:
                time.sleep(2 * (attempt + 1)); err = e
        else:
            raise RuntimeError(f'listing failed: {err}')
        ns = {'s3': 'http://s3.amazonaws.com/doc/2006-03-01/'}
        root = ET.fromstring(xml)
        keys += [c.find('s3:Key', ns).text for c in root.findall('s3:Contents', ns)]
        trunc = root.find('s3:IsTruncated', ns).text == 'true'
        token = root.find('s3:NextContinuationToken', ns).text if trunc else None
        if not trunc: break
    return [k for k in keys if k.endswith('.psv')]
def fetch(key):
    dest = os.path.join(ROOT, key.split('/training/')[1])
    if os.path.exists(dest) and os.path.getsize(dest) > 0: return 'kept'
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    for attempt in range(6):
        try:
            data = urllib.request.urlopen(BUCKET + '/' + key, timeout=60).read()
            if data and data.startswith(b'HR|'):
                with open(dest + '.part', 'wb') as f: f.write(data)
                os.replace(dest + '.part', dest); return 'ok'
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    return 'FAIL ' + key


def main():
    import argparse
    global ROOT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=str, default=str(RELEASE_ROOT / "data"), help="raw-data output directory")
    args = parser.parse_args()
    ROOT = args.root
    t0 = time.time(); log = lambda m: print(f'[s3 {time.strftime("%H:%M:%S", time.gmtime())}] {m}', flush=True)
    allkeys = []
    for s in ('training_setA', 'training_setB'):
        k = list_keys(f'challenge-2019/1.0.0/training/{s}/'); log(f'{s}: {len(k)} keys'); allkeys += k
    with cf.ThreadPoolExecutor(24) as ex:
        res = list(ex.map(fetch, allkeys))
    log(f"done in {time.time()-t0:.0f}s: ok={res.count('ok')} kept={res.count('kept')} fail={sum(r.startswith('FAIL') for r in res)}")
    for r in res:
        if r.startswith('FAIL'): print(r)
    for s in ('training_setA', 'training_setB'):
        d = os.path.join(ROOT, s); files = [f for f in os.listdir(d) if f.endswith('.psv')]
        empty = [f for f in files if os.path.getsize(os.path.join(d, f)) == 0]
        log(f'{s}: {len(files)} files, {len(empty)} empty')


if __name__ == "__main__":
    main()
