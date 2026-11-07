"""Truth-side candidate scoring (dev only): recall before linking (any candidate within max(2r,15) px of the truth)
and after linking by N, far window pin_hit-12..pin_hit on truth frames. usage: score_cands.py <stem> [...]"""
import json
import math
import sys

HERE = '/Users/toka/code/toms_gym/docs/research/2026-11-07-glasses-pov-hook/experiments/far-end-stacking'
L2 = '/Users/toka/code/toms_gym/docs/research/2026-11-07-glasses-pov-hook'


def med(v):
    v = sorted(v)
    return None if not v else round(v[len(v) // 2] if len(v) % 2 else 0.5 * (v[len(v) // 2 - 1] + v[len(v) // 2]), 2)


def score(stem):
    d = json.load(open(f'{HERE}/work/{stem}_cands.json'))
    t = json.load(open(f'{L2}/truth/{stem}.json'))
    pin = t['pin_hit_frame']
    far = [p for p in t['path'] if pin - 12 <= p['f'] <= pin and p.get('x') is not None]
    row = {'stem': stem, 'n_far': len(far)}
    hit = 0
    for p in far:
        tol = max(2 * p['r'], 15.0)
        cs = d['cands'].get(str(p['f']), [])
        hit += any(math.hypot(c[0] - p['x'], c[1] - p['y']) <= tol for c in cs)
    row['pre_link_recall_pct'] = round(100.0 * hit / len(far), 1) if far else None
    row['pre_link_best_px'] = med([min(math.hypot(c[0] - p['x'], c[1] - p['y']) for c in d['cands'].get(str(p['f']), [[1e9, 1e9]])) for p in far])
    for N, lk in sorted(d['by_n'].items(), key=lambda kv: int(kv[0])):
        hit, errs = 0, []
        for p in far:
            tol = max(2 * p['r'], 15.0)
            s = lk.get(str(p['f']))
            if s is None:
                continue
            e = math.hypot(s[0] - p['x'], s[1] - p['y'])
            errs.append(e)
            hit += e <= tol
        row[f'N{N}_recall_pct'] = round(100.0 * hit / len(far), 1) if far else None
        row[f'N{N}_median_px'] = med(errs)
    errs = []
    for p in far:
        s = d['final'].get(str(p['f']))
        if s is not None:
            errs.append(math.hypot(s[0] - p['x'], s[1] - p['y']))
    row['final_median_px'] = med(errs)
    return row


if __name__ == '__main__':
    for s in sys.argv[1:]:
        print(json.dumps(score(s)))
