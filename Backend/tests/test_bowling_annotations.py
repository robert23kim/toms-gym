"""Tests for bowling annotation endpoints (Task 1.3).

Covers all 7 endpoints with happy path + edge cases:
- GET  /result/<id>/frames
- GET  /result/<id>/frames/<n>
- GET  /result/<id>/annotation
- PUT  /result/<id>/annotation
- PUT  /result/<id>/annotation/ball/<frame>
- DELETE /result/<id>/annotation/ball/<frame>
- PUT  /result/<id>/annotation/markers
"""
import json
import uuid
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import text

from toms_gym.db import get_db_connection, Session as DBSession


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def bowling_result(db_session, create_test_setup):
    """Create a BowlingResult with linked Attempt that has a video_url."""
    setup = create_test_setup
    attempt_id = str(uuid.uuid4())
    result_id = str(uuid.uuid4())

    # Create Attempt with video_url
    db_session.execute(text("""
        INSERT INTO "Attempt" (id, user_competition_id, lift_type, weight_kg, status, video_url)
        VALUES (:id, :ucid, 'Bowling', 0, 'pending', :video_url)
    """), {
        "id": attempt_id,
        "ucid": setup["user_competition_id"],
        "video_url": "https://storage.googleapis.com/test-bucket/bowling/input/test.mp4",
    })

    # Create BowlingResult with NULL annotation and no frames_url
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
        "ball_annotations": {},
        "frame_markers": {},
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
def bowling_result_no_video(db_session, create_test_setup):
    """BowlingResult linked to an Attempt with NO video_url."""
    setup = create_test_setup
    attempt_id = str(uuid.uuid4())
    result_id = str(uuid.uuid4())

    db_session.execute(text("""
        INSERT INTO "Attempt" (id, user_competition_id, lift_type, weight_kg, status)
        VALUES (:id, :ucid, 'Bowling', 0, 'pending')
    """), {"id": attempt_id, "ucid": setup["user_competition_id"]})

    db_session.execute(text("""
        INSERT INTO "BowlingResult" (id, attempt_id, processing_status)
        VALUES (:id, :attempt_id, 'completed')
    """), {"id": result_id, "attempt_id": attempt_id})
    db_session.commit()

    return {"result_id": result_id, "attempt_id": attempt_id}


@pytest.fixture
def annotation_client(app):
    """Flask test client with bowling blueprint registered."""
    return app.test_client()


# ---------------------------------------------------------------------------
# GET /result/<id>/frames
# ---------------------------------------------------------------------------

class TestGetFrames:
    """GET /bowling/result/<id>/frames"""

    def test_cached_frames_returns_metadata(self, annotation_client, bowling_result_with_frames):
        """Already-extracted frames return cached metadata without calling service."""
        rid = bowling_result_with_frames["result_id"]
        resp = annotation_client.get(f'/bowling/result/{rid}/frames')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['frames_prefix'] == 'bowling/frames/test-123/'
        assert data['total_frames'] == 60
        assert data['fps'] == 30.0
        assert data['width'] == 1920
        assert data['height'] == 1080

    @patch('requests.post')
    @patch('google.oauth2.id_token.fetch_id_token')
    @patch('google.auth.transport.requests.Request')
    @patch.dict('os.environ', {'BOWLING_SERVICE_URL': 'http://test-service:8080'})
    def test_not_extracted_calls_service(
        self, mock_auth_req, mock_fetch_token, mock_requests_post,
        annotation_client, bowling_result
    ):
        """No frames_url triggers bowling service call.

        Note: requests, google.auth, google.oauth2 are imported INLINE inside
        get_frames(), so we must patch at the source module level (e.g.,
        @patch('requests.post')), NOT at the bowling_routes module level.
        """
        mock_fetch_token.return_value = 'fake-token'
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            'frames_prefix': 'bowling/frames/new/',
            'total_frames': 42, 'fps': 29.97, 'width': 1280, 'height': 720,
        }
        mock_resp.raise_for_status = MagicMock()
        mock_requests_post.return_value = mock_resp

        rid = bowling_result["result_id"]
        resp = annotation_client.get(f'/bowling/result/{rid}/frames')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total_frames'] == 42

        # Verify service was called with correct URL and raw video_url
        mock_requests_post.assert_called_once()
        call_args = mock_requests_post.call_args
        assert '/frames' in call_args[0][0]
        # Critical: must pass a.video_url (raw upload), NOT br.debug_video_url
        sent_video_url = call_args[1]['json']['video_url']
        assert sent_video_url == \
            'https://storage.googleapis.com/test-bucket/bowling/input/test.mp4', \
            f"Must use raw video URL (a.video_url), got: {sent_video_url}"

    def test_no_video_url_returns_400(self, annotation_client, bowling_result_no_video):
        """No video_url on attempt returns 400."""
        rid = bowling_result_no_video["result_id"]
        resp = annotation_client.get(f'/bowling/result/{rid}/frames')
        assert resp.status_code == 400
        assert 'No video' in resp.get_json()['error']

    def test_not_found_returns_404(self, annotation_client):
        """Non-existent result ID returns 404."""
        fake_id = str(uuid.uuid4())
        resp = annotation_client.get(f'/bowling/result/{fake_id}/frames')
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /result/<id>/frames/<n>
# ---------------------------------------------------------------------------

