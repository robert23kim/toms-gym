"""Loop 2, track 1: the lane through the whole throw, and which frame to trust.

Three questions, all measured with the loop-1 metric (common.py -> lane_sam.score):

1. `video_carry` / `video_carry_span` -- the loop-1 SAM 2 video-mode masks are on
   disk; re-score them with a self-supervised occlusion gate. A frame whose mask
   fails the gate gets the nearest passing frame's lines warped in through the
   camera model instead of its own. No SAM re-run.
2. `best_late` -- SAM on the six frames before pin contact, pick ONE with a
   picker that never sees the truth (fit residual, row coverage, gradient
   agreement, sharpness). Reports the picked, the oracle and every candidate.
3. `late_median` -- median of those six frames' lines, warped into the pre-hit
   frame (and, for a tripod, unwarped).
4. `video_keep` -- SAM 2 video mode re-prompted with even_points_keep on the
   pre-hit frame, propagated back to release, then gated as in (1).

usage:
  run_track.py --dump video_rev            # feature table, no results written
  run_track.py --methods video_carry,video_carry_span --kinds track
  run_track.py --methods best_late,late_median --kinds prehit
  run_track.py --methods video_keep --kinds track --weights sam2.1_t.pt
"""
import argparse
import json
import time

import cv2
import numpy as np

import common as C
import edges as E
import run2
import sam2x as S

gt, L = C.gt, C.L
MASKS = C.SCRATCH / "masks"
WORK = C.SCRATCH / "track-1"

# ------------------------------------------------------------------ gate config
# All thresholds are RELATIVE to the video's own median, because the absolute
# scales differ per video by more than the good/bad gap does: sample_input's row
# fit residual is 4-13 px on every frame (a 1500-row lane edge is not a perfect
# line) while Chardie's is 1.3-6.8, so an absolute residual cut fails every
# frame of one video and no frame of another. See --sweep for the sensitivity.
#
# The shipped gate is ONE test: how far the lane's centre at the bottom row sits
# from the median centre over the throw, as a fraction of the lane width, after
# every frame's lines are warped into one reference frame. The other five tests
# are kept switchable because the ablation (gate_ablation in every video_carry
# row) is the result: residual, coverage and width flag only frames the centre
# test already flags, and dropping the centre test costs Chardie 34 boards.
GATE = {
    "resid_ratio": 99,      # row fit residual / median residual over the throw
    "cov": 0.0,             # fraction of scored rows the mask covers (absolute)
    "width_lo": 0.0,        # lane width at the bottom / median width over throw
    "width_hi": 99,
    "ctr_frac": 0.03,       # |centre - median centre| / median width, bottom row
    "person": 99,           # fraction of the lane quad covered by YOLO person boxes
}
CARRY_K = 1             # a flagged frame takes the lines of the k nearest passing frames
                        # (median over k>1; measured worse on 2 of 3 videos, see gate_ablation)
OFF = {"resid_ratio": 99, "cov": 0.0, "width_lo": 0.0, "width_hi": 99, "ctr_frac": 99, "person": 99}
ABLATION = {
    "none (= loop 1)": dict(OFF),
    "centre .03, k=1 (shipped)": dict(OFF, ctr_frac=0.03, _k=1),
    "centre .03, k=3": dict(OFF, ctr_frac=0.03, _k=3),
    "centre .03, k=5": dict(OFF, ctr_frac=0.03, _k=5),
    "centre .03, k=9": dict(OFF, ctr_frac=0.03, _k=9),
    "centre .05, k=1": dict(OFF, ctr_frac=0.05, _k=1),
    "centre .08, k=1": dict(OFF, ctr_frac=0.08, _k=1),
    "centre .05, k=5": dict(OFF, ctr_frac=0.05, _k=5),
    "centre .08, k=5": dict(OFF, ctr_frac=0.08, _k=5),
    "centre .03 + person .15, k=1": dict(OFF, ctr_frac=0.03, person=0.15, _k=1),
    "brief four (resid+cov+width+person), k=1": dict(OFF, resid_ratio=1.5, cov=0.55, width_lo=0.88, width_hi=1.12, person=0.15, _k=1),
    "person .15, k=5": dict(OFF, person=0.15, _k=5),
    "resid 1.5, k=5": dict(OFF, resid_ratio=1.5, _k=5),
    "width .88-1.12, k=5": dict(OFF, width_lo=0.88, width_hi=1.12, _k=5),
    "cov .55, k=5": dict(OFF, cov=0.55, _k=5),
    "centre .03 + person .15, k=5": dict(OFF, ctr_frac=0.03, person=0.15, _k=5),
    "brief four (resid+cov+width+person), k=5": dict(OFF, resid_ratio=1.5, cov=0.55, width_lo=0.88, width_hi=1.12, person=0.15, _k=5),
    "all six, k=5": {"resid_ratio": 1.5, "cov": 0.55, "width_lo": 0.88, "width_hi": 1.12, "ctr_frac": 0.03, "person": 0.15, "_k": 5},
}


