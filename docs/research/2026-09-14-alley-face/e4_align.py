"""E4: aligning the face. From E3's homography of the right lane (the alignment question is
separate from the selection question, which E3 reports), every landmark is refined locally on the
frame - arrows and the three dot rows as sub-pixel dark-blob centroids on the H-rectified lane,
the pin bases with loop 4's rack fit (initialised from H, alias-margin guarded), the two near
corners as the gutter-edge lines (LSD segments along x = 0 / x = W, robustly fitted) crossed with
the foul line (segments along y = 0, else the foul-dot row's line) - and one weighted robust DLT
is fitted over all of them (weights = 1 / expected precision in lane inches: pins 0.45, arrows
0.7, dots 0.7, foul-line dots 0.7, approach dots 1.0, gutter-line points 1.5 (x-only), near corners
1.0). Variants: refit (all), no-near (drop the corner points), rows-only (arrows + dots, no pins),
pins-pooled (the rack pooled over the standing-pin frames through E5's camera model, when present).
Scored per frame against both truths (annotated / pins / all), pre-hit and last frames, pin-end
tail. Writes results/e4_align_<stem>.json, $AF_SCRATCH/pred/align_<stem>.json.gz, overlays/e4_*.
usage: e4_align.py [--set arrows+dots+rack+gutters] [stems...]"""
import argparse
import gzip
import json
import time

import cv2
import numpy as np

import af
import e2_candidates as E2

LM = af.LM
CONST = af.constellation()
SIG = {"pin": 0.45, "arrow": 0.7, "dot": 0.7, "fdot": 0.7, "adot": 1.0, "corner": 1.0, "gutter": 2.0}
REJECT_IN = 2.5
ROWS = {"arrow": (CONST["arrow_20"][1] - 30, CONST["arrow_20"][1] + 30), "dot": (CONST["dot_20"][1] - 18, CONST["dot_20"][1] + 18),
        "fdot": (CONST["fdot_20"][1] - 12, CONST["fdot_20"][1] + 12), "adot": (CONST["adot_20"][1] - 24, CONST["adot_20"][1] + 24)}


# ---------------------------------------------------------------- local refinement

PITCH = {"arrow": 5 * af.BOARD_IN, "dot": 3 * af.BOARD_IN, "fdot": 5 * af.BOARD_IN, "adot": 5 * af.BOARD_IN}
MIN_ROW = {"arrow": 4, "dot": 5, "fdot": 4, "adot": 4}


def refine_row(marks_xy, H, cls, img_shape):
    """One row of the constellation located in the E2 mark pool as a rigid pattern: the class's points
    are projected through H, and the projected pattern is slid (shift up to +-0.6 pitch in x, +-0.4 in
    y) and scaled (0.8-1.25) over the marks; the placement with the most marks within tol (3.5 px or
    0.12 pitch) wins, ties to the smallest move; accepted with >= MIN_ROW members. Marks then take
    their nearest projected point (one each). Rows that are partly off-frame are matched on the part in
    frame. Returns {name: (x, y, 0.0)}."""
    from scipy.spatial import cKDTree
    names = [n for n in CONST if af.classes_of(n) == cls]
    if len(marks_xy) < MIN_ROW[cls]:
        return {}
    proj = af.to_image(H, [CONST[n] for n in names])
    h, w = img_shape[:2]
    inside = (proj[:, 0] >= -20) & (proj[:, 0] < w + 20) & (proj[:, 1] >= -20) & (proj[:, 1] < h + 20)
    if inside.sum() < MIN_ROW[cls]:
        return {}
    proj = proj[inside]; names = [n for n, ok in zip(names, inside) if ok]
    pitch_px = float(np.median(np.abs(np.diff(proj[:, 0])))) if len(proj) > 1 else 20.0
    tol = max(3.5, 0.12 * pitch_px)
    tree = cKDTree(marks_xy)
    centre = proj.mean(0); rel = proj - centre
    sx = np.arange(-0.6 * pitch_px, 0.6 * pitch_px + 1e-6, max(1.0, pitch_px / 12))
    sy = np.arange(-0.4 * pitch_px, 0.4 * pitch_px + 1e-6, max(1.0, pitch_px / 12))
    best = None
    for sc in (0.8, 0.9, 1.0, 1.1, 1.25):
        base = centre + sc * rel
        for dx in sx:
            for dy in sy:
                P = base + np.array([dx, dy])
                d, _ = tree.query(P, k=1)
                n = int((d <= tol).sum())
                key = (n, -abs(sc - 1.0), -(dx * dx + dy * dy))
                if best is None or key > best[0]:
                    best = (key, P)
    if best is None or best[0][0] < MIN_ROW[cls]:
        return {}
    P = best[1]
    d, idx = tree.query(P, k=1)
    out = {}; used = set()
    for n, (x, y), dd, i in zip(names, P, d, idx):
        if dd <= tol and i not in used:
            used.add(int(i)); out[n] = (float(marks_xy[i][0]), float(marks_xy[i][1]), 0.0)
    return out


