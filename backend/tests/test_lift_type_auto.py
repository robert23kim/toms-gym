"""Automatic lift type (docs/plans/2026-11-13-auto-lift-type.md), DB-free.

Upload accepts/rejects Auto, dispatch sends auto + candidates, completion writes
the detected type, an Auto attempt scores nothing and is pending, and
POST /attempts/<id>/lift-type re-queues through the shared /analyze code path.
"""
import pathlib
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from flask import Flask

from toms_gym.integrations import lifting_processor
from toms_gym.routes import attempt_routes, competition_routes, lifting_routes, upload_routes
from toms_gym.services import lift_type_auto
from toms_gym.services.consistency import rank_consistency
from toms_gym.services.challenge_leaderboard import rank_challenge
from toms_gym.services.lift_history import shape_lift_row

USER_ID = "11111111-1111-4111-8111-111111111111"
OTHER_ID = "44444444-4444-4444-8444-444444444444"
COMP_ID = "55555555-5555-4555-8555-555555555555"
UC_ID = "22222222-2222-4222-8222-222222222222"
ATTEMPT_ID = "33333333-3333-4333-8333-333333333333"
RESULT_ID = "66666666-6666-4666-8666-666666666666"

CLUB_DESC = ('Gym - {"lifttypes": ["Situp", "Pushup", "Squat", "Plank"], '
             '"weightclasses": [], "gender": "", "mode": "consistency", '
             '"rules": {"week_start": "2026-11-02"}}')
BODYWEIGHT_DESC = 'Gym - {"lifttypes": ["Pushup", "Plank"], "weightclasses": [], "gender": ""}'
WEIGHTED_DESC = 'Gym - {"lifttypes": ["Squat", "Deadlift"], "weightclasses": [], "gender": ""}'
SQUAT_NO_MODE_DESC = 'Gym - {"lifttypes": ["Squat", "Pushup"], "weightclasses": [], "gender": ""}'
SINGLE_DESC = 'Gym - {"lifttypes": ["Pushup"], "weightclasses": [], "gender": ""}'


@pytest.fixture(autouse=True)
def fresh_champions_cache():
    competition_routes._champions_cache.update(at=0.0, data=None)
    yield
    competition_routes._champions_cache.update(at=0.0, data=None)


@pytest.fixture
def client():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(upload_routes.upload_bp)
    app.register_blueprint(attempt_routes.attempt_bp)
    app.register_blueprint(lifting_routes.lifting_bp)
    app.register_blueprint(competition_routes.competition_bp)
    return app.test_client()


def _dispatch_session(handlers):
    """MagicMock session whose execute() answers by the first matching SQL marker."""
    session = MagicMock()

    def execute(statement, params=None):
        sql = str(statement)
        result = MagicMock()
        result.rowcount = 1
        for marker, configure in handlers:
            if marker in sql:
                configure(result)
                break
        return result

    session.execute.side_effect = execute
    return session


def _writes(session, marker):
    return [c.args[1] for c in session.execute.call_args_list
            if marker in str(c.args[0]) and len(c.args) > 1]


def _sqls(session, marker=""):
    return [str(c.args[0]) for c in session.execute.call_args_list if marker in str(c.args[0])]


# --------------------------------------------------------------------------- #
# Upload paths
# --------------------------------------------------------------------------- #

def _upload_session(description):
    def comp(r):
        r.fetchone.return_value = (description,)

    def uc(r):
        r.fetchone.return_value = (UC_ID,)

    def inserted(r):
        r.fetchone.return_value = (ATTEMPT_ID,)
    return _dispatch_session([('FROM "Competition"', comp), ('FROM "UserCompetition"', uc),
                              ('INSERT INTO "Attempt"', inserted)])


@pytest.fixture
def bucket(monkeypatch):
    b = MagicMock()
    b.name = "test-bucket"
    b.blob.return_value.exists.return_value = True
    monkeypatch.setattr(upload_routes, "bucket", b)
    return b


