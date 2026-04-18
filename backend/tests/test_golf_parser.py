"""Tests for the golf scorecard OCR parser.

These tests drive the refactor from a single-player, word-level parser to a
symbol-level, multi-player parser. They use a saved fixture of real OCR output
from `golf_scorecard.jpg` (two handwritten players: TOM and CHRIS).

Expected scores (verified against totals printed on the card):
  TOM:   front [5,8,4,6,7,8,6,4,8]=56 / back [6,5,8,5,4,4,9,4,4]=49 / total 105
  CHRIS: front [6,5,5,5,6,7,3,3,6]=46 / back [4,6,5,5,6,4,5,8,4]=47 / total 93
"""
import json
import pathlib

import pytest

from toms_gym.routes.golf_routes import (
    _parse_scorecard_symbols,
    _group_rows,
    _cluster_by_x,
    _deduplicate_symbols,
)


FIXTURE_PATH = pathlib.Path(__file__).parent / "fixtures" / "golf_scorecard_ocr.json"


@pytest.fixture
def real_ocr():
    """Symbol-level OCR output from Vision API on golf_scorecard.jpg."""
    with open(FIXTURE_PATH) as f:
        return json.load(f)


# ---- Unit tests for helper functions ----


def test_cluster_by_x_groups_adjacent_symbols():
    syms = [
        {'text': '1', 'x': 100, 'y': 0, 'conf': 1.0},
        {'text': '0', 'x': 130, 'y': 0, 'conf': 1.0},
        {'text': '5', 'x': 160, 'y': 0, 'conf': 1.0},
        {'text': '7', 'x': 400, 'y': 0, 'conf': 1.0},
    ]
    clusters = _cluster_by_x(syms, gap_threshold=70)
    assert len(clusters) == 2
    assert [s['text'] for s in clusters[0]] == ['1', '0', '5']
    assert [s['text'] for s in clusters[1]] == ['7']


def test_deduplicate_symbols_removes_same_text_same_position():
    syms = [
        {'text': '5', 'x': 970, 'y': 1690, 'conf': 0.9},
        {'text': '5', 'x': 970, 'y': 1690, 'conf': 0.95},
        {'text': '5', 'x': 1118, 'y': 1690, 'conf': 0.9},
    ]
    out = _deduplicate_symbols(syms)
    assert len(out) == 2
    # Keeps the higher-confidence duplicate
    dup_survivor = [s for s in out if abs(s['x'] - 970) < 5][0]
    assert dup_survivor['conf'] == 0.95


# ---- Integration tests against real OCR fixture ----


def test_parser_detects_both_players(real_ocr):
    result = _parse_scorecard_symbols(
        real_ocr['symbols'], real_ocr['width'], real_ocr['height']
    )
    assert 'players' in result
    names = [p['name'] for p in result['players']]
    assert 'TOM' in names, f"Expected TOM in detected players, got {names}"
    assert 'CHRIS' in names, f"Expected CHRIS in detected players, got {names}"


def _holes_by_num(player):
    return {h['hole_number']: h for h in player['holes']}


def test_tom_scores_match_expected(real_ocr):
    result = _parse_scorecard_symbols(
        real_ocr['symbols'], real_ocr['width'], real_ocr['height']
    )
    tom = next(p for p in result['players'] if p['name'] == 'TOM')
    by_hole = _holes_by_num(tom)

    expected = {
        1: 5, 2: 8, 3: 4, 4: 6, 5: 7, 6: 8, 7: 6, 8: 4, 9: 8,
        10: 6, 11: 5, 12: 8, 13: 5, 14: 4, 15: 4, 16: 9, 17: 4, 18: 4,
    }
    for hole, expected_strokes in expected.items():
        assert by_hole[hole]['strokes'] == expected_strokes, (
            f"TOM hole {hole}: expected {expected_strokes}, "
            f"got {by_hole[hole]['strokes']}"
        )

    # Totals sanity check
    front = sum(by_hole[h]['strokes'] for h in range(1, 10))
    back = sum(by_hole[h]['strokes'] for h in range(10, 19))
    assert front == 56, f"TOM front 9 total: {front}"
    assert back == 49, f"TOM back 9 total: {back}"
    assert front + back == 105