class TestGetFrameImage:
    """GET /bowling/result/<id>/frames/<n>"""

    def test_valid_frame_redirects_to_gcs(self, annotation_client, bowling_result_with_frames):
        """Valid frame number returns redirect to correct GCS URL."""
        rid = bowling_result_with_frames["result_id"]
        resp = annotation_client.get(f'/bowling/result/{rid}/frames/5')
        assert resp.status_code == 302
        location = resp.headers['Location']
        # Frame 5 (0-indexed) -> 0006.jpg (1-indexed ffmpeg filename)
        assert '0006.jpg' in location
        assert 'bowling/frames/test-123/' in location

    def test_frame_0_maps_to_0001_jpg(self, annotation_client, bowling_result_with_frames):
        """Frame 0 (0-indexed) maps to 0001.jpg (critical off-by-one test)."""
        rid = bowling_result_with_frames["result_id"]
        resp = annotation_client.get(f'/bowling/result/{rid}/frames/0')
        assert resp.status_code == 302
        location = resp.headers['Location']
        assert '0001.jpg' in location, f"Frame 0 should map to 0001.jpg, got: {location}"

    def test_redirect_url_uses_bucket_name(self, annotation_client, bowling_result_with_frames):
        """GCS redirect URL uses bucket.name (storage import), not env var."""
        rid = bowling_result_with_frames["result_id"]
        resp = annotation_client.get(f'/bowling/result/{rid}/frames/0')
        assert resp.status_code == 302
        location = resp.headers['Location']
        # URL must contain storage.googleapis.com and a bucket name
        assert 'storage.googleapis.com' in location, \
            f"Redirect must go to GCS, got: {location}"
        # URL format: https://storage.googleapis.com/{bucket.name}/{prefix}{filename}
        # If bucket.name is wrong/empty, the URL would be malformed
        parts = location.replace('https://storage.googleapis.com/', '').split('/')
        assert len(parts) >= 2, f"URL should have bucket/prefix/file, got: {location}"

    def test_no_frames_url_returns_404(self, annotation_client, bowling_result):
        """Result without frames_url returns 404."""
        rid = bowling_result["result_id"]
        resp = annotation_client.get(f'/bowling/result/{rid}/frames/0')
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /result/<id>/annotation
# ---------------------------------------------------------------------------

