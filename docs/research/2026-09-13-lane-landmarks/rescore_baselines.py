"""Re-score the earlier loops' stored lanes against the E1 truths.

Loop 2 (SAM, single frames): rows carry `corners` -> direct.
Loop 3 (student, per frame): rows carry corner distances and widths, not the
corners. Corners sit at the annotated rows, so each corner's error is +-dx with
a known tiny dy; the sign pattern is the one (of 16) that reproduces the stored
top/bottom widths and board MAE. Frames where more than one pattern fits are
reported as ambiguous and skipped. Writes results/baselines_rescored.json + .md.
"""
import itertools
import json

import numpy as np

import common as C

L = C.L
C.use_full_camera()

LOOP2 = {"SAM 2 base, even3 ball-path prompts (loop 2) pre-hit": "even3_prehit_k", "SAM 2 base, even3 ball-path prompts (loop 2) last": "even3_last_k",
         "SAM 2 base, far-end crop zoom_lo (loop 2) pre-hit": "zoom_lo_prehit_k", "SAM 2 base, far-end crop zoom_lo (loop 2) last": "zoom_lo_last_k",
         "SAM 2 + pin centre pins_m (loop 2) pre-hit": "pins_m_prehit", "SAM 2 pose+pin landmark prompts (loop 2) pre-hit": "landmarks_prehit"}
LOOP3 = {"student seg640 gated (loop 3)": "seg640_lovo_{stem}_anc_gated__{stem}", "student seg640 +teacher gated (loop 3)": "seg640_lovo_{stem}_plus_anc_gated__{stem}",
         "student seg1024 gated (loop 3, tom_old only)": "seg1024_lovo_tom_old_anc_c02_gated__tom_old"}


def reconstruct(stem, f, row):
    truth = L.truth_corners(stem, f)
    y_top, y_bot = L.gt_y(stem, f)
    cands = []
    err = row["corner_err_px"]
    ys = {"top_left": y_top, "top_right": y_top, "bottom_left": y_bot, "bottom_right": y_bot}
    dx = {}
    for k in C.KEYS:
        dy = ys[k] - truth[k][1]
        v = err[k] ** 2 - dy ** 2
        dx[k] = float(np.sqrt(max(v, 0.0)))
    for signs in itertools.product((1, -1), repeat=4):
        c = {k: (truth[k][0] + s * dx[k], ys[k]) for k, s in zip(C.KEYS, signs)}
        tw = c["top_right"][0] - c["top_left"][0]; bw = c["bottom_right"][0] - c["bottom_left"][0]
        if abs(tw - row["top_width_pred_px"]) > 0.3 or abs(bw - row["bottom_width_pred_px"]) > 0.3:
            continue
        mae = L.score(stem, c, f)["board_mae"]
        if abs(mae - row["board_mae"]) > 0.03:
            continue
        cands.append(c)
    # duplicates from dx == 0 corners
    uniq = []
    for c in cands:
        if not any(all(abs(c[k][0] - u[k][0]) < 1e-6 for k in C.KEYS) for u in uniq):
            uniq.append(c)
    return uniq[0] if len(uniq) == 1 else None, len(uniq)


