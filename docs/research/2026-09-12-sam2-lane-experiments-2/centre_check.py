"""Far-end centre check: the standing pin cluster's centre is the lane centre
at the pin deck, independent of any hand-clicked corner. Compare each method's
predicted top centre (mean x of its top corners) with the pin centre and with
the annotated centre, on the pre-hit frame. Prints a markdown table."""
import json
import common as C
STEMS = C.STEMS
pins = {}
for r in json.load(open(C.RESULTS / "pins_m_prehit.json")):
    pins[r["stem"]] = (r["pin_centre_px"], r["truth_centre_px"], r["pin_lane_width_px"], r["truth_top_width_px"])
methods = ["even3_prehit_k", "soft_prehit_k", "ens_prehit_k", "zoom_lo_prehit_k", "zoom_prehit_k", "tiles_prehit_k", "hires_prehit_k",
           "gutters_prehit", "landmarks_prehit", "landmarks_pin_prehit", "pins_m_prehit", "pins_prehit"]
print("| top centre, px | " + " | ".join(C.LABEL[s].split(" (")[0] for s in STEMS) + " |")
print("|---|---|---|---|")
print("| pin cluster centre − annotated centre | " + " | ".join(f"{pins[s][0] - pins[s][1]:+.1f}" for s in STEMS) + " |")
print("| pin-derived width / annotated width | " + " | ".join(f"{pins[s][2] / pins[s][3]:.3f}" for s in STEMS) + " |")
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
        c = 0.5 * (r["corners"]["top_left"][0] + r["corners"]["top_right"][0])
        w = r["corners"]["top_right"][0] - r["corners"]["top_left"][0]
        cells.append(f"{c - pins[s][0]:+.1f} vs pins, {c - pins[s][1]:+.1f} vs ann. (w {w:.0f})")
    print(f"| `{m}` | " + " | ".join(cells) + " |")
