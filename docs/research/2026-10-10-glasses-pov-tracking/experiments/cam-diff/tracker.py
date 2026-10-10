"""Candidates from the camera-compensated residual, a colour gate, and a constant-velocity link
in camera-compensated coordinates. Frames here are CUT-local; run.py converts to SOURCE numbers."""
import math
import cv2
import numpy as np
from camdiff import residual

HUE_LO, HUE_HI, SAT_MIN = 112, 170, 30     # the purple ball in OpenCV HSV (0-180 hue)


def purple_mask(hsv, sat_min=SAT_MIN, val_max=255):
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    return ((h >= HUE_LO) & (h <= HUE_HI) & (s >= sat_min) & (v <= val_max)).astype(np.uint8)


def candidates(motion, frames, hsv, t, thr=22, min_area=12, max_area=40000, far_upscale=None):
    """Blobs of the residual at frame t: dicts {x, y, r, area, res, purple, f}.
    far_upscale: (y_limit, factor) -> residual rows above y_limit are upscaled by `factor` before
    thresholding (the brief's far-third 2x), blob coordinates mapped back."""
    res, valid = residual(motion, frames, t)
    if res is None:
        return [], None
    pm = purple_mask(hsv[t])
    out = []
    regions = [(res, 1.0, 0)]
    if far_upscale:
        y_lim, k = far_upscale
        top = cv2.resize(res[:y_lim], None, fx=k, fy=k, interpolation=cv2.INTER_CUBIC)
        regions = [(top, float(k), 0), (res[y_lim:], 1.0, y_lim)]
    for img, k, y0 in regions:
        m = (img > thr).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        n, lab, st, cen = cv2.connectedComponentsWithStats(m, 8)
        for i in range(1, n):
            a = st[i, cv2.CC_STAT_AREA] / (k * k)
            if a < min_area or a > max_area:
                continue
            x, y = cen[i][0] / k, cen[i][1] / k + y0
            w, h = st[i, cv2.CC_STAT_WIDTH] / k, st[i, cv2.CC_STAT_HEIGHT] / k
            if max(w, h) > 3.0 * max(1.0, min(w, h)):       # stripes (pin edges, gutter caps)
                continue
            r = math.sqrt(a / math.pi)
            # colour: purple fraction of the current frame inside the blob's disc
            xi, yi, ri = int(round(x)), int(round(y)), max(2, int(round(r)))
            Hh, Ww = pm.shape
            y1, y2, x1, x2 = max(0, yi - ri), min(Hh, yi + ri + 1), max(0, xi - ri), min(Ww, xi + ri + 1)
            disc = pm[y1:y2, x1:x2]
            yy, xx = np.ogrid[y1:y2, x1:x2]
            inside = (yy - yi) ** 2 + (xx - xi) ** 2 <= ri * ri
            pf = float(disc[inside].mean()) if inside.any() else 0.0
            comp = (lab[int(st[i, cv2.CC_STAT_TOP]):int(st[i, cv2.CC_STAT_TOP] + st[i, cv2.CC_STAT_HEIGHT]),
                        int(st[i, cv2.CC_STAT_LEFT]):int(st[i, cv2.CC_STAT_LEFT] + st[i, cv2.CC_STAT_WIDTH])] == i)
            rr = img[int(st[i, cv2.CC_STAT_TOP]):int(st[i, cv2.CC_STAT_TOP] + st[i, cv2.CC_STAT_HEIGHT]),
                     int(st[i, cv2.CC_STAT_LEFT]):int(st[i, cv2.CC_STAT_LEFT] + st[i, cv2.CC_STAT_WIDTH])]
            out.append({"f": t, "x": float(x), "y": float(y), "r": float(r), "area": float(a),
                        "res": float(rr[comp].mean()), "purple": pf, "wh": (float(w), float(h))})
    return out, res


def predict(motion, t, state):
    """State (x, y, vx, vy) in frame t-1 -> predicted (x, y) in frame t: camera motion on the
    position, the ball's own velocity carried as a compensated displacement."""
    x, y, vx, vy = state
    px, py = motion.point_fwd(t, x, y)
    qx, qy = motion.point_fwd(t, x + vx, y + vy)
    return px + (qx - px), py + (qy - py), (qx - px), (qy - py)


HSV_CTX = None


