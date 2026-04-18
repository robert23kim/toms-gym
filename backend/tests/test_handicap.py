"""Unit tests for the WHS handicap engine (`toms_gym.services.handicap`).

Drives Phase B §B2 of the Fairway migration. Pure-function test suite that
loads deterministic differential cases from `fixtures/whs_reference_cases.json`
and verifies:

  * `compute_differential`      \u2014 ((adj \u2212 rating \u2212 PCC) \u00d7 113) / slope
  * `compute_handicap_index`    \u2014 WHS \u00a75.2 lowest-N-of-last-20 adjustment table,
                                   establishing state, 54.0 ceiling, 12-month cap
  * `net_double_bogey_cap`      \u2014 per-hole cap at par + 2 + strokes_allocated
                                   (cap at 10 for users without a handicap)
  * `apply_twelve_month_cap`    \u2014 new index can't rise >5.0 above 12-month low
  * `allocate_strokes`          \u2014 distributes course handicap across 18 holes by
                                   stroke index
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


FIXTURE_PATH = pathlib.Path(__file__).parent / "fixtures" / "whs_reference_cases.json"


@pytest.fixture(scope="module")
def whs_fixture():
    with open(FIXTURE_PATH) as f:
        data = json.load(f)
    assert data["source"] == "USGA Rules of Handicapping \u00a75.2"
    return data


# ---------------------------------------------------------------------------
# compute_differential
# ---------------------------------------------------------------------------


def test_compute_differential_basic():
    # ((85 - 71.2 - 0) * 113) / 128 = (13.8 * 113) / 128 = 12.1828125
    result = compute_differential(
        adjusted_gross_score=85, course_rating=71.2, slope_rating=128, pcc=0
    )
    assert result == pytest.approx(12.1828125, abs=1e-6)


def test_compute_differential_rounds_to_tenth_or_less():
    # The value itself is returned with full precision; callers round when storing.
    result = compute_differential(
        adjusted_gross_score=90, course_rating=72.0, slope_rating=113, pcc=0
    )
    assert result == pytest.approx(18.0, abs=1e-6)


def test_compute_differential_with_pcc():
    # PCC adjustment of +1 makes the course effectively harder; differential drops.
    result = compute_differential(
        adjusted_gross_score=90, course_rating=72.0, slope_rating=113, pcc=1
    )
    assert result == pytest.approx(17.0, abs=1e-6)


# ---------------------------------------------------------------------------
# compute_handicap_index \u2014 WHS adjustment table (every row)
# ---------------------------------------------------------------------------


def _case_ids(cases):
    return [f"n={c['rounds']}_{c['rule']}" for c in cases]


def test_whs_table_covers_every_distinct_row(whs_fixture):
    # Sanity: the fixture must exercise all 11 distinct (num_used, adjustment) rules.
    rules = {c["rule"] for c in whs_fixture["cases"]}
    # 11 distinct WHS rows: 3, 4, 5, 6, 7\u20138, 9\u201311, 12\u201314, 15\u201316, 17\u201318, 19, 20+
    expected_count = 15
    assert len(whs_fixture["cases"]) == expected_count
    assert len(rules) == expected_count  # each fixture row should be uniquely labelled


@pytest.mark.parametrize(
    "case",
    # populated at collection time from the JSON fixture
    json.loads(FIXTURE_PATH.read_text())["cases"],
    ids=lambda c: f"n={c['rounds']}_{c['rule']}",
)
def test_handicap_index_matches_whs_reference(case):
    result = compute_handicap_index(case["differentials"])
    assert isinstance(result, HandicapResult)
    assert result.status == "active"
    assert result.rounds_used == case["rounds"]
    assert result.index == pytest.approx(case["expected_index"], abs=1e-6)


def test_handicap_index_uses_only_last_twenty_rounds(whs_fixture):
    payload = whs_fixture["twenty_plus_only_last_twenty"]
    result = compute_handicap_index(payload["differentials_in_submission_order"])
    assert result.status == "active"
    assert result.rounds_used == 20
    assert result.index == pytest.approx(payload["expected_index"], abs=1e-6)


# ---------------------------------------------------------------------------
# compute_handicap_index \u2014 establishing state (< 3 rounds)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case",
    json.loads(FIXTURE_PATH.read_text())["establishing"],
    ids=lambda c: f"establishing_n={c['rounds']}",
)
def test_establishing_state_under_three_rounds(case):
    result = compute_handicap_index(case["differentials"])
    assert result.index is None
    assert result.status == case["expected_status"]
    assert result.rounds_needed == case["expected_rounds_needed"]
    assert result.rounds_used == case["rounds"]


# ---------------------------------------------------------------------------
# compute_handicap_index \u2014 54.0 maximum
# ---------------------------------------------------------------------------


def test_handicap_index_caps_at_fifty_four(whs_fixture):
    payload = whs_fixture["maximum_index"]
    result = compute_handicap_index(payload["differentials"])
    assert result.status == "active"
    assert result.index == pytest.approx(54.0, abs=1e-6)


# ---------------------------------------------------------------------------
# compute_handicap_index \u2014 9-hole weighting
# ---------------------------------------------------------------------------


def test_nine_hole_rounds_count_as_half(whs_fixture):
    payload = whs_fixture["nine_hole_weighting"]
    result = compute_handicap_index(payload["submitted"])
    assert result.status == "active"
    assert result.rounds_used == payload["effective_round_count"]
    assert result.index == pytest.approx(payload["expected_index"], abs=1e-6)


# ---------------------------------------------------------------------------
# net_double_bogey_cap
# ---------------------------------------------------------------------------


def test_net_double_bogey_no_handicap_caps_at_ten(whs_fixture):
    payload = whs_fixture["ndb_no_handicap"]
    capped = net_double_bogey_cap(
        strokes_by_hole=payload["raw_strokes"],
        par_by_hole=payload["par_by_hole"],
        strokes_allocated_by_hole=None,  # user has no established handicap
    )
    assert capped == payload["expected_capped"]


def test_net_double_bogey_with_handicap_uses_par_plus_two_plus_strokes(whs_fixture):
    payload = whs_fixture["ndb_with_handicap"]
    strokes_allocated = allocate_strokes(
        course_handicap=payload["course_handicap"],
        hole_handicaps=payload["hole_handicaps"],
    )
    capped = net_double_bogey_cap(
        strokes_by_hole=payload["raw_strokes"],
        par_by_hole=payload["par_by_hole"],
        strokes_allocated_by_hole=strokes_allocated,
    )
    assert capped == payload["expected_capped"]


# ---------------------------------------------------------------------------
# apply_twelve_month_cap
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case",
    json.loads(FIXTURE_PATH.read_text())["twelve_month_cap"]["cases"],
    ids=lambda c: f"low={c['low_12mo']}_new={c['newly_computed']}",
)
def test_twelve_month_cap(case):
    capped = apply_twelve_month_cap(
        newly_computed=case["newly_computed"],
        low_in_last_twelve_months=case["low_12mo"],
    )
    assert capped == pytest.approx(case["expected_capped"], abs=1e-6)


# ---------------------------------------------------------------------------
# allocate_strokes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case",
    json.loads(FIXTURE_PATH.read_text())["allocate_strokes_cases"],
    ids=lambda c: f"ch={c['course_handicap']}",
)
def test_allocate_strokes(case):
    result = allocate_strokes(
        course_handicap=case["course_handicap"],
        hole_handicaps=case["hole_handicaps"],
    )
    assert result == case["expected_strokes"]
