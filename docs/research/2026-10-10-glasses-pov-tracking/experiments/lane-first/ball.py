"""Purple-ball candidates: HSV blob detection restricted to a region of interest (the lane quad)."""
import cv2
import numpy as np

H_LO, H_HI, S_MIN, V_LO, V_HI = 120, 172, 40, 55, 200


def purple_mask(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, (H_LO, S_MIN, V_LO), (H_HI, 255, V_HI))
    return m


def candidates(img, roi=None, min_area=12, max_n=40):
    """List of dicts {x, y, r, area, w, h}. r = mean of equivalent-area radius and bbox half-size."""
    m = purple_mask(img)
    if roi is not None:
        m = cv2.bitwise_and(m, roi)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    n, lab, st, cen = cv2.connectedComponentsWithStats(m)
    out = []
    for i in range(1, n):
        a = int(st[i, cv2.CC_STAT_AREA])
        if a < min_area:
            continue
        w, h = int(st[i, cv2.CC_STAT_WIDTH]), int(st[i, cv2.CC_STAT_HEIGHT])
        r_area = float(np.sqrt(a / np.pi))
        r_box = 0.5 * max(w, h)
        out.append({"x": float(cen[i][0]), "y": float(cen[i][1]), "r": 0.5 * (r_area + r_box),
                    "area": a, "w": w, "h": h, "fill": a / float(max(w * h, 1))})
    out.sort(key=lambda c: -c["area"])
    return out[:max_n]


def global_shift(prev_grey_q, grey_q):
    """Camera shift (dx, dy) in full-res px between two quarter-res float32 greys (phase correlation)."""
    (dx, dy), resp = cv2.phaseCorrelate(prev_grey_q, grey_q)
    return 4.0 * dx, 4.0 * dy, float(resp)


def grey_q(img):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    g = cv2.resize(g, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
    return np.float32(g)
