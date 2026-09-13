"""E1: complete the constellation truth. On the pre-hit frame (and -2 / -4) of each annotated
video the lane plane is rectified through the all-landmark truth homography (loop 4) and every
repeatable dark mark near the foul line is measured in lane inches: the guide dots (~7 ft), the
seven dots just behind the foul line (boards 5..35), the approach dots (~-12 ft). Writes
results/constellation.json (lane coordinates + per-video visibility), results/landmarks_<stem>.json
(loop 4's schema, extended with the dots), results/e1_dots.json (every measurement), overlays/e1_*.
usage: e1_constellation.py"""
import json

import cv2
import numpy as np

import af

LM = af.LM
PPI = 12.0
BANDS = {"guide": (4.5 * 12, 9.5 * 12), "foul": (-1.5 * 12, 0.6 * 12), "approach": (-14.5 * 12, -9.5 * 12)}
# expected pitch (boards) and the lane-y window the row may sit in (measured, then pinned): guide dots ~7 ft,
# foul-line dots just behind the foul line, approach dots ~12 ft behind it
GRID = {"guide": ((3, 5), (5.5 * 12, 8.5 * 12)), "foul": ((5,), (-0.8 * 12, 0.05 * 12)), "approach": ((5,), (-13.5 * 12, -10.5 * 12))}
X0, X1 = -6.0, af.W_IN + 6.0


def band_blobs(img, H, band, area=(6, 400)):
    y0, y1 = BANDS[band]
    rect, Hr = af.rectify_band(img, H, y0, y1, PPI, X0, X1)
    g = cv2.cvtColor(rect, cv2.COLOR_BGR2GRAY)
    blobs, thr = af.dark_blobs(g, bg_ks=31, k_mad=4.0, min_thr=8.0, area=area, open_ks=2)
    for b in blobs:
        b["x_in"] = X0 + b["x"] / PPI; b["y_in"] = y1 - b["y"] / PPI
        b["board"] = float(LM.boards_from_lane_x(b["x_in"]))
        b["in_lane"] = bool(0 <= b["x_in"] <= af.W_IN)
    return rect, blobs, thr


def grid_row(blobs, pitch_in, y_lo_in, y_hi_in, x_tol=0.9, y_tol=2.2, min_n=3):
    """Row of blobs on a regular grid x = off + k * pitch (lane inches) at one lane y: the (row seed,
    offset) with the most inliers. Blobs must be small (dots), inside the lane +-2 in. Returns the
    inlier blobs sorted by x with k relative to the grid line nearest the lane centre."""
    cand = [b for b in blobs if y_lo_in <= b["y_in"] <= y_hi_in and -2.0 <= b["x_in"] <= af.W_IN + 2.0 and b["area"] <= 260 and max(b["w"], b["h"]) <= 3.0 * PPI]
    best = (0, None, None)
    for seed in cand:
        same_y = [c for c in cand if abs(c["y_in"] - seed["y_in"]) <= y_tol]
        off = seed["x_in"]
        inl = [c for c in same_y if abs(((c["x_in"] - off + pitch_in / 2) % pitch_in) - pitch_in / 2) <= x_tol]
        # one blob per grid line (keep the darkest)
        byk = {}
        for c in inl:
            k = int(round((c["x_in"] - off) / pitch_in))
            if k not in byk or c["darkness"] > byk[k]["darkness"]:
                byk[k] = c
        n = len(byk)
        if n > best[0]:
            best = (n, off, byk)
    n, off, byk = best
    if n < min_n:
        return []
    # refine the offset on the inliers and re-index relative to the lane centre
    ks = np.array(sorted(byk)); xs = np.array([byk[k]["x_in"] for k in ks])
    off = float(np.mean(xs - ks * pitch_in))
    k0 = int(round((af.W_IN / 2 - off) / pitch_in))
    row = []
    for k in ks:
        b = dict(byk[k]); b["k"] = int(k - k0); b["x_grid"] = off + k * pitch_in; b["resid_in"] = b["x_in"] - b["x_grid"]
        row.append(b)
    return sorted(row, key=lambda b: b["x_in"])


