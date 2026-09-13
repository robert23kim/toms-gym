"""E2: feature candidates over the whole frame with no lane prior. Three cheap detectors per
frame: dark marks (multi-scale black-hat: arrows, dots), white columns (pin bodies), line segments
(LSD: foul line, gutter edges). On the annotated videos each candidate is matched to the
constellation projected through that frame's truth homography (tolerance = 1.5 lane inches at the
local scale, at least 4 px) and precision / recall per class are reported; the raw pool is what the
constellation match (E3) has to beat. Candidates go to $AF_SCRATCH/pred/cand_<stem>.json.gz (E3's
input), stats to results/e2_candidates_<stem>.json, overlays/e2_cand_<stem>_f<f>.jpg.
usage: e2_candidates.py [--step N] [stems...]"""
import argparse
import gzip
import json
import time

import cv2
import numpy as np

import af

LM = af.LM


# ---------------------------------------------------------------- detectors

def dark_marks(gray, ks=(9, 17, 29), area=(3, 400), max_dim=40, max_aspect=5.0):
    """Two tiers: strong (median + 6 MAD, >= 12 grey levels) and weak (>= 8 levels, flagged weak=1;
    the faint 7-ft guide dots at 688p live there)."""
    g = gray
    acc = np.zeros(g.shape, np.float32)
    for k in ks:
        ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
        bh = cv2.morphologyEx(g, cv2.MORPH_BLACKHAT, ker).astype(np.float32)
        acc = np.maximum(acc, bh)
    med = float(np.median(acc)); mad = float(np.median(np.abs(acc - med))) + 1e-6
    thr = max(12.0, med + 6.0 * mad); thr_weak = max(8.0, med + 4.0 * mad)
    out = []
    seen = np.zeros(g.shape, bool)
    for tier, t in (("strong", thr), ("weak", thr_weak)):
        m = (acc > t).astype(np.uint8)
        n, lab, stats, cent = cv2.connectedComponentsWithStats(m, 8)
        for i in range(1, n):
            x, y, w, h, a = stats[i]
            if a < area[0] or a > area[1] or max(w, h) > max_dim or max(w, h) / max(1, min(w, h)) > max_aspect:
                continue
            ys, xs = np.where(lab[y:y + h, x:x + w] == i)
            if tier == "weak" and seen[y + ys, x + xs].any():
                continue
            seen[y + ys, x + xs] = True
            wts = acc[y + ys, x + xs]
            out.append({"x": float(x + (xs * wts).sum() / wts.sum()), "y": float(y + (ys * wts).sum() / wts.sum()), "a": int(a), "d": round(float(wts.mean()), 1), "w": int(w), "h": int(h), "weak": int(tier == "weak")})
    return out, thr


def white_columns(img, thr=0.5, h_rng=(5, 90), w_rng=(2, 40), min_aspect=1.15):
    """Isolated white columns (single pin bodies where the rack is resolved; also the neighbouring
    lanes' pins). Kept for the record; the rack blobs below are what E3 uses."""
    wmap = LM.white_map(img)
    m = (wmap > thr).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    n, lab, stats, cent = cv2.connectedComponentsWithStats(m, 8)
    out = []
    for i in range(1, n):
        x, y, w, h, a = stats[i]
        if not (h_rng[0] <= h <= h_rng[1] and w_rng[0] <= w <= w_rng[1] and h / w >= min_aspect and a >= 0.35 * w * h):
            continue
        out.append({"x": float(cent[i][0]), "yb": float(y + h), "yt": float(y), "w": int(w), "h": int(h), "a": int(a)})
    return out