# ------------------------------------------------------------------ helpers

def person_cache(stem):
    p = WORK / f"person_{stem}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())


def lane_quad(lines, y_top, y_bot):
    c = L.lines_to_corners(lines[0], lines[1], y_top, y_bot)
    return np.array([c["top_left"], c["top_right"], c["bottom_right"], c["bottom_left"]], np.float32)


def person_overlap(lines, y_top, y_bot, boxes, shape):
    """Fraction of the lane quad's area covered by person boxes."""
    if not boxes:
        return 0.0
    H, W = shape
    quad = np.round(lane_quad(lines, y_top, y_bot)).astype(np.int32)
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [quad], 1)
    area = int(m.sum())
    if area < 50:
        return 0.0
    pb = np.zeros((H, W), np.uint8)
    for x1, y1, x2, y2 in boxes:
        cv2.rectangle(pb, (int(x1), int(y1)), (int(x2), int(y2)), 1, -1)
    return float((m & pb).sum()) / area


def sharpness(img, lines, y_top, y_bot):
    """Laplacian variance inside the lane quad (motion blur / defocus check)."""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    quad = np.round(lane_quad(lines, y_top, y_bot)).astype(np.int32)
    m = np.zeros(g.shape, np.uint8)
    cv2.fillPoly(m, [quad], 1)
    lap = cv2.Laplacian(g, cv2.CV_32F, ksize=3)
    v = lap[m > 0]
    return float(v.var()) if len(v) > 50 else 0.0


def grad_agree(img, lines, y_top, y_bot, comp=None):
    """Median gradient peak strength along the fitted lines (E.snap_rows), and
    the fraction of rows that found a peak. High = the line sits on a real
    image edge; low = the mask boundary is invented (occluder, blur)."""
    pol = 1
    if comp is not None:
        pol = E.polarity(img, comp, y_top, y_bot)
    out = []
    frac = []
    for side, ln in (("left", lines[0]), ("right", lines[1])):
        ys, xs = E.snap_rows(img, ln, y_top, y_bot, side, pol, band=6, min_frac=0.0)
        n = max(1.0, y_bot - y_top + 1)
        frac.append(len(ys) / n)
        if len(ys):
            g = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (3, 3), 0)
            gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
            sgn = pol * (1 if side == "left" else -1)
            vals = [abs(float(sgn * gx[int(y), int(round(x))])) for y, x in zip(ys, xs)]
            out.append(float(np.median(vals)))
            # how far the snapped line sits from the fitted one
            a, b = ln
            out.append(float(np.median(np.abs(xs - (a * ys + b)))))
    peak = float(np.mean(out[0::2])) if out else 0.0
    drift = float(np.mean(out[1::2])) if out else 99.0
    return {"grad_peak": round(peak, 1), "grad_drift_px": round(drift, 2),
            "grad_rows": round(float(np.mean(frac)), 2), "polarity": pol}


def width_center(stem, lines, f, ref, ref_y):
    """Lane width and centre at the reference frame's bottom / top rows, after
    warping this frame's lines into the reference frame (camera motion out)."""
    T = L.transform(stem, f, ref)
    yt, yb = L.gt_y(stem, f)
    lw = L.warp_line(T, lines[0], yt, yb)
    rw = L.warp_line(T, lines[1], yt, yb)
    Yt, Yb = ref_y
    out = {}
    for tag, Y in (("bot", Yb), ("top", Yt)):
        xl = lw[0] * Y + lw[1]
        xr = rw[0] * Y + rw[1]
        out[f"w_{tag}"] = float(xr - xl)
        out[f"c_{tag}"] = float(0.5 * (xr + xl))
    return out, (lw, rw)


def mae_of(stem, lines, f, pos):
    if lines is None or f not in pos:
        return None
    yt, yb = L.gt_y(stem, f)
    return L.score(stem, L.lines_to_corners(lines[0], lines[1], yt, yb), f)["board_mae"]


