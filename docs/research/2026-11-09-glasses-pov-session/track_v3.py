"""track_v3.py <stem> [--device mps|cpu] [--audit-log PATH]

Session 2026-11-09 integration. Ball stage = experiments/motion-only (picked by the RULES pick rule as the best
'partial', flagged: no experiment reached 'works'). Its run.py already composes the loop-2 track_v2 lane stage,
clean_series, pin_row_estimate + pin_motion, deck_decoy, add_depth, compute_events and draw_overlay_v2 by import;
this file imports that module unchanged, redirects its output folders, and writes
results/tracks/<stem>.json (loop-2 format + "stages") and overlays/final__<stem>.jpg.
An audit hook refuses any open() of the quarantine folder or of a truth/label file.

Rerun round 1 (judge hints, 2026-11-09): per-clip fallbacks, each keyed on a condition measured from the track
itself and installed as a wrapper over the imported module (run.py and track_v2.py are not edited):
  far seed   : a seed within release+SEED_NEAR frames at depth >= Z_DECK ft (at/above the headpin base row) is a
               static deck blob; the search is re-run without such candidates.
  pin row    : when pass 1 falls back to the cut pin_hit (no held crossing), pass 2 lets the SAM forward pass run to the
               cut end instead of cut pin_hit + SAM_TAIL, so the crossing window reaches cut_end before falling back.
  late jumps : when the 5-frame median board series between 15 ft and the pin row has a frame-to-frame jump > J4_JUMP
               boards, the series is re-cleaned with the jump rule at ROLL_JUMP boards over the whole roll.
  gutter     : SAM points keep the chain when the neighbour and the candidate sit in the same gutter channel (the board
               scale is extrapolated there); events.gutter is emitted when the late roll series is outside 0.5..39.5,
               and a pin-motion pin row is not used over a detected crossing while the ball is in a gutter.

Rerun round 2 (judge hints, 2026-11-09): the run is a loop of up to MAX_PASSES passes; each pass's configuration is
derived from what the previous pass measured, so a clip that passes in pass 1 is never touched:
  deck re-seed : still no held crossing after the SAM pass to the cut end -> SAM is re-prompted on the last residual
                 detection near the track end (else the last real point) in a tight crop (RESEED_SIDE_R x r_geo,
                 upscaled to ~RESEED_PX px) and propagated to the cut end; its points replace the dead/bloated tail.
  deck gate    : the J4 statistic fails (dead-band sign changes > 1 or a jump > 3 boards) and SAM points at deck depth
                 deviate > DECK_GATE_BOARDS from the residual chain -> those SAM points are rejected (sam_deck_lateral).
  gutter row   : no held crossing and the last GUTTER_TAIL track frames sit in one gutter channel by the per-frame
                 lane-first fit -> the pin row is the frame where the ball centre reaches the headpin base row inside the
                 channel (extrapolated <= GUTTER_EXTRAP frames past the track end), and pin motion is suppressed.
  entry        : events.entry_board_crossing is always written (board interpolated at the sub-frame headpin-row
                 crossing); it replaces entry_board only when fewer than 2 pre-window boards exist (entry_n < 2).
  dark seed    : no chained residual seed -> a dark-disc matched filter inside the lane-first lane (no colour) seeds the
                 chain and SAM runs from there.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import math
import os
import re
import shutil
import statistics
import sys
import time

S = '/Users/toka/code/toms_gym/docs/research/2026-11-09-glasses-pov-session'
Q = '/Users/toka/pov-holdout/2026-11-09-glasses-pov-session'
BALL_RUN = os.path.join(S, 'experiments', 'motion-only', 'run.py')
STAGE_DIR = os.path.join(S, 'work', 'v3')
PICK = {
    'ball': 'motion-only',
    'verdict': 'partial',
    'flagged': True,
    'flag': 'PARTIAL PICK: no experiment met works (recall >= 85 and entry_err <= 3 on >= 4 of 6); '
            'motion-only is the best partial by truth recall',
    'truth_recall_means': {'motion-only': 100.0, 'sam2-from-hand': 92.4, 'ball-colour-model (fails)': 74.17},
    'truth_entry_err_means': {'motion-only': 5.64, 'sam2-from-hand': 8.12, 'ball-colour-model (fails)': 6.51},
}
SEED_NEAR, Z_DECK = 20, 55.0
J4_JUMP, MED_K, ROLL_JUMP, ROLL_SEED_N = 3.0, 5, 3.0, 3
J4_DEAD = 1.0
GUTTER_LO, GUTTER_HI, GUTTER_W, GUTTER_N = 0.5, 39.5, 9.0, 10
GUTTER_MIN_PTS, GUTTER_TAIL, GUTTER_EXTRAP, GUTTER_FIT_N = 5, 15, 3, 4
HOLD_PTS = 3
MAX_PASSES = 4
RESEED_BACK, RESEED_SIDE_R, RESEED_SIDE_MIN, RESEED_SIDE_MAX, RESEED_PX = 6, 28.0, 128, 480, 768
DECK_GATE_BOARDS, DECK_REF_N = 2.0, 3
DARK_SCALE, DARK_RADII, DARK_RESP_MIN, DARK_INNER_MIN, DARK_TOP = 0.25, (2, 3, 4, 6, 8, 11, 15), 35.0, 100.0, 4
ENTRY_PRE = 6
SAFE_PREFIXES = (sys.prefix, sys.base_prefix, '/opt/homebrew', '/Library/Frameworks', '/System', '/usr/lib')
BAD_NAME = re.compile(r'(truth|label)', re.I)
_audit = {'fh': None, 'n': 0}
_ctx = {'rel': None, 'pin': None, 'off': 0, 'fallbacks': [], 'pr_info': None, 'sam_rejections': [], 'sam_channel_points': [],
        'pass': 1, 'sam_to_end': False, 'cfg': {'sam_to_end': False, 'reseed': False, 'deck_gate': False},
        'frames': None, 'lfs': None, 'device': 'mps', 'sam_cache': {}, 'lf_points': [], 'gutter_lf': None, 'deck_dev': [],
        'j4': None, 'workdir': None}
MO = TV = None


def _forbidden(p):
    ap = os.path.abspath(p)
    if ap.startswith(Q) or 'pov-holdout' in ap:
        return True
    if ap.startswith(SAFE_PREFIXES):
        return False
    return bool(BAD_NAME.search(ap))


def _hook(event, args):
    if event == 'subprocess.Popen' and _audit['fh'] is not None:
        _audit['fh'].write(f"POPEN\t{args[0]!r} {str(args[1])[:200]}\n")
        _audit['fh'].flush()
        return
    if event != 'open' or not args:
        return
    p = args[0]
    if isinstance(p, int):
        return
    try:
        p = os.fsdecode(p)
    except TypeError:
        return
    if _audit['fh'] is not None:
        _audit['n'] += 1
        _audit['fh'].write(f"{args[1] if len(args) > 1 else ''}\t{p}\n")
        _audit['fh'].flush()
    if _forbidden(p):
        raise PermissionError(f'track_v3 audit hook: refused open of {p}')


def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()[:16]


def banner(src, dst, lines):
    import cv2
    im = cv2.imread(src)
    if im is None:
        return False
    im = cv2.copyMakeBorder(im, 0, 12 + 24 * len(lines), 0, 0, cv2.BORDER_CONSTANT, value=(25, 25, 25))
    y = im.shape[0] - 12 - 24 * (len(lines) - 1)
    for t in lines:
        cv2.putText(im, t, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 200, 255), 1, cv2.LINE_AA)
        y += 24
    cv2.imwrite(dst, im, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return True


# ---------------------------------------------------------------- measured conditions (pure, reused by the checks)
def far_seed(k0, b0, k_rel):
    return k0 is not None and k0 < k_rel + SEED_NEAR and b0.get('z') is not None and b0['z'] >= Z_DECK


def channel(b):
    if b is None:
        return None
    if -GUTTER_W <= b < GUTTER_LO:
        return 'right'
    if GUTTER_HI < b <= GUTTER_HI + GUTTER_W:
        return 'left'
    return None


def med5_series(boards, rel, pr, k=MED_K):
    fs = sorted(f for f in boards if boards[f] is not None)
    h = k // 2
    med = {f: statistics.median([boards[g] for g in fs[max(0, i - h):i + h + 1]]) for i, f in enumerate(fs)}
    f15 = rel + 0.25 * (pr - rel)
    fsel = [f for f in fs if f15 <= f <= pr]
    return fsel, [med[f] for f in fsel]


def med5_max_jump(boards, rel, pr, k=MED_K):
    """Judge J4 statistic: max frame-to-frame jump of the k-frame (index) median of boards between 15 ft and pr."""
    fsel, vals = med5_series(boards, rel, pr, k)
    jumps = [(abs(b - a), fsel[i]) for i, (a, b) in enumerate(zip(vals, vals[1:]))]
    return max(jumps) if jumps else (0.0, None)


def sign_changes(vals, dead=J4_DEAD):
    """Judge J4 dead-band count (shared judge code semantics: a leg counts when it reaches `dead`)."""
    n, direction, ext = 0, 0, vals[0] if vals else 0
    for v in vals[1:]:
        if direction == 0:
            if abs(v - ext) >= dead:
                direction, ext = (1 if v > ext else -1), v
        elif direction == 1:
            if v > ext:
                ext = v
            elif ext - v >= dead:
                n, direction, ext = n + 1, -1, v
        else:
            if v < ext:
                ext = v
            elif v - ext >= dead:
                n, direction, ext = n + 1, 1, v
    return n


def j4_state(boards, rel, pr):
    fsel, vals = med5_series(boards, rel, pr)
    jump, f_at = med5_max_jump(boards, rel, pr)
    sc = sign_changes(vals) if len(vals) >= 2 else 0
    return {'n': len(vals), 'sign_changes_deadband': sc, 'max_jump': round(jump, 2), 'jump_at': f_at,
            'fails': bool(len(vals) >= 3 and (sc > 1 or jump > J4_JUMP))}


def channel_tail(lf_pts, end):
    """Evidence (c): >= GUTTER_MIN_PTS real points inside one gutter channel by the lane-first fit within the last
    GUTTER_TAIL frames of the track (ending at `end`)."""
    tail = [c for c in lf_pts or [] if end - GUTTER_TAIL <= c['f'] <= end and c.get('side')]
    for sd in ('right', 'left'):
        pts = [c for c in tail if c['side'] == sd]
        if len(pts) >= GUTTER_MIN_PTS:
            return {'side': sd, 'evidence': 'lane-first channel (all real points)', 'frames': [pts[0]['f'], pts[-1]['f']],
                    'n': len(pts), 'board_lf': [c['board_lf'] for c in pts],
                    'rule': f'>= {GUTTER_MIN_PTS} real track points inside one gutter channel by the per-frame lane-first '
                            f'fit within the last {GUTTER_TAIL} frames of the track (ends f{end})'}
    return None


def gutter_state(boards, rel, pr, channel_pts=None, last_real=None, lf_pts=None, edge_case=False):
    """events.gutter, or None. Primary evidence: the median of the last GUTTER_N cleaned roll boards before pr is
    outside 0.5..39.5. Secondary: the ball stage kept >= GUTTER_MIN_PTS SAM points inside one gutter channel by the
    per-frame lane-first fit within the last GUTTER_TAIL roll frames (the composition lane reads a gutter ball at
    board ~1 when its edge fit sits on the gutter lip). Third (round 2, only when edge_case: no held crossing or an
    entry outside the lane): the same test over every real track point."""
    late = [(f, boards[f]) for f in sorted(boards) if rel <= f < pr and boards[f] is not None][-GUTTER_N:]
    m = float(statistics.median([b for _, b in late])) if len(late) >= 3 else None
    side = None if m is None else 'right' if m < GUTTER_LO else 'left' if m > GUTTER_HI else None
    if side is not None:
        return {'side': side, 'evidence': 'late median', 'late_median': round(m, 2), 'frames': [late[0][0], late[-1][0]], 'n': len(late),
                'rule': f'median of the last {GUTTER_N} cleaned roll boards before the pin row outside {GUTTER_LO}..{GUTTER_HI}'}
    end = min(pr, last_real) if last_real is not None else pr
    tail = [c for c in channel_pts or [] if end - GUTTER_TAIL <= c['f'] <= end]
    for sd in ('right', 'left'):
        pts = [c for c in tail if c['side'] == sd]
        if len(pts) >= GUTTER_MIN_PTS:
            return {'side': sd, 'evidence': 'ball-stage lane-first channel', 'late_median': None if m is None else round(m, 2),
                    'frames': [pts[0]['f'], pts[-1]['f']], 'n': len(pts),
                    'board_lf': [c['board_lf'] for c in pts],
                    'rule': f'>= {GUTTER_MIN_PTS} SAM points kept inside one gutter channel by the per-frame lane-first fit '
                            f'within the last {GUTTER_TAIL} frames of the track (ends f{end}; late median {None if m is None else round(m, 2)} '
                            f'not outside {GUTTER_LO}..{GUTTER_HI})'}
    if edge_case:
        g = channel_tail(lf_pts, end)
        if g is not None:
            g['late_median'] = None if m is None else round(m, 2)
            return g
    return None


def theil_sen(pts):
    sl = [(b2 - b1) / (f2 - f1) for i, (f1, b1) in enumerate(pts) for f2, b2 in pts[i + 1:] if f2 != f1]
    if not sl:
        return None
    s = statistics.median(sl)
    return s, statistics.median([b - s * f for f, b in pts])


def entry_crossing(tr, pr):
    """Board at the sub-frame headpin-row crossing. t* from the real points bracketing the row at pr (centre y vs the
    3-frame-median base row), else t* = pr. Board = linear interpolation of the cleaned boards at the two bracketing
    frames; when either is missing, a Theil-Sen line over the last ENTRY_PRE cleaned boards before pr, evaluated at t*."""
    rows = {int(k): float(v) for k, v in (tr.get('base_rows') or {}).items()}
    boards = {int(k): float(v) for k, v in (tr.get('boards') or {}).items()}

    def at(f):
        v = [rows[g] for g in (f - 1, f, f + 1) if g in rows]
        return float(statistics.median(v)) if v else None

    real = sorted((p for p in tr.get('frames') or [] if p.get('src') != 'coast'), key=lambda p: p['f'])
    t = float(pr)
    how = 'no real crossing at the pin row: t* = pin row'
    i = next((i for i, p in enumerate(real) if p['f'] == pr), None)
    if i is not None and i > 0:
        a, b = real[i - 1], real[i]
        ra, rb = at(a['f']), at(b['f'])
        if ra is not None and rb is not None and a['y'] > ra and b['y'] <= rb:
            da, db = a['y'] - ra, b['y'] - rb
            t = a['f'] + da / (da - db)
            how = f"t* between f{a['f']} and f{b['f']} (centre y vs base row)"
            if a['f'] in boards and b['f'] in boards:
                w = (t - a['f']) / (b['f'] - a['f'])
                return round(boards[a['f']] + w * (boards[b['f']] - boards[a['f']]), 2), round(t, 2), how + '; boards interpolated', [a['f'], b['f']]
    pre = sorted((f, boards[f]) for f in boards if f < pr)[-ENTRY_PRE:]
    ts = theil_sen(pre) if len(pre) >= 2 else None
    return (None if ts is None else round(ts[0] * t + ts[1], 2)), round(t, 2), \
        how + f'; Theil-Sen over the last {len(pre)} cleaned boards before the pin row at t*', [pre[0][0], pre[-1][0]] if pre else None


# ---------------------------------------------------------------- round-2 mechanisms
def dark_candidates(frames, lfs, k_rel, k_end):
    """Dark-disc matched filter (inner mean of 255-gray minus the annulus r..1.6r) at per-row r_geo, inside the lane-first
    lane eroded by the annulus radius (the gutter channel is dark and adjacent), at DARK_SCALE. No colour assumption:
    every house ball is darker than the wood. Returns {k: [cand dicts]} with the find_seed fields."""
    import cv2
    import numpy as np
    out = {}
    s = DARK_SCALE
    radii = np.array(DARK_RADII, np.float32)
    for k in range(k_rel + MO.SEED_FROM, k_end + 1):
        lf = lfs.get(k)
        if lf is None:
            continue
        g = cv2.cvtColor(frames[k], cv2.COLOR_BGR2GRAY)
        gs = cv2.resize(g, None, fx=s, fy=s, interpolation=cv2.INTER_AREA).astype(np.float32)
        dark = 255.0 - gs
        h, w = dark.shape
        top = max(0.0, lf.pd_y)
        poly = np.array([[lf.xl(top) * s, top * s], [lf.xl(lf.bot_y) * s, lf.bot_y * s],
                         [lf.xr(lf.bot_y) * s, lf.bot_y * s], [lf.xr(top) * s, top * s]], np.int32)
        m = np.zeros((h, w), np.uint8)
        cv2.fillPoly(m, [poly], 255)
        rg_rows = np.array([max(0.0, MO.r_geo(lf, float(y) / s)) * s for y in range(h)], np.float32)
        near = np.argmin(np.abs(rg_rows[:, None] - radii[None, :]), axis=1)
        resp = np.full((h, w), -1.0, np.float32)
        inner_sel = np.zeros((h, w), np.float32)
        for j, r in enumerate(DARK_RADII):
            sel = near == j
            if not sel.any():
                continue
            ri, ro = int(r), int(round(1.6 * r)) + 1
            inner = cv2.filter2D(dark, -1, MO.LGB.disc_kernel(ri))
            outer = cv2.filter2D(dark, -1, MO.LGB.disc_kernel(ro))
            ai, ao = math.pi * ri * ri, math.pi * ro * ro
            ann = (outer * ao - inner * ai) / max(1.0, ao - ai)
            me = cv2.erode(m, np.ones((2 * ro + 1, 2 * ro + 1), np.uint8))
            rr = inner - ann
            rr[me == 0] = -1.0
            resp[sel] = rr[sel]
            inner_sel[sel] = inner[sel]
        dil = cv2.dilate(resp, np.ones((7, 7), np.uint8))
        peaks = np.argwhere((resp >= dil) & (resp >= DARK_RESP_MIN) & (inner_sel >= DARK_INNER_MIN))
        cs = []
        for py, px in peaks:
            x, y = float(px) / s, float(py) / s
            rg = MO.r_geo(lf, y)
            if rg <= 0:
                continue
            cs.append({'k': k, 'x': x, 'y': y, 'r': rg, 'rg': rg, 'area': 0, 'res': float(resp[py, px]),
                       'inner': float(inner_sel[py, px]), 'fill': 1.0, 'asp': 1.0, 'board': lf.board(x, y),
                       'z': lf.depth(y), 'dark': True})
        cs.sort(key=lambda c: -c['res'])
        if cs:
            out[k] = cs[:DARK_TOP]
    return out


def deck_reseed(frames, p, lfs, k_hi, tag):
    """SAM re-prompt on point p (cut-local k) in a tight square crop, propagated to k_hi. Returns ({k: (x, y, r)} for
    k > p.k in full-frame pixels, info)."""
    import cv2
    ST = sys.modules['sam_track']
    H, W = frames[0].shape[:2]
    lf = MO.trusted_lf(lfs, p['k'], p['y']) or lfs.get(p['k'])
    rg = MO.r_geo(lf, p['y']) if lf is not None else p['r']
    side = int(min(RESEED_SIDE_MAX, max(RESEED_SIDE_MIN, RESEED_SIDE_R * max(rg, 1.0))))
    side = min(side, W, H)
    scale = max(2, int(round(RESEED_PX / side)))
    x0 = int(min(max(0, p['x'] - side / 2), W - side))
    y0 = int(min(max(0, p['y'] - side / 2), H - side))
    crops = [cv2.resize(f[y0:y0 + side, x0:x0 + side], (side * scale, side * scale), interpolation=cv2.INTER_CUBIC)
             for f in frames[:k_hi + 1]]
    rr = max(p['r'], 6.0) * 1.3
    cb = [(p['x'] - rr - x0) * scale, (p['y'] - rr - y0) * scale, (p['x'] + rr - x0) * scale, (p['y'] + rr - y0) * scale]
    cb = [max(0, min(side * scale - 1, v)) for v in cb]
    log = lambda *a, **k: print(*a, **k, flush=True)  # noqa: E731
    raw = ST.propagate(crops, p['k'], cb, device=_ctx['device'], work_dir=_ctx['workdir'], tag=tag, log=log, k_end=k_hi)
    good, kd = ST.gate(raw, p['k'], log=log, k_end=k_hi)
    new, border = {}, None
    for k in sorted(good):
        cx, cy, cr, ca = good[k]
        if k <= p['k']:
            continue
        if min(cx, cy, side * scale - cx, side * scale - cy) < 2 * cr + 4:
            border = k
            break
        new[k] = (x0 + cx / scale, y0 + cy / scale, cr / scale)
    info = {'prompt': {'k': p['k'], 'f': p['k'] + _ctx['off'], 'src': p['src'], 'x': round(p['x'], 1), 'y': round(p['y'], 1), 'r': round(p['r'], 1)},
            'crop': [x0, y0, side], 'scale': scale, 'r_geo': round(rg, 1), 'masks': len(raw), 'good': len(good), 'death_k': kd,
            'border_k': border, 'points': len(new), 'k_range': [min(new), max(new)] if new else None}
    return new, info


# ---------------------------------------------------------------- wrappers installed over the motion-only module
def install(mo):
    global MO, TV
    MO, TV = mo, mo.TV
    orig_seed, orig_pre, orig_pm, orig_ev = mo.find_seed, TV.pin_row_estimate, TV.pin_motion, TV.compute_events
    orig_rf, orig_lp, orig_st, orig_stb = mo.read_frames, mo.lane_prepass, mo.sam_track, mo.sam_track_back

    def read_frames_v3(path):
        fr = orig_rf(path)
        _ctx['frames'] = fr
        return fr

    def lane_prepass_v3(frames, k_from):
        lfs = orig_lp(frames, k_from)
        _ctx['lfs'] = lfs
        return lfs

    def sam_track_v3(frames, k0, box, **kw):
        key = ('fwd', k0, tuple(round(v, 1) for v in box), kw.get('k_end'))
        if key not in _ctx['sam_cache']:
            _ctx['sam_cache'][key] = orig_st(frames, k0, box, **kw)
        else:
            print(f'  [sam2] cached forward pass {key[1:]}', flush=True)
        fwd, passes = _ctx['sam_cache'][key]
        return dict(fwd), copy.deepcopy(passes)

    def sam_track_back_v3(frames, k0, box, k_rel, **kw):
        key = ('bwd', k0, tuple(round(v, 1) for v in box), k_rel)
        if key not in _ctx['sam_cache']:
            _ctx['sam_cache'][key] = orig_stb(frames, k0, box, k_rel, **kw)
        else:
            print(f'  [sam2] cached backward pass {key[1:]}', flush=True)
        return dict(_ctx['sam_cache'][key])

    def find_seed_v3(cands_by_k, k_rel, k_end):
        k0, b0, b1, b2 = orig_seed(cands_by_k, k_rel, k_end)
        if far_seed(k0, b0, k_rel):
            dropped = {k: [round(c['z'], 1) for c in cs if c.get('z') is not None and c['z'] >= Z_DECK]
                       for k, cs in cands_by_k.items() if k < k_rel + SEED_NEAR}
            filt = {k: [c for c in cs if not (k < k_rel + SEED_NEAR and c.get('z') is not None and c['z'] >= Z_DECK)]
                    for k, cs in cands_by_k.items()}
            rej = {'k': k0, 'x': round(b0['x'], 1), 'y': round(b0['y'], 1), 'z_ft': round(b0['z'], 1)}
            k0, b0, b1, b2 = orig_seed(filt, k_rel, k_end)
            _ctx['fallbacks'].append({'far_seed': {
                'rejected_seed': rej, 'rule': f'seed within release+{SEED_NEAR} at depth >= {Z_DECK} ft (at/above the '
                'headpin base row) rejected; candidates at that depth in that window dropped, search re-run',
                'dropped_per_k': {str(k): v for k, v in dropped.items() if v},
                'reseed': None if k0 is None else {'k': k0, 'x': round(b0['x'], 1), 'y': round(b0['y'], 1), 'z_ft': round(b0['z'], 1)}}})
        if k0 is None and _ctx['frames'] is not None and _ctx['lfs']:
            dark = dark_candidates(_ctx['frames'], _ctx['lfs'], k_rel, k_end)
            k0, b0, b1, b2 = orig_seed(dark, k_rel, k_end)
            rec = {'trigger': 'no chained residual seed',
                   'rule': f'dark-disc matched filter (255-gray, disc r_geo minus annulus to 1.6 r_geo, >= {DARK_RESP_MIN} grey levels, '
                           f'inner darkness >= {DARK_INNER_MIN}) inside the lane-first lane eroded by the annulus, at {DARK_SCALE} scale, '
                           f'top {DARK_TOP} per frame; chained by the unchanged find_seed gates (3 frames); no colour assumption',
                   'frames_with_candidates': len(dark), 'candidates': sum(len(v) for v in dark.values()),
                   'seed': None if k0 is None else {'k': k0, 'f': k0 + _ctx['off'], 'x': round(b0['x'], 1), 'y': round(b0['y'], 1),
                                                    'r_geo': round(b0['rg'], 1), 'resp': round(b0['res'], 1), 'board': round(b0['board'], 2),
                                                    'z_ft': round(b0['z'], 1)}}
            if k0 is not None:
                for k, cs in dark.items():
                    cands_by_k.setdefault(k, []).extend(cs)
            _ctx['fallbacks'].append({'dark_seed': rec})
        return k0, b0, b1, b2

    def merge_once(chain, sam, motion, lfs, k_lo, k_hi, meta):
        by_k = {a['k']: a for a in chain if a['src'] != 'coast'}
        out, coast = [], 0
        deck_gate = _ctx['cfg'].get('deck_gate')
        for k in range(k_lo, k_hi + 1):
            if k in by_k:
                out.append(by_k[k])
                coast = 0
                continue
            sp = sam.get(k)
            if sp is not None:
                x, y, r = sp
                lf = mo.trusted_lf(lfs, k, y)
                rg = mo.r_geo(lf, y) if lf is not None else None
                ok, why = True, None
                if rg is not None and rg <= mo.R_FAR and not (mo.SAM_R_LO * rg <= r <= mo.SAM_R_HI * rg):
                    ok, why = False, 'sam_radius'
                    meta['gates']['sam_radius'] += 1
                if ok and lf is not None:
                    nb = [a for a in out[-4:] if a['src'] != 'coast']
                    if nb:
                        q = mo.trusted_lf(lfs, nb[-1]['k'], nb[-1]['y'])
                        if q is not None:
                            bc, bn = lf.board(x, y), q.board(nb[-1]['x'], nb[-1]['y'])
                            same_channel = channel(bn) is not None and channel(bc) == channel(bn)
                            if same_channel:
                                meta.setdefault('gutter_channel_kept', 0)
                                meta['gutter_channel_kept'] += 1
                                _ctx['sam_channel_points'].append({'k': k, 'f': k + _ctx['off'], 'board_lf': round(bc, 2), 'side': channel(bc)})
                            elif abs(bc - bn) > mo.LAT_BOARDS * (k - nb[-1]['k']):
                                ok, why = False, 'sam_lateral'
                                meta['gates']['sam_lateral'] += 1
                if ok and deck_gate and lf is not None and lf.depth(y) >= Z_DECK:
                    refs = []
                    for a in [a for a in out if a['src'] == 'residual'][-DECK_REF_N:]:
                        q = mo.trusted_lf(lfs, a['k'], a['y'])
                        if q is not None:
                            refs.append(q.board(a['x'], a['y']))
                    if refs and abs(lf.board(x, y) - statistics.median(refs)) > DECK_GATE_BOARDS:
                        ok, why = False, 'sam_deck_lateral'
                        meta['gates'].setdefault('sam_deck_lateral', 0)
                        meta['gates']['sam_deck_lateral'] += 1
                if ok:
                    out.append({'k': k, 'x': x, 'y': y, 'r': rg if rg is not None else r, 'conf': 0.6, 'src': 'sam',
                                'sam_r': round(r, 1)})
                    meta['sam_used'] += 1
                    coast = 0
                    continue
                if len(_ctx['sam_rejections']) < 80:
                    nb = [a for a in out[-4:] if a['src'] != 'coast']
                    _ctx['sam_rejections'].append({'k': k, 'gate': why, 'x': round(x, 1), 'y': round(y, 1), 'r': round(r, 1),
                                                   'rg': None if rg is None else round(rg, 1),
                                                   'board': None if lf is None else round(lf.board(x, y), 2),
                                                   'nb_k': nb[-1]['k'] if nb else None})
            pred, pb, psrc = mo.predict(out, motion, lfs, k)
            if pred is not None and coast < mo.COAST_MAX:
                coast += 1
                lf = mo.trusted_lf(lfs, k, pred[1])
                rp = mo.r_geo(lf, pred[1]) if lf is not None else out[-1]['r']
                out.append({'k': k, 'x': pred[0], 'y': pred[1], 'r': rp, 'conf': 0.2, 'src': 'coast'})
                meta['coasted_merge'] += 1
            elif pred is not None:
                break
        while out and out[-1]['src'] == 'coast':
            out.pop()
        return out

    def merge_sam_v3(chain, sam, motion, lfs, k_lo, k_hi, meta):
        snap = (copy.deepcopy(meta), list(_ctx['sam_rejections']), list(_ctx['sam_channel_points']))
        out = merge_once(chain, sam, motion, lfs, k_lo, k_hi, meta)
        if _ctx['cfg'].get('reseed') and _ctx['frames'] is not None:
            real = [a for a in out if a['src'] != 'coast']
            if real and real[-1]['k'] < k_hi - 2:
                res_pts = [a for a in real if a['src'] == 'residual' and a['k'] >= real[-1]['k'] - RESEED_BACK]
                p = res_pts[-1] if res_pts else real[-1]
                new, info = deck_reseed(_ctx['frames'], p, lfs, k_hi, f"reseed{_ctx['pass']}")
                info.update(trigger='no held headpin-row crossing after the SAM pass to the cut end',
                            prompt_rule=f'last residual point within {RESEED_BACK} frames of the track end (f{real[-1]["k"] + _ctx["off"]}), '
                                        f'else the last real point; crop {RESEED_SIDE_R} x r_geo clamped {RESEED_SIDE_MIN}..{RESEED_SIDE_MAX} px, '
                                        f'upscaled to ~{RESEED_PX} px; SAM 2 propagated to the cut end, gated and merged by the unchanged radius/lateral gates',
                            track_end_before=real[-1]['k'] + _ctx['off'])
                if new:
                    sam2 = {k: v for k, v in sam.items() if k <= p['k']}
                    sam2.update(new)
                    meta.clear()
                    meta.update(copy.deepcopy(snap[0]))
                    _ctx['sam_rejections'][:] = snap[1]
                    _ctx['sam_channel_points'][:] = snap[2]
                    out = merge_once(chain, sam2, motion, lfs, k_lo, k_hi, meta)
                    real2 = [a for a in out if a['src'] != 'coast']
                    info['track_end_after'] = real2[-1]['k'] + _ctx['off'] if real2 else None
                    info['points_kept'] = sum(1 for a in out if a['src'] == 'sam' and a['k'] > p['k'])
                _ctx['fallbacks'].append({'deck_reseed_sam': info})
        pts = []
        for a in out:
            if a['src'] == 'coast':
                continue
            lf = mo.trusted_lf(lfs, a['k'], a['y'])
            if lf is None:
                continue
            b = lf.board(a['x'], a['y'])
            pts.append({'k': a['k'], 'f': a['k'] + _ctx['off'], 'src': a['src'], 'board_lf': round(b, 2), 'side': channel(b),
                        'z_ft': round(lf.depth(a['y']), 1)})
        _ctx['lf_points'] = pts
        return out

    def relaxed_hold(tr, rel):
        rows = {int(k): float(v) for k, v in (tr.get('base_rows') or {}).items()}
        pts = sorted((p for p in tr.get('frames') or [] if p.get('src') != 'coast' and p['f'] >= rel + TV.PIN_ROW_MIN_REL),
                     key=lambda p: p['f'])

        def at(f):
            v = [rows[g] for g in (f - 1, f, f + 1) if g in rows]
            return float(statistics.median(v)) if v else None

        for i in range(len(pts) - HOLD_PTS + 1):
            run = pts[i:i + HOLD_PTS]
            bs = [at(p['f']) for p in run]
            if all(b is not None and p['y'] <= b for p, b in zip(run, bs)):
                return run[0]['f'], round(bs[0], 1), len(pts) - 1 - i
        return None, None, None

    def gutter_crossing(tr, rel):
        """Pin row for a gutter throw: the frame where the ball centre reaches the headpin base row inside the channel,
        extrapolated at most GUTTER_EXTRAP frames past the last real point from a line over the last GUTTER_FIT_N real
        points (y) and the base rows there."""
        rows = {int(k): float(v) for k, v in (tr.get('base_rows') or {}).items()}
        real = sorted((p for p in tr.get('frames') or [] if p.get('src') != 'coast' and p['f'] >= rel + TV.PIN_ROW_MIN_REL),
                      key=lambda p: p['f'])
        if not real:
            return None, None
        last = real[-1]['f']
        g = channel_tail(_ctx['lf_points'], last)
        if g is None:
            return None, None
        fit = real[-GUTTER_FIT_N:]
        if len(fit) < 2:
            return None, g
        import numpy as np
        fs = np.array([p['f'] for p in fit], float)
        ys = np.array([p['y'] for p in fit], float)
        rf = sorted(f for f in rows if last - GUTTER_FIT_N - 1 <= f <= last + 1)
        if len(rf) < 2:
            return None, g
        (vy, y0), *_ = np.linalg.lstsq(np.c_[fs, np.ones_like(fs)], ys, rcond=None)
        rfs = np.array(rf, float)
        (vr, r0), *_ = np.linalg.lstsq(np.c_[rfs, np.ones_like(rfs)], np.array([rows[f] for f in rf]), rcond=None)
        if abs(vy - vr) < 1e-6:
            return None, g
        f_star = (r0 - y0) / (vy - vr)
        gap = f_star - last
        if gap < -1.0 or gap > GUTTER_EXTRAP or vy - vr >= 0:
            g['crossing_f_star'] = round(float(f_star), 2)
            return None, g
        return {'f_star': round(float(f_star), 2), 'frame': int(round(f_star)), 'last_real': last, 'fit_frames': [int(fs[0]), int(fs[-1])],
                'closing_px_per_frame': round(float(vr - vy), 2)}, g

    def pin_row_estimate_v3(tr, base_quads, rel, pin_cut, frames, off):
        info = orig_pre(tr, base_quads, rel, pin_cut, frames, off)
        _ctx['gutter_lf'] = None
        if str(info.get('pin_row_source', '')).startswith('fallback') and (_ctx['cfg'].get('sam_to_end') or _ctx['sam_to_end']):
            f_est, row, after = relaxed_hold(tr, rel)
            if f_est is not None:
                last = max((p['f'] for p in tr.get('frames') or [] if p.get('src') != 'coast'), default=None)
                info.update(pin_row_frame_est=int(f_est), pin_row_base_y=row, pin_row_minus_cut=int(f_est) - pin_cut,
                            pin_row_source=f'detected (relaxed hold): ball centre y at the headpin base row on {HOLD_PTS} consecutive '
                                           f'real frames, {after} real frames after the crossing, track ends f{last}')
                _ctx['fallbacks'].append({'pin_row_relaxed_hold': {
                    'trigger': 'no held crossing with >= 3 real frames after it, after the SAM pass to the cut end',
                    'rule': f'{HOLD_PTS} consecutive real points at/above the headpin base row (3-frame median) from release+{TV.PIN_ROW_MIN_REL}',
                    'frame': int(f_est), 'real_frames_after': after, 'track_last_real': last}})
        if str(info.get('pin_row_source', '')).startswith('fallback'):
            gc, g = gutter_crossing(tr, rel)
            _ctx['gutter_lf'] = g
            if gc is not None:
                info.update(pin_row_frame_est=gc['frame'], pin_row_minus_cut=gc['frame'] - pin_cut,
                            pin_row_source=f"detected (gutter channel): ball in the {g['side']} gutter channel on {g['n']} of the last "
                                           f"{GUTTER_TAIL} track frames (lane-first fit); centre y reaches the headpin base row at "
                                           f"f{gc['f_star']} (line over the last {GUTTER_FIT_N} real points, track ends f{gc['last_real']})")
                _ctx['fallbacks'].append({'pin_row_gutter_crossing': {
                    'trigger': 'no held crossing and the track tail is inside one gutter channel by the lane-first fit',
                    'rule': f'pin row = frame where the ball centre reaches the headpin base row inside the channel, extrapolated '
                            f'<= {GUTTER_EXTRAP} frames past the last real point; pin motion is not used over it',
                    **gc, 'gutter': g}})
        _ctx['pr_info'] = dict(info)
        return info

    def pin_motion_v3(tr, frames, off, pin_cut, mo_):
        pm, info = orig_pm(tr, frames, off, pin_cut, mo_)
        pri = _ctx.get('pr_info') or {}
        if pm is not None and str(pri.get('pin_row_source', '')).startswith('detected'):
            boards = {int(k): float(v) for k, v in (tr.get('boards') or {}).items()}
            last = max((p['f'] for p in tr.get('frames') or [] if p.get('src') != 'coast'), default=None)
            g = gutter_state(boards, _ctx['rel'], pri['pin_row_frame_est'], _ctx['sam_channel_points'], last,
                             _ctx['lf_points'], edge_case='gutter channel' in str(pri.get('pin_row_source', '')))
            if g is not None:
                info = dict(info, why=f"suppressed: ball in the {g['side']} gutter channel at the detected crossing "
                                      f"(late median {g.get('late_median')}), rack motion at f{pm} cannot be the ball",
                            suppressed_frame=pm)
                _ctx['fallbacks'].append({'gutter_pin_motion_suppressed': {'pin_motion_frame': pm, 'geometric_frame': pri['pin_row_frame_est'], **g}})
                return None, info
        return pm, info

    def compute_events_v3(tr, rel, pr):
        boards = {int(k): float(v) for k, v in (tr.get('boards') or {}).items()}
        jump, f_at = med5_max_jump(boards, rel, pr)
        if jump > J4_JUMP:
            raw = {int(k) for k in (tr.get('boards_raw') or {})}
            roll = sorted(f for f in raw if f >= rel)
            if len(roll) > ROLL_SEED_N:
                pin = _ctx['pin']
                keep = (TV.JUMP_BOARDS, TV.TAIL_FROM, TV.SEED_N, TV.jump_reject)
                TV.JUMP_BOARDS, TV.TAIL_FROM, TV.SEED_N = ROLL_JUMP, pin - roll[ROLL_SEED_N], ROLL_SEED_N
                TV.jump_reject = lambda raw_, f_from, **kw: keep[3](raw_, f_from, jump=ROLL_JUMP, per_gap=TV.JUMP_PER_GAP, seed_n=ROLL_SEED_N)
                try:
                    before = dict(tr.get('series_rejected') or {})
                    rejected, pf = TV.clean_series(tr, rel, pin)
                finally:
                    TV.JUMP_BOARDS, TV.TAIL_FROM, TV.SEED_N, TV.jump_reject = keep
                TV.add_depth(tr, rel, pin, pr)
                tr['path_fit_diag_reclean'] = pf
                boards2 = {int(k): float(v) for k, v in (tr.get('boards') or {}).items()}
                jump2, f2 = med5_max_jump(boards2, rel, pr)
                _ctx['fallbacks'].append({'late_jump_reclean': {
                    'trigger': f'5-frame median jump {jump:.2f} > {J4_JUMP} at f{f_at} (window 15 ft..pin row f{pr})',
                    'rule': f'jump rule at {ROLL_JUMP} boards (+1 per frame skipped) walked from the {ROLL_SEED_N + 1}th roll frame '
                            f'f{roll[ROLL_SEED_N]} (seed = median of the first {ROLL_SEED_N}), instead of {keep[0]} boards from cut pin_hit-{keep[1]}',
                    'rejected_before': sorted(int(k) for k in before), 'rejected_after': sorted(rejected),
                    'med5_jump_after': round(jump2, 2), 'at_after': f2}})
        ev = orig_ev(tr, rel, pr)
        boards = {int(k): float(v) for k, v in (tr.get('boards') or {}).items()}
        last = max((p['f'] for p in tr.get('frames') or [] if p.get('src') != 'coast'), default=None)
        pri = _ctx.get('pr_info') or {}
        eb = ev.get('entry_board')
        edge_case = str(pri.get('pin_row_source', '')).startswith(('fallback', 'detected (gutter')) or eb is None or not (GUTTER_LO <= eb <= GUTTER_HI)
        g = gutter_state(boards, rel, pr, _ctx['sam_channel_points'], last, _ctx['lf_points'], edge_case=edge_case)
        if g is not None:
            ev['gutter'] = g
            ev['how']['gutter'] = g['rule'] + '; side right = boards below 0.5'
        ec, t_star, how, used = entry_crossing(tr, pr)
        ev['entry_board_crossing'] = ec
        ev['entry_t_star'] = t_star
        ev['entry_crossing_how'] = how
        ev['entry_crossing_frames'] = used
        ev['entry_board_theil_sen'] = ev.get('entry_board')
        if (ev.get('entry_n') or 0) < 2 and ec is not None:
            ev['entry_board'] = ec
            ev['entry_source'] = 'crossing'
            _ctx['fallbacks'].append({'entry_crossing': {
                'trigger': f"fewer than 2 cleaned boards in pin_row-{ENTRY_PRE}..pin_row-1 (entry_n {ev.get('entry_n')})",
                'rule': 'entry = board interpolated at the sub-frame headpin-row crossing (bracketing real points), else a Theil-Sen '
                        f'line over the last {ENTRY_PRE} cleaned boards before the pin row evaluated at t*',
                'entry': ec, 't_star': t_star, 'how': how, 'frames': used}})
        else:
            ev['entry_source'] = 'theil_sen'
        ev['how']['entry_board_crossing'] = ('board at the sub-frame crossing of the headpin base row: linear interpolation of the cleaned '
                                             'boards at the two real points bracketing the row (t* from centre y vs the 3-frame-median row), '
                                             f'else Theil-Sen over the last {ENTRY_PRE} cleaned boards before the pin row at t*; it is '
                                             'entry_board only when entry_n < 2')
        j4 = j4_state(boards, rel, pr)
        _ctx['j4'] = j4
        f15 = rel + 0.25 * (pr - rel)
        lfp = {c['f']: c for c in _ctx['lf_points']}
        dev = []
        res_b = [c for c in _ctx['lf_points'] if c['src'] == 'residual']
        for c in _ctx['lf_points']:
            if c['src'] == 'sam' and f15 <= c['f'] <= pr and c['z_ft'] >= Z_DECK:
                refs = [r['board_lf'] for r in res_b if r['f'] < c['f']][-DECK_REF_N:]
                if refs:
                    d = abs(c['board_lf'] - statistics.median(refs))
                    if d > DECK_GATE_BOARDS:
                        dev.append({'f': c['f'], 'board_lf': c['board_lf'], 'ref': round(statistics.median(refs), 2), 'dev': round(d, 2)})
        _ctx['deck_dev'] = dev
        ev['j4_measured'] = j4
        ev['sam_deck_deviations'] = dev
        return ev

    mo.find_seed, mo.merge_sam = find_seed_v3, merge_sam_v3
    mo.read_frames, mo.lane_prepass, mo.sam_track, mo.sam_track_back = read_frames_v3, lane_prepass_v3, sam_track_v3, sam_track_back_v3
    TV.pin_row_estimate, TV.pin_motion, TV.compute_events = pin_row_estimate_v3, pin_motion_v3, compute_events_v3


def run_pass(stem, device):
    _ctx.update(fallbacks=[], pr_info=None, sam_rejections=[], sam_channel_points=[], lf_points=[], gutter_lf=None, deck_dev=[], j4=None)
    sys.argv = [BALL_RUN, stem, '--device', device, '--any-stem']
    MO.main()
    return json.load(open(os.path.join(STAGE_DIR, 'tracks', f'{stem}.json')))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stem')
    ap.add_argument('--device', default='mps')
    ap.add_argument('--audit-log', default=None)
    a = ap.parse_args()
    if a.audit_log:
        _audit['fh'] = open(a.audit_log, 'w')
    sys.addaudithook(_hook)
    t0 = time.time()
    spec = importlib.util.spec_from_file_location('motion_only_run', BALL_RUN)
    mo = importlib.util.module_from_spec(spec)
    sys.modules['motion_only_run'] = mo
    spec.loader.exec_module(mo)
    mo.X = STAGE_DIR
    mo.WORK = os.path.join(STAGE_DIR, 'work')
    install(mo)
    cut = MO.load_cut(a.stem)
    stem = cut['stem']
    _ctx.update(rel=cut.get('release_frame'), pin=cut.get('pin_hit_frame'), off=cut.get('cut_start') or 0, device=a.device,
                workdir=os.path.join(STAGE_DIR, 'work', stem))
    os.makedirs(_ctx['workdir'], exist_ok=True)
    sam_tail_default = MO.SAM_TAIL
    if cut.get('cut_path'):
        _ctx['sam_to_end'] = (cut['pin_hit_frame'] - cut['cut_start'] + sam_tail_default) >= cut['nb_frames'] - 1
    cfg = {'sam_to_end': False, 'reseed': False, 'deck_gate': False}
    passes, triggers = [], []
    src = None
    for n in range(1, MAX_PASSES + 1):
        _ctx['pass'], _ctx['cfg'] = n, dict(cfg)
        MO.SAM_TAIL = 10 ** 6 if cfg['sam_to_end'] else sam_tail_default
        src = run_pass(stem, a.device)
        MO.SAM_TAIL = sam_tail_default
        ev = src.get('events') or {}
        pri = _ctx.get('pr_info') or {}
        fired = [next(iter(f)) for f in _ctx['fallbacks']]
        rec = {'n': n, 'cfg': dict(cfg), 'pin_row': src.get('pin_row_frame_est'), 'source': str(ev.get('pin_row_source'))[:80],
               'geometric_source': str(pri.get('pin_row_source'))[:60], 'points': len(src.get('frames') or []),
               'real_points': sum(1 for p in src.get('frames') or [] if p.get('src') != 'coast'),
               'track_end': max((p['f'] for p in src.get('frames') or [] if p.get('src') != 'coast'), default=None),
               'entry': ev.get('entry_board'), 'gutter': (ev.get('gutter') or {}).get('side'), 'j4': _ctx.get('j4'),
               'sam_deck_deviations': len(_ctx.get('deck_dev') or []), 'fallbacks': fired}
        passes.append(rec)
        if not cut.get('cut_path'):
            break
        src_fb = str(ev.get('pin_row_source', '')).startswith('fallback')
        geo_fb = str(pri.get('pin_row_source', '')).startswith('fallback')
        gutter = ev.get('gutter') is not None or _ctx.get('gutter_lf') is not None
        nxt, why = dict(cfg), []
        if src_fb or (geo_fb and gutter):
            if not cfg['sam_to_end']:
                nxt['sam_to_end'] = True
                why.append(f"pin row fell back ({'final' if src_fb else 'geometric, gutter evidence'}): SAM forward pass to the cut end "
                           f"(k{cut['nb_frames'] - 1}) instead of cut pin_hit + {sam_tail_default}")
            elif not cfg['reseed']:
                nxt['reseed'] = True
                why.append('pin row still fell back after the SAM pass to the cut end: deck re-seed of SAM from the last residual detection')
        j4 = _ctx.get('j4') or {}
        if j4.get('fails') and _ctx.get('deck_dev') and not cfg['deck_gate']:
            nxt['deck_gate'] = True
            why.append(f"J4 fails (dead-band sign changes {j4.get('sign_changes_deadband')}, max jump {j4.get('max_jump')}) and "
                       f"{len(_ctx['deck_dev'])} SAM deck points deviate > {DECK_GATE_BOARDS} boards from the residual chain: "
                       f"gate SAM deck points (depth >= {Z_DECK} ft) to within {DECK_GATE_BOARDS} boards")
        if nxt == cfg or n == MAX_PASSES:
            if nxt != cfg:
                triggers.append({'pass': n + 1, 'cfg': nxt, 'why': why, 'skipped': f'MAX_PASSES {MAX_PASSES} reached'})
            break
        shutil.copyfile(os.path.join(STAGE_DIR, 'tracks', f'{stem}.json'), os.path.join(STAGE_DIR, 'tracks', f'{stem}.pass{n}.json'))
        triggers.append({'pass': n + 1, 'cfg': nxt, 'why': why, 'previous': f'work/v3/tracks/{stem}.pass{n}.json'})
        cfg = nxt
    fallbacks = [{'pass_trigger': t} for t in triggers] + list(_ctx['fallbacks'])
    if len(passes) > 1:
        p1 = passes[0]
        fallbacks.insert(0, {'pin_row_pass2': {'trigger': f"pass 1 pin row fell back ({p1['source'][:70]}); track ended f{p1['track_end']}",
                                               'passes_run': len(passes), 'final_cfg': dict(cfg),
                                               'resolved': not str((src.get('events') or {}).get('pin_row_source', '')).startswith('fallback')}})
    st = src.get('stages') or {}
    stages = {
        'ball': f"{st.get('ball', 'motion-only')} [PARTIAL pick, flagged]",
        'lane': st.get('lane', 'none'),
        'pin_row': 'track_v2.pin_row_estimate (geometric headpin-row crossing) then track_v2.pin_motion override '
                   '(not over a detected crossing while the ball is in a gutter channel); relaxed hold / gutter channel crossing '
                   'when no held crossing; fallback = cut pin_hit (flagged in events.pin_row_source) after the SAM pass to the cut end '
                   'and the deck re-seed',
        'events': 'track_v2.deck_decoy + add_depth + compute_events (+ events.gutter, entry_board_crossing)',
        'path': st.get('path', 'none'),
        'pick': PICK,
    }
    out = dict(src)
    out['method'] = 'track_v3'
    out['stage'] = 'integrated'
    out['stages'] = stages
    out['pick_flag'] = PICK['flag']
    out.setdefault('meta', {})
    out['meta']['stages'] = stages
    out['meta']['track_v3'] = {'ball_run_py': BALL_RUN, 'ball_run_sha256_16': sha(BALL_RUN),
                               'track_v3_sha256_16': sha(os.path.abspath(__file__)),
                               'staging_dir': STAGE_DIR, 'wall_s_total': round(time.time() - t0, 1),
                               'audit_opens_logged': _audit['n'] if a.audit_log else None,
                               'round': 'rerun_round2',
                               'passes': passes,
                               'fallbacks': fallbacks,
                               'fallback_rules': {'far_seed': f'seed < release+{SEED_NEAR} with depth >= {Z_DECK} ft',
                                                  'dark_seed': 'no chained residual seed: dark-disc matched filter inside the lane-first lane seeds the chain',
                                                  'pin_row_pass2': 'pass 1 pin_row_source startswith fallback (or geometric fallback with gutter evidence): SAM to the cut end',
                                                  'pin_row_relaxed_hold': f'still fallback after the SAM pass to the cut end and {HOLD_PTS} consecutive real points at/above the base row exist',
                                                  'deck_reseed_sam': 'still fallback after the SAM pass to the cut end: SAM re-prompted on the last residual '
                                                                     f'detection within {RESEED_BACK} frames of the track end in a {RESEED_SIDE_R} x r_geo crop',
                                                  'pin_row_gutter_crossing': f'no held crossing and >= {GUTTER_MIN_PTS} of the last {GUTTER_TAIL} track frames in one gutter '
                                                                             f'channel (lane-first): pin row at the extrapolated (<= {GUTTER_EXTRAP} frames) base-row crossing',
                                                  'deck_gate': f'J4 fails and SAM deck points deviate > {DECK_GATE_BOARDS} boards from the residual chain: those points rejected',
                                                  'entry_crossing': 'entry_n < 2: entry_board = board at the sub-frame headpin-row crossing',
                                                  'late_jump_reclean': f'5-frame median jump > {J4_JUMP} boards in 15 ft..pin row',
                                                  'gutter': f'late median of {GUTTER_N} roll boards outside {GUTTER_LO}..{GUTTER_HI}; '
                                                            f'SAM lateral gate waived inside one channel ({GUTTER_W} boards wide); lane-first channel over all real points when no held crossing or the entry is outside the lane'},
                               'sam_rejections_final': list(_ctx['sam_rejections'])[:40],
                               'sam_channel_points': list(_ctx['sam_channel_points'])[:60],
                               'lf_points_tail': list(_ctx['lf_points'])[-GUTTER_TAIL - 5:],
                               'local_modules': sorted({os.path.abspath(m.__file__) for m in list(sys.modules.values())
                                                        if getattr(m, '__file__', None)
                                                        and not os.path.abspath(m.__file__).startswith(SAFE_PREFIXES)})}
    os.makedirs(os.path.join(S, 'results', 'tracks'), exist_ok=True)
    os.makedirs(os.path.join(S, 'overlays'), exist_ok=True)
    tp = os.path.join(S, 'results', 'tracks', f'{stem}.json')
    ov_src = os.path.join(STAGE_DIR, 'overlays', f'final__{stem}.jpg')
    ov_dst = os.path.join(S, 'overlays', f'final__{stem}.jpg')
    ev = out.get('events') or {}
    fired = [next(iter(f)) for f in fallbacks if next(iter(f)) != 'pass_trigger']
    lines = ["track_v3 | ball stage motion-only = PARTIAL pick (flagged: no experiment met 'works')",
             f"pin row f{out.get('pin_row_frame_est')}: {str(ev.get('pin_row_source', 'none'))[:60]}",
             f"entry {ev.get('entry_board')} ({ev.get('entry_source')}) at the pin row | final_board at the cut pin_hit {out.get('final_board')}"
             + (f" | gutter {ev['gutter']['side']}" if ev.get('gutter') else ''),
             f"rerun r2 passes {len(passes)}, fallbacks fired: {', '.join(fired) if fired else 'none'}"]
    out['meta']['overlay_v3'] = ov_dst if os.path.exists(ov_src) and banner(ov_src, ov_dst, lines) else None
    pic = os.path.join(STAGE_DIR, 'overlays', f'picture__{stem}.jpg')
    if os.path.exists(pic):
        shutil.copyfile(pic, os.path.join(S, 'overlays', f'picture__{stem}.jpg'))
    json.dump(out, open(tp, 'w'), indent=1)
    print(f"TRACK_V3 {stem}: points={len(out.get('frames') or [])} entry={ev.get('entry_board')} "
          f"pin_row={out.get('pin_row_frame_est')} ({str(ev.get('pin_row_source'))[:30]}) gutter={ev.get('gutter', {}).get('side') if ev.get('gutter') else None} "
          f"passes={len(passes)} fallbacks={fired} overlay={out['meta']['overlay_v3']} wall={out['meta']['track_v3']['wall_s_total']}s -> {tp}", flush=True)


if __name__ == '__main__':
    main()
