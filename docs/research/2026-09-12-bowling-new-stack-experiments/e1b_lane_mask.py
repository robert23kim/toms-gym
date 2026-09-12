"""E1b: lane corners from a promptable SEGMENTER (runs on CPU) vs annotated corners.

Two backends:
  sam2   - SAM 2.1 with a single positive point prompt at the lane centre. The
           point comes from the centroid of the Gemini quad from E1 (coarse but
           automatic), so the chain is VLM-for-the-rough-location + SAM-for-the-
           precise-boundary. Falls back to the GT centroid with --gt-point.
  yoloe  - YOLOE-11 seg with the text prompt "bowling lane" (no point at all).

Mask -> per-row leftmost/rightmost lane pixels -> robust line fit per edge ->
corners = edge lines evaluated at the GT top/bottom y (so the metric isolates
"is the edge line right", which is all the board homography depends on).

usage: e1b_lane_mask.py sam2|yoloe [--frames 0,60] [--weights ...] [--gt-point]
"""
import argparse
import json
import sys
import time

import cv2
import numpy as np

import gt

KEYS = ("top_left", "top_right", "bottom_left", "bottom_right")


def gemini_centroid(stem, frame):
    try:
        rows = json.load(open("e1_gemini-3.5-flash.json"))
    except FileNotFoundError:
        return None
    r = [r for r in rows if r["stem"] == stem and r["frame"] == frame and r["ok"]]
    if not r:
        return None
    p = r[0]["pred"]
    xs = [p[k][0] for k in KEYS]
    ys = [p[k][1] for k in KEYS]
    return float(np.mean(xs)), float(np.mean(ys))


def gt_centroid(stem):
    t = gt.lane_gt(stem)
    return float(np.mean([t[k][0] for k in KEYS])), float(np.mean([t[k][1] for k in KEYS]))


def lane_mask(kind, model, img_path, point):
    if kind == "sam2":
        pts = point if isinstance(point[0], (list, tuple)) else [[int(point[0]), int(point[1])]]
        res = model.predict(img_path, points=pts, labels=[1] * len(pts), verbose=False)[0]
        if res.masks is None or len(res.masks) == 0:
            return None
        return res.masks.data[0].cpu().numpy().astype(np.uint8)
    res = model.predict(img_path, conf=0.05, imgsz=1280, verbose=False)[0]
    if res.masks is None or len(res.masks) == 0:
        return None
    # largest mask wins
    masks = res.masks.data.cpu().numpy().astype(np.uint8)
    areas = masks.reshape(len(masks), -1).sum(1)
    m = masks[int(np.argmax(areas))]
    h, w = cv2.imread(img_path).shape[:2]
    if m.shape != (h, w):
        m = cv2.resize(m, (w, h), interpolation=cv2.INTER_NEAREST)
    return m


FIT_MARGIN = 0.0