def stats(maes, prefix=""):
    m = [v for v in maes if v is not None]
    if not m:
        return {f"{prefix}mae_mean": None}
    return {f"{prefix}mae_mean": round(float(np.mean(m)), 2),
            f"{prefix}mae_median": round(float(np.median(m)), 2),
            f"{prefix}mae_max": round(float(np.max(m)), 2),
            f"{prefix}within_2": round(100.0 * float(np.mean([v <= 2 for v in m])), 1)}


def save_tracked(name, stem, items):
    MASKS.mkdir(exist_ok=True)
    keep = {str(it["frame"]): it["mask"] for it in items if it.get("mask") is not None}
    lines = {str(it["frame"]): it["lines"] for it in items if it.get("lines") is not None}
    np.savez_compressed(MASKS / f"masks_{name}_{stem}.npz", **{k: np.packbits(v) for k, v in keep.items()})
    (MASKS / f"lines_{name}_{stem}.json").write_text(json.dumps(
        {k: [list(map(float, v[0])), list(map(float, v[1]))] for k, v in lines.items()}))


def perframe_extra(stem, items, key="board_mae"):
    """Loop-1 _perframe_rows shape: per_frame list + the four summary fields."""
    maes = [it[key] for it in items if it.get(key) is not None]
    ex = {"frames": [items[0]["frame"], items[-1]["frame"]], "frames_total": len(items),
          "frames_ok": len(maes),
          "per_frame": [{"frame": it["frame"], "board_mae": it.get(key),
                         "fit_resid_px": it.get("fit_resid_px")} for it in items]}
    s = stats(maes, "perframe_")
    ex.update({"perframe_mae_mean": s.get("perframe_mae_mean"), "perframe_mae_median": s.get("perframe_mae_median"),
               "perframe_mae_max": s.get("perframe_mae_max"), "perframe_within_2": s.get("perframe_within_2")})
    return ex


# ------------------------------------------------------- 1. gate over saved masks

def load_saved(src, stem):
    """Loop-1 video-mode masks + the prompt points they were made with."""
    z = np.load(MASKS / f"masks_{src}_{stem}.npz")
    keys = sorted(int(k) for k in z.files)
    rows = json.loads((C.PREV / "results" / f"{src}.json").read_text())
    row = [r for r in rows if r["stem"] == stem][0]
    pts = row["prompts"]["points"]
    fs, _ = L.trajectory_all(stem)
    ref = fs[-1] if src.endswith("rev") else max(0, fs[0] - 5)
    shape = cv2.imread(str(gt.frame_path(stem, keys[0]))).shape[:2]
    loop1 = {p["frame"]: p.get("board_mae") for p in row.get("per_frame", [])}
    return z, keys, pts, ref, shape, loop1


def frame_items(stem, keys, z, shape, pts, ref, want_person=True, masks_from=None):
    """Per-frame fit + no-truth quality features for every saved frame."""
    _, pos = L.trajectory_all(stem)
    people = person_cache(stem) if want_person else None
    ref_y = L.gt_y(stem, ref)
    items = []
    for k in keys:
        if masks_from is not None:
            m = masks_from[k]
        else:
            m = np.unpackbits(z[str(k)])[:shape[0] * shape[1]].reshape(shape).astype(np.uint8)
        yt, yb = L.gt_y(stem, k)
        anch = [tuple(L.warp_pt(L.transform(stem, ref, k), p)) for p in pts]
        fit = L.fit_edges(m, yt, yb, anch)
        it = {"frame": k, "mask": m, "lines": None, "board_mae": None, "fit_resid_px": None}
        if fit is None:
            items.append(it)
            continue
        lines = (fit[0], fit[1])
        it["lines"] = lines
        it["board_mae"] = mae_of(stem, lines, k, pos)
        comp = L.largest_component(m, anch)
        lg = (comp.astype(np.float32) * 2 - 1) if comp is not None else None
        soft = None
        if lg is not None:
            ys, xl, xr = E.soft_rows(lg, yt, yb, anch, comp)
            soft = E.fit_pair(ys, xl, xr)
        it["fit_resid_px"] = soft[2]["fit_resid_px"] if soft else fit[2]["fit_resid_px"]
        it["cov"] = fit[2]["row_coverage"]
        it["soft_mae"] = mae_of(stem, (soft[0], soft[1]), k, pos) if soft else None
        wc, _ = width_center(stem, lines, k, ref, ref_y)
        it.update(wc)
        img = cv2.imread(str(gt.frame_path(stem, k)))
        it["person"] = round(person_overlap(lines, yt, yb, (people or {}).get(str(k), []), shape), 3) if people is not None else 0.0
        it["sharp"] = round(sharpness(img, lines, yt, yb), 1)
        items.append(it)
    return items


