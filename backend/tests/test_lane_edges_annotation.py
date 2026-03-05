"""Tests for per-frame lane edge annotation endpoints.

Covers:
- PUT  /bowling/result/<id>/annotation/lane-edges/<frame>
- DELETE /bowling/result/<id>/annotation/lane-edges/<frame>
"""
import json
import uuid
import pytest
from sqlalchemy import text


# ---------------------------------------------------------------------------
# Fixtures (reuse conftest patterns)
# ---------------------------------------------------------------------------

@pytest.fixture
def bowling_result(db_session, create_test_setup):
    """Create a BowlingResult with NULL annotation."""
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

    return {"result_id": result_id, "attempt_id": attempt_id}


@pytest.fixture
def bowling_result_with_frames(db_session, bowling_result):
    """BowlingResult that already has frames extracted."""
    result_id = bowling_result["result_id"]
    annotation = {
        "version": "1.0",
        "video_metadata": {
            "fps": 30.0, "total_frames": 60, "width": 1920, "height": 1080,
        },
        "ball_annotations": {"3": {"x": 10, "y": 20, "radius": 15}},
        "frame_markers": {"pin_hit": 45},
    }
    db_session.execute(text("""
        UPDATE "BowlingResult"
        SET frames_url = :frames_url, annotation = :annotation
        WHERE id = :id
    """), {
        "id": result_id,
        "frames_url": "bowling/frames/test-123/",
        "annotation": json.dumps(annotation),
    })
    db_session.commit()
    return bowling_result


@pytest.fixture
def lane_edges_client(app):
    """Flask test client."""
    return app.test_client()


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

VALID_LANE_EDGES = {
    "top_left": [100, 50],
    "top_right": [500, 50],
    "bottom_left": [50, 400],
    "bottom_right": [550, 400],
}

VALID_LANE_EDGES_WITH_POLYLINES = {
    "top_left": [100, 50],
    "top_right": [500, 50],
    "bottom_left": [50, 400],
    "bottom_right": [550, 400],
    "left_edge_points": [[60, 100], [55, 200], [50, 300], [50, 400]],
    "right_edge_points": [[540, 100], [545, 200], [550, 300], [550, 400]],
}


# ---------------------------------------------------------------------------
# PUT /result/<id>/annotation/lane-edges/<frame>
# ---------------------------------------------------------------------------

