"""run.py <stem> [--device mps|cpu] [--mutate-purple]

Session 2026-11-08 experiment 'ball-colour-model' (stage: ball). The loop-2 tracker (L2/track_v2.py) with its ball
candidate source replaced:
  colour model : learned per clip from the on-lane ball at release+1..+8 (the big round not-lane blob in the lower
                 70 % of the frame; the cut starts at release-10 and the in-hand ball is below the frame, so there is
                 no in-hand disc to sample): median Lab/HSV over the eroded core, spread = MAD pooled over the frames.
                 median V < DARK_V -> 'dark' branch (darkness inside the lane edges + roundness), else 'colour' branch
                 (Lab ab distance <= tolerance, L within tolerance).
  coarse source: per frame, lane-first edge lane (LN.lane_mask + LN.fit_lane, hinted by the last ball point) ->
                 full-res mask of the model inside the lane polygon (edges inset 0.25 r_geo, rows from the pin column
                 top to the frame bottom) -> connected components -> roundness >= ROUND_MIN and r within
                 [0.4, 2.2] r_geo(row) -> the one nearest a constant-velocity prediction. The points and the edge quads
                 are written as a synthetic loop-1 base track, so LGB's lane gates, r_geo prior and SAM re-prompt all
                 run unchanged.
  LGB refine   : LGB.purple is replaced by the same model mask (HSV crop -> BGR -> model), so the far-end disc filter
                 looks for THIS ball.
Lane stage (composition edge+smooth3), clean_series, pin_row_estimate, pin_motion, deck_decoy, add_depth,
compute_events and draw_overlay_v2 are imported from track_v2 and not changed.
Writes tracks/<stem>.json (loop-2 format), overlays/final__<stem>.jpg. Never opens the truth folder.
"""
import argparse
import importlib.util
import json
import math
import os
import statistics
import sys
import time
from types import SimpleNamespace

import cv2
import numpy as np

S = '/Users/toka/code/toms_gym/docs/research/2026-11-09-glasses-pov-session'
L1 = '/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking'
L2 = '/Users/toka/code/toms_gym/docs/research/2026-11-07-glasses-pov-hook'
X = os.path.join(S, 'experiments', 'ball-colour-model')
WORK = os.path.join(X, 'work')
CUTS = os.path.join(S, 'work', 'cuts', 'cuts.json')

DARK_V = 70.0
ROUND_MIN = 0.6
R_LO, R_HI = 0.4, 2.2
BALL_UNITS = 7.78
INSET_R = 0.25
SAMPLE_FROM, SAMPLE_N = 1, 8
MIN_PIX = 40
DECK_REACH = 4.0    # a candidate above the pd row counts only once the prediction is within this many r_geo of it
CARRY_MAX = 10      # frames a failed edge fit may be bridged by the camera-carried last lane
L_DARK = 0.8        # dark branch: ball L below this fraction of the local lane wood L
AB_LANE = 18.0      # not-lane: ab distance from the band-local wood reference


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


TV2 = load('track_v2', os.path.join(L2, 'track_v2.py'))
LGB, CM = TV2.LGB, TV2.CM
LN = CM.LN
LG = CM.LG


def load_cut(stem):
    return {c['stem']: c for c in json.load(open(CUTS))}[stem]


LGB.load_cut = load_cut
CM.load_cut = load_cut
TV2.WORK = WORK
LGB.PIN_TAIL = 10 ** 6


def read_frames(path):
    cap = cv2.VideoCapture(path)
    out = []
    while True:
        ok, im = cap.read()
        if not ok:
            break
        out.append(im)
    cap.release()
    return out


