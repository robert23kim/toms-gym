"""Dev-only: redraw tracks/<stem>.json (orange) with the truth (green) on the pin_hit-4 frame -> work/cmp_<stem>.jpg, half size."""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
L = HERE.parents[1]
sys.path.insert(0, str(L))
import score_tracks  # noqa: E402

for stem in sys.argv[1:]:
    cuts = {c["stem"]: c for c in json.load(open(L / "work/cuts/cuts.json"))}
    c = cuts[stem]
    tr = json.load(open(HERE / "tracks" / f"{stem}.json"))
    truth = json.load(open(L / "truth" / f"{stem}.json"))
    sc = score_tracks.score(tr, truth)
    f = int(c["pin_hit_frame"]) - 4
    cap = cv2.VideoCapture(c["cut_path"])
    cap.set(cv2.CAP_PROP_POS_FRAMES, f - c["cut_start"])
    ok, im = cap.read()
    tp = sorted((int(k), score_tracks.ball_point(v)) for k, v in truth["ball"].items())
    tp = [(k, p) for k, p in tp if p is not None and truth["release_frame"] <= k <= truth["pin_hit_frame"]]
    pts = [(int(p[1][0]), int(p[1][1])) for p in tp]
    for a, b in zip(pts, pts[1:]):
        cv2.line(im, a, b, (0, 200, 0), 2)
    for k, p in tp:
        cv2.circle(im, (int(p[0]), int(p[1])), 4, (0, 255, 0), -1)
    pts = [(int(p["x"]), int(p["y"])) for p in tr["frames"]]
    for a, b in zip(pts, pts[1:]):
        cv2.line(im, a, b, (0, 140, 255), 2)
    for p in tr["frames"]:
        cv2.circle(im, (int(p["x"]), int(p["y"])), 3, (0, 100, 255), -1)
    q = tr["lane"].get(str(f))
    if q:
        cv2.polylines(im, [np.array([q["fl_l"], q["pd_l"], q["pd_r"], q["fl_r"]], np.int32)], True, (255, 220, 0), 3)
    for k, lq in (truth.get("lane_quads") or {}).items():
        if abs(int(k) - f) <= 3:
            cv2.polylines(im, [np.array([lq["fl_l"], lq["pd_l"], lq["pd_r"], lq["fl_r"]], np.int32)], True, (0, 255, 0), 2)
    txt = f"{stem[9:15]} f{f} recall {sc['recall_pct']} board_err {sc['board_err']} lane_err {sc['lane_err_boards']} win {sc['window_err']}"
    cv2.putText(im, txt, (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 3)
    cv2.putText(im, "orange = track, green = truth, cyan = lane", (20, 110), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 3)
    cv2.imwrite(str(HERE / "work" / f"cmp_{stem}.jpg"), cv2.resize(im, None, fx=0.5, fy=0.5))
    print(json.dumps({k: sc[k] for k in ("stem", "recall_pct", "median_px_err", "board_err", "lane_err_boards", "window_err", "pass")}))
