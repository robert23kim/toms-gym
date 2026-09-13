"""E3: one homography from all the landmarks, per frame, against both truths.

Per frame the lane hypothesis (E2's source) gives the foul-line ends and the far
corners; E2's detections give arrows (x-only constraints on their board line) and
pin bases (2D, while the pins stand; optionally carried through the camera model
afterwards). Weighted DLT, weights = 1 / expected precision in lane inches,
iterative rejection of constraints off by > thr. Variants (each a results row):
  corners            4-corner homography (baseline; equals the source lane)
  corners+arrows     + 7 arrows
  corners+pins       + pins 7 and 10
  corners+pins10     + all ten pin bases
  corners+arrows+pins, corners+arrows+pins10
  foul+arrows+pins   far corners dropped (the mask edge at the deck is the weak input)
  drop-<landmark>    foul+arrows+pins with one landmark left out (robustness)
  *+carry            pins carried from the last standing-pin frame via the camera model
usage: e3_fit.py [--tag loop3] [stems...]"""
import argparse
import json

import numpy as np

import common as C
import landmarks as LM

L = C.L
C.use_full_camera()
PRED = C.SCRATCH / "pred"

SIG_FOUL_IN = 1.0      # the loop-3 student's foul-line corners are 5-19 px off the annotation (0.5-3 boards); ~6 px on sample_input
SIG_FOUL_WEAK_IN = 4.0 # foul ends as a weak prior only
SIG_TOP_IN = 3.0       # a student / SAM edge at the deck: several px = several inches
SIG_ARROW_IN = 0.7     # ~1.5 px at mid-lane from an imperfect lane hypothesis (E2: 0.64 boards median)
SIG_PIN_IN = 0.45      # ~0.5 px at the deck
REJECT_IN = 2.5


ALIAS_MARGIN = 0.03   # E2 stores the margin; aliased frames scored 0.011-0.029 on tom_old, -0.025..-0.007 on Chardie; good frames >= 0.023


def pins_ok(det):
    p = det.get("pins")
    if not p or not p.get("ok"):
        return False
    m = p.get("alias_margin")
    return m is None or m > ALIAS_MARGIN


def constraints(det, T_top, use_top=True, use_arrows=True, pins="710", drop=None, pin_pts=None, foul="strong"):
    pts, wp, lines, wl, names = [], [], [], [], []
    if foul:
        key = "foul_snap" if (foul == "snap" and det.get("foul_snap")) else "foul"
        fl, fr = det[key]["left"], det[key]["right"]
        sig = SIG_FOUL_WEAK_IN if foul == "weak" else SIG_FOUL_IN
        pts += [((fl[0], fl[1]), (0.0, 0.0)), ((fr[0], fr[1]), (LM.W_IN, 0.0))]; wp += [1 / sig] * 2; names += ["foul_l", "foul_r"]
    lc = det["lane_corners"]
    if use_top:
        pts += [((lc["top_left"][0], lc["top_left"][1]), (0.0, T_top)), ((lc["top_right"][0], lc["top_right"][1]), (LM.W_IN, T_top))]
        wp += [1 / SIG_TOP_IN] * 2; names += ["top_l", "top_r"]
    if use_arrows:
        for b, v in det["arrows"].items():
            if drop == f"arrow_{b}":
                continue
            lines.append(((v["x"], v["y"]), LM.board_x_in(int(b)))); wl.append(1 / SIG_ARROW_IN); names.append(f"arrow_{b}")
    pin_pts = pin_pts if pin_pts is not None else (det["pins"]["bases"] if pins_ok(det) else None)
    if pins and pin_pts:
        bases = LM.pin_bases_in()
        keys = (7, 10) if pins == "710" else tuple(range(1, 11))
        for k in keys:
            if drop == f"pin_{k}":
                continue
            p = pin_pts[str(k)]
            pts.append(((p[0], p[1]), bases[k])); wp.append(1 / SIG_PIN_IN); names.append(f"pin_{k}")
    return pts, wp, lines, wl, names


