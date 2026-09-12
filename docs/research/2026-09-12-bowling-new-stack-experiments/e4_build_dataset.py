"""E4: build leave-one-video-out COCO datasets for RF-DETR ball fine-tuning.

For each held-out video a dataset_dir is written:

    EXP/e4_data/fold_<heldout>/
        train/_annotations.coco.json + <stem>_<idx>.jpg
        valid/_annotations.coco.json + ...      (15% slice of train)
        test/_annotations.coco.json  + ...      (the held-out video, all frames)

Positives get one "ball" box [x-r, y-r, 2r, 2r] clamped to the image.
Explicit no-ball frames are included as negative images with zero annotations,
capped at NEG_CAP per video so they cannot dominate the loss.

Images are hard-linked from EXP/frames/<stem>/ when possible (no copy cost).

Run: venv/bin/python e4_build_dataset.py
"""

import json
import os
import random
import shutil
from pathlib import Path

import cv2

import gt

EXP = Path(__file__).resolve().parent
OUT = EXP / "e4_data"
NEG_CAP = 40
VALID_FRACTION = 0.15
SEED = 1234

CATEGORIES = [{"id": 1, "name": "ball", "supercategory": "none"}]


def _frame_size(stem, idx):
    im = cv2.imread(str(gt.frame_path(stem, idx)))
    if im is None:
        raise FileNotFoundError(gt.frame_path(stem, idx))
    h, w = im.shape[:2]
    return w, h


def video_records(stem, neg_cap=NEG_CAP, rng=None):
    """[(stem, frame_idx, box_or_None)] - positives then a capped negative sample."""
    pos, neg = gt.ball_gt(stem)
    recs = []
    for idx in sorted(pos):
        x, y, r = pos[idx]
        recs.append((stem, idx, (x, y, r)))
    negs = sorted(neg)
    if neg_cap is not None and len(negs) > neg_cap:
        rng = rng or random.Random(SEED)
        negs = sorted(rng.sample(negs, neg_cap))
    for idx in negs:
        recs.append((stem, idx, None))
    return recs


def _clamped_box(x, y, r, w, h):
    x0 = max(0.0, x - r)
    y0 = max(0.0, y - r)
    x1 = min(float(w), x + r)
    y1 = min(float(h), y + r)
    bw, bh = x1 - x0, y1 - y0
    if bw <= 1 or bh <= 1:
        return None
    return [x0, y0, bw, bh]


def write_split(split_dir, records, link=True):
    split_dir.mkdir(parents=True, exist_ok=True)
    images, anns = [], []
    ann_id = 1
    n_pos = n_neg = 0
    for i, (stem, idx, box) in enumerate(records, start=1):
        src = gt.frame_path(stem, idx)
        name = f"{stem}_{idx:05d}.jpg"
        dst = split_dir / name
        if not dst.exists():
            if link:
                try:
                    os.link(src, dst)
                except OSError:
                    shutil.copyfile(src, dst)
            else:
                shutil.copyfile(src, dst)
        w, h = _frame_size(stem, idx)
        images.append({"id": i, "file_name": name, "width": w, "height": h})
        if box is not None:
            x, y, r = box
            cb = _clamped_box(x, y, r, w, h)
            if cb is None:
                n_neg += 1
                continue
            anns.append({
                "id": ann_id, "image_id": i, "category_id": 1,
                "bbox": [round(v, 2) for v in cb],
                "area": round(cb[2] * cb[3], 2), "iscrowd": 0,
                "segmentation": [],
            })
            ann_id += 1
            n_pos += 1
        else:
            n_neg += 1
    coco = {
        "info": {"description": "toms_gym bowling ball - E4 RF-DETR leave-one-video-out"},
        "licenses": [{"id": 1, "name": "internal", "url": ""}],
        "images": images,
        "annotations": anns,
        "categories": CATEGORIES,
    }
    (split_dir / "_annotations.coco.json").write_text(json.dumps(coco))
    return {"images": len(images), "boxes": len(anns), "pos": n_pos, "neg": n_neg}


def build_fold(heldout, stems):
    fold = OUT / f"fold_{heldout}"
    train_stems = [s for s in stems if s != heldout]
    rng = random.Random(SEED)
    train_recs = []
    for s in train_stems:
        train_recs.extend(video_records(s, rng=rng))
    rng.shuffle(train_recs)
    n_valid = max(1, int(round(len(train_recs) * VALID_FRACTION)))
    valid_recs, train_recs = train_recs[:n_valid], train_recs[n_valid:]
    # test = every annotated frame of the held-out video (positives + ALL negatives,
    # uncapped: the metric is computed over the full annotated set).
    test_recs = video_records(heldout, neg_cap=None)
    stats = {
        "train": write_split(fold / "train", train_recs),
        "valid": write_split(fold / "valid", valid_recs),
        "test": write_split(fold / "test", test_recs),
        "train_videos": train_stems,
        "heldout": heldout,
    }
    (fold / "stats.json").write_text(json.dumps(stats, indent=2))
    return stats


def main():
    stems = list(gt.VIDEOS)
    OUT.mkdir(parents=True, exist_ok=True)
    all_stats = {}
    for heldout in stems:
        s = build_fold(heldout, stems)
        all_stats[heldout] = s
        print(f"fold_{heldout}: train={s['train']} valid={s['valid']} test={s['test']}")
    (OUT / "stats.json").write_text(json.dumps(all_stats, indent=2))


if __name__ == "__main__":
    main()
