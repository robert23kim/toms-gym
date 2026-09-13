"""Shared setup for the lane-landmarks loop (loop 4). Reuses gt.py / lane_sam.py
from loop 1 (metric, per-frame truth, camera warps) and the full-video camera
models from loop 3, so every number is measured exactly as in loops 1-3.

Frames / weights / datasets live in the session scratchpad (LM_SCRATCH);
results/ and overlays/ in this folder are the deliverables.
"""
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
LOOP1 = HERE.parent / "2026-09-12-sam2-lane-experiments"
LOOP2 = HERE.parent / "2026-09-12-sam2-lane-experiments-2"
LOOP3 = HERE.parent / "2026-09-12-cheap-lane-model"
SCRATCH = Path(os.environ.get(
    "LM_SCRATCH",
    "/private/tmp/claude-502/-Users-toka-code-toms-gym/3a5c68fb-8327-4d78-8919-3cc1e8467ee1/scratchpad"))
os.environ.setdefault("SAM_FRAMES", str(SCRATCH / "frames"))
os.environ.setdefault("SAM_WEIGHTS", str(SCRATCH / "weights"))
os.environ.setdefault("YOLO_CONFIG_DIR", str(SCRATCH / "yolo_cfg"))
os.environ.setdefault("LANE_SCRATCH", str(SCRATCH))
sys.path.insert(0, str(LOOP1))

import gt  # noqa: E402
import lane_sam as L  # noqa: E402

RESULTS = HERE / "results"
OVERLAYS = HERE / "overlays"
FRAMES = SCRATCH / "frames"
STEMS = list(gt.VIDEOS)
LABEL = {"sample_input": "sample_input (1080p, handheld)", "20260112_121117": "Chardie (720p, handheld)",
         "tom_old": "tom_old (688p, tripod)", "bowling_video": "bowling_video (1080p, unlabeled)",
         "IMG_0242": "IMG_0242 (720p, unlabeled)"}
SHORT = {"sample_input": "sample_input", "20260112_121117": "Chardie", "tom_old": "tom_old",
         "bowling_video": "bowling_video", "IMG_0242": "IMG_0242"}
UNLABELED = {"bowling_video": Path.home() / "Downloads/bowling_video.mp4",
             "IMG_0242": Path.home() / "Downloads/IMG_0242.mov"}
KEYS = L.KEYS

# ------------------------------------------------------------ lane geometry (USBC)
LANE_WIDTH_IN = 41.5          # gutter to gutter, boards 1..39
BOARD_IN = LANE_WIDTH_IN / 39
LANE_LEN_FT = 60.0            # foul line to head-pin centre
ARROW_FT = 15.0               # arrows sit 12-16 ft down; the middle arrow at ~15 ft
ARROW_BOARDS = (5, 10, 15, 20, 25, 30, 35)
PIN_SPACING_IN = 12.0         # centre to centre, neighbours
PIN_7_10_IN = 36.0            # 7-pin to 10-pin centre to centre
BACK_ROW_FT = LANE_LEN_FT + 3 * (PIN_SPACING_IN * 0.8660254 / 12)  # rows are 10.39 in apart (equilateral)


def use_full_camera():
    """Loop 3's full-video camera model (every frame, not just the throw)."""
    for stem in STEMS:
        p = LOOP3 / "results" / f"camera_all_{stem}.json"
        if p.exists():
            L._cam[stem] = json.loads(p.read_text())


def frame_ids(stem):
    return sorted(int(p.stem) for p in (FRAMES / stem).glob("*.jpg"))


def read_frame(stem, f):
    return cv2.imread(str(FRAMES / stem / f"{f:05d}.jpg"))


def frame_for(stem, kind, back=2):
    """prehit = pin-hit marker - back; prehit-N; last / pre / mid as in loop 1."""
    if kind == "prehit":
        return L.pin_hit_frame(stem) - back
    if kind.startswith("prehit-"):
        return L.pin_hit_frame(stem) - int(kind.split("-")[1])
    return L.frame_indices(stem, kind)[0]


def throw_frames(stem):
    fs, _ = L.trajectory(stem)
    return list(range(max(0, fs[0] - 5), fs[-1] + 1))


def occluded_frames(stem):
    fs, _ = L.trajectory(stem)
    return list(range(0, fs[0] + 3))


def clean_frames(stem):
    fs, _ = L.trajectory(stem)
    return [f for f in throw_frames(stem) if f >= fs[0] + 3]


def truth_quad(stem, f):
    return L.truth_corners(stem, f)


def quad_h(corners, lane_width_px=390.0, lane_len_px=1000.0):
    """Image -> bird's-eye lane homography, loop-1 convention (x right = board 39 side)."""
    src = np.float32([corners["top_left"], corners["top_right"], corners["bottom_right"], corners["bottom_left"]])
    dst = np.float32([[0, 0], [lane_width_px, 0], [lane_width_px, lane_len_px], [0, lane_len_px]])
    return cv2.getPerspectiveTransform(src, dst)


def apply_h(H, pts):
    p = np.float32(pts).reshape(-1, 1, 2)
    return cv2.perspectiveTransform(p, H).reshape(-1, 2)


def boards_from_h(H, pts, lane_width_px=390.0):
    lane = apply_h(H, pts)
    return (lane_width_px - lane[:, 0]) / lane_width_px * 38.0 + 1.0, lane[:, 1]


