"""Tests for POST /admin/sweep-stuck-analysis. Self-contained: needs the local
test Postgres but not the DB-heavy conftest.

    docker run --rm -d --name sweep-test-pg -p 5434:5432 \
      -e POSTGRES_PASSWORD=test -e POSTGRES_DB=toms_gym_test postgres:15
    venv/bin/python -m pytest tests/test_sweep_stuck.py --noconftest
"""
import os
import uuid

# Must be set before importing toms_gym.db (engine is built at import time).
os.environ.setdefault(
    "DATABASE_URL", "postgresql+pg8000://postgres:test@localhost:5434/toms_gym_test"
)

import pytest
import sqlalchemy
from flask import Flask

from toms_gym.db import get_db_connection
from toms_gym.routes.admin_routes import admin_bp


@pytest.fixture()
def client():
    app = Flask(__name__)
    app.register_blueprint(admin_bp)
    return app.test_client()


@pytest.fixture()
def db():
    session = get_db_connection()
    for table in ("LiftingResult", "BowlingResult"):
        session.execute(sqlalchemy.text(f'''
            CREATE TABLE IF NOT EXISTS "{table}" (
                id TEXT PRIMARY KEY,
                attempt_id TEXT,
                processing_status TEXT NOT NULL,
                error_message TEXT,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        '''))
        session.execute(sqlalchemy.text(f'DELETE FROM "{table}"'))
    session.commit()
    yield session
    session.close()


def _insert(db, table, status, minutes_old):
    row_id = str(uuid.uuid4())
    db.execute(
        sqlalchemy.text(f'''
            INSERT INTO "{table}" (id, attempt_id, processing_status, updated_at)
            VALUES (:id, :aid, :status, now() - (:mins || ' minutes')::interval)
        '''),
        {"id": row_id, "aid": str(uuid.uuid4()), "status": status, "mins": minutes_old},
    )
    db.commit()
    return row_id


def _status(db, table, row_id):
    return db.execute(
        sqlalchemy.text(f'SELECT processing_status FROM "{table}" WHERE id = :id'),
        {"id": row_id},
    ).scalar()


def test_sweeps_stuck_processing_rows(client, db):
    stuck = _insert(db, "LiftingResult", "processing", 60)
    resp = client.post("/admin/sweep-stuck-analysis")
    assert resp.status_code == 200
    data = resp.get_json()
    assert stuck in data["swept"]["lifting"]
    assert _status(db, "LiftingResult", stuck) == "failed"


def test_sweeps_stuck_queued_rows_in_both_tables(client, db):
    lift = _insert(db, "LiftingResult", "queued", 45)
    bowl = _insert(db, "BowlingResult", "processing", 45)
    data = client.post("/admin/sweep-stuck-analysis").get_json()
    assert lift in data["swept"]["lifting"]
    assert bowl in data["swept"]["bowling"]
    assert _status(db, "BowlingResult", bowl) == "failed"


def test_leaves_fresh_and_terminal_rows_alone(client, db):
    fresh = _insert(db, "LiftingResult", "processing", 5)
    done = _insert(db, "LiftingResult", "completed", 500)
    failed = _insert(db, "LiftingResult", "failed", 500)
    data = client.post("/admin/sweep-stuck-analysis").get_json()
    assert data["swept"]["lifting"] == []
    assert _status(db, "LiftingResult", fresh) == "processing"
    assert _status(db, "LiftingResult", done) == "completed"
    assert _status(db, "LiftingResult", failed) == "failed"


def test_threshold_is_configurable(client, db):
    row = _insert(db, "LiftingResult", "processing", 10)
    data = client.post("/admin/sweep-stuck-analysis?older_than_minutes=5").get_json()
    assert row in data["swept"]["lifting"]
    assert data["older_than_minutes"] == 5


def test_swept_rows_carry_an_error_message(client, db):
    row = _insert(db, "LiftingResult", "processing", 60)
    client.post("/admin/sweep-stuck-analysis")
    msg = db.execute(
        sqlalchemy.text('SELECT error_message FROM "LiftingResult" WHERE id = :id'),
        {"id": row},
    ).scalar()
    assert msg and "stuck" in msg


def test_invalid_threshold_rejected(client, db):
    resp = client.post("/admin/sweep-stuck-analysis?older_than_minutes=0")
    assert resp.status_code == 400
    resp = client.post("/admin/sweep-stuck-analysis?older_than_minutes=abc")
    assert resp.status_code == 400
