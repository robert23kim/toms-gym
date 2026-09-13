"""Compose review.mp4 from results/*.json, overlays/ and the per-frame
predictions in $LANE_SCRATCH/pred. 1920x1080, 30 fps, H.264 via OpenCV (no ffmpeg).

Sections: title, data, method, results table, one tracked clip per annotated
video (truth green / student seg red / student pose magenta / SAM 2 blue),
pin-end stills, the unlabeled videos, latency, conclusion.
usage: make_review_video.py [--out review.mp4] [--seg seg640] [--pose pose640] [--fast]
"""
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
GREEN = (0, 220, 0); RED = (0, 0, 255); MAG = (255, 0, 200); BLUE = (255, 160, 0); YEL = (0, 255, 255)


def text(img, s, x, y, scale=1.0, color=FG, thick=2, max_w=None):
    """Draw s; shrink the scale so the line fits within max_w px (default: to the right edge minus a margin)."""
    max_w = (img.shape[1] - int(x) - 40) if max_w is None else max_w
    (tw, _), _ = cv2.getTextSize(s, cv2.FONT_HERSHEY_SIMPLEX, scale, thick)
    if tw > max_w and tw > 0:
        scale = scale * max_w / tw
    cv2.putText(img, s, (int(x), int(y)), cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick, cv2.LINE_AA)


def canvas():
    c = np.zeros((H, W, 3), np.uint8); c[:] = BG; return c


def card(title, lines, sub=None, y0=260, dy=48, scale=0.95):
    c = canvas(); text(c, title, 80, 120, 1.7, FG, 3)
    if sub:
        text(c, sub, 80, 175, 0.9, DIM, 2)
    y = y0
    for ln in lines:
        s, col = ln if isinstance(ln, tuple) else (ln, FG)
        text(c, s, 80, y, scale, col, 2); y += dy
    return c


def table_card(title, sub, header, rows, cols, y0=240, scale=0.78, dy=40, note=None):
    c = canvas(); text(c, title, 80, 120, 1.7, FG, 3)
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
            if i < len(cols):
                text(c, str(cell), cols[i], y, scale, col, 2)
        y += dy
    if note:
        y += 10
        for ln in note:
            text(c, ln, 80, y, 0.75, DIM, 2); y += 34
    return c


def fit_h(img, h):
    s = h / img.shape[0]
    return cv2.resize(img, (int(img.shape[1] * s), h), interpolation=cv2.INTER_AREA)


def panels(images, header, footer=None):
    c = canvas(); text(c, header, 40, 50, 1.0, FG, 2)
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
        h, w = im.shape[:2]; c[70:70 + h, x:x + w] = im; x += w + gap
    if footer:
        text(c, footer, 40, H - 30, 0.85, DIM, 2)
    return c


def load_json(p):
    return json.loads(Path(p).read_text()) if Path(p).exists() else None


class Pred:
    """Per-frame lines (+ masks) of one method on one video."""

    def __init__(self, name, stem, per_rows=None):
        self.lines = load_json(PRED / f"lines_{name}_{stem}.json") or {}
        mp = PRED / f"masks_{name}_{stem}.npz"
        self.z = np.load(mp) if mp.exists() else None
        self.per = {r["frame"]: r.get("board_mae") for r in (per_rows or [])}
        self.keys = sorted(int(k) for k in self.lines)

    def at(self, f, exact=True):
        if exact:
            return self.lines.get(str(f))
        avail = [k for k in self.keys if k <= f]
        return self.lines[str(avail[-1])] if avail else None

    def mask(self, f, shape):
        if self.z is None or str(f) not in self.z.files:
            return None
        return np.unpackbits(self.z[str(f)])[: shape[0] * shape[1]].reshape(shape).astype(bool)


def draw_lane(img, ln, y_top, y_bot, color, th=2):
    if not ln:
        return
    left = tuple(ln["left"]) if "left" in ln else tuple(ln[0]); right = tuple(ln["right"]) if "right" in ln else tuple(ln[1])
    c = L.lines_to_corners(left, right, y_top, y_bot)
    poly = np.array([c["top_left"], c["top_right"], c["bottom_right"], c["bottom_left"]], np.int32)
    cv2.polylines(img, [poly], True, color, th, cv2.LINE_AA)


