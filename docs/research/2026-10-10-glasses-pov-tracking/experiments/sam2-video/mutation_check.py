"""Shift a finished track by +100 px in x (lane too) and score it: the scorer must drop recall hard."""
import json, subprocess, sys, copy, os
L = '/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking'
X = os.path.join(L, 'experiments', 'sam2-video')
PY = '/Users/toka/code/bowling-app/analysis-engine/.venv/bin/python'
stem = sys.argv[1]
tr = json.load(open(f'{X}/tracks/{stem}.json'))
mut = copy.deepcopy(tr)
for p in mut['frames']:
    p['x'] += 100.0
for q in mut['lane'].values():
    for k in ('fl_l', 'fl_r', 'pd_l', 'pd_r'):
        q[k][0] += 100.0
if mut['final_board'] is not None:
    mut['final_board'] += 5
os.makedirs(f'{X}/work/mutation', exist_ok=True)
mp = f'{X}/work/mutation/{stem}_shift100.json'
json.dump(mut, open(mp, 'w'))
for label, path in (('original', f'{X}/tracks/{stem}.json'), ('shift+100px,board+5', mp)):
    out = subprocess.run([PY, f'{L}/score_tracks.py', path, f'{L}/truth/{stem}.json'], capture_output=True, text=True)
    d = json.loads(out.stdout); d.pop('lane_err_per_frame')
    print(label, {k: d[k] for k in ('recall_pct', 'n_matched', 'median_px_err', 'board_err', 'lane_err_boards')})
