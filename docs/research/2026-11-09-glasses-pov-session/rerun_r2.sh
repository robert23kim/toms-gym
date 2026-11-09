#!/bin/bash
# rerun_r2.sh <stems.txt> <tag>   sequential track_v3 runs, one torch process at a time, detached with nohup
S=/Users/toka/code/toms_gym/docs/research/2026-11-09-glasses-pov-session
PY=/Users/toka/code/bowling-app/analysis-engine/.venv/bin/python
LIST=$1; TAG=$2
DONE=$S/work/rerun_r2_$TAG.done
mkdir -p "$S/work/v3"
rm -f "$DONE"
STEMS=($(cat "$LIST"))
N=${#STEMS[@]}
T0=$(date +%s)
echo "=== rerun_r2 $TAG start $(date '+%F %T') pid $$ n=$N"
failed=()
i=0
for stem in "${STEMS[@]}"; do
  i=$((i+1))
  /usr/bin/python3 -I -c '
import os, subprocess, sys, time
me = os.getpid(); t0 = time.time(); said = False
while time.time() - t0 < 2400:
    ps = subprocess.run(["ps", "-axo", "pid=,command="], capture_output=True, text=True).stdout.splitlines()
    busy = [l.strip()[:160] for l in ps if ("track_v3.py" in l or "motion-only/run.py" in l or "track_v2.py" in l)
            and l.split()[0] != str(me) and " -c " not in l]
    if not busy:
        break
    if not said:
        print("    waiting for other torch process:", busy[0], flush=True); said = True
    time.sleep(15)
'
  extra=()
  if [ $i -eq 1 ]; then extra=(--audit-log "$S/work/v3/audit_open_rerun_r2_${TAG}_$stem.tsv"); fi
  echo "=== [$i/$N] $stem start $(date '+%T')"
  t=$(date +%s)
  "$PY" -I "$S/track_v3.py" "$stem" --device mps "${extra[@]}"
  rc=$?
  echo "=== [$i/$N] $stem rc=$rc wall=$(( $(date +%s) - t ))s"
  if [ $rc -ne 0 ]; then failed+=("$stem"); fi
done
fl=""
for f in "${failed[@]}"; do fl="$fl\"$f\","; done
echo "{\"finished\": \"$(date '+%F %T')\", \"tag\": \"$TAG\", \"n\": $N, \"failed_stems\": [${fl%,}], \"wall_s\": $(( $(date +%s) - T0 ))}" > "$DONE"
echo "=== rerun_r2 $TAG done $(date '+%F %T') failed: ${failed[*]:-none}"
