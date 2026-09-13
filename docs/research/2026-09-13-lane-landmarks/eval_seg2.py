"""Score a two-class (lane + arrow) student on its held-out video: the lane as in loop 3
(anchor-selected mask -> RANSAC-free loop-1 edge fit -> corners at the annotated rows, board
MAE against every truth) and the learned arrows (class-1 boxes -> centres, matched to the
truth arrows of that frame: recall within 1.5 boards, px error, false per frame).
Writes results/seg2_<run>__<stem>.json (per_frame with corners, usable as an E2/E3 lane
source) and $LM_SCRATCH/pred/lm_learned_<run>_<stem>.json (arrow detections).
usage: eval_seg2.py <run_name> <stem> [--imgsz N] [--conf 0.1] [--arrow-conf 0.15]"""
import argparse
import json
import time

import cv2
import numpy as np
import torch

import common as C
import landmarks as LM

from ultralytics import YOLO  # noqa: E402

L = C.L
C.use_full_camera()
PRED = C.SCRATCH / "pred"


def main(run, stem, imgsz, conf, arrow_conf, gate=True):
    m = YOLO(str(C.SCRATCH / "runs" / run / "weights" / "best.pt"))
    per, lat, det_out = [], [], {}
    fits = {}
    for f in C.frame_ids(stem):
        img = C.read_frame(stem, f)
        anchors = L.ball_points_on(stem, f)
        t0 = time.perf_counter()
        r = m.predict(img, imgsz=imgsz, device="cpu", conf=min(conf, arrow_conf), verbose=False, retina_masks=True, max_det=30)[0]
        lat.append(time.perf_counter() - t0)
        row = {"frame": f, "ok": False, "arrows": {}}
        truth_lm = LM.truth_landmarks(stem, f, "all")
        y_top, y_bot = L.gt_y(stem, f)
        # lane: class 0, candidate holding most ball-path points
        best, best_v, best_c = None, -1, 0.0
        arrows = []
        if len(r.boxes):
            cls = r.boxes.cls.cpu().numpy().astype(int); cf = r.boxes.conf.cpu().numpy(); xyxy = r.boxes.xyxy.cpu().numpy()
            for i in range(len(cls)):
                if cls[i] == 0 and cf[i] >= conf and r.masks is not None:
                    mask = r.masks.data[i].cpu().numpy().astype(np.uint8)
                    if mask.shape != img.shape[:2]:
                        mask = cv2.resize(mask, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_NEAREST)
                    v = sum(1 for x, y in anchors if 0 <= int(y) < mask.shape[0] and 0 <= int(x) < mask.shape[1] and mask[int(y), int(x)])
                    if v > best_v or (v == best_v and cf[i] > best_c):
                        best, best_v, best_c = mask, v, float(cf[i])
                elif cls[i] == 1 and cf[i] >= arrow_conf:
                    x1, y1, x2, y2 = xyxy[i]
                    arrows.append({"x": float((x1 + x2) / 2), "y": float((y1 + y2) / 2), "conf": float(cf[i])})
        row["lane_conf"] = round(best_c, 3)
        if best is not None:
            fit = L.fit_edges(best, y_top, y_bot, anchors)
            if fit is not None:
                left, right, info = fit
                corners = L.lines_to_corners(left, right, y_top, y_bot)
                tw = corners["top_right"][0] - corners["top_left"][0]; bw = corners["bottom_right"][0] - corners["bottom_left"][0]
                if tw > 0 and bw > tw:
                    fits[f] = corners
                    row["fit_resid_px"] = info["fit_resid_px"]
        # arrows: match each detection to the nearest truth arrow (px), correct if within 1.5 boards along x
        matched = {}
        for a in arrows:
            best_b, best_d = None, 1e9
            for b in C.ARROW_BOARDS:
                tx, ty = truth_lm[f"arrow_{b}"]
                d = np.hypot(a["x"] - tx, a["y"] - ty)
                if d < best_d:
                    best_b, best_d = b, d
            tx, ty = truth_lm[f"arrow_{best_b}"]
            Ht = LM.truth_h(stem, f, "all"); wpx, _ = LM.width_centre_at(Ht, ty); ppb = wpx / 38.0
            dxb = (a["x"] - tx) / ppb
            if abs(dxb) <= 1.5 and best_d <= 3 * ppb and (best_b not in matched or a["conf"] > matched[best_b]["conf"]):
                matched[best_b] = {"x": a["x"], "y": a["y"], "conf": a["conf"], "px_err": round(float(best_d), 2), "dx_boards": round(float(dxb), 2)}
        row["arrows"] = {str(b): v for b, v in matched.items()}
        row["arrows_detected"] = len(arrows); row["arrows_correct"] = len(matched)
        det_out[str(f)] = {"frame": f, "arrows": {str(b): {"x": v["x"], "y": v["y"], "darkness": 40.0 * v["conf"], "area": 0} for b, v in matched.items()}}
        per.append(row)
    # gate + carry on the lane (loop 3's rule, simplified: width sanity + centre jump), then score
    keys = sorted(fits)
    if gate and keys:
        cw = {f: (0.5 * (fits[f]["bottom_left"][0] + fits[f]["bottom_right"][0]), fits[f]["bottom_right"][0] - fits[f]["bottom_left"][0]) for f in keys}
        ref_c = float(np.median([v[0] for v in cw.values()])); ref_w = float(np.median([v[1] for v in cw.values()]))
        acc = [f for f in keys if abs(cw[f][0] - ref_c) <= 0.3 * ref_w]
    else:
        acc = keys
    for row in per:
        f = row["frame"]
        if not acc:
            break
        g = min(acc, key=lambda q: abs(q - f))
        c = fits[g]
        if g != f:
            # carry the nearest accepted lane's edge lines, re-evaluated at this frame's annotated rows (tripod-style carry)
            yt, yb = L.gt_y(stem, f)
            (lx1, ly1), (lx2, ly2) = c["top_left"], c["bottom_left"]; (rx1, ry1), (rx2, ry2) = c["top_right"], c["bottom_right"]
            la = (lx2 - lx1) / (ly2 - ly1); lb = lx1 - la * ly1; ra = (rx2 - rx1) / (ry2 - ry1); rb = rx1 - ra * ry1
            c = L.lines_to_corners((la, lb), (ra, rb), yt, yb)
        row["ok"] = True; row["carried"] = g != f
        row["corners"] = {k: [round(float(v[0]), 2), round(float(v[1]), 2)] for k, v in c.items()}
        s = C.score_both(stem, f, c)
        for t in C.TRUTHS:
            row[f"mae_{t}"] = s[t]["board_mae"]; row[f"tail_{t}"] = s[t]["board_mae_last20"]
    throw = set(C.throw_frames(stem)); ok = [r for r in per if r["ok"]]
    fp = L.pin_hit_frame(stem) - 2; fl = L.frame_indices(stem, "last")[0]
    summ = {"frames": len(per), "lane_frames_raw": len(keys), "lane_frames_accepted": len(acc), "latency_ms_median": round(1000 * float(np.median(lat[3:])), 1)}
    for t in C.TRUTHS:
        v = [r[f"mae_{t}"] for r in ok if r["frame"] in throw]
        summ[f"throw_median_{t}"] = round(float(np.median(v)), 2) if v else None
        summ[f"tail_median_{t}"] = round(float(np.median([r[f"tail_{t}"] for r in ok if r["frame"] in throw])), 2) if v else None
        summ[f"within2_{t}"] = round(float(np.mean(np.array(v) <= 2) * 100), 1) if v else None
        for nm, ff in (("prehit", fp), ("last", fl)):
            r = next((r for r in ok if r["frame"] == ff), None); summ[f"{nm}_{t}"] = r[f"mae_{t}"] if r else None
    ac = [r["arrows_correct"] for r in per]; ad = [r["arrows_detected"] for r in per]
    px = [a["px_err"] for r in per for a in r["arrows"].values()]; dxb = [abs(a["dx_boards"]) for r in per for a in r["arrows"].values()]
    summ["arrows"] = {"correct_per_frame_mean": round(float(np.mean(ac)), 2), "detected_per_frame_mean": round(float(np.mean(ad)), 2), "false_per_frame": round(float(np.mean(np.array(ad) - np.array(ac))), 2),
                      "recall": round(float(np.sum(ac) / (7.0 * len(per))), 3), "px_err_median": round(float(np.median(px)), 2) if px else None, "dx_boards_median_abs": round(float(np.median(dxb)), 2) if dxb else None,
                      "frames_with_ge5": round(float(np.mean(np.array(ac) >= 5)), 3)}
    out = {"stem": stem, "run": run, "imgsz": imgsz, "summary": summ, "per_frame": per}
    C.dump(C.RESULTS / f"seg2_{run}__{stem}.json", out)
    PRED.mkdir(exist_ok=True); (PRED / f"lm_learned_{run}_{stem}.json").write_text(json.dumps(det_out))
    print(f"seg2 {run} {C.SHORT[stem]}: lane frames {len(acc)}/{len(per)} throw median ann/pins/all {summ['throw_median_annotated']}/{summ['throw_median_pins']}/{summ['throw_median_all']} tail(pins) {summ['tail_median_pins']} prehit {summ['prehit_pins']} last {summ['last_pins']} | arrows {summ['arrows']} | {summ['latency_ms_median']} ms", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("run"); ap.add_argument("stem"); ap.add_argument("--imgsz", type=int, default=None); ap.add_argument("--conf", type=float, default=0.1); ap.add_argument("--arrow-conf", type=float, default=0.15)
    a = ap.parse_args()
    imgsz = a.imgsz or int(a.run.split("_")[1])
    main(a.run, a.stem, imgsz, a.conf, a.arrow_conf)
