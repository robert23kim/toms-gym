"""Re-score stored corners against a pin-centred truth: the annotated top
corners are shifted horizontally by the same-row pin-centre offset
(results/pin_centre_shift_same_row.json, from centre_check2.py), width unchanged.
The correction comes from the pins, not from any method, so it is the same
third-party ruler for every row. Prints a markdown table for the pre-hit frame."""
import json
import numpy as np
import common as C
L, gt = C.L, C.gt
STEMS = C.STEMS
# same-row shifts from centre_check2.py (pin centre vs the annotated centre line AT the pin-base row);
# the JSON field pin_centre_err_px compares two different rows and overstates tom_old (6.4 vs 1.7 px)
shift = {k: float(v) for k, v in json.load(open(C.RESULTS / "pin_centre_shift_same_row.json")).items()}

def mae(stem, f, corners, truth):
    pts = L.ball_points_on(stem, f)
    bt, _ = gt.board_from_corners(truth, pts)
    bp, _ = gt.board_from_corners(corners, pts)
    return float(np.mean(np.abs(bp - bt)))

methods = ["even3_prehit_k", "soft_prehit_k", "ens_prehit_k", "zoom_prehit_k", "zoom_lo_prehit_k", "tiles_prehit_k", "hires_prehit_k",
           "gutters_prehit", "landmarks_prehit", "landmarks_pin_prehit", "pins_m_prehit", "pins_prehit",
           "even3_prehit-6_k", "ens_prehit-6_k", "zoom_lo_prehit-6_k", "zoom_lo_prehit_k_tiny", "zoom_prehit-6_k_tiny"]
print("| method (pre-hit frames) | " + " | ".join(f"{C.LABEL[s].split(' (')[0]} ann. → pins" for s in STEMS) + " |")
print("|---|---|---|---|")
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
        f = r["frame"]
        corners = {k: tuple(v) for k, v in r["corners"].items()}
        truth = L.truth_corners(s, f)
        t2 = dict(truth)
        t2["top_left"] = (truth["top_left"][0] + shift[s], truth["top_left"][1])
        t2["top_right"] = (truth["top_right"][0] + shift[s], truth["top_right"][1])
        cells.append(f"{mae(s, f, corners, truth):.2f} → {mae(s, f, corners, t2):.2f}")
    print(f"| `{m}` | " + " | ".join(cells) + " |")
print("\ntop-centre shift applied (px):", {k: round(v, 1) for k, v in shift.items()})
