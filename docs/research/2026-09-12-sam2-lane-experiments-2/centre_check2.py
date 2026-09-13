"""Depth-consistent far-end centre check. The pin cluster centre is measured at
the row where the pin bases sit (annotated top row + pin_base_dy). Evaluate the
annotated lane's centre line and each method's centre line AT THAT ROW, so a
lane whose two edges have different slopes (tom_old: left -1.13 px/row, right
-0.30) is not compared across rows. Prints a markdown table and the shifts to
use for a pin-centred re-scoring."""
import json
import common as C
L = C.L
STEMS = C.STEMS
pins = {}
for r in json.load(open(C.RESULTS / "pins_m_prehit.json")):
    pins[r["stem"]] = (r["pin_centre_px"], r["pin_base_dy"], r["frame"])

def centre_at(corners, y):
    (lx1, ly1), (lx2, ly2) = corners["top_left"], corners["bottom_left"]
    (rx1, ry1), (rx2, ry2) = corners["top_right"], corners["bottom_right"]
    lx = lx1 + (y - ly1) / (ly2 - ly1) * (lx2 - lx1)
    rx = rx1 + (y - ry1) / (ry2 - ry1) * (rx2 - rx1)
    return 0.5 * (lx + rx), rx - lx

rows_out = []
shift = {}
for s in STEMS:
    pc, dy, f = pins[s]
    t = L.truth_corners(s, f)
    y_top = min(t["top_left"][1], t["top_right"][1])
    yb = y_top + dy
    tc, tw = centre_at(t, yb)
    tc_top, _ = centre_at(t, y_top)
    shift[s] = round(pc - tc, 2)
    rows_out.append((s, yb, pc, tc, tc_top))
print("| | " + " | ".join(C.LABEL[s].split(" (")[0] for s in STEMS) + " |")
print("|---|---|---|---|")
print("| pin-base row (annotated top row + dy) | " + " | ".join(f"{r[1]:.1f} ({pins[r[0]][1]:+.1f})" for r in rows_out) + " |")
print("| annotated centre: at top row → at pin-base row | " + " | ".join(f"{r[4]:.1f} → {r[3]:.1f}" for r in rows_out) + " |")
print("| pin cluster centre − annotated centre, same row | " + " | ".join(f"{r[2] - r[3]:+.1f}" for r in rows_out) + " |")
methods = ["even3_prehit_k", "soft_prehit_k", "ens_prehit_k", "zoom_lo_prehit_k", "tiles_prehit_k", "hires_prehit_k", "gutters_prehit",
           "landmarks_prehit", "pins_m_prehit", "pins_prehit", "even3_prehit-6_k"]
for m in methods:
    try:
        rows = {r["stem"]: r for r in json.load(open(C.RESULTS / f"{m}.json"))}
    except FileNotFoundError:
        continue
    cells = []
    for s in STEMS:
        r = rows.get(s)
        if not r or not r.get("ok"):
            cells.append("·")
            continue
        pc, dy, f = pins[s]
        t = L.truth_corners(s, r["frame"])
        y_top = min(t["top_left"][1], t["top_right"][1])
        c, w = centre_at({k: tuple(v) for k, v in r["corners"].items()}, y_top + dy)
        tc, _ = centre_at(t, y_top + dy)
        cells.append(f"{c - pc:+.1f} vs pins, {c - tc:+.1f} vs ann.")
    print(f"| `{m}` | " + " | ".join(cells) + " |")
print("\nsame-row shift (pins − annotation), px:", shift)
json.dump(shift, open(C.RESULTS / "pin_centre_shift_same_row.json", "w"))
