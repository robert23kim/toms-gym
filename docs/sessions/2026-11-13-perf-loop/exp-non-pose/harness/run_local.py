"""Run the engine's /analyze-lift code path on one local fixture, no GCS.

Mirrors service/app.py analyze_lift(): copy to <tmp>/input.mp4, analyze_lift(
output_video=annotated.mp4, camera_view_override=None, no_overlay=False),
build_lift_summary, _reencode_h264 on the annotated video, then the clip
re-encode pool (CLIP_UPLOAD_WORKERS, threads=2) with the GCS upload removed.
"""
import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

def code_hash(root):
    """sha256 over every .py under src/ and service/ (relative path + bytes)."""
    import hashlib
    h = hashlib.sha256()
    for sub in ("src", "service"):
        for dp, dns, fns in sorted(os.walk(os.path.join(root, sub))):
            dns[:] = sorted(d for d in dns if d != "__pycache__")
            for fn in sorted(fns):
                if fn.endswith(".py"):
                    fp = os.path.join(dp, fn)
                    h.update(os.path.relpath(fp, root).encode())
                    with open(fp, "rb") as f:
                        h.update(f.read())
    return h.hexdigest()[:16]


LIFT_TYPES = {"situp", "pushup", "squat", "plank", "deadlift", "bicep_curl", "bench_press"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--worktree", required=True)
    ap.add_argument("--fixture", required=True)
    ap.add_argument("--lift-type")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--keep-tmp", action="store_true")
    ap.add_argument("--expect-code-hash")
    a = ap.parse_args()

    worktree = os.path.realpath(a.worktree)
    sys.path.insert(0, worktree)
    name = os.path.splitext(os.path.basename(a.fixture))[0]
    lift_type = a.lift_type or name.split("_")[0]
    if lift_type not in LIFT_TYPES:
        sys.exit(f"unknown lift type {lift_type!r}")

    chash = code_hash(worktree)
    if a.expect_code_hash and a.expect_code_hash != chash:
        sys.exit(f"CODE HASH FAIL: {worktree} has {chash}, expected {a.expect_code_hash} (mount missing?)")
    from src.lifting import pipeline
    from src.lifting import plank_analyzer
    from src.lifting.pose import estimator as est_mod
    from src.lifting.summary import build_lift_summary
    import service.app as svc

    for mod in (pipeline, plank_analyzer, est_mod, svc):
        if not os.path.realpath(mod.__file__).startswith(worktree + os.sep):
            sys.exit(f"CANARY FAIL: {mod.__name__} loaded from {mod.__file__}, not {worktree}")

    if os.environ.get("PERF_FFMPEG_BIN"):
        from src.lifting import video_writer
        video_writer.FFMPEG_BIN = os.environ["PERF_FFMPEG_BIN"]

    sub = {}
    art = {"ffmpeg_reencode_runs": 0, "clips_uploaded": 0, "clips_reencoded": 0}
    import threading
    art_lock = threading.Lock()
    real_run = svc.subprocess.run

    def counting_run(cmd, *args, **kw):
        if cmd and cmd[0] == "ffmpeg":
            with art_lock:
                art["ffmpeg_reencode_runs"] += 1
        return real_run(cmd, *args, **kw)

    svc.subprocess.run = counting_run

    def timed(key, fn):
        def wrapper(*args, **kw):
            t = time.time()
            try:
                return fn(*args, **kw)
            finally:
                sub[key] = round(sub.get(key, 0.0) + time.time() - t, 2)
        return wrapper

    P = est_mod.PoseEstimator
    P.estimate_video = timed("pose", P.estimate_video)
    P.estimate_video_candidates = timed("pose", P.estimate_video_candidates)
    pipeline._render_output_video = timed("render_video", pipeline._render_output_video)
    pipeline._render_metric_clips = timed("render_clips", pipeline._render_metric_clips)
    plank_analyzer.analyze_plank = timed("plank_analyze", plank_analyzer.analyze_plank)

    os.makedirs(a.out_dir, exist_ok=True)
    tmp_dir = tempfile.mkdtemp(prefix="perfbench_")
    stages = {}
    t0 = time.time()
    last = [t0, None]

    def mark(stage):
        now = time.time()
        if last[1]:
            stages[last[1]] = round(stages.get(last[1], 0.0) + now - last[0], 2)
        last[:] = [now, stage]

    try:
        input_path = os.path.join(tmp_dir, "input.mp4")
        output_path = os.path.join(tmp_dir, "annotated.mp4")
        mark("download")
        shutil.copyfile(a.fixture, input_path)
        mark("analyze")
        analysis = pipeline.analyze_lift(input_path, output_video=output_path,
                                         camera_view_override=None, no_overlay=False,
                                         lift_type=lift_type)
        report = build_lift_summary(analysis)
        mark("reencode")
        final_video = svc._reencode_h264(output_path, os.path.join(tmp_dir, "annotated_h264.mp4"))
        mark("artifact_copy")
        art["annotated_uploaded_from"] = os.path.basename(final_video)
        art["annotated_bytes"] = os.path.getsize(final_video)
        art["clips_dir_exists"] = os.path.isdir(os.path.join(tmp_dir, "clips"))
        shutil.copyfile(final_video, os.path.join(a.out_dir, f"{name}.annotated.mp4"))
        keep_dir = os.path.join(a.out_dir, f"{name}.clips")
        mark("clips")
        metrics = [m for rm in report.get("rep_metrics", []) for m in rm.get("metrics", [])]

        def publish(metric):
            clip_path = metric.get("clip_url", "")
            if not clip_path or not os.path.isfile(clip_path):
                metric.pop("clip_url", None)
                return
            clip_name = os.path.basename(clip_path)
            h264_clip = os.path.join(tmp_dir, f"clip_h264_{clip_name}")
            svc._reencode_h264(clip_path, h264_clip, threads=2)
            clip_file = h264_clip if os.path.isfile(h264_clip) else clip_path
            with art_lock:
                art["clips_uploaded"] += 1
                art["clips_reencoded"] += int(clip_file == h264_clip)
                art["clip_bytes"] = art.get("clip_bytes", 0) + os.path.getsize(clip_file)
            if clip_name.startswith(("rep1_", "rep2_")):
                os.makedirs(keep_dir, exist_ok=True)
                shutil.copyfile(clip_file, os.path.join(keep_dir, clip_name))
            metric["clip_url"] = f"local://clips/{clip_name}"

        if os.path.isdir(os.path.join(tmp_dir, "clips")) and "rep_metrics" in report:
            with ThreadPoolExecutor(max_workers=max(1, svc.CLIP_UPLOAD_WORKERS)) as pool:
                list(pool.map(publish, metrics))
        mark(None)
    finally:
        if not a.keep_tmp:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    total = round(time.time() - t0, 2)
    summary_path = os.path.join(a.out_dir, f"{name}.summary.json")
    with open(summary_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    timing = {"fixture": name, "lift_type": lift_type, "worktree": worktree, "code_hash": chash,
              "env": {k: os.environ.get(k) for k in os.environ.get("PERF_FLAGS", "").split() if k},
              "stages": stages, "analyze_breakdown": sub, "wall_s": total, "artifact": art,
              "total_reps": report.get("total_reps"), "total_in_plank_s": report.get("total_in_plank_s")}
    with open(os.path.join(a.out_dir, f"{name}.timing.json"), "w") as f:
        json.dump(timing, f, indent=2)
    print(json.dumps(timing))


if __name__ == "__main__":
    main()
