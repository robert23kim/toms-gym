#!/usr/bin/env python3
"""mem_full.py <video> <lift_type> <outdir> - peak RSS of the whole process tree (parent, pose
workers, ffmpeg encoders; sampled every 0.2 s) for pipeline.analyze_lift with whatever flags are
in the environment. Laptop-native: shows how memory scales with clip length, not Cloud Run bytes."""
import os, sys, threading, time
import psutil
from src.lifting import pipeline
me = psutil.Process(); peak = {"tree": 0, "parent": 0, "kids": 0, "ffmpeg": 0}; stop = False
def sample():
    while not stop:
        try:
            kids = me.children(recursive=True); p = me.memory_info().rss; c = 0; nf = 0
            for k in kids:
                try:
                    c += k.memory_info().rss; nf += k.name().startswith("ffmpeg")
                except psutil.Error:
                    pass
            peak["parent"] = max(peak["parent"], p); peak["tree"] = max(peak["tree"], p + c)
            peak["kids"] = max(peak["kids"], len(kids)); peak["ffmpeg"] = max(peak["ffmpeg"], nf)
        except psutil.Error:
            pass
        time.sleep(0.2)
if __name__ == "__main__":
    video, lift, out = sys.argv[1:4]
    os.makedirs(out, exist_ok=True)
    t = threading.Thread(target=sample, daemon=True); t.start(); t0 = time.time()
    a = pipeline.analyze_lift(video, output_video=os.path.join(out, "annotated.mp4"), lift_type=lift)
    stop = True; t.join()
    clips = os.path.join(out, "clips"); n = len(os.listdir(clips)) if os.path.isdir(clips) else 0
    print({"tree_GiB": round(peak["tree"] / 2**30, 2), "parent_GiB": round(peak["parent"] / 2**30, 2),
           "max_children": peak["kids"], "max_ffmpeg": peak["ffmpeg"]}, "reps", len(a.report.reps),
          "clips", n, "wall_s", round(time.time() - t0, 1), "env",
          {k: os.environ.get(k) for k in ("LIFT_POSE_WORKERS", "SKIP_METRIC_CLIPS_FOR", "LIFT_VIDEO_ENCODER")})
