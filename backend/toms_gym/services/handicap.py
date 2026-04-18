"""WHS handicap engine.

Pure functions implementing USGA World Handicap System \u00a75.2 math:

  * `compute_differential`    \u2014 score differential from adjusted gross score,
                                 course rating, slope rating, and PCC.
  * `net_double_bogey_cap`    \u2014 per-hole cap at par + 2 + strokes_allocated
                                 (or a flat 10 for users without a handicap).
  * `allocate_strokes`        \u2014 distributes course handicap across 18 holes by
                                 stroke index.
  * `compute_handicap_index`  \u2014 WHS lowest-N-of-last-20 adjustment table,
                                 establishing state, 54.0 ceiling, 9-hole weighting.
  * `apply_twelve_month_cap`  \u2014 new index may not rise >5.0 above the user's
                                 lowest snapshot in the trailing 12 months.

No database access; callers persist `HandicapSnapshot` rows.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Union

# WHS \u00a75.2 adjustment table: rounds_in_last_20 -> (num_lowest_differentials_to_use, adjustment)
# Corrected per Fairway Phase B plan Revision 1 fix #1: rows 10, 11, 14, 15, 16 use 3, 3, 4, 5, 5.
WHS_TABLE = {
    3:  (1, -2.0),
    4:  (1, -1.0),
    5:  (1,  0.0),
    6:  (2, -1.0),
    7:  (2,  0.0),
    8:  (2,  0.0),
    9:  (3,  0.0),
    10: (3,  0.0),
    11: (3,  0.0),
    12: (4,  0.0),
    13: (4,  0.0),
    14: (4,  0.0),
    15: (5,  0.0),
    16: (5,  0.0),
    17: (6,  0.0),
    18: (6,  0.0),
    19: (7,  0.0),
    20: (8,  0.0),
}

MAX_HANDICAP_INDEX = 54.0
NO_HANDICAP_HOLE_CAP = 10
MIN_ROUNDS_TO_ESTABLISH = 3
TWELVE_MONTH_RISE_LIMIT = 5.0


@dataclass
class HandicapResult:
    """Outcome of `compute_handicap_index`.

    `status == "establishing"` when fewer than 3 effective rounds have been
    submitted; `index` is None and `rounds_needed` counts down to 3.
    `status == "active"` otherwise; `index` is the WHS handicap index, floored
    by 54.0.
    """

    index: Optional[float]
    status: str
    rounds_used: int
    rounds_needed: Optional[int] = None


# ---------------------------------------------------------------------------
# Differential
# ---------------------------------------------------------------------------


def compute_differential(
    adjusted_gross_score: float,
    course_rating: float,
    slope_rating: float,
    pcc: float = 0.0,
) -> float:
    """Score differential per WHS \u00a75.1.

    `((adjusted_gross_score \u2212 course_rating \u2212 pcc) \u00d7 113) / slope_rating`
    """
    return ((adjusted_gross_score - course_rating - pcc) * 113.0) / slope_rating


# ---------------------------------------------------------------------------
# Net double bogey
# ---------------------------------------------------------------------------


def net_double_bogey_cap(
    strokes_by_hole: Sequence[int],
    par_by_hole: Sequence[int],
    strokes_allocated_by_hole: Optional[Sequence[int]] = None,
) -> List[int]:
    """Apply WHS net-double-bogey cap per hole.

    For users with an established handicap, the per-hole cap is
    `par + 2 + strokes_allocated_this_hole`. For users without a handicap,
    the flat cap is 10 (WHS \u00a75.1b).
    """
    if len(strokes_by_hole) != len(par_by_hole):
        raise ValueError("strokes_by_hole and par_by_hole must be the same length")
    if strokes_allocated_by_hole is not None and len(strokes_allocated_by_hole) != len(strokes_by_hole):
        raise ValueError("strokes_allocated_by_hole must match strokes_by_hole length")

    capped: List[int] = []
    for i, strokes in enumerate(strokes_by_hole):
        if strokes_allocated_by_hole is None:
            cap = NO_HANDICAP_HOLE_CAP
        else:
            cap = par_by_hole[i] + 2 + strokes_allocated_by_hole[i]
        capped.append(min(strokes, cap))
    return capped


# ---------------------------------------------------------------------------
# Stroke allocation
# ---------------------------------------------------------------------------


def allocate_strokes(course_handicap: int, hole_handicaps: Sequence[int]) -> List[int]:
    """Distribute `course_handicap` strokes across holes by stroke index.

    Each hole receives one stroke when its stroke index \u2264 `course_handicap`.
    Handicaps above 18 wrap: a 22-stroke player gets one stroke on every hole
    plus a second stroke on the 4 hardest (stroke indexes 1\u20134). Negative
    course handicaps clamp to zero.
    """
    n = len(hole_handicaps)
    base = max(0, course_handicap) // n if n else 0
    remainder = max(0, course_handicap) - base * n
    return [base + (1 if hole_handicaps[i] <= remainder else 0) for i in range(n)]


# ---------------------------------------------------------------------------
# Handicap index
# ---------------------------------------------------------------------------


_RoundLike = Union[float, dict]


def _normalize_rounds(rounds: Sequence[_RoundLike]) -> List[dict]:
    normalized: List[dict] = []
    for r in rounds:
        if isinstance(r, dict):
            holes = int(r.get("holes", 18))
            differential = float(r["differential"])
        else:
            holes = 18
            differential = float(r)
        normalized.append({"holes": holes, "differential": differential})
    return normalized


def _effective_round_count(rounds: Sequence[dict]) -> int:
    """WHS 9-hole weighting: a 9-hole round counts as 0.5, 18-hole as 1.0."""
    weighted = sum(0.5 if r["holes"] == 9 else 1.0 for r in rounds)
    return int(weighted)  # floor


def compute_handicap_index(rounds: Sequence[_RoundLike]) -> HandicapResult:
    """Compute a WHS handicap index from submitted rounds (chronological order,
    most recent last).

    Accepts either:
      * a list of floats \u2014 treated as 18-hole differentials, or
      * a list of dicts `{"holes": 9|18, "differential": float}`.
    """
    all_rounds = _normalize_rounds(rounds)
    # WHS considers only the most recent 20 rounds.
    window = all_rounds[-20:]
    effective = _effective_round_count(window)

    if effective < MIN_ROUNDS_TO_ESTABLISH:
        return HandicapResult(
            index=None,
            status="establishing",
            rounds_used=effective,
            rounds_needed=MIN_ROUNDS_TO_ESTABLISH - effective,
        )

    num_lowest, adjustment = WHS_TABLE[min(effective, 20)]
    lowest = sorted(r["differential"] for r in window)[:num_lowest]
    raw_index = (sum(lowest) / num_lowest) + adjustment
    index = min(MAX_HANDICAP_INDEX, raw_index)

    return HandicapResult(index=index, status="active", rounds_used=effective)


# ---------------------------------------------------------------------------
# 12-month cap
# ---------------------------------------------------------------------------


def apply_twelve_month_cap(
    newly_computed: float,
    low_in_last_twelve_months: Optional[float],
) -> float:
    """WHS \u00a75.8 soft cap: the index may not rise more than 5.0 strokes above
    the user's lowest handicap index from the trailing 12 months. When no
    prior snapshot exists, the newly-computed value is returned unchanged.
    """
    if low_in_last_twelve_months is None:
        return newly_computed
    ceiling = low_in_last_twelve_months + TWELVE_MONTH_RISE_LIMIT
    return min(newly_computed, ceiling)
