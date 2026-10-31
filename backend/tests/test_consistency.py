"""The 100 Club consistency board — pure, DB-free.

    venv/bin/python -m pytest tests/test_consistency.py --noconftest
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from toms_gym.services.challenge_leaderboard import rank_challenge
from toms_gym.services.consistency import (
    DEFAULT_RULES,
    attempt_lifts,
    fill_rules,
    rank_consistency,
    week_of,
)

NY = ZoneInfo("America/New_York")
TYPES = ["Situp", "Pushup", "Squat", "Plank"]
RULES = fill_rules({})


def _at(local, hour=12, minute=0):
    """Aware datetime at local wall time in America/New_York."""
    y, m, d = (int(x) for x in local.split("-"))
    return datetime(y, m, d, hour, minute, tzinfo=NY)


def _att(aid, lift_type, local, *, reps=None, held_s=None, rep_form_scores=None,
         status="completed", created_at=None, video_url="v", annotated="ann"):
    return {
        "attempt_id": aid,
        "lift_type": lift_type,
        "weight_kg": 0.0,
        "status": status,
        "created_at": created_at if created_at is not None else _at(local),
        "video_url": video_url,
        "annotated_video_url": annotated,
        "held_s": held_s,
        "form_score": None,
        "steadiness": None,
        "reps": reps,
        "rep_form_scores": rep_form_scores,
    }


def _p(uid, name, attempts):
    return {"user_id": uid, "name": name, "weight_class": None, "gender": None,
            "attempts": attempts}


def _rank(participants, now, rules=None):
    return rank_consistency(participants, fill_rules(rules or {}), now, lift_types=TYPES)


def _row(rows, uid):
    return next(r for r in rows if r["user_id"] == uid)


# --------------------------------------------------------------------------- #
# rules / lifts / weeks
# --------------------------------------------------------------------------- #

def test_missing_rules_fall_back_to_defaults():
    r = fill_rules({"ramp": 10})
    assert r["ramp"] == 10
    assert r["base_quota"] == 100
    assert r["tz"] == "America/New_York"
    assert r["week_start"] == "2026-11-02"
    assert fill_rules(None) == DEFAULT_RULES


@pytest.mark.parametrize("key,bad", [
    ("tz", "Mars/X"),
    ("tz", 5),
    ("week_start", "Nov 2"),
    ("week_start", 20261102),
    ("base_quota", "lots"),
    ("base_quota", 0),
    ("base_quota", True),
    ("ramp", -5),
    ("weeks", "x"),
    ("weeks", 0),
    ("plank_seconds_per_lift", 0),
    ("type_bonus", 2.5),
    ("quota_bonus", [50]),
])
def test_bad_rule_values_fall_back_to_that_default(key, bad):
    r = fill_rules({key: bad, "ramp": 10} if key != "ramp" else {key: bad})
    assert r[key] == DEFAULT_RULES[key]
    if key != "ramp":
        assert r["ramp"] == 10
    rows, block = rank_consistency(
        [{"user_id": "u", "name": "U", "attempts": [_att("p", "Plank", "2026-11-03", held_s=30.0)]}],
        {key: bad}, NOW_WEEK3, lift_types=TYPES)
    assert block["status"] == "live" and rows[0]["this_week"]["index"] == 3


def test_numeric_rule_strings_are_coerced():
    r = fill_rules({"base_quota": "120", "ramp": "30", "weeks": 6.0, "week_start": "2026-11-09"})
    assert (r["base_quota"], r["ramp"], r["weeks"], r["week_start"]) == (120, 30, 6, "2026-11-09")


def test_bad_stored_rules_never_break_the_payload_builder():
    """The champions scan and achievements build every ended board; one bad row must not 500 them."""
    import json
    from consistency_scenario import AS_OF, COMPETITION_ID, fake_session
    from toms_gym.routes.competition_routes import _leaderboard_payload

    desc = "x - " + json.dumps({"lifttypes": TYPES, "mode": "consistency",
                                "rules": {"tz": "Mars/X", "week_start": "Nov 2",
                                          "base_quota": "100", "plank_seconds_per_lift": 0}})
    payload = _leaderboard_payload(fake_session(description=desc), COMPETITION_ID, now=AS_OF)
    assert payload["metric"] == "consistency"
    assert payload["consistency"]["rules"] == DEFAULT_RULES
    assert payload["rows"][0]["name"] == "Ana"


def test_plank_exchange_rate_is_ten_seconds_per_lift_floored():
    assert attempt_lifts(_att("p", "Plank", "2026-11-03", held_s=240.0), RULES) == 24
    assert attempt_lifts(_att("p", "Plank", "2026-11-03", held_s=59.9), RULES) == 5
    assert attempt_lifts(_att("p", "Plank", "2026-11-03", held_s=9.9), RULES) == 0


def test_situp_sloppy_reps_count_half():
    a = _att("s", "Situp", "2026-11-04", reps=50, rep_form_scores=[80.0] * 40 + [60.0] * 10)
    assert attempt_lifts(a, RULES) == 45


def test_pushup_and_squat_count_one_per_rep_and_other_types_zero():
    assert attempt_lifts(_att("p", "Pushup", "2026-11-04", reps=43), RULES) == 43
    assert attempt_lifts(_att("q", "Squat", "2026-11-04", reps=35), RULES) == 35
    assert attempt_lifts(_att("d", "Deadlift", "2026-11-04", reps=5), RULES) == 0


def test_unanalysed_attempt_has_no_lifts():
    assert attempt_lifts(_att("p", "Pushup", "2026-11-04", reps=None, status="pending"), RULES) is None
    assert attempt_lifts(_att("p", "Plank", "2026-11-04", held_s=None, status="pending"), RULES) is None


def test_week_boundary_sunday_night_local_belongs_to_the_old_week():
    # DST ended 2026-11-01, so Sunday 23:30 EST on 11-08 is Monday 04:30 UTC.
    sunday_late = datetime(2026, 11, 8, 23, 30, tzinfo=NY)
    assert sunday_late.astimezone(timezone.utc) == datetime(2026, 11, 9, 4, 30, tzinfo=timezone.utc)
    assert week_of(sunday_late, RULES) == 1
    assert week_of(datetime(2026, 11, 9, 4, 30, tzinfo=timezone.utc), RULES) == 1
    assert week_of(datetime(2026, 11, 9, 5, 0, tzinfo=timezone.utc), RULES) == 2
    assert week_of(datetime(2026, 11, 9, 0, 0, tzinfo=NY), RULES) == 2


def test_naive_created_at_is_treated_as_utc():
    # 04:30 UTC Monday is still Sunday in New York.
    assert week_of(datetime(2026, 11, 9, 4, 30), RULES) == 1
    assert week_of("2026-11-09T04:30:00", RULES) == 1
    assert week_of("2026-11-09T05:30:00Z", RULES) == 2
    assert week_of("2026-11-09T05:30:00+00:00", RULES) == 2


def test_week_of_before_start_is_warmup():
    assert week_of(_at("2026-11-01"), RULES) <= 0
    assert week_of(_at("2026-11-02", 0, 0), RULES) == 1


# --------------------------------------------------------------------------- #
# quota, points, bonuses
# --------------------------------------------------------------------------- #

NOW_WEEK3 = datetime(2026, 11, 19, 15, 0, tzinfo=NY)   # Thursday of week 3
NOW_AFTER = datetime(2026, 12, 30, 12, 0, tzinfo=NY)


def test_quota_ramps_after_a_met_week():
    p = _p("u", "ana", [
        _att("a", "Pushup", "2026-11-03", reps=100),
        _att("b", "Pushup", "2026-11-10", reps=125),
    ])
    rows, _ = _rank([p], NOW_WEEK3)
    r = rows[0]
    assert [w["quota"] for w in r["weeks"]] == [100, 125, 150]
    assert [w["met"] for w in r["weeks"]] == [True, True, False]
    assert r["this_week"]["quota"] == 150


def test_quota_resets_to_base_after_a_missed_week():
    p = _p("u", "ben", [
        _att("a", "Pushup", "2026-11-03", reps=100),
        _att("b", "Pushup", "2026-11-10", reps=124),
    ])
    rows, _ = _rank([p], NOW_WEEK3)
    r = rows[0]
    assert [w["quota"] for w in r["weeks"]] == [100, 125, 100]
    assert r["weeks"][1]["met"] is False
    assert r["streak"] == 0
    assert r["best_streak"] == 1


def test_lift_points_are_capped_at_the_quota_plus_quota_bonus():
    p = _p("u", "ana", [_att("a", "Pushup", "2026-11-03", reps=180)])
    rows, _ = _rank([p], NOW_WEEK3)
    w1 = rows[0]["weeks"][0]
    assert w1["lifts"] == 180
    # 100 capped + 50 quota bonus + 25 (sole pushup leader)
    assert w1["points"] == 175


def test_missed_week_gets_lift_points_without_quota_bonus():
    p = _p("u", "ana", [_att("a", "Squat", "2026-11-03", reps=99),
                        _att("b", "Pushup", "2026-11-03", reps=0)])
    other = _p("v", "zed", [_att("c", "Squat", "2026-11-03", reps=100)])
    rows, _ = _rank([p, other], NOW_WEEK3)
    w1 = _row(rows, "u")["weeks"][0]
    assert w1["met"] is False
    assert w1["points"] == 99
    assert w1["bonuses"] == []


def test_type_bonus_tie_rewards_everyone_at_the_top():
    a = _p("a", "ana", [_att("a1", "Squat", "2026-11-03", reps=40)])
    b = _p("b", "ben", [_att("b1", "Squat", "2026-11-04", reps=40)])
    c = _p("c", "cy", [_att("c1", "Squat", "2026-11-04", reps=39)])
    rows, _ = _rank([a, b, c], NOW_WEEK3)
    assert _row(rows, "a")["weeks"][0]["bonuses"] == ["Squat"]
    assert _row(rows, "b")["weeks"][0]["bonuses"] == ["Squat"]
    assert _row(rows, "c")["weeks"][0]["bonuses"] == []
    assert _row(rows, "a")["weeks"][0]["points"] == 40 + 25


def test_zero_never_wins_a_type_bonus():
    a = _p("a", "ana", [_att("a1", "Squat", "2026-11-03", reps=0)])
    b = _p("b", "ben", [_att("b1", "Plank", "2026-11-03", held_s=5.0)])
    rows, block = _rank([a, b], NOW_WEEK3)
    assert _row(rows, "a")["weeks"][0]["bonuses"] == []
    # 5 s is 0 lifts but plank is judged on seconds, so 5 s wins Plank.
    assert _row(rows, "b")["weeks"][0]["bonuses"] == ["Plank"]
    assert _row(rows, "b")["weeks"][0]["points"] == 25


def test_plank_bonus_judged_on_seconds_not_lifts():
    a = _p("a", "ana", [_att("a1", "Plank", "2026-11-03", held_s=49.0)])
    b = _p("b", "ben", [_att("b1", "Plank", "2026-11-03", held_s=41.0)])
    rows, _ = _rank([a, b], NOW_WEEK3)
    # both are 4 lifts; ana's 49 s beats ben's 41 s.
    assert _row(rows, "a")["weeks"][0]["by_type"]["Plank"] == 4
    assert _row(rows, "b")["weeks"][0]["by_type"]["Plank"] == 4
    assert _row(rows, "a")["weeks"][0]["bonuses"] == ["Plank"]
    assert _row(rows, "b")["weeks"][0]["bonuses"] == []
    assert _row(rows, "a")["weeks"][0]["plank_seconds"] == 49


def test_current_week_is_live_with_provisional_leaders_not_in_score():
    a = _p("a", "ana", [_att("a1", "Situp", "2026-11-17", reps=42)])
    rows, block = _rank([a], NOW_WEEK3)
    r = rows[0]
    assert r["this_week"]["leading"] == ["Situp"]
    assert r["weeks"][2]["bonuses"] == []
    assert r["weeks"][2]["points"] == 42
    assert r["score"] == 42
    assert block["type_leaders"] == {"Situp": [{"user_id": "a", "name": "ana", "amount": 42}]}


def test_current_week_quota_bonus_counts_live():
    a = _p("a", "ana", [_att("a1", "Pushup", "2026-11-17", reps=110)])
    rows, _ = _rank([a], NOW_WEEK3)
    r = rows[0]
    assert r["this_week"]["met"] is True
    assert r["score"] == 100 + 50
    assert r["streak"] == 1
    assert r["weeks_met"] == 1


def test_future_week_attempts_do_not_score():
    a = _p("a", "ana", [
        _att("a1", "Pushup", "2026-11-17", reps=10),
        _att("a2", "Pushup", "2026-11-24", reps=500),
    ])
    rows, _ = _rank([a], NOW_WEEK3)
    r = rows[0]
    assert r["score"] == 10
    assert len(r["weeks"]) == 3
    assert r["attempt_count"] == 1


def test_warmup_attempts_score_nothing_and_are_counted_apart():
    a = _p("a", "ana", [
        _att("w", "Pushup", "2026-10-31", reps=20),
        _att("a1", "Pushup", "2026-11-03", reps=10),
    ])
    rows, _ = _rank([a], NOW_WEEK3)
    r = rows[0]
    assert r["warmup_lifts"] == 20
    assert r["weeks"][0]["lifts"] == 10
    assert r["attempt_count"] == 1
    assert [h["date"] for h in r["history"]] == ["2026-11-03"]
    assert r["score"] == 10 + 25


def test_pending_attempt_counts_zero_and_is_flagged():
    a = _p("a", "ana", [
        _att("a1", "Pushup", "2026-11-17", reps=10),
        _att("a2", "Pushup", "2026-11-18", reps=None, status="pending", annotated=None),
    ])
    rows, _ = _rank([a], NOW_WEEK3)
    r = rows[0]
    assert r["this_week"]["pending"] == 1
    assert r["this_week"]["lifts"] == 10
    assert r["attempt_count"] == 1
    assert r["attempt_id"] == "a1"


def test_failed_attempts_are_ignored():
    a = _p("a", "ana", [_att("a1", "Pushup", "2026-11-17", reps=10, status="failed")])
    rows, _ = _rank([a], NOW_WEEK3)
    assert rows[0]["score"] == 0
    assert rows[0]["this_week"]["pending"] == 0


# --------------------------------------------------------------------------- #
# status
# --------------------------------------------------------------------------- #

def test_status_upcoming_before_week_start():
    a = _p("a", "ana", [_att("w", "Plank", "2026-10-31", held_s=100.0)])
    rows, block = _rank([a], datetime(2026, 10, 31, 15, 0, tzinfo=NY))
    assert block["status"] == "upcoming"
    assert block["week_index"] == 0
    assert block["week_start"] == "2026-11-02"
    assert block["week_end"] == "2026-11-08"
    assert block["days_left"] == 0
    assert block["type_leaders"] == {}
    r = rows[0]
    assert r["weeks"] == []
    assert r["this_week"]["quota"] == 100
    assert r["this_week"]["lifts"] == 0
    assert r["warmup_lifts"] == 10
    assert r["score"] == 0


def test_status_live_days_left_counts_sunday_as_one():
    _, block = _rank([], datetime(2026, 11, 22, 23, 59, tzinfo=NY))
    assert block["status"] == "live"
    assert block["week_index"] == 3
    assert block["days_left"] == 1
    _, block = _rank([], datetime(2026, 11, 2, 0, 0, tzinfo=NY))
    assert block["week_index"] == 1
    assert block["days_left"] == 7


def test_status_ended_after_the_last_week_and_all_bonuses_lock():
    a = _p("a", "ana", [_att("a1", "Pushup", "2026-12-27", reps=10),
                        _att("a2", "Pushup", "2026-12-28", reps=999)])
    rows, block = _rank([a], NOW_AFTER)
    assert block["status"] == "ended"
    assert block["week_index"] == 9
    assert block["weeks_total"] == 8
    assert block["week_start"] == "2026-12-21"
    assert block["week_end"] == "2026-12-27"
    assert block["days_left"] == 0
    assert block["type_leaders"] == {}
    r = rows[0]
    assert len(r["weeks"]) == 8
    assert r["weeks"][-1]["bonuses"] == ["Pushup"]
    assert r["score"] == 10 + 25
    assert r["this_week"]["lifts"] == 10
    assert r["this_week"]["leading"] == []


# --------------------------------------------------------------------------- #
# ranking
# --------------------------------------------------------------------------- #

def test_rank_by_total_points_with_zero_rows_last():
    a = _p("a", "ana", [_att("a1", "Pushup", "2026-11-17", reps=5)])
    b = _p("b", "aaron", [])
    c = _p("c", "cy", [_att("c1", "Pushup", "2026-11-17", reps=9)])
    rows, _ = _rank([a, b, c], NOW_WEEK3)
    assert [r["user_id"] for r in rows] == ["c", "a", "b"]
    assert [r["rank"] for r in rows] == [1, 2, 3]


def test_tiebreak_streak_beats_weeks_met():
    # Winner "zoe" loses on every lower key (this-week lifts, name, user_id).
    # zoe: w1 miss 50, w2 met 100 (150), w3 met 125 (175) -> 375, streak 2, met 2
    # amy: w1 met 100 (150), w2 miss 75 of 125, w3 met 200 (150) -> 375, streak 1, met 2
    z = _p("z", "zoe", [_att("z1", "Squat", "2026-11-03", reps=50),
                        _att("z2", "Squat", "2026-11-10", reps=100),
                        _att("z3", "Squat", "2026-11-17", reps=125)])
    a = _p("a", "amy", [_att("a1", "Squat", "2026-11-03", reps=100),
                        _att("a2", "Squat", "2026-11-10", reps=75),
                        _att("a3", "Squat", "2026-11-17", reps=200)])
    rows, _ = rank_consistency([a, z], fill_rules({"type_bonus": 0}), NOW_WEEK3,
                               lift_types=TYPES)
    rz, ra = _row(rows, "z"), _row(rows, "a")
    assert rz["score"] == ra["score"] == 375
    assert (rz["streak"], ra["streak"]) == (2, 1)
    assert rz["weeks_met"] == ra["weeks_met"] == 2
    assert rz["this_week"]["lifts"] < ra["this_week"]["lifts"]
    assert [r["user_id"] for r in rows] == ["z", "a"]


def test_tiebreak_streak_ranks_ahead_of_weeks_met():
    # Week 4 in progress, nobody has lifted yet. Winner "zoe" has the higher
    # streak but fewer weeks met, and loses on name and user_id.
    # zoe: w1 99, w2 99, w3 met 100 (150) -> 348, streak 1, met 1
    # amy: w1 met 100 (150), w2 met 125 (175), w3 miss 23 of 150 -> 348, streak 0, met 2
    z = _p("z", "zoe", [_att("z1", "Squat", "2026-11-03", reps=99),
                        _att("z2", "Squat", "2026-11-10", reps=99),
                        _att("z3", "Squat", "2026-11-17", reps=100)])
    a = _p("a", "amy", [_att("a1", "Squat", "2026-11-03", reps=100),
                        _att("a2", "Squat", "2026-11-10", reps=125),
                        _att("a3", "Squat", "2026-11-17", reps=23)])
    rows, _ = rank_consistency([a, z], fill_rules({"type_bonus": 0}),
                               datetime(2026, 11, 26, 15, 0, tzinfo=NY), lift_types=TYPES)
    rz, ra = _row(rows, "z"), _row(rows, "a")
    assert rz["score"] == ra["score"] == 348
    assert (rz["streak"], ra["streak"]) == (1, 0)
    assert (rz["weeks_met"], ra["weeks_met"]) == (1, 2)
    assert rz["this_week"]["lifts"] == ra["this_week"]["lifts"] == 0
    assert [r["user_id"] for r in rows] == ["z", "a"]


def test_tiebreak_weeks_met_decides_when_points_and_streak_tie():
    rules = fill_rules({"type_bonus": 0, "quota_bonus": 0, "ramp": 0})
    # zoe: w1 met 100, w2 0, w3 met 100 -> 200, streak 1, met 2, this week 100
    # amy: w1 50, w2 50, w3 met 150 (100) -> 200, streak 1, met 1, this week 150
    z = _p("z", "zoe", [_att("z1", "Squat", "2026-11-03", reps=100),
                        _att("z3", "Squat", "2026-11-17", reps=100)])
    a = _p("a", "amy", [_att("a1", "Squat", "2026-11-03", reps=50),
                        _att("a2", "Squat", "2026-11-10", reps=50),
                        _att("a3", "Squat", "2026-11-17", reps=150)])
    rows, _ = rank_consistency([a, z], rules, NOW_WEEK3, lift_types=TYPES)
    rz, ra = _row(rows, "z"), _row(rows, "a")
    assert rz["score"] == ra["score"] == 200
    assert rz["streak"] == ra["streak"] == 1
    assert (rz["weeks_met"], ra["weeks_met"]) == (2, 1)
    assert rz["this_week"]["lifts"] < ra["this_week"]["lifts"]
    assert [r["user_id"] for r in rows] == ["z", "a"]


def test_tiebreak_this_week_lifts_then_name():
    rules = fill_rules({"type_bonus": 0, "quota_bonus": 0})
    # Both 100 points, streak 0, weeks met 0; this week's lifts decide even
    # though the winner sorts last by name and user_id.
    z = _p("z", "zoe", [_att("z1", "Squat", "2026-11-03", reps=50),
                        _att("z2", "Squat", "2026-11-17", reps=50)])
    a = _p("a", "amy", [_att("a1", "Squat", "2026-11-10", reps=70),
                        _att("a2", "Squat", "2026-11-17", reps=30)])
    rows, _ = rank_consistency([a, z], rules, NOW_WEEK3, lift_types=TYPES)
    assert _row(rows, "z")["score"] == _row(rows, "a")["score"] == 100
    assert _row(rows, "z")["weeks_met"] == _row(rows, "a")["weeks_met"] == 0
    assert [r["user_id"] for r in rows] == ["z", "a"]   # this week 50 > 30
    c = _p("c", "Cy", [_att("c1", "Squat", "2026-11-17", reps=30)])
    d = _p("d", "bea", [_att("d1", "Squat", "2026-11-17", reps=30)])
    rows, _ = rank_consistency([c, d], rules, NOW_WEEK3, lift_types=TYPES)
    assert [r["user_id"] for r in rows] == ["d", "c"]   # name, case-insensitive


def test_rank_challenge_dispatches_consistency():
    a = _p("a", "ana", [_att("a1", "Squat", "2026-11-17", reps=30)])
    rows, block = rank_challenge([a], metric="consistency", rules={}, now=NOW_WEEK3,
                                 lift_types=TYPES)
    assert rows[0]["score"] == 30
    assert block["week_index"] == 3


def test_row_carries_the_board_contract_fields():
    a = _p("a", "ana", [_att("a1", "Squat", "2026-11-17", reps=30)])
    rows, block = _rank([a], NOW_WEEK3)
    r = rows[0]
    assert r["best_by_lift"] == {}
    assert r["form_score"] is None and r["steadiness"] is None and r["thumbnail_url"] is None
    assert r["clip_url"] == "ann"
    assert r["date"] == "2026-11-17"
    assert r["history"] == [{"score": 30, "date": "2026-11-17"}]
    assert set(r["this_week"]["by_type"]) == set(TYPES)
    assert block["rules"] == DEFAULT_RULES


# --------------------------------------------------------------------------- #
# shared scenario: the frontend fixture must equal the real payload
# --------------------------------------------------------------------------- #

def test_shared_scenario_fixture_matches_the_payload_builder():
    import json
    from consistency_scenario import FIXTURE, scenario_payload

    generated = json.loads(json.dumps(scenario_payload()))
    with open(FIXTURE) as fh:
        assert json.load(fh) == generated, \
            "fixture drifted: PYTHONPATH=. venv/bin/python tests/consistency_scenario.py"

    block = generated["consistency"]
    assert generated["metric"] == "consistency"
    assert (block["status"], block["week_index"], block["days_left"]) == ("live", 3, 4)
    assert (block["week_start"], block["week_end"]) == ("2026-11-16", "2026-11-22")
    assert block["type_leaders"] == {
        "Situp": [{"user_id": "a1", "name": "Ana", "amount": 42}],
        "Plank": [{"user_id": "b1", "name": "Ben", "amount": 100}],
    }
    ana, ben, cy = generated["rows"]
    assert [(r["name"], r["rank"], r["score"]) for r in (ana, ben, cy)] == [
        ("Ana", 1, 467), ("Ben", 2, 330), ("Cy", 3, 0)]
    assert (ana["streak"], ana["best_streak"], ana["weeks_met"]) == (2, 2, 2)
    assert (ana["warmup_lifts"], ana["attempt_count"]) == (20, 6)
    assert [h["score"] for h in ana["history"]] == [24, 45, 43, 70, 60, 42]
    assert [w["points"] for w in ana["weeks"]] == [200, 225, 42]
    assert [w["quota"] for w in ana["weeks"]] == [100, 125, 150]
    assert [w["bonuses"] for w in ana["weeks"]] == [["Situp", "Plank"], ["Situp", "Pushup"], []]
    assert ana["weeks"][0]["by_type"] == {"Situp": 45, "Pushup": 43, "Squat": 0, "Plank": 24}
    assert ana["this_week"]["leading"] == ["Situp"]
    assert ana["attempt_id"] == "a1-situp3"
    assert (ben["streak"], ben["weeks_met"], ben["attempt_count"]) == (1, 1, 4)
    assert [w["points"] for w in ben["weeks"]] == [145, 175, 10]
    assert [w["quota"] for w in ben["weeks"]] == [100, 100, 125]
    assert [w["bonuses"] for w in ben["weeks"]] == [["Pushup", "Squat"], ["Squat"], []]
    assert ben["this_week"]["pending"] == 1
    assert ben["this_week"]["plank_seconds"] == 100
    assert ben["this_week"]["leading"] == ["Plank"]
    assert ben["attempt_id"] == "b1-plank"
    assert [w["quota"] for w in cy["weeks"]] == [100, 100, 100]
    assert cy["attempt_id"] is None and cy["history"] == []


def test_shared_upcoming_and_ended_fixtures_match_the_payload_builder():
    import json
    from consistency_scenario import (ENDED_AS_OF, ENDED_FIXTURE, UPCOMING_AS_OF,
                                      UPCOMING_FIXTURE, scenario_payload)

    for path, as_of in ((UPCOMING_FIXTURE, UPCOMING_AS_OF), (ENDED_FIXTURE, ENDED_AS_OF)):
        generated = json.loads(json.dumps(scenario_payload(as_of)))
        with open(path) as fh:
            assert json.load(fh) == generated, \
                "fixture drifted: PYTHONPATH=. venv/bin/python tests/consistency_scenario.py"

    with open(UPCOMING_FIXTURE) as fh:
        upcoming = json.load(fh)
    assert (upcoming["consistency"]["status"], upcoming["consistency"]["week_index"]) == ("upcoming", 0)
    assert {r["this_week"]["index"] for r in upcoming["rows"]} == {0}
    assert [(r["name"], r["score"], r["warmup_lifts"], r["weeks"]) for r in upcoming["rows"]] == [
        ("Ana", 0, 20, []), ("Ben", 0, 0, []), ("Cy", 0, 0, [])]

    with open(ENDED_FIXTURE) as fh:
        ended = json.load(fh)
    assert (ended["consistency"]["status"], ended["consistency"]["week_index"]) == ("ended", 9)
    assert ended["consistency"]["type_leaders"] == {}
    ana, ben, cy = ended["rows"]
    assert [(r["name"], r["score"], r["streak"]) for r in (ana, ben, cy)] == [
        ("Ana", 492, 0), ("Ben", 355, 0), ("Cy", 0, 0)]
    assert {len(r["weeks"]) for r in ended["rows"]} == {8}
    assert {r["this_week"]["index"] for r in ended["rows"]} == {9}
    assert (ana["weeks"][2]["points"], ana["weeks"][2]["bonuses"]) == (67, ["Situp"])


# --------------------------------------------------------------------------- #
# upload: an air squat (weight 0) is accepted
# --------------------------------------------------------------------------- #

def test_upload_accepts_squat_with_weight_zero():
    from unittest.mock import MagicMock
    from toms_gym.routes.upload_routes import _create_attempt_record

    inserts = []
    session = MagicMock()

    def execute(statement, params=None):
        if 'INSERT INTO "Attempt"' in str(statement):
            inserts.append(params)
        result = MagicMock()
        result.fetchone.return_value = ["uc-1"]
        return result

    session.execute.side_effect = execute
    _create_attempt_record(session, "u1", "c1", "Squat", "0", "https://x/v.mp4")
    assert inserts and inserts[0]["lift_type"] == "Squat"
    assert inserts[0]["weight_kg"] == 0.0