class TestGetAnnotation:
    """GET /bowling/result/<id>/annotation"""

    def test_empty_annotation_returns_empty_dict(self, annotation_client, bowling_result):
        """NULL annotation column returns {}."""
        rid = bowling_result["result_id"]
        resp = annotation_client.get(f'/bowling/result/{rid}/annotation')
        assert resp.status_code == 200
        assert resp.get_json() == {}

    def test_populated_annotation_returns_full_json(
        self, annotation_client, bowling_result_with_frames
    ):
        """Populated annotation returns full JSON with all keys."""
        rid = bowling_result_with_frames["result_id"]
        resp = annotation_client.get(f'/bowling/result/{rid}/annotation')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['version'] == '1.0'
        assert 'ball_annotations' in data
        assert 'frame_markers' in data
        assert data['video_metadata']['total_frames'] == 60

    def test_not_found_returns_404(self, annotation_client):
        """Non-existent result returns 404."""
        resp = annotation_client.get(f'/bowling/result/{uuid.uuid4()}/annotation')
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /result/<id>/annotation
# ---------------------------------------------------------------------------

class TestSaveAnnotation:
    """PUT /bowling/result/<id>/annotation"""

    def test_save_and_retrieve_roundtrip(
        self, annotation_client, bowling_result_with_frames
    ):
        """Save annotation then retrieve it -- round-trip test."""
        rid = bowling_result_with_frames["result_id"]
        payload = {
            "version": "1.0",
            "ball_annotations": {"0": {"x": 100, "y": 200, "radius": 25}},
            "frame_markers": {"pin_hit": 45},
            "video_metadata": {"fps": 30, "total_frames": 60, "width": 1920, "height": 1080},
        }
        resp = annotation_client.put(
            f'/bowling/result/{rid}/annotation',
            json=payload,
        )
        assert resp.status_code == 200

        # Retrieve and verify round-trip
        resp2 = annotation_client.get(f'/bowling/result/{rid}/annotation')
        data = resp2.get_json()
        assert data['ball_annotations']['0']['x'] == 100
        assert data['frame_markers']['pin_hit'] == 45

    def test_no_body_returns_400(self, annotation_client, bowling_result):
        """PUT with no JSON body returns 400."""
        rid = bowling_result["result_id"]
        resp = annotation_client.put(
            f'/bowling/result/{rid}/annotation',
            data='',
            content_type='application/json',
        )
        assert resp.status_code == 400

    def test_put_overwrites_entire_annotation(
        self, annotation_client, bowling_result_with_frames
    ):
        """PUT /annotation replaces the entire annotation, not a merge."""
        rid = bowling_result_with_frames["result_id"]
        # First save ball annotation on frame 5
        annotation_client.put(
            f'/bowling/result/{rid}/annotation/ball/5',
            json={"x": 100, "y": 200, "radius": 25},
        )
        # Now PUT a completely new annotation without that ball
        new_annotation = {
            "version": "2.0",
            "ball_annotations": {},
            "frame_markers": {"pin_hit": 10},
            "video_metadata": {"fps": 30, "total_frames": 60, "width": 1920, "height": 1080},
        }
        resp = annotation_client.put(
            f'/bowling/result/{rid}/annotation',
            json=new_annotation,
        )
        assert resp.status_code == 200

        # Verify old ball annotation is gone (full overwrite, not merge)
        resp2 = annotation_client.get(f'/bowling/result/{rid}/annotation')
        data = resp2.get_json()
        assert data['version'] == '2.0'
        assert '5' not in data['ball_annotations'], \
            "PUT should overwrite entire annotation, not merge"
        assert data['frame_markers']['pin_hit'] == 10


# ---------------------------------------------------------------------------
# PUT /result/<id>/annotation/ball/<frame>
# ---------------------------------------------------------------------------

