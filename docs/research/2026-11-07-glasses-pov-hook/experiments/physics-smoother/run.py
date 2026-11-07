#!/usr/bin/env python
"""physics-smoother (loop 2, stage: path): a physical path model fitted in lane coordinates on top of the loop-1
sam2-video track. Reads the loop-1 track (per-frame ball + lane quads), re-derives the down-lane coordinate with a
decelerating kinematic model anchored on the pin row (contact row = ball centre + physical radius), then fits
board(ft) = skid line + optional hook (convex quadratic, boards rising only) with a Huber loss, choosing the hook
only when interleaved cross-validation AND BIC both prefer it and the fitted rise is >= 1 board.

usage: run.py <stem> [--device mps|cpu] [--track PATH]   (device is accepted for harness symmetry; no torch here)
writes tracks/<stem>.json (tracks format, SOURCE frames, boards{} = fitted boards, boards_raw{} = loop-1 boards,
path_fit{}, stage "path") and overlays/final__<stem>.jpg.
"""
import argparse
import json
import math
import os
import sys
import time

import numpy as np

L1 = '/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking'
L2 = '/Users/toka/code/toms_gym/docs/research/2026-11-07-glasses-pov-hook'
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, L1)
from lane_geom import edge_x, vanishing_point, pin_row, lane_point, TOTAL_BOARDS, LANE_FT  # noqa: E402

BALL_R_IN = 4.25
LANE_W_IN = 41.5
HUBER_FT = 1.5          # ft, kinematic fit
HUBER_BOARD = 1.0       # boards, path fit
BP_GRID = np.arange(35.0, 55.01, 1.0)
MIN_HOOK_PTS = 8
MIN_RISE = 1.0          # boards: truth uncertainty floor
CV_MARGIN = 0.05        # hook must beat straight by 5 % on held-out Huber loss
START_AFTER_RELEASE = 3
FIT_TO_HAND_PIN = os.environ.get('PS_FIT_TO_HAND_PIN') == '1' or '--fit-to-hand-pin-hit' in sys.argv   # include frames up to the hand pin_hit_frame even when the kinematic ft is past 60
FIT_FROM_FT = float(os.environ.get('PS_FIT_FROM_FT', 0.4 * LANE_FT))   # (env override is for the sensitivity sweep only)
W_EXP = float(os.environ.get('PS_W_EXP', 2.0))   # board model is fitted on the last 60 % of the roll: the quad is one SAM fit near the pins carried by an affine, and its error grows toward the near end


def edges(q, y):
    return edge_x(q['fl_l'], q['pd_l'], y), edge_x(q['fl_r'], q['pd_r'], y)


def r_phys(q, y):
    xl, xr = edges(q, y)
    return BALL_R_IN * abs(xl - xr) / LANE_W_IN


def depth_s(q, y):
    vp = vanishing_point(q)
    py = pin_row(q)
    if vp is None or y <= vp[1] + 1e-6 or py <= vp[1]:
        return None
    return (py - vp[1]) / (y - vp[1])


def huber_w(r, delta):
    a = np.abs(r)
    return np.where(a <= delta, 1.0, delta / np.maximum(a, 1e-9))


def huber_loss(r, delta):
    a = np.abs(r)
    return np.where(a <= delta, 0.5 * r * r, delta * (a - 0.5 * delta))


def irls(X, y, w0, delta, nonneg_cols=(), iters=30):
    """Weighted Huber linear fit by IRLS; columns in nonneg_cols are clipped at 0 (refit without them when negative)."""
    w = np.asarray(w0, float).copy()
    beta = np.zeros(X.shape[1])
    cols = list(range(X.shape[1]))
    for _ in range(iters):
        Xc = X[:, cols]
        sw = np.sqrt(w)
        beta_c, *_ = np.linalg.lstsq(Xc * sw[:, None], y * sw, rcond=None)
        bad = [c for c in nonneg_cols if c in cols and beta_c[cols.index(c)] < 0]
        if bad:
            cols = [c for c in cols if c not in bad]
            continue
        nb = np.zeros(X.shape[1])
        nb[cols] = beta_c
        r = y - X @ nb
        w = np.asarray(w0, float) * huber_w(r, delta)
        if np.max(np.abs(nb - beta)) < 1e-6:
            beta = nb
            break
        beta = nb
    return beta