def _use(monkeypatch, session):
    for mod in (upload_routes, attempt_routes, lifting_routes, competition_routes):
        monkeypatch.setattr(mod, "get_db_connection", lambda: session)


def _finalize(client, lift_type="Auto", weight="60"):
    return client.post("/upload/finalize", json={
        "object_name": "videos/x.mp4",
        "public_url": "https://storage.googleapis.com/test-bucket/videos/x.mp4",
        "competition_id": COMP_ID, "user_id": USER_ID,
        "lift_type": lift_type, "weight": weight,
    })


def _multipart(client, lift_type="Auto", weight="60"):
    return client.post("/upload", data={
        "video": (BytesIO(b"bytes"), "lift.mp4"),
        "competition_id": COMP_ID, "user_id": USER_ID,
        "lift_type": lift_type, "weight": weight,
    }, content_type="multipart/form-data")


def _create_attempt(client, lift_type="Auto"):
    return client.post("/attempts", json={
        "user_competition_id": UC_ID, "lift_type": lift_type,
        "weight_kg": 60, "video_url": "https://x/v.mp4",
    })


@pytest.mark.parametrize("post", [_finalize, _multipart, _create_attempt])
@pytest.mark.parametrize("raw", ["Auto", "auto"])
def test_auto_upload_lands_as_auto_with_zero_weight_when_switch_on(
        client, bucket, monkeypatch, post, raw):
    monkeypatch.setenv("AUTO_LIFT_TYPE", "1")
    session = _upload_session(CLUB_DESC)
    _use(monkeypatch, session)
    resp = post(client, raw)
    assert resp.status_code in (200, 201), resp.get_json()
    rows = _writes(session, 'INSERT INTO "Attempt"')
    assert len(rows) == 1
    assert rows[0]["lift_type"] == "Auto"
    assert rows[0]["weight_kg"] == 0


@pytest.mark.parametrize("post", [_finalize, _multipart, _create_attempt])
def test_auto_upload_is_400_when_switch_off(client, bucket, monkeypatch, post):
    monkeypatch.delenv("AUTO_LIFT_TYPE", raising=False)
    session = _upload_session(CLUB_DESC)
    _use(monkeypatch, session)
    resp = post(client)
    assert resp.status_code == 400
    assert "lift type" in resp.get_json()["error"].lower()
    assert _writes(session, 'INSERT INTO "Attempt"') == []
    bucket.blob.return_value.upload_from_string.assert_not_called()


@pytest.mark.parametrize("desc", [WEIGHTED_DESC, SQUAT_NO_MODE_DESC])
@pytest.mark.parametrize("post", [_finalize, _multipart, _create_attempt])
def test_auto_upload_is_400_on_a_weighted_challenge(client, bucket, monkeypatch, post, desc):
    monkeypatch.setenv("AUTO_LIFT_TYPE", "1")
    session = _upload_session(desc)
    _use(monkeypatch, session)
    resp = post(client)
    assert resp.status_code == 400
    assert "bodyweight" in resp.get_json()["error"].lower()
    assert _writes(session, 'INSERT INTO "Attempt"') == []


def test_auto_upload_accepted_on_a_plain_bodyweight_challenge(client, bucket, monkeypatch):
    monkeypatch.setenv("AUTO_LIFT_TYPE", "1")
    session = _upload_session(BODYWEIGHT_DESC)
    _use(monkeypatch, session)
    assert _finalize(client).status_code == 200


@pytest.mark.parametrize("post", [_finalize, _multipart])
def test_manual_upload_never_reads_the_competition(client, bucket, monkeypatch, post):
    monkeypatch.delenv("AUTO_LIFT_TYPE", raising=False)
    session = _upload_session(CLUB_DESC)
    _use(monkeypatch, session)
    resp = post(client, "Pushup", "60")
    assert resp.status_code == 200
    assert _writes(session, 'INSERT INTO "Attempt"')[0]["lift_type"] == "Pushup"
    assert _sqls(session, 'FROM "Competition"') == []


