"""Assemble results/dev.json from results/score_<stem>.json, results/cands_<stem>.json, tracks/ and the loop-2 baseline."""
import json
L2 = '/Users/toka/code/toms_gym/docs/research/2026-11-07-glasses-pov-hook'
STEMS = ['20260915_185121_23d80f05', '20260915_185331_19de9ec7', '20260915_185454_f240c883', '20260915_185645_9fde3c16',
         '20260915_190115_a7cf2c70']
base = {r['stem']: r for r in json.load(open(f'{L2}/results/baseline_v2.json'))['rows']}
rows = []
for s in STEMS:
    r = json.load(open(f'results/score_{s}.json'))
    tr = json.load(open(f'tracks/{s}.json'))
    c = json.load(open(f'results/cands_{s}.json'))
    r['wall_s'] = tr['meta']['wall_s']
    r['wall_s_incl_loop1'] = round(tr['meta']['wall_s'] + (tr['meta']['loop1_wall_s'] or 0), 1)
    r['replaced'] = len(tr['meta']['replaced'])
    r['replaced_median_shift_px'] = tr['meta']['replaced_median_shift_px']
    r['replaced_max_shift_px'] = tr['meta']['replaced_max_shift_px']
    r['final_board_source'] = 'loop-1 engine (unchanged)'
    r['cands'] = c
    r['baseline'] = {k: base[s][k] for k in ('recall_pct', 'far_recall_pct', 'median_px_err', 'far_median_px_err', 'path_err_rms',
                                             'path_err_far', 'entry_err', 'hook_err', 'direction_ok', 'wall_s')}
    rows.append(r)
keys = ['recall_pct', 'far_recall_pct', 'median_px_err', 'far_median_px_err', 'path_err_rms', 'path_err_far', 'entry_err',
        'hook_err', 'wall_s', 'wall_s_incl_loop1', 'path_missing']
means = {}
for k in keys:
    v = [r[k] for r in rows if r.get(k) is not None]
    means[k] = round(sum(v) / len(v), 2)
    means[k + '_n'] = len(v)
d = [r['direction_ok'] for r in rows if r['direction_ok'] is not None]
means['direction_ok_pct'] = round(100 * sum(d) / len(d), 1)
means['direction_ok_n'] = len(d)
bk = ['recall_pct', 'far_recall_pct', 'median_px_err', 'far_median_px_err', 'path_err_rms', 'path_err_far', 'entry_err', 'hook_err']
bm = {k: round(sum(base[s][k] for s in STEMS if base[s][k] is not None) / max(1, sum(1 for s in STEMS if base[s][k] is not None)), 2)
      for k in bk}
byn = {N: {'far_recall_pct_mean': round(sum(r['cands'][f'N{N}_recall_pct'] for r in rows) / 5, 1),
           'linked_median_px_by_stem': [r['cands'][f'N{N}_median_px'] for r in rows]} for N in ('1', '3', '5', '7')}
out = {'key': 'far-end-stacking', 'stage': 'ball', 'scorer': 'L2/score_v2.py', 'truth': 'L2/truth (dev only)',
       'config': {'n': 5, 'win': 24, 'seed': 10, 'k': 6, 'sigma': 8.0, 'sat': 30, 'centre': 'purple', 'passes': 2},
       'rows': rows, 'means': means, 'baseline_means': bm,
       'by_n': {'pre_link_far_recall_pct_mean': round(sum(r['cands']['pre_link_recall_pct'] for r in rows) / 5, 1),
                'pre_link_best_px_by_stem': [r['cands']['pre_link_best_px'] for r in rows], 'linked': byn,
                'note': 'N (stack size) changes neither far recall (100 on every stem before and after linking) nor the linked '
                        'position by more than 0.3 px; the gain over loop 1 is the re-centring (pass-2 scaled energy pick + '
                        'disc-clipped purple centroid), not the stacking'}}
json.dump(out, open('results/dev.json', 'w'), indent=1)
print(json.dumps(means))
print('baseline', json.dumps(bm))
for r in rows:
    print(r['stem'][9:15], {k: r[k] for k in ('far_median_px_err', 'median_px_err', 'path_err_far', 'hook_err', 'direction_ok', 'wall_s')})