def carry_lines(stem, passing, f, k=1):
    """Lines for frame f carried from the k nearest passing frames, each warped
    through the camera model and then median-combined. k > 1 matters because the
    ORB model's per-frame jitter at the pin end is 3.0 px on sample_input (2
    boards) against only 10 px of cumulative motion over 19 frames -- a single
    source frame inherits that jitter, a median over five does not."""
    near = sorted(passing, key=lambda q: abs(q["frame"] - f))[:max(1, k)]
    fits = []
    for q in near:
        yt, yb = L.gt_y(stem, q["frame"])
        T = L.transform(stem, q["frame"], f)
        fits.append((L.warp_line(T, q["lines"][0], yt, yb), L.warp_line(T, q["lines"][1], yt, yb)))
    if len(fits) == 1:
        return fits[0], [q["frame"] for q in near]
    return L.median_lines(fits), [q["frame"] for q in near]


def apply_gate(stem, items, ref, gate=GATE, iters=3, k=1):
    """Flag frames whose mask fails the gate and carry the nearest passing
    frame's lines into them through the camera model.

    The reference statistics (median residual / width / centre) are re-estimated
    over the passing frames only and the gate re-applied, because on Chardie more
    than half the throw is occluded and the first median is pulled by it."""
    ok = [it for it in items if it["lines"] is not None]
    if not ok:
        return items, {}
    pool = ok
    # The residual median is taken ONCE over every fitted frame. Re-estimating it
    # over the passing frames is a ratchet: the median falls, more frames fail,
    # it falls again -- on sample_input that left 5 of 91 frames passing.
    rr = float(np.median([it["fit_resid_px"] for it in ok if it["fit_resid_px"] is not None]))
    wb = cb = None
    for _ in range(iters):
        wb = float(np.median([it["w_bot"] for it in pool]))
        cb = float(np.median([it["c_bot"] for it in pool]))
        for it in items:
            if it["lines"] is None:
                it["gate"] = ["nomask"]
                continue
            why = []
            it["resid_ratio"] = round(it["fit_resid_px"] / rr, 2) if (it["fit_resid_px"] is not None and rr) else None
            if it["resid_ratio"] is not None and it["resid_ratio"] > gate["resid_ratio"]:
                why.append("resid")
            if it.get("cov", 1) < gate["cov"]:
                why.append("cov")
            r = it["w_bot"] / wb if wb else 1.0
            it["w_ratio"] = round(r, 3)
            if not (gate["width_lo"] <= r <= gate["width_hi"]):
                why.append("width")
            it["c_dev_px"] = round(abs(it["c_bot"] - cb), 1)
            if wb and it["c_dev_px"] / wb > gate["ctr_frac"]:
                why.append("centre")
            if it.get("person", 0) > gate["person"]:
                why.append("person")
            it["gate"] = why
        nxt = [it for it in items if it["lines"] is not None and not it["gate"]]
        if len(nxt) < 5 or [it["frame"] for it in nxt] == [it["frame"] for it in pool]:
            break
        pool = nxt
    passing = [it for it in items if it["lines"] is not None and not it["gate"]]
    _, pos = L.trajectory_all(stem)
    n_rep = 0
    for it in items:
        if it["lines"] is not None and not it["gate"]:
            it["src_frame"] = it["frame"]
            it["gated_mae"] = it["board_mae"]
            it["gated_lines"] = it["lines"]
            continue
        if not passing:
            it["gated_mae"], it["gated_lines"], it["src_frame"] = it["board_mae"], it["lines"], it["frame"]
            continue
        lines, srcs = carry_lines(stem, passing, it["frame"], k)
        it["gated_lines"] = lines
        it["gated_mae"] = mae_of(stem, lines, it["frame"], pos)
        it["src_frame"] = srcs[0]
        it["src_frames"] = srcs
        n_rep += 1
    # Oracle: would replacing this frame have helped? Truth-only, for reporting.
    for it in items:
        if it["board_mae"] is None or not passing:
            it["oracle_gain"] = None
            continue
        cl, _ = carry_lines(stem, passing, it["frame"], k)
        cm = mae_of(stem, cl, it["frame"], pos)
        it["carry_mae"] = cm
        it["oracle_gain"] = round(it["board_mae"] - cm, 2) if cm is not None else None
    oracle = [min(v for v in (it["board_mae"], it.get("carry_mae")) if v is not None)
              for it in items if it["board_mae"] is not None]
    tp = sum(1 for it in items if it.get("oracle_gain") is not None and it["gate"] and it["oracle_gain"] > 0)
    fp = sum(1 for it in items if it.get("oracle_gain") is not None and it["gate"] and it["oracle_gain"] <= 0)
    fn = sum(1 for it in items if it.get("oracle_gain") is not None and not it["gate"] and it["oracle_gain"] > 0)
    info = {"gate_median_w_bot": round(wb, 1), "gate_median_c_bot": round(cb, 1),
            "gate_median_resid_px": round(rr, 2),
            "frames_passing": len(passing), "frames_replaced": n_rep,
            "gate_reasons": {r: sum(1 for it in items if r in (it.get("gate") or []))
                             for r in ("nomask", "resid", "cov", "width", "centre", "person")},
            "gate_flag_tp": tp, "gate_flag_fp": fp, "gate_flag_fn": fn,
            "gate_precision": round(tp / max(1, tp + fp), 2), "gate_recall": round(tp / max(1, tp + fn), 2)}
    info.update(stats(oracle, "oracle_"))
    return items, info


