"""Dump every detector box per frame of a cut, for several detector/crop/scale configs.

usage: dump_dets.py <stem> [--configs a,b,c]   -> work/dets_<stem>.json
  {"stem", "size": [W, H], "cut_start", "configs": {name: {"<source f>": [[x, y, r, conf], ...]}},
   "shifts": {"<source f>": {a, b, tx, ty, inliers}}, "timings": {name: seconds}}
All coordinates are full-frame px, frames are SOURCE numbers. Boxes are dumped at conf >= 0.05 so any
higher floor is a free filter later. The far crop is a FIXED fraction of the frame (rows FAR_Y0..FAR_Y1 of H,
cols 0..FAR_X1 of W), which is where the pins sit on a head camera looking down the lane; see NOTES.md.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
L = HERE.parents[1]
ENGINE = Path("/Users/toka/code/bowling-app/pov-engine")
FAR_Y0, FAR_Y1, FAR_X1 = 0.22, 0.62, 0.80

CONFIGS = {
    # name: (model, region, scale)
    "bowl_full320": ("bowl", "full", 320),
    "bowl_full640": ("bowl", "full", 640),
    "bowl_full1280": ("bowl", "full", 1280),
    "bowl_far1x": ("bowl", "far", 1.0),
    "bowl_far1.5x": ("bowl", "far", 1.5),
    "bowl_fullnative": ("bowl", "full", None),       # imgsz = long side rounded up to 32
    "bowl_far2x": ("bowl", "far", 2.0),
    "bowl_far3x": ("bowl", "far", 3.0),
    "world_full1280": ("world", "full", 1280),
    "world_far2x": ("world", "far", 2.0),
}


def load_model(kind):
    from ultralytics import YOLO
    if kind == "bowl":
        return YOLO(str(ENGINE / "models" / "yolo11n_bowling.pt"))
    m = YOLO(str(ENGINE / "yolov8s-worldv2.pt"))
    m.set_classes(["bowling ball"])
    return m


def r32(v):
    return int(np.ceil(v / 32) * 32)


def detect(model, im, region, scale, conf, W, H):
    if region == "full":
        imgsz = r32(max(W, H)) if scale is None else int(scale)
        src, ox, oy, s = im, 0.0, 0.0, 1.0
    else:
        y0, y1, x1 = int(FAR_Y0 * H), int(FAR_Y1 * H), int(FAR_X1 * W)
        crop = im[y0:y1, 0:x1]
        src = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        ox, oy, s = 0.0, float(y0), float(scale)
        imgsz = r32(max(src.shape[:2]))
    res = model(src, conf=conf, imgsz=imgsz, verbose=False)[0]
    rows = []
    if res.boxes is not None and len(res.boxes):
        for b, c in zip(res.boxes.xyxy.cpu().numpy(), res.boxes.conf.cpu().numpy()):
            x1, y1, x2, y2 = [float(v) for v in b]
            cx, cy, r = (x1 + x2) / 2 / s + ox, (y1 + y2) / 2 / s + oy, max(x2 - x1, y2 - y1) / 2 / s
            rows.append([round(cx, 1), round(cy, 1), round(r, 1), round(float(c), 3)])
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stem")
    ap.add_argument("--configs", default=",".join(CONFIGS))
    ap.add_argument("--conf", type=float, default=0.05)
    args = ap.parse_args()
    cuts = {c["stem"]: c for c in json.load(open(L / "work/cuts/cuts.json"))}
    c = cuts[args.stem]
    out_path = HERE / "work" / f"dets_{args.stem}.json"
    doc = json.load(open(out_path)) if out_path.exists() else {"stem": args.stem, "cut_start": c["cut_start"], "configs": {}, "timings": {}}
    names = [n for n in args.configs.split(",") if n]
    cap = cv2.VideoCapture(c["cut_path"])
    W, H = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    doc["size"] = [W, H]
    frames = []
    while True:
        ok, im = cap.read()
        if not ok:
            break
        frames.append(im)
    cap.release()
    print(f"{args.stem}: {len(frames)} frames {W}x{H}", flush=True)
    if "shifts" not in doc:
        t0 = time.time()
        orb = cv2.ORB_create(2000)
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        prev, shifts = None, {}
        for k, im in enumerate(frames):
            g = cv2.cvtColor(cv2.resize(im, None, fx=0.5, fy=0.5), cv2.COLOR_BGR2GRAY)
            kp, d = orb.detectAndCompute(g, None)
            if prev is not None and d is not None and prev[1] is not None:
                m = bf.match(prev[1], d)
                if len(m) >= 20:
                    p1 = np.float32([prev[0][x.queryIdx].pt for x in m])
                    p2 = np.float32([kp[x.trainIdx].pt for x in m])
                    M, inl = cv2.estimateAffinePartial2D(p1, p2, method=cv2.RANSAC, ransacReprojThreshold=3)
                    if M is not None:
                        shifts[str(c["cut_start"] + k)] = {"a": float(M[0, 0]), "b": float(M[0, 1]), "tx": float(M[0, 2]) * 2,
                                                            "ty": float(M[1, 2]) * 2, "inliers": int(inl.sum()) if inl is not None else 0}
            prev = (kp, d)
        doc["shifts"] = shifts
        doc["timings"]["orb"] = round(time.time() - t0, 1)
    models = {}
    for name in names:
        kind, region, scale = CONFIGS[name]
        if kind not in models:
            models[kind] = load_model(kind)
        t0 = time.time()
        per = {}
        for k, im in enumerate(frames):
            per[str(c["cut_start"] + k)] = detect(models[kind], im, region, scale, args.conf, W, H)
        doc["configs"][name] = per
        doc["timings"][name] = round(time.time() - t0, 1)
        nb = sum(len(v) for v in per.values())
        print(f"  {name}: {nb} boxes, {doc['timings'][name]}s", flush=True)
        json.dump(doc, open(out_path, "w"))
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(ENGINE))
    sys.exit(main())
