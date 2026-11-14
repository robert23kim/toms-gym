#!/usr/bin/env python3
"""summarize_image.py <img-out-dir> : prod-image (emulated) runs per fixture, config and round.

Dirs are <cfg>-r<k> with cfg in base (image code), A (worktree, flags off), B (flags on).
non_pose = wall - pose for rep lifts (render, re-encode, clip publish); plank shows wall only.
"""
import collections
import glob
import json
import os
import sys


def main():
    runs = collections.defaultdict(dict)
    for f in glob.glob(os.path.join(sys.argv[1], "*-r[0-9]", "*.timing.json")):
        cfg, r = os.path.basename(os.path.dirname(f)).rsplit("-r", 1)
        d = json.load(open(f))
        pose = d["analyze_breakdown"].get("pose")
        runs[d["fixture"]][(int(r), cfg)] = (d["wall_s"], pose, None if pose is None else d["wall_s"] - pose)
    print("| fixture | round | base wall / pose / non-pose s | off (A) | on (B) | non-pose on vs off | wall on vs off |")
    print("|---|---|---|---|---|---|---|")
    for fx in sorted(runs):
        for r in sorted({k[0] for k in runs[fx]}):
            cells = []
            for cfg in ("base", "A", "B"):
                v = runs[fx].get((r, cfg))
                cells.append("-" if v is None else (f"{v[0]:.1f} / {v[1]:.1f} / {v[2]:.1f}" if v[1] is not None else f"{v[0]:.1f}"))
            a, b = runs[fx].get((r, "A")), runs[fx].get((r, "B"))
            np_ = f"{a[2]:.1f} -> {b[2]:.1f} ({100 * (b[2] - a[2]) / a[2]:+.0f}%)" if a and b and a[2] else "-"
            wall = f"{a[0] / b[0]:.2f}x" if a and b else "-"
            print(f"| {fx} | {r} | {cells[0]} | {cells[1]} | {cells[2]} | {np_} | {wall} |")


if __name__ == "__main__":
    main()
