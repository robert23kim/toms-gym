"""pin-anchored-geometry (loop 2, stage: lane). Per-frame lane geometry measured in the frame itself.

usage: run.py <stem> [--device mps|cpu] [--debug]

Input: the loop-1 sam2-video track (ball points unchanged) and its carried quads as PRIORS only.
Per frame: both lane edges are re-measured as straight lines on the wood/gutter transition (grey + Lab b*
signed gradient, band around the prior, ball rows masked, 3-sigma line fit, then a local refit around the ball
row); the pin-base row is measured on the headpin column (white map); the board is read from the measured
edges at the ball CENTRE row (the truth convention). Entry = board at the frame where the ball centre reaches the
measured pin-base row (no trailing median). Writes tracks/<stem>.json, overlays/final__<stem>.jpg.
--device is accepted for the harness and ignored (cv2/numpy only, no torch).
"""
import argparse, json, os, sys, time
import cv2, numpy as np

L1 = '/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking'
L2 = '/Users/toka/code/toms_gym/docs/research/2026-11-07-glasses-pov-hook'
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, L1)
from lane_geom import lane_point, image_point, fit_ft_model, depth_ratio, vanishing_point  # noqa: E402

METHOD = 'pin-anchored-geometry'
N_ROWS = 56
PIN_RULER_BOARDS = {7: 36.5, 4: 31.0, 2: 25.5, 1: 20.0, 3: 14.5, 6: 9.0, 10: 3.5}  # rule book, physical boards


def ex(p, q, y):
    return p[0] + (q[0] - p[0]) * (y - p[1]) / (q[1] - p[1])


def quad_line(q, side):
    """(a, b): x = a*y + b of the carried quad edge."""
    p, r = q['fl_' + side], q['pd_' + side]
    a = (r[0] - p[0]) / (r[1] - p[1])
    return a, p[0] - a * p[1]


def robust_line(ys, xs, min_sig=2.5, rounds=3):
    ys, xs = np.asarray(ys, float), np.asarray(xs, float)
    keep = np.ones(len(ys), bool)
    c = None
    for _ in range(rounds):
        if keep.sum() < 3:
            return None
        c = np.polyfit(ys[keep], xs[keep], 1)
        res = xs - np.polyval(c, ys)
        s = max(np.std(res[keep]), min_sig / 3)
        keep = np.abs(res) < max(3 * s, min_sig)
    if keep.sum() < 3:
        return None
    c = np.polyfit(ys[keep], xs[keep], 1)
    res = xs[keep] - np.polyval(c, ys[keep])
    return {'a': float(c[0]), 'b': float(c[1]), 'n': int(keep.sum()), 'rms': float(np.sqrt(np.mean(res ** 2))),
            'ymin': float(ys[keep].min()), 'ymax': float(ys[keep].max())}


class FrameSignals:
    def __init__(self, img):
        self.img = img
        g = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32), (5, 5), 0)
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        b = cv2.GaussianBlur(lab[..., 2].astype(np.float32) - 128.0, (5, 5), 0)
        sg = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=5)
        sb = cv2.Sobel(b, cv2.CV_32F, 1, 0, ksize=5)
        k = np.ones((7, 1), np.float32) / 7
        sg = cv2.filter2D(sg, -1, k)
        sb = cv2.filter2D(sb, -1, k)
        ng = np.percentile(np.abs(sg), 97) + 1e-6
        nb = np.percentile(np.abs(sb), 97) + 1e-6
        self.score = sg / ng + 1.5 * sb / nb  # + where darker/greyer -> brighter/yellower going right
        self.H, self.W = g.shape
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        self.white = cv2.GaussianBlur(np.clip(hsv[..., 2].astype(np.float32) - hsv[..., 1].astype(np.float32), 0, 255) / 255.0, (3, 3), 0)


