"""track_v2.py <stem> [--device mps|cpu]

Loop-2 integrated tracker. Composes the stages picked by the fixed decision rule by importing the experiment
modules (no stage is re-implemented here):
  ball : experiments/lane-gated-ball/run.py main()  (gated re-walk of the loop-1 sam2-video track + far-end disc refine)
  lane : experiments/composition/run.py run()       (--lane edge --smooth 3: per-frame gutter-edge lane on every ball
                                                     frame, board at the ball centre row, Theil-Sen entry at pin_hit)
         with its ball_stage replaced by the lane-gated-ball points
  path : none (physics-smoother verdict 'partial'); composition's own line/hook fit is kept as path_fit_diag only,
         never as path_fit, and is not drawn
Fallback per stem: ball fails (exception, or no point in release..pin_hit) -> loop-1 sam2-video points; lane fails
(exception, boards on < 50 % of the ball frames in release..pin_hit, or no final board) -> loop-1 engine lane
(the loop-1 quads at the ball centre row, final_board = median of the last 5 boards <= pin_hit, as lane-gated-ball).
Fix pass (2026-11-07, after the two skeptics):
  series : one-sided tail outlier rejection in the board series itself (clean_series): frames pin_hit-2..track end
           whose raw board is more than REJECT_BOARDS from a Theil-Sen line over raw pin_hit-10..pin_hit-3 are dropped
           from boards{} and lane_top_down (raw kept in boards_raw, listed in series_rejected); boards{} is the 3-frame
           median re-run on the cleaned raw; final_board is composition fit_path's entry re-run on the cleaned series.
  drawing: draw_overlay_v2 plots boards against a constant-speed depth anchored at release = 0 ft and the cuts.json
           pin_hit = 60 ft (ft_cv, stored per lane_top_down point; the per-frame ft is kept unchanged), keeps the pin_hit
           frame whatever its per-frame zone, labels the end "cut pin_hit (input)", and draws the tracker's own frames
           after pin_hit as a dashed, unscored extension. No path fit is drawn (path stage none).
Writes results/tracks/<stem>.json and overlays/final__<stem>.jpg. Never opens truth.
"""
import argparse
import importlib.util
import json
import os
import statistics
import sys
import time
from types import SimpleNamespace

import cv2
import numpy as np

L1 = '/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking'
L2 = '/Users/toka/code/toms_gym/docs/research/2026-11-07-glasses-pov-hook'
WORK = os.path.join(L2, 'work', 'track_v2')
LANE_MIN_FRAC = 0.5
REJECT_BOARDS = 6.0      # same size as the loop-1 drawing trim rule
PRE_LO, PRE_HI = 10, 3   # reference window pin_hit-10..pin_hit-3 (before the tail being tested)
TAIL_FROM = 2            # frames tested: pin_hit-2 .. track end
SMOOTH = 3


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


LGB = load('lgb_run', os.path.join(L2, 'experiments', 'lane-gated-ball', 'run.py'))
CM = load('comp_run', os.path.join(L2, 'experiments', 'composition', 'run.py'))


def in_roll(points, rel, pin):
    return [p for p in points if rel <= p['f'] <= pin]


def ball_stage(stem, device, log):
    wd = os.path.join(WORK, 'lgb')
    for d in ('tracks', 'overlays', 'work'):
        os.makedirs(os.path.join(wd, d), exist_ok=True)
    LGB.X = wd
    argv = sys.argv
    try:
        sys.argv = ['run.py', stem, '--device', device]
        LGB.main()
    finally:
        sys.argv = argv
    return json.load(open(os.path.join(wd, 'tracks', f'{stem}.json')))


def loop1_track(stem):
    return json.load(open(os.path.join(L1, 'results', 'tracks', f'{stem}.json')))


def lane_stage(stem, balls, device, log):
    CM.ball_stage = lambda s, cut, how, lg: ([dict(p) for p in balls], 'track_v2 ball stage (injected)')
    wd = os.path.join(WORK, 'comp')
    args = SimpleNamespace(device=device, lane='edge', refine=False, smooth=3, ball='file', out_dir=wd)
    return CM.run(stem, args, log)


