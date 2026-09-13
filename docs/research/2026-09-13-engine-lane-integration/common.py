"""Shared setup for the engine-integration loop. Reuses loop 1's gt.py /
lane_sam.py (metric, per-frame truth, camera warps) and loop 4's pins-based
far end so every number is measured exactly as in loops 1-4.

Frames live in the session scratchpad (EI_SCRATCH); results/ and overlays/ in
this folder are the deliverables. The engine under test is the worktree
~/code/bowling-app/lane-engine (branch feat/sam-lane-calibration); the old
engine is ~/code/bowling-app/situp-engine (05267b1, the deployed lineage).
"""
import json
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
LOOP1 = HERE.parent / "2026-09-12-sam2-lane-experiments"
LOOP4 = HERE.parent / "2026-09-13-lane-landmarks"
SCRATCH = Path(os.environ.get(
    "EI_SCRATCH",
    "/private/tmp/claude-502/-Users-toka-code-toms-gym/a9379cd8-1e58-4282-9859-05090e08da3d/scratchpad"))
os.environ.setdefault("SAM_FRAMES", str(SCRATCH / "frames"))
sys.path.insert(0, str(LOOP1))

import gt  # noqa: E402
import lane_sam as L  # noqa: E402

RESULTS = HERE / "results"
OVERLAYS = HERE / "overlays"
RUNS = SCRATCH / "runs"
STEMS = list(gt.VIDEOS)
SHORT = {"sample_input": "sample_input", "20260112_121117": "Chardie", "tom_old": "tom_old"}
LABEL = {"sample_input": "sample_input (1080p, handheld)", "20260112_121117": "Chardie (720p, handheld)",
         "tom_old": "tom_old (688p, tripod)"}
KEYS = L.KEYS
OLD_ENGINE = Path.home() / "code/bowling-app/situp-engine"
NEW_ENGINE = Path.home() / "code/bowling-app/lane-engine"
PY = Path.home() / "code/bowling-app/analysis-engine/.venv/bin/python"
TRUTHS = ("annotated", "pins")


def throw_frames(stem):
    fs, _ = L.trajectory(stem)
    return list(range(max(0, fs[0] - 5), fs[-1] + 1))


def clean_frames(stem):
    fs, _ = L.trajectory(stem)
    return [f for f in throw_frames(stem) if f >= fs[0] + 3]


_lm = {}


def truth_corners(stem, f, kind="annotated"):
    """annotated = loops 1-3 truth (per-frame on sample_input, warped static
    corners elsewhere); pins = loop 4's pins-based far end as fractions of the
    annotated top edge."""
    ann = L.truth_corners(stem, f)
    if kind == "annotated":
        return ann
    if stem not in _lm:
        _lm[stem] = json.loads((LOOP4 / "results" / f"landmarks_{stem}.json").read_text())
    frac = _lm[stem]["top_edge_fraction"][kind]
    tl, tr = np.array(ann["top_left"], float), np.array(ann["top_right"], float)
    d = tr - tl
    out = dict(ann)
    out["top_left"] = tuple(tl + frac["a_l"] * d)
    out["top_right"] = tuple(tl + frac["a_r"] * d)
    return out


def score_corners(stem, f, corners, kind="annotated"):
    """Loop-1 metric: boards of the annotated ball path (warped into frame f)
    through `corners` vs through the truth corners of frame f."""
    truth = truth_corners(stem, f, kind)
    pts = L.ball_points_on(stem, f)
    b_true, _ = gt.board_from_corners(truth, pts)
    b_pred, _ = gt.board_from_corners(corners, pts)
    diff = np.abs(b_pred - b_true)
    n = len(diff)
    tail = diff[int(0.8 * n):] if n >= 5 else diff
    return {"board_mae": round(float(diff.mean()), 2), "board_max": round(float(diff.max()), 2),
            "within_2": round(float((diff <= 2).mean() * 100), 1), "tail_mae": round(float(tail.mean()), 2),
            "top_width_err_px": round(float((corners["top_right"][0] - corners["top_left"][0]) - (truth["top_right"][0] - truth["top_left"][0])), 1),
            "top_centre_err_px": round(float(((corners["top_right"][0] + corners["top_left"][0]) - (truth["top_right"][0] + truth["top_left"][0])) / 2), 1)}


def corners_at_truth_rows(stem, f, corners):
    """Re-cut a quad's edge lines at the truth's top/bottom rows so every method is
    compared on the same rows (loop-1 convention)."""
    y_top, y_bot = L.gt_y(stem, f)

    def line(p, q):
        (x1, y1), (x2, y2) = p, q
        if abs(y2 - y1) < 1e-9:
            return (0.0, float(x1))
        a = (x2 - x1) / (y2 - y1)
        return (a, x1 - a * y1)
    left = line(corners["top_left"], corners["bottom_left"])
    right = line(corners["top_right"], corners["bottom_right"])
    return L.lines_to_corners(left, right, y_top, y_bot)


def polyline_corners_at_truth_rows(stem, f, left_pts, right_pts):
    """The old engine's per-Y interpolation between polyline points, evaluated at
    the truth rows (the engine's own board math for its dynamic edges)."""
    y_top, y_bot = L.gt_y(stem, f)
    lp = np.asarray(left_pts, float)
    rp = np.asarray(right_pts, float)
    lo = np.argsort(lp[:, 1]); ro = np.argsort(rp[:, 1])
    lx = lambda y: float(np.interp(y, lp[lo, 1], lp[lo, 0]))  # noqa: E731
    rx = lambda y: float(np.interp(y, rp[ro, 1], rp[ro, 0]))  # noqa: E731
    return {"top_left": (lx(y_top), y_top), "top_right": (rx(y_top), y_top),
            "bottom_left": (lx(y_bot), y_bot), "bottom_right": (rx(y_bot), y_bot)}


def summarize(rows, key="board_mae"):
    v = np.array([r[key] for r in rows if r.get("ok") and r.get(key) is not None], float)
    if len(v) == 0:
        return {"n": len(rows), "ok": 0, "mean": None, "median": None, "max": None, "within_2": 0.0}
    return {"n": len(rows), "ok": int(len(v)), "mean": round(float(v.mean()), 2), "median": round(float(np.median(v)), 2),
            "max": round(float(v.max()), 2), "within_2": round(float((v <= 2).mean() * 100), 1)}


def dump(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, default=float))


def load(path):
    return json.loads(Path(path).read_text())
