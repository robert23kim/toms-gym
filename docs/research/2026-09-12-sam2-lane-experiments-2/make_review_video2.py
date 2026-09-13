"""Compose the loop-2 review video from results/*.json, overlays/*.jpg and the
per-frame masks in the scratchpad. Reuses the loop-1 drawing helpers.

usage: make_review_video2.py [--out review.mp4] [--fps 30] [--hold 3]

Sections: title + the loop-1 numbers to beat, the three videos on the pre-hit
frame, the prompt bug, part 1 resolution at the pin end, part 2 extrapolation,
part 3 anchors, part 4 tracking (with clips), the annotation diagnostics, the
summary tables and the recommendation. Also writes results/summary.md.
"""
import argparse
import json
import re
from pathlib import Path

import cv2
import numpy as np

import common as C

L, gt = C.L, C.gt
import make_review_video as MV  # noqa: E402  (loop-1 helpers; sys.path set by common)

MV.SCRATCH = C.SCRATCH / "masks"
W, H, FG, DIM = MV.W, MV.H, MV.FG, MV.DIM
STEMS, LABEL = C.STEMS, C.LABEL
text, canvas, card, table_card, triptych, fmt = MV.text, MV.canvas, MV.card, MV.table_card, MV.triptych, MV.fmt
GREEN = (90, 210, 90)
RED = (80, 80, 230)

KINDS = ["last", "prehit", "prehit-6"]
KIND_LABEL = {"last": "last ball frame (after contact on 2 videos)", "prehit": "pin hit - 2 (pins standing, sharp)",
              "prehit-6": "pin hit - 6"}
LOOP1 = {"even3_last": (0.24, 0.39, 1.35), "track_last": (0.09, 1.07, 0.93), "even_last": (0.17, 0.50, 1.54),
         "best per video (any method)": (0.08, 0.32, 0.61)}
LOOP1_TRACK = {"video_rev": ("1.85 / 0.98", "16.39 / 4.02", "3.73 / 2.35"), "video_span": ("2.00 / 1.06", "19.45 / 3.86", "3.55 / 2.23")}


def load_rows2():
    """{(base, kind, tag): {stem: row}} from this folder's results."""
    out = {}
    for p in sorted(C.RESULTS.glob("*.json")):
        if p.name.startswith(("camera_", "summary")):
            continue
        try:
            rows = json.loads(p.read_text())
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(rows, list):
            continue
        for r in rows:
            key, kind = r.get("method"), r.get("kind")
            if not key or not kind:
                continue
            i = key.rfind(f"_{kind}")
            if i < 0:
                continue
            base, tag = key[:i], key[i + len(kind) + 1:]
            out.setdefault((base, kind, tag), {})[r["stem"]] = r
    return out


def cell(rows, stem, key="board_mae"):
    r = rows.get(stem) if rows else None
    return fmt(r, key)


def grid_card(title, sub, groups, note=None, desc=None):
    """groups: list of (label, {stem: row}). One line per group, MAE per video."""
    header = ["", "sample_input", "Chardie", "tom_old", "max (s / C / t)"]
    cols = [80, 760, 960, 1160, 1380]
    trs = []
    for lab, rows in groups:
        mx = " / ".join(cell(rows, s, "board_max") for s in STEMS)
        trs.append([lab] + [cell(rows, s) for s in STEMS] + [mx])
    c = table_card(title, sub, header, trs, cols, y0=300, scale=0.85, dy=44, note=note)
    if desc:
        for i, ln in enumerate(wrap(desc, 110)):
            text(c, ln, 80, 225 + 30 * i, 0.8, DIM, 2)
    return c


def wrap(s, n):
    words, lines, cur = s.split(), [], ""
    for w_ in words:
        if len(cur) + len(w_) + 1 > n:
            lines.append(cur)
            cur = w_
        else:
            cur = (cur + " " + w_).strip()
    if cur:
        lines.append(cur)
    return lines


def method_groups(rows2, base, tags=("_k", ""), kinds=KINDS):
    groups = []
    for kind in kinds:
        for tag in tags:
            rs = rows2.get((base, kind, tag))
            if rs:
                groups.append((f"{kind}{tag}", rs))
                break
    for kind in kinds:
        rs = rows2.get((base, kind, "_k_tiny")) or rows2.get((base, kind, "_tiny"))
        if rs:
            groups.append((f"{kind}  tiny", rs))
    return groups


def desc_of(rows2, base):
    for (b, _, _), rs in rows2.items():
        if b == base:
            for r in rs.values():
                if r.get("desc"):
                    return r["desc"]
    return ""


