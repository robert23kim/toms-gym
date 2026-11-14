import json
import pytest
from flask import Flask
from unittest.mock import MagicMock, patch
from toms_gym.app import app
from toms_gym.routes.competition_routes import competition_bp
import uuid

@pytest.fixture
def test_client():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(competition_bp)
    return app.test_client()

def test_get_competitions(test_client):
    """Test getting all competitions"""
    response = test_client.get('/competitions')
    assert response.status_code == 200
    data = response.get_json()
    assert "competitions" in data
    assert isinstance(data["competitions"], list)

def test_create_competition(test_client, test_competition_data):
    """Test creating a new competition"""
    response = test_client.post('/create_competition', json=test_competition_data)
    assert response.status_code == 201
    data = response.get_json()
    assert "competition_id" in data
    assert data["message"] == "Competition created successfully!"

def test_get_competition_by_id(test_client, test_competition_data):
    """Test getting a specific competition"""
    # First create a competition
    create_response = test_client.post('/create_competition', json=test_competition_data)
    assert create_response.status_code == 201
    data = create_response.get_json()
    competition_id = data["competition_id"]

    # Then get it by ID
    response = test_client.get(f'/competitions/{competition_id}')
    assert response.status_code == 200
    data = response.get_json()
    assert "competition" in data
    competition = data["competition"]
    assert competition["name"] == test_competition_data["name"]

def test_get_nonexistent_competition(test_client):
    """Test getting a non-existent competition"""
    # Use a valid UUID format that doesn't exist
    non_existent_id = str(uuid.uuid4())
    response = test_client.get(f'/competitions/{non_existent_id}')
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data
    assert data["error"] == "Competition not found"


# --------------------------------------------------------------------------- #
# GET /competitions/<id>/leaderboard
#
# These tests mock get_db_connection so they run without a database. Each query
# the route issues is matched on a substring of its SQL text.
#   1. SELECT ... FROM "Competition" WHERE id      -> .fetchone()
#   2. SELECT ... FROM "UserCompetition" uc ...     -> .mappings().fetchall()
#   3. SELECT COUNT(*) ... a.created_at::date       -> .scalar()
# --------------------------------------------------------------------------- #

def _comp_row(description):
    """Fake Competition row exposing ._mapping.get('description')."""
    row = MagicMock()
    row._mapping = {"description": description}
    return row


def _make_session(description, participant_rows, uploaded_today=0, missing=False):
    """Build a fake DB session dispatching on the query text."""
    session = MagicMock()

    def execute(statement, params=None):
        sql = str(statement)
        result = MagicMock()
        if 'FROM "Competition"' in sql:
            result.fetchone.return_value = None if missing else _comp_row(description)
        elif 'FROM "UserCompetition"' in sql and 'COUNT(*)' not in sql:
            result.mappings.return_value.fetchall.return_value = participant_rows
        elif 'COUNT(*)' in sql:
            result.scalar.return_value = uploaded_today
        return result

    session.execute.side_effect = execute
    return session


def _prow(**kw):
    """A single participant/attempt join row (dict-like mapping)."""
    base = {
        "user_id": kw.get("user_id"),
        "name": kw.get("name"),
        "weight_class": kw.get("weight_class", "83kg"),
        "gender": kw.get("gender", "male"),
        "attempt_id": kw.get("attempt_id"),
        "lift_type": kw.get("lift_type"),
        "weight_kg": kw.get("weight_kg"),
        "status": kw.get("status"),
        "created_at": kw.get("created_at"),
        "video_url": kw.get("video_url"),
        "annotated_video_url": kw.get("annotated_video_url"),
        "held_s": kw.get("held_s"),
        "form_score": kw.get("form_score"),
        "steadiness": kw.get("steadiness"),
        "reps": kw.get("reps"),
        "rep_form_scores": kw.get("rep_form_scores"),
    }
    return base


