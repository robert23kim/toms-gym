"""Lane-first ball tracker: per-frame lane edges, purple candidates inside the lane, a constant-velocity
Kalman filter in lane coordinates (u = fraction across from the left edge, Z = feet down the lane).
Depth uses the lane's vanishing point: Z = K / (y - y_vp) with K = 60 ft * (y_pd - y_vp) taken as a running
median over frames whose pin-deck row is in frame (per-frame pin-row jitter would otherwise move the depth)."""
import math
import statistics

import numpy as np

import ball as BL
import lane as LN

BALL_OVER_LANE = 4.25 / 41.5  # ball radius / lane width
GATE_MIN_PX = 40.0
GATE_MAX_PX = 300.0
MAX_MISSES = 12
FILL_MAX = 6
R_RATIO_MAX = 2.4
LANE_FT = 60.0
LANE_JUMP_PX = 200.0
COAST_MAX = 3


class KF:
    """CV Kalman on [u, Z, du, dZ] (u in lane widths, Z in feet, per frame). Z may be unobserved."""

    def __init__(self, u, z):
        self.x = np.array([u, z if z is not None else 0.0, 0.0, 1.0])
        self.P = np.diag([0.01, 100.0 if z is None else 1.0, 0.01, 1.0])
        self.q = np.diag([1e-5, 0.01, 2e-5, 0.02])
        self.z_seen = z is not None

    def predict(self):
        F = np.array([[1, 0, 1, 0], [0, 1, 0, 1], [0, 0, 1, 0], [0, 0, 0, 1]], float)
        self.x = F @ self.x
        self.P = F @ self.P @ F.T + self.q
        return self.x[0], self.x[1]

    def update(self, u, z, su=0.01, sz=0.5):
        if z is None:
            Hm = np.array([[1, 0, 0, 0]], float)
            R = np.array([[su ** 2]])
            meas = np.array([u])
        else:
            Hm = np.array([[1, 0, 0, 0], [0, 1, 0, 0]], float)
            R = np.diag([su ** 2, sz ** 2])
            meas = np.array([u, z])
            if not self.z_seen:
                self.x[1] = z
                self.P[1, 1] = 1.0
                self.z_seen = True
        y = meas - Hm @ self.x
        S = Hm @ self.P @ Hm.T + R
        K = self.P @ Hm.T @ np.linalg.inv(S)
        self.x = self.x + K @ y
        self.P = (np.eye(4) - K @ Hm) @ self.P


def pd_in_frame(lf):
    if lf is None:
        return False
    if lf.pd_y * LN.SCALE <= 30:
        return False
    return 40.0 <= lf.width(lf.pd_y) <= 420.0


def vanishing_y(lf):
    (al, bl), (ar, br) = lf.left, lf.right
    if abs(al - ar) < 1e-9:
        return None
    return (br - bl) / (al - ar)


def ring_fraction(mask_small, x, y, r):
    """Fraction of lane-mask pixels in the annulus [1.3r, 2.2r] around (x, y) (full-res in, half-res mask)."""
    s = LN.SCALE
    cx, cy, rr = x * s, y * s, max(r * s, 2.0)
    h, w = mask_small.shape
    x0, x1 = int(max(0, cx - 2.2 * rr)), int(min(w, cx + 2.2 * rr + 1))
    y0, y1 = int(max(0, cy - 2.2 * rr)), int(min(h, cy + 2.2 * rr + 1))
    if x1 <= x0 or y1 <= y0:
        return 0.0
    yy, xx = np.mgrid[y0:y1, x0:x1]
    d = np.hypot(xx - cx, yy - cy)
    ring = (d >= 1.3 * rr) & (d <= 2.2 * rr)
    n = int(ring.sum())
    if n == 0:
        return 0.0
    return float((mask_small[y0:y1, x0:x1][ring] > 0).sum()) / n


def plausible(c, lf, mask_small, depth):
    """Lane-plausible candidate: inside the lane, radius near the lane prior, lane wood around it
    (unless it is at the pin row). Returns (ok, ratio, u, z, ring)."""
    u = lf.u(c["x"], c["y"])
    z = depth(c["y"])
    r_e = max(BALL_OVER_LANE * lf.width(c["y"]), 2.0)
    ratio = abs(math.log(max(c["r"], 1.0) / r_e))
    ring = ring_fraction(mask_small, c["x"], c["y"], max(c["r"], r_e))
    at_pins = c["y"] < lf.pd_y + 3.0 * c["r"]
    near_pins = c["y"] < lf.pd_y + 4.0 * r_e and r_e <= 14.0
    lim = math.log(5.0) if near_pins and c["r"] >= 2.0 else math.log(R_RATIO_MAX)
    ok = (-0.03 <= u <= 1.03) and ratio <= lim and (ring >= 0.25 or at_pins)
    if z is not None and not (0.0 < z < 75.0):
        ok = False
    return ok, ratio, u, z, ring


