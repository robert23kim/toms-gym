"""far-end-stacking (loop 2, stage: ball): re-localise the tiny far-end ball by motion-compensated temporal stacking.

usage: run.py <stem> [--device mps|cpu] [--n 5] [--win 24] [--seed 10]
Reads  L1/work/cuts/cuts.json + the cut, the loop-1 sam2-video track L1/results/tracks/<stem>.json.
Writes tracks/<stem>.json (tracks format, SOURCE frames, stage "ball"), overlays/final__<stem>.jpg, work/<stem>_cands.json.

Window = pin_hit-WIN .. pin_hit (+2 for continuity). Seed = the loop-1 track's last SEED frames before the window
(position, camera-compensated velocity, purple-component radius). Per frame energy E = blur(purple hue window) x
blackhat(grey, ellipse 2.5 r) x |three-frame camera-compensated residual| on the full frame; candidates = top-K local
maxima of E near the carried prediction. Stacking: a candidate's unary is the mean of E along its constant-velocity
path carried into the N-1 neighbouring frames by the chained ORB homographies (N=1 is the no-stacking control).
Linking: first-order DP over the candidates with a velocity prior from each state's back-pointer. Final centre:
the purple component in frame t re-centred on the pick (stacked peak when the component is occluded).
Boards for the replaced frames come from the loop-1 lane quads (lane_geom.lane_point); final_board stays loop-1's.
--device is accepted for the harness and unused: no torch here (cv2/numpy only).
"""
import argparse
import json
import math
import os
import sys
import time

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
L1 = '/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking'
sys.path.insert(0, L1)
sys.path.insert(0, os.path.join(L1, 'experiments', 'cam-diff'))
from camdiff import Motion, residual  # noqa: E402
from lane_geom import lane_point, depth_ratio, fit_ft_model, image_point  # noqa: E402

HUE_LO, HUE_HI, SAT_MIN = 112, 170, 30
METHOD = 'far-end-stacking'


def load_cut(stem):
    cuts = json.load(open(f'{L1}/work/cuts/cuts.json'))
    cut = next(c for c in cuts if c['stem'] == stem)
    cap = cv2.VideoCapture(cut['cut_path'])
    frames = []
    while True:
        ok, im = cap.read()
        if not ok:
            break
        frames.append(im)
    cap.release()
    assert len(frames) == cut['nb_frames'], (len(frames), cut['nb_frames'])
    return cut, frames


def purple_mask(hsv, sat_min=SAT_MIN):
    h, s = hsv[..., 0], hsv[..., 1]
    return ((h >= HUE_LO) & (h <= HUE_HI) & (s >= sat_min)).astype(np.uint8)


