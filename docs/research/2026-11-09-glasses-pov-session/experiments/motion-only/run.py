"""run.py <stem> [--device mps|cpu] [--no-sam] [--any-stem]

Session 2026-11-09 experiment 'motion-only' (stage: ball). Appearance-free ball candidates:
  camera : ORB + RANSAC homography between consecutive frames (loop-1 cam-diff Motion), three-frame residual
           min(|I_t - warp(I_t-1)|, |I_t - warp(I_t+1)|) inside the lane polygon of a per-frame lane-first fit;
  blob   : compact residual blobs (aspect <= 2, fill >= 0.3) whose half-extent follows the geometric radius prior
           r_geo = 0.5 * 7.78 * lane_width_px(row) / 38 (ball 8.5 in; 4-13 px at the pins), chained with a <= 3
           boards/frame lateral gate and an image jump gate, coast <= 3 frames;
  SAM 2  : loop-1 sam2-video propagation prompted with a box on the first chained residual blob (never a colour
           blob), forward to the cut end and backward to release; fills frames the chain missed, gated by the same
           radius band (0.4..2.2 x r_geo where r_geo <= 16: the SAM mask bloats at the deck) and lateral gate.
Lane stage, series cleaning, pin-row estimate, pin motion, deck events and the overlay are the loop-2 track_v2
functions imported from L2 (composition edge lane with the ball points injected). Writes tracks/<stem>.json in the
loop-2 tracks format, overlays/final__<stem>.jpg and overlays/picture__<stem>.jpg (crops at ~20/40/55 ft).
Runs only on the dev stems unless --any-stem; never opens truth or the quarantine folder.
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
X = os.path.join(S, 'experiments', 'motion-only')
WORK = os.path.join(X, 'work')
DEV = {'104946', '105652', '110442', '111631', '112800', '113911', '114631', '115157'}

BALL_UNITS = 7.78
R_LO, R_HI = 0.45, 1.6          # residual blob half-extent / r_geo
SAM_R_LO, SAM_R_HI = 0.4, 2.2   # SAM r / r_geo where r_geo <= R_FAR
R_FAR = 16.0
LAT_BOARDS = 3.0
RES_THR = 14
FAR_R = 14.0                    # rows where r_geo <= 14 px use a disc-matched filter on the residual (the 3-frame min leaves crescents)
FAR_RADII = (5, 8, 11)
FAR_RESP_MIN, FAR_INNER_MIN, FAR_TOP = 8.0, 6.0, 6
MIN_AREA = 6
ASPECT_MAX, FILL_MIN = 2.0, 0.30
COAST_MAX = 3
JUMP_GAP_CAP = 2                # the jump allowance grows with frames coasted, but at most 2x (113911 f478 took a far peak 247 px off after 3 coasts)
SEED_FROM = 3                   # chain search starts at release + 3 (ball clear of the hand)
ROI_MARGIN, ROI_UP = 0.15, 0.25  # lane polygon widened by 15 % of the width, extended 25 % of the span past the pd row
QUAD_SMOOTH = 0.10
PIN_ROW_MIN_REL = 8
SAM_TAIL = 12                   # SAM propagation stops at cut pin_hit + 12 (the residual chain follows the deck)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


TV = load('track_v2', os.path.join(L2, 'track_v2.py'))
CM, LGB = TV.CM, TV.LGB
LG, LN = CM.LG, CM.LN
from camdiff import Motion, residual  # noqa: E402  (sys.path set by lane-gated-ball)
from sam_track import track as sam_track, track_back as sam_track_back  # noqa: E402


def load_cut(stem):
    cuts = json.load(open(os.path.join(S, 'work', 'cuts', 'cuts.json')))
    for c in cuts:
        if c['stem'] == stem or c['stem'].split('_')[1] == stem:
            return c
    raise KeyError(stem)


CM.load_cut = load_cut


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


# ---------------------------------------------------------------- lane pre-pass (lane-first, no ball needed)
def lane_prepass(frames, k_from):
    lfs, prev = {}, None
    H, W = frames[0].shape[:2]
    hint = (W / 2.0, 0.85 * H)
    for k in range(k_from, len(frames)):
        m = LN.lane_mask(frames[k])
        lf, info = LN.fit_lane(m, prev, hint)
        hint = None
        if lf is None or lf.pd_y < 60 or lf.width(lf.pd_y) <= 4:
            continue
        lfs[k] = lf
        prev = LN.component_mask(m, lf.comp_id)
    return lfs


def trusted_lf(lfs, k, y):
    lf = lfs.get(k)
    if lf is None or y is None:
        return None
    span = lf.bot_y - lf.pd_y
    if span <= 10 or not (lf.pd_y - 0.3 * span <= y <= lf.bot_y + 0.3 * span):
        return None
    lp = lfs.get(k - 1)
    if lp is not None:
        wr = lf.width(lf.pd_y) / max(1e-6, lp.width(lp.pd_y))
        if abs(lf.pd_y - lp.pd_y) > QUAD_SMOOTH * span or not (0.85 <= wr <= 1.18):
            return None
    return lf


def r_geo(lf, y):
    return 0.5 * BALL_UNITS * lf.width(y) / 38.0


def roi_mask(lf, shape):
    H, W = shape[:2]
    span = lf.bot_y - lf.pd_y
    top = max(0.0, lf.pd_y - ROI_UP * span)
    pts = []
    for y in (top, float(H - 1)):
        pts.append((lf.xl(y) - ROI_MARGIN * lf.width(y), y))
    for y in (float(H - 1), top):
        pts.append((lf.xr(y) + ROI_MARGIN * lf.width(y), y))
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [np.array(pts, np.int32)], 255)
    return m


# ---------------------------------------------------------------- residual candidates
def far_row(lf):
    """Topmost image row (exclusive) of the near band: rows above it have r_geo <= FAR_R."""
    lo, hi = 0, int(lf.bot_y)
    for _ in range(40):
        mid = (lo + hi) // 2
        if r_geo(lf, mid) <= FAR_R:
            lo = mid + 1
        else:
            hi = mid
    return max(0, lo)


def far_candidates(res, roi, lf, y_far, k):
    """Peaks of (mean residual in a disc of r_geo) - (mean in the annulus r_geo..1.7 r_geo) over the far band, radius
    picked per row from FAR_RADII nearest r_geo(row). Returns the FAR_TOP strongest as candidate dicts (r = r_geo)."""
    if y_far < 8:
        return []
    band = res[:y_far].astype(np.float32)
    band[roi[:y_far] == 0] = 0
    rows = np.arange(y_far, dtype=np.float32)
    rg_rows = np.array([r_geo(lf, float(y)) for y in rows], np.float32)
    resp = np.full(band.shape, -1.0, np.float32)
    inner_sel = np.zeros(band.shape, np.float32)
    for r in FAR_RADII:
        ri, ro = r, int(round(1.7 * r)) + 1
        inner = cv2.filter2D(band, -1, LGB.disc_kernel(ri))
        outer = cv2.filter2D(band, -1, LGB.disc_kernel(ro))
        ai, ao = math.pi * ri * ri, math.pi * ro * ro
        ann = (outer * ao - inner * ai) / max(1.0, ao - ai)
        sel = np.abs(rg_rows - r) == np.min(np.abs(rg_rows[:, None] - np.array(FAR_RADII, np.float32)[None, :]), axis=1)
        rr = inner - ann
        resp[sel] = rr[sel]
        inner_sel[sel] = inner[sel]
    resp[roi[:y_far] == 0] = -1.0
    dil = cv2.dilate(resp, np.ones((9, 9), np.uint8))
    peaks = np.argwhere((resp >= dil) & (resp >= FAR_RESP_MIN) & (inner_sel >= FAR_INNER_MIN))
    out = []
    for y, x in peaks:
        rg = float(rg_rows[y])
        if rg <= 0:
            continue
        out.append({'k': k, 'x': float(x), 'y': float(y), 'r': rg, 'rg': rg, 'area': 0, 'res': float(resp[y, x]),
                    'inner': float(inner_sel[y, x]), 'fill': 1.0, 'asp': 1.0, 'board': lf.board(float(x), float(y)),
                    'z': lf.depth(float(y)), 'far': True})
    out.sort(key=lambda c: -c['res'])
    return out[:FAR_TOP]


def candidates(motion, frames, k, lf, thr=RES_THR):
    res, valid = residual(motion, frames, k)
    if res is None:
        return [], None
    roi = roi_mask(lf, res.shape)
    y_far = far_row(lf)
    m = ((res > thr) & (roi > 0)).astype(np.uint8)
    m[:y_far] = 0
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    out = far_candidates(res, roi, lf, y_far, k)
    n, lab, st, cen = cv2.connectedComponentsWithStats(m, 8)
    for i in range(1, n):
        a = int(st[i, cv2.CC_STAT_AREA])
        if a < MIN_AREA:
            continue
        w, h = int(st[i, cv2.CC_STAT_WIDTH]), int(st[i, cv2.CC_STAT_HEIGHT])
        asp = max(w, h) / max(1, min(w, h))
        fill = a / float(w * h)
        if asp > ASPECT_MAX or fill < FILL_MIN:
            continue
        x, y = float(cen[i][0]), float(cen[i][1])
        rg = r_geo(lf, y)
        r_ext = 0.5 * max(w, h)
        if rg <= 0 or not (R_LO * rg <= r_ext <= R_HI * rg):
            continue
        y0, x0 = int(st[i, cv2.CC_STAT_TOP]), int(st[i, cv2.CC_STAT_LEFT])
        patch = res[y0:y0 + h, x0:x0 + w]
        comp = lab[y0:y0 + h, x0:x0 + w] == i
        out.append({'k': k, 'x': x, 'y': y, 'r': r_ext, 'rg': rg, 'area': a, 'res': float(patch[comp].mean()),
                    'fill': fill, 'asp': asp, 'board': lf.board(x, y), 'z': lf.depth(y)})
    out.sort(key=lambda c: -c['res'] * c['fill'])
    return out, res


def image_jump_ok(c, pred, rp, gap):
    return math.hypot(c['x'] - pred[0], c['y'] - pred[1]) <= (4 * rp + 40) * min(gap, JUMP_GAP_CAP)


def find_seed(cands_by_k, k_rel, k_end):
    """First k >= release+3 whose best blob has a successor at k+1 and k+2 inside the lateral, radius and jump gates."""
    for k in range(k_rel + SEED_FROM, k_end - 2):
        for b0 in cands_by_k.get(k, [])[:4]:
            b1s = [c for c in cands_by_k.get(k + 1, []) if abs(c['board'] - b0['board']) <= LAT_BOARDS
                   and 0.6 <= c['r'] / b0['r'] <= 1.6 and image_jump_ok(c, (b0['x'], b0['y']), b0['rg'], 1)
                   and c['y'] <= b0['y'] + 0.5 * b0['rg']]
            for b1 in b1s[:3]:
                px, py = 2 * b1['x'] - b0['x'], 2 * b1['y'] - b0['y']
                b2s = [c for c in cands_by_k.get(k + 2, []) if abs(c['board'] - b1['board']) <= LAT_BOARDS
                       and 0.6 <= c['r'] / b1['r'] <= 1.6 and image_jump_ok(c, (px, py), b1['rg'], 1)
                       and c['y'] <= b1['y'] + 0.5 * b1['rg']]
                if b2s:
                    return k, b0, b1, b2s[0]
    return None, None, None, None


def predict(acc, motion, lfs, k, forward=True):
    """(pred_xy, pred_board, src). Lane-coordinate line over the last 4 real points when their lane fits are
    trusted, else constant velocity through the homography chain."""
    real = [a for a in acc if a['src'] != 'coast']
    if not real:
        return None, None, None
    lf = trusted_lf(lfs, k, real[-1]['y'])
    if len(real) >= 3 and lf is not None:
        lp = []
        for a in real[-4:]:
            q = trusted_lf(lfs, a['k'], a['y'])
            if q is None:
                lp = []
                break
            lp.append((a['k'], q.board(a['x'], a['y']), q.depth(a['y'])))
        if len(lp) >= 3:
            ks = np.array([v[0] for v in lp], float)
            A = np.c_[ks - ks[-1], np.ones_like(ks)]
            (vb, b1), *_ = np.linalg.lstsq(A, np.array([v[1] for v in lp]), rcond=None)
            (vz, z1), *_ = np.linalg.lstsq(A, np.array([v[2] for v in lp]), rcond=None)
            dt = k - ks[-1]
            pb, pz = b1 + vb * dt, z1 + vz * dt
            if 0.5 < pz < 75.0:
                u = 1.0 - (pb - 1.0) / 38.0
                return lf.to_image(u, pz), float(pb), 'lane'
    if len(real) >= 2:
        a0, a1 = real[-2], real[-1]
        ax, ay = LGB.apply_h(LGB.compose(motion, a1['k'], k), a1['x'], a1['y'])
        bx, by = LGB.apply_h(LGB.compose(motion, a0['k'], k), a0['x'], a0['y'])
        dt = (k - a1['k']) / (a1['k'] - a0['k'])
        return (ax + (ax - bx) * dt, ay + (ay - by) * dt), None, 'homography'
    a1 = real[-1]
    return LGB.apply_h(LGB.compose(motion, a1['k'], k), a1['x'], a1['y']), None, 'homography'


def walk(acc, cands_by_k, motion, lfs, ks, meta, allow_grow=False):
    """Extend acc over frames ks (in order) with gated residual candidates, coasting <= COAST_MAX. Mutates acc."""
    coast = 0
    for k in ks:
        pred, pb, psrc = predict(acc, motion, lfs, k)
        if pred is None:
            break
        real = [a for a in acc if a['src'] != 'coast']
        gap = abs(k - real[-1]['k'])
        lf = trusted_lf(lfs, k, pred[1])
        rp = r_geo(lf, pred[1]) if lf is not None else real[-1]['r']
        chosen = None
        for c in cands_by_k.get(k, []):
            if lf is not None and not (R_LO * rp <= c['r'] <= R_HI * rp):
                meta['gates']['radius'] += 1
                continue
            if not image_jump_ok(c, pred, rp, gap):
                meta['gates']['jump'] += 1
                continue
            if pb is not None and abs(c['board'] - pb) > LAT_BOARDS * gap:
                meta['gates']['lateral'] += 1
                continue
            chosen = c
            break
        if chosen is None:
            if coast < COAST_MAX:
                coast += 1
                meta['coasted'] += 1
                acc.append({'k': k, 'x': pred[0], 'y': pred[1], 'r': rp, 'conf': 0.2, 'src': 'coast'})
                continue
            break
        coast = 0
        acc.append({'k': k, 'x': chosen['x'], 'y': chosen['y'], 'r': rp if lf is not None else chosen['r'],
                    'conf': 0.8, 'src': 'residual', 'res': round(chosen['res'], 1)})
    while acc and acc[-1]['src'] == 'coast':
        acc.pop()


def merge_sam(chain, sam, motion, lfs, k_lo, k_hi, meta):
    """Per frame: a real chain point wins; SAM fills a frame without one when it passes the radius band (where
    r_geo <= R_FAR) and the lateral gate against the chain's neighbours; else coast (<= 3) from the chain prediction."""
    by_k = {a['k']: a for a in chain if a['src'] != 'coast'}
    out, coast = [], 0
    for k in range(k_lo, k_hi + 1):
        if k in by_k:
            out.append(by_k[k])
            coast = 0
            continue
        sp = sam.get(k)
        if sp is not None:
            x, y, r = sp
            lf = trusted_lf(lfs, k, y)
            rg = r_geo(lf, y) if lf is not None else None
            ok = True
            if rg is not None and rg <= R_FAR and not (SAM_R_LO * rg <= r <= SAM_R_HI * rg):
                ok = False
                meta['gates']['sam_radius'] += 1
            if ok and lf is not None:
                nb = [a for a in out[-4:] if a['src'] != 'coast']
                if nb:
                    q = trusted_lf(lfs, nb[-1]['k'], nb[-1]['y'])
                    if q is not None and abs(lf.board(x, y) - q.board(nb[-1]['x'], nb[-1]['y'])) > LAT_BOARDS * (k - nb[-1]['k']):
                        ok = False
                        meta['gates']['sam_lateral'] += 1
            if ok:
                out.append({'k': k, 'x': x, 'y': y, 'r': rg if rg is not None else r, 'conf': 0.6, 'src': 'sam',
                            'sam_r': round(r, 1)})
                meta['sam_used'] += 1
                coast = 0
                continue
        pred, pb, psrc = predict(out, motion, lfs, k)
        if pred is not None and coast < COAST_MAX:
            coast += 1
            lf = trusted_lf(lfs, k, pred[1])
            rp = r_geo(lf, pred[1]) if lf is not None else out[-1]['r']
            out.append({'k': k, 'x': pred[0], 'y': pred[1], 'r': rp, 'conf': 0.2, 'src': 'coast'})
            meta['coasted_merge'] += 1
        elif pred is not None:
            break
    while out and out[-1]['src'] == 'coast':
        out.pop()
    return out