def measure_edge(sig, side, prior, y_top, y_bot, ball, band_fn, min_strength=0.35, n_rows=N_ROWS):
    """prior: (a, b) x = a*y + b. Returns (fit or None, points). sign + for the left edge (gutter -> wood), - right."""
    sign = 1.0 if side == 'l' else -1.0
    rows = np.linspace(y_top, y_bot, n_rows)
    bx, by, br = ball
    pts = []
    for y in rows:
        yi = int(round(y))
        if yi < 1 or yi >= sig.H - 1:
            continue
        xc = prior[0] * y + prior[1]
        if xc < 4 or xc > sig.W - 5:
            continue  # the edge has left the frame (near end)
        if abs(y - by) < 1.4 * br + 6 and abs(xc - bx) < 2.4 * br + 12:
            continue  # the ball (purple -> wood) mimics an edge
        w = band_fn(y)
        a, b = int(max(0, xc - w)), int(min(sig.W - 1, xc + w))
        if b - a < 4:
            continue
        prof = sign * sig.score[yi, a:b]
        i = int(np.argmax(prof))
        if prof[i] < min_strength:
            continue
        pts.append((y, a + i))
    if len(pts) < 6:
        return None, pts
    return robust_line([p[0] for p in pts], [p[1] for p in pts]), pts


def angle_scan(sig, side, prior, y_top, y_bot, ball, w_pin, da=0.6, step=0.004):
    """Pass 0: the edge line anchored near the pin row (x_a scanned over +-0.1 w_pin), slope scanned over
    prior +-da; score = sum of the clipped signed gradient along the line (a 1-D Hough). Returns (a, b)."""
    sign = 1.0 if side == 'l' else -1.0
    y_a = y_top + 4
    x_a0 = prior[0] * y_a + prior[1]
    rows = np.arange(int(y_a), int(y_bot), 6)
    bx, by, br = ball
    rows = rows[~((np.abs(rows - by) < 1.4 * br + 6))] if abs(x_a0 - bx) < 4 * br + 400 else rows
    if len(rows) < 6:
        return prior
    xa = x_a0 + np.arange(-max(6.0, 0.12 * w_pin), max(6.0, 0.12 * w_pin) + 0.1, 2.0)
    aa = prior[0] + np.arange(-da, da + 1e-9, step)
    dy = (rows - y_a).astype(np.float32)
    best, best_ab = -1e9, prior
    sc = sig.score
    W = sig.W
    for x0 in xa:
        xs = x0 + aa[:, None] * dy[None, :]  # (A, R)
        xi = np.clip(np.round(xs).astype(int), 0, W - 1)
        vals = sign * sc[rows[None, :], xi]
        vals = np.where((xs < 4) | (xs > W - 5), 0.0, vals)
        # rows where the ball sits near the candidate line contribute nothing
        near = (np.abs(rows[None, :] - by) < 1.4 * br + 6) & (np.abs(xs - bx) < 2.4 * br + 12)
        vals = np.where(near, 0.0, np.clip(vals, 0, 2.0))
        tot = vals.sum(1)
        j = int(np.argmax(tot))
        if tot[j] > best:
            best, best_ab = float(tot[j]), (float(aa[j]), float(x0 - aa[j] * y_a))
    return best_ab


def width_at(ql, qr, y):
    return (qr[0] * y + qr[1]) - (ql[0] * y + ql[1])


def line_vp(l, r):
    """y of the intersection of x = a*y + b lines; None when parallel."""
    if abs(l[0] - r[0]) < 1e-9:
        return None
    return (r[1] - l[1]) / (l[0] - r[0])


