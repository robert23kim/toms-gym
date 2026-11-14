#!/usr/bin/env python3
"""keydiff.py <base.summary.json> <variant.summary.json> [--expect-no-clips]

Key-path diff of two engine reports (indexed, so one item losing a key is seen). Passes when the key
sets are identical, or, with --expect-no-clips, when the ONLY difference is that
rep_metrics[].metrics[].clip_url is gone from the variant.
"""
import json
import re
import sys


def paths(node, prefix=""):
    out = set()
    if isinstance(node, dict):
        for k, v in node.items():
            out |= paths(v, f"{prefix}.{k}" if prefix else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out |= paths(v, f"{prefix}[{i}]")
    else:
        out.add(prefix)
    return out


def load(p):
    d = json.load(open(p))
    return d.get("report", d)


def main():
    base, var = paths(load(sys.argv[1])), paths(load(sys.argv[2]))
    missing, added = sorted(base - var), sorted(var - base)
    clip = re.compile(r"^rep_metrics\[\d+\]\.metrics\[\d+\]\.clip_url$")
    base_clips = [p for p in base if clip.match(p)]
    other = [p for p in missing if not clip.match(p)]
    gone = len(missing) - len(other)
    want_gone = len(base_clips) if "--expect-no-clips" in sys.argv else 0
    ok = added == [] and other == [] and gone == want_gone
    print(("PASS" if ok else "FAIL"), sys.argv[2].split("/")[-1], f"paths={len(base)} clip_url in base={len(base_clips)}",
          f"clip_url gone={gone} (want {want_gone})", "other missing:", other[:5], "added:", added[:5])
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