# ---------------------------------------------------------------- kinematic (down-lane) model
def fit_kinematics(t, s, T):
    """ft_obs = a*(s-1) + 60 (pin row = 60 ft, contact row s); ft(t) = d0 + v0*t - 0.5*k*t^2. Returns params."""
    from scipy.optimize import least_squares

    def resid(p):
        a, d0, v0, k = p
        pred = d0 + v0 * t - 0.5 * k * t * t
        obs = a * (s - 1.0) + LANE_FT
        pen = 50.0 * max(0.0, (0.6 * v0) - (v0 - k * T))      # final speed >= 60 % of release speed
        return np.append(obs - pred, pen)

    best = None
    for a0 in (50.0, 66.0, 90.0):
        for k0 in (0.0, 0.005):
            p0 = [a0, 1.0, LANE_FT / T, k0]
            r = least_squares(resid, p0, loss='huber', f_scale=HUBER_FT,
                              bounds=([25.0, 0.0, 0.3, 0.0], [150.0, 3.0, 3.0, 0.05]))
            if best is None or r.cost < best.cost:
                best = r
    a, d0, v0, k = best.x
    obs = a * (s - 1.0) + LANE_FT
    pred = d0 + v0 * t - 0.5 * k * t * t
    rmse = float(np.sqrt(np.mean((obs - pred) ** 2)))
    # frame where ft = 60 (smallest positive root)
    disc = v0 * v0 - 2 * k * (LANE_FT - d0)
    if k > 1e-9 and disc >= 0:
        t60 = (v0 - math.sqrt(disc)) / k
    else:
        t60 = (LANE_FT - d0) / v0
    return {'a': round(float(a), 3), 'b': round(float(LANE_FT - a), 3), 'd0_ft': round(float(d0), 2),
            'v0_ft_per_frame': round(float(v0), 4), 'decel_ft_per_frame2': round(float(k), 5),
            'v_end_ft_per_frame': round(float(v0 - k * T), 4), 'n': int(len(t)), 'rmse_ft': round(rmse, 2),
            't60_frames_after_release': round(float(t60), 1)}


def ft_of(km, t):
    return km['d0_ft'] + km['v0_ft_per_frame'] * t - 0.5 * km['decel_ft_per_frame2'] * t * t


# ---------------------------------------------------------------- board (across-lane) model
def design(ft, bp):
    cols = [np.ones_like(ft), ft]
    if bp is not None:
        cols.append(np.maximum(0.0, ft - bp) ** 2)
    return np.stack(cols, 1)


def fit_model(ft, b, w, bp):
    X = design(ft, bp)
    beta = irls(X, b, w, HUBER_BOARD, nonneg_cols=(2,) if bp is not None else ())
    return beta


def predict(beta, bp, ft):
    return design(np.asarray(ft, float), bp) @ beta


def cv_loss(ft, b, w, bp):
    """Interleaved 2-fold: fit on even-indexed points, score odd, and vice versa (weighted Huber loss per point)."""
    idx = np.arange(len(ft))
    tot = 0.0
    for parity in (0, 1):
        tr, te = idx % 2 == parity, idx % 2 != parity
        if tr.sum() < 4 or te.sum() < 2:
            return None
        beta = fit_model(ft[tr], b[tr], w[tr], bp)
        r = b[te] - predict(beta, bp, ft[te])
        tot += float(np.sum(w[te] * huber_loss(r, HUBER_BOARD)))
    return tot / float(np.sum(w))


def bic(ft, b, w, beta, bp, n_params):
    r = b - predict(beta, bp, ft)
    r = np.clip(r, -3 * HUBER_BOARD, 3 * HUBER_BOARD)   # clipped so one gutter excursion cannot buy a parameter
    n = len(ft)
    mse = float(np.sum(w * r * r) / np.sum(w))
    return n * math.log(max(mse, 1e-6)) + n_params * math.log(n)


