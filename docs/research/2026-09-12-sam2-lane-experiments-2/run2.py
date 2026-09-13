"""Loop 2 runner: same output schema as run_methods.py (one row per video per
method in results/<method>_<kind>.json, one overlay per row), new methods.

usage: run2.py [--methods a,b] [--kinds last,prehit] [--weights sam2.1_b.pt] [--tag _x] [--list]

A method is fn(stem, weights, kind) -> list of (row, corners, mask). Rows carry
lane_sam.score plus whatever the method wants to report. The metric, truth and
prompts are the previous folder's (see common.py).
"""
import argparse
import json
import time
import traceback

import cv2
import numpy as np

import common as C
import edges as E
import sam2x as S

gt, L = C.gt, C.L
METHODS = {}


def method(name, desc, kinds=None):
    """kinds=None accepts any frame kind (last, prehit, prehit-N, pre, mid)."""
    def deco(fn):
        METHODS[name] = (fn, desc, kinds)
        return fn
    return deco


def finish(stem, frame, mask, lines, prompts, t0, extra=None, kind=None):
    y_top, y_bot = L.gt_y(stem, frame)
    row = {"stem": stem, "frame": frame, "kind": kind, "latency_s": round(time.time() - t0, 2), "prompts": prompts}
    if lines is None:
        row["ok"] = False
        row.update(extra or {})
        return row, None, mask
    corners = L.lines_to_corners(lines[0], lines[1], y_top, y_bot)
    row.update(L.score(stem, corners, frame))
    row.update(extra or {})
    row["ok"] = True
    row["corners"] = {k: [round(v[0], 1), round(v[1], 1)] for k, v in corners.items()}
    return row, corners, mask


PROMPT_RULE = "old"   # "old" = loop-1 track_points_even (drops points near the ball); "keep" = common.even_points_keep


def even_points(stem, f, n=3, lo=0.15, hi=0.85):
    if PROMPT_RULE == "keep":
        return C.even_points_keep(stem, f, n=n, lo=lo, hi=hi)
    return L.track_points_even(stem, f, n=n, lo=lo, hi=hi)


def even_prompts(stem, f, n=3):
    pts = even_points(stem, f, n=n)
    return {"points": pts, "labels": [1] * len(pts)}


def pos(prompts):
    return [p for p, l in zip(prompts.get("points", []), prompts.get("labels", [])) if l == 1]


# ------------------------------------------------------------------ baselines

@method("even3", "3 evenly spaced path points, binary mask, row-extreme edge fit (loop-1 baseline, same code path)")
def even3(stem, weights, kind):
    f = C.frame_for(stem, kind)
    t0 = time.time()
    img = C.read_frame(stem, f)
    p = even_prompts(stem, f, 3)
    mask = L.predict_mask(L.model(weights), img, p["points"], p["labels"])
    y_top, y_bot = L.gt_y(stem, f)
    fit = L.fit_edges(mask, y_top, y_bot, pos(p)) if mask is not None else None
    lines = (fit[0], fit[1]) if fit else None
    return [finish(stem, f, mask, lines, p, t0, fit[2] if fit else None, kind)]


@method("even5", "5 evenly spaced path points, binary mask, row-extreme edge fit (loop-1 even_last)")
def even5(stem, weights, kind):
    f = C.frame_for(stem, kind)
    t0 = time.time()
    img = C.read_frame(stem, f)
    p = even_prompts(stem, f, 5)
    mask = L.predict_mask(L.model(weights), img, p["points"], p["labels"])
    y_top, y_bot = L.gt_y(stem, f)
    fit = L.fit_edges(mask, y_top, y_bot, pos(p)) if mask is not None else None
    lines = (fit[0], fit[1]) if fit else None
    return [finish(stem, f, mask, lines, p, t0, fit[2] if fit else None, kind)]


# ------------------------------------------------------------------ soft edges

