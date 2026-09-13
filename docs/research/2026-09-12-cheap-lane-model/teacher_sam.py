"""SAM 2 (tiny) teacher lanes on an unlabeled video, prompted from the ball
detector's path (loop-1/2 recipe: 3 points spaced evenly by image length
between 15 % and 85 % of the on-lane path, kept off the ball, no box, no
negatives). Saves masks + lines to $LANE_SCRATCH/pred/{masks,lines}_teacher_<stem>
and results/teacher__<stem>.json (per-frame fit residual, prompts, camera
drift vs the first frame). usage: teacher_sam.py <stem> [frames|step]
"""
import json
import sys
import time

import cv2
import numpy as np

import common as C
from camera_motion_shim import affine_between

L = C.L
PRED = C.SCRATCH / "pred"


def ball_path(stem, min_run=20):
    d = json.loads((PRED / f"ball_{stem}.json").read_text())
    fs = sorted(int(k) for k, v in d.items() if v)
    runs, cur = [], []
    for f in fs:
        if cur and f - cur[-1] > 3:
            runs.append(cur); cur = []
        cur.append(f)
    if cur:
        runs.append(cur)
    run = max(runs, key=len)
    if len(run) < min_run:
        raise SystemExit(f"no ball run >= {min_run} frames on {stem}: {[len(r) for r in runs]}")
    pts = [(d[str(f)][0]["x"], d[str(f)][0]["y"], d[str(f)][0]["r"]) for f in run]
    return run, pts


def even_points(pts, n=3, lo=0.15, hi=0.85):
    p = np.array([(x, y) for x, y, _ in pts], float)
    cum = np.concatenate([[0], np.cumsum(np.hypot(*(np.diff(p, axis=0).T)))])
    out = []
    for t in np.linspace(lo, hi, n):
        i = min(int(np.searchsorted(cum, t * cum[-1])), len(p) - 1)
        out.append([int(p[i][0]), int(p[i][1])])
    return out


def run(stem, frames, weights="sam2.1_t.pt"):
    run_fs, pts = ball_path(stem)
    prompts = even_points(pts)
    m = L.model(weights)
    orb = cv2.ORB_create(4000); bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    ref = cv2.imread(str(C.FRAMES / stem / f"{frames[0]:05d}.jpg"), 0)
    masks, lines, rows = {}, {}, []
    for f in frames:
        img = C.read_frame(stem, f)
        t0 = time.time()
        mk = L.predict_mask(m, img, points=prompts)
        dt = time.time() - t0
        A, n = affine_between(ref, cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), orb, bf)
        drift = float(np.hypot(A[0, 2], A[1, 2])) if A is not None else None
        row = {"frame": f, "ok": False, "latency_s": round(dt, 2), "drift_px": None if drift is None else round(drift, 1), "inliers": n}
        if mk is not None:
            comp = L.largest_component(mk, prompts)
            if comp is not None:
                ys = np.where(comp.any(1))[0]
                y_top, y_bot = int(np.percentile(ys, 2)), int(np.percentile(ys, 98))
                fit = L.fit_edges(comp, y_top, y_bot, prompts)
                if fit is not None:
                    left, right, info = fit
                    corners = L.lines_to_corners(left, right, y_top, y_bot)
                    lines[str(f)] = {"left": list(map(float, left)), "right": list(map(float, right)), "y": [y_top, y_bot],
                                     "corners": {k: [round(float(v[0]), 1), round(float(v[1]), 1)] for k, v in corners.items()}}
                    masks[str(f)] = np.packbits(comp.astype(bool))
                    row.update({"ok": True, "fit_resid_px": info["fit_resid_px"], "row_coverage": info["row_coverage"],
                                "top_width_px": round(corners["top_right"][0] - corners["top_left"][0], 1),
                                "bottom_width_px": round(corners["bottom_right"][0] - corners["bottom_left"][0], 1)})
        rows.append(row)
        print(row)
    PRED.mkdir(exist_ok=True)
    np.savez_compressed(PRED / f"masks_teacher_{stem}.npz", shape=np.array(img.shape[:2]), **masks)
    (PRED / f"lines_teacher_{stem}.json").write_text(json.dumps(lines))
    C.dump(C.RESULTS / f"teacher__{stem}.json", {"stem": stem, "weights": weights, "prompts": prompts, "ball_run": [run_fs[0], run_fs[-1]],
                                                  "ball_path": [[round(x, 1), round(y, 1)] for x, y, _ in pts], "per_frame": rows})
    # overlays on first / middle / last requested frame
    for f in (frames[0], frames[len(frames) // 2], frames[-1]):
        if str(f) not in lines:
            continue
        img = C.read_frame(stem, f)
        mk = np.unpackbits(masks[str(f)])[: img.shape[0] * img.shape[1]].reshape(img.shape[:2]).astype(bool)
        img[mk] = (0.5 * img[mk] + np.array([150, 60, 0])).clip(0, 255).astype(np.uint8)
        c = lines[str(f)]["corners"]
        p = np.array([c["top_left"], c["top_right"], c["bottom_right"], c["bottom_left"]], np.int32)
        cv2.polylines(img, [p], True, (0, 0, 255), 2, cv2.LINE_AA)
        for x, y in prompts:
            cv2.circle(img, (x, y), 9, (0, 255, 255), -1)
        for x, y in [(int(x), int(y)) for x, y, _ in pts]:
            cv2.circle(img, (x, y), 3, (255, 255, 0), -1)
        cv2.putText(img, f"teacher {weights} {stem} f{f}", (12, img.shape[0] - 16), 0, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.imwrite(str(C.OVERLAYS / f"teacher_{stem}_{f}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 85])


if __name__ == "__main__":
    stem = sys.argv[1]
    if len(sys.argv) > 2 and "-" in sys.argv[2]:
        a, b, s = sys.argv[2].split("-")[0], sys.argv[2].split("-")[1].split(":")[0], (sys.argv[2].split(":")[1] if ":" in sys.argv[2] else "1")
        frames = list(range(int(a), int(b) + 1, int(s)))
    else:
        frames = C.frame_ids(stem)[:: int(sys.argv[2]) if len(sys.argv) > 2 else 10]
    run(stem, frames)
