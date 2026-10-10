"""Per-frame lane detection for the glasses POV: the bowler's lane as the bright yellow component
bounded by the dark gutters; left/right edge lines (x = a*y + b, full-res px) by RANSAC on the
component's row extremes; pin-deck row = top of the component. Everything in full-res pixels."""
import cv2
import numpy as np

SCALE = 0.5  # lane work at half resolution
H_LO, H_HI, S_MIN, V_MIN = 5, 45, 8, 120


def lane_mask(img):
    """Half-res binary mask of lane wood (bright, yellowish)."""
    small = cv2.resize(img, None, fx=SCALE, fy=SCALE, interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, (H_LO, S_MIN, V_MIN), (H_HI, 255, 255))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    return m


def components(mask, min_area=1500):
    n, lab, st, cen = cv2.connectedComponentsWithStats(mask)
    comps = []
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] >= min_area:
            comps.append((i, st[i], cen[i]))
    return lab, comps


def ransac_line(ys, xs, thr=3.0, iters=200, rng=None):
    """x = a*y + b, robust. Returns (a, b, n_inliers) or None."""
    ys, xs = np.asarray(ys, float), np.asarray(xs, float)
    if len(ys) < 8:
        return None
    rng = rng or np.random.default_rng(0)
    best, best_in = None, 0
    n = len(ys)
    for _ in range(iters):
        i, j = rng.integers(0, n, 2)
        if ys[i] == ys[j]:
            continue
        a = (xs[i] - xs[j]) / (ys[i] - ys[j])
        b = xs[i] - a * ys[i]
        d = np.abs(xs - (a * ys + b))
        k = int((d < thr).sum())
        if k > best_in:
            best_in, best = k, (a, b)
    if best is None:
        return None
    a, b = best
    inl = np.abs(xs - (a * ys + b)) < thr
    if inl.sum() >= 2:
        A = np.vstack([ys[inl], np.ones(inl.sum())]).T
        (a, b), *_ = np.linalg.lstsq(A, xs[inl], rcond=None)
    return float(a), float(b), int(inl.sum())


class LaneFrame:
    """left/right: (a, b) full-res, x = a*y + b. pd_y: pin-deck row (full-res). bot_y: lowest row with both edges in frame."""

    def __init__(self, left, right, pd_y, bot_y, comp_id, n_in):
        self.left, self.right, self.pd_y, self.bot_y, self.comp_id, self.n_in = left, right, pd_y, bot_y, comp_id, n_in

    def shifted(self, dx, dy):
        """The same lane moved by a camera translation (dx, dy)."""
        al, bl = self.left
        ar, br = self.right
        return LaneFrame((al, bl + dx - al * dy), (ar, br + dx - ar * dy), self.pd_y + dy, self.bot_y, self.comp_id, self.n_in)

    def y_vp(self):
        return (self.right[1] - self.left[1]) / (self.left[0] - self.right[0])

    def xl(self, y):
        return self.left[0] * y + self.left[1]

    def xr(self, y):
        return self.right[0] * y + self.right[1]

    def width(self, y):
        return self.xr(y) - self.xl(y)

    def u(self, x, y):
        """Fraction across the lane from the left edge."""
        return (x - self.xl(y)) / max(self.width(y), 1e-6)

    def board(self, x, y):
        """Engine convention: board 1 at the right edge, 39 at the left."""
        return (1.0 - self.u(x, y)) * 38.0 + 1.0

    def depth(self, y, total_ft=60.0):
        """Depth along the lane in feet, pinned to total_ft at the pin-deck row: Z = total * w(pd) / w(y)."""
        return total_ft * self.width(self.pd_y) / max(self.width(y), 1e-6)

    def y_from_depth(self, z, total_ft=60.0):
        """Inverse of depth(): width is linear in y, so w(y) = total * w(pd) / z."""
        w = total_ft * self.width(self.pd_y) / max(z, 1e-3)
        aw = self.right[0] - self.left[0]
        bw = self.right[1] - self.left[1]
        if abs(aw) < 1e-9:
            return self.pd_y
        return (w - bw) / aw

    def to_image(self, u, z):
        y = self.y_from_depth(z)
        return self.xl(y) + u * self.width(y), y

    def quad(self):
        return {"fl_l": [round(self.xl(self.bot_y), 1), round(float(self.bot_y), 1)],
                "fl_r": [round(self.xr(self.bot_y), 1), round(float(self.bot_y), 1)],
                "pd_l": [round(self.xl(self.pd_y), 1), round(float(self.pd_y), 1)],
                "pd_r": [round(self.xr(self.pd_y), 1), round(float(self.pd_y), 1)],
                "fl_is_foul_line": False}

    def roi_mask(self, shape, margin_frac=0.15):
        """Full-res polygon between the edges (widened by margin_frac of width) from pd_y to the bottom."""
        h, w = shape[:2]
        ys = [self.pd_y, float(h - 1)]
        pts = []
        for y in ys:
            m = margin_frac * self.width(y)
            pts.append((self.xl(y) - m, y))
        for y in reversed(ys):
            m = margin_frac * self.width(y)
            pts.append((self.xr(y) + m, y))
        mask = np.zeros((h, w), np.uint8)
        cv2.fillPoly(mask, [np.array(pts, np.int32)], 255)
        return mask


