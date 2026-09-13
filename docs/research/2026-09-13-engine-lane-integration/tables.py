"""results/summary.md from results/eval_<config>__<stem>.json: one row per
config x video with the loop-1 metric against both truths and the product
number. usage: tables.py <config> [<config> ...]"""
import json
import sys

import common as C

COLS = ["config", "video", "lane", "throw MAE ann mean/med", "throw MAE pins mean/med", "<=2 bd (pins)", "clean med (pins)", "tail med (pins)", "pre-hit / last (pins)", "far-end width err px", "final board engine / truth (err)", "pass s"]


def row(config, stem):
    p = C.RESULTS / f"eval_{config}__{stem}.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text())
    ta, tp = d["throw_annotated"], d["throw_pins"]
    per = [r for r in d["per_frame"] if r.get("ok")]
    werr = sorted(abs(r["width_err_pins"]) for r in per)
    werr = werr[len(werr) // 2] if werr else None
    cal = d.get("calibration") or {}
    secs = (d.get("summary") or {}).get("lane_calibration_s")
    fb = d["final_board"]
    tf = d["truth_final_board"]["pins"]
    return [config, C.SHORT[stem], d["method"], f"{ta['mean']} / {ta['median']}", f"{tp['mean']} / {tp['median']}", f"{tp['within_2']} %",
            f"{d['clean_pins']['median']}", f"{d['tail_pins']}", f"{d['prehit_pins']} / {d['last_pins']}", f"{werr}",
            f"{fb} / {tf} ({d['final_board_err']['pins']})", f"{secs if secs is not None else '-'}"]


def main(configs):
    lines = ["| " + " | ".join(COLS) + " |", "|" + "---|" * len(COLS)]
    for config in configs:
        for stem in C.STEMS:
            r = row(config, stem)
            if r:
                lines.append("| " + " | ".join(str(v) for v in r) + " |")
    md = "\n".join(lines)
    (C.RESULTS / "summary.md").write_text(md + "\n")
    print(md)


if __name__ == "__main__":
    main(sys.argv[1:] or ["before", "before_yolo", "after_v2"])
