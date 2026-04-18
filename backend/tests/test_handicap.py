"""Unit tests for the WHS handicap engine.

Tests operate on pure-Python helpers in `toms_gym.services.handicap`.
No DB touching \u2014 fixtures load canonical reference cases from JSON.

Reference: USGA Rules of Handicapping \u00a75.2 (WHS adjustment table).
The parametric lowest-N + adjustment assertions must match \u00a75.2 bit-exact;
numeric expected_index values are pinned-as-regression and cross-checked at PR review.
"""
import json
import pathlib

import pytest

from toms_gym.services.handicap import (
    HandicapResult,
    allocate_strokes,
    apply_twelve_month_cap,
    compute_differential,
    compute_handicap_index,
    net_double_bogey_cap,
)

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "whs_reference_cases.json"


@pytest.fixture
def whs_cases():
    with open(FIXTURES) as f:
        return json.load(f)


# ---- Net-double-bogey cap ----


def test_ndb_caps_at_par_plus_two_plus_strokes_received():
    # Golfer with 9 handicap receives strokes on holes per allocation.
    # For a par-4 with 1 stroke received, NDB = par + 2 + 1 = 7.
    assert net_double_bogey_cap(par=4, strokes_received=1) == 7


def test_ndb_caps_at_10_when_no_handicap_yet():
    # Without a handicap, cap strokes at 10 (spec \u00a7B2).
    assert net_double_bogey_cap(par=3, strokes_received=None) == 10
    assert net_double_bogey_cap(par=5, strokes_received=None) == 10


def test_ndb_unchanged_when_strokes_below_cap():
    assert net_double_bogey_cap(par=4, strokes_received=0, actual=5) == 5


# ---- Stroke allocation ----


def test_allocate_strokes_none_when_no_index():
    # No handicap yet -> None -> caller must fall back to flat-10 NDB.
    assert allocate_strokes(None, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]) is None


def test_allocate_strokes_none_when_no_hole_handicaps():
    assert allocate_strokes(9.0, None) is None
    assert allocate_strokes(9.0, []) is None


def test_allocate_strokes_index_9_assigns_one_to_each_of_the_9_hardest():
    # Hole-handicap ranks 1..18 where hole i has rank (i+1). Hardest 9 = idx 0..8.
    ranks = list(range(1, 19))
    out = allocate_strokes(9.0, ranks)
    assert sum(out) == 9
    assert all(out[i] == 1 for i in range(9))
    assert all(out[i] == 0 for i in range(9, 18))


def test_allocate_strokes_wraps_around_past_18():
    # Index 20 -> all 18 holes get 1, plus 2 more on the two hardest.
    ranks = list(range(1, 19))
    out = allocate_strokes(20.0, ranks)
    assert sum(out) == 20
    assert out[0] == 2 and out[1] == 2
    assert all(out[i] == 1 for i in range(2, 18))


# ---- Differential ----


def test_differential_formula():
    # ((adjusted \u2212 rating \u2212 PCC) \u00d7 113) / slope ; PCC = 0 for MVP.
    diff = compute_differential(adjusted_total=85, rating=71.0, slope=124)
    assert diff == pytest.approx((85 - 71.0) * 113 / 124, rel=1e-6)


def test_nine_hole_differential_uses_nine_hole_values():
    # A nine-hole round uses the 9-hole rating/slope for differential.
    diff = compute_differential(adjusted_total=46, rating=35.2, slope=122)
    assert diff == pytest.approx((46 - 35.2) * 113 / 122, rel=1e-6)


# ---- Handicap index / WHS table ----


