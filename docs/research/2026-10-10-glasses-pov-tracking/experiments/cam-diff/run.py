"""cam-diff tracker for one glasses-POV cut.

usage: run.py <stem> [--no-sam] [--far-upscale] [--thr N]
reads  L/work/cuts/cuts.json + the cut, writes tracks/<stem>.json (SOURCE frame numbers) and
overlays/<stem>.jpg (pin_hit-4 frame, track polyline, lane quad, final board)."""
import argparse
import json
import os
import sys
import time

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ENGINE = "/Users/toka/code/bowling-app/pov-engine"
sys.path.insert(0, ENGINE)
from camdiff import L, Motion, load_cut            # noqa: E402
from tracker import track                            # noqa: E402


def pin_hit_guess(hsv, pts, back=12):
    """Guess for the SAM candidate frames only: the track runs 0-16 frames past pin contact on dev
    (the ball stays visible among the pins), so `end - 12` keeps the candidates on standing pins.
    A white-strip-above-the-ball rule was tried and fired ~25 frames early on the lane's pin
    reflections; the residual burst of flying pins came 8-15 frames late. Both dropped."""
    return max(pts[0]["f"], pts[-1]["f"] - back), "end-12"


def sam_lane(cut_path, pts, n_frames, pin_hit_guess, verbose, inliers=None, min_inliers=400):
    """Engine SAM lane pass prompted by this track (cut-local frames). Returns (per_frame quads, boards,
    final_board, pin_hit, calib_pin_row_source) or Nones."""
    from scripts.sam_lane_pass import board_summary, calibrated_boards, run_sam_lane_pass
    from src.bowling.lane_tracking import lane_calibration as LC
    LC.CANDIDATE_BACKS = (4, 8, 12, 16)   # the head keeps moving: spread the standing-pin candidates; 5 in all for the wall time
    LC.CANDIDATE_AHEADS = (3,)            # past the guess the pins may be falling
    LC.MAX_RESID_PX = 15.0     # wide-angle glasses lens: straight-line edge fits leave 9-14 px (190115 refused at 8)
    LC.GOOD_RESID_PX = 5.0     # engine default: stopping at the first <= 7 px fit picked a neighbour lane on 185645 (lane_err 66)
    positions = [(int(p["f"]), float(p["x"]), float(p["y"]), float(p["r"])) for p in pts]
    # the segment that prompts SAM: on-lane frames only (the track runs on among the pins, whose
    # points would fail the engine's path-covered check), and not the release frames where the
    # camera swing defeats the aligner
    seg = [q for q in positions if q[0] <= pin_hit_guess + 2]
    start = seg[0][0]
    if inliers is not None:
        for t in range(seg[0][0], seg[-1][0] - 10):
            if all(inliers[u] >= min_inliers for u in range(t, min(t + 3, len(inliers)))):
                start = t + 2
                break
    seg = [q for q in seg if q[0] >= start]
    if len(seg) < 12:
        seg = [q for q in positions if q[0] <= pin_hit_guess + 2][4:]
    if verbose:
        print(f"[cam-diff] SAM segment: cut frames {seg[0][0]}-{seg[-1][0]} ({len(seg)} points; ORB inliers >= {min_inliers} from {start})")
    calib, fields = run_sam_lane_pass(cut_path, positions, pin_hit=pin_hit_guess, weights_dir=f"{ENGINE}/models",
                                      verbose=verbose, segment=seg)
    if calib is None:
        return None, None, None, None, fields
    # pin hit = first frame of the WHOLE track whose centre (in the calibration frame) is above the pin row
    calib.segment_frames = None
    ref_path = calib.path_in_ref(positions)
    above = [q for q in ref_path if q[2] < calib.pin_row + 0.5 * max(q[3], 6.0)]
    pin_hit = int(above[0][0]) if above else int(positions[-1][0])
    on_lane = [q for q in positions if q[0] <= pin_hit]
    boards = calibrated_boards(calib, on_lane)
    summ = board_summary(calib, on_lane, boards)
    d = calib.to_dict(range(n_frames))
    return d["per_frame"], boards, summ, pin_hit, {**fields, "lane_method": calib.method, "quality": calib.quality,
                                                   "pin_row": calib.pin_row, "ref_frame": calib.ref_frame}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stem")
    ap.add_argument("--no-sam", action="store_true")
    ap.add_argument("--no-far-upscale", action="store_true", help="difference the top third at 1x (default: 2x)")
    ap.add_argument("--thr", type=int, default=22)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    cut, frames = load_cut(a.stem)
    cs = cut["cut_start"]
    n = len(frames)
    H_img = frames[0].shape[0]
    motion = Motion(frames)
    hsv = [cv2.cvtColor(f, cv2.COLOR_BGR2HSV) for f in frames]
    pts, info = track(motion, frames, hsv, far_upscale=(None if a.no_far_upscale else (H_img // 3, 2)), thr=a.thr)
    t_track = time.time() - t0
    if not a.quiet:
        print(f"[cam-diff] {a.stem}: {len(pts)} points, cut frames {pts[0]['f'] if pts else None}-{pts[-1]['f'] if pts else None}, "
              f"{info}, {t_track:.1f}s")
    lane, boards, summ, pin_hit_local, sam_fields = None, None, None, None, {}
    guess, guess_src = (pin_hit_guess(hsv, pts) if pts else (None, None))
    if not a.quiet:
        print(f"[cam-diff] pin hit guess: cut frame {guess} (source {None if guess is None else cs + guess}) by {guess_src}")
    if pts and not a.no_sam:
        try:
            lane, boards, summ, pin_hit_local, sam_fields = sam_lane(cut["cut_path"], pts, n, guess, not a.quiet, inliers=motion.inliers)
        except Exception as e:  # noqa: BLE001
            print(f"[cam-diff] SAM lane pass failed: {type(e).__name__}: {e}")
            sam_fields = {"error": str(e)[:200]}
    t_total = time.time() - t0
    release = cs + pts[0]["f"] if pts else None
    if pin_hit_local is not None:
        pin_hit, pin_src = cs + int(pin_hit_local), "sam_pin_row"
    elif guess is not None:
        pin_hit, pin_src = cs + int(guess), guess_src
    else:
        pin_hit, pin_src = None, None
    board_by_f = {}
    if boards:
        board_by_f = {str(cs + b["frame"]): b["board"] for b in boards if b["on_lane"] and np.isfinite(b["board"])}
    out = {
        "stem": a.stem, "method": "cam-diff" + ("+sam" if lane else ""),
        "frames": [{"f": cs + p["f"], "x": round(p["x"], 1), "y": round(p["y"], 1), "r": round(p["r"], 1),
                    "conf": round(float(p.get("purple", 0.0)) * (0.5 if p.get("src") == "interp" else 1.0), 2),
                    "src": p.get("src") or "residual"} for p in pts],
        "lane": {} if not lane else {str(cs + int(f)): {"fl_l": q["bottom_left"], "fl_r": q["bottom_right"],
                                                        "pd_l": q["top_left"], "pd_r": q["top_right"],
                                                        "fl_is_foul_line": False} for f, q in lane.items()},
        "boards": board_by_f,
        "final_board": None if not summ else summ.get("final_board"),
        "release_frame": release, "pin_hit_frame": pin_hit,
        "meta": {"pin_hit_source": pin_src, "pin_hit_guess": None if guess is None else cs + guess, "cut_start": cs, "cut_end": cut["cut_end"], "track_info": info, "sam": sam_fields,
                 "final_board_raw": None if not summ else summ.get("final_board_raw"),
                 "fl_note": "fl_* is the lowest calibrated lane row (SAM mask bottom), not the foul line",
                 "wall_s": round(t_total, 1), "track_s": round(t_track, 1), "thr": a.thr, "far_upscale": not a.no_far_upscale},
    }
    os.makedirs(f"{HERE}/tracks", exist_ok=True)
    os.makedirs(f"{HERE}/overlays", exist_ok=True)
    json.dump(out, open(f"{HERE}/tracks/{a.stem}.json", "w"), indent=1)
    # overlay: pin_hit-4 frame
    if pts:
        fo = max(0, min(n - 1, (pin_hit if pin_hit is not None else cs + pts[-1]["f"]) - 4 - cs))
        im = frames[fo].copy()
        poly = np.array([[int(p["x"]), int(p["y"])] for p in pts], np.int32)
        cv2.polylines(im, [poly], False, (0, 165, 255), 3)
        for p in pts:
            col = (0, 165, 255) if p.get("src") in (None, "residual") else (0, 255, 255) if p.get("src") == "guided" else (0, 90, 255)
            cv2.circle(im, (int(p["x"]), int(p["y"])), max(2, int(p["r"])), col, 2)
        # the same track carried into the displayed frame through the chained homographies (the path on the lane)
        comp = []
        for p in pts:
            x, y, t = p["x"], p["y"], p["f"]
            ok = True
            if t < fo:
                for u in range(t + 1, fo + 1):
                    if motion.H[u] is None:
                        ok = False
                        break
                    x, y = motion.point_fwd(u, x, y)
            elif t > fo:
                for u in range(t, fo, -1):
                    if motion.H[u] is None:
                        ok = False
                        break
                    x, y = motion.point_bwd(u, x, y)
            if ok and abs(x) < 4 * im.shape[1] and abs(y) < 4 * im.shape[0]:
                comp.append([int(x), int(y)])
        if len(comp) > 1:
            cv2.polylines(im, [np.array(comp, np.int32)], False, (255, 255, 255), 2)
        if lane and str(fo) in lane:
            q = lane[str(fo)]
            qq = np.array([q["bottom_left"], q["top_left"], q["top_right"], q["bottom_right"]], np.int32)
            cv2.polylines(im, [qq], True, (255, 255, 0), 3)
        txt = [f"cam-diff {a.stem} src f{fo + cs} (pin_hit-4)", f"final_board {out['final_board']} release {release} pin_hit {pin_hit}",
               f"orange=track in each frame's own coords, white=track warped into this frame, cyan=lane  {t_total:.0f}s"]
        for i, s in enumerate(txt):
            cv2.putText(im, s, (10, 40 + 36 * i), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 4)
            cv2.putText(im, s, (10, 40 + 36 * i), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        cv2.imwrite(f"{HERE}/overlays/{a.stem}.jpg", im, [cv2.IMWRITE_JPEG_QUALITY, 85])
    print(f"[cam-diff] done {a.stem}: final_board {out['final_board']} release {release} pin_hit {pin_hit} wall {t_total:.1f}s")


if __name__ == "__main__":
    main()
