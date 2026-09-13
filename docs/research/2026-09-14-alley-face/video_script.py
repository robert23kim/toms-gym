"""video_script.json for review_face.py: one answer card, the clip spec, one table card, one
recommendation card - numbers read from results/*.json. usage: video_script.py"""
import json

import numpy as np

import af

S = af.SHORT


def fmt(v, nd=2):
    return "-" if v is None else (f"{v:.{nd}f}" if isinstance(v, (int, float)) and not isinstance(v, bool) else str(v))


e3 = {s: af.load(af.RESULTS / f"e3_face_{s}.json")["summary"]["arrows+dots+rack+gutters"] for s in af.STEMS}
e3u = {s: af.load(af.RESULTS / f"e3_face_{s}.json")["summary"]["arrows+dots+rack+gutters"] for s in ("bowling_video",)}
e4 = {s: af.load(af.RESULTS / f"e4_align_{s}.json")["summary"] for s in af.STEMS}
e6 = {v: af.load(af.RESULTS / f"e6_eval_{v}_lovo_tom_old.json") for v in ("landmark", "class")}
abl = af.load(af.RESULTS / "e3_face_ablate__tom_old.json")["summary"]
c = af.load(af.constellation_path())["summary"]
heat = {}
for v in ("class", "landmark"):
    p = af.RESULTS / f"e3_face_heat_{v}_lovo_tom_old__tom_old.json"
    if p.exists():
        heat[v] = af.load(p)["summary"]["arrows+dots+rack+gutters"]

