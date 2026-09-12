"""Run SAM 2 lane-edge prompting methods against the three annotated videos.

usage: run_methods.py [--methods a,b,c] [--weights sam2.1_b.pt] [--tag _t] [--list]

Each method writes one row per video to results/<method>.json and one overlay
per video to overlays/<method>_<stem>.jpg. Rows carry the board metric from
lane_sam.score plus the prompts used, so the README and the review video are
built from the JSON alone. Per-frame methods also dump every frame's mask to
the scratchpad (masks_<method>_<stem>.npz) for the review video.

Truth is per frame (lane_sam.truth_corners): two of the three videos are
handheld, so a mask on frame f is scored against the lane on frame f, and
multi-frame combinations warp each frame's result into the target frame first.

Frame kinds: pre = 5 frames before the first ball frame, mid = middle of the
throw, last = last ball frame, span = k frames from pre to last.
"""
import argparse
import json
import time
from pathlib import Path

import cv2
import numpy as np

import gt
import lane_sam as L

METHODS = {}
SCRATCH = Path("/private/tmp/claude-502/-Users-toka-code-toms-gym/b090792b-0a7d-4249-9e93-4543c8a2bc1f/scratchpad")


def method(name, desc):
    def deco(fn):
        METHODS[name] = (fn, desc)
        return fn
    return deco


def _finish(stem, frame, mask, lines, prompts, quality, t0, extra=None):
    y_top, y_bot = L.gt_y(stem, frame)
    row = {"stem": stem, "frame": frame, "latency_s": round(time.time() - t0, 2), "prompts": prompts}
    if lines is None:
        row["ok"] = False
        row.update(extra or {})
        return row, None
    corners = L.lines_to_corners(lines[0], lines[1], y_top, y_bot)
    row.update(L.score(stem, corners, frame))
    row.update(quality or {})
    row.update(extra or {})
    row["ok"] = True
    row["corners"] = {k: [round(v[0], 1), round(v[1], 1)] for k, v in corners.items()}
    return row, corners


def _single(stem, frame, prompts, weights):
    img = cv2.imread(str(gt.frame_path(stem, frame)))
    m = L.model(weights)
    mask = L.predict_mask(m, img, prompts.get("points"), prompts.get("labels"), prompts.get("bboxes"))
    y_top, y_bot = L.gt_y(stem, frame)
    fit = L.fit_edges(mask, y_top, y_bot, _pos(prompts)) if mask is not None else None
    if fit is None:
        return mask, None, None
    return mask, (fit[0], fit[1]), fit[2]


def _pos(prompts):
    """Positive prompt points, used to pick the mask component."""
    pts = prompts.get("points") or []
    labs = prompts.get("labels") or [1] * len(pts)
    return [p for p, l in zip(pts, labs) if l == 1]


def _one(stem, f, prompts, weights, t0=None):
    t0 = t0 or time.time()
    mask, lines, q = _single(stem, f, prompts, weights)
    return [_finish(stem, f, mask, lines, prompts, q, t0) + (mask,)]


def _mae(stem, lines, f):
    if lines is None:
        return None
    y_top, y_bot = L.gt_y(stem, f)
    return L.score(stem, L.lines_to_corners(lines[0], lines[1], y_top, y_bot), f)["board_mae"]


# ------------------------------------------------------------- Feb 2026 prompts

@method("generic_box", "Feb-2026 engine prompt: fixed box over the middle of the frame, no scene knowledge")
def generic_box(stem, weights):
    f = L.frame_indices(stem, "last")[0]
    h, w = cv2.imread(str(gt.frame_path(stem, f))).shape[:2]
    return _one(stem, f, {"bboxes": [[int(w * 0.25), int(h * 0.10), int(w * 0.75), int(h * 0.85)]]}, weights)


