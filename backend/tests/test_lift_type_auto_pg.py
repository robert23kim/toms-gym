"""Migration 020 and the change-lift-type flow against a real, throwaway Postgres.

Skipped unless AUTO_LIFT_PG_URL names a local database, e.g.
  docker run --rm -d -p 5434:5432 -e POSTGRES_PASSWORD=test -e POSTGRES_DB=autolift_test postgres:15
  AUTO_LIFT_PG_URL=postgresql+pg8000://postgres:test@127.0.0.1:5434/autolift_test
The schema is dropped and recreated on every run, so the URL must never point at a shared database.
"""
import os
import threading
import time
import uuid
from types import SimpleNamespace
from urllib.parse import urlparse

import pytest
import sqlalchemy
from flask import Flask
from sqlalchemy.orm import sessionmaker

PG_URL = os.environ.get("AUTO_LIFT_PG_URL")
pytestmark = pytest.mark.skipif(not PG_URL, reason="AUTO_LIFT_PG_URL not set")

CLUB_DESC = ('Gym - {"lifttypes": ["Situp", "Pushup", "Squat", "Plank"], '
             '"weightclasses": [], "gender": "", "mode": "consistency", '
             '"rules": {"week_start": "2026-11-02"}}')

SCHEMA = """
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
CREATE TYPE lift_type AS ENUM ('Squat', 'Plank', 'Pushup', 'Situp');
CREATE TYPE attempt_status AS ENUM ('pending', 'completed', 'failed');
CREATE TABLE "User" (id UUID PRIMARY KEY, name TEXT NOT NULL, email TEXT, is_test BOOLEAN DEFAULT false);
CREATE TABLE "Competition" (
    id UUID PRIMARY KEY, name TEXT NOT NULL, description TEXT,
    start_date TIMESTAMPTZ NOT NULL DEFAULT now(), end_date TIMESTAMPTZ NOT NULL DEFAULT now(),
    status TEXT DEFAULT 'in_progress');
CREATE TABLE "UserCompetition" (
    id UUID PRIMARY KEY, user_id UUID REFERENCES "User"(id), competition_id UUID REFERENCES "Competition"(id),
    weight_class TEXT, gender TEXT);
CREATE TABLE "Attempt" (
    id UUID PRIMARY KEY, user_competition_id UUID REFERENCES "UserCompetition"(id) ON DELETE CASCADE,
    lift_type lift_type NOT NULL, weight_kg DECIMAL(5,2) NOT NULL,
    status attempt_status NOT NULL DEFAULT 'pending', video_url TEXT,
    created_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE "LiftingResult" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    attempt_id UUID REFERENCES "Attempt"(id) ON DELETE CASCADE UNIQUE,
    processing_status TEXT NOT NULL DEFAULT 'queued', annotated_video_url TEXT, summary_url TEXT,
    report JSONB, processing_time_s DECIMAL(8,2), error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now(), updated_at TIMESTAMPTZ DEFAULT now());
"""


@pytest.fixture(scope="module")
def engine():
    url = urlparse(PG_URL.replace("+pg8000", ""))
    assert url.hostname in ("127.0.0.1", "localhost"), "AUTO_LIFT_PG_URL must be a local throwaway DB"
    assert url.port not in (None, 5432, 5433), "5433 is the Cloud SQL proxy; use a docker Postgres port"
    eng = sqlalchemy.create_engine(PG_URL, isolation_level="AUTOCOMMIT")
    with eng.connect() as c:
        assert c.execute(sqlalchemy.text("SELECT current_database()")).scalar() == url.path.lstrip("/")
        assert url.path.lstrip("/") != "postgres"
    yield sqlalchemy.create_engine(PG_URL)
    eng.dispose()


@pytest.fixture
def db(engine, monkeypatch):
    with engine.begin() as c:
        for stmt in SCHEMA.split(";"):
            if stmt.strip():
                c.execute(sqlalchemy.text(stmt))
    factory = sessionmaker(bind=engine)
    import toms_gym.db as dbmod
    monkeypatch.setattr(dbmod, "get_db_connection", lambda: factory())
    from toms_gym.routes import attempt_routes, competition_routes, lifting_routes, user_routes
    for mod in (attempt_routes, lifting_routes, competition_routes, user_routes):
        monkeypatch.setattr(mod, "get_db_connection", lambda: factory())
    return factory


