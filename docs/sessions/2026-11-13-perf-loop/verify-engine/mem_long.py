#!/usr/bin/env python3
"""mem_long.py <video> <workers> - peak RSS (parent + all child processes, sampled every 0.2 s)
of PoseEstimator.estimate_video_candidates with LIFT_POSE_WORKERS=<workers>. Laptop-native,
so it measures how memory scales with clip length, not the Cloud Run number."""
import os, sys, threading, time
import psutil
os.environ["LIFT_POSE_WORKERS"] = sys.argv[2]
from src.lifting.pose.estimator import PoseEstimator
me = psutil.Process()
peak = {"tree": 0, "parent": 0, "children": 0}
stop = False
def sample():
    while not stop:
        try:
            kids = me.children(recursive=True)
            p = me.memory_info().rss
            c = sum(k.memory_info().rss for k in kids if k.is_running())
            peak["parent"] = max(peak["parent"], p); peak["children"] = max(peak["children"], c)
            peak["tree"] = max(peak["tree"], p + c); peak["nkids"] = max(peak.get("nkids", 0), len(kids))
        except psutil.Error:
            pass
        time.sleep(0.2)
if __name__ == "__main__":
    t = threading.Thread(target=sample, daemon=True); t.start()
    t0 = time.time()
    cands, fps = PoseEstimator().estimate_video_candidates(sys.argv[1])
    dt = time.time() - t0
    stop = True; t.join()
    from src.lifting.pose import parallel
    print({k: (round(v / 2**30, 2) if k != "nkids" else v) for k, v in peak.items()}, "GiB",
          "frames", len(cands), "poses", sum(len(c) for c in cands), "wall_s", round(dt, 1),
          "stats", {k: parallel.LAST_STATS.get(k) for k in ("sync_offsets", "extended_frames")} if parallel.LAST_STATS else None)