def test_put_attempt_rejects_auto(client, monkeypatch):
    monkeypatch.setenv("AUTO_LIFT_TYPE", "1")
    session = _upload_session(CLUB_DESC)
    _use(monkeypatch, session)
    resp = client.put(f"/attempts/{ATTEMPT_ID}", json={
        "lift_type": "Auto", "weight_kg": 0, "status": "pending", "video_url": "v"})
    assert resp.status_code == 400
    assert _writes(session, 'UPDATE "Attempt"') == []


def test_auto_is_not_mapped_to_snatch():
    assert upload_routes.map_lift_type("Auto") == "Auto"
    assert upload_routes.map_lift_type("auto") == "Auto"
    assert upload_routes.bodyweight_weight_kg("Auto", 60) == 0


# --------------------------------------------------------------------------- #
# Switch and eligibility
# --------------------------------------------------------------------------- #

def test_switch_defaults_off(monkeypatch):
    monkeypatch.delenv("AUTO_LIFT_TYPE", raising=False)
    assert lift_type_auto.switch_on() is False
    monkeypatch.setenv("AUTO_LIFT_TYPE", "0")
    assert lift_type_auto.switch_on() is False
    monkeypatch.setenv("AUTO_LIFT_TYPE", "1")
    assert lift_type_auto.switch_on() is True


def test_deploy_py_commits_the_switch_off():
    text = (pathlib.Path(__file__).resolve().parents[2] / "deploy.py").read_text()
    assert '"AUTO_LIFT_TYPE=0"' in text
    assert "AUTO_LIFT_TYPE=1" not in text


def _comp_by_id(client, monkeypatch, description):
    row = MagicMock()
    row._mapping = {"id": COMP_ID, "name": "Club", "description": description}
    session = MagicMock()
    session.execute.return_value.fetchone.return_value = row
    monkeypatch.setattr(competition_routes, "get_db_connection", lambda: session)
    resp = client.get(f"/competitions/{COMP_ID}")
    assert resp.status_code == 200
    return resp.get_json()["competition"]


@pytest.mark.parametrize("env, desc, expected", [
    ("1", CLUB_DESC, True),
    ("1", BODYWEIGHT_DESC, True),
    ("0", CLUB_DESC, False),
    (None, CLUB_DESC, False),
    ("1", WEIGHTED_DESC, False),
    ("1", SQUAT_NO_MODE_DESC, False),
    ("1", "Just a gym", False),
    ("1", SINGLE_DESC, False),
])
def test_competition_detail_reports_auto_lift_type_enabled(client, monkeypatch, env, desc, expected):
    if env is None:
        monkeypatch.delenv("AUTO_LIFT_TYPE", raising=False)
    else:
        monkeypatch.setenv("AUTO_LIFT_TYPE", env)
    comp = _comp_by_id(client, monkeypatch, desc)
    assert comp["auto_lift_type_enabled"] is expected


# --------------------------------------------------------------------------- #
# Dispatch and completion (lifting_processor._process_job)
# --------------------------------------------------------------------------- #

class _Engine:
    def __init__(self, body):
        self.body = body
        self.calls = []

    def __call__(self, url, json=None, headers=None, timeout=None):
        self.calls.append(json)
        return SimpleNamespace(status_code=200, json=lambda: self.body, text="")


def _job_session(description=CLUB_DESC):
    def comp(r):
        r.fetchone.return_value = (description,)

    def created(r):
        r.scalar.return_value = None
    return _dispatch_session([('JOIN "Competition"', comp), ("SELECT created_at", created)])


def _run_job(monkeypatch, lift_type, engine_body, description=CLUB_DESC):
    session = _job_session(description)
    engine = _Engine(engine_body)
    monkeypatch.setattr(lifting_processor, "_get_id_token", lambda: "tok")
    monkeypatch.setattr(lifting_processor.requests, "post", engine)
    import toms_gym.integrations.analysis_notify as notify
    monkeypatch.setattr(notify, "notify_analysis_complete", lambda *a, **k: None)
    lifting_processor._process_job(lambda: session, RESULT_ID, ATTEMPT_ID, "https://x/v.mp4", lift_type)
    return session, engine