def test_chris_scores_match_expected(real_ocr):
    result = _parse_scorecard_symbols(
        real_ocr['symbols'], real_ocr['width'], real_ocr['height']
    )
    chris = next(p for p in result['players'] if p['name'] == 'CHRIS')
    by_hole = _holes_by_num(chris)

    expected = {
        1: 6, 2: 5, 3: 5, 4: 5, 5: 6, 6: 7, 7: 3, 8: 3, 9: 6,
        10: 4, 11: 6, 12: 5, 13: 5, 14: 6, 15: 4, 16: 5, 17: 8, 18: 4,
    }
    for hole, expected_strokes in expected.items():
        assert by_hole[hole]['strokes'] == expected_strokes, (
            f"CHRIS hole {hole}: expected {expected_strokes}, "
            f"got {by_hole[hole]['strokes']}"
        )

    front = sum(by_hole[h]['strokes'] for h in range(1, 10))
    back = sum(by_hole[h]['strokes'] for h in range(10, 19))
    assert front == 46
    assert back == 47
    assert front + back == 93


def test_parser_does_not_treat_label_rows_as_players(real_ocr):
    """PAR, HANDICAP, BLACK, GOLD, GREEN, WHITE rows must not show up as players."""
    result = _parse_scorecard_symbols(
        real_ocr['symbols'], real_ocr['width'], real_ocr['height']
    )
    labels = {'PAR', 'HANDICAP', 'HDCP', 'HCP', 'BLACK', 'GOLD', 'GREEN',
              'WHITE', 'HOLE', 'OUT', 'IN', 'TOT', 'TOTAL', 'PLAYER'}
    for p in result['players']:
        assert p['name'] not in labels, f"Label {p['name']} misclassified as player"


def test_all_holes_have_valid_structure(real_ocr):
    result = _parse_scorecard_symbols(
        real_ocr['symbols'], real_ocr['width'], real_ocr['height']
    )
    for p in result['players']:
        assert len(p['holes']) == 18
        hole_nums = sorted(h['hole_number'] for h in p['holes'])
        assert hole_nums == list(range(1, 19))
        for h in p['holes']:
            assert 'par' in h and 'strokes' in h and 'ocr_confidence' in h


# ---- Upload-path integration tests (Task 5 / #14) ---------------------------
#
# These exercise /golf/upload end-to-end against the real DB: a multipart POST
# in, a JSON response with the nested {course, tee, needs_tee} shape out. They
# stub only (a) the Vision OCR call, (b) GCS blob writes, and (c) the EXIF
# auto-orient pass — everything else (match_or_create_course / _tee, DB
# inserts, response serialization) runs for real.

import io  # noqa: E402
import uuid  # noqa: E402

from sqlalchemy import text  # noqa: E402


def test_rate_limit_bypass_is_wired(app):
    """Tripwire regression test for Revision 1 fix #4. `rate_limit` no-ops only
    when `app.config['TESTING'] is True`; if future config drift flips this
    off, these integration tests will stop being deterministic under their
    10/hour cap. Fail fast here instead."""
    assert app.config['TESTING'] is True


@pytest.fixture
def clean_golf_tables(db_session):
    """Reset Fairway tables between upload tests so seed state is predictable."""
    db_session.execute(text('DELETE FROM "HoleScore"'))
    db_session.execute(text('DELETE FROM "HandicapSnapshot"'))
    db_session.execute(text('DELETE FROM "Round"'))
    db_session.execute(text('DELETE FROM "Tee"'))
    db_session.execute(text('DELETE FROM "Course"'))
    db_session.commit()
    yield


@pytest.fixture
def golf_user(db_session, clean_golf_tables):
    """Minimal User row so Round.user_id FK resolves."""
    user_id = str(uuid.uuid4())
    db_session.execute(
        text("""
            INSERT INTO "User" (id, email, name, username, auth_method, status, role, created_at)
            VALUES (:id, :email, :name, :username, 'password', 'active', 'user', NOW())
        """),
        {
            "id": user_id,
            "email": f"golfer_{user_id[:8]}@example.com",
            "name": "Golf Tester",
            "username": f"golfer_{user_id[:8]}",
        },
    )
    db_session.commit()
    return user_id


