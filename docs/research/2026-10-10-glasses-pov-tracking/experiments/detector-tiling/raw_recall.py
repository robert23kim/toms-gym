"""Raw any-box recall by distance band, before linking.

usage: raw_recall.py <stem> [<stem> ...]  -> prints a table; writes work/raw_recall.json
A truth frame (in [release, pin_hit], not ball_invisible) is hit when any box of the config at conf >= floor
is within max(2 r, 20 px) of the truth centre AND its radius is within [0.4 r, 3 r + 6 px] (the r guard stops a
lane-wide box from counting). Bands: near / mid / far = thirds of the truth frames by order.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
L = HERE.parents[1]
FLOORS = [0.05, 0.1, 0.2, 0.3]


def truth_points(stem):
    t = json.load(open(L / "truth" / f"{stem}.json"))
    lo, hi = t["release_frame"], t["pin_hit_frame"]
    hidden = {f for a, b in t.get("ball_invisible", []) for f in range(a, b + 1)}
    pts = []
    for k, v in t["ball"].items():
        f = int(k)
        x, y, r = (v.get("x"), v.get("y"), v.get("r")) if isinstance(v, dict) else (v[0], v[1], v[2])
        if x is None or f < lo or f > hi or f in hidden:
            continue
        pts.append((f, float(x), float(y), float(r or 0)))
    return sorted(pts)


def hit(boxes, x, y, r, floor):
    tol = max(2 * r, 20.0)
    for bx, by, br, bc in boxes:
        if bc < floor:
            continue
        if not (0.4 * r <= br <= 3 * r + 6):
            continue
        if ((bx - x) ** 2 + (by - y) ** 2) ** 0.5 <= tol:
            return True
    return False


def main():
    out = {}
    for stem in sys.argv[1:]:
        d = json.load(open(HERE / "work" / f"dets_{stem}.json"))
        pts = truth_points(stem)
        n = len(pts)
        bands = {"near": pts[: n // 3], "mid": pts[n // 3: 2 * n // 3], "far": pts[2 * n // 3:]}
        out[stem] = {}
        print(f"\n{stem} ({n} truth frames; bands {[ (b[0][0], b[-1][0]) for b in bands.values()]})")
        print(f"{'config':18s} {'floor':>5s} {'near':>6s} {'mid':>6s} {'far':>6s} {'all':>6s}")
        for name, per in d["configs"].items():
            for fl in FLOORS:
                row = {}
                for bn, bp in bands.items():
                    h = sum(hit(per.get(str(f), []), x, y, r, fl) for f, x, y, r in bp)
                    row[bn] = round(100 * h / max(1, len(bp)), 1)
                h = sum(hit(per.get(str(f), []), x, y, r, fl) for f, x, y, r in pts)
                row["all"] = round(100 * h / max(1, n), 1)
                out[stem][f"{name}@{fl}"] = row
                print(f"{name:18s} {fl:5.2f} {row['near']:6.1f} {row['mid']:6.1f} {row['far']:6.1f} {row['all']:6.1f}")
    p = HERE / "work" / "raw_recall.json"
    prev = json.load(open(p)) if p.exists() else {}
    prev.update(out)
    json.dump(prev, open(p, "w"), indent=1)


if __name__ == "__main__":
    main()
