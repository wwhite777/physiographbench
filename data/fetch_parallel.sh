#!/bin/bash
# Parallel CinC-2019 fetch: lists both hospital sets, downloads missing files
# with 24-way parallelism (skips files already present). Idempotent.
D="${PHYSIOGRAPH_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}/data"
base=https://physionet.org/files/challenge-2019/1.0.0/training
: > "$D/urls.txt"
for S in training_setA training_setB; do
  mkdir -p "$D/$S"
  curl -s --max-time 120 "$base/$S/" | grep -oE 'p[0-9]+\.psv' | sort -u > "$D/$S.list"
  echo "[par] $S listed $(wc -l < "$D/$S.list") files"
  while read -r f; do echo "$base/$S/$f $D/$S/$f"; done < "$D/$S.list" >> "$D/urls.txt"
done
echo "[par] total $(wc -l < "$D/urls.txt") urls; downloading missing (24-way)"
xargs -P 24 -n 2 sh -c '[ -f "$2" ] || curl -sf --max-time 60 -o "$2" "$1"' _ < "$D/urls.txt"
echo "[par] DONE A=$(find "$D/training_setA" -name '*.psv'|wc -l) B=$(find "$D/training_setB" -name '*.psv'|wc -l)"
du -sh "$D"