def fit_path(ft, b, w):
    ft, b, w = np.asarray(ft, float), np.asarray(b, float), np.asarray(w, float)
    out = {'n_points': int(len(ft))}
    beta_s = fit_model(ft, b, w, None)
    cv_s = cv_loss(ft, b, w, None)
    bic_s = bic(ft, b, w, beta_s, None, 2)
    best_h = None
    for bp in BP_GRID:
        if np.sum(ft > bp) < MIN_HOOK_PTS:
            continue
        beta = fit_model(ft, b, w, bp)
        if beta[2] <= 0:
            continue
        r = b - predict(beta, bp, ft)
        loss = float(np.sum(w * huber_loss(r, HUBER_BOARD)))
        if best_h is None or loss < best_h[0]:
            best_h = (loss, bp, beta)
    cand = {'straight': {'beta': beta_s, 'bp': None, 'cv': cv_s, 'bic': bic_s}}
    if best_h is not None:
        _, bp, beta = best_h
        cand['hook'] = {'beta': beta, 'bp': float(bp), 'cv': cv_loss(ft, b, w, bp), 'bic': bic(ft, b, w, beta, bp, 4)}
    chosen = 'straight'
    reasons = []
    if 'hook' in cand and cand['hook']['cv'] is not None and cv_s is not None:
        h = cand['hook']
        grid = np.linspace(h['bp'], LANE_FT, 50)
        curve = predict(h['beta'], h['bp'], grid)
        rise = float(curve[-1] - curve.min())
        cv_ok = h['cv'] < (1.0 - CV_MARGIN) * cv_s
        bic_ok = h['bic'] < bic_s
        rise_ok = rise >= MIN_RISE
        reasons = [f"cv {h['cv']:.3f} vs {cv_s:.3f} {'ok' if cv_ok else 'no'}",
                   f"bic {h['bic']:.1f} vs {bic_s:.1f} {'ok' if bic_ok else 'no'}",
                   f"rise {rise:.2f} {'ok' if rise_ok else 'no'}"]
        if cv_ok and bic_ok:
            chosen = 'hook' if rise_ok else 'curve'
    else:
        reasons = ['no admissible hook candidate']
    c = cand['hook'] if chosen in ('hook', 'curve') else cand['straight']
    beta, bp = c['beta'], c['bp']
    pred = predict(beta, bp, ft)
    res = b - pred
    grid = np.linspace(FIT_FROM_FT, LANE_FT, 121)
    curve = predict(beta, bp, grid)
    i_min = int(np.argmin(curve))
    out.update({
        'kind': chosen, 'chose_hook': chosen == 'hook',
        'params': {'b0': round(float(beta[0]), 4), 'b1_boards_per_ft': round(float(beta[1]), 5),
                   'breakpoint_ft': None if bp is None else round(float(bp), 1),
                   'c_boards_per_ft2': None if bp is None else round(float(beta[2]), 6)},
        'board_at_60ft': round(float(curve[-1]), 2),
        'min_board': round(float(curve[i_min]), 2), 'min_board_ft': round(float(grid[i_min]), 1),
        'board_at_0ft': round(float(predict(beta, bp, [0.0])[0]), 2),
        'fit_from_ft': FIT_FROM_FT,
        'residual_rms_boards': round(float(np.sqrt(np.mean(res * res))), 2),
        'residual_rms_boards_weighted': round(float(np.sqrt(np.sum(w * res * res) / np.sum(w))), 2),
        'selection': {'straight': {'cv': None if cv_s is None else round(cv_s, 4), 'bic': round(bic_s, 2)},
                      'hook': None if 'hook' not in cand else {
                          'cv': None if cand['hook']['cv'] is None else round(cand['hook']['cv'], 4),
                          'bic': round(cand['hook']['bic'], 2), 'bp': cand['hook']['bp'],
                          'c': round(float(cand['hook']['beta'][2]), 6)},
                      'reasons': reasons},
    })
    return out, beta, bp


# ---------------------------------------------------------------- driver
def load_inputs(stem, track_path):
    cuts = {c['stem']: c for c in json.load(open(os.path.join(L1, 'work', 'cuts', 'cuts.json')))}
    tr = json.load(open(track_path))
    return cuts[stem], tr


def per_frame_samples(tr):
    """{f: dict(x, y, r, board_raw, s_centre, s_contact, zone_raw)} for frames with a quad."""
    lanes = tr.get('lane') or {}
    out = {}
    for p in tr['frames']:
        q = lanes.get(str(p['f']))
        if not q:
            continue
        board = lane_point(q, p['x'], p['y'])[0]
        sc = depth_s(q, p['y'])
        yc = p['y'] + r_phys(q, p['y'])
        st = depth_s(q, yc)
        out[int(p['f'])] = {'x': p['x'], 'y': p['y'], 'r': p['r'], 'board_raw': board, 's_centre': sc,
                            's_contact': st, 'r_phys': r_phys(q, p['y'])}
    return out


