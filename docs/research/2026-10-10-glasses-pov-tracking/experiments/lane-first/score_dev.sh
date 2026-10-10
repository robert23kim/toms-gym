#!/bin/bash
# Run + score every dev stem, print one compact row each.
L=/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking
E=$L/experiments/lane-first
PY=/Users/toka/code/bowling-app/analysis-engine/.venv/bin/python
for s in 20260915_185121_23d80f05 20260915_185331_19de9ec7 20260915_185645_9fde3c16 20260915_185454_f240c883 20260915_190115_a7cf2c70; do
  $PY $E/run.py $s > /dev/null 2> $E/work/${s}_err.txt || { echo "$s RUN FAILED"; tail -3 $E/work/${s}_err.txt; continue; }
  $PY $L/score_tracks.py $E/tracks/$s.json $L/truth/$s.json | $PY -c "
import json,sys; d=json.load(sys.stdin); t=json.load(open('$E/tracks/$s.json'))
print('%s recall %5.1f (%d/%d) med_px %s board_err %s lane_err %s win %s pass %s | fb %s det %s fill %s wall %s' % (d['stem'][9:15], d['recall_pct'], d['n_matched'], d['n_truth_points'], d['median_px_err'], d['board_err'], d['lane_err_boards'], d['window_err'], d['pass'], t['final_board'], t['meta']['n_det'], t['meta']['n_fill'], t['meta']['wall_s']))"
done