class TestSaveLaneEdges:
    """PUT /bowling/result/<id>/annotation/lane-edges/<frame>"""

    def test_put_lane_edges_on_null_annotation(
        self, lane_edges_client, bowling_result, db_session
    ):
        """Set lane edges on result with NULL annotation (tests _ensure_annotation_structure)."""
        rid = bowling_result["result_id"]
        # Verify annotation is NULL before
        row = db_session.execute(text(
            'SELECT annotation FROM "BowlingResult" WHERE id = :id'
        ), {"id": rid}).fetchone()
        assert row[0] is None

        resp = lane_edges_client.put(
            f'/bowling/result/{rid}/annotation/lane-edges/0',
            json=VALID_LANE_EDGES,
        )
        assert resp.status_code == 200
        assert resp.get_json() == {'status': 'saved'}

    def test_put_and_get_lane_edges(self, lane_edges_client, bowling_result_with_frames):
        """PUT lane edges on frame 5 then GET annotation to verify stored correctly."""
        rid = bowling_result_with_frames["result_id"]
        resp = lane_edges_client.put(
            f'/bowling/result/{rid}/annotation/lane-edges/5',
            json=VALID_LANE_EDGES,
        )
        assert resp.status_code == 200

        # GET annotation and verify
        resp2 = lane_edges_client.get(f'/bowling/result/{rid}/annotation')
        data = resp2.get_json()
        assert 'frame_lane_edges' in data
        assert '5' in data['frame_lane_edges']
        stored = data['frame_lane_edges']['5']
        assert stored['top_left'] == [100, 50]
        assert stored['top_right'] == [500, 50]
        assert stored['bottom_left'] == [50, 400]
        assert stored['bottom_right'] == [550, 400]

    def test_put_preserves_existing_annotations(self, lane_edges_client, bowling_result_with_frames):
        """PUT lane edges does not clobber existing ball_annotations or frame_markers."""
        rid = bowling_result_with_frames["result_id"]
        resp = lane_edges_client.put(
            f'/bowling/result/{rid}/annotation/lane-edges/10',
            json=VALID_LANE_EDGES,
        )
        assert resp.status_code == 200

        resp2 = lane_edges_client.get(f'/bowling/result/{rid}/annotation')
        data = resp2.get_json()
        # Existing ball_annotations and frame_markers must survive
        assert data['ball_annotations']['3'] == {"x": 10, "y": 20, "radius": 15}
        assert data['frame_markers']['pin_hit'] == 45
        # Lane edges also present
        assert '10' in data['frame_lane_edges']

    def test_validate_missing_corners_returns_400(self, lane_edges_client, bowling_result):
        """PUT with missing corners returns 400."""
        rid = bowling_result["result_id"]
        incomplete = {
            "top_left": [100, 50],
            "top_right": [500, 50],
            # missing bottom_left and bottom_right
        }
        resp = lane_edges_client.put(
            f'/bowling/result/{rid}/annotation/lane-edges/0',
            json=incomplete,
        )
        assert resp.status_code == 400
        assert 'Missing required corners' in resp.get_json()['error']

    def test_validate_bad_corner_shape_returns_400(self, lane_edges_client, bowling_result):
        """PUT with bad corner shape (not [x, y]) returns 400."""
        rid = bowling_result["result_id"]
        bad_shape = {
            "top_left": [100],  # only 1 element
            "top_right": [500, 50],
            "bottom_left": [50, 400],
            "bottom_right": [550, 400],
        }
        resp = lane_edges_client.put(
            f'/bowling/result/{rid}/annotation/lane-edges/0',
            json=bad_shape,
        )
        assert resp.status_code == 400
        assert 'must be an [x, y] array' in resp.get_json()['error']

    def test_put_with_polyline_points(self, lane_edges_client, bowling_result_with_frames):
        """PUT with optional polyline points preserves them in storage."""
        rid = bowling_result_with_frames["result_id"]
        resp = lane_edges_client.put(
            f'/bowling/result/{rid}/annotation/lane-edges/7',
            json=VALID_LANE_EDGES_WITH_POLYLINES,
        )
        assert resp.status_code == 200

        resp2 = lane_edges_client.get(f'/bowling/result/{rid}/annotation')
        data = resp2.get_json()
        stored = data['frame_lane_edges']['7']
        assert stored['left_edge_points'] == [[60, 100], [55, 200], [50, 300], [50, 400]]
        assert stored['right_edge_points'] == [[540, 100], [545, 200], [550, 300], [550, 400]]
        assert stored['top_left'] == [100, 50]


# ---------------------------------------------------------------------------
# DELETE /result/<id>/annotation/lane-edges/<frame>
# ---------------------------------------------------------------------------

class TestDeleteLaneEdges:
    """DELETE /bowling/result/<id>/annotation/lane-edges/<frame>"""

    def test_delete_existing_removes_key(self, lane_edges_client, bowling_result_with_frames):
        """DELETE removes the lane edge override for a frame."""
        rid = bowling_result_with_frames["result_id"]

        # First PUT lane edges on frame 5
        lane_edges_client.put(
            f'/bowling/result/{rid}/annotation/lane-edges/5',
            json=VALID_LANE_EDGES,
        )
        # Verify it exists
        resp = lane_edges_client.get(f'/bowling/result/{rid}/annotation')
        assert '5' in resp.get_json()['frame_lane_edges']

        # DELETE it
        resp2 = lane_edges_client.delete(f'/bowling/result/{rid}/annotation/lane-edges/5')
        assert resp2.status_code == 200
        assert resp2.get_json() == {'status': 'deleted'}

        # Verify key is GONE
        resp3 = lane_edges_client.get(f'/bowling/result/{rid}/annotation')
        data = resp3.get_json()
        assert '5' not in data['frame_lane_edges'], \
            "DELETE should remove the frame_lane_edges key entirely"

    def test_delete_nonexistent_is_idempotent(self, lane_edges_client, bowling_result_with_frames):
        """DELETE on non-existent frame does not error (idempotent)."""
        rid = bowling_result_with_frames["result_id"]
        resp = lane_edges_client.delete(f'/bowling/result/{rid}/annotation/lane-edges/999')
        assert resp.status_code == 200

    def test_no_body_returns_400(self, lane_edges_client, bowling_result):
        """PUT with no body returns 400."""
        rid = bowling_result["result_id"]
        resp = lane_edges_client.put(
            f'/bowling/result/{rid}/annotation/lane-edges/0',
            data='',
            content_type='application/json',
        )
        assert resp.status_code == 400
