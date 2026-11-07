"""Run physics-smoother on the 5 dev stems sequentially, score each with L2/score_v2.py, write results/dev.json
(rows, means with the same keys as results/baseline_v2.json, the baseline rows and per-metric deltas). Dev only."""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
L2 = os.path.dirname(os.path.dirname(HERE))
PY = sys.executable
DEV = ['20260915_185121_23d80f05', '20260915_185331_19de9ec7', '20260915_185454_f240c883',
       '20260915_185645_9fde3c16', '20260915_190115_a7cf2c70']
MEAN_KEYS = ['recall_pct', 'far_recall_pct', 'median_px_err', 'far_median_px_err', 'path_err_rms', 'path_err_far',
             'path_bias', 'path_bias_far', 'path_missing', 'entry_err', 'hook_err', 'wall_s']
rows = []
for s in DEV:
    subprocess.run([PY, os.path.join(HERE, 'run.py'), s, '--device', 'mps'], check=True)
    tp = os.path.join(HERE, 'tracks', f'{s}.json')
    th = os.path.join(L2, 'truth', f'{s}.json')
    r = json.loads(subprocess.run([PY, os.path.join(L2, 'score_v2.py'), tp, th], check=True, capture_output=True, text=True).stdout)
    tr = json.load(open(tp))
    r['wall_s'] = tr['meta'].get('wall_s')
    r['wall_s_note'] = 'seconds on top of the saved loop-1 track (no torch); loop-1 wall_s is in meta.base_meta'
    r['base_wall_s'] = (tr['meta'].get('base_meta') or {}).get('wall_s')
    r['final_board'] = tr.get('final_board')
    r['final_board_engine'] = tr['meta'].get('final_board_engine')
    pf = tr.get('path_fit') or {}
    r['fit_kind'] = pf.get('kind')
    r['chose_hook'] = pf.get('chose_hook')
    r['fit_params'] = pf.get('params')
    r['fit_selection'] = pf.get('selection')
    r['fit_residual_rms_boards'] = pf.get('residual_rms_boards')
    km = tr.get('ft_model') or {}
    r['ft_model'] = {k: km.get(k) for k in ('a', 'd0_ft', 'v0_ft_per_frame', 'decel_ft_per_frame2', 'rmse_ft', 'implied_pin_frame', 'implied_minus_hand_pin_hit')}
    r['scored'] = True
    rows.append(r)
means = {}
for k in MEAN_KEYS:
    v = [float(r[k]) for r in rows if r.get(k) is not None]
    means[k] = round(sum(v) / len(v), 2) if v else None
    means[f'{k}_n'] = len(v)
d = [r['direction_ok'] for r in rows if r.get('direction_ok') is not None]
means['direction_ok_pct'] = round(100.0 * sum(d) / len(d), 1) if d else None
means['direction_ok_n'] = len(d)
base = json.load(open(os.path.join(L2, 'results', 'baseline_v2.json')))
bm = base['means']
delta = {k: (None if means.get(k) is None or bm.get(k) is None else round(means[k] - bm[k], 2))
         for k in MEAN_KEYS + ['direction_ok_pct']}
per_stem_vs_base = []
for r in rows:
    b = next((x for x in base['rows'] if x['stem'] == r['stem']), {})
    per_stem_vs_base.append({'stem': r['stem'], **{k: [b.get(k), r.get(k)] for k in ['path_err_rms', 'path_err_far', 'entry_err', 'hook_err', 'direction_ok']}})
out = {'experiment': 'physics-smoother', 'stage': 'path', 'base_tracks': 'L1/results/tracks (sam2-video)',
       'scorer': 'score_v2.py', 'truth_dir': os.path.join(L2, 'truth'), 'stems': DEV, 'rows': rows, 'means': means,
       'baseline_means': bm, 'delta_vs_baseline': delta, 'per_stem_vs_baseline': per_stem_vs_base}
os.makedirs(os.path.join(HERE, 'results'), exist_ok=True)
json.dump(out, open(os.path.join(HERE, 'results', 'dev.json'), 'w'), indent=1)
print(json.dumps({'means': means, 'delta_vs_baseline': delta}, indent=1))
for p in per_stem_vs_base:
    print(p)
