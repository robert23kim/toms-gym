"""8x look at the pin base row: annotated edges (orange), pins-based edges (cyan),
fitted pin columns (green) with per-column spacing, and the outer-edge span of
the white mask at belly height. usage: diag_pins.py"""
import cv2
import numpy as np
import common as C
import landmarks as LM
L = C.L
C.use_full_camera()
for stem in C.STEMS:
    f = C.frame_for(stem, "prehit")
    img = C.read_frame(stem, f)
    ann = L.truth_corners(stem, f); H0 = LM.h_from_quad(ann)
    w_px = ann["top_right"][0] - ann["top_left"][0]
    pts, sc, params, score, contrast, parts = LM.fit_rack(img, H0, w_px)
    ref = pts.copy()
    for _ in range(3):
        ref = LM.refine_pin_columns(img, ref, sc)
    cols = sorted(set(round(float(x), 1) for x in ref[:, 0]))
    # 7 columns: group by x
    xs = np.array(sorted(ref[:, 0]))
    groups = []
    for x in xs:
        if groups and abs(x - groups[-1][-1]) < 2.0 * sc.mean():
            groups[-1].append(x)
        else:
            groups.append([x])
    colx = [float(np.mean(g)) for g in groups]
    spacing = np.diff(colx)
    # outer edge span at belly height (4.5 in above base), half-max crossing on the white map
    wmap = LM.white_map(img)
    yb = float(np.mean([ref[6][1], ref[9][1]])); s = float(sc.mean())
    y_belly = yb - 4.5 * s
    x0 = ref[6][0] - 6 * s; x1 = ref[9][0] + 6 * s
    xx = np.arange(x0, x1, 0.1); prof = LM.sample(wmap, np.stack([xx, np.full(len(xx), y_belly)], 1))
    hm = 0.5 * (prof.max() + np.median(prof[:10].tolist() + prof[-10:].tolist()))
    on = np.where(prof >= hm)[0]
    span = (xx[on[0]], xx[on[-1]]) if len(on) else (None, None)
    width_from_span = (span[1] - span[0]) * LM.W_IN / (36 + LM.PIN_W_IN) if span[0] is not None else None
    width_from_spacing = (ref[9][0] - ref[6][0]) * LM.W_IN / 36
    wa, ca = LM.width_centre_at(H0, yb)
    print(f"{C.SHORT[stem]:13s} f{f} px/in {s:.2f} cols {[round(c,1) for c in colx]} spacing {np.round(spacing,1)} (expect {6*s:.1f})  7-10 {ref[9][0]-ref[6][0]:.1f}px -> width {width_from_spacing:.1f}px; outer span {span[1]-span[0] if span[0] is not None else None:.1f}px -> width {width_from_span:.1f}px; annotated width at that row {wa:.1f}px  centre pins {0.5*(ref[6][0]+ref[9][0]):.1f} span-centre {0.5*(span[0]+span[1]):.1f} ann {ca:.1f}")
    # 8x crop
    cx = 0.5 * (ref[6][0] + ref[9][0]); z = 8
    X1, X2 = int(cx - 0.75 * wa), int(cx + 0.75 * wa); Y1, Y2 = int(yb - 0.5 * wa), int(yb + 0.15 * wa)
    crop = cv2.resize(img[Y1:Y2, X1:X2], None, fx=z, fy=z, interpolation=cv2.INTER_CUBIC)
    sh = lambda x, y: (int(round((x - X1) * z)), int(round((y - Y1) * z)))  # noqa: E731
    for (x, y) in ref:
        cv2.line(crop, sh(x, y), sh(x, y - 15 * s), (0, 255, 0), 1)
    cv2.line(crop, sh(ca - wa / 2, yb - 3), sh(ca - wa / 2, yb + 3), (0, 200, 255), 2); cv2.line(crop, sh(ca + wa / 2, yb - 3), sh(ca + wa / 2, yb + 3), (0, 200, 255), 2)
    pl = cx - width_from_spacing / 2; pr = cx + width_from_spacing / 2
    cv2.line(crop, sh(pl, yb - 3), sh(pl, yb + 3), (255, 255, 0), 2); cv2.line(crop, sh(pr, yb - 3), sh(pr, yb + 3), (255, 255, 0), 2)
    if span[0] is not None:
        cv2.line(crop, sh(span[0], y_belly - 1), sh(span[0], y_belly + 1), (255, 0, 255), 2); cv2.line(crop, sh(span[1], y_belly - 1), sh(span[1], y_belly + 1), (255, 0, 255), 2)
    cv2.putText(crop, f"{C.SHORT[stem]} f{f} x8: orange=annotated edge at base row, cyan=pins spacing edge, magenta=outer pin edges at belly, green=columns", (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
    cv2.imwrite(str(C.OVERLAYS / f"diag_pins8x_{stem}.jpg"), crop, [cv2.IMWRITE_JPEG_QUALITY, 92])