# ---------------------------------------------------------------- colour model
def sample_ball(im, y_frac=0.3):
    """The big round not-lane blob below y_frac of the frame, at 320 px wide: (core Lab pixels, core HSV pixels, info)."""
    h0, w0 = im.shape[:2]
    Wd = 320
    Hd = int(h0 * Wd / w0)
    sm = cv2.resize(im, (Wd, Hd), interpolation=cv2.INTER_AREA)
    lab = cv2.cvtColor(sm, cv2.COLOR_BGR2LAB).astype(np.float32)
    hsv = cv2.cvtColor(sm, cv2.COLOR_BGR2HSV)
    y0 = int(Hd * y_frac)
    ref = np.median(lab[y0:].reshape(-1, 3), axis=0)
    L = lab[..., 0]
    mu = cv2.blur(L, (7, 7))
    sd = np.sqrt(np.maximum(cv2.blur(L * L, (7, 7)) - mu * mu, 0))
    notlane = (L < 0.6 * ref[0]) | (np.sqrt(((lab[..., 1:] - ref[1:]) ** 2).sum(-1)) > 30)
    m = (notlane & (sd < 40)).astype(np.uint8)
    m[:y0] = 0
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n, lb, st, _ = cv2.connectedComponentsWithStats(m)
    best = None
    for c in range(1, n):
        area = int(st[c, cv2.CC_STAT_AREA])
        if area < 120:
            continue
        ys, xs = np.nonzero(lb == c)
        (cx, cy), r = cv2.minEnclosingCircle(np.stack([xs, ys], 1).astype(np.float32))
        if r > Wd * 0.25:
            continue
        rnd = area / max(1.0, math.pi * r * r)
        if rnd < 0.65:
            continue
        if best is None or area > best[1]:
            best = (c, area, rnd, cx, cy, r)
    if best is None:
        return None, None, {'found': False}
    core = cv2.erode((lb == best[0]).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    if core.sum() < 50:
        core = lb == best[0]
    info = {'found': True, 'area': best[1], 'round': round(float(best[2]), 2),
            'cx': round(best[3] * w0 / Wd, 1), 'cy': round(best[4] * w0 / Wd, 1), 'r': round(best[5] * w0 / Wd, 1)}
    return lab[core], hsv[core].astype(np.float32), info


def learn_model(frames, k_rel, log):
    labs, hsvs, per = [], [], []
    for k in range(k_rel + SAMPLE_FROM, min(len(frames), k_rel + SAMPLE_FROM + SAMPLE_N)):
        la, hs, info = sample_ball(frames[k])
        per.append({'k': k, **info})
        if la is not None:
            labs.append(la)
            hsvs.append(hs)
    if not labs:
        return None
    lab = np.concatenate(labs)
    hsv = np.concatenate(hsvs)
    med_lab = np.median(lab, axis=0)
    med_hsv = np.median(hsv, axis=0)
    mad_lab = np.median(np.abs(lab - med_lab), axis=0) * 1.4826
    mad_v = float(np.median(np.abs(hsv[:, 2] - med_hsv[2])) * 1.4826)
    dark = bool(med_hsv[2] < DARK_V)
    model = {'kind': 'dark' if dark else 'colour', 'lab': [round(float(v), 1) for v in med_lab],
             'hsv': [round(float(v), 1) for v in med_hsv], 'lab_mad': [round(float(v), 1) for v in mad_lab],
             'v_mad': round(mad_v, 1), 'n_frames': len(labs), 'n_pixels': int(len(lab)), 'per_frame': per,
             'sample': f'on-lane ball at release+{SAMPLE_FROM}..+{SAMPLE_FROM + SAMPLE_N - 1} (cut starts at release-10: no in-hand disc in frame)'}
    model['ab_tol'] = round(float(min(40.0, max(22.0, 2.5 * math.hypot(mad_lab[1], mad_lab[2])))), 1)
    if dark:
        model['rule'] = (f'inside the lane polygon: L < {L_DARK} x band-local wood L or ab distance from the wood > {AB_LANE}, '
                         f'and ab distance to the ball model <= {model["ab_tol"]}; roundness >= {ROUND_MIN}, r within [{R_LO}, {R_HI}] r_geo')
    else:
        model['rule'] = (f'inside the lane polygon: ab distance from the band-local wood > {AB_LANE} and ab distance to the ball '
                         f'model <= {model["ab_tol"]}; roundness >= {ROUND_MIN}, r within [{R_LO}, {R_HI}] r_geo')
    log(f'  [model] {model["kind"]}: lab {model["lab"]} hsv {model["hsv"]} mad {model["lab_mad"]} from {len(labs)} frames; {model["rule"]}')
    return model


def band_refs(lab, poly, pd_y, nb=8):
    """Median Lab of the lane wood per row band inside the polygon, rows below the pd row only (pins and deck sit
    above it); rows above take the topmost wood band's value. Returns (edges, refs)."""
    ys = np.where(poly.any(axis=1))[0]
    if len(ys) == 0:
        return None
    lo = int(max(ys[0], pd_y + 2))
    hi = int(ys[-1]) + 1
    if hi - lo < 16:
        lo = int(ys[0])
    edges = np.linspace(lo, hi, nb + 1).astype(int)
    refs = []
    for a, b in zip(edges, edges[1:]):
        band = poly[a:b] > 0
        refs.append(np.median(lab[a:b][band], axis=0) if band.sum() >= 50 else None)
    first = next((r for r in refs if r is not None), None)
    if first is None:
        return None
    refs = [first if r is None else r for r in refs]
    return edges, refs


def mask_of(bgr, model, poly=None, pd_y=None):
    """float32 0/1 mask of ball pixels. Lane mode (poly given): not-lane against the band-local wood reference
    (dark branch: L < L_DARK x ref L, or ab distance from the wood > AB_LANE; colour branch: the ab test only) AND ab
    distance to the model <= ab_tol. Crop mode (LGB refine, no polygon): ab distance to the model <= ab_tol, and for
    the dark branch L below L_DARK x the crop's median L."""
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    chroma = np.hypot(lab[..., 1] - model['lab'][1], lab[..., 2] - model['lab'][2]) <= model['ab_tol']
    if poly is None:
        if model['kind'] == 'dark':
            return (chroma & (lab[..., 0] < L_DARK * float(np.median(lab[..., 0])))).astype(np.float32)
        return chroma.astype(np.float32)
    br = band_refs(lab, poly, pd_y if pd_y is not None else 0)
    out = np.zeros(bgr.shape[:2], bool)
    if br is None:
        return out.astype(np.float32)
    edges, refs = br
    for (a, b), ref in zip(zip(edges, edges[1:]), refs):
        d = np.hypot(lab[a:b, :, 1] - ref[1], lab[a:b, :, 2] - ref[2]) > AB_LANE
        if model['kind'] == 'dark':
            d |= lab[a:b, :, 0] < L_DARK * ref[0]
        out[a:b] = d
    ys = np.where(poly.any(axis=1))[0]
    if len(ys) and ys[0] < edges[0]:
        a, b = int(ys[0]), int(edges[0])
        ref = refs[0]
        d = np.hypot(lab[a:b, :, 1] - ref[1], lab[a:b, :, 2] - ref[2]) > AB_LANE
        if model['kind'] == 'dark':
            d |= lab[a:b, :, 0] < L_DARK * ref[0]
        out[a:b] = d
    return (out & chroma & (poly > 0)).astype(np.float32)


def purple_original(hsv, sat=30):
    return ((hsv[..., 0] >= 112) & (hsv[..., 0] <= 170) & (hsv[..., 1] >= sat)).astype(np.float32)


def install_model(model, mutate):
    if mutate:
        LGB.purple = purple_original
        return
    LGB.purple = lambda hsv, sat=30: mask_of(cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR), model)


