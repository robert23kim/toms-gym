"""Cloud Tasks push handlers: auth, status transitions, retry semantics."""
import pytest
from flask import Flask

import toms_gym.routes.jobs_routes as jobs_routes


class FakeRow:
    def __init__(self, status="queued"):
        self.id = "r-1"
        self.attempt_id = "a-1"
        self.processing_status = status
        self.video_url = "https://storage.googleapis.com/b/v.mp4"
        self.lift_type = "Plank"


class FakeSession:
    def __init__(self, row, final_status="completed"):
        self._row = row
        self._final_status = final_status
        self.executed = []
    def execute(self, stmt, params=None):
        self.executed.append((str(stmt), params))
        outer = self
        class R:
            def fetchone(self):
                return outer._row
            def scalar(self):
                return outer._final_status
        return R()
    def commit(self):
        pass
    def rollback(self):
        pass
    def close(self):
        pass


@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(jobs_routes.jobs_bp)
    app.config["TESTING"] = True
    return app


def _allow_auth(monkeypatch):
    monkeypatch.setattr(jobs_routes, "_verify_oidc", lambda req: True)


def test_rejects_unauthenticated(app):
    resp = app.test_client().post("/jobs/lifting/r-1")
    assert resp.status_code == 403


def test_completed_job_returns_200(app, monkeypatch):
    _allow_auth(monkeypatch)
    session = FakeSession(FakeRow(), final_status="completed")
    monkeypatch.setattr("toms_gym.db.get_db_connection", lambda: session)
    calls = []
    monkeypatch.setattr("toms_gym.integrations.lifting_processor._process_job",
                        lambda *a, **k: calls.append(a))
    resp = app.test_client().post("/jobs/lifting/r-1")
    assert resp.status_code == 200
    assert len(calls) == 1


def test_failed_job_returns_500_for_retry(app, monkeypatch):
    _allow_auth(monkeypatch)
    session = FakeSession(FakeRow(), final_status="failed")
    monkeypatch.setattr("toms_gym.db.get_db_connection", lambda: session)
    monkeypatch.setattr("toms_gym.integrations.lifting_processor._process_job",
                        lambda *a, **k: None)
    resp = app.test_client().post("/jobs/lifting/r-1")
    assert resp.status_code == 500


def test_missing_row_returns_200_no_retry(app, monkeypatch):
    _allow_auth(monkeypatch)
    session = FakeSession(None)
    monkeypatch.setattr("toms_gym.db.get_db_connection", lambda: session)
    resp = app.test_client().post("/jobs/lifting/r-gone")
    assert resp.status_code == 200
