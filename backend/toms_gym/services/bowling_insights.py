"""Bowling insights over stored games. Pure, DB-free.

Totals-only games give averages/trend/slots; games that carry frame symbols also
give strike/spare/first-ball stats. Tips are rule-based, highest impact first.
"""

import statistics

from toms_gym.services.bowling_score import InvalidFrame, frame_pins

# a missed spare costs roughly the pins left plus the lost bonus ball
PINS_PER_MISSED_SPARE = 11
MAX_TIPS = 4


def _round(value, digits=1):
    if value is None:
        return None
    return round(value + (1e-9 if value >= 0 else -1e-9), digits)


def _avg(values, digits=1):
    if not values:
        return None
    return _round(sum(values) / len(values), digits)


def _racks(frames):
    """Split a game's frames into racks (frames 1-9 are one rack; the 10th up to three)."""
    racks = []
    valid_frames = 0
    per_frame_first = []
    for idx, f in enumerate(frames):
        try:
            pins = frame_pins(f, idx)
        except (InvalidFrame, TypeError):
            per_frame_first.append(None)
            continue
        valid_frames += 1
        per_frame_first.append(pins[0])
        if idx < 9:
            racks.append(pins)
            continue
        current = []
        for p in pins:
            current.append(p)
            if p == 10 or len(current) == 2:
                racks.append(current)
                current = []
        if current:
            racks.append(current)
    return racks, valid_frames, per_frame_first


def _frame_stats(games):
    strikes = 0
    total_racks = 0
    spare_opportunities = 0
    spares = 0
    opens = 0
    single_pin_opportunities = 0
    single_pin_conversions = 0
    first_balls = []
    frames_analyzed = 0
    clean_games = 0
    tenth_totals = []
    strike_hits = [0] * 10
    strike_chances = [0] * 10

    for game in games:
        frames = game.get("frames")
        if not frames:
            continue
        racks, valid_frames, per_frame_first = _racks(frames)
        frames_analyzed += valid_frames
        game_opens = 0
        for i, first in enumerate(per_frame_first[:10]):
            if first is None:
                continue
            strike_chances[i] += 1
            if first == 10:
                strike_hits[i] += 1
        for rack in racks:
            total_racks += 1
            first_balls.append(rack[0])
            if rack[0] == 10:
                strikes += 1
                continue
            if len(rack) < 2:
                continue
            spare_opportunities += 1
            converted = rack[0] + rack[1] == 10
            if rack[0] == 9:
                single_pin_opportunities += 1
                single_pin_conversions += 1 if converted else 0
            if converted:
                spares += 1
            else:
                opens += 1
                game_opens += 1
        if valid_frames and game_opens == 0:
            clean_games += 1
        if len(frames) >= 10:
            try:
                tenth_totals.append(sum(frame_pins(frames[9], 9)))
            except (InvalidFrame, TypeError):
                pass

    if not total_racks:
        return None
    return {
        "strike_pct": _round(strikes / total_racks, 3),
        "spare_pct": _round(spares / spare_opportunities, 3) if spare_opportunities else None,
        "open_pct": _round(opens / total_racks, 3),
        "first_ball_avg": _avg(first_balls, 2),
        "single_pin_conversion": (
            _round(single_pin_conversions / single_pin_opportunities, 3)
            if single_pin_opportunities
            else None
        ),
        "tenth_frame_avg": _avg(tenth_totals),
        "strike_by_frame": [
            _round(strike_hits[i] / strike_chances[i], 2) if strike_chances[i] else 0.0
            for i in range(10)
        ],
        "clean_games": clean_games,
        "pins_left": opens * PINS_PER_MISSED_SPARE,
        "frames_analyzed": frames_analyzed,
    }