def link(motion, cands_by_t, n, min_purple=0.25, gate_k=2.5, gate_min=25.0, max_gap=4, grow=1.15, grow_add=3.0):
    """Greedy tracklets, nearest to the prediction, radius may shrink but not grow (yolo_chain's gate)."""
    tracklets = []   # each: {"pts": [cand...], "state": (x, y, vx, vy), "last_t": t, "miss": k}
    for t in range(n):
        cs = [c for c in cands_by_t.get(t, []) if c["purple"] >= min_purple]
        used = set()
        for tr in tracklets:
            if t - tr["last_t"] > max_gap or tr.get("dead"):
                continue
            # carry the state across missed frames through the camera motion
            x, y, vx, vy = tr["state"]
            for s in range(tr["last_t"] + 1, t + 1):
                x, y, vx, vy = predict(motion, s, (x, y, vx, vy))
            r0 = tr["pts"][-1]["r"]
            gate = max(gate_k * r0, gate_min) * (1 + 0.5 * (t - tr["last_t"] - 1))
            best, bd = None, None
            for i, c in enumerate(cs):
                if i in used or c["r"] > grow * r0 + grow_add:
                    continue
                d = math.hypot(c["x"] - x, c["y"] - y)
                if d <= gate and (bd is None or d < bd):
                    best, bd = i, d
            if best is None:
                continue
            c = cs[best]
            used.add(best)
            dt = t - tr["last_t"]
            nvx, nvy = (c["x"] - x + vx * dt) / dt, (c["y"] - y + vy * dt) / dt   # observed compensated velocity
            # smooth the velocity
            a = 0.6
            tr["state"] = (c["x"], c["y"], a * nvx + (1 - a) * vx, a * nvy + (1 - a) * vy)
            tr["pts"].append(c)
            tr["last_t"] = t
        for i, c in enumerate(cs):
            if i not in used:
                tracklets.append({"pts": [c], "state": (c["x"], c["y"], 0.0, 0.0), "last_t": t})
    return tracklets


