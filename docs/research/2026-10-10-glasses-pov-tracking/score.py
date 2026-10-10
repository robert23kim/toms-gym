"""Baseline: run the engine on every cut in work/cuts/cuts.json, convert to the tracks format, score.

usage:
  score.py [--engine-dir DIR] [--run-name baseline] [--configs service,yolo,yolo_chain,yolo_chain_sam]
           [--videos stem,...] [--extra-flags=...] [--jobs 2] [--timeout 600] [--skip-run] [--rerun]
           [--holdout-truth-dir DIR] [--no-overlays]

Raw engine output: work/runs/<run>/<config>/<stem>.*  (cut-local frame numbers)
Tracks (SOURCE frames): results/tracks_<run>/<config>__<stem>.json
Scores: results/<run>.json; overlays: overlays/<run>__<config>__<stem>.jpg (dev), <holdout-dir>/overlays/ (holdout).
A run whose _run.json says rc 0 and whose summary exists is not re-run unless --rerun.
Holdout scores are printed as metrics only (no truth values echoed).
"""
import argparse
import json
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import score_tracks  # noqa: E402

PY = "/Users/toka/code/bowling-app/analysis-engine/.venv/bin/python"
ENGINE = "/Users/toka/code/bowling-app/pov-engine"
HOLDOUT_DIR = "/Users/toka/.cache/bowling-pov-holdout-2026-10-10"
DEV = ["20260915_185121_23d80f05", "20260915_185331_19de9ec7", "20260915_185645_9fde3c16",
       "20260915_185454_f240c883", "20260915_190115_a7cf2c70", "20260915_191900_106ea7ca"]
HOLDOUT = ["20260915_191253_6cf2480f", "20260915_191820_0196b564", "20260915_191913_907c358b",
           "20260915_192142_eeb210f6", "20260915_192636_7c7fbfb0"]
CONFIGS = {
    "service": ["--simple-detect"],
    "yolo": ["--simple-detect", "--yolo"],
    "yolo_chain": ["--simple-detect", "--yolo-chain"],
    "yolo_chain_sam": ["--simple-detect", "--yolo-chain", "--sam-lane"],
}
CORNER_MAP = {"top_left": "pd_l", "top_right": "pd_r", "bottom_left": "fl_l", "bottom_right": "fl_r"}


