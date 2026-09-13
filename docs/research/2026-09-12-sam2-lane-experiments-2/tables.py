"""Print README tables from results/*.json (board MAE per video)."""
import json, sys
from pathlib import Path
import common as C
STEMS = C.STEMS
rows = {}
for p in sorted(C.RESULTS.glob("*.json")):
    if p.name.startswith(("camera_", "summary")):
        continue
    try:
        data = json.loads(p.read_text())
    except Exception:
        continue
    if not isinstance(data, list):
        continue
    for r in data:
        if r.get("method"):
            rows.setdefault(r["method"], {})[r["stem"]] = r

def f(key, stem, field="board_mae"):
    r = rows.get(key, {}).get(stem)
    if r is None:
        return "·"
    if not r.get("ok"):
        return "fail"
    v = r.get(field)
    return "·" if v is None else (f"{v:.2f}" if isinstance(v, float) else str(v))

def table(title, keys, field="board_mae", labels=None):
    print(f"\n**{title}**\n")
    print("| method | sample_input | Chardie | tom_old |")
    print("|---|---|---|---|")
    for k in keys:
        if k not in rows:
            continue
        lab = (labels or {}).get(k, k)
        print(f"| `{lab}` | " + " | ".join(f(k, s, field) for s in STEMS) + " |")

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    bases = ["even3", "soft", "ens", "zoom", "zoom_lo", "zoom_trim", "tiles", "hires", "ens_zoom", "snap2", "trim", "vp"]
    for kind in ("last", "prehit", "prehit-6"):
        table(f"kind = {kind}, sam2.1_b, kept prompts", [f"{b}_{kind}_k" for b in bases])
    table("loop-1 prompt rule (dropped points), sam2.1_b", [f"{b}_{k}" for b in ("even3", "soft", "zoom", "hires", "ens") for k in ("last", "prehit")])
    table("sam2.1_t (tiny), kept prompts", [f"{b}_{k}_k_tiny" for k in ("last", "prehit", "prehit-6") for b in ("even3", "soft", "ens", "zoom", "zoom_lo")])
    others = sorted(k for k in rows if not any(k.startswith(b + "_") for b in bases))
    table("other methods (agents)", others)
    pf = [k for k in rows if any(r.get("perframe_mae_mean") is not None for r in rows[k].values())]
    if pf:
        print("\n**per-frame (mean / median / max / % <= 2 boards)**\n")
        print("| method | sample_input | Chardie | tom_old |")
        print("|---|---|---|---|")
        for k in sorted(pf):
            cells = []
            for s in STEMS:
                r = rows[k].get(s, {})
                m = r.get("perframe_mae_mean")
                cells.append("·" if m is None else f"{m:.2f} / {r.get('perframe_mae_median') or 0:.2f} / {r.get('perframe_mae_max') or 0:.2f} / {r.get('perframe_within_2') or 0:.0f}%")
            print(f"| `{k}` | " + " | ".join(cells) + " |")


def wide(bases, tag="_k", kinds=("last", "prehit", "prehit-6"), title=""):
    print(f"\n**{title}**\n")
    print("| method | " + " | ".join(f"{k} (s / C / t)" for k in kinds) + " |")
    print("|---|" + "---|" * len(kinds))
    for b in bases:
        cells = []
        any_ = False
        for k in kinds:
            key = f"{b}_{k}{tag}"
            if key in rows:
                any_ = True
                cells.append(" / ".join(f(key, s) for s in STEMS))
            else:
                cells.append("·")
        if any_:
            print(f"| `{b}` | " + " | ".join(cells) + " |")


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "wide":
    wide(["even3", "soft", "ens", "zoom", "zoom_lo", "zoom_trim", "tiles", "ens_zoom", "hires", "snap2", "trim", "vp"], title="sam2.1_b, kept prompts")
    wide(["even3", "soft", "ens", "zoom", "zoom_lo"], tag="_k_tiny", title="sam2.1_t, kept prompts")
    wide(["even3", "soft", "zoom", "hires", "ens"], tag="", kinds=("last", "prehit"), title="loop-1 prompt rule (points near the ball dropped)")
