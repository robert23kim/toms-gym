"""Anchoring the lane on semantic landmarks (gutters, pins, the bowler) instead
of only on the ball path.

The lifting analyser in the same engine never asks "where are the bright pixels";
it asks for a named landmark (wrist, ankle, hip) and reasons about geometry
between them. This file tries the equivalent for the lane:

  gutters   the lane is the thing BETWEEN two gutters -> segment all three in one
            SAM decode and put the edge where lane_logit - gutter_logit changes sign
  pins      the pin cluster is a ruler of known real width (pins 7..10 span 40.8 in
            of a 41.5 in lane) sitting exactly at the lane's far end -> use it to
            anchor the top corners, where a board is 1-2 px and SAM is weakest
  landmarks no ball path at all: near anchor = the bowler's ball-side wrist at
            release (MediaPipe pose), far anchor = the pin cluster centre

Everything else (metric, truth, scoring, row schema) is loop 1's.
"""
import os
import time

import cv2
import numpy as np

import common as C
import edges as E
import run2
import sam2x as S

L = C.L

POSE_MODEL = os.path.expanduser(
    "~/code/bowling-app/analysis-engine/src/lifting/pose/.model_cache/pose_landmarker_full.task")

# Real-world bowling geometry (inches).
LANE_W_IN = 41.5
GUTTER_W_IN = 9.0
PIN_SPAN_IN = 36.0 + 4.766  # pin 7 to pin 10 centres + one pin diameter
PIN_TO_LANE = LANE_W_IN / PIN_SPAN_IN  # 1.017


# ------------------------------------------------------------------ first pass

def first_pass(stem, f, img, weights, n=3):
    """Loop-2 `soft` with `even_points_keep` prompts: keeps n prompts even when
    the ball sits on the path (pre-hit frames lost one to the avoid rule)."""
    pts = C.even_points_keep(stem, f, n=n)
    si = S.SamImage(img, weights)
    lg, sc = si.logit(pts)
    y_top, y_bot = L.gt_y(stem, f)
    comp = E.component(lg, pts)
    rows = E.soft_rows(lg, y_top, y_bot, pts, comp) if comp is not None else (np.array([]),) * 3
    fp = E.fit_pair(*rows)
    return dict(si=si, pts=pts, logit=lg, sam_score=sc, comp=comp, rows=rows, fit=fp,
                y_top=y_top, y_bot=y_bot)


def mae_of(stem, f, left, right, y_top, y_bot):
    return L.score(stem, L.lines_to_corners(left, right, y_top, y_bot), f)["board_mae"]


@run2.method("softk", "even_points_keep prompts (3 kept), sub-pixel soft edges - baseline for the anchor methods")
def softk(stem, weights, kind):
    f = C.frame_for(stem, kind)
    t0 = time.time()
    img = C.read_frame(stem, f)
    st = first_pass(stem, f, img, weights)
    p = {"points": st["pts"], "labels": [1] * len(st["pts"])}
    fp = st["fit"]
    extra = dict(fp[2], sam_score=round(st["sam_score"], 3)) if fp else {"sam_score": round(st["sam_score"], 3)}
    return [run2.finish(stem, f, st["comp"], (fp[0], fp[1]) if fp else None, p, t0, extra, kind)]


# ------------------------------------------------------------------ 1. gutters

def gutter_prompts(left, right, y_top, y_bot, k=0.12, fracs=(0.35, 0.60, 0.85)):
    """Points in the middle of each gutter: a gutter is 9 in next to a 41.5 in
    lane, so its centre sits 0.108 lane-widths outside the edge. Placed low
    enough down the lane that 0.12 * width is more than a couple of pixels."""
    gl, gr = [], []
    for fr in fracs:
        y = y_top + fr * (y_bot - y_top)
        xl = left[0] * y + left[1]
        xr = right[0] * y + right[1]
        w = xr - xl
        gl.append([int(round(xl - k * w)), int(round(y))])
        gr.append([int(round(xr + k * w)), int(round(y))])
    return gl, gr


