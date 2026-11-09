"""summarize.py [tag]: proxy table over the dev tracks (tracks/<stem><tag>.json) -> stdout markdown + proxies<tag>.json."""
import glob, json, os, statistics, sys

X = os.path.dirname(os.path.abspath(__file__))
tag = sys.argv[1] if len(sys.argv) > 1 else ''
rows = []
for p in sorted(glob.glob(os.path.join(X, 'tracks', f'*{tag}.json'))):
    name = os.path.basename(p)[:-5]
    if tag == '' and '_nosam' in name:
        continue
    if tag and not name.endswith(tag):
        continue
    t = json.load(open(p))
    pr, ev, px = t['proxy'], t['events'], t['meta']['timing']
    srcs = t['meta']['ball_meta']['sources']
    # diagnostic only: first real ball frame whose bottom (y + r) is at/above that frame's edge-lane pd row (wood top)
    pd_cross = None
    for q in t['frames']:
        lane = (t.get('lane') or {}).get(str(q['f']))
        if q['src'] == 'coast' or lane is None or q['f'] < t['release_frame'] + 8:
            continue
        pd = 0.5 * (lane['pd_l'][1] + lane['pd_r'][1])
        if q['y'] + (q['r'] or 0) <= pd:
            pd_cross = q['f']
            break
    rows.append({'stem': t['stem'].split('_')[1], 'points': len(t['frames']), 'sources': srcs,
                 'detection_rate': pr['detection_rate'], 'max_board_jump': pr['max_board_jump'],
                 'pin_row_detected': pr['pin_row_detected'], 'pin_row_source': pr['pin_row_source'][:28],
                 'pin_row': t['pin_row_frame_est'], 'cut_pin': t['pin_hit_frame'], 'geo': ev.get('pin_row_frame_geometric'),
                 'pin_motion': ev.get('pin_motion_frame'), 'pd_cross': pd_cross, 'last_real': ev.get('track_last_real_frame'), 'entry': ev.get('entry_board'), 'exit': ev.get('exit_board'),
                 'break_ft': ev.get('breakpoint_ft'), 'rise': ev.get('rise_after_break'), 'fallback': t['fallback'],
                 'rejected': sorted(int(k) for k in t.get('series_rejected') or {}), 'wall_s': px['wall_s'], 'sam_s': px.get('sam_s')})
hdr = ['stem', 'points', 'sources', 'detection_rate', 'max_board_jump', 'pin_row_detected', 'pin_row', 'cut_pin', 'geo', 'pin_motion', 'pd_cross', 'last_real',
       'entry', 'exit', 'break_ft', 'rise', 'fallback', 'rejected', 'wall_s', 'sam_s']
print('| ' + ' | '.join(hdr) + ' |')
print('|' + '---|' * len(hdr))
for r in rows:
    print('| ' + ' | '.join(str(r[h]) for h in hdr) + ' |')
m = lambda k: round(statistics.mean(v for v in (r[k] for r in rows) if v is not None), 3) if rows else None  # noqa: E731
summary = {'n_dev': len(rows), 'detection_rate_mean': m('detection_rate'), 'max_board_jump_mean': m('max_board_jump'),
           'pin_row_detected': sum(1 for r in rows if r['pin_row_detected']), 'wall_s_mean': m('wall_s'),
           'fallbacks': sum(1 for r in rows if r['fallback']), 'rows': rows}
print(json.dumps({k: v for k, v in summary.items() if k != 'rows'}))
json.dump(summary, open(os.path.join(X, f'proxies{tag}.json'), 'w'), indent=1)
