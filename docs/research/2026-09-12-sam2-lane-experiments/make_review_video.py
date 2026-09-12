"""Compose the review video from results/*.json, overlays/*.jpg and the
per-frame masks saved in the scratchpad.

usage: make_review_video.py [--out review.mp4] [--fps 30]

Sections: title + legend, the three videos with their annotated lane and ball
path, one card + overlay triptych per method (single-frame, then multi-frame),
tracked clips through the whole throw for the per-frame methods, and a summary
table. Also writes results/summary.md for the README.
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

import gt
import lane_sam as L

W, H = 1920, 1080
BG = (24, 24, 28)
FG = (235, 235, 235)
DIM = (150, 150, 160)
SCRATCH = Path("/private/tmp/claude-502/-Users-toka-code-toms-gym/b090792b-0a7d-4249-9e93-4543c8a2bc1f/scratchpad")
STEMS = list(gt.VIDEOS)
LABEL = {"sample_input": "sample_input (1080p, handheld)", "20260112_121117": "Chardie (720p, handheld)",
         "tom_old": "tom_old (688p, tripod)"}

SINGLE = ["generic_box", "center3", "track_pre", "track_mid", "track_last", "track1_last", "track9_last", "even_last", "even3_last", "even_neg_last", "even_person_last",
          "track_box_last", "lane_neg_last", "person_neg_mid", "person_neg_last", "multimask_sam_last", "multimask_geo_last"]
MULTI = ["median3_span", "median5_span", "median9_span", "median5_late", "outer5_span", "outer9_span",
         "vote5_span", "vote9_span", "vote9_person_span", "vote5_even_span", "median5_span_snap", "vote9_span_snap"]
TRACKED = ["perframe_track", "perframe_person", "video_span", "video_rev"]


def text(img, s, x, y, scale=1.0, color=FG, thick=2, font=cv2.FONT_HERSHEY_SIMPLEX):
    cv2.putText(img, s, (int(x), int(y)), font, scale, color, thick, cv2.LINE_AA)


def canvas():
    c = np.zeros((H, W, 3), np.uint8)
    c[:] = BG
    return c


def card(title, lines, sub=None):
    c = canvas()
    text(c, title, 80, 120, 1.8, FG, 3)
    if sub:
        text(c, sub, 80, 175, 0.9, DIM, 2)
    y = 260
    for ln in lines:
        if isinstance(ln, tuple):
            s, col = ln
        else:
            s, col = ln, FG
        text(c, s, 80, y, 0.95, col, 2)
        y += 48
    return c


def table_card(title, sub, header, rows, cols, y0=230, scale=0.8, dy=40, note=None):
    """Card with a fixed-column table. cols = x positions; rows = list of cell lists."""
    c = canvas()
    text(c, title, 80, 120, 1.8, FG, 3)
    if sub:
        text(c, sub, 80, 175, 0.9, DIM, 2)
    y = y0
    for i, cell in enumerate(header):
        text(c, cell, cols[i], y, scale, DIM, 2)
    y += dy
    for r in rows:
        for i, cell in enumerate(r):
            if i < len(cols):
                text(c, str(cell), cols[i], y, scale, FG, 2)
        y += dy
    if note:
        y += 10
        for ln in note:
            text(c, ln, 80, y, 0.8, DIM, 2)
            y += 36
    return c


def fit_h(img, h):
    s = h / img.shape[0]
    return cv2.resize(img, (int(img.shape[1] * s), h), interpolation=cv2.INTER_AREA)


def triptych(images, header, footer=None):
    c = canvas()
    text(c, header, 40, 50, 1.0, FG, 2)
    avail_h = H - 130 if footer else H - 80
    ims = [fit_h(im, avail_h) for im in images]
    gap = 16
    total = sum(im.shape[1] for im in ims) + gap * (len(ims) - 1)
    if total > W - 40:
        s = (W - 40) / total
        ims = [cv2.resize(im, (int(im.shape[1] * s), int(im.shape[0] * s)), interpolation=cv2.INTER_AREA) for im in ims]
        total = sum(im.shape[1] for im in ims) + gap * (len(ims) - 1)
    x = (W - total) // 2
    for im in ims:
        h, w = im.shape[:2]
        c[70:70 + h, x:x + w] = im
        x += w + gap
    if footer:
        text(c, footer, 40, H - 30, 0.85, DIM, 2)
    return c


def load_rows():
    rows = {}
    for p in sorted((L.EXP / "results").glob("*.json")):
        if p.name.startswith("camera_") or p.name == "summary.json":
            continue
        for r in json.loads(p.read_text()):
            rows.setdefault(r["method"], {})[r["stem"]] = r
    return rows


def fmt(r, key="board_mae"):
    if r is None or not r.get("ok"):
        return "fail"
    v = r.get(key)
    return "-" if v is None else f"{v:.2f}"


def method_card(name, rows):
    rs = rows.get(name, {})
    desc = next((r["desc"] for r in rs.values() if r.get("desc")), "")
    header = ["video", "board MAE", "max", "<=1 board", "latency"]
    cols = [80, 620, 820, 980, 1180]
    trs = []
    for s_ in STEMS:
        r = rs.get(s_)
        lat = f"{r['latency_s']:.1f}s" if r else ""
        w1 = f"{r['within_1']:.0f}%" if r and r.get("ok") else ""
        trs.append([LABEL[s_], fmt(r), fmt(r, "board_max"), w1, lat])
    note = None
    if any(r and r.get("perframe_mae_mean") is not None for r in rs.values()):
        note = ["per frame, each frame scored against its own lane (mean / max / % of frames <= 2 boards):"]
        for s_ in STEMS:
            r = rs.get(s_)
            if r and r.get("perframe_mae_mean") is not None:
                note.append(f"   {LABEL[s_]:32s} {r['perframe_mae_mean']:.2f}  /  {r['perframe_mae_max']:.2f}  /  {r['perframe_within_2']:.0f}%")
        note.append("the board MAE row above is the last frame only")
    c = table_card(name, "prompt method", header, trs, cols, y0=300, scale=0.9, dy=46, note=note)
    text(c, desc, 80, 235, 0.85, DIM, 2)
    return c


def overlays_for(name):
    ims = []
    for s in STEMS:
        p = L.EXP / "overlays" / f"{name}_{s}.jpg"
        if p.exists():
            ims.append(cv2.imread(str(p)))
    return ims


def intro_frames():
    ims = []
    for s in STEMS:
        fs, pos = L.trajectory(s)
        f = max(0, fs[0] - 5)
        img = cv2.imread(str(gt.frame_path(s, f)))
        t = {k: (int(round(v[0])), int(round(v[1]))) for k, v in L.truth_corners(s, f).items()}
        poly = np.array([t["top_left"], t["top_right"], t["bottom_right"], t["bottom_left"]], np.int32)
        cv2.polylines(img, [poly], True, (0, 220, 0), 2, cv2.LINE_AA)
        for (x, y) in L.ball_points_on(s, f):
            cv2.circle(img, (int(x), int(y)), 4, (0, 255, 255), -1, cv2.LINE_AA)
        cam = L.camera(s)
        cap = [f"{LABEL[s]}  f{f}", f"{len(pos)} annotated ball frames, camera shift up to {cam['motion_summary']['max_shift_px']} px"]
        y = img.shape[0] - 50
        for ln in cap:
            text(img, ln, 12, y, 0.75, (0, 0, 0), 4)
            text(img, ln, 12, y, 0.75, FG, 2)
            y += 30
        ims.append(img)
    return ims


def tracked_clip_frames(stem, methods, rows, slow=2):
    """Yield composed frames playing the throw with each method's mask."""
    fs, pos = L.trajectory_all(stem)
    start, end = max(0, fs[0] - 5), fs[-1]
    data = {}
    for m in methods:
        mp = SCRATCH / f"masks_{m}_{stem}.npz"
        lp = SCRATCH / f"lines_{m}_{stem}.json"
        if not mp.exists():
            continue
        z = np.load(mp)
        lines = json.loads(lp.read_text()) if lp.exists() else {}
        per = {pf["frame"]: pf.get("board_mae") for pf in rows.get(m, {}).get(stem, {}).get("per_frame", [])}
        data[m] = {"masks": z, "keys": sorted(int(k) for k in z.files), "lines": lines, "per": per}
    if not data:
        return
    shape = cv2.imread(str(gt.frame_path(stem, start))).shape[:2]
    for f in range(start, end + 1):
        panels = []
        for m in methods:
            if m not in data:
                continue
            d = data[m]
            img = cv2.imread(str(gt.frame_path(stem, f)))
            avail = [k for k in d["keys"] if k <= f]
            if avail:
                k = avail[-1]
                mask = np.unpackbits(d["masks"][str(k)])[: shape[0] * shape[1]].reshape(shape).astype(bool)
                img[mask] = (0.45 * img[mask] + np.array([150, 60, 0])).clip(0, 255).astype(np.uint8)
                ln = d["lines"].get(str(k))
                yt, yb = L.gt_y(stem, f)
                if ln:
                    c = L.lines_to_corners(tuple(ln[0]), tuple(ln[1]), yt, yb)
                    poly = np.array([c["top_left"], c["top_right"], c["bottom_right"], c["bottom_left"]], np.int32)
                    cv2.polylines(img, [poly], True, (0, 0, 255), 2, cv2.LINE_AA)
            t = {q: (int(round(v[0])), int(round(v[1]))) for q, v in L.truth_corners(stem, f).items()}
            poly = np.array([t["top_left"], t["top_right"], t["bottom_right"], t["bottom_left"]], np.int32)
            cv2.polylines(img, [poly], True, (0, 220, 0), 2, cv2.LINE_AA)
            if f in pos:
                x, y, r = pos[f]
                cv2.circle(img, (int(x), int(y)), int(max(r, 6)), (0, 255, 255), 2, cv2.LINE_AA)
            err = d["per"].get(f)
            for i, ln_ in enumerate([m, f"f{f}" + (f"  board err {err:.2f}" if err is not None else "")]):
                y = img.shape[0] - 46 + 30 * i
                text(img, ln_, 12, y, 0.75, (0, 0, 0), 4)
                text(img, ln_, 12, y, 0.75, FG, 2)
            panels.append(img)
        frame = triptych(panels, f"{LABEL[stem]} - lane tracked through the throw (green = annotated lane, red = SAM)",
                         "playing at half speed; masks from every 2nd frame for perframe_*, every frame for video_span")
        for _ in range(slow):
            yield frame