def measure_lane(sig, q, ball, carried, pin_y_prior, degenerate):
    """Both edges as straight lines in this frame. carried: {side: (a, b)} = the neighbouring frame's measured
    line translated by the camera shift (phase correlation); used as the prior when present, else the quad."""
    out = {}
    H = sig.H
    ql, qr = quad_line(q, 'l'), quad_line(q, 'r')
    pri = {'l': carried.get('l') or ql, 'r': carried.get('r') or qr}
    src = {'l': 'carried' if carried.get('l') else 'quad', 'r': 'carried' if carried.get('r') else 'quad'}
    vpy = line_vp(pri['l'], pri['r'])
    y_top = max(2.0, pin_y_prior + 6)
    if vpy is not None:
        y_top = max(y_top, vpy + 0.03 * H) if not degenerate else max(2.0, vpy + 0.03 * H)
    elif degenerate:
        y_top = 2.0
    y_bot = H - 3.0
    wf = lambda y: abs((pri['r'][0] * y + pri['r'][1]) - (pri['l'][0] * y + pri['l'][1]))  # noqa: E731
    for side in ('l', 'r'):
        prior = pri[side]
        w_pin = wf(y_top)
        prior = angle_scan(sig, side, prior, y_top, y_bot, ball, w_pin)
        w_fn = lambda y: max(8.0, 0.08 * wf(y))  # noqa: E731
        fit, pts = measure_edge(sig, side, prior, y_top, y_bot, ball, w_fn)
        passes = 1
        if fit is not None:
            w2 = lambda y: max(6.0, 0.06 * wf(y))  # noqa: E731
            fit2, pts2 = measure_edge(sig, side, (fit['a'], fit['b']), y_top, y_bot, ball, w2)
            if fit2 is not None and fit2['n'] >= 8:
                fit, pts, passes = fit2, pts2, 2
        ok = fit is not None and fit['n'] >= 12 and fit['rms'] <= 3.5
        if not ok:
            out[side] = {'a': prior[0], 'b': prior[1], 'n': 0 if fit is None else fit['n'], 'rms': None if fit is None else fit['rms'],
                         'ok': False, 'src': 'prior_' + src[side]}
        else:
            out[side] = dict(fit, ok=True, src='measured', passes=passes, prior_src=src[side])
        by = ball[1]
        if ok:
            span = max(40.0, 1.2 * wf(by))
            w3 = lambda y: 5.0  # noqa: E731
            fit3, _ = measure_edge(sig, side, (out[side]['a'], out[side]['b']), max(y_top, by - span), min(y_bot, by + span), ball, w3, n_rows=40)
            if fit3 is not None and fit3['n'] >= 8 and fit3['rms'] <= 2.5:
                out[side]['local'] = fit3
    out['y_top'] = y_top
    return out


def pin_base_row(sig, xl_pin, xr_pin, pin_y_prior):
    """Lowest row of the headpin's white body in the lane-centre column window; None when nothing white is there."""
    w = xr_pin - xl_pin
    if w < 20:
        return None
    xc = 0.5 * (xl_pin + xr_pin)
    hw = max(2, int(0.025 * w))
    y0, y1 = int(max(0, pin_y_prior - 0.6 * w)), int(min(sig.H - 1, pin_y_prior + 0.35 * w))
    x0, x1 = int(max(0, xc - hw)), int(min(sig.W - 1, xc + hw + 1))
    if y1 - y0 < 10 or x1 - x0 < 2:
        return None
    prof = sig.white[y0:y1, x0:x1].mean(1)
    pmax = float(prof.max())
    if pmax < 0.45:
        return None
    on = prof >= 0.5 * pmax
    i = int(np.argmax(prof))
    j = i
    while j + 1 < len(on) and on[j + 1]:
        j += 1
    return float(y0 + j)


def pin_ruler(sig, xl_pin, xr_pin, pin_y, ball_x):
    """Pin columns (7 at 6-in spacing, bodies 5-35 % of the lane width above the base row) as a ruler at the pin row.
    Returns {'px_per_in', 'headpin_x', 'board', 'width_ratio' (41.5 in by the ruler / edge width), 'n_peaks'} or None."""
    w = xr_pin - xl_pin
    if w < 30:
        return None
    y0, y1 = int(max(0, pin_y - 0.40 * w)), int(max(0, pin_y - 0.06 * w))
    x0, x1 = int(max(0, xl_pin - 0.12 * w)), int(min(sig.W - 1, xr_pin + 0.12 * w))
    if y1 - y0 < 4 or x1 - x0 < 20:
        return None
    prof = sig.white[y0:y1, x0:x1].mean(0)
    prof = np.convolve(prof, np.ones(3) / 3.0, 'same')
    thr = 0.5 * prof.max()
    peaks = [i for i in range(1, len(prof) - 1) if prof[i] >= prof[i - 1] and prof[i] > prof[i + 1] and prof[i] > thr]
    if len(peaks) < 4:
        return None
    # expected spacing: 6 in = w_edge * 6 / 41.5 px (edge scale); search the ruler scale 0.7-1.3 of that
    cand = []
    sp0 = w * 6.0 / 41.5
    for sp in np.linspace(0.7 * sp0, 1.3 * sp0, 61):
        for ph in peaks:
            cols = ph + sp * np.arange(-6, 7)
            cols = cols[(cols >= 0) & (cols < len(prof))]
            score = sum(prof[int(round(c))] for c in cols if abs(c - min(peaks, key=lambda q: abs(q - c))) <= max(1.5, 0.15 * sp))
            cand.append((score, sp, ph))
    score, sp, ph = max(cand)
    # the headpin is the column nearest the lane centre; snap the 7-column comb to the peaks
    xc_edge = 0.5 * (xl_pin + xr_pin) - x0
    k = int(round((xc_edge - ph) / sp))
    head = ph + k * sp
    matched = [min(peaks, key=lambda q: abs(q - (head + sp * d))) for d in range(-3, 4)]
    good = [(d, m) for d, m in zip(range(-3, 4), matched) if abs(m - (head + sp * d)) <= max(1.5, 0.15 * sp)]
    if len(good) < 4:
        return None
    d = np.array([g[0] for g in good], float)
    m = np.array([g[1] for g in good], float)
    c = np.polyfit(d, m, 1)  # m = c0 * d + c1 ; c0 = px per 6 in
    px_in = c[0] / 6.0
    head_x = c[1] + x0
    if px_in <= 0:
        return None
    board = 20.0 - (ball_x - head_x) / (px_in * 41.5 / 38.0)
    return {'px_per_in': round(float(px_in), 3), 'headpin_x': round(float(head_x), 1), 'board': round(float(board), 2),
            'width_ratio_ruler_over_edge': round(float(41.5 * px_in / w), 3), 'n_peaks': len(good), 'centre_offset_px': round(float(head_x - 0.5 * (xl_pin + xr_pin)), 1)}