def _report(**kw):
    return {"annotated_video_url": "a", "summary_url": "s", "processing_time_s": 1.0,
            "report": {"total_reps": 20, **kw}}


def test_dispatch_sends_auto_and_the_competition_candidates(monkeypatch):
    _, engine = _run_job(monkeypatch, "Auto", _report())
    assert engine.calls[0]["lift_type"] == "auto"
    assert engine.calls[0]["candidates"] == ["situp", "pushup", "squat", "plank"]


def test_explicit_lift_type_payload_is_unchanged(monkeypatch):
    competition_routes._champions_cache.update(at=1e12, data=[{"stale": True}])
    session, engine = _run_job(monkeypatch, "Pushup", _report())
    assert competition_routes._champions_cache["data"] is None
    assert engine.calls[0] == {"video_url": "https://x/v.mp4", "attempt_id": ATTEMPT_ID,
                               "lift_type": "pushup"}
    assert _sqls(session, 'JOIN "Competition"') == []
    assert _writes(session, "lift_type_source") == []


def test_completion_writes_detected_type_source_and_confidence(monkeypatch):
    competition_routes._champions_cache.update(at=1e12, data=[{"stale": True}])
    session, _ = _run_job(monkeypatch, "Auto", _report(
        detected_lift_type="pushup", lift_type_confidence=0.83,
        lift_type_scores={"pushup": 0.83, "plank": 0.1}))
    updates = [(s, p) for s, p in zip(_sqls(session, 'UPDATE "Attempt"'),
                                      _writes(session, 'UPDATE "Attempt"'))
               if "lift_type_source" in s]
    assert len(updates) == 1
    sql, params = updates[0]
    assert "lift_type = 'Auto'" in sql
    assert params["lift_type"] == "Pushup"
    assert params["confidence"] == pytest.approx(0.83)
    assert "'auto'" in sql
    assert competition_routes._champions_cache["data"] is None


def test_completion_reads_top_level_detection_too(monkeypatch):
    body = _report()
    body.update(detected_lift_type="situp", lift_type_confidence=0.7)
    session, _ = _run_job(monkeypatch, "Auto", body)
    params = [p for s, p in zip(_sqls(session, 'UPDATE "Attempt"'), _writes(session, 'UPDATE "Attempt"'))
              if "lift_type_source" in s]
    assert params[0]["lift_type"] == "Situp"


@pytest.mark.parametrize("detected", [None, "bicep_curl", "auto"])
def test_completion_without_a_usable_detection_leaves_auto(monkeypatch, detected):
    session, _ = _run_job(monkeypatch, "Auto", _report(
        detected_lift_type=detected, lift_type_confidence=0.2))
    attempt_updates = _sqls(session, 'UPDATE "Attempt"')
    assert attempt_updates and all("lift_type" not in s for s in attempt_updates)
    lr = _sqls(session, 'UPDATE "LiftingResult"')
    assert any("completed" in s for s in lr)


# --------------------------------------------------------------------------- #
# Scoring invariant
# --------------------------------------------------------------------------- #

RULES = {"week_start": "2026-11-02"}
NOW = "2026-11-05T12:00:00+00:00"


def _attempt(lift_type, status="completed", reps=None, held_s=None, created="2026-11-03T17:00:00+00:00",
             weight_kg=0.0, attempt_id="a1"):
    return {"attempt_id": attempt_id, "lift_type": lift_type, "status": status, "reps": reps,
            "held_s": held_s, "created_at": created, "weight_kg": weight_kg,
            "form_score": None, "rep_form_scores": None, "video_url": "v",
            "annotated_video_url": None, "steadiness": None}


