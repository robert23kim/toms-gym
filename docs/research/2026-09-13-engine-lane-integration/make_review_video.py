"""review.mp4: the old engine and the new engine side by side on the three
annotated videos, then the numbers. 1920x1080, 30 fps, H.264 via OpenCV.

Per video: the two engines' own debug renders (camera view + bird's-eye panel)
scaled side by side, a 3x pin-end inset per engine from the source frame with
the old static lane (cyan), the new per-frame lane (orange) and the truth
(green), and a live readout of the board the annotated ball maps to under each
lane. Then a results card from results/eval_*.json.
usage: make_review_video.py <after_config> [--before before] [--out review.mp4] [--fast]
"""
import argparse
import json
import re
from pathlib import Path

import cv2
import numpy as np

import common as C

L = C.L
W, H = 1920, 1080
BG = (24, 24, 28)
FG = (235, 235, 235)
DIM = (150, 150, 160)
GREEN = (0, 220, 0)
CYAN = (255, 220, 0)
ORANGE = (0, 140, 255)
YEL = (0, 255, 255)


def text(img, s, x, y, scale=1.0, color=FG, thick=2, max_w=None):
    max_w = (img.shape[1] - int(x) - 40) if max_w is None else max_w
    (tw, _), _ = cv2.getTextSize(s, cv2.FONT_HERSHEY_SIMPLEX, scale, thick)
    if tw > max_w and tw > 0:
        scale = scale * max_w / tw
    cv2.putText(img, s, (int(x), int(y)), cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick, cv2.LINE_AA)


def canvas():
    c = np.zeros((H, W, 3), np.uint8)
    c[:] = BG
    return c


def card(title, lines, sub=None, y0=260, dy=48, scale=0.95):
    c = canvas()
    text(c, title, 80, 120, 1.6, FG, 3)
    if sub:
        text(c, sub, 80, 175, 0.9, DIM, 2)
    y = y0
    for ln in lines:
        s, col = ln if isinstance(ln, tuple) else (ln, FG)
        text(c, s, 80, y, scale, col, 2)
        y += dy
    return c


def table_card(title, sub, header, rows, cols, y0=250, scale=0.8, dy=44, note=None):
    c = canvas()
    text(c, title, 80, 120, 1.6, FG, 3)
    if sub:
        text(c, sub, 80, 175, 0.9, DIM, 2)
    y = y0
    for i, cell in enumerate(header):
        text(c, cell, cols[i], y, scale, DIM, 2)
    y += dy
    for r in rows:
        col = FG
        if isinstance(r, tuple):
            r, col = r
        for i, cell in enumerate(r):
            text(c, str(cell), cols[i], y, scale, col, 2)
        y += dy
    if note:
        y += 12
        for ln in note:
            text(c, ln, 80, y, 0.75, DIM, 2)
            y += 34
    return c


def fit_h(img, h):
    s = h / img.shape[0]
    return cv2.resize(img, (max(1, int(img.shape[1] * s)), h), interpolation=cv2.INTER_AREA)


def static_lane(config, stem):
    txt = (C.RUNS / config / f"{stem}.log").read_text()
    m = re.search(r"lane_edges=(\{.*\})", txt)
    return json.loads(m.group(1)) if m else None


def quad_poly(c):
    return np.array([c["top_left"], c["top_right"], c["bottom_right"], c["bottom_left"]], np.int32)


def board_under(corners, pt):
    b, _ = C.gt.board_from_corners(corners, [pt])
    return float(b[0])


