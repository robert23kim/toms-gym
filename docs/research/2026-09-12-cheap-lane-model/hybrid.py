"""Hybrid: the student's lane supplies SAM 2's prompts, no ball track needed.

For a frame, take the student's saved lines (seg run, ransac variant when
present), build 3 positive points on the lane centre line at 20/50/80 % of
its height, run sam2.1_t once, fit the loop-1 edge lines on the SAM mask and
score. Compares to the student alone and to the ball-path-prompted SAM rows
of loops 1-2. usage: hybrid.py <run> <stem> [kinds: prehit,last,prehit-6,clean_all]
"""
import json
import sys
import time

import cv2
import numpy as np

import common as C

L = C.L
C.use_full_camera()
PRED = C.SCRATCH / "pred"


def student_lines(run, stem, f):
    for name in (f"{run}_gated", f"{run}_window", f"{run}_ransac", run):
        p = PRED / f"lines_{name}_{stem}.json"
        if p.exists():
            d = json.loads(p.read_text())
            if str(f) in d:
                return d[str(f)]
    return None


def centre_prompts(ln, y_top, y_bot, n=3, lo=0.2, hi=0.8):
    (la, lb), (ra, rb) = tuple(ln["left"]), tuple(ln["right"])
    out = []
    for t in np.linspace(lo, hi, n):
        y = y_top + t * (y_bot - y_top)
        x = ((la * y + lb) + (ra * y + rb)) / 2
        out.append([int(x), int(y)])
    return out


def run(run_name, stem, kinds, weights="sam2.1_t.pt"):
    m = L.model(weights)
    rows = []
    for kind in kinds:
        if kind == "clean_all":
            frames = C.clean_frames(stem)[::4]
        elif kind == "prehit":
            frames = [L.pin_hit_frame(stem) - 2]
        elif kind.startswith("prehit-"):
            frames = [L.pin_hit_frame(stem) - int(kind.split("-")[1])]
        else:
            frames = [L.frame_indices(stem, "last")[0]]
        for f in frames:
            ln = student_lines(run_name, stem, f)
            if ln is None:
                rows.append({"stem": stem, "frame": f, "kind": kind, "ok": False, "why": "no student lane"}); continue
            y_top, y_bot = L.gt_y(stem, f)
            prompts = centre_prompts(ln, y_top, y_bot)
            img = C.read_frame(stem, f)
            t0 = time.time()
            mk = L.predict_mask(m, img, points=prompts)
            dt = time.time() - t0
            row = {"stem": stem, "frame": f, "kind": kind, "prompts": prompts, "latency_s": round(dt, 2), "ok": False}
            if mk is not None:
                fit = L.fit_edges(mk, y_top, y_bot, prompts)
                if fit is not None:
                    left, right, info = fit
                    corners = L.lines_to_corners(left, right, y_top, y_bot)
                    row.update(L.score(stem, corners, f)); row["ok"] = True; row["fit_resid_px"] = info["fit_resid_px"]
                    stud = L.lines_to_corners(tuple(ln["left"]), tuple(ln["right"]), y_top, y_bot)
                    row["student_board_mae"] = L.score(stem, stud, f)["board_mae"]
                    if kind in ("prehit", "last"):
                        out = L.draw_overlay(stem, f, mk, corners, {"points": prompts, "labels": [1] * 3}, f"hybrid {run_name} -> {weights} {C.SHORT[stem]} f{f} ({kind}) MAE {row['board_mae']} (student alone {row['student_board_mae']})")
                        cv2.imwrite(str(C.OVERLAYS / f"hybrid_{run_name}_{kind}_{stem}.jpg"), out, [cv2.IMWRITE_JPEG_QUALITY, 85])
            rows.append(row)
            print({k: row.get(k) for k in ("frame", "kind", "board_mae", "student_board_mae", "latency_s", "ok")})
    C.dump(C.RESULTS / f"hybrid_{run_name}__{stem}.json", rows)
    ok = [r for r in rows if r.get("ok")]
    if ok:
        print(f"hybrid {run_name} {C.SHORT[stem]}: mean MAE {np.mean([r['board_mae'] for r in ok]):.2f} vs student {np.mean([r['student_board_mae'] for r in ok]):.2f} over {len(ok)} frames")


if __name__ == "__main__":
    kinds = sys.argv[3].split(",") if len(sys.argv) > 3 else ["prehit", "last", "prehit-6", "clean_all"]
    run(sys.argv[1], sys.argv[2], kinds)