def _cross(d, x0, band, rising, W):
    """Sub-pixel x where d changes sign in the requested direction, nearest x0."""
    lo = int(max(0, np.floor(x0 - band)))
    hi = int(min(W - 2, np.ceil(x0 + band)))
    if hi <= lo:
        return None
    seg = d[lo:hi + 1]
    a, b = seg[:-1], seg[1:]
    idx = np.where((a < 0) & (b >= 0))[0] if rising else np.where((a >= 0) & (b < 0))[0]
    if len(idx) == 0:
        return None
    i = idx[np.argmin(np.abs(lo + idx - x0))]
    da, db = float(a[i]), float(b[i])
    t = (-da / (db - da)) if db != da else 0.5
    return lo + i + t


def versus_rows(lane, gl_map, gr_map, left, right, y_top, y_bot, band_frac=0.30, min_band=8.0):
    """Per-row edges from the lane-vs-gutter logit difference."""
    H, W = lane.shape
    ys, ls, rs = [], [], []
    for y in range(int(y_top), int(y_bot) + 1):
        if y < 0 or y >= H:
            continue
        x_l = left[0] * y + left[1]
        x_r = right[0] * y + right[1]
        band = max(min_band, band_frac * (x_r - x_l))
        a = _cross(lane[y] - gl_map[y], x_l, band, True, W)
        b = _cross(lane[y] - gr_map[y], x_r, band, False, W)
        if a is None or b is None:
            continue
        ys.append(y)
        ls.append(a)
        rs.append(b)
    return np.array(ys, float), np.array(ls, float), np.array(rs, float)


@run2.method("gutters", "lane + left gutter + right gutter as three objects in one SAM decode; edge = where lane_logit - gutter_logit crosses zero")
def gutters(stem, weights, kind):
    f = C.frame_for(stem, kind)
    t0 = time.time()
    img = C.read_frame(stem, f)
    st = first_pass(stem, f, img, weights)
    fp = st["fit"]
    p = {"points": st["pts"], "labels": [1] * len(st["pts"])}
    if fp is None:
        return [run2.finish(stem, f, st["comp"], None, p, t0, {"stage": "first pass failed"}, kind)]
    left, right = fp[0], fp[1]
    y_top, y_bot = st["y_top"], st["y_bot"]
    gl, gr = gutter_prompts(left, right, y_top, y_bot)
    maps, scores = st["si"].logits([st["pts"], gl, gr])
    lane_lg, lg_l, lg_r = maps
    ys, xl, xr = versus_rows(lane_lg, lg_l, lg_r, left, right, y_top, y_bot)
    mp_ = E.fit_pair(ys, xl, xr)
    extra = {"first_pass_mae": mae_of(stem, f, left, right, y_top, y_bot),
             "vs_rows": int(len(ys)), "rows_possible": int(y_bot - y_top + 1),
             "sam_scores": [round(s, 3) for s in scores]}
    prompts = {"points": st["pts"] + gl + gr, "labels": [1] * (len(st["pts"]) + len(gl) + len(gr))}
    if mp_ is None:
        extra["stage"] = "no lane-vs-gutter crossings"
        return [run2.finish(stem, f, st["comp"], (left, right), prompts, t0, extra, kind)]
    extra.update(mp_[2])
    gcomp = E.component(lg_l, gl)
    if gcomp is not None:
        extra["gutter_left_px"] = int(gcomp.sum())
    return [run2.finish(stem, f, st["comp"], (mp_[0], mp_[1]), prompts, t0, extra, kind)]


# ------------------------------------------------------------------ 2. pins

PIN_H_FRAC = 15.0 / LANE_W_IN   # a pin is 15 in tall; verticals are not foreshortened