def inset(img, truth, old_c, new_c, ball, zoom=3):
    """3x crop around the truth top edge with the three lanes and the ball."""
    out = img.copy()
    cv2.polylines(out, [quad_poly(truth)], True, GREEN, 2, cv2.LINE_AA)
    if old_c is not None:
        cv2.polylines(out, [quad_poly(old_c)], True, CYAN, 2, cv2.LINE_AA)
    if new_c is not None:
        cv2.polylines(out, [quad_poly(new_c)], True, ORANGE, 2, cv2.LINE_AA)   # on top: it often sits on the truth
    if ball is not None:
        cv2.circle(out, (int(ball[0]), int(ball[1])), max(4, int(ball[2])), YEL, 2, cv2.LINE_AA)
    tw = truth["top_right"][0] - truth["top_left"][0]
    cx = (truth["top_left"][0] + truth["top_right"][0]) / 2
    cy = (truth["top_left"][1] + truth["top_right"][1]) / 2
    half_w = max(int(tw * 1.6), 70)
    half_h = max(int(tw * 1.0), 45)
    h, w = out.shape[:2]
    x1, x2 = int(max(0, cx - half_w)), int(min(w, cx + half_w))
    y1, y2 = int(max(0, cy - half_h)), int(min(h, cy + half_h * 1.6))
    crop = out[y1:y2, x1:x2]
    return cv2.resize(crop, None, fx=zoom, fy=zoom, interpolation=cv2.INTER_CUBIC)


def video_segment(stem, before, after, writer, slow=2, fast=False):
    cap_b = cv2.VideoCapture(str(C.RUNS / before / f"{stem}.mp4"))
    cap_a = cv2.VideoCapture(str(C.RUNS / after / f"{stem}.mp4"))
    calib = json.loads((C.RUNS / after / f"{stem}_lane_calibration.json").read_text())
    old = static_lane(before, stem)
    fs, pos = L.trajectory(stem)
    ph = L.pin_hit_frame(stem)
    start, end = max(0, fs[0] - 8), min(int(cap_b.get(7)) - 1, ph + 12)
    ev_b = json.loads((C.RESULTS / f"eval_{before}__{stem}.json").read_text())
    ev_a = json.loads((C.RESULTS / f"eval_{after}__{stem}.json").read_text())
    per_b = {r["frame"]: r for r in ev_b["per_frame"]}
    per_a = {r["frame"]: r for r in ev_a["per_frame"]}
    cap_b.set(1, start)
    cap_a.set(1, start)
    panel_h = 880
    for f in range(start, end + 1):
        okb, fb = cap_b.read()
        oka, fa = cap_a.read()
        if not (okb and oka):
            break
        if fast and f % 3:
            continue
        src = C.L.gt.frame_path(stem, f)
        img = cv2.imread(str(src))
        truth = C.truth_corners(stem, f, "pins")
        old_c = C.polyline_corners_at_truth_rows(stem, f, old["left_edge_points"], old["right_edge_points"]) if old and old.get("left_edge_points") else (C.corners_at_truth_rows(stem, f, {k: tuple(old[k]) for k in C.KEYS}) if old else None)
        new_c = per_a.get(f, {}).get("corners")
        new_c = {k: tuple(v) for k, v in new_c.items()} if new_c else None
        ball = pos.get(f)
        ball_here = None
        if ball is not None:
            ball_here = (ball[0], ball[1], ball[2])
        c = canvas()
        text(c, f"{C.LABEL[stem]}   frame {f}   (half speed)", 40, 44, 0.9, FG, 2)
        pb = fit_h(fb, panel_h)
        pa = fit_h(fa, panel_h)
        x = 40
        c[100:100 + panel_h, x:x + pb.shape[1]] = pb
        text(c, "BEFORE  deployed engine: one static classical lane", x, 92, 0.7, CYAN, 2)
        x2 = x + pb.shape[1] + 24
        c[100:100 + panel_h, x2:x2 + pa.shape[1]] = pa
        text(c, f"AFTER  SAM lane calibration ({calib['method']}), carried per frame", x2, 92, 0.7, ORANGE, 2)
        # insets + readout in the right column
        col_x = x2 + pa.shape[1] + 24
        col_w = W - col_x - 30
        ins = inset(img, truth, old_c, new_c, ball_here)
        ins = cv2.resize(ins, (col_w, int(ins.shape[0] * col_w / ins.shape[1])), interpolation=cv2.INTER_AREA)
        ih = min(ins.shape[0], 520)
        c[100:100 + ih, col_x:col_x + col_w] = ins[:ih]
        text(c, "pin end x3: truth green, before cyan, after orange", col_x, 92, 0.6, DIM, 2)
        y = 100 + ih + 50
        if ball_here is not None and f <= ph:
            bt = board_under(truth, ball_here[:2])
            bo = board_under(old_c, ball_here[:2]) if old_c else None
            bn = board_under(new_c, ball_here[:2]) if new_c else None
            text(c, "board of the annotated ball on this frame", col_x, y, 0.65, DIM, 2)
            y += 44
            text(c, f"truth   {bt:5.1f}", col_x, y, 0.9, GREEN, 2)
            y += 44
            text(c, f"before  {bo:5.1f}" if bo is not None else "before   -", col_x, y, 0.9, CYAN, 2)
            y += 44
            text(c, f"after   {bn:5.1f}" if bn is not None else "after    -", col_x, y, 0.9, ORANGE, 2)
            y += 60
        mb = per_b.get(f, {}).get("mae_pins")
        ma = per_a.get(f, {}).get("mae_pins")
        text(c, "board MAE of the whole path, this frame's lane", col_x, y, 0.65, DIM, 2)
        y += 44
        text(c, f"before  {mb:.2f}" if mb is not None else "before   -", col_x, y, 0.9, CYAN, 2)
        y += 44
        text(c, f"after   {ma:.2f}" if ma is not None else "after    -", col_x, y, 0.9, ORANGE, 2)
        for _ in range(slow):
            writer.write(c)
    cap_b.release()
    cap_a.release()