def run_one(engine, out_dir, config, cut, stem, extra, timeout, rerun):
    out_dir.mkdir(parents=True, exist_ok=True)
    summ = out_dir / f"{stem}_summary.json"
    meta_p = out_dir / f"{stem}_run.json"
    if not rerun and meta_p.exists() and summ.exists():
        m = json.loads(meta_p.read_text())
        if m.get("rc") == 0:
            print(f"{config:15s} {stem}: cached rc 0 ({m.get('wall_s')}s)", flush=True)
            return m
    cmd = [PY, "-m", "scripts.debug_ball_motion", cut, str(out_dir / f"{stem}.mp4"), *CONFIGS[config],
           "--output-summary", str(summ), "--telemetry", *extra]
    t0 = time.time()
    rc, why = None, None
    with open(out_dir / f"{stem}.log", "w") as fh:
        fh.write(" ".join(cmd) + "\n")
        fh.flush()
        try:
            rc = subprocess.run(cmd, cwd=engine, stdout=fh, stderr=subprocess.STDOUT, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            why = f"timeout {timeout}s"
    meta = {"cmd": cmd, "rc": rc, "error": why, "wall_s": round(time.time() - t0, 1)}
    meta_p.write_text(json.dumps(meta, indent=1))
    print(f"{config:15s} {stem}: rc {rc} {why or ''} in {meta['wall_s']}s", flush=True)
    return meta


def static_lane(run_dir, stem, summary):
    if summary.get("static_lane"):
        return summary["static_lane"], "summary.static_lane"
    log = run_dir / f"{stem}.log"
    if log.exists():
        m = re.search(r"lane_edges=(\{.*\})", log.read_text(errors="replace"))
        if m:
            try:
                d = json.loads(m.group(1))
                return {k: d[k] for k in CORNER_MAP}, "log"
            except (ValueError, KeyError):
                pass
    return None, None


def quad(c):
    q = {CORNER_MAP[k]: [round(float(c[k][0]), 1), round(float(c[k][1]), 1)] for k in CORNER_MAP}
    q["fl_is_foul_line"] = False
    return q


def convert(run_dir, config, stem, cut):
    """Engine summary (cut-local) -> tracks format (SOURCE frames)."""
    off = int(cut["cut_start"])
    summ_p = run_dir / f"{stem}_summary.json"
    summary = json.loads(summ_p.read_text()) if summ_p.exists() else {}
    calib_p = run_dir / f"{stem}_lane_calibration.json"
    calib = json.loads(calib_p.read_text()) if calib_p.exists() else None
    rmap = {}
    boards = {}
    if calib:
        for p in calib.get("positions") or []:
            f = int(p["frame"]) + off
            rmap[f] = p.get("r")
            if p.get("board") is not None:
                boards[str(f)] = round(float(p["board"]), 2)
    frames = [{"f": int(t[0]) + off, "x": float(t[1]), "y": float(t[2]), "r": rmap.get(int(t[0]) + off), "conf": None}
              for t in summary.get("trajectory", [])]
    lane, src_counts = {}, {}
    st, st_src = static_lane(run_dir, stem, summary)
    per = (calib or {}).get("per_frame") or {}
    for k in range(int(cut["cut_start"]), int(cut["cut_end"]) + 1):
        c = per.get(str(k - off))
        if c:
            lane[str(k)], s = quad(c), "calibrated"
        elif st:
            lane[str(k)], s = quad(st), "static"
        else:
            continue
        src_counts[s] = src_counts.get(s, 0) + 1
    yc = summary.get("yolo_chain") or {}
    throw = ((yc.get("chain") or {}).get("throw")) if yc.get("applied") else None
    if throw and throw.get("frames"):
        rel, pin, wsrc = int(throw["frames"][0]) + off, int(throw["frames"][1]) + off, "yolo_chain.throw"
    elif frames:
        rel, pin, wsrc = frames[0]["f"], frames[-1]["f"], "first/last trajectory frame"
    else:
        rel, pin, wsrc = None, None, None
    if calib and (calib.get("summary") or {}).get("last_lane_frame") is not None:
        pin, wsrc = int(calib["summary"]["last_lane_frame"]) + off, wsrc + "; pin=sam last_lane_frame"
    fb = summary.get("final_board")
    return {"stem": stem, "method": f"engine:{config}", "frames": frames, "lane": lane, "boards": boards,
            "final_board": None if fb is None else float(fb), "release_frame": rel, "pin_hit_frame": pin,
            "meta": {"lane_sources": src_counts, "static_lane_source": st_src, "window_source": wsrc,
                     "lane_method": summary.get("lane_method"), "final_board_static": summary.get("final_board_static"),
                     "entry_board": summary.get("entry_board"), "cut_start": off,
                     "summary_exists": summ_p.exists(), "yolo_chain_applied": yc.get("applied")}}


def overlay(tracks, truth, cut, out_path, label):
    import cv2
    f0 = int(truth["pin_hit_frame"]) - 4
    cap = cv2.VideoCapture(cut["cut_path"])
    cap.set(cv2.CAP_PROP_POS_FRAMES, f0 - int(cut["cut_start"]))
    ok, im = cap.read()
    cap.release()
    if not ok:
        return False
    q = tracks["lane"].get(str(f0))
    if q:
        H = im.shape[0]
        for a, b in (("pd_l", "fl_l"), ("pd_r", "fl_r")):
            x0 = score_tracks.line_x(q[a], q[b], 0)
            x1 = score_tracks.line_x(q[a], q[b], H)
            cv2.line(im, (int(x0), 0), (int(x1), H), (255, 255, 0), 3)
    tp = sorted((int(k), score_tracks.ball_point(v)) for k, v in truth["ball"].items())
    tp = [(f, p) for f, p in tp if p is not None]
    for i, (f, (x, y, r)) in enumerate(tp):
        cv2.circle(im, (int(x), int(y)), 7 if f != f0 else max(8, int(r or 8)), (0, 200, 0), 2 if f == f0 else -1)
        if i:
            cv2.line(im, (int(tp[i - 1][1][0]), int(tp[i - 1][1][1])), (int(x), int(y)), (0, 200, 0), 2)
    ep = tracks["frames"]
    for i, p in enumerate(ep):
        cv2.circle(im, (int(p["x"]), int(p["y"])), 6 if p["f"] != f0 else 14, (0, 140, 255), -1 if p["f"] != f0 else 3)
        if i and p["f"] - ep[i - 1]["f"] <= 6:
            cv2.line(im, (int(ep[i - 1]["x"]), int(ep[i - 1]["y"])), (int(p["x"]), int(p["y"])), (0, 140, 255), 2)
    for j, line in enumerate(label):
        cv2.putText(im, line, (16, 44 + 40 * j), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 0), 5)
        cv2.putText(im, line, (16, 44 + 40 * j), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 2)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), cv2.resize(im, None, fx=0.5, fy=0.5), [cv2.IMWRITE_JPEG_QUALITY, 85])
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine-dir", default=ENGINE)
    ap.add_argument("--run-name", default="baseline")
    ap.add_argument("--configs", default=",".join(CONFIGS))
    ap.add_argument("--videos", default="")
    ap.add_argument("--extra-flags", default="")
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--skip-run", action="store_true")
    ap.add_argument("--rerun", action="store_true")
    ap.add_argument("--truth-dir", default=str(HERE / "truth"))
    ap.add_argument("--holdout-truth-dir", default=HOLDOUT_DIR)
    ap.add_argument("--no-overlays", action="store_true")
    a = ap.parse_args()
    cuts_all = json.loads((HERE / "work" / "cuts" / "cuts.json").read_text())
    cuts = {c["stem"]: c for c in cuts_all if c.get("cut_path") and c.get("cut_start") is not None}
    no_cut = [c["stem"] for c in cuts_all if c["stem"] not in cuts]
    stems = [s for s in (a.videos.split(",") if a.videos else list(cuts)) if s in cuts]
    configs = [c for c in a.configs.split(",") if c]
    extra = a.extra_flags.split()
    root = HERE / "work" / "runs" / a.run_name
    tracks_dir = HERE / "results" / f"tracks_{a.run_name}"
    tracks_dir.mkdir(parents=True, exist_ok=True)
    jobs = [(c, s) for c in configs for s in stems]
    metas = {}
    if not a.skip_run:
        with ThreadPoolExecutor(max_workers=a.jobs) as ex:
            futs = {(c, s): ex.submit(run_one, a.engine_dir, root / c, c, cuts[s]["cut_path"], s, extra, a.timeout, a.rerun)
                    for c, s in jobs}
            for k, fu in futs.items():
                metas[k] = fu.result()
    rows, missing_truth = [], []
    for c, s in jobs:
        meta = metas.get((c, s))
        if meta is None:
            mp = root / c / f"{s}_run.json"
            meta = json.loads(mp.read_text()) if mp.exists() else {"rc": None, "error": "not run"}
        split = "dev" if s in DEV else "holdout" if s in HOLDOUT else "unknown"
        tr = convert(root / c, c, s, cuts[s])
        offs = [p["f"] for p in tr["frames"]] + [int(k) for k in tr["lane"]] + [int(k) for k in tr["boards"]]
        out_of_cut = [f for f in offs if not cuts[s]["cut_start"] <= f <= cuts[s]["cut_end"]]
        tr["meta"]["frames_outside_cut"] = len(out_of_cut)
        tp = tracks_dir / f"{c}__{s}.json"
        tp.write_text(json.dumps(tr, indent=1))
        processed = bool(meta.get("rc") == 0 and tr["meta"]["summary_exists"])
        row = {"config": c, "stem": s, "split": split, "rc": meta.get("rc"), "error": meta.get("error"),
               "wall_s": meta.get("wall_s"), "processed": processed, "n_track_points": len(tr["frames"]),
               "final_board": tr["final_board"], "lane_sources": tr["meta"]["lane_sources"],
               "window_source": tr["meta"]["window_source"], "frames_outside_cut": len(out_of_cut)}
        tdir = Path(a.truth_dir) if split == "dev" else Path(a.holdout_truth_dir)
        tpath = tdir / f"{s}.json"
        if not tpath.exists():
            missing_truth.append(s)
            row["scored"] = False
            rows.append(row)
            print(f"{c:15s} {s}: no truth at {tpath}", flush=True)
            continue
        truth = json.loads(tpath.read_text())
        sc = score_tracks.score(tr, truth)
        for k in ("recall_pct", "median_px_err", "n_truth_points", "board_err", "lane_err_boards", "window_err", "pass", "strong"):
            row[k] = sc[k]
        if tr["final_board"] is not None and truth.get("board") is not None:
            row["board_err_if_flipped"] = round(abs((40 - tr["final_board"]) - float(truth["board"])), 2)
        row["scored"] = True
        rows.append(row)
        if not a.no_overlays:
            od = HERE / "overlays" if split == "dev" else Path(a.holdout_truth_dir) / "overlays"
            lbl = [f"{a.run_name} {c} {s[:15]} f{int(truth['pin_hit_frame']) - 4}",
                   f"recall {sc['recall_pct']}%  board_err {sc['board_err']}  lane_err {sc['lane_err_boards']}",
                   "orange = engine track, green = truth, cyan = engine lane"]
            try:
                overlay(tr, truth, cuts[s], od / f"{a.run_name}__{c}__{s}.jpg", lbl)
            except Exception as e:  # noqa: BLE001
                row["overlay_error"] = str(e)
        print(f"{c:15s} {s} [{split}] rc {row['rc']} wall {row['wall_s']}s pts {row['n_track_points']} "
              f"recall {row['recall_pct']}% med {row['median_px_err']} board_err {row['board_err']} "
              f"lane_err {row['lane_err_boards']} win {row['window_err']} pass {row['pass']}", flush=True)
    for s in no_cut:
        for c in configs:
            rows.append({"config": c, "stem": s, "split": "dev" if s in DEV else "holdout" if s in HOLDOUT else "unknown",
                         "rc": None, "processed": False, "scored": False, "error": "no cut (no throw in clip)"})
    sha = subprocess.run(["git", "-C", a.engine_dir, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    out = {"run_name": a.run_name, "engine_dir": a.engine_dir, "engine_sha": sha, "extra_flags": a.extra_flags,
           "jobs": a.jobs, "timeout_s": a.timeout, "input": "cuts (work/cuts/<stem>.mp4, H.264)",
           "wall_note": f"wall_s measured with {a.jobs} engine processes in parallel on a shared machine; not a service timing",
           "thresholds": {"pass": {"recall_pct": score_tracks.PASS_RECALL, "board_err": score_tracks.PASS_BOARD},
                          "strong": {"recall_pct": score_tracks.STRONG_RECALL, "board_err": score_tracks.STRONG_BOARD},
                          "match_px": f"max(2*truth_r, {score_tracks.TOL_MIN_PX})",
                          "track_gap_interp_max": score_tracks.GAP_MAX, "lane_nearest_frames": score_tracks.LANE_NEAREST,
                          "recall_denominator": "truth ball keys in [release, pin_hit] minus ball_invisible (truth not interpolated)"},
           "configs": {k: " ".join(v) for k, v in CONFIGS.items() if k in configs},
           "stems_without_cut": no_cut, "stems_missing_truth": sorted(set(missing_truth)), "rows": rows}
    (HERE / "results" / f"{a.run_name}.json").write_text(json.dumps(out, indent=1))
    print(f"wrote results/{a.run_name}.json", flush=True)


if __name__ == "__main__":
    sys.exit(main())
