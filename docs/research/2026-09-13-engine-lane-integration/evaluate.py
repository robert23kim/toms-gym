"""Score an engine run's lane, per frame, with the loop-1 metric against both truths.

A run directory (see run_engine.py) holds <stem>.log (the old engine prints its
static lane as `lane_edges={...}`), <stem>_summary.json and, for --sam-lane runs,
<stem>_lane_calibration.json with per-frame corners. Old engine = the static lane
on every frame (its per-Y polyline interpolation when it has edge points);
new engine = the calibrated lane carried per frame. Also reports the product
number: the engine's final board vs the truth's board at the pin-hit frame.
usage: evaluate.py <config> [stems...]   (config = name of a directory under $EI_SCRATCH/runs)
"""
import json
import re
import sys

import numpy as np

import common as C

L = C.L


def static_lane_from_log(path):
    txt = open(path).read()
    m = re.search(r"lane_edges=(\{.*\})", txt)
    if not m:
        return None
    d = json.loads(m.group(1))
    return d


def old_corners(stem, f, lane):
    if lane.get("left_edge_points") and lane.get("right_edge_points"):
        return C.polyline_corners_at_truth_rows(stem, f, lane["left_edge_points"], lane["right_edge_points"])
    return C.corners_at_truth_rows(stem, f, {k: tuple(lane[k]) for k in C.KEYS})


def truth_final_board(stem):
    """Board of the annotated ball at the pin-hit frame (median of the last 5 on-lane frames), pins truth."""
    fs, pos = L.trajectory(stem)
    out = {}
    for kind in C.TRUTHS:
        vals = []
        for f in fs[-5:]:
            t = C.truth_corners(stem, f, kind)
            b, _ = C.gt.board_from_corners(t, [(pos[f][0], pos[f][1])])
            vals.append(float(b[0]))
        out[kind] = round(float(np.median(vals)), 2)
    return out


def evaluate(config, stem):
    run = C.RUNS / config
    log = run / f"{stem}.log"
    summ_p = run / f"{stem}_summary.json"
    calib_p = run / f"{stem}_lane_calibration.json"
    summary = C.load(summ_p) if summ_p.exists() else {}
    calib = C.load(calib_p) if calib_p.exists() else None
    static = static_lane_from_log(log) if log.exists() else None
    frames = C.throw_frames(stem)
    per = []
    for f in frames:
        row = {"frame": f, "ok": False}
        corners = None
        if calib and str(f) in calib.get("per_frame", {}):
            c = {k: tuple(v) for k, v in calib["per_frame"][str(f)].items()}
            corners = C.corners_at_truth_rows(stem, f, c)
            row["source"] = "calibrated"
        elif calib:
            row["source"] = "uncalibrated"   # outside the aligned range: never fall back to the static lane
        elif static is not None:
            corners = old_corners(stem, f, static)
            row["source"] = "static"
        if corners is not None and corners["top_right"][0] > corners["top_left"][0]:
            row["ok"] = True
            row["corners"] = {k: [round(float(v[0]), 1), round(float(v[1]), 1)] for k, v in corners.items()}
            for kind in C.TRUTHS:
                s = C.score_corners(stem, f, corners, kind)
                row[f"mae_{kind}"] = s["board_mae"]
                row[f"tail_{kind}"] = s["tail_mae"]
                row[f"within2_{kind}"] = s["within_2"]
                row[f"width_err_{kind}"] = s["top_width_err_px"]
                row[f"centre_err_{kind}"] = s["top_centre_err_px"]
        per.append(row)
    ph = L.pin_hit_frame(stem)
    fl = L.trajectory(stem)[0][-1]  # last on-lane ball frame (pin-hit marker)
    out = {"config": config, "stem": stem, "method": (calib or {}).get("method", "static classical lane"),
           "frames": len(per), "ok": sum(1 for r in per if r["ok"]), "per_frame": per,
           "summary": summary, "truth_final_board": truth_final_board(stem),
           "calibration": None if calib is None else {k: calib.get(k) for k in ("method", "ref_frame", "pin_hit", "timings", "quality", "crop", "camera")}}
    clean = set(C.clean_frames(stem))
    for kind in C.TRUTHS:
        rows = [dict(r, board_mae=r.get(f"mae_{kind}")) for r in per]
        out[f"throw_{kind}"] = C.summarize(rows)
        out[f"clean_{kind}"] = C.summarize([r for r in rows if r["frame"] in clean])
        out[f"prehit_{kind}"] = next((r.get(f"mae_{kind}") for r in per if r["frame"] == ph - 2), None)
        out[f"last_{kind}"] = next((r.get(f"mae_{kind}") for r in per if r["frame"] == fl), None)
        out[f"tail_{kind}"] = C.summarize([dict(r, board_mae=r.get(f"tail_{kind}")) for r in per])["median"]
    fb = summary.get("final_board")
    out["final_board"] = fb
    out["final_board_err"] = {k: (None if fb is None else round(abs(float(fb) - v), 2)) for k, v in out["truth_final_board"].items()}
    C.dump(C.RESULTS / f"eval_{config}__{stem}.json", out)
    print(f"{config:18s} {C.SHORT[stem]:13s} {out['method']:22s} ok {out['ok']}/{out['frames']} | throw MAE ann mean/med {out['throw_annotated']['mean']}/{out['throw_annotated']['median']} pins {out['throw_pins']['mean']}/{out['throw_pins']['median']} <=2: {out['throw_pins']['within_2']}% | prehit pins {out['prehit_pins']} last {out['last_pins']} | final board {fb} vs truth {out['truth_final_board']['pins']} (err {out['final_board_err']['pins']})", flush=True)
    return out


if __name__ == "__main__":
    config = sys.argv[1]
    for stem in (sys.argv[2:] or C.STEMS):
        evaluate(config, stem)
