"""Pure champion shaping — DB-free."""
from toms_gym.services.champions import shape_champions


def _comp(cid, name, end):
    return {"id": cid, "name": name, "end_date": end}


def _lb(metric, rows):
    return {"metric": metric, "rows": rows}


def _row(rank, name, uid, score, attempt="a1"):
    return {"rank": rank, "name": name, "user_id": uid, "score": score,
            "attempt_id": attempt}


def test_rank_one_becomes_champion():
    out = shape_champions([{
        "competition": _comp("c1", "Summer plank challenge", "2026-07-31"),
        "leaderboard": _lb("time", [_row(1, "wonder725", "u1", 275.4),
                                    _row(2, "victoria", "u2", 244.9)]),
    }])
    assert len(out) == 1
    c = out[0]
    assert c["name"] == "wonder725"
    assert c["user_id"] == "u1"
    assert c["competition_name"] == "Summer plank challenge"
    assert c["metric"] == "time"
    assert c["score"] == 275.4
    assert c["ended_on"] == "2026-07-31"
    assert c["attempt_id"] == "a1"


def test_challenge_with_no_valued_entries_produces_no_champion():
    out = shape_champions([{
        "competition": _comp("c1", "Empty", "2026-07-31"),
        "leaderboard": _lb("time", [_row(1, "joiner", "u1", 0),
                                    _row(2, "joiner2", "u2", None)]),
    }])
    assert out == []


def test_sorted_newest_ended_first():
    out = shape_champions([
        {"competition": _comp("old", "Old", "2026-05-01"),
         "leaderboard": _lb("weight", [_row(1, "a", "u1", 100)])},
        {"competition": _comp("new", "New", "2026-07-31"),
         "leaderboard": _lb("time", [_row(1, "b", "u2", 200)])},
    ])
    assert [c["competition_id"] for c in out] == ["new", "old"]


def test_missing_leaderboard_is_skipped():
    out = shape_champions([{"competition": _comp("c1", "Broken", "2026-07-31"),
                            "leaderboard": None}])
    assert out == []


def test_hall_of_fame_context_fields():
    out = shape_champions([{
        "competition": _comp("c1", "Summer plank challenge", "2026-07-31"),
        "leaderboard": _lb("time", [
            {**_row(1, "wonder725", "u1", 275.4), "attempt_count": 3, "date": "2026-07-20"},
            _row(2, "victoria", "u2", 244.9),
            _row(3, "sam", "u3", 200.0),
            _row(4, "joiner", "u4", 0, attempt=None),
        ]),
    }])
    c = out[0]
    assert c["runners_up"] == [
        {"name": "victoria", "user_id": "u2", "score": 244.9},
        {"name": "sam", "user_id": "u3", "score": 200.0},
    ]
    assert c["field_size"] == 3
    assert c["margin"] == 30.5
    assert c["winner_attempts"] == 3
    assert c["won_on"] == "2026-07-20"


def test_solo_champion_has_no_margin():
    out = shape_champions([{
        "competition": _comp("c1", "Solo", "2026-07-31"),
        "leaderboard": _lb("weight", [_row(1, "a", "u1", 100)]),
    }])
    c = out[0]
    assert c["runners_up"] == []
    assert c["field_size"] == 1
    assert c["margin"] is None
    assert c["winner_attempts"] == 1
    assert c["won_on"] is None


def test_consistency_board_champion_is_rank_one_on_points():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from toms_gym.services.challenge_leaderboard import rank_challenge

    ny = ZoneInfo("America/New_York")

    def att(aid, day, reps):
        return {"attempt_id": aid, "lift_type": "Pushup", "status": "completed",
                "created_at": datetime(2026, 11, day, 12, tzinfo=ny), "video_url": "v",
                "annotated_video_url": None, "held_s": None, "form_score": None,
                "reps": reps, "rep_form_scores": None}

    participants = [
        {"user_id": "u1", "name": "ana", "attempts": [att("a1", 3, 120)]},
        {"user_id": "u2", "name": "ben", "attempts": [att("b1", 4, 40)]},
        {"user_id": "u3", "name": "cy", "attempts": []},
    ]
    rows, block = rank_challenge(participants, metric="consistency", rules={},
                                 now=datetime(2026, 12, 28, 9, tzinfo=ny),
                                 lift_types=["Situp", "Pushup", "Squat", "Plank"])
    assert block["status"] == "ended"
    out = shape_champions([{
        "competition": _comp("c1", "The 100 Club", "2026-12-27"),
        "leaderboard": {"metric": "consistency", "rows": rows},
    }])
    c = out[0]
    assert c["metric"] == "consistency"
    assert c["name"] == "ana"
    assert c["score"] == 100 + 50 + 25
    assert c["field_size"] == 2
    assert c["margin"] == 135
    assert c["winner_attempts"] == 1
    assert c["won_on"] == "2026-11-03"
