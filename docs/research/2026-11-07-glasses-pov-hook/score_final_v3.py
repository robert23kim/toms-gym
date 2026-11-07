"""score_final_v3.py: exit-pass scoring. Scores results/tracks (track_v2 exit pass, "v3") and the shipped v2 tracks
(work/exit_pass/tracks_v2_before) with score_v2 against L2/truth on all 10 throws; adds the pin-row / entry-at-pin-row /
exit scores, the +3-frame pin-row mutation, and writes results/final_v3.json. Computed after the tracker ran; nothing
here feeds back into track_v2."""
import copy
import json
import os
import sys

L1 = '/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking'
L2 = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, L2)
sys.argv = sys.argv[:1]
import score_v2  # noqa: E402
import track_v2 as T  # noqa: E402

DEV = ['20260915_185121_23d80f05', '20260915_185331_19de9ec7', '20260915_185454_f240c883', '20260915_185645_9fde3c16',
       '20260915_190115_a7cf2c70']
HOLD = ['20260915_191253_6cf2480f', '20260915_191820_0196b564', '20260915_191913_907c358b', '20260915_192142_eeb210f6',
        '20260915_192636_7c7fbfb0']
NEW = ['pin_row_err', 'contact_frame_err', 'entry_err_pr', 'exit_err', 'exit_err_last', 'cut_contact_err']
OLD = ['far_recall_pct', 'path_err_far', 'path_err_rms', 'entry_err']


def J(p):
    return json.load(open(p))


def mean(rows, k):
    v = [float(r[k]) for r in rows if r.get(k) is not None]
    return {'mean': round(sum(v) / len(v), 2) if v else None, 'n': len(v)}