def pin_cluster(img, left, right, y_top, out_frac=0.30, up=0.80, down=0.20, debug=None):
    """Bright standing-pin cluster of THIS lane, found in a window anchored on
    the lane's own far end. Returns (x_left, x_right, y_base, info) in image
    coords or (None, None, None, info).

    Pins 7 and 10 span 40.8 in of a 41.5 in lane, so a window of the lane width
    plus 0.30 on each side cannot reach the next lane's cluster (its nearest pin
    is 0.44 lane-widths outside our edge).

    Blob extents are useless on their own: the pins merge with their own
    reflection on the deck into one blob (0.92-1.0 lane widths wide, 0.6 tall),
    and on a 720p phone the cluster splits across two blobs. So a blob only
    fixes the band of rows that holds the pin BODIES (its top, plus 15/41.5 of
    a lane width), and the extent comes from a column profile inside that band.
    """
    H, W = img.shape[:2]
    xl = left[0] * y_top + left[1]
    xr = right[0] * y_top + right[1]
    w = xr - xl
    x1, x2 = int(max(0, xl - out_frac * w)), int(min(W, xr + out_frac * w))
    y1, y2 = int(max(0, y_top - up * w)), int(min(H, y_top + down * w))
    info = {"pin_window": [x1, y1, x2, y2]}
    if x2 - x1 < 10 or y2 - y1 < 6:
        return None, None, None, info
    crop = img[y1:y2, x1:x2]
    cw = crop.shape[1]
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    white = np.clip(hsv[..., 2].astype(np.int32) - hsv[..., 1].astype(np.int32), 0, 255).astype(np.uint8)
    white = cv2.GaussianBlur(white, (3, 3), 0)
    _, binimg = cv2.threshold(white, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    bw_mask = (binimg > 0).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(bw_mask, 8)
    cand = []
    for i in range(1, n):
        bx, by, bbw, bbh, a = stats[i]
        if bbw > 0.85 * cw:          # a full-width band is the signage above the deck
            continue
        if bbh < 0.20 * w or a < 0.01 * w * w:
            continue
        cand.append((a, bx, by, bbw, bbh))
    info["pin_cands"] = len(cand)
    if not cand:
        return None, None, None, info
    _, bx, by, bbw, bbh = max(cand)
    band_top = int(by)
    band_bot = int(min(crop.shape[0], by + max(3, round(PIN_H_FRAC * w))))
    band_h = band_bot - band_top
    if band_h < 3:
        return None, None, None, info
    prof = bw_mask[band_top:band_bot].sum(0).astype(float)
    on = prof >= max(2.0, 0.45 * band_h)
    if on.sum() < 3:
        return None, None, None, info
    # the widest run of pin columns, bridging the gaps between pins (pin centres
    # are 6 in apart, a pin is 4.77 in wide, so a real gap is under 0.12 lane widths).
    # Without this the kickback panels and the ball return at the window's edges
    # add stray columns and the "cluster" comes out 1.5 lane widths wide.
    gap = max(3, int(round(0.12 * w)))
    idx = np.where(on)[0]
    runs, a0, prev = [], idx[0], idx[0]
    for v in idx[1:]:
        if v - prev > gap:
            runs.append((a0, prev))
            a0 = v
        prev = v
    runs.append((a0, prev))
    a0, a1 = max(runs, key=lambda r: r[1] - r[0])
    cols = np.array([a0, a1])
    info["pin_runs"] = len(runs)
    info["pin_band"] = [int(y1 + band_top), int(y1 + band_bot)]
    info["pin_cols_on"] = int(len(cols))
    info["pin_base_dy"] = round(float(y1 + band_bot - y_top), 1)
    if debug is not None:
        dbg = crop.copy()
        cv2.rectangle(dbg, (0, band_top), (cw - 1, band_bot), (255, 255, 0), 1)
        cv2.line(dbg, (int(cols[0]), 0), (int(cols[0]), dbg.shape[0]), (0, 0, 255), 1)
        cv2.line(dbg, (int(cols[-1]), 0), (int(cols[-1]), dbg.shape[0]), (0, 0, 255), 1)
        cv2.imwrite(debug, cv2.resize(dbg, None, fx=4, fy=4, interpolation=cv2.INTER_NEAREST))
    return float(x1 + cols[0]), float(x1 + cols[-1] + 1), float(y1 + band_bot), info


def pin_anchor(stem, f, img, left, right, y_top, weights, debug=None):
    """Pin-derived (top_left, top_right) in frame f. Pins only stand until the
    pin-hit marker, so they are measured on pin_hit-2 and warped into f."""
    fp_frame = C.frame_for(stem, "prehit")
    info = {"pin_frame": fp_frame}
    if fp_frame == f:
        pimg, pl, pr, py = img, left, right, y_top
    else:
        pimg = C.read_frame(stem, fp_frame)
        T = L.transform(stem, f, fp_frame)
        y_bot = L.gt_y(stem, f)[1]
        pl = L.warp_line(T, left, y_top, y_bot)
        pr = L.warp_line(T, right, y_top, y_bot)
        py = L.warp_pt(T, ((left[0] * y_top + left[1] + right[0] * y_top + right[1]) / 2, y_top))[1]
    xl, xr, ybase, pinfo = pin_cluster(pimg, pl, pr, py, debug=debug)
    info.update(pinfo)
    if xl is None:
        return None, None, info
    cx = 0.5 * (xl + xr)
    half = 0.5 * (xr - xl) * PIN_TO_LANE
    a = (cx - half, ybase)
    b = (cx + half, ybase)
    info["pin_span_px"] = round(xr - xl, 1)
    info["pin_lane_width_px"] = round(2 * half, 1)
    if fp_frame != f:
        T2 = L.transform(stem, fp_frame, f)
        a, b = L.warp_pt(T2, a), L.warp_pt(T2, b)
    return a, b, info


def fit_through(ys, xs, px, py, iters=3):
    """Robust line x = a*y + b constrained to pass through (px, py)."""
    ys = np.asarray(ys, float)
    xs = np.asarray(xs, float)
    if len(ys) < 8:
        return None
    dy, dx = ys - py, xs - px
    keep = np.ones(len(ys), bool)
    a = float(np.sum(dy * dx) / max(np.sum(dy * dy), 1e-9))
    for _ in range(iters):
        resid = np.abs(dx - a * dy)
        keep = resid <= max(3.0, 2.0 * np.median(resid) + 1e-6)
        if keep.sum() < 8:
            break
        a = float(np.sum(dy[keep] * dx[keep]) / max(np.sum(dy[keep] * dy[keep]), 1e-9))
    return (a, px - a * py), float(np.mean(np.abs(dx - a * dy)))


def lower_rows(rows, y_top, y_bot, frac=0.40):
    """SAM's sub-pixel rows from the lower part of the lane, where the lane is
    wide and the mask is trustworthy."""
    ys, xl, xr = rows
    if len(ys) == 0:
        return rows
    cut = y_top + frac * (y_bot - y_top)
    m = ys >= cut
    return ys[m], xl[m], xr[m]


def _pins_common(stem, weights, kind, mode):
    f = C.frame_for(stem, kind)
    t0 = time.time()
    img = C.read_frame(stem, f)
    st = first_pass(stem, f, img, weights)
    fp = st["fit"]
    p = {"points": st["pts"], "labels": [1] * len(st["pts"])}
    if fp is None:
        return [run2.finish(stem, f, st["comp"], None, p, t0, {"stage": "first pass failed"}, kind)]
    left, right = fp[0], fp[1]
    y_top, y_bot = st["y_top"], st["y_bot"]
    a, b, info = pin_anchor(stem, f, img, left, right, y_top, weights)
    truth = L.truth_corners(stem, f)
    info["truth_top_width_px"] = round(truth["top_right"][0] - truth["top_left"][0], 1)
    info["first_pass_mae"] = mae_of(stem, f, left, right, y_top, y_bot)
    prompts = dict(p)
    if a is None:
        info["stage"] = "no pin cluster"
        return [run2.finish(stem, f, st["comp"], (left, right), prompts, t0, info, kind)]
    info["pin_top_width_px"] = round(b[0] - a[0], 1)
    info["pin_vs_truth_width"] = round((b[0] - a[0]) / max(info["truth_top_width_px"], 1e-6), 3)
    info["pin_centre_px"] = round(0.5 * (a[0] + b[0]), 1)
    info["truth_centre_px"] = round(0.5 * (truth["top_left"][0] + truth["top_right"][0]), 1)
    info["pin_centre_err_px"] = round(info["pin_centre_px"] - info["truth_centre_px"], 1)
    prompts["bboxes"] = [[a[0], a[1] - 2, b[0], b[1] + 2]]

    ys, xl, xr = lower_rows(st["rows"], y_top, y_bot)
    info["rows_used"] = int(len(ys))
    if mode == "width":
        fl = fit_through(ys, xl, a[0], a[1])
        fr = fit_through(ys, xr, b[0], b[1])
        if fl is None or fr is None:
            info["stage"] = "too few lower rows"
            return [run2.finish(stem, f, st["comp"], (left, right), prompts, t0, info, kind)]
        lines = (fl[0], fr[0])
        info["fit_resid_px"] = round((fl[1] + fr[1]) / 2, 2)
    elif mode == "mid":  # keep SAM's top width, re-centre it on the pin cluster
        low = E.fit_pair(ys, xl, xr)
        if low is None:
            info["stage"] = "too few lower rows"
            return [run2.finish(stem, f, st["comp"], (left, right), prompts, t0, info, kind)]
        ll, rr = low[0], low[1]
        wl = ll[0] * a[1] + ll[1]
        wr = rr[0] * a[1] + rr[1]
        half = 0.5 * (wr - wl)
        cx = 0.5 * (a[0] + b[0])
        fl = fit_through(ys, xl, cx - half, a[1])
        fr = fit_through(ys, xr, cx + half, a[1])
        if fl is None or fr is None:
            info["stage"] = "too few lower rows"
            return [run2.finish(stem, f, st["comp"], (left, right), prompts, t0, info, kind)]
        lines = (fl[0], fr[0])
        info["sam_width_at_pins_px"] = round(2 * half, 1)
        info["fit_resid_px"] = round((fl[1] + fr[1]) / 2, 2)
    else:  # "centre": keep SAM's width/slope, pivot the pair about the bottom
        low = E.fit_pair(ys, xl, xr)
        if low is None:
            info["stage"] = "too few lower rows"
            return [run2.finish(stem, f, st["comp"], (left, right), prompts, t0, info, kind)]
        ll, rr = low[0], low[1]
        mid = 0.5 * ((ll[0] * y_top + ll[1]) + (rr[0] * y_top + rr[1]))
        dx = 0.5 * (a[0] + b[0]) - mid
        out = []
        for (aa, bb) in (ll, rr):
            na = aa + dx / (y_top - y_bot)
            out.append((na, bb - dx * y_bot / (y_top - y_bot)))
        lines = (out[0], out[1])
        info["centre_shift_px"] = round(dx, 2)
        info.update(low[2])
    return [run2.finish(stem, f, st["comp"], lines, prompts, t0, info, kind)]


@run2.method("pins", "pin cluster (40.8 of 41.5 in) sets both top corners; SAM's lower-60% sub-pixel rows set the slope")
def pins(stem, weights, kind):
    return _pins_common(stem, weights, kind, "width")


@run2.method("pins_c", "pin cluster sets only the lane CENTRE at the pin deck; SAM keeps the width, the pair pivots about the foul line")
def pins_c(stem, weights, kind):
    return _pins_common(stem, weights, kind, "centre")


@run2.method("pins_m", "pin cluster sets the lane CENTRE at the pin deck, SAM's own width is kept there and both lines are refitted through it")
def pins_m(stem, weights, kind):
    return _pins_common(stem, weights, kind, "mid")


# ------------------------------------------------------------------ 3. landmarks

_pose = None
WRIST = {"left": 15, "right": 16}
ANKLE = {"left": 27, "right": 28}
FOOT = {"left": 31, "right": 32}


def pose_landmarks(img):
    """MediaPipe PoseLandmarker (the model the lifting engine uses), IMAGE mode,
    up to 5 people. Returns a list of {idx: (x, y, vis)} in pixels."""
    global _pose
    import mediapipe as mp
    if _pose is None:
        base = mp.tasks.BaseOptions(model_asset_path=POSE_MODEL)
        opts = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=base, running_mode=mp.tasks.vision.RunningMode.IMAGE,
            num_poses=5, min_pose_detection_confidence=0.3)
        _pose = mp.tasks.vision.PoseLandmarker.create_from_options(opts)
    h, w = img.shape[:2]
    res = _pose.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(img, cv2.COLOR_BGR2RGB)))
    out = []
    for lms in (res.pose_landmarks or []):
        out.append({i: (lm.x * w, lm.y * h, lm.visibility) for i, lm in enumerate(lms)})
    return out


