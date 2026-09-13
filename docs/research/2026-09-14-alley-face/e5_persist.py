"""E5: persistence through the throw. Per frame, the landmarks E4 refined on that frame (arrows,
the three dot rows, the pin bases while they stand, the near corners) are matched by name to the
same landmarks on a reference frame (the pre-hit frame) and a similarity is fitted by RANSAC -
the static-landmark camera model; with the dots as a second near depth the arrows are no longer the
only static row after the pins fall. Landmarks missing on a frame (bowler, ball, fallen pins) are
carried from the reference through that camera model, and the lane is fitted on every frame from
detected + carried landmarks. The rack is also POOLED: every standing-pin frame's fitted bases are
moved into the reference frame and the median taken (loop 4 finding 9), then moved back per frame
(-> $AF_SCRATCH/pred/pooled_pins_<stem>.json, consumed by E4's pins-pooled variant). Compared with
loop 4's +carry / +carryLM rows and with the ORB camera (loop 3's camera_all) on sample_input's
hand per-frame corners. Writes results/e5_persist_<stem>.json. usage: e5_persist.py [stems...]"""
import argparse
import gzip
import json

import cv2
import numpy as np

import af
import e4_align as E4

LM = af.LM
CONST = af.constellation()


def frame_landmarks(al, f, ph):
    """{name: (x, y)} of everything E4 refined on frame f (pins only while standing)."""
    a = al.get(str(f))
    if not a:
        return {}
    pts = {}
    for cls, rr in a["rows"].items():
        for n, (x, y) in rr.items():
            pts[n] = (x, y)
    if a.get("pins") and f < ph - 1:
        for n, (x, y) in a["pins"].items():
            pts[n] = (x, y)
    for n, (x, y) in (a.get("corners") or {}).items():
        pts[n] = (x, y)
    return pts


def similarity(src, dst):
    if len(src) < 3:
        return None, 0
    A, inl = cv2.estimateAffinePartial2D(np.float32(src), np.float32(dst), method=cv2.RANSAC, ransacReprojThreshold=4.0, maxIters=2000, confidence=0.995)
    if A is None:
        return None, 0
    return A, int(inl.sum())


def warp(A, p):
    return (float(A[0, 0] * p[0] + A[0, 1] * p[1] + A[0, 2]), float(A[1, 0] * p[0] + A[1, 1] * p[1] + A[1, 2]))


def inv(A):
    R = A[:, :2]; Ri = np.linalg.inv(R)
    return np.hstack([Ri, (-Ri @ A[:, 2])[:, None]])


