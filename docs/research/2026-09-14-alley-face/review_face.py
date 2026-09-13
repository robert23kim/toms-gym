"""Compose review.mp4 (1920x1080, 30 fps, H.264 via OpenCV avc1, no ffmpeg) - about one minute,
one message: the question and the answer on one card, one clip of the face being found and aligned
(E3 lanes -> E4 refit on the same frames, tracked through the throw), one table card, one
recommendation card. usage: review_face.py [--fast] [--stem tom_old]"""
import argparse
import gzip
import json

import cv2
import numpy as np

import af

LM = af.LM
W, H = 1920, 1080
BG = (24, 24, 28); FG = (235, 235, 235); DIM = (150, 150, 160)
GREEN = (0, 220, 0); YEL = (0, 255, 255); ORANGE = (0, 165, 255); MAG = (255, 0, 200); CYAN = (255, 255, 0); RED = (0, 0, 255)


def text(img, s, x, y, scale=1.0, color=FG, thick=2, max_w=None):
    max_w = (img.shape[1] - int(x) - 40) if max_w is None else max_w
    (tw, _), _ = cv2.getTextSize(s, cv2.FONT_HERSHEY_SIMPLEX, scale, thick)
    if tw > max_w and tw > 0:
        scale = scale * max_w / tw
    cv2.putText(img, s, (int(x), int(y)), cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick, cv2.LINE_AA)


def canvas():
    c = np.zeros((H, W, 3), np.uint8); c[:] = BG; return c


def card(title, lines, sub=None, y0=250, dy=50, scale=0.95):
    c = canvas(); text(c, title, 80, 120, 1.5, FG, 3)
    if sub:
        text(c, sub, 80, 175, 0.85, DIM, 2)
    y = y0
    for ln in lines:
        if isinstance(ln, (tuple, list)) and len(ln) == 2 and isinstance(ln[1], (tuple, list)):
            s, col = ln[0], tuple(int(v) for v in ln[1])
        else:
            s, col = ln, FG
        text(c, str(s), 80, y, scale, col, 2); y += dy
    return c


def table_card(title, sub, header, rows, cols, y0=240, scale=0.72, dy=40, note=None):
    c = canvas(); text(c, title, 80, 120, 1.4, FG, 3)
    if sub:
        text(c, sub, 80, 175, 0.85, DIM, 2)
    y = y0
    for i, cell in enumerate(header):
        text(c, cell, cols[i], y, scale, DIM, 2, max_w=(cols[i + 1] - cols[i] - 10) if i + 1 < len(cols) else None)
    y += dy
    for r in rows:
        col = FG
        if isinstance(r, (tuple, list)) and len(r) == 2 and isinstance(r[1], (tuple, list)) and isinstance(r[0], (tuple, list)):
            r, col = r[0], tuple(int(v) for v in r[1])
        for i, cell in enumerate(r):
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
    c = canvas(); text(c, header, 40, 50, 0.9, FG, 2)
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


def lane_poly(img, Hm, color, th=2):
    q = af.to_image(np.array(Hm), [(0, 0), (af.W_IN, 0), (af.W_IN, LM.HEAD_IN), (0, LM.HEAD_IN)]).astype(np.int32)
    cv2.polylines(img, [q.reshape(-1, 1, 2)], True, color, th, cv2.LINE_AA)


def inset(img, centre, half_w, half_h, z=4):
    h, w = img.shape[:2]
    x1, x2 = int(max(0, centre[0] - half_w)), int(min(w, centre[0] + half_w)); y1, y2 = int(max(0, centre[1] - half_h)), int(min(h, centre[1] + half_h))
    crop = img[y1:y2, x1:x2]
    if crop.size == 0:
        return
    crop = cv2.resize(crop, None, fx=z, fy=z, interpolation=cv2.INTER_NEAREST)
    ch, cw = crop.shape[:2]; cw = min(cw, w - 20); crop = crop[:, :cw]
    img[10:10 + ch, 10:10 + cw] = crop
    cv2.rectangle(img, (10, 10), (10 + cw, 10 + ch), (255, 255, 255), 2)
    text(img, f"pin end x{z}", 16, 10 + ch - 8, 0.6, (255, 255, 255), 2)


def fmt(v, nd=2):
    return "-" if v is None else (f"{v:.{nd}f}" if isinstance(v, (int, float)) and not isinstance(v, bool) else str(v))


