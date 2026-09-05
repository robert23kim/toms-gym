"""Parser accuracy against real lane-screen photos (cached Vision OCR, no network)."""
import copy
import json
import pathlib

import pytest

from toms_gym.services import bowling_sheet_parser as bp

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "bowling"
NIGHT = sorted(p.stem[:-4] for p in FIXTURES.glob("night_*_ocr.json"))
GAME = sorted(p.stem[:-4] for p in FIXTURES.glob("game_*_ocr.json"))


def _load(stem):
    ocr = json.loads((FIXTURES / f"{stem}_ocr.json").read_text())
    truth = json.loads((FIXTURES / f"{stem}_truth.json").read_text())
    return ocr, truth


def _parse(stem, sheet_type):
    ocr, truth = _load(stem)
    return bp.parse_sheet(sheet_type, ocr["words"], ocr["symbols"], ocr["page_w"], ocr["page_h"]), truth


@pytest.mark.parametrize("stem", NIGHT)
def test_night_sheet_matches_truth(stem):
    parsed, truth = _parse(stem, "night")
    got = {p["name"]: p for p in parsed["players"]}
    assert list(got) == [p["name"] for p in truth["players"]]
    for tp in truth["players"]:
        p = got[tp["name"]]
        assert p["games"] == tp["games"], (stem, tp["name"])
        assert (p["scratch"], p["hdcp"], p["total"]) == (tp["scratch"], tp["hdcp"], tp["total"]), (stem, tp["name"])
        assert p["flagged"] is False, (stem, tp["name"], p["flag_reason"])
    assert parsed["team_name"] == truth["team"]["name"]


