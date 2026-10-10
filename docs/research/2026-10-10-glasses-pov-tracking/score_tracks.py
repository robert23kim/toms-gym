"""Score one tracks.json against one truth.json.

usage: score_tracks.py <tracks.json> <truth.json>   -> prints one JSON object

recall_pct     : % of truth ball frames (truth `ball` keys, NOT interpolated) in [release_frame, pin_hit_frame]
                 minus `ball_invisible` ranges that have a track point at that frame, or one linearly interpolated
                 between consecutive track frames a<b with b-a <= 6, within max(2 * truth r, 20) px.
median_px_err  : median distance over the matched frames.
board_err      : |final_board - truth.board| (null if either is null).
lane_err_boards: mean over truth lane frames (lane_quads, else lane.ref_frames pin_end_row) of
                 |centre offset| + 0.5 * |width error| at the truth pin row, in boards (truth width / 39),
                 using the tracker quad at the nearest frame within 3 (edges extended pd->fl). Null if none.
window_err     : [|release - truth|, |pin_hit - truth|] (null entries when missing).
pass           : recall_pct >= 60 and board_err <= 3;  strong: recall_pct >= 80 and board_err <= 2.
"""
import json
import math
import statistics
import sys

GAP_MAX = 6
TOL_MIN_PX = 20.0
LANE_NEAREST = 3
PASS_RECALL, PASS_BOARD = 60.0, 3.0
STRONG_RECALL, STRONG_BOARD = 80.0, 2.0


def ball_point(p):
    """Truth ball entry as (x, y, r): dict {x, y, r} or list [x, y, r]."""
    if isinstance(p, dict):
        if p.get("x") is None or p.get("y") is None:
            return None
        return float(p["x"]), float(p["y"]), float(p.get("r") or 0.0)
    if isinstance(p, (list, tuple)) and len(p) >= 2 and p[0] is not None and p[1] is not None:
        return float(p[0]), float(p[1]), float(p[2] or 0.0) if len(p) > 2 else 0.0
    return None


def truth_frames(truth):
    lo, hi = truth.get("release_frame"), truth.get("pin_hit_frame")
    if lo is None or hi is None:
        return {}
    hidden = {f for a, b in truth.get("ball_invisible", []) for f in range(int(a), int(b) + 1)}
    out = {}
    for k, p in (truth.get("ball") or {}).items():
        f, bp = int(k), ball_point(p)
        if lo <= f <= hi and f not in hidden and bp is not None:
            out[f] = bp
    return out


def track_at(track, fs, f):
    if f in track:
        return track[f]
    import bisect
    i = bisect.bisect_left(fs, f)
    if i == 0 or i >= len(fs):
        return None
    a, b = fs[i - 1], fs[i]
    if b - a > GAP_MAX:
        return None
    t = (f - a) / (b - a)
    return (track[a][0] + t * (track[b][0] - track[a][0]), track[a][1] + t * (track[b][1] - track[a][1]))


def line_x(p, q, y):
    (x1, y1), (x2, y2) = p, q
    if abs(y2 - y1) < 1e-9:
        return float(x1)
    return x1 + (x2 - x1) * (y - y1) / (y2 - y1)


def truth_lane_rows(truth):
    rows = {}
    for k, q in (truth.get("lane_quads") or {}).items():
        y = (q["pd_l"][1] + q["pd_r"][1]) / 2.0
        rows[int(k)] = (y, float(q["pd_l"][0]), float(q["pd_r"][0]))
    if not rows:
        for k, rf in ((truth.get("lane") or {}).get("ref_frames") or {}).items():
            pr = rf.get("pin_end_row")
            if pr and pr.get("left_x") is not None and pr.get("right_x") is not None:
                rows[int(k)] = (float(pr["y"]), float(pr["left_x"]), float(pr["right_x"]))
    return rows


def lane_error(tracks, truth):
    lanes = {int(k): v for k, v in (tracks.get("lane") or {}).items()}
    per = []
    for f, (y, tl, tr) in sorted(truth_lane_rows(truth).items()):
        cands = [g for g in lanes if abs(g - f) <= LANE_NEAREST]
        if not cands:
            per.append({"f": f, "err": None})
            continue
        g = min(cands, key=lambda g: (abs(g - f), g))
        q = lanes[g]
        el, er = line_x(q["pd_l"], q["fl_l"], y), line_x(q["pd_r"], q["fl_r"], y)
        el, er = min(el, er), max(el, er)
        bw = (tr - tl) / 39.0
        if bw <= 0:
            per.append({"f": f, "err": None})
            continue
        centre = abs((el + er) / 2 - (tl + tr) / 2) / bw
        width = abs((er - el) - (tr - tl)) / bw
        per.append({"f": f, "g": g, "centre_boards": round(centre, 2), "width_boards": round(width, 2),
                    "err": round(centre + 0.5 * width, 2)})
    vals = [p["err"] for p in per if p["err"] is not None]
    return (round(sum(vals) / len(vals), 2) if vals else None), per


def score(tracks, truth):
    tf = truth_frames(truth)
    track = {}
    for p in tracks.get("frames") or []:
        if p.get("x") is None or p.get("y") is None:
            continue
        track[int(p["f"])] = (float(p["x"]), float(p["y"]))
    fs = sorted(track)
    errs, matched = [], 0
    for f, (x, y, r) in tf.items():
        e = track_at(track, fs, f)
        if e is None:
            continue
        d = math.hypot(e[0] - x, e[1] - y)
        if d <= max(2 * r, TOL_MIN_PX):
            matched += 1
            errs.append(d)
    n = len(tf)
    fb, tb = tracks.get("final_board"), truth.get("board")
    board_err = None if fb is None or tb is None else round(abs(float(fb) - float(tb)), 2)
    lane_err, lane_per = lane_error(tracks, truth)

    def werr(k):
        a, b = tracks.get(k), truth.get(k)
        return None if a is None or b is None else abs(int(a) - int(b))
    recall = round(100.0 * matched / n, 1) if n else 0.0
    ok = lambda rt, bt: bool(recall >= rt and board_err is not None and board_err <= bt)  # noqa: E731
    return {
        "stem": tracks.get("stem"), "method": tracks.get("method"),
        "recall_pct": recall, "n_matched": matched, "n_truth_points": n,
        "median_px_err": round(statistics.median(errs), 1) if errs else None,
        "board_err": board_err, "lane_err_boards": lane_err, "lane_err_per_frame": lane_per,
        "window_err": [werr("release_frame"), werr("pin_hit_frame")],
        "pass": ok(PASS_RECALL, PASS_BOARD), "strong": ok(STRONG_RECALL, STRONG_BOARD),
    }


def main():
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    tracks = json.load(open(sys.argv[1]))
    truth = json.load(open(sys.argv[2]))
    print(json.dumps(score(tracks, truth)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
