"""Print the baseline.md tables from cloudrun-base/, profile-cloudrun/, profile/ and prod_timings.json."""
import csv, json, os, re, statistics, sys
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
FX = "/Users/toka/code/bowling-app/perf-fixtures-2026-11-13"
prod = json.load(open(os.path.join(FX, "prod_timings.json")))
rows = list(csv.DictReader(open(os.path.join(D, "cloudrun-base/bench.tsv")), delimiter="\t"))
by = {}
for r in rows: by.setdefault(r["fixture"], {})[r["run"]] = r
cmp = open(os.path.join(D, "cloudrun-base/compare.txt")).read().split("== ")[1:]
verdict = {}
for blk in cmp:
    head = blk.splitlines()[0]; ok = "exit=0" in blk
    verdict[head] = "MATCH" if ok else "DIFF(" + ",".join(sorted(set(re.findall(r"FAIL \[(\w+)\]", blk)))) + ")"
print("| fixture | prod analyze / clips / total s | r1 analyze / clips / reencode / total s | r2 analyze / clips / reencode / total s | spread analyze | r1 vs prod | r2 vs prod | r1 vs base-image |")
print("|---|---|---|---|---|---|---|---|")
for f, rr in by.items():
    p = prod[f]; cells = []
    for k in ("1", "2"):
        r = rr.get(k); cells.append(f"{r['analyze_s']} / {r['clips_s']} / {r['reencode_s']} / {r['processing_time_s']}" if r else "-")
    a = [float(rr[k]["analyze_s"]) for k in rr if rr[k]["analyze_s"]]
    spread = f"{(max(a)-min(a))/statistics.mean(a)*100:.1f}%" if len(a) > 1 else "-"
    print(f"| {f} | {p['engine_analyze_s']} / {p['engine_clips_s']} / {p['engine_reported_s']} | {cells[0]} | {cells[1]} | {spread} | "
          f"{verdict.get(f+' r1 vs prod','-')} | {verdict.get(f+' r2 vs prod','-')} | {verdict.get(f+' r1 vs base-image','-')} | {verdict.get(f+' r2 vs base-image','-')} |")
print()
KEYS = [("model_init", ["model_init"]), ("decode (pose pass)", ["decode[pose]"]), ("pose inference", ["pose_inference"]),
        ("rgb convert + skeleton build", None), ("track + smooth", ["track_person", "clean_pose_track"]),
        ("rep detect + score + alerts", ["rep_detect_score", "alerts", "camera_view", "active_arm"]),
        ("render video (decode/draw+overlay/encode)", None), ("render clips (decode/draw/encode)", None)]
for src, label in (("profile-cloudrun", "Cloud Run (perf-prof tag, 8 vCPU gVisor, prod deps)"), ("profile", "laptop native arm64 (secondary)")):
    print(f"#### {label}\n")
    print("| fixture | frames | res | analyze s | model init | decode | pose inference | ms/frame inf | poses/frame | rgb+build | track+smooth | rep+score | render video (dec/enc) | render clips (dec/enc) | clips written |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for fn in sorted(os.listdir(os.path.join(D, src))):
        p = os.path.join(D, src, fn)
        if not fn.endswith(".json") or "numposes" in fn: continue
        d = json.load(open(p)); d = d.get("result", d) if "result" in d else d
        if not d or "stages" not in d: continue
        s = d["stages"]; c = d["counts"]; g = lambda k: s.get(k, 0.0); m = d["meta"]
        if "plank_analyze_total" in s:
            print(f"| {d['fixture']} ({fn}) | {m['frames']} | {m['w']}x{m['h']} | {d['analyze_total_s']} | in workers | in workers | parallel pose total {g('plank_pose_parallel_total')} | - | - | - | - | rest {round(g('plank_analyze_total')-g('plank_pose_parallel_total')-g('plank_render_total'),2)} | {g('plank_render_total')} (enc {g('encode_write[plank_render]')}) | - | 0 |")
            continue
        inf = g("pose_inference"); n = c.get("pose_inference", 1)
        print(f"| {d['fixture']} | {m['frames']} | {m['w']}x{m['h']} | {d['analyze_total_s']} | {g('model_init')} | {g('decode[pose]')} | {inf} | {1000*inf/n:.0f} | {c.get('poses_returned',0)/n:.2f} | "
              f"{round(g('pose_pass_total')-inf-g('decode[pose]'),2)} | {round(g('track_person')+g('clean_pose_track'),2)} | {round(g('rep_detect_score')+g('alerts'),2)} | "
              f"{g('render_video_total')} ({g('decode[render_video]')}/{g('encode_write[render_video]')}) | {g('render_clips_total')} ({g('decode[render_clips]')}/{g('encode_write[render_clips]')}) | {d['clips_written']} |")
    print()
