"""Per-frame camera motion for EVERY frame of the annotated videos (loop 1
only covered the throw). ORB + RANSAC similarity against loop 1's reference
frame, chained through the previous frame when a direct match is weak.
Writes results/camera_all_<stem>.json in loop 1's schema and validates the
warped static corners against sample_input's per-frame annotation.
"""
import json
import sys

import cv2
import numpy as np

import common as C
from camera_motion_shim import affine_between

L = C.L


def run(stem):
    cam1 = L.camera(stem)
    f_ref = cam1["ref"]
    frames = C.frame_ids(stem)
    orb = cv2.ORB_create(4000)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    ref = cv2.imread(str(C.FRAMES / stem / f"{f_ref:05d}.jpg"), 0)
    aff, inl, how = {}, {}, {}
    prev_img, prev_A = ref, np.array([[1, 0, 0], [0, 1, 0]], float)
    for f in frames:
        img = cv2.imread(str(C.FRAMES / stem / f"{f:05d}.jpg"), 0)
        if f == f_ref:
            A, n, h = np.array([[1, 0, 0], [0, 1, 0]], float), -1, "ref"
        else:
            A, n = affine_between(ref, img, orb, bf)
            h = "direct"
            if A is None or n < 40:
                # chain: prev->this composed with ref->prev
                B, m = affine_between(prev_img, img, orb, bf)
                if B is not None and m >= 20:
                    A = (np.vstack([B, [0, 0, 1]]) @ np.vstack([prev_A, [0, 0, 1]]))[:2]
                    n, h = m, "chain"
                elif A is None:
                    A, n, h = prev_A, 0, "hold"
        aff[f] = [[float(v) for v in row] for row in A]
        inl[f] = int(n)
        how[f] = h
        prev_img, prev_A = img, np.array(A, float)
    out = {"stem": stem, "ref": f_ref, "static_frame": cam1.get("static_frame"), "frames": frames,
           "affine": {str(f): aff[f] for f in frames}, "inliers": {str(f): inl[f] for f in frames},
           "how": {str(f): how[f] for f in frames}}
    # agreement with loop 1 on the overlapping frames (corner px)
    static = C.gt.lane_gt(stem)
    d = []
    for f in cam1["frames"]:
        A1 = np.array(cam1["affine"][str(f)], float); A2 = np.array(aff[f], float)
        for k in C.KEYS:
            p1 = L.warp_pt(A1, static[k]); p2 = L.warp_pt(A2, static[k])
            d.append(np.hypot(p1[0] - p2[0], p1[1] - p2[1]))
    out["vs_loop1_px_mean"] = round(float(np.mean(d)), 2)
    out["vs_loop1_px_max"] = round(float(np.max(d)), 2)
    C.dump(C.RESULTS / f"camera_all_{stem}.json", out)
    print(stem, "frames", len(frames), "how", {h: sum(1 for v in how.values() if v == h) for h in ("ref", "direct", "chain", "hold")},
          "vs loop1 px mean/max", out["vs_loop1_px_mean"], out["vs_loop1_px_max"])
    return out


def validate_sample_input(out):
    """Warp the static corners to every frame and compare with the hand
    per-frame annotation (the label noise a camera-warped label carries)."""
    ann = C.gt.load_annotation("sample_input")
    fle = ann["frame_lane_edges"]
    static = C.gt.lane_gt("sample_input")
    f_static = L.STATIC_FRAME.get("sample_input", out["static_frame"])
    A_s = np.array(out["affine"][str(f_static)], float)
    inv = L._inv(A_s)
    errs = {}
    for f in out["frames"]:
        A = np.array(out["affine"][str(f)], float)
        T = (np.vstack([A, [0, 0, 1]]) @ np.vstack([inv, [0, 0, 1]]))[:2]
        e = []
        for k in C.KEYS:
            p = L.warp_pt(T, static[k]); q = fle[str(f)][k]
            e.append(np.hypot(p[0] - q[0], p[1] - q[1]))
        errs[f] = float(np.mean(e))
    v = np.array(list(errs.values()))
    thr = [f for f in out["frames"] if f < 38]
    print("sample_input warped-static vs per-frame annotation: mean %.1f px max %.1f px; pre-release frames mean %.1f"
          % (v.mean(), v.max(), np.mean([errs[f] for f in thr])))
    return {"mean_px": round(float(v.mean()), 2), "max_px": round(float(v.max()), 2), "per_frame": {str(f): round(e, 1) for f, e in errs.items()}}


if __name__ == "__main__":
    stems = sys.argv[1:] or C.STEMS
    for s in stems:
        o = run(s)
        if s == "sample_input":
            val = validate_sample_input(o)
            C.dump(C.RESULTS / "camera_all_validation_sample_input.json", val)