def track_cut(frames, log=None):
    recs, lanes, pd_ok, k_samples = [], {}, {}, []
    prev_mask, prev_gq, kf, last = None, None, None, None
    lane_prev, coast = None, 0
    S = np.zeros(2)  # cumulative camera shift
    dets_hist = []   # (f, x_stab, y_stab)
    misses = fills = 0
    started, ended = False, None
    for f, img in frames:
        gq = BL.grey_q(img)
        shift = (0.0, 0.0)
        if prev_gq is not None:
            dx, dy, resp = BL.global_shift(prev_gq, gq)
            if abs(dx) < 150 and abs(dy) < 150:
                shift = (dx, dy)
        prev_gq = gq
        S = S + np.array(shift)
        pred_xy, pred_r = None, None
        if last is not None:
            pred_r = last["r"]
            v = np.zeros(2)
            if len(dets_hist) >= 2:
                vs = []
                hh = dets_hist[-4:]
                for (fa, xa, ya), (fb, xb, yb) in zip(hh[:-1], hh[1:]):
                    if 0 < fb - fa <= 2 and hh[-1][0] - fb <= 3:
                        vs.append([(xb - xa) / float(fb - fa), (yb - ya) / float(fb - fa)])
                if vs:
                    v = np.median(np.array(vs), axis=0)
            fl, xl_, yl_ = dets_hist[-1] if dets_hist else (f - 1, last["x"] - S[0] + shift[0], last["y"] - S[1] + shift[1])
            steps = min(f - fl, 2)
            if misses >= 3:
                v = np.zeros(2)
            pred_xy = (xl_ + v[0] * steps + S[0], yl_ + v[1] * steps + S[1])
        m = LN.lane_mask(img)
        lf, info = LN.fit_lane(m, prev_mask, pred_xy)
        if lf is not None and lane_prev is not None and coast < COAST_MAX:
            ym = 0.5 * (max(lane_prev.pd_y, 0.0) + img.shape[0])
            exp = lane_prev.shifted(*shift)
            jump = max(abs(lf.xl(ym) - exp.xl(ym)), abs(lf.xr(ym) - exp.xr(ym)))
            if jump > LANE_JUMP_PX or abs(lf.y_vp() - exp.y_vp()) > 400:
                info = {**info, "why": "inconsistent with previous lane", "jump": round(jump)}
                lf = None
        if lf is not None:
            lab, _ = LN.components(m)
            prev_mask = (lab == lf.comp_id).astype(np.uint8)
            lane_prev, coast = lf, 0
        elif lane_prev is not None and coast < COAST_MAX:
            coast += 1
            lf = lane_prev.shifted(*shift)
            lane_prev = lf
            info = {**info, "coast": coast}
        else:
            lf, lane_prev, coast = None, None, 0
        ok = pd_in_frame(lf)
        y_vp = vanishing_y(lf) if lf is not None else None
        if lf is not None:
            lanes[f] = lf
        pd_ok[f] = ok
        if ok and y_vp is not None and 40.0 < lf.pd_y - y_vp < 600.0 and min(lf.n_in) >= 100:
            k_samples.append(LANE_FT * (lf.pd_y - y_vp))
        K = statistics.median(k_samples) if k_samples else None

        def depth(y):
            if K is None or y_vp is None or y - y_vp < 5:
                return None
            return K / (y - y_vp)

        def y_of(z):
            return y_vp + K / max(z, 1e-3)

        if kf is not None:
            u_p, z_p = kf.predict()
            if lf is not None and last is not None:
                y_p = min(max(pred_xy[1], 0.0), img.shape[0] - 1.0)
                x_lane = lf.xl(y_p) + u_p * lf.width(y_p)
                r_p = max(BALL_OVER_LANE * lf.width(y_p), 2.0)
                if abs(x_lane - pred_xy[0]) <= 2.5 * r_p + 40.0:
                    pred_xy = (x_lane, y_p)
                else:
                    pred_xy = (pred_xy[0], y_p)
                    kf.x[0] = lf.u(pred_xy[0], y_p)
                    kf.x[2] = 0.0
                    kf.P[0, 0] = 0.01
                pred_r = r_p
        if ended is not None:
            continue
        roi = lf.roi_mask(img.shape) if lf is not None else None
        cands = BL.candidates(img, roi)
        plaus = {}
        if lf is not None:
            for i, c in enumerate(cands):
                pl = plausible(c, lf, m, depth)
                if pl[0]:
                    plaus[i] = pl
        det = None
        if not started:
            h = img.shape[0]
            if lf is not None:
                good = [cands[i] for i in plaus if cands[i]["area"] >= 300]
                if good:
                    det = good[0]
            else:
                big = [c for c in cands if c["area"] >= 2500 and c["y"] > 0.6 * h and c["fill"] >= 0.45
                       and 0.5 <= c["w"] / float(max(c["h"], 1)) <= 2.0]
                if big:
                    det = big[0]
            started = det is not None
        else:
            gate = min(max(2.5 * pred_r, GATE_MIN_PX) * (1.0 + 0.5 * misses), GATE_MAX_PX)
            best, bs = None, 1e9
            for i, c in enumerate(cands):
                if lf is not None and i not in plaus:
                    continue
                d = math.hypot(c["x"] - pred_xy[0], c["y"] - pred_xy[1])
                if d > gate:
                    continue
                if lf is not None:
                    ratio = plaus[i][1]
                else:
                    ratio = abs(math.log(max(c["r"], 1.0) / max(pred_r, 2.0)))
                    if ratio > math.log(R_RATIO_MAX) or c["fill"] < 0.3:
                        continue
                s_ = d / gate + 0.5 * ratio
                if s_ < bs:
                    bs, best = s_, c
            if best is None and lf is not None and misses >= 1 and plaus:
                z_last = last.get("z") or 0.0
                lim = math.log(1.8) if ok else math.log(1.5)
                opts = [(plaus[i][1], i) for i in plaus
                        if plaus[i][1] <= lim and cands[i]["fill"] >= (0.3 if cands[i]["r"] >= 40 else 0.4)
                        and (plaus[i][4] >= (0.25 if cands[i]["r"] >= 40 else 0.5) or cands[i]["y"] < lf.pd_y + 3.0 * cands[i]["r"])
                        and cands[i]["y"] > lf.pd_y - cands[i]["r"]
                        and (plaus[i][3] is None or plaus[i][3] > z_last - 5.0)]
                if opts:
                    best = cands[min(opts)[1]]
            det = best
        rec = None
        if det is not None:
            misses, fills = 0, 0
            rec = {"f": f, "x": det["x"], "y": det["y"], "r": det["r"], "conf": round(float(det["fill"]), 2), "src": "det"}
            dets_hist.append((f, det["x"] - S[0], det["y"] - S[1]))
        elif started and pred_xy is not None:
            misses += 1
            if kf is not None and lf is not None and fills < FILL_MAX and np.all(np.isfinite(pred_xy)):
                uf = lf.u(pred_xy[0], pred_xy[1])
                if -0.05 <= uf <= 1.05 and lf.pd_y - pred_r <= pred_xy[1] <= img.shape[0] - 1 and lf.width(pred_xy[1]) > 10:
                    fills += 1
                    rec = {"f": f, "x": pred_xy[0], "y": pred_xy[1], "r": pred_r, "conf": 0.0, "src": "fill"}
            if misses > MAX_MISSES:
                ended = f
        if rec is not None:
            if det is not None:
                r_e = max(BALL_OVER_LANE * lf.width(rec["y"]), 2.0) if lf is not None and lf.width(rec["y"]) > 10 else None
                rec["ratio"] = None if r_e is None else round(abs(math.log(max(rec["r"], 1.0) / r_e)), 3)
            if lf is not None and lf.width(rec["y"]) > 10 and (y_vp is None or rec["y"] > y_vp + 20):
                rec["u"] = lf.u(rec["x"], rec["y"])
                rec["board"] = lf.board(rec["x"], rec["y"])
                z = depth(rec["y"])
                if z is not None:
                    rec["z"] = z
                if rec["src"] == "det":
                    su = max(0.01, 0.3 * rec["r"] / lf.width(rec["y"]))
                    if kf is None:
                        kf = KF(rec["u"], z)
                    else:
                        kf.update(rec["u"], z, su=su, sz=0.3 + 0.03 * (z or 0.0))
                    rec["u_kf"] = float(kf.x[0])
                    rec["board_kf"] = (1.0 - float(kf.x[0])) * 38.0 + 1.0
            recs.append(rec)
            last = rec
        if log is not None:
            log.append({"f": f, "lane": info, "ok": ok, "n_cands": len(cands), "n_plaus": len(plaus), "det": det is not None,
                        "best_ratio": None if not plaus else round(min(p[1] for p in plaus.values()), 2), "misses": misses,
                        "shift": [round(shift[0], 1), round(shift[1], 1)], "K": None if K is None else round(K),
                        "y_vp": None if y_vp is None else round(y_vp), "pd_y": None if lf is None else round(lf.pd_y),
                        "pred": None if pred_xy is None else [round(pred_xy[0]), round(pred_xy[1])]})
    return {"recs": recs, "lanes": lanes, "lane_ok": pd_ok, "ended": ended}
