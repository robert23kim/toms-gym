"""Join Cloud Run bench outputs: per result -> instance, host class (which base ref it matches), analyze_s, pose stats."""
import glob, json, os, re, subprocess, sys
N = "/Users/toka/code/toms_gym-perf/docs/sessions/2026-11-13-perf-loop"
O = "/Users/toka/code/bowling-app/perf-exp-pose-parallel-out/cloudrun"
FX = "/Users/toka/code/bowling-app/perf-fixtures-2026-11-13"
CMP = f"{N}/harness/compare.py"

def match(ref, cand):
    return subprocess.run([sys.executable, CMP, ref, cand], capture_output=True, text=True).returncode == 0

# base: attempt -> instance, and class by instance id suffix (baseline.md: A = ...eed6b1222b98, B = ...bb285fb747c2)
base_inst = {}
for l in open(f"{N}/cloudrun-base/instances.tsv"):
    p = l.split()
    if len(p) >= 3:
        base_inst[p[2]] = "A" if p[1].endswith("eed6b1222b98") else ("B" if p[1].endswith("bb285fb747c2") else "?")
base = {}  # fixture -> class -> list of (analyze_s, path)
for f in sorted(glob.glob(f"{N}/cloudrun-base/*.r?.json")):
    name, r = os.path.basename(f)[:-5].rsplit(".", 1)
    d = json.load(open(f))
    cls = base_inst.get(f"perf-bench-{name}-{r}") or base_inst.get(f"perf-bench-{name}-perf-base-{r}") or "?"
    base.setdefault(name, {}).setdefault(cls, []).append((d["stages"]["analyze"], f))

for f in sorted(glob.glob(f"{N}/base-image/*.summary.json")):
    base.setdefault(os.path.basename(f)[:-13], {})["img"] = [(None, f)]

# pose stat lines per instance
lines = []
for l in open(f"{O}/pose-log-lines.txt"):
    p = l.rstrip("\n").split("\t")
    if len(p) >= 4:
        lines.append((p[0], p[1].replace("bowling-service-perf-", ""), p[2][-6:], p[3]))
lines.sort()
pose_by_attempt = {}
pending = {}
for ts, rev, inst, text in lines:
    if "LIFT_POSE_PARALLEL" in text:
        pending[inst] = dict(kv.split("=", 1) for kv in text.split("LIFT_POSE_PARALLEL ")[1].split(" "))
    elif "ANALYSIS_STAGES" in text:
        m = re.search(r"attempt=(\S+)", text)
        pose_by_attempt[m.group(1)] = (inst, pending.pop(inst, None))

rows = []
for tagdir in sorted(glob.glob(f"{O}/*/")):
    tag = os.path.basename(tagdir.rstrip("/"))
    for f in sorted(glob.glob(f"{tagdir}*.r?.json")):
        name, r = os.path.basename(f)[:-5].rsplit(".", 1)
        try:
            d = json.load(open(f))
            an = d["stages"]["analyze"]
        except Exception as e:
            rows.append({"tag": tag, "fixture": name, "run": r, "error": repr(e)[:80]})
            continue
        rev = {"off": "pp-off", "f4": "pp-f4"}.get(tag, "pp-" + tag)
        inst, pose = pose_by_attempt.get(f"perf-bench-{name}-{rev}-{r}", (None, None))
        classes = [c for c in sorted(base.get(name, {})) if any(match(p, f) for _a, p in base[name][c])]
        rows.append({"tag": tag, "fixture": name, "run": r, "inst": inst, "matches_base_class": classes,
                     "matches_prod": match(f"{FX}/{name}.prod.json", f), "analyze_s": an,
                     "base_analyze_by_class": {c: [a for a, _ in v] for c, v in base.get(name, {}).items() if c != "img"},
                     "reps": (d.get("report") or {}).get("total_reps"),
                     "pose_parallel_s": pose and float(pose["parallel_s"]), "splice_s": pose and float(pose["splice_s"]),
                     "sync_offsets": pose and pose["sync_offsets"], "extended": pose and pose["extended_frames"],
                     "workers": pose and pose["workers"]})
json.dump(rows, open(f"{O}/joined.json", "w"), indent=1)
for r in rows:
    if "error" in r:
        print(r); continue
    print(f"{r['tag']:4} {r['fixture']:16} {r['run']} inst={r['inst']} class={'+'.join(r['matches_base_class']) or 'NONE':7} prod={'Y' if r['matches_prod'] else 'n'} "
          f"analyze={r['analyze_s']:7} base={r['base_analyze_by_class']} pose={r['pose_parallel_s']}+{r['splice_s']} sync={r['sync_offsets']} ext={r['extended']} reps={r['reps']}")