class TestSaveBallAnnotation:
    """PUT /bowling/result/<id>/annotation/ball/<frame>"""

    def test_set_ball_on_null_annotation(self, annotation_client, bowling_result, db_session):
        """Set ball on result with NULL annotation (tests _ensure_annotation_structure)."""
        rid = bowling_result["result_id"]
        # Verify annotation is NULL before
        row = db_session.execute(text(
            'SELECT annotation FROM "BowlingResult" WHERE id = :id'
        ), {"id": rid}).fetchone()
        assert row[0] is None

        resp = annotation_client.put(
            f'/bowling/result/{rid}/annotation/ball/0',
            json={"x": 100, "y": 200, "radius": 25},
        )
        assert resp.status_code == 200

        # Verify stored correctly with 0-indexed key
        resp2 = annotation_client.get(f'/bowling/result/{rid}/annotation')
        data = resp2.get_json()
        assert '0' in data['ball_annotations']
        assert data['ball_annotations']['0']['x'] == 100

    def test_set_ball_on_empty_annotation(self, annotation_client, bowling_result, db_session):
        """Set ball on annotation = {} (missing ball_annotations key)."""
        rid = bowling_result["result_id"]
        # Set annotation to empty JSON object (no ball_annotations key)
        db_session.execute(text("""
            UPDATE "BowlingResult" SET annotation = '{}'::jsonb WHERE id = :id
        """), {"id": rid})
        db_session.commit()

        resp = annotation_client.put(
            f'/bowling/result/{rid}/annotation/ball/5',
            json={"x": 50, "y": 60, "radius": 20},
        )
        assert resp.status_code == 200

        resp2 = annotation_client.get(f'/bowling/result/{rid}/annotation')
        data = resp2.get_json()
        assert data['ball_annotations']['5']['x'] == 50

    def test_set_ball_on_existing_annotations(
        self, annotation_client, bowling_result_with_frames
    ):
        """Set ball on annotation that already has ball_annotations."""
        rid = bowling_result_with_frames["result_id"]
        resp = annotation_client.put(
            f'/bowling/result/{rid}/annotation/ball/10',
            json={"x": 300, "y": 400, "radius": 30},
        )
        assert resp.status_code == 200

        resp2 = annotation_client.get(f'/bowling/result/{rid}/annotation')
        data = resp2.get_json()
        assert data['ball_annotations']['10']['x'] == 300

    def test_set_null_marks_no_ball_visible(
        self, annotation_client, bowling_result_with_frames
    ):
        """PUT with null body marks "no ball visible" (value is null, key exists)."""
        rid = bowling_result_with_frames["result_id"]
        # Send null body -- axios.put(url, null) sends empty body
        resp = annotation_client.put(
            f'/bowling/result/{rid}/annotation/ball/7',
            data='null',
            content_type='application/json',
        )
        assert resp.status_code == 200

        resp2 = annotation_client.get(f'/bowling/result/{rid}/annotation')
        data = resp2.get_json()
        assert '7' in data['ball_annotations'], "Key '7' should exist"
        assert data['ball_annotations']['7'] is None, "Value should be null (no ball visible)"

    def test_frame_key_is_0_indexed_string(
        self, annotation_client, bowling_result_with_frames
    ):
        """Verify frame number stored as 0-indexed string key in JSON."""
        rid = bowling_result_with_frames["result_id"]
        annotation_client.put(
            f'/bowling/result/{rid}/annotation/ball/0',
            json={"x": 1, "y": 2, "radius": 3},
        )

        resp = annotation_client.get(f'/bowling/result/{rid}/annotation')
        data = resp.get_json()
        # Key must be string "0", not "1" (no off-by-one)
        assert '0' in data['ball_annotations']
        assert '1' not in data['ball_annotations']


# ---------------------------------------------------------------------------
# DELETE /result/<id>/annotation/ball/<frame>
# ---------------------------------------------------------------------------