@pytest.mark.parametrize("status", ["pending", "completed"])
def test_auto_attempt_scores_nothing_and_is_pending(status):
    from toms_gym.services.consistency import to_utc
    p = {"user_id": "u1", "name": "alice",
         "attempts": [_attempt("Auto", status=status, reps=40)]}
    rows, block = rank_consistency([p], RULES, to_utc(NOW),
                                   lift_types=["Situp", "Pushup", "Squat", "Plank"])
    r = rows[0]
    assert r["score"] == 0
    assert r["this_week"]["lifts"] == 0
    assert r["this_week"]["pending"] == 1
    assert r["attempt_count"] == 0
    assert r["history"] == []
    assert block["type_leaders"] == {}


def test_auto_warmup_attempt_adds_nothing():
    from toms_gym.services.consistency import to_utc
    p = {"user_id": "u1", "name": "alice",
         "attempts": [_attempt("Auto", reps=40, created="2026-10-31T17:00:00+00:00")]}
    rows, _ = rank_consistency([p], RULES, to_utc(NOW))
    assert rows[0]["warmup_lifts"] == 0


@pytest.mark.parametrize("metric", ["weight", "reps", "time"])
def test_auto_attempt_is_not_counted_on_other_boards(metric):
    p = {"user_id": "u1", "name": "alice",
         "attempts": [_attempt("Auto", reps=40, held_s=60)]}
    row = rank_challenge([p], metric=metric)[0]
    assert row["score"] == 0
    assert row["attempt_count"] == 0
    assert row["best_by_lift"] == {}


def test_lift_history_never_shows_the_engine_auto_label():
    row = {"attempt_id": "a1", "lift_type": "Pushup", "report_lift_type": "auto"}
    assert shape_lift_row(row)["lift_type"] == "Pushup"
    assert shape_lift_row({"lift_type": "Auto"})["lift_type"] == "Auto"
    assert shape_lift_row({"lift_type": "Pushup", "report_lift_type": "pushup"})["lift_type"] == "pushup"


def test_lift_history_auto_attempt_counts_nothing_whatever_the_report_says():
    row = shape_lift_row({"lift_type": "Auto", "report_lift_type": "pushup",
                          "total_reps": "12", "hold_s": "30"})
    assert row["lift_type"] == "Auto"
    assert row["total_reps"] is None
    assert row["hold_s"] is None
    kept = shape_lift_row({"lift_type": "Pushup", "total_reps": "12"})
    assert kept["total_reps"] == 12


# --------------------------------------------------------------------------- #
# Result / attempt payloads
# --------------------------------------------------------------------------- #

def _lr_row(**kw):
    import datetime as dt
    base = dict(id=RESULT_ID, attempt_id=ATTEMPT_ID, processing_status="completed",
                annotated_video_url="a", summary_url=None, report={"total_reps": 3},
                processing_time_s=1.0, error_message=None,
                created_at=dt.datetime(2026, 11, 13), updated_at=dt.datetime(2026, 11, 13),
                attempt_created_at=dt.datetime(2026, 11, 13), user_id=USER_ID,
                competition_id=COMP_ID, lift_type="Pushup", lift_type_source="auto",
                lift_type_confidence=0.83)
    base.update(kw)
    return SimpleNamespace(**base)


@pytest.mark.parametrize("row_kw, needs", [
    ({}, False),
    ({"lift_type": "Auto", "lift_type_source": "user", "lift_type_confidence": None}, True),
    ({"lift_type": "Auto", "processing_status": "processing"}, False),
    ({"lift_type": "Auto", "processing_status": "failed"}, True),
])
def test_lifting_result_carries_lift_type_fields(client, monkeypatch, row_kw, needs):
    session = MagicMock()
    session.execute.return_value.fetchone.return_value = _lr_row(**row_kw)
    monkeypatch.setattr(lifting_routes, "get_db_connection", lambda: session)
    body = client.get(f"/lifting/result/{ATTEMPT_ID}").get_json()
    row = _lr_row(**row_kw)
    assert body["lift_type"] == row.lift_type
    assert body["lift_type_source"] == row.lift_type_source
    assert body["lift_type_confidence"] == row.lift_type_confidence
    assert body["needs_lift_type"] is needs


