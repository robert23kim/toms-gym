"""Add SAM 2 teacher pseudo-labels (bowling_video) to the datasets and write
the *_plus folds: lovo_<stem>_plus = the other two annotated videos + the
teacher frames; all3_plus = all three + teacher frames. A teacher frame is
kept when its fit residual is <= 4 px and it is outside the throw window
(bowler / ball on the lane), so no occluded pseudo-label enters training.
"""
import os

import numpy as np
import yaml

import common as C
from build_dataset import DS, ORDER, KP, FLIP_IDX

STEM = "bowling_video"


def teacher_frames():
    import json
    t = json.loads((C.RESULTS / f"teacher__{STEM}.json").read_text())
    lines = json.loads((C.SCRATCH / "pred" / f"lines_teacher_{STEM}.json").read_text())
    lo, hi = t["ball_run"]
    keep = {}
    for r in t["per_frame"]:
        f = r["frame"]
        if r.get("ok") and r["fit_resid_px"] <= 4.0 and not (lo - 5 <= f <= hi + 10) and str(f) in lines:
            keep[f] = lines[str(f)]["corners"]
    return keep, (lo, hi)


def write():
    keep, window = teacher_frames()
    img0 = C.read_frame(STEM, min(keep))
    h, w = img0.shape[:2]
    for task in ("seg", "pose"):
        (DS / task / "images" / STEM).mkdir(parents=True, exist_ok=True)
        (DS / task / "labels" / STEM).mkdir(parents=True, exist_ok=True)
    paths = []
    for f, q in keep.items():
        for task in ("seg", "pose"):
            link = DS / task / "images" / STEM / f"{f:05d}.jpg"
            if not link.exists():
                os.symlink(C.FRAMES / STEM / f"{f:05d}.jpg", link)
        xs = np.clip([q[k][0] / w for k in ORDER], 0, 1); ys = np.clip([q[k][1] / h for k in ORDER], 0, 1)
        (DS / "seg" / "labels" / STEM / f"{f:05d}.txt").write_text("0 " + " ".join(f"{x:.6f} {y:.6f}" for x, y in zip(xs, ys)) + "\n")
        kx = np.clip([q[k][0] / w for k in KP], 0, 1); ky = np.clip([q[k][1] / h for k in KP], 0, 1)
        x1, x2, y1, y2 = kx.min(), kx.max(), ky.min(), ky.max()
        (DS / "pose" / "labels" / STEM / f"{f:05d}.txt").write_text(
            f"0 {(x1 + x2) / 2:.6f} {(y1 + y2) / 2:.6f} {x2 - x1:.6f} {y2 - y1:.6f} " + " ".join(f"{x:.6f} {y:.6f} 2" for x, y in zip(kx, ky)) + "\n")
        paths.append(f"{f:05d}.jpg")
    print(f"{STEM}: {len(keep)} teacher frames kept (throw window {window} excluded)")
    for task in ("seg", "pose"):
        for base in [f"lovo_{s}" for s in C.STEMS] + ["all3"]:
            tr = (DS / task / f"{base}_train.txt").read_text().split()
            va = (DS / task / f"{base}_val.txt").read_text().split()
            tr = tr + [str(DS / task / "images" / STEM / p) for p in paths]
            name = f"{base}_plus"
            (DS / task / f"{name}_train.txt").write_text("\n".join(tr) + "\n")
            (DS / task / f"{name}_val.txt").write_text("\n".join(va) + "\n")
            y = {"path": str(DS / task), "train": f"{name}_train.txt", "val": f"{name}_val.txt", "names": {0: "lane"}}
            if task == "pose":
                y["kpt_shape"] = [4, 3]; y["flip_idx"] = FLIP_IDX
            (DS / task / f"{name}.yaml").write_text(yaml.safe_dump(y, sort_keys=False))
            print(task, name, "train", len(tr), "val", len(va))


if __name__ == "__main__":
    write()
