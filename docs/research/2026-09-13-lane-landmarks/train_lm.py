"""Train the two-class (lane + arrow) yolo11n-seg student. usage: train_lm.py <fold> [imgsz] [epochs]
Runs go to $LM_SCRATCH/runs/seg2_<imgsz>_<fold>/weights/best.pt (best.pt chosen on the training videos' val split)."""
import sys
import time
import common as C
from ultralytics import YOLO

DS = C.SCRATCH / "ds" / "seg2"; RUNS = C.SCRATCH / "runs"


def train(fold, imgsz=640, epochs=30):
    name = f"seg2_{imgsz}_{fold}"
    kw = dict(data=str(DS / f"{fold}.yaml"), imgsz=imgsz, epochs=epochs, batch=16 if imgsz <= 640 else int(__import__("os").environ.get("LM_BATCH", "4")), device="mps",
              project=str(RUNS), name=name, exist_ok=True, workers=4, patience=20, plots=False, verbose=False,
              fliplr=0.0, degrees=5.0, translate=0.1, scale=0.5, perspective=0.0005, hsv_h=0.02, hsv_s=0.6, hsv_v=0.5,
              close_mosaic=10, seed=0, deterministic=False, cache="ram", overlap_mask=True)
    import os
    if os.environ.get("LM_MOSAIC") is not None:   # MPS assigner crash workaround: fewer instances per mosaic
        kw["mosaic"] = float(os.environ["LM_MOSAIC"])
    if os.environ.get("LM_TAG"):
        name = name + os.environ["LM_TAG"]; kw["name"] = name
    # fliplr off: the arrows' board identity is left/right asymmetric only through the lane, but the
    # lane label is symmetric, so a flip is harmless for class 0 and confusing for nothing; keep loop 3's other aug.
    t0 = time.time()
    wp = C.SCRATCH / "weights" / "yolo11n-seg.pt"
    m = YOLO(str(wp) if wp.exists() else "yolo11n-seg.pt")
    m.train(**kw)
    (RUNS / name / "train_time_s.txt").write_text(f"{time.time() - t0:.0f}\n")
    print(f"DONE {name} in {(time.time() - t0) / 60:.1f} min", flush=True)


if __name__ == "__main__":
    train(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 640, int(sys.argv[3]) if len(sys.argv) > 3 else 30)