def overlays_for2(base, kind, tag):
    ims = []
    for s in STEMS:
        p = C.OVERLAYS / f"{base}_{kind}{tag}_{s}.jpg"
        if p.exists():
            ims.append(cv2.imread(str(p)))
    return ims


def first_overlay_kind(base, rows2):
    for kind in ("last", "prehit", "prehit-6"):
        for tag in ("_k", ""):
            if rows2.get((base, kind, tag)) and overlays_for2(base, kind, tag):
                return kind, tag
    return None, None


def intro_prehit():
    ims = []
    for s in STEMS:
        f = C.frame_for(s, "prehit")
        img = C.read_frame(s, f)
        t = {k: (int(round(v[0])), int(round(v[1]))) for k, v in L.truth_corners(s, f).items()}
        poly = np.array([t["top_left"], t["top_right"], t["bottom_right"], t["bottom_left"]], np.int32)
        cv2.polylines(img, [poly], True, (0, 220, 0), 2, cv2.LINE_AA)
        for (x, y) in L.ball_points_on(s, f):
            cv2.circle(img, (int(x), int(y)), 4, (0, 255, 255), -1, cv2.LINE_AA)
        for x, y in C.even_points_keep(s, f, 3):
            cv2.circle(img, (int(x), int(y)), 10, (0, 255, 255), -1, cv2.LINE_AA)
            cv2.circle(img, (int(x), int(y)), 10, (0, 0, 0), 2, cv2.LINE_AA)
        cap = [f"{LABEL[s]}  f{f} = pin hit - 2", "pins standing, bowler off the lane, 3 kept prompts"]
        y = img.shape[0] - 50
        for ln in cap:
            text(img, ln, 12, y, 0.75, (0, 0, 0), 4)
            text(img, ln, 12, y, 0.75, FG, 2)
            y += 30
        ims.append(img)
    return ims


def image_card(title, path, footer=None):
    c = canvas()
    text(c, title, 40, 50, 1.0, FG, 2)
    img = cv2.imread(str(path))
    if img is None:
        return c
    avail_h = H - (130 if footer else 80)
    s = min(avail_h / img.shape[0], (W - 40) / img.shape[1])
    im = cv2.resize(img, (int(img.shape[1] * s), int(img.shape[0] * s)), interpolation=cv2.INTER_AREA)
    x = (W - im.shape[1]) // 2
    c[70:70 + im.shape[0], x:x + im.shape[1]] = im
    if footer:
        for i, ln in enumerate(footer if isinstance(footer, list) else [footer]):
            text(c, ln, 40, H - 30 - 30 * (len(footer) - 1 - i if isinstance(footer, list) else 0), 0.8, DIM, 2)
    return c


def summary_rows(rows2, kind, bases, tag="_k", label_kind=False):
    trs = []
    for b in bases:
        rs = rows2.get((b, kind, tag)) or rows2.get((b, kind, ""))
        if not rs:
            continue
        trs.append([f"{b}  ({kind})" if label_kind else b] + [cell(rs, s) for s in STEMS])
    return trs


def big_table(title, sub, trs, base_rows=None, y0=230, dy=34, scale=0.72):
    header = ["method", "sample_input", "Chardie", "tom_old"]
    cols = [80, 760, 1000, 1240]
    rows = []
    if base_rows:
        rows += [[f"loop 1  {k}"] + [f"{v:.2f}" for v in vals] for k, vals in base_rows.items()]
        rows.append(["", "", "", ""])
    rows += trs
    return table_card(title, sub, header, rows, cols, y0=y0, scale=scale, dy=dy)


