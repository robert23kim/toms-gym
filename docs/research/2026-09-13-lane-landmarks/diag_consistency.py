"""Which landmark sets agree under one homography? Fits on the pre-hit frame:
 A foul ends (2D) + arrows (x-only)            -> implied far end at the pin base row
 B foul ends (2D) + pins 7/10 (2D)             -> arrow residuals
 C foul ends + arrows + pins 7/10 + all pins   -> residuals of everything
and the annotated quad itself. Prints lane width / centre at the pin base row
and per-constraint residuals (inches)."""
import json
import numpy as np
import common as C
import landmarks as LM
L = C.L
C.use_full_camera()
e1 = {(r["stem"], r["frame"]): r for r in json.load(open(C.RESULTS / "e1_truth.json"))}
out = {}
for stem in C.STEMS:
    f = C.frame_for(stem, "prehit")
    r = e1[(stem, f)]
    ann = L.truth_corners(stem, f)
    bases = LM.pin_bases_in()
    foul = [((ann["bottom_left"][0], ann["bottom_left"][1]), (0.0, 0.0)), ((ann["bottom_right"][0], ann["bottom_right"][1]), (LM.W_IN, 0.0))]
    arrows = {int(b): (v["x"], v["y"]) for b, v in r["arrows"].items()}
    # drop the V outlier on Chardie by symmetry: |ft - ft of mirror| > 1 ft
    ft = {int(b): v["ft_ann"] for b, v in r["arrows"].items()}
    keep = {}
    for b, p in arrows.items():
        m = 40 - b
        if m in ft and abs(ft[b] - ft[m]) > 1.0:
            continue
        keep[b] = p
    arrows = keep
    arr_lines = [((p[0], p[1]), LM.board_x_in(b)) for b, p in sorted(arrows.items())]
    pin_pts = {int(k): tuple(v) for k, v in r["rack"]["bases"].items()}
    pins710 = [((pin_pts[7][0], pin_pts[7][1]), bases[7]), ((pin_pts[10][0], pin_pts[10][1]), bases[10])]
    pins_all = [((pin_pts[k][0], pin_pts[k][1]), bases[k]) for k in range(1, 11)]
    yb = r["pins_far_end"]["pin_base_row_y"]
    fits = {
        "annotation quad": LM.h_from_quad(ann),
        "A foul + arrows(x)": LM.fit_homography(foul, arr_lines, [10, 10], [1] * len(arr_lines)),
        "B foul + pins 7,10": LM.fit_homography(foul + pins710, [], [10, 10, 1, 1], []),
        "C foul + arrows + pins 7,10": LM.fit_homography(foul + pins710, arr_lines, [10, 10, 1, 1], [1] * len(arr_lines)),
        "D foul + arrows + all pins": LM.fit_homography(foul + pins_all, arr_lines, [10, 10] + [1] * 10, [1] * len(arr_lines)),
        "E arrows + pins 7,10 (no foul)": LM.fit_homography(pins710, arr_lines, [1, 1], [1] * len(arr_lines)),
    }
    print(f"\n== {C.SHORT[stem]} f{f}  (annotated width/centre at pin row {r['annotated_at_pin_row']['width_px']} / {r['annotated_at_pin_row']['centre_x']}; pins {r['pins_far_end']['pin_lane_width_px']} / {r['pins_far_end']['pin_centre_x']})")
    res = {}
    for name, H in fits.items():
        if H is None:
            print(name, "no fit"); continue
        w, c = LM.width_centre_at(H, yb)
        ra = LM.residuals(H, [], arr_lines); rp = LM.residuals(H, pins_all, [])
        rf = LM.residuals(H, foul, [])
        # foul-line width under H at the annotated bottom row
        wb, cb = LM.width_centre_at(H, ann["bottom_left"][1])
        sc = LM.score_h(stem, f, H)  # vs annotated truth
        print(f"{name:32s} far width {w:6.1f} centre {c:7.1f} | foul width {wb:6.1f} | arrow resid in: {np.round(ra,2)} mean {np.mean(np.abs(ra)):.2f} | pin resid in: mean {np.mean(rp):.2f} 7/10 {rp[6]:.2f}/{rp[9]:.2f} | foul resid {np.round(rf,2)} | MAE vs ann {sc['board_mae']} tail {sc['board_mae_last20']}")
        res[name] = {"far_width_px": round(w, 2), "far_centre_px": round(c, 2), "foul_width_px": round(wb, 2), "arrow_resid_in": [round(v, 2) for v in ra],
                     "pin_resid_in": [round(v, 2) for v in rp], "foul_resid_in": [round(v, 2) for v in rf], "mae_vs_annotation": sc}
    out[stem] = {"frame": f, "pin_base_row_y": yb, "arrows_used": sorted(arrows), "fits": res}
C.dump(C.RESULTS / "e1_consistency.json", out)
