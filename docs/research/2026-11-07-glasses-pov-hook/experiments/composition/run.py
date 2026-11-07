"""run.py <stem> [--device mps|cpu] [--lane auto|sam|edge] [--refine] [--ball file|rerun] [--out-dir DIR]

Loop-2 'composition' (stage: both): the loop-1 appearance-prior ball track (fixed purple hue + camera-compensated
motion peak, 100 % far recall on dev) over a per-frame lane stage, with a straight-line / line+hook path fit.

Lane variants
  sam  : the engine SAM per-frame lane quads that loop 1 stored with the sam2-video track
         (L1/results/tracks/<stem>.json "lane", one SAM fit carried by the engine's per-frame affine, pin_y included).
  edge : a lane-first-style measurement on EVERY frame (L1/experiments/lane-first/lane.py: half-res wood mask,
         RANSAC gutter edges, component chosen by the ball), optionally refined at the ball's row (--refine: each
         edge snapped to the strongest wood->gutter grey step within +-12 px of the fitted line at that row).
  auto : sam where loop 1 has a quad for the frame, else edge (the fallback for the stems SAM refused: 185121, 191820).

Every frame number is a SOURCE frame (cut frame k = cut_start + k). Boards 1-39 from the right gutter, read at the
ball CENTRE row like the dev truth ("boards"); the contact-row read (y + r) is kept beside it ("boards_contact").
Writes <out-dir>/tracks/<stem>.json (tracks format + lane_top_down + path_fit + stage "both") and
<out-dir>/overlays/final__<stem>.jpg (pin_hit-4 frame, whole track warped into it, edges used, pin-row board,
top-down panel board vs ft).
"""
import argparse
import json
import math
import os
import statistics
import sys
import time

import cv2
import numpy as np

L1 = '/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking'
L2 = '/Users/toka/code/toms_gym/docs/research/2026-11-07-glasses-pov-hook'
EXP = os.path.join(L2, 'experiments', 'composition')
AP = os.path.join(L1, 'experiments', 'appearance-prior')
LF = os.path.join(L1, 'experiments', 'lane-first')
sys.path.insert(0, L1)
sys.path.insert(0, LF)
import lane_geom as LG  # noqa: E402
import lane as LN  # noqa: E402  (lane-first lane.py)

METHOD = 'composition'
REFINE_WIN = 12          # px either side of the fitted edge searched for the grey step at the ball row
REFINE_MIN_STEP = 25.0   # grey levels: smaller steps keep the fitted line
TAIL = 0.6               # path fit uses the last 60 % of release..pin_hit (the scorer's roll tail)
ENTRY_N = 10             # frames before pin_hit in the entry (board at 60 ft) fit
HOOK_MIN_GAIN = 0.5      # boards RMS the hook term must remove to be drawn
HOOK_MIN_AMOUNT = 1.0    # boards the fitted path must rise after its minimum to count as a hook
SMOOTH_K = 5             # rolling median window for min_board


def load_cut(stem):
    cuts = {c['stem']: c for c in json.load(open(os.path.join(L1, 'work', 'cuts', 'cuts.json')))}
    return cuts[stem]


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


# ---------------------------------------------------------------- ball stage
def ball_stage(stem, cut, how, log):
    """[{f, x, y, r, conf, src}] in SOURCE frames from the loop-1 appearance-prior track, or re-run apptrack."""
    p = os.path.join(AP, 'tracks', f'{stem}.json')
    if how == 'file' and os.path.exists(p):
        t = json.load(open(p))
        log(f'  [ball] appearance-prior track from file: {len(t["frames"])} points {t["frames"][0]["f"]}..{t["frames"][-1]["f"]}')
        return [dict(q) for q in t['frames']], 'appearance-prior/fixed (loop-1 track file)'
    sys.path.insert(0, AP)
    sys.path.insert(0, '/Users/toka/code/bowling-app/pov-engine')
    import run as APR  # noqa: E402  (appearance-prior/run.py: ensure_cache)
    from apptrack import TrackConfig, track  # noqa: E402
    frames = read_frames(cut['cut_path'])
    dets, shifts, _ = APR.ensure_cache(stem)
    pos, rep = track(frames, dets, shifts, TrackConfig(model='fixed', use_yolo=False))
    off = cut['cut_start']
    log(f'  [ball] apptrack re-run: {rep}')
    return [{'f': q['k'] + off, 'x': q['x'], 'y': q['y'], 'r': q['r'], 'conf': q['conf'], 'src': q['src']} for q in pos], \
        'appearance-prior/fixed (re-run)'