def rescore_loop3():
    out = {}
    for label, pat in LOOP3.items():
        for stem in C.STEMS:
            name = pat.format(stem=stem)
            p = C.LOOP3 / "results" / f"{name}.json"
            if not p.exists() or (("{stem}" not in pat) and stem not in name):
                continue
            d = json.loads(p.read_text())
            per = []
            amb = 0
            for r in d["per_frame"]:
                if not r.get("ok") or "corner_err_px" not in r:
                    continue
                c, n = reconstruct(stem, r["frame"], r)
                if c is None:
                    amb += 1; continue
                s = C.score_both(stem, r["frame"], c)
                per.append({"frame": r["frame"], "carried": r.get("carried"), "corners": {k: [round(v[0], 2), round(v[1], 2)] for k, v in c.items()},
                            **{f"mae_{t}": s[t]["board_mae"] for t in C.TRUTHS}, **{f"tail_{t}": s[t]["board_mae_last20"] for t in C.TRUTHS},
                            "top_width_err_px_pins": s["pins"]["top_width_err_px"], "top_centre_err_px_pins": s["pins"]["top_centre_err_px"]})
            throw = set(C.throw_frames(stem)); fl = L.frame_indices(stem, "last")[0]; fp = L.pin_hit_frame(stem) - 2
            summ = {"n_rows": len(d["per_frame"]), "reconstructed": len(per), "ambiguous": amb}
            for t in C.TRUTHS:
                v = [r[f"mae_{t}"] for r in per if r["frame"] in throw]
                summ[f"throw_median_{t}"] = round(float(np.median(v)), 2) if v else None
                summ[f"throw_mean_{t}"] = round(float(np.mean(v)), 2) if v else None
                tv = [r[f"tail_{t}"] for r in per if r["frame"] in throw]
                summ[f"throw_tail_median_{t}"] = round(float(np.median(tv)), 2) if tv else None
                for nm, ff in (("prehit", fp), ("last", fl)):
                    r = next((r for r in per if r["frame"] == ff), None)
                    summ[f"{nm}_{t}"] = r[f"mae_{t}"] if r else None
            out[f"{label}|{stem}"] = {"label": label, "stem": stem, "source": name, "summary": summ, "per_frame": per}
            print(f"{label:45s} {C.SHORT[stem]:13s} rebuilt {len(per)}/{len(d['per_frame'])} (amb {amb})  throw median ann/pins/all {summ['throw_median_annotated']}/{summ['throw_median_pins']}/{summ['throw_median_all']}  prehit {summ['prehit_annotated']}/{summ['prehit_pins']}  last {summ['last_annotated']}/{summ['last_pins']}")
    return out


def rescore_loop2():
    out = {}
    for label, name in LOOP2.items():
        p = C.LOOP2 / "results" / f"{name}.json"
        if not p.exists():
            continue
        for r in json.loads(p.read_text()):
            if not r.get("ok") or "corners" not in r:
                continue
            stem, f = r["stem"], r["frame"]
            c = {k: tuple(v) for k, v in r["corners"].items()}
            s = C.score_both(stem, f, c)
            out[f"{label}|{stem}"] = {"label": label, "stem": stem, "frame": f, "source": name, "stored_mae": r.get("board_mae"),
                                      **{f"mae_{t}": s[t]["board_mae"] for t in C.TRUTHS}, **{f"tail_{t}": s[t]["board_mae_last20"] for t in C.TRUTHS},
                                      "top_width_err_px_pins": s["pins"]["top_width_err_px"], "top_centre_err_px_pins": s["pins"]["top_centre_err_px"]}
            print(f"{label:55s} {C.SHORT[stem]:13s} f{f} stored {r.get('board_mae')} -> ann {s['annotated']['board_mae']} pins {s['pins']['board_mae']} all {s['all']['board_mae']}  (tail pins {s['pins']['board_mae_last20']})")
    return out


if __name__ == "__main__":
    l2 = rescore_loop2(); l3 = rescore_loop3()
    C.dump(C.RESULTS / "baselines_rescored.json", {"loop2": l2, "loop3": l3})
    md = ["| method | video | frame(s) | MAE vs annotated | vs pins | vs all landmarks | tail (last 20 % of path) vs pins | far width err px vs pins | far centre err px vs pins |", "|---|---|---|---|---|---|---|---|---|"]
    for k, r in l2.items():
        md.append(f"| {r['label']} | {C.SHORT[r['stem']]} | f{r['frame']} | {r['mae_annotated']} | {r['mae_pins']} | {r['mae_all']} | {r['tail_pins']} | {r['top_width_err_px_pins']:+.1f} | {r['top_centre_err_px_pins']:+.1f} |")
    for k, r in l3.items():
        s = r["summary"]
        med_w = np.median([q["top_width_err_px_pins"] for q in r["per_frame"]]) if r["per_frame"] else float("nan")
        med_c = np.median([q["top_centre_err_px_pins"] for q in r["per_frame"]]) if r["per_frame"] else float("nan")
        md.append(f"| {r['label']} throw median | {C.SHORT[r['stem']]} | {s['reconstructed']} frames | {s['throw_median_annotated']} | {s['throw_median_pins']} | {s['throw_median_all']} | {s['throw_tail_median_pins']} | {med_w:+.1f} | {med_c:+.1f} |")
        md.append(f"| {r['label']} pre-hit / last | {C.SHORT[r['stem']]} | pre-hit / last | {s['prehit_annotated']} / {s['last_annotated']} | {s['prehit_pins']} / {s['last_pins']} | {s['prehit_all']} / {s['last_all']} | | | |")
    (C.RESULTS / "baselines_rescored.md").write_text("\n".join(md) + "\n")
