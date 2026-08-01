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
