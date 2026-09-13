"""Side-by-side 5x crops of the far end on two frames with the annotated corners
(green) and a method's predicted corners (red) from results JSON. No mask, so
the eye can judge where the lane ends against the deck and the gutters."""
import json, sys
import cv2, numpy as np
import common as C
L = C.L
stem, fa, fb, method = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
tiles = []
for f in (fa, fb):
    img = C.read_frame(stem, f)
    t = L.truth_corners(stem, f)
    cx = (t["top_left"][0] + t["top_right"][0]) / 2; cy = t["top_left"][1]
    w = t["top_right"][0] - t["top_left"][0]
    r = int(max(w * 1.3, 70)); rh = int(max(w * 0.9, 50))
    x1, x2 = int(max(0, cx - r)), int(min(img.shape[1], cx + r)); y1, y2 = int(max(0, cy - rh)), int(min(img.shape[0], cy + rh))
    crop = img[y1:y2, x1:x2].copy(); z = 5
    crop = cv2.resize(crop, None, fx=z, fy=z, interpolation=cv2.INTER_CUBIC)
    def poly(c, col):
        p = np.array([[(c[k][0] - x1) * z, (c[k][1] - y1) * z] for k in ("top_left", "top_right", "bottom_right", "bottom_left")], np.int32)
        cv2.polylines(crop, [p], True, col, 2, cv2.LINE_AA)
    poly(t, (0, 220, 0))
    for kind in ("last", "prehit", "prehit-6"):
        try:
            rows = json.load(open(f"results/{method}_{kind}_k.json"))
        except FileNotFoundError:
            continue
        for row in rows:
            if row["stem"] == stem and row["frame"] == f and row.get("ok"):
                poly({k: tuple(v) for k, v in row["corners"].items()}, (0, 0, 255))
                cv2.putText(crop, f"{method}_{kind}_k MAE {row['board_mae']}", (8, crop.shape[0] - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(crop, f"{stem} f{f}", (8, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    tiles.append(crop)
h = min(t.shape[0] for t in tiles); tiles = [t[:h] for t in tiles]
out = np.hstack(tiles)
p = C.OVERLAYS / f"diagtop_{stem}_{fa}_{fb}.jpg"; cv2.imwrite(str(p), out, [cv2.IMWRITE_JPEG_QUALITY, 92]); print(p, out.shape)