def purple_component(pm, x, y, r, win=None):
    """Connected purple component nearest (x, y) within r: (cx, cy, r_eq, area, w, h) or None."""
    H, W = pm.shape
    win = win or int(4 * r + 10)
    xi, yi = int(round(x)), int(round(y))
    x1, x2, y1, y2 = max(0, xi - win), min(W, xi + win + 1), max(0, yi - win), min(H, yi + win + 1)
    sub = pm[y1:y2, x1:x2]
    if sub.size == 0:
        return None
    sub = cv2.morphologyEx(sub, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    n, lab, st, cen = cv2.connectedComponentsWithStats(sub, 8)
    best, bd = None, None
    for i in range(1, n):
        a = st[i, cv2.CC_STAT_AREA]
        if a < 4:
            continue
        cx, cy = cen[i][0] + x1, cen[i][1] + y1
        d = math.hypot(cx - x, cy - y)
        if d <= max(r, 6.0) and (bd is None or d < bd):
            best, bd = i, d
    if best is None:
        return None
    a = float(st[best, cv2.CC_STAT_AREA])
    return (float(cen[best][0] + x1), float(cen[best][1] + y1), math.sqrt(a / math.pi), a,
            float(st[best, cv2.CC_STAT_WIDTH]), float(st[best, cv2.CC_STAT_HEIGHT]))


class Chain:
    """Composed homographies between frames of the cut (full-res), None when a link is missing."""

    def __init__(self, motion):
        self.m = motion
        self.cache = {}

    def H(self, a, b):
        """Homography taking frame a coordinates onto frame b."""
        if a == b:
            return np.eye(3)
        key = (a, b)
        if key in self.cache:
            return self.cache[key]
        M = np.eye(3)
        if b > a:
            for u in range(a + 1, b + 1):
                if self.m.H[u] is None:
                    M = None
                    break
                M = self.m.H[u] @ M
        else:
            for u in range(a, b, -1):
                if self.m.H[u] is None:
                    M = None
                    break
                M = np.linalg.inv(self.m.H[u]) @ M
        self.cache[key] = M
        return M

    def pt(self, a, b, x, y):
        M = self.H(a, b)
        if M is None:
            return None
        p = M @ np.array([x, y, 1.0])
        return float(p[0] / p[2]), float(p[1] / p[2])


NO_PURPLE = False


def energy_map(motion, frames, hsv, k, r):
    """Full-frame float32 energy: purple x blackhat x |residual|, each blurred by r/2."""
    res, _ = residual(motion, frames, k)
    g = motion.greys[k]
    sig = max(1.0, r / 3.0)
    ks = int(2.2 * r) | 1
    bh = cv2.morphologyEx(g, cv2.MORPH_BLACKHAT, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ks, ks))).astype(np.float32)
    bh = cv2.GaussianBlur(bh, (0, 0), sig)
    pm = cv2.GaussianBlur(purple_mask(hsv).astype(np.float32), (0, 0), sig)
    if res is None:
        rs = np.full(g.shape, 10.0, np.float32)       # unknown camera motion: residual uninformative, keep colour x shape
    else:
        rs = cv2.GaussianBlur(res.astype(np.float32), (0, 0), sig)
    return (bh * rs) if NO_PURPLE else (pm * bh * rs)


def local_maxima(E, x0, y0, gate, r, K):
    H, W = E.shape
    x1, x2, y1, y2 = int(max(0, x0 - gate)), int(min(W, x0 + gate + 1)), int(max(0, y0 - gate)), int(min(H, y0 + gate + 1))
    sub = E[y1:y2, x1:x2]
    if sub.size == 0 or sub.max() <= 0:
        return []
    ks = int(max(3, r)) | 1
    dil = cv2.dilate(sub, np.ones((ks, ks), np.uint8))
    ys, xs = np.where((sub >= dil) & (sub > 0.02 * sub.max()))
    vals = sub[ys, xs]
    order = np.argsort(-vals)[:K]
    return [(float(xs[i] + x1), float(ys[i] + y1), float(vals[i])) for i in order]


def sample(E, x, y):
    H, W = E.shape
    xi, yi = int(round(x)), int(round(y))
    if xi < 1 or yi < 1 or xi >= W - 1 or yi >= H - 1:
        return 0.0
    return float(E[yi - 1:yi + 2, xi - 1:xi + 2].max())


def carry_v(chain, a, b, x, y, vx, vy):
    """Velocity (vx, vy) at (x, y) in frame a expressed in frame b."""
    p = chain.pt(a, b, x, y)
    q = chain.pt(a, b, x + vx, y + vy)
    if p is None or q is None:
        return None
    return p, (q[0] - p[0], q[1] - p[1])


def stacked(E, emax, chain, k, x, y, vx, vy, n_side):
    """Sum of log(E/emax) along the constant-velocity path through (x, y, v) at frame k over k-n..k+n (track-before-
    detect log-likelihood; N=1 is the single-frame log ratio)."""
    eps = 1e-3
    vals = [math.log(sample(E[k], x, y) / emax[k] + eps)]
    used = 1
    for d in range(-n_side, n_side + 1):
        if d == 0 or (k + d) not in E:
            continue
        q = chain.pt(k, k + d, x + vx * d, y + vy * d)
        if q is None:
            continue
        vals.append(math.log(sample(E[k + d], q[0], q[1]) / emax[k + d] + eps))
        used += 1
    return float(np.sum(vals)), used


