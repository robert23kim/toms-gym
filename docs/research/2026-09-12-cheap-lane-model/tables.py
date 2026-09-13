"""README tables from results/*.json -> results/summary.md (and stdout).
usage: tables.py [prefixes...]  e.g. tables.py seg640 pose640 seg640_plus
A prefix P is scored on stem s through results/P_lovo_<s>[suffix]__<s>.json, where a
prefix like seg640_plus maps to run seg640_lovo_<s>_plus.
"""
import json
import sys
from pathlib import Path

import common as C


def load(p):
    return json.loads(Path(p).read_text()) if Path(p).exists() else None


def run_name(prefix, fold):
    """prefix 'seg640' -> seg640_<fold>; 'seg640|_plus_gated' -> seg640_<fold>_plus_gated
    (the suffix after '|' is appended after the fold: training variant then post-processing)."""
    base, _, suffix = prefix.partition("|")
    return f"{base}_{fold}{suffix}"


def f(v, nd=2):
    return "-" if v is None else (f"{v:.{nd}f}" if isinstance(v, (int, float)) else str(v))


def student_rows(prefix):
    out = []
    for s in C.STEMS:
        r = load(C.RESULTS / f"{run_name(prefix, 'lovo_' + s)}__{s}.json")
        if not r:
            out.append([C.SHORT[s], prefix, "-", "-", "-", "-", "-", "-", "-"])
            continue
        out.append([C.SHORT[s], prefix, f(r["last"]["board_mae"]), f(r["prehit"]["board_mae"]),
                    f"{f(r['clean']['mean'])} / {f(r['clean']['median'])}", f"{f(r['occluded']['mean'])} / {f(r['occluded']['median'])}",
                    f"{f(r['throw']['within_2'], 0)} %", f"{r['frames_ok']}/{r['frames_total']}", f"{f(r['latency_ms_median'], 0)} ms"])
    return out


def sam_rows():
    l1 = {r["stem"]: r for r in load(C.LOOP1 / "results" / "even3_last.json") or []}
    l1t = {r["stem"]: r for r in load(C.LOOP1 / "results" / "track_last_tiny.json") or []}
    vr = {r["stem"]: r for r in load(C.LOOP1 / "results" / "video_rev.json") or []}
    cy = {r["stem"]: r for r in load(C.LOOP2 / "results" / "video_carry_track.json") or []}
    e3 = {r["stem"]: r for r in load(C.LOOP2 / "results" / "even3_prehit_k.json") or []}
    out = []
    for s in C.STEMS:
        a, t, b, c, e = l1.get(s), l1t.get(s), vr.get(s), cy.get(s), e3.get(s)
        out.append([C.SHORT[s], "SAM 2 base, even3 prompts (loops 1-2)", f(a and a["board_mae"]), f(e and e["board_mae"]), "-", "no lane", "-", "1 frame", f"{f(a and a['latency_s'] * 1000, 0)} ms"])
        out.append([C.SHORT[s], "SAM 2 tiny, path prompts (loop 1)", f(t and t["board_mae"]), "-", "-", "no lane", "-", "1 frame", f"{f(t and t['latency_s'] * 1000, 0)} ms"])
        out.append([C.SHORT[s], "SAM 2 video mode, per frame (loop 1)", f(b and b["board_mae"]), "-", f"{f(b and b['perframe_mae_mean'])} / {f(b and b['perframe_mae_median'])} *", "-", f"{f(b and b['perframe_within_2'], 0)} %", f"{b and b['frames_ok']}/{b and b['frames_total']}", f"{f(b and b['latency_s'] * 1000 / max(1, b['frames_total']), 0)} ms"])
        out.append([C.SHORT[s], "SAM 2 gate + carry (loop 2)", f(c and c["board_mae"]), "-", f"{f(c and c['perframe_mae_mean'])} / {f(c and c['perframe_mae_median'])} *", "carried", f"{f(c and c['perframe_within_2'], 0)} %", f"{c and c['frames_ok']}/{c and c['frames_total']}", "-"])
    return out


def hybrid_rows(prefix):
    out = []
    for s in C.STEMS:
        r = load(C.RESULTS / f"hybrid_{run_name(prefix, 'lovo_' + s)}__{s}.json")
        if not r:
            continue
        one = {x["kind"]: x for x in r if x["kind"] != "clean_all"}
        cl = [x["board_mae"] for x in r if x["kind"] == "clean_all" and x.get("ok")]
        import numpy as np
        out.append([C.SHORT[s], f"hybrid: {prefix} prompts -> SAM 2 tiny", f(one.get("last", {}).get("board_mae")), f(one.get("prehit", {}).get("board_mae")),
                    f"{f(float(np.mean(cl)))} / {f(float(np.median(cl)))}" if cl else "-", "no lane", "-", f"{len(cl)} clean", "~600 ms"])
    return out


def md_table(header, rows):
    s = "| " + " | ".join(header) + " |\n|" + "---|" * len(header) + "\n"
    for r in rows:
        s += "| " + " | ".join(str(x) for x in r) + " |\n"
    return s


def main(prefixes):
    header = ["video", "method", "last", "pre-hit", "clean mean / med", "occluded mean / med", "<=2 boards (throw)", "frames with a lane", "per frame"]
    rows = []
    for s in C.STEMS:
        for p in prefixes:
            rows += [r for r in student_rows(p) if r[0] == C.SHORT[s]]
            rows += [r for r in hybrid_rows(p) if r[0] == C.SHORT[s]]
        rows += [r for r in sam_rows() if r[0] == C.SHORT[s]]
    md = md_table(header, rows)
    md += "\n\\* SAM per-frame means are over the throw frames the method scored (loop 1 video mode: whole throw incl. occluded frames; loop 2 gate+carry: accepted frames only).\n"
    # unlabeled
    vt = []
    for p in prefixes:
        for stem in C.UNLABELED:
            r = load(C.RESULTS / f"{run_name(p, 'all3')}__{stem}__vs_teacher.json")
            if r:
                vt.append([stem, run_name(p, "all3"), f"{f(r['vs_teacher_reliable']['mean'])} / {f(r['vs_teacher_reliable']['median'])}", f"{r['vs_teacher_reliable']['ok']}/{r['vs_teacher_reliable']['n']}", f(r["corner_px_reliable"], 1), f"{f(r['vs_teacher_in_throw']['mean'])} / {f(r['vs_teacher_in_throw']['median'])}"])
    if vt:
        md += "\n**Unlabeled videos, student vs SAM 2 teacher (teacher corners as truth, detected ball path as the points)**\n\n"
        md += md_table(["video", "student", "boards mean / med (teacher reliable)", "frames", "corner px", "boards in throw (teacher occluded)"], vt)
    (C.RESULTS / "summary.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main(sys.argv[1:] or ["seg640", "pose640"])
