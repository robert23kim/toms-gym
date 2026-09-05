"""Parse Vision OCR of bowling lane screens into games. Pure, DB-free.

Two layouts:
  night — end-of-night RESULTS table: Player · Game 1..3 · Scratch · Hdcp · Total
  game  — end-of-game frame strip: 10 frames of roll glyphs over a running score
Every row is validated against the ten-pin rules / sheet checksums; a mismatch flags
the row rather than silently accepting it.
"""
import re
import unicodedata
from statistics import median

from toms_gym.services.bowling_score import (
    infer_night_row, score_frames, validate_night_row, InvalidFrame, frame_pins,
)


class SheetParseError(Exception):
    pass


NIGHT_LABELS = {"PLAYER", "TEAM", "RESULTS", "GAME", "SCRATCH", "HDCP", "TOTAL", "QUBICA", "AME", "AMF"}
GAME_LABELS = {
    "END", "OF", "GAME", "TOT", "PIN", "FALL", "HDCP", "BONUS", "POINTS", "TEAM", "TOTAL", "PLAYER",
    "LANE", "YOUR", "WAY", "CHATTER", "BOWLERS", "BOWLER", "PHOTO", "RECAP", "STATISTICS",
    "SCORE", "STOP", "MPH", "YLYW", "ND", "RD", "ST", "TH",
}
ROLL_GLYPHS = {"X": "X", "/": "/", "-": "-", "―": "-", "—": "-", "–": "-", "_": "-", "F": "F",
               "O": "0", "I": "1", "L": "1", "|": "1"}


def _roll_glyph(text):
    """Normalise one OCR symbol to a roll glyph; circled split digits (⑦) become plain digits."""
    if text.upper() in ROLL_GLYPHS:
        return ROLL_GLYPHS[text.upper()]
    if len(text) == 1 and text.isdigit():
        return str(unicodedata.digit(text))
    return None


def _is_int(text):
    return bool(re.fullmatch(r"\d{1,4}", text))


def _alpha(text):
    return bool(re.fullmatch(r"[A-Za-z][A-Za-z.'\-]*", text))


def _fit_line(points):
    """Least-squares y = a + b*x over [(x, y)]; b = 0 when degenerate."""
    if len(points) < 2:
        return (points[0][1] if points else 0.0), 0.0
    n = len(points)
    mx = sum(p[0] for p in points) / n
    my = sum(p[1] for p in points) / n
    sxx = sum((p[0] - mx) ** 2 for p in points)
    if sxx == 0:
        return my, 0.0
    b = sum((p[0] - mx) * (p[1] - my) for p in points) / sxx
    return my - b * mx, b


# ---------------------------------------------------------------- night sheet

def _night_header_bands(words, page_h):
    """Find header word groups (Game 1..3 / Scratch / Hdcp / Total); return bands sorted by y."""
    cands = []
    for i, w in enumerate(words):
        t = w["text"].lower()
        if t == "game":
            nxt = [v for v in words if _is_int(v["text"]) and v["x"] > w["x"]
                   and v["x"] - w["x"] < w["h"] * 4 and abs(v["y"] - w["y"]) < w["h"]]
            if nxt:
                d = min(nxt, key=lambda v: v["x"] - w["x"])
                d["_header"] = True
                cands.append(("game", int(d["text"]), (w["x"] + d["x"]) / 2, w["y"]))
        elif t in ("scratch", "hdcp", "total"):
            cands.append((t, None, w["x"], w["y"]))
    bands = []
    for c in sorted(cands, key=lambda c: c[3]):
        for b in bands:
            if abs(b["y"] - c[3]) < page_h * 0.08:
                b["cols"].append(c)
                b["y"] = median(v[3] for v in b["cols"])
                break
        else:
            bands.append({"y": c[3], "cols": [c]})
    out = []
    for b in bands:
        cols = {}
        for kind, num, x, y in b["cols"]:
            key = f"game{num}" if kind == "game" else kind
            cols.setdefault(key, (x, y))
        if any(k.startswith("game") for k in cols):
            out.append({"y": b["y"], "cols": cols})
    return out


