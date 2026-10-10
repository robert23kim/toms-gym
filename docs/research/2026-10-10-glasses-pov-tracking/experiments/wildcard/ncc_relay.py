"""NCC template relay: carry the ball forward and backward from a YOLO-chain seed with a
Lab-space normalised cross-correlation template, re-centred on the dark ball blob each frame."""
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np

Pos = Tuple[int, float, float, float, float]  # frame, x, y, r, score


def shift_pt(shifts: Dict[int, dict], k: int, x: float, y: float, forward: bool = True) -> Tuple[float, float]:
    """Camera similarity taking frame k-1 -> k (forward) or its inverse (backward, k -> k-1)."""
    s = shifts.get(k)
    if not s:
        return x, y
    a, b, tx, ty = s["a"], s["b"], s["tx"], s["ty"]
    if forward:
        return a * x + b * y + tx, -b * x + a * y + ty
    det = a * a + b * b
    if det < 1e-6:
        return x, y
    u, v = x - tx, y - ty
    return (a * u - b * v) / det, (b * u + a * v) / det


def dark_blob(lab: np.ndarray, x: float, y: float, r: float, drop: float = 25.0) -> Optional[Tuple[float, float, float]]:
    """Centroid + equivalent radius of the dark component nearest (x, y) inside a 2r window; None if no clear blob.
    Darkness is relative to the window's border ring (the lane around the ball)."""
    H, W = lab.shape[:2]
    h = int(max(2.0 * r, 12))
    x0, y0, x1, y1 = int(x) - h, int(y) - h, int(x) + h + 1, int(y) + h + 1
    if x0 < 0 or y0 < 0 or x1 > W or y1 > H:
        return None
    Lc = lab[y0:y1, x0:x1, 0].astype(np.float32)
    ring = np.concatenate([Lc[0, :], Lc[-1, :], Lc[:, 0], Lc[:, -1]])
    thr = float(np.median(ring)) - drop
    m = (Lc < thr).astype(np.uint8)
    n, lab_, st, cen = cv2.connectedComponentsWithStats(m)
    best = None
    for i in range(1, n):
        area = st[i, cv2.CC_STAT_AREA]
        if area < 4:
            continue
        cx, cy = cen[i]
        d = np.hypot(cx - h, cy - h)
        if d > max(r, 6):
            continue
        if best is None or area > best[0]:
            best = (area, cx, cy)
    if best is None:
        return None
    area, cx, cy = best
    return x0 + cx, y0 + cy, float(np.sqrt(area / np.pi))


def _crop(im, x, y, h):
    H, W = im.shape[:2]
    x0, y0, x1, y1 = int(round(x - h)), int(round(y - h)), int(round(x + h)), int(round(y + h))
    if x0 < 0 or y0 < 0 or x1 > W or y1 > H or x1 - x0 < 4 or y1 - y0 < 4:
        return None
    return im[y0:y1, x0:x1]


def _match(lab, tpl, qx, qy, win):
    H, W = lab.shape[:2]
    th, tw = tpl.shape[:2]
    x0, y0 = int(max(0, qx - win - tw / 2)), int(max(0, qy - win - th / 2))
    x1, y1 = int(min(W, qx + win + tw / 2)), int(min(H, qy + win + th / 2))
    sub = lab[y0:y1, x0:x1]
    if sub.shape[0] <= th or sub.shape[1] <= tw:
        return None
    res = cv2.matchTemplate(sub, tpl, cv2.TM_CCOEFF_NORMED)
    _, mx, _, loc = cv2.minMaxLoc(res)
    return loc[0] + x0 + tw / 2.0, loc[1] + y0 + th / 2.0, float(mx)


def relay(labs: List[np.ndarray], shifts: Dict[int, dict], k0: int, x: float, y: float, r: float, *, forward: bool,
          min_score: float = 0.55, max_miss: int = 3, scales=(1.0,), max_steps: int = 200,
          refine: bool = True, max_r: float = 170.0, log=None) -> List[Pos]:
    """Track from frame k0 (cut-local) with the ball at (x, y, r). Returns positions for the frames after k0
    (forward) or before it (backward), nearest first."""
    out: List[Pos] = []
    step = 1 if forward else -1
    vx = vy = 0.0
    miss = 0
    k = k0
    cur_lab = labs[k0]
    while len(out) < max_steps:
        kn = k + step
        if kn < 0 or kn >= len(labs):
            break
        h = max(1.4 * r, 9.0)
        tpl = _crop(cur_lab, x, y, h)
        if tpl is None:
            break
        # prediction: camera shift (k -> kn) applied to the current position, plus the ball's own velocity
        px, py = shift_pt(shifts, kn if forward else k, x, y, forward=forward)
        px, py = px + vx, py + vy
        win = max(2.5 * r, 40.0) + 0.5 * np.hypot(vx, vy)
        best = None
        for s in scales:
            t = tpl if s == 1.0 else cv2.resize(tpl, None, fx=s, fy=s, interpolation=cv2.INTER_LINEAR)
            m = _match(labs[kn], t, px, py, win)
            if m and (best is None or m[2] > best[2]):
                best = (m[0], m[1], m[2], s)
        if best is None or best[2] < min_score:
            miss += 1
            if miss > max_miss:
                break
            # coast on the prediction without updating the template frame
            x, y = px, py
            k = kn
            continue
        miss = 0
        nx, ny, sc, s = best
        nr = r * s
        if refine:
            b = dark_blob(labs[kn], nx, ny, nr)
            # the blob must be the ball, not the ball merged with the dark masking / gutter behind it
            if b is not None and np.hypot(b[0] - nx, b[1] - ny) <= max(0.7 * nr, 4) and 0.45 * nr <= b[2] <= 1.6 * nr:
                nx, ny = 0.5 * (nx + b[0]), 0.5 * (ny + b[1])
                nr = float(np.clip(b[2], nr * 0.85, nr * 1.15))
        # going away from the camera the ball never grows; coming back toward release it grows fast
        nr = min(nr, r * (1.03 if forward else 1.35))
        if nr > max_r:
            break  # bigger than any released ball: the ball is still in the hand at the frame bottom
        ux, uy = shift_pt(shifts, kn if forward else k, x, y, forward=forward)
        vx, vy = 0.6 * vx + 0.4 * (nx - ux), 0.6 * vy + 0.4 * (ny - uy)
        x, y, r = nx, ny, max(nr, 3.0)
        k = kn
        cur_lab = labs[kn]
        out.append((kn, float(x), float(y), float(r), float(sc)))
        if log:
            log(f"    relay {'fwd' if forward else 'bwd'} k={kn} x={x:.0f} y={y:.0f} r={r:.1f} ncc={sc:.2f} s={s}")
    return out


def seed_from_box(lab: np.ndarray, x: float, y: float, rbox: float) -> Tuple[float, float, float]:
    """A YOLO box is 2-3x the ball; take the dark blob inside it for the ball centre and radius."""
    b = dark_blob(lab, x, y, rbox * 0.8, drop=25.0)
    if b is None:
        return x, y, rbox * 0.4
    return b[0], b[1], max(b[2], 4.0)
