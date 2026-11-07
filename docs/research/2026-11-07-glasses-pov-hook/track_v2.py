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
Exit pass (2026-11-07, after Tom's showcase notes):
  ball   : the lane-gated-ball stage runs to the END of the cut (pin_hit+20, LGB.PIN_TAIL lifted) so the ball is followed
           through the pin deck; the lane stage measures the edge lane on those frames too and boards past the pd row are
           read on the straight edge lines extended upward (lane_geom.lane_point is linear in y).
  series : clean_series is a frame-to-frame jump rule (jump_reject): from cut pin_hit-2 on, a raw board more than
           JUMP_BOARDS + JUMP_PER_GAP x (frames skipped) from the last KEPT board is dropped (a ball cannot move 6 in
           sideways in 33 ms); a hook arrives in steps of <= 2.5 boards and is kept whatever its size.
  depth  : pin_row_frame_est = first ball frame (not coasted, >= release+8, held on the next real frame, >= 3 real frames
           after it) whose centre y is at/above the headpin base row: the midpoint between the top of the bright pin
           column (pin heads, measured in the frame) and the edge pd row (the bottom of the pins' mirror image on the
           glossy deck; the column is pin + reflection). ft_cv = 60 (f - release) / (pin_row_frame_est - release); the cut anchor
           is kept as ft_cv_cut. Fallback: no crossing -> cut pin_hit (pin_row_source says which).
  events : entry (Theil-Sen at the pin row), exit (last ball point with ft_cv <= 63 before the ball is lost), deck
           frames, breakpoint (minimum of the 5-frame median board over the roll) -> out['events'].
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
JUMP_BOARDS = 6.0        # max board step from the last kept frame (a ball cannot move 6 in sideways in one frame)
JUMP_PER_GAP = 1.0       # extra allowance per frame skipped since the last kept frame
SEED_N = 3               # the chain starts at the median of the 3 raw boards before the tested window
TAIL_FROM = 2            # frames tested: cut pin_hit-2 .. track end (the old window start)
SMOOTH = 3
PIN_IN, LANE_IN = 15.0, 41.5   # pin height, lane width (in)
PIN_ROW_MIN_REL = 8      # pin-row search starts at release+8 (quads before are carried through the head swing)
ENTRY_PRE = 6            # entry Theil-Sen over the 6 frames before the pin row
EXIT_FT, DECK_LO_FT, DECK1_FT = 63.0, 60.0, 62.6
BREAK_MED = 5
PM_BASE_N, PM_K, PM_LEAD = 10, 4.0, 2   # pin-motion clock: baseline frames, threshold x median, frames ball->lean
DECK_MID_FT = 61.3
STATIC_PX = 3.0          # max camera-compensated drift (px) over the next 3 frames below which a deck point is static


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
    LGB.PIN_TAIL = 10 ** 6     # exit pass: follow the ball to the end of the cut (pin_hit+20), not pin_hit+4
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


def jump_reject(raw, f_from, jump=JUMP_BOARDS, per_gap=JUMP_PER_GAP, seed_n=SEED_N):
    """{f: board} -> rejected {f: info}. Frames >= f_from are walked in order against the last KEPT board (seeded with
    the median of the seed_n raw boards before f_from); a frame further than jump + per_gap * (frames skipped) from it
    is dropped, otherwise it becomes the new reference. A spike or a plateau reached by one impossible step stays out
    until the series comes back; a sustained move reached in steps <= jump (a hook) is kept."""
    fs = sorted(raw)
    before = [f for f in fs if f < f_from]
    if not before:
        return {}
    kb = float(statistics.median([raw[f] for f in before[-seed_n:]]))
    kf = before[-1]
    rej = {}
    for f in fs:
        if f < f_from:
            continue
        thr = jump + per_gap * max(0, f - kf - 1)
        if abs(raw[f] - kb) > thr:
            rej[f] = {'raw': round(raw[f], 2), 'ref': round(kb, 2), 'ref_f': kf, 'thr': round(thr, 1)}
        else:
            kb, kf = raw[f], f
    return rej


def clean_series(tr, rel, pin):
    """Jump-rule rejection on the raw boards from cut pin_hit-2 on (191820 f463-467 read ~19 after the camera whip, one
    21-board step). Mutates tr; returns (rejected {f: info}, composition fit_path on the cleaned series)."""
    raw = {int(k): float(v) for k, v in (tr.get('boards_raw') or {}).items()}
    rejected = jump_reject(raw, pin - TAIL_FROM)
    keep = {f: b for f, b in raw.items() if f not in rejected}
    fs = sorted(keep)
    h = SMOOTH // 2
    boards = {}
    for i, f in enumerate(fs):
        win = [keep[g] for g in fs[max(0, i - h):i + h + 1] if abs(g - f) <= h]
        boards[str(f)] = round(float(statistics.median(win)), 2)
    tr['boards'] = boards
    tr['boards_clean_raw'] = {str(f): round(b, 2) for f, b in sorted(keep.items())}
    tr['boards_contact'] = {k: v for k, v in (tr.get('boards_contact') or {}).items() if int(k) not in rejected}
    tr['lane_top_down'] = [dict(p, board=boards[str(p['f'])]) for p in tr.get('lane_top_down') or []
                           if p['f'] not in rejected and str(p['f']) in boards]
    ft_of = {p['f']: p['ft'] for p in tr['lane_top_down']}
    pf = CM.fit_path({int(k): v for k, v in boards.items()}, rel, pin, lambda f: ft_of.get(int(round(f))))
    tr['final_board'] = None if pf.get('board_at_60ft') is None else round(pf['board_at_60ft'], 1)
    tr['series_rejected'] = {str(f): v for f, v in sorted(rejected.items())}
    tr['series_rule'] = (f'jump rule: raw boards on frames >= cut pin_hit-{TAIL_FROM} are walked in order against the last '
                         f'kept raw board (seed = median of the {SEED_N} raw boards before); a frame more than {JUMP_BOARDS} + '
                         f'{JUMP_PER_GAP} x (frames skipped) boards from it is dropped from boards and lane_top_down (kept in '
                         f'boards_raw); boards = {SMOOTH}-frame median of the cleaned raw; final_board = composition fit_path '
                         f'entry (Theil-Sen over cut pin_hit-10..pin_hit at cut pin_hit) on the cleaned series')
    return rejected, pf


def pin_base_row_pd15(q):
    """Variant B: the pd row minus one pin height (15 in at the lane-edge px/in). Kept for comparison only: the pin ruler
    reads about 0.78x the lane-edge px/in (gate notes), so this row sits 5-10 px too high."""
    pd = CM.LG.pin_row(q)
    w = abs(CM.LG.edge_x(q['fl_l'], q['pd_l'], pd) - CM.LG.edge_x(q['fl_r'], q['pd_r'], pd))
    return pd - PIN_IN / LANE_IN * w


def column_top(im, q):
    """Top row of the bright pin column above the pd row: walk up from the pd row over the middle 70 % of the lane width,
    past the dim reflection end to the first row >= 25 % near-white (S < 50, V >= 225), then on until 3 consecutive rows
    are < 10 % near-white (the darker masking unit above the pin heads)."""
    pd = CM.LG.pin_row(q)
    xl, xr = CM.LG.edge_x(q['fl_l'], q['pd_l'], pd), CM.LG.edge_x(q['fl_r'], q['pd_r'], pd)
    w, cx = abs(xr - xl), 0.5 * (xl + xr)
    y_lo, y_hi = int(max(0, pd - 1.0 * w)), int(min(im.shape[0], pd))
    x0, x1 = int(max(0, cx - 0.35 * w)), int(min(im.shape[1], cx + 0.35 * w))
    if y_hi - y_lo < 10 or x1 - x0 < 10:
        return None
    hsv = cv2.cvtColor(im[y_lo:y_hi, x0:x1], cv2.COLOR_BGR2HSV)
    frac = ((hsv[..., 1] < 50) & (hsv[..., 2] >= 225)).mean(axis=1)
    i = len(frac) - 1
    while i >= 0 and frac[i] < 0.25:
        i -= 1
    run = 0
    while i >= 0:
        run = run + 1 if frac[i] < 0.10 else 0
        if run == 3:
            return float(y_lo + i + 3)
        i -= 1
    return None


def pin_row_estimate(tr, base_quads, rel, pin_cut, frames, off):
    """Self-detected pin-row frame from the tracker's own ball points, lane quads and frames (no truth read).
    Headpin base row per frame = midpoint of the bright pin column: column_top (pin heads) and the edge pd row (the
    bottom of the pins' mirror image on the glossy deck); the column is pin + reflection, 54-66 px tall, so the base
    sits half-way. 3-frame median over f-1..f+1.
    pin_row_frame_est     : first non-coasted ball frame >= release+8 whose centre y <= that row, held on the next real
                            ball frame, with >= 3 real ball frames after it (the last refine points before the track
                            coasts out are the least trustworthy).
    pin_row_frame_contact : same with the contact row y + r.
    pin_row_frame_pd15    : centre y <= pd row - 15 in at the lane-edge px/in (variant B).
    pin_row_frame_lane    : the literal spec: centre y <= loop-1 quad pin_y where present, else the edge pd row."""
    quads = {int(k): v for k, v in (tr.get('lane') or {}).items()}
    pts = sorted((p for p in tr.get('frames') or [] if p.get('src') != 'coast' and p['f'] >= rel + PIN_ROW_MIN_REL),
                 key=lambda p: p['f'])
    mid, pd15 = {}, {}
    for f, q in quads.items():
        if not CM.depth_ok(q) or f < rel + PIN_ROW_MIN_REL or not 0 <= f - off < len(frames):
            continue
        pd15[f] = pin_base_row_pd15(q)
        top = column_top(frames[f - off], q)
        if top is not None:
            mid[f] = 0.5 * (top + CM.LG.pin_row(q))

    def at(rows, f):
        v = [rows[g] for g in (f - 1, f, f + 1) if g in rows]
        return float(statistics.median(v)) if v else None

    def first(rows, test):
        for i, p in enumerate(pts):
            b = at(rows, p['f'])
            if b is None or not test(p, b) or len(pts) - 1 - i < 3:
                continue
            nxt = pts[i + 1]
            nb = at(rows, nxt['f'])
            if nb is not None and test(nxt, nb):
                return p['f'], round(b, 1)
        return None, None

    f_est, row_est = first(mid, lambda p, b: p['y'] <= b)
    f_contact, _ = first(mid, lambda p, b: p['y'] + (p['r'] or 0) <= b)
    f_pd15, _ = first(pd15, lambda p, b: p['y'] <= b)
    f_lane = None
    for p in pts:
        lq = base_quads.get(str(p['f'])) or {}
        q = quads.get(p['f'])
        row = lq.get('pin_y') if lq.get('pin_y') is not None else (CM.LG.pin_row(q) if q else None)
        if row is not None and p['y'] <= row:
            f_lane = p['f']
            break
    src = 'detected: ball centre y at the headpin base row (midpoint of pin column top and edge pd row)'
    if f_est is None:
        f_est, src = pin_cut, 'fallback: cuts.json pin_hit (no held crossing of the detected pin row)'
    tr['base_rows'] = {str(f): round(v, 2) for f, v in sorted(mid.items())}
    return {'pin_row_frame_est': int(f_est), 'pin_row_source': src, 'pin_row_base_y': row_est,
            'pin_row_frame_contact': f_contact, 'pin_row_frame_pd15': f_pd15, 'pin_row_frame_lane': f_lane,
            'pin_row_rows_measured': len(mid), 'cut_pin_hit': pin_cut, 'pin_row_minus_cut': int(f_est) - pin_cut}


def deck_decoy(tr, frames, off, pr, mo=None):
    """(first static frame or None, {f: max compensated drift px over the next 3 frames}). A non-coasted point at/after
    pin_row-1 is static when every non-coasted point within the next 3 frames (>= 2 of them) lies < STATIC_PX px from it
    after ORB homography compensation; the ball track ends at the first static point (a purple pit/kickback patch)."""
    pts = {p['f']: p for p in tr.get('frames') or [] if p.get('src') != 'coast' and p['f'] >= pr - 1}
    if len(pts) < 3:
        return None, {}
    mo = mo or LGB.Motion(frames)
    drift = {}
    for f in sorted(pts):
        later = [g for g in sorted(pts) if f < g <= f + 3]
        if len(later) < 2:
            continue
        d = 0.0
        for g in later:
            x, y = LGB.apply_h(LGB.compose(mo, f - off, g - off), pts[f]['x'], pts[f]['y'])
            d = max(d, float(np.hypot(pts[g]['x'] - x, pts[g]['y'] - y)))
        drift[f] = round(d, 2)
    first = next((f for f in sorted(drift) if drift[f] < STATIC_PX), None)
    return first, {str(k): v for k, v in drift.items()}


def rack_box(im, q):
    """Pins' bounding box (x0, y0, x1, y1) in one frame: rows column_top..edge pd row, columns between the lane edges
    whose rows column_top..midpoint are >= 20 % bright low-saturation (S < 50, V >= 225), padded 4 px."""
    top = column_top(im, q)
    if top is None:
        return None
    pd = CM.LG.pin_row(q)
    xl, xr = CM.LG.edge_x(q['fl_l'], q['pd_l'], pd), CM.LG.edge_x(q['fl_r'], q['pd_r'], pd)
    x0, x1 = int(max(0, min(xl, xr))), int(min(im.shape[1], max(xl, xr)))
    y0, ym = int(top), int(0.5 * (top + pd))
    if ym - y0 < 4 or x1 - x0 < 8:
        return None
    hsv = cv2.cvtColor(im[y0:ym, x0:x1], cv2.COLOR_BGR2HSV)
    frac = ((hsv[..., 1] < 50) & (hsv[..., 2] >= 225)).mean(axis=0)
    cols = np.where(frac >= 0.2)[0]
    if len(cols) < 3:
        return None
    return (max(0, x0 + int(cols[0]) - 4), max(0, y0 - 4), min(im.shape[1], x0 + int(cols[-1]) + 5), int(pd) + 1)


def pin_motion(tr, frames, off, pin_cut, mo):
    """First pin motion from camera-compensated frame differencing inside the rack box (ORB homography, then a local
    phase-correlation translation of the rack crop: the whole-frame homography leaves 1-2 px at the pins, baseline 8-20
    grey levels on 192142). stat(f) = mean |gray_f - warp(gray_f-1 -> f)| over the box minus a disc of 2.5 r + 3 px around the ball (at f and at f-1 moved to f).
    Threshold = PM_K x the median stat over the PM_BASE_N frames before the cut pin_hit (fixed a priori). Motion frame =
    first f >= cut pin_hit with stat(f) and stat(f+1) above the threshold. Returns (frame or None, info)."""
    quads = {int(k): v for k, v in (tr.get('lane') or {}).items()}
    balls = {p['f']: p for p in tr.get('frames') or []}
    stat, box = {}, None
    f_lo, f_hi = pin_cut - PM_BASE_N, off + len(frames) - 1
    for f in range(f_lo, f_hi + 1):
        k = f - off
        if k < 1 or k >= len(frames):
            continue
        qf = quads.get(f) or quads.get(min(quads, key=lambda g: abs(g - f))) if quads else None
        if qf is None:
            continue
        b = rack_box(frames[k], qf)
        box = b or box
        if box is None:
            continue
        Hm = LGB.compose(mo, k - 1, k)
        if Hm is None:
            continue
        g1 = cv2.cvtColor(frames[k], cv2.COLOR_BGR2GRAY).astype(np.float32)
        g0 = cv2.warpPerspective(cv2.cvtColor(frames[k - 1], cv2.COLOR_BGR2GRAY).astype(np.float32), Hm,
                                 (g1.shape[1], g1.shape[0]))
        x0, y0, x1, y1 = box
        mg = 10
        X0, Y0 = max(0, x0 - mg), max(0, y0 - mg)
        X1, Y1 = min(g1.shape[1], x1 + mg), min(g1.shape[0], y1 + mg)
        c1, c0 = g1[Y0:Y1, X0:X1], g0[Y0:Y1, X0:X1]
        if c1.shape[0] < 8 or c1.shape[1] < 8:
            continue
        (sx, sy), _ = cv2.phaseCorrelate(c1, c0, cv2.createHanningWindow((c1.shape[1], c1.shape[0]), cv2.CV_32F))
        c0 = cv2.warpAffine(c0, np.float32([[1, 0, -sx], [0, 1, -sy]]), (c1.shape[1], c1.shape[0]),
                            borderMode=cv2.BORDER_REPLICATE)
        g0 = g0.copy()
        g0[Y0:Y1, X0:X1] = c0
        d = np.abs(g1[y0:y1, x0:x1] - g0[y0:y1, x0:x1])
        m = np.ones(d.shape, bool)
        yy, xx = np.mgrid[y0:y1, x0:x1]
        for g, mp in ((f, None), (f - 1, Hm)):
            p = balls.get(g)
            if p is None:
                continue
            px, py = (p['x'], p['y']) if mp is None else LGB.apply_h(mp, p['x'], p['y'])
            m &= (xx - px) ** 2 + (yy - py) ** 2 > (2.5 * (p.get('r') or 8) + 3) ** 2
        if m.sum() < 20:
            continue
        stat[f] = round(float(d[m].mean()), 3)
    base = [stat[f] for f in range(pin_cut - PM_BASE_N, pin_cut) if f in stat]
    info = {'stat': {str(k): v for k, v in sorted(stat.items())}, 'baseline_n': len(base)}
    if len(base) < 5:
        info['why'] = 'baseline too short'
        return None, info
    thr = PM_K * float(statistics.median(base))
    info['threshold'] = round(thr, 3)
    for f in sorted(stat):
        if f >= pin_cut and stat[f] > thr and stat.get(f + 1, 0) > thr:
            return f, info
    info['why'] = 'no two consecutive frames above the threshold'
    return None, info


def deck_geometry(tr, ex, base_rows):
    """'pit' when the ball bottom at the exit frame is at/behind the back-row base row (headpin base moved 2.6 ft back
    through the edge vanishing point), else 'hidden' (still on the deck, then covered by pins)."""
    q = (tr.get('lane') or {}).get(str(ex))
    p = next((p for p in tr.get('frames') or [] if p['f'] == ex), None)
    v = [base_rows[g] for g in (ex - 1, ex, ex + 1) if g in base_rows]
    if q is None or p is None or not v:
        return 'hidden', None
    head = float(statistics.median(v))
    vp = CM.LG.vanishing_point(q)
    if vp is None or head <= vp[1]:
        return 'hidden', None
    back = vp[1] + (head - vp[1]) * (60.0 + 3.0) / (62.6 + 3.0)
    return ('pit' if p['y'] + (p.get('r') or 0) <= back else 'hidden'), round(back, 1)


def ft_cv_of(f, rel, pr):
    return 60.0 * (f - rel) / (pr - rel)


def add_depth(tr, rel, pin_cut, pr):
    tr['lane_top_down'] = [dict(p, ft_cv=round(ft_cv_of(p['f'], rel, pr), 2), ft_cv_cut=round(ft_cv_of(p['f'], rel, pin_cut), 2))
                           for p in tr.get('lane_top_down') or []]


def rolling_med(fs, vals, k):
    h = k // 2
    return [float(statistics.median([vals[j] for j in range(len(fs)) if abs(fs[j] - fs[i]) <= h])) for i in range(len(fs))]


def compute_events(tr, rel, pr):
    """Events from the tracker's own series. Pure: the mutation check calls it with a shifted pr."""
    boards = {int(k): float(v) for k, v in (tr.get('boards') or {}).items()}
    clean = {int(k): float(v) for k, v in (tr.get('boards_clean_raw') or tr.get('boards_raw') or {}).items()}
    dec = tr.get('deck_decoy_from')
    real = {p['f'] for p in tr.get('frames') or [] if p.get('src') != 'coast' and (dec is None or p['f'] < dec)}
    ft = lambda f: ft_cv_of(f, rel, pr)  # noqa: E731
    ev = {'pin_row_frame_est': pr, 'deck_decoy_from': dec}
    pre = sorted((f, boards[f]) for f in boards if pr - ENTRY_PRE <= f <= pr - 1)
    ts = CM.theil_sen(pre)
    ev['entry_board'] = None if not ts else round(ts[0] * pr + ts[1], 2)
    ev['entry_board_raw'] = clean.get(pr)
    ev['entry_n'] = len(pre)
    tail = sorted(f for f in boards if f in real and f >= pr)
    ex = tail[-1] if tail else None
    ev['exit_frame'] = ex
    ev['exit_board'] = None if ex is None else boards[ex]
    ev['exit_board_raw'] = None if ex is None else clean.get(ex)
    base_rows = {int(k): float(v) for k, v in (tr.get('base_rows') or {}).items()}
    kind, back_y = deck_geometry(tr, ex, base_rows) if ex is not None else (None, None)
    if ex is not None and kind != 'pit' and tr.get('cut_last_frame') is not None and ex >= tr['cut_last_frame'] - 1:
        kind = 'cut_end'
    ev['exit_kind'] = kind
    ev['exit_back_row_y'] = back_y
    ex_ft = None if ex is None else (60.0 if ex == pr else DECK1_FT if kind == 'pit' else DECK_MID_FT)
    ev['exit_ft_deck'] = ex_ft
    ev['deck_points'] = [] if ex is None else [
        {'f': f, 'board': boards[f], 'ft_deck': round(60.0 + (ex_ft - 60.0) * ((f - pr) / (ex - pr) if ex > pr else 0.0), 2)}
        for f in tail]
    last_pt = max(real) if real else None
    ev['exit_reason'] = (None if ex is None else 'dropped into the pit (ball bottom at/behind the back-row base row)'
                         if kind == 'pit' else 'the cut ends at f%d' % ex if kind == 'cut_end'
                         else 'last seen, ball hidden by pins after f%d' % ex)
    ev['track_last_frame'] = last_pt
    lb = [f for f in sorted(boards) if f in real]
    ev['track_last_real_frame'] = lb[-1] if lb else None
    ev['track_last_real_board'] = boards[lb[-1]] if lb else None
    ev['deck_frames'] = len(tail)
    ev['deck_frame_list'] = tail
    ev['deflection'] = None if ex is None or ev.get('entry_board') is None else (
        'straight through' if abs(ev['exit_board'] - ev['entry_board']) <= 2.0
        else 'deflected left' if ev['exit_board'] > ev['entry_board'] else 'deflected right')
    roll = sorted(f for f in clean if rel <= f <= pr)
    if len(roll) >= BREAK_MED:
        med = rolling_med(roll, [clean[f] for f in roll], BREAK_MED)
        i = min(range(len(roll)), key=lambda j: med[j])
        fb = roll[i]
        ev['breakpoint_frame'] = fb
        ev['breakpoint_board'] = round(med[i], 2)
        ev['breakpoint_ft'] = round(ft(fb), 1)
        ev['breakpoint_at_roll_end'] = bool(i >= len(roll) - 2 or i <= 1)
        ev['rise_after_break'] = round(max(med[i:]) - med[i], 2)
    else:
        ev.update(breakpoint_frame=None, breakpoint_board=None, breakpoint_ft=None, breakpoint_at_roll_end=None,
                  rise_after_break=None)
    ev['how'] = {
        'pin_row_frame_est': 'first non-coasted ball frame >= release+8 whose centre y is at/above the headpin base '
                             'row (midpoint of the pin column top and the edge pd row, 3-frame median), held on the next '
                             'real frame with >= 3 real frames after it; fallback cuts.json pin_hit',
        'entry_board': f'Theil-Sen over boards (3-frame median, cleaned) on pin_row-{ENTRY_PRE}..pin_row-1, evaluated at '
                       'pin_row; entry_board_raw = cleaned raw board at pin_row',
        'exit_frame': 'last non-coasted, moving (not deck_decoy) ball frame >= pin_row with a board; exit_board = boards '
                      'there; exit_kind pit when the ball bottom is at/behind the back-row base row (headpin base moved '
                      '2.6 ft back through the edge vanishing point), else hidden; deck depth: frames pin_row..exit spread '
                      'linearly from 60 ft to 62.6 (pit) or 61.3 (hidden)',
        'deck_frames': 'non-coasted moving ball frames with a board from pin_row to exit',
        'deflection': 'sign of exit_board - entry_board, dead band 2 boards (straight through inside it)',
        'breakpoint_ft': f'ft_cv at the minimum of the {BREAK_MED}-frame median of the cleaned raw boards over '
                         'release..pin_row; breakpoint_at_roll_end = minimum in the first/last 2 roll frames (no '
                         'measurable hook back)',
        'ft_cv': '60 * (f - release) / (pin_row_frame_est - release); release is the cuts.json input',
        'deck_decoy_from': f'first non-coasted ball point at/after pin_row-1 whose camera-compensated drift to every real point '
                           f'in the next 3 frames is < {STATIC_PX} px (a static purple patch in the pit/kickback, truth notes '
                           'finding 5; threshold read off the drift table: moving >= 3.4, static <= 2.4); frames from it on do '
                           'not count for exit, deck frames or the last real frame',
    }
    return ev


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
    txt = [f"track_v2 {tr['stem']} f{f_show} (detected pin row - 4)",
           f"entry board at the detected pin row (f{pin}): {tr.get('final_board')}  path fit: none",
           'orange = raw track; green = boards vs constant-speed depth (release 0 .. detected pin row 60 ft)',
           'dashed grey = tracker frames through the pin deck; magenta = entry board at the pin row']
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
        cv2.putText(panel, f"b{tr['final_board']:.1f} @pin row", (4, H - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
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
    frames = CM.read_frames(cut['cut_path'])
    pr_info = pin_row_estimate(tr, base.get('lane') or {}, rel, pin, frames, off)
    geo_detected = pr_info['pin_row_source'].startswith('detected')
    pr_info['pin_row_frame_geometric'] = pr_info['pin_row_frame_est'] if geo_detected else None
    mo = LGB.Motion(frames)
    pm, pm_info = pin_motion(tr, frames, off, pin, mo)
    tr['pin_motion'] = pm_info
    pr_info['pin_motion_frame'] = pm
    if pm is not None:
        pr_info['pin_row_frame_est'] = pm - PM_LEAD
        pr_info['pin_row_source'] = f'pin motion: first camera-compensated rack motion f{pm} - {PM_LEAD}'
    elif geo_detected:
        pr_info['pin_row_source'] = 'geometric: ' + pr_info['pin_row_source']
    pr_info['pin_row_minus_cut'] = pr_info['pin_row_frame_est'] - pin
    pr = pr_info['pin_row_frame_est']
    tr['deck_decoy_from'], tr['deck_motion_px'] = deck_decoy(tr, frames, off, pr, mo)
    tr['cut_last_frame'] = off + len(frames) - 1
    add_depth(tr, rel, pin, pr)
    events = compute_events(tr, rel, pr)
    events.update({k: v for k, v in pr_info.items() if k != 'pin_row_frame_est'})
    log(f'[pin row] {pr_info}')
    log(f'[events] entry {events["entry_board"]} exit f{events["exit_frame"]} {events["exit_board"]} deck {events["deck_frames"]} '
        f'break {events["breakpoint_board"]} @ {events["breakpoint_ft"]} ft')
    bm = ball_tr.get('meta') or {}
    wall = round(time.time() - t0 + (bm.get('base_wall_s') or (base.get('meta') or {}).get('wall_s') or 0.0), 1)
    out = {'stem': stem, 'method': 'track_v2', 'stage': 'both',
           'stages': {'ball': ball_name, 'lane': lane_name, 'path': 'none'},
           **tr,
           'release_frame': rel, 'pin_hit_frame': pin, 'pin_row_frame_est': pr,
           'deck_decoy_from': tr.get('deck_decoy_from'), 'deck_motion_px': tr.get('deck_motion_px'),
           'pin_motion': tr.get('pin_motion'), 'base_rows': tr.get('base_rows'),
           'events': events,
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
    quads = {int(k): v for k, v in (out.get('lane') or {}).items()}
    td = sorted((p for p in out.get('lane_top_down') or [] if p['f'] <= pr), key=lambda p: p['f'])
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
    out['meta']['overlay'] = draw_overlay_v2(frames, dict(cut, pin_hit_frame=pr), dict(draw, final_board=events['entry_board']),
                                             op, quads, hdr)
    out['meta']['overlay']['depth'] = 'ft_cv = 60 * (f - release) / (pin_row_frame_est - release); release is the cuts.json input'
    json.dump(out, open(tp, 'w'), indent=1)
    log(f'TRACK_V2 {stem}: ball={ball_name} lane={lane_name} fallback={fallback} points={len(out["frames"])} '
        f'boards={len(out.get("boards") or {})} final_board={out["final_board"]} pin_row={pr} (cut {pin}) rejected={sorted(out.get("series_rejected") or {})} '
        f'overlay={out["meta"]["overlay"]} wall={wall}s -> {tp}')


if __name__ == '__main__':
    main()
