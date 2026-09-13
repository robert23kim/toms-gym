"""E1: landmark truth from the physical lane on standing-pin frames.

Per annotated video and frame (pre-hit -2 / -4 / -6): fit the ten-pin rack to the
white pins (template from the annotated quad, similarity search), detect the
seven arrows on the rectified lane, take the foul-line ends from the annotated
bottom corners. Build the pins-based far end (centre = rack centre, width =
7-10 spacing x 41.5/36 at the back-row base) and report how far the hand
corners are from it. Writes results/landmarks_<stem>.json (pre-hit frame),
results/e1_truth.json, overlays/e1_*.jpg.
usage: e1_truth.py [stems...]"""
import sys

import cv2
import numpy as np

import common as C
import landmarks as LM

L = C.L
C.use_full_camera()


def draw_rack(img, pts, scale, color, th=1):
    for (x, y), s in zip(pts, scale):
        h = LM.PIN_H_IN * s
        cv2.line(img, (int(round(x)), int(round(y))), (int(round(x)), int(round(y - h))), color, th, cv2.LINE_AA)
        cv2.circle(img, (int(round(x)), int(round(y))), 2, color, -1, cv2.LINE_AA)


def pins_truth(stem, f, bases, y_top, y_bot):
    """Far end from the pins: back-row bases 7 and 10 give centre + width at their
    row; edge lines through the annotated foul-line ends; corners at y_top / y_bot."""
    ann = L.truth_corners(stem, f)
    p7, p10 = bases[6], bases[9]
    y_base = 0.5 * (p7[1] + p10[1])
    cx = 0.5 * (p7[0] + p10[0])
    width = (p10[0] - p7[0]) * LM.W_IN / 36.0
    far_l = (cx - width / 2, y_base); far_r = (cx + width / 2, y_base)
    out = {}
    for name, far, near in (("left", far_l, ann["bottom_left"]), ("right", far_r, ann["bottom_right"])):
        a = (far[0] - near[0]) / (far[1] - near[1]); b = near[0] - a * near[1]
        out[f"top_{name}"] = (a * y_top + b, y_top); out[f"bottom_{name}"] = (a * y_bot + b, y_bot)
    return out, {"pin_base_row_y": round(float(y_base), 1), "pin_centre_x": round(float(cx), 2), "pin_lane_width_px": round(float(width), 2)}


