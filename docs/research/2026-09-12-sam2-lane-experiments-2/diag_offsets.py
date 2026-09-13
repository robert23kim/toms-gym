"""Numeric edge diagnostic: median (mask edge - truth line) in px at five heights
per side, for a prompt set on a frame. Positive = mask edge is right of truth."""
import sys
import numpy as np
import common as C, edges as E, sam2x as S
L = C.L
stem, f, rule = sys.argv[1], int(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else "keep"
img = C.read_frame(stem, f)
pts = C.even_points_keep(stem, f, 3) if rule == "keep" else L.track_points_even(stem, f, n=3)
si = S.SamImage(img, "sam2.1_b.pt")
lg, _ = si.logit(pts)
comp = E.component(lg, pts)
t = L.truth_corners(stem, f)
y_top, y_bot = L.gt_y(stem, f)
ys, xl, xr = E.soft_rows(lg, y_top, y_bot, pts, comp)
out = {"stem": stem, "frame": f, "rule": rule, "prompts": pts, "rows": int(len(ys)), "coverage": round(len(ys) / (y_bot - y_top + 1), 2)}
for side, (ka, kb), xs in (("left", ("top_left", "bottom_left"), xl), ("right", ("top_right", "bottom_right"), xr)):
    (x1, y1), (x2, y2) = t[ka], t[kb]
    tx = x1 + (ys - y1) / (y2 - y1) * (x2 - x1)
    d = xs - tx
    bands = []
    for lo, hi in ((0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, 1.0)):
        m = (ys >= y_top + lo * (y_bot - y_top)) & (ys < y_top + hi * (y_bot - y_top))
        bands.append(round(float(np.median(d[m])), 1) if m.sum() else None)
    out[side] = bands
w_true = t["top_right"][0] - t["top_left"][0]
top = ys < y_top + 0.1 * (y_bot - y_top)
out["top_width_mask_vs_truth"] = (round(float(np.median(xr[top] - xl[top])), 1) if top.sum() else None, round(w_true, 1))
print(out)
