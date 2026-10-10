"""Score every dev track with L/score_tracks.py (subprocess, the official way) and print the dev table + mean."""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
L = HERE.parents[1]
PY = "/Users/toka/code/bowling-app/analysis-engine/.venv/bin/python"
DEV = ["20260915_185121_23d80f05", "20260915_185331_19de9ec7", "20260915_185645_9fde3c16", "20260915_185454_f240c883", "20260915_190115_a7cf2c70"]

rows = []
for stem in DEV:
    tp = HERE / "tracks" / f"{stem}.json"
    if not tp.exists():
        rows.append({"stem": stem, "missing": True})
        continue
    out = subprocess.run([PY, str(L / "score_tracks.py"), str(tp), str(L / "truth" / f"{stem}.json")], capture_output=True, text=True)
    sc = json.loads(out.stdout)
    tr = json.load(open(tp))
    sc["wall_s"] = tr.get("wall_s")
    sc["from_cache"] = tr.get("from_cache")
    sc["lane_method"] = tr.get("lane_method")
    rows.append(sc)
print("| stem | recall % | median px | board_err | lane_err | window_err | pass | lane | wall s |")
print("|---|---|---|---|---|---|---|---|---|")
for r in rows:
    if r.get("missing"):
        print(f"| {r['stem'][9:15]} | - | - | - | - | - | - | - | - |")
        continue
    print(f"| {r['stem'][9:15]} | {r['recall_pct']} | {r['median_px_err']} | {r['board_err']} | {r['lane_err_boards']} | {r['window_err']} | {r['pass']} | {r['lane_method']} | {r['wall_s']}{' (cache)' if r['from_cache'] else ''} |")
ok = [r for r in rows if not r.get("missing")]
rec = [r["recall_pct"] for r in ok]
be = [r["board_err"] for r in ok if r["board_err"] is not None]
print(f"\nmean recall {sum(rec)/len(rec):.1f} over {len(rec)}; mean board_err {sum(be)/len(be) if be else None} over {len(be)}; pass {sum(1 for r in ok if r['pass'])}/{len(ok)}")
json.dump(rows, open(HERE / "work" / "dev_scores.json", "w"), indent=1)