def results_rows(before, after):
    rows = []
    for stem in C.STEMS:
        b = json.loads((C.RESULTS / f"eval_{before}__{stem}.json").read_text())
        a = json.loads((C.RESULTS / f"eval_{after}__{stem}.json").read_text())
        rows.append([C.SHORT[stem],
                     f"{b['throw_pins']['median']}", f"{a['throw_pins']['median']}",
                     f"{b['throw_pins']['within_2']}%", f"{a['throw_pins']['within_2']}%",
                     f"{b['final_board']} / {a['final_board']} / {a['truth_final_board']['pins']}",
                     a["method"]])
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("after")
    ap.add_argument("--before", default="before")
    ap.add_argument("--out", default=str(C.HERE / "review.mp4"))
    ap.add_argument("--fast", action="store_true")
    a = ap.parse_args()
    script = json.loads((C.HERE / "video_script.json").read_text())
    writer = cv2.VideoWriter(a.out, cv2.VideoWriter_fourcc(*"avc1"), 30, (W, H))
    if not writer.isOpened():
        writer = cv2.VideoWriter(a.out, cv2.VideoWriter_fourcc(*"mp4v"), 30, (W, H))

    def hold(img, sec):
        for _ in range(int(sec * 30)):
            writer.write(img)

    t = script["title"]
    hold(card(t["title"], t["lines"], t.get("sub")), 6 if not a.fast else 1)
    m = script["method"]
    hold(card(m["title"], m["lines"], m.get("sub"), scale=0.85, dy=44), 8 if not a.fast else 1)
    for stem in C.STEMS:
        video_segment(stem, a.before, a.after, writer, slow=2, fast=a.fast)
    r = script["results"]
    hold(table_card(r["title"], r["sub"], ["video", "MAE before", "MAE after", "<=2 bd before", "<=2 bd after", "final board before / after / truth", "method"],
                    results_rows(a.before, a.after), [80, 380, 560, 740, 940, 1140, 1560], note=r.get("note")), 10 if not a.fast else 1)
    e = script["end"]
    hold(card(e["title"], e["lines"], e.get("sub"), scale=0.85, dy=44), 7 if not a.fast else 1)
    writer.release()
    print("wrote", a.out)


if __name__ == "__main__":
    main()
