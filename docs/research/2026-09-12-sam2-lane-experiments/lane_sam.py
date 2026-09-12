"""SAM 2 lane-edge experiments: prompt builders, edge fitting, board metric, overlays.

Every method turns one or more frames into a lane mask, the mask into two edge
lines (x = a*y + b), and the lines into four corners evaluated at the annotated
top/bottom y. The metric is the same as the 2026-09-12 new-stack report: apply
the 4-corner board homography to every annotated ball position and compare the
board number against the homography from the annotated corners.

Ball positions come from the annotation files and stand in for a ball detector;
the point of the loop is the lane, not the ball.
"""
import json
import os
import time
from pathlib import Path

import cv2
import numpy as np

import gt

KEYS = ("top_left", "top_right", "bottom_left", "bottom_right")
EXP = Path(__file__).resolve().parent
WEIGHTS_DIR = Path(os.environ.get(
    "SAM_WEIGHTS",
    "/private/tmp/claude-502/-Users-toka-code-toms-gym/b090792b-0a7d-4249-9e93-4543c8a2bc1f/scratchpad/weights"))

_models = {}


def model(weights="sam2.1_b.pt"):
    if weights not in _models:
        from ultralytics import SAM
        cwd = os.getcwd()
        os.chdir(WEIGHTS_DIR)
        try:
            _models[weights] = SAM(weights)
        finally:
            os.chdir(cwd)
    return _models[weights]


# ---------------------------------------------------------------- trajectory

def pin_hit_frame(stem):
    ann = gt.load_annotation(stem)
    f = ann.get("pin_hit_frame")
    if f is None:
        f = (ann.get("frame_markers") or {}).get("pin_hit")
    return int(f) if f is not None else None


def trajectory_all(stem):
    pos, _ = gt.ball_gt(stem)
    return sorted(pos), pos


def trajectory(stem):
    """Ball positions while the ball is on the lane: annotated frames up to
    the pin-hit marker. Chardie is annotated 36 frames into the pit, which
    is off the lane and not a board."""
    fs, pos = trajectory_all(stem)
    ph = pin_hit_frame(stem)
    if ph is not None:
        fs = [f for f in fs if f <= ph]
        pos = {f: pos[f] for f in fs}
    return fs, pos