# ---------------------------------------------------------------- lane stage
def sam_quads(stem):
    p = os.path.join(L1, 'results', 'tracks', f'{stem}.json')
    if not os.path.exists(p):
        return {}
    t = json.load(open(p))
    return {int(k): v for k, v in (t.get('lane') or {}).items()}


def refine_edge(gray, x_fit, y, side):
    """Snap a fitted edge x at row y to the strongest wood->gutter step within +-REFINE_WIN px.
    side 'L': wood is to the right of the edge (grey rises left->right); 'R': wood is to the left (grey falls)."""
    H, W = gray.shape
    yi = int(round(y))
    if not 1 <= yi < H - 1:
        return x_fit, None
    x0, x1 = int(max(2, x_fit - REFINE_WIN)), int(min(W - 3, x_fit + REFINE_WIN))
    if x1 - x0 < 4:
        return x_fit, None
    row = gray[yi - 1:yi + 2, x0 - 2:x1 + 3].astype(np.float32).mean(axis=0)
    row = cv2.GaussianBlur(row.reshape(1, -1), (5, 1), 0).ravel()
    d = row[4:] - row[:-4]                       # step over 4 px, centred at i + 2
    sgn = 1.0 if side == 'L' else -1.0
    s = sgn * d
    i = int(np.argmax(s))
    if s[i] < REFINE_MIN_STEP:
        return x_fit, None
    return float(x0 - 2 + i + 2), float(s[i])


def edge_quad(img, prev_mask, ball, refine):
    """lane-first per-frame lane fit with the ball as the component hint -> (quad, mask, info)."""
    mask = LN.lane_mask(img)
    lf, info = LN.fit_lane(mask, prev_mask, (ball['x'], ball['y']))
    if lf is None:
        return None, mask, info
    u = lf.u(ball['x'], ball['y'])
    if not -0.15 <= u <= 1.15:
        return None, mask, dict(info, why='ball outside the fitted lane', u=round(u, 3))
    q = lf.quad()
    q['src'] = 'edge'
    if refine:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        y = ball['y']
        xl, xr = lf.xl(y), lf.xr(y)
        nl, sl = refine_edge(gray, xl, y, 'L')
        nr, sr = refine_edge(gray, xr, y, 'R')
        q['row_edges'] = {'y': round(y, 1), 'xl_fit': round(xl, 1), 'xr_fit': round(xr, 1),
                          'xl': round(nl, 1), 'xr': round(nr, 1), 'step_l': sl, 'step_r': sr}
    cm = LN.component_mask(mask, lf.comp_id)
    return q, cm, info


def depth_ok(q, min_pd_row=60.0):
    """An edge quad whose pd row sits at the frame top (the lane's far end is out of frame on the release frames, the
    camera looks down) carries a board but no depth: ft from it is meaningless (185121 f298 read 42 ft)."""
    return LG.pin_row(q) >= min_pd_row


def board_from_quad(q, x, y):
    re = q.get('row_edges')
    if re and abs(re['y'] - y) < 0.6:
        w = re['xl'] - re['xr']
        return None if abs(w) < 1e-6 else (x - re['xr']) / w * 38.0 + 1.0
    return LG.lane_point(q, x, y)[0]


# ---------------------------------------------------------------- path fit
def theil_sen(pts):
    """(slope, intercept) robust line through [(f, b)] ; intercept at f = 0."""
    n = len(pts)
    if n < 2:
        return None
    slopes = [(pts[j][1] - pts[i][1]) / (pts[j][0] - pts[i][0]) for i in range(n) for j in range(i + 1, n)
              if pts[j][0] != pts[i][0]]
    if not slopes:
        return None
    m = statistics.median(slopes)
    c = statistics.median([b - m * f for f, b in pts])
    return m, c