def _detail_row(**kw):
    base = {"id": ATTEMPT_ID, "participant_id": USER_ID, "competition_id": COMP_ID,
            "participant_name": "alice", "lift_type": "Auto", "weight": 0, "status": "completed",
            "video_url": "https://x/v.mp4", "lift_type_source": "user",
            "lift_type_confidence": None, "analysis_status": None}
    base.update(kw)
    row = MagicMock()
    row._mapping = base
    return row


@pytest.mark.parametrize("row_kw, needs", [
    ({}, True),
    ({"analysis_status": "queued"}, False),
    ({"lift_type": "Situp", "lift_type_source": "auto", "lift_type_confidence": 0.5,
      "analysis_status": "completed"}, False),
])
def test_attempt_details_carry_lift_type_fields(client, monkeypatch, row_kw, needs):
    session = MagicMock()
    session.execute.return_value.fetchone.return_value = _detail_row(**row_kw)
    monkeypatch.setattr(competition_routes, "get_db_connection", lambda: session)
    body = client.get(f"/competitions/{COMP_ID}/participants/{USER_ID}/attempts/{ATTEMPT_ID}").get_json()
    expected = {**_detail_row()._mapping, **row_kw}
    assert body["lift_type_source"] == expected["lift_type_source"]
    assert body["lift_type_confidence"] == expected["lift_type_confidence"]
    assert body["needs_lift_type"] is needs
    assert "analysis_status" not in body
    assert 'LEFT JOIN "LiftingResult"' in str(session.execute.call_args[0][0])


# --------------------------------------------------------------------------- #
# POST /attempts/<id>/lift-type
# --------------------------------------------------------------------------- #

def _owner_row(**kw):
    base = dict(id=ATTEMPT_ID, lift_type="Pushup", weight_kg=0, video_url="https://x/v.mp4",
                user_id=USER_ID, competition_id=COMP_ID, description=CLUB_DESC,
                processing_status="completed")
    base.update(kw)
    return SimpleNamespace(**base)


def _change_session(row, lr=None):
    """lr: the (id, processing_status) the shared re-queue helper sees."""
    if lr is None and row is not None and row.processing_status is not None:
        lr = SimpleNamespace(id=RESULT_ID, processing_status=row.processing_status)

    def lookup(r):
        r.fetchone.return_value = row

    def existing(r):
        r.fetchone.return_value = lr
    return _dispatch_session([('JOIN "Competition"', lookup),
                              ('SELECT id, processing_status FROM "LiftingResult"', existing)])


@pytest.fixture
def enqueued(monkeypatch):
    calls = []
    monkeypatch.setattr(lifting_routes, "enqueue_analysis_job", lambda kind, rid: calls.append((kind, rid)))
    return calls


def _change(client, monkeypatch, session, lift_type="Situp", user_id=USER_ID, attempt_id=ATTEMPT_ID,
            switch="1"):
    if switch is None:
        monkeypatch.delenv("AUTO_LIFT_TYPE", raising=False)
    else:
        monkeypatch.setenv("AUTO_LIFT_TYPE", switch)
    _use(monkeypatch, session)
    body = {"lift_type": lift_type}
    if user_id is not None:
        body["user_id"] = user_id
    return client.post(f"/attempts/{attempt_id}/lift-type", json=body)


def test_change_404_on_unknown_attempt(client, monkeypatch, enqueued):
    assert _change(client, monkeypatch, _change_session(None)).status_code == 404
    session = _change_session(_owner_row())
    assert _change(client, monkeypatch, session, attempt_id="not-a-uuid").status_code == 404
    session.execute.assert_not_called()
    assert enqueued == []


@pytest.mark.parametrize("user_id", [OTHER_ID, None, ""])
def test_change_403_unless_owner(client, monkeypatch, enqueued, user_id):
    session = _change_session(_owner_row())
    resp = _change(client, monkeypatch, session, user_id=user_id)
    assert resp.status_code == 403
    assert _writes(session, 'UPDATE "Attempt"') == []
    assert enqueued == []


