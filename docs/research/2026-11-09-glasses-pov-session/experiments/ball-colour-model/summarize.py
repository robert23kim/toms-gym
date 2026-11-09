"""summarize.py: dev proxies per stem and means from tracks/*.json (dev stems only)."""
import json, os, statistics
X = os.path.dirname(os.path.abspath(__file__))
S = '/Users/toka/code/toms_gym/docs/research/2026-11-09-glasses-pov-session'
dev = json.load(open(os.path.join(S, 'results', 'split.json')))['dev_stems']
rows = []
for s in dev:
    p = os.path.join(X, 'tracks', f'{s}.json')
    if not os.path.exists(p):
        rows.append({'stem': s, 'missing': True}); continue
    t = json.load(open(p)); pr = t['proxies']; ev = t['events']; m = t['meta']; bm = m.get('ball_meta') or {}
    rows.append({'stem': s, 'model': t['stages']['ball_model']['kind'], 'lab': t['stages']['ball_model']['lab'], 'ab_tol': t['stages']['ball_model']['ab_tol'],
                 'detection_rate': pr['detection_rate'], 'window': pr['window'], 'max_board_jump': pr['max_board_jump_med5'],
                 'pin_row_detected': pr['pin_row_detected'], 'pin_row': t['pin_row_frame_est'], 'cut_pin': t['pin_hit_frame'],
                 'pin_row_source': ev['pin_row_source'][:40], 'entry': ev['entry_board'], 'exit': ev['exit_board'], 'break_ft': ev['breakpoint_ft'],
                 'coarse_points': m.get('coarse_points'), 'coasted': bm.get('coasted'), 'refined': bm.get('refined'), 'reprompts': bm.get('sam_reprompts'),
                 'gates': bm.get('gates'), 'fallback': t['fallback'], 'rejected': sorted(int(k) for k in (t.get('series_rejected') or {})),
                 'wall_s': m['wall_s'], 'stage_s': m.get('stage_s')})
ok = [r for r in rows if not r.get('missing')]
summary = {'n_dev': len(ok), 'n_missing': len(rows) - len(ok),
           'detection_rate_mean': round(statistics.mean(r['detection_rate'] for r in ok), 3) if ok else None,
           'max_board_jump_mean': round(statistics.mean(r['max_board_jump'] for r in ok if r['max_board_jump'] is not None), 2) if ok else None,
           'pin_row_detected': sum(1 for r in ok if r['pin_row_detected']),
           'runtime_s_per_clip_mean': round(statistics.mean(r['wall_s'] for r in ok), 1) if ok else None,
           'runtime_s_per_clip_max': max((r['wall_s'] for r in ok), default=None)}
json.dump({'summary': summary, 'per_stem': rows}, open(os.path.join(X, 'dev_proxies.json'), 'w'), indent=1)
print(json.dumps(summary))
for r in rows:
    print(json.dumps(r))
