"""Unit tests for the pure `rank_challenge` helper.

DB-free — run with:
    venv/bin/python -m pytest tests/test_challenge_leaderboard.py --noconftest
"""
from toms_gym.services.challenge_leaderboard import rank_challenge


def _plank(attempt_id, held_s, created_at, *, status="completed",
           form_score=None, video_url=None, annotated_video_url=None):
    return {
        "attempt_id": attempt_id,
        "lift_type": "Plank",
        "weight_kg": 0.0,
        "status": status,
        "created_at": created_at,
        "video_url": video_url,
        "annotated_video_url": annotated_video_url,
        "held_s": held_s,
        "form_score": form_score,
    }


def _lift(attempt_id, lift_type, weight_kg, created_at, *, status="completed",
          video_url=None, annotated_video_url=None):
    return {
        "attempt_id": attempt_id,
        "lift_type": lift_type,
        "weight_kg": weight_kg,
        "status": status,
        "created_at": created_at,
        "video_url": video_url,
        "annotated_video_url": annotated_video_url,
        "held_s": None,
        "form_score": None,
    }


def _participant(user_id, name, attempts, **kw):
    return {
        "user_id": user_id,
        "name": name,
        "weight_class": kw.get("weight_class", "83kg"),
        "gender": kw.get("gender", "male"),
        "attempts": attempts,
    }


# --------------------------------------------------------------------------- #
# time metric
# --------------------------------------------------------------------------- #

def test_time_longest_hold_wins():
    participants = [
        _participant("u1", "alice", [_plank("a1", 40.0, "2026-07-01")]),
        _participant("u2", "bob", [_plank("b1", 65.8, "2026-07-01")]),
        _participant("u3", "carol", [_plank("c1", 52.0, "2026-07-01")]),
    ]
    rows = rank_challenge(participants, metric="time")
    assert [r["name"] for r in rows] == ["bob", "carol", "alice"]
    assert [r["rank"] for r in rows] == [1, 2, 3]
    assert rows[0]["score"] == 65.8
    assert rows[0]["best_by_lift"] == {"Plank": 65.8}


def test_time_null_held_excluded():
    """A completed plank with no hold time is not scored; if it's the athlete's
    only attempt they fall to score 0 and sort last."""
    participants = [
        _participant("u1", "alice", [_plank("a1", 30.0, "2026-07-01")]),
        _participant("u2", "bob", [_plank("b1", None, "2026-07-01")]),
    ]
    rows = rank_challenge(participants, metric="time")
    assert rows[0]["name"] == "alice"
    assert rows[1]["name"] == "bob"
    assert rows[1]["score"] == 0
    assert rows[1]["attempt_count"] == 0
    assert rows[1]["history"] == []
    assert rows[1]["clip_url"] is None
    assert rows[1]["date"] is None


def test_time_best_of_multiple_attempts():
    participants = [
        _participant("u1", "alice", [
            _plank("a1", 20.0, "2026-06-28"),
            _plank("a2", 45.0, "2026-06-30"),
            _plank("a3", 33.0, "2026-07-02"),
        ]),
    ]
    rows = rank_challenge(participants, metric="time")
    assert rows[0]["score"] == 45.0
    assert rows[0]["attempt_count"] == 3
    # history is chronological by created_at.
    assert rows[0]["history"] == [
        {"score": 20.0, "date": "2026-06-28"},
        {"score": 45.0, "date": "2026-06-30"},
        {"score": 33.0, "date": "2026-07-02"},
    ]


def test_time_tiebreak_form_then_created():
    """Equal hold: higher form score wins; equal form: earliest created_at."""
    # Equal held, different form -> higher form first.
    p_form = [
        _participant("u1", "low_form", [_plank("a1", 50.0, "2026-07-01", form_score=0.70)]),
        _participant("u2", "high_form", [_plank("b1", 50.0, "2026-07-01", form_score=0.95)]),
    ]
    rows = rank_challenge(p_form, metric="time")
    assert [r["name"] for r in rows] == ["high_form", "low_form"]

    # Equal held, equal form -> earliest created_at first.
    p_date = [
        _participant("u1", "later", [_plank("a1", 50.0, "2026-07-05", form_score=0.90)]),
        _participant("u2", "earlier", [_plank("b1", 50.0, "2026-07-01", form_score=0.90)]),
    ]
    rows = rank_challenge(p_date, metric="time")
    assert [r["name"] for r in rows] == ["earlier", "later"]


def test_time_zero_hold_athletes_last():
    participants = [
        _participant("u1", "no_score", [_plank("a1", None, "2026-07-01")]),
        _participant("u2", "joined_only", []),
        _participant("u3", "scored", [_plank("c1", 60.0, "2026-07-01")]),
    ]
    rows = rank_challenge(participants, metric="time")
    assert rows[0]["name"] == "scored"
    assert {r["name"] for r in rows[1:]} == {"no_score", "joined_only"}
    assert all(r["score"] == 0 for r in rows[1:])