@pytest.mark.parametrize("lift_type", ["Deadlift", "Auto", "auto", "", None, "Bowling"])
def test_change_400_unless_a_competition_lift_type(client, monkeypatch, enqueued, lift_type):
    session = _change_session(_owner_row())
    resp = _change(client, monkeypatch, session, lift_type=lift_type)
    assert resp.status_code == 400
    assert _writes(session, 'UPDATE "Attempt"') == []
    assert enqueued == []


@pytest.mark.parametrize("status", ["queued", "processing"])
def test_change_409_while_analysis_runs(client, monkeypatch, enqueued, status):
    session = _change_session(_owner_row(processing_status=status))
    resp = _change(client, monkeypatch, session)
    assert resp.status_code == 409
    assert _writes(session, 'UPDATE "Attempt"') == []
    assert enqueued == []


@pytest.mark.parametrize("switch", [None, "0"])
def test_change_400_when_the_switch_is_off(client, monkeypatch, enqueued, switch):
    session = _change_session(_owner_row())
    resp = _change(client, monkeypatch, session, switch=switch)
    assert resp.status_code == 400
    assert "not available" in resp.get_json()["error"]
    assert _writes(session, 'UPDATE "Attempt"') == []
    assert _sqls(session, 'UPDATE "LiftingResult"') == []
    assert enqueued == []


@pytest.mark.parametrize("desc, target", [(WEIGHTED_DESC, "Squat"), (SQUAT_NO_MODE_DESC, "Squat"),
                                          (SINGLE_DESC, "Pushup")])
def test_change_400_on_a_board_without_automatic(client, monkeypatch, enqueued, desc, target):
    session = _change_session(_owner_row(lift_type="Deadlift" if desc == WEIGHTED_DESC else "Pushup",
                                         description=desc, processing_status="failed"))
    resp = _change(client, monkeypatch, session, lift_type=target)
    assert resp.status_code == 400
    assert _writes(session, 'UPDATE "Attempt"') == []
    assert enqueued == []


def test_change_409_when_the_shared_helper_finds_analysis_running(client, monkeypatch, enqueued):
    session = _change_session(_owner_row(processing_status="completed"),
                              lr=SimpleNamespace(id=RESULT_ID, processing_status="processing"))
    resp = _change(client, monkeypatch, session, lift_type="Situp")
    assert resp.status_code == 409
    assert enqueued == []
    session.rollback.assert_called()
    session.commit.assert_not_called()


def test_change_same_type_completed_is_unchanged_and_not_requeued(client, monkeypatch, enqueued):
    session = _change_session(_owner_row(lift_type="Pushup"))
    resp = _change(client, monkeypatch, session, lift_type="pushup")
    assert resp.status_code == 200
    assert resp.get_json() == {"attempt_id": ATTEMPT_ID, "lift_type": "Pushup", "status": "unchanged"}
    sqls = _sqls(session, 'UPDATE "Attempt"')
    assert len(sqls) == 1 and "lift_type_source = 'user'" in sqls[0]
    assert "lift_type_confidence = NULL" in sqls[0]
    assert _sqls(session, 'UPDATE "LiftingResult"') == []
    assert _sqls(session, 'INSERT INTO "LiftingResult"') == []
    assert enqueued == []
    session.commit.assert_called()


def test_change_requeues_through_the_shared_analyze_path(client, monkeypatch, enqueued):
    competition_routes._champions_cache.update(at=1e12, data=[{"stale": True}])
    session = _change_session(_owner_row(lift_type="Pushup", weight_kg=60))
    resp = _change(client, monkeypatch, session, lift_type="Situp")
    assert resp.status_code == 200, resp.get_json()
    assert resp.get_json() == {"attempt_id": ATTEMPT_ID, "lift_type": "Situp", "status": "queued"}

    (sql,) = _sqls(session, 'UPDATE "Attempt"')
    (params,) = _writes(session, 'UPDATE "Attempt"')
    assert "lift_type_source = 'user'" in sql and "lift_type_confidence = NULL" in sql
    assert params["lift_type"] == "Situp"
    assert params["weight_kg"] == 0
    assert params["status"] == "pending"

    (reset,) = _sqls(session, 'UPDATE "LiftingResult"')
    assert "processing_status = 'queued'" in reset and "report = NULL" in reset
    assert enqueued == [("lifting", RESULT_ID)]
    assert competition_routes._champions_cache["data"] is None
    session.commit.assert_called()


