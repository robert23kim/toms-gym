"""Pose-inference seconds per frame vs num_poses on the same decoded frames (timing only)."""
import sys, time, json, cv2, mediapipe as mp
model, video, nmax = sys.argv[1], sys.argv[2], int(sys.argv[3])
cap = cv2.VideoCapture(video); cap.set(cv2.CAP_PROP_ORIENTATION_AUTO, 1); fps = cap.get(cv2.CAP_PROP_FPS)
frames = []
while len(frames) < nmax:
    ok, f = cap.read()
    if not ok: break
    frames.append(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
res = {}
for rep in (1, 2):
    for n in (5, 1):
        lm = mp.tasks.vision.PoseLandmarker.create_from_options(mp.tasks.vision.PoseLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=model), running_mode=mp.tasks.vision.RunningMode.VIDEO,
            min_pose_detection_confidence=0.5, min_tracking_confidence=0.5, num_poses=n))
        t = time.perf_counter(); got = 0
        for i, fr in enumerate(frames):
            r = lm.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=fr), int(i * 1000 / fps)); got += len(r.pose_landmarks or [])
        dt = time.perf_counter() - t; lm.close()
        res[f"num_poses={n} rep{rep}"] = dict(s=round(dt, 2), ms_per_frame=round(1000 * dt / len(frames), 1), poses_per_frame=round(got / len(frames), 2))
print(json.dumps(dict(video=video.split('/')[-1], frames=len(frames), **res)))
