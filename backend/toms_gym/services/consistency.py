"""The 100 Club consistency board — pure, DB-free.

Weeks run Monday to Sunday in the challenge timezone from ``week_start``. Each
week has a quota (``base_quota``, ``ramp`` higher after a met week, back to
``base_quota`` after a miss). Weekly points are ``min(lifts, quota)`` plus
``quota_bonus`` when met plus ``type_bonus`` per lift type led (plank judged
on seconds). The week in progress scores lifts and the quota bonus live; its
type leaders are provisional and lock when it ends.
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from toms_gym.services.challenge_leaderboard import attempt_rep_score

DEFAULT_RULES = {
    "base_quota": 100,
    "ramp": 25,
    "weeks": 8,
    "quota_bonus": 50,
    "type_bonus": 25,
    "plank_seconds_per_lift": 10,
    "tz": "America/New_York",
    "week_start": "2026-11-02",
}

COUNTED_LIFT_TYPES = ("Situp", "Pushup", "Squat", "Plank")
REP_COUNTED = frozenset({"Situp", "Pushup", "Squat"})


# Smallest valid value per integer rule.
_INT_RULE_MIN = {
    "base_quota": 1,
    "ramp": 0,
    "weeks": 1,
    "quota_bonus": 0,
    "type_bonus": 0,
    "plank_seconds_per_lift": 1,
}


def _valid_int(value, minimum) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, float):
        if not value.is_integer():
            return None
        value = int(value)
    elif isinstance(value, str):
        try:
            value = int(value.strip())
        except ValueError:
            return None
    if not isinstance(value, int) or value < minimum:
        return None
    return value


def _valid_rule(key, value):
    """The value coerced to its rule type, or None when unusable."""
    if key in _INT_RULE_MIN:
        return _valid_int(value, _INT_RULE_MIN[key])
    if key == "tz":
        if not isinstance(value, str):
            return None
        try:
            ZoneInfo(value)
        except Exception:  # ZoneInfoNotFoundError, ValueError on odd keys
            return None
        return value
    if key == "week_start":
        if not isinstance(value, str):
            return None
        try:
            return date.fromisoformat(value.strip()).isoformat()
        except ValueError:
            return None
    return value


def fill_rules(rules) -> dict:
    """Stored rules over the defaults; a missing or unusable value keeps its default.

    create_competition stores rules unvalidated, and the champions scan builds every
    ended board, so a bad value must never raise here or downstream.
    """
    out = dict(DEFAULT_RULES)
    if isinstance(rules, dict):
        for k, v in rules.items():
            if v is None:
                continue
            valid = _valid_rule(k, v)
            if valid is not None:
                out[k] = valid
    return out


def _num(value):
    """Integral floats as ints so JSON reads 45, not 45.0."""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def to_utc(created) -> Optional[datetime]:
    """Aware UTC datetime from a datetime/date/ISO string; naive means UTC."""
    if created is None:
        return None
    if isinstance(created, datetime):
        dt = created
    elif isinstance(created, date):
        dt = datetime(created.year, created.month, created.day)
    else:
        text = str(created).strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _week1(rules) -> date:
    return date.fromisoformat(str(rules["week_start"]))


def local_date(created, rules) -> Optional[date]:
    dt = to_utc(created)
    if dt is None:
        return None
    return dt.astimezone(ZoneInfo(rules["tz"])).date()


def week_of(created, rules) -> Optional[int]:
    """1-based challenge week of an instant; <= 0 is before week_start."""
    d = local_date(created, rules)
    if d is None:
        return None
    return (d - _week1(rules)).days // 7 + 1


def attempt_lifts(attempt, rules) -> Optional[float]:
    """Lifts one attempt contributes; None until analysed, 0 for other types."""
    lift_type = attempt.get("lift_type")
    if lift_type == "Plank":
        held = attempt.get("held_s")
        if held is None:
            return None
        return math.floor(float(held) / float(rules["plank_seconds_per_lift"]))
    if lift_type in REP_COUNTED:
        return attempt_rep_score(attempt)
    return 0


def _empty_week(index, start, quota, types):
    return {
        "index": index,
        "start": start.isoformat(),
        "quota": quota,
        "lifts": 0,
        "met": False,
        "points": 0,
        "bonuses": [],
        "by_type": {t: 0 for t in types},
        "plank_seconds": 0,
        "pending": 0,
    }


def rank_consistency(participants, rules, now, lift_types=None) -> Tuple[List[dict], dict]:
    rules = fill_rules(rules)
    types = list(lift_types) if lift_types else list(COUNTED_LIFT_TYPES)
    scoring = [t for t in types if t in COUNTED_LIFT_TYPES]
    weeks_total = int(rules["weeks"])
    base = rules["base_quota"]
    week1 = _week1(rules)

    now_week = week_of(now, rules)
    if now_week is None or now_week < 1:
        status, week_index, cap = "upcoming", 0, 0
    elif now_week > weeks_total:
        status, week_index, cap = "ended", weeks_total + 1, weeks_total
    else:
        status, week_index, cap = "live", now_week, now_week

    def finished(w):
        return w < week_index

    # Pass 1: per-athlete per-week tallies.
    tallies = []
    for p in participants:
        weeks = {w: {"by_type": {t: 0 for t in types}, "plank_seconds": 0.0, "pending": 0}
                 for w in range(1, cap + 1)}
        counted = []
        warmup = 0
        for a in p.get("attempts", []):
            if a.get("status") == "failed":
                continue
            w = week_of(a.get("created_at"), rules)
            if w is None or w > cap:
                continue
            lifts = attempt_lifts(a, rules)
            if w < 1:
                if lifts is not None and a.get("lift_type") in scoring:
                    warmup += lifts
                continue
            if a.get("lift_type") not in scoring:
                continue
            if lifts is None:
                if a.get("status") != "completed":
                    weeks[w]["pending"] += 1
                continue
            weeks[w]["by_type"][a["lift_type"]] += lifts
            if a["lift_type"] == "Plank":
                weeks[w]["plank_seconds"] += float(a["held_s"])
            counted.append((to_utc(a.get("created_at")), a, lifts))
        tallies.append({"p": p, "weeks": weeks, "counted": counted, "warmup": warmup})

    def amount(tally, w, t):
        wk = tally["weeks"][w]
        return wk["plank_seconds"] if t == "Plank" else wk["by_type"][t]

    # Pass 2: who led each type each week (ties share it; zero never wins).
    leaders: Dict[int, Dict[str, List[int]]] = {}
    for w in range(1, cap + 1):
        leaders[w] = {}
        for t in scoring:
            top = max((amount(x, w, t) for x in tallies), default=0)
            if top > 0:
                leaders[w][t] = [i for i, x in enumerate(tallies) if amount(x, w, t) == top]

    rows = []
    for i, tally in enumerate(tallies):
        p = tally["p"]
        run = best = met_count = 0
        total = 0
        week_rows = []
        for w in range(1, cap + 1):
            wk = tally["weeks"][w]
            quota = base + rules["ramp"] * run
            lifts = sum(wk["by_type"].values())
            met = lifts >= quota
            led = [t for t in scoring if i in leaders[w].get(t, [])]
            bonuses = led if finished(w) else []
            points = (min(lifts, quota) + (rules["quota_bonus"] if met else 0)
                      + rules["type_bonus"] * len(bonuses))
            total += points
            if met:
                run += 1
                met_count += 1
                best = max(best, run)
            elif finished(w):
                run = 0
            week_rows.append({
                "index": w,
                "start": (week1 + timedelta(days=7 * (w - 1))).isoformat(),
                "quota": _num(quota),
                "lifts": _num(lifts),
                "met": met,
                "points": _num(points),
                "bonuses": bonuses,
                "by_type": {t: _num(v) for t, v in wk["by_type"].items()},
                "plank_seconds": _num(wk["plank_seconds"]),
                "pending": wk["pending"],
                "_led": led,
            })

        if status == "live":
            cur = week_rows[-1]
            this_week = {k: cur[k] for k in ("quota", "lifts", "met", "pending",
                                             "by_type", "plank_seconds")}
            this_week["leading"] = list(cur["_led"])
        elif status == "ended" and week_rows:
            cur = week_rows[-1]
            this_week = {k: cur[k] for k in ("quota", "lifts", "met", "pending",
                                             "by_type", "plank_seconds")}
            this_week["leading"] = []
        else:
            empty = _empty_week(1, week1, base, types)
            this_week = {k: empty[k] for k in ("quota", "lifts", "met", "pending",
                                               "by_type", "plank_seconds")}
            this_week["leading"] = []
        this_week = {"index": week_index, **this_week}
        for wr in week_rows:
            wr.pop("_led")

        counted = sorted(tally["counted"], key=lambda c: c[0])
        latest = counted[-1][1] if counted else None
        rows.append({
            "user_id": p.get("user_id"),
            "name": p.get("name"),
            "weight_class": p.get("weight_class"),
            "gender": p.get("gender"),
            "score": _num(total),
            "streak": run,
            "best_streak": best,
            "weeks_met": met_count,
            "this_week": this_week,
            "weeks": week_rows,
            "warmup_lifts": _num(tally["warmup"]),
            "best_by_lift": {},
            "form_score": None,
            "steadiness": None,
            "attempt_id": latest.get("attempt_id") if latest else None,
            "clip_url": (latest.get("annotated_video_url") or latest.get("video_url"))
            if latest else None,
            "thumbnail_url": None,
            "date": local_date(latest.get("created_at"), rules).isoformat() if latest else None,
            "attempt_count": len(counted),
            "history": [
                {"score": _num(lifts), "date": local_date(a.get("created_at"), rules).isoformat()}
                for _, a, lifts in counted
            ],
        })

    def sort_key(r):
        return (
            0 if r["score"] > 0 else 1,
            -r["score"],
            -r["streak"],
            -r["weeks_met"],
            -r["this_week"]["lifts"],
            (r["name"] or "").lower(),
            str(r["user_id"]),
        )

    rows.sort(key=sort_key)
    for n, r in enumerate(rows):
        r["rank"] = n + 1

    if status == "live":
        cur_start = week1 + timedelta(days=7 * (week_index - 1))
    elif status == "ended":
        cur_start = week1 + timedelta(days=7 * (weeks_total - 1))
    else:
        cur_start = week1
    cur_end = cur_start + timedelta(days=6)
    days_left = 0
    if status == "live":
        days_left = (cur_end - local_date(now, rules)).days + 1

    type_leaders = {}
    if status == "live":
        for t in scoring:
            idx = leaders[week_index].get(t)
            if idx:
                type_leaders[t] = sorted(
                    ({"user_id": tallies[j]["p"].get("user_id"),
                      "name": tallies[j]["p"].get("name"),
                      "amount": _num(amount(tallies[j], week_index, t))} for j in idx),
                    key=lambda e: ((e["name"] or "").lower(), str(e["user_id"])),
                )

    block = {
        "rules": rules,
        "status": status,
        "week_index": week_index,
        "weeks_total": weeks_total,
        "week_start": cur_start.isoformat(),
        "week_end": cur_end.isoformat(),
        "days_left": days_left,
        "type_leaders": type_leaders,
    }
    return rows, block