def release_anchor(stem, f, weights, back=3):
    """Near anchor without the ball path: the bowler's ball-side wrist at
    release, warped into frame f. Falls back to the foot, then to the bottom
    centre of the YOLO person box."""
    fs, pos = L.trajectory(stem)
    f_rel = max(0, fs[0] - back)
    img = C.read_frame(stem, f_rel)
    ball = pos[fs[0]][:2]
    info = {"release_frame": f_rel}
    people = []
    try:
        people = pose_landmarks(img)
    except Exception as e:  # noqa: BLE001
        info["pose_error"] = f"{type(e).__name__}: {e}"[:160]
    # 1. the bowler among several people: the pose with any keypoint nearest the ball
    def near_ball(lms):
        return min(float(np.hypot(x - ball[0], y - ball[1])) for (x, y, v) in lms.values() if v > 0.2) \
            if any(v > 0.2 for (_, _, v) in lms.values()) else 1e18
    best, bd, src = None, 1e18, None
    if people:
        lms = min(people, key=near_ball)
        info["poses"] = len(people)
        # 2. ball-side wrist if it is visible at all; the swing hides it more often
        #    than not, so fall back to the leading foot, then the ankle.
        for group, name, vmin in ((WRIST, "wrist", 0.20), (FOOT, "foot", 0.30), (ANKLE, "ankle", 0.30)):
            for side, idx in group.items():
                x, y, v = lms.get(idx, (0, 0, 0))
                d = float(np.hypot(x - ball[0], y - ball[1]))
                if v > vmin and d < bd:
                    best, bd, src = (x, y), d, f"pose_{name}_{side}"
            if best is not None:
                break
        info["pose_keypoint_vis"] = {f"{n}_{s}": round(lms.get(i, (0, 0, 0))[2], 3)
                                     for g, n in ((WRIST, "wrist"), (FOOT, "foot")) for s, i in g.items()}
    else:
        info["poses"] = 0
    if best is None:
        boxes = L.person_boxes(img)
        if boxes:
            bx = min(boxes, key=lambda q: abs((q[0] + q[2]) / 2 - ball[0]))
            best, src = ((bx[0] + bx[2]) / 2, float(bx[3])), "yolo_box_bottom"
    info["near_source"] = src
    info["near_dist_to_ball_px"] = round(bd, 1) if best is not None else None
    if best is None:
        return None, info
    info["near_raw"] = [round(best[0], 1), round(best[1], 1)]
    if f_rel != f:
        best = L.warp_pt(L.transform(stem, f_rel, f), best)
    return best, info