def clean_series(tr, rel, pin):
    """One-sided outlier rejection at the end of the series (a 2-sided median cannot fix the last frames; on 191820
    f463-467 all read ~19 after the camera whip). Mutates tr; returns the rejected {f: raw}."""
    raw = {int(k): float(v) for k, v in (tr.get('boards_raw') or {}).items()}
    ref = sorted((f, b) for f, b in raw.items() if pin - PRE_LO <= f <= pin - PRE_HI)
    ts = CM.theil_sen(ref)
    rejected = {}
    if ts:
        m, c = ts
        for f, b in raw.items():
            if f >= pin - TAIL_FROM and abs(b - (m * f + c)) > REJECT_BOARDS:
                rejected[f] = {'raw': round(b, 2), 'pred': round(m * f + c, 2)}
    keep = {f: b for f, b in raw.items() if f not in rejected}
    fs = sorted(keep)
    h = SMOOTH // 2
    boards = {}
    for i, f in enumerate(fs):
        win = [keep[g] for g in fs[max(0, i - h):i + h + 1] if abs(g - f) <= h]
        boards[str(f)] = round(float(statistics.median(win)), 2)
    tr['boards'] = boards
    tr['boards_contact'] = {k: v for k, v in (tr.get('boards_contact') or {}).items() if int(k) not in rejected}
    td = []
    for p in tr.get('lane_top_down') or []:
        if p['f'] in rejected or str(p['f']) not in boards:
            continue
        td.append(dict(p, board=boards[str(p['f'])], ft_cv=round(60.0 * (p['f'] - rel) / (pin - rel), 2)))
    tr['lane_top_down'] = td
    ft_of = {p['f']: p['ft'] for p in td}
    pf = CM.fit_path({int(k): v for k, v in boards.items()}, rel, pin, lambda f: ft_of.get(int(round(f))))
    tr['final_board'] = None if pf.get('board_at_60ft') is None else round(pf['board_at_60ft'], 1)
    tr['series_rejected'] = {str(f): v for f, v in sorted(rejected.items())}
    tr['series_rule'] = (f'raw boards on frames >= pin_hit-{TAIL_FROM} more than {REJECT_BOARDS} boards from a Theil-Sen '
                         f'line over raw pin_hit-{PRE_LO}..pin_hit-{PRE_HI} are dropped from boards and lane_top_down '
                         f'(kept in boards_raw); boards = {SMOOTH}-frame median of the cleaned raw; final_board = '
                         f'composition fit_path entry (Theil-Sen over pin_hit-10..pin_hit at pin_hit) on the cleaned series')
    return rejected, pf


def dashed(im, pts, color, th, on=10, off=8):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        d = max(1.0, float(np.hypot(x1 - x0, y1 - y0)))
        t = 0.0
        while t < d:
            t1 = min(d, t + on)
            a = (int(x0 + (x1 - x0) * t / d), int(y0 + (y1 - y0) * t / d))
            b = (int(x0 + (x1 - x0) * t1 / d), int(y0 + (y1 - y0) * t1 / d))
            cv2.line(im, a, b, color, th)
            t = t1 + off


