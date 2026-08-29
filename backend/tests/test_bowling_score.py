import pytest

from toms_gym.services.bowling_score import (
    InvalidFrame,
    frame_pins,
    infer_night_row,
    score_frames,
    validate_night_row,
)

PERFECT = [["X"]] * 9 + [["X", "X", "X"]]
GUTTER = [["-", "-"]] * 10
ALL_NINE_SPARE = [["9", "/"]] * 9 + [["9", "/", "9"]]
TOM = [["X"], ["8", "1"], ["X"], ["9", "/"], ["X"], ["6", "3"], ["8", "/"], ["X"], ["9", "-"], ["7", "/", "9"]]
CHRIS = [["X"], ["9", "-"], ["X"], ["8", "-"], ["X"], ["9", "/"], ["9", "/"], ["9", "/"], ["X"], ["X", "8", "-"]]


def test_perfect_game():
    r = score_frames(PERFECT)
    assert r["total"] == 300
    assert r["valid"]
    assert r["cumulative"] == [30 * i for i in range(1, 11)]


def test_gutter_game():
    assert score_frames(GUTTER)["total"] == 0


def test_all_nine_spare():
    assert score_frames(ALL_NINE_SPARE)["total"] == 190


def test_real_fixture_rows():
    assert score_frames(TOM)["cumulative"] == [19, 28, 48, 68, 87, 96, 116, 135, 144, 163]
    assert score_frames(CHRIS)["cumulative"] == [19, 28, 46, 54, 74, 93, 112, 132, 160, 178]


def test_tenth_frame_variants():
    assert score_frames([["-", "-"]] * 9 + [["X", "X", "X"]])["total"] == 30
    assert score_frames([["-", "-"]] * 9 + [["X", "9", "/"]])["total"] == 20
    assert score_frames([["-", "-"]] * 9 + [["9", "/", "X"]])["total"] == 20
    assert score_frames([["-", "-"]] * 9 + [["9", "-"]])["total"] == 9


def test_foul_counts_zero():
    assert frame_pins(["F", "9"], 0) == [0, 9]


def test_invalid_frames_flagged_not_raised():
    r = score_frames([["9", "9"]] + [["-", "-"]] * 9)
    assert not r["valid"]
    assert "frame 1" in r["errors"][0]


def test_partial_game_incomplete():
    r = score_frames([["X"], ["9", "/"]])
    assert r["complete"] is False
    assert r["cumulative"] == [20, 30]


def test_frame_pins_rejects_third_ball_before_tenth():
    with pytest.raises(InvalidFrame):
        frame_pins(["9", "-", "5"], 3)


def test_strike_ends_the_frame_before_the_tenth():
    with pytest.raises(InvalidFrame):
        frame_pins(["X", "5"], 0)
    r = score_frames([["X", "5"]] + [["-", "-"]] * 9)
    assert not r["valid"] and "frame 1" in r["errors"][0]


def test_tenth_frame_requires_bonus_ball():
    with pytest.raises(InvalidFrame):
        frame_pins(["X"], 9)
    with pytest.raises(InvalidFrame):
        frame_pins(["9", "/"], 9)
    with pytest.raises(InvalidFrame):
        frame_pins(["9", "-", "5"], 9)


def test_validate_night_row():
    assert validate_night_row([164, 236, 196], 596, 111, 707) == (True, None)
    ok, why = validate_night_row([164, 236, 196], 597, 111, 707)
    assert not ok and "scratch" in why
    ok, why = validate_night_row([164, 236, 196], 596, 111, 708)
    assert not ok and "total" in why
    ok, why = validate_night_row([164, None, 196], 596, 111, 707)
    assert not ok and "missing" in why


def test_infer_missing_total():
    row, inferred = infer_night_row([225, 205, 176], 606, 186, None)
    assert row["total"] == 792 and inferred == ["total"]


def test_infer_missing_game():
    row, inferred = infer_night_row([116, None, 91], 340, 270, 610)
    assert row["games"] == [116, 133, 91] and inferred == ["games[1]"]


def test_infer_missing_scratch_and_hdcp():
    row, inferred = infer_night_row([116, 133, 91], None, None, 610)
    assert row["scratch"] == 340
    assert row["hdcp"] == 270
    assert inferred == ["scratch", "hdcp"]


def test_infer_leaves_two_missing_games_alone():
    row, inferred = infer_night_row([116, None, None], 340, 270, 610)
    assert row["games"] == [116, None, None] and inferred == []
