"""Student vs SAM 2 teacher on an unlabeled video (no hand truth).

On every frame the teacher scored, take the teacher's corners as truth, the
student's saved edge lines evaluated at the teacher's y band as the
prediction, and the detected ball path as the evaluation points: board MAE
through the two homographies, exactly the loop-1 metric with the teacher in
the annotator's seat. Frames where the teacher itself is unreliable (fit
residual > 4 px, or inside the throw where the bowler occludes the lane) are
reported separately. usage: eval_unlabeled.py <run> <stem> [--tag T]
"""
import argparse
import json

import numpy as np

import common as C

L = C.L
PRED = C.SCRATCH / "pred"


def main(run, stem, tag=""):
    teacher = json.loads((C.RESULTS / f"teacher__{stem}.json").read_text())
    tl = json.loads((PRED / f"lines_teacher_{stem}.json").read_text())
    sl = json.loads((PRED / f"lines_{run}{tag}_{stem}.json").read_text())
    pts = teacher["ball_path"]
    lo, hi = teacher["ball_run"]
    rows = []
    for r in teacher["per_frame"]:
        f = r["frame"]
        if not r.get("ok") or str(f) not in tl:
            continue
        t = tl[str(f)]
        y_top, y_bot = t["y"]
        truth = L.lines_to_corners(tuple(t["left"]), tuple(t["right"]), y_top, y_bot)
        s = sl.get(str(f))
        row = {"frame": f, "teacher_resid_px": r["fit_resid_px"], "in_throw": lo <= f <= hi + 10,
               "teacher_reliable": r["fit_resid_px"] <= 4.0 and not (lo <= f <= hi + 10), "ok": s is not None}
        if s is not None:
            pred = L.lines_to_corners(tuple(s["left"]), tuple(s["right"]), y_top, y_bot)
            bt, _ = C.gt.board_from_corners(truth, pts); bp, _ = C.gt.board_from_corners(pred, pts)
            d = np.abs(bp - bt)
            row.update({"board_mae": round(float(d.mean()), 2), "board_max": round(float(d.max()), 2), "within_2": round(float((d <= 2).mean() * 100), 1),
                        "corner_err_px": {k: round(float(np.hypot(pred[k][0] - truth[k][0], pred[k][1] - truth[k][1])), 1) for k in C.KEYS},
                        "top_width_teacher_px": round(truth["top_right"][0] - truth["top_left"][0], 1),
                        "top_width_student_px": round(pred["top_right"][0] - pred["top_left"][0], 1)})
            row["corner_err_mean_px"] = round(float(np.mean(list(row["corner_err_px"].values()))), 1)
        rows.append(row)
    rel = [r for r in rows if r["teacher_reliable"]]
    thr = [r for r in rows if r["in_throw"]]
    out = {"stem": stem, "method": run + tag, "teacher": "sam2.1_t even3 from ball detector", "frames": len(rows),
           "vs_teacher_reliable": C.summarize(rel), "vs_teacher_in_throw": C.summarize(thr), "vs_teacher_all": C.summarize(rows),
           "corner_px_reliable": round(float(np.mean([r["corner_err_mean_px"] for r in rel if r.get("ok")])), 1) if rel else None,
           "per_frame": rows}
    C.dump(C.RESULTS / f"{run}{tag}__{stem}__vs_teacher.json", out)
    print(f"{run}{tag} vs teacher on {stem}: reliable frames {out['vs_teacher_reliable']}  in-throw {out['vs_teacher_in_throw']}  corner px {out['corner_px_reliable']}")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("run"); ap.add_argument("stem"); ap.add_argument("--tag", default="")
    a = ap.parse_args(); main(a.run, a.stem, a.tag)
