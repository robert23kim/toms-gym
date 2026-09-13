"""Shared setup for the cheap-lane-model loop. Reuses gt.py / lane_sam.py from
the 2026-09-12 SAM 2 folder so every number is measured with the same metric
and the same per-frame truth as the two SAM loops.

Datasets, weights, frames and training runs live in the session scratchpad
(LANE_SCRATCH); results/ and overlays/ in this folder are the deliverables.
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
SCRATCH = Path(os.environ.get(
    "LANE_SCRATCH",
    "/private/tmp/claude-502/-Users-toka-code-toms-gym/d71975f3-301e-4fe0-bb28-8bbc7bdffcb2/scratchpad"))
os.environ.setdefault("SAM_FRAMES", str(SCRATCH / "frames"))
os.environ.setdefault("SAM_WEIGHTS", str(SCRATCH / "weights"))
sys.path.insert(0, str(LOOP1))

import gt  # noqa: E402
import lane_sam as L  # noqa: E402

RESULTS = HERE / "results"
OVERLAYS = HERE / "overlays"
FRAMES = SCRATCH / "frames"
STEMS = list(gt.VIDEOS)  # annotated: sample_input, 20260112_121117 (Chardie), tom_old
LABEL = {"sample_input": "sample_input (1080p, handheld)", "20260112_121117": "Chardie (720p, handheld)",
         "tom_old": "tom_old (688p, tripod)", "bowling_video": "bowling_video (1080p, unlabeled)",
         "IMG_0242": "IMG_0242 (720p, unlabeled)"}
SHORT = {"sample_input": "sample_input", "20260112_121117": "Chardie", "tom_old": "tom_old",
         "bowling_video": "bowling_video", "IMG_0242": "IMG_0242"}
UNLABELED = {"bowling_video": Path.home() / "Downloads/bowling_video.mp4",
             "IMG_0242": Path.home() / "Downloads/IMG_0242.mov"}
KEYS = L.KEYS


def extract_unlabeled(stem, step=1):
    out = FRAMES / stem
    out.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(UNLABELED[stem]))
    idx = n = 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        if idx % step == 0:
            p = out / f"{idx:05d}.jpg"
            if not p.exists():
                cv2.imwrite(str(p), fr, [cv2.IMWRITE_JPEG_QUALITY, 95])
            n += 1
        idx += 1
    cap.release()
    return n, idx


def frame_ids(stem):
    return sorted(int(p.stem) for p in (FRAMES / stem).glob("*.jpg"))


def read_frame(stem, f):
    return cv2.imread(str(FRAMES / stem / f"{f:05d}.jpg"))


# ------------------------------------------------------------ extended camera
# Loop 1 fitted camera motion from 5 frames before release to the last ball
# frame. Training wants a label on every frame, so camera_all.py extends the
# fit to the whole video and this swaps it in for lane_sam's lookups.

def use_full_camera():
    for stem in STEMS:
        p = RESULTS / f"camera_all_{stem}.json"
        if p.exists():
            L._cam[stem] = json.loads(p.read_text())


def truth_quad(stem, f):
    """Annotated lane corners on frame f (per-frame annotation on sample_input,
    static corners warped through the camera model elsewhere)."""
    return L.truth_corners(stem, f)


def throw_frames(stem):
    """Frames from 5 before release to the last on-lane ball frame (loop-1 scoring span)."""
    fs, _ = L.trajectory(stem)
    return list(range(max(0, fs[0] - 5), fs[-1] + 1))


def occluded_frames(stem):
    """Frames where the bowler is still on the approach / at the line: from the
    start of the video to 3 frames after release. SAM 2 fails on these; a
    learned model has a chance."""
    fs, _ = L.trajectory(stem)
    return list(range(0, fs[0] + 3))


def clean_frames(stem):
    fs, _ = L.trajectory(stem)
    return [f for f in throw_frames(stem) if f >= fs[0] + 3]


def corners_from_mask(stem, f, mask, anchors=None):
    """Loop-1 edge fit: rows between the annotated top/bottom y, robust line per
    edge, corners at those y. Returns (corners, lines, info) or None."""
    y_top, y_bot = L.gt_y(stem, f)
    if anchors is None:
        anchors = L.ball_points_on(stem, f)
    fit = L.fit_edges(mask, y_top, y_bot, anchors)
    if fit is None:
        return None
    left, right, info = fit
    return L.lines_to_corners(left, right, y_top, y_bot), (left, right), info


def corners_from_quad(stem, f, quad):
    """Corners from four predicted keypoints: fit the two edge lines through the
    predicted corner pairs and evaluate at the annotated y so the metric is the
    same as the mask path."""
    y_top, y_bot = L.gt_y(stem, f)
    (lx1, ly1), (lx2, ly2) = quad["top_left"], quad["bottom_left"]
    (rx1, ry1), (rx2, ry2) = quad["top_right"], quad["bottom_right"]
    if abs(ly2 - ly1) < 1 or abs(ry2 - ry1) < 1:
        return None
    la = (lx2 - lx1) / (ly2 - ly1); lb = lx1 - la * ly1
    ra = (rx2 - rx1) / (ry2 - ry1); rb = rx1 - ra * ry1
    return L.lines_to_corners((la, lb), (ra, rb), y_top, y_bot), ((la, lb), (ra, rb))


def score_row(stem, f, corners, extra=None):
    row = {"stem": stem, "frame": f, "ok": corners is not None}
    if corners is not None:
        row.update(L.score(stem, corners, f))
        row["corners"] = {k: [round(float(v[0]), 1), round(float(v[1]), 1)] for k, v in corners.items()}
    if extra:
        row.update(extra)
    return row


def summarize(rows, key="board_mae"):
    v = np.array([r[key] for r in rows if r.get("ok")], float)
    n = len(rows)
    if len(v) == 0:
        return {"n": n, "ok": 0, "mean": None, "median": None, "max": None, "within_2": 0.0}
    return {"n": n, "ok": int(len(v)), "mean": round(float(v.mean()), 2), "median": round(float(np.median(v)), 2),
            "max": round(float(v.max()), 2), "within_2": round(float((v <= 2).mean() * 100), 1)}


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1))
