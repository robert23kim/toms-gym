"""wildcard: NCC template relay from a YOLO-chain seed, SAM lane for the board.

usage: run.py <stem> [--no-sam]
Reads L/work/cuts/cuts.json + the cut; writes tracks/<stem>.json (SOURCE frames) and overlays/<stem>.jpg.
Pipeline: engine scan_video (YOLO boxes + ORB shifts) -> engine chain_detections (seed only) ->
ncc_relay forward to the pins and backward to release -> engine run_sam_lane_pass (per-frame lane, boards)."""
import json
import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ENGINE = "/Users/toka/code/bowling-app/pov-engine"
HERE = Path(__file__).resolve().parent
L = HERE.parents[1]
sys.path.insert(0, ENGINE)
sys.path.insert(0, str(HERE))
os.chdir(ENGINE)  # the SAM segmenter and chain pass resolve models/ relative to the engine
from src.bowling.trajectory.yolo_chain import ChainConfig, chain_detections  # noqa: E402
from src.bowling.trajectory.yolo_chain_pass import scan_video  # noqa: E402
from ncc_relay import relay, seed_from_box, shift_pt  # noqa: E402

CORNER_MAP = {"top_left": "pd_l", "top_right": "pd_r", "bottom_left": "fl_l", "bottom_right": "fl_r"}


def release_estimate(track, H, W, max_r=150.0):
    """First tracked frame with the whole ball inside the frame and r <= max_r: before release the ball is
    cut off at the bottom and bigger than any ball on the lane (truth r at release 107-130 px)."""
    for k in sorted(track):
        x, y, r, _ = track[k]
        if r <= max_r and y + r < H - 2 and x - r > 2 and x + r < W - 2:
            return k
    return min(track) if track else None


def pin_estimate(track, shifts, start_k, bias=8):
    """First frame (after start_k + 20) where the 5-frame mean camera-compensated ball speed drops below
    max(0.2 r, 1.5 px): the ball has stopped travelling up the lane. +bias frames: on the dev set the speed
    settles 1-12 frames (median 5) before the ball is level with the pin bases; 8 keeps the SAM segment and the
    final-board read at the pins (tuned on dev truth)."""
    ks = sorted(track)
    spd = {}
    for a, b in zip(ks, ks[1:]):
        if b != a + 1:
            continue
        qx, qy = shift_pt(shifts, b, track[a][0], track[a][1])
        spd[b] = float(np.hypot(track[b][0] - qx, track[b][1] - qy))
    for i in range(len(ks) - 5):
        k = ks[i]
        if k < start_k + 20:
            continue
        w = [spd.get(ks[j]) for j in range(i, i + 5)]
        if all(v is not None for v in w) and np.mean(w) < max(0.2 * track[k][2], 1.5):
            return min(k + bias, ks[-1])
    return ks[-1] if ks else None


