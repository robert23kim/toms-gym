import glob, json, os, statistics as st, subprocess, sys
O = "/Users/toka/code/bowling-app/perf-exp-pose-parallel-out/ab"
N = "/Users/toka/code/toms_gym-perf/docs/sessions/2026-11-13-perf-loop"
data = {}
for f in sorted(glob.glob(f"{O}/*/*.timing.json")):
    arm, rep = os.path.basename(os.path.dirname(f)).rsplit("-r", 1)
    d = json.load(open(f))
    data.setdefault(d["fixture"], {}).setdefault(arm, []).append((int(rep), d["analyze_breakdown"].get("pose") or d["analyze_breakdown"].get("plank_analyze"), d["stages"]["analyze"], d["wall_s"], f))
print("fixture | arm | n | pose s per rep | pose median | analyze median | wall median | pose speedup vs off (per-rep pairs)")
for fx in sorted(data):
    off = {r: p for r, p, *_ in data[fx].get("off", [])}
    for arm in ("base", "off", "w2", "w4"):
        rows = sorted(data[fx].get(arm, []))
        if not rows: continue
        poses = [p for _r, p, *_ in rows]
        sp = [round(off[r] / p, 2) for r, p, *_ in rows if r in off and p]
        print(f"{fx} | {arm} | {len(rows)} | {poses} | {st.median(poses)} | {st.median([a for *_x, a, _w, _f in rows])} | {st.median([w for *_x, w, _f in rows])} | {sp}")
print()
print("equivalence (native): each arm's summary vs off-r1 summary of the same fixture, and off-r1 vs base-local/run1")
for fx in sorted(data):
    ref = f"{O}/off-r1/{fx}.summary.json"
    res = []
    for arm in ("base", "off", "w2", "w4"):
        for rep, *_x, f in sorted(data[fx].get(arm, [])):
            s = f.replace(".timing.json", ".summary.json")
            same = open(s, "rb").read() == open(ref, "rb").read()
            rc = subprocess.run([sys.executable, f"{N}/harness/compare.py", ref, s], capture_output=True).returncode
            res.append(f"{arm}-r{rep}:{'bytes=' if same else 'BYTES-DIFFER'}{'/cmp-ok' if rc == 0 else '/CMP-FAIL'}")
    bl = f"{N}/base-local/run1/{fx}.summary.json"
    rc = subprocess.run([sys.executable, f"{N}/harness/compare.py", bl, ref], capture_output=True).returncode
    print(fx, " ".join(res), "| off-r1 vs base-local/run1:", "bytes=" if open(bl, "rb").read() == open(ref, "rb").read() else "bytes-differ", "cmp-ok" if rc == 0 else "CMP-FAIL")