def fit(pts, wp, lines, wl, names, robust=True):
    if not robust:
        return LM.fit_homography(pts, lines, wp, wl), []
    wp = list(wp); wl = list(wl)
    H = LM.fit_homography(pts, lines, wp, wl)
    dropped = []
    for _ in range(3):
        if H is None:
            break
        r = LM.residuals(H, pts, lines)
        changed = False
        n_pins_live = sum(1 for i in range(len(pts)) if names[i].startswith("pin") and wp[i] > 0)
        n_other = sum(1 for i in range(len(pts)) if not names[i].startswith("foul") and wp[i] > 0) + sum(1 for w in wl if w > 0)
        for i in range(len(pts)):
            if names[i].startswith("foul") and (n_other < 8 or n_pins_live == 0):
                continue
            if names[i].startswith("top") and n_pins_live == 0:
                continue  # the only far-end depth anchor: arrows alone leave the far end free
            if wp[i] > 0 and r[i] > REJECT_IN:
                wp[i] = 0.0; dropped.append(names[i]); changed = True
        for j in range(len(lines)):
            if wl[j] > 0 and r[len(pts) + j] > REJECT_IN:
                wl[j] = 0.0; dropped.append(names[len(pts) + j]); changed = True
        if not changed:
            break
        # never fit on fewer than 4 effective constraints beyond the foul ends
        if sum(1 for w in wp if w > 0) + sum(1 for w in wl if w > 0) < 6:
            break
        H = LM.fit_homography(pts, lines, wp, wl)
    return H, dropped


def carried_pins(stem, f, dets, ph, mode="orb"):
    """Pin bases from the last frame with an ok rack fit before the pin hit, moved into frame f
    through the ORB camera model (mode orb) or through a similarity fitted on the arrows detected
    on both frames (mode lm; needs >= 3 common arrows, else None)."""
    import cv2
    cands = [g for g in sorted(dets) if g < ph and pins_ok(dets[g])]
    if not cands:
        return None
    g = max(cands)
    if mode == "orb":
        T = L.transform(stem, g, f)
    else:
        common = [b for b in dets[g]["arrows"] if b in dets[f]["arrows"]]
        if len(common) < 3:
            return None
        src = np.float32([[dets[g]["arrows"][b]["x"], dets[g]["arrows"][b]["y"]] for b in common])
        dst = np.float32([[dets[f]["arrows"][b]["x"], dets[f]["arrows"][b]["y"]] for b in common])
        T, inl = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC, ransacReprojThreshold=3.0)
        if T is None or inl.sum() < 3:
            return None
    return {k: list(L.warp_pt(T, tuple(v))) for k, v in dets[g]["pins"]["bases"].items()}