def _soft_full2(stem, f, img, weights, n=3):
    """Full-frame logits with even path prompts -> per-row sub-pixel samples,
    plus the encoded image so more prompts can be decoded on it."""
    p = even_prompts(stem, f, n)
    si = S.SamImage(img, weights)
    lg, sc = si.logit(p["points"], p["labels"])
    y_top, y_bot = L.gt_y(stem, f)
    comp = E.component(lg, pos(p))
    ys, xl, xr = E.soft_rows(lg, y_top, y_bot, pos(p), comp)
    return si, p, lg, sc, comp, (ys, xl, xr)


def _soft_full(stem, f, img, weights, n=3):
    return _soft_full2(stem, f, img, weights, n)[1:]


@method("soft", "even3 prompts, sub-pixel edges from the logit zero crossings")
def soft(stem, weights, kind):
    f = C.frame_for(stem, kind)
    t0 = time.time()
    img = C.read_frame(stem, f)
    p, lg, sc, comp, (ys, xl, xr) = _soft_full(stem, f, img, weights)
    fp = E.fit_pair(ys, xl, xr)
    lines = (fp[0], fp[1]) if fp else None
    extra = dict(fp[2], sam_score=round(sc, 3)) if fp else {"sam_score": round(sc, 3)}
    return [finish(stem, f, comp, lines, p, t0, extra, kind)]


@method("snap2", "soft, then polarity-aware sub-pixel gradient snap within +-6 px (weak rows dropped)")
def snap2(stem, weights, kind):
    f = C.frame_for(stem, kind)
    t0 = time.time()
    img = C.read_frame(stem, f)
    p, lg, sc, comp, (ys, xl, xr) = _soft_full(stem, f, img, weights)
    fp = E.fit_pair(ys, xl, xr)
    if fp is None:
        return [finish(stem, f, comp, None, p, t0, None, kind)]
    y_top, y_bot = L.gt_y(stem, f)
    pol = E.polarity(img, comp, y_top, y_bot)
    left, right, info = E.snap_pair(img, fp[0], fp[1], y_top, y_bot, pol)
    info["polarity"] = pol
    info["before_snap_mae"] = L.score(stem, L.lines_to_corners(fp[0], fp[1], y_top, y_bot), f)["board_mae"]
    return [finish(stem, f, comp, (left, right), p, t0, info, kind)]


# ------------------------------------------------------------------ zoom / tiles

def _zoom_rows(stem, f, img, weights, left, right, y0, y1, n=3, lo=0.15, hi=0.85):
    """SAM on a crop of rows y0..y1 (upscaled to 1024 by the letterbox),
    prompted with path points inside the crop; sub-pixel rows in full coords."""
    H, W = img.shape[:2]
    box = E.crop_box(left, right, y0, y1, W, H)
    x1, ya, x2, yb = box
    pts = C.path_points_between(stem, f, ya, yb, n=n, lo=lo, hi=hi)
    if len(pts) < 1:
        return None, box, pts
    lg, sc = S.crop_logit(img, box, pts, weights)
    local_anchors = [(x - x1, y - y1) for x, y in pts]
    comp = E.component(lg, local_anchors)
    if comp is None:
        return None, box, pts
    ys, xl, xr = E.soft_rows(lg, max(0, y0 - ya), min(lg.shape[0] - 1, y1 - ya), local_anchors, comp)
    return (ys + ya, xl + x1, xr + x1, comp, sc), box, pts


def _paste(full_comp, comp, box):
    out = full_comp.copy() if full_comp is not None else None
    if out is None:
        return None
    x1, y1, x2, y2 = box
    out[y1:y2, x1:x2] = comp
    return out