def test_change_from_auto_creates_a_result_when_none_exists(client, monkeypatch, enqueued):
    session = _change_session(_owner_row(lift_type="Auto", processing_status=None), lr=None)
    resp = _change(client, monkeypatch, session, lift_type="Plank")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "queued"
    assert len(_sqls(session, 'INSERT INTO "LiftingResult"')) == 1
    assert len(enqueued) == 1


def test_change_same_type_after_failed_analysis_requeues(client, monkeypatch, enqueued):
    session = _change_session(_owner_row(lift_type="Situp", processing_status="failed"))
    resp = _change(client, monkeypatch, session, lift_type="Situp")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "queued"
    assert enqueued == [("lifting", RESULT_ID)]


def test_analyze_route_still_uses_the_same_helper(client, monkeypatch, enqueued):
    session = _dispatch_session([
        ('FROM "Attempt" WHERE id', lambda r: setattr(r.fetchone, "return_value",
                                                      SimpleNamespace(id=ATTEMPT_ID, video_url="v"))),
        ('SELECT id, processing_status FROM "LiftingResult"',
         lambda r: setattr(r.fetchone, "return_value",
                           SimpleNamespace(id=RESULT_ID, processing_status="completed"))),
    ])
    _use(monkeypatch, session)
    resp = client.post(f"/lifting/analyze/{ATTEMPT_ID}")
    assert resp.status_code == 200
    assert resp.get_json() == {"lifting_result_id": RESULT_ID, "status": "queued",
                               "message": "Re-queued for analysis"}
    assert enqueued == [("lifting", RESULT_ID)]
    assert len(_sqls(session, 'UPDATE "LiftingResult"')) == 1


# --------------------------------------------------------------------------- #
# Migration 020
# --------------------------------------------------------------------------- #

def test_migration_020_is_additive_and_isolated(monkeypatch):
    import toms_gym.db as db
    from toms_gym.app import run_startup_migrations
    session = MagicMock()
    monkeypatch.setattr(db, "get_db_connection", lambda: session)
    run_startup_migrations()
    calls = [str(c.args[0]) for c in session.execute.call_args_list]
    enum = [s for s in calls if "ADD VALUE IF NOT EXISTS 'Auto'" in s]
    cols = [s for s in calls if "lift_type_source" in s]
    assert len(enum) == 1 and "ALTER TYPE lift_type" in enum[0]
    assert len(cols) == 1
    assert "ADD COLUMN IF NOT EXISTS lift_type_source TEXT NOT NULL DEFAULT 'user'" in cols[0]
    assert "ADD COLUMN IF NOT EXISTS lift_type_confidence REAL" in cols[0]
    assert "lift_type_source" not in enum[0]


# --------------------------------------------------------------------------- #
# Profile aggregates never count Auto as a lift type
# --------------------------------------------------------------------------- #

def test_profile_aggregates_exclude_auto(monkeypatch):
    from toms_gym.routes import user_routes
    app = Flask(__name__)
    app.register_blueprint(user_routes.user_bp)
    session = MagicMock()
    session.execute.return_value.fetchone.return_value = SimpleNamespace(_mapping={"id": USER_ID})
    session.execute.return_value.fetchall.return_value = []
    monkeypatch.setattr(user_routes, "get_db_connection", lambda: session)
    app.test_client().get(f"/users/{USER_ID}/profile")
    sqls = [str(c.args[0]) for c in session.execute.call_args_list]
    successful = [s for s in sqls if "successful_lifts" in s]
    best = [s for s in sqls if "best_weight" in s]
    assert successful and "a.lift_type <> 'Auto'" in successful[0]
    assert best and "a.lift_type <> 'Auto'" in best[0]