@run2.method("landmarks", "no ball path: prompts on the segment from the bowler's ball-side wrist at release to the pin cluster centre")
def landmarks(stem, weights, kind):
    f = C.frame_for(stem, kind)
    t0 = time.time()
    img = C.read_frame(stem, f)
    st = first_pass(stem, f, img, weights)   # only to locate the pin window
    info = {}
    if st["fit"] is None:
        return [run2.finish(stem, f, st["comp"], None, {}, t0, {"stage": "no reference lane"}, kind)]
    left, right = st["fit"][0], st["fit"][1]
    y_top, y_bot = st["y_top"], st["y_bot"]
    info["ballpath_mae"] = mae_of(stem, f, left, right, y_top, y_bot)
    a, b, pinfo = pin_anchor(stem, f, img, left, right, y_top, weights)
    info.update(pinfo)
    near, ninfo = release_anchor(stem, f, weights)
    info.update(ninfo)
    if a is None or near is None:
        info["stage"] = "missing anchor"
        return [run2.finish(stem, f, st["comp"], None, {}, t0, info, kind)]
    far = (0.5 * (a[0] + b[0]), 0.5 * (a[1] + b[1]))
    pts = [[int(round(near[0] + t * (far[0] - near[0]))), int(round(near[1] + t * (far[1] - near[1])))]
           for t in (0.15, 0.50, 0.85)]
    info["anchor_near"] = [round(near[0], 1), round(near[1], 1)]
    info["anchor_far"] = [round(far[0], 1), round(far[1], 1)]
    lg, sc = st["si"].logit(pts)
    comp = E.component(lg, pts)
    prompts = {"points": pts, "labels": [1] * len(pts), "bboxes": [[a[0], a[1] - 2, b[0], b[1] + 2]]}
    if comp is None:
        info["stage"] = "no mask"
        return [run2.finish(stem, f, None, None, prompts, t0, info, kind)]
    ys, xl, xr = E.soft_rows(lg, y_top, y_bot, pts, comp)
    fp = E.fit_pair(ys, xl, xr)
    info["sam_score"] = round(sc, 3)
    info.update(fp[2] if fp else {})
    return [run2.finish(stem, f, comp, (fp[0], fp[1]) if fp else None, prompts, t0, info, kind)]