def test_leaderboard_plank_challenge_metric_time(test_client):
    """Plank-only declared challenge -> metric 'time', rows ranked by hold with
    clip fields carried through."""
    description = 'Gym - {"lifttypes": ["Plank"], "weightclasses": [], "gender": "M"}'
    rows = [
        _prow(user_id="u1", name="alice", attempt_id="a1", lift_type="Plank",
              weight_kg=0, status="completed", created_at="2026-07-01",
              video_url="v1", annotated_video_url="ann1",
              held_s="40.0", form_score="0.80"),
        _prow(user_id="u2", name="bob", attempt_id="b1", lift_type="Plank",
              weight_kg=0, status="completed", created_at="2026-07-01",
              video_url="v2", annotated_video_url="ann2",
              held_s="65.8", form_score="0.91", steadiness="1.5"),
    ]
    session = _make_session(description, rows, uploaded_today=2)
    with patch("toms_gym.routes.competition_routes.get_db_connection", return_value=session):
        resp = test_client.get("/competitions/comp1/leaderboard")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["metric"] == "time"
    assert data["lift_types"] == ["Plank"]
    assert data["momentum"] == {"joined": 2, "uploaded_today": 2}
    assert [r["name"] for r in data["rows"]] == ["bob", "alice"]
    top = data["rows"][0]
    assert top["rank"] == 1
    assert top["score"] == 65.8
    assert top["clip_url"] == "ann2"
    assert top["date"] == "2026-07-01"
    assert top["best_by_lift"] == {"Plank": 65.8}
    assert top["steadiness"] == 1.5  # best attempt's body_line_stdev_deg surfaces


def test_leaderboard_lifting_challenge_metric_weight(test_client):
    """Declared multi-lift challenge -> metric 'weight', best-lift total."""
    description = 'Gym - {"lifttypes": ["Squat", "Deadlift"], "weightclasses": [], "gender": "M"}'
    rows = [
        _prow(user_id="u1", name="alice", attempt_id="a1", lift_type="Squat",
              weight_kg=120.0, status="completed", created_at="2026-07-01"),
        _prow(user_id="u1", name="alice", attempt_id="a2", lift_type="Deadlift",
              weight_kg=150.0, status="completed", created_at="2026-07-02"),
        _prow(user_id="u2", name="bob", attempt_id="b1", lift_type="Squat",
              weight_kg=200.0, status="completed", created_at="2026-07-01"),
    ]
    session = _make_session(description, rows, uploaded_today=0)
    with patch("toms_gym.routes.competition_routes.get_db_connection", return_value=session):
        resp = test_client.get("/competitions/comp1/leaderboard")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["metric"] == "weight"
    assert data["lift_types"] == ["Squat", "Deadlift"]
    # alice total 270 > bob 200
    assert [r["name"] for r in data["rows"]] == ["alice", "bob"]
    assert data["rows"][0]["score"] == 270.0
    assert data["rows"][0]["form_score"] is None


def test_leaderboard_weight_pending_uploads_form_podium(test_client):
    """Regression (T2): entrants who uploaded but whose analysis hasn't run yet
    (status='pending', no LiftingResult) must still surface as scored rows so
    the podium renders instead of "No entries yet". The score is the declared
    weight, which is independent of analysis."""
    description = 'Gym - {"lifttypes": ["Deadlift"], "weightclasses": [], "gender": "M"}'
    rows = [
        _prow(user_id="u1", name="alice", attempt_id="a1", lift_type="Deadlift",
              weight_kg=140.0, status="pending", created_at="2026-07-01",
              video_url="v1", annotated_video_url=None),
        _prow(user_id="u2", name="bob", attempt_id="b1", lift_type="Deadlift",
              weight_kg=160.0, status="pending", created_at="2026-07-01",
              video_url="v2", annotated_video_url=None),
    ]
    session = _make_session(description, rows, uploaded_today=2)
    with patch("toms_gym.routes.competition_routes.get_db_connection", return_value=session):
        resp = test_client.get("/competitions/comp1/leaderboard")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["metric"] == "weight"
    # Both pending uploads produce positive scores (the frontend podium keeps
    # rows with score > 0).
    scored = [r for r in data["rows"] if r["score"] > 0]
    assert [r["name"] for r in scored] == ["bob", "alice"]
    assert scored[0]["score"] == 160.0
    # Clip falls back to the raw upload when there's no annotated video yet.
    assert scored[0]["clip_url"] == "v2"