def score_tracklet(tr):
    pts = tr["pts"]
    if len(pts) < 4:
        return -1.0
    r = np.array([p["r"] for p in pts])
    fs = np.array([p["f"] for p in pts], float)
    slope = np.polyfit(fs, r, 1)[0] if len(pts) > 2 else 0.0
    shrink = r[: max(1, len(r) // 4)].mean() / max(1e-6, r[-max(1, len(r) // 4):].mean())
    purple = np.mean([p["purple"] for p in pts])
    res = np.mean([p["res"] for p in pts])
    span = pts[-1]["f"] - pts[0]["f"] + 1
    if slope > 0.3:
        return -1.0
    return span * purple * (0.5 + min(res, 60) / 60.0) * (0.5 + min(shrink, 3.0) / 3.0)


def select_throw(tracklets):
    best = max(tracklets, key=score_tracklet, default=None)
    if best is None or score_tracklet(best) <= 0:
        return None
    return best


def guided(hsv, res, x, y, r, win_k=3.0, win_min=30.0, sat_min=45, res_min=10, area_lo=0.2, area_hi=4.0):
    """Colour blob nearest the prediction inside a window: purple pixels (and moving ones when
    the residual exists). Returns a candidate dict or None."""
    H, W = hsv.shape[:2]
    w = int(max(win_k * r, win_min))
    xi, yi = int(round(x)), int(round(y))
    x1, x2, y1, y2 = max(0, xi - w), min(W, xi + w + 1), max(0, yi - w), min(H, yi + w + 1)
    if x2 - x1 < 4 or y2 - y1 < 4:
        return None
    m = purple_mask(hsv[y1:y2, x1:x2], sat_min=sat_min)
    if res is not None:
        m &= (res[y1:y2, x1:x2] > res_min).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n, lab, st, cen = cv2.connectedComponentsWithStats(m, 8)
    exp = math.pi * r * r
    best, bd = None, None
    for i in range(1, n):
        a = st[i, cv2.CC_STAT_AREA]
        if a < max(6, area_lo * exp) or a > area_hi * exp + 50:
            continue
        wd, hg = st[i, cv2.CC_STAT_WIDTH], st[i, cv2.CC_STAT_HEIGHT]
        # a ball is a filled disc; a chunk of masking panel or a stripe is not
        if res is None and (max(wd, hg) > 1.6 * min(wd, hg) or a < 0.45 * wd * hg):
            continue
        cx, cy = cen[i][0] + x1, cen[i][1] + y1
        d = math.hypot(cx - x, cy - y)
        if bd is None or d < bd:
            best, bd = i, d
    if best is None:
        return None
    a = st[best, cv2.CC_STAT_AREA]
    rr = res[int(cen[best][1] + y1), int(cen[best][0] + x1)] if res is not None else 0
    return {"x": float(cen[best][0] + x1), "y": float(cen[best][1] + y1), "r": float(math.sqrt(a / math.pi)),
            "area": float(a), "res": float(rr), "purple": 1.0, "src": "guided"}


def extend(motion, hsv, res_by_t, cands_by_t, seed_pts, n, forward=True, max_miss=6, min_purple=0.25,
           gate_k=2.5, gate_min=25.0, shrink_ok=(1.15, 3.0), grow_ok=(1.4, 6.0)):
    """Walk from one end of the seed, claim the nearest candidate (or a guided colour blob) at the
    camera-compensated constant-velocity prediction. Returns the new points (cut-local frames)."""
    pts = sorted(seed_pts, key=lambda p: p["f"])
    if len(pts) < 2:
        return []
    if forward:
        a, b = pts[-2], pts[-1]
        step = 1
    else:
        a, b = pts[1], pts[0]
        step = -1
    # velocity in b's frame, camera-compensated: move a's position into b's frame first
    ax, ay = a["x"], a["y"]
    if forward:
        ax, ay = motion.point_fwd(b["f"], ax, ay)
    else:
        ax, ay = motion.point_bwd(a["f"], ax, ay)
    dt = abs(b["f"] - a["f"])
    vx, vy = (b["x"] - ax) / dt, (b["y"] - ay) / dt
    x, y, r = b["x"], b["y"], b["r"]
    t = b["f"]
    out, miss = [], 0
    while True:
        t += step
        if t < 0 or t >= n:
            break
        if forward:
            px, py = motion.point_fwd(t, x, y)
            qx, qy = motion.point_fwd(t, x + vx, y + vy)
        else:
            px, py = motion.point_bwd(t + 1, x, y)
            qx, qy = motion.point_bwd(t + 1, x + vx, y + vy)
        vx, vy = qx - px, qy - py
        x, y = qx, qy
        gate = max(gate_k * r, gate_min) * (1 + 0.4 * miss)
        rk, ra = shrink_ok if forward else grow_ok
        best, bd = None, None
        for c in cands_by_t.get(t, []):
            if c["purple"] < min_purple or c["r"] > rk * r + ra:
                continue
            d = math.hypot(c["x"] - x, c["y"] - y)
            if d <= gate and (bd is None or d < bd):
                best, bd = c, d
        if best is None:
            g = guided(hsv[t], res_by_t.get(t), x, y, r, win_k=gate_k * (1 + 0.4 * miss))
            if g is not None and g["r"] <= rk * r + ra:
                best = g
        if best is None:
            miss += 1
            if miss > (max_miss if res_by_t.get(t) is not None else 2):
                break
            continue
        if best.get("src") == "guided":
            rr, rx, ry = refine_radius(hsv[t], best["x"], best["y"], best["r"])
            best = dict(best, r=rr, x=rx, y=ry)
        nvx, nvy = best["x"] - (x - vx), best["y"] - (y - vy)   # observed step = new - (predicted - v)
        k = miss + 1
        nvx, nvy = nvx / k, nvy / k
        vx, vy = 0.6 * nvx + 0.4 * vx, 0.6 * nvy + 0.4 * vy
        x, y = best["x"], best["y"]
        r = 0.5 * r + 0.5 * best["r"] if best["r"] < r else best["r"]
        out.append(dict(best, f=t))
        miss = 0
    return out


def interpolate(pts, max_gap=6):
    pts = sorted(pts, key=lambda p: p["f"])
    out = []
    for a, b in zip(pts, pts[1:]):
        out.append(a)
        g = b["f"] - a["f"]
        if 1 < g <= max_gap:
            for k in range(1, g):
                w = k / g
                out.append({"f": a["f"] + k, "x": a["x"] + w * (b["x"] - a["x"]), "y": a["y"] + w * (b["y"] - a["y"]),
                            "r": a["r"] + w * (b["r"] - a["r"]), "purple": 0.0, "res": 0.0, "src": "interp"})
    if pts:
        out.append(pts[-1])
    return out


def track(motion, frames, hsv, far_upscale=None, thr=22):
    n = len(frames)
    cb, rb = {}, {}
    for t in range(n):
        raw, rb[t] = candidates(motion, frames, hsv, t, thr=thr, far_upscale=far_upscale)
        cb[t] = refine_candidates(hsv[t], raw)
    global HSV_CTX
    HSV_CTX = hsv
    trs = link(motion, cb, n)
    best = select_throw(trs)
    if best is None:
        return [], {"tracklets": len(trs), "seed": None}
    seed = list(best["pts"])
    fwd = extend(motion, hsv, rb, cb, seed, n, forward=True)
    bwd = extend(motion, hsv, rb, cb, seed, n, forward=False)
    pts = sorted(list(bwd) + list(seed) + list(fwd), key=lambda p: p["f"])
    return interpolate(pts), {"tracklets": len(trs), "seed": [seed[0]["f"], seed[-1]["f"], len(seed)],
                              "fwd": len(fwd), "bwd": len(bwd), "cands": sum(len(v) for v in cb.values())}


def refine_radius(hsv, x, y, r, sat_min=40, max_win=320):
    """The residual blob of a uniformly dark ball is its rim and highlights, so its equivalent radius
    under-reads the ball. Re-read (r, x, y) from the purple component containing/nearest the centre;
    the window grows while the component touches its border."""
    H, W = hsv.shape[:2]
    w = int(max(3.0 * r + 20, 40))
    while True:
        xi, yi = int(round(x)), int(round(y))
        x1, x2, y1, y2 = max(0, xi - w), min(W, xi + w + 1), max(0, yi - w), min(H, yi + w + 1)
        if x2 - x1 < 4 or y2 - y1 < 4:
            return r, x, y
        m = purple_mask(hsv[y1:y2, x1:x2], sat_min=sat_min)
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        n, lab, st, cen = cv2.connectedComponentsWithStats(m, 8)
        best, bd = None, None
        for i in range(1, n):
            a = st[i, cv2.CC_STAT_AREA]
            if a < 6:
                continue
            cx, cy = cen[i][0] + x1, cen[i][1] + y1
            d = math.hypot(cx - x, cy - y)
            rr = math.sqrt(a / math.pi)
            if d <= max(0.8 * rr, 6) + 0.5 * r and (bd is None or d < bd):
                best, bd = i, d
        if best is None:
            return r, x, y
        l, t_, wd, hg = (int(st[best, k]) for k in (cv2.CC_STAT_LEFT, cv2.CC_STAT_TOP, cv2.CC_STAT_WIDTH, cv2.CC_STAT_HEIGHT))
        touches = l == 0 or t_ == 0 or l + wd >= (x2 - x1) or t_ + hg >= (y2 - y1)
        if touches and w < max_win and (x1 > 0 or y1 > 0 or x2 < W or y2 < H):
            w = int(w * 1.8)
            continue
        break
    a = st[best, cv2.CC_STAT_AREA]
    if max(wd, hg) > 2.2 * min(wd, hg):      # merged with a panel or a stripe: keep the residual's r
        return r, x, y
    rr = math.sqrt(a / math.pi)
    if rr > 12.0 * r + 30:
        return r, x, y
    return float(max(rr, 0.6 * r)), float(cen[best][0] + x1), float(cen[best][1] + y1)


def refine_candidates(hsv, cands, min_purple=0.25):
    """Refine every purple-enough candidate and merge those that resolve to the same ball."""
    out = []
    for c in cands:
        if c["purple"] < min_purple:
            continue
        rr, rx, ry = refine_radius(hsv, c["x"], c["y"], c["r"])
        c = dict(c, r=rr, x=rx, y=ry, r_raw=c["r"], x_raw=c["x"], y_raw=c["y"])
        dup = None
        for o in out:
            if math.hypot(o["x"] - rx, o["y"] - ry) <= 0.5 * max(o["r"], rr) + 2:
                dup = o
                break
        if dup is None:
            out.append(c)
        else:
            dup["res"] = max(dup["res"], c["res"])
            dup["area"] += c["area"]
    return out
