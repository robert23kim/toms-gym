"""Loop-2 scorer: one tracks.json against one truth v2 json (ball path + per-frame board + entry + hook).

usage: score_v2.py <tracks.json> <truth.json>   -> prints one JSON object

Truth path frames = truth.path entries with release_frame <= f <= pin_hit_frame (sparse: 13-15 per dev stem).
Far window = truth path frames with pin_hit-12 <= f <= pin_hit. All windows use the TRUTH release/pin_hit.

recall_pct / far_recall_pct : % of (far) truth path frames with a track point at f, or one linearly interpolated
                              between consecutive track frames a<b with b-a <= 6, within max(2 * truth r, 15) px.
median_px_err / far_median_px_err : median distance over every (far) truth frame that HAS a track point
                              (matched or not); median_px_err_matched is loop 1's matched-only median.
track board at f            : tracks.boards[str(f)], else lane_top_down entry with that f (.board), else
                              path_fit.boards_by_frame[str(f)] (a per-frame evaluation the track may provide).
                              No interpolation. Frames with none are counted in path_missing / path_missing_far.
path_err_rms / path_err_far : RMS of (track board - truth path board) over the (far) truth frames with a track board.
entry_err                   : |entry - truth.entry.board|, entry = path_fit.board_at_60ft if present else final_board.
hook_err                    : |(entry - min)_track - (entry_board - min_board)_truth|; track min = path_fit.min_board
                              if present, else the min of the track board series over frames
                              release + 0.4 * (pin_hit - release) .. pin_hit (raw boards, no smoothing).
direction_ok                : least-squares slope x 12 over the far window, track (every track board frame in the
                              window) and truth (truth path points); ok when the signs agree, or both |delta| < 1.
window_err                  : [|release - truth|, |pin_hit - truth|].
Boards: 1-39 from the right gutter; the ball moving right = board falling, a hook back left = board rising.
"""
import bisect
import json
import math
import statistics
import sys

GAP_MAX = 6
TOL_MIN_PX = 15.0
FAR_FRAMES = 12
ROLL_TAIL = 0.6
FLAT_BOARDS = 1.0


def path_frames(truth):
    lo, hi = truth.get("release_frame"), truth.get("pin_hit_frame")
    out = {}
    for p in truth.get("path") or []:
        if p.get("x") is None or p.get("y") is None:
            continue
        f = int(p["f"])
        if lo is not None and hi is not None and not lo <= f <= hi:
            continue
        out[f] = p
    return out


def track_points(tracks):
    return {int(p["f"]): (float(p["x"]), float(p["y"])) for p in tracks.get("frames") or []
            if p.get("x") is not None and p.get("y") is not None}


def track_at(track, fs, f):
    if f in track:
        return track[f]
    i = bisect.bisect_left(fs, f)
    if i == 0 or i >= len(fs):
        return None
    a, b = fs[i - 1], fs[i]
    if b - a > GAP_MAX:
        return None
    t = (f - a) / (b - a)
    return (track[a][0] + t * (track[b][0] - track[a][0]), track[a][1] + t * (track[b][1] - track[a][1]))


def board_series(tracks):
    """{f: (board, source)} with the priority boards > lane_top_down > path_fit.boards_by_frame."""
    out = {}
    pf = (tracks.get("path_fit") or {}).get("boards_by_frame") or {}
    for k, v in pf.items():
        if v is not None:
            out[int(k)] = (float(v), "path_fit")
    for e in tracks.get("lane_top_down") or []:
        if e.get("board") is not None:
            out[int(e["f"])] = (float(e["board"]), "lane_top_down")
    for k, v in (tracks.get("boards") or {}).items():
        if v is not None:
            out[int(k)] = (float(v), "boards")
    return out


def rms(v):
    return round(math.sqrt(sum(x * x for x in v) / len(v)), 2) if v else None


def med(v):
    return round(statistics.median(v), 1) if v else None


def slope12(pts):
    if len(pts) < 2:
        return None
    n = len(pts)
    mf = sum(f for f, _ in pts) / n
    mb = sum(b for _, b in pts) / n
    den = sum((f - mf) ** 2 for f, _ in pts)
    if den <= 0:
        return None
    return round(FAR_FRAMES * sum((f - mf) * (b - mb) for f, b in pts) / den, 2)


