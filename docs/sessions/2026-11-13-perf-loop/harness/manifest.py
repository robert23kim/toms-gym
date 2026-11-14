#!/usr/bin/env python3
"""Print the fixtures.md manifest table from fixtures, prod timings and base runs."""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import compare as C
FX = os.environ.get("FIXTURES", "/Users/toka/code/bowling-app/perf-fixtures-2026-11-13")
P = os.path.dirname(HERE)
prod = json.load(open(f"{FX}/prod_timings.json"))

def probe(path):
    o = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,r_frame_rate,nb_frames:stream_side_data=rotation:format=duration",
                        "-of", "json", path], capture_output=True, text=True).stdout
    d = json.loads(o); s = d["streams"][0]
    rot = next((sd.get("rotation") for sd in s.get("side_data_list", []) if "rotation" in sd), 0)
    return s["nb_frames"], s["r_frame_rate"].split("/")[0], f'{s["width"]}x{s["height"]}', round(float(d["format"]["duration"]), 1), rot

def t(path):
    try: return json.load(open(path))
    except Exception: return None

def verdict(a, b):
    if not os.path.exists(b): return "n/a"
    d = C.compare(C.load(a), C.load(b))
    return "MATCH" if not d else "DIFF(" + ",".join(sorted({g for g, _ in d})) + ")"

def board(r):
    if "total_in_plank_s" in r: return f'hold {r["total_in_plank_s"]:.1f}s'
    clean = sum(1 for m in r.get("rep_metrics", []) if (m.get("form_score") or 0) >= 70)
    return f'{r.get("total_reps")} reps / {clean} clean'

rows = []
print("| fixture | lift | frames | fps | res | rot | dur s | prod result | prod analyze / clips / reencode / engine / total s | laptop-native wall (analyze) s, run1/run2 | prod-image wall s | native vs prod | prod-image vs prod |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for name in sorted(prod):
    v = prod[name]
    vid = next(f for f in os.listdir(FX) if f.startswith(name + ".") and f.split(".")[-1] in ("mp4", "mov"))
    fr, fps, res, dur, rot = probe(f"{FX}/{vid}")
    pj = f"{FX}/{name}.prod.json"
    r1, r2 = t(f"{P}/base-local/run1/{name}.timing.json"), t(f"{P}/base-local/run2/{name}.timing.json")
    im = t(f"{P}/base-image/{name}.timing.json")
    nat = " / ".join(f'{x["wall_s"]} ({x["stages"]["analyze"]})' for x in (r1, r2) if x)
    print(f'| {vid} | {v["lift_type"]} | {fr} | {fps} | {res} | {rot} | {dur} | {board(C.load(pj))} | '
          f'{v["engine_analyze_s"]} / {v["engine_clips_s"]} / {v["engine_reencode_s"]} / {v["engine_s"]} / {v["total_s"]} | '
          f'{nat} | {im["wall_s"] if im else "n/a"} | {verdict(pj, f"{P}/base-local/run1/{name}.summary.json")} | '
          f'{verdict(pj, f"{P}/base-image/{name}.summary.json")} |')
