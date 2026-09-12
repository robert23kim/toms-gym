"""E3: VLM ball auto-labelling accuracy vs ball ground truth.

Sends single frames to a Gemini model and asks for the bowling ball's bounding
box (or null). Scores with the engine's 50px center criterion, including
false positives on explicit no-ball frames. This measures whether a VLM can
bootstrap a training set, not whether it can run per frame in production.

usage: e3_vlm_ball_label.py MODEL [--every 3] [--neg 8] [--context]
"""
import argparse
import json
import sys
import time

import gemini
import gt

PROMPT = """This is one frame of a phone video of a ten-pin bowling lane filmed from behind the bowler.

Find the BOWLING BALL if it is on the lane surface (rolling toward the pins). The ball may be small, dark, and motion-blurred into a streak; a blurred ball is still the ball. Ignore balls on the ball-return rack, in a bowler's hands before release, and pins.

Respond with JSON only:
{"ball": [ymin, xmin, ymax, xmax]} with coordinates normalized 0-1000 (y down, x right), or {"ball": null} if no ball is on the lane in this frame."""

PROMPT_CONTEXT = """These are two consecutive frames of a phone video of a ten-pin bowling lane filmed from behind the bowler. The FIRST image is the earlier frame, the SECOND image is the frame to label.

Find the BOWLING BALL in the SECOND image if it is on the lane surface (rolling toward the pins). Compare the two frames: the ball is the small object that moved along the lane. It may be dark and motion-blurred into a streak; a blurred ball is still the ball. Ignore balls on the ball-return rack, in a bowler's hands before release, and pins.

Respond with JSON only:
{"ball": [ymin, xmin, ymax, xmax]} with coordinates for the SECOND image normalized 0-1000 (y down, x right), or {"ball": null} if no ball is on the lane."""


def ask(model, stem, idx, thinking, context):
    ann = gt.load_annotation(stem)
    w, h = ann["video_metadata"]["width"], ann["video_metadata"]["height"]
    parts = []
    if context and idx > 0:
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": gt.image_b64(gt.frame_path(stem, idx - 1))}})
    parts.append({"inline_data": {"mime_type": "image/jpeg", "data": gt.image_b64(gt.frame_path(stem, idx))}})
    parts.append({"text": PROMPT_CONTEXT if (context and idx > 0) else PROMPT})
    t0 = time.time()
    text, usage = gemini.generate(model, parts, thinking=thinking)
    dt = time.time() - t0
    d = gemini.parse_json(text)
    b = d.get("ball")
    if not b:
        return None, dt, usage
    ymin, xmin, ymax, xmax = [float(v) for v in b]
    return ((xmin + xmax) / 2 / 1000 * w, (ymin + ymax) / 2 / 1000 * h), dt, usage


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--every", type=int, default=3)
    ap.add_argument("--neg", type=int, default=8)
    ap.add_argument("--thinking", type=int, default=None)
    ap.add_argument("--context", action="store_true")
    a = ap.parse_args()
    tag = f"{a.model}{'_ctx' if a.context else ''}{'' if a.thinking is None else '_t'+str(a.thinking)}"
    all_rows = []
    summary = {}
    for stem in gt.VIDEOS:
        pos, neg = gt.ball_gt(stem)
        pos_frames = sorted(pos)[::a.every]
        neg_sorted = sorted(neg)
        step = max(1, len(neg_sorted) // a.neg) if neg_sorted else 1
        neg_frames = neg_sorted[::step][:a.neg]
        pred = {}
        lat = []
        for f in pos_frames + neg_frames:
            try:
                p, dt, usage = ask(a.model, stem, f, a.thinking, a.context)
                pred[f] = p
                lat.append(dt)
                all_rows.append({"stem": stem, "frame": f, "pred": p, "gt": pos.get(f), "latency_s": round(dt, 2)})
            except Exception as e:  # noqa: BLE001
                pred[f] = None
                all_rows.append({"stem": stem, "frame": f, "error": str(e)[:200]})
            print(json.dumps(all_rows[-1]), flush=True)
        m = gt.evaluate_centers(pred, {f: pos[f] for f in pos_frames}, set(neg_frames))
        m["neg_frames"] = len(neg_frames)
        m["mean_latency_s"] = round(sum(lat) / len(lat), 2) if lat else None
        summary[stem] = m
    json.dump({"summary": summary, "rows": all_rows}, open(f"e3_{tag}.json", "w"), indent=1)
    print("\n== summary", tag)
    print(f"{'video':18s} {'recall':>7s} {'prec':>7s} {'meanerr':>8s} {'tp':>4s} {'fp':>4s} {'fn':>4s} {'negs':>5s} {'lat s':>6s}")
    for stem, m in summary.items():
        me = f"{m['mean_err_px']:.1f}" if m["mean_err_px"] is not None else "-"
        print(f"{stem:18s} {m['recall']:6.1f}% {m['precision']:6.1f}% {me:>8s} {m['tp']:4d} {m['fp']:4d} {m['fn']:4d} {m['neg_frames']:5d} {m['mean_latency_s']:6}")


if __name__ == "__main__":
    sys.exit(main())