def snap_to_grid(row, pitch_in, centre=af.W_IN / 2):
    """Assign each blob an integer index k on a symmetric grid x = centre + k * pitch (k in Z or Z+1/2),
    choosing the phase (0 or half) that fits best. Returns (phase, [(k, blob)], rms)."""
    best = None
    for phase in (0.0, 0.5):
        ks = [round((b["x_in"] - centre) / pitch_in - phase) + phase for b in row]
        res = [b["x_in"] - (centre + k * pitch_in) for k, b in zip(ks, row)]
        rms = float(np.sqrt(np.mean(np.square(res))))
        if best is None or rms < best[2]:
            best = (phase, list(zip(ks, row)), rms)
    return best


def draw_band(rect, blobs, row, title, path):
    ov = rect.copy()
    for b in blobs:
        cv2.circle(ov, (int(b["x"]), int(b["y"])), 6, (0, 200, 255), 1)
    for b in row:
        cv2.circle(ov, (int(b["x"]), int(b["y"])), 9, (0, 255, 0), 2)
        cv2.putText(ov, f"{b['board']:.1f}", (int(b["x"]) - 10, int(b["y"]) - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
    for x_in in (0.0, af.W_IN):
        x = int((x_in - X0) * PPI); cv2.line(ov, (x, 0), (x, ov.shape[0] - 1), (255, 0, 255), 1)
    cv2.putText(ov, title, (6, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    z = max(1, int(1400 / ov.shape[1]))
    cv2.imwrite(str(path), cv2.resize(ov, None, fx=z, fy=z, interpolation=cv2.INTER_CUBIC), [cv2.IMWRITE_JPEG_QUALITY, 90])


def contrast_at(img, H, x_in, y_in, r_in=0.9, ring_in=2.5):
    """Darkness of a lane-plane point: median of a small rectified patch around (x_in, y_in)
    minus the median of a ring around it (grey levels, positive = dark mark). Also returns
    the patch's px per inch in the source image (resolution) as a visibility caveat."""
    ppi = 8.0
    rect, Hr = af.rectify_band(img, H, y_in - ring_in, y_in + ring_in, ppi, x_in - ring_in, x_in + ring_in)
    g = cv2.cvtColor(rect, cv2.COLOR_BGR2GRAY).astype(np.float32)
    yy, xx = np.mgrid[0:g.shape[0], 0:g.shape[1]]
    cx = (x_in - (x_in - ring_in)) * ppi; cy = ((y_in + ring_in) - y_in) * ppi
    d = np.hypot(xx - cx, yy - cy) / ppi
    inner = g[d <= r_in]; outer = g[(d > r_in + 0.4) & (d <= ring_in)]
    if len(inner) < 3 or len(outer) < 10:
        return None, None
    p_img = af.to_image(H, [(x_in, y_in), (x_in + 1.0, y_in)])
    res = float(np.hypot(*(p_img[1] - p_img[0])))
    return float(np.median(outer) - np.median(inner)), res


def measure(stem, f):
    img = af.read_frame(stem, f)
    H = af.truth_h(stem, f, "all")
    out = {"stem": stem, "frame": f, "bands": {}}
    for band in BANDS:
        rect, blobs, thr = band_blobs(img, H, band)
        pitches, (ylo, yhi) = GRID[band]
        rows = [(p, grid_row(blobs, p * af.BOARD_IN, ylo, yhi, min_n=3)) for p in pitches]
        pitch_b, row = max(rows, key=lambda t: len(t[1]))
        out["bands"][band] = {"thr": round(thr, 1), "n_blobs": len(blobs), "pitch_boards": pitch_b,
                              "row": [{"x_in": round(b["x_in"], 2), "y_in": round(b["y_in"], 2), "board": round(b["board"], 2), "area": b["area"], "darkness": round(b["darkness"], 1),
                                       "k": b["k"], "x_grid": round(b["x_grid"], 2), "resid_in": round(b["resid_in"], 2)} for b in row]}
        # image coordinates of each row blob (rect -> lane -> image)
        for b, r in zip(row, out["bands"][band]["row"]):
            p = af.to_image(H, [(b["x_in"], b["y_in"])])[0]
            r["x"] = round(float(p[0]), 2); r["y"] = round(float(p[1]), 2)
        if f == af.frame_for(stem, "prehit"):
            draw_band(rect, blobs, row, f"{af.SHORT[stem]} f{f} {band} band {BANDS[band][0]/12:.1f}..{BANDS[band][1]/12:.1f} ft (green = row)", af.OVERLAYS / f"e1_{band}_{stem}.jpg")
    return out


def main():
    meas = {}
    for stem in af.STEMS:
        fp = af.frame_for(stem, "prehit")
        meas[stem] = [measure(stem, fp), measure(stem, fp - 2), measure(stem, fp - 4)]
        for m in meas[stem]:
            for band, v in m["bands"].items():
                print(f"{af.SHORT[stem]:13s} f{m['frame']} {band:9s} blobs {v['n_blobs']:3d} row {len(v['row'])}: " + " ".join(f"{r['board']:.1f}@{r['y_in']/12:.2f}ft" for r in v["row"]))
    af.dump(af.RESULTS / "e1_dots.json", meas)

    # ---- constellation from the measurements (tom_old carries the dot rows; the others confirm what they can)
    pts = {}
    for b, x in LM.arrow_x_in().items():
        pts[f"arrow_{b}"] = {"x_in": x, "y_in": None, "class": "arrow", "source": "rule-book board, V depth measured per video (loop 4)"}
    for k, (x, y) in LM.pin_bases_in().items():
        pts[f"pin_{k}_base"] = {"x_in": x, "y_in": y, "class": "pin", "source": "rule-book rack"}
    pts["foul_left"] = {"x_in": 0.0, "y_in": 0.0, "class": "foul", "source": "rule-book"}
    pts["foul_right"] = {"x_in": af.W_IN, "y_in": 0.0, "class": "foul", "source": "rule-book"}
    # arrow V depth: mean of the per-video E1 fits
    Vs = [af.landmark_doc(s)["all_fit"]["V"] for s in af.STEMS if af.landmark_doc(s).get("all_fit", {}).get("V")]
    V = {"centre_ft": float(np.mean([v["centre_ft"] for v in Vs])), "ft_per_5_boards": float(np.mean([v["ft_per_5_boards"] for v in Vs])),
         "per_video": {s: af.landmark_doc(s)["all_fit"]["V"] for s in af.STEMS}}
    for b in LM.C.ARROW_BOARDS:
        pts[f"arrow_{b}"]["y_in"] = round((V["centre_ft"] - V["ft_per_5_boards"] * abs(b - 20) / 5.0) * 12, 2)
    summary = {"arrow_V": V, "dot_rows": {}}
    # dot rows. The grid pitch is the one that fits the most blobs; the lead frame is the one with the
    # most inliers (ties: lowest grid rms) and only frames whose row sits within 4 in of the lead's lane-y
    # are pooled. The constellation is SYMMETRIC about the lane centre by the rules (x = W/2 + k * pitch,
    # k = -K..K); the measured centre offset under the truth homography is recorded as the truth's own
    # near-end error, not baked into the model. K: guide dots 5 (boards 5..35, 11 dots), foul-line and
    # approach dots 3 (boards 5..35, 7 dots) - the observed k range is reported beside it.
    K_MAX = {"guide": 5, "foul": 3, "approach": 3}
    for band, cls in (("guide", "dot"), ("foul", "fdot"), ("approach", "adot")):
        frames = [(s_, m) for s_ in af.STEMS for m in meas[s_] if len(m["bands"][band]["row"]) >= 3]
        if not frames:
            summary["dot_rows"][band] = {"found": False}
            continue
        pitches = [m["bands"][band]["pitch_boards"] for _, m in frames]
        pitch_b = int(np.median(pitches)); pitch_in = pitch_b * af.BOARD_IN
        frames = [(s_, m) for s_, m in frames if m["bands"][band]["pitch_boards"] == pitch_b]
        rms = lambda m: float(np.sqrt(np.mean([bb["resid_in"] ** 2 for bb in m["bands"][band]["row"]])))  # noqa: E731
        ymean = lambda m: float(np.mean([bb["y_in"] for bb in m["bands"][band]["row"]]))  # noqa: E731
        lead_s, lead = max(frames, key=lambda t: (len(t[1]["bands"][band]["row"]), -rms(t[1])))
        y_lead = ymean(lead)
        pooled, agree = {}, {}
        for s_, m in frames:
            ok = abs(ymean(m) - y_lead) <= 4.0 and rms(m) <= 0.6
            agree.setdefault(s_, []).append({"frame": m["frame"], "n": len(m["bands"][band]["row"]), "grid_rms_in": round(rms(m), 2), "y_ft": round(ymean(m) / 12, 3), "pooled": ok,
                                             "k_observed": sorted(bb["k"] for bb in m["bands"][band]["row"])})
            if not ok:
                continue
            for bb in m["bands"][band]["row"]:
                if abs(bb["k"]) <= K_MAX[band]:
                    pooled.setdefault(bb["k"], []).append((bb["x_in"], bb["y_in"], s_))
        ks = sorted(pooled)
        offs = [x - k * pitch_in for k, v in pooled.items() for (x, _, _) in v]
        off = float(np.mean(offs)); y_mean = float(np.mean([y for v in pooled.values() for (_, y, _) in v]))
        centre_shift = off - af.W_IN / 2
        names = {}
        # positions: the MEASURED grid (offset `off` under the truth, which the visible lane edges confirm at
        # the foul line on tom_old) - the rows sit 0.4-0.7 in left of the lane centre, and a symmetric model
        # would misplace every dot by that much; `x_rule_in` keeps the symmetric value for the record
        for k in range(-K_MAX[band], K_MAX[band] + 1):
            x_rule = af.W_IN / 2 + k * pitch_in; x_grid = off + k * pitch_in
            board = LM.boards_from_lane_x(x_rule)
            name = f"{cls}_{int(round(board))}"
            obs = pooled.get(k, [])
            names[name] = {"x_in": round(x_grid, 2), "y_in": round(y_mean, 2), "class": cls, "k": k, "board": round(float(board), 2), "x_rule_in": round(x_rule, 2),
                           "n_obs": len(obs), "videos": sorted({s_ for (_, _, s_) in obs}),
                           "x_obs_mean_in": round(float(np.mean([x for (x, _, _) in obs])), 2) if obs else None,
                           "x_obs_minus_grid_in": round(float(np.mean([x for (x, _, _) in obs])) - x_grid, 2) if obs else None,
                           "source": "measured grid" if obs else "measured grid, unobserved position"}
        pts.update(names)
        summary["dot_rows"][band] = {"found": True, "pitch_boards": pitch_b, "pitch_in": round(pitch_in, 3), "lead": {"stem": lead_s, "frame": lead["frame"], "n": len(lead["bands"][band]["row"])},
                                     "measured_centre_minus_lane_centre_in": round(centre_shift, 2), "y_ft": round(y_mean / 12, 3), "y_in_std_pooled": round(float(np.std([y for v in pooled.values() for (_, y, _) in v])), 2),
                                     "k_observed": [min(ks), max(ks)], "k_model": [-K_MAX[band], K_MAX[band]], "count_model": len(names), "count_observed": len(ks), "frames": agree}
    # gutter lines and the foul line as line constraints
    lines = {"gutter_left": {"x_in": 0.0}, "gutter_right": {"x_in": af.W_IN}, "foul_line": {"y_in": 0.0}}
    # ---- per-video visibility on the pre-hit frame. Arrows and pins: loop 4's per-video detection
    # (landmarks_<stem>.json, detected on that frame). Dots: detected in the row on >= 2 of the 3 standing-pin
    # frames of that video. Foul corners: in frame (annotated). Plus a contrast number at the projected
    # model position (1.5 in disc) as a secondary check.
    vis = {}
    for stem in af.STEMS:
        fp = af.frame_for(stem, "prehit"); img = af.read_frame(stem, fp); H = af.truth_h(stem, fp, "all")
        h, w = img.shape[:2]
        l4 = af.C4.landmark_doc(stem)["landmarks"]
        seen = {}
        for band, cls in (("guide", "dot"), ("foul", "fdot"), ("approach", "adot")):
            sr = summary["dot_rows"].get(band, {})
            if not sr.get("found"):
                continue
            for m in meas[stem]:
                fr = next((a_ for a_ in sr["frames"].get(stem, []) if a_["frame"] == m["frame"]), None)
                if not fr or not fr["pooled"]:
                    continue
                for bb in m["bands"][band]["row"]:
                    x_grid = af.W_IN / 2 + bb["k"] * sr["pitch_in"]
                    name = f"{cls}_{int(round(LM.boards_from_lane_x(x_grid)))}"
                    seen[name] = seen.get(name, 0) + 1
        vis[stem] = {}
        for name, p in pts.items():
            q = af.to_image(H, [(p["x_in"], p["y_in"])])[0]
            inside = bool(0 <= q[0] < w and 0 <= q[1] < h)
            c, res = contrast_at(img, H, p["x_in"], p["y_in"], r_in=1.5, ring_in=3.5) if inside and p["class"] != "pin" else (None, None)
            if p["class"] in ("arrow", "pin"):
                visible = name in l4
            elif p["class"] == "foul":
                visible = inside
            else:
                visible = seen.get(name, 0) >= 2
            vis[stem][name] = {"in_frame": inside, "x": round(float(q[0]), 1), "y": round(float(q[1]), 1), "contrast": round(c, 1) if c is not None else None,
                               "px_per_in": round(res, 2) if res else None, "detected_frames": seen.get(name, 0), "visible": bool(visible)}
    summary["visibility_prehit"] = {s_: {cls: {"in_frame": sum(1 for n, v in vis[s_].items() if pts[n]["class"] == cls and v["in_frame"]),
                                               "visible": sum(1 for n, v in vis[s_].items() if pts[n]["class"] == cls and v["visible"]),
                                               "total": sum(1 for n in pts if pts[n]["class"] == cls)} for cls in ("foul", "fdot", "dot", "adot", "arrow", "pin")} for s_ in af.STEMS}
    doc = {"lane": {"width_in": af.W_IN, "board_in": af.BOARD_IN, "x": "inches from the LEFT edge (board 39 side), board 1 on the right", "y": "inches down-lane from the foul line; negative = approach"},
           "points": pts, "lines": lines, "summary": summary, "visibility_prehit": vis}
    af.dump(af.constellation_path(), doc)
    # ---- per-video landmark docs in loop 4's schema, extended with the dots measured on that video's pre-hit frame
    for stem in af.STEMS:
        base = json.loads(json.dumps(af.C4.landmark_doc(stem)))
        fp = base["frame"]
        for band, cls in (("guide", "dot"), ("foul", "fdot"), ("approach", "adot")):
            mb = meas[stem][0]["bands"][band]; sr = summary["dot_rows"].get(band, {})
            fr = next((a_ for a_ in sr.get("frames", {}).get(stem, []) if a_["frame"] == fp), None) if sr.get("found") else None
            if not fr or not fr["pooled"]:
                continue
            for b in mb["row"]:
                x_grid = af.W_IN / 2 + b["k"] * sr["pitch_in"]
                name = f"{cls}_{int(round(LM.boards_from_lane_x(x_grid)))}"
                if name in pts:
                    base["landmarks"][name] = {"x": b["x"], "y": b["y"], "frame": fp, "source": "detected", "confidence": round(min(1.0, b["darkness"] / 30), 2)}
        base["constellation"] = str(af.constellation_path().relative_to(af.HERE))
        af.dump(af.RESULTS / f"landmarks_{stem}.json", base)
    for band, sr in summary["dot_rows"].items():
        print(band, {k: v for k, v in sr.items() if k != "frames"})
        for s_, fr in sr.get("frames", {}).items():
            print("   ", af.SHORT[s_], [(a_["frame"], a_["n"], a_["grid_rms_in"], a_["y_ft"], a_["pooled"]) for a_ in fr])
    print(json.dumps(summary["visibility_prehit"], indent=None))


if __name__ == "__main__":
    main()
