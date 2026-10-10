#!/bin/zsh
# run + score every dev stem sequentially; args passed to run.py
D=/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking/experiments/cam-diff
L=/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking
PY=/Users/toka/code/bowling-app/analysis-engine/.venv/bin/python
TAG=${TAG:-main}
mkdir -p $D/work/scores_$TAG
for s in 20260915_185121_23d80f05 20260915_185331_19de9ec7 20260915_185645_9fde3c16 20260915_185454_f240c883 20260915_190115_a7cf2c70; do
  $PY $D/run.py $s "$@" > $D/work/scores_$TAG/$s.log 2>&1
  echo "RC $? $s"
  $PY $L/score_tracks.py $D/tracks/$s.json $L/truth/$s.json > $D/work/scores_$TAG/$s.json
  $PY -c "import json;d=json.load(open('$D/work/scores_$TAG/$s.json'));m=json.load(open('$D/tracks/$s.json'))['meta'];print('SCORE',d['stem'][9:15],'recall',d['recall_pct'],'px',d['median_px_err'],'board_err',d['board_err'],'lane_err',d['lane_err_boards'],'win',d['window_err'],'pass',d['pass'],'wall',m['wall_s'],'pin_src',m['pin_hit_source'])"
done
echo ALLDONE