@method("zoom", "soft full frame, then a second SAM pass on a crop of the top 55% of the lane (pin end at 2-4x)")
def zoom(stem, weights, kind):
    f = C.frame_for(stem, kind)
    t0 = time.time()
    img = C.read_frame(stem, f)
    p, lg, sc, comp, full = _soft_full(stem, f, img, weights)
    fp = E.fit_pair(*full)
    if fp is None:
        return [finish(stem, f, comp, None, p, t0, None, kind)]
    y_top, y_bot = L.gt_y(stem, f)
    y1 = y_top + 0.55 * (y_bot - y_top)
    z, box, zpts = _zoom_rows(stem, f, img, weights, fp[0], fp[1], y_top, y1)
    extra = {"crop": list(box), "crop_prompts": zpts, "full_mae": L.score(stem, L.lines_to_corners(fp[0], fp[1], y_top, y_bot), f)["board_mae"]}
    if z is None:
        extra["zoom"] = "failed"
        return [finish(stem, f, comp, (fp[0], fp[1]), p, t0, extra, kind)]
    ys, xl, xr = E.merge_rows([(full[0], full[1], full[2], 0), (z[0], z[1], z[2], 1)])
    mp = E.fit_pair(ys, xl, xr)
    extra.update(mp[2] if mp else {})
    extra["zoom_scale"] = round(1024 / max(box[2] - box[0], box[3] - box[1]), 2)
    prompts = {"points": p["points"] + zpts, "labels": [1] * (len(p["points"]) + len(zpts)), "bboxes": [list(box)]}
    return [finish(stem, f, _paste(comp, z[3], box), (mp[0], mp[1]) if mp else (fp[0], fp[1]), prompts, t0, extra, kind)]


@method("tiles", "soft full frame, then SAM on three overlapping crops (top / middle / bottom of the lane), merged rows")
def tiles(stem, weights, kind):
    f = C.frame_for(stem, kind)
    t0 = time.time()
    img = C.read_frame(stem, f)
    p, lg, sc, comp, full = _soft_full(stem, f, img, weights)
    fp = E.fit_pair(*full)
    if fp is None:
        return [finish(stem, f, comp, None, p, t0, None, kind)]
    y_top, y_bot = L.gt_y(stem, f)
    hl = y_bot - y_top
    bands = [(0.0, 0.45), (0.30, 0.75), (0.60, 1.0)]
    samples = [(full[0], full[1], full[2], 0)]
    boxes, allpts = [], []
    pasted = comp
    for i, (a, b) in enumerate(bands):
        z, box, zpts = _zoom_rows(stem, f, img, weights, fp[0], fp[1], y_top + a * hl, y_top + b * hl)
        boxes.append(list(box))
        allpts += zpts
        if z is None:
            continue
        # rows near a band's centre win over neighbours: priority falls off with distance to centre
        c = y_top + 0.5 * (a + b) * hl
        pr = 10 - np.abs(z[0] - c) / (0.5 * (b - a) * hl + 1e-6)
        for y, l, r, q in zip(z[0], z[1], z[2], pr):
            samples.append((np.array([y]), np.array([l]), np.array([r]), float(q)))
        pasted = _paste(pasted, z[3], box)
    ys, xl, xr = E.merge_rows(samples)
    mp = E.fit_pair(ys, xl, xr)
    extra = {"crops": boxes, "full_mae": L.score(stem, L.lines_to_corners(fp[0], fp[1], y_top, y_bot), f)["board_mae"]}
    extra.update(mp[2] if mp else {})
    prompts = {"points": p["points"] + allpts, "labels": [1] * (len(p["points"]) + len(allpts)), "bboxes": boxes}
    return [finish(stem, f, pasted, (mp[0], mp[1]) if mp else (fp[0], fp[1]), prompts, t0, extra, kind)]


def _zoom_generic(stem, weights, kind, crop_hi=0.55, p_lo=0.15, p_hi=0.85, n=3, trim=0.0):
    f = C.frame_for(stem, kind)
    t0 = time.time()
    img = C.read_frame(stem, f)
    p, lg, sc, comp, full = _soft_full(stem, f, img, weights)
    fp = E.fit_pair(*full)
    if fp is None:
        return [finish(stem, f, comp, None, p, t0, None, kind)]
    y_top, y_bot = L.gt_y(stem, f)
    y1 = y_top + crop_hi * (y_bot - y_top)
    z, box, zpts = _zoom_rows(stem, f, img, weights, fp[0], fp[1], y_top, y1, n=n, lo=p_lo, hi=p_hi)
    extra = {"crop": list(box), "crop_prompts": zpts, "trim": trim,
             "full_mae": L.score(stem, L.lines_to_corners(fp[0], fp[1], y_top, y_bot), f)["board_mae"]}
    if z is None:
        extra["zoom"] = "failed"
        return [finish(stem, f, comp, (fp[0], fp[1]), p, t0, extra, kind)]
    ys, xl, xr = E.merge_rows([(full[0], full[1], full[2], 0), (z[0], z[1], z[2], 1)])
    keep = ys >= y_top + trim * (y_bot - y_top)
    mp = E.fit_pair(ys[keep], xl[keep], xr[keep])
    extra.update(mp[2] if mp else {})
    extra["zoom_scale"] = round(1024 / max(box[2] - box[0], box[3] - box[1]), 2)
    prompts = {"points": p["points"] + zpts, "labels": [1] * (len(p["points"]) + len(zpts)), "bboxes": [list(box)]}
    return [finish(stem, f, _paste(comp, z[3], box), (mp[0], mp[1]) if mp else (fp[0], fp[1]), prompts, t0, extra, kind)]


