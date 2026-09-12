"""E4: train RFDETRNano per leave-one-video-out fold and evaluate on the held-out video.

Usage:
    venv/bin/python e4_train_eval.py --folds tom_old --resolution 640 --epochs 15
    venv/bin/python e4_train_eval.py --all --resolution 640 --epochs 15

Writes EXP/e4_runs/<tag>/<fold>/{checkpoint_best_total.pth, metrics.csv, eval.json}.
Evaluation uses gt.evaluate_centers (50px center metric, identical to the engine's
scoreboard) at conf floors 0.05 / 0.10 / 0.25 / 0.50, top-1 box center per frame.
"""

import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch

import gt

EXP = Path(__file__).resolve().parent
DATA = EXP / "e4_data"
RUNS = EXP / "e4_runs"
CONF_FLOORS = [0.05, 0.10, 0.25, 0.50]
BASE_THRESHOLD = 0.01  # predict once low, then re-threshold offline


def _load_model(ckpt, resolution, device):
    from rfdetr import RFDETRNano
    return RFDETRNano(pretrain_weights=str(ckpt), resolution=resolution,
                      device=device, num_classes=1)


def _raw_predictions(model, stem, frames, batch=8):
    """{frame_idx: [(conf, cx, cy)] sorted desc} using one low-threshold pass."""
    out = {}
    for i in range(0, len(frames), batch):
        chunk = frames[i:i + batch]
        paths = [str(gt.frame_path(stem, f)) for f in chunk]
        dets = model.predict(paths, threshold=BASE_THRESHOLD,
                             include_source_image=False)
        if not isinstance(dets, list):
            dets = [dets]
        for f, d in zip(chunk, dets):
            rows = []
            for (x0, y0, x1, y1), c in zip(np.asarray(d.xyxy).reshape(-1, 4),
                                           np.asarray(d.confidence).reshape(-1)):
                rows.append((float(c), (float(x0) + float(x1)) / 2.0,
                             (float(y0) + float(y1)) / 2.0))
            rows.sort(reverse=True)
            out[f] = rows
    return out


def _top1_at(raw, floor):
    pred = {}
    for f, rows in raw.items():
        pred[f] = (rows[0][1], rows[0][2]) if rows and rows[0][0] >= floor else None
    return pred


def cpu_seconds_per_frame(ckpt, resolution, stem, frames, n=20):
    model = _load_model(ckpt, resolution, "cpu")
    sample = frames[:n]
    # warm up once so lazy init / first-call overhead is not counted
    model.predict([str(gt.frame_path(stem, sample[0]))], threshold=BASE_THRESHOLD,
                  include_source_image=False)
    t = time.time()
    for f in sample:
        model.predict([str(gt.frame_path(stem, f))], threshold=BASE_THRESHOLD,
                      include_source_image=False)
    el = time.time() - t
    del model
    return el / len(sample), len(sample)