def test_time_clip_and_date_from_best_attempt():
    """clip_url prefers the annotated video and comes from the score-setting
    attempt; date is that attempt's created_at."""
    participants = [
        _participant("u1", "alice", [
            _plank("a1", 20.0, "2026-06-28", video_url="v1", annotated_video_url="ann1"),
            _plank("a2", 66.0, "2026-07-01", video_url="v2", annotated_video_url="ann2"),
        ]),
    ]
    rows = rank_challenge(participants, metric="time")
    assert rows[0]["clip_url"] == "ann2"
    assert rows[0]["attempt_id"] == "a2"
    assert rows[0]["date"] == "2026-07-01"
    assert rows[0]["form_score"] is None


def test_time_clip_falls_back_to_raw_video():
    participants = [
        _participant("u1", "alice", [
            _plank("a1", 66.0, "2026-07-01", video_url="raw", annotated_video_url=None),
        ]),
    ]
    rows = rank_challenge(participants, metric="time")
    assert rows[0]["clip_url"] == "raw"


# --------------------------------------------------------------------------- #
# weight metric
# --------------------------------------------------------------------------- #

def test_weight_per_lift_rollup():
    """Score = sum of the max weight per lift type across completed attempts."""
    participants = [
        _participant("u1", "alice", [
            _lift("a1", "Squat", 100.0, "2026-07-01"),
            _lift("a2", "Squat", 120.0, "2026-07-02"),   # best squat
            _lift("a3", "Bench Press", 80.0, "2026-07-01"),
            _lift("a4", "Deadlift", 140.0, "2026-07-01"),
        ]),
    ]
    rows = rank_challenge(participants, metric="weight")
    assert rows[0]["best_by_lift"] == {
        "Squat": 120.0, "Bench Press": 80.0, "Deadlift": 140.0,
    }
    assert rows[0]["score"] == 340.0
    assert rows[0]["attempt_count"] == 4


def test_weight_single_lift_reduces_to_best_single():
    participants = [
        _participant("u1", "alice", [
            _lift("a1", "Deadlift", 150.0, "2026-07-01"),
            _lift("a2", "Deadlift", 170.0, "2026-07-02"),
        ]),
        _participant("u2", "bob", [
            _lift("b1", "Deadlift", 160.0, "2026-07-01"),
        ]),
    ]
    rows = rank_challenge(participants, metric="weight")
    assert [r["name"] for r in rows] == ["alice", "bob"]
    assert rows[0]["score"] == 170.0
    assert rows[1]["score"] == 160.0


def test_weight_pending_and_failed_excluded():
    participants = [
        _participant("u1", "alice", [
            _lift("a1", "Squat", 200.0, "2026-07-01", status="pending"),
            _lift("a2", "Squat", 90.0, "2026-07-02", status="completed"),
            _lift("a3", "Squat", 300.0, "2026-07-03", status="failed"),
        ]),
    ]
    rows = rank_challenge(participants, metric="weight")
    assert rows[0]["score"] == 90.0
    assert rows[0]["attempt_count"] == 1


def test_weight_tiebreak_by_created_at():
    participants = [
        _participant("u1", "later", [_lift("a1", "Squat", 100.0, "2026-07-05")]),
        _participant("u2", "earlier", [_lift("b1", "Squat", 100.0, "2026-07-01")]),
    ]
    rows = rank_challenge(participants, metric="weight")
    assert [r["name"] for r in rows] == ["earlier", "later"]


def test_weight_planks_excluded_from_weight_board():
    """A mixed board ranks by weight and never scores planks."""
    participants = [
        _participant("u1", "alice", [
            _lift("a1", "Squat", 100.0, "2026-07-01"),
            _plank("a2", 90.0, "2026-07-02"),   # ignored on a weight board
        ]),
    ]
    rows = rank_challenge(participants, metric="weight")
    assert rows[0]["best_by_lift"] == {"Squat": 100.0}
    assert rows[0]["score"] == 100.0
    assert rows[0]["attempt_count"] == 1


def test_weight_zero_score_and_clip_from_heaviest():
    participants = [
        _participant("u1", "joined", []),
        _participant("u2", "alice", [
            _lift("a1", "Squat", 100.0, "2026-07-01", annotated_video_url="ann_sq"),
            _lift("a2", "Deadlift", 150.0, "2026-07-02", annotated_video_url="ann_dl"),
        ]),
    ]
    rows = rank_challenge(participants, metric="weight")
    assert rows[0]["name"] == "alice"
    assert rows[0]["clip_url"] == "ann_dl"   # heaviest single attempt
    assert rows[0]["attempt_id"] == "a2"
    assert rows[0]["date"] == "2026-07-02"
    assert rows[0]["form_score"] is None
    assert rows[1]["name"] == "joined"
    assert rows[1]["score"] == 0
    assert rows[1]["clip_url"] is None
    assert rows[1]["attempt_id"] is None


def test_unknown_metric_raises():
    import pytest
    with pytest.raises(ValueError):
        rank_challenge([], metric="bogus")
