"""Loop 2's SAM lanes (single frames, corners stored) as an E2/E3 lane source:
results/lanes_sam_<method>__<stem>.json with per_frame[].corners for the pre-hit
and last frames. usage: sam_lanes.py [even3_k|zoom_lo_k]"""
import sys
import common as C
meth = sys.argv[1] if len(sys.argv) > 1 else "even3_k"
base = meth[:-2] if meth.endswith("_k") else meth
suffix = "_k" if meth.endswith("_k") else ""
for stem in C.STEMS:
    rows = []
    for kind in ("prehit", "last"):
        for r in C.load(C.LOOP2 / "results" / f"{base}_{kind}{suffix}.json"):
            if r["stem"] == stem and r.get("ok") and "corners" in r:
                rows.append({"frame": r["frame"], "kind": kind, "corners": r["corners"], "stored_mae": r.get("board_mae")})
    C.dump(C.RESULTS / f"lanes_sam_{meth}__{stem}.json", {"stem": stem, "method": meth, "per_frame": rows})
    print(stem, [(r["frame"], r["kind"], r["stored_mae"]) for r in rows])
