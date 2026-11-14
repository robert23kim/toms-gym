#!/usr/bin/env python3
"""classify_cloudrun.py <bench-outdir> [...]

For every <fixture>.r<k>.json in the bench dirs: compare.py against the class-A and
class-B references from the base run (baseline.md), print which host class the
response matches, its instance id and its stage seconds. A response matching
neither class is a FAIL: the candidate changed the result.
"""
import csv
import glob
import json
import os
import subprocess
import sys

N = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
BASE = os.path.join(N, "cloudrun-base")
CMP = os.path.join(N, "harness", "compare.py")
REF = {
    "A": {"pushup_3c66c85e": "pushup_3c66c85e.r1.json", "pushup_e18a31d1": "pushup_e18a31d1.r1.json",
          "situp_16b6ca35": "situp_16b6ca35.r1.json", "situp_667a8480": "situp_667a8480.r1.json",
          "situp_c9dec98b": "situp_c9dec98b.r1.json", "plank_9600f455": "plank_9600f455.r2.json",
          "squat_f47a8848": "squat_f47a8848.r2.json",
          "pushup_97b4aaf2": os.path.join(N, "base-image", "pushup_97b4aaf2.summary.json")},
    "B": {"squat_f47a8848": "squat_f47a8848.r2.json", "pushup_3c66c85e": "pushup_3c66c85e.r2.json",
          "pushup_97b4aaf2": "pushup_97b4aaf2.r2.json", "pushup_e18a31d1": "pushup_e18a31d1.r2.json",
          "situp_16b6ca35": "situp_16b6ca35.r2.json", "situp_667a8480": "situp_667a8480.r2.json",
          "situp_c9dec98b": "situp_c9dec98b.r2.json", "plank_9600f455": "plank_9600f455.r1.json"},
}


def matches(ref, cand):
    return subprocess.run([sys.executable, CMP, os.path.join(BASE, ref), cand],
                          capture_output=True, text=True).returncode == 0


def main():
    rows, bad = [], 0
    for d in sys.argv[1:]:
        inst = {}
        p = os.path.join(d, "instances.tsv")
        if os.path.isfile(p):
            for r in csv.reader(open(p), delimiter="\t"):
                if len(r) >= 3:
                    inst[r[2]] = r[1][-6:]
        for f in sorted(glob.glob(os.path.join(d, "*.r[0-9].json"))):
            name, k = os.path.basename(f)[:-5].rsplit(".r", 1)
            resp = json.load(open(f))
            cls = [c for c in ("A", "B") if matches(REF[c][name], f)]
            if not cls:
                bad += 1
            s = resp.get("stages", {})
            iid = next((v for a, v in inst.items()
                        if a.startswith(f"perf-bench-{name}-") and a.endswith(f"-r{k}")), "?")
            rows.append([os.path.basename(d.rstrip("/")), name, k, "+".join(cls) or "NEITHER", iid,
                         s.get("analyze"), s.get("reencode"), s.get("clips"), s.get("upload"),
                         resp.get("processing_time_s")])
    print("\t".join(["run", "fixture", "k", "class", "instance", "analyze", "reencode", "clips", "upload", "total"]))
    for r in rows:
        print("\t".join(str(x) for x in r))
    print(f"responses={len(rows)} matching_neither_class={bad}")
    sys.exit(1 if bad or not rows else 0)


if __name__ == "__main__":
    main()
