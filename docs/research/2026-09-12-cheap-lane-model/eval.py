"""Score a trained student on every frame of a video with the loop-1 metric.

usage: eval.py <run_name> [stems...] [--imgsz N] [--device cpu|mps] [--conf 0.1] [--tag T]
run_name is a folder under $LANE_SCRATCH/runs (weights/best.pt inside).

Per frame: the student's mask (seg) or 4 keypoints (pose) -> the two edge lines
-> corners at the annotated top/bottom y -> board MAE against the per-frame
truth over the annotated ball path. Writes results/<run><tag>__<stem>.json in
the loop-1 row schema (+ per_frame, clean / occluded / whole-video summaries,
CPU latency) and $LANE_SCRATCH/pred/<run><tag>_<stem>.npz|json for the review
video. Unlabeled stems get lines + confidence only.
"""
import argparse
import json
import os
import time
from pathlib import Path

import cv2
import numpy as np
import torch

import common as C

os.environ.setdefault("YOLO_CONFIG_DIR", str(C.SCRATCH / "yolo_cfg"))
from ultralytics import YOLO  # noqa: E402

L = C.L
C.use_full_camera()
PRED = C.SCRATCH / "pred"
KP = ("top_left", "top_right", "bottom_left", "bottom_right")


def load(run):
    p = C.SCRATCH / "runs" / run / "weights" / "best.pt"
    m = YOLO(str(p))
    return m, p


def candidates(m, img, imgsz, device, conf):
    """Every detection above conf: [(mask_or_quad, conf)], highest conf first."""
    r = m.predict(img, imgsz=imgsz, device=device, conf=conf, verbose=False, retina_masks=True, max_det=5)[0]
    out = []
    if len(r.boxes) == 0:
        return out
    order = torch.argsort(r.boxes.conf, descending=True).tolist()
    for i in order:
        c = float(r.boxes.conf[i])
        if m.task == "segment":
            if r.masks is None:
                continue
            mask = r.masks.data[i].cpu().numpy().astype(np.uint8)
            if mask.shape != img.shape[:2]:
                mask = cv2.resize(mask, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_NEAREST)
            out.append((mask, c))
        else:
            xy = r.keypoints.xy[i].cpu().numpy()
            out.append(({k: (float(xy[j][0]), float(xy[j][1])) for j, k in enumerate(KP)}, c))
    return out


def inside_quad(q, pts):
    poly = np.array([q["top_left"], q["top_right"], q["bottom_right"], q["bottom_left"]], np.float32)
    return sum(1 for x, y in pts if cv2.pointPolygonTest(poly, (float(x), float(y)), False) >= 0)


def select(cands, task, anchors):
    """Pick the candidate holding the most anchor points (the ball path); ties and
    no-anchor cases fall back to confidence. Returns (pred, conf, votes)."""
    if not cands:
        return None, 0.0, 0
    if not anchors:
        return cands[0][0], cands[0][1], 0
    best, best_v = None, -1
    for pred, c in cands:
        if task == "segment":
            h, w = pred.shape
            v = sum(1 for x, y in anchors if 0 <= int(y) < h and 0 <= int(x) < w and pred[int(y), int(x)])
        else:
            v = inside_quad(pred, anchors)
        if v > best_v:
            best, best_v = (pred, c), v
    if best_v == 0:
        return cands[0][0], cands[0][1], 0
    return best[0], best[1], best_v


def infer(m, img, imgsz, device, conf, anchors=None):
    pred, c, _ = select(candidates(m, img, imgsz, device, conf), m.task, anchors)
    return pred, c


def lines_from_pred(stem, f, pred, task, labeled):
    """(corners, (left, right), info) using the annotated y band when labeled,
    else the prediction's own y extent."""
    if pred is None:
        return None
    if task == "segment":
        if labeled:
            y_top, y_bot = L.gt_y(stem, f)
            anchors = L.ball_points_on(stem, f)
        else:
            ys = np.where(pred.any(1))[0]
            if len(ys) < 20:
                return None
            y_top, y_bot = int(ys.min()) + 2, int(ys.max()) - 2
            anchors = None
        fit = L.fit_edges(pred, y_top, y_bot, anchors)
        if fit is None:
            return None
        left, right, info = fit
        return L.lines_to_corners(left, right, y_top, y_bot), (left, right), info
    if labeled:
        y_top, y_bot = L.gt_y(stem, f)
    else:
        y_top = (pred["top_left"][1] + pred["top_right"][1]) / 2
        y_bot = (pred["bottom_left"][1] + pred["bottom_right"][1]) / 2
    (lx1, ly1), (lx2, ly2) = pred["top_left"], pred["bottom_left"]
    (rx1, ry1), (rx2, ry2) = pred["top_right"], pred["bottom_right"]
    if abs(ly2 - ly1) < 1 or abs(ry2 - ry1) < 1:
        return None
    la = (lx2 - lx1) / (ly2 - ly1); lb = lx1 - la * ly1
    ra = (rx2 - rx1) / (ry2 - ry1); rb = rx1 - ra * ry1
    return L.lines_to_corners((la, lb), (ra, rb), y_top, y_bot), ((la, lb), (ra, rb)), {"fit_resid_px": 0.0}


