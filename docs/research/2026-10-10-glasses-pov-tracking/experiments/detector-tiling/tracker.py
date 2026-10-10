"""Multi-scale box pool -> engine yolo_chain -> track.

The fine-tuned YOLO11n is scale-specific (NOTES.md): the release ball (r 90-130 px) is only found at imgsz 320/640,
the mid roll at 1280, the far end (r 4-13 px) only at native resolution. So the pool per frame is the union of the
boxes from several inference scales, deduplicated, and the engine's chain links it.
"""
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Sequence

import numpy as np

ENGINE = "/Users/toka/code/bowling-app/pov-engine"
if ENGINE not in sys.path:
    sys.path.insert(0, ENGINE)
from src.bowling.trajectory.yolo_chain import ChainConfig, chain_detections  # noqa: E402

Box = List[float]  # x, y, r, conf


@dataclass
class PoolConfig:
    # config name -> conf floor; a box from that config below its floor is dropped
    floors: Dict[str, float] = field(default_factory=lambda: {
        "bowl_full320": 0.1, "bowl_full640": 0.1, "bowl_full1280": 0.1, "bowl_far1x": 0.1})
    merge_k: float = 0.75   # two boxes closer than merge_k * max(r) are the same object
    max_r_frac: float = 0.25  # a box wider than this fraction of the frame width is the lane / the bowler, not a ball


def pool_frame(cfg_boxes: Dict[str, Sequence[Box]], pc: PoolConfig, W: int) -> List[Box]:
    """Union of the configs' boxes; boxes of one object (closer than merge_k x the larger r) are merged into the
    most confident one, whose radius becomes the MEDIAN over the merged boxes: each inference scale draws the
    same ball at a different looseness (640: r 38, 1280: r 20 on the 185121 ball at frame 317) and taking the
    tightest or the most confident box alone makes r jump by 1.5-2x between frames and breaks the chain."""
    cand = []
    for name, floor in pc.floors.items():
        for x, y, r, c in cfg_boxes.get(name, []):
            if c >= floor and r <= pc.max_r_frac * W:
                cand.append([float(x), float(y), float(r), float(c), [float(r)]])
    cand.sort(key=lambda b: -b[3])
    out: List[List] = []
    for b in cand:
        for o in out:
            if np.hypot(b[0] - o[0], b[1] - o[1]) <= pc.merge_k * max(b[2], o[2]):
                o[4].append(b[2])
                break
        else:
            out.append(b)
    return [[o[0], o[1], float(np.median(o[4])), o[3]] for o in out]


def build_pool(doc: dict, pc: PoolConfig) -> Dict[int, List[Box]]:
    W = doc["size"][0]
    frames = set()
    for name in pc.floors:
        frames |= set(doc["configs"].get(name, {}).keys())
    pool = {}
    for k in sorted(frames, key=int):
        pool[int(k)] = pool_frame({n: doc["configs"].get(n, {}).get(k, []) for n in pc.floors}, pc, W)
    return pool


def shifts_of(doc: dict) -> Dict[int, dict]:
    return {int(k): v for k, v in doc.get("shifts", {}).items()}


def run_chain(doc: dict, pc: PoolConfig = PoolConfig(), cc: ChainConfig = ChainConfig()):
    pool = build_pool(doc, pc)
    positions, report = chain_detections(pool, shifts_of(doc), cc)
    report["pool_boxes"] = sum(len(v) for v in pool.values())
    return positions, report, pool
