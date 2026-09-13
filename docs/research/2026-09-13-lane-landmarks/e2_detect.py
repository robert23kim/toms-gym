"""E2: landmark detectors at inference time, from a predicted lane (no annotation).

For every frame of a video that has a lane hypothesis (default: loop 3's gated
student corners rebuilt by rescore_baselines.py; --lanes <json> for another
source with per_frame[].corners): (a) pins = rack fit initialised from that lane
(frames up to the pin-hit marker), (b) arrows = classical detector on the lane
rectified through that hypothesis, (c) foul-line ends = the hypothesis' bottom
corners. Scored against the E1 truth landmarks projected into each frame
(truth_landmarks): recall, px error, boards error at the landmark's row.
Writes results/e2_detect_<src>__<stem>.json and $LM_SCRATCH/pred/lm_<src>_<stem>.json
(the detections E3 consumes). usage: e2_detect.py [--src loop3] [stems...]"""
import argparse
import json
import time

import cv2
import numpy as np

import common as C
import landmarks as LM

L = C.L
C.use_full_camera()
PRED = C.SCRATCH / "pred"


def lane_source(src, stem):
    if src.startswith("loop3"):
        d = C.load(C.RESULTS / "baselines_rescored.json")["loop3"]
        label = src.split(":", 1)[1] if ":" in src else "student seg640 gated (loop 3)"
        key = f"{label}|{stem}"
        return {r["frame"]: {k: tuple(v) for k, v in r["corners"].items()} for r in d[key]["per_frame"]}
    d = C.load(src)
    rows = d["per_frame"] if isinstance(d, dict) else d
    return {r["frame"]: {k: tuple(v) for k, v in r["corners"].items()} for r in rows if r.get("corners")}


def px_per_board_at(stem, f, y):
    t = C.truth_corners(stem, f, "all")
    H = LM.h_from_quad(t)
    w, _ = LM.width_centre_at(H, y)
    return w / 38.0


