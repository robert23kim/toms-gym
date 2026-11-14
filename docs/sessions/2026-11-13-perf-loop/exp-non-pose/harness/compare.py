#!/usr/bin/env python3
"""Compare two lift result JSONs (prod GET /lifting/result body, or a bare
summary from run_local). Exit 0 if equivalent, 1 with a readable diff if not.

Gates (strict by default; all are what the leaderboard or the result page read):
  reps            total_reps and len(rep_metrics) identical
  clean_split     per-rep form_score >= 70 (CLEAN_REP_MIN_FORM) identical
  grade           per-rep form_grade, overall_grade identical
  view            camera_view, active_arm identical
  score_drift     per-rep form_score, overall_score, per-metric value drift < 2 points
  metric_status   per-metric pass/warn/fail identical
  rep_timing      per-rep start_s/end_s within 0.25 s
  plank_hold      total_in_plank_s, longest_run_s within 0.5 s
  plank_type      plank_type identical
  plank_score     overall_form_score (0..1) drift < 0.02, body_line_* drift < 2 deg
--tolerate a,b  downgrades the named gates to warnings (never reps/clean_split/plank_hold
                unless --i-know is also given).
"""
import argparse
import json
import math
import sys

CLEAN = 70.0
HARD = {"reps", "clean_split", "plank_hold"}


def load(path):
    with open(path) as f:
        d = json.load(f)
    return d["report"] if isinstance(d, dict) and "report" in d and isinstance(d["report"], dict) else d


def num(v):
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) or math.isinf(f) else f


def align(ra, rb, add):
    """Pair reps by time overlap so one extra or missing rep is reported once
    instead of shifting every later rep (equal counts can still hide one)."""

    def span(r):
        return num(r.get("start_s")) or 0.0, num(r.get("end_s")) or 0.0

    pairs, j = [], 0
    for i, x in enumerate(ra, 1):
        xs, xe = span(x)
        best, best_ov = None, 0.0
        for k in range(j, len(rb)):
            ys, ye = span(rb[k])
            if ys > xe:
                break
            ov = min(xe, ye) - max(xs, ys)
            if ov > best_ov:
                best, best_ov = k, ov
        if best is None:
            add("reps", f"rep {i} ({xs}-{xe}s) only in A")
            continue
        for k in range(j, best):
            add("reps", f"rep B#{k + 1} ({span(rb[k])[0]}-{span(rb[k])[1]}s) only in B")
        pairs.append((i, x, rb[best]))
        j = best + 1
    for k in range(j, len(rb)):
        add("reps", f"rep B#{k + 1} ({span(rb[k])[0]}-{span(rb[k])[1]}s) only in B")
    return pairs


def compare(a, b):
    out = []  # (gate, message)

    def add(gate, msg):
        out.append((gate, msg))

    def near(gate, label, x, y, tol):
        x, y = num(x), num(y)
        if x is None and y is None:
            return
        if x is None or y is None or abs(x - y) >= tol:
            add(gate, f"{label}: {x} vs {y} (tol {tol})")

    is_plank = "total_in_plank_s" in a or "total_in_plank_s" in b
    if is_plank:
        near("plank_hold", "total_in_plank_s", a.get("total_in_plank_s"), b.get("total_in_plank_s"), 0.5)
        near("plank_hold", "longest_run_s", a.get("longest_run_s"), b.get("longest_run_s"), 0.5)
        if a.get("plank_type") != b.get("plank_type"):
            add("plank_type", f"plank_type: {a.get('plank_type')} vs {b.get('plank_type')}")
        near("plank_score", "overall_form_score", a.get("overall_form_score"), b.get("overall_form_score"), 0.02)
        near("plank_score", "body_line_median_deg", a.get("body_line_median_deg"), b.get("body_line_median_deg"), 2.0)
        near("plank_score", "body_line_stdev_deg", a.get("body_line_stdev_deg"), b.get("body_line_stdev_deg"), 2.0)
        return out

    ra, rb = a.get("rep_metrics") or [], b.get("rep_metrics") or []
    if a.get("total_reps") != b.get("total_reps") or len(ra) != len(rb):
        add("reps", f"total_reps: {a.get('total_reps')} vs {b.get('total_reps')} "
                    f"(rep_metrics {len(ra)} vs {len(rb)})")
    for k in ("camera_view", "active_arm"):
        if a.get(k) != b.get(k):
            add("view", f"{k}: {a.get(k)} vs {b.get(k)}")
    if a.get("overall_grade") != b.get("overall_grade"):
        add("grade", f"overall_grade: {a.get('overall_grade')} vs {b.get('overall_grade')}")
    near("score_drift", "overall_score", a.get("overall_score"), b.get("overall_score"), 2.0)

    for i, x, y in align(ra, rb, add):
        fx, fy = num(x.get("form_score")), num(y.get("form_score"))
        if (fx is not None and fx >= CLEAN) != (fy is not None and fy >= CLEAN):
            add("clean_split", f"rep {i}: form_score {fx} vs {fy} crosses {CLEAN}")
        near("score_drift", f"rep {i} form_score", fx, fy, 2.0)
        if x.get("form_grade") != y.get("form_grade"):
            add("grade", f"rep {i} form_grade: {x.get('form_grade')} vs {y.get('form_grade')}")
        near("rep_timing", f"rep {i} start_s", x.get("start_s"), y.get("start_s"), 0.25)
        near("rep_timing", f"rep {i} end_s", x.get("end_s"), y.get("end_s"), 0.25)
        mx = {m.get("key"): m for m in x.get("metrics") or []}
        my = {m.get("key"): m for m in y.get("metrics") or []}
        if set(mx) != set(my):
            add("metric_status", f"rep {i} metric keys: {sorted(mx)} vs {sorted(my)}")
        for k in sorted(set(mx) & set(my)):
            if mx[k].get("status") != my[k].get("status"):
                add("metric_status", f"rep {i} {k} status: {mx[k].get('status')} vs {my[k].get('status')}")
            near("score_drift", f"rep {i} {k} value", mx[k].get("value"), my[k].get("value"), 2.0)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--tolerate", default="")
    ap.add_argument("--i-know", action="store_true")
    ap.add_argument("--max-lines", type=int, default=40)
    args = ap.parse_args()
    tol = {t for t in args.tolerate.split(",") if t}
    if tol & HARD and not args.i_know:
        sys.exit(f"refusing to tolerate hard gates {sorted(tol & HARD)} without --i-know")
    diffs = compare(load(args.a), load(args.b))
    fails = [d for d in diffs if d[0] not in tol]
    warns = [d for d in diffs if d[0] in tol]
    for label, rows in (("FAIL", fails), ("warn", warns)):
        for g, m in rows[: args.max_lines]:
            print(f"{label} [{g}] {m}")
        if len(rows) > args.max_lines:
            print(f"{label} ... {len(rows) - args.max_lines} more")
    gates = sorted({g for g, _ in fails})
    print(("MATCH" if not fails else "DIFF") + f" {args.a} vs {args.b}"
          + (f" failing gates: {','.join(gates)}" if gates else "")
          + (f" (tolerated: {len(warns)} warnings)" if warns else ""))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