# ---------------------------------------------------------------- coarse source
def lane_polygon(shape, lf, y_top, r_of_y):
    H, W = shape[:2]
    rows = np.arange(int(max(0, y_top)), H, 8.0)
    rows = np.append(rows, H - 1)
    left = [(lf.xl(y) + INSET_R * r_of_y(y), y) for y in rows]
    right = [(lf.xr(y) - INSET_R * r_of_y(y), y) for y in rows]
    poly = np.array(left + right[::-1], np.int32)
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [poly], 1)
    return m


def r_geo_fn(lf):
    return lambda y: 0.5 * BALL_UNITS * max(lf.width(y), 1.0) / 38.0


def detect(im, model, lf, pred, pred_r, y_top, mutate):
    """Ball candidates in one frame inside the lane polygon: [(x, y, r, score, roundness)] best first."""
    rg = r_geo_fn(lf)
    poly = lane_polygon(im.shape, lf, y_top, rg)
    if mutate:
        m = purple_original(cv2.cvtColor(im, cv2.COLOR_BGR2HSV)) * poly
    else:
        m = mask_of(im, model, poly, lf.pd_y)
    m = m.astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lb, st, cen = cv2.connectedComponentsWithStats(m)
    cands = []
    for c in range(1, n):
        area = int(st[c, cv2.CC_STAT_AREA])
        if area < MIN_PIX:
            continue
        cx, cy = float(cen[c][0]), float(cen[c][1])
        rgeo = rg(cy)
        if area < 0.3 * math.pi * rgeo * rgeo:
            continue
        w, h = int(st[c, cv2.CC_STAT_WIDTH]), int(st[c, cv2.CC_STAT_HEIGHT])
        asp = w / max(h, 1)
        if not 0.5 <= asp <= 2.0:
            continue
        ys, xs = np.nonzero(lb == c)
        (ex, ey), er = cv2.minEnclosingCircle(np.stack([xs, ys], 1).astype(np.float32))
        rnd = area / max(1.0, math.pi * er * er)
        r = math.sqrt(area / math.pi)
        d = 0.0 if pred is None else math.hypot(cx - pred[0], cy - pred[1])
        if cy < lf.pd_y and (pred is None or pred[1] > lf.pd_y + DECK_REACH * rgeo):
            continue
        rmin = ROUND_MIN - 0.1 if (pred is not None and d <= 1.5 * max(pred_r or rgeo, rgeo)) else ROUND_MIN
        if rnd < rmin or not (R_LO * rgeo <= r <= R_HI * rgeo):
            continue
        if pred is not None and d > 4 * max(pred_r or rgeo, rgeo) + 60:
            continue
        score = rnd - 0.002 * d
        cands.append((cx, cy, r, score, rnd))
    cands.sort(key=lambda t: -t[3])
    return cands