def ablation(stem, items, ref):
    """Every gate variant re-run on the same features (pure numpy, no SAM)."""
    import copy
    slim = [{k: v for k, v in it.items() if k != "mask"} for it in items]
    out = {}
    for tag, g in ABLATION.items():
        g = dict(g)
        k = g.pop("_k", 1)
        it2, info = apply_gate(stem, copy.deepcopy(slim), ref, g, k=k)
        s = stats([q.get("gated_mae") for q in it2])
        out[tag] = {"mae_mean": s["mae_mean"], "mae_median": s["mae_median"], "mae_max": s["mae_max"],
                    "within_2": s["within_2"], "replaced": info["frames_replaced"], "k": k,
                    "precision": info["gate_precision"], "recall": info["gate_recall"]}
    return out


def _carry(src, name):
    @run2.method(name, f"loop-1 {src} masks re-scored with a self-supervised occlusion gate; failing frames carry the nearest passing frame's lines through the camera model", kinds=("track",))
    def fn(stem, weights, kind):
        t0 = time.time()
        z, keys, pts, ref, shape, loop1 = load_saved(src, stem)
        items = frame_items(stem, keys, z, shape, pts, ref)
        items, info = apply_gate(stem, items, ref, k=CARRY_K)
        abl = ablation(stem, items, ref)   # before lines are overwritten below
        # carry the gated mask too so the review video shows what was used
        for it in items:
            if it.get("src_frame") is not None and it["src_frame"] != it["frame"] and it.get("mask") is not None:
                srcm = [q for q in items if q["frame"] == it["src_frame"]][0]["mask"]
                it["mask"] = L.warp_mask(L.transform(stem, it["src_frame"], it["frame"]), srcm)
            it["lines"] = it.get("gated_lines") or it["lines"]
        ex = perframe_extra(stem, items, key="gated_mae")
        ex.update(info)
        ex.update(stats([loop1.get(it["frame"]) for it in items], "loop1_"))
        ex.update(stats([it["board_mae"] for it in items], "refit_"))
        ex.update(stats([it.get("soft_mae") for it in items], "soft_"))
        ex["gate_cfg"] = dict(GATE, carry_k=CARRY_K)
        ex["replaced_frames"] = [it["frame"] for it in items if it.get("src_frame") not in (None, it["frame"])]
        ex["mae_on_replaced_before"] = stats([it["board_mae"] for it in items
                                             if it.get("src_frame") not in (None, it["frame"])], "rep_")
        ex["mae_on_replaced_after"] = stats([it["gated_mae"] for it in items
                                            if it.get("src_frame") not in (None, it["frame"])], "rep_")
        ex["mae_on_kept"] = stats([it["gated_mae"] for it in items
                                   if it.get("src_frame") == it["frame"]], "kept_")
        ex["gate_ablation"] = abl
        save_tracked(f"{name}", stem, items)
        last = items[-1]
        prompts = {"points": pts, "labels": [1] * len(pts)}
        return [run2.finish(stem, last["frame"], last["mask"], last["lines"], prompts, t0, ex, kind)]
    return fn


_carry("video_rev", "video_carry")
_carry("video_span", "video_carry_span")


# ------------------------------------------------------------- 2/3. late frames