def run(stem, track_path, log):
    t0 = time.time()
    cut, tr = load_inputs(stem, track_path)
    rel, pin = int(cut['release_frame']), int(cut['pin_hit_frame'])
    T = pin - rel
    samples = per_frame_samples(tr)
    out = {'stem': stem, 'method': 'physics-smoother(sam2-video)', 'stage': 'path',
           'frames': tr['frames'], 'lane': tr.get('lane') or {}, 'boards': {}, 'boards_raw': tr.get('boards') or {},
           'final_board': None, 'release_frame': rel, 'pin_hit_frame': pin, 'lane_top_down': [], 'path_fit': None,
           'meta': {'base_track': track_path, 'base_method': tr.get('method'), 'base_meta': tr.get('meta'),
                    'final_board_engine': tr.get('final_board'), 'base_ft_model': tr.get('lane_top_down_model')}}
    if not samples:
        out['meta']['reason'] = 'no lane quads in the base track'
        out['meta']['wall_s'] = round(time.time() - t0, 2)
        return out
    # --- kinematics on contact-row depth
    ks = [(f - rel, d['s_contact']) for f, d in sorted(samples.items())
          if rel + START_AFTER_RELEASE <= f <= pin and d['s_contact'] is not None and 0.08 <= d['s_contact'] <= 1.03
          and d['board_raw'] is not None and -2.0 <= d['board_raw'] <= 42.0]
    if len(ks) < 8:
        out['meta']['reason'] = f'{len(ks)} kinematic samples'
        out['meta']['wall_s'] = round(time.time() - t0, 2)
        return out
    km = fit_kinematics(np.array([k[0] for k in ks], float), np.array([k[1] for k in ks], float), float(T))
    km['implied_pin_frame'] = round(rel + km['t60_frames_after_release'], 1)
    km['implied_minus_hand_pin_hit'] = round(km['implied_pin_frame'] - pin, 1)
    km['ft_at_hand_pin_hit'] = round(float(ft_of(km, T)), 1)
    km['kind'] = 'contact_row_decel_fit'
    out['ft_model'] = km
    log(f'{stem}: kinematics a={km["a"]} d0={km["d0_ft"]} v0={km["v0_ft_per_frame"]} k={km["decel_ft_per_frame2"]} '
        f'rmse {km["rmse_ft"]} ft, 60 ft at f{km["implied_pin_frame"]} (hand pin hit {pin}, {km["implied_minus_hand_pin_hit"]:+.1f})')
    # --- path fit in (ft, board)
    pts = []
    for f, d in sorted(samples.items()):
        if f < rel + START_AFTER_RELEASE or f > pin or d['board_raw'] is None:
            continue
        ft = float(ft_of(km, f - rel))
        ft_end = max(LANE_FT, float(ft_of(km, T))) if FIT_TO_HAND_PIN else LANE_FT
        if not (FIT_FROM_FT <= ft <= ft_end) or not (-2.0 <= d['board_raw'] <= 42.0):
            continue
        s = max(0.05, min(1.0, (ft - km['b']) / km['a']))
        pts.append((f, ft, d['board_raw'], s ** W_EXP))
    if len(pts) < 8:
        out['meta']['reason'] = f'{len(pts)} path samples'
        out['meta']['wall_s'] = round(time.time() - t0, 2)
        return out
    fit, beta, bp = fit_path([p[1] for p in pts], [p[2] for p in pts], [p[3] for p in pts])
    fit['weighting'] = f's^{W_EXP:g} (depth ratio, 1 at the pin row); fit window ft >= {FIT_FROM_FT:g}, near end extrapolated'
    fit['frames_used'] = [pts[0][0], pts[-1][0]]
    fit['fit_to_hand_pin_hit'] = FIT_TO_HAND_PIN
    used = {p[0] for p in pts}
    log(f'{stem}: path {fit["kind"]} n={fit["n_points"]} {fit["params"]} entry {fit["board_at_60ft"]} min {fit["min_board"]}@{fit["min_board_ft"]} '
        f'rms {fit["residual_rms_boards"]} | {"; ".join(fit["selection"]["reasons"])}')
    # --- per-frame outputs
    boards, td, bbf = {}, [], {}
    for f, d in sorted(samples.items()):
        if f < rel or f > pin:
            continue
        ft = float(ft_of(km, f - rel))
        bf = float(predict(beta, bp, [min(ft, LANE_FT)])[0])
        boards[str(f)] = round(bf, 2)
        bbf[str(f)] = round(bf, 2)
        on = bool(0.5 <= bf <= 39.5 and 0.0 <= ft <= 60.5)
        zone = ('behind_foul' if ft < 0 else 'past_pins' if ft > 60.5 else 'gutter_r' if bf < 0.5
                else 'gutter_l' if bf > 39.5 else 'lane')
        td.append({'f': f, 'board': round(bf, 2), 'ft': round(ft, 2), 'on_lane': on, 'zone': zone,
                   'in_fit_window': f in used,
                   'board_raw': None if d['board_raw'] is None else round(d['board_raw'], 2),
                   'board_engine': (tr.get('boards') or {}).get(str(f))})
    fit['boards_by_frame'] = bbf
    out.update({'boards': boards, 'lane_top_down': td, 'path_fit': fit, 'final_board': fit['board_at_60ft'],
                'lane_top_down_model': {'kind': 'physics-smoother kinematic', 'a': km['a'], 'b': km['b'],
                                        'note': 'ft per frame comes from ft_model (time), not from a*s+b'}})
    out['meta']['wall_s'] = round(time.time() - t0, 2)
    return out


