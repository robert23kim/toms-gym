"""Diagnostic: zoomed crops along both lane edges with the truth line (green),
the SAM component boundary (red) and the intensity profile, to see whether a
consistent offset is a mask error or an annotation convention."""
import sys
import cv2
import numpy as np
import common as C, edges as E, sam2x as S
L = C.L
stem, f = sys.argv[1], int(sys.argv[2])
img = C.read_frame(stem, f)
pts = C.even_points_keep(stem, f, 3)
si = S.SamImage(img, "sam2.1_b.pt")
lg, _ = si.logit(pts)
comp = E.component(lg, pts)
t = L.truth_corners(stem, f)
y_top, y_bot = L.gt_y(stem, f)
tiles = []
for side, (ka, kb) in (("left", ("top_left", "bottom_left")), ("right", ("top_right", "bottom_right"))):
    (x1, y1), (x2, y2) = t[ka], t[kb]
    for fr in (0.15, 0.5, 0.9):
        y = int(y1 + fr * (y2 - y1)); x = x1 + fr * (x2 - x1)
        r = 28
        ya, yb = max(0, y - r), min(img.shape[0], y + r); xa, xb = int(max(0, x - r)), int(min(img.shape[1], x + r))
        crop = img[ya:yb, xa:xb].copy()
        # truth line through this tile
        for yy in range(ya, yb):
            xt = x1 + (yy - y1) / (y2 - y1 + 1e-6) * (x2 - x1)
            xi = int(round(xt)) - xa
            if 0 <= xi < crop.shape[1]: crop[yy - ya, xi] = (0, 220, 0)
        # mask boundary
        for yy in range(ya, yb):
            row = comp[yy, xa:xb]
            xs = np.where(row)[0]
            if len(xs):
                e = xs.min() if side == "left" else xs.max()
                crop[yy - ya, e] = (0, 0, 255)
        z = cv2.resize(crop, None, fx=6, fy=6, interpolation=cv2.INTER_NEAREST)
        g = cv2.cvtColor(img[y, xa:xb][None], cv2.COLOR_BGR2GRAY)[0]
        cv2.putText(z, f"{side} {fr:.2f} y={y}", (4, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        # profile: gray along the row, plotted
        h = 60; prof = np.full((h, z.shape[1], 3), 30, np.uint8)
        for i, v in enumerate(g):
            cv2.line(prof, (i * 6, h - 1), (i * 6, h - 1 - int(v / 255 * (h - 2))), (200, 200, 200), 4)
        tiles.append(np.vstack([z, prof]))
row1 = np.hstack(tiles[:3]); row2 = np.hstack(tiles[3:])
out = np.vstack([row1, row2])
p = C.OVERLAYS / f"diag_{stem}_{f}.jpg"
cv2.imwrite(str(p), out, [cv2.IMWRITE_JPEG_QUALITY, 90])
print(p, "mask width at y_bot:", (lambda xs: (xs.min(), xs.max()))(np.where(comp[int(y_bot) - 2])[0]), "truth:", t["bottom_left"], t["bottom_right"])