def detected_ball_path(stem):
    p = PRED / f"ball_{stem}.json"
    if not p.exists():
        return []
    d = json.loads(p.read_text())
    fs = sorted(int(k) for k, v in d.items() if v)
    runs, cur = [], []
    for f in fs:
        if cur and f - cur[-1] > 3:
            runs.append(cur); cur = []
        cur.append(f)
    if cur:
        runs.append(cur)
    run = max(runs, key=len) if runs else []
    return [(d[str(f)][0]["x"], d[str(f)][0]["y"]) for f in run] if len(run) >= 20 else []


def run_stem(m, run, stem, imgsz, device, conf, tag, frames=None, select_mode="anchor"):
    labeled = stem in C.STEMS
    task = m.task
    frames = frames or C.frame_ids(stem)
    per, masks, lines, lat = [], {}, {}, []
    static_anchors = detected_ball_path(stem) if (select_mode == "anchor" and not labeled) else []
    for f in frames:
        img = C.read_frame(stem, f)
        anchors = (L.ball_points_on(stem, f) if labeled else static_anchors) if select_mode == "anchor" else None
        t0 = time.perf_counter()
        pred, score = infer(m, img, imgsz, device, conf, anchors)
        lat.append(time.perf_counter() - t0)
        got = lines_from_pred(stem, f, pred, task, labeled)
        row = {"frame": f, "conf": round(score, 3), "ok": got is not None}
        if got is not None:
            corners, (left, right), info = got
            lines[str(f)] = {"left": [float(left[0]), float(left[1])], "right": [float(right[0]), float(right[1])],
                             "corners": {k: [round(float(v[0]), 1), round(float(v[1]), 1)] for k, v in corners.items()}}
            row["fit_resid_px"] = info.get("fit_resid_px")
            if labeled:
                row.update(L.score(stem, corners, f))
        if task == "segment" and pred is not None:
            masks[str(f)] = np.packbits(pred.astype(bool))
        if task == "pose" and pred is not None:
            row["kpts"] = {k: [round(v[0], 1), round(v[1], 1)] for k, v in pred.items()}
        per.append(row)
    PRED.mkdir(exist_ok=True)
    if masks:
        np.savez_compressed(PRED / f"masks_{run}{tag}_{stem}.npz", shape=np.array(C.read_frame(stem, frames[0]).shape[:2]), **masks)
    (PRED / f"lines_{run}{tag}_{stem}.json").write_text(json.dumps(lines))
    lat = np.array(lat[3:]) if len(lat) > 5 else np.array(lat)  # drop warm-up
    out = {"stem": stem, "method": run + tag, "task": task, "imgsz": imgsz, "device": device, "select": select_mode, "weights": str(C.SCRATCH / "runs" / run / "weights" / "best.pt"),
           "frames_total": len(frames), "frames_ok": int(sum(r["ok"] for r in per)),
           "latency_ms_mean": round(float(lat.mean() * 1000), 1), "latency_ms_median": round(float(np.median(lat) * 1000), 1),
           "per_frame": per}
    if labeled:
        throw = set(C.throw_frames(stem)); clean = set(C.clean_frames(stem)); occ = set(C.occluded_frames(stem))
        sel = lambda S: [r for r in per if r["frame"] in S]  # noqa: E731
        out["throw"] = C.summarize(sel(throw)); out["clean"] = C.summarize(sel(clean)); out["occluded"] = C.summarize(sel(occ))
        out["all_frames"] = C.summarize(per)
        f_last = L.frame_indices(stem, "last")[0]; f_pre = L.pin_hit_frame(stem) - 2
        for name, ff in (("last", f_last), ("prehit", f_pre)):
            r = next((r for r in per if r["frame"] == ff), None)
            out[name] = {"frame": ff, "board_mae": r.get("board_mae") if r else None, "corner_err_mean_px": r.get("corner_err_mean_px") if r else None}
        # loop-1 schema top-level = the last frame row
        r = next((r for r in per if r["frame"] == f_last), None)
        if r and r.get("ok"):
            for k in ("board_mae", "board_max", "within_1", "within_2", "corner_err_px", "corner_err_mean_px", "top_width_true_px", "top_width_pred_px", "bottom_width_true_px", "bottom_width_pred_px"):
                out[k] = r.get(k)
        out["frame"] = f_last; out["ok"] = bool(r and r.get("ok"))
        out["perframe_mae_mean"] = out["throw"]["mean"]; out["perframe_mae_median"] = out["throw"]["median"]; out["perframe_within_2"] = out["throw"]["within_2"]
    C.dump(C.RESULTS / f"{run}{tag}__{stem}.json", out)
    return out


