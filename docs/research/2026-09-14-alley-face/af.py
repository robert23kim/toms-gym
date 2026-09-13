"""Shared setup for the alley-face loop (loop 5). Reuses loop 4's common.py /
landmarks.py (truths in three flavours, rack fit, arrow detector, weighted DLT)
and through them loop 1's gt / lane_sam (metric, camera warps, ball path) and
loop 3's full-video camera models. Nothing in the earlier folders is written.

This module is deliberately not called common.py: loop 4's landmarks.py does
`import common`, so that name must resolve to loop 4's module.

Frames / weights / datasets / runs live in the session scratchpad (AF_SCRATCH);
results/ and overlays/ here are the deliverables.
"""
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
LOOP4 = HERE.parent / "2026-09-13-lane-landmarks"
LOOP3 = HERE.parent / "2026-09-12-cheap-lane-model"
SCRATCH = Path(os.environ.get(
    "AF_SCRATCH",
    "/private/tmp/claude-502/-Users-toka-code-toms-gym/06d30d1b-ddda-464a-9f08-c75e215855ea/scratchpad"))
os.environ.setdefault("LM_SCRATCH", str(SCRATCH))
os.environ.setdefault("YOLO_CONFIG_DIR", str(SCRATCH / "yolo_cfg"))
sys.path.insert(0, str(LOOP4))

import common as C4  # noqa: E402  (loop 4)
import landmarks as LM  # noqa: E402  (loop 4)

L = C4.L
gt = C4.gt
C4.use_full_camera()

RESULTS = HERE / "results"
OVERLAYS = HERE / "overlays"
FRAMES = SCRATCH / "frames"
PRED = SCRATCH / "pred"
STEMS = C4.STEMS
ALL_STEMS = STEMS + ["bowling_video", "IMG_0242"]
LABEL = C4.LABEL
SHORT = C4.SHORT
UNLABELED = C4.UNLABELED
KEYS = C4.KEYS
W_IN = LM.W_IN
BOARD_IN = LM.BOARD_IN
HEAD_IN = LM.HEAD_IN

read_frame = C4.read_frame
frame_ids = C4.frame_ids
frame_for = C4.frame_for
throw_frames = C4.throw_frames
truth_corners = C4.truth_corners
score_corners = C4.score_corners
score_both = C4.score_both
dump = C4.dump
load = C4.load
has_result = C4.has_result
TRUTHS = C4.TRUTHS


def pin_hit(stem):
    return L.pin_hit_frame(stem)


def truth_h(stem, f, kind="all"):
    return LM.truth_h(stem, f, kind)


def to_lane(H, pts):
    return LM.to_lane(H, pts)


def to_image(H, pts):
    return LM.to_image(H, pts)


# ------------------------------------------------------------ constellation (E1 writes it, everything else reads it)

def constellation_path():
    return RESULTS / "constellation.json"


_const = None


def constellation():
    """{name: (x_in, y_in)} of every constellation point, plus the gutter lines.
    Reads results/constellation.json (E1); falls back to the rule-book arrows + pins."""
    global _const
    if _const is None:
        pts = {}
        if constellation_path().exists():
            doc = load(constellation_path())
            for k, v in doc["points"].items():
                pts[k] = (float(v["x_in"]), float(v["y_in"]))
        else:
            ax = LM.arrow_x_in()
            for b, x in ax.items():
                pts[f"arrow_{b}"] = (x, (15.3 - 0.43 * abs(b - 20) / 5.0) * 12)
            for k, (x, y) in LM.pin_bases_in().items():
                pts[f"pin_{k}_base"] = (x, y)
            pts["foul_left"] = (0.0, 0.0); pts["foul_right"] = (W_IN, 0.0)
        _const = pts
    return _const


def landmark_doc(stem):
    """Per-video landmark doc: this loop's (with dots) when written, else loop 4's."""
    p = RESULTS / f"landmarks_{stem}.json"
    return load(p) if p.exists() else C4.landmark_doc(stem)


def truth_points(stem, f, kind="all"):
    """Image positions of every constellation point on frame f under the truth homography."""
    H = truth_h(stem, f, kind)
    out = {}
    for k, (x, y) in constellation().items():
        p = to_image(H, [(x, y)])[0]
        out[k] = (float(p[0]), float(p[1]))
    return out


