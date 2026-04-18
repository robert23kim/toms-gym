"""WHS handicap engine \u2014 pure functions over differentials.

All functions here are side-effect free and DB-free so they can be unit-tested
in isolation. The route layer is responsible for fetching rounds, calling these
helpers, and writing HandicapSnapshot rows.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional


# rounds_available -> (differentials_to_use, adjustment)
# Matches spec \u00a7B2 WHS table exactly: 9-11 \u2192 lowest 3, 12-14 \u2192 lowest 4,
# 15-16 \u2192 lowest 5, 17-18 \u2192 lowest 6, 19 \u2192 lowest 7, 20+ \u2192 lowest 8.
WHS_TABLE = {
    3:  (1, -2.0), 4:  (1, -1.0), 5:  (1,  0),
    6:  (2, -1.0), 7:  (2,  0),   8:  (2,  0),
    9:  (3,  0),  10:  (3,  0),  11:  (3,  0),
    12: (4,  0),  13:  (4,  0),  14:  (4,  0),
    15: (5,  0),  16:  (5,  0),
    17: (6,  0),  18:  (6,  0),
    19: (7,  0),
    20: (8,  0),
}
MAX_INDEX = 54.0
PCC = 0  # MVP: Playing Conditions Calculation disabled.


@dataclass
class HandicapResult:
    handicap_index: Optional[float]
    diffs_used_count: int
    adjustment: float
    status: str  # "active" | "establishing"
    rounds_needed: int  # 0 when active


def net_double_bogey_cap(
    par: int,
    strokes_received: Optional[int] = None,
    actual: Optional[int] = None,
) -> int:
    """Cap strokes at NDB (par + 2 + strokes received on that hole).

    If the user has no handicap yet, cap at a flat 10 per spec \u00a7B2.
    When `actual` is provided, returns min(actual, cap).
    """
    if strokes_received is None:
        cap = 10
    else:
        cap = par + 2 + strokes_received
    if actual is None:
        return cap
    return min(actual, cap)


def compute_differential(adjusted_total: float, rating: float, slope: int) -> float:
    """((adjusted \u2212 rating \u2212 PCC) \u00d7 113) / slope.

    Works for both 18-hole and 9-hole rounds \u2014 the caller chooses the right
    rating/slope values for the round length.
    """
    return ((adjusted_total - rating - PCC) * 113) / slope


def _effective_round_count(nine_hole_flags: List[bool]) -> int:
    """9-hole rounds count as 0.5 toward the last-20 pool. Integer floor."""
    full = sum(1 for f in nine_hole_flags if not f)
    nines = sum(1 for f in nine_hole_flags if f)
    return full + nines // 2


def compute_handicap_index(
    differentials: List[float],
    nine_hole_flags: List[bool],
) -> HandicapResult:
    """Compute WHS index from the user's last-20 differentials.

    Inputs are expected to be ordered newest-first by the caller; this function
    only cares about the values themselves (WHS picks lowest N).
    """
    assert len(differentials) == len(nine_hole_flags), "length mismatch"
    effective = _effective_round_count(nine_hole_flags)

    if effective < 3:
        return HandicapResult(
            handicap_index=None,
            diffs_used_count=0,
            adjustment=0.0,
            status="establishing",
            rounds_needed=3 - effective,
        )

    lookup_n = min(effective, 20)
    diffs_to_use, adjustment = WHS_TABLE[lookup_n]
    best = sorted(differentials)[:diffs_to_use]
    avg = sum(best) / diffs_to_use
    raw = math.trunc((avg + adjustment) * 0.96 * 10) / 10
    index = min(raw, MAX_INDEX)

    return HandicapResult(
        handicap_index=index,
        diffs_used_count=diffs_to_use,
        adjustment=adjustment,
        status="active",
        rounds_needed=0,
    )


def allocate_strokes(
    handicap_index: Optional[float],
    hole_handicaps: Optional[List[int]],
) -> Optional[List[int]]:
    """Return per-hole strokes received given an 18-slot hole-handicap array.

    `hole_handicaps` is the usual 1..18 ranking where rank 1 is hardest.
    Total strokes received = floor(handicap_index); allocated one-per-hole by
    rank. Handicap > 18 wraps around (hole rank 1 gets 2 strokes before rank 2
    gets a second stroke, etc.).

    Returns None when either input is missing \u2014 caller should fall back to
    the flat NDB-10 cap per spec \u00a7B2.
    """
    if handicap_index is None or not hole_handicaps or len(hole_handicaps) != 18:
        return None
    total = int(math.floor(handicap_index))
    out = [0] * 18
    # rank 1 is hardest; assign strokes starting from rank 1.
    order = sorted(range(18), key=lambda i: hole_handicaps[i])
    for k in range(total):
        out[order[k % 18]] += 1
    return out


def apply_twelve_month_cap(
    new_index: float, twelve_month_low: Optional[float]
) -> float:
    """Cap handicap rise at 5.0 above the user's 12-month low.

    The cap never pushes the index down; only prevents it rising too far.
    """
    if twelve_month_low is None:
        return new_index
    ceiling = twelve_month_low + 5.0
    return min(new_index, ceiling)
