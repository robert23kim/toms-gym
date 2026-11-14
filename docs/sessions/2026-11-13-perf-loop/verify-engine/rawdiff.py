#!/usr/bin/env python3
"""rawdiff.py A B - every leaf of the two result reports compared exactly (NaN == NaN); only the
per-metric clip_url is allowed to be missing on one side. Exit 0 = bit-identical except clip_url."""
import json, math, sys
def load(p):
    d = json.load(open(p))
    return d["report"] if isinstance(d, dict) and isinstance(d.get("report"), dict) else d
def walk(x, p, out):
    if isinstance(x, dict):
        for k, v in x.items(): walk(v, p + "." + str(k), out)
    elif isinstance(x, list):
        for i, v in enumerate(x): walk(v, p + f"[{i}]", out)
    else: out[p] = x
def same(x, y):
    if isinstance(x, float) and isinstance(y, float) and math.isnan(x) and math.isnan(y): return True
    return type(x) == type(y) and x == y
a, b = {}, {}
walk(load(sys.argv[1]), "", a); walk(load(sys.argv[2]), "", b)
diff = [(k, a[k], b[k]) for k in sorted(set(a) & set(b)) if not same(a[k], b[k])]
oa = sorted(set(a) - set(b)); ob = sorted(set(b) - set(a))
bad_only = [k for k in oa + ob if not k.endswith(".clip_url")]
print(f"leaves A={len(a)} B={len(b)} differing={len(diff)} onlyA={len(oa)} onlyB={len(ob)} only-not-clip_url={len(bad_only)}")
for r in diff[:4]: print("  diff", r)
for k in bad_only[:4]: print("  only", k)
sys.exit(1 if diff or bad_only else 0)
