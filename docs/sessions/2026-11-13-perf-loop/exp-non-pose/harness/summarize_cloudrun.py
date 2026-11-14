#!/usr/bin/env python3
"""summarize_cloudrun.py <classify.tsv> : per fixture and host class, mean seconds for
base (cloudrun-base), off (np-off-*) and on (np-on-*) runs, from classify_cloudrun.py output.

Squat matches both class references, so its class comes from the instance that served it
(the class the same instance showed on other fixtures); unknown stays "A+B".
"""
import collections
import csv
import sys


def arm(run):
    return "base" if run == "cloudrun-base" else ("off" if run.startswith("np-off") else "on")


def main():
    rows = [r for r in csv.DictReader(open(sys.argv[1]), delimiter="\t") if r.get("fixture")]
    inst_class = {}
    for r in rows:
        if r["class"] in ("A", "B") and r["instance"] != "?":
            inst_class.setdefault(r["instance"], set()).add(r["class"])
    mixed = {i: c for i, c in inst_class.items() if len(c) > 1}
    for r in rows:
        if r["class"] == "A+B" and len(inst_class.get(r["instance"], ())) == 1:
            r["class"] = next(iter(inst_class[r["instance"]]))
    groups = collections.defaultdict(list)
    for r in rows:
        groups[(r["fixture"], r["class"], arm(r["run"]))].append(r)

    def cell(fixture, cls, a):
        g = groups.get((fixture, cls, a))
        if not g:
            return None, "-"
        tot = [float(r["total"]) for r in g]
        mean = sum(tot) / len(tot)
        parts = "/".join(f"{sum(float(r[k]) for r in g) / len(g):.1f}" for k in ("analyze", "reencode", "clips", "upload"))
        return mean, f"{mean:.1f} (n={len(g)}; {min(tot):.1f}-{max(tot):.1f}; {parts})"

    print("| fixture | host class | base total s (n; min-max; analyze/reencode/clips/upload) | flags off | flags on | on vs base | on vs off |")
    print("|---|---|---|---|---|---|---|")
    for fixture in sorted({r["fixture"] for r in rows}):
        for cls in sorted({r["class"] for r in rows if r["fixture"] == fixture}):
            b, bs = cell(fixture, cls, "base")
            o, os_ = cell(fixture, cls, "off")
            n, ns = cell(fixture, cls, "on")
            vb = f"{b / n:.2f}x ({100 * (n - b) / b:+.0f}%)" if b and n else "-"
            vo = f"{o / n:.2f}x ({100 * (n - o) / o:+.0f}%)" if o and n else "-"
            print(f"| {fixture} | {cls} | {bs} | {os_} | {ns} | {vb} | {vo} |")
    print()
    print("instances and the class each showed:", {i: "".join(sorted(c)) for i, c in sorted(inst_class.items())})
    if mixed:
        print("WARNING: instance showed both classes:", mixed)
    print("upload stalls (>5 s):", [(r["run"], r["fixture"], r["k"], r["upload"]) for r in rows if float(r["upload"]) > 5])


if __name__ == "__main__":
    main()
