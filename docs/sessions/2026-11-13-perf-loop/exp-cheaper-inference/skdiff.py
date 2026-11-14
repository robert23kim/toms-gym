"""Compare two screen dirs: per fixture skeleton max delta (px), frames differing, reps."""
import json, os, sys
import numpy as np
a, b = sys.argv[1], sys.argv[2]
for f in sorted(os.listdir(b)):
    if not f.endswith(".skeletons.npy"):
        continue
    n = f[:-len(".skeletons.npy")]
    if not os.path.exists(os.path.join(a, f)):
        print(n, "missing in A"); continue
    x, y = np.load(os.path.join(a, f)), np.load(os.path.join(b, f))
    ja, jb = (json.load(open(os.path.join(d, n + ".screen.json"))) for d in (a, b))
    if x.shape != y.shape:
        print(n, "SHAPE", x.shape, y.shape); continue
    same = np.array_equal(x, y, equal_nan=True)
    pres = int((np.isnan(x[:, :, 0]) != np.isnan(y[:, :, 0])).any(axis=1).sum())
    d = np.abs(x[:, :, :2] - y[:, :, :2]); d = np.where(np.isnan(d), 0, d)
    diff_frames = int((d.max(axis=(1, 2)) > 0).sum())
    print(f"{n}: identical={same} frames={len(x)} frames_differing={diff_frames} presence_mismatch_frames={pres} "
          f"max_px={d.max():.3f} p99_px={np.percentile(d.max(axis=(1,2)), 99):.3f} reps {ja['total_reps']}->{jb['total_reps']} "
          f"pose_s {ja['pose_s']}->{jb['pose_s']} stats={jb['pose_stats']}")