def white_racks(img, thr=0.45, w_rng=(16, 320), min_fill=0.35):
    """Rack candidates = white blobs with the proportions of a ten-pin rack seen from the approach:
    at these resolutions the staggered rows merge into one white mass ~40.8 in wide (pin 7 to pin 10
    outer bellies) and 15 in tall, often doubled downward by the pins' reflection on the deck. So the
    blob's top edge and width are the measurements: px/in = w / 40.8, base row = top + 15 in. Kept:
    w in w_rng, 0.2 w <= h <= 1.3 w, fill >= min_fill."""
    wmap = LM.white_map(img)
    m = (wmap > thr).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((1, 5), np.uint8))
    n, lab, stats, cent = cv2.connectedComponentsWithStats(m, 8)
    out = []
    for i in range(1, n):
        x, y, w, h, a = stats[i]
        if not (w_rng[0] <= w <= w_rng[1] and 0.2 * w <= h <= 1.3 * w and a >= min_fill * w * h):
            continue
        ppi = w / 40.8
        out.append({"cx": float(x + w / 2), "top": float(y), "bot": float(y + h), "w": int(w), "h": int(h), "fill": round(float(a / (w * h)), 2), "ppi": round(float(ppi), 3), "base_y": float(y + 15.0 * ppi)})
    return out


_lsd = None


def line_segments(gray, min_len_frac=0.05):
    global _lsd
    if _lsd is None:
        _lsd = cv2.createLineSegmentDetector(cv2.LSD_REFINE_STD)
    lines = _lsd.detect(gray)[0]
    out = []
    if lines is None:
        return out
    min_len = min_len_frac * gray.shape[0]
    for (x1, y1, x2, y2) in lines.reshape(-1, 4):
        ln = float(np.hypot(x2 - x1, y2 - y1))
        if ln >= min_len:
            out.append({"x1": float(x1), "y1": float(y1), "x2": float(x2), "y2": float(y2), "len": round(ln, 1)})
    return out


# ---------------------------------------------------------------- truth matching

def local_ppi(H, x_in, y_in):
    p = af.to_image(H, [(x_in, y_in), (x_in + 1.0, y_in)])
    return float(np.hypot(*(p[1] - p[0])))


def match_points(cands, truth_pts, H, tol_in=1.5, min_px=4.0, key=("x", "y")):
    """Greedy nearest match of candidates to truth points. Returns (matched candidate idx per truth name, n_true_candidates)."""
    if not cands:
        return {}, 0
    cx = np.array([c[key[0]] for c in cands]); cy = np.array([c[key[1]] for c in cands])
    used = set(); matched = {}
    for name, (tx, ty) in truth_pts.items():
        x_in, y_in = af.constellation()[name]
        tol = max(min_px, tol_in * local_ppi(H, x_in, y_in))
        d = np.hypot(cx - tx, cy - ty)
        order = np.argsort(d)
        for i in order[:5]:
            if d[i] > tol:
                break
            if i in used:
                continue
            used.add(int(i)); matched[name] = int(i); break
    return matched, len(used)


LINE_X = {"gutter_left": 0.0, "gutter_right": af.W_IN, "neighbour_left": -9.25, "neighbour_right": af.W_IN + 9.25}


def match_segments(segs, H, tol_in=1.5):
    """Which constellation line each segment lies on (sampled points within tol_in of x = const lane
    lines between the approach and the deck, or of the foul line y = 0)."""
    labels = []
    for s in segs:
        pts = [(s["x1"] + t * (s["x2"] - s["x1"]), s["y1"] + t * (s["y2"] - s["y1"])) for t in np.linspace(0, 1, 7)]
        lane = af.to_lane(H, pts)
        lab = None
        if np.all(np.abs(lane[:, 1]) <= tol_in) and np.all((lane[:, 0] > -6) & (lane[:, 0] < af.W_IN + 6)):
            lab = "foul_line"
        else:
            for name, x0 in LINE_X.items():
                if np.all(np.abs(lane[:, 0] - x0) <= tol_in) and np.all((lane[:, 1] > -40) & (lane[:, 1] < 780)):
                    lab = name; break
        labels.append(lab)
    return labels


# ---------------------------------------------------------------- per video