def truth_points_v(stem, f):
    """Per-video truth: arrows at the V depth loop 4 measured on THAT video (its truth homography's
    near end is only good to ~0.4 ft of arrow depth), pin bases from the same doc; dots and foul
    corners from the constellation model. Use this for scoring detectors; truth_points() (one model V)
    is what the constellation match assumes."""
    out = truth_points(stem, f, "all")
    for k, v in LM.truth_landmarks(stem, f, "all").items():
        out[k] = (float(v[0]), float(v[1]))
    return out


def classes_of(name):
    if name.startswith("arrow"):
        return "arrow"
    if name.startswith("pin"):
        return "pin"
    if name.startswith("dot"):
        return "dot"
    if name.startswith("fdot"):
        return "fdot"
    if name.startswith("adot"):
        return "adot"
    if name.startswith("foul"):
        return "foul"
    return "other"


# ------------------------------------------------------------ rectification helpers

def rectify_band(img, H, y0_in, y1_in, px_per_in=12.0, x0_in=-8.0, x1_in=None):
    """Bird's-eye of the lane plane between y0_in and y1_in (lane inches from the foul
    line; negative = approach) and x0_in..x1_in. y increases downward = toward the foul line.
    Returns (image, Hr) with Hr image->rect."""
    x1_in = W_IN + 8.0 if x1_in is None else x1_in
    S = np.array([[px_per_in, 0, -x0_in * px_per_in], [0, -px_per_in, y1_in * px_per_in], [0, 0, 1]], np.float64)
    Hr = S @ H
    w = int(round((x1_in - x0_in) * px_per_in)); h = int(round((y1_in - y0_in) * px_per_in))
    return cv2.warpPerspective(img, Hr, (w, h), flags=cv2.INTER_CUBIC), Hr


def rect_to_lane(Hr_meta, px, py):
    """Inverse of rectify_band's pixel grid: rect px -> lane inches."""
    px_per_in, x0_in, y1_in = Hr_meta
    return x0_in + px / px_per_in, y1_in - py / px_per_in


def dark_blobs(gray, bg_ks=41, k_mad=4.0, min_thr=10.0, area=(6, 1500), open_ks=3):
    """Small dark blobs against a local median background. Returns list of dicts
    (x, y, area, darkness, w, h) in the input image's pixels."""
    g = gray.astype(np.float32)
    bg = cv2.medianBlur(gray.astype(np.uint8), bg_ks).astype(np.float32)
    dark = bg - g
    mad = np.median(np.abs(dark - np.median(dark))) + 1e-6
    thr = max(min_thr, float(np.median(dark) + k_mad * mad))
    m = (dark > thr).astype(np.uint8)
    if open_ks:
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((open_ks, open_ks), np.uint8))
    n, lab, stats, cent = cv2.connectedComponentsWithStats(m, 8)
    out = []
    for i in range(1, n):
        x, y, bw, bh, a = stats[i]
        if a < area[0] or a > area[1]:
            continue
        ys, xs = np.where(lab == i)
        wts = dark[ys, xs]
        out.append({"x": float((xs * wts).sum() / wts.sum()), "y": float((ys * wts).sum() / wts.sum()), "area": int(a),
                    "darkness": float(wts.mean()), "w": int(bw), "h": int(bh)})
    return out, thr


# ------------------------------------------------------------ person masks (occlusion)
_seg = None


def person_mask(img, conf=0.3):
    """Union mask of COCO persons from yolo11n-seg (0/1 uint8, frame size)."""
    global _seg
    if _seg is None:
        from ultralytics import YOLO
        wp = SCRATCH / "weights" / "yolo11n-seg.pt"
        cwd = os.getcwd(); os.chdir(SCRATCH / "weights")
        try:
            _seg = YOLO(str(wp) if wp.exists() else "yolo11n-seg.pt")
        finally:
            os.chdir(cwd)
    h, w = img.shape[:2]
    res = _seg.predict(img, classes=[0], conf=conf, verbose=False, imgsz=640)[0]
    m = np.zeros((h, w), np.uint8)
    if res.masks is not None:
        for mk in res.masks.data.cpu().numpy():
            mk = cv2.resize(mk.astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST)
            m |= mk
    return m


def summarize(v):
    v = np.array([x for x in v if x is not None], float)
    if len(v) == 0:
        return {"n": 0, "median": None, "mean": None, "max": None}
    return {"n": int(len(v)), "median": round(float(np.median(v)), 3), "mean": round(float(v.mean()), 3), "max": round(float(v.max()), 3)}