def test_leaderboard_404_unknown_competition(test_client):
    session = _make_session(None, [], missing=True)
    with patch("toms_gym.routes.competition_routes.get_db_connection", return_value=session):
        resp = test_client.get(f"/competitions/{uuid.uuid4()}/leaderboard")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "Competition not found"


def test_leaderboard_empty_challenge(test_client):
    """No participants -> 200 with rows [] and a valid metric."""
    description = 'Gym - {"lifttypes": ["Plank"], "weightclasses": [], "gender": "M"}'
    session = _make_session(description, [], uploaded_today=0)
    with patch("toms_gym.routes.competition_routes.get_db_connection", return_value=session):
        resp = test_client.get("/competitions/comp1/leaderboard")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["rows"] == []
    assert data["metric"] == "time"
    assert data["momentum"] == {"joined": 0, "uploaded_today": 0}


def test_leaderboard_metric_inferred_plank_only(test_client):
    """No metadata but every completed attempt is a plank -> metric 'time'."""
    description = "Just a plain location, no metadata"
    rows = [
        _prow(user_id="u1", name="alice", attempt_id="a1", lift_type="Plank",
              weight_kg=0, status="completed", created_at="2026-07-01",
              held_s="30.0", form_score="0.80"),
    ]
    session = _make_session(description, rows, uploaded_today=1)
    with patch("toms_gym.routes.competition_routes.get_db_connection", return_value=session):
        resp = test_client.get("/competitions/comp1/leaderboard")
    data = resp.get_json()
    assert data["metric"] == "time"
    assert data["lift_types"] == ["Plank"]


def test_leaderboard_metric_mixed_excludes_planks(test_client):
    """Declared board mixing Plank with a weighted lift ranks by weight and
    never scores the plank."""
    description = 'Gym - {"lifttypes": ["Plank", "Squat"], "weightclasses": [], "gender": "M"}'
    rows = [
        _prow(user_id="u1", name="alice", attempt_id="a1", lift_type="Squat",
              weight_kg=100.0, status="completed", created_at="2026-07-01"),
        _prow(user_id="u1", name="alice", attempt_id="a2", lift_type="Plank",
              weight_kg=0, status="completed", created_at="2026-07-02",
              held_s="90.0", form_score="0.95"),
    ]
    session = _make_session(description, rows, uploaded_today=0)
    with patch("toms_gym.routes.competition_routes.get_db_connection", return_value=session):
        resp = test_client.get("/competitions/comp1/leaderboard")
    data = resp.get_json()
    assert data["metric"] == "weight"
    assert data["rows"][0]["best_by_lift"] == {"Squat": 100.0}
    assert data["rows"][0]["score"] == 100.0
    assert data["rows"][0]["attempt_count"] == 1


# --------------------------------------------------------------------------- #
# T1: bot/e2e users (User.is_test = true) must be excluded from every public
# lifting surface — Top Lifts, /leaderboard, and challenge leaderboards — while
# their own profile stays visible. These surfaces are all fed by three
# competition_routes queries, so we assert the exclusion clause is present in
# each executed SQL statement (DB-free; the mock captures the SQL text).
# --------------------------------------------------------------------------- #

_IS_TEST_EXCLUSION = "COALESCE(u.is_test, false) = false"


def _capturing_session(participant_rows=None):
    """Fake session that records every SQL string it executes."""
    session = MagicMock()
    session.executed_sql = []

    def execute(statement, params=None):
        sql = str(statement)
        session.executed_sql.append(sql)
        result = MagicMock()
        result.__iter__ = lambda self: iter([])
        result.mappings.return_value.fetchall.return_value = participant_rows or []
        return result

    session.execute.side_effect = execute
    return session