def _tips(summary, frame_stats):
    tips = []

    def add(key, title, body, stat):
        tips.append({"key": key, "title": title, "body": body, "stat": stat})

    if summary["games"] == 0:
        add(
            "no_games",
            "Snap your first score sheet",
            "Photograph the end-of-night results screen and every game gets tracked automatically.",
            None,
        )
        return tips

    average = summary["average"] or 0.0
    slot1 = summary["slot_averages"]["1"]
    slot3 = summary["slot_averages"]["3"]
    delta = summary["trend"]["delta"]

    if frame_stats:
        spare_pct = frame_stats["spare_pct"]
        per_game = frame_stats["pins_left"] / summary["games"]
        if spare_pct is not None and spare_pct < 0.7:
            add(
                "spares",
                "Spares are your biggest lever",
                f"You convert {spare_pct * 100:.0f}% of your spare chances. "
                f"Cleaning those up is worth about {per_game:.0f} pins a game.",
                f"{spare_pct * 100:.0f}% spares · ~{per_game:.0f} pins a game left on the table",
            )
        if frame_stats["first_ball_avg"] is not None and frame_stats["first_ball_avg"] < 8.5:
            add(
                "first_ball",
                "Work the first ball",
                "Your first ball averages under 8.5 pins, so you are leaving big clusters. "
                "Aim for a repeatable target line before chasing spares.",
                f"{frame_stats['first_ball_avg']} pins on the first ball",
            )
        if frame_stats["tenth_frame_avg"] is not None and frame_stats["tenth_frame_avg"] < average / 10 - 2:
            add(
                "tenth",
                "You give pins back in the tenth",
                "Your tenth frame scores below your own frame average. Treat the bonus balls "
                "as a normal frame instead of swinging for the fences.",
                f"{frame_stats['tenth_frame_avg']} in the tenth",
            )

    if (
        len(tips) < MAX_TIPS
        and slot1 is not None
        and slot3 is not None
        and summary["sessions"] >= 3
        and slot3 <= slot1 - 12
    ):
        add(
            "fade_game3",
            "You fade in game 3",
            "Your third game runs well below your first. Hydrate, slow down between frames, "
            "and re-check your line after game 2.",
            f"G1 {slot1} → G3 {slot3}",
        )
    if len(tips) < MAX_TIPS and slot1 is not None and slot3 is not None and slot1 <= slot3 - 12:
        add(
            "slow_start",
            "You start slow",
            "Game 1 is your weakest. A few practice shots or a longer warm-up should get "
            "game 1 closer to your average.",
            f"G1 {slot1} → G3 {slot3}",
        )
    if len(tips) < MAX_TIPS and summary["stdev"] > 25:
        add(
            "consistency",
            "Consistency is costing you",
            "Your scores swing widely night to night. Repeating the same approach and "
            "target beats chasing strikes.",
            f"±{summary['stdev']} spread",
        )
    if len(tips) < MAX_TIPS and delta is not None and abs(delta) >= 8:
        if delta > 0:
            add(
                "trend_up",
                "You are trending up",
                "Your last five games are well above the ones before them. Keep whatever "
                "you changed.",
                f"+{delta} on your last 5",
            )
        else:
            add(
                "trend_down",
                "You are trending down",
                "Your last five games are below your earlier ones. Worth checking ball "
                "surface and your starting position.",
                f"{delta} on your last 5",
            )
    if len(tips) < MAX_TIPS and frame_stats is None:
        add(
            "snap_a_game",
            "Snap a game screen",
            "Photograph the end-of-game lane screen to unlock strike, spare and first-ball "
            "stats on top of your totals.",
            None,
        )
    return tips[:MAX_TIPS]


def _sheet_kind(game):
    if game.get("sheet_type") in ("night", "game"):
        return game["sheet_type"]
    return "game" if game.get("frames") or game.get("has_frames") else "night"


def merge_duplicate_games(games):
    """Collapse the same game stored twice — once from the night RESULTS sheet (game slot,
    handicap) and once from its End-of-game screen (frames) — into one row. A night row pairs
    with at most one screen row of the same date and score (and vice versa), so a bowler who
    scores 134 twice in a night keeps both games. Order of first appearance is kept; the
    screen row lends its frames to the night row."""
    merged = []
    unpaired = {}
    for game in games:
        if not game or game.get("total_score") is None:
            merged.append(game)
            continue
        key = (game.get("played_on"), game["total_score"])
        kind = _sheet_kind(game)
        partner = next((r for r in unpaired.get(key, []) if _sheet_kind(r) != kind), None)
        if partner is None:
            row = dict(game)
            unpaired.setdefault(key, []).append(row)
            merged.append(row)
            continue
        unpaired[key].remove(partner)
        night, screen = (partner, game) if kind == "game" else (game, partner)
        if not night.get("frames") and (screen.get("frames") or screen.get("has_frames")):
            if screen.get("frames"):
                partner["frames"] = screen["frames"]
            partner["has_frames"] = True
        if night is game:
            partner["game_number"] = game.get("game_number", partner.get("game_number"))
            if game.get("hdcp") is not None:
                partner["hdcp"] = game["hdcp"]
    return merged


def compute_insights(games):
    ordered = sorted(
        [g for g in games if g and g.get("total_score") is not None],
        key=lambda g: (g.get("played_on") or "", g.get("game_number") or 0),
    )
    scores = [int(g["total_score"]) for g in ordered]
    summary = {
        "games": len(scores),
        "average": _avg(scores) or 0.0,
        "high": max(scores) if scores else 0,
        "low": min(scores) if scores else 0,
        "stdev": _round(statistics.stdev(scores)) if len(scores) > 1 else 0.0,
        "trend": {"last5": None, "prior": None, "delta": None},
        "slot_averages": {"1": None, "2": None, "3": None},
        "sessions": 0,
        "session_series": [],
        "over_200": sum(1 for s in scores if s >= 200),
        "hdcp_latest": None,
    }

    if scores:
        last5 = scores[-5:]
        prior = scores[:-5]
        summary["trend"] = {
            "last5": _avg(last5),
            "prior": _avg(prior),
            "delta": _round(_avg(last5) - _avg(prior)) if prior else None,
        }
        for slot in ("1", "2", "3"):
            summary["slot_averages"][slot] = _avg(
                [int(g["total_score"]) for g in ordered if g.get("game_number") == int(slot)]
            )
        by_date = {}
        for g in ordered:
            by_date.setdefault(g.get("played_on"), []).append(int(g["total_score"]))
        summary["sessions"] = len(by_date)
        summary["session_series"] = [
            {"played_on": date, "average": _avg(vals), "games": len(vals)}
            for date, vals in sorted(by_date.items(), key=lambda kv: kv[0] or "")
        ]
        for g in reversed(ordered):
            if g.get("hdcp") is not None:
                summary["hdcp_latest"] = int(g["hdcp"])
                break

    frame_stats = _frame_stats(ordered) if ordered else None
    summary["frame_stats"] = frame_stats
    summary["tips"] = _tips(summary, frame_stats)
    return summary