def main():
    stem = sys.argv[1]
    use_sam = "--no-sam" not in sys.argv
    cuts = {c["stem"]: c for c in json.load(open(L / "work/cuts/cuts.json"))}
    cut = cuts[stem]
    off = int(cut["cut_start"])
    video = cut["cut_path"]
    t_all = time.time()
    timings = {}
    meta = {"engine": ENGINE, "cut": video, "cut_start": off, "cut_end": int(cut["cut_end"])}

    t0 = time.time()
    dets, shifts, scan_meta = scan_video(video, f"{ENGINE}/models/yolo11n_bowling.pt", conf=0.05)
    timings["scan_s"] = round(time.time() - t0, 1)
    chain, rep = chain_detections(dets, shifts, ChainConfig())
    meta["chain"] = {"n": len(chain), "frames": [chain[0][0] + off, chain[-1][0] + off] if chain else None,
                     "throw": rep.get("throw")}

    cap = cv2.VideoCapture(video)
    frames = []
    while True:
        ok, im = cap.read()
        if not ok:
            break
        frames.append(im)
    cap.release()
    H, W = frames[0].shape[:2]
    labs = [cv2.cvtColor(f, cv2.COLOR_BGR2LAB) for f in frames]

    track = {}
    t0 = time.time()
    if chain:
        seed = max(chain[:6], key=lambda p: p[4])
        k0 = int(seed[0])
        sx, sy, sr = seed_from_box(labs[k0], seed[1], seed[2], seed[3])
        meta["seed"] = {"frame": k0 + off, "x": round(sx, 1), "y": round(sy, 1), "r": round(sr, 1),
                        "box_r": round(seed[3], 1), "box_conf": round(seed[4], 2)}
        fwd = relay(labs, shifts, k0, sx, sy, sr, forward=True)
        bwd = relay(labs, shifts, k0, sx, sy, sr, forward=False, scales=(1.0, 1.15, 1.3), min_score=0.45)
        track[k0] = (sx, sy, sr, float(seed[4]))
        for p in fwd + bwd:
            track[p[0]] = (p[1], p[2], p[3], p[4])
        meta["relay"] = {"forward": len(fwd), "backward": len(bwd)}
    else:
        meta["seed"] = None
    timings["relay_s"] = round(time.time() - t0, 1)

    rel_k = release_estimate(track, H, W)
    pin_k = pin_estimate(track, shifts, meta["seed"]["frame"] - off) if track else None
    positions = [(k, x, y, r, c) for k, (x, y, r, c) in sorted(track.items())]
    # the SAM pass aligns frames sequentially from the segment start: the 10-12 frames after release are the
    # head swing (ORB fails, the ball fills the frame), so the lane segment starts 12 frames after release
    seg_lo = (rel_k + 12) if rel_k is not None else None
    segment = [p for p in positions if seg_lo is not None and seg_lo <= p[0] <= (pin_k if pin_k is not None else 10**9)]
    meta["segment"] = [segment[0][0] + off, segment[-1][0] + off] if segment else None

    lane, boards, final_board, sam_fields = {}, {}, None, {}
    if use_sam and len(segment) >= 6:
        t0 = time.time()
        from scripts.sam_lane_pass import calibrated_boards, run_sam_lane_pass
        from src.bowling.lane_tracking import lane_calibration as lc
        lc.CANDIDATE_BACKS, lc.CANDIDATE_AHEADS = (4, 6, 8), (6, 12)  # bound the SAM wall time when every candidate fails
        calib, sam_fields = run_sam_lane_pass(video, segment, pin_hit=None, segment=segment, verbose=True,
                                              overlay_path=str(HERE / "work" / f"sam_{stem}.jpg"))
        timings["sam_s"] = round(time.time() - t0, 1)
        if calib is not None:
            doc = calib.to_dict()
            for k, c in doc["per_frame"].items():
                q = {CORNER_MAP[a]: [round(float(c[a][0]), 1), round(float(c[a][1]), 1)] for a in CORNER_MAP}
                q["fl_is_foul_line"] = False
                lane[str(int(k) + off)] = q
            for b in calibrated_boards(calib, segment):
                if b["board"] is not None and np.isfinite(b["board"]):
                    boards[str(int(b["frame"]) + off)] = round(float(b["board"]), 2)
            final_board = sam_fields.get("final_board")
        sam_fields = {k: v for k, v in sam_fields.items() if k != "lane_edges"}

    out = {
        "stem": stem, "method": "wildcard:ncc_relay+sam",
        "frames": [{"f": k + off, "x": round(x, 1), "y": round(y, 1), "r": round(r, 1), "conf": round(c, 3)}
                   for k, x, y, r, c in positions],
        "lane": lane, "boards": boards,
        "final_board": None if final_board is None else float(final_board),
        "release_frame": None if rel_k is None else rel_k + off,
        "pin_hit_frame": None if pin_k is None else min(pin_k, len(frames) - 1) + off,
        "meta": {**meta, "sam": sam_fields, "timings": timings, "wall_s": round(time.time() - t_all, 1),
                 "fl_is_foul_line": False, "note": "fl_* = lowest visible lane row (the foul line is never in frame)"},
    }
    out["meta"]["wall_s"] = round(time.time() - t_all, 1)
    (HERE / "tracks").mkdir(exist_ok=True)
    (HERE / "overlays").mkdir(exist_ok=True)
    json.dump(out, open(HERE / "tracks" / f"{stem}.json", "w"), indent=1)

    # overlay: the pin_hit-4 frame, the track as a polyline, the lane quad, the final board
    ov_k = int(np.clip((out["pin_hit_frame"] or (len(frames) - 1 + off)) - 4 - off, 0, len(frames) - 1))
    im = frames[ov_k].copy()
    pts = np.int32([[p["x"], p["y"]] for p in out["frames"]])
    if len(pts) > 1:
        cv2.polylines(im, [pts], False, (0, 140, 255), 3)
    for p in out["frames"]:
        cv2.circle(im, (int(p["x"]), int(p["y"])), max(int(p["r"]), 3), (0, 200, 255), 2)
    q = lane.get(str(ov_k + off))
    if q:
        poly = np.int32([q["fl_l"], q["pd_l"], q["pd_r"], q["fl_r"]])
        cv2.polylines(im, [poly], True, (255, 255, 0), 3)
    txt = [f"wildcard ncc_relay {stem} f{ov_k + off}", f"final board {out['final_board']}  release {out['release_frame']}  pin {out['pin_hit_frame']}",
           f"track {out['frames'][0]['f'] if out['frames'] else None}-{out['frames'][-1]['f'] if out['frames'] else None}  wall {out['meta']['wall_s']}s"]
    for i, s in enumerate(txt):
        cv2.putText(im, s, (20, 60 + 50 * i), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 0, 0), 6)
        cv2.putText(im, s, (20, 60 + 50 * i), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 2)
    cv2.imwrite(str(HERE / "overlays" / f"{stem}.jpg"), im, [cv2.IMWRITE_JPEG_QUALITY, 85])
    print(json.dumps({k: out[k] for k in ("stem", "final_board", "release_frame", "pin_hit_frame")} | {"n_frames": len(out["frames"]), "timings": timings, "wall_s": out["meta"]["wall_s"]}))


if __name__ == "__main__":
    main()