def test_participants_query_excludes_test_users(test_client):
    """GET /competitions/<id>/participants feeds Top Lifts + /leaderboard."""
    session = _capturing_session()
    with patch("toms_gym.routes.competition_routes.get_db_connection", return_value=session):
        resp = test_client.get("/competitions/comp1/participants")
    assert resp.status_code == 200
    joined = " ".join(session.executed_sql)
    assert _IS_TEST_EXCLUSION in joined
    assert '"UserCompetition"' in joined


def test_lifts_query_excludes_test_users(test_client):
    """GET /competitions/<id>/lifts feeds Top Lifts This Month."""
    session = _capturing_session()
    with patch("toms_gym.routes.competition_routes.get_db_connection", return_value=session):
        resp = test_client.get("/competitions/comp1/lifts")
    assert resp.status_code == 200
    joined = " ".join(session.executed_sql)
    assert _IS_TEST_EXCLUSION in joined
    # The lifts query must join User to filter it.
    assert 'JOIN "User" u' in joined


def test_leaderboard_query_excludes_test_users(test_client):
    """GET /competitions/<id>/leaderboard is the per-challenge leaderboard."""
    description = 'Gym - {"lifttypes": ["Squat"], "weightclasses": [], "gender": "M"}'
    session = _make_session(description, [], uploaded_today=0)
    session.executed_sql = []
    original = session.execute.side_effect

    def spy(statement, params=None):
        session.executed_sql.append(str(statement))
        return original(statement, params)

    session.execute.side_effect = spy
    with patch("toms_gym.routes.competition_routes.get_db_connection", return_value=session):
        resp = test_client.get("/competitions/comp1/leaderboard")
    assert resp.status_code == 200
    participant_sql = [s for s in session.executed_sql
                       if 'FROM "UserCompetition" uc' in s and 'COUNT(*)' not in s]
    assert participant_sql, "leaderboard did not run the participant/attempt query"
    assert _IS_TEST_EXCLUSION in participant_sql[0]


def test_test_user_still_visible_on_own_profile():
    """A designated test account (is_test=true) must still see its own uploads
    via its direct profile URL — the profile query must NOT filter on is_test."""
    from toms_gym.routes.user_routes import user_bp
    from flask import Flask

    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(user_bp)
    client = app.test_client()

    user_id = str(uuid.uuid4())
    executed = []

    def execute(statement, params=None):
        executed.append(str(statement))
        result = MagicMock()
        result.fetchone.return_value = None  # user not found -> early 404, but SQL captured
        result.mappings.return_value.fetchall.return_value = []
        result.__iter__ = lambda self: iter([])
        return result

    session = MagicMock()
    session.execute.side_effect = execute
    with patch("toms_gym.routes.user_routes.get_db_connection", return_value=session):
        client.get(f"/users/{user_id}/profile")

    user_lookup = [s for s in executed if 'FROM "User"' in s]
    assert user_lookup, "profile route did not query the User table"
    assert all("is_test" not in s for s in user_lookup), \
        "profile route must not filter test users out of their own profile"


def test_leaderboard_pushup_challenge_metric_reps(test_client):
    """Pushup-only declared challenge -> metric 'reps', ranked by best rep count."""
    description = 'Gym - {"lifttypes": ["Pushup"], "weightclasses": [], "gender": "M"}'
    rows = [
        _prow(user_id="u1", name="alice", attempt_id="a1", lift_type="Pushup",
              status="completed", created_at="2026-08-01",
              video_url="v1", annotated_video_url="ann1",
              reps="18", form_score="0.80"),
        _prow(user_id="u2", name="bob", attempt_id="b1", lift_type="Pushup",
              status="completed", created_at="2026-08-01",
              video_url="v2", annotated_video_url="ann2",
              reps="31", form_score="0.91"),
    ]
    session = _make_session(description, rows, uploaded_today=2)
    with patch("toms_gym.routes.competition_routes.get_db_connection", return_value=session):
        resp = test_client.get("/competitions/comp1/leaderboard")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["metric"] == "reps"
    assert data["lift_types"] == ["Pushup"]
    assert [r["name"] for r in data["rows"]] == ["bob", "alice"]
    top = data["rows"][0]
    assert top["rank"] == 1
    assert top["score"] == 31
    assert top["best_by_lift"] == {"Pushup": 31}
    assert top["clip_url"] == "ann2"