def link(E, emax, chain, ks, cands, seed, n_side, sigma=8.0, w_unary=1.0, pred_penalty=0.7):
    """DP over per-frame candidates. seed = (x, y, vx, vy) in frame ks[0]-1 coordinates."""
    states = []     # per frame: list of dicts {x, y, vx, vy, u, score, bp}
    x0, y0, vx0, vy0 = seed
    prev = [{'x': x0, 'y': y0, 'vx': vx0, 'vy': vy0, 'score': 0.0, 'bp': None, 'k': ks[0] - 1}]
    for k in ks:
        cur = []
        # unaries: per-candidate velocity from the best previous state
        pb = max(prev, key=lambda s: s['score'])
        cv = carry_v(chain, pb['k'], k, pb['x'], pb['y'], pb['vx'], pb['vy'])
        for i, (cx, cy, e) in enumerate(cands[k]):
            if cv is None:
                vx, vy = pb['vx'], pb['vy']
            else:
                vx, vy = cx - cv[0][0], cy - cv[0][1]
            u, used = stacked(E, emax, chain, k, cx, cy, vx, vy, n_side)
            if i == len(cands[k]) - 1:          # the carried prediction is a fallback for occluded frames, not a peak
                u -= pred_penalty * used
            cur.append({'x': cx, 'y': cy, 'u': u, 'e1': e, 'used': used, 'k': k})
        for s in cur:
            un = s['u']
            best, bsc, bv = None, None, None
            for j, p in enumerate(prev):
                cvp = carry_v(chain, p['k'], k, p['x'], p['y'], p['vx'], p['vy'])
                if cvp is None:
                    px, py, pvx, pvy = p['x'] + p['vx'], p['y'] + p['vy'], p['vx'], p['vy']
                else:
                    px, py = cvp[0][0] + cvp[1][0], cvp[0][1] + cvp[1][1]
                    pvx, pvy = cvp[1]
                d2 = (s['x'] - px) ** 2 + (s['y'] - py) ** 2
                sc = p['score'] + w_unary * un - d2 / (2 * sigma * sigma)
                if bsc is None or sc > bsc:
                    best, bsc = j, sc
                    base = (px - pvx, py - pvy)
                    bv = (0.7 * (s['x'] - base[0]) + 0.3 * pvx, 0.7 * (s['y'] - base[1]) + 0.3 * pvy)
            s['score'], s['bp'], s['un'] = bsc, best, un
            s['vx'], s['vy'] = bv
        states.append(cur)
        prev = cur
    # backtrack
    out = {}
    j = int(np.argmax([s['score'] for s in prev]))
    for i in range(len(ks) - 1, -1, -1):
        s = states[i][j]
        out[ks[i]] = s
        j = s['bp']
    return out


def add_top_down(tr):
    lanes = tr.get('lane') or {}
    rel, pin = tr.get('release_frame'), tr.get('pin_hit_frame')
    samples = []
    for p in tr['frames']:
        q = lanes.get(str(p['f']))
        if q and rel is not None and pin is not None and rel <= p['f'] <= pin:
            s = depth_ratio(q, p['y'])
            board = lane_point(q, p['x'], p['y'])[0]
            if s is not None and s <= 1.05 and board is not None and 0.5 <= board <= 39.5:
                samples.append((p['f'], s))
    model = fit_ft_model(samples, rel)
    out = []
    for p in tr['frames']:
        q = lanes.get(str(p['f']))
        if not q:
            continue
        board, ft = lane_point(q, p['x'], p['y'], model['a'], model['b'])
        if board is None or ft is None:
            continue
        on = bool(0.5 <= board <= 39.5 and 0.0 <= ft <= 60.5)
        zone = ('behind_foul' if ft < 0 else 'past_pins' if ft > 60.5 else 'gutter_r' if board < 0.5
                else 'gutter_l' if board > 39.5 else 'lane')
        out.append({'f': p['f'], 'board': round(board, 2), 'ft': round(ft, 2), 'on_lane': on, 'zone': zone,
                    'board_engine': tr.get('boards', {}).get(str(p['f']))})
    tr['lane_top_down'] = out
    tr['lane_top_down_model'] = model


