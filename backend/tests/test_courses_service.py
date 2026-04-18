"""Integration tests for the courses service.

These hit a real Postgres (via the conftest `db_session` fixture) so we can
exercise pg_trgm similarity and foreign-key behavior end-to-end.
"""
import pytest
from sqlalchemy import text

from toms_gym.services.courses import (
    match_or_create_course,
    match_or_create_tee,
    search_courses,
    CourseMatch,
    TeeMatch,
)


@pytest.fixture
def seeded_course(db_session):
    # Clean any prior Course/Tee rows so tests are independent.
    db_session.execute(text('DELETE FROM "Tee"'))
    db_session.execute(text('DELETE FROM "Course"'))
    db_session.commit()

    course_id = db_session.execute(text(
        """INSERT INTO "Course" (name, city, state, status, latitude, longitude)
           VALUES ('Pebble Beach Golf Links', 'Pebble Beach', 'CA', 'verified',
                   36.5681, -121.9497)
           RETURNING id"""
    )).scalar()
    db_session.execute(text(
        """INSERT INTO "Tee" (course_id, name, color_hex, rating_18, slope_18, par)
           VALUES (:cid, 'Blue', '#185FA5', 72.7, 138, 72)"""
    ), {"cid": course_id})
    db_session.commit()
    return course_id


def test_fuzzy_match_course_tolerates_typos(db_session, seeded_course):
    match = match_or_create_course(db_session, name="Peble Beach Golf Lnks", near=None)
    assert isinstance(match, CourseMatch)
    assert match.course_id == str(seeded_course)
    assert match.created is False
    assert match.similarity >= 0.4


def test_course_match_creates_pending_on_miss(db_session):
    match = match_or_create_course(
        db_session, name="Totally Made Up Course XYZ", near=None
    )
    assert match.created is True
    assert match.status == "pending"


def test_geo_filter_prefers_nearby_course(db_session, seeded_course):
    # Seed a second Pebble-named course far away.
    far_id = db_session.execute(text(
        """INSERT INTO "Course" (name, latitude, longitude, status)
           VALUES ('Pebble Beach Club', 40.0, -100.0, 'verified') RETURNING id"""
    )).scalar()
    db_session.commit()

    match = match_or_create_course(
        db_session, name="Pebble Beach", near=(36.5681, -121.9497)
    )
    assert match.course_id == str(seeded_course)
    assert match.course_id != str(far_id)


def test_tee_match_by_name(db_session, seeded_course):
    tee = match_or_create_tee(
        db_session, course_id=seeded_course, name="Blue",
        rating=None, slope=None
    )
    assert isinstance(tee, TeeMatch)
    assert tee.created is False
    assert tee.tee_id is not None


def test_tee_creates_when_rating_slope_present(db_session, seeded_course):
    tee = match_or_create_tee(
        db_session, course_id=seeded_course, name="White",
        rating=70.2, slope=131
    )
    assert tee.created is True
    assert tee.tee_id is not None


def test_tee_needs_tee_when_no_match_and_no_rating(db_session, seeded_course):
    tee = match_or_create_tee(
        db_session, course_id=seeded_course, name="Unknown Tee",
        rating=None, slope=None
    )
    assert tee.created is False
    assert tee.tee_id is None
    assert tee.needs_tee is True


def test_search_courses_returns_top_matches(db_session, seeded_course):
    results = search_courses(db_session, q="Pebble", near=None, limit=5)
    assert len(results) >= 1
    assert any(r["id"] == str(seeded_course) for r in results)