def caption(img, lines):
    for i, s in enumerate(lines):
        y = img.shape[0] - 16 - 30 * (len(lines) - 1 - i)
        text(img, s, 12, y, 0.75, (0, 0, 0), 4); text(img, s, 12, y, 0.75, FG, 2)


def tracked_clip(stem, seg, pose, sam, slow=2, fast=False):
    fs, pos = L.trajectory_all(stem)
    start, end = 0, min(fs[-1] + 5, C.frame_ids(stem)[-1])
    shape = C.read_frame(stem, start).shape[:2]
    step = 3 if fast else 1
    first_ball = C.L.trajectory(stem)[0][0]
    for f in range(start, end + 1, step):
        yt, yb = L.gt_y(stem, f)
        t = {q: (int(round(v[0])), int(round(v[1]))) for q, v in L.truth_corners(stem, f).items()}
        tpoly = np.array([t["top_left"], t["top_right"], t["bottom_right"], t["bottom_left"]], np.int32)
        outs = []
        for name, pr, col, exact in (("student seg", seg, RED, True), ("student pose", pose, MAG, True), ("SAM 2 video mode (loop 1)", sam, BLUE, False)):
            img = C.read_frame(stem, f)
            if pr is None:
                continue
            m = pr.mask(f, shape) if exact else None
            if m is not None:
                img[m] = (0.5 * img[m] + np.array([120, 40, 0])).clip(0, 255).astype(np.uint8)
            ln = pr.at(f, exact)
            cv2.polylines(img, [tpoly], True, GREEN, 2, cv2.LINE_AA)
            draw_lane(img, ln, yt, yb, col, 2)
            if f in pos:
                x, y, r = pos[f]; cv2.circle(img, (int(x), int(y)), int(max(r, 6)), YEL, 2, cv2.LINE_AA)
            err = pr.per.get(f)
            phase = "bowler on the lane" if f < first_ball + 3 else ("ball rolling" if f <= fs[-1] else "after")
            caption(img, [name, f"f{f}  {phase}" + (f"   board err {err:.2f}" if err is not None else "   (no lane)" if ln is None else "")])
            outs.append(img)
        frame = panels(outs, f"{C.LABEL[stem]} - every frame, no prompt: green = annotated, red = student seg (gated), magenta = student pose, blue = SAM 2 video mode",
                       "students: one 640 px pass per frame on CPU. SAM 2: loop 1's video mode, prompted once from the ball path and propagated")
        for _ in range(1 if fast else (slow if f >= first_ball - 5 else 1)):
            yield frame


def unlabeled_clip(stem, student, teacher, header, fast=False):
    ids = C.frame_ids(stem)
    step = 3 if fast else 1
    for f in ids[::step]:
        img = C.read_frame(stem, f)
        shape = img.shape[:2]
        m = student.mask(f, shape)
        if m is not None:
            img[m] = (0.5 * img[m] + np.array([120, 40, 0])).clip(0, 255).astype(np.uint8)
        ln = student.at(f)
        if ln:
            c = ln["corners"]
            poly = np.array([c["top_left"], c["top_right"], c["bottom_right"], c["bottom_left"]], np.int32)
            cv2.polylines(img, [poly], True, RED, 2, cv2.LINE_AA)
        if teacher is not None:
            tl = teacher.at(f, exact=False)
            if tl:
                c = tl["corners"]
                poly = np.array([c["top_left"], c["top_right"], c["bottom_right"], c["bottom_left"]], np.int32)
                cv2.polylines(img, [poly], True, BLUE, 2, cv2.LINE_AA)
        caption(img, [f"f{f}", "red = student (all3), blue = SAM 2 teacher (ball-path prompts)" if teacher else "red = student (all3)"])
        yield panels([img], header)


def fmt(v):
    return "-" if v is None else (f"{v:.2f}" if isinstance(v, float) else str(v))


