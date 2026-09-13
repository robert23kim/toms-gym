"""Shared setup for loop 2. Reuses gt.py / lane_sam.py / camera results from the
2026-09-12 folder so every number here is measured with the same metric, the
same per-frame truth and the same ball-path prompts as the previous table.

Frame kinds add `prehit` (pin_hit - 2): pins standing, bowler off the lane,
no motion blur. `last` stays what it was (the last annotated ball frame, which
is after pin contact on two of the three videos) so rows are comparable.
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PREV = HERE.parent / "2026-09-12-sam2-lane-experiments"
SCRATCH = Path(os.environ.get(
    "SAM2X_SCRATCH",
    "/private/tmp/claude-502/-Users-toka-code-toms-gym/aec659a7-dd91-473a-be23-bf34027e9b97/scratchpad"))
os.environ.setdefault("SAM_FRAMES", str(SCRATCH / "frames"))
os.environ.setdefault("SAM_WEIGHTS", str(SCRATCH / "weights"))
sys.path.insert(0, str(PREV))

import gt  # noqa: E402
import lane_sam as L  # noqa: E402

RESULTS = HERE / "results"
OVERLAYS = HERE / "overlays"
STEMS = list(gt.VIDEOS)
LABEL = {"sample_input": "sample_input (1080p, handheld)", "20260112_121117": "Chardie (720p, handheld)",
         "tom_old": "tom_old (688p, tripod)"}


def frame_for(stem, kind, back=2):
    """Frame index for a kind: pre / mid / last as in lane_sam.frame_indices,
    prehit = pin-hit marker minus `back` frames, preN = N frames before release."""
    if kind == "prehit":
        return L.pin_hit_frame(stem) - back
    if kind.startswith("prehit-"):
        return L.pin_hit_frame(stem) - int(kind.split("-")[1])
    return L.frame_indices(stem, kind)[0]


def read_frame(stem, f):
    import cv2
    return cv2.imread(str(gt.frame_path(stem, f)))


def path_points_between(stem, f, y0, y1, n=3, lo=0.15, hi=0.85, avoid_r=3.0):
    """n positive points spaced evenly by image length along the part of the
    (camera-warped) ball path whose y lies in [y0, y1], between lo and hi of
    that part's length. Same rule as lane_sam.track_points_even, restricted
    to a band so crops get their own prompts."""
    import numpy as np
    pts = np.array(L.ball_points_on_ordered(stem, f), float)
    keep = (pts[:, 1] >= y0) & (pts[:, 1] <= y1)
    pts = pts[keep]
    if len(pts) < 2:
        return [[int(v) for v in p] for p in pts]
    seg = np.hypot(*(np.diff(pts, axis=0).T))
    cum = np.concatenate([[0], np.cumsum(seg)])
    _, pos = L.trajectory(stem)
    here = pos.get(f)
    out = []
    for t in np.linspace(lo, hi, n):
        i = int(np.searchsorted(cum, t * cum[-1]))
        i = min(max(i, 0), len(pts) - 1)
        if here is not None:
            # never prompt on the ball itself: slide toward the foul line until clear
            r = avoid_r * max(here[2], 8)
            while i > 0 and np.hypot(pts[i][0] - here[0], pts[i][1] - here[1]) < r:
                i -= 1
        out.append([int(pts[i][0]), int(pts[i][1])])
    return out


def even_points_keep(stem, f, n=3, lo=0.15, hi=0.85, avoid_r=3.0):
    """Like lane_sam.track_points_even but keeps n points: a point that would
    land within avoid_r ball radii of the ball on this frame is slid along the
    path toward the foul line until it is clear, instead of being dropped.
    On pre-hit frames the ball sits at the far end and the loop-1 rule left
    only two prompts, so the mask stopped short of the pin deck."""
    import numpy as np
    _, pos = L.trajectory(stem)
    pts = np.array(L.ball_points_on_ordered(stem, f), float)
    if len(pts) < 2:
        return [[int(v) for v in p] for p in pts]
    seg = np.hypot(*(np.diff(pts, axis=0).T))
    cum = np.concatenate([[0], np.cumsum(seg)])
    total = cum[-1]
    here = pos.get(f)
    out = []
    for t in np.linspace(lo, hi, n):
        i = int(np.searchsorted(cum, t * total))
        i = min(max(i, 0), len(pts) - 1)
        if here is not None:
            r = avoid_r * max(here[2], 8)
            while i > 0 and np.hypot(pts[i][0] - here[0], pts[i][1] - here[1]) < r:
                i -= 1
        out.append([int(pts[i][0]), int(pts[i][1])])
    return out