rows, missing = [], []
for split, stems in (('holdout', HOLD), ('dev', DEV)):
    for stem in stems:
        tr = J(f'{L2}/results/tracks/{stem}.json')
        old = J(f'{L2}/work/exit_pass/tracks_v2_before/{stem}.json')
        truth = J(f'{L2}/truth/{stem}.json')
        if 'pin_row' not in truth or 'exit' not in truth:
            missing.append(stem)
        s3 = score_v2.score(tr, truth)
        s2 = score_v2.score(old, truth)
        ev = tr['events']
        tpr, tex = truth.get('pin_row') or {}, truth.get('exit') or {}
        ob = {int(k): v for k, v in old['boards'].items()}
        v2_last_f = max(ob) if ob else None
        r = {'stem': stem, 'split': split,
             'pin_row_frame_est': ev['pin_row_frame_est'], 'pin_row_source': ev['pin_row_source'].split(':')[0],
             'cut_pin_hit': tr['pin_hit_frame'], 'pin_row_minus_cut': ev['pin_row_minus_cut'],
             'pin_row_variants': {k: ev.get(k) for k in ('pin_row_frame_contact', 'pin_row_frame_pd15', 'pin_row_frame_lane')},
             'entry_board': ev['entry_board'], 'entry_board_raw': ev['entry_board_raw'],
             'exit_frame': ev['exit_frame'], 'exit_board': ev['exit_board'], 'exit_reason': ev['exit_reason'],
             'track_last_real_frame': ev['track_last_real_frame'], 'track_last_real_board': ev['track_last_real_board'],
             'deck_frames': ev['deck_frames'],
             'breakpoint_ft': ev['breakpoint_ft'], 'breakpoint_board': ev['breakpoint_board'],
             'breakpoint_at_roll_end': ev['breakpoint_at_roll_end'], 'rise_after_break': ev['rise_after_break'],
             'final_board_at_cut': tr['final_board'], 'series_rejected': sorted(int(k) for k in tr.get('series_rejected') or {}),
             'truth_pin_row_frame': tpr.get('frame'), 'truth_pin_row_board': tpr.get('board'),
             'truth_exit_frame': tex.get('frame'), 'truth_exit_board': tex.get('board'),
             **{k: s3.get(k) for k in NEW + OLD},
             'v2_entry_err_pr': None if tpr.get('board') is None or old.get('final_board') is None
             else round(abs(old['final_board'] - tpr['board']), 2),
             'v2_exit_err': None if tex.get('board') is None or v2_last_f is None or tex.get('observed') is False else round(abs(ob[v2_last_f] - tex['board']), 2),
             'v2_last_frame': v2_last_f,
             **{'v2_' + k: s2.get(k) for k in OLD}}
        # mutation: pin_row_frame_est + 3 through the same events function
        m = copy.deepcopy(tr)
        pr = ev['pin_row_frame_est']
        ev3 = T.compute_events(m, tr['release_frame'], pr + 3)
        m['events'] = {**ev, **{k: ev3[k] for k in ev3 if k != 'how'}}
        s3m = score_v2.score(m, truth)
        r['mutation_pr_plus3'] = {'pin_row_err': s3m.get('pin_row_err'), 'breakpoint_ft': ev3['breakpoint_ft'],
                                  'pin_row_err_delta': None if s3m.get('pin_row_err') is None or s3.get('pin_row_err') is None
                                  else s3m['pin_row_err'] - s3['pin_row_err'],
                                  'breakpoint_changed': ev3['breakpoint_ft'] != ev['breakpoint_ft']}
        # diagnostics (score side only, never fed back): the hand-cut pin_hit as a pin-row detector, and the breakpoint
        # the tracker's own series gives when 60 ft is anchored at the truth pin row instead of the detected one
        r['truth_pin_row_flagged'] = str(tpr.get('note', '')).startswith('NOT re-derived')
        r['truth_pin_row_note'] = str(tpr.get('note', ''))[:200]
        t60 = tpr.get('frame_contact_row') if tpr.get('frame_contact_row') is not None else tpr.get('frame')
        r['truth_pin_row_60ft'] = t60
        r['cut_pin_row_err'] = None if t60 is None else abs(tr['pin_hit_frame'] - int(t60))
        r['cut_contact_err'] = None if truth.get('contact_frame') is None else abs(tr['pin_hit_frame'] - int(truth['contact_frame']))
        r['truth_contact_frame'] = truth.get('contact_frame')
        r['contact_frame_err'] = s3.get('contact_frame_err')
        r['deck_decoy_from'] = ev.get('deck_decoy_from')
        r['exit_kind'] = ev.get('exit_kind')
        r['deflection'] = ev.get('deflection')
        r['pin_motion_frame'] = ev.get('pin_motion_frame')
        variants = {'pin_motion_minus2': None if ev.get('pin_motion_frame') is None else ev['pin_motion_frame'] - T.PM_LEAD,
                    'geometric': ev.get('pin_row_frame_geometric'), 'cut': tr['pin_hit_frame']}
        tc = truth.get('contact_frame')
        r['pin_row_variants3'] = {k: {'frame': v, 'err_60ft': None if v is None or t60 is None else abs(v - int(t60)),
                                      'err_contact': None if v is None or tc is None else abs(v - int(tc))}
                                  for k, v in variants.items()}
        for k in variants:
            r[f'v3_{k}_err_60ft'] = r['pin_row_variants3'][k]['err_60ft']
            r[f'v3_{k}_err_contact'] = r['pin_row_variants3'][k]['err_contact']
        r['breakpoint_ft_at_truth_pin_row'] = None if t60 is None else T.compute_events(tr, tr['release_frame'], int(t60))['breakpoint_ft']
        r['entry_board_raw_at_truth_pin_row'] = None if tpr.get('frame') is None else (tr.get('boards_clean_raw') or {}).get(str(tpr['frame']))
        r['exit_within_2'] = None if r.get('exit_err') is None else r['exit_err'] <= 2.0
        r['exit_last_within_2'] = None if r.get('exit_err_last') is None else r['exit_err_last'] <= 2.0
        rows.append(r)

