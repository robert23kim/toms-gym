"""Chunk-interleaved pose timing: every arm's PoseEstimator sees the same frames, chunk by chunk,
in rotating order, so machine load hits all arms alike. Times est._detect (resize + BGR->RGB +
mp.Image + inference), per SOURCE frame. off2 is a second flag-off arm: the noise floor."""
import argparse, json, os, statistics as st, sys, time

ARMS = {"off": {}, "off2": {}, "np1": {"num_poses": 1}, "stride2": {"frame_stride": 2},
        "side640": {"max_side": 640}, "np1+stride2": {"num_poses": 1, "frame_stride": 2}}
ARMS.update({"np3": {"num_poses": 3}, "np2": {"num_poses": 2}})
if os.environ.get("IBENCH_ARMS"):
    ARMS = {k: ARMS[k] for k in os.environ["IBENCH_ARMS"].split(",")}

ap = argparse.ArgumentParser()
ap.add_argument("--worktree", required=True); ap.add_argument("--fixture", required=True)
ap.add_argument("--chunk", type=int, default=48); ap.add_argument("--out", required=True)
a = ap.parse_args()
wt = os.path.realpath(a.worktree); sys.path.insert(0, wt)
from src.lifting.pose import estimator as est
from src.bowling.video.io import open_video
import cv2
assert os.path.realpath(est.__file__).startswith(wt + os.sep), est.__file__

ests = {k: est.PoseEstimator(**v) for k, v in ARMS.items()}
wall = {k: [] for k in ARMS}; cpu = {k: 0.0 for k in ARMS}
cap = open_video(a.fixture); fps = cap.get(cv2.CAP_PROP_FPS)
names = list(ARMS); idx = 0; ci = 0; frames = 0
while True:
    chunk = []
    while len(chunk) < a.chunk:
        ok, f = cap.read()
        if not ok:
            break
        chunk.append((idx, f)); idx += 1
    if not chunk:
        break
    frames += len(chunk)
    order = names[ci % len(names):] + names[:ci % len(names)]
    for k in order:
        e = ests[k]; s = e._frame_stride
        t = time.perf_counter(); c = time.process_time()
        for i, f in chunk:
            if i % s == 0:
                e._detect(f, i * 1000.0 / fps)
        wall[k].append((time.perf_counter() - t) / len(chunk)); cpu[k] += time.process_time() - c
    ci += 1
res = {"fixture": os.path.basename(a.fixture), "frames": frames, "chunks": ci, "chunk": a.chunk, "arms": {}}
for k in names:
    ratios = [w / o for w, o in zip(wall[k], wall["off"])]
    res["arms"][k] = {"wall_ms_per_frame": round(1000 * st.mean(wall[k]), 2), "cpu_ms_per_frame": round(1000 * cpu[k] / frames, 2),
                      "ratio_vs_off_total": round(sum(wall[k]) / sum(wall["off"]), 3),
                      "ratio_vs_off_chunk_median": round(st.median(ratios), 3),
                      "ratio_vs_off_chunk_p10_p90": [round(x, 3) for x in (sorted(ratios)[len(ratios) // 10], sorted(ratios)[-1 - len(ratios) // 10])],
                      "stats": {s: ests[k].stats[s] for s in ("num_poses", "max_side", "frame_stride", "inferred", "resized", "poses")}}
json.dump(res, open(a.out, "w"), indent=1)
for k, v in res["arms"].items():
    print(res["fixture"], k, v)
