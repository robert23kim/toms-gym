"""E1a: what is on the lane plane near the foul line? Rectified band (approach -16 ft ..
20 ft) through the all-landmark truth homography on the pre-hit frame, dark blobs marked.
usage: e1_inspect.py [stems...]  -> overlays/e1_near_<stem>.jpg"""
import sys
import cv2
import numpy as np
import af

PPI = 12.0
for stem in (sys.argv[1:] or af.STEMS):
    f = af.frame_for(stem, "prehit")
    img = af.read_frame(stem, f)
    H = af.truth_h(stem, f, "all")
    y0, y1 = -16 * 12.0, 20 * 12.0
    rect, Hr = af.rectify_band(img, H, y0, y1, PPI, x0_in=-8, x1_in=af.W_IN + 8)
    g = cv2.cvtColor(rect, cv2.COLOR_BGR2GRAY)
    blobs, thr = af.dark_blobs(g, bg_ks=41, k_mad=4.0, area=(8, 2500))
    ov = rect.copy()
    for ft in range(-15, 21):
        y = int((y1 - ft * 12) * PPI)
        col = (0, 200, 255) if ft % 5 == 0 else (90, 90, 90)
        cv2.line(ov, (0, y), (ov.shape[1] - 1, y), col, 1)
        if ft % 5 == 0:
            cv2.putText(ov, f"{ft} ft", (4, y - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 200, 255), 1)
    for x_in in (0.0, af.W_IN):
        x = int((x_in + 8) * PPI); cv2.line(ov, (x, 0), (x, ov.shape[0] - 1), (255, 0, 255), 1)
    for b in blobs:
        cv2.circle(ov, (int(b["x"]), int(b["y"])), 7, (0, 255, 0), 1)
    cv2.putText(ov, f"{af.SHORT[stem]} f{f} rectified -16..20 ft, {PPI:.0f} px/in, dark blobs green (thr {thr:.1f})", (4, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.imwrite(str(af.OVERLAYS / f"e1_near_{stem}.jpg"), ov, [cv2.IMWRITE_JPEG_QUALITY, 90])
    # blob table in lane inches
    rows = []
    for b in blobs:
        x_in = b["x"] / PPI - 8; y_in = y1 - b["y"] / PPI
        rows.append((round(y_in / 12, 2), round(x_in, 1), round(af.LM.boards_from_lane_x(x_in), 1), b["area"], round(b["darkness"], 1)))
    rows.sort()
    print(stem, f, "rect", rect.shape, "blobs", len(blobs))
    for r in rows:
        print("  ft %6.2f  x_in %6.1f  board %5.1f  area %4d  dark %5.1f" % r)