def _migrate():
    from toms_gym.app import run_startup_migrations
    run_startup_migrations()


def _columns(engine):
    with engine.connect() as c:
        return {r.column_name: (r.data_type, r.column_default, r.is_nullable) for r in c.execute(sqlalchemy.text("""
            SELECT column_name, data_type, column_default, is_nullable FROM information_schema.columns
            WHERE table_name = 'Attempt' AND column_name LIKE 'lift_type_%'"""))}


def _seed(factory, lift_type="Pushup", status="completed", result_status="completed"):
    ids = SimpleNamespace(user=str(uuid.uuid4()), comp=str(uuid.uuid4()), uc=str(uuid.uuid4()),
                          attempt=str(uuid.uuid4()), result=str(uuid.uuid4()))
    s = factory()
    s.execute(sqlalchemy.text('INSERT INTO "User" (id, name, email) VALUES (:u, \'Athlete\', \'a@example.com\')'),
              {"u": ids.user})
    s.execute(sqlalchemy.text('INSERT INTO "Competition" (id, name, description) VALUES (:c, \'Club\', :d)'),
              {"c": ids.comp, "d": CLUB_DESC})
    s.execute(sqlalchemy.text('INSERT INTO "UserCompetition" (id, user_id, competition_id) VALUES (:uc, :u, :c)'),
              {"uc": ids.uc, "u": ids.user, "c": ids.comp})
    s.execute(sqlalchemy.text("""
        INSERT INTO "Attempt" (id, user_competition_id, lift_type, weight_kg, status, video_url)
        VALUES (:a, :uc, :lt, 0, :st, 'https://x/v.mp4')"""),
              {"a": ids.attempt, "uc": ids.uc, "lt": lift_type, "st": status})
    if result_status:
        s.execute(sqlalchemy.text("""
            INSERT INTO "LiftingResult" (id, attempt_id, processing_status) VALUES (:r, :a, :st)"""),
                  {"r": ids.result, "a": ids.attempt, "st": result_status})
    s.commit()
    s.close()
    return ids


def _attempt(factory, attempt_id):
    s = factory()
    row = s.execute(sqlalchemy.text("""
        SELECT a.lift_type::text AS lift_type, a.lift_type_source, a.lift_type_confidence,
               a.status::text AS status, lr.processing_status
        FROM "Attempt" a LEFT JOIN "LiftingResult" lr ON lr.attempt_id = a.id WHERE a.id = :a"""),
                    {"a": attempt_id}).fetchone()
    s.close()
    return row


def test_migration_020_adds_auto_and_both_columns_and_is_idempotent(db, engine):
    _migrate()
    _migrate()
    cols = _columns(engine)
    assert cols["lift_type_source"] == ("text", "'user'::text", "NO")
    assert cols["lift_type_confidence"][0] == "real"
    with engine.connect() as c:
        labels = [r[0] for r in c.execute(sqlalchemy.text(
            "SELECT unnest(enum_range(NULL::lift_type))::text"))]
    assert labels.count("Auto") == 1


def _hold_attempt_read_lock(engine, release):
    conn = engine.connect()
    conn.execute(sqlalchemy.text('SELECT count(*) FROM "Attempt"'))
    release.wait(30)
    conn.rollback()
    conn.close()


def _migrate_while_attempt_is_read(engine, budget_s):
    release, done = threading.Event(), threading.Event()
    holder = threading.Thread(target=_hold_attempt_read_lock, args=(engine, release))
    holder.start()
    time.sleep(0.3)
    started = time.monotonic()
    worker = threading.Thread(target=lambda: (_migrate(), done.set()))
    worker.start()
    worker.join(budget_s)
    elapsed = time.monotonic() - started
    release.set()
    holder.join()
    worker.join()
    return done.is_set() and elapsed < budget_s, elapsed


def test_reboot_does_not_wait_on_a_running_analysis(db, engine):
    _migrate()
    ok, elapsed = _migrate_while_attempt_is_read(engine, budget_s=3)
    assert ok, f"boot waited {elapsed:.1f}s behind an open Attempt read"