def late_candidates(stem, weights, backs=(1, 2, 3, 4, 5, 6)):
    """SAM with even_points_keep on the frames pin_hit-1 .. pin_hit-6, with the
    no-truth picker features and (for reporting) each candidate's board MAE."""
    _, pos = L.trajectory_all(stem)
    out = []
    for b in backs:
        f = C.frame_for(stem, f"prehit-{b}")
        img = C.read_frame(stem, f)
        if img is None:
            continue
        pts = C.even_points_keep(stem, f, 3)
        si = S.SamImage(img, weights)
        lg, sc = si.logit(pts)
        yt, yb = L.gt_y(stem, f)
        comp = E.component(lg, pts)
        if comp is None:
            out.append({"back": b, "frame": f, "ok": False})
            continue
        ys, xl, xr = E.soft_rows(lg, yt, yb, pts, comp)
        fp = E.fit_pair(ys, xl, xr)
        if fp is None:
            out.append({"back": b, "frame": f, "ok": False})
            continue
        lines = (fp[0], fp[1])
        c = {"back": b, "frame": f, "ok": True, "lines": lines, "mask": comp, "prompts": pts,
             "sam_score": round(sc, 3), "resid_px": fp[2]["fit_resid_px"],
             "cov": round(fp[2]["rows"] / max(1.0, yb - yt + 1), 3),
             "sharp": round(sharpness(img, lines, yt, yb), 1),
             "mae": mae_of(stem, lines, f, pos)}
        c.update(grad_agree(img, lines, yt, yb, comp))
        out.append(c)
    return out


def pick_late(cands):
    """Self-supervised pick. Rank each candidate on four no-truth features
    (low residual, high row coverage, strong gradient agreement, sharp), then
    take the best total rank. Ranks, not z-scores: the features have wildly
    different scales and one blurred frame would dominate a z-score sum."""
    ok = [c for c in cands if c.get("ok")]
    if not ok:
        return None, {}
    feats = [("resid_px", +1), ("cov", -1), ("grad_peak", -1), ("grad_drift_px", +1),
             ("grad_rows", -1), ("sharp", -1)]
    rank = {c["frame"]: 0.0 for c in ok}
    detail = {}
    for key, sgn in feats:
        order = sorted(ok, key=lambda c: sgn * c.get(key, 0))
        for i, c in enumerate(order):
            rank[c["frame"]] += i
        detail[key] = {c["frame"]: i for i, c in enumerate(order)}
    best = min(ok, key=lambda c: (rank[c["frame"]], c["back"]))
    return best, {"pick_rank": {str(k): v for k, v in rank.items()},
                  "pick_feature_ranks": {k: {str(a): b for a, b in v.items()} for k, v in detail.items()}}


def _cand_table(cands):
    return [{k: c.get(k) for k in ("back", "frame", "ok", "mae", "resid_px", "cov", "grad_peak",
                                   "grad_drift_px", "grad_rows", "sharp", "sam_score")} for c in cands]


@run2.method("best_late", "SAM on the 6 frames before pin contact; one picked by a truth-free picker (fit residual, row coverage, gradient agreement, sharpness)", kinds=("prehit",))
def best_late(stem, weights, kind):
    t0 = time.time()
    cands = late_candidates(stem, weights)
    best, pinfo = pick_late(cands)
    tbl = _cand_table(cands)
    maes = [c["mae"] for c in cands if c.get("ok") and c.get("mae") is not None]
    ex = {"candidates": tbl, "oracle_mae": min(maes) if maes else None,
          "oracle_frame": min([c for c in cands if c.get("mae") is not None], key=lambda c: c["mae"])["frame"] if maes else None,
          "worst_mae": max(maes) if maes else None,
          "cand_mae_mean": round(float(np.mean(maes)), 2) if maes else None}
    ex.update(pinfo)
    if best is None:
        return [run2.finish(stem, C.frame_for(stem, "prehit"), None, None, {}, t0, ex, kind)]
    ex["picked_frame"] = best["frame"]
    ex["picked_back"] = best["back"]
    ex["pick_regret"] = round(best["mae"] - ex["oracle_mae"], 2) if (best.get("mae") is not None and ex["oracle_mae"] is not None) else None
    prompts = {"points": best["prompts"], "labels": [1] * len(best["prompts"])}
    return [run2.finish(stem, best["frame"], best["mask"], best["lines"], prompts, t0, ex, kind)]


