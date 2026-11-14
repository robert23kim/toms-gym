"""Seam probe: does a cold-started landmarker re-sync bit-exactly with the sequential stream?"""
import struct, sys, time, json, os
import cv2
import mediapipe as mp
from src.lifting.pose.estimator import _ensure_model, resolve_pose_delegate
from src.bowling.video.io import open_video


def mk():
    o = mp.tasks.vision.PoseLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=_ensure_model(), delegate=resolve_pose_delegate()),
        running_mode=mp.tasks.vision.RunningMode.VIDEO, min_pose_detection_confidence=0.5,
        min_tracking_confidence=0.5, num_poses=int(os.environ.get('PROBE_NUM_POSES','5')))
    return mp.tasks.vision.PoseLandmarker.create_from_options(o)


def run(path, start, end):
    cap = open_video(path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    lm = mk()
    out = {}
    i = 0
    while i < end:
        if i < start:
            if not cap.grab():
                break
            i += 1
            continue
        ret, frame = cap.read()
        if not ret:
            break
        ts = i * (1000.0 / fps) if fps > 0 else 0.0
        img = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        r = lm.detect_for_video(img, int(ts))
        vals = []
        for pl in (r.pose_landmarks or []):
            for p in pl:
                vals += [p.x, p.y, p.z, p.visibility or 0.0, p.presence or 0.0]
        for pl in (r.pose_world_landmarks or []):
            for p in pl:
                vals += [p.x, p.y, p.z]
        out[i] = (len(r.pose_landmarks or []), struct.pack(f"{len(vals)}d", *vals), vals)
        i += 1
    cap.release(); lm.close()
    return out


def main():
    path, n, warm = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    offsets = [int(x) for x in sys.argv[4].split(",")]
    t = time.time(); a = run(path, 0, n); ta = time.time() - t
    b = run(path, 0, n)
    det = sum(1 for i in a if a[i][1] != b[i][1])
    npose = [a[i][0] for i in sorted(a)]
    print(json.dumps({"video": path.split("/")[-1], "frames": len(a), "seq_s": round(ta, 1), "seq_vs_seq_diff_frames": det,
                      "poses_hist": {k: npose.count(k) for k in sorted(set(npose))}}))
    for off in offsets:
        c = run(path, off, min(off + warm, len(a)))
        first_same = None; relapse = 0; maxd = []
        for i in sorted(c):
            same = c[i][1] == a[i][1]
            if same and first_same is None:
                first_same = i - off
            if (not same) and first_same is not None:
                relapse += 1
            if c[i][0] == a[i][0] and len(c[i][2]) == len(a[i][2]) and c[i][2]:
                maxd.append(max(abs(x - y) for x, y in zip(c[i][2], a[i][2])))
            else:
                maxd.append(None)
        tail_same = 0
        for i in sorted(c, reverse=True):
            if c[i][1] == a[i][1]:
                tail_same += 1
            else:
                break
        print(json.dumps({"offset": off, "poses_at_off": a[off][0], "first_identical_after": first_same,
                          "diff_frames_after_first": relapse, "identical_tail_len": tail_same, "n": len(c),
                          "maxdiff_first8": [None if d is None else float(f"{d:.3g}") for d in maxd[:8]],
                          "maxdiff_at_20_40_last": [None if d is None else float(f"{d:.3g}") for d in (maxd[20:21] + maxd[40:41] + maxd[-1:])]}))


if __name__ == "__main__":
    main()