def run(stem):
    annotated = stem in af.STEMS
    with gzip.open(af.PRED / f"align_{stem}.json.gz", "rt") as fh:
        al = json.load(fh)
    ph = af.pin_hit(stem) if annotated else 10 ** 9
    frames = sorted(int(k) for k in al)
    if not frames:
        print("E5", stem, "nothing aligned"); return
    f_ref = af.frame_for(stem, "prehit") if annotated else frames[len(frames) // 2]
    if str(f_ref) not in al:
        f_ref = min(frames, key=lambda f: abs(f - f_ref))
    ref = frame_landmarks(al, f_ref, ph)
    # camera model per frame: similarity ref -> f on the named static landmarks
    cam = {}; rows = []
    prev = None
    for f in frames:
        lm = frame_landmarks(al, f, ph)
        common = [n for n in lm if n in ref]
        A, n_in = similarity([ref[n] for n in common], [lm[n] for n in common])
        how = "landmarks"
        if A is None or n_in < 3:
            A = prev if prev is not None else np.array([[1, 0, 0], [0, 1, 0]], float); how = "hold"; n_in = 0
        prev = A; cam[f] = A
        cls_used = {c: sum(1 for n in common if af.classes_of(n) == c) for c in ("arrow", "dot", "fdot", "adot", "pin", "foul")}
        rows.append({"frame": f, "n_common": len(common), "inliers": n_in, "how": how, "by_class": cls_used})
    # pooled rack: standing-pin frames' bases moved into the reference frame, median per pin
    pooled_ref = {}
    for f in frames:
        a = al[str(f)]
        if not a.get("pins") or f >= ph - 1 or rows[frames.index(f)]["how"] != "landmarks":
            continue
        Ai = inv(cam[f])
        for n, p in a["pins"].items():
            pooled_ref.setdefault(n, []).append(warp(Ai, p))
    pooled = {n: (float(np.median([p[0] for p in v])), float(np.median([p[1] for p in v]))) for n, v in pooled_ref.items() if len(v) >= 3}
    n_pool = int(np.median([len(v) for v in pooled_ref.values()])) if pooled_ref else 0
    pooled_per_frame = {str(f): {n: list(warp(cam[f], p)) for n, p in pooled.items()} for f in frames} if pooled else {}
    (af.PRED / f"pooled_pins_{stem}.json").write_text(json.dumps(pooled_per_frame))
    # carried lane per frame: detected landmarks + reference landmarks carried through the camera for the missing ones
    per = []
    if annotated:
        cam_orb = af.L
        ann = af.gt.load_annotation(stem); fle = ann.get("frame_lane_edges")
        static = {k: tuple(fle[str(min(int(q) for q in fle))][k]) for k in af.KEYS} if fle else None
        f0 = min(int(q) for q in fle) if fle else None
    for f in frames:
        lm = frame_landmarks(al, f, ph)
        carried = {}
        for n, p in ref.items():
            if n not in lm and not (af.classes_of(n) == "pin" and f >= ph - 1 and False):
                carried[n] = warp(cam[f], p)
        # pins after the hit: carried from the pooled rack (static in the scene)
        rows_ = {}; pins = {}; corners = {}
        for n, p in list(lm.items()) + list(carried.items()):
            cls = af.classes_of(n)
            if cls == "pin":
                pins[n] = p
            elif cls == "foul":
                corners[n] = p
            else:
                rows_.setdefault(cls, {})[n] = (p[0], p[1], 0.0)
        if pooled_per_frame.get(str(f)):
            pins = {n: tuple(p) for n, p in pooled_per_frame[str(f)].items()}
        H, names, dropped = E4.joint_fit(rows_, pins, {}, None, "rows+pins")
        row = {"frame": f, "n_detected": len(lm), "n_carried": len(carried), "camera": rows[frames.index(f)]["how"]}
        if H is not None and np.all(np.isfinite(H)) and annotated:
            y_top, y_bot = af.L.gt_y(stem, f)
            try:
                cn = LM.corners_from_h(H, y_top, y_bot); sb = af.score_both(stem, f, cn)
                row.update({"ok": True, "mae": {t: sb[t]["board_mae"] for t in af.TRUTHS}, "tail": {t: sb[t]["board_mae_last20"] for t in af.TRUTHS}, "width_err_px_pins": sb["pins"]["top_width_err_px"]})
            except Exception:  # noqa: BLE001
                row["ok"] = False
        else:
            row["ok"] = H is not None
        if annotated and fle:
            A_orb = af.L.transform(stem, f0, f); A_lm = cam[f]
            # carry the hand corners of the first hand-annotated frame through both models; error vs that frame's hand corners
            # (the landmark model's reference is f_ref, so chain ref -> f0 first)
            e_lm = []; e_orb = []
            A_ref_to_f0 = cam.get(f0)
            for k in af.KEYS:
                q = fle[str(f)][k]
                p_orb = warp(A_orb, static[k]); e_orb.append(float(np.hypot(p_orb[0] - q[0], p_orb[1] - q[1])))
                if A_ref_to_f0 is not None:
                    p_ref = warp(inv(A_ref_to_f0), static[k]); p_lm = warp(A_lm, p_ref); e_lm.append(float(np.hypot(p_lm[0] - q[0], p_lm[1] - q[1])))
            row["cam_err_px"] = {"landmarks": round(float(np.mean(e_lm)), 2) if e_lm else None, "orb": round(float(np.mean(e_orb)), 2), "landmarks_top": round(float(np.mean(e_lm[:2])), 2) if e_lm else None, "orb_top": round(float(np.mean(e_orb[:2])), 2)}
        per.append(row)
    summ = {"frames": len(frames), "ref_frame": f_ref, "ref_landmarks": len(ref), "camera_fits": sum(1 for r in rows if r["how"] == "landmarks"), "common_median": float(np.median([r["n_common"] for r in rows])),
            "common_median_after_hit": float(np.median([r["n_common"] for r in rows if r["frame"] >= ph])) if any(r["frame"] >= ph for r in rows) else None,
            "pooled_pins": len(pooled), "pooled_frames_median": n_pool}
    if annotated:
        throw = set(af.throw_frames(stem)); ok = [r for r in per if r.get("ok") and "mae" in r]
        rt = [r for r in ok if r["frame"] in throw]; post = [r for r in ok if r["frame"] >= ph and r["frame"] in throw]
        for t in af.TRUTHS:
            summ[f"throw_median_{t}"] = round(float(np.median([r["mae"][t] for r in rt])), 2) if rt else None
            summ[f"tail_median_{t}"] = round(float(np.median([r["tail"][t] for r in rt])), 2) if rt else None
            summ[f"post_hit_median_{t}"] = round(float(np.median([r["mae"][t] for r in post])), 2) if post else None
            summ[f"last_{t}"] = next((r["mae"][t] for r in ok if r["frame"] == af.L.frame_indices(stem, "last")[0]), None)
        summ["ok_in_throw"] = len(rt); summ["post_hit_frames"] = len(post)
        summ["throw_frames_all"] = len(throw)
        ce = [r["cam_err_px"] for r in per if r.get("cam_err_px") and r["cam_err_px"]["landmarks"] is not None]
        if ce:
            summ["cam_err_px"] = {k: round(float(np.mean([c[k] for c in ce])), 2) for k in ("landmarks", "orb", "landmarks_top", "orb_top")}
            summ["cam_err_px_max"] = {k: round(float(np.max([c[k] for c in ce])), 2) for k in ("landmarks", "orb")}
    af.dump(af.RESULTS / f"e5_persist_{stem}.json", {"stem": stem, "summary": summ, "camera": rows, "per_frame": per})
    print(f"E5 {af.SHORT[stem]:13s} " + json.dumps(summ), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("stems", nargs="*")
    a = ap.parse_args()
    for stem in (a.stems or af.STEMS):
        run(stem)