@method("zoom_lo", "zoom with the crop's prompts kept in the lower half of the crop path (10-55%), away from the pin deck")
def zoom_lo(stem, weights, kind):
    return _zoom_generic(stem, weights, kind, p_lo=0.10, p_hi=0.55, n=2)


@method("zoom_trim", "zoom_lo, then the top 15% of lane rows (deck bleed) excluded from the line fit")
def zoom_trim(stem, weights, kind):
    return _zoom_generic(stem, weights, kind, p_lo=0.10, p_hi=0.55, n=2, trim=0.15)


# ------------------------------------------------------------------ ensembles

VARIANTS = [(3, 0.15, 0.85, 0), (3, 0.20, 0.80, 0), (3, 0.25, 0.75, 0), (4, 0.15, 0.85, 0), (5, 0.15, 0.85, 0),
            (5, 0.10, 0.90, 0), (3, 0.15, 0.85, 6), (3, 0.15, 0.85, -6), (4, 0.15, 0.85, 6), (4, 0.15, 0.85, -6)]


@method("ens", "10 prompt variants (3-5 points, 4 spacings, +-6 px lateral jitter) decoded on one encoding; mean logit, soft edges")
def ens(stem, weights, kind):
    f = C.frame_for(stem, kind)
    t0 = time.time()
    img = C.read_frame(stem, f)
    si = S.SamImage(img, weights)
    y_top, y_bot = L.gt_y(stem, f)
    acc = None
    per = []
    allpts = []
    for n, lo, hi, dx in VARIANTS:
        pts = [[x + dx, y] for x, y in even_points(stem, f, n=n, lo=lo, hi=hi)]
        lg, sc = si.logit(pts)
        comp = E.component(lg, pts)
        ys, xl, xr = E.soft_rows(lg, y_top, y_bot, pts, comp)
        fp = E.fit_pair(ys, xl, xr)
        mae = L.score(stem, L.lines_to_corners(fp[0], fp[1], y_top, y_bot), f)["board_mae"] if fp else None
        per.append({"n": n, "lo": lo, "hi": hi, "dx": dx, "score": round(sc, 3), "mae": mae})
        acc = lg if acc is None else acc + lg
        allpts += pts
    mean = acc / len(VARIANTS)
    anchors = [[x, y] for x, y in even_points(stem, f, n=3)]
    comp = E.component(mean, anchors)
    ys, xl, xr = E.soft_rows(mean, y_top, y_bot, anchors, comp)
    fp = E.fit_pair(ys, xl, xr)
    maes = [v["mae"] for v in per if v["mae"] is not None]
    extra = {"variants": per, "variant_mae_min": min(maes) if maes else None, "variant_mae_max": max(maes) if maes else None,
             "variant_mae_median": round(float(np.median(maes)), 2) if maes else None}
    extra.update(fp[2] if fp else {})
    prompts = {"points": allpts, "labels": [1] * len(allpts)}
    return [finish(stem, f, comp, (fp[0], fp[1]) if fp else None, prompts, t0, extra, kind)]