@pytest.fixture
def stub_ocr_and_gcs(monkeypatch):
    """Neutralize the three outside-world dependencies of the upload handler.

    - `_run_ocr`           → returns a sentinel object (truthy, `text` attr).
    - `_extract_players_from_ocr` → returns a single minimal 18-hole player.
    - `_auto_orient_image` → identity pass-through (no PIL Image.open on stub bytes).
    - `bucket.blob()`      → stub with upload_from_string / upload_from_file no-ops.
    """
    from toms_gym.routes import golf_routes

    class _StubOCRResponse:
        text = "stub ocr text"
        pages = []

    def _stub_run_ocr(_gcs_uri):
        return _StubOCRResponse()

    def _stub_extract_players(_resp):
        return [{
            "name": "TESTPLAYER",
            "holes": [
                {"hole_number": n, "par": 4, "strokes": 4, "ocr_confidence": 0.95}
                for n in range(1, 19)
            ],
        }]

    def _stub_auto_orient(file_bytes, content_type='image/jpeg'):
        return file_bytes

    class _StubBlob:
        def __init__(self, name): self.name = name
        def upload_from_string(self, data, content_type=None): pass
        def upload_from_file(self, f, content_type=None): pass

    class _StubBucket:
        name = "stub-bucket"
        def blob(self, name): return _StubBlob(name)

    monkeypatch.setattr(golf_routes, "_run_ocr", _stub_run_ocr)
    monkeypatch.setattr(golf_routes, "_extract_players_from_ocr", _stub_extract_players)
    monkeypatch.setattr(golf_routes, "_auto_orient_image", _stub_auto_orient)
    monkeypatch.setattr(golf_routes, "bucket", _StubBucket())


def _post_scorecard(client, **form):
    """Build a multipart upload request with a stub JPEG byte blob."""
    form.setdefault("image", (io.BytesIO(b"fake-jpeg-bytes"), "card.jpg"))
    return client.post(
        "/golf/upload",
        data=form,
        content_type="multipart/form-data",
    )


def test_upload_resolves_existing_course_by_name(
    client, db_session, golf_user, stub_ocr_and_gcs
):
    """Fuzzy-match: a typo on an existing verified course name should resolve
    to that course (not create a new pending one) and the existing 'Blue' tee
    should be picked up by name — i.e. `needs_tee` is False."""
    course_id = db_session.execute(text(
        """INSERT INTO "Course" (name, status) VALUES ('Pebble Beach Golf Links', 'verified')
           RETURNING id"""
    )).scalar()
    db_session.execute(text(
        """INSERT INTO "Tee" (course_id, name, rating_18, slope_18)
           VALUES (:cid, 'Default', 72.7, 138)"""
    ), {"cid": course_id})
    db_session.commit()

    resp = _post_scorecard(
        client,
        user_id=golf_user,
        course_name="Peble Beech Golf Lnks",  # deliberate typos
    )

    assert resp.status_code == 200, resp.get_data(as_text=True)
    body = resp.get_json()
    assert body["round"]["course"]["id"] == str(course_id)
    assert body["round"]["course"]["status"] == "verified"
    assert body["round"]["needs_tee"] is False
    assert body["round"]["tee"]["id"] is not None


def test_upload_creates_pending_course_on_miss(
    client, golf_user, stub_ocr_and_gcs
):
    """Novel course name with no seed → service creates a pending row; the
    response's nested course block reflects `status='pending'`."""
    resp = _post_scorecard(
        client,
        user_id=golf_user,
        course_name=f"Ephemeral Test Course {uuid.uuid4()}",
    )

    assert resp.status_code == 200, resp.get_data(as_text=True)
    body = resp.get_json()
    assert body["round"]["course"]["status"] == "pending"
    assert body["round"]["course"]["id"] is not None


def test_upload_marks_needs_tee_when_no_tee_on_course(
    client, db_session, golf_user, stub_ocr_and_gcs
):
    """Seed a course with zero tees; upload without rating/slope → tee service
    can't match or create, so `needs_tee=True` and `tee.id is None`."""
    course_id = db_session.execute(text(
        """INSERT INTO "Course" (name, status) VALUES ('Tee-Less Municipal', 'verified')
           RETURNING id"""
    )).scalar()
    db_session.commit()

    resp = _post_scorecard(
        client,
        user_id=golf_user,
        course_name="Tee-Less Municipal",
        # No slope_rating / course_rating → service can't create a new Tee.
    )

    assert resp.status_code == 200, resp.get_data(as_text=True)
    body = resp.get_json()
    assert body["round"]["course"]["id"] == str(course_id)
    assert body["round"]["needs_tee"] is True
    assert body["round"]["tee"]["id"] is None
