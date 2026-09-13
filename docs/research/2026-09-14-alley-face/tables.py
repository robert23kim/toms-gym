"""Markdown tables for the README from results/*.json. usage: tables.py -> results/tables.md"""
import json

import numpy as np

import af

S = af.SHORT


def fmt(v, nd=2):
    if v is None:
        return "-"
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, (int, np.integer)):
        return str(v)
    if isinstance(v, (float, np.floating)):
        return f"{v:.{nd}f}"
    return str(v)


def e1_table():
    d = af.load(af.constellation_path()); sm = d["summary"]
    out = ["| feature | lane position (in) | count | source | " + " | ".join(f"visible on {S[s]} (pre-hit)" for s in af.STEMS) + " |", "|---|---|---|---|---|---|---|"]
    V = sm["arrow_V"]
    vis = sm["visibility_prehit"]
    out.append(f"| foul-line corners | (0, 0), (41.5, 0) | 2 | rule | " + " | ".join(f"{vis[s]['foul']['visible']}/2" for s in af.STEMS) + " |")
    for band, cls, label in (("foul", "fdot", "foul-line dots (approach side)"), ("guide", "dot", "guide dots"), ("approach", "adot", "approach dots")):
        r = sm["dot_rows"].get(band, {})
        if not r.get("found"):
            out.append(f"| {label} | not found | - | - | " + " | ".join("-" for _ in af.STEMS) + " |"); continue
        out.append(f"| {label} | y = {r['y_ft']:.2f} ft ({r['y_ft'] * 12:.1f} in), x = 20.75 + k x {r['pitch_in']:.2f} in ({r['pitch_boards']} boards), k = {r['k_model'][0]}..{r['k_model'][1]} | {r['count_model']} ({r['count_observed']} observed) | measured on {S[r['lead']['stem']]} f{r['lead']['frame']} (+ pooled frames), symmetric completion; measured centre {r['measured_centre_minus_lane_centre_in']:+.2f} in from the lane centre | " + " | ".join(f"{vis[s][cls]['visible']}/{vis[s][cls]['total']}" for s in af.STEMS) + " |")
    out.append(f"| seven arrows | boards 5..35, V centre {V['centre_ft']:.2f} ft, {V['ft_per_5_boards']:.2f} ft per 5 boards (per video: " + ", ".join(f"{S[s]} {V['per_video'][s]['centre_ft']:.2f}/{V['per_video'][s]['ft_per_5_boards']:.2f}" for s in af.STEMS) + ") | 7 | rule-book boards, depth from loop 4 | " + " | ".join(f"{vis[s]['arrow']['visible']}/7" for s in af.STEMS) + " |")
    out.append("| ten pin bases | rule-book rack, head pin at 60 ft | 10 | rule | " + " | ".join(f"{vis[s]['pin']['visible']}/10" for s in af.STEMS) + " |")
    out.append("| gutter edges, foul line | x = 0, x = 41.5, y = 0 | lines | rule | all | all | all |")
    return "\n".join(out)


def timeline_table():
    d = af.load(af.RESULTS / "e1_timeline_summary.json")
    out = ["| video | class | points | clear per frame (median, throw) | frames with >= half clear (of throw frames) | hidden by the bowler | by the ball | pins in motion |", "|---|---|---|---|---|---|---|---|"]
    for s in af.STEMS:
        for cls, v in d[s]["classes"].items():
            ob = v["occluded_by"]
            out.append(f"| {S[s]} | {cls} | {v['n']} | {fmt(v['clear_median_throw'], 0)} | {v['frames_ge_half_clear_throw']}/{d[s]['throw_frames']} | {ob.get('person') or '-'} | {ob.get('ball') or '-'} | {ob.get('pins') or '-'} |")
    return "\n".join(out)