@method("ens_zoom", "ens on the full frame, then ens on the top-55% crop; merged rows")
def ens_zoom(stem, weights, kind):
    f = C.frame_for(stem, kind)
    t0 = time.time()
    img = C.read_frame(stem, f)
    H, W = img.shape[:2]
    y_top, y_bot = L.gt_y(stem, f)

    def ens_rows(image, off, pts_fn, ya, yb):
        si = S.SamImage(image, weights)
        acc = None
        for n, lo, hi, dx in VARIANTS:
            pts = [[x + dx - off[0], y - off[1]] for x, y in pts_fn(n, lo, hi)]
            if not pts:
                continue
            lg, _ = si.logit(pts)
            acc = lg if acc is None else acc + lg
        if acc is None:
            return None
        anchors = [[x - off[0], y - off[1]] for x, y in pts_fn(3, 0.15, 0.85)]
        comp = E.component(acc, anchors)
        if comp is None:
            return None
        ys, xl, xr = E.soft_rows(acc, ya, yb, anchors, comp)
        return ys + off[1], xl + off[0], xr + off[0], comp

    full = ens_rows(img, (0, 0), lambda n, lo, hi: even_points(stem, f, n=n, lo=lo, hi=hi), y_top, y_bot)
    if full is None:
        return [finish(stem, f, None, None, {}, t0, None, kind)]
    fp = E.fit_pair(full[0], full[1], full[2])
    if fp is None:
        return [finish(stem, f, full[3], None, {}, t0, None, kind)]
    y1 = y_top + 0.55 * (y_bot - y_top)
    box = E.crop_box(fp[0], fp[1], y_top, y1, W, H)
    x1, ya, x2, yb = box
    z = ens_rows(img[ya:yb, x1:x2], (x1, ya), lambda n, lo, hi: C.path_points_between(stem, f, ya, yb, n=n, lo=lo, hi=hi),
                 max(0, y_top - ya), min(yb - ya - 1, y1 - ya))
    extra = {"crop": list(box), "full_mae": L.score(stem, L.lines_to_corners(fp[0], fp[1], y_top, y_bot), f)["board_mae"]}
    if z is None:
        return [finish(stem, f, full[3], (fp[0], fp[1]), {}, t0, dict(extra, zoom="failed"), kind)]
    ys, xl, xr = E.merge_rows([(full[0], full[1], full[2], 0), (z[0], z[1], z[2], 1)])
    mp = E.fit_pair(ys, xl, xr)
    extra.update(mp[2] if mp else {})
    pts = even_points(stem, f, n=3)
    prompts = {"points": pts, "labels": [1] * len(pts), "bboxes": [list(box)]}
    return [finish(stem, f, _paste(full[3], z[3], box), (mp[0], mp[1]) if mp else (fp[0], fp[1]), prompts, t0, extra, kind)]


# ------------------------------------------------------------------ image size

@method("hires", "even3 prompts with the encoder run at imgsz 2048 instead of 1024 (soft edges)")
def hires(stem, weights, kind):
    f = C.frame_for(stem, kind)
    t0 = time.time()
    img = C.read_frame(stem, f)
    p = even_prompts(stem, f, 3)
    try:
        si = S.SamImage(img, weights, imgsz=2048)
        lg, sc = si.logit(p["points"], p["labels"])
    except Exception as e:  # noqa: BLE001
        return [finish(stem, f, None, None, p, t0, {"error": f"{type(e).__name__}: {e}"[:200]}, kind)]
    y_top, y_bot = L.gt_y(stem, f)
    comp = E.component(lg, pos(p))
    ys, xl, xr = E.soft_rows(lg, y_top, y_bot, pos(p), comp)
    fp = E.fit_pair(ys, xl, xr)
    extra = dict(fp[2], sam_score=round(sc, 3)) if fp else {"sam_score": round(sc, 3)}
    return [finish(stem, f, comp, (fp[0], fp[1]) if fp else None, p, t0, extra, kind)]


# ------------------------------------------------------------------ extrapolation: trimmed fit, vanishing point