def parse_night_sheet(words, page_w, page_h):
    bands = _night_header_bands(words, page_h)
    if not bands:
        raise SheetParseError("no Game/Scratch/Total header found")
    player_band = bands[0]
    team_band = bands[1] if len(bands) > 1 else None
    cols = player_band["cols"]
    _, slope = _fit_line([(x, y) for x, y in cols.values()])
    x_ref = min(x for x, _ in cols.values())

    def deskew(w):
        return w["y"] - slope * (w["x"] - x_ref)

    y_top = max(deskew({"x": x, "y": y}) for x, y in cols.values())
    y_bot = min(deskew({"x": x, "y": y}) for x, y in team_band["cols"].values()) if team_band else page_h
    first_col_x = min(x for x, _ in cols.values())

    names = []
    for w in words:
        if not _alpha(w["text"]) or w["text"].upper() in NIGHT_LABELS:
            continue
        if w["x"] >= first_col_x - page_w * 0.05:
            continue
        yy = deskew(w)
        if y_top < yy < y_bot:
            names.append({"name": w["text"], "y": yy, "x": w["x"]})
    names.sort(key=lambda n: n["y"])
    merged = []
    for n in names:
        if merged and abs(merged[-1]["y"] - n["y"]) < page_h * 0.02:
            merged[-1]["name"] += " " + n["name"]
        else:
            merged.append(dict(n))
    names = merged
    if not names:
        raise SheetParseError("no player names found")
    spacing = median([b["y"] - a["y"] for a, b in zip(names, names[1:])]) if len(names) > 1 else page_h * 0.05
    tol = max(spacing * 0.55, page_h * 0.015)

    col_keys = sorted(cols, key=lambda k: cols[k][0])
    col_xs = [cols[k][0] for k in col_keys]
    per_col = {k: [] for k in col_keys}
    for w in words:
        if not _is_int(w["text"]) or w["x"] < first_col_x - page_w * 0.05 or w.get("_header"):
            continue
        yy = deskew(w)
        if not (y_top < yy < y_bot):
            continue
        # numbers are right-aligned inside their column, so they sit right of the header centre
        ci = min(range(len(col_xs)), key=lambda i: abs(col_xs[i] - w["x"] + page_w * 0.01))
        per_col[col_keys[ci]].append({"v": int(w["text"]), "yy": yy})
    cells = {n["name"]: {} for n in names}
    for key, items in per_col.items():
        items.sort(key=lambda it: it["yy"])
        if len(items) == len(names):
            # a full column: perspective skews rows unevenly, so rank order beats nearest-y
            for n, it in zip(names, items):
                cells[n["name"]][key] = it["v"]
            continue
        for it in items:
            row = min(names, key=lambda n: abs(n["y"] - it["yy"]))
            if abs(row["y"] - it["yy"]) <= tol and key not in cells[row["name"]]:
                cells[row["name"]][key] = it["v"]

    game_keys = sorted(k for k in col_keys if k.startswith("game"))
    players = []
    for n in names:
        c = cells[n["name"]]
        games = [c.get(k) for k in game_keys]
        scratch, hdcp, total = c.get("scratch"), c.get("hdcp"), c.get("total")
        row, inferred = infer_night_row(games, scratch, hdcp, total)
        ok, why = validate_night_row(row["games"], row["scratch"], row["hdcp"], row["total"])
        players.append({
            "name": n["name"], "games": row["games"], "scratch": row["scratch"],
            "hdcp": row["hdcp"], "total": row["total"], "inferred": inferred,
            "flagged": not ok, "flag_reason": why,
        })

    team_name = None
    if team_band:
        ty = team_band["y"]
        tw = [w for w in words if w["x"] < first_col_x - page_w * 0.05 and ty < w["y"] < ty + page_h * 0.12
              and w["text"].upper() not in NIGHT_LABELS - {"TEAM"} and (_alpha(w["text"]) or _is_int(w["text"]))]
        tw = [w for w in tw if not (w["text"].upper() == "TEAM" and abs(w["y"] - ty) < page_h * 0.02)]
        if tw:
            team_name = " ".join(w["text"] for w in sorted(tw, key=lambda w: w["x"]))
    return {"team_name": team_name, "players": players}


# ---------------------------------------------------------------- game screen

