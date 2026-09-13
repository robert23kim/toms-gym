"""Physical lane landmarks: geometry, detectors, homography fitting.

Lane coordinates are physical: x in inches from the LEFT edge (bowler's view,
board 39 side; board 1 is on the right), y in inches down-lane from the foul
line. The annotated quad's top edge is assumed to sit at the head-pin row
(60 ft) for the initial guess only; every fit re-estimates the far end.
"""
import math

import cv2
import numpy as np

import common as C

L = C.L
W_IN = C.LANE_WIDTH_IN          # 41.5
BOARD_IN = C.BOARD_IN           # 1.064
HEAD_IN = 60.0 * 12             # head-pin spot
ROW_IN = 12.0 * math.sqrt(3) / 2  # 10.39 in between pin rows
PIN_H_IN = 15.0                 # pin height
PIN_W_IN = 4.77                 # pin belly width
# pin -> (dx from lane centre in inches, row 0..3); row 0 = head pin
PIN_LAYOUT = {1: (0, 0), 2: (-6, 1), 3: (6, 1), 4: (-12, 2), 5: (0, 2), 6: (12, 2),
              7: (-18, 3), 8: (-6, 3), 9: (6, 3), 10: (18, 3)}


def board_x_in(board):
    """Centre of board `board` (1 = right edge, 39 = left edge) in inches from the left edge."""
    return W_IN - (board - 0.5) * BOARD_IN


def pin_bases_in():
    cx = W_IN / 2
    return {p: (cx + dx, HEAD_IN + row * ROW_IN) for p, (dx, row) in PIN_LAYOUT.items()}


def arrow_x_in():
    return {b: board_x_in(b) for b in C.ARROW_BOARDS}


# ---------------------------------------------------------------- homographies

def h_from_quad(corners, top_in=HEAD_IN):
    """image -> lane inches from four corners, top edge at top_in."""
    src = np.float32([corners["top_left"], corners["top_right"], corners["bottom_right"], corners["bottom_left"]])
    dst = np.float32([[0, top_in], [W_IN, top_in], [W_IN, 0], [0, 0]])
    return cv2.getPerspectiveTransform(src, dst)


def to_lane(H, pts):
    return cv2.perspectiveTransform(np.float32(pts).reshape(-1, 1, 2), H).reshape(-1, 2)


def to_image(H, pts):
    return cv2.perspectiveTransform(np.float32(pts).reshape(-1, 1, 2), np.linalg.inv(H)).reshape(-1, 2)


def boards_from_lane_x(x_in):
    """Engine / loop-1 board convention: left edge = 39.0, right edge = 1.0, linear."""
    return (W_IN - np.asarray(x_in, float)) / W_IN * 38.0 + 1.0


def score_h(stem, f, H, truth_corners=None):
    """Loop-1 metric for an image->lane-inches homography: boards of the ball
    path under H vs under the truth corners' homography. Adds the last-20 %
    (pin-end) tail of the path."""
    truth_corners = truth_corners or L.truth_corners(stem, f)
    pts = L.ball_points_on_ordered(stem, f)
    b_true, _ = C.gt.board_from_corners(truth_corners, pts)
    b_pred = boards_from_lane_x(to_lane(H, pts)[:, 0])
    diff = np.abs(b_pred - b_true)
    n = len(diff)
    tail = diff[int(0.8 * n):] if n >= 5 else diff
    return {"board_mae": round(float(diff.mean()), 2), "board_max": round(float(diff.max()), 2),
            "within_1": round(float((diff <= 1).mean() * 100), 1), "within_2": round(float((diff <= 2).mean() * 100), 1),
            "board_mae_last20": round(float(tail.mean()), 2)}