def score_h(stem, f, H_pred, truth=None):
    """Loop-1 metric on an arbitrary homography (not just 4 corners): boards of the
    warped ball path under H_pred vs under the truth corners' homography."""
    truth = truth or L.truth_corners(stem, f)
    pts = L.ball_points_on(stem, f)
    b_true, _ = gt.board_from_corners(truth, pts)
    b_pred, _ = boards_from_h(H_pred, pts)
    diff = np.abs(b_pred - b_true)
    n = len(diff)
    tail = diff[int(0.8 * n):] if n >= 5 else diff
    return {"board_mae": round(float(diff.mean()), 2), "board_max": round(float(diff.max()), 2),
            "within_1": round(float((diff <= 1).mean() * 100), 1), "within_2": round(float((diff <= 2).mean() * 100), 1),
            "board_mae_last20": round(float(tail.mean()), 2)}


def score_corners(stem, f, corners, truth=None):
    """Loop-1 score against an explicit truth (default: annotated). Adds last-20% tail."""
    truth = truth or L.truth_corners(stem, f)
    pts = L.ball_points_on(stem, f)
    b_true, _ = gt.board_from_corners(truth, pts)
    b_pred, _ = gt.board_from_corners(corners, pts)
    diff = np.abs(b_pred - b_true)
    n = len(diff)
    tail = diff[int(0.8 * n):] if n >= 5 else diff
    cerr = {k: float(np.hypot(corners[k][0] - truth[k][0], corners[k][1] - truth[k][1])) for k in KEYS}
    return {"board_mae": round(float(diff.mean()), 2), "board_max": round(float(diff.max()), 2),
            "within_1": round(float((diff <= 1).mean() * 100), 1), "within_2": round(float((diff <= 2).mean() * 100), 1),
            "board_mae_last20": round(float(tail.mean()), 2),
            "corner_err_px": {k: round(v, 1) for k, v in cerr.items()},
            "corner_err_mean_px": round(float(np.mean(list(cerr.values()))), 1),
            "top_width_true_px": round(truth["top_right"][0] - truth["top_left"][0], 1),
            "top_width_pred_px": round(corners["top_right"][0] - corners["top_left"][0], 1),
            "top_width_err_px": round((corners["top_right"][0] - corners["top_left"][0]) - (truth["top_right"][0] - truth["top_left"][0]), 1),
            "top_centre_err_px": round(((corners["top_right"][0] + corners["top_left"][0]) - (truth["top_right"][0] + truth["top_left"][0])) / 2, 1),
            "bottom_width_true_px": round(truth["bottom_right"][0] - truth["bottom_left"][0], 1),
            "bottom_width_pred_px": round(corners["bottom_right"][0] - corners["bottom_left"][0], 1)}


def summarize(rows, key="board_mae"):
    v = np.array([r[key] for r in rows if r.get("ok") and r.get(key) is not None], float)
    n = len(rows)
    if len(v) == 0:
        return {"n": n, "ok": 0, "mean": None, "median": None, "max": None, "within_2": 0.0}
    return {"n": n, "ok": int(len(v)), "mean": round(float(v.mean()), 2), "median": round(float(np.median(v)), 2),
            "max": round(float(v.max()), 2), "within_2": round(float((v <= 2).mean() * 100), 1)}


def dump(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, default=float))


def load(path):
    """Read a result JSON; falls back to <path>.gz (the large per-frame E3 files are committed gzipped)."""
    import gzip
    path = Path(path)
    if path.exists():
        return json.loads(path.read_text())
    gz = path.with_name(path.name + ".gz")
    if gz.exists():
        with gzip.open(gz, "rt") as fh:
            return json.load(fh)
    raise FileNotFoundError(path)


def has_result(path):
    path = Path(path)
    return path.exists() or path.with_name(path.name + ".gz").exists()


def landmarks_path(stem):
    return RESULTS / f"landmarks_{stem}.json"


# ------------------------------------------------------------ landmark truths (E1)
# The pins-based / all-landmark far end is measured once per video on the pre-hit
# frame and stored as fractions along the annotated top edge (a_l, a_r), so it
# applies to every frame's annotated quad without a camera warp (sample_input's
# per-frame hand corners keep their own motion; Chardie / tom_old's warped quads
# carry the same relative correction). Bottom corners are the annotated ones.
_lm_doc = {}


def landmark_doc(stem):
    if stem not in _lm_doc:
        _lm_doc[stem] = load(landmarks_path(stem))
    return _lm_doc[stem]


def truth_corners(stem, f, kind="annotated"):
    """kind: annotated (loop 1-3 truth) | pins (E1 pins-based far end) | all (foul + arrows + all pins fit)."""
    ann = L.truth_corners(stem, f)
    if kind == "annotated":
        return ann
    frac = landmark_doc(stem)["top_edge_fraction"][kind]
    tl, tr = np.array(ann["top_left"], float), np.array(ann["top_right"], float)
    d = tr - tl
    out = dict(ann)
    out["top_left"] = tuple(tl + frac["a_l"] * d)
    out["top_right"] = tuple(tl + frac["a_r"] * d)
    return out


TRUTHS = ("annotated", "pins", "all")


def score_both(stem, f, corners):
    """Loop-1 metric against every truth: {truth: {board_mae, ..., board_mae_last20}}."""
    return {k: score_corners(stem, f, corners, truth=truth_corners(stem, f, k)) for k in TRUTHS}
