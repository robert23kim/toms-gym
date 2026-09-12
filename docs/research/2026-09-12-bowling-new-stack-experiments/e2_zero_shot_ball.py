"""E2: zero-shot text-prompted ball detection vs ball ground truth.

Runs an open-vocabulary detector with the prompt "bowling ball" on every
annotated frame (ball frames + explicit no-ball frames) of the three videos and
reports recall/precision at several confidence floors with the engine's 50px
center criterion. No training, no lane mask, no tracking.

usage: e2_zero_shot_ball.py yoloe|yoloworld [--weights ...] [--imgsz 1280]
"""
import argparse
import json
import sys
import time

import gt

CONFS = (0.01, 0.05, 0.10, 0.25, 0.50)


def load(kind, weights):
    from ultralytics import YOLOE, YOLOWorld
    if kind == "yoloe":
        m = YOLOE(weights or "yoloe-11s-seg.pt")
        m.set_classes(["bowling ball"], m.get_text_pe(["bowling ball"]))
    else:
        m = YOLOWorld(weights or "yolov8s-worldv2.pt")
        m.set_classes(["bowling ball"])
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["yoloe", "yoloworld"])
    ap.add_argument("--weights", default=None)
    ap.add_argument("--imgsz", type=int, default=1280)
    ap.add_argument("--device", default="cpu")
    a = ap.parse_args()
    model = load(a.kind, a.weights)
    summary = {}
    for stem in gt.VIDEOS:
        pos, neg = gt.ball_gt(stem)
        frames = sorted(set(pos) | set(neg))
        raw = {}
        t0 = time.time()
        for f in frames:
            res = model.predict(str(gt.frame_path(stem, f)), conf=0.01, imgsz=a.imgsz,
                                device=a.device, verbose=False)[0]
            dets = []
            if res.boxes is not None and len(res.boxes):
                for b, c in zip(res.boxes.xyxy.tolist(), res.boxes.conf.tolist()):
                    dets.append((float(c), (b[0] + b[2]) / 2, (b[1] + b[3]) / 2))
            raw[f] = sorted(dets, reverse=True)
        dt = time.time() - t0
        summary[stem] = {"frames": len(frames), "sec_per_frame": round(dt / len(frames), 3)}
        print(f"\n== {stem}: {len(frames)} frames, {dt/len(frames):.2f}s/frame ({a.kind} {a.weights or 'default'} imgsz={a.imgsz})")
        print(f"{'conf':>5s} {'recall':>7s} {'prec':>7s} {'meanerr':>8s} {'tp':>4s} {'fp':>4s} {'fn':>4s}")
        for conf in CONFS:
            pred = {}
            for f, dets in raw.items():
                keep = [d for d in dets if d[0] >= conf]
                pred[f] = (keep[0][1], keep[0][2]) if keep else None
            m = gt.evaluate_centers(pred, pos, neg)
            summary[stem][str(conf)] = m
            me = f"{m['mean_err_px']:.1f}" if m["mean_err_px"] is not None else "-"
            print(f"{conf:5.2f} {m['recall']:6.1f}% {m['precision']:6.1f}% {me:>8s} {m['tp']:4d} {m['fp']:4d} {m['fn']:4d}")
    tag = f"{a.kind}_{(a.weights or 'default').replace('.pt','')}_{a.imgsz}"
    json.dump(summary, open(f"e2_{tag}.json", "w"), indent=1)


if __name__ == "__main__":
    sys.exit(main())