def e2_table():
    out = ["| video | frames | ms | dark marks / frame (strong) | precision of the pool (strong) | rack blobs / frame, precision | rack recall (standing) | arrow recall, px | guide dots | foul dots | approach dots | true gutter / foul-line segments per frame |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for s in af.ALL_STEMS:
        p = af.RESULTS / f"e2_candidates_{s}.json"
        if not p.exists():
            continue
        d = af.load(p); m = d["summary"]
        if "recall" in m:
            r = m["recall"]; sg = m["segs_true_per_frame"]
            out.append(f"| {S[s]} | {m['frames']} | {fmt(m['ms_median'], 0)} | {fmt(m['marks_per_frame'], 0)} ({fmt(m['strong_marks_per_frame'], 0)}) | {fmt(m['marks_precision'], 3)} ({fmt(m['marks_precision_strong'], 3)}) | {fmt(m['racks_per_frame'], 1)}, {fmt(m['racks_precision'], 3)} | {fmt(m['rack_recall_standing'], 3)} | {fmt(r['arrow']['recall'], 2)}, {fmt(r['arrow']['px_err_median'], 1)} | {fmt(r['dot']['recall'], 2)} | {fmt(r['fdot']['recall'], 2)} | {fmt(r['adot']['recall'], 2)} | L {sg['gutter_left']} R {sg['gutter_right']} foul {sg['foul_line']} |")
        else:
            out.append(f"| {S[s]} | {m['frames']} (every 3rd) | {fmt(m['ms_median'], 0)} | {fmt(m['marks_per_frame'], 0)} ({fmt(m['strong_marks_per_frame'], 0)}) | - | {fmt(m['racks_per_frame'], 1)}, - | - | - | - | - | - | - |")
    return "\n".join(out)


def e3_table():
    out = ["| video | feature set | frames | lanes found / frame (median) | right lane found (throw frames) | top score is the right lane | bowler's feet pick it | frame centre | widest | board MAE median: annotated / pins / all | tail (pins) | pre-hit (pins) | far width err px | far centre err px | ms |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for s in af.STEMS:
        for tag in ("", "ablate__", "heat_class_lovo_tom_old__", "heat_landmark_lovo_tom_old__"):
            p = af.RESULTS / f"e3_face_{tag}{s}.json"
            if not p.exists():
                continue
            d = af.load(p)
            label = {"": "", "ablate__": " (every 5th frame)", "heat_class_lovo_tom_old__": " - pool = class heatmap model's arrows (held-out)", "heat_landmark_lovo_tom_old__": " - pool = landmark heatmap model's arrows (held-out)"}[tag]
            for sname, m in d["summary"].items():
                out.append(f"| {S[s]} | {sname}{label} | {m['frames']} | {fmt(m['lanes_per_frame_median'], 0)} | {fmt(m.get('right_found_frac'), 2)} | {fmt(m.get('top_is_right_frac'), 2)} | {fmt(m.get('feet_pick_right_frac'), 2)} | {fmt(m.get('centre_pick_right_frac'), 2)} | {fmt(m.get('widest_pick_right_frac'), 2)} | {fmt(m.get('mae_median_annotated'))} / {fmt(m.get('mae_median_pins'))} / {fmt(m.get('mae_median_all'))} | {fmt(m.get('tail_median_pins'))} | {fmt(m.get('prehit_pins'))} | {fmt(m.get('far_width_err_px_medabs_pins'), 1)} | {fmt(m.get('far_centre_err_px_medabs_pins'), 1)} | {fmt(m['ms_median'], 0)} |")
    rows2 = ["| video | feature set | frames | lanes / frame (median, max) | frames with >= 1 lane | ball's lane found | ball's lane is the top score | ms |", "|---|---|---|---|---|---|---|---|"]
    for s in ("bowling_video", "IMG_0242"):
        p = af.RESULTS / f"e3_face_{s}.json"
        if not p.exists():
            continue
        d = af.load(p)
        for sname, m in d["summary"].items():
            rows2.append(f"| {S[s]} | {sname} | {m['frames']} | {fmt(m['lanes_per_frame_median'], 0)}, {m.get('lanes_per_frame_max')} | {fmt(m.get('frames_with_ge1_lane'), 2)} | {fmt(m.get('ball_lane_found_frac'), 2)} | {fmt(m.get('ball_lane_is_top_frac'), 2)} | {fmt(m['ms_median'], 0)} |")
    return "\n".join(out) + "\n\n" + "\n".join(rows2)


def e4_table():
    out = ["| video | variant | frames | throw median: annotated / pins / all | tail (pins) | pre-hit (pins) | last (pins) | far width err px | far centre err px | near corners err px (L / R) |", "|---|---|---|---|---|---|---|---|---|---|"]
    for s in af.STEMS:
        p = af.RESULTS / f"e4_align_{s}.json"
        if not p.exists():
            continue
        d = af.load(p); m = d["summary"]
        for v in ("e3", "rows+pins", "refit", "no-near", "rows-only", "pins-pooled"):
            if v not in m:
                continue
            q = m[v]; ne = q.get("near_corner_err_px_median")
            out.append(f"| {S[s]} | {v} | {q['ok']} | {fmt(q['throw_median_annotated'])} / {fmt(q['throw_median_pins'])} / {fmt(q['throw_median_all'])} | {fmt(q['tail_median_pins'])} | {fmt(q['prehit_pins'])} | {fmt(q['last_pins'])} | {fmt(q['far_width_err_px_medabs_pins'], 1)} | {fmt(q['far_centre_err_px_medabs_pins'], 1)} | " + (f"{fmt(ne['bottom_left'], 1)} / {fmt(ne['bottom_right'], 1)}" if ne else "-") + " |")
    return "\n".join(out)


def e5_table():
    out = ["| video | frames | camera fits | landmarks in common (median; after the hit) | pooled rack (pins, frames) | lane on every frame: throw median annotated / pins / all | tail (pins) | after the hit (pins) | last (pins) | camera vs hand corners px: landmarks / ORB (pin end) | max |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for s in af.STEMS:
        p = af.RESULTS / f"e5_persist_{s}.json"
        if not p.exists():
            continue
        m = af.load(p)["summary"]; ce = m.get("cam_err_px"); cm = m.get("cam_err_px_max")
        out.append(f"| {S[s]} | {m['frames']} | {m['camera_fits']} | {fmt(m['common_median'], 0)}; {fmt(m.get('common_median_after_hit'), 0)} | {m['pooled_pins']}, {m['pooled_frames_median']} | {fmt(m.get('throw_median_annotated'))} / {fmt(m.get('throw_median_pins'))} / {fmt(m.get('throw_median_all'))} | {fmt(m.get('tail_median_pins'))} | {fmt(m.get('post_hit_median_pins'))} ({m.get('post_hit_frames')} f) | {fmt(m.get('last_pins'))} | " + (f"{ce['landmarks']} / {ce['orb']} ({ce['landmarks_top']} / {ce['orb_top']})" if ce else "-") + " | " + (f"{cm['landmarks']} / {cm['orb']}" if cm else "-") + " |")
    return "\n".join(out)


def e6_table():
    out = ["| model | held-out video | class | clear points | recall (6 px) | px err median | precision | classical E2 recall, same frames | in-distribution recall (training videos' held-back frames) |", "|---|---|---|---|---|---|---|---|---|"]
    fit = ["| model | held-out video | frames fitted (throw) | named points / frame | constellation fit: throw median annotated / pins / all | tail (pins) | pre-hit (pins) | far width err px | ms / frame |", "|---|---|---|---|---|---|---|---|---|"]
    import glob
    for p in sorted(glob.glob(str(af.RESULTS / "e6_eval_*.json"))):
        d = af.load(p); name = p.split("e6_eval_")[1][:-5]; variant, fold = name.split("_", 1); held = fold.replace("lovo_", "")
        cl = d["classical_e2_same_frames"]
        for c, v in d["held_out"]["per_class"].items():
            ind = [q["per_class"][c]["recall"] for q in d["in_distribution"].values() if q["per_class"][c]["recall"] is not None]
            out.append(f"| {variant} | {S[held]} | {c} | {v['clear']} | {fmt(v['recall'])} | {fmt(v['px_err_median'], 1)} | {fmt(v['precision'], 3)} | {fmt(cl[c]['recall']) if c in cl else '-'} | {fmt(float(np.mean(ind))) if ind else '-'} |")
        f = d["held_out"].get("fit")
        if f:
            fit.append(f"| {variant} | {S[held]} | {f['ok_in_throw']} | {fmt(f['n_named_median'], 0)} | {fmt(f['throw_median_annotated'])} / {fmt(f['throw_median_pins'])} / {fmt(f['throw_median_all'])} | {fmt(f['tail_median_pins'])} | {fmt(f['prehit_pins'])} | {fmt(f['far_width_err_px_medabs_pins'], 1)} | {fmt(d['ms_median'], 0)} |")
    return "\n".join(out) + "\n\n" + "\n".join(fit)


if __name__ == "__main__":
    parts = []
    for title, fn in (("E1 constellation", e1_table), ("E1 visibility timeline", timeline_table), ("E2 candidates", e2_table), ("E3 finding the face", e3_table), ("E4 aligning the face", e4_table), ("E5 persistence", e5_table), ("E6 heatmap model", e6_table)):
        try:
            parts += [f"## {title}\n", fn(), ""]
        except Exception as e:  # noqa: BLE001
            parts += [f"## {title}\n", f"(not available: {e})", ""]
    (af.RESULTS / "tables.md").write_text("\n".join(parts) + "\n")
    print("\n".join(parts))
