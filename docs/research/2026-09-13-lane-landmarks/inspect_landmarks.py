"""Visual check of which landmarks are visible: pin-deck crop at 6x, rectified
lane (bird's-eye from the annotated corners, 390 x 2000 px) so arrows / dots
show as a strip, plus the foul-line end. usage: inspect_landmarks.py [kind]"""
import sys
import cv2
import numpy as np
import common as C

C.use_full_camera()
kind = sys.argv[1] if len(sys.argv) > 1 else "prehit"
for s in C.STEMS:
    f = C.frame_for(s, kind)
    img = C.read_frame(s, f)
    h, w = img.shape[:2]
    t = C.truth_quad(s, f)
    # pin deck crop: around the top edge, 1.6 lane widths wide, up to 1.2 widths above
    tw = t["top_right"][0] - t["top_left"][0]
    cx = (t["top_left"][0] + t["top_right"][0]) / 2; cy = (t["top_left"][1] + t["top_right"][1]) / 2
    x1, x2 = int(max(0, cx - 1.1 * tw)), int(min(w, cx + 1.1 * tw))
    y1, y2 = int(max(0, cy - 1.3 * tw)), int(min(h, cy + 0.5 * tw))
    crop = img[y1:y2, x1:x2]
    z = max(1, int(round(480 / max(1, crop.shape[1]))))
    crop = cv2.resize(crop, None, fx=z, fy=z, interpolation=cv2.INTER_CUBIC)
    # draw annotated top corners
    for k in ("top_left", "top_right"):
        px, py = t[k]
        cv2.circle(crop, (int((px - x1) * z), int((py - y1) * z)), 5, (0, 220, 0), 2)
    cv2.putText(crop, f"{C.SHORT[s]} f{f} pin deck x{z}", (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.imwrite(str(C.OVERLAYS / f"inspect_pins_{s}.jpg"), crop, [cv2.IMWRITE_JPEG_QUALITY, 92])
    # rectified lane: 390 wide (10 px / board), 2000 tall (60 ft -> 33 px/ft)
    H = C.quad_h(t, 390, 2000)
    rect = cv2.warpPerspective(img, H, (390, 2000), flags=cv2.INTER_CUBIC)
    # arrows expected ~15 ft = 45 ft from the pins -> y = 2000 * 45/60 = 1500; mark the band 12-16 ft
    for ft in (12, 15, 16):
        y = int(2000 * (60 - ft) / 60)
        cv2.line(rect, (0, y), (389, y), (0, 200, 255), 1)
    for b in C.ARROW_BOARDS:
        x = int(390 - (b - 1) / 38 * 390)  # board 1 at the right
        cv2.line(rect, (x, 1380), (x, 1620), (255, 0, 255), 1)
    strip = rect[1200:1800]  # 6 ft .. 24 ft
    strip = cv2.resize(strip, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
    cv2.putText(strip, f"{C.SHORT[s]} f{f} rectified 6-24 ft (arrows ~15 ft)", (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.imwrite(str(C.OVERLAYS / f"inspect_arrows_{s}.jpg"), strip, [cv2.IMWRITE_JPEG_QUALITY, 92])
    full = cv2.resize(rect, None, fx=0.5, fy=0.5)
    cv2.imwrite(str(C.OVERLAYS / f"inspect_rect_{s}.jpg"), full, [cv2.IMWRITE_JPEG_QUALITY, 88])
    print(s, f, "top width px", round(tw, 1), "crop", crop.shape, "zoom", z)