def run(stem, tag):
    dets = {int(k): v for k, v in json.loads((PRED / f"lm_{tag}_{stem}.json").read_text()).items()}
    ph = L.pin_hit_frame(stem)
    T_top = LM.top_edge_depth_in(stem)
    fl = L.frame_indices(stem, "last")[0]; fp = ph - 2
    variants = {
        "corners": dict(use_top=True, use_arrows=False, pins=None),
        "corners+arrows": dict(use_top=True, use_arrows=True, pins=None),
        "corners+pins": dict(use_top=True, use_arrows=False, pins="710"),
        "corners+pins10": dict(use_top=True, use_arrows=False, pins="all"),
        "corners+arrows+pins": dict(use_top=True, use_arrows=True, pins="710"),
        "corners+arrows+pins10": dict(use_top=True, use_arrows=True, pins="all"),
        "foul+arrows+pins": dict(use_top=False, use_arrows=True, pins="710"),
        "foul+arrows+pins10": dict(use_top=False, use_arrows=True, pins="all"),
        "foul+arrows": dict(use_top=False, use_arrows=True, pins=None),
        "foul+pins10": dict(use_top=False, use_arrows=False, pins="all"),
    }
    for b in C.ARROW_BOARDS:
        variants[f"drop-arrow_{b}"] = dict(use_top=False, use_arrows=True, pins="710", drop=f"arrow_{b}")
    for k in (7, 10):
        variants[f"drop-pin_{k}"] = dict(use_top=False, use_arrows=True, pins="all", drop=f"pin_{k}")
    # second-pass arrows: detect again from the best pin-corrected lane of pass 1 (corners+pins10 when
    # pins stand, else the source corners); the source-lane detections are kept as *(1pass) rows
    dets1 = dets
    dets = {}
    for f in sorted(dets1):
        det = dict(dets1[f]); det["arrows_1pass"] = det["arrows"]
        pts, wp, lines, wl, names = constraints(det, T_top, use_top=True, use_arrows=False, pins="all")
        H1 = LM.fit_homography(pts, lines, wp, wl) if sum(1 for n in names if n.startswith("pin")) else LM.h_from_quad({k: tuple(v) for k, v in det["lane_corners"].items()})
        try:
            arr2, _ = LM.detect_arrows(C.read_frame(stem, f), H1)
            det["arrows"] = {str(b): {"x": v["x"], "y": v["y"], "darkness": v["darkness"], "area": v["area"]} for b, v in arr2.items()}
        except Exception:  # noqa: BLE001
            pass
        try:
            img = C.read_frame(stem, f)
            lc = det["lane_corners"]; y_top, y_bot = L.gt_y(stem, f)
            (lx1, ly1), (lx2, ly2) = lc["top_left"], lc["bottom_left"]; (rx1, ry1), (rx2, ry2) = lc["top_right"], lc["bottom_right"]
            la = (lx2 - lx1) / (ly2 - ly1); lb = lx1 - la * ly1; ra = (rx2 - rx1) / (ry2 - ry1); rb = rx1 - ra * ry1
            y_lo = y_top + 0.6 * (y_bot - y_top)
            left, right = L.snap_edges(img, (la, lb), (ra, rb), y_lo, y_bot, band=int(max(6, 0.06 * (lc["bottom_right"][0] - lc["bottom_left"][0]))))
            det["foul_snap"] = {"left": [left[0] * y_bot + left[1], y_bot], "right": [right[0] * y_bot + right[1], y_bot]}
        except Exception:  # noqa: BLE001
            pass
        dets[f] = det
    variants["arrows+pins10"] = dict(use_top=False, use_arrows=True, pins="all", foul=None)
    variants["arrows+pins10+weakfoul"] = dict(use_top=False, use_arrows=True, pins="all", foul="weak")
    variants["arrows+pins10+top"] = dict(use_top=True, use_arrows=True, pins="all", foul=None)
    variants["snapfoul+arrows+pins10"] = dict(use_top=False, use_arrows=True, pins="all", foul="snap")
    variants["snapfoul+pins10"] = dict(use_top=False, use_arrows=False, pins="all", foul="snap")
    variants["snapcorners"] = dict(use_top=True, use_arrows=False, pins=None, foul="snap")
    variants["corners+arrows(1pass)"] = dict(use_top=True, use_arrows=True, pins=None, onepass=True)
    variants["foul+arrows+pins(1pass)"] = dict(use_top=False, use_arrows=True, pins="710", onepass=True)
    results = {}
    for name, kw in variants.items():
        kw = dict(kw); onepass = kw.pop("onepass", False)
        for carry in (False, "orb", "lm"):
            if carry and not kw.get("pins"):
                continue
            if carry and name.startswith("drop-"):
                continue
            vname = name + ({"orb": "+carry", "lm": "+carryLM"}.get(carry, "") if carry else "")
            per = []
            for f in sorted(dets):
                det = dets[f]
                pin_pts = None
                if kw.get("pins") and carry and not pins_ok(det):
                    pin_pts = carried_pins(stem, f, dets, ph, mode=carry)
                det_use = dict(det, arrows=det["arrows_1pass"]) if onepass else det
                pts, wp, lines, wl, names = constraints(det_use, T_top, pin_pts=pin_pts, **kw)
                n_pins = sum(1 for n in names if n.startswith("pin")); n_arr = sum(1 for n in names if n.startswith("arrow"))
                if kw.get("pins") and n_pins == 0 and not kw.get("use_top") and n_arr < 3:
                    per.append({"frame": f, "ok": False, "why": "no pins/arrows"}); continue
                if kw.get("foul", "strong") is None and (n_pins == 0 or n_arr < 3):
                    per.append({"frame": f, "ok": False, "why": "no foul ends and too few landmarks"}); continue
                if not kw.get("use_top") and n_pins == 0 and not kw.get("use_arrows"):
                    per.append({"frame": f, "ok": False, "why": "underdetermined"}); continue
                if not kw.get("use_top") and n_pins == 0:
                    # foul + arrows only: arrows at one depth do not fix the far end; skip (documented degenerate case)
                    per.append({"frame": f, "ok": False, "why": "arrows-only degenerate"}); continue
                H, dropped = fit(pts, wp, lines, wl, names, robust=(name != "corners"))
                if H is None or not np.all(np.isfinite(H)):
                    per.append({"frame": f, "ok": False, "why": "fit failed"}); continue
                y_top, y_bot = L.gt_y(stem, f)
                corners = LM.corners_from_h(H, y_top, y_bot)
                if not all(np.isfinite([v for c in corners.values() for v in c])) or corners["top_right"][0] <= corners["top_left"][0]:
                    per.append({"frame": f, "ok": False, "why": "degenerate corners"}); continue
                row = {"frame": f, "ok": True, "n_arrows": n_arr, "n_pins": n_pins, "pins_carried": bool(pin_pts is not None), "dropped": dropped,
                       "corners": {k: [round(float(v[0]), 2), round(float(v[1]), 2)] for k, v in corners.items()}}
                for t in C.TRUTHS:
                    s = C.score_corners(stem, f, corners, truth=C.truth_corners(stem, f, t))
                    row[f"mae_{t}"] = s["board_mae"]; row[f"tail_{t}"] = s["board_mae_last20"]
                    row[f"width_err_px_{t}"] = s["top_width_err_px"]; row[f"centre_err_px_{t}"] = s["top_centre_err_px"]
                per.append(row)
            throw = set(C.throw_frames(stem)); ok = [r for r in per if r["ok"]]
            post = [r for r in ok if r["frame"] in throw and r["frame"] >= ph]
            summ = {"frames": len(per), "ok": len(ok), "ok_in_throw": sum(1 for r in ok if r["frame"] in throw), "post_hit_frames": len(post)}
            for t in C.TRUTHS:
                summ[f"post_hit_median_{t}"] = round(float(np.median([r[f"mae_{t}"] for r in post])), 2) if post else None
                v = [r[f"mae_{t}"] for r in ok if r["frame"] in throw]
                summ[f"throw_median_{t}"] = round(float(np.median(v)), 2) if v else None
                summ[f"throw_mean_{t}"] = round(float(np.mean(v)), 2) if v else None
                summ[f"throw_within2_{t}"] = round(float(np.mean(np.array(v) <= 2) * 100), 1) if v else None
                summ[f"tail_median_{t}"] = round(float(np.median([r[f"tail_{t}"] for r in ok if r["frame"] in throw])), 2) if v else None
                summ[f"width_err_px_median_{t}"] = round(float(np.median([r[f"width_err_px_{t}"] for r in ok if r["frame"] in throw])), 2) if v else None
                summ[f"width_err_px_medabs_{t}"] = round(float(np.median([abs(r[f"width_err_px_{t}"]) for r in ok if r["frame"] in throw])), 2) if v else None
                summ[f"centre_err_px_medabs_{t}"] = round(float(np.median([abs(r[f"centre_err_px_{t}"]) for r in ok if r["frame"] in throw])), 2) if v else None
                for nm, ff in (("prehit", fp), ("last", fl)):
                    r = next((r for r in ok if r["frame"] == ff), None)
                    summ[f"{nm}_{t}"] = r[f"mae_{t}"] if r else None
            results[vname] = {"summary": summ, "per_frame": per}
            print(f"E3 {tag} {C.SHORT[stem]:13s} {vname:28s} ok {summ['ok']}/{summ['frames']} | throw med ann/pins/all {summ['throw_median_annotated']}/{summ['throw_median_pins']}/{summ['throw_median_all']} tail(pins) {summ['tail_median_pins']} | prehit pins {summ['prehit_pins']} last {summ['last_pins']} post-hit med {summ['post_hit_median_pins']} ({summ['post_hit_frames']}f) | far width err px (pins) {summ['width_err_px_median_pins']} centre {summ['centre_err_px_medabs_pins']}", flush=True)
    C.dump(C.RESULTS / f"e3_fit_{tag}__{stem}.json", {"stem": stem, "tag": tag, "variants": results})
    (PRED / f"lm2_{tag}_{stem}.json").write_text(json.dumps({str(f): {"arrows": d["arrows"], "pins": d.get("pins")} for f, d in dets.items()}))
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="loop3"); ap.add_argument("stems", nargs="*")
    a = ap.parse_args()
    for stem in a.stems or C.STEMS:
        run(stem, a.tag)
