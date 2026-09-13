"""CPU latency + size of the students vs SAM 2 tiny, on this Mac.
usage: bench.py <run> [<run> ...] [--imgsz 640] [--threads 4] [--frames 30]
Writes results/bench.json (appends per run/imgsz/threads)."""
import argparse
import json
import os
import time

import numpy as np
import torch

import common as C

os.environ.setdefault("YOLO_CONFIG_DIR", str(C.SCRATCH / "yolo_cfg"))
from ultralytics import YOLO  # noqa: E402


def bench(run, imgsz, threads, n):
    torch.set_num_threads(threads)
    p = C.SCRATCH / "runs" / run / "weights" / "best.pt"
    m = YOLO(str(p))
    frames = [C.read_frame("sample_input", f) for f in C.frame_ids("sample_input")[:n + 3]]
    ts = []
    for i, img in enumerate(frames):
        t0 = time.perf_counter()
        m.predict(img, imgsz=imgsz, device="cpu", conf=0.1, verbose=False, retina_masks=True, max_det=3)
        if i >= 3:
            ts.append(time.perf_counter() - t0)
    ts = np.array(ts) * 1000
    params = sum(x.numel() for x in m.model.parameters())
    row = {"run": run, "task": m.task, "imgsz": imgsz, "threads": threads, "n": len(ts), "ms_median": round(float(np.median(ts)), 1),
           "ms_mean": round(float(ts.mean()), 1), "ms_p90": round(float(np.percentile(ts, 90)), 1), "params_M": round(params / 1e6, 2), "size_MB": round(p.stat().st_size / 1e6, 1)}
    print(row)
    return row


def sam_bench(imgsz, threads, n):
    torch.set_num_threads(threads)
    L = C.L
    m = L.model("sam2.1_t.pt")
    ts = []
    for i, f in enumerate(C.frame_ids("sample_input")[:n + 2]):
        img = C.read_frame("sample_input", f)
        t0 = time.perf_counter()
        L.predict_mask(m, img, points=[[540, 1100], [560, 1000], [575, 950]])
        if i >= 2:
            ts.append(time.perf_counter() - t0)
    ts = np.array(ts) * 1000
    p = C.SCRATCH / "weights" / "sam2.1_t.pt"
    row = {"run": "sam2.1_t (3 point prompts)", "task": "sam", "imgsz": 1024, "threads": threads, "n": len(ts), "ms_median": round(float(np.median(ts)), 1),
           "ms_mean": round(float(ts.mean()), 1), "ms_p90": round(float(np.percentile(ts, 90)), 1), "params_M": 38.9, "size_MB": round(p.stat().st_size / 1e6, 1)}
    print(row)
    return row


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("runs", nargs="*"); ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--threads", type=int, default=4); ap.add_argument("--frames", type=int, default=30); ap.add_argument("--sam", action="store_true")
    a = ap.parse_args()
    out = C.RESULTS / "bench.json"
    rows = json.loads(out.read_text()) if out.exists() else []
    for r in a.runs:
        rows.append(bench(r, a.imgsz, a.threads, a.frames))
    if a.sam:
        rows.append(sam_bench(1024, a.threads, min(a.frames, 8)))
    C.dump(out, rows)