def run(stem, src, tag, frames=None, overlay_frames=()):
    lanes = lane_source(src, stem)
    frames = frames or sorted(lanes)
    ph = L.pin_hit_frame(stem)
    per, det_out = [], {}
    t_pins, t_arr = [], []
    for f in frames:
        q = lanes.get(f)
        if q is None:
            continue
        img = C.read_frame(stem, f)
        H0 = LM.h_from_quad(q)
        truth = LM.truth_landmarks(stem, f, "all")
        row = {"frame": f, "pins": None, "arrows": {}}
        det = {"frame": f, "foul": {"left": list(q["bottom_left"]), "right": list(q["bottom_right"])}, "arrows": {}, "pins": None, "lane_corners": {k: list(v) for k, v in q.items()}}
        # pins (standing): rack fit from the hypothesis
        if f <= ph - 1:
            t0 = time.perf_counter()
            w_px = q["top_right"][0] - q["top_left"][0]
            try:
                pts, sc, params, score, contrast, parts = LM.fit_rack(img, H0, max(w_px, 10), coarse=True)
                for _ in range(2):
                    pts = LM.refine_pin_columns(img, pts, sc)
                t_pins.append(time.perf_counter() - t0)
                errs = {}
                for k in range(1, 11):
                    tx, ty = truth[f"pin_{k}_base"]
                    errs[str(k)] = round(float(np.hypot(pts[k - 1][0] - tx, pts[k - 1][1] - ty)), 2)
                ppb = px_per_board_at(stem, f, float(np.mean([pts[6][1], pts[9][1]])))
                c_det = 0.5 * (pts[6][0] + pts[9][0]); c_true = 0.5 * (truth["pin_7_base"][0] + truth["pin_10_base"][0])
                w_det = pts[9][0] - pts[6][0]; w_true = truth["pin_10_base"][0] - truth["pin_7_base"][0]
                row["pins"] = {"contrast_sigma": round(contrast, 1), "score": round(score, 3), "px_err": errs, "px_err_mean": round(float(np.mean(list(errs.values()))), 2),
                               "centre_err_px": round(float(c_det - c_true), 2), "centre_err_boards": round(float((c_det - c_true) / ppb), 2),
                               "span_err_px": round(float(w_det - w_true), 2), "span_err_boards": round(float((w_det - w_true) / ppb * LM.W_IN / 36), 2),
                               "alias_margin": parts.get("alias_margin"),
                               "ok": bool(contrast >= 2.5 and score > 0.2 and (parts.get("alias_margin") is None or parts["alias_margin"] > 0.02))}
                det["pins"] = {"bases": {str(k): [float(pts[k - 1][0]), float(pts[k - 1][1])] for k in range(1, 11)}, "contrast_sigma": float(contrast), "score": float(score), "alias_margin": parts.get("alias_margin"), "ok": row["pins"]["ok"]}
            except Exception as e:  # noqa: BLE001
                row["pins"] = {"ok": False, "error": str(e)[:100]}
        # arrows from the hypothesis-rectified lane
        t0 = time.perf_counter()
        try:
            arrows, _ = LM.detect_arrows(img, H0)
        except Exception as e:  # noqa: BLE001
            arrows = {}
        t_arr.append(time.perf_counter() - t0)
        for b, v in arrows.items():
            tx, ty = truth[f"arrow_{b}"]
            ppb = px_per_board_at(stem, f, ty)
            row["arrows"][str(b)] = {"px_err": round(float(np.hypot(v["x"] - tx, v["y"] - ty)), 2), "dx_boards": round(float((v["x"] - tx) / ppb), 2), "darkness": v["darkness"]}
            det["arrows"][str(b)] = {"x": v["x"], "y": v["y"], "darkness": v["darkness"], "area": v["area"]}
        row["arrows_found"] = len(arrows)
        row["arrows_correct"] = int(sum(1 for a in row["arrows"].values() if abs(a["dx_boards"]) <= 1.5))
        per.append(row); det_out[str(f)] = det
        if f in overlay_frames:
            ov = img.copy()
            for k, (tx, ty) in truth.items():
                cv2.circle(ov, (int(tx), int(ty)), 4, (0, 220, 0), 1, cv2.LINE_AA)
            for b, v in arrows.items():
                cv2.drawMarker(ov, (int(v["x"]), int(v["y"])), (255, 0, 255), cv2.MARKER_TRIANGLE_UP, 12, 2, cv2.LINE_AA)
            if det["pins"]:
                for k, (x, y) in det["pins"]["bases"].items():
                    cv2.circle(ov, (int(x), int(y)), 3, (0, 0, 255), -1, cv2.LINE_AA)
            p = np.array([q["top_left"], q["top_right"], q["bottom_right"], q["bottom_left"]], np.int32); cv2.polylines(ov, [p], True, (0, 200, 255), 1, cv2.LINE_AA)
            cv2.putText(ov, f"E2 {src} {C.SHORT[stem]} f{f}: truth landmarks green, detected arrows magenta, pins red, lane hypothesis orange", (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
            cv2.imwrite(str(C.OVERLAYS / f"e2_{tag}_{stem}_f{f}.jpg"), ov, [cv2.IMWRITE_JPEG_QUALITY, 88])
    # summaries
    pin_rows = [r for r in per if r["pins"] and r["pins"].get("ok")]
    pin_all = [r for r in per if r["pins"] is not None]
    arr_found = [r["arrows_found"] for r in per]; arr_ok = [r["arrows_correct"] for r in per]
    arr_dx = [a["dx_boards"] for r in per for a in r["arrows"].values() if abs(a["dx_boards"]) <= 1.5]
    arr_px = [a["px_err"] for r in per for a in r["arrows"].values() if abs(a["dx_boards"]) <= 1.5]
    summ = {"frames": len(per),
            "pins": {"frames_standing": len(pin_all), "fired": len(pin_rows), "recall": round(len(pin_rows) / max(1, len(pin_all)), 3),
                     "px_err_mean_median": round(float(np.median([r["pins"]["px_err_mean"] for r in pin_rows])), 2) if pin_rows else None,
                     "centre_err_boards_median_abs": round(float(np.median([abs(r["pins"]["centre_err_boards"]) for r in pin_rows])), 2) if pin_rows else None,
                     "span_err_boards_median_abs": round(float(np.median([abs(r["pins"]["span_err_boards"]) for r in pin_rows])), 2) if pin_rows else None,
                     "ms": round(1000 * float(np.median(t_pins)), 0) if t_pins else None},
            "arrows": {"found_per_frame_mean": round(float(np.mean(arr_found)), 2), "correct_per_frame_mean": round(float(np.mean(arr_ok)), 2),
                       "recall_within_1.5_boards": round(float(np.sum(arr_ok) / (7.0 * len(per))), 3), "false_per_frame": round(float(np.mean(np.array(arr_found) - np.array(arr_ok))), 2),
                       "dx_boards_median_abs": round(float(np.median(np.abs(arr_dx))), 2) if arr_dx else None, "px_err_median": round(float(np.median(arr_px)), 2) if arr_px else None,
                       "frames_with_ge5_correct": round(float(np.mean(np.array(arr_ok) >= 5)), 3), "ms": round(1000 * float(np.median(t_arr)), 0) if t_arr else None}}
    out = {"stem": stem, "source": src, "summary": summ, "per_frame": per}
    C.dump(C.RESULTS / f"e2_detect_{tag}__{stem}.json", out)
    PRED.mkdir(exist_ok=True)
    (PRED / f"lm_{tag}_{stem}.json").write_text(json.dumps(det_out))
    print(f"E2 {tag} {C.SHORT[stem]:13s} frames {len(per)} | pins fired {len(pin_rows)}/{len(pin_all)} px {summ['pins']['px_err_mean_median']} centre {summ['pins']['centre_err_boards_median_abs']} bd span {summ['pins']['span_err_boards_median_abs']} bd {summ['pins']['ms']} ms | "
          f"arrows {summ['arrows']['correct_per_frame_mean']}/7 correct ({summ['arrows']['false_per_frame']} false) recall {summ['arrows']['recall_within_1.5_boards']} dx {summ['arrows']['dx_boards_median_abs']} bd {summ['arrows']['ms']} ms", flush=True)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--src", default="loop3"); ap.add_argument("--tag", default=None); ap.add_argument("stems", nargs="*")
    a = ap.parse_args()
    tag = a.tag or ("loop3" if a.src == "loop3" else "custom")
    for stem in a.stems or C.STEMS:
        fp = C.frame_for(stem, "prehit"); occ = C.occluded_frames(stem)
        run(stem, a.src, tag, overlay_frames=(fp, occ[len(occ) // 2], L.frame_indices(stem, "mid")[0]))