@run2.method("late_median", "median of the 6 pre-hit frames' fitted lines, each warped into the pre-hit frame (plus an unwarped number for comparison)", kinds=("prehit",))
def late_median(stem, weights, kind):
    t0 = time.time()
    cands = late_candidates(stem, weights)
    ok = [c for c in cands if c.get("ok")]
    target = C.frame_for(stem, "prehit")
    _, pos = L.trajectory_all(stem)
    if not ok:
        return [run2.finish(stem, target, None, None, {}, t0, {"candidates": _cand_table(cands)}, kind)]
    warped, raw = [], []
    for c in ok:
        yt, yb = L.gt_y(stem, c["frame"])
        T = L.transform(stem, c["frame"], target)
        warped.append((L.warp_line(T, c["lines"][0], yt, yb), L.warp_line(T, c["lines"][1], yt, yb)))
        raw.append(c["lines"])
    lw = L.median_lines(warped)
    lr = L.median_lines(raw)
    ex = {"candidates": _cand_table(cands), "frames": [c["frame"] for c in ok],
          "nowarp_mae": mae_of(stem, lr, target, pos),
          "oracle_mae": min([c["mae"] for c in ok if c.get("mae") is not None], default=None)}
    base = [c for c in ok if c["frame"] == target]
    mask = base[0]["mask"] if base else ok[-1]["mask"]
    prompts = {"points": (base[0] if base else ok[-1])["prompts"], "labels": [1] * 3}
    return [run2.finish(stem, target, mask, lw, prompts, t0, ex, kind)]


# --------------------------------------------------------------- 4. video_keep

@run2.method("video_keep", "SAM 2 video mode prompted with even_points_keep on the pre-hit frame and propagated back to release, then the occlusion gate", kinds=("track",))
def video_keep(stem, weights, kind):
    from ultralytics.models.sam import SAM2VideoPredictor
    t0 = time.time()
    fs, _ = L.trajectory_all(stem)
    start = max(0, fs[0] - 5)
    prehit = C.frame_for(stem, "prehit")
    frames = list(range(start, prehit + 1))[::-1]     # prehit -> release
    clip = WORK / f"clip_keep_{stem}_{frames[0]}_{frames[-1]}.mp4"
    first = cv2.imread(str(gt.frame_path(stem, frames[0])))
    h, w = first.shape[:2]
    if not clip.exists():
        vw = cv2.VideoWriter(str(clip), cv2.VideoWriter_fourcc(*"mp4v"), 30, (w, h))
        for f in frames:
            vw.write(cv2.imread(str(gt.frame_path(stem, f))))
        vw.release()
    pts = C.even_points_keep(stem, frames[0], 3)
    overrides = dict(conf=0.25, task="segment", mode="predict", imgsz=1024,
                     model=str(L.WEIGHTS_DIR / weights), verbose=False)
    pred = SAM2VideoPredictor(overrides=overrides)
    masks = {}
    for i, res in enumerate(pred(source=str(clip), points=[pts], labels=[[1] * len(pts)], stream=True)):
        f = frames[i] if i < len(frames) else frames[-1]
        m = None
        if res.masks is not None and len(res.masks):
            m = res.masks.data[0].cpu().numpy().astype(np.uint8)
            if m.shape != (h, w):
                m = cv2.resize(m, (w, h), interpolation=cv2.INTER_NEAREST)
        if m is not None:
            masks[f] = m
    keys = sorted(masks)
    items = frame_items(stem, keys, None, (h, w), pts, frames[0], masks_from=masks)
    items, info = apply_gate(stem, items, frames[0], k=CARRY_K)
    for it in items:
        if it.get("src_frame") is not None and it["src_frame"] != it["frame"] and it.get("mask") is not None:
            srcm = [q for q in items if q["frame"] == it["src_frame"]][0]["mask"]
            it["mask"] = L.warp_mask(L.transform(stem, it["src_frame"], it["frame"]), srcm)
        it["lines"] = it.get("gated_lines") or it["lines"]
    ex = perframe_extra(stem, items, key="gated_mae")
    ex.update(info)
    ex.update(stats([it["board_mae"] for it in items], "refit_"))
    ex["prompt_frame"] = frames[0]
    save_tracked("video_keep", stem, items)
    last = items[-1]
    return [run2.finish(stem, last["frame"], last["mask"], last["lines"],
                        {"points": pts, "labels": [1] * len(pts)}, t0, ex, kind)]


# --------------------------------------------------------------------- dump

