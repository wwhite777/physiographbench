#!/bin/bash
set -uo pipefail
D="${PHYSIOGRAPH_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}/data"; cd "$D"
echo "[fetch $(date -u +%H:%M:%S)] trying whole-project zip..."
curl -sL --max-time 2400 -o cinc.zip "https://physionet.org/content/challenge-2019/get-zip/1.0.0/" || true
sz=$(stat -c%s cinc.zip 2>/dev/null || echo 0); echo "[fetch] cinc.zip=$sz bytes"
if [ "$sz" -gt 5000000 ]; then
  unzip -q -o cinc.zip && rm -f cinc.zip && echo "[fetch] unzipped project zip"
else
  rm -f cinc.zip; echo "[fetch] zip unavailable -> recursive wget (slower, 40k files)"
  for S in training_setA training_setB; do
    echo "[fetch $(date -u +%H:%M:%S)] $S ..."
    wget -q -r -N -c -np -nH --cut-dirs=4 -R "index.html*" \
      "https://physionet.org/files/challenge-2019/1.0.0/training/$S/"
  done
fi
echo "[fetch $(date -u +%H:%M:%S)] DONE"
echo "[layout]"; find "$D" -maxdepth 3 -type d | grep -i training | head
echo "[psv count] A=$(find "$D" -path '*setA*' -name '*.psv'|wc -l) B=$(find "$D" -path '*setB*' -name '*.psv'|wc -l)"
du -sh "$D"
