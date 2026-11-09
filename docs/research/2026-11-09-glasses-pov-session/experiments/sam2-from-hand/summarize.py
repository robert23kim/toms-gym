"""summarize.py: dev proxies over tracks/*.json (no truth). detection_rate = real (non-coast) frames / frames from
release+5 to pin_row_frame_est; max_board_jump = max frame-to-frame step of the 5-frame rolling median of
boards_clean_raw over release..pin_row; pin_row_detected = source not a fallback."""
import json
import os
import statistics
import sys

X = os.path.dirname(os.path.abspath(__file__))
DEV = ['20261108_104946_3b1b2308', '20261108_105652_31fc9b5e', '20261108_110442_d27f6c73', '20261108_111631_9c1e9211',
       '20261108_112800_0c01c7c1', '20261108_113911_e5c680e6', '20261108_114631_01d562c5', '20261108_115157_0e03a53c']


def rolling_med(fs, vals, k=5):
    h = k // 2
    return [statistics.median([vals[j] for j in range(len(fs)) if abs(fs[j] - fs[i]) <= h]) for i in range(len(fs))]


def proxies(t):
    rel, pr = t['release_frame'], t['pin_row_frame_est']
    real = {p['f'] for p in t['frames'] if p.get('src') != 'coast'}
    win = list(range(rel + 5, pr + 1))
    det = sum(1 for f in win if f in real) / max(1, len(win))
    clean = {int(k): v for k, v in (t.get('boards_clean_raw') or {}).items() if rel <= int(k) <= pr}
    fs = sorted(clean)
    jump = None
    if len(fs) >= 6:
        med = rolling_med(fs, [clean[f] for f in fs])
        jump = max(abs(med[i + 1] - med[i]) for i in range(len(med) - 1))
    src = t['events'].get('pin_row_source') or ''
    ev = t['events']
    return {'stem': t['stem'][9:15], 'detection_rate': round(det, 3), 'max_board_jump': None if jump is None else round(jump, 2),
            'pin_row_detected': not src.startswith('fallback'), 'pin_row_src': src.split(':')[0], 'pin_row': pr,
            'cut_pin_hit': t['pin_hit_frame'], 'entry': ev.get('entry_board'), 'exit_f': ev.get('exit_frame'),
            'deck': ev.get('deck_frames'), 'break_ft': ev.get('breakpoint_ft'), 'points': len(t['frames']),
            'gated': len((t['meta'].get('gate') or {}).get('gated') or []), 'refined': (t['meta'].get('gate') or {}).get('refined'),
            'rejected': sorted(int(k) for k in (t.get('series_rejected') or {})), 'prompt': t['meta'].get('prompt_src'),
            'prompt_k0': t['meta'].get('prompt_k0'), 'wall_s': t['meta'].get('wall_s'), 'sam_s': t['meta'].get('sam_s')}


def main():
    rows = []
    for s in DEV:
        p = os.path.join(X, 'tracks', f'{s}.json')
        if not os.path.exists(p):
            rows.append({'stem': s[9:15], 'missing': True})
            continue
        rows.append(proxies(json.load(open(p))))
    ok = [r for r in rows if not r.get('missing')]
    for r in rows:
        print(json.dumps(r))
    agg = {'n_dev': len(ok),
           'detection_rate_mean': round(statistics.mean(r['detection_rate'] for r in ok), 3) if ok else None,
           'max_board_jump_mean': round(statistics.mean(r['max_board_jump'] for r in ok if r['max_board_jump'] is not None), 2) if ok else None,
           'pin_row_detected': sum(1 for r in ok if r['pin_row_detected']),
           'wall_s_mean': round(statistics.mean(r['wall_s'] for r in ok if r['wall_s']), 1) if ok else None,
           'sam_s_mean': round(statistics.mean(r['sam_s'] for r in ok if r['sam_s']), 1) if ok else None}
    print(json.dumps(agg))
    json.dump({'rows': rows, 'agg': agg}, open(os.path.join(X, 'dev_summary.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