def frame_indices(stem, kind, k=1):
    """Frame sets: pre = 5 before first ball frame (bowler at the line),
    post = k frames evenly spread over the second half of the throw,
    last = last annotated ball frame."""
    fs, _ = trajectory_all(stem)
    if kind == "pre":
        return [max(0, fs[0] - 5)]
    if kind == "last":
        return [fs[-1]]
    if kind == "post":
        lo = fs[len(fs) // 2]
        hi = fs[-1]
        return sorted({int(round(v)) for v in np.linspace(lo, hi, k)})
    if kind == "all_post":
        return fs[len(fs) // 2:]
    if kind == "mid":
        return [fs[len(fs) // 2]]
    if kind == "span":
        lo = max(0, fs[0] - 5)
        return sorted({int(round(v)) for v in np.linspace(lo, fs[-1], k)})
    if kind == "late":
        lo = fs[int(len(fs) * 0.7)]
        return sorted({int(round(v)) for v in np.linspace(lo, fs[-1], k)})
    raise ValueError(kind)


_person = None


def person_boxes(img, min_h_frac=0.08):
    """Person boxes from YOLO11n (COCO class 0), used to place negative prompts
    on the bowler. Returns [[x1, y1, x2, y2], ...]."""
    global _person
    if _person is None:
        from ultralytics import YOLO
        cwd = os.getcwd()
        os.chdir(WEIGHTS_DIR)
        try:
            _person = YOLO("yolo11n.pt")
        finally:
            os.chdir(cwd)
    res = _person.predict(img, classes=[0], conf=0.3, verbose=False)[0]
    h = img.shape[0]
    out = []
    for b in res.boxes.xyxy.cpu().numpy():
        if (b[3] - b[1]) >= min_h_frac * h:
            out.append([int(v) for v in b])
    return out


def person_negatives(boxes):
    pts = []
    for x1, y1, x2, y2 in boxes:
        cx = (x1 + x2) / 2
        hh = y2 - y1
        for fr in (0.3, 0.6, 0.85):
            pts.append([int(cx), int(y1 + fr * hh)])
    return pts


def vote_masks(masks, thresh=0.5):
    """Pixel-wise majority vote over several frames' masks: the lane is static,
    the bowler is not."""
    stack = np.stack([m.astype(np.float32) for m in masks])
    return (stack.mean(0) >= thresh).astype(np.uint8)


def outermost_lines(line_sets, y_top, y_bot):
    """Occlusion only ever narrows the mask, so take the leftmost left edge and
    rightmost right edge (judged at the bottom y) across frames."""
    left = min((ls[0] for ls in line_sets), key=lambda l: l[0] * y_bot + l[1])
    right = max((ls[1] for ls in line_sets), key=lambda l: l[0] * y_bot + l[1])
    return left, right


def track_points(stem, frame, n=5, avoid_r=3.0):
    """n points along the ball path, skipping the ball's own position on this
    frame (a point on the ball segments the ball)."""
    fs, pos = trajectory(stem)
    picks = [fs[int(i)] for i in np.linspace(0, len(fs) - 1, n + 2)][1:-1]
    pts = []
    here = pos.get(frame)
    for f in picks:
        x, y, r = pos[f]
        if here is not None and np.hypot(x - here[0], y - here[1]) < avoid_r * max(here[2], 8):
            continue
        pts.append([int(x), int(y)])
    return pts


def track_points_even(stem, frame, n=5, lo=0.15, hi=0.85, avoid_r=3.0):
    """n points spaced evenly by image distance along the ball path (moved
    into this frame), between lo and hi of the path length so none sit on
    the pin deck or the foul line. Time-even picks bunch at the pin end
    because the ball moves slowly in image space far from the camera."""
    fs, pos = trajectory(stem)
    pts = np.array(ball_points_on_ordered(stem, frame), float)
    if len(pts) < 2:
        return [[int(v) for v in p] for p in pts]
    seg = np.hypot(*(np.diff(pts, axis=0).T))
    cum = np.concatenate([[0], np.cumsum(seg)])
    total = cum[-1]
    here = pos.get(frame)
    out = []
    for t in np.linspace(lo, hi, n):
        i = int(np.searchsorted(cum, t * total))
        i = min(max(i, 0), len(pts) - 1)
        x, y = pts[i]
        if here is not None and np.hypot(x - here[0], y - here[1]) < avoid_r * max(here[2], 8):
            continue
        out.append([int(x), int(y)])
    return out


# ---------------------------------------------------------------- SAM calls

def predict_mask(m, img, points=None, labels=None, bboxes=None):
    # One object, many points: ultralytics reads a flat (N, 2) list as N
    # separate single-point prompts, so nest to (1, N, 2).
    kw = {}
    if points:
        kw["points"] = [points]
        kw["labels"] = [labels or [1] * len(points)]
    if bboxes:
        kw["bboxes"] = bboxes
    res = m.predict(img, verbose=False, **kw)[0]
    if res.masks is None or len(res.masks) == 0:
        return None
    mk = res.masks.data[0].cpu().numpy().astype(np.uint8)
    h, w = img.shape[:2]
    if mk.shape != (h, w):
        mk = cv2.resize(mk, (w, h), interpolation=cv2.INTER_NEAREST)
    return mk


def predict_multimask(m, img, points, labels=None, bboxes=None):
    """The three candidate masks SAM returns for an ambiguous prompt, with
    SAM's own quality scores. Uses the predictor's feature path directly
    because the public predict() pins multimask_output=False."""
    import torch
    from ultralytics.utils import ops
    if m.predictor is None:
        m.predict(img, points=[points], labels=[labels or [1] * len(points)], verbose=False)
    p = m.predictor
    p.setup_source(None)
    im = p.preprocess([img])
    feats = p.get_im_features(im)
    pts, lbl, _ = p._prepare_prompts(im.shape[2:], img.shape[:2], bboxes=bboxes,
                                     points=[points], labels=[labels or [1] * len(points)])
    masks, scores = p._inference_features(feats, pts, lbl, multimask_output=True)
    masks = ops.scale_masks(masks[None].float(), img.shape[:2], padding=False)[0]
    masks = (masks > 0.0).cpu().numpy().astype(np.uint8)
    return list(masks), [float(s) for s in scores]


# ---------------------------------------------------------------- edges

def largest_component(mask, anchors=None):
    """The connected component holding most anchor points (the ball path), else
    the largest. A leaked mask can span two lanes as two components, and the
    bigger one is not always the one the ball rolled on."""
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    if n <= 1:
        return None
    pick = None
    if anchors:
        votes = {}
        for x, y in anchors:
            xi, yi = int(round(x)), int(round(y))
            if 0 <= yi < lab.shape[0] and 0 <= xi < lab.shape[1] and lab[yi, xi] > 0:
                votes[lab[yi, xi]] = votes.get(lab[yi, xi], 0) + 1
        if votes:
            pick = max(votes, key=votes.get)
    if pick is None:
        pick = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return (lab == pick).astype(np.uint8)


def robust_line(ys, xs):
    ys = np.asarray(ys, float)
    xs = np.asarray(xs, float)
    a, b = np.polyfit(ys, xs, 1)
    for _ in range(3):
        resid = np.abs(xs - (a * ys + b))
        keep = resid <= max(3.0, 2.0 * np.median(resid) + 1e-6)
        if keep.sum() < 10:
            break
        a, b = np.polyfit(ys[keep], xs[keep], 1)
    return a, b, float(np.mean(np.abs(xs - (a * ys + b))))


def fit_edges(mask, y_top, y_bot, anchors=None):
    """(left, right) as (a, b) with x = a*y + b, fitted on the rows between
    y_top and y_bot of the component holding the anchors (else the largest).
    None if too few rows."""
    m = largest_component(mask, anchors)
    if m is None:
        return None
    ys, ls, rs = [], [], []
    for y in range(int(y_top), int(y_bot) + 1):
        if y < 0 or y >= m.shape[0]:
            continue
        xs = np.where(m[y])[0]
        if len(xs) < 5:
            continue
        ys.append(y)
        ls.append(xs.min())
        rs.append(xs.max())
    if len(ys) < 10:
        return None
    la, lb, lr = robust_line(ys, ls)
    ra, rb, rr = robust_line(ys, rs)
    return (la, lb), (ra, rb), {"fit_resid_px": round((lr + rr) / 2, 2),
                                "row_coverage": round(len(ys) / (y_bot - y_top + 1), 2)}


def lines_to_corners(left, right, y_top, y_bot):
    (la, lb), (ra, rb) = left, right
    return {"top_left": (la * y_top + lb, y_top), "top_right": (ra * y_top + rb, y_top),
            "bottom_left": (la * y_bot + lb, y_bot), "bottom_right": (ra * y_bot + rb, y_bot)}


def median_lines(line_sets):
    """Median of (a, b) per edge over several frames' fits."""
    L = np.array([[ls[0][0], ls[0][1]] for ls in line_sets])
    R = np.array([[ls[1][0], ls[1][1]] for ls in line_sets])
    return tuple(np.median(L, 0)), tuple(np.median(R, 0))


def snap_edges(img, left, right, y_top, y_bot, band=6):
    """Move each fitted line onto the strongest horizontal-gradient response
    within +-band px, then refit. Returns new (left, right)."""
    g = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    gx = np.abs(cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3))
    out = []
    for (a, b) in (left, right):
        ys, xs = [], []
        for y in range(int(y_top), int(y_bot) + 1):
            x0 = int(round(a * y + b))
            lo, hi = max(0, x0 - band), min(gx.shape[1] - 1, x0 + band)
            if hi <= lo:
                continue
            seg = gx[y, lo:hi + 1]
            xs.append(lo + int(np.argmax(seg)))
            ys.append(y)
        if len(ys) < 10:
            out.append((a, b))
            continue
        na, nb, _ = robust_line(ys, xs)
        out.append((na, nb))
    return out[0], out[1]


# ---------------------------------------------------------------- camera / per-frame truth

# Frame the static annotated corners belong to. sample_input has per-frame
# corners (used directly); Chardie's static corners match the end of the
# throw (SAM on f170 agrees to <1 board, the pre-release frame is 30 px away);
# tom_old is a tripod so it does not matter.
STATIC_FRAME = {"20260112_121117": 170}
_cam = {}


def camera(stem):
    if stem not in _cam:
        _cam[stem] = json.loads((EXP / "results" / f"camera_{stem}.json").read_text())
    return _cam[stem]


def _A(stem, f):
    cam = camera(stem)
    fr = cam["frames"]
    f = min(max(f, fr[0]), fr[-1])
    return np.array(cam["affine"][str(f)], float)


def _inv(A):
    R = A[:, :2]
    Ri = np.linalg.inv(R)
    return np.hstack([Ri, (-Ri @ A[:, 2])[:, None]])


def transform(stem, f_from, f_to):
    """2x3 affine taking frame f_from pixel coords to frame f_to."""
    A = np.vstack([_A(stem, f_to), [0, 0, 1]])
    B = np.vstack([_inv(_A(stem, f_from)), [0, 0, 1]])
    return (A @ B)[:2]


def warp_pt(T, p):
    return (T[0, 0] * p[0] + T[0, 1] * p[1] + T[0, 2], T[1, 0] * p[0] + T[1, 1] * p[1] + T[1, 2])


def warp_line(T, line, y0, y1):
    """x = a*y + b in the source frame -> same line in the target frame."""
    a, b = line
    p0 = warp_pt(T, (a * y0 + b, y0))
    p1 = warp_pt(T, (a * y1 + b, y1))
    if abs(p1[1] - p0[1]) < 1e-6:
        return line
    na = (p1[0] - p0[0]) / (p1[1] - p0[1])
    return (na, p0[0] - na * p0[1])


def warp_mask(T, mask):
    h, w = mask.shape
    return cv2.warpAffine(mask, T.astype(np.float32), (w, h), flags=cv2.INTER_NEAREST)


def truth_corners(stem, f):
    ann = gt.load_annotation(stem)
    fle = ann.get("frame_lane_edges")
    if fle:
        keys = sorted(int(k) for k in fle)
        k = min(keys, key=lambda q: abs(q - f))
        e = fle[str(k)]
        return {q: tuple(e[q]) for q in KEYS}
    static = gt.lane_gt(stem)
    f_static = STATIC_FRAME.get(stem, camera(stem)["ref"])
    T = transform(stem, f_static, f)
    return {q: warp_pt(T, static[q]) for q in KEYS}


def gt_y(stem, f):
    t = truth_corners(stem, f)
    return (min(t["top_left"][1], t["top_right"][1]), max(t["bottom_left"][1], t["bottom_right"][1]))


def ball_points_on(stem, f):
    """Every annotated ball position, moved into frame f's pixel coordinates."""
    _, pos = trajectory(stem)
    out = []
    for g, (x, y, _r) in pos.items():
        out.append(warp_pt(transform(stem, g, f), (x, y)))
    return out


def ball_points_on_ordered(stem, f):
    fs, pos = trajectory(stem)
    return [warp_pt(transform(stem, g, f), (pos[g][0], pos[g][1])) for g in fs]


# ---------------------------------------------------------------- metric

def score(stem, corners, f):
    truth = truth_corners(stem, f)
    pts = ball_points_on(stem, f)
    b_true, _ = gt.board_from_corners(truth, pts)
    b_pred, _ = gt.board_from_corners(corners, pts)
    diff = np.abs(b_pred - b_true)
    cerr = {k: float(np.hypot(corners[k][0] - truth[k][0], corners[k][1] - truth[k][1])) for k in KEYS}
    return {
        "board_mae": round(float(diff.mean()), 2),
        "board_max": round(float(diff.max()), 2),
        "within_1": round(float((diff <= 1).mean() * 100), 1),
        "within_2": round(float((diff <= 2).mean() * 100), 1),
        "corner_err_px": {k: round(v, 1) for k, v in cerr.items()},
        "corner_err_mean_px": round(float(np.mean(list(cerr.values()))), 1),
        "top_width_true_px": round(truth["top_right"][0] - truth["top_left"][0], 1),
        "top_width_pred_px": round(corners["top_right"][0] - corners["top_left"][0], 1),
        "bottom_width_true_px": round(truth["bottom_right"][0] - truth["bottom_left"][0], 1),
        "bottom_width_pred_px": round(corners["bottom_right"][0] - corners["bottom_left"][0], 1),
    }


# ---------------------------------------------------------------- overlays

def draw_overlay(stem, frame, mask, corners, prompts, caption, extra=None):
    """Mask tint, GT lane green, predicted lane red, prompts, caption, and a
    3x pin-end inset (where a board is 1-2 px)."""
    img = cv2.imread(str(gt.frame_path(stem, frame)))
    h, w = img.shape[:2]
    out = img.copy()
    if mask is not None:
        mb = mask.astype(bool)
        out[mb] = (0.45 * out[mb] + np.array([150, 60, 0])).clip(0, 255).astype(np.uint8)
    truth = {k: (int(round(v[0])), int(round(v[1]))) for k, v in truth_corners(stem, frame).items()}

    def poly(c, color, th):
        p = np.array([c["top_left"], c["top_right"], c["bottom_right"], c["bottom_left"]], np.int32)
        cv2.polylines(out, [p], True, color, th, cv2.LINE_AA)

    poly(truth, (0, 220, 0), 2)
    if corners is not None:
        poly({k: (int(round(v[0])), int(round(v[1]))) for k, v in corners.items()}, (0, 0, 255), 2)
    for (x, y), lab in zip(prompts.get("points", []), prompts.get("labels", [])):
        if lab == 1:
            cv2.circle(out, (int(x), int(y)), 9, (0, 255, 255), -1, cv2.LINE_AA)
            cv2.circle(out, (int(x), int(y)), 9, (0, 0, 0), 2, cv2.LINE_AA)
        else:
            cv2.drawMarker(out, (int(x), int(y)), (255, 0, 255), cv2.MARKER_TILTED_CROSS, 22, 3, cv2.LINE_AA)
    for (x1, y1, x2, y2) in prompts.get("bboxes", []):
        cv2.rectangle(out, (int(x1), int(y1)), (int(x2), int(y2)), (255, 255, 0), 2)

    # pin-end inset: 3x zoom on the annotated top edge
    tw = truth["top_right"][0] - truth["top_left"][0]
    cx = (truth["top_left"][0] + truth["top_right"][0]) / 2
    cy = (truth["top_left"][1] + truth["top_right"][1]) / 2
    half_w = max(int(tw * 1.2), 60)
    half_h = max(int(tw * 0.6), 30)
    x1, x2 = int(max(0, cx - half_w)), int(min(w, cx + half_w))
    y1, y2 = int(max(0, cy - half_h)), int(min(h, cy + half_h))
    crop = out[y1:y2, x1:x2]
    if crop.size:
        z = 3
        crop = cv2.resize(crop, None, fx=z, fy=z, interpolation=cv2.INTER_NEAREST)
        ch, cw = crop.shape[:2]
        cw = min(cw, w - 20)
        crop = crop[:, :cw]
        out[10:10 + ch, 10:10 + cw] = crop
        cv2.rectangle(out, (10, 10), (10 + cw, 10 + ch), (255, 255, 255), 2)
        cv2.putText(out, "pin end x3", (14, 10 + ch - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)

    lines = [caption] + (extra or [])
    y = h - 16 - 30 * (len(lines) - 1)
    for ln in lines:
        cv2.putText(out, ln, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(out, ln, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)
        y += 30
    return out


def save_json(path, rows):
    Path(path).write_text(json.dumps(rows, indent=1))