def score(tracks, truth):
    tf = path_frames(truth)
    rel, pin = truth.get("release_frame"), truth.get("pin_hit_frame")
    far_lo = None if pin is None else pin - FAR_FRAMES
    is_far = lambda f: far_lo is not None and far_lo <= f <= pin  # noqa: E731
    track = track_points(tracks)
    fs = sorted(track)
    d_all, d_far, d_matched = [], [], []
    m_all = m_far = 0
    n_far = sum(1 for f in tf if is_far(f))
    for f, p in tf.items():
        e = track_at(track, fs, f)
        if e is None:
            continue
        d = math.hypot(e[0] - float(p["x"]), e[1] - float(p["y"]))
        ok = d <= max(2 * float(p.get("r") or 0.0), TOL_MIN_PX)
        d_all.append(d)
        if ok:
            m_all += 1
            d_matched.append(d)
        if is_far(f):
            d_far.append(d)
            m_far += ok
    n = len(tf)

    bs = board_series(tracks)
    errs, errs_far, src = [], [], {}
    miss = miss_far = 0
    for f, p in tf.items():
        if p.get("board") is None:
            continue
        if f not in bs:
            miss += 1
            miss_far += is_far(f)
            continue
        b, s = bs[f]
        src[s] = src.get(s, 0) + 1
        errs.append(b - float(p["board"]))
        if is_far(f):
            errs_far.append(b - float(p["board"]))

    pf = tracks.get("path_fit") or {}
    entry = pf.get("board_at_60ft") if pf.get("board_at_60ft") is not None else tracks.get("final_board")
    t_entry = (truth.get("entry") or {}).get("board")
    entry_err = None if entry is None or t_entry is None else round(abs(float(entry) - float(t_entry)), 2)

    t_min = truth.get("min_board")
    if pf.get("min_board") is not None:
        tr_min, tr_min_src = float(pf["min_board"]), "path_fit"
    else:
        tail_lo = None if rel is None or pin is None else rel + (1.0 - ROLL_TAIL) * (pin - rel)
        tail = [b for f, (b, _) in bs.items() if tail_lo is not None and tail_lo <= f <= pin]
        tr_min, tr_min_src = (min(tail), "series_last60") if tail else (None, None)
    track_hook = None if entry is None or tr_min is None else round(float(entry) - tr_min, 2)
    truth_hook = None if t_entry is None or t_min is None else round(float(t_entry) - float(t_min), 2)
    hook_err = None if track_hook is None or truth_hook is None else round(abs(track_hook - truth_hook), 2)

    tr_trend = slope12([(f, b) for f, (b, _) in sorted(bs.items()) if is_far(f)])
    tt_trend = slope12([(f, float(p["board"])) for f, p in sorted(tf.items()) if is_far(f) and p.get("board") is not None])
    if tr_trend is None or tt_trend is None:
        direction_ok = None
    else:
        same = (tr_trend > 0) == (tt_trend > 0) and tr_trend != 0 and tt_trend != 0
        direction_ok = bool(same or (abs(tr_trend) < FLAT_BOARDS and abs(tt_trend) < FLAT_BOARDS))

    def werr(k):
        a, b = tracks.get(k), truth.get(k)
        return None if a is None or b is None else abs(int(a) - int(b))

    return {
        "stem": tracks.get("stem"), "method": tracks.get("method"), "stage": tracks.get("stage"),
        "recall_pct": round(100.0 * m_all / n, 1) if n else 0.0, "n_matched": m_all, "n_truth_points": n,
        "far_recall_pct": round(100.0 * m_far / n_far, 1) if n_far else None, "n_far_matched": m_far,
        "n_far_points": n_far,
        "median_px_err": med(d_all), "far_median_px_err": med(d_far), "median_px_err_matched": med(d_matched),
        "path_err_rms": rms(errs), "path_err_far": rms(errs_far), "path_bias": round(sum(errs) / len(errs), 2) if errs else None,
        "path_bias_far": round(sum(errs_far) / len(errs_far), 2) if errs_far else None,
        "path_missing": miss, "path_missing_far": miss_far, "path_sources": src,
        "entry": None if entry is None else round(float(entry), 2), "entry_err": entry_err,
        "track_min_board": None if tr_min is None else round(tr_min, 2), "track_min_src": tr_min_src,
        "track_hook": track_hook, "truth_hook": truth_hook, "hook_err": hook_err,
        "track_trend_boards": tr_trend, "truth_trend_boards": tt_trend, "direction_ok": direction_ok,
        "window_err": [werr("release_frame"), werr("pin_hit_frame")],
    }


def main():
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    with open(sys.argv[1]) as fh:
        tracks = json.load(fh)
    with open(sys.argv[2]) as fh:
        truth = json.load(fh)
    print(json.dumps(score(tracks, truth)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