# ---------------------------------------------------------------- pictures
def picture(frames, off, tr, pr, rel, out_path):
    td = {p['f']: p for p in tr.get('lane_top_down') or []}
    pts = {p['f']: p for p in tr['frames']}
    tiles, info = [], []
    for ft in (20.0, 40.0, 55.0):
        cand = [f for f in td if f in pts and rel <= f <= pr]
        if not cand:
            continue
        f = min(cand, key=lambda g: abs(td[g]['ft_cv'] - ft))
        p = pts[f]
        k = f - off
        if not 0 <= k < len(frames):
            continue
        im = frames[k]
        side = int(max(10 * (p['r'] or 6), 140))
        x0, y0 = int(max(0, p['x'] - side / 2)), int(max(0, p['y'] - side / 2))
        crop = im[y0:y0 + side, x0:x0 + side].copy()
        sc = 320.0 / max(1, crop.shape[1])
        crop = cv2.resize(crop, None, fx=sc, fy=sc, interpolation=cv2.INTER_CUBIC)
        cv2.circle(crop, (int((p['x'] - x0) * sc), int((p['y'] - y0) * sc)), max(2, int((p['r'] or 3) * sc)), (0, 140, 255), 1)
        cv2.drawMarker(crop, (int((p['x'] - x0) * sc), int((p['y'] - y0) * sc)), (0, 255, 255), cv2.MARKER_CROSS, 8, 1)
        t = f"f{f} {td[f]['ft_cv']:.0f}ft r{p['r']:.0f} {p['src']} b{td[f]['board']:.1f}"
        cv2.putText(crop, t, (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 3)
        cv2.putText(crop, t, (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
        tiles.append(crop)
        info.append({'target_ft': ft, 'f': f, 'ft_cv': td[f]['ft_cv'], 'src': p['src'], 'r': p['r']})
    if tiles:
        h = max(t.shape[0] for t in tiles)
        tiles = [cv2.copyMakeBorder(t, 0, h - t.shape[0], 0, 4, cv2.BORDER_CONSTANT, value=(30, 30, 30)) for t in tiles]
        cv2.imwrite(out_path, np.hstack(tiles), [cv2.IMWRITE_JPEG_QUALITY, 88])
    return info


def chained_polyline(frames, motion, tr, off, k_show):
    pts = []
    for p in tr['frames']:
        k = p['f'] - off
        if not 0 <= k < len(frames) or p['src'] == 'coast':
            continue
        lo, hi = (k + 1, k_show) if k < k_show else (k_show + 1, k)
        if any(motion.H[u] is None for u in range(lo, hi + 1)):
            continue
        pts.append(tuple(int(v) for v in LGB.apply_h(LGB.compose(motion, k, k_show), p['x'], p['y'])))
    return pts


# ---------------------------------------------------------------- proxies
def proxies(out, rel, pr):
    real = {p['f'] for p in out['frames'] if p['src'] != 'coast'}
    lo, hi = rel + 5, pr
    n = max(0, hi - lo + 1)
    det = sum(1 for f in range(lo, hi + 1) if f in real) / n if n else 0.0
    boards = {int(k): v for k, v in (out.get('boards') or {}).items()}
    fs = sorted(f for f in boards if rel <= f <= pr)
    med = TV.rolling_med(fs, [boards[f] for f in fs], 5) if len(fs) >= 2 else []
    jumps = [abs(b - a) for a, b in zip(med, med[1:])]
    src = out['events'].get('pin_row_source') or ''
    return {'detection_rate': round(det, 3), 'detection_window': [lo, hi], 'real_in_window': int(det * n) if n else 0,
            'max_board_jump': round(max(jumps), 2) if jumps else None, 'board_series_n': len(fs),
            'board_series_gaps': sum(1 for a, b in zip(fs, fs[1:]) if b - a > 1),
            'pin_row_detected': not src.startswith('fallback'), 'pin_row_source': src}


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stem')
    ap.add_argument('--device', default='mps')
    ap.add_argument('--no-sam', action='store_true')
    ap.add_argument('--any-stem', action='store_true', help='lift the dev-stem guard (integration only)')
    ap.add_argument('--tag', default='')
    ap.add_argument('--thr', type=int, default=RES_THR)
    a = ap.parse_args()
    log = lambda *x, **k: print(*x, **k, flush=True)  # noqa: E731
    cut = load_cut(a.stem)
    stem = cut['stem']
    short = stem.split('_')[1]
    if short not in DEV and not a.any_stem:
        log(f'REFUSED {stem}: not a dev stem (dev = {sorted(DEV)}); pass --any-stem to run anyway')
        sys.exit(2)
    for d in ('tracks', 'overlays', os.path.join('work', stem)):
        os.makedirs(os.path.join(X, d), exist_ok=True)
    if not cut.get('cut_path') or not cut.get('verified'):
        empty = {'stem': stem, 'method': 'motion-only', 'stage': 'ball', 'stages': {'ball': 'motion-only', 'lane': 'none', 'path': 'none'},
                 'frames': [], 'lane': {}, 'boards': {}, 'boards_raw': {}, 'final_board': None, 'lane_top_down': [],
                 'release_frame': cut.get('release_frame'), 'pin_hit_frame': cut.get('pin_hit_frame'), 'pin_row_frame_est': None,
                 'events': {}, 'fallback': [], 'meta': {'note': f"no cut: {cut.get('notes') or 'no throw'}", 'wall_s': 0.0},
                 'proxy': {'detection_rate': 0.0, 'max_board_jump': None, 'pin_row_detected': False, 'pin_row_source': 'none: no cut'}}
        tp = os.path.join(X, 'tracks', f'{stem}{a.tag}.json')
        json.dump(empty, open(tp, 'w'), indent=1)
        log(f'MOTION_ONLY {stem}: no cut ({empty["meta"]["note"]}); empty track -> {tp}')
        return
    t0 = time.time()
    rel, pin, off = cut['release_frame'], cut['pin_hit_frame'], cut['cut_start']
    frames = read_frames(cut['cut_path'])
    assert len(frames) == cut['nb_frames'], (len(frames), cut['nb_frames'])
    k_rel, k_pin, k_end = rel - off, pin - off, len(frames) - 1
    timing = {}
    t = time.time()
    motion = Motion(frames)
    timing['orb_s'] = round(time.time() - t, 1)
    t = time.time()
    lfs = lane_prepass(frames, max(0, k_rel))
    timing['lane_prepass_s'] = round(time.time() - t, 1)
    log(f'{stem}: {len(frames)} frames, release k{k_rel}, cut pin k{k_pin}; ORB failed pairs '
        f'{sum(1 for h in motion.H[1:] if h is None)}, lane fits {len(lfs)}/{len(frames) - k_rel}')
    meta = {'gates': {'radius': 0, 'jump': 0, 'lateral': 0, 'sam_radius': 0, 'sam_lateral': 0}, 'coasted': 0,
            'coasted_merge': 0, 'sam_used': 0}
    t = time.time()
    cands_by_k, n_cands = {}, 0
    for k in range(k_rel, k_end + 1):
        lf = lfs.get(k)
        if lf is None:
            continue
        cs, _ = candidates(motion, frames, k, lf, a.thr)
        cands_by_k[k] = cs
        n_cands += len(cs)
    timing['residual_s'] = round(time.time() - t, 1)
    k0, b0, b1, b2 = find_seed(cands_by_k, k_rel, k_end)
    if k0 is None:
        log('no chained residual seed; writing an empty track')
        chain, sam_pts, sam_meta = [], {}, {'why': 'no seed'}
    else:
        log(f'  [seed] k{k0} (f{k0 + off}) at ({b0["x"]:.0f},{b0["y"]:.0f}) r_ext {b0["r"]:.1f} r_geo {b0["rg"]:.1f} '
            f'res {b0["res"]:.0f} board {b0["board"]:.1f}')
        chain = [{'k': c['k'], 'x': c['x'], 'y': c['y'], 'r': c['rg'], 'conf': 0.8, 'src': 'residual', 'res': round(c['res'], 1)}
                 for c in (b0, b1, b2)]
        walk(chain, cands_by_k, motion, lfs, range(k0 + 3, k_end + 1), meta)
        back = [dict(chain[2]), dict(chain[1]), dict(chain[0])]
        walk(back, cands_by_k, motion, lfs, range(k0 - 1, k_rel - 1, -1), meta)
        chain = sorted(back[3:] + chain, key=lambda c: c['k'])
        timing['chain_s'] = round(time.time() - t - timing['residual_s'], 1)
        sam_pts, sam_meta = {}, {'skipped': a.no_sam}
        if not a.no_sam:
            t = time.time()
            rr = 1.25 * max(b0['rg'], 6.0)
            box = [b0['x'] - rr, b0['y'] - rr, b0['x'] + rr, b0['y'] + rr]
            wd = os.path.join(X, 'work', stem)
            k_sam_end = min(k_end, k_pin + SAM_TAIL)
            fwd, passes = sam_track(frames, k0, box, device=a.device, work_dir=wd, k_end=k_sam_end, log=log)
            bwd = sam_track_back(frames, k0, box, k_rel, device=a.device, work_dir=wd, log=log)
            sam_pts = {**bwd, **fwd}
            sam_meta = {'prompt_k': k0, 'prompt_f': k0 + off, 'box': [round(v, 1) for v in box], 'forward': len(fwd),
                        'backward': len(bwd), 'passes': passes}
            timing['sam_s'] = round(time.time() - t, 1)
    real_chain = [c for c in chain if c['src'] != 'coast']
    if real_chain:
        k_lo = min(min(real_chain, key=lambda c: c['k'])['k'], min(sam_pts) if sam_pts else 10 ** 9, k_rel)
        k_lo = max(k_rel, k_lo)
        merged = merge_sam(chain, sam_pts, motion, lfs, k_lo, k_end, meta)
    else:
        merged = []
    balls = [{'f': p['k'] + off, 'x': round(p['x'], 1), 'y': round(p['y'], 1), 'r': round(p['r'], 1), 'conf': p['conf'],
              'src': p['src']} for p in merged]
    srcs = {}
    for p in balls:
        srcs[p['src']] = srcs.get(p['src'], 0) + 1
    log(f'  [ball] {len(balls)} points {srcs}; gates {meta["gates"]}; candidates {n_cands}')

    # ---- lane stage (loop-2 composition edge lane, ball points injected), then the track_v2 tail
    fallback, lane_err = [], None
    lane_tr = None
    if balls:
        try:
            CM.ball_stage = lambda s, cut_, how, lg: ([dict(p) for p in balls], 'motion-only ball stage (injected)')
            args = SimpleNamespace(device=a.device, lane='edge', refine=False, smooth=3, ball='file',
                                   out_dir=os.path.join(WORK, 'comp'))
            lane_tr = CM.run(stem, args, log)
            roll = [p for p in balls if rel <= p['f'] <= pin]
            nb = sum(1 for p in roll if str(p['f']) in (lane_tr.get('boards') or {}))
            if not roll or nb < TV.LANE_MIN_FRAC * len(roll) or lane_tr.get('final_board') is None:
                lane_err, lane_tr = f'boards on {nb}/{len(roll)} roll frames, final_board {lane_tr.get("final_board")}', None
        except Exception as e:  # noqa: BLE001
            lane_err, lane_tr = f'{type(e).__name__}: {e}', None
    if lane_tr is None:
        fallback.append('lane')
        quads = {str(k + off): lfs[k].quad() for k in lfs}
        boards = {}
        for p in balls:
            q = quads.get(str(p['f']))
            if q:
                b = LG.lane_point(q, p['x'], p['y'])[0]
                if b is not None:
                    boards[str(p['f'])] = round(b, 2)
        tr = {'frames': balls, 'lane': quads, 'boards': boards, 'boards_raw': dict(boards), 'boards_contact': {},
              'final_board': None, 'lane_top_down': [], 'lane_top_down_model': {'a': 60.0, 'b': 0.0}}
        lane_name = 'prepass lane-first quads (fallback)'
        lane_meta = {'lane_variant': 'prepass-edge', 'fallback_used': True}
        rejected, diag = {}, None
        log(f'[lane] composition edge lane failed ({lane_err}); prepass quads')
    else:
        tr = {k: lane_tr.get(k) for k in ('frames', 'lane', 'boards', 'boards_raw', 'boards_contact', 'final_board',
                                          'lane_top_down', 'lane_top_down_model')}
        lane_name = 'composition/edge+smooth3'
        tr['final_board_pre_fixpass'] = tr.get('final_board')
        rejected, diag = TV.clean_series(tr, rel, pin)
        lane_meta = {k: lane_tr['meta'].get(k) for k in ('lane_variant', 'lane_sources', 'edge_fit_failures',
                                                           'edge_fail_reasons', 'fallback_used', 'smooth', 'lane_s', 'board_row')}
        log(f'[series] rejected {sorted(rejected)}; final_board {tr["final_board_pre_fixpass"]} -> {tr["final_board"]}')
    t = time.time()
    pr_info = TV.pin_row_estimate(tr, {}, rel, pin, frames, off)
    geo = pr_info['pin_row_source'].startswith('detected')
    pr_info['pin_row_frame_geometric'] = pr_info['pin_row_frame_est'] if geo else None
    pm, pm_info = TV.pin_motion(tr, frames, off, pin, motion)
    tr['pin_motion'] = pm_info
    pr_info['pin_motion_frame'] = pm
    if pm is not None:
        pr_info['pin_row_frame_est'] = pm - TV.PM_LEAD
        pr_info['pin_row_source'] = f'pin motion: first camera-compensated rack motion f{pm} - {TV.PM_LEAD}'
    elif geo:
        pr_info['pin_row_source'] = 'geometric: ' + pr_info['pin_row_source']
    pr_info['pin_row_minus_cut'] = pr_info['pin_row_frame_est'] - pin
    pr = pr_info['pin_row_frame_est']
    tr['deck_decoy_from'], tr['deck_motion_px'] = TV.deck_decoy(tr, frames, off, pr, motion)
    tr['cut_last_frame'] = off + len(frames) - 1
    TV.add_depth(tr, rel, pin, pr)
    events = TV.compute_events(tr, rel, pr)
    events.update({k: v for k, v in pr_info.items() if k != 'pin_row_frame_est'})
    timing['events_s'] = round(time.time() - t, 1)
    log(f'[pin row] {pr_info["pin_row_source"]} f{pr} (cut {pin})')
    log(f'[events] entry {events["entry_board"]} exit f{events["exit_frame"]} {events["exit_board"]} deck {events["deck_frames"]} '
        f'break {events["breakpoint_board"]} @ {events["breakpoint_ft"]} ft')
    wall = round(time.time() - t0, 1)
    timing['wall_s'] = wall
    out = {'stem': stem, 'method': 'motion-only', 'stage': 'ball',
           'stages': {'ball': 'motion-only' + (' (residual only, --no-sam)' if a.no_sam else ' (residual chain + SAM 2 fill)'),
                      'lane': lane_name, 'path': 'none'},
           **tr,
           'release_frame': rel, 'pin_hit_frame': pin, 'pin_row_frame_est': pr,
           'events': events,
           'final_board_rule': 'Theil-Sen over boards in pin_hit-10..pin_hit evaluated at pin_hit (composition fit_path), on the series after clean_series'
           if not fallback else 'none (lane fallback)',
           'path_fit_diag': diag,
           'fallback': fallback, 'fallback_reasons': {'ball': None, 'lane': lane_err},
           'meta': {'device': a.device, 'cut_start': off, **lane_meta,
                    'ball_meta': {**meta, 'sources': srcs, 'candidates': n_cands, 'seed': None if k0 is None else
                                  {'k': k0, 'f': k0 + off, 'x': round(b0['x'], 1), 'y': round(b0['y'], 1), 'r_ext': round(b0['r'], 1),
                                   'r_geo': round(b0['rg'], 1), 'res': round(b0['res'], 1)},
                                  'sam': sam_meta, 'orb_failed_pairs': sum(1 for h in motion.H[1:] if h is None),
                                  'lane_prepass_fits': len(lfs),
                                  'params': {'R_LO': R_LO, 'R_HI': R_HI, 'SAM_R_LO': SAM_R_LO, 'SAM_R_HI': SAM_R_HI, 'R_FAR': R_FAR,
                                             'LAT_BOARDS': LAT_BOARDS, 'RES_THR': a.thr, 'ASPECT_MAX': ASPECT_MAX,
                                             'FILL_MIN': FILL_MIN, 'FAR_R': FAR_R, 'FAR_RADII': FAR_RADII, 'FAR_RESP_MIN': FAR_RESP_MIN, 'FAR_INNER_MIN': FAR_INNER_MIN, 'COAST_MAX': COAST_MAX, 'JUMP_GAP_CAP': JUMP_GAP_CAP, 'SEED_FROM': SEED_FROM}},
                    'timing': timing, 'wall_s': wall, 'wall_note': 'whole process: ORB, lane pre-pass, residual, chain, SAM, lane stage, events, overlays',
                    'stages': {'ball': 'motion-only', 'lane': lane_name, 'path': 'none'}}}
    out['proxy'] = proxies(out, rel, pr)
    tp = os.path.join(X, 'tracks', f'{stem}{a.tag}.json')
    json.dump(out, open(tp, 'w'), indent=1)
    # ---- overlay: pin-row-4 frame with the homography-chained track (white) under the track_v2 drawing
    k_show = max(0, min(len(frames) - 1, pr - 4 - off))
    fr2 = list(frames)
    im = frames[k_show].copy()
    poly = chained_polyline(frames, motion, out, off, k_show)
    if len(poly) > 1:
        cv2.polylines(im, [np.array(poly, np.int32)], False, (255, 255, 255), 3)
    fr2[k_show] = im
    quads = {int(k): v for k, v in (out.get('lane') or {}).items()}
    hdr = [f"ball motion-only{' (no SAM)' if a.no_sam else ''} {srcs} | lane {lane_name} | fallback {fallback or '-'} | white = track chained through the homographies",
           f"series rejected {sorted(int(k) for k in out.get('series_rejected') or {}) or '-'} | pin row {pr_info['pin_row_source'][:40]} | wall {wall}s"]
    op = os.path.join(X, 'overlays', f'final__{stem}{a.tag}.jpg')
    try:
        out['meta']['overlay'] = TV.draw_overlay_v2(fr2, dict(cut, pin_hit_frame=pr), dict(out, final_board=events['entry_board']),
                                                    op, quads, hdr)
    except Exception as e:  # noqa: BLE001
        out['meta']['overlay'] = {'error': f'{type(e).__name__}: {e}'}
        log(f'[overlay] failed: {e}')
    out['meta']['picture'] = picture(frames, off, out, pr, rel, os.path.join(X, 'overlays', f'picture__{stem}{a.tag}.jpg'))
    out['meta']['timing']['wall_s'] = round(time.time() - t0, 1)
    json.dump(out, open(tp, 'w'), indent=1)
    log(f'MOTION_ONLY {stem}: points={len(out["frames"])} {srcs} boards={len(out.get("boards") or {})} entry={events["entry_board"]} '
        f'pin_row={pr} (cut {pin}) proxy={out["proxy"]} timing={out["meta"]["timing"]} -> {tp}')


if __name__ == '__main__':
    main()
