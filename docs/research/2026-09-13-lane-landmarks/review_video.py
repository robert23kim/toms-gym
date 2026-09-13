"""Compose review.mp4 (1920x1080, 30 fps, H.264 via OpenCV, no ffmpeg) from results/,
overlays/ and $LM_SCRATCH/pred. Sections: title / question / E1 truth (rack fits, arrows,
truth quads) / baselines re-scored / E2 detectors / E3 table / per-video tracked clips
(annotated green, pins truth cyan, student red, landmark fit yellow, detections drawn,
far-end inset) / E4 / conclusion. usage: review_video.py [--fast] [--variant NAME]"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

import common as C

L = C.L
C.use_full_camera()
PRED = C.SCRATCH / "pred"
W, H = 1920, 1080
BG = (24, 24, 28); FG = (235, 235, 235); DIM = (150, 150, 160)
GREEN = (0, 220, 0); RED = (0, 0, 255); CYAN = (255, 255, 0); YEL = (0, 255, 255); MAG = (255, 0, 200); ORANGE = (0, 165, 255)


def text(img, s, x, y, scale=1.0, color=FG, thick=2, max_w=None):
    max_w = (img.shape[1] - int(x) - 40) if max_w is None else max_w
    (tw, _), _ = cv2.getTextSize(s, cv2.FONT_HERSHEY_SIMPLEX, scale, thick)
    if tw > max_w and tw > 0:
        scale = scale * max_w / tw
    cv2.putText(img, s, (int(x), int(y)), cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick, cv2.LINE_AA)


def canvas():
    c = np.zeros((H, W, 3), np.uint8); c[:] = BG; return c


def card(title, lines, sub=None, y0=260, dy=46, scale=0.9):
    c = canvas(); text(c, title, 80, 120, 1.6, FG, 3)
    if sub:
        text(c, sub, 80, 175, 0.85, DIM, 2)
    y = y0
    for ln in lines:
        s, col = ln if isinstance(ln, tuple) else (ln, FG)
        text(c, s, 80, y, scale, col, 2); y += dy
    return c


def table_card(title, sub, header, rows, cols, y0=240, scale=0.72, dy=38, note=None):
    c = canvas(); text(c, title, 80, 120, 1.5, FG, 3)
    if sub:
        text(c, sub, 80, 175, 0.85, DIM, 2)
    y = y0
    for i, cell in enumerate(header):
        text(c, cell, cols[i], y, scale, DIM, 2, max_w=(cols[i + 1] - cols[i] - 10) if i + 1 < len(cols) else None)
    y += dy
    for r in rows:
        col = FG
        if isinstance(r, tuple):
            r, col = r
        for i, cell in enumerate(r):
            if i < len(cols):
                text(c, str(cell), cols[i], y, scale, col, 2, max_w=(cols[i + 1] - cols[i] - 10) if i + 1 < len(cols) else None)
        y += dy
    if note:
        y += 10
        for ln in note:
            text(c, ln, 80, y, 0.72, DIM, 2); y += 32
    return c


def fit_h(img, h):
    s = h / img.shape[0]
    return cv2.resize(img, (max(1, int(img.shape[1] * s)), h), interpolation=cv2.INTER_AREA)


def panels(images, header, footer=None):
    c = canvas(); text(c, header, 40, 50, 0.95, FG, 2)
    avail_h = H - 130 if footer else H - 80
    ims = [fit_h(im, avail_h) for im in images]
    gap = 16
    total = sum(im.shape[1] for im in ims) + gap * (len(ims) - 1)
    if total > W - 40:
        s = (W - 40) / total
        ims = [cv2.resize(im, (max(1, int(im.shape[1] * s)), max(1, int(im.shape[0] * s))), interpolation=cv2.INTER_AREA) for im in ims]
        total = sum(im.shape[1] for im in ims) + gap * (len(ims) - 1)
    x = (W - total) // 2
    for im in ims:
        h, w = im.shape[:2]; c[70:70 + h, x:x + w] = im; x += w + gap
    if footer:
        text(c, footer, 40, H - 30, 0.8, DIM, 2)
    return c


def caption(img, lines):
    for i, s in enumerate(lines):
        y = img.shape[0] - 16 - 30 * (len(lines) - 1 - i)
        text(img, s, 12, y, 0.7, (0, 0, 0), 4); text(img, s, 12, y, 0.7, FG, 2)


def poly(img, q, color, th=2):
    p = np.array([q["top_left"], q["top_right"], q["bottom_right"], q["bottom_left"]], np.int32)
    cv2.polylines(img, [p], True, color, th, cv2.LINE_AA)


def inset(img, centre, half_w, half_h, z=4, where="tl"):
    h, w = img.shape[:2]
    x1, x2 = int(max(0, centre[0] - half_w)), int(min(w, centre[0] + half_w)); y1, y2 = int(max(0, centre[1] - half_h)), int(min(h, centre[1] + half_h))
    crop = img[y1:y2, x1:x2]
    if crop.size == 0:
        return
    crop = cv2.resize(crop, None, fx=z, fy=z, interpolation=cv2.INTER_NEAREST)
    ch, cw = crop.shape[:2]; cw = min(cw, w - 20); crop = crop[:, :cw]
    ox, oy = (10, 10) if where == "tl" else (w - cw - 10, 10)
    img[oy:oy + ch, ox:ox + cw] = crop
    cv2.rectangle(img, (ox, oy), (ox + cw, oy + ch), (255, 255, 255), 2)
    text(img, f"pin end x{z}", (ox + 6), (oy + ch - 8), 0.6, (255, 255, 255), 2)


def fmt(v, nd=2):
    return "-" if v is None else (f"{v:.{nd}f}" if isinstance(v, (int, float)) and not isinstance(v, bool) else str(v))


def tracked_clip(stem, e3, dets, variant, fast=False):
    """Per frame: left = source student lane (red) vs annotated (green) vs pins truth (cyan);
    right = landmark fit (yellow) with the detected arrows / pins; both with a far-end inset."""
    base = {r["frame"]: r for r in e3["variants"]["corners"]["per_frame"] if r.get("ok")}
    fitd = {r["frame"]: r for r in e3["variants"][variant]["per_frame"] if r.get("ok")}
    fs, pos = L.trajectory_all(stem)
    first_ball = L.trajectory(stem)[0][0]
    frames = sorted(base)
    step = 3 if fast else 1
    for f in frames[::step]:
        img0 = C.read_frame(stem, f)
        ann = L.truth_corners(stem, f); tp = C.truth_corners(stem, f, "pins")
        outs = []
        for side in ("student", "fit"):
            img = img0.copy()
            poly(img, ann, GREEN, 2); poly(img, tp, CYAN, 1)
            if side == "student":
                q = {k: tuple(v) for k, v in base[f]["corners"].items()}; poly(img, q, RED, 2)
                err = base[f]["mae_pins"]; cap = ["loop-3 student lane (red)", f"f{f}   board err vs pins truth {err:.2f}"]
            else:
                r = fitd.get(f)
                d = dets.get(f, {})
                for b, v in d.get("arrows", {}).items():
                    cv2.drawMarker(img, (int(v["x"]), int(v["y"])), MAG, cv2.MARKER_TRIANGLE_UP, 12, 2, cv2.LINE_AA)
                if d.get("pins") and d["pins"].get("ok"):
                    for k, p in d["pins"]["bases"].items():
                        cv2.circle(img, (int(p[0]), int(p[1])), 3, ORANGE, -1, cv2.LINE_AA)
                if r:
                    q = {k: tuple(v) for k, v in r["corners"].items()}; poly(img, q, YEL, 2)
                    cap = [f"landmark fit: {variant} (yellow)", f"f{f}   board err vs pins truth {r['mae_pins']:.2f}   arrows {r['n_arrows']}  pins {r['n_pins']}" + ("  (pins carried)" if r.get("pins_carried") else "")]
                else:
                    cap = [f"landmark fit: {variant}", f"f{f}   no fit on this frame (no standing pins / too few arrows)"]
            if f in pos:
                x, y, rr = pos[f]; cv2.circle(img, (int(x), int(y)), int(max(rr, 6)), (255, 255, 255), 1, cv2.LINE_AA)
            tw = tp["top_right"][0] - tp["top_left"][0]; cx = 0.5 * (tp["top_left"][0] + tp["top_right"][0]); cy = tp["top_left"][1]
            inset(img, (cx, cy), max(int(tw * 1.1), 50), max(int(tw * 0.5), 25), z=4)
            phase = "bowler on the lane" if f < first_ball + 3 else ("ball rolling" if f <= fs[-1] else "after")
            caption(img, cap + [phase])
            outs.append(img)
        frame = panels(outs, f"{C.LABEL[stem]} - every frame: green = hand annotation, cyan = pins-based truth, red = student, yellow = landmark fit; magenta = detected arrows, orange = detected pin bases",
                       "the student's lane is the only input; pins and arrows are detected from it and the homography refitted, on every frame")
        for _ in range(1 if fast else (2 if f >= first_ball - 5 else 1)):
            yield frame


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=str(C.HERE / "review.mp4")); ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--fast", action="store_true"); ap.add_argument("--variant", default="foul+arrows+pins10")
    ap.add_argument("--script", default=str(C.HERE / "video_script.json"))
    a = ap.parse_args()
    vw = cv2.VideoWriter(a.out, cv2.VideoWriter_fourcc(*"avc1"), a.fps, (W, H))
    hold = (lambda frame, s: [vw.write(frame) for _ in range(int(s * a.fps))])
    script = json.loads(Path(a.script).read_text()) if Path(a.script).exists() else {}
    for key, secs in (("title", 7), ("question", 10), ("truth", 10)):
        blk = script.get(key)
        if blk:
            hold(card(blk["title"], blk["lines"], blk.get("sub")), 2 if a.fast else secs)
    # E1 stills: rack fits, arrows, full-frame landmarks
    for stem in C.STEMS:
        fp = C.frame_for(stem, "prehit")
        ims = [cv2.imread(str(C.OVERLAYS / f"e1_rack_{stem}_f{fp}.jpg")), cv2.imread(str(C.OVERLAYS / f"e1_arrows_rect_{stem}_f{fp}.jpg")), cv2.imread(str(C.OVERLAYS / f"e1_landmarks_{stem}_f{fp}.jpg"))]
        ims = [im for im in ims if im is not None]
        if ims:
            hold(panels(ims, f"E1 truth on {C.LABEL[stem]}, pre-hit frame f{fp}: ten-pin rack fit (green) | arrows on the rectified lane (green circles) | landmarks and the two quads (orange = hand, cyan = pins)",
                        "pins-based far end: centre = rack centre, width = 7-10 base spacing x 41.5/36; arrows are an independent check of both truths"), 2 if a.fast else 8)
    # tables
    for key in ("e1_table", "baselines_table", "e2_table", "e3_table", "e4_table"):
        blk = script.get(key)
        if blk:
            hold(table_card(blk["title"], blk.get("sub"), blk["header"], [tuple(r) if isinstance(r, list) and len(r) == 2 and isinstance(r[1], list) else r for r in blk["rows"]], blk["cols"], scale=blk.get("scale", 0.68), dy=blk.get("dy", 34), note=blk.get("note")), 3 if a.fast else blk.get("secs", 14))
    # tracked clips
    for stem in C.STEMS:
        p = C.RESULTS / f"e3_fit_loop3__{stem}.json"
        if not C.has_result(p):
            continue
        e3 = C.load(p)
        dets = {int(k): v for k, v in json.loads((PRED / f"lm_loop3_{stem}.json").read_text()).items()}
        p2 = PRED / f"lm2_loop3_{stem}.json"
        if p2.exists():
            for k, v in json.loads(p2.read_text()).items():
                if int(k) in dets:
                    dets[int(k)]["arrows"] = v["arrows"]
        variant = a.variant if a.variant in e3["variants"] else "corners+pins10"
        for fr in tracked_clip(stem, e3, dets, variant, fast=a.fast):
            vw.write(fr)
    # E2 stills
    for stem in C.STEMS:
        fp = C.frame_for(stem, "prehit"); occ = C.occluded_frames(stem); fo = occ[len(occ) // 2]
        ims = [cv2.imread(str(C.OVERLAYS / f"e2_loop3_{stem}_f{f}.jpg")) for f in (fo, fp)]
        ims = [im for im in ims if im is not None]
        if ims:
            hold(panels(ims, f"E2 detectors from the student's lane on {C.LABEL[stem]}: bowler on the lane (left) and pre-hit (right); green = truth landmarks, magenta = detected arrows, red = detected pin bases", None), 2 if a.fast else 6)
    for key, secs in (("e4", 9), ("conclusion", 16), ("engine", 12)):
        blk = script.get(key)
        if blk:
            hold(card(blk["title"], blk["lines"], blk.get("sub")), 2 if a.fast else secs)
    vw.release()
    print("wrote", a.out)


if __name__ == "__main__":
    main()