def run(stem, frames):
    per_frame = []
    for f in frames:
        img = C.read_frame(stem, f)
        ann = L.truth_corners(stem, f)
        y_top, y_bot = L.gt_y(stem, f)
        w_px = ann["top_right"][0] - ann["top_left"][0]
        H0 = LM.h_from_quad(ann)
        pts0, sc0 = LM.rack_template(H0)
        pts, sc, params, score, contrast, parts = LM.fit_rack(img, H0, w_px)
        pts_ref = LM.refine_pin_columns(img, pts, sc)
        arrows, _ = LM.detect_arrows(img, H0, debug=str(C.OVERLAYS / f"e1_arrows_rect_{stem}_f{f}.jpg"))
        truth_p, pinfo = pins_truth(stem, f, pts_ref, y_top, y_bot)
        # hand corners vs pins truth
        ann_vs = C.score_corners(stem, f, ann, truth=truth_p)
        # same-row comparison at the pin base row
        wa, ca = LM.width_centre_at(H0, pinfo["pin_base_row_y"])
        # arrows: nominal board vs board under each truth
        Hp = LM.h_from_quad(truth_p)
        arr_rows = {}
        for b, v in arrows.items():
            xa = LM.to_lane(H0, [(v["x"], v["y"])])[0]; xp = LM.to_lane(Hp, [(v["x"], v["y"])])[0]
            arr_rows[b] = {"x": round(v["x"], 2), "y": round(v["y"], 2), "darkness": v["darkness"], "area": v["area"],
                           "board_ann": round(float(LM.boards_from_lane_x(xa[0])), 2), "board_pins": round(float(LM.boards_from_lane_x(xp[0])), 2),
                           "ft_ann": round(float(xa[1] / 12), 2), "ft_pins": round(float(xp[1] / 12), 2),
                           "err_boards_ann": round(float(LM.boards_from_lane_x(xa[0]) - LM.boards_from_lane_x(LM.board_x_in(b))), 2),
                           "err_boards_pins": round(float(LM.boards_from_lane_x(xp[0]) - LM.boards_from_lane_x(LM.board_x_in(b))), 2)}
        row = {"stem": stem, "frame": f, "rack": {"params": params, "score": round(score, 4), "contrast_sigma": round(contrast, 1), "parts": parts,
                                                   "bases": {str(p + 1): [round(float(x), 2), round(float(y), 2)] for p, (x, y) in enumerate(pts_ref)},
                                                   "scale_px_per_in": round(float(sc.mean()), 3)},
               "pins_far_end": pinfo,
               "annotated_at_pin_row": {"width_px": round(float(wa), 2), "centre_x": round(float(ca), 2)},
               "pins_minus_annotated": {"centre_px": round(float(pinfo["pin_centre_x"] - ca), 2), "width_px": round(float(pinfo["pin_lane_width_px"] - wa), 2),
                                        "width_ratio": round(float(pinfo["pin_lane_width_px"] / wa), 3)},
               "truth_pins_corners": {k: [round(float(v[0]), 2), round(float(v[1]), 2)] for k, v in truth_p.items()},
               "annotated_corners": {k: [round(float(v[0]), 2), round(float(v[1]), 2)] for k, v in ann.items()},
               "annotated_vs_pins_truth": ann_vs,
               "arrows": arr_rows, "arrows_found": len(arr_rows)}
        if arr_rows:
            ea = [abs(v["err_boards_ann"]) for v in arr_rows.values()]; ep = [abs(v["err_boards_pins"]) for v in arr_rows.values()]
            row["arrow_abs_err_boards"] = {"annotated": round(float(np.mean(ea)), 2), "pins": round(float(np.mean(ep)), 2)}
        per_frame.append(row)
        # overlays: pin crop with template before (magenta) / after (green), plus truths
        cx = (ann["top_left"][0] + ann["top_right"][0]) / 2; cy = (ann["top_left"][1] + ann["top_right"][1]) / 2
        h, w = img.shape[:2]
        x1, x2 = int(max(0, cx - 1.0 * w_px)), int(min(w, cx + 1.0 * w_px)); y1, y2 = int(max(0, cy - 1.0 * w_px)), int(min(h, cy + 0.4 * w_px))
        z = max(1, int(round(600 / max(1, x2 - x1))))
        crop = cv2.resize(img[y1:y2, x1:x2], None, fx=z, fy=z, interpolation=cv2.INTER_CUBIC)
        sh = lambda p: (np.asarray(p, float) - [x1, y1]) * z  # noqa: E731
        draw_rack(crop, sh(pts0), sc0 * z, (255, 0, 255), 1)
        draw_rack(crop, sh(pts_ref), sc * z, (0, 255, 0), 2)
        for k, col in (("top_left", (0, 220, 0)), ("top_right", (0, 220, 0))):
            cv2.circle(crop, tuple(int(v) for v in sh(ann[k])), 6, (0, 200, 255), 2)
            cv2.circle(crop, tuple(int(v) for v in sh(truth_p[k])), 6, (255, 255, 0), 2)
        cv2.putText(crop, f"{C.SHORT[stem]} f{f} rack fit x{z}: magenta=annotation template, green=fit ({contrast:.0f} sigma)", (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
        cv2.putText(crop, "orange=annotated top corners, cyan=pins-based", (8, 44), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
        cv2.imwrite(str(C.OVERLAYS / f"e1_rack_{stem}_f{f}.jpg"), crop, [cv2.IMWRITE_JPEG_QUALITY, 92])
        # full-frame landmarks overlay
        full = img.copy()
        for q, col in ((ann, (0, 200, 255)), (truth_p, (255, 255, 0))):
            p = np.array([q["top_left"], q["top_right"], q["bottom_right"], q["bottom_left"]], np.int32)
            cv2.polylines(full, [p], True, col, 1, cv2.LINE_AA)
        for (x, y) in pts_ref:
            cv2.circle(full, (int(x), int(y)), 3, (0, 255, 0), -1, cv2.LINE_AA)
        for b, v in arr_rows.items():
            cv2.drawMarker(full, (int(v["x"]), int(v["y"])), (255, 0, 255), cv2.MARKER_TRIANGLE_UP, 12, 2, cv2.LINE_AA)
            cv2.putText(full, str(b), (int(v["x"]) + 6, int(v["y"]) - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 255), 1)
        cv2.putText(full, f"{C.SHORT[stem]} f{f}: pins (green), arrows (magenta), annotated quad (orange), pins-based quad (cyan)", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.imwrite(str(C.OVERLAYS / f"e1_landmarks_{stem}_f{f}.jpg"), full, [cv2.IMWRITE_JPEG_QUALITY, 88])
        print(f"{C.SHORT[stem]:13s} f{f}: rack {params} score {score:.3f} ({contrast:.0f}s) pins-ann centre {row['pins_minus_annotated']['centre_px']:+.1f}px width x{row['pins_minus_annotated']['width_ratio']:.3f}  "
              f"ann vs pins-truth MAE {ann_vs['board_mae']} (tail {ann_vs['board_mae_last20']})  arrows {len(arr_rows)}/7 abs err ann/pins {row.get('arrow_abs_err_boards')}", flush=True)
    return per_frame


def fraction_along_top(ann, quad):
    """Top corners of `quad` (at the annotated top row) as fractions along the annotated top edge."""
    tl, tr = np.array(ann["top_left"], float), np.array(ann["top_right"], float)
    d = tr - tl; n = float(d @ d)
    return {"a_l": round(float((np.array(quad["top_left"]) - tl) @ d / n), 5), "a_r": round(float((np.array(quad["top_right"]) - tl) @ d / n), 5)}


def all_landmark_truth(stem, f, row):
    """Fit D: foul ends (weight 10) + all ten pin bases (2D) + arrows (x-only), corners at the annotated rows."""
    ann = L.truth_corners(stem, f); y_top, y_bot = L.gt_y(stem, f)
    bases = LM.pin_bases_in()
    foul = [((ann["bottom_left"][0], ann["bottom_left"][1]), (0.0, 0.0)), ((ann["bottom_right"][0], ann["bottom_right"][1]), (LM.W_IN, 0.0))]
    pins = [((row["rack"]["bases"][str(k)][0], row["rack"]["bases"][str(k)][1]), bases[k]) for k in range(1, 11)]
    arr = [((v["x"], v["y"]), LM.board_x_in(int(b))) for b, v in row["arrows"].items()]
    H = LM.fit_homography(foul + pins, arr, [10, 10] + [1] * 10, [1] * len(arr))
    quad = LM.corners_from_h(H, y_top, y_bot)
    # arrows' down-lane position under this physical fit -> V parameters
    ys = {int(b): float(LM.to_lane(H, [(v["x"], v["y"])])[0][1]) / 12 for b, v in row["arrows"].items()}
    v = None
    if len(ys) >= 4:
        bs = np.array(sorted(ys)); d = np.abs(bs - 20); yy = np.array([ys[b] for b in bs])
        k, c = np.polyfit(d, yy, 1)
        v = {"centre_ft": round(float(c), 2), "ft_per_5_boards": round(float(-k * 5), 3), "arrow_ft": {str(b): round(ys[b], 2) for b in bs}}
    return H, quad, {"arrow_resid_in": [round(x, 2) for x in LM.residuals(H, [], arr)], "pin_resid_in": [round(x, 2) for x in LM.residuals(H, pins, [])], "V": v}


if __name__ == "__main__":
    stems = sys.argv[1:] or C.STEMS
    all_rows = []
    summary = []
    for stem in stems:
        fp = C.frame_for(stem, "prehit")
        rows = run(stem, [fp, fp - 2, fp - 4])
        all_rows += rows
        main = rows[0]
        ann = L.truth_corners(stem, fp)
        truth_p = {k: tuple(v) for k, v in main["truth_pins_corners"].items()}
        H_all, truth_a, all_info = all_landmark_truth(stem, fp, main)
        lm = {}
        for p, xy in main["rack"]["bases"].items():
            lm[f"pin_{p}_base"] = {"x": xy[0], "y": xy[1], "frame": fp, "source": "detected", "confidence": round(min(1.0, main["rack"]["contrast_sigma"] / 5), 2)}
        for b, v in main["arrows"].items():
            lm[f"arrow_{b}"] = {"x": v["x"], "y": v["y"], "frame": fp, "source": "detected", "confidence": round(min(1.0, v["darkness"] / 40), 2)}
        lm["foul_left"] = {"x": ann["bottom_left"][0], "y": ann["bottom_left"][1], "frame": fp, "source": "annotation", "confidence": 0.9}
        lm["foul_right"] = {"x": ann["bottom_right"][0], "y": ann["bottom_right"][1], "frame": fp, "source": "annotation", "confidence": 0.9}
        # detector repeatability over the three standing-pin frames, relative to that frame's annotation (camera-free)
        rep = {"centre_px": [r["pins_minus_annotated"]["centre_px"] for r in rows], "width_ratio": [r["pins_minus_annotated"]["width_ratio"] for r in rows],
               "arrows_found": [r["arrows_found"] for r in rows]}
        rep["centre_px_std"] = round(float(np.std(rep["centre_px"])), 2); rep["width_ratio_std"] = round(float(np.std(rep["width_ratio"])), 4)
        doc = {"stem": stem, "frame": fp, "landmarks": lm,
               "top_edge_fraction": {"annotated": {"a_l": 0.0, "a_r": 1.0}, "pins": fraction_along_top(ann, truth_p), "all": fraction_along_top(ann, truth_a)},
               "pins_far_end": main["pins_far_end"], "truth_pins_corners": main["truth_pins_corners"],
               "truth_all_corners": {k: [round(float(v[0]), 2), round(float(v[1]), 2)] for k, v in truth_a.items()},
               "all_fit": all_info, "repeatability_3_frames": rep,
               "top_edge_depth_in": round(float(np.mean(LM.to_lane(H_all, [ann["top_left"], ann["top_right"]])[:, 1])), 1)}
        C.dump(C.landmarks_path(stem), doc)
        # summary row (pre-hit frame)
        ann_vs_all = C.score_corners(stem, fp, ann, truth=truth_a)
        pins_vs_all = C.score_corners(stem, fp, truth_p, truth=truth_a)
        wa, ca = LM.width_centre_at(LM.h_from_quad(ann), main["pins_far_end"]["pin_base_row_y"])
        w_all, c_all = LM.width_centre_at(H_all, main["pins_far_end"]["pin_base_row_y"])
        board_px = float(wa) / 38.0; wa = float(wa); ca = float(ca); w_all = float(w_all); c_all = float(c_all)
        srow = {"stem": stem, "frame": fp, "pin_base_row_y": main["pins_far_end"]["pin_base_row_y"], "px_per_board_at_pins": round(board_px, 2),
                "annotated": {"width_px": round(wa, 1), "centre_px": round(ca, 1)},
                "pins": {"width_px": main["pins_far_end"]["pin_lane_width_px"], "centre_px": main["pins_far_end"]["pin_centre_x"]},
                "all_landmarks": {"width_px": round(w_all, 1), "centre_px": round(c_all, 1)},
                "hand_corner_vs_pins": {k: {"dx_px": round(ann[k][0] - truth_p[k][0], 1), "boards": round((ann[k][0] - truth_p[k][0]) / board_px, 2)} for k in ("top_left", "top_right")},
                "hand_corner_vs_all": {k: {"dx_px": round(ann[k][0] - truth_a[k][0], 1), "boards": round((ann[k][0] - truth_a[k][0]) / board_px, 2)} for k in ("top_left", "top_right")},
                "annotated_quad_mae": {"vs_pins": main["annotated_vs_pins_truth"]["board_mae"], "vs_pins_tail": main["annotated_vs_pins_truth"]["board_mae_last20"],
                                       "vs_all": ann_vs_all["board_mae"], "vs_all_tail": ann_vs_all["board_mae_last20"]},
                "pins_quad_vs_all": {"mae": pins_vs_all["board_mae"], "tail": pins_vs_all["board_mae_last20"]},
                "arrows": {"found": main["arrows_found"], "abs_err_boards": main.get("arrow_abs_err_boards"), "resid_in_all_fit": all_info["arrow_resid_in"]},
                "pin_resid_in_all_fit": all_info["pin_resid_in"], "V": all_info["V"], "repeatability": rep}
        summary.append(srow)
        print(stem, "fractions", doc["top_edge_fraction"], "V", all_info["V"] and {k: all_info["V"][k] for k in ("centre_ft", "ft_per_5_boards")}, "rep", rep)
    C.dump(C.RESULTS / "e1_truth.json", all_rows)
    C.dump(C.RESULTS / "e1_summary.json", summary)
    # markdown
    md = ["| video | px/board at pins | far width px: hand / pins / all | far centre px: hand / pins / all | hand TL, TR vs pins (px = boards) | annotated quad MAE vs pins (tail) | vs all (tail) | arrows found, abs err boards hand / pins | pins vs arrows agreement (all-fit resid, in) | repeatability over 3 frames (centre px std, width ratio std) |", "|---|---|---|---|---|---|---|---|---|---|"]
    for s in summary:
        hc = s["hand_corner_vs_pins"]
        md.append(f"| {C.SHORT[s['stem']]} f{s['frame']} | {s['px_per_board_at_pins']:.2f} | {s['annotated']['width_px']:.1f} / {s['pins']['width_px']:.1f} / {s['all_landmarks']['width_px']:.1f} | {s['annotated']['centre_px']:.1f} / {s['pins']['centre_px']:.1f} / {s['all_landmarks']['centre_px']:.1f} | "
                  f"{hc['top_left']['dx_px']:+.1f} = {hc['top_left']['boards']:+.1f}, {hc['top_right']['dx_px']:+.1f} = {hc['top_right']['boards']:+.1f} | {s['annotated_quad_mae']['vs_pins']} ({s['annotated_quad_mae']['vs_pins_tail']}) | {s['annotated_quad_mae']['vs_all']} ({s['annotated_quad_mae']['vs_all_tail']}) | "
                  f"{s['arrows']['found']}/7, {s['arrows']['abs_err_boards']['annotated'] if s['arrows']['abs_err_boards'] else '-'} / {s['arrows']['abs_err_boards']['pins'] if s['arrows']['abs_err_boards'] else '-'} | arrows {np.mean(np.abs(s['arrows']['resid_in_all_fit'])):.2f}, pins {np.mean(s['pin_resid_in_all_fit']):.2f} | {s['repeatability']['centre_px_std']}, {s['repeatability']['width_ratio_std']} |")
    (C.RESULTS / "e1_summary.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))
