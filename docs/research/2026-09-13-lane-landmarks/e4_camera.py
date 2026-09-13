"""E4: the static landmarks as the camera model. On every frame, E2's detected
arrows (+ pin bases while they stand) are matched to the same landmarks on the
reference frame; a similarity (RANSAC, then least squares on inliers) is the
per-frame camera motion. Compared on sample_input, which has hand-clicked corners
on every frame, against loop 3's ORB camera model (camera_all_sample_input.json):
warp the static reference corners through each model and measure the px distance
to the hand corners. Also reports the per-frame count of landmarks used.
usage: e4_camera.py [--tag loop3] [stems...]"""
import argparse
import json

import cv2
import numpy as np

import common as C
import landmarks as LM

L = C.L
C.use_full_camera()
PRED = C.SCRATCH / "pred"


def frame_landmarks(det, ph, f, min_dark=12.0):
    pts = {}
    for b, v in det.get("arrows", {}).items():
        if v.get("darkness", 99) >= min_dark:
            pts[f"arrow_{b}"] = (v["x"], v["y"])
    if f < ph - 1 and det.get("pins") and det["pins"].get("ok"):
        for k, p in det["pins"]["bases"].items():
            pts[f"pin_{k}"] = (p[0], p[1])
    return pts


def similarity(src, dst):
    """2x3 similarity src->dst by RANSAC (cv2.estimateAffinePartial2D), None if < 3 inliers."""
    if len(src) < 3:
        return None, 0
    A, inl = cv2.estimateAffinePartial2D(np.float32(src), np.float32(dst), method=cv2.RANSAC, ransacReprojThreshold=4.0, maxIters=2000, confidence=0.995)
    if A is None:
        return None, 0
    return A, int(inl.sum())


def run(stem, tag):
    dets = {int(k): v for k, v in json.loads((PRED / f"lm_{tag}_{stem}.json").read_text()).items()}
    p2 = PRED / f"lm2_{tag}_{stem}.json"   # second-pass arrows from e3_fit (detected from the pin-corrected lane)
    if p2.exists():
        for k, v in json.loads(p2.read_text()).items():
            if int(k) in dets:
                dets[int(k)]["arrows"] = v["arrows"]
    ph = L.pin_hit_frame(stem)
    cam = L.camera(stem)
    # reference = the frame the static corners belong to, so both models warp the same points
    f_ref = L.STATIC_FRAME.get(stem, cam["static_frame"] if cam.get("static_frame") is not None else cam["ref"])
    ref_lm = frame_landmarks(dets[f_ref], ph, f_ref) if f_ref in dets else {}
    # reference landmarks: use the E1 truth landmarks on the reference frame when the detection is thin
    truth_ref = LM.truth_landmarks(stem, f_ref, "all")
    ref_pts = {k: truth_ref[k if k.startswith("arrow") else k + "_base"] for k in list(truth_ref.keys()) if False}
    ref_pts = {}
    for k, v in truth_ref.items():
        kk = k.replace("_base", "")
        ref_pts[kk] = v
    static = C.gt.lane_gt(stem)
    ann = C.gt.load_annotation(stem); fle = ann.get("frame_lane_edges")
    if fle:
        # per-frame hand corners exist: judge both camera models on how well they carry the hand
        # corners of the first frame onto every other frame (no static-corner frame to guess)
        f_ref = min(int(k) for k in fle)
        static = {k: tuple(fle[str(f_ref)][k]) for k in C.KEYS}
        ref_pts = {}
        for k, v in LM.truth_landmarks(stem, f_ref, "all").items():
            ref_pts[k.replace("_base", "")] = v
    rows = []
    prev_A = None
    for f in sorted(dets):
        lm = frame_landmarks(dets[f], ph, f)
        common = [k for k in lm if k in ref_pts]
        src = [ref_pts[k] for k in common]; dst = [lm[k] for k in common]
        A, n_in = similarity(src, dst)
        how = "landmarks"
        if A is None or n_in < 3:
            A = prev_A if prev_A is not None else np.array([[1, 0, 0], [0, 1, 0]], float); how = "hold"; n_in = 0
        prev_A = A
        row = {"frame": f, "n_landmarks": len(common), "inliers": n_in, "how": how, "A": [[float(v) for v in r] for r in A]}
        if fle:  # sample_input: per-frame hand corners exist
            A_orb = L.transform(stem, f_ref, f)
            e_lm, e_orb = [], []
            for k in C.KEYS:
                p_lm = L.warp_pt(A, static[k]); p_orb = L.warp_pt(A_orb, static[k]); q = fle[str(f)][k]
                e_lm.append(float(np.hypot(p_lm[0] - q[0], p_lm[1] - q[1]))); e_orb.append(float(np.hypot(p_orb[0] - q[0], p_orb[1] - q[1])))
            row["err_landmarks_px"] = round(float(np.mean(e_lm)), 2); row["err_orb_px"] = round(float(np.mean(e_orb)), 2)
            row["err_landmarks_top_px"] = round(float(np.mean(e_lm[:2])), 2); row["err_orb_top_px"] = round(float(np.mean(e_orb[:2])), 2)
        else:
            # no per-frame hand truth: agreement with ORB on the static corners
            A_orb = L.transform(stem, f_ref, f)
            d = [float(np.hypot(*(np.array(L.warp_pt(A, static[k])) - np.array(L.warp_pt(A_orb, static[k]))))) for k in C.KEYS]
            row["vs_orb_px"] = round(float(np.mean(d)), 2)
        rows.append(row)
    summ = {"frames": len(rows), "frames_with_landmark_fit": sum(1 for r in rows if r["how"] == "landmarks"),
            "landmarks_per_frame_median": float(np.median([r["n_landmarks"] for r in rows]))}
    if fle:
        throw = set(C.throw_frames(stem))
        for key in ("err_landmarks_px", "err_orb_px", "err_landmarks_top_px", "err_orb_top_px"):
            v = [r[key] for r in rows]; vt = [r[key] for r in rows if r["frame"] in throw]
            summ[key + "_mean"] = round(float(np.mean(v)), 2); summ[key + "_max"] = round(float(np.max(v)), 2); summ[key + "_throw_mean"] = round(float(np.mean(vt)), 2)
    else:
        summ["vs_orb_px_mean"] = round(float(np.mean([r["vs_orb_px"] for r in rows])), 2)
    C.dump(C.RESULTS / f"e4_camera_{tag}__{stem}.json", {"stem": stem, "tag": tag, "ref": f_ref, "summary": summ, "per_frame": rows})
    print(f"E4 {C.SHORT[stem]:13s} {summ}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="loop3"); ap.add_argument("stems", nargs="*")
    a = ap.parse_args()
    for stem in a.stems or C.STEMS:
        run(stem, a.tag)
