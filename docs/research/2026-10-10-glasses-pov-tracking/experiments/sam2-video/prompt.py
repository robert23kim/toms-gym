"""Purple-ball prompt finder: compact purple blobs (the gutter's blue streak is purple too but elongated)."""
import cv2, numpy as np

HSV_LO, HSV_HI = (118, 50, 35), (165, 255, 255)


def purple_mask(im):
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, HSV_LO, HSV_HI)
    return cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))


def compact_blobs(im, min_area=300, y_min_frac=0.25):
    """Blobs in the lower part of the frame that look like a ball: aspect 0.55-1.8, bbox fill >= 0.45.
    Returns [(x0, y0, x1, y1, area, score)] sorted by area desc."""
    m = purple_mask(im)
    H, W = m.shape
    n, lab, stats, cents = cv2.connectedComponentsWithStats(m)
    out = []
    for i in range(1, n):
        x, y, w, h, a = (int(v) for v in stats[i])
        if a < min_area or cents[i][1] < y_min_frac * H:
            continue
        asp = w / max(h, 1)
        fill = a / float(w * h)
        if not (0.55 <= asp <= 1.8) or fill < 0.45:
            continue
        out.append((x, y, x + w, y + h, a, fill))
    out.sort(key=lambda b: -b[4])
    return out


def blob_at(im, near=None, max_dist=None, **kw):
    bl = compact_blobs(im, **kw)
    if near is not None:
        bl = [b for b in bl if np.hypot((b[0] + b[2]) / 2 - near[0], (b[1] + b[3]) / 2 - near[1]) <= max_dist]
    return bl[0] if bl else None


def _c(b):
    return (b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0, float(np.sqrt(b[4] / np.pi))


def chained_blob(frames, k, n_top=4, gate_k=3.0, gate_px=60.0, area_ratio=(0.4, 2.5)):
    """A compact blob at frame k that has a motion-consistent successor at k+1 and k+2 (distance <= gate_k * r + gate_px,
    area within area_ratio). Largest such blob, else None. Distractors (gutter glints, panels) do not chain."""
    if k + 2 >= len(frames):
        return None
    b0s = compact_blobs(frames[k])[:n_top]
    b1s = compact_blobs(frames[k + 1])[:n_top]
    b2s = compact_blobs(frames[k + 2])[:n_top]

    def succ(b, cands, pred=None):
        x, y, r = _c(b)
        px, py = pred if pred is not None else (x, y)
        best = None
        for c in cands:
            cx, cy, cr = _c(c)
            if not (area_ratio[0] <= c[4] / b[4] <= area_ratio[1]):
                continue
            d = np.hypot(cx - px, cy - py)
            if d <= gate_k * r + gate_px and (best is None or d < best[0]):
                best = (d, c)
        return None if best is None else best[1]

    for b0 in b0s:
        b1 = succ(b0, b1s)
        if b1 is None:
            continue
        x0, y0, _ = _c(b0)
        x1, y1, _ = _c(b1)
        b2 = succ(b1, b2s, pred=(2 * x1 - x0, 2 * y1 - y0))
        if b2 is not None:
            return b0
    return None
