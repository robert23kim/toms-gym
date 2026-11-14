#!/usr/bin/env python3
"""summarize_ab.py <ab-dir> - per fixture: base vs cand seconds (engine processing_time_s and
client wall), strict compare.py of every cand run against every base run of the same fixture,
and the host class + instance of each response (classify_cloudrun.py references)."""
import csv, glob, json, os, statistics, subprocess, sys
AB = sys.argv[1]
N = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
CMP = os.path.join(N, "harness", "compare.py")
sys.path.insert(0, os.path.join(N, "exp-non-pose", "harness"))
import classify_cloudrun as K

def ok(a, b):
    return subprocess.run([sys.executable, CMP, a, b], capture_output=True, text=True).returncode == 0

def rows(tag):
    out, inst = {}, {}
    p = os.path.join(AB, tag, "instances.tsv")
    if os.path.isfile(p):
        for r in csv.reader(open(p), delimiter="\t"):
            if len(r) >= 3: inst[r[2]] = r[1][-6:]
    for r in csv.DictReader(open(os.path.join(AB, tag, "bench.tsv")), delimiter="\t"):
        f = os.path.join(AB, tag, f'{r["fixture"]}.r{r["run"]}.json')
        cls = [c for c in ("A", "B") if ok(os.path.join(K.BASE, K.REF[c][r["fixture"]]), f)]
        r["class"] = "+".join(cls) or "NEITHER"
        r["inst"] = inst.get(f'perf-bench-{r["fixture"]}-{tag}-ab-r{r["run"]}', "?")
        r["path"] = f
        out.setdefault(r["fixture"], []).append(r)
    return out

base, cand = rows("perf-base"), rows("perf-cand")
fx = list(base)
print("| fixture | base s (r1, r2) | cand s (r1, r2) | speedup (mean) | base class/inst | cand class/inst | cand vs base compare | stages cand: analyze / reencode / clips / upload |")
print("|---|---|---|---|---|---|---|---|")
tb = tc = 0.0; bad_http = 0; fails = []
for name in fx:
    b, c = base[name], cand.get(name, [])
    bad_http += sum(1 for r in b + c if r["http"] != "200")
    bs = [float(r["processing_time_s"]) for r in b if r["processing_time_s"]]
    cs = [float(r["processing_time_s"]) for r in c if r["processing_time_s"]]
    tb += statistics.mean(bs); tc += statistics.mean(cs)
    pairs = [(x, y) for x in b for y in c]
    m = sum(ok(x["path"], y["path"]) for x, y in pairs)
    if m != len(pairs): fails.append(name)
    st = "; ".join(f'{r["analyze_s"]} / {r["reencode_s"]} / {r["clips_s"]} / {r["upload_s"]}' for r in c)
    print(f'| {name} | {", ".join(f"{v:.1f}" for v in bs)} | {", ".join(f"{v:.1f}" for v in cs)} | '
          f'{statistics.mean(bs)/statistics.mean(cs):.2f}x | {", ".join(r["class"]+"/"+r["inst"] for r in b)} | '
          f'{", ".join(r["class"]+"/"+r["inst"] for r in c)} | {m}/{len(pairs)} MATCH | {st} |')
print(f"\nsum of per-fixture means: base {tb:.1f} s, cand {tc:.1f} s, {tb/tc:.2f}x, -{100*(1-tc/tb):.0f}%")
print(f"non-200 responses: {bad_http}; fixtures with any cand-vs-base DIFF: {fails or 'none'}")
