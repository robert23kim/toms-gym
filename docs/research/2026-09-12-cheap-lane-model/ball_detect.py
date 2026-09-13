"""Run the engine's fine-tuned ball detector (models/yolo11n_bowling.pt) over a
video's frames and save per-frame ball centres: $LANE_SCRATCH/pred/ball_<stem>.json.
Used to build SAM 2 prompts on the unlabeled videos (ball first, lane second)."""
import json
import os
import sys

import common as C

os.environ.setdefault("YOLO_CONFIG_DIR", str(C.SCRATCH / "yolo_cfg"))
from ultralytics import YOLO  # noqa: E402

BALL = C.gt.ENGINE / "models" / "yolo11n_bowling.pt"


def run(stem, conf=0.25, step=1):
    m = YOLO(str(BALL))
    out = {}
    for f in C.frame_ids(stem)[::step]:
        r = m.predict(C.read_frame(stem, f), imgsz=640, conf=conf, verbose=False, device="cpu", max_det=5)[0]
        dets = []
        for b, c, k in zip(r.boxes.xyxy.tolist(), r.boxes.conf.tolist(), r.boxes.cls.tolist()):
            dets.append({"x": (b[0] + b[2]) / 2, "y": (b[1] + b[3]) / 2, "r": (b[2] - b[0] + b[3] - b[1]) / 4, "conf": c, "cls": int(k), "name": m.names[int(k)]})
        out[str(f)] = dets
    (C.SCRATCH / "pred").mkdir(exist_ok=True)
    (C.SCRATCH / "pred" / f"ball_{stem}.json").write_text(json.dumps(out))
    n = sum(1 for v in out.values() if v)
    print(stem, "frames with a detection", n, "/", len(out), "classes", m.names)
    return out


if __name__ == "__main__":
    for s in (sys.argv[1:] or list(C.UNLABELED)):
        run(s)
