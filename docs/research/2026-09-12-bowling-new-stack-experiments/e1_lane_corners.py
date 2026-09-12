"""E1: lane corners from a VLM vs annotated lane corners.

For each video and each sampled frame, ask the model for the four lane corners,
then measure (a) pixel error per corner and (b) the board-number error that the
predicted homography would induce on the annotated ball positions.

usage: e1_lane_corners.py MODEL [--frames 0,60] [--repeats 3]
"""
import argparse
import json
import statistics
import sys
import time

import numpy as np

import gemini
import gt

PROMPT = """This is one frame of a phone video of a ten-pin bowling lane, filmed from behind the bowler looking down the lane toward the pins.

Find the four corners of the LANE SURFACE (the playing surface the ball rolls on). The lane is bounded on the left and right by the gutters (the channels beside the lane), at the far end by the pin deck where the pins stand, and at the near end by the foul line or, if the foul line is out of frame, by the bottom edge of the image where the lane leaves the frame.

Return the four corners as image points:
- top_left: where the LEFT lane/gutter boundary meets the pin deck (just in front of the pins)
- top_right: where the RIGHT lane/gutter boundary meets the pin deck
- bottom_left: where the LEFT lane/gutter boundary meets the foul line (or the bottom of the visible lane)
- bottom_right: where the RIGHT lane/gutter boundary meets the foul line (or the bottom of the visible lane)

Use the lane/gutter boundary itself, not the outside edge of the gutter or the ball-return rail. Be precise: the far end of the lane is narrow in the image, so small errors matter.

Respond with JSON only, in this exact shape, with each point as [y, x] in normalized coordinates 0-1000 (y down, x right):
{"top_left": [y, x], "top_right": [y, x], "bottom_left": [y, x], "bottom_right": [y, x]}"""

KEYS = ("top_left", "top_right", "bottom_left", "bottom_right")


MARK_NOTE = """

IMPORTANT: several lanes are visible. The bowling ball currently rolling is circled in MAGENTA. Return the corners of THE LANE THE MAGENTA-CIRCLED BALL IS ROLLING ON, not any neighbouring lane."""


def marked_frame_b64(stem, idx):
    """Frame with the GT ball circled in magenta (stands in for the ball detector)."""
    import base64
    import cv2
    pos, _ = gt.ball_gt(stem)
    x, y, r = pos[idx]
    img = cv2.imread(str(gt.frame_path(stem, idx)))
    cv2.circle(img, (int(x), int(y)), int(max(r * 2.5, 18)), (255, 0, 255), 3)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 95])
    return base64.b64encode(buf.tobytes()).decode()


def ball_frame(stem):
    pos, _ = gt.ball_gt(stem)
    fs = sorted(pos)
    return fs[len(fs) // 2]


def ask(model, stem, idx, thinking, mark_ball=False):
    ann = gt.load_annotation(stem)
    w, h = ann["video_metadata"]["width"], ann["video_metadata"]["height"]
    if mark_ball:
        data, prompt = marked_frame_b64(stem, idx), PROMPT + MARK_NOTE
    else:
        data, prompt = gt.image_b64(gt.frame_path(stem, idx)), PROMPT
    parts = [{"inline_data": {"mime_type": "image/jpeg", "data": data}}, {"text": prompt}]
    t0 = time.time()
    text, usage = gemini.generate(model, parts, thinking=thinking)
    dt = time.time() - t0
    d = gemini.parse_json(text)
    pred = {}
    for k in KEYS:
        y, x = d[k]
        pred[k] = (float(x) / 1000.0 * w, float(y) / 1000.0 * h)
    return pred, dt, usage


def score(stem, pred):
    truth = gt.lane_gt(stem)
    pos, _ = gt.ball_gt(stem)
    pts = [(x, y) for (x, y, _r) in pos.values()]
    corner_err = {k: float(np.hypot(pred[k][0] - truth[k][0], pred[k][1] - truth[k][1])) for k in KEYS}
    b_true, _ = gt.board_from_corners(truth, pts)
    b_pred, _ = gt.board_from_corners(pred, pts)
    diff = np.abs(b_pred - b_true)
    top_w_true = truth["top_right"][0] - truth["top_left"][0]
    top_w_pred = pred["top_right"][0] - pred["top_left"][0]
    return {
        "corner_err_px": corner_err,
        "corner_err_mean_px": float(np.mean(list(corner_err.values()))),
        "board_abs_err_mean": float(diff.mean()),
        "board_abs_err_max": float(diff.max()),
        "board_within_1": float((diff <= 1.0).mean() * 100),
        "board_within_2": float((diff <= 2.0).mean() * 100),
        "top_width_true_px": float(top_w_true),
        "top_width_pred_px": float(top_w_pred),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--frames", default="0,60")
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--thinking", type=int, default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--mark-ball", action="store_true",
                    help="use the median ball frame and circle the GT ball (ball-detector stand-in)")
    a = ap.parse_args()
    frames = [int(x) for x in a.frames.split(",")]
    results = []
    for stem in gt.VIDEOS:
        for idx in ([ball_frame(stem)] if a.mark_ball else frames):
            for rep in range(a.repeats):
                try:
                    pred, dt, usage = ask(a.model, stem, idx, a.thinking, a.mark_ball)
                    s = score(stem, pred)
                    row = {"stem": stem, "frame": idx, "rep": rep, "ok": True, "latency_s": round(dt, 2),
                           "pred": {k: [round(v[0]), round(v[1])] for k, v in pred.items()}, **s,
                           "tokens": usage.get("totalTokenCount")}
                except Exception as e:  # noqa: BLE001
                    row = {"stem": stem, "frame": idx, "rep": rep, "ok": False, "error": str(e)[:200]}
                results.append(row)
                print(json.dumps(row), flush=True)
    out = a.out or f"e1_{a.model}{'_markball' if a.mark_ball else ''}.json"
    json.dump(results, open(out, "w"), indent=1)
    print("\n== summary", a.model)
    print(f"{'video':18s} {'corner px':>10s} {'board mae':>10s} {'board max':>10s} {'<=1 board':>10s} {'top w true/pred':>16s}")
    for stem in gt.VIDEOS:
        rows = [r for r in results if r["stem"] == stem and r["ok"]]
        if not rows:
            print(f"{stem:18s} all failed")
            continue
        print(f"{stem:18s} {statistics.mean(r['corner_err_mean_px'] for r in rows):10.1f} "
              f"{statistics.mean(r['board_abs_err_mean'] for r in rows):10.2f} "
              f"{max(r['board_abs_err_max'] for r in rows):10.2f} "
              f"{statistics.mean(r['board_within_1'] for r in rows):9.0f}% "
              f"{rows[0]['top_width_true_px']:7.0f}/{statistics.mean(r['top_width_pred_px'] for r in rows):<8.0f}")


if __name__ == "__main__":
    sys.exit(main())