def _fit_through(ys, xs, vp, iters=3):
    """x = a*y + b constrained to pass through vp = (xv, yv); robust to outliers."""
    xv, yv = vp
    ys = np.asarray(ys, float)
    xs = np.asarray(xs, float)
    keep = np.ones(len(ys), bool)
    a = 0.0
    for _ in range(iters + 1):
        dy = ys[keep] - yv
        dx = xs[keep] - xv
        a = float((dx * dy).sum() / max((dy * dy).sum(), 1e-9))
        resid = np.abs(xs - (a * ys + (xv - a * yv)))
        nk = resid <= max(3.0, 2.0 * np.median(resid) + 1e-6)
        if nk.sum() < 10:
            break
        keep = nk
    b = xv - a * yv
    return (a, b), float(np.mean(np.abs(xs - (a * ys + b))))


def _vp_from_lines(lines, w=None):
    """Least-squares point nearest to all lines x = a*y + b."""
    A = np.array([[1.0, -a] for a, _ in lines])
    B = np.array([b for _, b in lines])
    W = np.ones(len(lines)) if w is None else np.asarray(w, float)
    sol, *_ = np.linalg.lstsq(A * W[:, None], B * W, rcond=None)
    return float(sol[0]), float(sol[1])


TRIM = 0.30


@method("trim", "soft edges fitted only on rows below the top 30% of the lane (where a board is wide and the mask is clean), extrapolated to the pin end")
def trim(stem, weights, kind):
    f = C.frame_for(stem, kind)
    t0 = time.time()
    img = C.read_frame(stem, f)
    p, lg, sc, comp, (ys, xl, xr) = _soft_full(stem, f, img, weights)
    y_top, y_bot = L.gt_y(stem, f)
    sweep = {}
    best = None
    for tr in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5):
        keep = ys >= y_top + tr * (y_bot - y_top)
        fp = E.fit_pair(ys[keep], xl[keep], xr[keep])
        if fp is None:
            continue
        sweep[str(tr)] = L.score(stem, L.lines_to_corners(fp[0], fp[1], y_top, y_bot), f)["board_mae"]
        if abs(tr - TRIM) < 1e-9:
            best = fp
    extra = {"trim": TRIM, "sweep_mae_by_trim": sweep}
    if best:
        extra.update(best[2])
    return [finish(stem, f, comp, (best[0], best[1]) if best else None, p, t0, extra, kind)]


LANE_PITCH = 1.55   # neighbouring lane centre offset in own-lane widths (41.5 in lane + two 9.25 in gutters + capping)


@method("vp", "vanishing point from the lane and its two neighbours (SAM prompted on the path mirrored by one lane pitch); each edge refitted through the VP on the lower 70% of rows")
def vp(stem, weights, kind):
    f = C.frame_for(stem, kind)
    t0 = time.time()
    img = C.read_frame(stem, f)
    H, W = img.shape[:2]
    si, p, lg, sc, comp, (ys, xl, xr) = _soft_full2(stem, f, img, weights)
    fp = E.fit_pair(ys, xl, xr)
    if fp is None:
        return [finish(stem, f, comp, None, p, t0, None, kind)]
    y_top, y_bot = L.gt_y(stem, f)
    (la, lb), (ra, rb) = fp[0], fp[1]

    def width(y):
        return (ra * y + rb) - (la * y + lb)

    lines, wts, used, npts = [fp[0], fp[1]], [1.0, 1.0], [], []
    own_w = width(y_bot)
    for k in (-1, 1):
        q = [[int(x + k * LANE_PITCH * width(y)), int(y)] for x, y in p["points"]]
        q = [[x, y] for x, y in q if 0 <= x < W]
        if len(q) < 2:
            continue
        lgk, _ = si.logit(q)
        ck = E.component(lgk, q)
        if ck is None:
            continue
        yk, lk, rk = E.soft_rows(lgk, y_top, y_bot, q, ck)
        fk = E.fit_pair(yk, lk, rk)
        if fk is None:
            continue
        cov = len(yk) / (y_bot - y_top + 1)
        wk = (fk[1][0] * y_bot + fk[1][1]) - (fk[0][0] * y_bot + fk[0][1])
        ok = cov >= 0.6 and fk[2]["fit_resid_px"] < 3.0 and 0.6 * own_w <= wk <= 1.4 * own_w
        npts += q
        if ok:
            lines += [fk[0], fk[1]]
            wts += [1.0, 1.0]
            used.append(k)
            comp = np.maximum(comp, ck)
    xv, yv = _vp_from_lines(lines, wts)
    lo = ys >= y_top + 0.30 * (y_bot - y_top)
    left, rl = _fit_through(ys[lo], xl[lo], (xv, yv))
    right, rr = _fit_through(ys[lo], xr[lo], (xv, yv))
    own_vp = _vp_from_lines([fp[0], fp[1]])
    extra = {"vp": [round(xv, 1), round(yv, 1)], "vp_own_lines_only": [round(own_vp[0], 1), round(own_vp[1], 1)],
             "neighbours_used": used, "lines_used": len(lines), "fit_resid_px": round((rl + rr) / 2, 2),
             "unconstrained_mae": L.score(stem, L.lines_to_corners(fp[0], fp[1], y_top, y_bot), f)["board_mae"]}
    # also: through the VP of the own lines only (no neighbours) for comparison
    l2, _ = _fit_through(ys[lo], xl[lo], own_vp)
    r2, _ = _fit_through(ys[lo], xr[lo], own_vp)
    extra["own_vp_mae"] = L.score(stem, L.lines_to_corners(l2, r2, y_top, y_bot), f)["board_mae"]
    prompts = {"points": p["points"] + npts, "labels": [1] * (len(p["points"]) + len(npts))}
    return [finish(stem, f, comp, (left, right), prompts, t0, extra, kind)]


