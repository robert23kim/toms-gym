"""Glasses-POV ball tracker: multi-scale YOLO box pool -> engine yolo_chain -> engine SAM lane -> board.

usage: run.py <stem> [--cache] [--configs ...]
reads  L/work/cuts/cuts.json and the cut
writes tracks/<stem>.json (tracks format, SOURCE frame numbers), overlays/<stem>.jpg (pin_hit-4 frame, track
       polyline, lane quad, final board), work/run_<stem>.json (report + timings)
--cache: take the boxes from work/dets_<stem>.json (dump_dets.py) instead of running the detector (tuning only;
         the wall time is then not a run time).
"""
import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
L = HERE.parents[1]
ENGINE = Path("/Users/toka/code/bowling-app/pov-engine")
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ENGINE))
from tracker import PoolConfig, run_chain  # noqa: E402
from src.bowling.trajectory.yolo_chain import ChainConfig  # noqa: E402
from dump_dets import CONFIGS, detect, load_model  # noqa: E402

DEFAULT_CONFIGS = ["bowl_full320", "bowl_full640", "bowl_full1280", "bowl_far1x"]
CHAIN = ChainConfig(r_grow=1.5)   # the pool mixes inference scales whose boxes differ by up to 2x in r (NOTES.md); 1.5 tuned on dev


def read_cut(path):
    cap = cv2.VideoCapture(path)
    frames = []
    while True:
        ok, im = cap.read()
        if not ok:
            break
        frames.append(im)
    cap.release()
    return frames


def detect_all(frames, cut_start, names, conf=0.05):
    W, H = frames[0].shape[1], frames[0].shape[0]
    doc = {"size": [W, H], "cut_start": cut_start, "configs": {}, "timings": {}, "shifts": {}}
    models = {}
    for name in names:
        kind, region, scale = CONFIGS[name]
        if kind not in models:
            models[kind] = load_model(kind)
        t0 = time.time()
        doc["configs"][name] = {str(cut_start + k): detect(models[kind], im, region, scale, conf, W, H) for k, im in enumerate(frames)}
        doc["timings"][name] = round(time.time() - t0, 1)
    t0 = time.time()
    orb = cv2.ORB_create(2000)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    prev = None
    for k, im in enumerate(frames):
        g = cv2.cvtColor(cv2.resize(im, None, fx=0.5, fy=0.5), cv2.COLOR_BGR2GRAY)
        kp, d = orb.detectAndCompute(g, None)
        if prev is not None and d is not None and prev[1] is not None:
            m = bf.match(prev[1], d)
            if len(m) >= 20:
                p1 = np.float32([prev[0][x.queryIdx].pt for x in m])
                p2 = np.float32([kp[x.trainIdx].pt for x in m])
                M, inl = cv2.estimateAffinePartial2D(p1, p2, method=cv2.RANSAC, ransacReprojThreshold=3)
                if M is not None:
                    doc["shifts"][str(cut_start + k)] = {"a": float(M[0, 0]), "b": float(M[0, 1]), "tx": float(M[0, 2]) * 2,
                                                         "ty": float(M[1, 2]) * 2, "inliers": int(inl.sum()) if inl is not None else 0}
        prev = (kp, d)
    doc["timings"]["orb"] = round(time.time() - t0, 1)
    return doc


LANE_MAX_RESID = 14.0
LANE_MAX_R = 30.0   # prompts come from the path; the release ball (r 60-130 px, head still down) warps badly into
                    # the pin-hit frame and the SAM mask fails the residual gate (3 of 5 dev with the whole chain)