def lane_from_fits(fits, pin_y, H):
    yb = H - 3.0
    q = {'pd_l': [round(fits['l']['a'] * pin_y + fits['l']['b'], 1), round(pin_y, 1)],
         'pd_r': [round(fits['r']['a'] * pin_y + fits['r']['b'], 1), round(pin_y, 1)],
         'fl_l': [round(fits['l']['a'] * yb + fits['l']['b'], 1), yb], 'fl_r': [round(fits['r']['a'] * yb + fits['r']['b'], 1), yb],
         'fl_is_foul_line': False, 'pin_y': round(pin_y, 1)}
    return q


def edge_x_at(fit, y):
    loc = fit.get('local')
    if loc:
        return loc['a'] * y + loc['b']
    return fit['a'] * y + fit['b']


def run(stem, debug=False):
    t0 = time.time()
    cuts = {c['stem']: c for c in json.load(open(L1 + '/work/cuts/cuts.json'))}
    cut = cuts[stem]
    tr = json.load(open(f'{L1}/results/tracks/{stem}.json'))
    off = cut['cut_start']
    rel, pin = cut['release_frame'], cut['pin_hit_frame']
    pts = {p['f']: p for p in tr['frames'] if p.get('x') is not None}
    quads = tr.get('lane') or {}
    truth = None
    if debug:
        tp = f'{L2}/truth/{stem}.json'
        truth = {p['f']: p for p in json.load(open(tp))['path']} if os.path.exists(tp) else None
    cap = cv2.VideoCapture(cut['cut_path'])
    k = 0
    lane, boards, meas = {}, {}, {}
    pin_offsets = []
    ref_img = None
    f_ref = pin - 4
    n_meas = n_prior = n_untrusted = 0
    untrusted = {}
    frames_img = {}
    while True:
        ok, img = cap.read()
        if not ok:
            break
        f = off + k
        k += 1
        if f == f_ref:
            ref_img = img.copy()
        if rel <= f <= pin + 4 and f in pts and str(f) in quads:
            frames_img[f] = img
    cap.release()
    order = sorted(frames_img, reverse=True)  # far end first: the quads are good there, the near end is carried
    prev_small, prev_fits, prev_f = None, None, None
    win = None
    last_ok = {}
    for f in order:
        img = frames_img[f]
        p, q = pts[f], quads[str(f)]
        sig = FrameSignals(img)
        small = cv2.resize(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA).astype(np.float32)
        if win is None:
            win = cv2.createHanningWindow(small.shape[::-1], cv2.CV_32F)
        carried = {}
        shift = None
        if prev_small is not None and prev_fits is not None:
            (dx, dy), resp = cv2.phaseCorrelate(prev_small, small, win)
            dx, dy = 4.0 * dx, 4.0 * dy
            shift = (round(dx, 1), round(dy, 1), round(float(resp), 3))
            if resp > 0.05:
                for side in ('l', 'r'):
                    if prev_fits[side]['ok']:
                        last_ok[side] = (prev_fits[side]['a'], prev_fits[side]['b'])
                    elif side in last_ok:
                        pass  # keep the older line, already shifted into prev's frame below
                    if side in last_ok:
                        a, b = last_ok[side]
                        last_ok[side] = (a, b - a * dy + dx)
                        carried[side] = last_ok[side]
            else:
                last_ok.clear()
        pin_y_prior = float(q.get('pin_y') if q.get('pin_y') is not None else 0.5 * (q['pd_l'][1] + q['pd_r'][1]))
        pin_y_prior_m = pin_y_prior + (float(np.median(pin_offsets[-5:])) if pin_offsets else 0.0)
        ball = (float(p['x']), float(p['y']), float(p.get('r') or 10.0))
        qw = ex(q['fl_r'], q['pd_r'], ball[1]) - ex(q['fl_l'], q['pd_l'], ball[1])
        degenerate = ball[2] >= 25.0 and ((ball[1] - pin_y_prior) < 2.0 * ball[2] or qw < 4.0 * ball[2])  # near-end frames only: the camera looks down, the carried quad is meaningless
        fits = measure_lane(sig, q, ball, carried, pin_y_prior_m, degenerate)
        both = fits['l']['ok'] and fits['r']['ok']
        n_meas += both
        n_prior += not both
        xl_p = fits['l']['a'] * pin_y_prior_m + fits['l']['b']
        xr_p = fits['r']['a'] * pin_y_prior_m + fits['r']['b']
        pin_meas = pin_base_row(sig, xl_p, xr_p, pin_y_prior_m) if (f >= pin - 24 and not degenerate) else None
        if pin_meas is not None and abs(pin_meas - pin_y_prior) < 0.5 * (xr_p - xl_p):
            pin_offsets.append(pin_meas - pin_y_prior)
            pin_y = pin_meas
        else:
            pin_y = pin_y_prior_m
        xl = edge_x_at(fits['l'], ball[1])
        xr = edge_x_at(fits['r'], ball[1])
        ruler = pin_ruler(sig, xl_p, xr_p, pin_y, ball[0]) if (pin - 8 <= f <= pin + 1 and not degenerate) else None
        prev_small, prev_fits, prev_f = small, fits, f
        if abs(xl - xr) < 10:
            continue
        w_ball = xr - xl
        trusted = both and (4.5 * ball[2] <= w_ball <= 14.0 * ball[2])
        if not trusted:
            n_untrusted += 1
            untrusted[str(f)] = {'w': round(w_ball, 1), 'r': ball[2], 'l_ok': fits['l']['ok'], 'r_ok': fits['r']['ok']}
            continue
        board = (ball[0] - xr) / (xl - xr) * 38.0 + 1.0
        boards[str(f)] = round(float(board), 2)
        lane[str(f)] = lane_from_fits(fits, pin_y, sig.H)
        meas[f] = {'xl': xl, 'xr': xr, 'pin_y': pin_y, 'pin_meas': pin_meas, 'l_ok': fits['l']['ok'], 'r_ok': fits['r']['ok'],
                   'l_rms': fits['l'].get('rms'), 'r_rms': fits['r'].get('rms'), 'l_n': fits['l'].get('n'), 'r_n': fits['r'].get('n'),
                   'l_local': bool(fits['l'].get('local')), 'r_local': bool(fits['r'].get('local')), 'l_src': fits['l']['src'], 'r_src': fits['r']['src'],
                   'quad_xl': ex(q['fl_l'], q['pd_l'], ball[1]), 'quad_xr': ex(q['fl_r'], q['pd_r'], ball[1]), 'y': ball[1],
                   'degenerate_quad': bool(degenerate), 'shift': shift, 'y_top': round(fits['y_top'], 1), 'pin_ruler': ruler}
        if debug and truth and f in truth:
            t = truth[f]
            tl, trr = t.get('left_x'), t.get('right_x')
            print(f'f{f} y{ball[1]:.0f} L meas {xl:.1f} truth {tl} quad {meas[f]["quad_xl"]:.1f} | R meas {xr:.1f} truth {trr} quad {meas[f]["quad_xr"]:.1f}'
                  f' | board {board:.2f} truth {t.get("board")} | pin_y {pin_y:.0f} prior {pin_y_prior:.0f} meas {pin_meas}'
                  f' | l {fits["l"]["src"]} n{fits["l"].get("n")} rms{fits["l"].get("rms") and round(fits["l"]["rms"], 2)} r {fits["r"]["src"]} n{fits["r"].get("n")} rms{fits["r"].get("rms") and round(fits["r"]["rms"], 2)}'
                  f' loc {int(meas[f]["l_local"])}{int(meas[f]["r_local"])} deg {int(degenerate)} shift {shift} ytop {fits["y_top"]:.0f}')
    frames_img.clear()
    fs = sorted(meas)
    # entry: the board at the pin-row frame = pin_hit_frame (cuts.json: ball at the rack front), evaluated as a local
    # linear fit over pin_hit-4..pin_hit+1 (no trailing median). The frame where the ball bottom reaches the measured
    # pin-base row is kept as a diagnostic: on a tilting camera the pixel comparison is not a lane-depth test.
    pin_row_frame = None
    for f in fs:
        if pin - 12 <= f <= pin + 3 and meas[f]['pin_meas'] is not None and meas[f]['y'] + float(pts[f].get('r') or 0.0) <= meas[f]['pin_meas'] + 0.5:
            pin_row_frame = f
            break
    entry_f, entry_src = (pin if str(pin) in boards else (fs[-1] if fs else None)), 'pin_hit_frame'
    entry = None
    if entry_f is not None:
        win = [(f, boards[str(f)]) for f in fs if entry_f - 4 <= f <= entry_f + 1]
        if len(win) >= 3:
            c = np.polyfit([w[0] for w in win], [w[1] for w in win], 1)
            entry = float(np.polyval(c, entry_f))
        else:
            entry = boards.get(str(entry_f))
    # smoothed series for the hook min (5-frame median), raw boards stay in boards{}
    ser = [(f, boards[str(f)]) for f in fs if f <= pin]
    sm = {}
    for i, (f, b) in enumerate(ser):
        w = [v for _, v in ser[max(0, i - 2):i + 3]]
        sm[f] = float(np.median(w))
    tail_lo = rel + 0.4 * (pin - rel)
    tail = [(f, b) for f, b in sm.items() if tail_lo <= f <= pin]
    min_f, min_b = (min(tail, key=lambda t: t[1]) if tail else (None, None))
    resid = [boards[str(f)] - sm[f] for f, _ in ser]
    # top-down
    tr2 = {'stem': stem, 'method': METHOD, 'stage': 'lane', 'frames': tr['frames'], 'lane': lane, 'boards': boards,
           'final_board': None if entry is None else round(entry, 2), 'release_frame': rel, 'pin_hit_frame': pin}
    samples = []
    for f in fs:
        if rel <= f <= pin:
            s = depth_ratio(lane[str(f)], meas[f]['y'])
            if s is not None and 0.5 <= boards[str(f)] <= 39.5 and not meas[f]['degenerate_quad']:
                samples.append((f, s))
    model = fit_ft_model(samples, rel)
    td = []
    for f in fs:
        b, ft = lane_point(lane[str(f)], pts[f]['x'], pts[f]['y'], model['a'], model['b'])
        if b is None or ft is None:
            continue
        on = 0.5 <= b <= 39.5 and 0 <= ft <= 60.5
        zone = 'behind_foul' if ft < 0 else 'past_pins' if ft > 60.5 else 'gutter_r' if b < 0.5 else 'gutter_l' if b > 39.5 else 'lane'
        td.append({'f': f, 'board': round(b, 2), 'ft': round(ft, 2), 'on_lane': on, 'zone': zone})
    tr2['lane_top_down'] = td
    tr2['lane_top_down_model'] = model
    ft_at = {e['f']: e['ft'] for e in td}
    ruler_entry = [meas[f]['pin_ruler'] for f in fs if entry_f is not None and entry_f - 2 <= f <= entry_f + 1 and meas[f].get('pin_ruler')]
    ruler_summary = None
    if ruler_entry:
        ruler_summary = {'board_mean': round(float(np.mean([r['board'] for r in ruler_entry])), 2), 'boards': [r['board'] for r in ruler_entry],
                         'width_ratio_mean': round(float(np.mean([r['width_ratio_ruler_over_edge'] for r in ruler_entry])), 3),
                         'centre_offset_px': [r['centre_offset_px'] for r in ruler_entry], 'n': len(ruler_entry)}
    tr2['path_fit'] = {'kind': 'measured_edges_raw+5median', 'params': {'entry_frame': entry_f, 'entry_src': entry_src, 'entry_fit': 'linear over entry-4..entry+1', 'pin_row_frame_ball_bottom': pin_row_frame, 'pin_ruler_at_entry': ruler_summary},
                       'board_at_60ft': None if entry is None else round(entry, 2), 'min_board': None if min_b is None else round(min_b, 2),
                       'min_board_ft': None if min_f is None else ft_at.get(min_f), 'min_board_frame': min_f,
                       'residual_rms_boards': round(float(np.sqrt(np.mean(np.square(resid)))), 2) if resid else None, 'n_points': len(ser)}
    tr2['meta'] = {'built_on': 'L1/results/tracks sam2-video (ball points unchanged, quads as priors)', 'cut_start': off,
                   'frames_measured_both_edges': n_meas, 'frames_prior_fallback': n_prior, 'frames_untrusted_no_board': n_untrusted, 'untrusted': untrusted, 'width_gate': '4.5 r <= lane width at ball row <= 14 r and both edges measured', 'pin_row_offsets_px': [round(v, 1) for v in pin_offsets],
                   'entry_frame': entry_f, 'entry_source': entry_src, 'pin_row_frame_ball_bottom': pin_row_frame, 'wall_s': round(time.time() - t0, 1), 'device': 'cpu (cv2 only)',
                   'per_frame': {str(f): {k: (round(v, 2) if isinstance(v, float) else v) for k, v in m.items()} for f, m in meas.items()}}
    os.makedirs(HERE + '/tracks', exist_ok=True)
    os.makedirs(HERE + '/overlays', exist_ok=True)
    with open(f'{HERE}/tracks/{stem}.json', 'w') as fh:
        json.dump(tr2, fh, indent=1)
    if ref_img is not None and str(f_ref) in lane:
        overlay(ref_img, f_ref, tr2, pts, meas, f'{HERE}/overlays/final__{stem}.jpg')
    print(f'{stem}: boards {len(boards)}, measured both {n_meas}, prior {n_prior}, entry {entry} at f{entry_f} ({entry_src}), '
          f'min {min_b} f{min_f}, model {model.get("kind")} a={model.get("a")} implied_pin {model.get("implied_pin_frame")}, wall {tr2["meta"]["wall_s"]}s')
    return tr2


