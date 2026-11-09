#!/usr/bin/env python3
"""Score auto_cuts.py entries against the loop-1 labels (cuts.json) and the loop-2 truth pin_row.

usage: score_auto_cuts.py <entries_dir> [--shift-release N] [--set-cut-end STEM=FRAME] [--json OUT]
release_err = auto - cuts.json release_frame; pin_err = auto pin_hit - cuts.json pin_hit_frame.
contains   = cut_start <= release_label - 5 and cut_end >= pin_row + 15, pin_row = loop-2 truth pin_row_frame where
             present, else cuts.json pin_hit + 10.
--shift-release and --set-cut-end are mutations: they move the entry the scorer reads (cut_start/cut_end follow a
release shift with the auto_cuts rule) to prove the error and containment columns can change.
"""
import argparse, glob, json, os, statistics
L1 = '/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking/work/cuts/cuts.json'
TR = '/Users/toka/code/toms_gym/docs/research/2026-11-07-glasses-pov-hook/truth/'
DEV = {'20260915_185121_23d80f05', '20260915_185331_19de9ec7', '20260915_185645_9fde3c16'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('entries')
    ap.add_argument('--shift-release', type=int, default=0)
    ap.add_argument('--set-cut-end', action='append', default=[])
    ap.add_argument('--json')
    a = ap.parse_args()
    lab = {c['stem']: c for c in json.load(open(L1))}
    setce = dict(x.split('=') for x in a.set_cut_end)
    rows = []
    for f in sorted(glob.glob(os.path.join(a.entries, '*.json'))):
        e = json.load(open(f))
        s = e['stem']
        c = lab.get(s)
        if c is None:
            continue
        tp = os.path.join(TR, s + '.json')
        pr = json.load(open(tp)).get('pin_row_frame') if os.path.exists(tp) else None
        if e['release_frame'] is not None and a.shift_release:
            e['release_frame'] += a.shift_release
            e['cut_start'] += a.shift_release
            e['cut_end'] += a.shift_release
        if s in setce:
            e['cut_end'] = int(setce[s])
        r = {'stem': s, 'split': 'dev' if s in DEV else 'holdout', 'label_release': c['release_frame'],
             'label_pin_hit': c['pin_hit_frame'], 'auto_release': e['release_frame'], 'auto_pin_hit': e['pin_hit_frame'],
             'release_source': e.get('release_source'), 'cut_path': e['cut_path'], 'verified': e['verified'],
             'notes': e.get('notes')}
        if c['release_frame'] is None:
            r['no_throw_ok'] = e['cut_path'] is None and e['release_frame'] is None
        elif e['release_frame'] is None:
            r['missed'] = True
        else:
            need_end = pr if pr is not None else c['pin_hit_frame'] + 10
            r.update({'release_err': e['release_frame'] - c['release_frame'],
                      'pin_err': e['pin_hit_frame'] - c['pin_hit_frame'],
                      'pin_row': need_end, 'pin_row_src': 'truth' if pr is not None else 'cuts pin_hit+10',
                      'cut': [e['cut_start'], e['cut_end']], 'need': [c['release_frame'] - 5, need_end + 15],
                      'contains': e['cut_start'] <= c['release_frame'] - 5 and e['cut_end'] >= need_end + 15,
                      'end_margin': e['cut_end'] - (need_end + 15)})
        rows.append(r)
    print(f"{'stem':26s} {'split':8s} {'lab_rel':>7s} {'auto':>5s} {'err':>4s} {'lab_pin':>7s} {'auto':>5s} {'err':>4s} "
          f"{'cut':>11s} {'need':>11s} contains margin verified source")
    for r in rows:
        if 'release_err' in r:
            print(f"{r['stem']:26s} {r['split']:8s} {r['label_release']:7d} {r['auto_release']:5d} {r['release_err']:+4d} "
                  f"{r['label_pin_hit']:7d} {r['auto_pin_hit']:5d} {r['pin_err']:+4d} {str(r['cut']):>11s} {str(r['need']):>11s} "
                  f"{str(r['contains']):8s} {r['end_margin']:+5d} {str(r['verified']):8s} {r['release_source'].split(' (')[0]}")
        else:
            print(f"{r['stem']:26s} {r['split']:8s} no_throw_ok={r.get('no_throw_ok')} missed={r.get('missed')} "
                  f"auto_release={r['auto_release']} notes={r['notes']}")
    for split in ('dev', 'holdout'):
        rr = [r for r in rows if r['split'] == split and 'release_err' in r]
        if rr:
            e = [abs(r['release_err']) for r in rr]
            p = [abs(r['pin_err']) for r in rr]
            print(f"{split}: n={len(rr)} release |err| mean {statistics.mean(e):.2f} max {max(e)}  "
                  f"pin |err| mean {statistics.mean(p):.1f} max {max(p)}  contains {sum(r['contains'] for r in rr)}/{len(rr)}  "
                  f"verified {sum(bool(r['verified']) for r in rr)}/{len(rr)}")
    if a.json:
        json.dump(rows, open(a.json, 'w'), indent=1)


if __name__ == '__main__':
    main()
