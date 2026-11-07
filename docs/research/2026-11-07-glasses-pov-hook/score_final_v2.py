"""score_final_v2.py: score results/tracks (track_v2) and the loop-1 sam2-video tracks on all 10 throws with score_v2,
dev against L2/truth and holdout against the holdout folder outside the repo; write results/final_v2.json with numbers
only (every truth_* field the scorer returns is dropped), plus the leave-one-out sensitivity of the stage picks
re-made from the judges' per-stem holdout rows (results/judge_*.json)."""
import json
import os
import sys

L1 = '/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking'
L2 = os.path.dirname(os.path.abspath(__file__))
HO = '/Users/toka/pov-holdout/2026-11-07-glasses-pov-hook'
sys.path.insert(0, L2)
import score_v2  # noqa: E402

DEV = ['20260915_185121_23d80f05', '20260915_185331_19de9ec7', '20260915_185454_f240c883', '20260915_185645_9fde3c16',
       '20260915_190115_a7cf2c70']
HOLD = ['20260915_191253_6cf2480f', '20260915_191820_0196b564', '20260915_191913_907c358b', '20260915_192142_eeb210f6',
        '20260915_192636_7c7fbfb0']
KEYS = ['recall_pct', 'far_recall_pct', 'median_px_err', 'far_median_px_err', 'path_err_rms', 'path_err_far',
        'path_bias_far', 'path_missing', 'entry_err', 'hook_err']


def clean(r):
    return {k: v for k, v in r.items() if not k.startswith('truth')}


def truth(stem, split):
    return json.load(open(os.path.join(L2, 'truth', f'{stem}.json') if split == 'dev' else os.path.join(HO, f'{stem}.json')))


def mean(rows, k):
    v = [float(r[k]) for r in rows if r.get(k) is not None]
    return (round(sum(v) / len(v), 3) if v else None), len(v)


def means(rows):
    out = {}
    for k in KEYS:
        out[k], out[k + '_n'] = mean(rows, k)
    d = [r['direction_ok'] for r in rows if r.get('direction_ok') is not None]
    out['direction_ok_pct'] = round(100.0 * sum(d) / len(d), 1) if d else None
    out['entry_le3_count'] = sum(1 for r in rows if r.get('entry_err') is not None and r['entry_err'] <= 3)
    return out


def score_all():
    rows, diag_rows = [], []
    for split, stems in (('dev', DEV), ('holdout', HOLD)):
        for s in stems:
            t = truth(s, split)
            v2 = json.load(open(os.path.join(L2, 'results', 'tracks', f'{s}.json')))
            v1 = json.load(open(os.path.join(L1, 'results', 'tracks', f'{s}.json')))
            a, b = clean(score_v2.score(v2, t)), clean(score_v2.score(v1, t))
            row = {'stem': s, 'split': split, 'stages': v2.get('stages'), 'fallback': v2.get('fallback'),
                   'n_points': len(v2['frames']), 'n_boards': len(v2.get('boards') or {}),
                   'final_board': v2.get('final_board'),
                   'board_at_60ft': v2.get('final_board'),
                   'board_at_60ft_note': 'no path stage: the entry is final_board (Theil-Sen at pin_hit)',
                   'min_board': a['track_min_board'],
                   **{k: a[k] for k in KEYS + ['direction_ok', 'entry', 'track_trend_boards', 'path_bias']},
                   'path_missing_far': a['path_missing_far'],
                   'series_rejected': sorted(int(k) for k in (v2.get('series_rejected') or {})),
                   'final_board_pre_fixpass': v2.get('final_board_pre_fixpass'),
                   'wall_s': (v2.get('meta') or {}).get('wall_s'),
                   **{f'v1_{k}': b[k] for k in KEYS + ['direction_ok']},
                   'v1_final_board': v1.get('final_board')}
            rows.append(row)
            # diagnostic only: composition's own line/hook fit put back as path_fit (not the chosen path stage)
            pf = v2.get('path_fit_diag')
            if pf:
                c = clean(score_v2.score(dict(v2, path_fit=pf), t))
                diag_rows.append({'stem': s, 'split': split, 'fit_kind': pf.get('kind'), 'board_at_60ft': pf.get('board_at_60ft'),
                                  'min_board': pf.get('min_board'),
                                  'rise_after_min': (pf.get('params') or {}).get('rise_after_min'),
                                  **{k: c[k] for k in ('entry_err', 'hook_err', 'path_err_far', 'direction_ok')}})
            print(f"{split:7s} {s[9:15]} far {a['far_recall_pct']}/{b['far_recall_pct']} px {a['far_median_px_err']}/{b['far_median_px_err']} "
                  f"path_far {a['path_err_far']}/{b['path_err_far']} entry {a['entry_err']}/{b['entry_err']} hook {a['hook_err']}/{b['hook_err']} "
                  f"dir {a['direction_ok']}/{b['direction_ok']}  (v2/v1)", flush=True)
    return rows, diag_rows


