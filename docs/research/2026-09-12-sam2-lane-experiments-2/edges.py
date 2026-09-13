"""Edge extraction from SAM logits and from the image, and line fitting.

lane_sam.fit_edges takes the leftmost / rightmost pixel of the binary mask on
each row. Two things are lost there: the sub-pixel position of the boundary
(the logit zero crossing sits between two pixels) and half a pixel per side
(the first pixel *inside* is not the edge). Both matter where a board is
1-2 px. Functions here return per-row edge samples (ys, xs) so results from
several crops / scales can be merged before one robust line fit per edge.
"""
import cv2
import numpy as np

import common as C

L = C.L


def component(logit, anchors):
    """Binary lane component (holds the anchors, else the largest) of logit > 0."""
    return L.largest_component((logit > 0).astype(np.uint8), anchors)


def soft_rows(logit, y_top, y_bot, anchors, comp=None, min_w=5):
    """Per-row sub-pixel left/right edges from the logit zero crossings of the
    lane component. Returns (ys, xl, xr) as float arrays; rows without the
    component are skipped."""
    if comp is None:
        comp = component(logit, anchors)
    if comp is None:
        return np.array([]), np.array([]), np.array([])
    H, W = logit.shape
    ys, ls, rs = [], [], []
    for y in range(int(y_top), int(y_bot) + 1):
        if y < 0 or y >= H:
            continue
        xs = np.where(comp[y])[0]
        if len(xs) < min_w:
            continue
        xl, xr = int(xs.min()), int(xs.max())
        row = logit[y]
        if xl >= 1 and row[xl - 1] < 0 <= row[xl]:
            t = -row[xl - 1] / (row[xl] - row[xl - 1])
            l_sub = xl - 1 + t
        else:
            l_sub = xl - 0.5
        if xr + 1 < W and row[xr] >= 0 > row[xr + 1]:
            t = row[xr] / (row[xr] - row[xr + 1])
            r_sub = xr + t
        else:
            r_sub = xr + 0.5
        ys.append(y)
        ls.append(l_sub)
        rs.append(r_sub)
    return np.array(ys, float), np.array(ls, float), np.array(rs, float)


def fit(ys, xs):
    """x = a*y + b, robust (lane_sam.robust_line). None with < 10 samples."""
    if len(ys) < 10:
        return None
    a, b, resid = L.robust_line(ys, xs)
    return (a, b), resid


def fit_pair(ys, xl, xr):
    fl = fit(ys, xl)
    fr = fit(ys, xr)
    if fl is None or fr is None:
        return None
    return fl[0], fr[0], {"fit_resid_px": round((fl[1] + fr[1]) / 2, 2), "rows": int(len(ys))}


def merge_rows(samples):
    """samples: list of (ys, xl, xr, priority). For each row keep the sample
    with the highest priority (e.g. the zoomed crop over the full frame)."""
    best = {}
    for ys, xl, xr, pr in samples:
        for y, l, r in zip(ys, xl, xr):
            y = int(y)
            if y not in best or pr > best[y][2]:
                best[y] = (l, r, pr)
    ys = np.array(sorted(best), float)
    return ys, np.array([best[int(y)][0] for y in ys]), np.array([best[int(y)][1] for y in ys])


def polarity(img, comp, y_top, y_bot, ring=8):
    """+1 when the lane is brighter than what lies just outside its edges,
    -1 otherwise. Measured on a ring `ring` px wide around the component,
    within the scored rows, so the comparison is lane vs gutter."""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    k = np.ones((1, 2 * ring + 1), np.uint8)
    inner = cv2.erode(comp, k)
    outer = cv2.dilate(comp, k) & (1 - comp)
    band = np.zeros_like(comp)
    band[int(max(0, y_top)):int(min(comp.shape[0], y_bot + 1))] = 1
    a = g[(inner & band) > 0]
    b = g[(outer & band) > 0]
    if len(a) < 50 or len(b) < 50:
        return 1
    return 1 if a.mean() >= b.mean() else -1


def snap_rows(img, line, y_top, y_bot, side, pol, band=6, min_frac=0.4):
    """Per-row sub-pixel position of the strongest gradient of the expected
    sign within +-band px of the line. Left edge with a bright lane is a
    dark->bright step (gx > 0); the right edge the opposite. Rows whose best
    response is below min_frac of the median are dropped rather than snapped
    to noise (motion blur, no edge in the window)."""
    g = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (3, 3), 0)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
    sgn = pol * (1 if side == "left" else -1)
    resp = sgn * gx
    a, b = line
    H, W = resp.shape
    ys, xs, peaks = [], [], []
    for y in range(int(y_top), int(y_bot) + 1):
        if y < 0 or y >= H:
            continue
        x0 = int(round(a * y + b))
        lo, hi = max(1, x0 - band), min(W - 2, x0 + band)
        if hi <= lo:
            continue
        seg = resp[y, lo:hi + 1]
        i = int(np.argmax(seg))
        pk = float(seg[i])
        if pk <= 0:
            continue
        x = lo + i
        # parabolic sub-pixel refinement on the three samples around the peak
        l_, c_, r_ = resp[y, x - 1], resp[y, x], resp[y, x + 1]
        den = l_ - 2 * c_ + r_
        off = 0.5 * (l_ - r_) / den if abs(den) > 1e-6 else 0.0
        off = float(np.clip(off, -0.5, 0.5))
        ys.append(y)
        xs.append(x + off)
        peaks.append(pk)
    if len(ys) < 10:
        return np.array([]), np.array([])
    ys, xs, peaks = np.array(ys, float), np.array(xs, float), np.array(peaks)
    keep = peaks >= min_frac * np.median(peaks)
    return ys[keep], xs[keep]


def snap_pair(img, left, right, y_top, y_bot, pol, band=6, min_frac=0.4):
    """Snap both lines; a side that finds too few rows keeps its input line."""
    out = []
    info = {}
    for side, ln in (("left", left), ("right", right)):
        ys, xs = snap_rows(img, ln, y_top, y_bot, side, pol, band, min_frac)
        f = fit(ys, xs)
        info[f"snap_rows_{side}"] = int(len(ys))
        out.append(ln if f is None else f[0])
    return out[0], out[1], info


def crop_box(left, right, y0, y1, W, H, margin_frac=0.5, min_margin=30, y_pad_frac=0.1):
    """Crop around the lane between rows y0..y1 given coarse edge lines:
    x margins of max(min_margin, margin_frac * local width) each side."""
    (la, lb), (ra, rb) = left, right
    xl = min(la * y0 + lb, la * y1 + lb)
    xr = max(ra * y0 + rb, ra * y1 + rb)
    w1 = (ra * y1 + rb) - (la * y1 + lb)
    m = max(min_margin, margin_frac * w1)
    pad = y_pad_frac * (y1 - y0)
    x1, x2 = int(max(0, xl - m)), int(min(W, xr + m))
    ya, yb = int(max(0, y0 - pad)), int(min(H, y1 + pad))
    return x1, ya, x2, yb