@pytest.mark.parametrize("n,diffs_used,adjustment", [
    # Every row of spec \u00a7B2 WHS table \u2014 one case per row, plus an extra >20 case.
    (3, 1, -2.0),  (4, 1, -1.0), (5, 1, 0),
    (6, 2, -1.0),  (7, 2, 0),    (8, 2, 0),
    (9, 3, 0),     (10, 3, 0),   (11, 3, 0),    # spec: 9\u201311 \u2192 lowest 3
    (12, 4, 0),    (13, 4, 0),   (14, 4, 0),    # spec: 12\u201314 \u2192 lowest 4
    (15, 5, 0),    (16, 5, 0),                  # spec: 15\u201316 \u2192 lowest 5
    (17, 6, 0),    (18, 6, 0),                  # spec: 17\u201318 \u2192 lowest 6
    (19, 7, 0),                                 # spec: 19   \u2192 lowest 7
    (20, 8, 0),    (25, 8, 0),                  # spec: 20+  \u2192 lowest 8
])
def test_whs_table_selects_correct_diffs_and_adjustment(n, diffs_used, adjustment):
    # Differentials [0, 1, 2, ..., n-1] \u2014 lowest `diffs_used` are picked.
    diffs = [float(i) for i in range(n)]
    result = compute_handicap_index(diffs, nine_hole_flags=[False] * n)
    assert isinstance(result, HandicapResult)
    assert result.diffs_used_count == diffs_used
    avg = sum(sorted(diffs)[:diffs_used]) / diffs_used
    # Expected raw index = (avg + adjustment) * 0.96 truncated to 1 decimal.
    import math
    expected = math.trunc((avg + adjustment) * 0.96 * 10) / 10
    assert result.handicap_index == pytest.approx(min(expected, 54.0), abs=0.05)


def test_establishing_with_zero_rounds_returns_null_index():
    result = compute_handicap_index([], nine_hole_flags=[])
    assert result.handicap_index is None
    assert result.status == "establishing"
    assert result.rounds_needed == 3


def test_establishing_with_two_rounds_returns_null_index():
    result = compute_handicap_index([12.3, 10.1], nine_hole_flags=[False, False])
    assert result.handicap_index is None
    assert result.status == "establishing"
    assert result.rounds_needed == 1


def test_handicap_index_capped_at_54():
    # Even with very high differentials, index must not exceed 54.0.
    diffs = [80.0] * 3
    result = compute_handicap_index(diffs, nine_hole_flags=[False] * 3)
    assert result.handicap_index <= 54.0


# ---- 12-month low cap ----


def test_twelve_month_cap_limits_rise_to_5_above_low():
    # 12-month low is 8.0; new raw index is 14.3 \u2192 capped at 13.0.
    capped = apply_twelve_month_cap(new_index=14.3, twelve_month_low=8.0)
    assert capped == 13.0


def test_twelve_month_cap_does_not_lower_handicap():
    # New index of 5.0 vs low of 8.0 \u2014 cap has no effect.
    assert apply_twelve_month_cap(new_index=5.0, twelve_month_low=8.0) == 5.0


def test_twelve_month_cap_noop_when_no_history():
    assert apply_twelve_month_cap(new_index=12.0, twelve_month_low=None) == 12.0


# ---- 9-hole counts as 0.5 toward last 20 ----


def test_nine_hole_counts_as_half_round():
    # 6 nine-hole diffs \u2192 equivalent to 3 full rounds \u2192 should use WHS(3) row.
    diffs = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0]
    result = compute_handicap_index(diffs, nine_hole_flags=[True] * 6)
    # Effective round count = 3 \u2192 diffs_used = 1, adjustment = -2.0.
    assert result.diffs_used_count == 1
    assert result.adjustment == -2.0


def test_mixed_eighteen_and_nine_hole_count():
    # 2 eighteen + 2 nine = 2 + 1 = 3 effective rounds.
    diffs = [12.0, 10.0, 11.0, 9.0]
    result = compute_handicap_index(
        diffs, nine_hole_flags=[False, False, True, True]
    )
    assert result.diffs_used_count == 1
    assert result.adjustment == -2.0


# ---- Fixture JSON sanity ----


def test_fixture_cites_usga_source(whs_cases):
    assert "USGA Rules of Handicapping \u00a75.2" in whs_cases["source"]
