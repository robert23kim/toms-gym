#!/bin/bash
S=/Users/toka/code/toms_gym/docs/research/2026-11-09-glasses-pov-session
PY=/Users/toka/code/bowling-app/analysis-engine/.venv/bin/python
DONE=$S/work/run_missing.done
mkdir -p "$S/work/v3"
rm -f "$DONE"
STEMS=(
20261108_105322_bbdb3ef5 20261108_105652_31fc9b5e 20261108_110713_ab4ecb80 20261108_112146_61935a3b
20261108_112800_0c01c7c1 20261108_113113_2504dbca 20261108_113911_e5c680e6 20261108_114236_5184e3d7
20261108_115105_6698185a
)
N=${#STEMS[@]}
T0=$(date +%s)
echo "=== run_missing start $(date '+%F %T') pid $$ n=$N (9 stems the first batch skipped)"
failed=()
i=0
for stem in "${STEMS[@]}"; do
  i=$((i+1))
  /usr/bin/python3 -I -c '
import os, subprocess, sys, time
me = os.getpid(); t0 = time.time(); said = False
while time.time() - t0 < 1800:
    ps = subprocess.run(["ps", "-axo", "pid=,command="], capture_output=True, text=True).stdout.splitlines()
    busy = [l.strip()[:160] for l in ps if "analysis-engine/.venv/bin/python" in l and str(me) not in l.split()[0]]
    if not busy:
        break
    if not said:
        print("    waiting for other torch process:", busy[0], flush=True); said = True
    time.sleep(15)
'
  extra=()
  :
  echo "=== [$i/$N] $stem start $(date '+%T')"
  t=$(date +%s)
  "$PY" -I "$S/track_v3.py" "$stem" --device mps "${extra[@]}"
  rc=$?
  echo "=== [$i/$N] $stem rc=$rc wall=$(( $(date +%s) - t ))s"
  if [ $rc -ne 0 ]; then failed+=("$stem"); fi
done
fl=""
for f in "${failed[@]}"; do fl="$fl\"$f\","; done
echo "{\"finished\": \"$(date '+%F %T')\", \"n\": $N, \"failed_stems\": [${fl%,}], \"wall_s\": $(( $(date +%s) - T0 ))}" > "$DONE"
echo "=== run_missing done $(date '+%F %T') failed: ${failed[*]:-none}"
