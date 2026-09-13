"""Generate video_script.json (cards for review_video.py) from results/*.json + fixed text.
usage: video_script.py"""
import json
import numpy as np
import common as C

def fmt(v, nd=2):
    return "-" if v is None else (f"{v:.{nd}f}" if isinstance(v, (int, float)) and not isinstance(v, bool) else str(v))

e1 = {r["stem"]: r for r in C.load(C.RESULTS / "e1_summary.json")}
bl = C.load(C.RESULTS / "baselines_rescored.json")
e3 = {s: C.load(C.RESULTS / f"e3_fit_loop3__{s}.json")["variants"] for s in C.STEMS}
e2 = {s: C.load(C.RESULTS / f"e2_detect_loop3__{s}.json")["summary"] for s in C.STEMS}
e4 = {s: C.load(C.RESULTS / f"e4_camera_loop3__{s}.json")["summary"] for s in C.STEMS if (C.RESULTS / f"e4_camera_loop3__{s}.json").exists()}

def v(s, name, key):
    return e3[s].get(name, {}).get("summary", {}).get(key)

script = {
 "title": {"title": "Do more lane landmarks make the board number more accurate?", "sub": "Lane-landmarks loop, 2026-09-13 - pins, arrows and the foul line as homography constraints",
           "lines": ["Loops 1-3 fitted the lane from four corners; every remaining error sat at the pin end, where a board is 1-2 px,",
                     "and the hand-clicked corners there were themselves 1-3 boards off (loop 2).",
                     "This loop: (E1) a truth from the physical landmarks, (E2) detect them from a rough lane, (E3) fit one homography",
                     "to all of them, (E4) use them as the camera model. Every number in three truths: hand corners, pins, all landmarks."]},
 "question": {"title": "The landmarks and what they constrain", "sub": "positions fixed by the rules of the game",
              "lines": ["foul line, both ends           0 ft, boards 1 and 39        near end (the annotation already has it)",
                        "seven arrows                   ~15 ft, boards 5 ... 35       absolute board positions mid-lane, x-only constraints",
                        "ten pin bases                  60-62.6 ft, 12 in apart        far-end centre AND width from a physical ruler",
                        "range-finder dots              34-44 ft                      visible on none of the three videos",
                        "", "Hypothesis: an over-determined, weighted, robust fit to all visible landmarks beats the four-corner fit,",
                        "most of all at the far end, and the pins fix the width that neither SAM nor the student gets right."]},
 "truth": {"title": "E1 - the truth first: the ten-pin rack as a ruler", "sub": "pre-hit frame; rack template projected through the annotated quad, similarity fitted to the white pins; arrows from the rectified lane",
           "lines": [f"sample_input  hand far width {fmt(e1['sample_input']['annotated']['width_px'],1)} px, pins {fmt(e1['sample_input']['pins']['width_px'],1)} px  ({fmt(e1['sample_input']['pins']['width_px']/e1['sample_input']['annotated']['width_px']*100,0)} %); centre shift {fmt(e1['sample_input']['pins']['centre_px']-e1['sample_input']['annotated']['centre_px'],1)} px; arrows 7/7, err vs hand / pins {fmt(e1['sample_input']['arrows']['abs_err_boards']['annotated'])} / {fmt(e1['sample_input']['arrows']['abs_err_boards']['pins'])} boards",
                     f"Chardie       hand {fmt(e1['20260112_121117']['annotated']['width_px'],1)} px, pins {fmt(e1['20260112_121117']['pins']['width_px'],1)} px  ({fmt(e1['20260112_121117']['pins']['width_px']/e1['20260112_121117']['annotated']['width_px']*100,0)} %); centre shift {fmt(e1['20260112_121117']['pins']['centre_px']-e1['20260112_121117']['annotated']['centre_px'],1)} px; arrows {e1['20260112_121117']['arrows']['found']}/7, err {fmt(e1['20260112_121117']['arrows']['abs_err_boards']['annotated'])} / {fmt(e1['20260112_121117']['arrows']['abs_err_boards']['pins'])}",
                     f"tom_old       hand {fmt(e1['tom_old']['annotated']['width_px'],1)} px, pins {fmt(e1['tom_old']['pins']['width_px'],1)} px  ({fmt(e1['tom_old']['pins']['width_px']/e1['tom_old']['annotated']['width_px']*100,0)} %); centre shift {fmt(e1['tom_old']['pins']['centre_px']-e1['tom_old']['annotated']['centre_px'],1)} px; arrows 7/7, err {fmt(e1['tom_old']['arrows']['abs_err_boards']['annotated'])} / {fmt(e1['tom_old']['arrows']['abs_err_boards']['pins'])}",
                     "", "Two independent pin widths (7-10 base spacing; outer edges of pins 7 and 10) agree to ~1 px on every video.",
                     "The arrows, detected without the pins, side with the pins on two of three videos; under one homography both agree to ~1 px.",
                     f"The hand annotation scores {fmt(e1['sample_input']['annotated_quad_mae']['vs_pins'])} / {fmt(e1['20260112_121117']['annotated_quad_mae']['vs_pins'])} / {fmt(e1['tom_old']['annotated_quad_mae']['vs_pins'])} boards against the pins truth (pin-end tail {fmt(e1['sample_input']['annotated_quad_mae']['vs_pins_tail'])} / {fmt(e1['20260112_121117']['annotated_quad_mae']['vs_pins_tail'])} / {fmt(e1['tom_old']['annotated_quad_mae']['vs_pins_tail'])}).",
                     "That is the error every earlier loop was measured against."]},
}
# baselines table card
rows = []
for label, key in (("student seg640 gated (loop 3), throw median", "student seg640 gated (loop 3)"), ("student +teacher (loop 3), throw median", "student seg640 +teacher gated (loop 3)"), ("student 1024 (loop 3), throw median", "student seg1024 gated (loop 3, tom_old only)")):
    for s in C.STEMS:
        r = bl["loop3"].get(f"{key}|{s}")
        if r:
            sm = r["summary"]; rows.append([C.SHORT[s], label, fmt(sm["throw_median_annotated"]), fmt(sm["throw_median_pins"]), fmt(sm["throw_median_all"]), fmt(sm["throw_tail_median_pins"])])
