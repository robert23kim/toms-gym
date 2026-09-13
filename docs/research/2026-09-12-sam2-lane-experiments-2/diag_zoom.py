"""Debug one zoom crop: the crop at 3x with the zoomed mask contour (red), the
full-frame mask contour (blue), truth (green), prompts (yellow) and the fitted
lines from the full pass (cyan) and the merged pass (magenta)."""
import sys, time
import cv2, numpy as np
import common as C, edges as E, sam2x as S, run2 as R
L = C.L
stem, f = sys.argv[1], int(sys.argv[2])
R.PROMPT_RULE = "keep"
weights = "sam2.1_b.pt"
img = C.read_frame(stem, f)
H, W = img.shape[:2]
p, lg, sc, comp, full = R._soft_full(stem, f, img, weights)
fp = E.fit_pair(*full)
y_top, y_bot = L.gt_y(stem, f)
y1 = y_top + 0.55 * (y_bot - y_top)
z, box, zpts = R._zoom_rows(stem, f, img, weights, fp[0], fp[1], y_top, y1, n=2, lo=0.10, hi=0.55)
x1, ya, x2, yb = box
crop = img[ya:yb, x1:x2].copy()
zc = z[3]
fc = comp[ya:yb, x1:x2]
for m, col in ((fc, (255, 120, 0)), (zc, (0, 0, 255))):
    cs, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cv2.drawContours(crop, cs, -1, col, 1)
t = L.truth_corners(stem, f)
def line_pts(ln, y0, y1_):
    a, b = ln
    return (int(a * y0 + b - x1), int(y0 - ya)), (int(a * y1_ + b - x1), int(y1_ - ya))
for k1, k2 in (("top_left", "bottom_left"), ("top_right", "bottom_right")):
    cv2.line(crop, (int(t[k1][0] - x1), int(t[k1][1] - ya)), (int(t[k2][0] - x1), int(t[k2][1] - ya)), (0, 220, 0), 1)
cv2.line(crop, (int(t["top_left"][0] - x1), int(t["top_left"][1] - ya)), (int(t["top_right"][0] - x1), int(t["top_right"][1] - ya)), (0, 220, 0), 1)
ys, xl, xr = E.merge_rows([(full[0], full[1], full[2], 0), (z[0], z[1], z[2], 1)])
mp = E.fit_pair(ys, xl, xr)
for ln in fp[:2]:
    cv2.line(crop, *line_pts(ln, y_top, yb), (255, 255, 0), 1)
for ln in mp[:2]:
    cv2.line(crop, *line_pts(ln, y_top, yb), (255, 0, 255), 1)
for x, y in zpts:
    cv2.circle(crop, (x - x1, y - ya), 4, (0, 255, 255), -1)
zc3 = cv2.resize(crop, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
full_mae = L.score(stem, L.lines_to_corners(fp[0], fp[1], y_top, y_bot), f)["board_mae"]
merged_mae = L.score(stem, L.lines_to_corners(mp[0], mp[1], y_top, y_bot), f)["board_mae"]
cv2.putText(zc3, f"{stem} f{f} full(cyan) {full_mae} merged(magenta) {merged_mae}  blue=full mask red=zoom mask green=truth", (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
pth = C.OVERLAYS / f"diagzoom_{stem}_{f}.jpg"
cv2.imwrite(str(pth), zc3, [cv2.IMWRITE_JPEG_QUALITY, 92]); print(pth, zc3.shape)
