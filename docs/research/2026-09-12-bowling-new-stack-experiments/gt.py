"""Shared ground-truth loading, frame extraction and the 50px-center metric.

Mirrors src/evaluation.py in the engine so numbers are comparable with the
detection scoreboard (TP = predicted center within 50px of annotated center).
"""
import json
import os
from pathlib import Path

import cv2
import numpy as np

ENGINE = Path("/Users/toka/code/bowling-app/analysis-engine")
EXP = Path(__file__).resolve().parent
FRAMES = EXP / "frames"

VIDEOS = {
    "sample_input": ENGINE / "sample_input.mp4",
    "20260112_121117": ENGINE / "videos/input/20260112_121117.mp4",
    "tom_old": ENGINE / "videos/input/tom_old.mp4",
}


def load_annotation(stem):
    return json.load(open(ENGINE / "annotations" / stem / "annotation.json"))


def ball_gt(stem):
    """{frame_idx: (x, y, r)} for frames with a ball, plus set of explicit no-ball frames."""
    ann = load_annotation(stem)
    pos, neg = {}, set()
    for k, v in ann["ball_annotations"].items():
        if v is None:
            neg.add(int(k))
        else:
            pos[int(k)] = (float(v["x"]), float(v["y"]), float(v.get("radius", v.get("r", 15))))
    return pos, neg


def lane_gt(stem):
    e = load_annotation(stem)["lane_edges"]
    return {k: tuple(e[k]) for k in ("top_left", "top_right", "bottom_left", "bottom_right")}


def frame_path(stem, idx):
    return FRAMES / stem / f"{idx:05d}.jpg"


def extract_frames(stem, indices=None):
    """Write JPEGs for the requested frame indices (all frames when None)."""
    out = FRAMES / stem
    out.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(VIDEOS[stem]))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    want = set(range(n)) if indices is None else set(indices)
    idx = 0
    written = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx in want:
            p = frame_path(stem, idx)
            if not p.exists():
                cv2.imwrite(str(p), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            written += 1
        idx += 1
    cap.release()
    return written, idx


def evaluate_centers(pred, gt_pos, gt_neg=None, radius_px=50.0):
    """pred: {frame_idx: (x, y) or None}. Returns scoreboard-style metrics.

    Frames in gt_pos with no prediction count as FN. Predictions on frames in
    gt_neg (explicit no-ball frames) count as FP. Predictions >radius from GT
    count as both FN and FP, like src/evaluation.py.
    """
    tp = fn = fp = 0
    errors = []
    for f, (gx, gy, _r) in gt_pos.items():
        p = pred.get(f)
        if p is None:
            fn += 1
            continue
        d = float(np.hypot(p[0] - gx, p[1] - gy))
        if d <= radius_px:
            tp += 1
            errors.append(d)
        else:
            fn += 1
            fp += 1
    for f in (gt_neg or ()):
        if pred.get(f) is not None:
            fp += 1
    total = len(gt_pos)
    return {
        "tp": tp, "fn": fn, "fp": fp, "total": total,
        "recall": 100.0 * tp / total if total else 0.0,
        "precision": 100.0 * tp / (tp + fp) if (tp + fp) else 0.0,
        "mean_err_px": float(np.mean(errors)) if errors else None,
        "max_err_px": float(np.max(errors)) if errors else None,
    }


def board_from_corners(corners, pts, lane_width_px=390.0, lane_len_px=1000.0):
    """Map image points to board numbers using a 4-corner homography.

    Same convention as the engine's BoardCalculator: lane_x=0 -> board 1
    (right gutter side), lane_x=width -> board 39. corners: dict with
    top_left/top_right/bottom_left/bottom_right in image px. Returns raw
    (unrounded) board numbers.
    """
    src = np.float32([corners["top_left"], corners["top_right"],
                      corners["bottom_right"], corners["bottom_left"]])
    # bird's-eye: x grows to the right, so right gutter is x=lane_width.
    dst = np.float32([[0, 0], [lane_width_px, 0],
                      [lane_width_px, lane_len_px], [0, lane_len_px]])
    H = cv2.getPerspectiveTransform(src, dst)
    p = np.float32(pts).reshape(-1, 1, 2)
    lane = cv2.perspectiveTransform(p, H).reshape(-1, 2)
    # board 1 is the rightmost board -> flip x so that right edge maps to 0.
    lane_x = lane_width_px - lane[:, 0]
    return (lane_x / lane_width_px) * 38.0 + 1.0, lane[:, 1] / lane_len_px


def image_b64(path):
    import base64
    return base64.b64encode(open(path, "rb").read()).decode()
