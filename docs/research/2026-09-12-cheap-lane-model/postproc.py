"""Post-processing on a student's saved per-frame masks, no re-inference:

  ransac   - per-row left/right extremes of the anchored component, RANSAC line
             per edge (2-row samples, 3 px inliers), least squares on inliers.
  window   - median of the RANSAC line parameters over +-k frames (k=5).
  video    - one lane per video: median over clean frames (the SAM loops' setting).

Scores each variant with the loop-1 metric and writes
results/<run>_<variant>__<stem>.json (+ pred/lines_<run>_<variant>_<stem>.json).
usage: postproc.py <run> <stem> [--k 5]
"""
import argparse
import json

import numpy as np

import common as C

L = C.L
C.use_full_camera()
PRED = C.SCRATCH / "pred"


def ransac_line(ys, xs, thr=3.0, iters=200, seed=0):
    ys = np.asarray(ys, float); xs = np.asarray(xs, float)
    n = len(ys)
    if n < 10:
        return None
    rng = np.random.default_rng(seed)
    best, best_in = None, None
    for _ in range(iters):
        i, j = rng.choice(n, 2, replace=False)
        if abs(ys[i] - ys[j]) < 5:
            continue
        a = (xs[i] - xs[j]) / (ys[i] - ys[j]); b = xs[i] - a * ys[i]
        inl = np.abs(xs - (a * ys + b)) <= thr
        if best is None or inl.sum() > best_in.sum():
            best, best_in = (a, b), inl
    if best is None or best_in.sum() < 10:
        return None
    a, b = np.polyfit(ys[best_in], xs[best_in], 1)
    resid = float(np.mean(np.abs(xs[best_in] - (a * ys[best_in] + b))))
    return (a, b), resid, float(best_in.mean())


def fit_ransac(mask, y_top, y_bot, anchors):
    m = L.largest_component(mask, anchors)
    if m is None:
        return None
    ys, ls, rs = [], [], []
    for y in range(int(y_top), int(y_bot) + 1):
        if 0 <= y < m.shape[0]:
            xs = np.where(m[y])[0]
            if len(xs) >= 5:
                ys.append(y); ls.append(xs.min()); rs.append(xs.max())
    lf = ransac_line(ys, ls); rf = ransac_line(ys, rs)
    if lf is None or rf is None:
        return None
    return lf[0], rf[0], {"fit_resid_px": round((lf[1] + rf[1]) / 2, 2), "inlier_frac": round(min(lf[2], rf[2]), 2), "rows": len(ys)}


