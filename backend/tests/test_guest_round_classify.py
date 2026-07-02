"""_classify_guest_round: partial scorecard rounds must never be scored as 18-hole.

Run with --noconftest (imports golf_routes, no DB calls).
Regression for the -42.0 leaderboard entry: a back-nine-only card scored
against an 18-hole rating.
"""
from toms_gym.routes.golf_routes import _classify_guest_round


def _holes(strokes_by_number):
    return [{'hole_number': n, 'par': 4, 'strokes': s, 'ocr_confidence': 0.9}
            for n, s in strokes_by_number.items()]


def test_full_round_is_scoreable():
    holes = _holes({n: 5 for n in range(1, 19)})
    scoreable, holes_count, valid = _classify_guest_round(holes)
    assert (scoreable, holes_count, len(valid)) == (True, 18, 18)


def test_back_nine_only_is_a_nine_hole_round_without_differential():
    holes = _holes({n: 5 for n in range(10, 19)})
    scoreable, holes_count, valid = _classify_guest_round(holes)
    assert (scoreable, holes_count, len(valid)) == (True, 9, 9)


def test_front_nine_only_is_a_nine_hole_round():
    holes = _holes({n: 5 for n in range(1, 10)})
    assert _classify_guest_round(holes)[:2] == (True, 9)


def test_single_hole_is_not_saveable():
    holes = _holes({10: 5})
    scoreable, holes_count, _ = _classify_guest_round(holes)
    assert holes_count is None


def test_partial_18_is_saved_but_not_scored():
    holes = _holes({n: 5 for n in range(1, 15)})  # 14 holes across both nines
    scoreable, holes_count, _ = _classify_guest_round(holes)
    assert (scoreable, holes_count) == (False, 18)


def test_nine_holes_spanning_both_nines_is_not_a_nine_hole_round():
    holes = _holes({n: 5 for n in list(range(1, 6)) + list(range(10, 14))})
    scoreable, holes_count, _ = _classify_guest_round(holes)
    assert (scoreable, holes_count) == (False, 18)


def test_nine_hole_differential_is_doubled_to_18_equivalent():
    """Back-nine 51 at default 72/113: 9-hole diff (51-36)=15.0 -> stored 30.0."""
    from toms_gym.services.handicap import compute_differential
    adjusted = 51
    nine = compute_differential(adjusted, 72.0 / 2.0, 113)
    assert round(nine * 2.0, 1) == 30.0