agg = {}
for split in ('holdout', 'dev', 'all'):
    rs = [r for r in rows if split == 'all' or r['split'] == split]
    agg[split] = {k: mean(rs, k) for k in NEW + OLD + ['v2_entry_err_pr', 'v2_exit_err', 'cut_pin_row_err'] + ['v2_' + k for k in OLD]}
    ok = [r for r in rs if not r.get('truth_pin_row_flagged')]
    agg[split]['pin_row_source_counts'] = {s_: sum(1 for r in rs if r['pin_row_source'] == s_) for s_ in ('pin motion', 'geometric', 'fallback')}
    for k in ('pin_motion_minus2', 'geometric', 'cut'):
        for e in ('err_60ft', 'err_contact'):
            agg[split][f'v3_{k}_{e}'] = mean(rs, f'v3_{k}_{e}')
    for k in ('pin_row_err', 'cut_pin_row_err', 'entry_err_pr', 'v2_entry_err_pr'):
        agg[split][k + '_rederived_truth_only'] = mean(ok, k)
# canary: the unchanged scorer fields reproduce final_v2.json on the shipped v2 track of 185454
fv2 = {r['stem']: r for r in J(f'{L2}/results/final_v2.json')['rows']}
c = score_v2.score(J(f'{L2}/work/exit_pass/tracks_v2_before/20260915_185454_f240c883.json'), J(f'{L2}/truth/20260915_185454_f240c883.json'))
canary = {k: (c.get(k), fv2['20260915_185454_f240c883'].get(k)) for k in ('path_err_far', 'entry_err', 'far_recall_pct')}
empty = score_v2.score(dict(J(f'{L2}/results/tracks/20260915_192142_eeb210f6.json'), frames=[], events={}), J(f'{L2}/truth/20260915_192142_eeb210f6.json'))
out = {'what': 'exit pass: pin row detected by the tracker, ball followed through the pin deck, entry at the pin row, exit',
       'rows': rows, 'means': agg, 'truth_missing_pin_row_or_exit': missing,
       'canary_185454_v2_vs_final_v2': canary, 'canary_empty_track': {k: empty.get(k) for k in ('recall_pct', 'pin_row_err', 'exit_err')},
       'truth_flag_note': 'truth pin_row rows marked NOT re-derived are excluded in *_rederived_truth_only; at this run the truth agent '
                          'had re-derived all 10 (dev rows revised during the exit pass, read at run time)',
       'caveats': ['release_frame is still the cuts.json input; ft_cv anchors 60 ft at the detected pin row under constant speed',
                   'pin row and centre point were chosen after seeing the 192142/192636 crossing frames; their known contacts (490/463) were in the task text',
                   'truth and tracker share one instrument (purple ball, wood-to-gutter edges)',
                   'all 10 throws have been seen; dev thresholds were tuned on dev and the stages picked from holdout rows',
                   'pin_row_err resolution is 2-3 frames (row jitter +-5 px, ball ~2 px per frame at the deck)',
                   'exit = lead definition (ft_cv <= 63); constant speed overstates depth once the ball hits pins, so it fires 3-4 frames after the pin row; exit_err_last is the last real tracked frame']}
json.dump(out, open(f'{L2}/results/final_v3.json', 'w'), indent=1)
print('missing', [s[9:15] for s in missing])
print('canary', canary, 'empty', out['canary_empty_track'])
for r in rows:
    print(r['split'][:4], r['stem'][9:15], 'pr', r['pin_row_frame_est'], 'cut', r['cut_pin_hit'], 'T', r['truth_pin_row_frame'], '| entry', r['entry_board'], 'T', r['truth_pin_row_board'],
          '| exit f', r['exit_frame'], r['exit_board'], 'last', r['track_last_real_frame'], r['track_last_real_board'], 'T', r['truth_exit_frame'], r['truth_exit_board'],
          '| break', r['breakpoint_board'], '@', r['breakpoint_ft'], '| err pr', r['pin_row_err'], 'ent', r['entry_err_pr'], 'exit', r['exit_err'], 'last', r['exit_err_last'], '| mut', r['mutation_pr_plus3'])
for sp in ('holdout', 'dev', 'all'):
    print(sp, {k: ((v['mean'], v['n']) if 'mean' in v else v) for k, v in agg[sp].items()})
for r in rows:
    print(r['stem'][9:15], 'cut_pr_err', r['cut_pin_row_err'], 'break@truth_pr', r['breakpoint_ft_at_truth_pin_row'], 'raw@truth_pr', r['entry_board_raw_at_truth_pin_row'])