def lane_pass(cut_path, positions_src, cut_start, overlay_path, max_r=LANE_MAX_R, pin_refit=False):
    """Engine SAM lane calibration on the cut (cut-local frames in, source frames out)."""
    from src.bowling.lane_tracking import lane_calibration as LC
    from src.bowling.lane_tracking.sam_prompter import SamLaneSegmenter
    from scripts.sam_lane_pass import board_summary, calibrated_boards
    # The chain reaches the pins, so the engine's default candidates (pin_hit-4, then later ones) have the ball in the
    # rack and the mask leaks into the deck (190115 resid 12 px); after the hit the bowler turns away. So the
    # pin-hit guess is moved 6 frames before the chain end and only earlier candidates are tried. The glasses'
    # wide lens bends the lane edges (fit residual 8-13 px on 185121/190115 against the engine's 8 px gate).
    LC.CANDIDATE_BACKS, LC.CANDIDATE_AHEADS = (8,), (2,)   # 3 candidates: each is 2-3 SAM calls (~25 s) and a fit above 5 px never stops the search early
    LC.MAX_RESID_PX = LANE_MAX_RESID
    local = [(int(p[0]) - cut_start, float(p[1]), float(p[2]), float(p[3])) for p in positions_src]
    prompt_seg = [p for p in local if p[3] <= max_r] or local
    seg = SamLaneSegmenter("sam2.1_t.pt", str(ENGINE / "models"))
    out = {"lane": {}, "boards": {}, "final_board": None, "lane_method": None, "pin_hit_frame": None,
           "prompt_segment": [prompt_seg[0][0] + cut_start, prompt_seg[-1][0] + cut_start, len(prompt_seg)]}
    try:
        calib = LC.calibrate_lane(cut_path, local, seg, segment=prompt_seg, pin_hit=local[-1][0], back=4, pin_refit=pin_refit,
                                  verbose=True, overlay_path=overlay_path)
    except Exception as e:  # noqa: BLE001
        print(f"  [lane] raised {type(e).__name__}: {e}")
        calib = None
    if calib is None:
        out["lane_error"] = getattr(seg, "load_error", None) or "no calibration"
        return out
    boards = calibrated_boards(calib, local)
    summ = board_summary(calib, local, boards)
    out["final_board"] = summ.get("final_board")
    out["final_board_raw"] = summ.get("final_board_raw")
    out["entry_board"] = summ.get("entry_board")
    out["lane_method"] = calib.method
    out["lane_quality"] = calib.quality
    out["boards"] = {str(b["frame"] + cut_start): b["board"] for b in boards if b.get("on_lane")}
    for f in calib.aligner.frames():
        c = calib.corners_at(int(f))
        out["lane"][str(int(f) + cut_start)] = {"fl_l": [round(float(c["bottom_left"][0]), 1), round(float(c["bottom_left"][1]), 1)],
                                                "fl_r": [round(float(c["bottom_right"][0]), 1), round(float(c["bottom_right"][1]), 1)],
                                                "pd_l": [round(float(c["top_left"][0]), 1), round(float(c["top_left"][1]), 1)],
                                                "pd_r": [round(float(c["top_right"][0]), 1), round(float(c["top_right"][1]), 1)]}
    cr = calib.crossing(local)
    if cr is not None:
        out["pin_hit_frame"] = int(round(cr[2])) + cut_start
    return out