def pick_component(lab, comps, prev, hint_xy, shape_small):
    """Choose our lane: the component containing hint_xy (half-res) if any, else the one most overlapping
    prev (half-res mask), else the biggest touching the bottom row."""
    hs, ws = shape_small
    if hint_xy is not None and np.all(np.isfinite(hint_xy)):
        x, y = int(round(hint_xy[0])), int(round(hint_xy[1]))
        if 0 <= x < ws and 0 <= y < hs:
            cid = lab[y, x]
            if cid and any(c[0] == cid for c in comps):
                return cid, "hint"
    if prev is not None:
        best, bo = None, 0
        for cid, st, cen in comps:
            o = int(((lab == cid) & (prev > 0)).sum())
            if o > bo:
                bo, best = o, cid
        if best is not None and bo > 0.3 * (prev > 0).sum():
            return best, "overlap"
    best, ba = None, 0
    for cid, st, cen in comps:
        if st[cv2.CC_STAT_TOP] + st[cv2.CC_STAT_HEIGHT] >= hs - 2 and st[cv2.CC_STAT_AREA] > ba:
            ba, best = st[cv2.CC_STAT_AREA], cid
    return best, "bottom"


def edges_from_component(lab, cid, shape_small):
    hs, ws = shape_small
    m = (lab == cid)
    rows = np.where(m.any(axis=1))[0]
    lys, lxs, rys, rxs, widths = [], [], [], [], {}
    for y in rows:
        xs = np.where(m[y])[0]
        l, r = xs[0], xs[-1]
        widths[y] = r - l
        if r - l < 8:
            continue
        if l > 1:
            lys.append(y); lxs.append(l)
        if r < ws - 2:
            rys.append(y); rxs.append(r)
    return lys, lxs, rys, rxs, widths, rows


def fit_lane(mask, prev_mask=None, hint_xy=None):
    """mask: half-res lane mask. hint_xy: predicted ball position, full-res. Returns (LaneFrame|None, info)."""
    lab, comps = components(mask)
    if not comps:
        return None, {"why": "no components"}
    hint = None if hint_xy is None else (hint_xy[0] * SCALE, hint_xy[1] * SCALE)
    cid, how = pick_component(lab, comps, prev_mask, hint, mask.shape)
    if cid is None:
        return None, {"why": "no bottom component"}
    lys, lxs, rys, rxs, widths, rows = edges_from_component(lab, cid, mask.shape)
    L = ransac_line(lys, lxs)
    R = ransac_line(rys, rxs)
    info = {"how": how, "n_left": len(lys), "n_right": len(rys)}
    if L is None or R is None:
        return None, {**info, "why": "edge fit failed"}
    # scale lines to full res: x_full = x_half/SCALE, y_full = y_half/SCALE  ->  x = a*y + b/SCALE
    left = (L[0], L[1] / SCALE)
    right = (R[0], R[1] / SCALE)
    if right[0] <= left[0]:  # must converge upward: right slope > left slope
        return None, {**info, "why": "edges do not converge"}
    if L[2] < 30 or R[2] < 30:
        return None, {**info, "why": "too few edge rows", "inl": [L[2], R[2]]}
    y_vp = (right[1] - left[1]) / (left[0] - right[0])
    # pin-deck row: topmost row whose component width is >= 0.5 of the fitted width, 3 consecutive rows
    top = None
    for y in rows:
        wf = (right[0] - left[0]) * (y / SCALE) + (right[1] - left[1])
        if wf <= 0:
            continue
        if all((y + k) in widths and widths[y + k] >= 0.5 * wf * SCALE for k in range(3)):
            top = y
            break
    if top is None:
        return None, {**info, "why": "no pin row"}
    pd_y = top / SCALE
    if not (-6000 < y_vp < pd_y - 30):
        return None, {**info, "why": "bad vanishing point", "y_vp": round(y_vp)}
    # lowest row with both edges inside the frame
    h_full = mask.shape[0] / SCALE
    w_full = mask.shape[1] / SCALE
    bot = h_full - 1
    for y in np.arange(h_full - 1, pd_y, -1.0):
        if left[0] * y + left[1] >= 0 and right[0] * y + right[1] <= w_full - 1:
            bot = y
            break
    lf = LaneFrame(left, right, float(pd_y), float(bot), cid, (L[2], R[2]))
    return lf, info


def component_mask(mask, cid):
    lab, _ = components(mask)
    return (lab == cid).astype(np.uint8) * 255
