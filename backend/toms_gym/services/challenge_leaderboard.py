"""Per-challenge leaderboard ranking — pure functions over attempts.

This module is side-effect free and DB-free so it can be unit-tested in
isolation, mirroring `services/handicap.py`. The route layer loads participants
and their completed attempts (LEFT JOIN LiftingResult for plank hold time / form
score / annotated clip) and calls `rank_challenge()` to produce ranked rows.

A challenge is ranked by exactly one metric:

* ``"time"`` (plank challenges) — rank by the athlete's longest hold
  (``held_s``) across their completed plank attempts, descending.
* ``"weight"`` (lifting challenges) — rank by best-lift total: per athlete, the
  max ``weight_kg`` per lift type among completed attempts, summed. Planks are
  excluded from a weight board (you can't add seconds to kilograms).
"""
from __future__ import annotations

from functools import cmp_to_key
from typing import List, Optional


def _created_key(created) -> str:
    """Return a chronologically-sortable string for a created_at value.

    Accepts datetime/date objects or ISO strings; ``None`` sorts last.
    """
    if created is None:
        return "9999-12-31"
    if hasattr(created, "isoformat"):
        return created.isoformat()
    return str(created)


def _iso_date(created) -> Optional[str]:
    """Return the YYYY-MM-DD portion of a created_at value (or None)."""
    if created is None:
        return None
    if hasattr(created, "isoformat"):
        text = created.isoformat()
    else:
        text = str(created)
    # Trim a time component if present ("2026-07-01T10:00:00" -> "2026-07-01").
    return text.split("T")[0][:10]


def _clip_url(attempt) -> Optional[str]:
    """Prefer the annotated clip; fall back to the raw upload."""
    return attempt.get("annotated_video_url") or attempt.get("video_url")


def _compare_time_attempts(a, b) -> int:
    """Best-first ordering for plank attempts: longest hold, then higher form
    score, then earliest created_at."""
    ah, bh = a["held_s"], b["held_s"]
    if ah != bh:
        return -1 if ah > bh else 1
    af = a["form_score"] if a["form_score"] is not None else float("-inf")
    bf = b["form_score"] if b["form_score"] is not None else float("-inf")
    if af != bf:
        return -1 if af > bf else 1
    ak, bk = _created_key(a["created_at"]), _created_key(b["created_at"])
    if ak != bk:
        return -1 if ak < bk else 1
    return 0


def _rank_time(participants) -> List[dict]:
    rows = []
    for p in participants:
        # A hold time only exists once analysis has produced it, so the metric's
        # ``held_s is not None`` check already gates on completion. We accept any
        # non-failed attempt here so the ranking mirrors the weight board.
        submitted = [a for a in p.get("attempts", []) if a.get("status") != "failed"]
        qualifying = [
            a for a in submitted
            if a.get("lift_type") == "Plank" and a.get("held_s") is not None
        ]

        chrono = sorted(qualifying, key=lambda a: _created_key(a["created_at"]))
        history = [
            {"score": a["held_s"], "date": _iso_date(a["created_at"])}
            for a in chrono
        ]

        if qualifying:
            best = sorted(qualifying, key=cmp_to_key(_compare_time_attempts))[0]
            score = best["held_s"]
            row = {
                "score": score,
                "best_by_lift": {"Plank": score},
                "form_score": best["form_score"],
                "attempt_id": best.get("attempt_id"),
                "clip_url": _clip_url(best),
                "thumbnail_url": None,
                "date": _iso_date(best["created_at"]),
                "_best_created": _created_key(best["created_at"]),
                "_best_form": best["form_score"],
            }
        else:
            row = {
                "score": 0,
                "best_by_lift": {},
                "form_score": None,
                "attempt_id": None,
                "clip_url": None,
                "thumbnail_url": None,
                "date": None,
                "_best_created": _created_key(None),
                "_best_form": None,
            }

        row.update({
            "user_id": p.get("user_id"),
            "name": p.get("name"),
            "weight_class": p.get("weight_class"),
            "gender": p.get("gender"),
            "attempt_count": len(qualifying),
            "history": history,
        })
        rows.append(row)

    def sort_key(r):
        form = r["_best_form"] if r["_best_form"] is not None else float("-inf")
        return (
            0 if r["score"] > 0 else 1,   # zero-score rows last
            -r["score"],                  # longest hold first
            -form,                        # higher form score first
            r["_best_created"],           # earliest created_at first
        )

    return _finalize(rows, sort_key)


def _rank_weight(participants) -> List[dict]:
    rows = []
    for p in participants:
        # The declared weight is known at upload time and never depends on
        # analysis (analysis grades form, not the load). Count any submitted
        # attempt that hasn't failed so a joined lifter shows on the podium
        # immediately — not only after the (often slow) analysis completes.
        submitted = [a for a in p.get("attempts", []) if a.get("status") != "failed"]
        # Planks carry a weight_kg but never belong on a weight board.
        qualifying = [
            a for a in submitted
            if a.get("weight_kg") is not None and a.get("lift_type") != "Plank"
        ]

        chrono = sorted(qualifying, key=lambda a: _created_key(a["created_at"]))
        history = [
            {"score": a["weight_kg"], "date": _iso_date(a["created_at"])}
            for a in chrono
        ]

        best_by_lift = {}
        for a in qualifying:
            lift = a["lift_type"]
            if lift not in best_by_lift or a["weight_kg"] > best_by_lift[lift]:
                best_by_lift[lift] = a["weight_kg"]
        score = sum(best_by_lift.values()) if best_by_lift else 0

        if qualifying:
            # Clip/date come from the single heaviest attempt (earliest breaks ties).
            best = min(
                qualifying,
                key=lambda a: (-a["weight_kg"], _created_key(a["created_at"])),
            )
            row = {
                "score": score,
                "best_by_lift": best_by_lift,
                "attempt_id": best.get("attempt_id"),
                "clip_url": _clip_url(best),
                "date": _iso_date(best["created_at"]),
                "_best_created": _created_key(best["created_at"]),
            }
        else:
            row = {
                "score": 0,
                "best_by_lift": {},
                "attempt_id": None,
                "clip_url": None,
                "date": None,
                "_best_created": _created_key(None),
            }

        row.update({
            "user_id": p.get("user_id"),
            "name": p.get("name"),
            "weight_class": p.get("weight_class"),
            "gender": p.get("gender"),
            "form_score": None,
            "thumbnail_url": None,
            "attempt_count": len(qualifying),
            "history": history,
        })
        rows.append(row)

    def sort_key(r):
        return (
            0 if r["score"] > 0 else 1,   # zero-score rows last
            -r["score"],                  # heaviest total first
            r["_best_created"],           # earliest created_at first
        )

    return _finalize(rows, sort_key)


def _finalize(rows, sort_key) -> List[dict]:
    rows.sort(key=sort_key)
    out = []
    for i, r in enumerate(rows):
        r.pop("_best_created", None)
        r.pop("_best_form", None)
        r["rank"] = i + 1
        out.append(r)
    return out


def rank_challenge(participants, *, metric) -> List[dict]:
    """Rank challenge participants best-first for the given metric.

    ``metric`` is ``"time"`` (plank: best hold) or ``"weight"`` (best-lift total).
    See the module docstring for the participant shape and scoring rules.
    """
    if metric == "time":
        return _rank_time(participants)
    if metric == "weight":
        return _rank_weight(participants)
    raise ValueError(f"unknown metric: {metric!r}")
