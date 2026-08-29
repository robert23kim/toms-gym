from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from toms_gym.routes.lifting_routes import lifting_bp


@pytest.fixture
def client():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(lifting_bp)
    return app.test_client()


def _result_row(**overrides):
    row = MagicMock()
    row.id = "r1"
    row.attempt_id = "a1"
    row.processing_status = "completed"
    row.annotated_video_url = "https://cdn/annotated.mp4"
    row.summary_url = None
    row.report = {"total_reps": 12}
    row.processing_time_s = 42.5
    row.error_message = None
    row.created_at = datetime(2026, 8, 29, 1, 0, 0)
    row.updated_at = datetime(2026, 8, 29, 1, 5, 0)
    row.user_id = "u1"
    row.competition_id = "c1"
    for k, v in overrides.items():
        setattr(row, k, v)
    return row


def _session(row):
    session = MagicMock()
    session.execute.return_value.fetchone.return_value = row
    return session


def test_result_carries_ids_needed_to_deep_link(client):
    session = _session(_result_row())
    with patch("toms_gym.routes.lifting_routes.get_db_connection", return_value=session):
        resp = client.get("/lifting/result/a1")

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["attempt_id"] == "a1"
    assert body["processing_status"] == "completed"
    assert body["user_id"] == "u1"
    assert body["competition_id"] == "c1"
    sql = str(session.execute.call_args[0][0])
    assert '"UserCompetition"' in sql and "LEFT JOIN" in sql


def test_result_without_linked_competition_still_returns(client):
    session = _session(_result_row(user_id=None, competition_id=None))
    with patch("toms_gym.routes.lifting_routes.get_db_connection", return_value=session):
        resp = client.get("/lifting/result/a1")

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["user_id"] is None
    assert body["competition_id"] is None


def test_missing_result_is_404(client):
    session = _session(None)
    with patch("toms_gym.routes.lifting_routes.get_db_connection", return_value=session):
        resp = client.get("/lifting/result/nope")

    assert resp.status_code == 404