class TestDeleteBallAnnotation:
    """DELETE /bowling/result/<id>/annotation/ball/<frame>"""

    def test_delete_existing_removes_key(self, annotation_client, bowling_result_with_frames):
        """Delete existing annotation removes the key entirely."""
        rid = bowling_result_with_frames["result_id"]
        # First set a ball annotation
        annotation_client.put(
            f'/bowling/result/{rid}/annotation/ball/3',
            json={"x": 10, "y": 20, "radius": 15},
        )
        # Verify it exists
        resp = annotation_client.get(f'/bowling/result/{rid}/annotation')
        assert '3' in resp.get_json()['ball_annotations']

        # Delete it
        resp2 = annotation_client.delete(f'/bowling/result/{rid}/annotation/ball/3')
        assert resp2.status_code == 200

        # Verify key is GONE (not null)
        resp3 = annotation_client.get(f'/bowling/result/{rid}/annotation')
        data = resp3.get_json()
        assert '3' not in data['ball_annotations'], \
            "DELETE should remove key entirely, not set to null"

    def test_delete_nonexistent_is_idempotent(
        self, annotation_client, bowling_result_with_frames
    ):
        """Delete non-existent frame annotation does not error (idempotent)."""
        rid = bowling_result_with_frames["result_id"]
        resp = annotation_client.delete(f'/bowling/result/{rid}/annotation/ball/999')
        assert resp.status_code == 200

    def test_delete_vs_put_null_semantics(self, annotation_client, bowling_result_with_frames):
        """DELETE removes key; PUT null keeps key with null value. They are different."""
        rid = bowling_result_with_frames["result_id"]

        # PUT null on frame 20 (= "no ball visible")
        annotation_client.put(
            f'/bowling/result/{rid}/annotation/ball/20',
            data='null',
            content_type='application/json',
        )
        resp = annotation_client.get(f'/bowling/result/{rid}/annotation')
        data = resp.get_json()
        assert '20' in data['ball_annotations'], "PUT null should keep key"
        assert data['ball_annotations']['20'] is None, "PUT null value should be null"

        # DELETE frame 20 (= "not yet annotated")
        annotation_client.delete(f'/bowling/result/{rid}/annotation/ball/20')
        resp2 = annotation_client.get(f'/bowling/result/{rid}/annotation')
        data2 = resp2.get_json()
        assert '20' not in data2['ball_annotations'], "DELETE should remove key entirely"


# ---------------------------------------------------------------------------
# PUT /result/<id>/annotation/markers
# ---------------------------------------------------------------------------

class TestSaveMarkers:
    """PUT /bowling/result/<id>/annotation/markers"""

    def test_set_all_4_markers(self, annotation_client, bowling_result_with_frames):
        """Set all 4 frame markers."""
        rid = bowling_result_with_frames["result_id"]
        markers = {
            "ball_down": 5,
            "breakpoint": 30,
            "pin_hit": 45,
            "ball_off_deck": 55,
        }
        resp = annotation_client.put(
            f'/bowling/result/{rid}/annotation/markers',
            json=markers,
        )
        assert resp.status_code == 200

        resp2 = annotation_client.get(f'/bowling/result/{rid}/annotation')
        data = resp2.get_json()
        assert data['frame_markers']['ball_down'] == 5
        assert data['frame_markers']['breakpoint'] == 30
        assert data['frame_markers']['pin_hit'] == 45
        assert data['frame_markers']['ball_off_deck'] == 55

    def test_markers_stored_in_annotation_json(
        self, annotation_client, bowling_result_with_frames, db_session
    ):
        """Markers are stored inside the annotation JSONB column."""
        rid = bowling_result_with_frames["result_id"]
        annotation_client.put(
            f'/bowling/result/{rid}/annotation/markers',
            json={"pin_hit": 42},
        )

        # Read directly from DB to verify storage location
        row = db_session.execute(text(
            'SELECT annotation FROM "BowlingResult" WHERE id = :id'
        ), {"id": rid}).fetchone()
        annotation = row[0]
        assert annotation['frame_markers']['pin_hit'] == 42

    def test_no_body_returns_400(self, annotation_client, bowling_result):
        """PUT markers with no body returns 400."""
        rid = bowling_result["result_id"]
        resp = annotation_client.put(
            f'/bowling/result/{rid}/annotation/markers',
            data='',
            content_type='application/json',
        )
        assert resp.status_code == 400