def overlay(frames, cut, tr, chain, replaced, out_path):
    off = cut['cut_start']
    k = max(0, min(len(frames) - 1, cut['pin_hit_frame'] - 4 - off))
    im = frames[k].copy()
    f = off + k
    q = (tr.get('lane') or {}).get(str(f))
    if q:
        cv2.polylines(im, [np.array([q['fl_l'], q['pd_l'], q['pd_r'], q['fl_r']], np.int32)], True, (255, 255, 0), 3)
        if q.get('pin_y') is not None:
            xl, xr = int(lane_point(q, 0, q['pin_y'])[0] * 0), 0
            cv2.line(im, (int(q['pd_l'][0]) - 40, int(q['pin_y'])), (int(q['pd_r'][0]) + 40, int(q['pin_y'])), (255, 255, 0), 1)
    # whole track carried into this frame through the chained homographies
    comp = []
    for p in tr['frames']:
        pk = p['f'] - off
        if not 0 <= pk < len(frames):
            continue
        w = chain.pt(pk, k, p['x'], p['y'])
        if w is not None and abs(w[0]) < 3 * im.shape[1] and abs(w[1]) < 3 * im.shape[0]:
            comp.append((int(w[0]), int(w[1]), p['f'] in replaced, max(2, int(p['r']))))
    if len(comp) > 1:
        cv2.polylines(im, [np.array([(c[0], c[1]) for c in comp], np.int32)], False, (255, 255, 255), 2)
    for cx, cy, rep, r in comp:
        cv2.circle(im, (cx, cy), r, (255, 200, 0) if rep else (0, 140, 255), 1 if not rep else 2)
    # board read at the pin row: last replaced frame on the lane
    board_txt = '-'
    bs = tr.get('boards') or {}
    last = [fr for fr in sorted(replaced) if str(fr) in bs and fr <= cut['pin_hit_frame']]
    if last:
        board_txt = f"{bs[str(last[-1])]:.1f} @f{last[-1]}"
    meta = tr['meta']
    txt = [f"{METHOD} {tr['stem']} f{f} (pin_hit-4)",
           f"board at pin row {board_txt}   final_board(loop-1) {tr['final_board']}   N={meta['n_stack']}",
           "white=track in this frame's coords (chained H), cyan=replaced far-end, orange=loop-1 kept, yellow=loop-1 quad",
           f"replaced {len(replaced)} frames, median shift {meta['replaced_median_shift_px']} px, +{meta['wall_s']}s on loop-1"]
    for i, t in enumerate(txt):
        cv2.putText(im, t, (16, 50 + 44 * i), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 5)
        cv2.putText(im, t, (16, 50 + 44 * i), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    im = cv2.resize(im, (im.shape[1] // 2, im.shape[0] // 2))
    H = im.shape[0]
    W = 160
    strip = np.full((H, W, 3), (70, 160, 215), np.uint8)
    # top-down trace: on-lane points from release+5 on, dropping jumps > 6 boards or > 10 ft (loop-1 rule: the quad is
    # unreliable on the release frames)
    on = [p for p in tr.get('lane_top_down') or [] if p['zone'] in ('lane', 'gutter_r', 'gutter_l') and p['f'] >= cut['release_frame'] + 5]
    td, prev = [], None
    if on:
        medb = sorted(p['board'] for p in on)[len(on) // 2]
        for p in on:
            if prev is None and abs(p['board'] - medb) > 6:
                continue
            if prev is not None and (abs(p['board'] - prev['board']) > 6 or abs(p['ft'] - prev['ft']) > 10):
                continue
            td.append(p)
            prev = p
    for bd in (5, 10, 15, 20, 25, 30, 35):
        x = int(W * (39 - bd) / 38)
        cv2.line(strip, (x, 0), (x, H), (120, 190, 230), 1)
        cv2.putText(strip, str(bd), (x - 8, H - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (30, 30, 30), 1)
    if not td:
        cv2.putText(strip, 'no lane', (30, H // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.circle(strip, (int(W * 19 / 38), 6), 4, (255, 255, 255), -1)
    tp = [(int(W * (39 - min(max(p['board'], -0.5), 40.5)) / 38), int(H * (1 - p['ft'] / 60))) for p in td]
    if len(tp) > 1:
        cv2.polylines(strip, [np.array(tp, np.int32)], False, (150, 40, 150), 2)
    for p, (x, y) in zip(td, tp):
        if p['f'] in replaced:
            cv2.circle(strip, (x, y), 2, (255, 200, 0), -1)
    cv2.putText(strip, 'board', (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
    cv2.putText(strip, 'ft 60', (W - 44, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
    cv2.imwrite(out_path, np.hstack([im, strip]), [cv2.IMWRITE_JPEG_QUALITY, 85])


DISC = 1.3


def refine_centre(E_k, pm, s, r_prev, mode, sat=None):
    """Final centre for one frame. purple: purple pixels inside a 1.3 r disc, two mean-shift steps capped at r/2;
    energy: energy-weighted centroid inside 0.8 r of the pick. Returns (x, y, r, rule, purple_px)."""
    rr = DISC * max(r_prev, 5.0)
    x, y = s['x'], s['y']
    cnt = 0
    xi, yi, ri = int(round(x)), int(round(y)), int(math.ceil(rr))
    y1, y2, x1, x2 = max(0, yi - ri), min(pm.shape[0], yi + ri + 1), max(0, xi - ri), min(pm.shape[1], xi + ri + 1)
    sub = pm[y1:y2, x1:x2].astype(bool)
    yy, xx = np.mgrid[y1:y2, x1:x2]
    cnt = int((sub & ((xx - x) ** 2 + (yy - y) ** 2 <= rr * rr)).sum())
    if mode == 'purple':
        for _ in range(2):
            inside = sub & ((xx - x) ** 2 + (yy - y) ** 2 <= rr * rr)
            cnt = int(inside.sum())
            if cnt < 0.35 * math.pi * r_prev * r_prev:
                break
            if sat is not None:
                wgt = np.clip((sat[y1:y2, x1:x2].astype(np.float32) - 25.0) / 40.0, 0.0, 1.0) * inside
                nx, ny = float((xx * wgt).sum() / wgt.sum()), float((yy * wgt).sum() / wgt.sum())
            else:
                nx, ny = float(xx[inside].mean()), float(yy[inside].mean())
            d = math.hypot(nx - s['x'], ny - s['y'])
            cap = 0.5 * r_prev
            if d > cap:
                nx, ny = s['x'] + (nx - s['x']) * cap / d, s['y'] + (ny - s['y']) * cap / d
            x, y = nx, ny
        if cnt >= 0.35 * math.pi * r_prev * r_prev:
            return x, y, min(math.sqrt(cnt / math.pi), r_prev + 0.5), 'purple_disc', cnt
    # energy-weighted centroid inside 0.8 r of the pick
    ri = int(max(3, round(0.8 * r_prev)))
    xi, yi = int(round(s['x'])), int(round(s['y']))
    y1, y2, x1, x2 = max(0, yi - ri), min(E_k.shape[0], yi + ri + 1), max(0, xi - ri), min(E_k.shape[1], xi + ri + 1)
    sub = E_k[y1:y2, x1:x2]
    x, y = s['x'], s['y']
    if sub.size and sub.max() > 0:
        yy, xx = np.mgrid[y1:y2, x1:x2]
        w = (sub - 0.5 * sub.max()) * (((xx - xi) ** 2 + (yy - yi) ** 2) <= ri * ri)
        w[w < 0] = 0
        if w.sum() > 0:
            x, y = float((xx * w).sum() / w.sum()), float((yy * w).sum() / w.sum())
    r = min(math.sqrt(cnt / math.pi), r_prev + 0.5) if cnt >= 0.35 * math.pi * r_prev * r_prev else r_prev
    return x, y, r, 'energy_centroid', cnt


def solve(frames, hsv, motion, chain, ks, seed, kl, r_of_k, r_seed, args, n_list):
    """One pass: energy maps with per-frame r, candidates around the carried prediction, DP for each N, refinement
    on the chosen N. Returns dict(E, cands, pred_log, by_n, chosen, out_pts, rules)."""
    n = len(frames)
    E, emax = {}, {}
    for k in range(ks[0] - 3, ks[-1] + 4):
        if 0 < k < n - 1:
            E[k] = energy_map(motion, frames, hsv[k], k, r_of_k(k))
    cands, pred_log = {}, {}
    px, py, pvx, pvy = seed
    pk = kl
    gate = max(45.0, 6 * r_seed)
    for k in ks:
        cv = carry_v(chain, pk, k, px, py, pvx, pvy)
        if cv is None:
            qx, qy, qvx, qvy = px + pvx * (k - pk), py + pvy * (k - pk), pvx, pvy
        else:
            qx, qy = cv[0][0] + cv[1][0] * (k - pk), cv[0][1] + cv[1][1] * (k - pk)
            qvx, qvy = cv[1]
        pred_log[k] = (qx, qy)
        emax[k] = max(1e-6, float(E[k][int(max(0, qy - gate)):int(qy + gate + 1), int(max(0, qx - gate)):int(qx + gate + 1)].max()))
        cs = local_maxima(E[k], qx, qy, gate, r_of_k(k), args.k)
        cs.append((qx, qy, sample(E[k], qx, qy)))     # the prediction itself, for occluded frames
        cands[k] = cs
        strong = [c for c in cs[:-1] if c[2] >= 0.3 * cs[0][2]] if cs[:-1] else []
        if strong:
            bx, by, _ = min(strong, key=lambda c: math.hypot(c[0] - qx, c[1] - qy))
            if math.hypot(bx - qx, by - qy) <= 2.5 * r_seed + 6:
                px, py = bx, by
                pvx, pvy = 0.6 * (bx - (qx - qvx)) + 0.4 * qvx, 0.6 * (by - (qy - qvy)) + 0.4 * qvy
                pk = k
                continue
        px, py, pvx, pvy, pk = qx, qy, qvx, qvy, k
    for k in E:
        if k not in emax:
            kn = min(ks, key=lambda j: abs(j - k))
            q = chain.pt(kn, k, *pred_log[kn]) or pred_log[kn]
            emax[k] = max(1e-6, float(E[k][int(max(0, q[1] - gate)):int(q[1] + gate + 1), int(max(0, q[0] - gate)):int(q[0] + gate + 1)].max()))
    by_n = {N: link(E, emax, chain, ks, cands, seed, (N - 1) // 2, sigma=args.sigma) for N in n_list}
    chosen = by_n[args.n]
    out_pts, rules = {}, {}
    r_prev = r_of_k(ks[0])
    for k in ks:
        s = chosen[k]
        r_prev = min(r_prev, r_of_k(k)) if r_of_k(k) < r_seed else r_prev
        x, y, r, rule, cnt = refine_centre(E[k], purple_mask(hsv[k], args.sat), s, r_prev, args.centre,
                                           sat=hsv[k][..., 1] if args.sat_weight else None)
        r_prev = min(r_prev, max(r, 0.5 * r_seed))
        out_pts[k] = (x, y, r_prev)
        rules[k] = {'rule': rule, 'u': round(s['u'], 2), 'e1': round(s['e1'], 1), 'used': s['used'], 'purple_px': cnt,
                    'inliers': motion.inliers[k], 'r_energy': round(r_of_k(k), 1),
                    'pred': [round(pred_log[k][0], 1), round(pred_log[k][1], 1)], 'link': [round(s['x'], 1), round(s['y'], 1)]}
    return {'E': E, 'cands': cands, 'pred_log': pred_log, 'by_n': by_n, 'chosen': chosen, 'out_pts': out_pts, 'rules': rules}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stem')
    ap.add_argument('--device', default='mps')
    ap.add_argument('--n', type=int, default=5, help='stack size N (odd); 1 = no stacking')
    ap.add_argument('--win', type=int, default=24)
    ap.add_argument('--seed', type=int, default=10)
    ap.add_argument('--k', type=int, default=6)
    ap.add_argument('--sigma', type=float, default=8.0)
    ap.add_argument('--sat', type=int, default=SAT_MIN, help='purple mask S threshold (final centre + energy)')
    ap.add_argument('--centre', default='purple', choices=['energy', 'purple'])
    ap.add_argument('--disc', type=float, default=1.3, help='purple centroid disc radius as a multiple of r')
    ap.add_argument('--sat-weight', action='store_true', help='weight the purple centroid by clip((S-25)/40)')
    ap.add_argument('--no-purple-energy', action='store_true', help='ablation: energy = blackhat x residual only')
    ap.add_argument('--passes', type=int, default=2, help='2 = recompute the energy with the per-frame radius from pass 1')
    args = ap.parse_args()
    t0 = time.time()
    stem = args.stem
    global NO_PURPLE, DISC
    NO_PURPLE = args.no_purple_energy
    DISC = args.disc
    base = json.load(open(f'{L1}/results/tracks/{stem}.json'))
    cut, frames = load_cut(stem)
    off = cut['cut_start']
    n = len(frames)
    k_pin = cut['pin_hit_frame'] - off
    k_lo = max(1, k_pin - args.win)
    k_hi = min(n - 2, k_pin + 2)
    ks = list(range(k_lo, k_hi + 1))
    motion = Motion(frames)
    chain = Chain(motion)
    hsv = {k: cv2.cvtColor(frames[k], cv2.COLOR_BGR2HSV) for k in range(k_lo - 4 - args.seed, k_hi + 4) if 0 <= k < n}
    bp = {p['f'] - off: p for p in base['frames']}
    seed_ks = [k for k in range(k_lo - args.seed, k_lo) if k in bp]
    if len(seed_ks) < 3:
        raise SystemExit(f'{stem}: only {len(seed_ks)} seed frames before cut frame {k_lo}')
    rs = []
    for k in seed_ks:
        p = bp[k]
        pc = purple_component(purple_mask(hsv[k], args.sat), p['x'], p['y'], p['r'])
        if pc is not None and pc[3] >= 12:
            rs.append(pc[2])
    r_seed = float(np.median(rs)) if rs else float(bp[seed_ks[-1]]['r'])
    kl = seed_ks[-1]
    vs = []
    for k in seed_ks[-4:-1]:
        w = chain.pt(k, kl, bp[k]['x'], bp[k]['y'])
        if w is not None:
            vs.append(((bp[kl]['x'] - w[0]) / (kl - k), (bp[kl]['y'] - w[1]) / (kl - k)))
    vx, vy = (float(np.mean([v[0] for v in vs])), float(np.mean([v[1] for v in vs]))) if vs else (0.0, 0.0)
    seed = (bp[kl]['x'], bp[kl]['y'], vx, vy)
    t1 = time.time()
    n_list = sorted({1, 3, 5, 7, args.n})
    p1 = solve(frames, hsv, motion, chain, ks, seed, kl, lambda k: r_seed, r_seed, args, n_list)
    res, pass_used = p1, 1
    if args.passes >= 2:
        # per-frame radius from pass 1 (non-increasing toward the pins, floor 0.5 r_seed), margin frames take the nearest
        r_by_k = {k: v[2] for k, v in p1['out_pts'].items()}
        rk = lambda k: r_by_k[min(r_by_k, key=lambda j: abs(j - k))]  # noqa: E731
        res, pass_used = solve(frames, hsv, motion, chain, ks, seed, kl, rk, r_seed, args, n_list), 2
    out_pts, rules, cands, by_n = res['out_pts'], res['rules'], res['cands'], res['by_n']
    rules = {k + off: v for k, v in rules.items()}
    replaced = set()
    frames_out, shifts = [], []
    for p in base['frames']:
        k = p['f'] - off
        if k in out_pts:
            x, y, r = out_pts[k]
            shifts.append(math.hypot(x - p['x'], y - p['y']))
            replaced.add(p['f'])
            frames_out.append({'f': p['f'], 'x': round(x, 1), 'y': round(y, 1), 'r': round(r, 1),
                               'conf': round(float(rules[p['f']]['u']), 2), 'src': rules[p['f']]['rule']})
        else:
            frames_out.append(dict(p))
    have = {p['f'] for p in frames_out}
    for k, (x, y, r) in out_pts.items():
        f = k + off
        if f not in have and f <= cut['pin_hit_frame'] + 2:
            replaced.add(f)
            frames_out.append({'f': f, 'x': round(x, 1), 'y': round(y, 1), 'r': round(r, 1),
                               'conf': round(float(rules[f]['u']), 2), 'src': rules[f]['rule']})
    frames_out.sort(key=lambda p: p['f'])
    boards = dict(base.get('boards') or {})
    lane = base.get('lane') or {}
    for p in frames_out:
        if p['f'] in replaced and str(p['f']) in lane and p['f'] <= cut['pin_hit_frame']:
            b = lane_point(lane[str(p['f'])], p['x'], p['y'])[0]
            if b is not None:
                boards[str(p['f'])] = round(float(b), 2)
    wall = round(time.time() - t0, 1)
    tr = {'stem': stem, 'method': METHOD, 'stage': 'ball', 'frames': frames_out, 'lane': lane, 'boards': boards,
          'final_board': base.get('final_board'), 'release_frame': cut['release_frame'],
          'pin_hit_frame': cut['pin_hit_frame'],
          'meta': {'builds_on': 'L1/results/tracks (sam2-video) + L1 lane quads', 'device_arg_unused': args.device,
                   'n_stack': args.n, 'win': args.win, 'seed_frames': [k + off for k in seed_ks], 'r_seed': round(r_seed, 2),
                   'seed_v': [round(vx, 2), round(vy, 2)], 'window': [k_lo + off, k_hi + off], 'k_cands': args.k,
                   'sigma': args.sigma, 'sat': args.sat, 'centre': args.centre, 'passes': pass_used, 'no_purple_energy': args.no_purple_energy, 'sat_weight': args.sat_weight, 'disc': args.disc,
                   'replaced': sorted(replaced), 'replaced_median_shift_px': round(float(np.median(shifts)), 2) if shifts else None,
                   'replaced_max_shift_px': round(float(max(shifts)), 2) if shifts else None,
                   'rules': rules, 'final_board_source': 'loop-1 engine (unchanged)',
                   'wall_s': wall, 'solve_s': round(time.time() - t1, 1), 'loop1_wall_s': (base.get('meta') or {}).get('wall_s'),
                   'inliers_window': [motion.inliers[k] for k in ks]}}
    add_top_down(tr)
    os.makedirs(f'{HERE}/tracks', exist_ok=True)
    os.makedirs(f'{HERE}/overlays', exist_ok=True)
    os.makedirs(f'{HERE}/work', exist_ok=True)
    json.dump(tr, open(f'{HERE}/tracks/{stem}.json', 'w'), indent=1)
    dump = {'stem': stem, 'r_seed': r_seed, 'window': [k_lo + off, k_hi + off], 'passes': pass_used,
            'cands': {str(k + off): [[round(c[0], 1), round(c[1], 1), round(c[2], 1)] for c in cands[k]] for k in ks},
            'cands_pass1': {str(k + off): [[round(c[0], 1), round(c[1], 1), round(c[2], 1)] for c in p1['cands'][k]] for k in ks},
            'by_n': {str(N): {str(k + off): [round(s['x'], 1), round(s['y'], 1), round(s['u'], 2)] for k, s in d.items()}
                     for N, d in by_n.items()},
            'by_n_pass1': {str(N): {str(k + off): [round(s['x'], 1), round(s['y'], 1), round(s['u'], 2)] for k, s in d.items()}
                           for N, d in p1['by_n'].items()},
            'final': {str(k + off): [round(v[0], 1), round(v[1], 1), round(v[2], 1)] for k, v in out_pts.items()}}
    json.dump(dump, open(f'{HERE}/work/{stem}_cands.json', 'w'))
    overlay(frames, cut, tr, chain, replaced, f'{HERE}/overlays/final__{stem}.jpg')
    print(json.dumps({'stem': stem, 'replaced': len(replaced), 'median_shift_px': tr['meta']['replaced_median_shift_px'],
                      'max_shift_px': tr['meta']['replaced_max_shift_px'], 'r_seed': round(r_seed, 1), 'seed_v': tr['meta']['seed_v'],
                      'r_last': round(out_pts[ks[-1]][2], 1),
                      'rules': {r: sum(1 for v in rules.values() if v['rule'] == r) for r in set(v['rule'] for v in rules.values())},
                      'wall_s': wall, 'inliers_min': min(tr['meta']['inliers_window'])}))


if __name__ == '__main__':
    main()