# ---------------------------------------------------------------- overlay
def project(q, km, board, ft):
    """(board, ft) -> image (x, y) of the ball CENTRE in the frame of quad q (ft -> contact row -> centre row)."""
    vp = vanishing_point(q)
    py = pin_row(q)
    if vp is None:
        return None
    s = (ft - km['b']) / km['a']
    if s <= 0.03 or py <= vp[1]:
        return None
    yc = vp[1] + (py - vp[1]) / s
    y = yc - r_phys(q, yc)
    xl, xr = edges(q, y)
    return xr + (board - 1.0) / (TOTAL_BOARDS - 1) * (xl - xr), y


def overlay(out, cut, path):
    import cv2
    rel, pin = out['release_frame'], out['pin_hit_frame']
    f = max(cut['cut_start'], min(cut['cut_end'], pin - 4))
    cap = cv2.VideoCapture(cut['cut_path'])
    cap.set(cv2.CAP_PROP_POS_FRAMES, f - cut['cut_start'])
    ok, im = cap.read()
    cap.release()
    if not ok:
        return False
    im = cv2.resize(im, (im.shape[1] // 2, im.shape[0] // 2))
    H, W = im.shape[:2]
    q = (out.get('lane') or {}).get(str(f))
    km = out.get('ft_model')
    fit = out.get('path_fit')
    if q:
        for a, b in (('fl_l', 'pd_l'), ('fl_r', 'pd_r')):
            y0, y1 = H * 2 - 1, 0
            p0 = (int(edge_x(q[a], q[b], y0) / 2), int(y0 / 2))
            p1 = (int(edge_x(q[a], q[b], y1) / 2), int(y1 / 2))
            cv2.line(im, p0, p1, (255, 220, 0), 2)
        py = int(pin_row(q) / 2)
        cv2.line(im, (0, py), (W, py), (0, 200, 255), 1)
    if q and km and fit:
        raw = [(e['board_raw'], e['ft']) for e in out['lane_top_down'] if e['board_raw'] is not None and -2 <= e['board_raw'] <= 42 and 0 <= e['ft'] <= 60]
        for b, ft in raw:
            p = project(q, km, b, ft)
            if p:
                cv2.circle(im, (int(p[0] / 2), int(p[1] / 2)), 3, (0, 140, 255), -1)
        pl = []
        for e in out['lane_top_down']:
            if 0 <= e['ft'] <= 60:
                p = project(q, km, e['board'], e['ft'])
                if p:
                    pl.append((int(p[0] / 2), int(p[1] / 2)))
        if len(pl) > 1:
            cv2.polylines(im, [np.array(pl, np.int32)], False, (60, 220, 60), 3)
        p60 = project(q, km, fit['board_at_60ft'], LANE_FT)
        if p60:
            cv2.drawMarker(im, (int(p60[0] / 2), int(p60[1] / 2)), (255, 255, 255), cv2.MARKER_CROSS, 16, 2)
    lines = [f"physics-smoother {out['stem']} f{f} (pin_hit-4)",
             f"board@60ft {fit['board_at_60ft'] if fit else '-'}  engine final {out['meta'].get('final_board_engine')}",
             f"fit {fit['kind'] if fit else '-'} n={fit['n_points'] if fit else 0} rms {fit['residual_rms_boards'] if fit else '-'}  "
             f"60ft@f{km['implied_pin_frame'] if km else '-'} hand {pin}"]
    for i, s in enumerate(lines):
        cv2.putText(im, s, (8, 24 + 22 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3)
        cv2.putText(im, s, (8, 24 + 22 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    # top-down panel: board 39 at the left, 1 at the right, foul line bottom, pins top
    PW = 220
    strip = np.full((H, PW, 3), (70, 160, 215), np.uint8)
    X = lambda b: int(PW * (39 - min(max(b, -1.0), 41.0)) / 38)  # noqa: E731
    Y = lambda ft: int((H - 20) * (1 - ft / 60) + 10)  # noqa: E731
    for bd in (5, 10, 15, 20, 25, 30, 35):
        cv2.drawMarker(strip, (X(1 + (bd - 0.5) * 38 / 39), Y(15)), (40, 40, 40), cv2.MARKER_TRIANGLE_UP, 8, 2)
    cv2.line(strip, (X(20), Y(60)), (X(20), Y(0)), (120, 190, 230), 1)
    cv2.circle(strip, (X(20), Y(60)), 4, (255, 255, 255), -1)
    cv2.circle(strip, (X(17.5), Y(60)), 3, (0, 0, 255), 1)
    if fit:
        for e in out['lane_top_down']:
            if e['board_raw'] is not None and 0 <= e['ft'] <= 60:
                cv2.circle(strip, (X(e['board_raw']), Y(e['ft'])), 2, (0, 140, 255), -1)
        tp = [(X(e['board']), Y(e['ft'])) for e in out['lane_top_down'] if 0 <= e['ft'] <= 60]
        if len(tp) > 1:
            cv2.polylines(strip, [np.array(tp, np.int32)], False, (60, 220, 60), 2)
        if fit['params'].get('breakpoint_ft') is not None:
            cv2.line(strip, (0, Y(fit['params']['breakpoint_ft'])), (PW, Y(fit['params']['breakpoint_ft'])), (150, 40, 150), 1)
        cv2.putText(strip, f"b{fit['board_at_60ft']:.1f} {fit['kind']}", (4, H - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)
    cv2.imwrite(path, np.hstack([im, strip]))
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stem')
    ap.add_argument('--device', default='mps', help='unused (no torch in this stage); kept for the harness')
    ap.add_argument('--track', default=None, help='base track JSON (default: loop-1 results/tracks/<stem>.json)')
    ap.add_argument('--fit-to-hand-pin-hit', action='store_true', help='fit the board model on frames up to pin_hit_frame even past the kinematic 60 ft')
    a = ap.parse_args()
    track_path = a.track or os.path.join(L1, 'results', 'tracks', f'{a.stem}.json')
    log = lambda s: print(s, flush=True)  # noqa: E731
    out = run(a.stem, track_path, log)
    cut = {c['stem']: c for c in json.load(open(os.path.join(L1, 'work', 'cuts', 'cuts.json')))}[a.stem]
    os.makedirs(os.path.join(HERE, 'tracks'), exist_ok=True)
    os.makedirs(os.path.join(HERE, 'overlays'), exist_ok=True)
    op = os.path.join(HERE, 'tracks', f'{a.stem}.json')
    json.dump(out, open(op, 'w'), indent=1)
    ov = os.path.join(HERE, 'overlays', f'final__{a.stem}.jpg')
    if cut.get('cut_path') and os.path.exists(cut['cut_path']):
        overlay(out, cut, ov)
    log(f'wrote {op} ({len(out["boards"])} fitted boards, final {out["final_board"]}, wall {out["meta"].get("wall_s")}s) and {ov}')


if __name__ == '__main__':
    main()
