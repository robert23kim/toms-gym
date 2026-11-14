import sys, time, cv2
from src.bowling.video.io import open_video
for p in sys.argv[1:]:
    cap = open_video(p); t = time.time(); n = 0
    while cap.grab(): n += 1
    tg = time.time() - t; cap.release()
    cap = open_video(p); t = time.time(); m = 0
    while cap.read()[0]: m += 1
    tr = time.time() - t; meta = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); cap.release()
    cap = open_video(p); t = time.time(); cap.set(cv2.CAP_PROP_POS_FRAMES, n * 7 // 8); ok, fr = cap.read(); ts = time.time() - t; cap.release()
    print(p.split("/")[-1], "grab_all_s", round(tg, 2), "read_all_s", round(tr, 2), "frames", n, m, "meta", meta, "seek7/8_s", round(ts, 3))
