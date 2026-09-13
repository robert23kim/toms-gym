"""E6 evaluation: the heatmap model's detections on the held-out video vs the constellation truth
(recall / precision / px error per class on the frames where the point is clear), against the
classical E2 detectors on the same frames; then the constellation fitted from the model's
detections alone (landmark variant: named points -> one weighted DLT; class variant: names assigned
by E3's chain logic is out of scope, reported as class-level recall only) against both truths and
against E4. Also the in-distribution number on the training videos' held-back frames, so a
model that does not fire on the held-out video is reported beside what it does at home.
usage: e6_eval.py [fold ...]"""
import json
import sys

import numpy as np

import af
import e6_heatmap as E6

LM = af.LM
CONST = af.constellation()
TOL_PX = 6.0


def evaluate(stem, pred, variant, frames):
    tl = {r["frame"]: r["status"] for r in af.load(af.RESULTS / f"e1_timeline_{stem}.json")["per_frame"]}
    ph = af.pin_hit(stem)
    per_cls = {c: {"clear": 0, "found": 0, "px": [], "n_det": 0} for c in E6.CLASSES}
    fit_rows = []
    for f in frames:
        dets = pred["per_frame"].get(str(f))
        if dets is None:
            continue
        tp = af.truth_points_v(stem, f)
        for c in E6.CLASSES:
            per_cls[c]["n_det"] += sum(1 for d in dets if af.classes_of(d["name"]) == c or d["name"] == c)
        used = set()
        matched = {}
        for n, (tx, ty) in tp.items():
            c = af.classes_of(n)
            if tl[f][n] != "clear" or (c == "pin" and f >= ph):
                continue
            per_cls[c]["clear"] += 1
            cands = [(i, d) for i, d in enumerate(dets) if i not in used and ((d["name"] == n) if variant == "landmark" else (d["name"] == c))]
            if not cands:
                continue
            i, d = min(cands, key=lambda t: np.hypot(t[1]["x"] - tx, t[1]["y"] - ty))
            e = float(np.hypot(d["x"] - tx, d["y"] - ty))
            if e <= TOL_PX:
                used.add(i); per_cls[c]["found"] += 1; per_cls[c]["px"].append(e); matched[n] = (d["x"], d["y"])
        # constellation fit from the named detections (landmark variant): all points with conf >= 0.3, robust DLT
        if variant == "landmark":
            pts, w, names = [], [], []
            for d in dets:
                if d["conf"] < 0.3 or d["name"] not in CONST:
                    continue
                c = af.classes_of(d["name"])
                if c == "pin" and f >= ph:
                    continue
                pts.append(((d["x"], d["y"]), CONST[d["name"]])); w.append(1 / {"pin": 0.45, "arrow": 0.7, "dot": 0.7, "fdot": 0.7, "adot": 1.0, "foul": 1.0}[c]); names.append(d["name"])
            # one detection per name: keep the most confident
            best = {}
            for (p, q), ww, n, d in zip(pts, w, names, [d for d in dets if d["conf"] >= 0.3 and d["name"] in CONST and not (af.classes_of(d["name"]) == "pin" and f >= ph)]):
                if n not in best or d["conf"] > best[n][2]:
                    best[n] = ((p, q), ww, d["conf"])
            pts = [v[0] for v in best.values()]; w = [v[1] for v in best.values()]
            row = {"frame": f, "n_named": len(pts)}
            if len(pts) >= 5:
                H, dropped = LM.fit_robust(pts, [], w, [], thr_in=2.5, iters=3)
                if H is not None and np.all(np.isfinite(H)):
                    y_top, y_bot = af.L.gt_y(stem, f)
                    try:
                        cn = LM.corners_from_h(H, y_top, y_bot)
                        if cn["top_right"][0] > cn["top_left"][0]:
                            sb = af.score_both(stem, f, cn)
                            row.update({"ok": True, "mae": {t: sb[t]["board_mae"] for t in af.TRUTHS}, "tail": {t: sb[t]["board_mae_last20"] for t in af.TRUTHS}, "dropped": len(dropped), "width_err_px_pins": sb["pins"]["top_width_err_px"]})
                    except Exception:  # noqa: BLE001
                        pass
            fit_rows.append(row)
    out = {"per_class": {c: {"clear": v["clear"], "found": v["found"], "recall": round(v["found"] / v["clear"], 3) if v["clear"] else None,
                             "detections": v["n_det"], "precision": round(v["found"] / v["n_det"], 3) if v["n_det"] else None,
                             "px_err_median": round(float(np.median(v["px"])), 2) if v["px"] else None} for c, v in per_cls.items()}}
    if fit_rows:
        throw = set(af.throw_frames(stem)); ok = [r for r in fit_rows if r.get("ok")]; rt = [r for r in ok if r["frame"] in throw]
        out["fit"] = {"frames": len(fit_rows), "ok": len(ok), "ok_in_throw": len(rt), "n_named_median": float(np.median([r["n_named"] for r in fit_rows]))}
        for t in af.TRUTHS:
            out["fit"][f"throw_median_{t}"] = round(float(np.median([r["mae"][t] for r in rt])), 2) if rt else None
            out["fit"][f"tail_median_{t}"] = round(float(np.median([r["tail"][t] for r in rt])), 2) if rt else None
            out["fit"][f"prehit_{t}"] = next((r["mae"][t] for r in ok if r["frame"] == ph - 2), None)
        out["fit"]["far_width_err_px_medabs_pins"] = round(float(np.median([abs(r["width_err_px_pins"]) for r in rt])), 2) if rt else None
        out["fit_rows"] = fit_rows
    return out


