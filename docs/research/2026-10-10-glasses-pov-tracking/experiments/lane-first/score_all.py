"""Score every dev stem (tracks/ vs L/truth) -> results.json + a markdown table on stdout."""
import json
import os
import subprocess
import sys

L = "/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking"
E = os.path.join(L, "experiments", "lane-first")
PY = sys.executable
DEV = ["20260915_185121_23d80f05", "20260915_185331_19de9ec7", "20260915_185645_9fde3c16",
       "20260915_185454_f240c883", "20260915_190115_a7cf2c70"]
BASE = {r["stem"]: r for r in json.load(open(os.path.join(L, "results", "baseline.json")))["rows"]
        if r.get("config") == "yolo_chain_sam"} if isinstance(json.load(open(os.path.join(L, "results", "baseline.json"))), dict) else {}
rows = []
for s in DEV:
    out = subprocess.run([PY, os.path.join(L, "score_tracks.py"), os.path.join(E, "tracks", s + ".json"),
                          os.path.join(L, "truth", s + ".json")], capture_output=True, text=True)
    d = json.loads(out.stdout)
    t = json.load(open(os.path.join(E, "tracks", s + ".json")))
    d["wall_s"] = t["meta"]["wall_s"]; d["final_board"] = t["final_board"]; d["n_det"] = t["meta"]["n_det"]; d["n_fill"] = t["meta"]["n_fill"]
    d.pop("lane_err_per_frame", None)
    rows.append(d)
t191900 = json.load(open(os.path.join(E, "tracks", "20260915_191900_106ea7ca.json")))
summary = {"method": "lane-first", "rows": rows,
           "dev_mean_recall": round(sum(r["recall_pct"] for r in rows) / len(rows), 1),
           "dev_mean_board_err": round(sum(r["board_err"] for r in rows if r["board_err"] is not None) / max(1, sum(r["board_err"] is not None for r in rows)), 2),
           "dev_pass": sum(bool(r["pass"]) for r in rows),
           "no_throw_191900": {"frames": len(t191900["frames"]), "release_frame": t191900["release_frame"]}}
json.dump(summary, open(os.path.join(E, "results.json"), "w"), indent=1)
print("| stem | recall % | matched | median px | board (truth) | board_err | lane_err boards | window_err | pass | det/fill | wall s |")
print("|---|---|---|---|---|---|---|---|---|---|---|")
for r in rows:
    tb = json.load(open(os.path.join(L, "truth", r["stem"] + ".json")))["board"]
    print(f"| {r['stem'][9:15]} | {r['recall_pct']} | {r['n_matched']}/{r['n_truth_points']} | {r['median_px_err']} | {r['final_board']} ({tb}) | {r['board_err']} | {r['lane_err_boards']} | {r['window_err']} | {'pass' if r['pass'] else 'FAIL'}{' strong' if r['strong'] else ''} | {r['n_det']}/{r['n_fill']} | {r['wall_s']} |")
print(f"\nmean recall {summary['dev_mean_recall']} %, mean board_err {summary['dev_mean_board_err']}, pass {summary['dev_pass']}/5; 191900: {summary['no_throw_191900']}")