def cached_features(src, stem):
    """Per-frame features without the masks, cached so threshold sweeps are free."""
    p = WORK / f"feat_{src}_{stem}.json"
    if p.exists():
        d = json.loads(p.read_text())
        for it in d["items"]:
            it["lines"] = tuple(tuple(v) for v in it["lines"]) if it["lines"] else None
        return d["items"], d["ref"], {int(k): v for k, v in d["loop1"].items()}
    z, keys, pts, ref, shape, loop1 = load_saved(src, stem)
    items = frame_items(stem, keys, z, shape, pts, ref)
    slim = [{k: v for k, v in it.items() if k != "mask"} for it in items]
    WORK.mkdir(exist_ok=True)
    p.write_text(json.dumps({"items": slim, "ref": ref,
                             "loop1": {str(k): v for k, v in loop1.items()}}, default=float))
    return cached_features(src, stem)


SWEEP = {"resid_ratio": [1.2, 1.35, 1.5, 1.75, 2.0, 99],
         "cov": [0.0, 0.4, 0.55, 0.7, 0.8],
         "width_lo": [0.7, 0.8, 0.88, 0.94, 0.0],
         "width_hi": [1.06, 1.12, 1.2, 1.4, 99],
         "ctr_frac": [0.015, 0.02, 0.03, 0.05, 0.1, 99],
         "person": [0.05, 0.1, 0.15, 0.25, 0.4, 99]}


def sweep(src, stems):
    """One threshold at a time off the default, to show the gate is not knife-edge.
    99 / 0.0 effectively switches that test off."""
    import copy
    base = {}
    for stem in stems:
        base[stem] = cached_features(src, stem)
    print(f"{src}: default gate {json.dumps(GATE)}")
    hdr = f"{'feature':>12} {'value':>7} " + " ".join(f"{s[:11]:>13}" for s in stems)
    print(hdr)

    def line(tag, val, g):
        cells = []
        for stem in stems:
            items, ref, _ = base[stem]
            it2, info = apply_gate(stem, copy.deepcopy(items), ref, g, k=CARRY_K)
            s = stats([q.get("gated_mae") for q in it2])
            cells.append(f"{str(s['mae_mean']):>6}/{info['frames_replaced']:>3}rep")
        print(f"{tag:>12} {str(val):>7} " + " ".join(f"{c:>13}" for c in cells))

    line("(default)", "-", GATE)
    for key, vals in SWEEP.items():
        for v in vals:
            g = dict(GATE)
            g[key] = v
            line(key, v, g)
    print("\nall tests off (= loop 1 refit, sanity check):")
    line("none", "-", {"resid_ratio": 99, "cov": 0.0, "width_lo": 0.0, "width_hi": 99, "ctr_frac": 99, "person": 99})


def dump(src, stems):
    """Feature table per frame: used to set the gate thresholds by eye."""
    for stem in stems:
        items, ref, loop1 = cached_features(src, stem)
        items, info = apply_gate(stem, items, ref, k=CARRY_K)
        print(f"\n=== {src} {stem}  ref={ref} {json.dumps(info)}")
        print(f"{'frame':>6} {'mae':>7} {'soft':>7} {'gated':>7} {'resid':>6} {'cov':>5} {'wrat':>6} {'cdev':>6} {'pers':>6} {'sharp':>8} {'src':>6}  gate")
        for it in items:
            print(f"{it['frame']:>6} {str(it['board_mae']):>7} {str(it.get('soft_mae')):>7} "
                  f"{str(it.get('gated_mae')):>7} {str(it.get('fit_resid_px')):>6} {str(it.get('cov')):>5} "
                  f"{str(it.get('w_ratio')):>6} {str(it.get('c_dev_px')):>6} {str(it.get('person')):>6} "
                  f"{str(it.get('sharp')):>8} {str(it.get('src_frame')):>6}  {','.join(it.get('gate') or [])}")
        for tag, key in (("loop1", None), ("refit", "board_mae"), ("soft", "soft_mae"), ("gated", "gated_mae")):
            v = [loop1.get(it["frame"]) for it in items] if key is None else [it.get(key) for it in items]
            print(tag, json.dumps(stats(v)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--methods", default="")
    ap.add_argument("--kinds", default="track")
    ap.add_argument("--weights", default="sam2.1_b.pt")
    ap.add_argument("--tag", default="")
    ap.add_argument("--stems", default=",".join(C.STEMS))
    ap.add_argument("--dump", default="")
    ap.add_argument("--sweep", default="")
    a = ap.parse_args()
    if a.dump:
        dump(a.dump, a.stems.split(","))
        return
    if a.sweep:
        sweep(a.sweep, a.stems.split(","))
        return
    run2.run(a.methods.split(","), a.kinds.split(","), a.weights, a.tag, a.stems.split(","))


if __name__ == "__main__":
    main()
