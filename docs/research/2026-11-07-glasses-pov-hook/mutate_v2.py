"""Mutation checks for score_v2.py on real loop-1 tracks (in memory; nothing on disk is changed).

usage: mutate_v2.py  -> prints one JSON list and writes results/mutations_v2.json
"""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import score_v2  # noqa: E402

L1 = Path("/Users/toka/code/toms_gym/docs/research/2026-10-10-glasses-pov-tracking")


def load(stem):
    tr = json.loads((L1 / "results" / "tracks" / f"{stem}.json").read_text())
    th = json.loads((HERE / "truth" / f"{stem}.json").read_text())
    return tr, th


def empty(tr, th):
    t = copy.deepcopy(tr)
    t["frames"] = []
    return t


def shift_far(tr, th, dx=25.0):
    t = copy.deepcopy(tr)
    lo = th["pin_hit_frame"] - score_v2.FAR_FRAMES
    n = 0
    for p in t["frames"]:
        if p["f"] >= lo:
            p["x"] = float(p["x"]) + dx
            n += 1
    assert n > 0, "shift touched no frame"
    return t


def mirror(tr, th):
    t = copy.deepcopy(tr)
    t["boards"] = {k: round(40.0 - v, 2) for k, v in t["boards"].items()}
    for e in t.get("lane_top_down") or []:
        if e.get("board") is not None:
            e["board"] = round(40.0 - e["board"], 2)
    if t.get("final_board") is not None:
        t["final_board"] = 40.0 - t["final_board"]
    return t


def early_final(tr, th, k=2):
    t = copy.deepcopy(tr)
    t["final_board"] = t["boards"][str(th["pin_hit_frame"] - k)]
    return t


def truth_as_track(tr, th):
    """Identity: a track equal to the truth path must score recall 100 and zero board errors."""
    p = th["path"]
    return {"stem": th["stem"], "method": "truth", "frames": [{"f": q["f"], "x": q["x"], "y": q["y"], "r": q["r"]} for q in p],
            "boards": {str(q["f"]): q["board"] for q in p}, "final_board": th["entry"]["board"],
            "release_frame": th["release_frame"], "pin_hit_frame": th["pin_hit_frame"],
            "path_fit": {"kind": "truth", "board_at_60ft": th["entry"]["board"], "min_board": th["min_board"]}}


def path_fit_only(tr, th):
    """path_fit branch: boards and lane_top_down removed, boards_by_frame from the old boards shifted +3."""
    t = copy.deepcopy(tr)
    bb = {k: v + 3.0 for k, v in t["boards"].items()}
    t["boards"], t["lane_top_down"] = {}, []
    t["path_fit"] = {"kind": "test", "board_at_60ft": (t["final_board"] or 0) + 3.0, "boards_by_frame": bb}
    return t


CASES = [
    ("a_empty_frames", "20260915_185454_f240c883", empty, ["recall_pct", "far_recall_pct"]),
    ("a_empty_frames", "20260915_190115_a7cf2c70", empty, ["recall_pct", "far_recall_pct"]),
    ("b_shift_far_25px", "20260915_185454_f240c883", shift_far, ["far_recall_pct", "recall_pct", "far_median_px_err", "median_px_err"]),
    ("b_shift_far_25px", "20260915_190115_a7cf2c70", shift_far, ["far_recall_pct", "recall_pct", "far_median_px_err", "median_px_err"]),
    ("c_mirror_boards", "20260915_185331_19de9ec7", mirror, ["path_err_rms", "path_err_far", "direction_ok", "track_trend_boards"]),
    ("c_mirror_boards", "20260915_190115_a7cf2c70", mirror, ["path_err_rms", "path_err_far", "direction_ok", "track_trend_boards"]),
    ("c_mirror_boards", "20260915_185454_f240c883", mirror, ["path_err_rms", "path_err_far", "direction_ok", "track_trend_boards"]),
    ("d_final_board_2_early", "20260915_185331_19de9ec7", early_final, ["entry_err", "hook_err"]),
    ("d_final_board_2_early", "20260915_185454_f240c883", early_final, ["entry_err", "hook_err"]),
    ("d_final_board_2_early", "20260915_190115_a7cf2c70", early_final, ["entry_err", "hook_err"]),
    ("e_truth_as_track", "20260915_190115_a7cf2c70", truth_as_track, ["recall_pct", "far_recall_pct", "path_err_rms", "entry_err", "hook_err", "direction_ok"]),
    ("e_truth_as_track", "20260915_185331_19de9ec7", truth_as_track, ["recall_pct", "far_recall_pct", "path_err_rms", "entry_err", "hook_err", "direction_ok"]),
    ("f_path_fit_branch_plus3", "20260915_185454_f240c883", path_fit_only, ["path_err_rms", "path_bias", "entry_err", "path_sources"]),
]


def main():
    out = []
    for name, stem, fn, metrics in CASES:
        tr, th = load(stem)
        before = score_v2.score(tr, th)
        after = score_v2.score(fn(tr, th), th)
        row = {"name": name, "stem": stem, "before": {m: before[m] for m in metrics}, "after": {m: after[m] for m in metrics},
               "context": {"n_truth_points": before["n_truth_points"], "n_far_points": before["n_far_points"],
                           "track_trend_boards": before["track_trend_boards"], "truth_trend_boards": before["truth_trend_boards"]}}
        out.append(row)
        print(json.dumps(row))
    (HERE / "results" / "mutations_v2.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