def refine_pins(img, H, standing):
    if not standing:
        return None, None
    p = af.to_image(H, [(0, LM.HEAD_IN), (af.W_IN, LM.HEAD_IN)])
    w_px = float(p[1][0] - p[0][0])
    try:
        pts, sc, params, score, contrast, parts = LM.fit_rack(img, H, max(w_px, 10), coarse=True)
        for _ in range(2):
            pts = LM.refine_pin_columns(img, pts, sc)
    except Exception as e:  # noqa: BLE001
        return None, {"error": str(e)[:80]}
    ok = bool(contrast >= 2.5 and score > 0.2 and (parts.get("alias_margin") is None or parts["alias_margin"] > 0.03))
    return ({f"pin_{k}_base": (float(pts[k - 1][0]), float(pts[k - 1][1])) for k in range(1, 11)} if ok else None), {"contrast": round(float(contrast), 1), "score": round(float(score), 3), "alias_margin": parts.get("alias_margin"), "ok": ok}


def gutter_lines(segs, H, tol_in=2.0, y_rng=(-30.0, 500.0)):
    """LSD segments along x = 0 / x = W under H (sampled points within tol_in, between the approach
    and ~42 ft) -> robust image lines x = a*y + b per side, plus the segment points as x-only constraints."""
    out = {}
    for side, x0 in (("left", 0.0), ("right", af.W_IN)):
        pts = []
        for s in segs:
            P = np.float32([(s["x1"] + t * (s["x2"] - s["x1"]), s["y1"] + t * (s["y2"] - s["y1"])) for t in np.linspace(0, 1, 5)])
            lane = af.to_lane(H, P)
            if np.all(np.abs(lane[:, 0] - x0) <= tol_in) and np.all((lane[:, 1] > y_rng[0]) & (lane[:, 1] < y_rng[1])):
                pts += [tuple(p) for p in P]
        if len(pts) >= 6:
            pts = np.array(pts); a, b, resid = af.L.robust_line(pts[:, 1], pts[:, 0])
            out[side] = {"a": float(a), "b": float(b), "n": int(len(pts)), "resid": float(resid), "pts": pts.tolist()}
    return out


def foul_line(segs, H, fdots, tol_in=2.0):
    """Image line of the foul line: LSD segments along y = 0 under H; else the fitted line through the foul-dot row (y = -1.85 in) is NOT used (different y)."""
    pts = []
    for s in segs:
        P = np.float32([(s["x1"] + t * (s["x2"] - s["x1"]), s["y1"] + t * (s["y2"] - s["y1"])) for t in np.linspace(0, 1, 5)])
        lane = af.to_lane(H, P)
        if np.all(np.abs(lane[:, 1]) <= tol_in) and np.all((lane[:, 0] > -6) & (lane[:, 0] < af.W_IN + 6)):
            pts += [tuple(p) for p in P]
    if len(pts) >= 6:
        pts = np.array(pts); a, b, resid = af.L.robust_line(pts[:, 0], pts[:, 1])   # y = a*x + b
        return {"a": float(a), "b": float(b), "n": int(len(pts)), "resid": float(resid)}
    return None


def near_corners(gl, fl):
    """Gutter line x = a*y + b crossed with the foul line y = c*x + d."""
    out = {}
    if not fl:
        return out
    for side in ("left", "right"):
        if side not in gl:
            continue
        a, b = gl[side]["a"], gl[side]["b"]; c, d = fl["a"], fl["b"]
        # x = a*(c*x + d) + b -> x (1 - a c) = a d + b
        den = 1 - a * c
        if abs(den) < 1e-6:
            continue
        x = (a * d + b) / den; y = c * x + d
        out[f"foul_{side}"] = (float(x), float(y))
    return out


# ---------------------------------------------------------------- the joint fit