def draw_overlay(frames, cut_start, f_src, positions, lane, final_board, stem, path, note):
    k = min(max(f_src - cut_start, 0), len(frames) - 1)
    im = frames[k].copy()
    pts = [(int(p[1]), int(p[2])) for p in positions]
    for a, b in zip(pts, pts[1:]):
        cv2.line(im, a, b, (0, 140, 255), 3)
    for p in positions:
        if int(p[0]) == f_src:
            cv2.circle(im, (int(p[1]), int(p[2])), max(int(p[3]), 6), (0, 255, 255), 3)
    q = lane.get(str(f_src))
    if q:
        poly = np.array([q["fl_l"], q["pd_l"], q["pd_r"], q["fl_r"]], np.int32)
        cv2.polylines(im, [poly], True, (255, 220, 0), 3)
    cv2.putText(im, f"{stem} f{f_src} (pin_hit-4)", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
    cv2.putText(im, f"final board {final_board}  {note}", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
    cv2.imwrite(str(path), im)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stem")
    ap.add_argument("--cache", action="store_true")
    ap.add_argument("--configs", default=",".join(DEFAULT_CONFIGS))
    ap.add_argument("--no-lane", action="store_true")
    ap.add_argument("--pin-refit", action="store_true")
    args = ap.parse_args()
    names = [n for n in args.configs.split(",") if n]
    t_all = time.time()
    cuts = {c["stem"]: c for c in json.load(open(L / "work/cuts/cuts.json"))}
    c = cuts[args.stem]
    cut_start = int(c["cut_start"])
    frames = read_cut(c["cut_path"])
    cache = HERE / "work" / f"dets_{args.stem}.json"
    if args.cache and cache.exists():
        doc = json.load(open(cache))
        doc["configs"] = {n: doc["configs"][n] for n in names}
    else:
        doc = detect_all(frames, cut_start, names)
    t_det = time.time() - t_all
    pc = PoolConfig(floors={n: 0.1 for n in names})
    positions, report, pool = run_chain(doc, pc, CHAIN)
    t_chain = time.time() - t_all - t_det
    print(f"{args.stem}: {len(frames)} frames, {report['pool_boxes']} pooled boxes, chain {len(positions)} positions "
          f"{[positions[0][0], positions[-1][0]] if positions else None} throw {report.get('throw')}")
    (HERE / "overlays").mkdir(exist_ok=True)
    (HERE / "tracks").mkdir(exist_ok=True)
    lane = {"lane": {}, "boards": {}, "final_board": None, "pin_hit_frame": None}
    if positions and not args.no_lane:
        lane = lane_pass(c["cut_path"], positions, cut_start, str(HERE / "work" / f"lane_{args.stem}.jpg"), pin_refit=args.pin_refit)
    t_lane = time.time() - t_all - t_det - t_chain
    tracks = {"stem": args.stem, "method": "detector-tiling:pool(" + "+".join(names) + ")+yolo_chain+sam_lane",
              "frames": [{"f": int(p[0]), "x": round(float(p[1]), 1), "y": round(float(p[2]), 1), "r": round(float(p[3]), 1), "conf": round(float(p[4]), 3)} for p in positions],
              "lane": lane["lane"], "boards": lane["boards"], "final_board": lane["final_board"],
              "fl_is_foul_line": False,
              "fl_note": "fl_* is the bottom of the SAM lane mask on that frame (lowest visible lane row), not the foul line, which is never in view after release",
              "release_frame": int(positions[0][0]) if positions else None,
              "pin_hit_frame": lane.get("pin_hit_frame") or (int(positions[-1][0]) if positions else None),
              "lane_method": lane.get("lane_method"), "lane_error": lane.get("lane_error"),
              "wall_s": round(time.time() - t_all, 1), "from_cache": bool(args.cache and cache.exists())}
    json.dump(tracks, open(HERE / "tracks" / f"{args.stem}.json", "w"), indent=1)
    rep = {"stem": args.stem, "chain": report, "timings": {"detect_s": round(t_det, 1), "chain_s": round(t_chain, 2), "lane_s": round(t_lane, 1),
                                                          "wall_s": tracks["wall_s"], "det_breakdown": doc.get("timings")},
           "lane": {k: v for k, v in lane.items() if k not in ("lane", "boards")}}
    json.dump(rep, open(HERE / "work" / f"run_{args.stem}.json", "w"), indent=1, default=str)
    draw_overlay(frames, cut_start, int(c["pin_hit_frame"]) - 4, positions, lane["lane"], lane["final_board"], args.stem,
                 HERE / "overlays" / f"{args.stem}.jpg", f"lane {lane.get('lane_method') or lane.get('lane_error')}")
    print(f"  final_board {lane['final_board']} lane {lane.get('lane_method')} wall {tracks['wall_s']}s "
          f"(detect {t_det:.1f} chain {t_chain:.2f} lane {t_lane:.1f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
