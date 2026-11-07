"""Bodyweight lifts (Pushup, Situp, Plank) always store weight_kg 0, whatever a
stale client posts; weighted lifts keep the posted weight."""
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from flask import Flask

from toms_gym.routes import attempt_routes, upload_routes

USER_ID = "11111111-1111-4111-8111-111111111111"
COMP_ID = "32ca7bad-a970-4a09-acec-02b768793063"
UC_ID = "22222222-2222-4222-8222-222222222222"
ATTEMPT_ID = "33333333-3333-4333-8333-333333333333"


@pytest.fixture
def client():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(upload_routes.upload_bp)
    app.register_blueprint(attempt_routes.attempt_bp)
    return app.test_client()


@pytest.fixture
def session(monkeypatch):
    s = MagicMock()
    s.execute.return_value.fetchone.return_value = (UC_ID,)
    s.execute.return_value.rowcount = 1
    monkeypatch.setattr(upload_routes, "get_db_connection", lambda: s)
    monkeypatch.setattr(attempt_routes, "get_db_connection", lambda: s)
    bucket = MagicMock()
    bucket.name = "test-bucket"
    bucket.blob.return_value.exists.return_value = True
    monkeypatch.setattr(upload_routes, "bucket", bucket)
    return s


def _attempt_weight(session, marker):
    writes = [c.args[1] for c in session.execute.call_args_list
              if marker in str(c.args[0]) and len(c.args) > 1]
    assert len(writes) == 1, f"expected one {marker} write, saw {len(writes)}"
    return writes[0]["weight_kg"]


def _finalize(client, lift_type, weight):
    return client.post("/upload/finalize", json={
        "object_name": "videos/x.mp4",
        "public_url": "https://storage.googleapis.com/test-bucket/videos/x.mp4",
        "competition_id": COMP_ID, "user_id": USER_ID,
        "lift_type": lift_type, "weight": weight,
    })


def _multipart(client, lift_type, weight):
    return client.post("/upload", data={
        "video": (BytesIO(b"bytes"), "lift.mp4"),
        "competition_id": COMP_ID, "user_id": USER_ID,
        "lift_type": lift_type, "weight": weight,
    }, content_type="multipart/form-data")


@pytest.mark.parametrize("lift_type", ["Pushup", "Situp", "Plank"])
def test_finalize_zeroes_weight_for_bodyweight_lifts(client, session, lift_type):
    resp = _finalize(client, lift_type, "60")
    assert resp.status_code == 200, resp.get_json()
    assert _attempt_weight(session, 'INSERT INTO "Attempt"') == 0


@pytest.mark.parametrize("lift_type", ["Pushup", "Situp", "Plank"])
def test_multipart_upload_zeroes_weight_for_bodyweight_lifts(client, session, lift_type):
    resp = _multipart(client, lift_type, "60")
    assert resp.status_code == 200, resp.get_json()
    assert _attempt_weight(session, 'INSERT INTO "Attempt"') == 0


@pytest.mark.parametrize("post", [_finalize, _multipart])
def test_weighted_lift_keeps_posted_weight(client, session, post):
    resp = post(client, "Squat", "60")
    assert resp.status_code == 200, resp.get_json()
    assert _attempt_weight(session, 'INSERT INTO "Attempt"') == 60.0


@pytest.mark.parametrize("lift_type", ["pushup", "SITUP", "Plank"])
def test_create_attempt_zeroes_weight_case_insensitively(client, session, lift_type):
    resp = client.post("/attempts", json={
        "user_competition_id": UC_ID, "lift_type": lift_type,
        "weight_kg": 60, "video_url": "https://x/v.mp4",
    })
    assert resp.status_code == 201, resp.get_json()
    assert _attempt_weight(session, 'INSERT INTO "Attempt"') == 0


def test_update_attempt_zeroes_weight_for_bodyweight_lift(client, session):
    resp = client.put(f"/attempts/{ATTEMPT_ID}", json={
        "lift_type": "Pushup", "weight_kg": 60, "status": "completed",
        "video_url": "https://x/v.mp4",
    })
    assert resp.status_code == 200, resp.get_json()
    assert _attempt_weight(session, 'UPDATE "Attempt"') == 0


def test_attempt_routes_keep_weight_for_weighted_lift(client, session):
    resp = client.post("/attempts", json={
        "user_competition_id": UC_ID, "lift_type": "Deadlift",
        "weight_kg": 140, "video_url": "https://x/v.mp4",
    })
    assert resp.status_code == 201, resp.get_json()
    assert _attempt_weight(session, 'INSERT INTO "Attempt"') == 140