t = e3["tom_old"]; si = e3["sample_input"]
script = {
    "answer": {"title": "Does the alley have a face?  Yes - and it can be found without a ball, a mask or a prompt, where the camera can see its eyes.",
               "sub": "Alley-face loop, 2026-09-14: the lane's markings (arrows, three dot rows, the rack, the foul line) as one constellation with one degree of freedom - a homography",
               "lines": [f"Found from the raw feature pool alone: the right lane on {fmt(t['right_found_frac'] * 100, 0)} % of tom_old's throw frames ({fmt(t['prehit_pins'])} boards pre-hit, {fmt(t['mae_median_pins'])} median vs the pins truth),",
                         f"{fmt(si['right_found_frac'] * 100, 0)} % of sample_input's, 0 % of Chardie's (720p: the arrows have no contrast); four lanes per frame on the six-lane video.",
                         f"Arrows alone cannot do it ({fmt(abl['arrows']['right_found_frac'] * 100, 0)} % at {fmt(abl['arrows']['mae_median_pins'])} boards); arrows + the rack can ({fmt(abl['arrows+rack']['right_found_frac'] * 100, 0)}-{fmt(abl['arrows+dots+rack']['right_found_frac'] * 100, 0)} %).",
                         "", ("The constellation itself is off-centre: every dot row sits 0.4-0.7 in left of the lane centre under the truth.", (150, 150, 160)),
                         ("The top-scoring face is usually the neighbouring lane; choosing the bowler's lane needs the bowler or the ball.", (150, 150, 160)),
                         ("Aligning fixes the far end (rack) but not the near end: the dot rows are not in the pool on handheld video, so 0.62 -> 0.81.", (150, 150, 160)),
                         (f"A class-level heatmap model transfers the arrows to a new placement (recall {fmt(e6['class']['held_out']['per_class']['arrow']['recall'])}, precision {fmt(e6['class']['held_out']['per_class']['arrow']['precision'])}); a per-landmark one memorises positions ({fmt(e6['landmark']['held_out']['per_class']['arrow']['recall'])}).", (150, 150, 160))],
               "secs": 16, "scale": 0.8, "dy": 46},
    "clip": {"frames": None, "max_frames": 900},
    "table": {"title": "Board MAE vs the pins truth (throw median) - finding, aligning, and loop 4's baselines", "sub": "every row: the same ball path, the same metric; E3 = found from the pool with no lane input; E4 = rack refit + arrows as a rigid pattern; loop 4 = mask student + pin refit",
              "header": ["video", "loop 4: student", "loop 4: student + pins", "E3 found (frames)", "E3 pre-hit", "E4 aligned", "far width err px E3 -> E4", "top score = right lane"],
              "cols": [60, 300, 560, 860, 1120, 1320, 1520, 1760],
              "rows": [["tom_old", "1.61", "0.41", f"{fmt(t['mae_median_pins'])} ({fmt(t['right_found_frac'] * 100, 0)} %)", fmt(t['prehit_pins']), fmt(e4['tom_old']['rows+pins']['throw_median_pins']), f"{fmt(t['far_width_err_px_medabs_pins'], 1)} -> {fmt(e4['tom_old']['rows+pins']['far_width_err_px_medabs_pins'], 1)}", f"{fmt(t['top_is_right_frac'] * 100, 0)} %"],
                       ["sample_input", "1.19", "0.37", f"{fmt(si['mae_median_pins'])} ({fmt(si['right_found_frac'] * 100, 0)} %)", fmt(si['prehit_pins']), fmt(e4['sample_input']['rows+pins']['throw_median_pins']), f"{fmt(si['far_width_err_px_medabs_pins'], 1)} -> {fmt(e4['sample_input']['rows+pins']['far_width_err_px_medabs_pins'], 1)}", f"{fmt(si['top_is_right_frac'] * 100, 0)} %"],
                       ["Chardie", "0.64", "0.78", "not found (0 %)", "-", "-", "-", "-"],
                       (["bowling_video (6 lanes)", "-", "-", f"4 lanes / frame, ball's lane found {fmt(e3u['bowling_video']['ball_lane_found_frac'] * 100, 0)} %", "-", "-", "-", f"{fmt(e3u['bowling_video']['ball_lane_is_top_frac'] * 100, 0)} %"], [150, 150, 160])],
              "note": [f"heatmap model, held-out tom_old: class-level arrows recall {fmt(e6['class']['held_out']['per_class']['arrow']['recall'])} (precision {fmt(e6['class']['held_out']['per_class']['arrow']['precision'])}) vs the black-hat pool's 0.95 at 5 % precision; per-landmark model: arrows {fmt(e6['landmark']['held_out']['per_class']['arrow']['recall'])}, pins {fmt(e6['landmark']['held_out']['per_class']['pin']['recall'])}, dots 0"]
                      + ([f"constellation match on the class model's arrows, held-out tom_old: right lane on {fmt(heat['class']['right_found_frac'] * 100, 0)} % of throw frames at {fmt(heat['class']['mae_median_pins'])} boards (pool: {fmt(t['right_found_frac'] * 100, 0)} % at {fmt(t['mae_median_pins'])})"] if "class" in heat else []),
              "secs": 18, "scale": 0.68, "dy": 40},
    "recommend": {"title": "For the engine", "sub": None,
                  "lines": ["1. The constellation is a prompt-free lane proposal: dark-mark chains + a rack blob find a lane on sharp, close video (~1 s Python). Not at 720p.",
                            "2. Never pick the lane by constellation score - anchor on the bowler's feet or the ball; the best face is a neighbour on most frames.",
                            "3. Far end from the rack (loop 4), near end still from the mask student: the pool has no foul-line dots on handheld video.",
                            "4. Learned landmarks: class-level heatmaps transfer appearance (arrows 0.92 on a new placement), per-landmark heatmaps memorise geometry.",
                            "   The next data is other phones and angles, not more throws at this alley.",
                            "5. Truth near end: verified on tom_old by the visible lane edge, unverified on the other two; the dot rows are 0.4-0.7 in off the lane centre."],
                  "secs": 14, "scale": 0.8, "dy": 50},
}
(af.HERE / "video_script.json").write_text(json.dumps(script, indent=1))
print("wrote video_script.json", list(script))