def run(stem, step=1, overlay_frames=()):
    annotated = stem in af.STEMS
    frames = af.frame_ids(stem)[::step]
    tl = af.load(af.RESULTS / f"e1_timeline_{stem}.json")["per_frame"] if annotated else None
    tl = {r["frame"]: r["status"] for r in tl} if tl else None
    cands = {}
    stats = []
    t_all = []
    for f in frames:
        img = af.read_frame(stem, f); gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        t0 = time.perf_counter()
        marks, thr = dark_marks(gray); cols = white_columns(img); racks = white_racks(img); segs = line_segments(gray)
        t_all.append(time.perf_counter() - t0)
        cands[str(f)] = {"marks": marks, "cols": cols, "racks": racks, "segs": segs}
        row = {"frame": f, "n_marks": len(marks), "n_strong": sum(1 for m in marks if not m["weak"]), "n_cols": len(cols), "n_racks": len(racks), "n_segs": len(segs), "ms": round(1000 * t_all[-1], 0)}
        if annotated:
            H = af.truth_h(stem, f, "all"); tp = af.truth_points_v(stem, f)
            clear = {n for n, s in tl[f].items() if s == "clear"}
            mark_targets = {n: p for n, p in tp.items() if af.classes_of(n) in ("arrow", "dot", "fdot", "adot")}
            mm, n_true_marks = match_points(marks, mark_targets, H)
            pin_targets = {n: p for n, p in tp.items() if af.classes_of(n) == "pin"}
            pm, n_true_cols = match_points(cols, pin_targets, H, tol_in=2.0, key=("x", "yb"))
            # rack candidates: centre within 3 in of the rack centre at the base row, width within 25 % of the 40.8 in body span
            r7, r10 = tp["pin_7_base"], tp["pin_10_base"]; rc = (0.5 * (r7[0] + r10[0]), 0.5 * (r7[1] + r10[1])); ppi_r = local_ppi(H, af.W_IN / 2, LM.HEAD_IN)
            rack_true = [i for i, r in enumerate(racks) if abs(r["cx"] - rc[0]) <= 3.0 * ppi_r and abs(r["base_y"] - rc[1]) <= 5.0 * ppi_r and 0.7 <= r["w"] / (40.8 * ppi_r) <= 1.35]
            labs = match_segments(segs, H)
            row["marks_true"] = n_true_marks; row["cols_true"] = n_true_cols; row["racks_true"] = len(rack_true); row["rack_found"] = int(bool(rack_true))
            row["marks_true_strong"] = sum(1 for n, i in mm.items() if not marks[i]["weak"])
            row["segs_true"] = {k: sum(1 for l in labs if l == k) for k in list(LINE_X) + ["foul_line"]}
            row["recall"] = {}
            for cls in ("arrow", "dot", "fdot", "adot"):
                names = [n for n in mark_targets if af.classes_of(n) == cls and n in clear]
                row["recall"][cls] = {"clear": len(names), "found": sum(1 for n in names if n in mm)}
            names = [n for n in pin_targets if n in clear]
            row["recall"]["pin"] = {"clear": len(names), "found": sum(1 for n in names if n in pm)}
            row["px_err"] = {cls: [round(float(np.hypot(marks[mm[n]]["x"] - tp[n][0], marks[mm[n]]["y"] - tp[n][1])), 2) for n in mm if af.classes_of(n) == cls] for cls in ("arrow", "dot", "fdot", "adot")}
            row["matched"] = {"marks": mm, "cols": pm, "racks": rack_true, "seg_labels": labs}
        stats.append(row)
        if f in overlay_frames:
            ov = img.copy()
            for s in segs:
                cv2.line(ov, (int(s["x1"]), int(s["y1"])), (int(s["x2"]), int(s["y2"])), (200, 200, 0), 1, cv2.LINE_AA)
            for c in cols:
                cv2.rectangle(ov, (int(c["x"] - c["w"] / 2), int(c["yt"])), (int(c["x"] + c["w"] / 2), int(c["yb"])), (255, 120, 0), 1)
            for r in racks:
                cv2.rectangle(ov, (int(r["cx"] - r["w"] / 2), int(r["top"])), (int(r["cx"] + r["w"] / 2), int(r["bot"])), (255, 0, 255), 2)
            for m in marks:
                cv2.circle(ov, (int(m["x"]), int(m["y"])), 4, (0, 0, 255) if not m["weak"] else (0, 120, 255), 1, cv2.LINE_AA)
            if annotated:
                for n, (tx, ty) in tp.items():
                    cv2.circle(ov, (int(tx), int(ty)), 6, (0, 255, 0), 1, cv2.LINE_AA)
            cv2.putText(ov, f"E2 {af.SHORT[stem]} f{f}: dark marks red/orange=weak ({len(marks)}), white columns orange ({len(cols)}), racks magenta ({len(racks)}), segments yellow ({len(segs)}); green = truth", (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
            cv2.imwrite(str(af.OVERLAYS / f"e2_cand_{stem}_f{f}.jpg"), ov, [cv2.IMWRITE_JPEG_QUALITY, 88])
    with gzip.open(af.PRED / f"cand_{stem}.json.gz", "wt") as fh:
        json.dump(cands, fh)
    summ = {"frames": len(stats), "ms_median": round(1000 * float(np.median(t_all)), 0),
            "marks_per_frame": round(float(np.mean([r["n_marks"] for r in stats])), 1), "strong_marks_per_frame": round(float(np.mean([r["n_strong"] for r in stats])), 1), "racks_per_frame": round(float(np.mean([r["n_racks"] for r in stats])), 1), "cols_per_frame": round(float(np.mean([r["n_cols"] for r in stats])), 1), "segs_per_frame": round(float(np.mean([r["n_segs"] for r in stats])), 1)}
    if annotated:
        summ["marks_precision"] = round(float(np.sum([r["marks_true"] for r in stats]) / max(1, np.sum([r["n_marks"] for r in stats]))), 4)
        summ["cols_precision"] = round(float(np.sum([r["cols_true"] for r in stats]) / max(1, np.sum([r["n_cols"] for r in stats]))), 4)
        summ["marks_precision_strong"] = round(float(np.sum([r["marks_true_strong"] for r in stats]) / max(1, np.sum([r["n_strong"] for r in stats]))), 4)
        ph = af.pin_hit(stem); standing = [r for r in stats if r["frame"] < ph]
        summ["racks_precision"] = round(float(np.sum([r["racks_true"] for r in stats]) / max(1, np.sum([r["n_racks"] for r in stats]))), 4)
        summ["rack_recall_standing"] = round(float(np.mean([r["rack_found"] for r in standing])), 3) if standing else None
        summ["segs_true_per_frame"] = {k: round(float(np.mean([r["segs_true"][k] for r in stats])), 2) for k in list(LINE_X) + ["foul_line"]}
        summ["recall"] = {}
        for cls in ("arrow", "dot", "fdot", "adot", "pin"):
            c = sum(r["recall"][cls]["clear"] for r in stats); fd = sum(r["recall"][cls]["found"] for r in stats)
            summ["recall"][cls] = {"clear_total": c, "found": fd, "recall": round(fd / c, 3) if c else None,
                                   "px_err_median": round(float(np.median([e for r in stats for e in r["px_err"].get(cls, [])])), 2) if cls != "pin" and any(r["px_err"].get(cls) for r in stats) else None}
    af.dump(af.RESULTS / f"e2_candidates_{stem}.json", {"stem": stem, "step": step, "summary": summ, "per_frame": [{k: v for k, v in r.items() if k != "matched"} for r in stats]})
    print(f"E2 {af.SHORT[stem]:13s} frames {len(stats)} {summ['ms_median']:.0f} ms | marks {summ['marks_per_frame']}/frame cols {summ['cols_per_frame']} segs {summ['segs_per_frame']}"
          + (f" racks {summ['racks_per_frame']} | precision marks {summ['marks_precision']:.3f} (strong {summ['marks_precision_strong']:.3f}) racks {summ['racks_precision']:.3f} rack recall {summ['rack_recall_standing']} | recall " + " ".join(f"{c}:{v['recall']}" for c, v in summ["recall"].items()) + f" | true segs/frame {summ['segs_true_per_frame']}" if annotated else ""), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--step", type=int, default=1); ap.add_argument("stems", nargs="*")
    a = ap.parse_args()
    for stem in (a.stems or af.ALL_STEMS):
        if stem in af.STEMS:
            fp = af.frame_for(stem, "prehit"); occ = af.C4.occluded_frames(stem)
            ov = (fp, occ[len(occ) // 2], af.L.frame_indices(stem, "mid")[0])
            run(stem, 1, ov)
        else:
            ids = af.frame_ids(stem)
            run(stem, max(a.step, 3), (ids[len(ids) // 4], ids[len(ids) // 2]))