@run2.method("landmarks_pin", "landmarks prompts, then the pin cluster anchors the top corners (methods 3 + 2 combined)")
def landmarks_pin(stem, weights, kind):
    out = landmarks(stem, weights, kind)
    row, corners, mask = out[0]
    if not row.get("ok"):
        return out
    f, t0 = row["frame"], time.time() - row["latency_s"]
    stem_img = C.read_frame(stem, f)
    y_top, y_bot = L.gt_y(stem, f)
    # rebuild the lines from the corners we already have, then re-anchor the top
    left = ((corners["bottom_left"][0] - corners["top_left"][0]) / (y_bot - y_top), 0)
    left = (left[0], corners["top_left"][0] - left[0] * y_top)
    right = ((corners["bottom_right"][0] - corners["top_right"][0]) / (y_bot - y_top), 0)
    right = (right[0], corners["top_right"][0] - right[0] * y_top)
    a, b, info = pin_anchor(stem, f, stem_img, left, right, y_top, weights)
    # only carry the descriptive fields: run2.finish applies `extra` AFTER the
    # score, so re-using the whole landmarks row would overwrite board_mae with
    # the pre-anchor value and the row would silently report the wrong method.
    extra = {k: row[k] for k in ("ballpath_mae", "near_source", "poses", "anchor_near", "anchor_far", "sam_score") if k in row}
    extra["landmarks_only_mae"] = row["board_mae"]
    extra.update(info)
    if a is None:
        return [run2.finish(stem, f, mask, (left, right), row["prompts"], t0, extra, kind)]
    st = first_pass(stem, f, stem_img, weights)
    ys, xl, xr = lower_rows(st["rows"], y_top, y_bot)
    fl = fit_through(ys, xl, a[0], a[1])
    fr = fit_through(ys, xr, b[0], b[1])
    if fl is None or fr is None:
        return [run2.finish(stem, f, mask, (left, right), row["prompts"], t0, extra, kind)]
    return [run2.finish(stem, f, mask, (fl[0], fr[0]), row["prompts"], t0, extra, kind)]