for label, key in (("SAM 2 even3 ball-path prompts (loop 2), pre-hit", "SAM 2 base, even3 ball-path prompts (loop 2) pre-hit"), ("SAM 2 far-end crop zoom_lo (loop 2), pre-hit", "SAM 2 base, far-end crop zoom_lo (loop 2) pre-hit"), ("SAM 2 + pin centre pins_m (loop 2), pre-hit", "SAM 2 + pin centre pins_m (loop 2) pre-hit")):
    for s in C.STEMS:
        r = bl["loop2"].get(f"{key}|{s}")
        if r:
            rows.append(([C.SHORT[s], label, fmt(r["mae_annotated"]), fmt(r["mae_pins"]), fmt(r["mae_all"]), fmt(r["tail_pins"])], [150, 150, 160]))
script["baselines_table"] = {"title": "Loops 2-3 re-scored in the three truths (board MAE, lower is better)", "sub": "same corners, same frames, same metric - only the truth changes; tail = last 20 % of the ball path (the pin end)",
                             "header": ["video", "method", "vs hand corners", "vs pins", "vs all landmarks", "tail vs pins"], "cols": [60, 300, 1080, 1300, 1480, 1700], "rows": rows, "scale": 0.66, "dy": 32, "secs": 14,
                             "note": ["tom_old's student is 1.6 boards off, not 3.2; loop 2's far-end crop is the best SAM method on sample_input (0.15), not the worst (0.89)."]}
# E2 card
rows = []
for s in C.STEMS:
    q = e2[s]
    rows.append([C.SHORT[s], f"{q['pins']['fired']}/{q['pins']['frames_standing']}", fmt(q['pins']['px_err_mean_median']), fmt(q['pins']['centre_err_boards_median_abs']), fmt(q['pins']['span_err_boards_median_abs']), fmt(q['arrows']['correct_per_frame_mean']), fmt(q['arrows']['false_per_frame']), fmt(q['arrows']['recall_within_1.5_boards']), fmt(q['arrows']['dx_boards_median_abs']), f"{fmt(q['pins']['ms'],0)} / {fmt(q['arrows']['ms'],0)}"])
script["e2_table"] = {"title": "E2 - detecting the landmarks from loop 3's student lane, every frame", "sub": "pins: rack fit initialised from the student's far end (while the pins stand); arrows: blob detector on the student-rectified lane; scored against the E1 landmarks projected into each frame",
                      "header": ["video", "pins fired / standing", "pin px err (med)", "pin centre err (boards)", "pin span err (boards)", "arrows correct / frame", "false / frame", "arrow recall", "arrow dx (boards)", "ms pins / arrows"],
                      "cols": [60, 260, 500, 700, 940, 1160, 1380, 1520, 1660, 1800], "rows": rows, "scale": 0.62, "dy": 34, "secs": 12,
                      "note": ["the learned arrow head (two-class yolo11n-seg, 640 px) detects zero arrows on held-out tom_old; the classical detector carries E2", "one-column alias of the rack fit on 2-4 % of frames from a poor hypothesis at 720p: guarded by the score margin at +-1 column"]}
# E3 card
rows = []
for name in ("corners", "corners+arrows", "corners+pins10", "corners+arrows+pins10", "arrows+pins10+weakfoul"):
    for s in C.STEMS:
        rows.append(([C.SHORT[s], name, fmt(v(s, name, "throw_median_annotated")), fmt(v(s, name, "throw_median_pins")), fmt(v(s, name, "throw_median_all")), fmt(v(s, name, "tail_median_pins")), fmt(v(s, name, "prehit_pins")), fmt(v(s, name, "width_err_px_median_pins"), 1)], [235, 235, 235] if "pins" in name else [150, 150, 160]))