def _frame_columns(words):
    """Fit frame column centres from the 1..10 header; returns (centres[10], boundaries[11], header_y_at(x))."""
    candidates = []
    for w in words:
        t = w["text"].upper()
        num = None
        if _is_int(t) and 1 <= int(t) <= 10:
            num = int(t)
        elif t in ("I", "L", "|"):
            num = 1
        elif t in ("IO", "LO", "I0", "1O"):
            num = 10
        if num is None:
            continue
        candidates.append((num, w["x"], w["y"], max(w["h"], 1)))
    # A tilted photo drifts the header's y by a few px per column, so group by
    # y-gap between neighbours (< one glyph height) rather than a rounded y bucket.
    candidates.sort(key=lambda c: c[2])
    header_rows, current = [], []
    for cand in candidates:
        if current and cand[2] - current[-1][2] > 0.75 * min(cand[3], current[-1][3]):
            header_rows.append(current)
            current = []
        current.append(cand)
    if current:
        header_rows.append(current)
    best = None
    for row in header_rows:
        by_num = {}
        for num, x, y, _ in row:
            by_num.setdefault(num, []).append((x, y))
        # a steep tilt interleaves roll digits from the row below with the header; fit the
        # line on digits seen once, then let each duplicated digit pick the x nearest that line
        unique = {n: v[0] for n, v in by_num.items() if len(v) == 1}
        if len(unique) >= 3 and len(unique) < len(by_num):
            ua, ub = _fit_line([(n, x) for n, (x, _) in unique.items()])
            seen = {n: (v[0] if len(v) == 1 else min(v, key=lambda xy: abs(ua + ub * n - xy[0])))
                    for n, v in by_num.items()}
        else:
            seen = {n: v[0] for n, v in by_num.items()}
        if len(seen) >= 5:
            xs = sorted((n, x) for n, (x, _) in seen.items())
            a, b = _fit_line([(n, x) for n, x in xs])
            if b <= 0:
                continue
            resid = sum(abs(a + b * n - x) for n, x in xs) / len(xs)
            if resid < b * 0.25 and (best is None or len(seen) > best[0]):
                best = (len(seen), a, b, list(seen.values()))
    if not best:
        raise SheetParseError("no 1..10 frame header found")
    _, a, b, xy = best
    centres = [a + b * n for n in range(1, 11)]
    bounds = [centres[0] - b / 2] + [(centres[i] + centres[i + 1]) / 2 for i in range(9)] + [centres[9] + b * 0.7]
    ya, yb = _fit_line(xy)
    return centres, bounds, lambda x: ya + yb * x


def _legal_frames(tenth):
    out = []
    if not tenth:
        out.append(["X"])
        # first ball descending: an unread spare reads "9 /" not "- /", an unread 7-pin frame "7 -" not "- 7"
        for a in range(9, -1, -1):
            out.append([str(a) if a else "-", "/"])
        for a in range(9, -1, -1):
            for b in range(10 - a):
                out.append([str(a) if a else "-", str(b) if b else "-"])
        return out
    sym = lambda v: "X" if v == 10 else ("-" if v == 0 else str(v))
    for a in range(11):
        if a == 10:
            for b in range(11):
                if b == 10:
                    out.extend([["X", "X", sym(c)] for c in range(11)])
                else:
                    out.extend([["X", sym(b), "/"]] + [["X", sym(b), sym(c)] for c in range(10 - b)])
        else:
            for b in range(10 - a + 1):
                if a + b == 10:
                    out.extend([[sym(a), "/", sym(c)] for c in range(11)])
                else:
                    out.append([sym(a), sym(b)])
    return out


LEGAL_FRAMES = _legal_frames(False)
LEGAL_TENTH = _legal_frames(True)


def _penalty(candidate, observed):
    """How badly a legal frame disagrees with OCR glyphs (0 = exact); skipped leading
    glyphs cost more than trailing extras so a lone "9" reads as "9 -" not "- 9"."""
    if not observed:
        return 1
    i = skipped = 0
    for s in candidate:
        if i < len(observed) and observed[i] == s:
            i += 1
        elif i < len(observed):
            skipped += 1
    missed = len(observed) - i
    if missed:
        return 10 + missed * 3
    return skipped * 2 + (len(candidate) - len(observed))


def _conflicts(candidate, observed):
    return _penalty(candidate, observed) >= 10


def _solve_frames(observed, printed):
    """Reconstruct 10 legal frames consistent with the printed running score and closest to OCR."""
    order = []
    for i in range(10):
        pool = LEGAL_TENTH if i == 9 else LEGAL_FRAMES
        ranked = sorted(pool, key=lambda c: _penalty(c, observed[i]))
        order.append(ranked[:40] if observed[i] else ranked)

    def consistent(frames):
        res = score_frames(frames)
        k = len(frames)
        for j in range(k):
            # frame j's score is settled once its bonus rolls exist
            settled = j <= k - 3 or (j == k - 2 and frames[j][0] != "X") or j == 9 or (
                j == k - 2 and len(frames[j + 1]) >= 2) or (
                j == k - 1 and frames[j][0] != "X" and frames[j][-1] != "/")
            if settled and printed[j] is not None and res["cumulative"][j] != printed[j]:
                return False
        return True

    best = [None]

    def dfs(i, frames):
        if i == 10:
            best[0] = list(frames)
            return True
        for cand in order[i]:
            frames.append(cand)
            if consistent(frames) and dfs(i + 1, frames):
                return True
            frames.pop()
        return False

    dfs(0, [])
    if best[0] is None:
        return None, [], []
    solved = best[0]
    conflicts = [i + 1 for i in range(10) if observed[i] and _conflicts(solved[i], observed[i])]
    return solved, conflicts, _ambiguous_frames(solved, observed, printed)