def test_leaderboard_situp_challenge_metric_reps(test_client):
    """Situp-only declared challenge -> metric 'reps', ranked by best rep count."""
    description = 'Gym - {"lifttypes": ["Situp"], "weightclasses": [], "gender": "M"}'
    rows = [
        _prow(user_id="u1", name="alice", attempt_id="a1", lift_type="Situp",
              status="completed", created_at="2026-09-12",
              video_url="v1", annotated_video_url="ann1",
              reps="22", form_score="0.80"),
        _prow(user_id="u2", name="bob", attempt_id="b1", lift_type="Situp",
              status="completed", created_at="2026-09-12",
              video_url="v2", annotated_video_url="ann2",
              reps="40", form_score="0.91"),
    ]
    session = _make_session(description, rows, uploaded_today=2)
    with patch("toms_gym.routes.competition_routes.get_db_connection", return_value=session):
        resp = test_client.get("/competitions/comp1/leaderboard")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["metric"] == "reps"
    assert data["lift_types"] == ["Situp"]
    assert [r["name"] for r in data["rows"]] == ["bob", "alice"]
    assert data["rows"][0]["score"] == 40
    assert data["rows"][0]["best_by_lift"] == {"Situp": 40}


def test_leaderboard_situp_sloppy_reps_count_half(test_client):
    """Situp boards score clean reps in full and the rest at half credit."""
    description = 'Gym - {"lifttypes": ["Situp"], "weightclasses": [], "gender": "M"}'
    rows = [
        _prow(user_id="u1", name="alice", attempt_id="a1", lift_type="Situp",
              status="completed", created_at="2026-09-12",
              video_url="v1", annotated_video_url="ann1",
              reps="4", form_score="0.70",
              rep_form_scores=[90.0, 71.2, 40.0, 69.9]),
        _prow(user_id="u2", name="bob", attempt_id="b1", lift_type="Situp",
              status="completed", created_at="2026-09-12",
              video_url="v2", annotated_video_url="ann2",
              reps="3", form_score="0.95",
              rep_form_scores=[95.0, 92.0, 88.0]),
    ]
    session = _make_session(description, rows, uploaded_today=2)
    with patch("toms_gym.routes.competition_routes.get_db_connection", return_value=session):
        resp = test_client.get("/competitions/comp1/leaderboard")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["metric"] == "reps"
    # alice: 2 clean + 2 sloppy * 0.5 = 3.0; bob: 3 clean = 3 -> bob wins on form.
    assert [r["name"] for r in data["rows"]] == ["bob", "alice"]
    assert data["rows"][0]["score"] == 3
    assert data["rows"][1]["score"] == 3.0
    assert data["rows"][1]["reps_total"] == 4
    assert data["rows"][1]["clean_reps"] == 2


def test_leaderboard_mixed_rep_lifts_declared_metric_reps(test_client):
    """A challenge declaring both rep lifts is still a reps board."""
    description = 'Gym - {"lifttypes": ["Pushup", "Situp"], "weightclasses": [], "gender": "M"}'
    rows = [
        _prow(user_id="u1", name="alice", attempt_id="a1", lift_type="Situp",
              status="completed", created_at="2026-09-12",
              video_url="v1", annotated_video_url="ann1",
              reps="22", form_score="0.80"),
    ]
    session = _make_session(description, rows, uploaded_today=1)
    with patch("toms_gym.routes.competition_routes.get_db_connection", return_value=session):
        resp = test_client.get("/competitions/comp1/leaderboard")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["metric"] == "reps"
    assert data["rows"][0]["score"] == 22