# ------------------------------------------------------------------ 4. pins + zoom

@run2.method("pins_zoom", "pin-anchored top corners plus a second SAM pass on a crop of the top 55% of the lane (pin end gets anchor AND resolution)")
def pins_zoom(stem, weights, kind):
    f = C.frame_for(stem, kind)
    t0 = time.time()
    img = C.read_frame(stem, f)
    H, W = img.shape[:2]
    st = first_pass(stem, f, img, weights)
    fp = st["fit"]
    p = {"points": st["pts"], "labels": [1] * len(st["pts"])}
    if fp is None:
        return [run2.finish(stem, f, st["comp"], None, p, t0, {"stage": "first pass failed"}, kind)]
    left, right = fp[0], fp[1]
    y_top, y_bot = st["y_top"], st["y_bot"]
    y1 = y_top + 0.55 * (y_bot - y_top)
    box = E.crop_box(left, right, y_top, y1, W, H)
    x1, ya, x2, yb = box
    zpts = C.path_points_between(stem, f, ya, yb, n=3)
    samples = [(st["rows"][0], st["rows"][1], st["rows"][2], 0)]
    info = {"crop": list(box), "first_pass_mae": mae_of(stem, f, left, right, y_top, y_bot)}
    if len(zpts) >= 1:
        lgz, scz = S.crop_logit(img, box, zpts, weights)
        anch = [(x - x1, y - ya) for x, y in zpts]
        czomp = E.component(lgz, anch)
        if czomp is not None:
            zys, zxl, zxr = E.soft_rows(lgz, max(0, y_top - ya), min(lgz.shape[0] - 1, y1 - ya), anch, czomp)
            samples.append((zys + ya, zxl + x1, zxr + x1, 1))
            info["zoom_rows"] = int(len(zys))
    ys, xl, xr = E.merge_rows(samples)
    a, b, pinfo = pin_anchor(stem, f, img, left, right, y_top, weights)
    info.update(pinfo)
    prompts = {"points": st["pts"] + zpts, "labels": [1] * (len(st["pts"]) + len(zpts)), "bboxes": [list(box)]}
    merged = E.fit_pair(ys, xl, xr)
    if merged:
        info["merged_mae"] = mae_of(stem, f, merged[0], merged[1], y_top, y_bot)
    if a is None:
        info["stage"] = "no pin cluster"
        lines = (merged[0], merged[1]) if merged else (left, right)
        return [run2.finish(stem, f, st["comp"], lines, prompts, t0, info, kind)]
    info["pin_top_width_px"] = round(b[0] - a[0], 1)
    prompts["bboxes"].append([a[0], a[1] - 2, b[0], b[1] + 2])
    lys, lxl, lxr = lower_rows((ys, xl, xr), y_top, y_bot)
    fl = fit_through(lys, lxl, a[0], a[1])
    fr = fit_through(lys, lxr, b[0], b[1])
    if fl is None or fr is None:
        lines = (merged[0], merged[1]) if merged else (left, right)
        return [run2.finish(stem, f, st["comp"], lines, prompts, t0, info, kind)]
    info["fit_resid_px"] = round((fl[1] + fr[1]) / 2, 2)
    return [run2.finish(stem, f, st["comp"], (fl[0], fr[0]), prompts, t0, info, kind)]


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--methods", default="softk,gutters,pins,pins_c,landmarks")
    ap.add_argument("--kinds", default="prehit,last")
    ap.add_argument("--weights", default="sam2.1_b.pt")
    ap.add_argument("--tag", default="")
    ap.add_argument("--stems", default=",".join(C.STEMS))
    a = ap.parse_args()
    run2.run(a.methods.split(","), a.kinds.split(","), a.weights, a.tag, a.stems.split(","))