def summary_card(title, rows, names):
    header = ["method", "sample_input", "Chardie", "tom_old", "per-frame mean (s / C / t)"]
    cols = [80, 560, 800, 1000, 1240]
    trs = []
    for n in names:
        rs = rows.get(n)
        if not rs:
            continue
        pf = [rs.get(s_, {}).get("perframe_mae_mean") for s_ in STEMS]
        pfs = "  /  ".join(f"{v:.2f}" if v is not None else "-" for v in pf) if any(v is not None for v in pf) else ""
        trs.append([n] + [fmt(rs.get(s_)) for s_ in STEMS] + [pfs])
    return table_card(title, "board MAE, lower is better; fail = no usable mask", header, trs, cols, y0=230, scale=0.75, dy=36)


def write_summary_md(rows):
    lines = ["| method | description | sample_input | Chardie | tom_old | per-frame mean (s / C / t) |", "|---|---|---|---|---|---|"]
    for n in SINGLE + MULTI + TRACKED:
        rs = rows.get(n)
        if not rs:
            continue
        desc = next((r["desc"] for r in rs.values() if r.get("desc")), "")
        cells = [fmt(rs.get(s)) for s in STEMS]
        pf = [rs.get(s, {}).get("perframe_mae_mean") for s in STEMS]
        pfs = " / ".join(f"{v:.2f}" if v is not None else "-" for v in pf) if any(v is not None for v in pf) else ""
        lines.append(f"| `{n}` | {desc} | {cells[0]} | {cells[1]} | {cells[2]} | {pfs} |")
    (L.EXP / "results" / "summary.md").write_text("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(L.EXP / "review.mp4"))
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--hold", type=float, default=3.0)
    a = ap.parse_args()
    rows = load_rows()
    write_summary_md(rows)
    vw = cv2.VideoWriter(a.out, cv2.VideoWriter_fourcc(*"avc1"), a.fps, (W, H))
    assert vw.isOpened()

    def hold(frame, sec):
        for _ in range(int(sec * a.fps)):
            vw.write(frame)

    hold(card("SAM 2 lane detection experiments", [
        "Can SAM 2.1 find the bowling lane accurately enough to read boards?",
        "Three annotated videos, board error measured through the 4-corner homography.",
        "",
        ("Legend:", DIM),
        "  green outline  = annotated lane (per frame; the camera moves on two videos)",
        "  red outline    = lane fitted from the SAM mask",
        "  blue tint      = SAM mask",
        "  yellow dot     = positive prompt point (from the ball path)",
        "  magenta X      = negative prompt point",
        "  cyan box       = box prompt",
        "  inset, top-left = pin end at 3x (one board is 1-2 px there)",
        "",
        "Board MAE = mean |board error| over every annotated ball position.",
    ], "2026-09-12, CPU only, sam2.1_b"), a.hold + 3)

    hold(triptych(intro_frames(), "The three videos: annotated lane (green) and ball path (yellow) on the pre-release frame",
                  "Ball positions come from the annotation and stand in for a ball detector."), a.hold + 2)

    hold(card("Part 1: single-frame prompts", [
        "One SAM call on one frame. What the prompt is, and which frame, is the whole game.",
        "",
        "generic_box / center3 : what the Feb-2026 engine code did (no scene knowledge)",
        "track_*               : positive points along the ball path (pre / mid / last frame)",
        "track_box, lane_neg   : path points plus a box, or plus negatives outside the first mask",
        "person_neg            : path points plus negatives on YOLO-detected people",
        "multimask_*           : SAM's three candidate masks, picked by SAM score or by geometry",
    ]), a.hold)
    for n in SINGLE:
        if n not in rows:
            continue
        hold(method_card(n, rows), a.hold)
        ims = overlays_for(n)
        if ims:
            hold(triptych(ims, n), a.hold + 1)

    hold(card("Part 2: combining several frames", [
        "Path-point prompts on k frames spread over the throw, each result warped through",
        "the camera motion into the last frame, then combined:",
        "",
        "median : median of the fitted edge lines",
        "outer  : outermost left / right edge (occlusion by the bowler only ever narrows the mask)",
        "vote   : pixel-wise majority vote of the warped masks, then one edge fit",
        "snap   : move the final lines onto the strongest gradient within +-6 px",
    ]), a.hold)
    for n in MULTI:
        if n not in rows:
            continue
        hold(method_card(n, rows), a.hold)
        ims = overlays_for(n)
        if ims:
            hold(triptych(ims, n), a.hold + 1)

    hold(card("Part 3: tracking the lane through the throw", [
        "Two of the three videos are handheld (up to 36 px of drift), so production needs a lane per frame.",
        "",
        "perframe_track  : SAM with path points on every 2nd ball frame, independently",
        "perframe_person : same, plus negatives on detected people",
        "video_span      : SAM 2 video mode, prompted once before release and propagated",
        "",
        "Each frame is scored against the annotated lane for that frame.",
    ]), a.hold)
    for n in TRACKED:
        if n in rows:
            hold(method_card(n, rows), a.hold)
    for s in STEMS:
        for fr in tracked_clip_frames(s, TRACKED, rows):
            vw.write(fr)

    hold(summary_card("Summary 1/3: single-frame prompts", rows, SINGLE + ["track_last_tiny", "even_last_tiny", "track_last_large", "even_last_large"]), a.hold + 5)
    hold(summary_card("Summary 2/3: multi-frame combinations", rows, MULTI), a.hold + 4)
    hold(summary_card("Summary 3/3: tracking through the throw", rows, TRACKED), a.hold + 4)
    vw.release()
    print("wrote", a.out)


if __name__ == "__main__":
    main()
