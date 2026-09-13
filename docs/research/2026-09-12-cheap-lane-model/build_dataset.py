"""Build YOLO datasets (segment + pose) from the annotated lane corners.

Label per frame = the annotated lane quad on that frame (sample_input: hand
per-frame corners; Chardie / tom_old: static corners warped through the
full-video camera model from camera_all.py). Segment labels are the quad as a
polygon, pose labels are its bbox + 4 keypoints (TL, TR, BL, BR).

Folds: lovo_<stem> trains on the other two annotated videos, all3 trains on
all three. The in-training val split is every 10th frame of the TRAINING
videos (so best.pt is chosen without looking at the held-out video); the
held-out video is scored only by eval.py.
"""
import os
from pathlib import Path

import numpy as np
import yaml

import common as C

C.use_full_camera()
DS = C.SCRATCH / "ds"
ORDER = ("top_left", "top_right", "bottom_right", "bottom_left")  # polygon order
KP = ("top_left", "top_right", "bottom_left", "bottom_right")     # keypoint order
FLIP_IDX = [1, 0, 3, 2]


def quad_for(stem, f):
    q = C.truth_quad(stem, f)
    return {k: (float(v[0]), float(v[1])) for k, v in q.items()}


def write_labels():
    for task in ("seg", "pose"):
        for stem in C.STEMS:
            (DS / task / "images" / stem).mkdir(parents=True, exist_ok=True)
            (DS / task / "labels" / stem).mkdir(parents=True, exist_ok=True)
    meta = {}
    for stem in C.STEMS:
        img0 = C.read_frame(stem, C.frame_ids(stem)[0])
        h, w = img0.shape[:2]
        meta[stem] = (w, h)
        for f in C.frame_ids(stem):
            q = quad_for(stem, f)
            for task in ("seg", "pose"):
                link = DS / task / "images" / stem / f"{f:05d}.jpg"
                if not link.exists():
                    os.symlink(C.FRAMES / stem / f"{f:05d}.jpg", link)
            xs = np.clip([q[k][0] / w for k in ORDER], 0, 1); ys = np.clip([q[k][1] / h for k in ORDER], 0, 1)
            poly = " ".join(f"{x:.6f} {y:.6f}" for x, y in zip(xs, ys))
            (DS / "seg" / "labels" / stem / f"{f:05d}.txt").write_text(f"0 {poly}\n")
            kx = np.clip([q[k][0] / w for k in KP], 0, 1); ky = np.clip([q[k][1] / h for k in KP], 0, 1)
            x1, x2, y1, y2 = kx.min(), kx.max(), ky.min(), ky.max()
            box = f"{(x1 + x2) / 2:.6f} {(y1 + y2) / 2:.6f} {x2 - x1:.6f} {y2 - y1:.6f}"
            kps = " ".join(f"{x:.6f} {y:.6f} 2" for x, y in zip(kx, ky))
            (DS / "pose" / "labels" / stem / f"{f:05d}.txt").write_text(f"0 {box} {kps}\n")
    return meta


def write_folds():
    folds = {f"lovo_{s}": [t for t in C.STEMS if t != s] for s in C.STEMS}
    folds["all3"] = list(C.STEMS)
    for task in ("seg", "pose"):
        for name, train_stems in folds.items():
            tr, va = [], []
            for stem in train_stems:
                for i, f in enumerate(C.frame_ids(stem)):
                    p = str(DS / task / "images" / stem / f"{f:05d}.jpg")
                    (va if i % 10 == 5 else tr).append(p)
            (DS / task / f"{name}_train.txt").write_text("\n".join(tr) + "\n")
            (DS / task / f"{name}_val.txt").write_text("\n".join(va) + "\n")
            y = {"path": str(DS / task), "train": f"{name}_train.txt", "val": f"{name}_val.txt", "names": {0: "lane"}}
            if task == "pose":
                y["kpt_shape"] = [4, 3]
                y["flip_idx"] = FLIP_IDX
            (DS / task / f"{name}.yaml").write_text(yaml.safe_dump(y, sort_keys=False))
            print(task, name, "train", len(tr), "val", len(va))


if __name__ == "__main__":
    print(write_labels())
    write_folds()