def _ambiguous_frames(solved, observed, printed):
    """Frames where another legal frame also fits the glyphs read AND every printed score —
    the reviewer should see those, since the split ("8 1" vs "1 8") was a guess."""
    base = score_frames(solved)["cumulative"]
    out = []
    for i in range(10):
        # Vision routinely drops "-" glyphs, so a lone "8" reading as "8 -" is expected, not a guess;
        # a leading gutter or any digit/X// the solution needs but nobody read is worth marking
        read = sum(1 for g in observed[i] if g != "-")
        needed = [g for k, g in enumerate(solved[i]) if not (g == "-" and k > 0)]
        if len(needed) <= read:
            continue
        pool = LEGAL_TENTH if i == 9 else LEGAL_FRAMES
        for cand in pool:
            if cand == solved[i] or _conflicts(cand, observed[i]):
                continue
            alt = score_frames(solved[:i] + [cand] + solved[i + 1:])
            if not alt["valid"]:
                continue
            same = all(alt["cumulative"][j] == base[j] for j in range(10)
                       if printed[j] is not None or j == 9)
            if same:
                out.append(i + 1)
                break
    return out


def parse_game_sheet(words, symbols, page_w, page_h):
    centres, bounds, header_at = _frame_columns(words)
    left = bounds[0]
    right = bounds[-1]
    # deskew everything by the header's tilt so row bands and name/score filters see flat rows
    slope = header_at(left + 1000.0) - header_at(left)
    slope /= 1000.0
    words = [dict(w, y=w["y"] - slope * (w["x"] - left)) for w in words]
    symbols = [dict(s, y=s["y"] - slope * (s["x"] - left)) for s in symbols]
    header_y = header_at(left)
    footer_y = min([w["y"] for w in words if w["text"].upper() in ("TOT", "GAME") and w["y"] > header_y + page_h * 0.2]
                   or [page_h])
    names = [w for w in words if _alpha(w["text"]) and len(w["text"]) >= 2
             and w["text"].upper() not in GAME_LABELS and w["x"] < left - page_w * 0.02
             and header_y + w["h"] * 0.5 < w["y"] < footer_y]
    names.sort(key=lambda w: w["y"])
    nums = sorted((w for w in words if _is_int(w["text"]) and left < w["x"] < right
                   and header_y + page_h * 0.02 < w["y"] < footer_y), key=lambda w: w["y"])
    lines = []
    for w in nums:
        if lines and abs(lines[-1]["y"] - w["y"]) < page_h * 0.03:
            lines[-1]["words"].append(w)
            lines[-1]["y"] = median(v["y"] for v in lines[-1]["words"])
        else:
            lines.append({"y": w["y"], "words": [w]})
    cum_lines = [ln for ln in lines if len(ln["words"]) >= 5
                 and sum(len(w["text"]) >= 2 for w in ln["words"]) >= 3]
    if not cum_lines:
        raise SheetParseError(f"found {len(names)} bowlers but no score lines")
    # pair each score line with the nearest unclaimed name above/around it; a line whose name
    # OCR dropped still parses under a placeholder (flagged), a name with no line is skipped
    pairs = []
    unclaimed = list(names)
    for line in cum_lines:
        pick = min(unclaimed, key=lambda n: abs(n["y"] - line["y"]), default=None)
        if pick is not None and abs(pick["y"] - line["y"]) < page_h * 0.08:
            unclaimed.remove(pick)
            pairs.append((pick, line, None))
        else:
            pairs.append(({"text": f"Bowler {len(pairs) + 1}"}, line, "name not read"))

    players = []
    prev_cum_y = header_y
    for n, line, name_issue in pairs:
        cum_y = line["y"]
        top = prev_cum_y + page_h * 0.02
        bot = cum_y + page_h * 0.03
        prev_cum_y = cum_y
        printed = [None] * 10
        for w in line["words"]:
            fi = next((i for i in range(10) if bounds[i] <= w["x"] < bounds[i + 1]), None)
            if fi is not None and printed[fi] is None:
                printed[fi] = int(w["text"])
        band_syms = [s for s in symbols if top < s["y"] < cum_y - page_h * 0.02 and left < s["x"] < right]
        observed = [[] for _ in range(10)]
        for s in sorted(band_syms, key=lambda s: s["x"]):
            g = _roll_glyph(s["text"])
            if g is None:
                continue
            fi = next((i for i in range(10) if bounds[i] <= s["x"] < bounds[i + 1]), None)
            if fi is not None:
                observed[fi].append(g)
        # a strike glyph hugs the cell's right edge; a stray leading "X" in the next cell belongs left
        for i in range(1, 10):
            if observed[i][:1] == ["X"] and len(observed[i]) > 1 and i < 9 and not observed[i - 1]:
                observed[i - 1].append(observed[i].pop(0))
        total_words = [w for w in words if _is_int(w["text"]) and w["x"] > right and top < w["y"] < bot]
        total = int(total_words[0]["text"]) if total_words else printed[9]
        if printed[9] is None and total is not None:
            printed[9] = total
        frames, conflicts, inferred = _solve_frames(observed, printed)
        flagged, reason = False, None
        if frames is None:
            frames, inferred = observed, []
            flagged, reason = True, "rolls could not be reconciled with the printed score"
        elif conflicts:
            flagged, reason = True, "printed score disagrees with the rolls read in frame " + ", ".join(map(str, conflicts))
        elif total is not None and printed[9] != total:
            flagged, reason = True, f"running score {printed[9]} != total {total}"
        if name_issue and not flagged:
            flagged, reason = True, name_issue
        players.append({"name": n["text"], "frames": frames, "printed_cumulative": printed,
                        "total": total, "flagged": flagged, "flag_reason": reason,
                        "inferred_frames": inferred})
    team_words = [w for w in words if w["text"].upper() == "TEAM"]
    team_name = None
    for tw in team_words:
        nxt = [w for w in words if abs(w["y"] - tw["y"]) < tw["h"] and 0 < w["x"] - tw["x"] < tw["w"] * 3]
        if nxt:
            team_name = "Team " + " ".join(w["text"] for w in sorted(nxt, key=lambda w: w["x"]))
            break
    return {"team_name": team_name, "players": players}


