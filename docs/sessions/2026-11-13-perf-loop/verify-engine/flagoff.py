#!/usr/bin/env python3
"""flagoff.py <video> <lift> <outdir> <out.json> - analyze_lift + build_lift_summary with whatever
env is set; writes the summary with clip_url reduced to its basename, for a byte compare."""
import json, os, sys
from src.lifting import pipeline
from src.lifting.summary import build_lift_summary
video, lift, out, dst = sys.argv[1:5]
os.makedirs(out, exist_ok=True)
rep = build_lift_summary(pipeline.analyze_lift(video, output_video=os.path.join(out, "annotated.mp4"), lift_type=lift))
for rm in rep.get("rep_metrics", []):
    for m in rm.get("metrics", []):
        if m.get("clip_url"): m["clip_url"] = os.path.basename(m["clip_url"])
json.dump(rep, open(dst, "w"), sort_keys=True, default=str)
print(dst, "flags", {k: os.environ.get(k) for k in ("LIFT_POSE_WORKERS", "SKIP_METRIC_CLIPS_FOR", "LIFT_VIDEO_ENCODER")})