def test_leaderboard_metric_inferred_pushup_only(test_client):
    """No declared lifttypes but every attempt is a Pushup -> metric 'reps'."""
    description = 'Gym'
    rows = [
        _prow(user_id="u1", name="alice", attempt_id="a1", lift_type="Pushup",
              status="completed", created_at="2026-08-01", video_url="v1",
              reps="22"),
    ]
    session = _make_session(description, rows, uploaded_today=1)
    with patch("toms_gym.routes.competition_routes.get_db_connection", return_value=session):
        resp = test_client.get("/competitions/comp1/leaderboard")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["metric"] == "reps"
    assert data["rows"][0]["score"] == 22


def test_leaderboard_pushup_pending_analysis_scores_zero(test_client):
    """A pushup upload with no analysis yet still joins the board at score 0."""
    description = 'Gym - {"lifttypes": ["Pushup"], "weightclasses": [], "gender": "M"}'
    rows = [
        _prow(user_id="u1", name="alice", attempt_id="a1", lift_type="Pushup",
              status="pending", created_at="2026-08-01", video_url="v1",
              reps=None),
    ]
    session = _make_session(description, rows, uploaded_today=1)
    with patch("toms_gym.routes.competition_routes.get_db_connection", return_value=session):
        resp = test_client.get("/competitions/comp1/leaderboard")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["metric"] == "reps"
    assert data["rows"][0]["score"] == 0
    assert data["rows"][0]["attempt_count"] == 0


# --------------------------------------------------------------------------- #
# The 100 Club: mode "consistency", admin as_of preview, mode/rules round-trip
# --------------------------------------------------------------------------- #

_CONSISTENCY_DESC = ('Gym - {"lifttypes": ["Situp", "Pushup", "Squat", "Plank"], '
                     '"weightclasses": [], "gender": "", "mode": "consistency", '
                     '"rules": {"week_start": "2026-11-02"}}')


def _squat_row(created_at, reps="30"):
    return _prow(user_id="u1", name="alice", attempt_id="a1", lift_type="Squat",
                 weight_kg=0, status="completed", created_at=created_at,
                 video_url="v1", annotated_video_url="ann1", reps=reps)


def test_leaderboard_consistency_mode_beats_lift_type_inference(test_client):
    """A mixed Situp/Pushup/Squat/Plank set would fall through to 'weight';
    mode 'consistency' must win first."""
    session = _make_session(_CONSISTENCY_DESC, [_squat_row("2026-11-03T17:00:00+00:00")])
    with patch("toms_gym.routes.competition_routes.get_db_connection", return_value=session):
        resp = test_client.get("/competitions/comp1/leaderboard")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["metric"] == "consistency"
    assert data["lift_types"] == ["Situp", "Pushup", "Squat", "Plank"]
    assert data["consistency"]["rules"]["base_quota"] == 100
    assert data["consistency"]["weeks_total"] == 8
    assert data["rows"][0]["name"] == "alice"


def test_leaderboard_same_lifts_without_mode_stay_legacy(test_client):
    description = ('Gym - {"lifttypes": ["Situp", "Pushup", "Squat", "Plank"], '
                   '"weightclasses": [], "gender": ""}')
    session = _make_session(description, [_squat_row("2026-11-03T17:00:00+00:00")])
    with patch("toms_gym.routes.competition_routes.get_db_connection", return_value=session):
        data = test_client.get("/competitions/comp1/leaderboard").get_json()
    assert data["metric"] == "weight"
    assert "consistency" not in data


def test_auto_attempt_on_the_club_board_scores_nothing_and_is_pending(test_client, monkeypatch):
    """An attempt still waiting for its lift type never counts as a default lift."""
    monkeypatch.setenv("ADMIN_TOKEN", "s3cret")
    auto = _prow(user_id="u1", name="alice", attempt_id="a2", lift_type="Auto",
                 weight_kg=0, status="completed", created_at="2026-11-03T18:00:00+00:00",
                 video_url="v2", reps="40")
    resp = _as_of_get(test_client, "2026-11-04T12:00:00-05:00", token="s3cret",
                      rows=[_squat_row("2026-11-03T17:00:00+00:00"), auto])
    assert resp.status_code == 200
    data = resp.get_json()
    row = data["rows"][0]
    assert row["score"] == 30
    assert row["this_week"]["lifts"] == 30
    assert row["this_week"]["pending"] == 1
    assert row["this_week"]["by_type"] == {"Situp": 0, "Pushup": 0, "Squat": 30, "Plank": 0}
    assert data["lift_types"] == ["Situp", "Pushup", "Squat", "Plank"]