# ---------------------------------------------------------------- dispatch

def parse_sheet(sheet_type, words, symbols, page_w, page_h):
    if sheet_type == "night":
        return parse_night_sheet(words, page_w, page_h)
    if sheet_type == "game":
        return parse_game_sheet(words, symbols, page_w, page_h)
    raise SheetParseError(f"unknown sheet_type {sheet_type!r}")


def shape_games(parsed, sheet_type, played_on):
    rows = []
    for p in parsed["players"]:
        if sheet_type == "night":
            per_game_hdcp = None
            if p.get("hdcp") is not None and len(p["games"]) and p["hdcp"] % len(p["games"]) == 0:
                per_game_hdcp = p["hdcp"] // len(p["games"])
            conf = 1.0 - 0.2 * len(p.get("inferred", [])) - (0.5 if p["flagged"] else 0)
            for gi, g in enumerate(p["games"], start=1):
                rows.append({
                    "player_name": p["name"], "game_number": gi, "total_score": g,
                    "hdcp": per_game_hdcp, "frames": None, "computed_total": None,
                    "flagged": p["flagged"] or g is None, "flag_reason": p["flag_reason"],
                    "confidence": max(conf, 0.0), "played_on": played_on,
                })
        else:
            res = score_frames(p["frames"])
            flagged = p["flagged"] or not res["valid"] or (p["total"] is not None and res["total"] != p["total"])
            reason = p["flag_reason"] or (res["errors"][0] if res["errors"] else None)
            if not flagged:
                reason = None
            elif reason is None:
                reason = f"computed {res['total']} != printed {p['total']}"
            inferred = p.get("inferred_frames") or []
            rows.append({
                "player_name": p["name"], "game_number": 1, "total_score": p["total"] if p["total"] is not None else res["total"],
                "hdcp": None, "frames": p["frames"], "computed_total": res["total"],
                "flagged": flagged, "flag_reason": reason,
                "confidence": 0.4 if flagged else max(0.5, 0.95 - 0.1 * len(inferred)),
                "inferred_frames": inferred, "played_on": played_on,
            })
    return rows
