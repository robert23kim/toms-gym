"""usage: run.py <stem>  -> tracks/<stem>.json (SOURCE frame numbers) + overlays/<stem>.jpg"""
import json
import os
import statistics
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import EXP, cut_entry, read_cut  # noqa: E402
import tracker as TR  # noqa: E402


def main(stem):
    t0 = time.time()
    e = cut_entry(stem)
    out_path = os.path.join(EXP, "tracks", stem + ".json")
    if e.get("cut_path") is None:
        json.dump({"stem": stem, "method": "lane-first", "frames": [], "lane": {}, "boards": {}, "final_board": None,
                   "release_frame": None, "pin_hit_frame": None, "note": "no cut in cuts.json: no throw"}, open(out_path, "w"))
        print(stem, "no cut -> empty tracks")
        return
    frames = read_cut(e)
    log = []
    res = TR.track_cut(frames, log)
    recs = res["recs"]
    lanes = res["lanes"]
    dets = [r for r in recs if r["src"] == "det"]
    on_lane = [r for r in dets if "board_kf" in r]
    good = [r for r in on_lane[-8:] if r.get("ratio") is not None and r["ratio"] <= 0.41] or on_lane[-5:]
    final_board = round(statistics.median([r["board_kf"] for r in good[-5:]]), 1) if len(on_lane) >= 2 else None
    release = dets[0]["f"] if dets else None
    pin_hit = res["ended"] if res["ended"] is not None else (dets[-1]["f"] if dets else None)
    tracks = {
        "stem": stem, "method": "lane-first",
        "frames": [{"f": r["f"], "x": round(r["x"], 1), "y": round(r["y"], 1), "r": round(r["r"], 1), "conf": r["conf"],
                    "src": r["src"], "on_lane": bool("u" in r and -0.03 <= r["u"] <= 1.03 and res["lane_ok"].get(r["f"], False)),
                    "u": None if "u" not in r else round(r["u"], 4), "z_ft": None if "z" not in r else round(r["z"], 2), "board": None if "board" not in r else round(r["board"], 2)}
                   for r in recs],
        "lane": {str(f): lf.quad() for f, lf in lanes.items() if res["lane_ok"].get(f)},
        "boards": {str(r["f"]): round(r["board"], 2) for r in recs if "board" in r},
        "final_board": final_board, "release_frame": release, "pin_hit_frame": pin_hit,
        "meta": {"cut_start": e["cut_start"], "cut_end": e["cut_end"], "wall_s": round(time.time() - t0, 1),
                 "n_det": len(dets), "n_fill": len(recs) - len(dets), "ended_at": res["ended"],
                 "note": "release/pin_hit here are the tracker's own estimates (first detection / pin-row crossing); the cut window itself is cuts.json's [release-10, pin_hit+20]"},
    }
    json.dump(tracks, open(out_path, "w"), indent=1)
    json.dump(log, open(os.path.join(EXP, "work", stem + "_log.json"), "w"))
    # overlay on pin_hit-4 (cuts.json) frame
    fo = e["pin_hit_frame"] - 4
    img = dict(frames)[fo].copy()
    pts = np.array([[int(r["x"]), int(r["y"])] for r in recs], np.int32)
    if len(pts) > 1:
        cv2.polylines(img, [pts], False, (0, 0, 255), 3)
    for r in recs:
        col = (0, 0, 255) if r["src"] == "det" else (255, 128, 0)
        cv2.circle(img, (int(r["x"]), int(r["y"])), max(2, int(r["r"])), col, 2)
    lf = lanes.get(fo)
    if lf is not None and res["lane_ok"].get(fo):
        q = lf.quad()
        poly = np.array([q["fl_l"], q["pd_l"], q["pd_r"], q["fl_r"]], np.int32)
        cv2.polylines(img, [poly], True, (0, 255, 0), 3)
    txt = [f"{stem} f{fo} (pin_hit-4) lane-first", f"final board {final_board} (right gutter = 1)",
           f"det {len(dets)} fill {len(recs) - len(dets)} release~{release} pin~{pin_hit} wall {tracks['meta']['wall_s']}s",
           "red = detections, orange = Kalman fill, green = lane quad at this frame"]
    for i, t in enumerate(txt):
        cv2.putText(img, t, (20, 50 + 45 * i), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 6)
        cv2.putText(img, t, (20, 50 + 45 * i), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
    cv2.imwrite(os.path.join(EXP, "overlays", stem + ".jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 80])
    print(stem, "det", len(dets), "fill", len(recs) - len(dets), "board", final_board, "release", release, "pin", pin_hit,
          "wall", tracks["meta"]["wall_s"])


if __name__ == "__main__":
    main(sys.argv[1])