def coarse_track(frames, cut, model, mutate, log):
    """Per-frame detections + edge quads in SOURCE frames: a synthetic loop-1 base track for LGB. The camera model
    (ORB homography chain, loop-1 cam-diff Motion) carries the last lane fit through frames where the edge fit fails
    (<= CARRY_MAX frames, quads flagged src 'edge-carry') and moves the last two points into the current frame for the
    constant-velocity prediction."""
    off, rel, pin = cut['cut_start'], cut['release_frame'], cut['pin_hit_frame']
    H, W = frames[0].shape[:2]
    k_rel = rel - off
    mo = LGB.Motion(frames)
    pts, quads, prev_mask = {}, {}, None
    info = {'no_lane': 0, 'lane_carried': 0, 'no_cand': 0, 'lane_why': {}, 'orb_failed_pairs': sum(1 for h in mo.H[1:] if h is None)}
    last = []
    lf_last, k_lf = None, None
    for k in range(k_rel, len(frames)):
        im = frames[k]
        if len(last) >= 2:
            (k0, x0, y0, r0), (k1, x1, y1, r1) = last[-2], last[-1]
            ax, ay = LGB.apply_h(LGB.compose(mo, k1, k), x1, y1)
            bx, by = LGB.apply_h(LGB.compose(mo, k0, k), x0, y0)
            dt = (k - k1) / (k1 - k0)
            pred, pred_r = (ax + (ax - bx) * dt, ay + (ay - by) * dt), r1
        elif last:
            k1, x1, y1, r1 = last[-1]
            pred, pred_r = LGB.apply_h(LGB.compose(mo, k1, k), x1, y1), r1
        else:
            pred, pred_r = None, None
        hint = pred if pred is not None else (W / 2, H * 0.9)
        mask = LN.lane_mask(im)
        lf, linfo = LN.fit_lane(mask, prev_mask, hint)
        src = 'edge'
        if lf is None:
            info['no_lane'] += 1
            why = linfo.get('why')
            info['lane_why'][why] = info['lane_why'].get(why, 0) + 1
            if lf_last is None or k - k_lf > CARRY_MAX:
                continue
            cx0, cy0 = 0.5 * (lf_last.xl(lf_last.pd_y) + lf_last.xr(lf_last.pd_y)), lf_last.pd_y
            cx1, cy1 = LGB.apply_h(LGB.compose(mo, k_lf, k), cx0, cy0)
            lf = lf_last.shifted(cx1 - cx0, cy1 - cy0)
            src = 'edge-carry'
            info['lane_carried'] += 1
        else:
            prev_mask = LN.component_mask(mask, lf.comp_id)
            lf_last, k_lf = lf, k
        q = lf.quad()
        q['src'] = src
        quads[str(k + off)] = q
        top = TV2.column_top(im, q)
        y_top = lf.pd_y - 0.6 * (lf.pd_y - top) if top is not None and top < lf.pd_y else lf.pd_y - 30
        cands = detect(im, model, lf, pred, pred_r, y_top, mutate)
        if not cands:
            info['no_cand'] += 1
            continue
        cx, cy, r, score, rnd = cands[0]
        pts[k] = (cx, cy, r)
        last.append((k, cx, cy, r))
        last = last[-4:]
    base = {'stem': cut['stem'], 'method': 'ball-colour-model/coarse', 'stage': 'ball',
            'frames': [{'f': k + off, 'x': round(v[0], 1), 'y': round(v[1], 1), 'r': round(v[2], 1), 'conf': 0.8,
                        'src': 'colour'} for k, v in sorted(pts.items())],
            'lane': quads, 'boards': {}, 'final_board': None, 'release_frame': rel, 'pin_hit_frame': pin,
            'meta': {'model': {k: v for k, v in model.items() if k != 'per_frame'}, 'coarse_info': info, 'wall_s': 0.0}}
    log(f'  [coarse] {len(pts)} points on {len(frames) - k_rel} frames from release, {len(quads)} quads ({info["lane_carried"]} carried), '
        f'no lane {info["no_lane"]} ({info["lane_why"]}), no candidate {info["no_cand"]}')
    return base