@method("center3", "Feb-2026 fallback prompt: three points down the frame centre line")
def center3(stem, weights):
    f = L.frame_indices(stem, "last")[0]
    h, w = cv2.imread(str(gt.frame_path(stem, f))).shape[:2]
    pts = [[w // 2, int(h * 0.30)], [w // 2, int(h * 0.50)], [w // 2, int(h * 0.70)]]
    return _one(stem, f, {"points": pts, "labels": [1, 1, 1]}, weights)


# ------------------------------------------------------------- single-frame trajectory prompts

def _track_prompts(stem, f, n=5):
    pts = L.track_points(stem, f, n=n)
    return {"points": pts, "labels": [1] * len(pts)}


for _fk in ("pre", "mid", "last"):
    def _mk(fk):
        @method(f"track_{fk}", f"5 positive points along the ball path, {fk} frame")
        def fn(stem, weights):
            f = L.frame_indices(stem, fk)[0]
            return _one(stem, f, _track_prompts(stem, f), weights)
        return fn
    _mk(_fk)


@method("track1_last", "A single positive point on the ball path (the 2026-09-12 report's prompt), last frame")
def track1_last(stem, weights):
    f = L.frame_indices(stem, "last")[0]
    return _one(stem, f, _track_prompts(stem, f, n=1), weights)


@method("track9_last", "9 positive points along the ball path, last frame")
def track9_last(stem, weights):
    f = L.frame_indices(stem, "last")[0]
    return _one(stem, f, _track_prompts(stem, f, n=9), weights)


def _even_prompts(stem, f, n=5):
    pts = L.track_points_even(stem, f, n=n)
    return {"points": pts, "labels": [1] * len(pts)}


@method("even_last", "5 points spaced evenly along the path's image length (15-85%), last frame")
def even_last(stem, weights):
    f = L.frame_indices(stem, "last")[0]
    return _one(stem, f, _even_prompts(stem, f), weights)


@method("even3_last", "3 evenly spaced path points, last frame")
def even3_last(stem, weights):
    f = L.frame_indices(stem, "last")[0]
    return _one(stem, f, _even_prompts(stem, f, n=3), weights)


@method("even_neg_last", "Evenly spaced path points plus negatives half a lane-width outside the first mask, last frame")
def even_neg_last(stem, weights):
    f = L.frame_indices(stem, "last")[0]
    t0 = time.time()
    p = _even_prompts(stem, f)
    neg = _lane_neg(stem, f, weights, p)
    p = {"points": p["points"] + neg, "labels": p["labels"] + [0] * len(neg)}
    return _one(stem, f, p, weights, t0)


@method("even_person_last", "Evenly spaced path points plus negatives on detected people, last frame")
def even_person_last(stem, weights):
    f = L.frame_indices(stem, "last")[0]
    t0 = time.time()
    img = cv2.imread(str(gt.frame_path(stem, f)))
    neg = L.person_negatives(L.person_boxes(img))
    p = _even_prompts(stem, f)
    p = {"points": p["points"] + neg, "labels": p["labels"] + [0] * len(neg)}
    return _one(stem, f, p, weights, t0)


@method("track_box_last", "Path points plus a loose box around the path (x +-25% of frame width), last frame")
def track_box_last(stem, weights):
    f = L.frame_indices(stem, "last")[0]
    h, w = cv2.imread(str(gt.frame_path(stem, f))).shape[:2]
    pts = L.ball_points_on(stem, f)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    box = [int(max(0, min(xs) - 0.25 * w)), int(max(0, min(ys) - 0.03 * h)),
           int(min(w - 1, max(xs) + 0.25 * w)), int(min(h - 1, max(ys) + 0.05 * h))]
    p = _track_prompts(stem, f)
    p["bboxes"] = [box]
    return _one(stem, f, p, weights)


def _lane_neg(stem, f, weights, prompts):
    """Second-pass negatives half a lane-width outside the first mask's fitted edges."""
    h, w = cv2.imread(str(gt.frame_path(stem, f))).shape[:2]
    _, lines1, _ = _single(stem, f, prompts, weights)
    if lines1 is None:
        return []
    y_top, y_bot = L.gt_y(stem, f)
    (la, lb), (ra, rb) = lines1
    neg = []
    for y in np.linspace(y_top + 0.15 * (y_bot - y_top), y_bot - 0.05 * (y_bot - y_top), 3):
        width = (ra * y + rb) - (la * y + lb)
        off = max(12.0, 0.5 * width)
        for x in (la * y + lb - off, ra * y + rb + off):
            if 0 <= x < w:
                neg.append([int(x), int(y)])
    return neg


@method("lane_neg_last", "Two passes: path points, then negatives half a lane-width outside the first mask, last frame")
def lane_neg_last(stem, weights):
    f = L.frame_indices(stem, "last")[0]
    t0 = time.time()
    p = _track_prompts(stem, f)
    neg = _lane_neg(stem, f, weights, p)
    p = {"points": p["points"] + neg, "labels": p["labels"] + [0] * len(neg)}
    return _one(stem, f, p, weights, t0)


def _person_prompts(stem, f):
    img = cv2.imread(str(gt.frame_path(stem, f)))
    boxes = L.person_boxes(img)
    neg = L.person_negatives(boxes)
    p = _track_prompts(stem, f)
    return {"points": p["points"] + neg, "labels": p["labels"] + [0] * len(neg), "person_boxes": boxes}


for _fk in ("mid", "last"):
    def _mk(fk):
        @method(f"person_neg_{fk}", f"Path points plus negative points on every YOLO-detected person, {fk} frame")
        def fn(stem, weights):
            f = L.frame_indices(stem, fk)[0]
            t0 = time.time()
            return _one(stem, f, _person_prompts(stem, f), weights, t0)
        return fn
    _mk(_fk)


# ------------------------------------------------------------- candidate masks

def _multimask_rows(stem, weights, pick, fk="last"):
    f = L.frame_indices(stem, fk)[0]
    img = cv2.imread(str(gt.frame_path(stem, f)))
    pts = L.track_points(stem, f)
    prompts = {"points": pts, "labels": [1] * len(pts)}
    t0 = time.time()
    masks, scores = L.predict_multimask(L.model(weights), img, pts)
    y_top, y_bot = L.gt_y(stem, f)
    cands = []
    for i, (mk, sc) in enumerate(zip(masks, scores)):
        fit = L.fit_edges(mk, y_top, y_bot, pts)
        area = float(mk.sum())
        if fit is None:
            cands.append({"i": i, "sam_score": sc, "area": area, "fit": None})
            continue
        inside = float(np.mean([mk[int(y), int(x)] > 0 for x, y in pts])) if pts else 0.0
        geo = fit[2]["row_coverage"] * inside / (1.0 + fit[2]["fit_resid_px"])
        cands.append({"i": i, "sam_score": sc, "area": area, "fit": fit, "geo": geo,
                      "resid": fit[2]["fit_resid_px"], "coverage": fit[2]["row_coverage"], "inside": inside,
                      "board_mae": _mae(stem, (fit[0], fit[1]), f)})
    valid = [c for c in cands if c["fit"] is not None]
    if not valid:
        return [_finish(stem, f, None, None, prompts, None, t0) + (None,)]
    best = max(valid, key=(lambda c: c["sam_score"]) if pick == "sam" else (lambda c: c["geo"]))
    fit = best["fit"]
    extra = {"candidates": [{k: (round(v, 3) if isinstance(v, float) else v) for k, v in c.items() if k != "fit"}
                            for c in cands], "picked": best["i"]}
    return [_finish(stem, f, masks[best["i"]], (fit[0], fit[1]), prompts, fit[2], t0, extra) + (masks[best["i"]],)]


@method("multimask_sam_last", "3 candidate masks from the path points; keep the one SAM scores highest")
def multimask_sam(stem, weights):
    return _multimask_rows(stem, weights, "sam")


@method("multimask_geo_last", "3 candidate masks; keep the straightest full-height one containing the path")
def multimask_geo(stem, weights):
    return _multimask_rows(stem, weights, "geo")


# ------------------------------------------------------------- multi-frame

def _frames_masks(stem, weights, frames, person_neg=False, even=False):
    out = []
    for f in frames:
        p = _person_prompts(stem, f) if person_neg else (_even_prompts(stem, f) if even else _track_prompts(stem, f))
        mask, lines, q = _single(stem, f, p, weights)
        out.append({"frame": f, "prompts": p, "mask": mask, "lines": lines,
                    "board_mae": _mae(stem, lines, f), "fit_resid_px": (q or {}).get("fit_resid_px")})
    return out


def _combine(stem, items, how, snap=False, t0=None, target=None):
    """Combine per-frame results into one lane on the target frame (default:
    the last one). Lines and masks are warped through the camera model first."""
    last = items[-1]
    target = last["frame"] if target is None else target
    y_top, y_bot = L.gt_y(stem, target)
    per_frame = [{k: it[k] for k in ("frame", "board_mae", "fit_resid_px")} for it in items]
    extra = {"frames": [it["frame"] for it in items], "per_frame": per_frame, "combine": how,
             "frames_ok": sum(1 for it in items if it["lines"] is not None)}
    fits = []
    for it in items:
        if it["lines"] is None:
            continue
        T = L.transform(stem, it["frame"], target)
        yt, yb = L.gt_y(stem, it["frame"])
        fits.append((L.warp_line(T, it["lines"][0], yt, yb), L.warp_line(T, it["lines"][1], yt, yb)))
    prompts = last["prompts"]
    mask = last["mask"]
    if how == "vote":
        ms = [L.warp_mask(L.transform(stem, it["frame"], target), it["mask"]) for it in items if it["mask"] is not None]
        if not ms:
            return [_finish(stem, target, None, None, prompts, None, t0, extra) + (None,)]
        mask = L.vote_masks(ms)
        fit = L.fit_edges(mask, y_top, y_bot, _pos(prompts))
        if fit is None:
            return [_finish(stem, target, mask, None, prompts, None, t0, extra) + (mask,)]
        left, right = fit[0], fit[1]
        extra.update(fit[2])
    else:
        if not fits:
            return [_finish(stem, target, mask, None, prompts, None, t0, extra) + (mask,)]
        if how == "median":
            left, right = L.median_lines(fits)
        elif how == "outer":
            left, right = L.outermost_lines(fits, y_top, y_bot)
        else:
            raise ValueError(how)
    if snap:
        img = cv2.imread(str(gt.frame_path(stem, target)))
        left, right = L.snap_edges(img, left, right, y_top, y_bot)
    return [_finish(stem, target, mask, (left, right), prompts, None, t0, extra) + (mask,)]


def _multi(name, desc, kind, k, how, snap=False, person_neg=False, even=False):
    @method(name, desc)
    def fn(stem, weights):
        t0 = time.time()
        items = _frames_masks(stem, weights, L.frame_indices(stem, kind, k), person_neg=person_neg, even=even)
        return _combine(stem, items, how, snap=snap, t0=t0)
    return fn


_multi("median3_span", "Path points on 3 frames spread pre..last, median of the (camera-warped) edge lines", "span", 3, "median")
_multi("median5_span", "Path points on 5 frames spread pre..last, median of the edge lines", "span", 5, "median")
_multi("median9_span", "Path points on 9 frames spread pre..last, median of the edge lines", "span", 9, "median")
_multi("median5_late", "Path points on 5 frames in the last 30% of the throw, median of edge lines", "late", 5, "median")
_multi("outer5_span", "5 frames pre..last, outermost left/right edge across frames (occlusion only narrows)", "span", 5, "outer")
_multi("outer9_span", "9 frames pre..last, outermost edges", "span", 9, "outer")
_multi("vote5_span", "5 frames pre..last, pixel-wise majority vote of warped masks, then one edge fit", "span", 5, "vote")
_multi("vote9_span", "9 frames pre..last, pixel-wise majority vote of warped masks, then one edge fit", "span", 9, "vote")
_multi("vote9_person_span", "vote9_span with negative points on detected people in every frame", "span", 9, "vote", person_neg=True)
_multi("vote5_even_span", "vote5_span with evenly spaced path points", "span", 5, "vote", even=True)
_multi("median5_span_snap", "median5_span, then snap each edge line to the strongest gradient within +-6 px", "span", 5, "median", snap=True)
_multi("vote9_span_snap", "vote9_span, then gradient snap", "span", 9, "vote", snap=True)


# ------------------------------------------------------------- per-frame tracking (moving camera)

def _save_masks(name, stem, items):
    keep = {str(it["frame"]): it["mask"] for it in items if it["mask"] is not None}
    lines = {str(it["frame"]): it["lines"] for it in items if it["lines"] is not None}
    np.savez_compressed(SCRATCH / f"masks_{name}_{stem}.npz", **{k: np.packbits(v) for k, v in keep.items()})
    (SCRATCH / f"lines_{name}_{stem}.json").write_text(json.dumps(
        {k: [list(map(float, v[0])), list(map(float, v[1]))] for k, v in lines.items()}))


def _perframe_rows(stem, items, prompts, t0, name, extra=None):
    maes = [it["board_mae"] for it in items if it["board_mae"] is not None]
    last = items[-1]
    ex = {"frames": [items[0]["frame"], last["frame"]], "frames_total": len(items),
          "frames_ok": len(maes), "per_frame": [{k: it[k] for k in ("frame", "board_mae", "fit_resid_px")} for it in items],
          "perframe_mae_mean": round(float(np.mean(maes)), 2) if maes else None,
          "perframe_mae_median": round(float(np.median(maes)), 2) if maes else None,
          "perframe_mae_max": round(float(np.max(maes)), 2) if maes else None,
          "perframe_within_2": round(100.0 * float(np.mean([m <= 2 for m in maes])), 1) if maes else None}
    ex.update(extra or {})
    _save_masks(name, stem, items)
    rows = _finish(stem, last["frame"], last["mask"], last["lines"], prompts, None, t0, ex)
    return [rows + (last["mask"],)]


@method("perframe_track", "SAM on every 2nd ball frame with path points; each frame scored against its own lane")
def perframe_track(stem, weights):
    fs, _ = L.trajectory_all(stem)
    frames = fs[::2]
    t0 = time.time()
    items = _frames_masks(stem, weights, frames)
    return _perframe_rows(stem, items, items[-1]["prompts"], t0, "perframe_track")


@method("perframe_even", "SAM on every 2nd ball frame with evenly spaced path points")
def perframe_even(stem, weights):
    fs, _ = L.trajectory_all(stem)
    frames = fs[::2]
    t0 = time.time()
    items = _frames_masks(stem, weights, frames, even=True)
    return _perframe_rows(stem, items, items[-1]["prompts"], t0, "perframe_even")


@method("perframe_person", "perframe_track with negative points on detected people")
def perframe_person(stem, weights):
    fs, _ = L.trajectory_all(stem)
    frames = fs[::2]
    t0 = time.time()
    items = _frames_masks(stem, weights, frames, person_neg=True)
    return _perframe_rows(stem, items, items[-1]["prompts"], t0, "perframe_person")


def _video(stem, weights, name, reverse):
    from ultralytics.models.sam import SAM2VideoPredictor
    fs, pos = L.trajectory_all(stem)
    start = max(0, fs[0] - 5)
    end = fs[-1]
    frames = list(range(start, end + 1))
    if reverse:
        frames = frames[::-1]
    clip = SCRATCH / f"clip_{stem}_{frames[0]}_{frames[-1]}.mp4"
    first = cv2.imread(str(gt.frame_path(stem, frames[0])))
    h, w = first.shape[:2]
    if not clip.exists():
        vw = cv2.VideoWriter(str(clip), cv2.VideoWriter_fourcc(*"mp4v"), 30, (w, h))
        for f in frames:
            vw.write(cv2.imread(str(gt.frame_path(stem, f))))
        vw.release()
    pts = L.track_points_even(stem, frames[0]) if reverse else L.track_points(stem, frames[0])
    prompts = {"points": pts, "labels": [1] * len(pts)}
    t0 = time.time()
    overrides = dict(conf=0.25, task="segment", mode="predict", imgsz=1024,
                     model=str(L.WEIGHTS_DIR / weights), verbose=False)
    pred = SAM2VideoPredictor(overrides=overrides)
    items = []
    for i, res in enumerate(pred(source=str(clip), points=[pts], labels=[[1] * len(pts)], stream=True)):
        f = frames[i] if i < len(frames) else frames[-1]
        mask = None
        if res.masks is not None and len(res.masks):
            mask = res.masks.data[0].cpu().numpy().astype(np.uint8)
            if mask.shape != (h, w):
                mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)
        y_top, y_bot = L.gt_y(stem, f)
        anchors = [tuple(L.warp_pt(L.transform(stem, frames[0], f), p)) for p in pts]
        fit = L.fit_edges(mask, y_top, y_bot, anchors) if mask is not None else None
        lines = (fit[0], fit[1]) if fit else None
        items.append({"frame": f, "prompts": prompts, "mask": mask, "lines": lines,
                      "board_mae": _mae(stem, lines, f) if f in pos else None,
                      "fit_resid_px": fit[2]["fit_resid_px"] if fit else None})
    items.sort(key=lambda it: it["frame"])
    return _perframe_rows(stem, items, prompts, t0, name)


@method("video_span", "SAM 2 video mode: prompt once on the pre-release frame, propagate forward to the last frame; per-frame scoring")
def video_span(stem, weights):
    return _video(stem, weights, "video_span", reverse=False)


@method("video_rev", "SAM 2 video mode run backwards: evenly spaced prompts on the clean last frame, propagate back to release")
def video_rev(stem, weights):
    return _video(stem, weights, "video_rev", reverse=True)


# ------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--methods", default=",".join(METHODS))
    ap.add_argument("--weights", default="sam2.1_b.pt")
    ap.add_argument("--tag", default="")
    ap.add_argument("--stems", default=",".join(gt.VIDEOS))
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list:
        for k, (_, d) in METHODS.items():
            print(f"{k:22s} {d}")
        return
    out = L.EXP / "results"
    ov = L.EXP / "overlays"
    out.mkdir(exist_ok=True)
    ov.mkdir(exist_ok=True)
    for name in a.methods.split(","):
        fn, desc = METHODS[name]
        key = name + a.tag
        rows = []
        for stem in a.stems.split(","):
            for row, corners, mask in fn(stem, a.weights):
                row["method"] = key
                row["weights"] = a.weights
                row["desc"] = desc
                rows.append(row)
                cap = f"{key} | {stem} | f{row['frame']}"
                if row["ok"]:
                    extra = [f"board MAE {row['board_mae']}  max {row['board_max']}  <=1: {row['within_1']}%"]
                    if row.get("perframe_mae_mean") is not None:
                        extra.append(f"per-frame MAE mean {row['perframe_mae_mean']}  max {row['perframe_mae_max']}  <=2: {row['perframe_within_2']}%")
                else:
                    extra = ["no mask / fit failed"]
                img = L.draw_overlay(stem, row["frame"], mask, corners, row["prompts"], cap, extra)
                cv2.imwrite(str(ov / f"{key}_{stem}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 88])
                print(json.dumps({k: row.get(k) for k in ("method", "stem", "frame", "ok", "board_mae", "board_max", "within_1", "perframe_mae_mean", "perframe_mae_max", "latency_s")}), flush=True)
        L.save_json(out / f"{key}.json", rows)


if __name__ == "__main__":
    main()
