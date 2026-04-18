"""Course + Tee matching service.

`match_or_create_course` fuzzy-matches on name via pg_trgm similarity and
optionally biases toward courses near a given lat/lng. On miss, inserts a new
Course with status='pending'.

`match_or_create_tee` tries an exact-name match on the given course's tees;
creates a new Tee when rating/slope are provided; otherwise signals that the
review UI must prompt the user.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict

import sqlalchemy

SIMILARITY_THRESHOLD = 0.4      # pg_trgm similarity — tuned for typos.
SEARCH_SIMILARITY_THRESHOLD = 0.2  # lower bar for autocomplete/search prefixes.
GEO_RADIUS_DEGREES = 0.5        # ~55 km; rough bbox prefilter before sim.


@dataclass
class CourseMatch:
    course_id: str
    created: bool
    status: str
    similarity: float  # 1.0 when created


@dataclass
class TeeMatch:
    tee_id: Optional[str]
    created: bool
    needs_tee: bool  # True when no match and no rating/slope to create one


def match_or_create_course(
    session,
    name: str,
    near: Optional[Tuple[float, float]],
) -> CourseMatch:
    """Fuzzy-match by name, optionally bias by lat/lng. Create pending on miss."""
    params = {"name": name, "threshold": SIMILARITY_THRESHOLD}
    geo_clause = ""
    if near:
        lat, lng = near
        params.update({"lat": lat, "lng": lng, "rad": GEO_RADIUS_DEGREES})
        # Prefer nearby courses: filter to bbox first (cheap), then rank by sim.
        geo_clause = (
            " AND latitude BETWEEN :lat - :rad AND :lat + :rad"
            " AND longitude BETWEEN :lng - :rad AND :lng + :rad"
        )

    row = session.execute(sqlalchemy.text(f"""
        SELECT id, status, similarity(name, :name) AS sim
        FROM "Course"
        WHERE similarity(name, :name) > :threshold {geo_clause}
        ORDER BY sim DESC
        LIMIT 1
    """), params).fetchone()

    if row:
        return CourseMatch(
            course_id=str(row[0]), created=False,
            status=row[1], similarity=float(row[2]),
        )

    insert_row = session.execute(sqlalchemy.text("""
        INSERT INTO "Course" (name, latitude, longitude, status)
        VALUES (:name, :lat, :lng, 'pending') RETURNING id
    """), {
        "name": name,
        "lat": near[0] if near else None,
        "lng": near[1] if near else None,
    }).fetchone()
    session.commit()
    return CourseMatch(
        course_id=str(insert_row[0]), created=True,
        status="pending", similarity=1.0,
    )


def match_or_create_tee(
    session,
    course_id: str,
    name: str,
    rating: Optional[float],
    slope: Optional[int],
) -> TeeMatch:
    """Exact-name match first; create when rating/slope present; else signal."""
    row = session.execute(sqlalchemy.text("""
        SELECT id FROM "Tee"
        WHERE course_id = :cid AND LOWER(name) = LOWER(:name)
        LIMIT 1
    """), {"cid": course_id, "name": name}).fetchone()
    if row:
        return TeeMatch(tee_id=str(row[0]), created=False, needs_tee=False)

    if rating is not None and slope is not None:
        new_row = session.execute(sqlalchemy.text("""
            INSERT INTO "Tee" (course_id, name, rating_18, slope_18)
            VALUES (:cid, :name, :rating, :slope) RETURNING id
        """), {"cid": course_id, "name": name, "rating": rating, "slope": slope}).fetchone()
        session.commit()
        return TeeMatch(tee_id=str(new_row[0]), created=True, needs_tee=False)

    return TeeMatch(tee_id=None, created=False, needs_tee=True)


def search_courses(
    session,
    q: str,
    near: Optional[Tuple[float, float]],
    limit: int = 10,
) -> List[Dict]:
    params = {"q": q, "threshold": SEARCH_SIMILARITY_THRESHOLD, "limit": limit}
    geo_clause = ""
    if near:
        lat, lng = near
        params.update({"lat": lat, "lng": lng, "rad": GEO_RADIUS_DEGREES})
        geo_clause = (
            " AND latitude BETWEEN :lat - :rad AND :lat + :rad"
            " AND longitude BETWEEN :lng - :rad AND :lng + :rad"
        )
    rows = session.execute(sqlalchemy.text(f"""
        SELECT id, name, city, state, country, latitude, longitude, status,
               similarity(name, :q) AS sim
        FROM "Course"
        WHERE similarity(name, :q) > :threshold {geo_clause}
        ORDER BY sim DESC
        LIMIT :limit
    """), params).fetchall()
    return [
        {
            "id": str(r[0]), "name": r[1], "city": r[2], "state": r[3],
            "country": r[4],
            "latitude": float(r[5]) if r[5] is not None else None,
            "longitude": float(r[6]) if r[6] is not None else None,
            "status": r[7], "similarity": float(r[8]),
        }
        for r in rows
    ]
