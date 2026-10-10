#!/bin/bash
# run_dev.sh <stem>... : run.py + score each stem sequentially; one line per stem appended to dev_scores.jsonl
X=/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking/experiments/sam2-video
L=/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking
PY=/Users/toka/code/bowling-app/analysis-engine/.venv/bin/python
DEV="${DEVICE:-mps}"
cd /Users/toka/code/bowling-app/pov-engine || exit 1
for s in "$@"; do
  $PY $X/run.py "$s" --device "$DEV" 2>&1 | grep -v "^$" | grep -v Ultralytics | tee "$X/work/log_$s.txt"
  if [ -f "$L/truth/$s.json" ]; then
    $PY $L/score_tracks.py "$X/tracks/$s.json" "$L/truth/$s.json" | $PY -c "
import json,sys; d=json.load(sys.stdin); d.pop('lane_err_per_frame'); tr=json.load(open('$X/tracks/$s.json')); d['wall_s']=tr['meta'].get('wall_s'); d['device']='$DEV'; print(json.dumps(d))" | tee -a "$X/dev_scores.jsonl"
  fi
done