def rolling_median(vals, k):
    h = k // 2
    return [statistics.median(vals[max(0, i - h):i + h + 1]) for i in range(len(vals))]


def fit_path(series, release, pin_hit, ft_of):
    """series {f: board} on release..pin_hit. Line vs line+hook over the roll tail; the hook (board rising again
    after a minimum, i.e. the ball coming back LEFT) is kept only when it removes >= HOOK_MIN_GAIN boards RMS and
    rises >= HOOK_MIN_AMOUNT boards. Entry = Theil-Sen over the last ENTRY_N frames evaluated at pin_hit."""
    pts = sorted((f, b) for f, b in series.items() if release <= f <= pin_hit)
    out = {'kind': None, 'params': {}, 'board_at_60ft': None, 'min_board': None, 'min_board_ft': None,
           'residual_rms_boards': None, 'n_points': len(pts)}
    if len(pts) < 4:
        return out
    tail_lo = release + (1.0 - TAIL) * (pin_hit - release)
    tail = [p for p in pts if p[0] >= tail_lo] or pts[-4:]
    last = [p for p in pts if p[0] >= pin_hit - ENTRY_N] or pts[-4:]
    ts = theil_sen(last)
    entry = ts[0] * pin_hit + ts[1] if ts else last[-1][1]
    # line and line+hook (quadratic beyond a breakpoint, upward) over the tail, least squares with the Theil-Sen
    # line as the robust baseline residual
    f = np.array([p[0] for p in tail], float)
    b = np.array([p[1] for p in tail], float)
    f0 = f[0]
    A = np.c_[np.ones_like(f), f - f0]
    (c0, c1), *_ = np.linalg.lstsq(A, b, rcond=None)
    line = c0 + c1 * (f - f0)
    rms_line = float(np.sqrt(np.mean((b - line) ** 2)))
    best = None
    for fb in np.arange(f0 + 2, f[-1] - 2, 1.0):
        h = np.maximum(0.0, f - fb) ** 2
        A2 = np.c_[np.ones_like(f), f - f0, h]
        (d0, d1, d2), *_ = np.linalg.lstsq(A2, b, rcond=None)
        if d2 <= 0:
            continue
        fit = d0 + d1 * (f - f0) + d2 * h
        rms = float(np.sqrt(np.mean((b - fit) ** 2)))
        if best is None or rms < best[0]:
            best = (rms, fb, d0, d1, d2, fit)
    kind = 'line'
    fitted = line
    params = {'f0': f0, 'b0': round(float(c0), 3), 'slope_boards_per_frame': round(float(c1), 4)}
    rms = rms_line
    if best is not None:
        rms_h, fb, d0, d1, d2, fit_h = best
        ff = np.arange(f0, pin_hit + 1, 1.0)
        full = d0 + d1 * (ff - f0) + d2 * np.maximum(0.0, ff - fb) ** 2
        rise = float(full[-1] - full.min())
        if rms_line - rms_h >= HOOK_MIN_GAIN and rise >= HOOK_MIN_AMOUNT:
            kind, fitted, rms = 'line+hook', fit_h, rms_h
            params = {'f0': f0, 'b0': round(float(d0), 3), 'slope_boards_per_frame': round(float(d1), 4),
                      'break_frame': float(fb), 'curv_boards_per_frame2': round(float(d2), 5),
                      'rise_after_min': round(rise, 2), 'rms_line': round(rms_line, 2)}
        else:
            params['hook_rejected'] = {'rms_line': round(rms_line, 2), 'rms_hook': round(rms_h, 2),
                                       'rise': round(rise, 2), 'break_frame': float(fb)}
    # min of the smoothed tail (raw far-end jitter of 1-2.5 boards invents a hook otherwise)
    sm = rolling_median([p[1] for p in tail], SMOOTH_K)
    if kind == 'line+hook':
        ff = np.arange(f0, pin_hit + 1, 1.0)
        full = best[2] + best[3] * (ff - f0) + best[4] * np.maximum(0.0, ff - best[1]) ** 2
        i = int(np.argmin(full))
        mn, f_min = float(full[i]), float(ff[i])
    else:
        # a straight line has no hook: its minimum over the tail is at one end (the entry when the ball is still
        # moving right at the pins); the smoothed-series minimum is kept for the notes only
        ff = np.arange(f0, pin_hit + 1, 1.0)
        full = c0 + c1 * (ff - f0)
        i = int(np.argmin(full))
        mn, f_min = float(full[i]), float(ff[i])
        params['smoothed_tail_min'] = round(float(min(sm)), 2)
    out.update({'kind': kind, 'params': params, 'board_at_60ft': round(float(entry), 2), 'min_board': round(mn, 2),
                'min_board_frame': f_min, 'min_board_ft': None if ft_of(f_min) is None else round(ft_of(f_min), 1),
                'residual_rms_boards': round(rms, 2), 'n_points': len(pts), 'n_tail': len(tail),
                'entry_fit': {'n': len(last), 'slope_boards_per_frame': None if not ts else round(ts[0], 4)},
                'boards_by_frame': {str(int(ff)): round(float(v), 2) for ff, v in zip(f, fitted)}})
    return out