def classical(stem, frames):
    """E2's classical detectors on the same frames, same tolerance, from results/e2_candidates (recall) - re-matched at 6 px."""
    import gzip
    with gzip.open(af.PRED / f"cand_{stem}.json.gz", "rt") as fh:
        cands = json.load(fh)
    tl = {r["frame"]: r["status"] for r in af.load(af.RESULTS / f"e1_timeline_{stem}.json")["per_frame"]}
    ph = af.pin_hit(stem)
    per = {c: {"clear": 0, "found": 0, "px": [], "n_det": 0} for c in ("arrow", "dot", "fdot", "adot")}
    for f in frames:
        c = cands.get(str(f))
        if not c:
            continue
        mx = np.array([m["x"] for m in c["marks"]]); my = np.array([m["y"] for m in c["marks"]])
        tp = af.truth_points_v(stem, f)
        for cls in per:
            per[cls]["n_det"] += len(mx)
        for n, (tx, ty) in tp.items():
            cls = af.classes_of(n)
            if cls not in per or tl[f][n] != "clear":
                continue
            per[cls]["clear"] += 1
            if len(mx):
                d = np.hypot(mx - tx, my - ty); k = int(np.argmin(d))
                if d[k] <= TOL_PX:
                    per[cls]["found"] += 1; per[cls]["px"].append(float(d[k]))
    return {c: {"clear": v["clear"], "found": v["found"], "recall": round(v["found"] / v["clear"], 3) if v["clear"] else None, "px_err_median": round(float(np.median(v["px"])), 2) if v["px"] else None, "marks_per_frame": round(v["n_det"] / max(1, len(frames)), 1)} for c, v in per.items()}


if __name__ == "__main__":
    folds = sys.argv[1:] or list(E6.folds())
    out = {}
    for fold in folds:
        fd = E6.folds()[fold]; held = fd["held"]
        for variant in ("landmark", "class"):
            p = af.PRED / f"heat_{variant}_{fold}__{held}.json"
            if not p.exists():
                print("missing", p); continue
            pred = json.loads(p.read_text())
            frames = sorted(int(k) for k in pred["per_frame"])
            res = {"held_out": evaluate(held, pred, variant, frames), "ms_median": pred["ms_median"]}
            # in-distribution: training videos' val frames
            ind = {}
            for s in fd["val"]:
                pv = af.PRED / f"heat_{variant}_{fold}__{s}.json"
                if pv.exists():
                    pr = json.loads(pv.read_text()); fr = [f for f in fd["val"][s] if str(f) in pr["per_frame"]]
                    ind[s] = {k: v for k, v in evaluate(s, pr, variant, fr).items() if k != "fit_rows"}
            res["in_distribution"] = ind
            res["classical_e2_same_frames"] = classical(held, frames)
            out[f"{variant}_{fold}"] = res
            print(f"E6 {variant} {fold} held-out {af.SHORT[held]}: " + json.dumps({c: (v["recall"], v["px_err_median"], v["precision"]) for c, v in res["held_out"]["per_class"].items()}) + " fit " + json.dumps({k: v for k, v in res["held_out"].get("fit", {}).items() if "median" in k or k == "ok_in_throw"}) + " | classical " + json.dumps({c: v["recall"] for c, v in res["classical_e2_same_frames"].items()}), flush=True)
            af.dump(af.RESULTS / f"e6_eval_{variant}_{fold}.json", res)