def overlays(run, stem, tag, kinds=("occluded", "prehit", "last")):
    """Overlay jpgs for a few frames: truth green, prediction red, mask tint."""
    lines = json.loads((PRED / f"lines_{run}{tag}_{stem}.json").read_text())
    mp = PRED / f"masks_{run}{tag}_{stem}.npz"
    mz = np.load(mp) if mp.exists() else None
    res = json.loads((C.RESULTS / f"{run}{tag}__{stem}.json").read_text())
    for kind in kinds:
        if kind == "occluded":
            f = C.occluded_frames(stem)[len(C.occluded_frames(stem)) // 2] if stem in C.STEMS else C.frame_ids(stem)[len(C.frame_ids(stem)) // 3]
        elif kind == "prehit":
            f = L.pin_hit_frame(stem) - 2 if stem in C.STEMS else C.frame_ids(stem)[int(len(C.frame_ids(stem)) * 0.75)]
        else:
            f = L.frame_indices(stem, "last")[0] if stem in C.STEMS else C.frame_ids(stem)[-1]
        ln = lines.get(str(f))
        corners = {k: tuple(v) for k, v in ln["corners"].items()} if ln else None
        mask = None
        if mz is not None and str(f) in mz.files:
            mask = np.unpackbits(mz[str(f)])[: int(np.prod(mz["shape"]))].reshape(tuple(mz["shape"])).astype(np.uint8)
        row = next((r for r in res["per_frame"] if r["frame"] == f), {})
        cap = f"{run}{tag} {C.SHORT[stem]} f{f} ({kind})  board MAE {row.get('board_mae')}  conf {row.get('conf')}"
        if stem in C.STEMS:
            img = L.draw_overlay(stem, f, mask, corners, {}, cap)
        else:
            img = C.read_frame(stem, f)
            if mask is not None:
                mb = mask.astype(bool); img[mb] = (0.45 * img[mb] + np.array([150, 60, 0])).clip(0, 255).astype(np.uint8)
            if corners is not None:
                p = np.array([corners["top_left"], corners["top_right"], corners["bottom_right"], corners["bottom_left"]], np.int32)
                cv2.polylines(img, [p], True, (0, 0, 255), 2, cv2.LINE_AA)
            tl = PRED / f"lines_teacher_{stem}.json"
            if tl.exists():
                d = json.loads(tl.read_text()); ks = sorted(int(k) for k in d)
                near = min(ks, key=lambda q: abs(q - f)) if ks else None
                if near is not None and abs(near - f) <= 4:
                    c = d[str(near)]["corners"]
                    p = np.array([c["top_left"], c["top_right"], c["bottom_right"], c["bottom_left"]], np.int32)
                    cv2.polylines(img, [p], True, (255, 160, 0), 2, cv2.LINE_AA)
            cv2.putText(img, cap, (12, img.shape[0] - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4, cv2.LINE_AA)
            cv2.putText(img, cap, (12, img.shape[0] - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.imwrite(str(C.OVERLAYS / f"{run}{tag}_{kind}_{stem}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 85])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("run"); ap.add_argument("stems", nargs="*")
    ap.add_argument("--imgsz", type=int, default=None); ap.add_argument("--device", default="cpu")
    ap.add_argument("--conf", type=float, default=0.1); ap.add_argument("--tag", default="")
    ap.add_argument("--no-overlays", action="store_true")
    ap.add_argument("--select", default="anchor", choices=["anchor", "conf"], help="anchor: candidate holding most ball-path points (default); conf: top confidence")
    a = ap.parse_args()
    m, p = load(a.run)
    imgsz = a.imgsz or int(a.run.split("_")[0].lstrip("segpose") or 640)
    stems = a.stems or C.STEMS
    for stem in stems:
        t0 = time.time()
        out = run_stem(m, a.run, stem, imgsz, a.device, a.conf, a.tag, select_mode=a.select)
        s = out.get("throw"); c = out.get("clean"); o = out.get("occluded")
        print(f"{a.run}{a.tag} {C.SHORT[stem]:13s} ok {out['frames_ok']}/{out['frames_total']}  "
              + (f"throw mean/med {s['mean']}/{s['median']}  clean {c['mean']}/{c['median']}  occluded {o['mean']}/{o['median']}  last {out['last']['board_mae']}  prehit {out['prehit']['board_mae']}  " if s else "")
              + f"lat {out['latency_ms_median']} ms  ({time.time() - t0:.0f}s)")
        if not a.no_overlays:
            overlays(a.run, stem, a.tag)