def test_auto_attempt_never_drives_metric_inference(test_client):
    rows = [
        _prow(user_id="u1", name="alice", attempt_id="a1", lift_type="Pushup",
              weight_kg=0, status="completed", created_at="2026-07-01T10:00:00",
              video_url="v1", reps="12"),
        _prow(user_id="u1", name="alice", attempt_id="a2", lift_type="Auto",
              weight_kg=0, status="pending", created_at="2026-07-02T10:00:00", video_url="v2"),
    ]
    session = _make_session("Gym", rows)
    with patch("toms_gym.routes.competition_routes.get_db_connection", return_value=session):
        data = test_client.get("/competitions/comp1/leaderboard").get_json()
    assert data["metric"] == "reps"
    assert data["lift_types"] == ["Pushup"]
    assert data["rows"][0]["score"] == 12


def _as_of_get(test_client, as_of, token=None, rows=None):
    session = _make_session(_CONSISTENCY_DESC, rows if rows is not None else [
        _squat_row("2026-11-03T17:00:00+00:00")])
    headers = {"X-Admin-Token": token} if token is not None else {}
    with patch("toms_gym.routes.competition_routes.get_db_connection", return_value=session):
        return test_client.get("/competitions/comp1/leaderboard",
                               query_string={"as_of": as_of}, headers=headers)


def test_as_of_is_503_when_admin_token_unset(test_client, monkeypatch):
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    resp = _as_of_get(test_client, "2026-11-04T12:00:00-05:00", token="anything")
    assert resp.status_code == 503
    session = _make_session(_CONSISTENCY_DESC, [])
    with patch("toms_gym.routes.competition_routes.get_db_connection", return_value=session):
        assert test_client.get("/competitions/comp1/leaderboard").status_code == 200


def test_as_of_is_401_on_missing_or_wrong_token(test_client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "s3cret")
    assert _as_of_get(test_client, "2026-11-04T12:00:00-05:00").status_code == 401
    assert _as_of_get(test_client, "2026-11-04T12:00:00-05:00", token="nope").status_code == 401


def test_as_of_with_admin_token_computes_the_board_at_that_instant(test_client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "s3cret")
    resp = _as_of_get(test_client, "2026-11-04T12:00:00-05:00", token="s3cret")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["consistency"]["status"] == "live"
    assert data["consistency"]["week_index"] == 1
    assert data["rows"][0]["this_week"]["lifts"] == 30
    assert data["rows"][0]["score"] == 30


def test_as_of_rejects_garbage_with_400(test_client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "s3cret")
    resp = _as_of_get(test_client, "next tuesday", token="s3cret")
    assert resp.status_code == 400


def test_as_of_plus_offset_survives_query_decoding(test_client, monkeypatch):
    """An unencoded '+00:00' arrives as ' 00:00'."""
    monkeypatch.setenv("ADMIN_TOKEN", "s3cret")
    resp = _as_of_get(test_client, "2026-11-04T17:00:00 00:00", token="s3cret")
    assert resp.status_code == 200
    assert resp.get_json()["consistency"]["week_index"] == 1


@pytest.mark.parametrize("raw,hour_utc", [
    ("2026-11-04 12:00:00", 12),
    ("2026-11-04 12:00", 12),
    ("2026-11-04T12:00:00Z", 12),
    ("2026-11-04 12:00:00Z", 12),
    ("2026-11-04T12:00:00-05:00", 17),
    ("2026-11-04 12:00:00-05:00", 17),
    ("2026-11-04T12:00:00 05:00", 7),
    ("2026-11-04 12:00:00 05:00", 7),
])
def test_as_of_formats_parse_to_the_right_instant(raw, hour_utc):
    """Runs on CI's Python 3.10 too, whose fromisoformat is the strictest we deploy."""
    import datetime as dt
    from toms_gym.routes.competition_routes import _parse_as_of
    assert _parse_as_of(raw) == dt.datetime(2026, 11, 4, hour_utc, tzinfo=dt.timezone.utc)