# ---------------------------------------------------------------- overlay
def draw_overlay(frames, cut, tr, out_path, used_quads):
    off = cut['cut_start']
    k = max(0, min(len(frames) - 1, cut['pin_hit_frame'] - 4 - off))
    f_show = off + k
    im = frames[k].copy()
    pin = cut['pin_hit_frame']
    q = used_quads.get(f_show)
    m = tr.get('lane_top_down_model') or {'a': 60.0, 'b': 0.0}
    td = {p['f']: p for p in tr.get('lane_top_down') or []}
    # raw track (thin orange) and the camera-compensated track (green): every point -> (board, ft) in its own
    # frame's quad -> image point in the shown frame's quad; trimmed at pin_hit and to on-lane/gutter zones
    # raw points that read on or beside the lane only (185121 holds 3 false blobs at the frame top while the ball is
    # out of frame at f299-306; they have no sane board)
    bds = tr.get('boards') or {}
    ok_f = {f for f, p in td.items() if f <= pin and p['zone'] in ('lane', 'gutter_r', 'gutter_l')}
    raw = [(int(p['x']), int(p['y'])) for p in tr['frames'] if p['f'] in ok_f]
    if len(raw) > 1:
        cv2.polylines(im, [np.array(raw, np.int32)], False, (0, 140, 255), 2)
    if q:
        pts = []
        for f in sorted(td):
            p = td[f]
            if f > pin or p['zone'] not in ('lane', 'gutter_r', 'gutter_l'):
                continue
            ip = LG.image_point(q, p['board'], p['ft'], m['a'], m['b'])
            if ip is not None:
                pts.append((int(ip[0]), int(ip[1])))
        if len(pts) > 1:
            cv2.polylines(im, [np.array(pts, np.int32)], False, (60, 220, 60), 4)
        poly = np.array([q['fl_l'], q['pd_l'], q['pd_r'], q['fl_r']], np.int32)
        cv2.polylines(im, [poly], True, (255, 255, 0), 3)
        py = LG.pin_row(q)
        xl, xr = LG.edge_x(q['fl_l'], q['pd_l'], py), LG.edge_x(q['fl_r'], q['pd_r'], py)
        cv2.line(im, (int(xl), int(py)), (int(xr), int(py)), (255, 0, 255), 2)
        pf = tr.get('path_fit') or {}
        if pf.get('board_at_60ft') is not None:
            bx = xr + (pf['board_at_60ft'] - 1.0) / 38.0 * (xl - xr)
            cv2.drawMarker(im, (int(bx), int(py)), (255, 0, 255), cv2.MARKER_TRIANGLE_DOWN, 24, 3)
        re = q.get('row_edges')
        if re:
            for xx in (re['xl'], re['xr']):
                cv2.line(im, (int(xx), int(re['y']) - 12), (int(xx), int(re['y']) + 12), (0, 0, 255), 2)
    for p in tr['frames']:
        if p['f'] in ok_f:
            cv2.circle(im, (int(p['x']), int(p['y'])), max(2, int(p['r'] or 3)), (0, 140, 255), 1)
    pf = tr.get('path_fit') or {}
    srcs = tr['meta'].get('lane_sources', {})
    txt = [f"{METHOD}/{tr['meta']['lane_variant']} {tr['stem']} f{f_show} (pin_hit-4)",
           f"board at pin row {pf.get('board_at_60ft')}  fit {pf.get('kind')}  min {pf.get('min_board')} @ {pf.get('min_board_ft')} ft",
           f"lane frames {srcs}  fallback {tr['meta'].get('fallback_used')}  points {len(tr['frames'])}",
           'orange = raw track, green = track warped into this frame, cyan = lane used here, magenta = pin row + entry']
    for i, t in enumerate(txt):
        cv2.putText(im, t, (16, 50 + 44 * i), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 0), 6)
        cv2.putText(im, t, (16, 50 + 44 * i), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 2)
    im = cv2.resize(im, (im.shape[1] // 2, im.shape[0] // 2))
    # top-down panel: board across (39 left .. 1 right), ft up (foul line bottom, pins top)
    H = im.shape[0]
    W = 220
    pad = 40
    panel = np.full((H, W, 3), (40, 40, 40), np.uint8)
    lane_w = W - 2 * pad
    lane_h = H - 2 * pad
    cv2.rectangle(panel, (pad, pad), (pad + lane_w, pad + lane_h), (70, 160, 215), -1)
    X = lambda bd: int(pad + lane_w * (39 - bd) / 38)  # noqa: E731
    Y = lambda ft: int(pad + lane_h * (1 - ft / 60))   # noqa: E731
    for bd in (1, 10, 20, 30, 39):
        cv2.putText(panel, str(bd), (X(bd) - 8, pad - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (220, 220, 220), 1)
    for ft in (0, 15, 30, 45, 60):
        cv2.putText(panel, f'{ft}ft', (2, Y(ft) + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (220, 220, 220), 1)
    for bd in (5, 10, 15, 20, 25, 30, 35):
        cv2.drawMarker(panel, (X(1 + (bd - 0.5) * 38 / 39), Y(15)), (40, 40, 40), cv2.MARKER_TRIANGLE_UP, 7, 1)
    cv2.circle(panel, (X(20), Y(60)), 4, (255, 255, 255), -1)
    for f in sorted(td):
        p = td[f]
        if f <= pin and p['zone'] in ('lane', 'gutter_r', 'gutter_l'):
            cv2.circle(panel, (X(min(max(p['board'], -1), 41)), Y(min(max(p['ft'], 0), 61))), 2, (150, 40, 150), -1)
    bf = pf.get('boards_by_frame') or {}
    line = [(X(b), Y(td[int(f)]['ft'])) for f, b in sorted(bf.items(), key=lambda kv: int(kv[0])) if int(f) in td]
    if len(line) > 1:
        cv2.polylines(panel, [np.array(line, np.int32)], False, (0, 0, 255), 2)
    if pf.get('board_at_60ft') is not None:
        cv2.drawMarker(panel, (X(pf['board_at_60ft']), Y(60)), (0, 0, 255), cv2.MARKER_TRIANGLE_DOWN, 12, 2)
        cv2.putText(panel, f"b{pf['board_at_60ft']:.1f}", (6, H - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.imwrite(out_path, np.hstack([im, panel]), [cv2.IMWRITE_JPEG_QUALITY, 85])


# ---------------------------------------------------------------- main
def run(stem, args, log):
    t_start = time.time()
    cut = load_cut(stem)
    out_dir = args.out_dir or EXP
    os.makedirs(os.path.join(out_dir, 'tracks'), exist_ok=True)
    os.makedirs(os.path.join(out_dir, 'overlays'), exist_ok=True)
    out = os.path.join(out_dir, 'tracks', f'{stem}.json')
    if not cut.get('cut_path'):
        tr = {'stem': stem, 'method': METHOD, 'stage': 'both', 'frames': [], 'lane': {}, 'boards': {}, 'final_board': None,
              'release_frame': None, 'pin_hit_frame': None, 'meta': {'note': 'no cut: no throw', 'wall_s': 0.0}}
        json.dump(tr, open(out, 'w'), indent=1)
        log('no cut; empty track written')
        return tr
    off = cut['cut_start']
    rel, pin = cut['release_frame'], cut['pin_hit_frame']
    frames = read_frames(cut['cut_path'])
    balls, ball_src = ball_stage(stem, cut, args.ball, log)
    balls = [b for b in balls if off <= b['f'] <= cut['cut_end']]
    sam = sam_quads(stem) if args.lane in ('sam', 'auto') else {}
    t_lane = time.time()
    quads, sources, prev_mask, edge_info = {}, {}, None, {}
    n_edge_fail = 0
    for b in balls:
        f = b['f']
        q = None
        if f in sam:
            q = dict(sam[f], src='sam')
        elif args.lane in ('edge', 'auto'):
            q, prev_mask, info = edge_quad(frames[f - off], prev_mask, b, args.refine)
            if q is None:
                n_edge_fail += 1
                edge_info[f] = info.get('why')
        if q is not None:
            quads[f] = q
            sources[q['src']] = sources.get(q['src'], 0) + 1
    lane_s = time.time() - t_lane
    boards, boards_c, samples = {}, {}, []
    for b in balls:
        q = quads.get(b['f'])
        if q is None:
            continue
        bd = board_from_quad(q, b['x'], b['y'])
        if bd is not None and math.isfinite(bd):
            boards[str(b['f'])] = round(bd, 2)
        bc = LG.lane_point(q, b['x'], b['y'] + (b['r'] or 0))[0]
        if bc is not None and math.isfinite(bc):
            boards_c[str(b['f'])] = round(bc, 2)
        if rel <= b['f'] <= pin and depth_ok(q):
            s = LG.depth_ratio(q, b['y'])
            if s is not None and s <= 1.6 and bd is not None and 0.5 <= bd <= 39.5:
                samples.append((b['f'], s))
    boards_raw = dict(boards)
    if args.smooth and args.smooth > 1:
        # per-frame boards, de-jittered: rolling median over --smooth consecutive track frames (the lane fit jitters
        # +-8 px frame to frame at the far end, 1-2.5 boards; the raw series is kept in boards_raw)
        fs = sorted(int(k) for k in boards_raw)
        h = args.smooth // 2
        for i, f in enumerate(fs):
            win = [boards_raw[str(g)] for g in fs[max(0, i - h):i + h + 1] if abs(g - f) <= h]
            boards[str(f)] = round(float(statistics.median(win)), 2)
    # ft: the edge quad's pd row is the wood-mask top, 0-15 px below the pin bases (185331: 562 vs 549), so the
    # engine's s = (pd - vp)/(y - vp) passes 1 before the pins and ft overshoots (implied_pin 342 vs 358). Rescale s so
    # the ball at pin_hit (cuts.json, an input) sits at s = 1, then fit release-at-foul-line + constant speed as loop 1.
    s_at_pin = [LG.depth_ratio(quads[b['f']], b['y']) for b in balls
                if b['f'] in quads and abs(b['f'] - pin) <= 1 and depth_ok(quads[b['f']])]
    s_at_pin = [v for v in s_at_pin if v is not None and 0.6 <= v <= 1.6]
    s_pin = float(statistics.median(s_at_pin)) if s_at_pin else 1.0
    model = LG.fit_ft_model([(f, s / s_pin) for f, s in samples], rel)
    model = dict(model, a_fit=model['a'], a=round(model['a'] / s_pin, 3), s_pin=round(s_pin, 4),
                 note='ft = a * s + b with s rescaled so the ball at pin_hit reads 60 ft (a = a_fit / s_pin)')
    td = []
    for b in balls:
        q = quads.get(b['f'])
        if q is None or not depth_ok(q):
            continue
        board, ft = LG.lane_point(q, b['x'], b['y'], model['a'], model['b'])
        bd = boards.get(str(b['f']), board)
        if bd is None or ft is None:
            continue
        on = bool(0.5 <= bd <= 39.5 and 0.0 <= ft <= 60.5)
        zone = ('behind_foul' if ft < 0 else 'past_pins' if ft > 60.5 else 'gutter_r' if bd < 0.5
                else 'gutter_l' if bd > 39.5 else 'lane')
        td.append({'f': b['f'], 'board': round(bd, 2), 'ft': round(ft, 2), 'on_lane': on, 'zone': zone})
    ft_of = {p['f']: p['ft'] for p in td}
    series = {int(k): v for k, v in boards.items()}
    pf = fit_path(series, rel, pin, lambda f: ft_of.get(int(round(f))))
    fallback_used = sorted({s for s in sources if s != 'sam'}) if args.lane == 'auto' else []
    meta = {'device': args.device, 'ball_stage': ball_src, 'lane_variant': args.lane, 'refine': bool(args.refine),
            'smooth': int(args.smooth or 0),
            'lane_sources': sources, 'edge_fit_failures': n_edge_fail, 'edge_fail_reasons': edge_info,
            'fallback_used': bool(fallback_used and args.lane == 'auto' and not sam),
            'sam_quads_available': len(sam), 'lane_s': round(lane_s, 1),
            'wall_s': round(time.time() - t_start, 1),
            'wall_note': 'wall_s covers reading the cut, the stored ball track and the per-frame lane stage only; '
                         'the loop-1 appearance-prior tracker (~1 s + 8-10 s scan) and, for the sam variant, the loop-1 '
                         'engine SAM lane pass (43-195 s) are read from disk, not re-run',
            'release_source': 'cuts.json', 'pin_hit_source': 'cuts.json', 'cut_start': off,
            'board_row': 'ball centre (dev truth convention); boards_contact = y + r'}
    tr = {'stem': stem, 'method': f'{METHOD}/{args.lane}{"+refine" if args.refine else ""}{f"+smooth{args.smooth}" if args.smooth and args.smooth > 1 else ""}', 'stage': 'both',
          'frames': [{'f': b['f'], 'x': round(b['x'], 1), 'y': round(b['y'], 1), 'r': round(b['r'], 1), 'conf': b.get('conf'),
                      'src': b.get('src')} for b in balls],
          'lane': {str(f): {k: v for k, v in q.items() if k != 'row_edges'} | ({'row_edges': q['row_edges']} if 'row_edges' in q else {})
                   for f, q in quads.items()},
          'boards': boards, 'boards_raw': boards_raw, 'boards_contact': boards_c,
          'final_board': None if pf.get('board_at_60ft') is None else round(pf['board_at_60ft'], 1),
          'release_frame': rel, 'pin_hit_frame': pin, 'lane_top_down': td, 'lane_top_down_model': model,
          'path_fit': pf, 'meta': meta}
    json.dump(tr, open(out, 'w'), indent=1)
    draw_overlay(frames, cut, tr, os.path.join(out_dir, 'overlays', f'final__{stem}.jpg'), quads)
    log(f'wrote {out}: lane {sources} (edge failures {n_edge_fail}), boards {len(boards)}, fit {pf.get("kind")} '
        f'entry {pf.get("board_at_60ft")} min {pf.get("min_board")} rms {pf.get("residual_rms_boards")}, '
        f'ft model {model.get("kind")} a={model.get("a")} implied_pin {model.get("implied_pin_frame")}, wall {meta["wall_s"]}s')
    return tr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stem')
    ap.add_argument('--device', default='mps')
    ap.add_argument('--lane', default='auto', choices=['auto', 'sam', 'edge'])
    ap.add_argument('--refine', action='store_true')
    ap.add_argument('--smooth', type=int, default=0, help='rolling-median window (frames) over the per-frame boards; 0/1 = raw')
    ap.add_argument('--ball', default='file', choices=['file', 'rerun'])
    ap.add_argument('--out-dir', default=None)
    args = ap.parse_args()
    run(args.stem, args, lambda *a, **k: print(*a, **k, flush=True))


if __name__ == '__main__':
    main()
