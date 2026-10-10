"""Shared helpers: cuts.json, cut frames in SOURCE numbering, truth (dev only, for diagnostics)."""
import json
import os

import cv2

L = "/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking"
EXP = os.path.join(L, "experiments", "lane-first")
CUTS = os.path.join(L, "work", "cuts", "cuts.json")
DEV = ["20260915_185121_23d80f05", "20260915_185331_19de9ec7", "20260915_185645_9fde3c16",
       "20260915_185454_f240c883", "20260915_190115_a7cf2c70", "20260915_191900_106ea7ca"]


def cut_entry(stem):
    for e in json.load(open(CUTS)):
        if e["stem"] == stem:
            return e
    raise KeyError(stem)


def read_cut(entry):
    """List of (source_frame, bgr) for the whole cut."""
    cap = cv2.VideoCapture(entry["cut_path"])
    out = []
    k = 0
    while True:
        ok, img = cap.read()
        if not ok:
            break
        out.append((entry["cut_start"] + k, img))
        k += 1
    cap.release()
    assert len(out) == entry["nb_frames"], (len(out), entry["nb_frames"])
    return out


def truth(stem):
    p = os.path.join(L, "truth", stem + ".json")
    return json.load(open(p)) if os.path.exists(p) else None
