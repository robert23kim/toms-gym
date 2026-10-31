"""Shared 100 Club scenario: three athletes, as_of Thursday of week 3, plus
the same rows before week 1 and after the last week.

The fixtures tests/fixtures/consistency_leaderboard_{sample,upcoming,ended}.json
are generated from this through the real payload builder:

    cd backend && PYTHONPATH=. venv/bin/python tests/consistency_scenario.py
"""
import json
import os
from datetime import datetime
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
AS_OF = datetime(2026, 11, 19, 15, 0, tzinfo=NY)
UPCOMING_AS_OF = datetime(2026, 10, 31, 15, 0, tzinfo=NY)
ENDED_AS_OF = datetime(2026, 12, 28, 12, 0, tzinfo=NY)
COMPETITION_ID = "the-100-club-sample"
_FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
FIXTURE = os.path.join(_FIXTURES, "consistency_leaderboard_sample.json")
UPCOMING_FIXTURE = os.path.join(_FIXTURES, "consistency_leaderboard_upcoming.json")
ENDED_FIXTURE = os.path.join(_FIXTURES, "consistency_leaderboard_ended.json")
SCENARIOS = ((FIXTURE, AS_OF), (UPCOMING_FIXTURE, UPCOMING_AS_OF), (ENDED_FIXTURE, ENDED_AS_OF))

RULES = {"base_quota": 100, "ramp": 25, "weeks": 8, "quota_bonus": 50, "type_bonus": 25,
         "plank_seconds_per_lift": 10, "tz": "America/New_York", "week_start": "2026-11-02"}
DESCRIPTION = "100 lifts a week. Situps, pushups, squats or planks. Hit it and the bar rises. - " + \
    json.dumps({"lifttypes": ["Situp", "Pushup", "Squat", "Plank"], "weightclasses": [],
                "gender": "", "mode": "consistency", "rules": RULES})


def _noon(y, m, d):
    return datetime(y, m, d, 12, 0, tzinfo=NY)


def _row(uid, name, aid=None, lift=None, day=None, *, reps=None, held_s=None,
         scores=None, status="completed", weight_kg=0, analysed=True):
    return {
        "user_id": uid, "name": name, "weight_class": None, "gender": None,
        "attempt_id": aid, "lift_type": lift,
        "weight_kg": weight_kg if aid else None,
        "status": status if aid else None,
        "created_at": _noon(*day) if day else None,
        "video_url": f"https://storage.example/{aid}.mp4" if aid else None,
        "annotated_video_url": f"https://storage.example/{aid}-annotated.mp4"
        if aid and analysed else None,
        "held_s": None if held_s is None else str(held_s),
        "form_score": None, "steadiness": None,
        "reps": None if reps is None else str(reps),
        "rep_form_scores": scores,
    }


PARTICIPANT_ROWS = [
    _row("a1", "Ana", "a1-warmup", "Pushup", (2026, 10, 31), reps=20),
    _row("a1", "Ana", "a1-plank", "Plank", (2026, 11, 3), held_s=240.0),
    _row("a1", "Ana", "a1-situp1", "Situp", (2026, 11, 4), reps=50,
         scores=[80.0] * 40 + [60.0] * 10),
    _row("a1", "Ana", "a1-pushup1", "Pushup", (2026, 11, 5), reps=43),
    _row("a1", "Ana", "a1-pushup2", "Pushup", (2026, 11, 10), reps=70),
    _row("a1", "Ana", "a1-situp2", "Situp", (2026, 11, 12), reps=60, scores=[90.0] * 60),
    _row("a1", "Ana", "a1-situp3", "Situp", (2026, 11, 17), reps=42, scores=[85.0] * 42),
    _row("b1", "Ben", "b1-pushup1", "Pushup", (2026, 11, 3), reps=60),
    _row("b1", "Ben", "b1-squat1", "Squat", (2026, 11, 5), reps=35),
    _row("b1", "Ben", "b1-squat2", "Squat", (2026, 11, 11), reps=100),
    _row("b1", "Ben", "b1-plank", "Plank", (2026, 11, 18), held_s=100.0),
    _row("b1", "Ben", "b1-pending", "Pushup", (2026, 11, 19), status="pending",
         analysed=False),
    _row("c1", "Cy"),
]


def fake_session(description=DESCRIPTION, rows=PARTICIPANT_ROWS, uploaded_today=0):
    session = MagicMock()

    def execute(statement, params=None):
        sql = str(statement)
        result = MagicMock()
        if 'FROM "Competition"' in sql:
            comp = MagicMock()
            comp._mapping = {"description": description}
            result.fetchone.return_value = comp
        elif 'FROM "UserCompetition"' in sql and "COUNT(*)" not in sql:
            result.mappings.return_value.fetchall.return_value = rows
        elif "COUNT(*)" in sql:
            result.scalar.return_value = uploaded_today
        return result

    session.execute.side_effect = execute
    return session


def scenario_payload(as_of=AS_OF):
    from toms_gym.routes.competition_routes import _leaderboard_payload
    return _leaderboard_payload(fake_session(), COMPETITION_ID, now=as_of)


if __name__ == "__main__":
    for path, as_of in SCENARIOS:
        with open(path, "w") as fh:
            json.dump(scenario_payload(as_of), fh, indent=2)
            fh.write("\n")
        print(path)