def test_without_as_of_the_board_uses_now(test_client, monkeypatch):
    """No param, no token: public, and an attempt in a future week scores nothing."""
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    session = _make_session(_CONSISTENCY_DESC, [_squat_row("2099-01-06T17:00:00+00:00")])
    with patch("toms_gym.routes.competition_routes.get_db_connection", return_value=session):
        resp = test_client.get("/competitions/comp1/leaderboard")
    assert resp.status_code == 200
    assert resp.get_json()["rows"][0]["score"] == 0


def test_creating_a_competition_passes_mode_and_rules_into_metadata(test_client):
    captured = {}
    session = MagicMock()

    def execute(statement, params=None):
        captured["params"] = params
        result = MagicMock()
        result.fetchone.return_value = ["new-id"]
        return result

    session.execute.side_effect = execute
    body = {"name": "The 100 Club", "description": "100 lifts a week.",
            "start_date": "2026-10-31T10:00:00-04:00", "end_date": "2026-12-27T23:59:59-05:00",
            "status": "in_progress", "lifttypes": ["Situp", "Pushup", "Squat", "Plank"],
            "mode": "consistency", "rules": {"base_quota": 100, "week_start": "2026-11-02"}}
    with patch("toms_gym.routes.competition_routes.get_db_connection", return_value=session):
        resp = test_client.post("/create_competition", json=body)
    assert resp.status_code == 201
    desc = captured["params"]["description"]
    location, blob = desc.split(" - ", 1)
    assert location == "100 lifts a week."
    meta = json.loads(blob)
    assert meta["mode"] == "consistency"
    assert meta["rules"] == {"base_quota": 100, "week_start": "2026-11-02"}
    assert meta["lifttypes"] == ["Situp", "Pushup", "Squat", "Plank"]


def test_creating_a_legacy_competition_has_no_mode_keys(test_client):
    captured = {}
    session = MagicMock()

    def execute(statement, params=None):
        captured["params"] = params
        result = MagicMock()
        result.fetchone.return_value = ["new-id"]
        return result

    session.execute.side_effect = execute
    with patch("toms_gym.routes.competition_routes.get_db_connection", return_value=session):
        test_client.post("/create_competition", json={"name": "x", "description": "Gym",
                                                      "lifttypes": ["Squat"]})
    meta = json.loads(captured["params"]["description"].split(" - ", 1)[1])
    assert set(meta) == {"lifttypes", "weightclasses", "gender"}


def _comp_by_id_row(description):
    row = MagicMock()
    data = {"id": "comp1", "name": "The 100 Club", "description": description}
    row._mapping = data
    return row


def test_competition_by_id_returns_mode_and_filled_rules(test_client):
    session = MagicMock()
    session.execute.return_value.fetchone.return_value = _comp_by_id_row(_CONSISTENCY_DESC)
    with patch("toms_gym.routes.competition_routes.get_db_connection", return_value=session):
        resp = test_client.get("/competitions/comp1")
    assert resp.status_code == 200
    comp = resp.get_json()["competition"]
    assert comp["lifttypes"] == ["Situp", "Pushup", "Squat", "Plank"]
    assert comp["mode"] == "consistency"
    assert comp["rules"]["week_start"] == "2026-11-02"
    assert comp["rules"]["ramp"] == 25
    assert comp["rules"]["tz"] == "America/New_York"


def test_competition_by_id_legacy_has_null_mode(test_client):
    session = MagicMock()
    session.execute.return_value.fetchone.return_value = _comp_by_id_row(
        'Gym - {"lifttypes": ["Plank"], "weightclasses": [], "gender": "M"}')
    with patch("toms_gym.routes.competition_routes.get_db_connection", return_value=session):
        comp = test_client.get("/competitions/comp1").get_json()["competition"]
    assert comp["mode"] is None
    assert comp["rules"] is None
