"""Pose pass + analysis (no render) on one fixture; dumps skeletons, summary, pose seconds and pose stats.

Screening instrument for the cheaper-inference experiment: only the pose pass changes,
so a bitwise-identical skeleton dump means an identical report on this machine.
"""
import argparse, hashlib, json, os, sys, time
import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--worktree", required=True)
    ap.add_argument("--fixture", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--pose-only", action="store_true", help="timing run: skip the dumps")
    a = ap.parse_args()
    worktree = os.path.realpath(a.worktree)
    sys.path.insert(0, worktree)
    name = os.path.splitext(os.path.basename(a.fixture))[0]
    lift_type = name.split("_")[0]

    from src.lifting import pipeline
    from src.lifting.pose import estimator as est_mod
    from src.lifting.config import LANDMARK_NAMES
    from src.lifting.summary import build_lift_summary
    for mod in (pipeline, est_mod):
        if not os.path.realpath(mod.__file__).startswith(worktree + os.sep):
            sys.exit(f"CANARY FAIL: {mod.__name__} loaded from {mod.__file__}")

    pose_s = [0.0]

    def timed(fn):
        def wrapper(*args, **kw):
            t = time.perf_counter()
            try:
                return fn(*args, **kw)
            finally:
                pose_s[0] += time.perf_counter() - t
        return wrapper

    P = est_mod.PoseEstimator
    P.estimate_video = timed(P.estimate_video)
    P.estimate_video_candidates = timed(P.estimate_video_candidates)

    t0 = time.perf_counter()
    analysis = pipeline.analyze_lift(a.fixture, output_video=None, camera_view_override=None,
                                     no_overlay=False, lift_type=lift_type)
    total = time.perf_counter() - t0
    report = build_lift_summary(analysis)

    names = [LANDMARK_NAMES[i] for i in sorted(LANDMARK_NAMES)]
    arr = np.full((len(analysis.skeletons), len(names), 3), np.nan)
    for i, sk in enumerate(analysis.skeletons):
        for j, n in enumerate(names):
            kp = sk.keypoints.get(n)
            if kp is not None:
                arr[i, j] = (kp.x, kp.y, kp.confidence)
    os.makedirs(a.out_dir, exist_ok=True)
    out = {"fixture": name, "lift_type": lift_type, "pose_s": round(pose_s[0], 2), "total_s": round(total, 2),
           "cpu_s": round(sum(__import__("resource").getrusage(0)[:2]), 2),
           "frames": len(analysis.skeletons), "total_reps": report.get("total_reps"),
           "skeleton_sha": hashlib.sha256(arr.tobytes()).hexdigest()[:16],
           "pose_stats": dict(getattr(est_mod, "LAST_RUN_STATS", {})),
           "flags": {k: v for k, v in os.environ.items() if k.startswith("POSE_")}}
    if not a.pose_only:
        np.save(os.path.join(a.out_dir, f"{name}.skeletons.npy"), arr)
        with open(os.path.join(a.out_dir, f"{name}.summary.json"), "w") as f:
            json.dump(report, f, indent=2, default=str)
        with open(os.path.join(a.out_dir, f"{name}.screen.json"), "w") as f:
            json.dump(out, f, indent=2)
    print(json.dumps(out))


if __name__ == "__main__":
    main()
