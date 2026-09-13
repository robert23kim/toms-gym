"""E6 -> E3: the constellation match run on the heatmap model's detections instead of the black-hat
pool. The class variant's arrow (and dot) peaks with conf >= 0.3 become the dark marks (strong tier);
rack blobs and LSD segments stay E2's. Held-out video of the fold only. Writes
results/e3_face_heat_<variant>_<fold>__<stem>.json. usage: e6_face.py <fold> <variant>"""
import gzip
import json
import sys

import af
import e3_face as E3
import e6_heatmap as E6

fold, variant = sys.argv[1], sys.argv[2]
held = E6.folds()[fold]["held"]
pred = json.loads((af.PRED / f"heat_{variant}_{fold}__{held}.json").read_text())["per_frame"]
with gzip.open(af.PRED / f"cand_{held}.json.gz", "rt") as fh:
    cands = json.load(fh)
out = {}
for f, c in cands.items():
    dets = pred.get(f, [])
    marks = [{"x": d["x"], "y": d["y"], "a": 9, "d": round(30 * d["conf"], 1), "w": 3, "h": 3, "weak": 0}
             for d in dets if d["conf"] >= 0.3 and (d["name"] in ("arrow", "dot", "fdot", "adot") or af.classes_of(d["name"]) in ("arrow", "dot", "fdot", "adot"))]
    out[f] = {"marks": marks, "cols": c["cols"], "racks": c["racks"], "segs": c["segs"]}
p = af.PRED / f"cand_heat_{variant}_{fold}__{held}.json.gz"
with gzip.open(p, "wt") as fh:
    json.dump(out, fh)
print("pool from the heatmap model:", held, "marks/frame", round(sum(len(v["marks"]) for v in out.values()) / max(1, len(out)), 1), flush=True)
fp = af.frame_for(held, "prehit")
E3.run(held, ["arrows+dots+rack+gutters"], overlay_frames=(fp,), tag=f"heat_{variant}_{fold}", cand_path=p)