def write_summary_md(rows2):
    lines = ["| method | kind | sample_input | Chardie | tom_old |", "|---|---|---|---|---|"]
    for (b, kind, tag), rs in sorted(rows2.items()):
        lines.append(f"| `{b}{tag}` | {kind} | " + " | ".join(cell(rs, s) for s in STEMS) + " |")
    (C.RESULTS / "summary.md").write_text("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(C.HERE / "review.mp4"))
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--hold", type=float, default=3.0)
    ap.add_argument("--extra", default=str(C.HERE / "video_cards.json"), help="JSON list of {title, lines} cards inserted before the summary")
    a = ap.parse_args()
    rows2 = load_rows2()
    write_summary_md(rows2)
    vw = cv2.VideoWriter(a.out, cv2.VideoWriter_fourcc(*"avc1"), a.fps, (W, H))
    assert vw.isOpened()

    def hold(frame, sec):
        for _ in range(int(sec * a.fps)):
            vw.write(frame)

    def show_method(base, part_note=None):
        groups = method_groups(rows2, base)
        if not groups:
            return
        hold(grid_card(base, "board MAE per frame kind (lower is better); _k = kept prompts", groups, note=part_note, desc=desc_of(rows2, base)), a.hold + 1)
        kind, tag = first_overlay_kind(base, rows2)
        if kind:
            ims = overlays_for2(base, kind, tag)
            if ims:
                hold(triptych(ims, f"{base}_{kind}{tag}", "green = annotated lane, red = fitted lane, blue = mask, yellow = prompts, cyan = crop box; inset = pin end x3"), a.hold + 1)

    hold(card("SAM 2 lane detection, loop 2", [
        "Same three videos, same metric, same truth as loop 1: can we beat 0.24 / 0.39 / 1.35 boards,",
        "and is there a better anchor than the ball path?",
        "",
        ("Numbers to beat (loop 1, last frame, sam2.1_b):", DIM),
        "  even3_last   0.24 / 0.39 / 1.35      best per video, any method   0.08 / 0.32 / 0.61",
        "  tracking     video_rev per-frame mean 1.85 / 16.39 / 3.73",
        "",
        ("Three levers tried here:", DIM),
        "  1. resolution at the pin end   (sub-pixel edges, zoomed crops, tiles, 2048 px, prompt ensembles)",
        "  2. extrapolation               (trimmed fits, a vanishing point shared with the neighbouring lanes)",
        "  3. anchors and tracking        (gutters as objects, the pins, pose landmarks; occlusion-gated tracking)",
        "",
        "Legend as before: green = annotated lane, red = SAM lane, yellow = prompts, cyan = crop box, inset = pin end x3",
    ], "2026-09-12, CPU only"), a.hold + 4)

    hold(triptych(intro_prehit(), "New frame kind: pin hit - 2. Pins standing, bowler gone, no motion blur; the ball is at the far end",
                  "Loop 1 scored the last annotated ball frame, which is after pin contact on two videos"), a.hold + 2)

    # the prompt bug
    g_old = [("prehit, loop-1 prompt rule", rows2.get(("even3", "prehit", ""), {})), ("prehit, kept prompts", rows2.get(("even3", "prehit", "_k"), {})),
             ("last, loop-1 prompt rule", rows2.get(("even3", "last", ""), {})), ("last, kept prompts", rows2.get(("even3", "last", "_k"), {}))]
    hold(grid_card("The prompt bug: 2 of 3 points survived", "even3, sam2.1_b; the ball was on the lane at pin hit - 2", g_old,
                   note=["track_points_even drops any point within 3 ball radii of the ball. At pin hit - 2 the ball is at the far end,",
                         "so the top prompt vanished and the mask stopped short of the pin deck; tom_old's last frame had the same bug.",
                         "even_points_keep slides the point down the path instead: sample_input pre-hit 0.55 -> 0.31, tom_old last 1.35 -> 1.17."]), a.hold + 3)
    ims = overlays_for2("even3", "prehit", "") + overlays_for2("even3", "prehit", "_k")
    if len(ims) == 6:
        hold(triptych(ims[:3], "even3_prehit with the loop-1 rule: two prompts, mask ends below the pins"), a.hold)
        hold(triptych(ims[3:], "even3_prehit_k: three prompts"), a.hold)

    hold(card("Part 1: resolution at the pin end", [
        "SAM's mask decoder works on a 256-cell grid: 7.5 source px per cell on a 1080x1920 frame, where a board is 1-2 px.",
        "",
        "soft      : sub-pixel edges from the logit zero crossings instead of the first / last mask pixel",
        "zoom      : second SAM pass on a crop of the top 55% of the lane (2.5-4.4x), rows merged with the full frame",
        "zoom_lo   : the crop's prompts kept in its lower half, away from the pin deck (the deck looks like lane)",
        "zoom_trim : zoom_lo with the top 15% of rows excluded from the fit",
        "tiles     : three overlapping crops (top / middle / bottom)",
        "hires     : the encoder at imgsz 2048",
        "ens       : 10 prompt variants decoded on one encoding, mean logit (the decoder is ~free once encoded)",
        "snap2     : polarity-aware gradient snap (a loop-1 idea done properly; it still fails)",
    ]), a.hold + 2)
    for b in ["soft", "zoom", "zoom_lo", "zoom_trim", "tiles", "hires", "ens", "ens_zoom", "snap2"]:
        show_method(b)

    hold(card("Part 2: extrapolation from the wide end", [
        "If the far end is unreliable, fit the lines where a board is 10 px and extrapolate.",
        "",
        "trim : fit on the rows below the top 30% of the lane only (sweep 0-50% in the JSON)",
        "vp   : vanishing point from the lane AND its neighbours (SAM prompted on the path shifted by one lane pitch);",
        "       each edge refitted through the VP on the lower 70% of rows",
        "",
        "Result: worse on every video. The mask's far-end rows agree with the annotation better than any extrapolation",
        "from the wide end does, so the lower-lane edges carry their own small systematic offsets (gutter lip, annotation).",
    ]), a.hold + 2)
    for b in ["trim", "vp"]:
        show_method(b)

    anchors = [b for (b, _, _) in rows2 if b.startswith(("gutters", "pins", "landmarks", "pose", "foul"))]
    anchors = sorted(set(anchors))
    hold(card("Part 3: anchors (the fitness-model question)", [
        "The lifting analysis anchors on named pose landmarks, not on pixels. The lane equivalent:",
        "",
        "gutters   : lane + left gutter + right gutter as three objects in one SAM decode; the edge is where they meet",
        "pins      : the standing pin cluster is a ruler: 7-pin to 10-pin spans 40.8 in of a 41.5 in lane, centred",
        "landmarks : prompts from the release point (pose) to the pin centre, no ball path at all",
        "",
        "Methods below were run by the anchors agent; the pin-vs-annotation width check follows them.",
    ] + ([f"available: {', '.join(anchors)}"] if anchors else ["(no anchor results found)"])), a.hold + 2)
    for b in anchors:
        show_method(b)

    tracked = sorted({b for (b, _, _) in rows2 if b.startswith(("video_", "best_late", "late_median", "carry"))})
    hold(card("Part 4: tracking through the throw, and which frame to trust", [
        "video_carry : loop-1 video-mode masks re-scored with an occlusion gate; gated frames carry the nearest clean lane",
        "              through the camera model instead of their own mask",
        "best_late   : SAM on the 6 frames before pin hit, one picked by a self-supervised quality score",
        "late_median : median of those 6 frames' lines (warped into the pre-hit frame)",
        "",
        "Loop 1 per-frame means to beat: 1.85 / 16.39 / 3.73 (video_rev), 2.00 / 19.45 / 3.55 (video_span)",
    ] + ([f"available: {', '.join(tracked)}"] if tracked else ["(no tracking results found)"])), a.hold + 2)
    for b in tracked:
        groups = []
        for kind in ("prehit", "last", "all", "span", "rev"):
            for tag in ("", "_k", "_tiny", "_k_tiny"):
                rs = rows2.get((b, kind, tag))
                if rs:
                    groups.append((f"{kind}{tag}", rs))
        if not groups:
            continue
        note = None
        pf = [(lab, rs) for lab, rs in groups if any(r.get("perframe_mae_mean") is not None for r in rs.values())]
        if pf:
            note = ["per frame, mean / median / max / % of frames <= 2 boards:"]
            for lab, rs in pf:
                for s in STEMS:
                    r = rs.get(s)
                    if r and r.get("perframe_mae_mean") is not None:
                        note.append(f"   {lab:10s} {LABEL[s]:30s} {r['perframe_mae_mean']:.2f} / {r.get('perframe_mae_median', 0) or 0:.2f} / {r['perframe_mae_max']:.2f} / {r.get('perframe_within_2', 0) or 0:.0f}%")
        hold(grid_card(b, "board MAE on the reported frame", groups, note=note, desc=desc_of(rows2, b)), a.hold + 2)
        kind, tag = first_overlay_kind(b, rows2)
        if kind:
            ims = overlays_for2(b, kind, tag)
            if ims:
                hold(triptych(ims, f"{b}_{kind}{tag}"), a.hold + 1)
    clip_methods = [m for m in ["video_rev", "video_span"] if (C.SCRATCH / "masks" / f"masks_{m}_sample_input.npz").exists()]
    clip_methods += [k for k in sorted({key.split("_", 1)[1] for key in [p.stem for p in (C.SCRATCH / "masks").glob("masks_*.npz")]}) if k.rsplit("_", 1)[0] not in ("video_rev", "video_span") and k.rsplit("_", 1)[0] not in clip_methods]
    # masks_<method>_<stem>.npz -> method names (stems contain underscores, so strip known stems)
    names = set()
    for p in (C.SCRATCH / "masks").glob("masks_*.npz"):
        n = p.stem[len("masks_"):]
        for s in STEMS:
            if n.endswith("_" + s):
                names.add(n[: -len(s) - 1])
    clip_methods = [m for m in ["video_rev", "video_span"] if m in names] + sorted(n for n in names if n not in ("video_rev", "video_span"))
    rows_for_clips = {}
    for (b, kind, tag), rs in rows2.items():
        if b in clip_methods and kind in ("prehit", "last", "all", "span", "rev"):
            rows_for_clips.setdefault(b, {}).update(rs)
    if clip_methods:
        for s in STEMS:
            for fr in MV.tracked_clip_frames(s, clip_methods[:3], rows_for_clips):
                vw.write(fr)

    hold(card("What the annotation cannot tell you", [
        "Every number here is relative to hand-clicked corners. Three checks on the truth itself:",
        "",
        "1. sample_input's per-frame corners are 6 hand-clicked sets over 180 frames; the top width varies 58-61 px,",
        "   i.e. about +-1 board of annotation noise at the pins. Results near 0.1-0.2 boards are at that floor.",
        "2. tom_old: on the sharp pre-hit frames SAM's far-end edges sit 5-7 px right of the annotated ones (both edges,",
        "   tapering to 0 at the foul line). The pins put the annotation within 1.7 px of the lane centre and SAM 5 px",
        "   right of it: this one is SAM's, unique to the standing-pin frames, and it shrinks on the pin-hit frame,",
        "   which is why the blurred last frame scores better than the sharp ones. The pin anchor removes it.",
        "3. Chardie: SAM agrees with the pins to 1 px; the annotation is 2.3 px (two boards) off them.",
    ]), a.hold + 4)
    for s, fa, fb in (("tom_old", 169, 171), ("20260112_121117", 132, 170), ("sample_input", 117, 128)):
        p = C.OVERLAYS / f"diagtop_{s}_{fa}_{fb}.jpg"
        if p.exists():
            hold(image_card(f"{LABEL[s]}: far end at 5x, pre-hit (left) vs last frame (right). green = annotation, red = zoom_k", p), a.hold + 2)
    p = C.OVERLAYS / "diag_tom_old_169.jpg"
    if p.exists():
        hold(image_card("tom_old f169 edges at 6x: green = annotation, red = SAM mask boundary, bars = gray profile across the edge", p,
                        "both SAM edges sit 5-6 px right of the annotation at the far end; the pins say the annotation is within 2 px and SAM is not"), a.hold + 2)

    if Path(a.extra).exists():
        for cd in json.loads(Path(a.extra).read_text()):
            hold(card(cd["title"], cd["lines"], cd.get("sub")), cd.get("hold", a.hold + 3))

    single = ["even3", "soft", "ens", "zoom", "zoom_lo", "zoom_trim", "tiles", "hires", "ens_zoom", "snap2", "trim", "vp"] + anchors
    for kind in KINDS:
        trs = summary_rows(rows2, kind, single)
        if trs:
            hold(big_table(f"Summary: {kind}", f"board MAE, sam2.1_b, kept prompts (_k); {KIND_LABEL[kind]}", trs,
                           base_rows=LOOP1 if kind == "last" else None), a.hold + 5)
    trs = summary_rows(rows2, "last", ["even3", "soft", "ens", "zoom", "zoom_lo"], tag="_k_tiny", label_kind=True)
    trs += summary_rows(rows2, "prehit-6", ["even3", "soft", "ens", "zoom", "zoom_lo"], tag="_k_tiny", label_kind=True)
    if trs:
        hold(big_table("Summary: sam2.1_t (tiny) on last and pin hit - 6", "0.7 s per encode on CPU", trs), a.hold + 3)
    if tracked:
        header = ["method", "sample_input", "Chardie", "tom_old"]
        cols = [80, 760, 1000, 1240]
        rows = [[f"loop 1  {k}", *v] for k, v in LOOP1_TRACK.items()] + [["", "", "", ""]]
        for b in tracked:
            for (bb, kind, tag), rs in rows2.items():
                if bb != b:
                    continue
                pf = [rs.get(s, {}).get("perframe_mae_mean") for s in STEMS]
                if any(v is not None for v in pf):
                    rows.append([f"{b}_{kind}{tag}"] + [f"{v:.2f} / {rs.get(s, {}).get('perframe_mae_median', 0) or 0:.2f}" if v is not None else "-" for v, s in zip(pf, STEMS)])
        hold(table_card("Summary: tracking (per-frame mean / median)", "each frame scored against its own lane", header, rows, cols, y0=230, scale=0.72, dy=34), a.hold + 4)
    vw.release()
    print("wrote", a.out)


if __name__ == "__main__":
    main()