def overlay(img, f_ref, tr, pts, meas, out_path):
    q = tr['lane'][str(f_ref)]
    m = tr['lane_top_down_model']
    vis = img.copy()
    H, W = vis.shape[:2]
    # measured edge lines in this frame
    for side, col in (('l', (255, 255, 0)), ('r', (255, 255, 0))):
        p, r = q['fl_' + side], q['pd_' + side]
        cv2.line(vis, (int(p[0]), int(p[1])), (int(r[0]), int(r[1])), col, 2)
    cv2.line(vis, (int(q['pd_l'][0]) - 40, int(q['pin_y'])), (int(q['pd_r'][0]) + 40, int(q['pin_y'])), (255, 0, 255), 2)
    poly = []
    ft_mono, run_max = {}, -1e9
    pf_meta = tr['meta']['per_frame']
    for e in sorted(tr['lane_top_down'], key=lambda e: e['f']):
        if pf_meta.get(str(e['f']), {}).get('degenerate_quad') or e['ft'] > 63:
            continue  # the near-end frames with a bogus carried pin row have no usable ft
        run_max = max(run_max, e['ft'])
        ft_mono[e['f']] = run_max  # drawing only: the ball does not roll backwards
    for e in tr['lane_top_down']:
        if e['zone'] not in ('lane', 'gutter_r', 'gutter_l') or e['f'] > tr['pin_hit_frame'] or e['f'] not in ft_mono:
            continue
        ip = image_point(q, e['board'], ft_mono[e['f']], m['a'], m['b'])
        if ip is None:
            continue
        poly.append((int(ip[0]), int(ip[1])))
    if len(poly) > 1:
        cv2.polylines(vis, [np.array(poly, np.int32)], False, (0, 255, 0), 3)
    p = pts.get(f_ref)
    if p:
        cv2.circle(vis, (int(p['x']), int(p['y'])), int(max(4, p.get('r') or 6)), (0, 140, 255), 2)
    pf = tr['path_fit']
    txt = [f'{METHOD} {tr["stem"]} f{f_ref}', f'entry board {pf["board_at_60ft"]} at f{pf["params"]["entry_frame"]} ({pf["params"]["entry_src"]})',
           f'min board {pf["min_board"]} at f{pf["min_board_frame"]}  measured {tr["meta"]["frames_measured_both_edges"]} / prior {tr["meta"]["frames_prior_fallback"]}']
    for i, t in enumerate(txt):
        cv2.putText(vis, t, (10, 30 + 30 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 4)
        cv2.putText(vis, t, (10, 30 + 30 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    # far-end inset (2x) around the ball
    if p:
        r = int(max(20, 6 * (p.get('r') or 10)))
        x0, y0 = int(max(0, p['x'] - 2 * r)), int(max(0, p['y'] - r))
        x1, y1 = int(min(W, p['x'] + 2 * r)), int(min(H, p['y'] + r))
        inset = cv2.resize(vis[y0:y1, x0:x1], None, fx=2, fy=2)
        ih, iw = inset.shape[:2]
        if ih < H - 120 and iw < W:
            vis[H - ih - 10:H - 10, 10:10 + iw] = inset
            cv2.rectangle(vis, (10, H - ih - 10), (10 + iw, H - 10), (255, 255, 255), 1)
    # top-down panel
    PW, PH = 300, H
    panel = np.full((PH, PW, 3), (40, 120, 180), np.uint8)
    lx0, lx1 = 40, PW - 40
    ty = lambda ft: int(PH - 60 - (PH - 120) * ft / 63.0)  # noqa: E731
    tx = lambda b: int(lx0 + (lx1 - lx0) * (39 - b) / 38)  # noqa: E731
    cv2.rectangle(panel, (lx0, ty(63)), (lx1, ty(0)), (90, 170, 220), -1)
    for ft in (0, 15, 30, 45, 60):
        cv2.line(panel, (lx0, ty(ft)), (lx1, ty(ft)), (60, 60, 60), 1)
        cv2.putText(panel, f'{ft}ft', (2, ty(ft) + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
    for b in (5.4, 10.3, 15.1, 20.0, 24.9, 29.7, 34.6):
        cv2.drawMarker(panel, (tx(b), ty(15)), (0, 0, 0), cv2.MARKER_TRIANGLE_UP, 8, 1)
    for b in (20.0, 14.5, 25.5, 9.0, 31.0, 3.5, 36.5):
        cv2.circle(panel, (tx(b), ty(60 + (0 if b == 20 else 0.87 if b in (14.5, 25.5) else 1.73 if b in (9.0, 31.0) else 2.6))), 4, (255, 255, 255), -1)
    tp = []
    for e in tr['lane_top_down']:
        if e['f'] > tr['pin_hit_frame'] or e['zone'] == 'behind_foul' or e['f'] not in ft_mono:
            continue
        b = min(40.5, max(-1.5, e['board']))
        tp.append((tx(b), ty(min(63, ft_mono[e['f']]))))
    if len(tp) > 1:
        cv2.polylines(panel, [np.array(tp, np.int32)], False, (160, 0, 160), 3)
    if pf['board_at_60ft'] is not None:
        cv2.circle(panel, (tx(pf['board_at_60ft']), ty(60)), 7, (0, 255, 0), 2)
    cv2.putText(panel, f'b{pf["board_at_60ft"]}', (10, PH - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
    cv2.putText(panel, 'board vs ft (ft monotone for drawing)', (6, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 0), 1)
    for b in (1, 10, 20, 30, 39):
        cv2.putText(panel, str(b), (tx(b) - 8, ty(0) + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
    out = np.concatenate([vis, panel], 1)
    out = cv2.resize(out, None, fx=0.6, fy=0.6, interpolation=cv2.INTER_AREA)
    cv2.imwrite(out_path, out, [cv2.IMWRITE_JPEG_QUALITY, 85])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stem')
    ap.add_argument('--device', default='mps')
    ap.add_argument('--debug', action='store_true')
    a = ap.parse_args()
    run(a.stem, debug=a.debug)


if __name__ == '__main__':
    main()