@pytest.mark.parametrize("stem", NIGHT)
def test_night_sheet_shape_games(stem):
    parsed, truth = _parse(stem, "night")
    rows = bp.shape_games(parsed, "night", "2026-08-28")
    assert len(rows) == 3 * len(truth["players"])
    tom = [r for r in rows if r["player_name"] == truth["players"][-1]["name"]]
    assert [r["total_score"] for r in tom] == truth["players"][-1]["games"]
    assert all(r["frames"] is None and r["played_on"] == "2026-08-28" for r in rows)
    assert all(r["hdcp"] == truth["players"][-1]["hdcp"] // 3 for r in tom)


def test_night_glare_cell_is_inferred_not_flagged():
    ocr, truth = _load(NIGHT[0])
    victim = truth["players"][1]
    words = [w for w in ocr["words"] if not (w["text"] == str(victim["total"]) and w["x"] > ocr["page_w"] * 0.8)]
    parsed = bp.parse_night_sheet(words, ocr["page_w"], ocr["page_h"])
    p = next(p for p in parsed["players"] if p["name"] == victim["name"])
    assert p["total"] == victim["total"] and p["inferred"] == ["total"] and not p["flagged"]


def test_night_corrupted_scratch_is_flagged_never_accepted():
    ocr, truth = _load(NIGHT[0])
    victim = truth["players"][0]
    words = copy.deepcopy(ocr["words"])
    for w in words:
        if w["text"] == str(victim["scratch"]) and w["x"] > ocr["page_w"] * 0.6:
            w["text"] = str(victim["scratch"] + 1)
    parsed = bp.parse_night_sheet(words, ocr["page_w"], ocr["page_h"])
    p = next(p for p in parsed["players"] if p["name"] == victim["name"])
    assert p["flagged"] and "scratch" in p["flag_reason"]


def test_night_no_header_raises():
    with pytest.raises(bp.SheetParseError):
        bp.parse_night_sheet([{"text": "Tom", "x": 10, "y": 10, "w": 5, "h": 5, "conf": 1}], 100, 100)


@pytest.mark.parametrize("stem", GAME)
def test_game_sheet_matches_truth(stem):
    parsed, truth = _parse(stem, "game")
    got = {p["name"].upper(): p for p in parsed["players"]}
    assert list(got) == [p["name"].upper() for p in truth["players"]]
    for tp in truth["players"]:
        p = got[tp["name"].upper()]
        assert p["printed_cumulative"] == tp["cumulative"], (stem, tp["name"])
        assert p["frames"] == tp["frames"], (stem, tp["name"], p["frames"])
        assert p["total"] == tp["total"]
        assert not p["flagged"], (stem, tp["name"], p["flag_reason"])
    assert parsed["team_name"] == truth["team_name"]


@pytest.mark.parametrize("stem", GAME)
def test_game_sheet_shape_games(stem):
    parsed, truth = _parse(stem, "game")
    rows = bp.shape_games(parsed, "game", "2026-08-28")
    assert [r["computed_total"] for r in rows] == [p["total"] for p in truth["players"]]
    assert all(r["frames"] and r["game_number"] == 1 and not r["flagged"] for r in rows)


def test_game_irreconcilable_score_is_flagged():
    ocr, truth = _load(GAME[0])
    words = copy.deepcopy(ocr["words"])
    last = truth["players"][0]
    for w in words:
        if w["text"] == str(last["cumulative"][4]) and abs(w["y"] - 288) < 20:
            w["text"] = "98"
    parsed = bp.parse_game_sheet(words, ocr["symbols"], ocr["page_w"], ocr["page_h"])
    p = parsed["players"][0]
    assert p["flagged"] and "frame" in p["flag_reason"]


def test_solver_recovers_dropped_dash():
    observed = [["X"], ["9"], ["X"], ["8"], ["X"], ["9", "/"], ["9", "/"], ["9", "/"], ["X"], ["X", "8"]]
    printed = [19, 28, 46, 54, 74, 93, 112, 132, 160, 178]
    frames, conflicts, _inferred = bp._solve_frames(observed, printed)
    assert conflicts == []
    assert frames == [["X"], ["9", "-"], ["X"], ["8", "-"], ["X"], ["9", "/"], ["9", "/"], ["9", "/"], ["X"], ["X", "8", "-"]]


def test_solver_returns_none_when_impossible():
    assert bp._solve_frames([[] for _ in range(10)], [31] + [None] * 9) == (None, [], [])


def _solve(observed, printed):
    return bp._solve_frames(observed, printed)


def test_inferred_marks_unread_frame_but_not_dropped_dash():
    # truth: 8 1 | 8 - | X | 9 / | 7 / | 9 / | 8 / | 7 / | 8 1 | 9 / X  = 17? use a real running score
    truth = [["8", "1"], ["8", "-"], ["X"], ["9", "/"], ["7", "/"], ["9", "/"], ["8", "/"], ["7", "/"], ["8", "1"], ["9", "/", "X"]]
    printed = bp.score_frames(truth)["cumulative"]
    observed = [list(f) for f in truth]
    observed[0] = ["1"]      # first-ball digit dropped: "1 8" and "8 1" both fit → inferred
    observed[1] = ["8"]      # trailing miss dropped: expected, not inferred
    observed[3] = []         # nothing read: "9 /" vs "8 /" … → inferred
    frames, conflicts, inferred = _solve(observed, printed)
    assert conflicts == []
    assert frames[1] == ["8", "-"]
    assert 1 in inferred and 4 in inferred
    assert 2 not in inferred


def test_inferred_marks_spare_with_unread_first_ball():
    truth = [["X"], ["8", "/"], ["9", "-"], ["X"], ["X"], ["X"], ["X"], ["X"], ["X"], ["X", "X", "X"]]
    printed = bp.score_frames(truth)["cumulative"]
    observed = [list(f) for f in truth]
    observed[1] = ["/"]
    frames, conflicts, inferred = _solve(observed, printed)
    assert frames[1][1] == "/" and frames[1][0] != "-"
    assert 2 in inferred


def test_fully_read_frames_are_not_inferred():
    truth = [["X"], ["8", "/"], ["9", "-"], ["7", "2"], ["X"], ["X"], ["X"], ["X"], ["X"], ["X", "X", "X"]]
    printed = bp.score_frames(truth)["cumulative"]
    frames, conflicts, inferred = _solve([list(f) for f in truth], printed)
    assert frames == truth
    assert inferred == []