def run_fold(heldout, resolution, epochs, batch_size, tag, device_pref="mps",
             patience=5, time_cpu=True):
    from rfdetr import RFDETRNano

    dataset_dir = DATA / f"fold_{heldout}"
    out_dir = RUNS / tag / heldout
    out_dir.mkdir(parents=True, exist_ok=True)
    stats = json.loads((dataset_dir / "stats.json").read_text())

    device_used = device_pref
    t0 = time.time()
    try:
        m = RFDETRNano(resolution=resolution, device=device_pref)
        m.train(dataset_dir=str(dataset_dir), epochs=epochs, batch_size=batch_size,
                output_dir=str(out_dir), num_workers=0, tensorboard=False,
                early_stopping=True, early_stopping_patience=patience,
                early_stopping_use_ema=True)
    except Exception as exc:  # noqa: BLE001 - MPS fallback is the whole point
        print(f"[{heldout}] {device_pref} training failed ({type(exc).__name__}: {exc}); retrying on cpu")
        device_used = "cpu"
        m = RFDETRNano(resolution=resolution, device="cpu")
        m.train(dataset_dir=str(dataset_dir), epochs=epochs, batch_size=batch_size,
                output_dir=str(out_dir), num_workers=0, tensorboard=False,
                early_stopping=True, early_stopping_patience=patience,
                early_stopping_use_ema=True)
    train_seconds = time.time() - t0
    del m

    ckpt = out_dir / "checkpoint_best_total.pth"
    pos, neg = gt.ball_gt(heldout)
    frames = sorted(set(pos) | set(neg))

    eval_device = device_pref if torch.backends.mps.is_available() else "cpu"
    model = _load_model(ckpt, resolution, eval_device)
    t1 = time.time()
    raw = _raw_predictions(model, heldout, frames)
    infer_seconds = time.time() - t1
    del model

    results = {}
    for floor in CONF_FLOORS:
        results[f"{floor:.2f}"] = gt.evaluate_centers(_top1_at(raw, floor), pos, neg)

    cpu_spf = None
    if time_cpu:
        try:
            cpu_spf, n_timed = cpu_seconds_per_frame(ckpt, resolution, heldout, frames)
        except Exception as exc:  # noqa: BLE001
            print(f"[{heldout}] cpu timing failed: {exc}")
            n_timed = 0
    else:
        n_timed = 0

    metrics_csv = out_dir / "metrics.csv"
    epochs_run = max(0, len(metrics_csv.read_text().strip().splitlines()) - 1) if metrics_csv.exists() else None

    payload = {
        "heldout": heldout,
        "train_videos": stats["train_videos"],
        "dataset": {k: stats[k] for k in ("train", "valid", "test")},
        "resolution": resolution,
        "epochs_requested": epochs,
        "epoch_rows_logged": epochs_run,
        "batch_size": batch_size,
        "device_train": device_used,
        "device_eval": eval_device,
        "train_seconds": round(train_seconds, 1),
        "eval_frames": len(frames),
        "eval_seconds_total": round(infer_seconds, 1),
        f"eval_seconds_per_frame_{eval_device}": round(infer_seconds / len(frames), 4),
        "cpu_seconds_per_frame": round(cpu_spf, 4) if cpu_spf else None,
        "cpu_timed_frames": n_timed,
        "n_pos": len(pos),
        "n_neg": len(neg),
        "by_conf": results,
    }
    (out_dir / "eval.json").write_text(json.dumps(payload, indent=2))
    # free ~575MB/fold; only checkpoint_best_total.pth is needed to reproduce eval
    for junk in ("last.ckpt", "last_ema.pth", "checkpoint_best_ema.pth"):
        p = out_dir / junk
        if p.exists():
            p.unlink()
    json.dump({str(f): raw[f][:3] for f in raw},
              open(out_dir / "raw_top3.json", "w"))
    print(json.dumps(payload, indent=2))
    return payload


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folds", nargs="*", default=None)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--resolution", type=int, default=640)
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--patience", type=int, default=5)
    ap.add_argument("--device", default="mps")
    ap.add_argument("--tag", default=None)
    ap.add_argument("--no-cpu-timing", action="store_true")
    a = ap.parse_args()

    folds = list(gt.VIDEOS) if a.all else (a.folds or [])
    tag = a.tag or f"res{a.resolution}_ep{a.epochs}"
    allp = {}
    for f in folds:
        allp[f] = run_fold(f, a.resolution, a.epochs, a.batch_size, tag,
                           device_pref=a.device, patience=a.patience,
                           time_cpu=not a.no_cpu_timing)
    summary = RUNS / tag / "summary.json"
    summary.parent.mkdir(parents=True, exist_ok=True)
    existing = json.loads(summary.read_text()) if summary.exists() else {}
    existing.update(allp)
    summary.write_text(json.dumps(existing, indent=2))


if __name__ == "__main__":
    main()