# ---------------------------------------------------------------- leave-one-out sensitivity
def judge_rows(key):
    d = json.load(open(os.path.join(L2, 'results', f'judge_{key}.json')))
    rows = {r['stem']: r for r in d['rows']}
    base = {r['stem']: r for r in (d.get('baseline_rows') or d.get('baseline_rows_loop1_sam2video'))}
    return rows, base


EXPS = {'pin-anchored-geometry': 'lane', 'lane-gated-ball': 'ball', 'far-end-stacking': 'ball', 'composition': 'both',
        'physics-smoother': 'path'}
LOWER = ['far_median_px_err', 'path_err_rms', 'path_err_far', 'entry_err', 'hook_err']


def ok(r):
    return r is not None and not r.get('crashed') and r.get('far_recall_pct') is not None


def verdict(key, stems, literal_ball):
    rows, base = judge_rows(key)
    stage = EXPS[key]
    R = [rows.get(s) for s in stems]
    B = [base.get(s) for s in stems]
    if any(not ok(r) for r in R):
        return 'partial', 'crash/no output on a stem'
    n = len(stems)

    def m(rs, k):
        v = [float(r[k]) for r in rs if r.get(k) is not None]
        return sum(v) / len(v) if v else None
    if stage == 'ball':
        beats = sum(1 for r, b in zip(R, B) if r['far_recall_pct'] > (b.get('far_recall_pct') or 0))
        worse = sum(1 for r, b in zip(R, B) for k in LOWER if r.get(k) is not None and b.get(k) is not None and r[k] > b[k] + 0.01) \
            + sum(1 for r, b in zip(R, B) if (b.get('far_recall_pct') or 0) > r['far_recall_pct'])
        if literal_ball:
            return ('works' if beats >= 3 else 'partial' if worse else 'fails'), f'far_recall beats loop-1 on {beats}/{n}'
        return ('works' if worse == 0 else 'partial'), f'{worse} per-stem metric regressions'
    pf_ok = m(R, 'path_err_far') < m(B, 'path_err_far')
    le3 = sum(1 for r in R if r.get('entry_err') is not None and r['entry_err'] <= 3)
    if stage in ('lane', 'both'):
        w = pf_ok and le3 >= 3
        return ('works' if w else 'partial' if pf_ok else 'fails'), f'path_err_far {m(R, "path_err_far"):.2f} vs {m(B, "path_err_far"):.2f}, entry<=3 {le3}/{n}'
    false_hook = any(r.get('chose_hook') and r['stem'] == '20260915_191820_0196b564' for r in R)
    en_ok = m(R, 'entry_err') < m(B, 'entry_err')
    w = pf_ok and en_ok and le3 >= 3 and not false_hook
    return ('works' if w else 'partial' if pf_ok else 'fails'), f'path_err_far ok {pf_ok}, entry ok {en_ok}, entry<=3 {le3}/{n}, false hook on 191820 {false_hook}'


def picks(stems, literal_ball):
    v = {k: verdict(k, stems, literal_ball) for k in EXPS}

    def hm(key, k):
        rows, _ = judge_rows(key)
        x = [float(rows[s][k]) for s in stems if rows[s].get(k) is not None]
        return sum(x) / len(x)
    ball_c = [k for k in EXPS if EXPS[k] in ('ball', 'both') and v[k][0] == 'works']
    ball = max(ball_c, key=lambda k: (hm(k, 'far_recall_pct'), -hm(k, 'far_median_px_err'))) if ball_c else 'loop1/sam2-video'
    lane_c = [k for k in EXPS if EXPS[k] in ('lane', 'both') and v[k][0] == 'works']
    lane = min(lane_c, key=lambda k: (hm(k, 'path_err_far'), hm(k, 'entry_err'))) if lane_c else 'loop1/engine-lane'
    path = 'physics-smoother(subject to refit check)' if v['physics-smoother'][0] == 'works' else 'none'
    return {'ball': ball, 'lane': lane, 'path': path}, {k: list(x) for k, x in v.items()}


def sensitivity():
    out = {}
    for mode, lit in (('judges_rule', False), ('literal_ball_rubric', True)):
        full, vfull = picks(HOLD, lit)
        loo = {}
        for s in HOLD:
            p, v = picks([x for x in HOLD if x != s], lit)
            loo[s] = {'picks': p, 'flips': {k: [full[k], p[k]] for k in p if p[k] != full[k]}, 'verdicts': v}
        out[mode] = {'full_picks': full, 'full_verdicts': vfull, 'leave_one_out': loo,
                     'any_flip': any(x['flips'] for x in loo.values()),
                     'deciding_stems': {s: x['flips'] for s, x in loo.items() if x['flips']}}
    out['rule_at_n4'] = ('verdicts re-derived on the 4 remaining stems: lane/both works = path_err_far mean below loop-1 on '
                         'the same stems AND entry_err <= 3 on >= 3 stems (count kept, not scaled); ball works (judges_rule) = '
                         'no per-stem regression vs loop-1 on far recall / far px / path rms / path far / entry / hook '
                         '(lane-gated-ball judge override), (literal_ball_rubric) = far_recall beats loop-1 on >= 3 stems; '
                         'path works = path_err_far and entry_err means both below loop-1, entry<=3 on >= 3, no hook drawn on 191820')
    return out


