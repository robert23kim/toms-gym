"""End-to-end integration test for the annotation flow.

Tests the full lifecycle: create result → annotate ball → mark "no ball" →
delete annotation → set markers → verify final structure.

This catches bugs that unit tests miss: SQL query correctness, jsonb_set
path handling, _ensure_annotation_structure race conditions, and
DELETE-vs-PUT-null semantics in a real database.
"""
import json
import os
import uuid
import pytest
from sqlalchemy import text

from toms_gym.db import get_db_connection, Session as DBSession


@pytest.fixture(autouse=True)
def ensure_bowling_result_table(db_session):
    """Ensure BowlingResult table and prior migrations exist before testing."""
    migrations_dir = os.path.join(
        os.path.dirname(__file__), '..', 'toms_gym', 'migrations'
    )
    for migration in ['004_bowling_result.sql', '005_bowling_lane_edges.sql', '006_bowling_annotations.sql']:
        path = os.path.join(migrations_dir, migration)
        with open(path) as f:
            sql = f.read()
        db_session.execute(text(sql))
    db_session.commit()


@pytest.fixture
def integration_result(db_session, create_test_setup):
    """Create a BowlingResult with annotation = NULL for integration testing."""
    setup = create_test_setup
    attempt_id = str(uuid.uuid4())
    result_id = str(uuid.uuid4())

    db_session.execute(text("""
        INSERT INTO "Attempt" (id, user_competition_id, lift_type, weight_kg, status, video_url)
        VALUES (:id, :ucid, 'Bowling', 0, 'pending', :video_url)
    """), {
        "id": attempt_id,
        "ucid": setup["user_competition_id"],
        "video_url": "https://storage.googleapis.com/test-bucket/bowling/input/test.mp4",
    })

    db_session.execute(text("""
        INSERT INTO "BowlingResult" (id, attempt_id, processing_status)
        VALUES (:id, :attempt_id, 'completed')
    """), {"id": result_id, "attempt_id": attempt_id})
    db_session.commit()

    return result_id


@pytest.fixture
def integration_client(app):
    return app.test_client()


class TestAnnotationIntegration:
    """End-to-end annotation lifecycle test."""

    def test_full_annotation_lifecycle(self, integration_client, integration_result, db_session):
        """Complete annotation lifecycle: create → annotate → clear → markers → verify."""
        rid = integration_result
        client = integration_client

        # 1. Start with annotation = NULL
        resp = client.get(f'/bowling/result/{rid}/annotation')
        assert resp.status_code == 200
        assert resp.get_json() == {}

        # 2. PUT ball annotation on frame 0
        resp = client.put(
            f'/bowling/result/{rid}/annotation/ball/0',
            json={"x": 100, "y": 200, "radius": 25},
        )
        assert resp.status_code == 200

        # 3. Verify ball_annotations has key "0" with correct values
        resp = client.get(f'/bowling/result/{rid}/annotation')
        assert resp.status_code == 200
        data = resp.get_json()
        assert '0' in data['ball_annotations']
        assert data['ball_annotations']['0'] == {"x": 100, "y": 200, "radius": 25}

        # 4. PUT null on frame 0 → "no ball visible" (key exists, value is null)
        resp = client.put(
            f'/bowling/result/{rid}/annotation/ball/0',
            data='null',
            content_type='application/json',
        )
        assert resp.status_code == 200

        resp = client.get(f'/bowling/result/{rid}/annotation')
        data = resp.get_json()
        assert '0' in data['ball_annotations'], "Key '0' must still exist after PUT null"
        assert data['ball_annotations']['0'] is None, "Value must be null (no ball visible)"

        # 5. DELETE frame 0 → key completely gone ("not yet annotated")
        resp = client.delete(f'/bowling/result/{rid}/annotation/ball/0')
        assert resp.status_code == 200

        resp = client.get(f'/bowling/result/{rid}/annotation')
        data = resp.get_json()
        assert '0' not in data['ball_annotations'], \
            "Key '0' must be completely removed after DELETE"

        # 6. Set all 4 frame markers
        markers = {
            "ball_down": 5,
            "breakpoint": 30,
            "pin_hit": 45,
            "ball_off_deck": 55,
        }
        resp = client.put(
            f'/bowling/result/{rid}/annotation/markers',
            json=markers,
        )
        assert resp.status_code == 200

        # 7. Verify full annotation structure
        resp = client.get(f'/bowling/result/{rid}/annotation')
        assert resp.status_code == 200
        data = resp.get_json()

        # Structure check
        assert 'ball_annotations' in data
        assert 'frame_markers' in data
        assert data['frame_markers']['ball_down'] == 5
        assert data['frame_markers']['breakpoint'] == 30
        assert data['frame_markers']['pin_hit'] == 45
        assert data['frame_markers']['ball_off_deck'] == 55

        # 8. Verify frame_markers and ball_annotations coexist
        # Add a ball annotation and verify markers are still there
        resp = client.put(
            f'/bowling/result/{rid}/annotation/ball/10',
            json={"x": 300, "y": 400, "radius": 30},
        )
        assert resp.status_code == 200

        resp = client.get(f'/bowling/result/{rid}/annotation')
        data = resp.get_json()
        assert data['ball_annotations']['10'] == {"x": 300, "y": 400, "radius": 30}
        assert data['frame_markers']['pin_hit'] == 45, \
            "frame_markers must survive ball_annotation updates"

    def test_jsonb_set_on_null_annotation(self, integration_client, integration_result, db_session):
        """jsonb_set works when annotation column is NULL (via _ensure_annotation_structure)."""
        rid = integration_result

        # Verify annotation is actually NULL in DB
        row = db_session.execute(text(
            'SELECT annotation FROM "BowlingResult" WHERE id = :id'
        ), {"id": rid}).fetchone()
        assert row[0] is None

        # This should NOT crash with jsonb_set on NULL
        resp = integration_client.put(
            f'/bowling/result/{rid}/annotation/ball/0',
            json={"x": 1, "y": 2, "radius": 3},
        )
        assert resp.status_code == 200

    def test_jsonb_set_on_empty_object(self, integration_client, integration_result, db_session):
        """jsonb_set works when annotation is {} (no ball_annotations key)."""
        rid = integration_result

        # Set annotation to empty object
        db_session.execute(text("""
            UPDATE "BowlingResult" SET annotation = '{}'::jsonb WHERE id = :id
        """), {"id": rid})
        db_session.commit()

        # This should NOT crash
        resp = integration_client.put(
            f'/bowling/result/{rid}/annotation/ball/0',
            json={"x": 1, "y": 2, "radius": 3},
        )
        assert resp.status_code == 200

    def test_frame_0_to_0001_jpg_mapping(self, integration_client, integration_result, db_session):
        """Frame 0 redirects to 0001.jpg (off-by-one is the #1 bug risk)."""
        rid = integration_result

        # Set frames_url so the redirect endpoint works
        db_session.execute(text("""
            UPDATE "BowlingResult"
            SET frames_url = 'bowling/frames/test/'
            WHERE id = :id
        """), {"id": rid})
        db_session.commit()

        resp = integration_client.get(f'/bowling/result/{rid}/frames/0')
        assert resp.status_code == 302
        location = resp.headers['Location']
        assert '0001.jpg' in location, \
            f"Frame 0 must map to 0001.jpg, got: {location}"
        # Also verify frame 1 -> 0002.jpg
        resp2 = integration_client.get(f'/bowling/result/{rid}/frames/1')
        assert '0002.jpg' in resp2.headers['Location']