# ---------------------------------------------------------------- stages
def ball_stage(stem, base_path, device):
    wd = os.path.join(WORK, 'lgb')
    for d in ('tracks', 'overlays', 'work'):
        os.makedirs(os.path.join(wd, d), exist_ok=True)
    LGB.X = wd
    argv = sys.argv
    try:
        sys.argv = ['run.py', stem, '--device', device, '--base', base_path]
        LGB.main()
    finally:
        sys.argv = argv
    return json.load(open(os.path.join(wd, 'tracks', f'{stem}.json')))


def lane_stage(stem, balls, device, log):
    CM.ball_stage = lambda s, cut, how, lg: ([dict(p) for p in balls], 'ball-colour-model ball stage (injected)')
    wd = os.path.join(WORK, 'comp')
    args = SimpleNamespace(device=device, lane='edge', refine=False, smooth=3, ball='file', out_dir=wd)
    return CM.run(stem, args, log)


def proxies(out, rel, pr):
    real = {p['f'] for p in out['frames'] if p.get('src') != 'coast'}
    lo, hi = rel + 5, pr
    n = hi - lo + 1
    det = sum(1 for f in range(lo, hi + 1) if f in real) / n if n > 0 else None
    clean = {int(k): float(v) for k, v in (out.get('boards_clean_raw') or out.get('boards_raw') or {}).items()}
    fs = sorted(f for f in clean if lo <= f <= hi)
    jump = None
    if len(fs) >= 2:
        med = TV2.rolling_med(fs, [clean[f] for f in fs], 5)
        jump = round(max(abs(b - a) for a, b in zip(med, med[1:])), 2)
    return {'detection_rate': None if det is None else round(det, 3), 'window': [lo, hi], 'real_in_window': sum(1 for f in range(lo, hi + 1) if f in real),
            'max_board_jump_med5': jump, 'pin_row_detected': not out['events']['pin_row_source'].startswith('fallback')}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stem')
    ap.add_argument('--device', default='mps')
    ap.add_argument('--mutate-purple', action='store_true', help='mutation check: the fixed purple window of loop 2 instead of the learned model')
    a = ap.parse_args()
    log = lambda *x, **k: print(*x, **k, flush=True)  # noqa: E731
    t0 = time.time()
    stem = a.stem
    cut = load_cut(stem)
    rel, pin, off = cut['release_frame'], cut['pin_hit_frame'], cut['cut_start']
    frames = read_frames(cut['cut_path'])
    model = learn_model(frames, rel - off, log)
    if model is None:
        raise SystemExit(f'{stem}: no ball sample at release+{SAMPLE_FROM}..')
    install_model(model, a.mutate_purple)
    t_model = round(time.time() - t0, 1)
    t1 = time.time()
    base = coarse_track(frames, cut, model, a.mutate_purple, log)
    t_coarse = round(time.time() - t1, 1)
    os.makedirs(os.path.join(WORK, 'coarse'), exist_ok=True)
    base_path = os.path.join(WORK, 'coarse', f'{stem}.json')
    json.dump(base, open(base_path, 'w'), indent=1)
    fallback = []
    # ---- ball (LGB gated re-walk over the colour-model coarse points)
    ball_tr, ball_err = None, None
    t1 = time.time()
    try:
        ball_tr = ball_stage(stem, base_path, a.device)
        if not TV2.in_roll(ball_tr.get('frames') or [], rel, pin):
            ball_err, ball_tr = 'no ball point in release..pin_hit', None
    except Exception as e:  # noqa: BLE001
        ball_err = f'{type(e).__name__}: {e}'
    t_lgb = round(time.time() - t1, 1)
    if ball_tr is None:
        log(f'[ball] lane-gated-ball failed ({ball_err}); coarse colour-model points')
        fallback.append('ball')
        ball_tr = base
        ball_name = 'colour-model coarse (LGB fallback)'
    else:
        ball_name = 'lane-gated-ball over colour-model coarse'
    coasted = [p['f'] for p in ball_tr['frames'] if p.get('src') == 'coast']
    balls = [{k: p.get(k) for k in ('f', 'x', 'y', 'r', 'conf', 'src')} for p in ball_tr['frames'] if p.get('src') != 'coast']
    # ---- lane (unchanged loop-2 stage)
    lane_tr, lane_err = None, None
    t1 = time.time()
    try:
        lane_tr = lane_stage(stem, balls, a.device, log)
        nb = sum(1 for p in TV2.in_roll(balls, rel, pin) if str(p['f']) in (lane_tr.get('boards') or {}))
        nr = len(TV2.in_roll(balls, rel, pin))
        if nr == 0 or nb < TV2.LANE_MIN_FRAC * nr or lane_tr.get('final_board') is None:
            lane_err = f'boards on {nb}/{nr} roll frames, final_board {lane_tr.get("final_board")}'
            lane_tr = None
    except Exception as e:  # noqa: BLE001
        lane_err = f'{type(e).__name__}: {e}'
    t_lane = round(time.time() - t1, 1)
    if lane_tr is None:
        log(f'[lane] composition edge lane failed ({lane_err}); coarse edge quads at the ball centre row')
        fallback.append('lane')
        tr = {'frames': [dict(p) for p in balls], 'lane': base['lane'], 'boards': {}, 'boards_raw': {}, 'final_board': None,
              'lane_top_down': [], 'lane_top_down_model': {'a': 60.0, 'b': 0.0}}
        for p in balls:
            q = base['lane'].get(str(p['f']))
            if q:
                b = LG.lane_point(q, p['x'], p['y'])[0]
                if b is not None:
                    tr['boards'][str(p['f'])] = round(b, 2)
        tr['boards_raw'] = dict(tr['boards'])
        lane_name = 'coarse edge quads (fallback)'
        lane_meta = {'lane_variant': 'coarse-edge', 'fallback_used': True}
        diag = None
    else:
        tr = {k: lane_tr.get(k) for k in ('frames', 'lane', 'boards', 'boards_raw', 'boards_contact', 'final_board',
                                          'lane_top_down', 'lane_top_down_model')}
        lane_name = 'composition/edge+smooth3'
        tr['final_board_pre_fixpass'] = tr.get('final_board')
        rejected, pf_clean = TV2.clean_series(tr, rel, pin)
        log(f'[series] rejected {sorted(rejected)}; final_board {tr["final_board_pre_fixpass"]} -> {tr["final_board"]}')
        lane_meta = {k: lane_tr['meta'].get(k) for k in ('lane_variant', 'lane_sources', 'edge_fit_failures',
                                                           'edge_fail_reasons', 'fallback_used', 'smooth', 'lane_s', 'board_row')}
        diag = pf_clean
    # ---- pin row, deck, events (unchanged loop-2 functions)
    t1 = time.time()
    pr_info = TV2.pin_row_estimate(tr, base.get('lane') or {}, rel, pin, frames, off)
    geo_detected = pr_info['pin_row_source'].startswith('detected')
    pr_info['pin_row_frame_geometric'] = pr_info['pin_row_frame_est'] if geo_detected else None
    mo = LGB.Motion(frames)
    pm, pm_info = TV2.pin_motion(tr, frames, off, pin, mo)
    tr['pin_motion'] = pm_info
    pr_info['pin_motion_frame'] = pm
    if pm is not None:
        pr_info['pin_row_frame_est'] = pm - TV2.PM_LEAD
        pr_info['pin_row_source'] = f'pin motion: first camera-compensated rack motion f{pm} - {TV2.PM_LEAD}'
    elif geo_detected:
        pr_info['pin_row_source'] = 'geometric: ' + pr_info['pin_row_source']
    pr_info['pin_row_minus_cut'] = pr_info['pin_row_frame_est'] - pin
    pr = pr_info['pin_row_frame_est']
    tr['deck_decoy_from'], tr['deck_motion_px'] = TV2.deck_decoy(tr, frames, off, pr, mo)
    tr['cut_last_frame'] = off + len(frames) - 1
    TV2.add_depth(tr, rel, pin, pr)
    events = TV2.compute_events(tr, rel, pr)
    events.update({k: v for k, v in pr_info.items() if k != 'pin_row_frame_est'})
    t_events = round(time.time() - t1, 1)
    log(f'[pin row] {pr_info["pin_row_frame_est"]} (cut {pin}) {pr_info["pin_row_source"]}')
    log(f'[events] entry {events["entry_board"]} exit f{events["exit_frame"]} {events["exit_board"]} deck {events["deck_frames"]} '
        f'break {events["breakpoint_board"]} @ {events["breakpoint_ft"]} ft')
    bm = ball_tr.get('meta') or {}
    wall = round(time.time() - t0, 1)
    out = {'stem': stem, 'method': 'ball-colour-model', 'stage': 'both',
           'stages': {'ball': ball_name, 'lane': lane_name, 'path': 'none',
                      'ball_model': {k: v for k, v in model.items() if k != 'per_frame'},
                      'mutate_purple': bool(a.mutate_purple)},
           **tr,
           'release_frame': rel, 'pin_hit_frame': pin, 'pin_row_frame_est': pr,
           'events': events,
           'final_board_rule': 'Theil-Sen over boards in pin_hit-10..pin_hit evaluated at pin_hit (composition fit_path), on the series after clean_series'
           if lane_name.startswith('composition') else 'none (lane fallback)',
           'path_fit_diag': diag,
           'fallback': fallback, 'fallback_reasons': {'ball': ball_err, 'lane': lane_err},
           'meta': {'device': a.device, 'cut_start': off, **lane_meta,
                    'ball_model_per_frame': model['per_frame'],
                    'coarse_info': base['meta']['coarse_info'], 'coarse_points': len(base['frames']),
                    'coasted_frames': coasted, 'coast_note': 'LGB coast points (homography predictions, no detection) are dropped before the lane stage: 113911 f475-477 read boards 31 on a 20-board line during a head whip',
                    'ball_meta': {k: bm.get(k) for k in ('gates', 'refined', 'refine_rejected', 'coasted', 'sam_reprompts',
                                                         'sam_candidates_used', 'stage_wall_s')},
                    'stages': {'ball': ball_name, 'lane': lane_name, 'path': 'none', 'ball_model_kind': model['kind']},
                    'stage_s': {'read_and_model_s': t_model, 'coarse_s': t_coarse, 'lgb_s': t_lgb,
                                'lane_s': t_lane, 'events_s': t_events},
                    'wall_s': wall, 'wall_note': 'whole process, nothing read from a previous run'}}
    out['proxies'] = proxies(out, rel, pr)
    os.makedirs(os.path.join(X, 'tracks'), exist_ok=True)
    os.makedirs(os.path.join(X, 'overlays'), exist_ok=True)
    tag = '__mutpurple' if a.mutate_purple else ''
    tp = os.path.join(X, 'tracks', f'{stem}{tag}.json')
    quads = {int(k): v for k, v in (out.get('lane') or {}).items()}
    op = os.path.join(X, 'overlays', f'final__{stem}{tag}.jpg')
    hdr = [f"ball {ball_name} [{model['kind']}] | lane {lane_name} | fallback {fallback or '-'}",
           f"series rejected {sorted(int(k) for k in out.get('series_rejected') or {}) or '-'} | pin row {pr} ({'detected' if out['proxies']['pin_row_detected'] else 'FALLBACK'}) | det {out['proxies']['detection_rate']}"]
    out['meta']['overlay'] = TV2.draw_overlay_v2(frames, dict(cut, pin_hit_frame=pr), dict(out, final_board=events['entry_board']),
                                                 op, quads, hdr)
    json.dump(out, open(tp, 'w'), indent=1)
    log(f'BCM {stem}: model={model["kind"]} ball={ball_name} lane={lane_name} fallback={fallback} points={len(out["frames"])} '
        f'boards={len(out.get("boards") or {})} entry={events["entry_board"]} pin_row={pr} (cut {pin}) proxies={out["proxies"]} wall={wall}s -> {tp}')


if __name__ == '__main__':
    main()
