"""Per-frame camera motion so the lane truth can follow a handheld phone.

For every frame from 5 before release to the last ball frame, fit a
similarity transform (ORB + RANSAC) from the reference frame. The static
annotated lane corners are warped through it to give per-frame truth; on
sample_input, which carries hand-annotated per-frame corners, the warped
corners are checked against them.

Writes results/camera_<stem>.json = {"ref": f, "affine": {f: [[a,b,tx],[c,d,ty]]}, ...}
"""
import json
import sys

import cv2
import numpy as np

import gt
import lane_sam as L

KEYS = L.KEYS


def affine_between(img_ref, img, orb, bf):
    k1, d1 = orb.detectAndCompute(img_ref, None)
    k2, d2 = orb.detectAndCompute(img, None)
    if d1 is None or d2 is None:
        return None, 0
    m = bf.match(d1, d2)
    if len(m) < 20:
        return None, len(m)
    p1 = np.float32([k1[x.queryIdx].pt for x in m])
    p2 = np.float32([k2[x.trainIdx].pt for x in m])
    M, inl = cv2.estimateAffinePartial2D(p1, p2, method=cv2.RANSAC, ransacReprojThreshold=3)
    return M, int(inl.sum()) if inl is not None else 0


def edge_alignment(img, corners):
    """Mean |Sobel x| along the two lane edge segments: high when these fixed
    pixel coordinates sit on the real lane edges in this frame."""
    g = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (3, 3), 0)
    gx = np.abs(cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3))
    vals = []
    for a, b in (("top_left", "bottom_left"), ("top_right", "bottom_right")):
        (x1, y1), (x2, y2) = corners[a], corners[b]
        for t in np.linspace(0.05, 0.95, 60):
            x, y = x1 + t * (x2 - x1), y1 + t * (y2 - y1)
            xi, yi = int(round(x)), int(round(y))
            if 0 <= yi < gx.shape[0] and 1 <= xi < gx.shape[1] - 1:
                vals.append(gx[yi, xi - 1:xi + 2].max())
    return float(np.mean(vals)) if vals else 0.0


def run(stem):
    fs, _ = L.trajectory(stem)
    f_ref = max(0, fs[0] - 5)
    frames = list(range(f_ref, fs[-1] + 1))
    orb = cv2.ORB_create(4000)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    ref = cv2.imread(str(gt.frame_path(stem, f_ref)), 0)
    aff, inliers = {}, {}
    for f in frames:
        if f == f_ref:
            aff[f] = [[1, 0, 0], [0, 1, 0]]
            inliers[f] = -1
            continue
        img = cv2.imread(str(gt.frame_path(stem, f)), 0)
        M, n = affine_between(ref, img, orb, bf)
        if M is None:
            M = np.array(aff[f - 1], float)
        aff[f] = [[float(v) for v in row] for row in M]
        inliers[f] = n
    static = gt.lane_gt(stem)
    # which frame do the static corners belong to? the one where they sit on edges
    align = {}
    for f in frames[::2]:
        align[f] = edge_alignment(cv2.imread(str(gt.frame_path(stem, f))), static)
    f_static = max(align, key=align.get)
    out = {"stem": stem, "ref": f_ref, "static_frame": f_static, "frames": frames,
           "affine": {str(f): aff[f] for f in frames}, "inliers": {str(f): inliers[f] for f in frames},
           "edge_alignment": {str(f): round(v, 1) for f, v in align.items()}}
    ann = gt.load_annotation(stem)
    if "frame_lane_edges" in ann:
        # validate: warp static corners (from f_static) to each frame, compare to the hand annotation
        A_s = np.array(aff[f_static], float)
        errs = {}
        for f in frames:
            if str(f) not in ann["frame_lane_edges"]:
                continue
            A_f = np.array(aff[f], float)
            T = compose(A_f, invert(A_s))
            e = []
            for k in KEYS:
                p = warp(T, static[k])
                q = ann["frame_lane_edges"][str(f)][k]
                e.append(float(np.hypot(p[0] - q[0], p[1] - q[1])))
            errs[f] = round(float(np.mean(e)), 1)
        out["validation_px"] = errs
        out["validation_summary"] = {"mean": round(float(np.mean(list(errs.values()))), 1),
                                     "max": round(float(np.max(list(errs.values()))), 1)}
        # and the drift the static truth would have suffered without warping
        drift = {}
        for f, e in ann["frame_lane_edges"].items():
            drift[int(f)] = round(float(np.mean([np.hypot(e[k][0] - static[k][0], e[k][1] - static[k][1]) for k in KEYS])), 1)
        out["static_drift_px"] = {"mean": round(float(np.mean(list(drift.values()))), 1), "max": round(float(np.max(list(drift.values()))), 1)}
    ex = np.array([aff[f] for f in frames])
    out["motion_summary"] = {"max_shift_px": round(float(np.max(np.hypot(ex[:, 0, 2], ex[:, 1, 2]))), 1),
                             "min_inliers": int(min(v for v in inliers.values() if v >= 0))}
    (L.EXP / "results").mkdir(exist_ok=True)
    (L.EXP / "results" / f"camera_{stem}.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("stem", "ref", "static_frame", "motion_summary") if k in out}
                     | {k: out[k] for k in ("validation_summary", "static_drift_px") if k in out}))


def invert(A):
    A = np.asarray(A, float)
    R = A[:, :2]
    t = A[:, 2]
    Ri = np.linalg.inv(R)
    return np.hstack([Ri, (-Ri @ t)[:, None]])


def compose(A, B):
    """A after B (both 2x3)."""
    A3 = np.vstack([A, [0, 0, 1]])
    B3 = np.vstack([B, [0, 0, 1]])
    return (A3 @ B3)[:2]


def warp(A, p):
    A = np.asarray(A, float)
    x, y = p[0], p[1]
    return (A[0, 0] * x + A[0, 1] * y + A[0, 2], A[1, 0] * x + A[1, 1] * y + A[1, 2])


if __name__ == "__main__":
    for s in (sys.argv[1:] or list(gt.VIDEOS)):
        run(s)