def joint_fit(rows, pins, corners, gl, variant):
    pts, wp, lines, wl, names = [], [], [], [], []
    if variant != "rows-only" and pins:
        for n, (x, y) in pins.items():
            pts.append(((x, y), CONST[n])); wp.append(1 / SIG["pin"]); names.append(n)
    for cls, rr in rows.items():
        for n, (x, y, _) in rr.items():
            pts.append(((x, y), CONST[n])); wp.append(1 / SIG[cls]); names.append(n)
    if variant not in ("no-near", "rows-only", "rows+pins") and corners:
        for n, (x, y) in corners.items():
            pts.append(((x, y), CONST[n])); wp.append(1 / SIG["corner"]); names.append(n)
    if variant not in ("rows-only", "rows+pins") and gl:
        for side, x0 in (("left", 0.0), ("right", af.W_IN)):
            if side in gl:
                P = gl[side]["pts"]
                step = max(1, len(P) // 12)
                for (x, y) in P[::step]:
                    lines.append(((x, y), x0)); wl.append(1 / SIG["gutter"]); names.append(f"gutter_{side}")
    if len(pts) * 2 + len(lines) < 8 or len(pts) < 3:
        return None, names, []
    H, dropped = LM.fit_robust(pts, lines, wp, wl, thr_in=REJECT_IN, iters=3)
    return H, names, dropped


def run(stem, sname, pooled_pins=None, overlay_frames=()):
    annotated = stem in af.STEMS
    rows_all = af.load(af.PRED / f"face_rows_{stem}.json")[sname]
    with gzip.open(af.PRED / f"cand_{stem}.json.gz", "rt") as fh:
        cands = json.load(fh)
    ph = af.pin_hit(stem) if annotated else None
    per = []
    out_align = {}
    variants = ("rows+pins", "refit", "no-near", "rows-only") + (("pins-pooled",) if pooled_pins else ())
    t_all = []
    for r in rows_all:
        f = r["frame"]
        if "H" not in r:
            per.append({"frame": f, "ok": False, "why": "no right lane from E3"}); continue
        H0 = np.array(r["H"]); img = af.read_frame(stem, f); c = cands[str(f)]
        t0 = time.perf_counter()
        standing = (ph is None) or (f < ph - 1)
        pins, pin_info = refine_pins(img, H0, standing)
        # stage A: arrows (grid-assigned under E3's coarse lane) + the rack -> H_A, a lane whose near end is
        # already far better than E3's; stage B: every row re-detected under H_A; the gutter / foul-line
        # segments are taken within 1.0 in of the rows+pins lane (around E3's coarse lane they picked the
        # gutter lip or the next lane on sample_input)
        mxy = np.array([[m["x"], m["y"]] for m in c["marks"]], np.float32) if c["marks"] else np.zeros((0, 2), np.float32)
        rows = {"arrow": refine_row(mxy, H0, "arrow", img.shape)}
        HA, _, _ = joint_fit(rows, pins, {}, None, "rows+pins")
        HA = HA if HA is not None and np.all(np.isfinite(HA)) and abs(np.linalg.det(HA)) > 1e-12 else H0
        rows = {cls: refine_row(mxy, HA, cls, img.shape) for cls in ROWS}
        if not rows["arrow"]:
            rows["arrow"] = refine_row(mxy, H0, "arrow", img.shape)
        H1, _, _ = joint_fit(rows, pins, {}, None, "rows+pins")
        Hg = H1 if H1 is not None and np.all(np.isfinite(H1)) and abs(np.linalg.det(H1)) > 1e-12 else HA
        gl = gutter_lines(c["segs"], Hg, tol_in=1.0); fl = foul_line(c["segs"], Hg, rows["fdot"], tol_in=1.0); corners = near_corners(gl, fl)
        dt = time.perf_counter() - t0; t_all.append(dt)
        row = {"frame": f, "ok": True, "ms": round(1000 * dt, 0), "n": {cls: len(v) for cls, v in rows.items()}, "pins": pin_info, "gutters": {k: v["n"] for k, v in gl.items()}, "foul_line": bool(fl), "corners": list(corners), "fits": {}}
        out_align[str(f)] = {"rows": {cls: {n: [v[0], v[1]] for n, v in rr.items()} for cls, rr in rows.items()}, "pins": pins, "corners": corners, "gl": {k: {"a": v["a"], "b": v["b"]} for k, v in gl.items()}, "fl": fl}
        for variant in variants:
            pp = pins
            if variant == "pins-pooled":
                pp = {n: tuple(v) for n, v in (pooled_pins.get(str(f)) or {}).items()} or pins
            H, names, dropped = joint_fit(rows, pp, corners, gl, "rows+pins" if variant == "pins-pooled" else variant)
            if H is None or not np.all(np.isfinite(H)):
                row["fits"][variant] = {"ok": False}; continue
            fit = {"ok": True, "n_constraints": len(names), "dropped": dropped[:12], "H": [[float(v) for v in q] for q in H]}
            if annotated:
                y_top, y_bot = af.L.gt_y(stem, f)
                try:
                    cn = LM.corners_from_h(H, y_top, y_bot)
                except Exception:  # noqa: BLE001
                    row["fits"][variant] = {"ok": False}; continue
                if not all(np.isfinite([v for q in cn.values() for v in q])) or cn["top_right"][0] <= cn["top_left"][0]:
                    row["fits"][variant] = {"ok": False}; continue
                sb = af.score_both(stem, f, cn)
                fit.update({"mae": {t: sb[t]["board_mae"] for t in af.TRUTHS}, "tail": {t: sb[t]["board_mae_last20"] for t in af.TRUTHS},
                            "width_err_px_pins": sb["pins"]["top_width_err_px"], "centre_err_px_pins": sb["pins"]["top_centre_err_px"],
                            "near_err_px": {k: sb["all"]["corner_err_px"][k] for k in ("bottom_left", "bottom_right")}, "corners": {k: [round(float(v[0]), 2), round(float(v[1]), 2)] for k, v in cn.items()}})
            row["fits"][variant] = fit
        # E3's own lane on the same frame for reference
        if annotated and "mae" in r:
            row["e3"] = {"mae": r["mae"], "tail": r["tail"], "width_err_px_pins": r.get("width_err_px_pins"), "centre_err_px_pins": r.get("centre_err_px_pins")}
        per.append(row)
        if f in overlay_frames:
            ov = img.copy()
            if annotated:
                t = af.truth_corners(stem, f, "all"); q = np.array([t["top_left"], t["top_right"], t["bottom_right"], t["bottom_left"]], np.int32); cv2.polylines(ov, [q.reshape(-1, 1, 2)], True, (0, 220, 0), 1, cv2.LINE_AA)
            q = af.to_image(H0, [(0, 0), (af.W_IN, 0), (af.W_IN, LM.HEAD_IN), (0, LM.HEAD_IN)]).astype(np.int32); cv2.polylines(ov, [q.reshape(-1, 1, 2)], True, (0, 200, 255), 1, cv2.LINE_AA)
            fit = row["fits"].get("refit", {})
            if fit.get("ok"):
                Hr = np.array(fit["H"]); q = af.to_image(Hr, [(0, 0), (af.W_IN, 0), (af.W_IN, LM.HEAD_IN), (0, LM.HEAD_IN)]).astype(np.int32); cv2.polylines(ov, [q.reshape(-1, 1, 2)], True, (0, 255, 255), 2, cv2.LINE_AA)
            for cls, rr in rows.items():
                for n, (x, y, _) in rr.items():
                    cv2.circle(ov, (int(x), int(y)), 4, (255, 0, 255), 1, cv2.LINE_AA)
            if pins:
                for n, (x, y) in pins.items():
                    cv2.circle(ov, (int(x), int(y)), 2, (0, 140, 255), -1, cv2.LINE_AA)
            for n, (x, y) in corners.items():
                cv2.drawMarker(ov, (int(x), int(y)), (255, 255, 0), cv2.MARKER_CROSS, 14, 2, cv2.LINE_AA)
            for side, g in gl.items():
                ys = np.array([p[1] for p in g["pts"]]); y0, y1 = ys.min(), ys.max(); cv2.line(ov, (int(g["a"] * y0 + g["b"]), int(y0)), (int(g["a"] * y1 + g["b"]), int(y1)), (255, 255, 0), 1, cv2.LINE_AA)
            cv2.putText(ov, f"E4 {af.SHORT[stem]} f{f}: E3 lane orange -> refit yellow (truth green); refined arrows/dots magenta, pins orange dots, gutter lines + near corners cyan", (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            if fit.get("ok") and annotated:
                cv2.putText(ov, f"board MAE vs pins: E3 {r.get('mae', {}).get('pins')} -> refit {fit['mae']['pins']}   near-corner err px {fit['near_err_px']}", (8, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            cv2.imwrite(str(af.OVERLAYS / f"e4_align_{stem}_f{f}.jpg"), ov, [cv2.IMWRITE_JPEG_QUALITY, 88])
    with gzip.open(af.PRED / f"align_{stem}.json.gz", "wt") as fh:
        json.dump(out_align, fh)
    # summaries
    summ = {"frames": len(per), "aligned": sum(1 for r in per if r["ok"]), "ms_median": round(float(np.median(t_all)) * 1000, 0) if t_all else None,
            "rows_found_median": {cls: float(np.median([r["n"][cls] for r in per if r["ok"]])) for cls in ROWS} if any(r["ok"] for r in per) else None,
            "pins_ok_frac_standing": round(float(np.mean([r["pins"]["ok"] for r in per if r["ok"] and r["pins"] and "ok" in r["pins"]])), 3) if any(r["ok"] and r["pins"] and "ok" in r["pins"] for r in per) else None,
            "corners_both_frac": round(float(np.mean([len(r["corners"]) == 2 for r in per if r["ok"]])), 3) if any(r["ok"] for r in per) else None}
    if annotated:
        throw = set(af.throw_frames(stem)); fl_ = af.L.frame_indices(stem, "last")[0]
        for variant in ("e3",) + variants:
            rows_ = []
            for r in per:
                if not r["ok"]:
                    continue
                v = r["e3"] if variant == "e3" else r["fits"].get(variant, {})
                if v and v.get("mae"):
                    rows_.append((r["frame"], v))
            s = {"ok": len(rows_)}
            rt = [(f, v) for f, v in rows_ if f in throw]
            for t in af.TRUTHS:
                s[f"throw_median_{t}"] = round(float(np.median([v["mae"][t] for _, v in rt])), 2) if rt else None
                s[f"tail_median_{t}"] = round(float(np.median([v["tail"][t] for _, v in rt])), 2) if rt else None
                s[f"prehit_{t}"] = next((v["mae"][t] for f, v in rows_ if f == ph - 2), None)
                s[f"last_{t}"] = next((v["mae"][t] for f, v in rows_ if f == fl_), None)
            s["far_width_err_px_medabs_pins"] = round(float(np.median([abs(v["width_err_px_pins"]) for _, v in rt if v.get("width_err_px_pins") is not None])), 2) if rt else None
            s["far_centre_err_px_medabs_pins"] = round(float(np.median([abs(v["centre_err_px_pins"]) for _, v in rt if v.get("centre_err_px_pins") is not None])), 2) if rt else None
            if variant != "e3":
                ne = [v["near_err_px"] for _, v in rt if "near_err_px" in v]
                s["near_corner_err_px_median"] = {k: round(float(np.median([x[k] for x in ne])), 2) for k in ("bottom_left", "bottom_right")} if ne else None
            summ[variant] = s
            print(f"E4 {af.SHORT[stem]:13s} [{sname}] {variant:12s} ok {s['ok']} | throw med ann/pins/all {s['throw_median_annotated']}/{s['throw_median_pins']}/{s['throw_median_all']} tail(pins) {s['tail_median_pins']} | prehit {s['prehit_pins']} last {s['last_pins']} | far width {s['far_width_err_px_medabs_pins']} centre {s['far_centre_err_px_medabs_pins']} | near px {s.get('near_corner_err_px_median')}", flush=True)
    af.dump(af.RESULTS / f"e4_align_{stem}.json", {"stem": stem, "set": sname, "summary": summ, "per_frame": [{k: (v if k != "fits" else {vn: {kk: vv for kk, vv in fit.items() if kk not in ("H", "corners")} for vn, fit in v.items()}) for k, v in r.items()} for r in per]})
    af.dump(af.PRED / f"align_rows_{stem}.json", per)
    return summ


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--set", default="arrows+dots+rack+gutters"); ap.add_argument("stems", nargs="*")
    a = ap.parse_args()
    for stem in (a.stems or af.STEMS):
        pooled = None
        pp = af.PRED / f"pooled_pins_{stem}.json"
        if pp.exists():
            pooled = json.loads(pp.read_text())
        fp = af.frame_for(stem, "prehit") if stem in af.STEMS else None
        run(stem, a.set, pooled, overlay_frames=(fp, fp - 60, fp - 120) if fp else ())
