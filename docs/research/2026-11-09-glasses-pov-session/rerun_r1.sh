#!/bin/bash
S=/Users/toka/code/toms_gym/docs/research/2026-11-09-glasses-pov-session
PY=/Users/toka/code/bowling-app/analysis-engine/.venv/bin/python
DONE=$S/work/rerun_r1.done
mkdir -p "$S/work/v3"
rm -f "$DONE"
STEMS=(
20261108_104714_593f3a1d 20261108_105857_afb68558 20261108_110622_9060f40e 20261108_112413_aa021459
20261108_113541_fd941fc1 20261108_113716_f433d7d5 20261108_114059_25d4ce4d 20261108_114438_abe7fcc1
20261108_114631_01d562c5 20261108_114810_62ef90d8 20261108_114919_768b5f15 20261108_115157_0e03a53c
)
N=${#STEMS[@]}
T0=$(date +%s)
echo "=== run_all start $(date '+%F %T') pid $$ n=$N (rerun round 1: the 12 judge rerun stems)"
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
  if [ $i -eq 1 ]; then extra=(--audit-log "$S/work/v3/audit_open_rerun_r1_$stem.tsv"); fi
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
echo "=== run_all done $(date '+%F %T') failed: ${failed[*]:-none}"