def test_first_migration_gives_up_instead_of_queueing_every_attempt_reader(db, engine):
    ok, elapsed = _migrate_while_attempt_is_read(engine, budget_s=15)
    assert ok, f"boot waited {elapsed:.1f}s behind an open Attempt read"
    _migrate()
    assert set(_columns(engine)) == {"lift_type_source", "lift_type_confidence"}


@pytest.fixture
def client(db, monkeypatch):
    from toms_gym.routes import attempt_routes, competition_routes, lifting_routes, user_routes
    app = Flask(__name__)
    for bp in (attempt_routes.attempt_bp, lifting_routes.lifting_bp,
               competition_routes.competition_bp, user_routes.user_bp):
        app.register_blueprint(bp)
    return app.test_client()


@pytest.fixture
def enqueued(monkeypatch):
    from toms_gym.routes import lifting_routes
    calls = []
    monkeypatch.setattr(lifting_routes, "enqueue_analysis_job", lambda kind, rid: calls.append((kind, rid)))
    return calls


def test_change_flow_writes_the_row_and_requeues_once(db, client, enqueued, monkeypatch):
    monkeypatch.setenv("AUTO_LIFT_TYPE", "1")
    _migrate()
    ids = _seed(db)
    resp = client.post(f"/attempts/{ids.attempt}/lift-type", json={"lift_type": "situp", "user_id": ids.user})
    assert resp.status_code == 200, resp.get_json()
    assert resp.get_json()["status"] == "queued"
    row = _attempt(db, ids.attempt)
    assert (row.lift_type, row.lift_type_source, row.status, row.processing_status) == \
        ("Situp", "user", "pending", "queued")
    again = client.post(f"/attempts/{ids.attempt}/lift-type", json={"lift_type": "Plank", "user_id": ids.user})
    assert again.status_code == 409
    assert _attempt(db, ids.attempt).lift_type == "Situp"
    assert enqueued == [("lifting", ids.result)]


def test_change_is_refused_with_the_switch_off(db, client, enqueued, monkeypatch):
    monkeypatch.delenv("AUTO_LIFT_TYPE", raising=False)
    _migrate()
    ids = _seed(db)
    resp = client.post(f"/attempts/{ids.attempt}/lift-type", json={"lift_type": "Situp", "user_id": ids.user})
    assert resp.status_code == 400
    assert _attempt(db, ids.attempt).lift_type == "Pushup"
    assert enqueued == []


def test_completion_writes_the_detected_type_onto_an_auto_attempt(db, monkeypatch):
    from toms_gym.integrations import lifting_processor
    import toms_gym.integrations.analysis_notify as notify
    _migrate()
    ids = _seed(db, lift_type="Auto", status="pending", result_status="queued")
    body = {"annotated_video_url": "a", "summary_url": "s", "processing_time_s": 1.0,
            "report": {"lift_type": "pushup", "detected_lift_type": "pushup", "lift_type_confidence": 0.82,
                       "total_reps": 12}}
    monkeypatch.setattr(lifting_processor, "_get_id_token", lambda: "tok")
    monkeypatch.setattr(lifting_processor.requests, "post",
                        lambda *a, **k: SimpleNamespace(status_code=200, json=lambda: body, text=""))
    monkeypatch.setattr(notify, "notify_analysis_complete", lambda *a, **k: None)
    lifting_processor._process_job(db, ids.result, ids.attempt, "https://x/v.mp4", "Auto")
    row = _attempt(db, ids.attempt)
    assert (row.lift_type, row.lift_type_source, row.status, row.processing_status) == \
        ("Pushup", "auto", "completed", "completed")
    assert row.lift_type_confidence == pytest.approx(0.82)


def test_profile_never_counts_an_undetected_auto_attempt(db, client):
    _migrate()
    ids = _seed(db, lift_type="Auto", status="completed")
    body = client.get(f"/users/{ids.user}/profile").get_json()
    comps = body.get("competitions") or body.get("competition_history") or []
    assert comps and all(c["successful_lifts"] == 0 for c in comps), body
    assert [b for b in body.get("best_lifts", []) if b.get("type") == "Auto"] == []