def main():
    rows, diag = score_all()
    dev = [r for r in rows if r['split'] == 'dev']
    hold = [r for r in rows if r['split'] == 'holdout']
    v1 = lambda rs: [{k[3:]: v for k, v in r.items() if k.startswith('v1_')} for r in rs]  # noqa: E731
    ba = {}
    for k, kk in (('far_recall', 'far_recall_pct'), ('entry_err', 'entry_err'), ('path_err_far', 'path_err_far')):
        ba[f'v1_{k}'], ba[f'v1_{k}_n'] = mean(v1(rows), kk)
        ba[f'v2_{k}'], ba[f'v2_{k}_n'] = mean(rows, kk)
    bah = {}
    for k, kk in (('far_recall', 'far_recall_pct'), ('entry_err', 'entry_err'), ('path_err_far', 'path_err_far'),
                  ('path_err_rms', 'path_err_rms'), ('hook_err', 'hook_err')):
        bah[f'v1_{k}'], bah[f'v1_{k}_n'] = mean(v1(hold), kk)
        bah[f'v2_{k}'], bah[f'v2_{k}_n'] = mean(hold, kk)
    prev = None
    pp = os.path.join(L2, 'work', 'fixpass', 'before', 'final_v2.json')
    if os.path.exists(pp):
        pv = json.load(open(pp))
        prev = {'note': 'track_v2 before the fix pass (same scorer, same truth); copy in work/fixpass/before/',
                'holdout': {k: pv['means']['holdout'].get(k) for k in ('path_err_far', 'path_err_rms', 'entry_err', 'hook_err',
                                                                      'direction_ok_pct', 'entry_le3_count')},
                'before_after': pv.get('before_after')}
    caveats = [
        'Shared instrument: the holdout ball truth is a purple/dark HSV blob fit confirmed by eye, and the lane-gated-ball far '
        'refine is a purple disc filter; the truth boards come from same-frame wood->gutter edge lines, and the composition '
        'lane is per-frame wood-mask gutter edges. The px and board agreement measures agreement with that shared '
        'instrument, and v1 (SAM masks) is scored on the instrument v2 copies. Absolute board accuracy below ~1.5 boards '
        'is not established: the truth pin ruler and the edge profile disagree by 1-2 boards (px/in 1.67 vs 2.1).',
        'Post-selection: the ball and lane stages were picked from the judges\' holdout rows (judge_*.json), hence the '
        'leave-one-out flips in sensitivity, so the holdout means are not a fresh test. before_after (n=10) also mixes in '
        'the 5 dev stems on which the refine thresholds and the smoothing were tuned; before_after_holdout is the n=5 view.',
        'Entry convention: every tracker evaluates at the cuts.json pin_hit; 192142 and 192636 truth entry is at the observed '
        'contact 10 and 4 frames later, so most of their entry_err is that convention.',
        'Fix-pass series rule (clean_series) was written after the skeptics read the 191820 holdout row; its threshold sits '
        'between the largest kept tail deviation (4.51 boards) and the smallest rejected one (20.12) on these 10 stems.']
    out = {'scorer': 'score_v2.py', 'tracks_dir': 'results/tracks', 'v1_tracks_dir': f'{L1}/results/tracks',
           'truth': {'dev': 'truth/', 'holdout': 'holdout folder outside the repo (numbers only here; truth_* fields dropped)'},
           'rows': rows,
           'means': {'dev': means(dev), 'holdout': means(hold), 'all10': means(rows),
                     'v1_dev': means(v1(dev)), 'v1_holdout': means(v1(hold)), 'v1_all10': means(v1(rows))},
           'before_after': ba,
           'before_after_holdout': bah,
           'before_fixpass': prev,
           'claim_caveats': caveats,
           'diag_composition_path_fit': {'note': 'NOT the chosen path stage; composition fit_path re-scored on the v2 boards',
                                         'rows': diag, 'holdout_means': means([r for r in diag if r['split'] == 'holdout']),
                                         'dev_means': means([r for r in diag if r['split'] == 'dev'])},
           'sensitivity': sensitivity(),
           'fallback_stems': [r['stem'] for r in rows if r.get('fallback')]}
    json.dump(out, open(os.path.join(L2, 'results', 'final_v2.json'), 'w'), indent=1)
    print(json.dumps({'means_holdout': out['means']['holdout'], 'v1_holdout': out['means']['v1_holdout'],
                      'means_dev': out['means']['dev'], 'v1_dev': out['means']['v1_dev'], 'before_after': ba,
                      'before_after_holdout': bah, 'before_fixpass': prev}, indent=0))
    print(json.dumps(out['sensitivity'], indent=0)[:6000])
    print(json.dumps(out['diag_composition_path_fit'], indent=0)[:3500])


if __name__ == '__main__':
    main()