# ------------------------------------------------------------------ main

def run(names, kinds, weights, tag, stems):
    C.RESULTS.mkdir(exist_ok=True)
    C.OVERLAYS.mkdir(exist_ok=True)
    for name in names:
        fn, desc, allowed = METHODS[name]
        for kind in kinds:
            if allowed is not None and kind not in allowed:
                continue
            key = f"{name}_{kind}{tag}"
            rows = []
            for stem in stems:
                try:
                    outs = fn(stem, weights, kind)
                except Exception:  # noqa: BLE001
                    traceback.print_exc()
                    outs = [({"stem": stem, "frame": None, "kind": kind, "ok": False, "error": traceback.format_exc()[-400:], "prompts": {}}, None, None)]
                for row, corners, mask in outs:
                    row["method"] = key
                    row["weights"] = weights
                    row["desc"] = desc
                    rows.append(row)
                    if row.get("frame") is not None:
                        cap = f"{key} | {stem} | f{row['frame']}"
                        extra = [f"board MAE {row['board_mae']}  max {row['board_max']}  <=1: {row['within_1']}%"] if row["ok"] else ["no mask / fit failed"]
                        try:
                            im = L.draw_overlay(stem, row["frame"], mask, corners, row.get("prompts", {}), cap, extra)
                            cv2.imwrite(str(C.OVERLAYS / f"{key}_{stem}.jpg"), im, [cv2.IMWRITE_JPEG_QUALITY, 88])
                        except Exception:  # noqa: BLE001
                            traceback.print_exc()
                    print(json.dumps({k: row.get(k) for k in ("method", "stem", "frame", "ok", "board_mae", "board_max", "within_1", "latency_s")}), flush=True)
            (C.RESULTS / f"{key}.json").write_text(json.dumps(rows, indent=1, default=float))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--methods", default=",".join(METHODS))
    ap.add_argument("--kinds", default="last,prehit")
    ap.add_argument("--weights", default="sam2.1_b.pt")
    ap.add_argument("--tag", default="")
    ap.add_argument("--stems", default=",".join(C.STEMS))
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--prompts", default="old", choices=["old", "keep"], help="keep = slide points off the ball instead of dropping them; adds tag _k")
    a = ap.parse_args()
    global PROMPT_RULE
    PROMPT_RULE = a.prompts
    if a.prompts == "keep":
        a.tag = "_k" + a.tag
    if a.list:
        for k, (_, d, kinds) in METHODS.items():
            print(f"{k:12s} {(','.join(kinds) if kinds else 'any'):14s} {d}")
        return
    run(a.methods.split(","), a.kinds.split(","), a.weights, a.tag, a.stems.split(","))


if __name__ == "__main__":
    main()