def main(run, stem, k=5):
    labeled = stem in C.STEMS
    z = np.load(PRED / f"masks_{run}_{stem}.npz")
    shape = tuple(int(v) for v in z["shape"])
    base = json.loads((C.RESULTS / f"{run}__{stem}.json").read_text())
    conf = {r["frame"]: r["conf"] for r in base["per_frame"]}
    frames = C.frame_ids(stem)
    fits = {}
    for f in frames:
        if str(f) not in z.files:
            continue
        mask = np.unpackbits(z[str(f)])[: shape[0] * shape[1]].reshape(shape).astype(np.uint8)
        if labeled:
            y_top, y_bot = L.gt_y(stem, f); anchors = L.ball_points_on(stem, f)
        else:
            ys = np.where(mask.any(1))[0]
            if len(ys) < 20:
                continue
            y_top, y_bot = int(ys.min()) + 2, int(ys.max()) - 2; anchors = None
        fit = fit_ransac(mask, y_top, y_bot, anchors)
        if fit is not None:
            fits[f] = (fit[0], fit[1], fit[2], y_top, y_bot)
    variants = {"ransac": {}, "window": {}, "video": {}, "gated": {}}
    keys = sorted(fits)
    for f in keys:
        variants["ransac"][f] = (fits[f][0], fits[f][1])
    # window median
    for f in keys:
        near = [g for g in keys if abs(g - f) <= k and fits[g][2]["inlier_frac"] >= 0.5]
        if not near:
            near = [f]
        A = np.array([[fits[g][0][0], fits[g][0][1], fits[g][1][0], fits[g][1][1]] for g in near])
        med = np.median(A, 0)
        variants["window"][f] = ((med[0], med[1]), (med[2], med[3]))
    # one lane per video from clean frames (labeled: loop-1 clean set; else frames with good fits)
    pool = [g for g in keys if (g in set(C.clean_frames(stem)) if labeled else True) and fits[g][2]["inlier_frac"] >= 0.5 and conf.get(g, 0) >= 0.1]
    if len(pool) >= 3:
        A = np.array([[fits[g][0][0], fits[g][0][1], fits[g][1][0], fits[g][1][1]] for g in pool]); med = np.median(A, 0)
        for f in keys:
            variants["video"][f] = ((med[0], med[1]), (med[2], med[3]))

    # gated: reject frames that fail a sanity check, carry the nearest accepted lane
    def sane(f):
        left, right = fits[f][0], fits[f][1]; y_top, y_bot = fits[f][3], fits[f][4]
        c = L.lines_to_corners(left, right, y_top, y_bot)
        tw = c["top_right"][0] - c["top_left"][0]; bw = c["bottom_right"][0] - c["bottom_left"][0]
        return fits[f][2]["inlier_frac"] >= 0.7 and tw > 0 and bw > tw and fits[f][2]["rows"] >= 0.6 * (y_bot - y_top)
    acc = [f for f in keys if sane(f)]
    # centre-jump rule (loop 2): a lane whose foul-line centre sits far from the video's
    # median centre is the neighbouring lane, not a bad fit
    if acc:
        def centre_w(f):
            c = L.lines_to_corners(fits[f][0], fits[f][1], fits[f][3], fits[f][4])
            return (c["bottom_left"][0] + c["bottom_right"][0]) / 2, c["bottom_right"][0] - c["bottom_left"][0]
        cw = {f: centre_w(f) for f in acc}
        ref_c = float(np.median([v[0] for v in cw.values()])); ref_w = float(np.median([v[1] for v in cw.values()]))
        acc = [f for f in acc if abs(cw[f][0] - ref_c) <= 0.3 * ref_w]
    if acc:
        med = {}
        for f in acc:
            near = [g for g in acc if abs(g - f) <= k]
            A = np.array([[fits[g][0][0], fits[g][0][1], fits[g][1][0], fits[g][1][1]] for g in near]); m_ = np.median(A, 0)
            med[f] = ((m_[0], m_[1]), (m_[2], m_[3]))
        for f in frames:
            g = min(acc, key=lambda q: abs(q - f))
            variants["gated"][f] = med[g]
    variants["gate_rate"] = len(acc) / max(1, len(keys))
    gate_rate = variants.pop("gate_rate", None)
    for name, lines in variants.items():
        if not lines:
            continue
        per, save = [], {}
        for f in frames:
            row = {"frame": f, "conf": conf.get(f, 0.0), "ok": f in lines}
            if f in lines:
                left, right = lines[f]
                src_f = f if f in fits else min(fits, key=lambda q: abs(q - f))
                y_top, y_bot = (L.gt_y(stem, f) if labeled else (fits[src_f][3], fits[src_f][4]))
                corners = L.lines_to_corners(left, right, y_top, y_bot)
                save[str(f)] = {"left": [float(left[0]), float(left[1])], "right": [float(right[0]), float(right[1])], "y": [y_top, y_bot],
                                "corners": {q: [round(float(v[0]), 1), round(float(v[1]), 1)] for q, v in corners.items()}}
                row["fit_resid_px"] = fits[src_f][2]["fit_resid_px"]; row["inlier_frac"] = fits[src_f][2]["inlier_frac"]; row["carried"] = f not in fits
                if labeled:
                    row.update(L.score(stem, corners, f))
            per.append(row)
        (PRED / f"lines_{run}_{name}_{stem}.json").write_text(json.dumps(save))
        out = dict(base); out.update({"method": f"{run}_{name}", "postproc": name, "per_frame": per, "frames_ok": int(sum(r["ok"] for r in per)), "gate_rate": gate_rate})
        if labeled:
            throw = set(C.throw_frames(stem)); clean = set(C.clean_frames(stem)); occ = set(C.occluded_frames(stem))
            sel = lambda S: [r for r in per if r["frame"] in S]  # noqa: E731
            out["throw"] = C.summarize(sel(throw)); out["clean"] = C.summarize(sel(clean)); out["occluded"] = C.summarize(sel(occ)); out["all_frames"] = C.summarize(per)
            for nm, ff in (("last", L.frame_indices(stem, "last")[0]), ("prehit", L.pin_hit_frame(stem) - 2)):
                r = next((r for r in per if r["frame"] == ff), None)
                out[nm] = {"frame": ff, "board_mae": r.get("board_mae") if r else None}
            out["perframe_mae_mean"] = out["throw"]["mean"]; out["perframe_mae_median"] = out["throw"]["median"]; out["perframe_within_2"] = out["throw"]["within_2"]
            print(f"{run}_{name:7s} {C.SHORT[stem]:13s} ok {out['frames_ok']}/{len(per)}  throw {out['throw']['mean']}/{out['throw']['median']}  clean {out['clean']['mean']}/{out['clean']['median']}  occl {out['occluded']['mean']}/{out['occluded']['median']}  last {out['last']['board_mae']}  prehit {out['prehit']['board_mae']}  <=2: {out['throw']['within_2']}%")
        else:
            print(f"{run}_{name} {stem} ok {out['frames_ok']}/{len(per)}")
        C.dump(C.RESULTS / f"{run}_{name}__{stem}.json", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("run"); ap.add_argument("stem"); ap.add_argument("--k", type=int, default=5)
    a = ap.parse_args(); main(a.run, a.stem, a.k)
