"""Score every dev stem's tracks in a folder with score_v2 and write a JSON table + means.

usage: score_all.py <tracks_dir> <out.json> [--truth-dir DIR] [--stems a,b,...] [--prefix P]
Tracks file per stem: <tracks_dir>/<prefix><stem>.json. A missing tracks file is a row with scored=false.
Means skip nulls and report *_n (stems contributing); direction_ok_pct = % true among non-null.
Dev only: this script never reads the holdout truth folder.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import score_v2  # noqa: E402

DEV = ["20260915_185121_23d80f05", "20260915_185331_19de9ec7", "20260915_185454_f240c883",
       "20260915_185645_9fde3c16", "20260915_190115_a7cf2c70"]
MEAN_KEYS = ["recall_pct", "far_recall_pct", "median_px_err", "far_median_px_err", "path_err_rms", "path_err_far",
             "path_bias", "path_bias_far", "path_missing", "entry_err", "hook_err", "wall_s"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tracks_dir")
    ap.add_argument("out")
    ap.add_argument("--truth-dir", default=str(HERE / "truth"))
    ap.add_argument("--stems", default=",".join(DEV))
    ap.add_argument("--prefix", default="")
    a = ap.parse_args()
    if "pov-holdout" in a.truth_dir:
        print("score_all.py is dev-only; refusing a holdout truth dir", file=sys.stderr)
        return 2
    rows = []
    for s in [x for x in a.stems.split(",") if x]:
        tp = Path(a.tracks_dir) / f"{a.prefix}{s}.json"
        th = Path(a.truth_dir) / f"{s}.json"
        if not tp.exists() or not th.exists():
            rows.append({"stem": s, "scored": False, "error": f"missing {'tracks' if not tp.exists() else 'truth'}"})
            continue
        tr = json.loads(tp.read_text())
        row = score_v2.score(tr, json.loads(th.read_text()))
        row["wall_s"] = (tr.get("meta") or {}).get("wall_s")
        row["final_board"] = tr.get("final_board")
        row["has_path_fit"] = bool(tr.get("path_fit"))
        row["scored"] = True
        rows.append(row)
        print(f"{s[16:]} rec {row['recall_pct']} far {row['far_recall_pct']} med {row['median_px_err']}/{row['far_median_px_err']} "
              f"path {row['path_err_rms']}/{row['path_err_far']} miss {row['path_missing']} entry {row['entry_err']} "
              f"hook {row['hook_err']} dir {row['direction_ok']}", flush=True)
    means = {}
    sc = [r for r in rows if r.get("scored")]
    for k in MEAN_KEYS:
        v = [float(r[k]) for r in sc if r.get(k) is not None]
        means[k] = round(sum(v) / len(v), 2) if v else None
        means[f"{k}_n"] = len(v)
    d = [r["direction_ok"] for r in sc if r.get("direction_ok") is not None]
    means["direction_ok_pct"] = round(100.0 * sum(d) / len(d), 1) if d else None
    means["direction_ok_n"] = len(d)
    out = {"tracks_dir": str(a.tracks_dir), "truth_dir": a.truth_dir, "scorer": "score_v2.py",
           "thresholds": {"match_px": f"max(2*truth_r, {score_v2.TOL_MIN_PX})", "gap_interp_max": score_v2.GAP_MAX,
                          "far_frames": score_v2.FAR_FRAMES, "roll_tail_for_min": score_v2.ROLL_TAIL,
                          "flat_boards": score_v2.FLAT_BOARDS},
           "stems": [r["stem"] for r in rows], "rows": rows, "means": means}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps(means))
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