def face_clip(stem, fast=False, frames=None):
    """Left: the candidate pool + every lane E3 found (top score yellow, others orange, truth green);
    right: the aligned face (E4 refit) with the refined landmarks. Tracked through the throw."""
    rows3 = {r["frame"]: r for r in af.load(af.PRED / f"face_rows_{stem}.json")["arrows+dots+rack+gutters"]}
    rows4 = {r["frame"]: r for r in af.load(af.PRED / f"align_rows_{stem}.json")} if (af.PRED / f"align_rows_{stem}.json").exists() else {}
    with gzip.open(af.PRED / f"face_{stem}.json.gz", "rt") as fh:
        faces = json.load(fh)
    with gzip.open(af.PRED / f"cand_{stem}.json.gz", "rt") as fh:
        cands = json.load(fh)
    al = {}
    if (af.PRED / f"align_{stem}.json.gz").exists():
        with gzip.open(af.PRED / f"align_{stem}.json.gz", "rt") as fh:
            al = json.load(fh)
    fs, pos = af.L.trajectory_all(stem)
    first_ball = af.L.trajectory(stem)[0][0]; ph = af.pin_hit(stem)
    frames = frames or [f for f in sorted(rows3) if first_ball - 12 <= f <= ph + 12]
    step = 3 if fast else 1
    for f in frames[::step]:
        img0 = af.read_frame(stem, f)
        tq = af.truth_corners(stem, f, "pins")
        outs = []
        # left: pool + lanes
        img = img0.copy()
        c = cands.get(str(f), {})
        for m in c.get("marks", [])[:2000]:
            if not m.get("weak"):
                cv2.circle(img, (int(m["x"]), int(m["y"])), 2, RED, 1, cv2.LINE_AA)
        for r in c.get("racks", []):
            cv2.rectangle(img, (int(r["cx"] - r["w"] / 2), int(r["top"])), (int(r["cx"] + r["w"] / 2), int(r["bot"])), MAG, 1)
        lanes = faces.get(str(f), {}).get("arrows+dots+rack+gutters", {}).get("lanes", [])
        for i, l in enumerate(lanes[:6]):
            lane_poly(img, l["H"], YEL if i == 0 else ORANGE, 2 if i == 0 else 1)
        r3 = rows3.get(f, {})
        cap = [f"E3 find: {len(lanes)} lane(s) from the candidate pool", f"f{f}   right lane " + ("found, rank %s" % r3.get("right_rank") if r3.get("right_found") else "not found") + (f"   board err vs pins {r3['mae']['pins']:.2f}" if r3.get("mae") else "")]
        caption(img, cap)
        outs.append(img)
        # right: aligned
        img = img0.copy()
        p = np.array([tq["top_left"], tq["top_right"], tq["bottom_right"], tq["bottom_left"]], np.int32); cv2.polylines(img, [p.reshape(-1, 1, 2)], True, GREEN, 1, cv2.LINE_AA)
        r4 = rows4.get(f); a = al.get(str(f))
        if r4 and r4.get("ok") and r4["fits"].get("refit", {}).get("ok"):
            fit = r4["fits"]["refit"]
            if "H" in fit:
                lane_poly(img, fit["H"], YEL, 2)
            if a:
                for cls, rr in a["rows"].items():
                    for n, (x, y) in rr.items():
                        cv2.circle(img, (int(x), int(y)), 3, MAG, 1, cv2.LINE_AA)
                if a.get("pins"):
                    for n, (x, y) in a["pins"].items():
                        cv2.circle(img, (int(x), int(y)), 2, ORANGE, -1, cv2.LINE_AA)
                for n, (x, y) in (a.get("corners") or {}).items():
                    cv2.drawMarker(img, (int(x), int(y)), CYAN, cv2.MARKER_CROSS, 12, 2, cv2.LINE_AA)
            cap = ["E4 align: every landmark refined, one weighted fit", f"f{f}   board err vs pins {fit['mae']['pins']:.2f} (E3 {r3['mae']['pins']:.2f})   near corners {fit['near_err_px']['bottom_left']:.0f}/{fit['near_err_px']['bottom_right']:.0f} px" if fit.get("mae") else f"f{f}"]
        else:
            cap = ["E4 align", f"f{f}   no aligned lane on this frame"]
        if f in pos:
            x, y, rr_ = pos[f]; cv2.circle(img, (int(x), int(y)), int(max(rr_, 6)), (255, 255, 255), 1, cv2.LINE_AA)
        tw = tq["top_right"][0] - tq["top_left"][0]; cx = 0.5 * (tq["top_left"][0] + tq["top_right"][0]); cy = tq["top_left"][1]
        inset(img, (cx, cy), max(int(tw * 1.1), 50), max(int(tw * 0.5), 25), z=4)
        phase = "bowler on the lane" if f < first_ball + 3 else ("ball rolling" if f <= ph else "pins falling")
        caption(img, cap + [phase])
        outs.append(img)
        fr = panels(outs, f"{af.LABEL[stem]} - left: dark marks (red), rack blobs (magenta), lanes found (yellow = top score); right: the aligned face (yellow) vs the pins truth (green)",
                    "no ball path, no trained mask, no prompt: the constellation is found from the candidate pool and aligned on every frame")
        for _ in range(1 if fast else 3):
            yield fr


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=str(af.HERE / "review.mp4")); ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--fast", action="store_true"); ap.add_argument("--stem", default="tom_old"); ap.add_argument("--script", default=str(af.HERE / "video_script.json"))
    a = ap.parse_args()
    script = json.loads(open(a.script).read())
    vw = cv2.VideoWriter(a.out, cv2.VideoWriter_fourcc(*"avc1"), a.fps, (W, H))
    hold = lambda frame, s: [vw.write(frame) for _ in range(int(s * a.fps))]  # noqa: E731
    blk = script["answer"]; hold(card(blk["title"], blk["lines"], blk.get("sub"), scale=blk.get("scale", 0.9), dy=blk.get("dy", 48)), 2 if a.fast else blk.get("secs", 14))
    clip = script.get("clip", {})
    frames = clip.get("frames")
    n = 0
    for fr in face_clip(a.stem, fast=a.fast, frames=frames):
        vw.write(fr); n += 1
        if not a.fast and clip.get("max_frames") and n >= clip["max_frames"]:
            break
    blk = script["table"]; hold(table_card(blk["title"], blk.get("sub"), blk["header"], [tuple(r) if isinstance(r, list) and len(r) == 2 and isinstance(r[1], list) else r for r in blk["rows"]], blk["cols"], scale=blk.get("scale", 0.7), dy=blk.get("dy", 38), note=blk.get("note")), 2 if a.fast else blk.get("secs", 16))
    blk = script["recommend"]; hold(card(blk["title"], blk["lines"], blk.get("sub"), scale=blk.get("scale", 0.9), dy=blk.get("dy", 48)), 2 if a.fast else blk.get("secs", 12))
    vw.release()
    print("wrote", a.out, "clip frames", n)


if __name__ == "__main__":
    main()
