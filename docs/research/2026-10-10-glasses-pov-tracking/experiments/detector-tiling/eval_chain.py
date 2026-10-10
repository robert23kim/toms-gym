"""Score a pool/chain configuration offline on the dumped boxes of one or more dev stems (no torch)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
L = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(L))
from tracker import PoolConfig, run_chain  # noqa: E402
from src.bowling.trajectory.yolo_chain import ChainConfig  # noqa: E402
import score_tracks  # noqa: E402


def to_tracks(stem, positions, method="pool_chain"):
    return {"stem": stem, "method": method,
            "frames": [{"f": int(p[0]), "x": round(float(p[1]), 1), "y": round(float(p[2]), 1), "r": round(float(p[3]), 1), "conf": round(float(p[4]), 3)} for p in positions],
            "lane": {}, "boards": {}, "final_board": None,
            "release_frame": int(positions[0][0]) if positions else None, "pin_hit_frame": int(positions[-1][0]) if positions else None}


def evaluate(stems, pc, cc, verbose=True):
    rows = []
    for stem in stems:
        doc = json.load(open(HERE / "work" / f"dets_{stem}.json"))
        pos, rep, pool = run_chain(doc, pc, cc)
        truth = json.load(open(L / "truth" / f"{stem}.json"))
        sc = score_tracks.score(to_tracks(stem, pos), truth)
        rows.append((stem, sc["recall_pct"], sc["median_px_err"], sc["window_err"], rep.get("throw"), rep["pool_boxes"]))
        if verbose:
            print(f"{stem[9:15]} recall {sc['recall_pct']:5.1f} med {sc['median_px_err']} win {sc['window_err']} throw {rep.get('throw')} pool {rep['pool_boxes']} cands {rep['candidates'][:4]}")
    return rows


if __name__ == "__main__":
    stems = sys.argv[1:]
    evaluate(stems, PoolConfig(), ChainConfig(r_grow=1.3))
