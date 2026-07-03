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
              held_s="65.8", form_score="0.91"),
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