script["e3_table"] = {"title": "E3 - one homography from all the landmarks, per frame (throw median, board MAE)", "sub": "input = loop 3's student lane only; corners = that lane itself; pins10 = the ten detected pin bases; arrows re-detected from the pin-corrected lane",
                      "header": ["video", "constraints", "vs hand corners", "vs pins", "vs all", "tail vs pins", "pre-hit vs pins", "far width err px"], "cols": [60, 240, 760, 980, 1160, 1320, 1520, 1720], "rows": rows, "scale": 0.7, "dy": 36, "secs": 16,
                      "note": ["pins fix the far end on every frame (width error 12 / 6 / 3 px -> under 1 px); arrows alone cannot extrapolate 45 ft to the pins and are not needed once the pins are in",
                               "Chardie's error does not move against the pins truth because the student's foul-line corners are 2 boards off - the near end is the next landmark to detect"]}
# E4 card
si = e4.get("sample_input", {})
script["e4"] = {"title": "E4 - the static landmarks as the camera model", "sub": "arrows + pin bases matched to the first frame, RANSAC similarity per frame, vs loop 3's ORB model on sample_input's hand-clicked per-frame corners",
                "lines": [f"sample_input (handheld): hand corners of frame 0 carried onto every frame - landmarks {fmt(si.get('err_landmarks_px_mean'))} px mean, ORB {fmt(si.get('err_orb_px_mean'))} px",
                          f"    at the pin end: landmarks {fmt(si.get('err_landmarks_top_px_mean'))} px, ORB {fmt(si.get('err_orb_top_px_mean'))} px;  worst frame {fmt(si.get('err_landmarks_px_max'))} vs {fmt(si.get('err_orb_px_max'))} px;  {fmt(si.get('landmarks_per_frame_median'),0)} landmarks per frame",
                          f"Chardie (handheld, no per-frame truth): {fmt(e4.get('20260112_121117', {}).get('vs_orb_px_mean'))} px from ORB;  tom_old (tripod): {fmt(e4.get('tom_old', {}).get('vs_orb_px_mean'))} px from ORB with only {fmt(e4.get('tom_old', {}).get('landmarks_per_frame_median'),0)} landmarks median (pins fall at f171 of 409)",
                          "", "While the pins stand, 17 static points at two depths beat ORB on the whole frame, most of all at the pin end.",
                          "After the hit only the seven arrows remain, nearly collinear at one depth: the similarity is ill-conditioned. Two depths are needed."]}
script["conclusion"] = {"title": "What the results say", "sub": None,
    "lines": ["1. The hand corners were the floor, and it was 1-2 boards at the pins: 10 % too wide on sample_input, 7 % too narrow and 4 px left on tom_old.",
              "2. The pins are the far-end ruler and fix it on every frame from a lane that was 12 px off: sample_input 1.19 -> 0.37, tom_old 1.61 -> 0.41 boards (pins truth),",
              "   and 1.83 -> 0.77 against the hand corners, which never saw a pin. Far-end width error: 12 / 6 / 3 px -> under 1 px.",
              "3. The arrows cannot fix the far end (extrapolating 45 ft from a 30-board baseline) and add nothing once the pins are in;",
              "   with the pins and no foul-line input they recover the pre-hit lane to 0.05 boards, and they are what is left after the pins fall.",
              "4. The student's near end is as wrong as its far end (2-3 boards at the foul line on two videos): the next landmark to detect is the foul line.",
              "5. Rack-fit alias (one pin column) on 2-4 % of frames: guard with the score margin at +-1 column.",
              "6. Landmarks beat ORB as the camera model while the pins stand (4.0 vs 5.3 px; 2.4 vs 5.2 at the pin end).",
              "7. Learned arrows: zero detections at 640 and 1024 px. Aside: the two-class 1024 student (batch 4) gives a lane on every tom_old frame at 0.26 boards vs pins."]}
script["engine"] = {"title": "Recommendation for the engine", "sub": None,
    "lines": ["- Detect the pin rack and refit the homography on every frame while the pins stand; the student or SAM lane is the initial guess,",
              "  the ten pin bases at their rule-book coordinates are the constraint; accept by the alias margin.",
              "- Treat the four corners as a hypothesis, not a measurement; add a foul-line / gutter-edge landmark at the near end.",
              "- Use the arrows for the camera (with the pins) and for a lane with no foul-line input, not for the far end.",
              "- Rebuild the truth before the next accuracy claim: results/landmarks_<stem>.json, common.truth_corners(stem, f, 'pins'). Report both columns."]}
(C.HERE / "video_script.json").write_text(json.dumps(script, indent=1))
print("wrote video_script.json with", list(script))
