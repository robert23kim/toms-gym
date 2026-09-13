"""E1b: visibility timeline. Every constellation point projected into every frame of each annotated
video through that frame's truth homography; status = out of frame / behind the bowler (yolo11n-seg
person mask) / under the ball (annotation) / pins in motion (after the pin-hit marker) / clear.
Writes results/e1_timeline_<stem>.json (per frame per point), results/e1_timeline_summary.json,
overlays/e1_timeline_<stem>.png (rows = points, columns = frames). usage: e1_timeline.py [stems]"""
import sys

import cv2
import numpy as np

import af

COL = {"clear": (60, 200, 60), "person": (40, 40, 220), "ball": (0, 200, 255), "pins": (200, 60, 200), "out": (70, 70, 70)}
ORDER = ["foul", "fdot", "dot", "adot", "arrow", "pin"]


def run(stem):
    pts = af.constellation()
    names = sorted(pts, key=lambda n: (ORDER.index(af.classes_of(n)) if af.classes_of(n) in ORDER else 9, pts[n][0]))
    ph = af.pin_hit(stem)
    _, pos = af.L.trajectory_all(stem)
    rows = []
    for f in af.frame_ids(stem):
        img = af.read_frame(stem, f); h, w = img.shape[:2]
        H = af.truth_h(stem, f, "all")
        pm = cv2.dilate(af.person_mask(img), np.ones((9, 9), np.uint8))
        ball = pos.get(f)
        st = {}
        for n in names:
            x, y = af.to_image(H, [pts[n]])[0]
            xi, yi = int(round(x)), int(round(y))
            if not (0 <= xi < w and 0 <= yi < h):
                st[n] = "out"
            elif pm[yi, xi]:
                st[n] = "person"
            elif ball is not None and np.hypot(x - ball[0], y - ball[1]) <= 1.0 * max(ball[2], 4) + 2:
                st[n] = "ball"
            elif af.classes_of(n) == "pin" and f >= ph:
                st[n] = "pins"
            else:
                st[n] = "clear"
        rows.append({"frame": f, "status": st, "person_px": int(pm.sum())})
    # summary per class
    fs = [r["frame"] for r in rows]; throw = set(af.throw_frames(stem))
    summ = {"frames": len(rows), "throw_frames": len(throw), "classes": {}}
    for cls in ORDER:
        cn = [n for n in names if af.classes_of(n) == cls]
        if not cn:
            continue
        clear_per_frame = [sum(1 for n in cn if r["status"][n] == "clear") for r in rows]
        clear_throw = [c for r, c in zip(rows, clear_per_frame) if r["frame"] in throw]
        occl = {k: sum(1 for r in rows for n in cn if r["status"][n] == k) for k in COL}
        summ["classes"][cls] = {"n": len(cn), "clear_median_all": float(np.median(clear_per_frame)), "clear_median_throw": float(np.median(clear_throw)) if clear_throw else None,
                                "frames_all_clear": int(sum(1 for c in clear_per_frame if c == len(cn))), "frames_none_clear": int(sum(1 for c in clear_per_frame if c == 0)),
                                "frames_ge_half_clear_throw": int(sum(1 for c in clear_throw if c >= len(cn) / 2)), "status_counts": occl}
    # occlusion episodes per class (which frames the bowler / ball / pins hide it)
    for cls in summ["classes"]:
        cn = [n for n in names if af.classes_of(n) == cls]
        ep = {}
        for k in ("person", "ball", "pins"):
            fr = [r["frame"] for r in rows if any(r["status"][n] == k for n in cn)]
            ep[k] = f"{fr[0]}-{fr[-1]} ({len(fr)} frames)" if fr else None
        summ["classes"][cls]["occluded_by"] = ep
    af.dump(af.RESULTS / f"e1_timeline_{stem}.json", {"stem": stem, "pin_hit": ph, "names": names, "summary": summ, "per_frame": rows})
    # image: rows = points, cols = frames
    cw = max(1, 1600 // len(rows)); rh = 12
    im = np.zeros((rh * len(names) + 40, cw * len(rows) + 160, 3), np.uint8); im[:] = (24, 24, 28)
    for i, n in enumerate(names):
        cv2.putText(im, n.replace("_base", ""), (4, 30 + i * rh + 9), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (220, 220, 220), 1)
        for j, r in enumerate(rows):
            im[30 + i * rh:30 + (i + 1) * rh - 1, 160 + j * cw:160 + (j + 1) * cw] = COL[r["status"][n]]
    for f in (af.throw_frames(stem)[0], ph):
        j = fs.index(f) if f in fs else None
        if j is not None:
            cv2.line(im, (160 + j * cw, 28), (160 + j * cw, im.shape[0] - 2), (255, 255, 255), 1)
    cv2.putText(im, f"{af.SHORT[stem]}: visibility of every constellation point per frame (green clear, blue bowler, yellow ball, magenta pins in motion, grey out of frame); lines = release, pin hit", (4, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (230, 230, 230), 1)
    cv2.imwrite(str(af.OVERLAYS / f"e1_timeline_{stem}.png"), im)
    print(stem, {c: (v["clear_median_throw"], v["frames_ge_half_clear_throw"], v["occluded_by"]) for c, v in summ["classes"].items()}, flush=True)
    return summ


if __name__ == "__main__":
    out = {}
    for stem in (sys.argv[1:] or af.STEMS):
        out[stem] = run(stem)
    if len(sys.argv) == 1:
        af.dump(af.RESULTS / "e1_timeline_summary.json", out)