def draw_overlay_v2(frames, cut, tr, out_path, used_quads, header):
    """composition.draw_overlay with three changes: depth = ft_cv (constant speed, release 0 ft .. cut pin_hit 60 ft)
    instead of the per-frame ft; frames are chosen by f (release..pin_hit solid, after pin_hit dashed) and board, not
    by the per-frame zone; the end is labelled as the cuts.json pin_hit."""
    off, rel, pin = cut['cut_start'], cut['release_frame'], cut['pin_hit_frame']
    k = max(0, min(len(frames) - 1, pin - 4 - off))
    f_show = off + k
    im = frames[k].copy()
    q = used_quads.get(f_show)
    m = tr.get('lane_top_down_model') or {'a': 60.0, 'b': 0.0}
    td = {p['f']: p for p in tr.get('lane_top_down') or [] if p['f'] >= rel}
    on = lambda p: -8.0 <= p['board'] <= 47.0  # noqa: E731  (gutter balls read below 0.5; the panel clamps to -1..41)
    roll = [f for f in sorted(td) if f <= pin and on(td[f])]
    ext = [f for f in sorted(td) if f > pin and on(td[f])]
    pts_by_f = {p['f']: (int(p['x']), int(p['y'])) for p in tr['frames']}
    raw = [pts_by_f[f] for f in roll if f in pts_by_f]
    if len(raw) > 1:
        cv2.polylines(im, [np.array(raw, np.int32)], False, (0, 140, 255), 2)
    if q:
        def ip(f):
            v = CM.LG.image_point(q, td[f]['board'], td[f]['ft_cv'], m['a'], m['b'])
            return None if v is None else (int(v[0]), int(v[1]))
        g = [v for v in (ip(f) for f in roll) if v is not None]
        if len(g) > 1:
            cv2.polylines(im, [np.array(g, np.int32)], False, (60, 220, 60), 4)
        e = [v for v in (ip(f) for f in ([roll[-1]] if roll else []) + ext) if v is not None]
        if len(e) > 1:
            dashed(im, e, (200, 200, 200), 3)
        poly = np.array([q['fl_l'], q['pd_l'], q['pd_r'], q['fl_r']], np.int32)
        cv2.polylines(im, [poly], True, (255, 255, 0), 3)
        py = CM.LG.pin_row(q)
        xl, xr = CM.LG.edge_x(q["fl_l"], q["pd_l"], py), CM.LG.edge_x(q['fl_r'], q['pd_r'], py)
        cv2.line(im, (int(xl), int(py)), (int(xr), int(py)), (255, 0, 255), 2)
        if tr.get('final_board') is not None:
            bx = xr + (tr['final_board'] - 1.0) / 38.0 * (xl - xr)
            cv2.drawMarker(im, (int(bx), int(py)), (255, 0, 255), cv2.MARKER_TRIANGLE_DOWN, 24, 3)
    for f in roll:
        if f in pts_by_f:
            p = next(pp for pp in tr['frames'] if pp['f'] == f)
            cv2.circle(im, pts_by_f[f], max(2, int(p['r'] or 3)), (0, 140, 255), 1)
    txt = [f"track_v2 {tr['stem']} f{f_show} (cut pin_hit-4)",
           f"board at cut pin_hit (cuts.json, f{pin}): {tr.get('final_board')}  path fit: none",
           'orange = raw track; green = boards vs constant-speed depth (release 0 .. cut pin_hit 60 ft)',
           'dashed grey = frames after cut pin_hit (unscored); magenta = board at cut pin_hit']
    for i, t in enumerate(txt):
        cv2.putText(im, t, (16, 50 + 40 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 6)
        cv2.putText(im, t, (16, 50 + 40 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    im = cv2.resize(im, (im.shape[1] // 2, im.shape[0] // 2))
    H, W, pad = im.shape[0], 220, 40
    FT_MAX = 66.0
    panel = np.full((H, W, 3), (40, 40, 40), np.uint8)
    lane_w, lane_h = W - 2 * pad, H - 2 * pad
    X = lambda bd: int(pad + lane_w * (39 - bd) / 38)  # noqa: E731
    Y = lambda ft: int(pad + lane_h * (1 - ft / FT_MAX))  # noqa: E731
    cv2.rectangle(panel, (pad, Y(60)), (pad + lane_w, Y(0)), (70, 160, 215), -1)
    cv2.rectangle(panel, (pad, Y(FT_MAX)), (pad + lane_w, Y(60)), (60, 60, 60), -1)
    for bd in (1, 10, 20, 30, 39):
        cv2.putText(panel, str(bd), (X(bd) - 8, pad - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (220, 220, 220), 1)
    for ft in (0, 15, 30, 45, 60):
        cv2.putText(panel, f'{ft}ft', (2, Y(ft) + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (220, 220, 220), 1)
    for bd in (5, 10, 15, 20, 25, 30, 35):
        cv2.drawMarker(panel, (X(1 + (bd - 0.5) * 38 / 39), Y(15)), (40, 40, 40), cv2.MARKER_TRIANGLE_UP, 7, 1)
    cv2.circle(panel, (X(20), Y(60)), 4, (255, 255, 255), -1)
    P = lambda f: (X(min(max(td[f]['board'], -1), 41)), Y(min(max(td[f]['ft_cv'], 0), FT_MAX)))  # noqa: E731
    line = [P(f) for f in roll]
    if len(line) > 1:
        cv2.polylines(panel, [np.array(line, np.int32)], False, (60, 220, 60), 2)
    for v in line:
        cv2.circle(panel, v, 2, (150, 40, 150), -1)
    el = ([P(roll[-1])] if roll else []) + [P(f) for f in ext]
    if len(el) > 1:
        dashed(panel, el, (200, 200, 200), 1, 4, 3)
    if tr.get('final_board') is not None:
        cv2.drawMarker(panel, (X(tr['final_board']), Y(60)), (255, 0, 255), cv2.MARKER_TRIANGLE_DOWN, 12, 2)
        cv2.putText(panel, f"b{tr['final_board']:.1f} @cut pin_hit", (4, H - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                    (255, 255, 255), 1)
    out = np.hstack([im, panel])
    for j, t in enumerate(header):
        y = out.shape[0] - 64 + 22 * j
        cv2.putText(out, t, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 4)
        cv2.putText(out, t, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.imwrite(out_path, out, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return {'roll_frames_drawn': len(roll), 'after_pin_hit_frames_drawn': len(ext),
            'pin_hit_drawn': pin in roll, 'shown_frame': f_show}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stem')
    ap.add_argument('--device', default='mps')
    a = ap.parse_args()
    log = lambda *x, **k: print(*x, **k, flush=True)  # noqa: E731
    t0 = time.time()
    stem = a.stem
    cut = CM.load_cut(stem)
    rel, pin, off = cut['release_frame'], cut['pin_hit_frame'], cut['cut_start']
    fallback = []
    base = loop1_track(stem)

    # ---- ball
    ball_tr, ball_err = None, None
    try:
        ball_tr = ball_stage(stem, a.device, log)
        if not in_roll(ball_tr.get('frames') or [], rel, pin):
            ball_err, ball_tr = 'no ball point in release..pin_hit', None
    except Exception as e:  # noqa: BLE001
        ball_err = f'{type(e).__name__}: {e}'
    if ball_tr is None:
        log(f'[ball] lane-gated-ball failed ({ball_err}); loop-1 sam2-video points')
        fallback.append('ball')
        ball_tr = base
        ball_name = 'loop1/sam2-video (fallback)'
    else:
        ball_name = 'lane-gated-ball'
    balls = [{k: p.get(k) for k in ('f', 'x', 'y', 'r', 'conf', 'src')} for p in ball_tr['frames']]

    # ---- lane
    lane_tr, lane_err = None, None
    try:
        lane_tr = lane_stage(stem, balls, a.device, log)
        nb = sum(1 for p in in_roll(balls, rel, pin) if str(p['f']) in (lane_tr.get('boards') or {}))
        nr = len(in_roll(balls, rel, pin))
        if nr == 0 or nb < LANE_MIN_FRAC * nr or lane_tr.get('final_board') is None:
            lane_err = f'boards on {nb}/{nr} roll frames, final_board {lane_tr.get("final_board")}'
            lane_tr = None
    except Exception as e:  # noqa: BLE001
        lane_err = f'{type(e).__name__}: {e}'
    if lane_tr is None:
        log(f'[lane] composition edge lane failed ({lane_err}); loop-1 engine lane')
        fallback.append('lane')
        if ball_name == 'lane-gated-ball':
            src = ball_tr                       # its boards{} / final_board are the loop-1 quads at the ball centre row
        else:
            src = base
        tr = {k: src.get(k) for k in ('frames', 'lane', 'boards', 'final_board', 'lane_top_down', 'lane_top_down_model')}
        tr['frames'] = [dict(p) for p in balls]
        lane_name = 'loop1/engine-sam-lane (fallback)'
        tr['lane_top_down'] = [dict(p, ft_cv=round(60.0 * (p['f'] - rel) / (pin - rel), 2)) for p in tr.get('lane_top_down') or []]
        lane_meta = {'lane_variant': 'loop1-engine', 'lane_sources': {'sam': len(tr.get('lane') or {})}, 'fallback_used': True}
        diag = None
    else:
        tr = {k: lane_tr.get(k) for k in ('frames', 'lane', 'boards', 'boards_raw', 'boards_contact', 'final_board',
                                          'lane_top_down', 'lane_top_down_model')}
        lane_name = 'composition/edge+smooth3'
        tr['final_board_pre_fixpass'] = tr.get('final_board')
        rejected, pf_clean = clean_series(tr, rel, pin)
        log(f'[series] rejected {sorted(rejected)}; final_board {tr["final_board_pre_fixpass"]} -> {tr["final_board"]}')
        lane_meta = {k: lane_tr['meta'].get(k) for k in ('lane_variant', 'lane_sources', 'edge_fit_failures',
                                                           'edge_fail_reasons', 'fallback_used', 'smooth', 'lane_s',
                                                           'board_row')}
        diag = pf_clean            # composition fit_path re-run on the cleaned series (diagnostic, not drawn)
    bm = ball_tr.get('meta') or {}
    wall = round(time.time() - t0 + (bm.get('base_wall_s') or (base.get('meta') or {}).get('wall_s') or 0.0), 1)
    out = {'stem': stem, 'method': 'track_v2', 'stage': 'both',
           'stages': {'ball': ball_name, 'lane': lane_name, 'path': 'none'},
           **tr,
           'release_frame': rel, 'pin_hit_frame': pin,
           'final_board_rule': 'Theil-Sen over boards in pin_hit-10..pin_hit evaluated at pin_hit (composition fit_path), on the series after clean_series'
           if lane_name.startswith('composition') else 'median of the last 5 boards <= pin_hit (loop-1 engine)',
           'path_fit_diag': diag,
           'fallback': fallback, 'fallback_reasons': {'ball': ball_err, 'lane': lane_err},
           'meta': {'device': a.device, 'cut_start': off, **lane_meta,
                    'ball_meta': {k: bm.get(k) for k in ('gates', 'refined', 'refine_rejected', 'coasted', 'sam_reprompts',
                                                         'stage_wall_s', 'base_wall_s', 'base_method')},
                    'wall_s': wall,
                    'wall_note': 'track_v2 process seconds + the loop-1 sam2-video wall the ball stage consumes (not re-run)'}}
    os.makedirs(os.path.join(L2, 'results', 'tracks'), exist_ok=True)
    os.makedirs(os.path.join(L2, 'overlays'), exist_ok=True)
    tp = os.path.join(L2, 'results', 'tracks', f'{stem}.json')
    json.dump(out, open(tp, 'w'), indent=1)
    # overlay (fix pass): draw_overlay_v2. The loop-1 6-board drawing trim is still computed, on the cleaned series,
    # as a check that the series rule left nothing for it (expected [] everywhere); trimmed points would be left out
    frames = CM.read_frames(cut['cut_path'])
    quads = {int(k): v for k, v in (out.get('lane') or {}).items()}
    td = sorted((p for p in out.get('lane_top_down') or [] if p['f'] <= pin), key=lambda p: p['f'])
    trimmed = []
    for i, p in enumerate(td):
        nb = [q['board'] for q in td[max(0, i - 2):i] + td[i + 1:i + 3]]
        if nb and abs(p['board'] - statistics.median(nb)) > 6.0:
            trimmed.append(p['f'])
    out['meta']['overlay_trimmed_frames'] = trimmed
    draw = dict(out, lane_top_down=[p for p in out.get('lane_top_down') or [] if p['f'] not in trimmed])
    op = os.path.join(L2, 'overlays', f'final__{stem}.jpg')
    hdr = [f"ball {ball_name} | lane {lane_name} | path none | fallback {fallback or '-'}",
           f"series rejected {sorted(int(k) for k in out.get('series_rejected') or {}) or '-'} | drawing trims {trimmed or '-'}"]
    out['meta']['overlay'] = draw_overlay_v2(frames, cut, draw, op, quads, hdr)
    out['meta']['overlay']['depth'] = 'ft_cv = 60 * (f - release) / (pin_hit - release), both cuts.json inputs'
    json.dump(out, open(tp, 'w'), indent=1)
    log(f'TRACK_V2 {stem}: ball={ball_name} lane={lane_name} fallback={fallback} points={len(out["frames"])} '
        f'boards={len(out.get("boards") or {})} final_board={out["final_board"]} rejected={sorted(out.get("series_rejected") or {})} '
        f'overlay={out["meta"]["overlay"]} wall={wall}s -> {tp}')


if __name__ == '__main__':
    main()