def fit_edges(mask, y_top, y_bot):
    """Return (left_line, right_line) as (a, b) with x = a*y + b, fitted on
    rows between y_top and y_bot using the largest connected component."""
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    if n <= 1:
        return None
    big = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    m = (lab == big)
    ys, ls, rs = [], [], []
    y_fit_top = int(y_top + FIT_MARGIN * (y_bot - y_top))
    for y in range(int(y_top), int(y_bot) + 1):
        xs = np.where(m[y])[0]
        if y < y_fit_top:
            continue
        if len(xs) < 5:
            continue
        ys.append(y)
        ls.append(xs.min())
        rs.append(xs.max())
    if len(ys) < 10:
        return None
    ys = np.array(ys, float)

    def robust(xs):
        xs = np.array(xs, float)
        a, b = np.polyfit(ys, xs, 1)
        for _ in range(3):
            resid = np.abs(xs - (a * ys + b))
            keep = resid <= max(3.0, 2.0 * np.median(resid) + 1e-6)
            if keep.sum() < 10:
                break
            a, b = np.polyfit(ys[keep], xs[keep], 1)
        return a, b, float(np.mean(np.abs(xs - (a * ys + b))))

    la, lb, lr = robust(ls)
    ra, rb, rr = robust(rs)
    coverage = len(ys) / max(1.0, (y_bot - y_top + 1))
    return (la, lb), (ra, rb), {"fit_resid_px": round((lr + rr) / 2, 1), "row_coverage": round(coverage, 2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["sam2", "yoloe"])
    ap.add_argument("--frames", default="0,60")
    ap.add_argument("--weights", default=None)
    ap.add_argument("--gt-point", action="store_true")
    ap.add_argument("--point", default="gemini", choices=["gemini", "ball", "track", "gt"],
                    help="ball = GT ball position on the median ball frame (ball-detector stand-in)")
    ap.add_argument("--fit-margin", type=float, default=0.0,
                    help="skip this fraction of rows at the pin end when fitting edge lines (extrapolate instead)")
    a = ap.parse_args()
    global FIT_MARGIN
    FIT_MARGIN = a.fit_margin
    if a.gt_point:
        a.point = "gt"
    frames = [int(x) for x in a.frames.split(",") if x.isdigit()]
    if a.kind == "sam2":
        from ultralytics import SAM
        model = SAM(a.weights or "sam2.1_b.pt")
    else:
        from ultralytics import YOLOE
        model = YOLOE(a.weights or "yoloe-11l-seg.pt")
        model.set_classes(["bowling lane"], model.get_text_pe(["bowling lane"]))
    results = []
    for stem in gt.VIDEOS:
        truth = gt.lane_gt(stem)
        pos, _ = gt.ball_gt(stem)
        pts = [(x, y) for (x, y, _r) in pos.values()]
        y_top = min(truth["top_left"][1], truth["top_right"][1])
        y_bot = max(truth["bottom_left"][1], truth["bottom_right"][1])
        if a.point == "track":
            # several lane-surface pixels = the ball trajectory, on a pre-release frame
            fs = sorted(pos)
            picks = [fs[int(i)] for i in np.linspace(0, len(fs) - 1, 7)][1:-1]
            track_pts = [[int(pos[f][0]), int(pos[f][1])] for f in picks]
            n_frames = gt.load_annotation(stem)["video_metadata"]["total_frames"]
            frames = [max(0, fs[0] - 5)] if a.frames == "0,60" else [
                (n_frames - 1 if tok == "last" else max(0, fs[0] - 5) if tok == "pre" else int(tok))
                for tok in a.frames.split(",")]
        if a.point == "ball":
            # lane-surface pixel = where the ball is mid-throw; image = a frame
            # before release so the point lands on the lane, not on the ball.
            fs = sorted(pos)
            mid = fs[len(fs) // 2]
            ball_pt = (pos[mid][0], pos[mid][1])
            frames = [max(0, fs[0] - 5)]
        for f in frames:
            if a.point == "gt":
                point = gt_centroid(stem)
            elif a.point == "ball":
                point = ball_pt
            elif a.point == "track":
                point = track_pts
            else:
                point = gemini_centroid(stem, f) or gt_centroid(stem)
            t0 = time.time()
            img_path = str(gt.frame_path(stem, f))
            m = lane_mask(a.kind, model, img_path, point)
            dt = time.time() - t0
            row = {"stem": stem, "frame": f, "point": point if isinstance(point[0], (list, tuple)) else [round(point[0]), round(point[1])], "latency_s": round(dt, 2)}
            lines = fit_edges(m, y_top, y_bot) if m is not None else None
            if lines is None:
                row["ok"] = False
                results.append(row)
                print(json.dumps(row), flush=True)
                continue
            (la, lb), (ra, rb), quality = lines
            pred = {"top_left": (la * y_top + lb, y_top), "top_right": (ra * y_top + rb, y_top),
                    "bottom_left": (la * y_bot + lb, y_bot), "bottom_right": (ra * y_bot + rb, y_bot)}
            corner_err = {k: float(np.hypot(pred[k][0] - truth[k][0], pred[k][1] - truth[k][1])) for k in KEYS}
            b_true, _ = gt.board_from_corners(truth, pts)
            b_pred, _ = gt.board_from_corners(pred, pts)
            diff = np.abs(b_pred - b_true)
            row.update(quality)
            row.update({"ok": True, "pred": {k: [round(v[0]), round(v[1])] for k, v in pred.items()},
                        "corner_err_px": {k: round(v, 1) for k, v in corner_err.items()},
                        "corner_err_mean_px": float(np.mean(list(corner_err.values()))),
                        "board_abs_err_mean": float(diff.mean()), "board_abs_err_max": float(diff.max()),
                        "board_within_1": float((diff <= 1).mean() * 100),
                        "top_width_true_px": float(truth["top_right"][0] - truth["top_left"][0]),
                        "top_width_pred_px": float(pred["top_right"][0] - pred["top_left"][0])})
            results.append(row)
            print(json.dumps(row), flush=True)
            # debug overlay
            img = cv2.imread(img_path)
            overlay = img.copy()
            overlay[m.astype(bool)] = (0.5 * overlay[m.astype(bool)] + [0, 0, 128]).astype(np.uint8)
            for k in KEYS:
                cv2.circle(overlay, (int(truth[k][0]), int(truth[k][1])), 8, (0, 255, 0), -1)
                cv2.circle(overlay, (int(pred[k][0]), int(pred[k][1])), 6, (0, 0, 255), -1)
            for pt in (point if isinstance(point[0], (list, tuple)) else [point]):
                cv2.circle(overlay, (int(pt[0]), int(pt[1])), 10, (255, 255, 0), 2)
            h, w = overlay.shape[:2]
            cv2.imwrite(f"dbg_e1b_{a.kind}_{a.point}_{stem}_{f}.jpg", cv2.resize(overlay, (int(w * 900 / h), 900)))
    tag = f"{a.kind}_{a.point}" + ("" if a.frames == "0,60" else "_" + a.frames.replace(",", "-")) + (f"_m{a.fit_margin}" if a.fit_margin else "")
    json.dump(results, open(f"e1b_{tag}.json", "w"), indent=1)
    print("\n== summary", tag)
    print(f"{'video':18s} {'frame':>5s} {'corner px':>10s} {'board mae':>10s} {'board max':>10s} {'<=1 board':>10s} {'top w true/pred':>16s} {'sec':>5s} {'resid':>6s} {'cover':>6s}")
    for r in results:
        if r.get("ok"):
            print(f"{r['stem']:18s} {r['frame']:5d} {r['corner_err_mean_px']:10.1f} {r['board_abs_err_mean']:10.2f} "
                  f"{r['board_abs_err_max']:10.2f} {r['board_within_1']:9.0f}% {r['top_width_true_px']:7.0f}/{r['top_width_pred_px']:<8.0f} {r['latency_s']:5.1f} {r['fit_resid_px']:6.1f} {r['row_coverage']:6.2f}")
        else:
            print(f"{r['stem']:18s} {r['frame']:5d} no mask")
    print("\n== auto-selected frame per video (lowest fit residual, coverage >= 0.8)")
    for stem in gt.VIDEOS:
        rs = [r for r in results if r["stem"] == stem and r.get("ok") and r["row_coverage"] >= 0.8]
        if not rs:
            print(f"{stem:18s} none qualifies")
            continue
        r = min(rs, key=lambda r: r["fit_resid_px"])
        print(f"{stem:18s} frame {r['frame']:4d} board mae {r['board_abs_err_mean']:.2f} max {r['board_abs_err_max']:.2f} <=1: {r['board_within_1']:.0f}% resid {r['fit_resid_px']}")


if __name__ == "__main__":
    sys.exit(main())