def corners_from_h(H, y_top, y_bot):
    """Corners of the lane edges (x=0 and x=W) under H, evaluated at image rows y_top / y_bot."""
    out = {}
    for name, x_in in (("left", 0.0), ("right", W_IN)):
        p = to_image(H, [[x_in, 0.0], [x_in, HEAD_IN]])
        (x0, y0), (x1, y1) = p
        a = (x1 - x0) / (y1 - y0); b = x0 - a * y0
        out[f"top_{name}"] = (a * y_top + b, y_top)
        out[f"bottom_{name}"] = (a * y_bot + b, y_bot)
    return out


def width_centre_at(H, y):
    """Lane width (px) and centre x at image row y under H (edge lines x=0, x=W)."""
    c = corners_from_h(H, y, y + 1)
    return c["top_right"][0] - c["top_left"][0], 0.5 * (c["top_right"][0] + c["top_left"][0])


# ---------------------------------------------------------------- white / dark maps

def white_map(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    w = np.clip(hsv[..., 2].astype(np.float32) - hsv[..., 1].astype(np.float32), 0, 255) / 255.0
    return cv2.GaussianBlur(w, (3, 3), 0)


def sample(mapf, pts):
    """Bilinear samples of a float map at (x, y) points; 0 outside."""
    h, w = mapf.shape
    pts = np.asarray(pts, np.float32).reshape(-1, 2)
    x = pts[:, 0]; y = pts[:, 1]
    ok = (x >= 0) & (x <= w - 1.001) & (y >= 0) & (y <= h - 1.001)
    out = np.zeros(len(pts), np.float32)
    if ok.any():
        xs = x[ok]; ys = y[ok]
        x0 = np.floor(xs).astype(int); y0 = np.floor(ys).astype(int)
        fx = xs - x0; fy = ys - y0
        v = (mapf[y0, x0] * (1 - fx) * (1 - fy) + mapf[y0, x0 + 1] * fx * (1 - fy)
             + mapf[y0 + 1, x0] * (1 - fx) * fy + mapf[y0 + 1, x0 + 1] * fx * fy)
        out[ok] = v
    return out


# ---------------------------------------------------------------- pin rack fit

def rack_template(H):
    """Image positions of the 10 pin bases under H plus the local px/inch scale
    at each base (horizontal) so bodies can be drawn 15 in tall."""
    bases = pin_bases_in()
    pts = np.array([bases[p] for p in range(1, 11)], np.float32)
    img_pts = to_image(H, pts)
    # local horizontal scale: image distance for +1 in in lane x
    img_pts2 = to_image(H, pts + np.array([1.0, 0.0], np.float32))
    scale = np.hypot(*(img_pts2 - img_pts).T)
    return img_pts, scale


def rack_score(wmap, base_pts, scale, n_body=8):
    """Matched filter: white along each pin's body axis (base -> 14 in up),
    dark in the gaps between neighbouring columns at mid-height, dark above
    the pin tops. Higher is better."""
    body, gap, above = [], [], []
    for (x, y), s in zip(base_pts, scale):
        h = PIN_H_IN * s
        ts = np.linspace(0.08, 0.92, n_body)
        body.append(np.stack([np.full(n_body, x), y - ts * h], 1))
        for g in (-3.0, 3.0):
            gap.append([[x + g * s, y - 0.55 * h]])
        above.append(np.stack([np.full(3, x), y - h * np.array([1.15, 1.30, 1.45])], 1))
    body = np.concatenate(body); gap = np.concatenate(gap); above = np.concatenate(above)
    sb = sample(wmap, body).mean(); sg = sample(wmap, gap).mean(); sa = sample(wmap, above).mean()
    return float(sb - 0.7 * sg - 0.5 * sa), {"body": round(float(sb), 3), "gap": round(float(sg), 3), "above": round(float(sa), 3)}


def fit_rack(img, H0, w_px, search=None, coarse=False):
    """Fit a similarity (dx, dy, s about the rack centre) that moves the
    H0-rendered pin rack onto the white pins. Coarse-to-fine grid search.
    Returns (base_pts_fitted, scale_fitted, params, score, contrast)."""
    wmap = white_map(img)
    pts0, sc0 = rack_template(H0)
    centre = pts0.mean(0)
    # +-0.30 lane widths reaches a hand annotation's worst case; +-0.25 at inference (a student mask
    # that leaked into the next lane needs the reach; a range narrow enough to exclude the one-column
    # alias, +-0.12, found the wrong rack on more frames, not fewer). The alias is caught by its margin.
    rng = search or ({"dx": 0.25 * w_px, "dy": 0.15 * w_px, "s": (0.75, 1.30)} if coarse else {"dx": 0.30 * w_px, "dy": 0.15 * w_px, "s": (0.70, 1.35)})

    def apply(dx, dy, s):
        return centre + s * (pts0 - centre) + np.array([dx, dy]), sc0 * s

    best = (-1e9, None)
    scores = []
    if coarse:  # inference: ~8x fewer evaluations, the hill-climb below recovers the precision
        dxs = np.arange(-rng["dx"], rng["dx"] + 1e-6, max(1.0, rng["dx"] / 12))
        dys = np.arange(-rng["dy"], rng["dy"] + 1e-6, max(1.0, rng["dy"] / 6))
        ss = np.arange(rng["s"][0], rng["s"][1] + 1e-6, 0.05)
    else:
        dxs = np.arange(-rng["dx"], rng["dx"] + 1e-6, max(0.5, rng["dx"] / 30))
        dys = np.arange(-rng["dy"], rng["dy"] + 1e-6, max(0.5, rng["dy"] / 15))
        ss = np.arange(rng["s"][0], rng["s"][1] + 1e-6, 0.025)
    for s in ss:
        for dy in dys:
            for dx in dxs:
                p, sc = apply(dx, dy, s)
                v, _ = rack_score(wmap, p, sc)
                scores.append(v)
                if v > best[0]:
                    best = (v, (dx, dy, s))
    # refine
    dx, dy, s = best[1]
    for step in (0.5, 0.25, 0.1):
        improved = True
        while improved:
            improved = False
            for ddx, ddy, dds in ((step, 0, 0), (-step, 0, 0), (0, step, 0), (0, -step, 0), (0, 0, step / 20), (0, 0, -step / 20)):
                p, sc = apply(dx + ddx, dy + ddy, s + dds)
                v, _ = rack_score(wmap, p, sc)
                if v > best[0] + 1e-6:
                    best = (v, (dx + ddx, dy + ddy, s + dds)); dx, dy, s = best[1]; improved = True
    p, sc = apply(*best[1])
    v, parts = rack_score(wmap, p, sc)
    scores = np.array(scores)
    contrast = float((v - np.median(scores)) / (scores.std() + 1e-6))
    # alias check: the same rack shifted by one pin column (6 in) overlaps 6 of the 7 columns and
    # is the failure mode seen at 720p; report the margin over the better of the two aliases
    col = 6.0 * float(sc.mean())
    alias = max(rack_score(wmap, p + np.array([col, 0.0]), sc)[0], rack_score(wmap, p - np.array([col, 0.0]), sc)[0])
    parts["alias_margin"] = round(float(v - alias), 4)
    return p, sc, {"dx": round(float(best[1][0]), 2), "dy": round(float(best[1][1]), 2), "s": round(float(best[1][2]), 3)}, v, contrast, parts


def refine_pin_columns(img, base_pts, scale, half_in=2.5):
    """Per-column sub-pixel x: intensity-weighted centre of the white profile in a
    band across each pin body at 30-70 % of its height, within +-half_in of the
    template column. Keeps the template x when the profile is flat."""
    wmap = white_map(img)
    out = base_pts.copy()
    for i, ((x, y), s) in enumerate(zip(base_pts, scale)):
        h = PIN_H_IN * s
        xs = np.arange(x - half_in * s, x + half_in * s + 1e-6, 0.25)
        prof = np.zeros(len(xs))
        for t in np.linspace(0.3, 0.7, 5):
            prof += sample(wmap, np.stack([xs, np.full(len(xs), y - t * h)], 1))
        prof -= prof.min()
        if prof.sum() < 1e-6 or prof.max() < 0.05:
            continue
        out[i, 0] = float((xs * prof).sum() / prof.sum())
    return out


# ---------------------------------------------------------------- arrows

def rectify(img, H, px_per_in=10.0 / BOARD_IN, len_in=HEAD_IN):
    """Bird's-eye lane image: 10 px per board wide, same px/in along the lane."""
    S = np.array([[px_per_in, 0, 0], [0, -px_per_in, len_in * px_per_in], [0, 0, 1]], np.float64)  # y down = toward foul line
    Hr = S @ H
    w = int(round(W_IN * px_per_in)); h = int(round(len_in * px_per_in))
    return cv2.warpPerspective(img, Hr, (w, h), flags=cv2.INTER_CUBIC), Hr


def detect_arrows(img, H, y_ft=(9.0, 19.0), tol_boards=2.5, debug=None):
    """Dark arrow inlays on the rectified lane, assigned to the seven nominal
    boards. Returns {board: {x, y (image px), x_in, y_in (lane, under H),
    darkness, area}} and the rectified debug image."""
    px_per_in = 10.0 / BOARD_IN
    rect, Hr = rectify(img, H, px_per_in)
    g = cv2.cvtColor(rect, cv2.COLOR_BGR2GRAY).astype(np.float32)
    y0 = int(rect.shape[0] - y_ft[1] * 12 * px_per_in); y1 = int(rect.shape[0] - y_ft[0] * 12 * px_per_in)
    band = g[y0:y1]
    bg = cv2.medianBlur(band.astype(np.uint8), 41).astype(np.float32)
    dark = bg - band
    mad = np.median(np.abs(dark - np.median(dark))) + 1e-6
    thr = max(10.0, np.median(dark) + 4.0 * mad)
    m = (dark > thr).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, stats, cent = cv2.connectedComponentsWithStats(m, 8)
    blobs = []
    for i in range(1, n):
        x, y, bw, bh, a = stats[i]
        if a < 25 or a > 1500 or bw > 40:
            continue
        ys, xs = np.where(lab == i)
        wts = dark[ys, xs]
        cx = float((xs * wts).sum() / wts.sum()); cy = float((ys * wts).sum() / wts.sum()) + y0
        blobs.append({"x": cx, "y": cy, "area": int(a), "darkness": float(wts.mean()), "w": int(bw), "h": int(bh)})
    cols = {b: board_x_in(b) * px_per_in for b in C.ARROW_BOARDS}
    tol = tol_boards * 10.0
    found = {}
    for b, xc in cols.items():
        cands = [bl for bl in blobs if abs(bl["x"] - xc) <= tol]
        if not cands:
            continue
        best = max(cands, key=lambda bl: bl["darkness"] * math.sqrt(bl["area"]) - 0.5 * abs(bl["x"] - xc))
        found[b] = best
    # V-shape / consistency: the shift (blob x - nominal) should be smooth across the seven; drop outliers > 12 px from the median shift
    if len(found) >= 3:
        shifts = {b: found[b]["x"] - cols[b] for b in found}
        med = float(np.median(list(shifts.values())))
        found = {b: v for b, v in found.items() if abs(shifts[b] - med) <= 12.0}
    # V-shape: mirror arrows (b, 40-b) sit at the same depth; drop the one of a pair that
    # is off the V fitted to the rest (rect y vs |b-20| linear, outer arrows nearer the foul line)
    found = v_filter(found)
    out = {}
    Hr_inv = np.linalg.inv(Hr)
    for b, bl in found.items():
        p_img = cv2.perspectiveTransform(np.float32([[[bl["x"], bl["y"]]]]), Hr_inv).reshape(2)
        lane = to_lane(H, [p_img])[0]
        out[b] = {"x": float(p_img[0]), "y": float(p_img[1]), "x_in": float(lane[0]), "y_in": float(lane[1]),
                  "rect_x": bl["x"], "rect_y": bl["y"], "darkness": round(bl["darkness"], 1), "area": bl["area"],
                  "board_under_H": float(boards_from_lane_x(lane[0]))}
    if debug is not None:
        dbg = rect[y0 - 40:y1 + 40].copy()
        for b, xc in cols.items():
            cv2.line(dbg, (int(xc), 0), (int(xc), dbg.shape[0]), (255, 0, 255), 1)
        for bl in blobs:
            cv2.circle(dbg, (int(bl["x"]), int(bl["y"] - y0 + 40)), 6, (0, 255, 255), 1)
        for b, v in out.items():
            cv2.circle(dbg, (int(v["rect_x"]), int(v["rect_y"] - y0 + 40)), 9, (0, 255, 0), 2)
            cv2.putText(dbg, str(b), (int(v["rect_x"]) + 10, int(v["rect_y"] - y0 + 40)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        cv2.imwrite(debug, cv2.resize(dbg, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC))
    return out, rect


def v_filter(found, tol_px=70.0):
    """Keep arrows consistent with one V: robust line rect_y = c + k*|b-20|, k >= 0
    (outer arrows nearer the foul line = larger rect y). Iteratively drops the
    worst residual above tol_px (about 7 in; the arrows' own V is ~5 in per step). Needs >= 4 arrows to act."""
    found = dict(found)
    while len(found) >= 4:
        bs = np.array(sorted(found)); d = np.abs(bs - 20.0); ys = np.array([found[b]["y"] for b in bs])
        A = np.stack([np.ones_like(d), d], 1)
        # least squares on all, then check residuals
        coef, *_ = np.linalg.lstsq(A, ys, rcond=None)
        if coef[1] < 0:  # wrong orientation: refit with k clamped at 0 (flat)
            coef = np.array([np.median(ys), 0.0])
        res = ys - A @ coef
        # leave-one-out residual for the worst point (the outlier drags the fit)
        worst = None
        for i, b in enumerate(bs):
            m = np.ones(len(bs), bool); m[i] = False
            cf, *_ = np.linalg.lstsq(A[m], ys[m], rcond=None)
            if cf[1] < 0:
                cf = np.array([np.median(ys[m]), 0.0])
            r = abs(ys[i] - A[i] @ cf)
            if worst is None or r > worst[1]:
                worst = (int(b), float(r))
        if worst[1] > tol_px:
            found.pop(worst[0])
        else:
            break
    return found


# ---------------------------------------------------------------- multi-landmark homography (DLT with point / point-on-line constraints)

def fit_homography(points=(), lines=(), weights_pts=None, weights_lines=None, H_init=None):
    """Weighted DLT. points: [((u,v),(x,y))] full 2D correspondences (image -> lane inches);
    lines: [((u,v), x_in)] the image point lies on the lane line x = x_in (unknown y).
    Returns H (3x3, image -> lane) or None."""
    rows, ws = [], []
    for i, ((u, v), (x, y)) in enumerate(points):
        w = 1.0 if weights_pts is None else weights_pts[i]
        rows.append([-u, -v, -1, 0, 0, 0, x * u, x * v, x]); ws.append(w)
        rows.append([0, 0, 0, -u, -v, -1, y * u, y * v, y]); ws.append(w)
    for i, ((u, v), x) in enumerate(lines):
        w = 1.0 if weights_lines is None else weights_lines[i]
        rows.append([-u, -v, -1, 0, 0, 0, x * u, x * v, x]); ws.append(w)
    if len(rows) < 8:
        return None
    A = np.array(rows, np.float64); w = np.array(ws, np.float64)
    # normalise image coords for conditioning
    us = np.array([p[0][0] for p in points] + [l[0][0] for l in lines]); vs = np.array([p[0][1] for p in points] + [l[0][1] for l in lines])
    mu, mv = us.mean(), vs.mean(); su = us.std() + 1e-9; sv = vs.std() + 1e-9
    T = np.array([[1 / su, 0, -mu / su], [0, 1 / sv, -mv / sv], [0, 0, 1]])
    rows2 = []
    k = 0
    for ((u, v), (x, y)) in points:
        un, vn = (u - mu) / su, (v - mv) / sv
        rows2.append([-un, -vn, -1, 0, 0, 0, x * un, x * vn, x]); rows2.append([0, 0, 0, -un, -vn, -1, y * un, y * vn, y])
    for ((u, v), x) in lines:
        un, vn = (u - mu) / su, (v - mv) / sv
        rows2.append([-un, -vn, -1, 0, 0, 0, x * un, x * vn, x])
    A = np.array(rows2, np.float64) * w[:, None]
    _, _, Vt = np.linalg.svd(A)
    Hn = Vt[-1].reshape(3, 3)
    H = Hn @ T
    if abs(H[2, 2]) > 1e-12:
        H = H / H[2, 2]
    return H


def residuals(H, points=(), lines=()):
    """Lane-inch residuals per constraint."""
    out = []
    for (uv, xy) in points:
        p = to_lane(H, [uv])[0]
        out.append(float(np.hypot(p[0] - xy[0], p[1] - xy[1])))
    for (uv, x) in lines:
        p = to_lane(H, [uv])[0]
        out.append(float(abs(p[0] - x)))
    return out


def fit_robust(points, lines, w_pts, w_lines, thr_in=2.0, iters=3):
    """Iteratively reweighted fit: constraints with residual > thr_in get weight 0 (never drops the foul-line ends)."""
    wp = list(w_pts); wl = list(w_lines)
    H = fit_homography(points, lines, wp, wl)
    dropped = []
    for _ in range(iters):
        if H is None:
            return None, dropped
        r = residuals(H, points, lines)
        rp = r[:len(points)]; rl = r[len(points):]
        changed = False
        for i, v in enumerate(rl):
            if v > thr_in and wl[i] > 0:
                wl[i] = 0.0; dropped.append(("line", i, round(v, 2))); changed = True
        for i, v in enumerate(rp):
            if v > 2.5 * thr_in and wp[i] > 0 and w_pts[i] < 5:  # protected anchors keep weight
                wp[i] = 0.0; dropped.append(("point", i, round(v, 2))); changed = True
        if not changed:
            break
        H = fit_homography(points, lines, wp, wl)
    return H, dropped


# ---------------------------------------------------------------- per-frame landmark truth

def top_edge_depth_in(stem):
    """Lane-y (inches) of the annotated top edge under the all-landmark fit on the pre-hit frame."""
    doc = C.landmark_doc(stem)
    if "top_edge_depth_in" in doc:
        return doc["top_edge_depth_in"]
    return HEAD_IN


def truth_h(stem, f, kind="all"):
    """image -> lane inches homography of a truth quad on frame f, top edge at the depth measured in E1."""
    return h_from_quad(C.truth_corners(stem, f, kind), top_in=top_edge_depth_in(stem))


def truth_landmarks(stem, f, kind="all"):
    """Image positions on frame f of the arrows (7) and pin bases (10) implied by the
    truth quad of that frame: the landmarks are lane-plane points at known lane
    coordinates, so they move with the quad (camera motion included)."""
    H = truth_h(stem, f, kind)
    out = {}
    ax = arrow_x_in()
    V = C.landmark_doc(stem).get("all_fit", {}).get("V") or {"centre_ft": 15.3, "ft_per_5_boards": 0.43}
    for b, x in ax.items():
        y = (V["centre_ft"] - V["ft_per_5_boards"] * abs(b - 20) / 5.0) * 12
        p = to_image(H, [(x, y)])[0]
        out[f"arrow_{b}"] = (float(p[0]), float(p[1]))
    for k, (x, y) in pin_bases_in().items():
        p = to_image(H, [(x, y)])[0]
        out[f"pin_{k}_base"] = (float(p[0]), float(p[1]))
    return out
