"""Markdown tables for the README from results/*.json. usage: tables.py  -> results/tables.md"""
import json
import numpy as np
import common as C

L = C.L


def fmt(v, nd=2):
    return "-" if v is None else (f"{v:.{nd}f}" if isinstance(v, (int, float)) and not isinstance(v, bool) else str(v))


def e2_table():
    out = ["| lane hypothesis | video | frames | pins: fired / standing | pins px err (median) | pin centre err (boards, med) | pin span err (boards, med) | alias frames (>3 boards) | arrows correct / frame | false / frame | arrow recall | arrow dx (boards, med) | ms pins / arrows |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for tag, label in (("loop3", "student seg640 gated (loop 3)"), ("loop3_plus", "student +teacher (loop 3)"), ("loop3_1024", "student 1024 (loop 3)"), ("seg2_1024", "two-class student 1024 (this loop)"), ("sam_even3_k", "SAM 2 even3 (loop 2, 2 frames)"), ("sam_zoom_lo_k", "SAM 2 crop (loop 2, 2 frames)")):
        for stem in C.STEMS:
            p = C.RESULTS / f"e2_detect_{tag}__{stem}.json"
            if not p.exists():
                continue
            d = C.load(p); s = d["summary"]; pr = [r for r in d["per_frame"] if r["pins"] and "centre_err_boards" in r["pins"]]
            alias = sum(1 for r in pr if abs(r["pins"]["centre_err_boards"]) > 3)
            out.append(f"| {label} | {C.SHORT[stem]} | {s['frames']} | {s['pins']['fired']} / {s['pins']['frames_standing']} | {fmt(s['pins']['px_err_mean_median'])} | {fmt(s['pins']['centre_err_boards_median_abs'])} | {fmt(s['pins']['span_err_boards_median_abs'])} | {alias} | {fmt(s['arrows']['correct_per_frame_mean'])} | {fmt(s['arrows']['false_per_frame'])} | {fmt(s['arrows']['recall_within_1.5_boards'])} | {fmt(s['arrows']['dx_boards_median_abs'])} | {fmt(s['pins']['ms'], 0)} / {fmt(s['arrows']['ms'], 0)} |")
    return "\n".join(out)


E3_MAIN = ["corners", "snapcorners", "corners+arrows", "corners+pins", "corners+pins10", "corners+arrows+pins10", "foul+arrows+pins10", "arrows+pins10", "arrows+pins10+weakfoul", "arrows+pins10+top", "snapfoul+pins10", "snapfoul+arrows+pins10",
           "corners+arrows+pins10+carry", "corners+arrows+pins10+carryLM", "corners+arrows(1pass)", "foul+arrows+pins(1pass)"]


def e3_table(tag, variants=E3_MAIN, title=None):
    out = [f"| variant ({tag}) | video | frames ok | throw median: annotated / pins / all | tail (last 20 %) pins | pre-hit pins | last pins | far width err px (pins, med) | far centre err px (pins, med abs) |",
           "|---|---|---|---|---|---|---|---|---|"]
    for stem in C.STEMS:
        p = C.RESULTS / f"e3_fit_{tag}__{stem}.json"
        if not C.has_result(p):
            continue
        d = C.load(p)["variants"]
        for v in variants:
            if v not in d:
                continue
            s = d[v]["summary"]
            out.append(f"| {v} | {C.SHORT[stem]} | {s['ok_in_throw']} | {fmt(s['throw_median_annotated'])} / {fmt(s['throw_median_pins'])} / {fmt(s['throw_median_all'])} | {fmt(s['tail_median_pins'])} | {fmt(s['prehit_pins'])} | {fmt(s['last_pins'])} | {fmt(s['width_err_px_median_pins'], 1)} | {fmt(s['centre_err_px_medabs_pins'], 1)} |")
    return "\n".join(out)


def e3_drop_table(tag):
    out = [f"| dropped landmark ({tag}, foul+arrows+pins base) | " + " | ".join(C.SHORT[s] + " throw median (pins) / tail" for s in C.STEMS) + " |", "|---|---|---|---|"]
    names = ["foul+arrows+pins", "foul+arrows+pins10"] + [f"drop-arrow_{b}" for b in C.ARROW_BOARDS] + ["drop-pin_7", "drop-pin_10"]
    ds = {s: C.load(C.RESULTS / f"e3_fit_{tag}__{s}.json")["variants"] for s in C.STEMS if C.has_result(C.RESULTS / f"e3_fit_{tag}__{s}.json")}
    for n in names:
        cells = []
        for s in C.STEMS:
            v = ds.get(s, {}).get(n)
            cells.append(f"{fmt(v['summary']['throw_median_pins'])} / {fmt(v['summary']['tail_median_pins'])}" if v else "-")
        out.append(f"| {n} | " + " | ".join(cells) + " |")
    return "\n".join(out)


def e4_table():
    out = ["| video | landmarks per frame (median) | frames with a landmark fit | corner error vs hand per-frame corners: landmarks / ORB (px mean, throw) | top corners: landmarks / ORB | max: landmarks / ORB | vs ORB (px mean, no hand truth) |", "|---|---|---|---|---|---|---|"]
    for stem in C.STEMS:
        p = C.RESULTS / f"e4_camera_loop3__{stem}.json"
        if not p.exists():
            continue
        s = C.load(p)["summary"]
        if "err_landmarks_px_mean" in s:
            out.append(f"| {C.SHORT[stem]} | {s['landmarks_per_frame_median']} | {s['frames_with_landmark_fit']}/{s['frames']} | {s['err_landmarks_px_throw_mean']} / {s['err_orb_px_throw_mean']} | {s['err_landmarks_top_px_throw_mean']} / {s['err_orb_top_px_throw_mean']} | {s['err_landmarks_px_max']} / {s['err_orb_px_max']} | - |")
        else:
            out.append(f"| {C.SHORT[stem]} | {s['landmarks_per_frame_median']} | {s['frames_with_landmark_fit']}/{s['frames']} | - | - | - | {s['vs_orb_px_mean']} |")
    return "\n".join(out)


if __name__ == "__main__":
    parts = ["## E1 truth\n", (C.RESULTS / "e1_summary.md").read_text(), "\n## Baselines re-scored\n", (C.RESULTS / "baselines_rescored.md").read_text(), "\n## E2 detectors\n", e2_table()]
    for tag in ("loop3", "loop3_plus", "loop3_1024", "seg2_1024", "sam_even3_k", "sam_zoom_lo_k"):
        if any(C.has_result(C.RESULTS / f"e3_fit_{tag}__{s}.json") for s in C.STEMS):
            parts += [f"\n## E3 fits: {tag}\n", e3_table(tag), "\n", e3_drop_table(tag)]
    parts += ["\n## E4 camera\n", e4_table()]
    (C.RESULTS / "tables.md").write_text("\n".join(parts) + "\n")
    print("\n".join(parts))
