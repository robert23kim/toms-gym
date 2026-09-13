"""Train the cheap lane students with ultralytics on MPS.

usage: train.py <task:seg|pose> <fold> [imgsz] [epochs] [tag]
Runs go to $LANE_SCRATCH/runs/<task><imgsz>_<fold><tag>/weights/{best,last}.pt
"""
import os
import sys
import time
from pathlib import Path

import common as C

os.environ.setdefault("YOLO_CONFIG_DIR", str(C.SCRATCH / "yolo_cfg"))
from ultralytics import YOLO  # noqa: E402

DS = C.SCRATCH / "ds"
RUNS = C.SCRATCH / "runs"


def train(task, fold, imgsz=640, epochs=40, tag="", model=None, extra=None):
    base = model or (f"yolo11n-{task}.pt")
    name = f"{task}{imgsz}_{fold}{tag}"
    kw = dict(data=str(DS / task / f"{fold}.yaml"), imgsz=imgsz, epochs=epochs, batch=16, device="mps",
              project=str(RUNS), name=name, exist_ok=True, workers=4, patience=20, plots=False, verbose=False,
              fliplr=0.5, degrees=5.0, translate=0.1, scale=0.5, perspective=0.0005, hsv_h=0.02, hsv_s=0.6, hsv_v=0.5,
              close_mosaic=10, seed=0, deterministic=False, cache="ram")
    if task == "seg":
        kw["overlap_mask"] = True
    if extra:
        kw.update(extra)
    t0 = time.time()
    m = YOLO(str(C.SCRATCH / "weights" / base) if (C.SCRATCH / "weights" / base).exists() else base)
    m.train(**kw)
    dt = time.time() - t0
    (RUNS / name / "train_time_s.txt").write_text(f"{dt:.0f}\n")
    print(f"DONE {name} in {dt / 60:.1f} min")
    return RUNS / name / "weights" / "best.pt"


if __name__ == "__main__":
    task, fold = sys.argv[1], sys.argv[2]
    imgsz = int(sys.argv[3]) if len(sys.argv) > 3 else 640
    epochs = int(sys.argv[4]) if len(sys.argv) > 4 else 40
    tag = sys.argv[5] if len(sys.argv) > 5 else ""
    train(task, fold, imgsz, epochs, tag)