def results_rows(seg_prefix, pose_prefix):
    """Table rows: per held-out video, student seg (gated), student seg +plus (gated), pose, SAM."""
    loop1 = {r["stem"]: r for r in load_json(C.LOOP1 / "results" / "even3_last.json") or []}
    vrev = {r["stem"]: r for r in load_json(C.LOOP1 / "results" / "video_rev.json") or []}
    carry = {r["stem"]: r for r in load_json(C.LOOP2 / "results" / "video_carry_track.json") or []}
    rows = []
    for stem in C.STEMS:
        for label, run in (("student seg, gated", f"{seg_prefix}_lovo_{stem}_anc_gated"), ("student seg +teacher frames", f"{seg_prefix}_lovo_{stem}_plus_anc_gated"), ("student pose", f"{pose_prefix}_lovo_{stem}")):
            r = load_json(C.RESULTS / f"{run}__{stem}.json")
            if not r:
                continue
            rows.append((stem, label, r["last"]["board_mae"], r["prehit"]["board_mae"], r["clean"]["mean"], r["clean"]["median"], r["occluded"]["mean"], r["occluded"]["median"], r["throw"]["within_2"], r["latency_ms_median"]))
        a, b, c = loop1.get(stem), vrev.get(stem), carry.get(stem)
        rows.append((stem, "SAM 2 even3 (loop 1)", a and a["board_mae"], None, None, None, None, None, None, a and a["latency_s"] * 1000))
        rows.append((stem, "SAM 2 video mode", b and b["board_mae"], None, b and b["perframe_mae_mean"], b and b["perframe_mae_median"], None, None, b and b["perframe_within_2"], None))
        rows.append((stem, "SAM 2 gate+carry (loop 2)", c and c["board_mae"], None, c and c["perframe_mae_mean"], c and c["perframe_mae_median"], None, None, c and c["perframe_within_2"], None))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(C.HERE / "review.mp4")); ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--seg", default="seg640"); ap.add_argument("--pose", default="pose640"); ap.add_argument("--fast", action="store_true")
    ap.add_argument("--script", default=str(C.HERE / "video_script.json"), help="cards text (title/data/method/conclusion) as JSON")
    a = ap.parse_args()
    vw = cv2.VideoWriter(a.out, cv2.VideoWriter_fourcc(*"avc1"), a.fps, (W, H))
    hold = (lambda frame, s: [vw.write(frame) for _ in range(int(s * a.fps))])
    script = load_json(a.script) or {}
    for key, secs in (("title", 7), ("data", 8), ("method", 9)):
        blk = script.get(key)
        if blk:
            hold(card(blk["title"], blk["lines"], blk.get("sub")), 2 if a.fast else secs)
    # data thumbnails
    thumbs = []
    for stem in C.STEMS + list(C.UNLABELED):
        f = C.frame_ids(stem)[len(C.frame_ids(stem)) // 2]
        img = C.read_frame(stem, f)
        if stem in C.STEMS:
            t = {q: (int(round(v[0])), int(round(v[1]))) for q, v in L.truth_corners(stem, f).items()}
            cv2.polylines(img, [np.array([t["top_left"], t["top_right"], t["bottom_right"], t["bottom_left"]], np.int32)], True, GREEN, 3, cv2.LINE_AA)
        caption(img, [C.LABEL[stem], f"{len(C.frame_ids(stem))} frames" + ("" if stem in C.STEMS else "  (no annotation)")])
        thumbs.append(img)
    hold(panels(thumbs, "The five videos: three annotated (green = hand-clicked lane, per frame) and two unlabeled from Downloads"), 2 if a.fast else 7)
    # results table
    rows = results_rows(a.seg, a.pose)
    header = ["video", "method", "last", "pre-hit", "clean mean", "clean med", "occl. mean", "occl. med", "<=2 boards", "ms/frame"]
    cols = [60, 330, 760, 880, 1010, 1150, 1290, 1430, 1570, 1740]
    trs = []
    for r in rows:
        col = FG if r[1].startswith("student") else DIM
        trs.append(([C.SHORT[r[0]], r[1]] + [fmt(v) for v in r[2:9]] + [fmt(round(r[9])) if r[9] is not None else "-"], col))
    hold(table_card("Board MAE on the held-out video (leave-one-video-out), lower is better", "students never saw the scored video (anchor-selected, gated + carry); SAM rows are loops 1-2 on the same frames and metric",
                    header, trs, cols, y0=230, scale=0.66, dy=34,
                    note=["last / pre-hit = the single frames the SAM loops report; clean = ball rolling, bowler off the lane; occl. = bowler on the lane (SAM has no lane there).",
                          "ms/frame: students on this Mac's CPU at 640 px; SAM 2 base 2.1 s, tiny 0.7 s per frame plus a ball track for prompts."]), 3 if a.fast else 14)
    # tracked clips
    for stem in C.STEMS:
        seg_name = next((n for n in (f"{a.seg}_lovo_{stem}_plus_anc_gated", f"{a.seg}_lovo_{stem}_anc_gated", f"{a.seg}_lovo_{stem}_gated", f"{a.seg}_lovo_{stem}") if (C.RESULTS / f"{n}__{stem}.json").exists()), f"{a.seg}_lovo_{stem}")
        seg_r = load_json(C.RESULTS / f"{seg_name}__{stem}.json"); pose_r = load_json(C.RESULTS / f"{a.pose}_lovo_{stem}__{stem}.json")
        sam_r = next((r for r in load_json(C.LOOP1 / "results" / "video_rev.json") or [] if r["stem"] == stem), None)
        seg = Pred(seg_name, stem, seg_r and seg_r["per_frame"]) if seg_r else None
        if seg is not None and seg.z is None:  # gated lines carry no masks of their own: borrow the run's
            base = seg_name.replace("_gated", "").replace("_window", "").replace("_ransac", "")
            seg.z = Pred(base, stem).z
        pose = Pred(f"{a.pose}_lovo_{stem}", stem, pose_r and pose_r["per_frame"]) if pose_r else None
        sam = Pred("sam_video_rev", stem, sam_r and sam_r["per_frame"]) if sam_r else None
        if seg is None and pose is None:
            continue
        for fr in tracked_clip(stem, seg, pose, sam, fast=a.fast):
            vw.write(fr)
    # pin-end stills
    for stem in C.STEMS:
        ims = []
        for cand in (f"{a.seg}_lovo_{stem}_plus_anc", f"{a.seg}_lovo_{stem}_anc", f"{a.seg}_lovo_{stem}"):
            p = C.OVERLAYS / f"{cand}_prehit_{stem}.jpg"
            if p.exists():
                ims.append(cv2.imread(str(p))); break
        p = C.OVERLAYS / f"{a.pose}_lovo_{stem}_prehit_{stem}.jpg"
        if p.exists():
            ims.append(cv2.imread(str(p)))
        p2 = C.LOOP2 / "overlays" / f"even3_prehit_k_{stem}.jpg"
        if p2.exists():
            ims.append(cv2.imread(str(p2)))
        if ims:
            hold(panels(ims, f"{C.LABEL[stem]} - pre-hit frame, pin end x3: student seg / student pose / SAM 2 (loop 2, even3 prompts)", "green = annotated lane, red = prediction; a board is 1-2 px at the pin end"), 2 if a.fast else 6)
    # unlabeled
    for stem, hdr in (("bowling_video", "bowling_video (never seen, new camera placement): student all3 vs SAM 2 teacher"), ("IMG_0242", "IMG_0242 (never seen, handheld, panning): student all3 + teacher frames")):
        prefer = (f"{a.seg}_all3",) if stem == "bowling_video" else (f"{a.seg}_all3_plus", f"{a.seg}_all3")  # bowling_video's teacher frames are in all3_plus's training set
        all3 = next((n for n in prefer if (C.RESULTS / f"{n}__{stem}.json").exists()), None)
        sr = load_json(C.RESULTS / f"{all3}__{stem}.json") if all3 else None
        if not sr:
            continue
        st = Pred(all3, stem, sr["per_frame"])
        te = Pred("teacher", stem) if stem == "bowling_video" else None
        vt = load_json(C.RESULTS / f"{all3}__{stem}__vs_teacher.json")
        if vt:
            hdr += f"  |  vs teacher: {vt['vs_teacher_reliable']['median']} boards median, {vt['corner_px_reliable']} px corners"
        for fr in unlabeled_clip(stem, st, te, hdr, fast=a.fast):
            vw.write(fr)
    # latency + conclusion
    for key, secs in (("latency", 8), ("conclusion", 14)):
        blk = script.get(key)
        if blk:
            hold(card(blk["title"], blk["lines"], blk.get("sub")), 2 if a.fast else secs)
    vw.release()
    print("wrote", a.out)


if __name__ == "__main__":
    main()
