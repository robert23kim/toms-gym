#!/bin/bash
S=/Users/toka/code/toms_gym/docs/research/2026-11-09-glasses-pov-session
/usr/bin/python3 -I -c '
import os, time
p = "/Users/toka/code/toms_gym/docs/research/2026-11-09-glasses-pov-session/work/rerun_r1.done"
t0 = time.time()
while not os.path.exists(p) and time.time() - t0 < 5400:
    time.sleep(20)
print("rerun_r1.done seen" if os.path.exists(p) else "gave up waiting after 90 min", flush=True)
'
echo "=== starting run_missing after rerun round 1 $(date '+%F %T')"
exec bash "$S/run_missing.sh"
