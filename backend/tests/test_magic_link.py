"""DB-free unit tests for passwordless magic-link sign-in (T15).

Runs under run_ci_tests.sh with --noconftest (no live DB). The pure token
logic is tested directly; the route is exercised against a minimal Flask app
with all DB + SMTP helpers patched, so the no-enumeration guarantee is checked
without a database.
"""

from datetime import timedelta
from unittest import mock

import pytest
from flask import Flask

from toms_gym.services import magic_link as ml
from toms_gym.routes import auth_routes


# --------------------------------------------------------------------------- #
# Pure token logic: expiry + single-use
# --------------------------------------------------------------------------- #

def test_token_usable_when_unused_and_unexpired():
    now = ml.now_utc()
    assert ml.is_token_usable(None, now + timedelta(minutes=5), now) is True


def test_token_dead_after_expiry():
    now = ml.now_utc()
    assert ml.is_token_usable(None, now - timedelta(seconds=1), now) is False


def test_token_dead_exactly_at_expiry_boundary():
    now = ml.now_utc()
    # expires_at == now is not strictly greater than now -> expired.
    assert ml.is_token_usable(None, now, now) is False


def test_token_single_use_dead_once_used():
    now = ml.now_utc()
    # Even a still-unexpired token is dead the moment used_at is set.
    assert ml.is_token_usable(now, now + timedelta(minutes=10), now) is False


def test_compute_expiry_is_15_minutes():
    now = ml.now_utc()
    assert ml.compute_expiry(now) - now == timedelta(minutes=ml.MAGIC_LINK_TTL_MINUTES)
    assert ml.MAGIC_LINK_TTL_MINUTES == 15


def test_hash_is_stable_and_hides_raw_token():
    raw = ml.generate_raw_token()
    assert ml.hash_token(raw) == ml.hash_token(raw)
    assert raw not in ml.hash_token(raw)
    assert len(ml.hash_token(raw)) == 64  # sha256 hex


def test_generated_tokens_are_unique():
    assert ml.generate_raw_token() != ml.generate_raw_token()


# --------------------------------------------------------------------------- #
# Rate-limit predicate
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("count,expected", [
    (0, False),
    (2, False),
    (3, True),
    (10, True),
])
def test_is_rate_limited(count, expected):
    assert ml.is_rate_limited(count) is expected
    assert ml.MAGIC_LINK_MAX_PER_WINDOW == 3


# --------------------------------------------------------------------------- #
# Route: no email enumeration
# --------------------------------------------------------------------------- #

def _app():
    app = Flask(__name__)
    app.config['TESTING'] = True  # bypasses the rate_limit decorator's IP check
    app.config['JWT_SECRET_KEY'] = 'test-secret'
    app.register_blueprint(auth_routes.auth_bp, url_prefix='/auth')
    return app


def _post_magic_link(client, email):
    return client.post('/auth/magic-link', json={"email": email})


def test_magic_link_response_identical_for_existing_and_missing_email():
    app = _app()
    client = app.test_client()

    existing = {
        "id": "11111111-1111-1111-1111-111111111111",
        "name": "Real Person",
        "email": "real@example.com",
        "auth_method": "passwordless",
        "is_test": False,
    }

    with mock.patch.object(auth_routes, 'get_db_connection', return_value=mock.MagicMock()), \
         mock.patch.object(auth_routes, '_recent_magic_token_count', return_value=0), \
         mock.patch.object(auth_routes, '_insert_magic_token'), \
         mock.patch.object(auth_routes, '_magic_frontend_base', return_value='https://front.example'), \
         mock.patch.object(auth_routes, '_send_magic_link_email') as send:

        # (a) email maps to a real account -> a link IS sent...
        with mock.patch.object(auth_routes, '_find_user_for_magic_link', return_value=existing):
            hit = _post_magic_link(client, 'real@example.com')
        assert send.called

        send.reset_mock()

        # (b) email maps to nothing -> NO link sent...
        with mock.patch.object(auth_routes, '_find_user_for_magic_link', return_value=None):
            miss = _post_magic_link(client, 'nobody@example.com')
        assert not send.called

    # ...but the caller cannot tell the two apart: identical status + body.
    assert hit.status_code == 200
    assert miss.status_code == 200
    assert hit.get_json() == miss.get_json()
    assert hit.get_json()["message"] == ml.GENERIC_MAGIC_LINK_MESSAGE


def test_magic_link_skips_test_user_but_response_unchanged():
    app = _app()
    client = app.test_client()

    test_user = {
        "id": "22222222-2222-2222-2222-222222222222",
        "name": "T30G Upload Bot",
        "email": "bot@example.com",
        "auth_method": "passwordless",
        "is_test": True,
    }

    with mock.patch.object(auth_routes, 'get_db_connection', return_value=mock.MagicMock()), \
         mock.patch.object(auth_routes, '_find_user_for_magic_link', return_value=test_user), \
         mock.patch.object(auth_routes, '_send_magic_link_email') as send:
        resp = _post_magic_link(client, 'bot@example.com')

    assert not send.called
    assert resp.status_code == 200
    assert resp.get_json()["message"] == ml.GENERIC_MAGIC_LINK_MESSAGE


def test_magic_link_rejects_missing_email():
    app = _app()
    client = app.test_client()
    resp = client.post('/auth/magic-link', json={})
    assert resp.status_code == 400


def test_magic_link_dispatch_failure_still_returns_generic_200():
    app = _app()
    client = app.test_client()
    with mock.patch.object(auth_routes, '_dispatch_magic_link',
                           side_effect=RuntimeError("db down")):
        resp = _post_magic_link(client, 'real@example.com')
    assert resp.status_code == 200
    assert resp.get_json()["message"] == ml.GENERIC_MAGIC_LINK_MESSAGE


def test_undeliverable_email_never_touches_db():
    # Bot/e2e/*.local addresses short-circuit before any DB work.
    with mock.patch.object(auth_routes, 'get_db_connection') as conn:
        auth_routes._dispatch_magic_link('someone@guest.tomsgym.local')
    conn.assert_not_called()


# --------------------------------------------------------------------------- #
# Route: consume (single-use + JWT issuance)
# --------------------------------------------------------------------------- #

def test_consume_dead_token_returns_400():
    app = _app()
    client = app.test_client()
    with mock.patch.object(auth_routes, 'get_db_connection', return_value=mock.MagicMock()), \
         mock.patch.object(auth_routes, '_consume_magic_token', return_value=None):
        resp = client.get('/auth/magic/whatever-token')
    assert resp.status_code == 400


def test_consume_passwordless_user_returns_userid_without_jwt():
    app = _app()
    client = app.test_client()
    user = {"id": "33333333-3333-3333-3333-333333333333", "name": "Nopass",
            "email": "nopass@example.com", "auth_method": "passwordless"}
    with mock.patch.object(auth_routes, 'get_db_connection', return_value=mock.MagicMock()), \
         mock.patch.object(auth_routes, '_consume_magic_token', return_value=user["id"]), \
         mock.patch.object(auth_routes, '_get_user_identity', return_value=user):
        resp = client.get('/auth/magic/good-token')
    body = resp.get_json()
    assert resp.status_code == 200
    assert body["user_id"] == user["id"]
    assert body["access_token"] is None


def test_consume_password_user_gets_jwt():
    app = _app()
    client = app.test_client()
    user = {"id": "44444444-4444-4444-4444-444444444444", "name": "Haspass",
            "email": "haspass@example.com", "auth_method": "password"}
    with app.app_context():
        with mock.patch.object(auth_routes, 'get_db_connection', return_value=mock.MagicMock()), \
             mock.patch.object(auth_routes, '_consume_magic_token', return_value=user["id"]), \
             mock.patch.object(auth_routes, '_get_user_identity', return_value=user):
            resp = client.get('/auth/magic/good-token')
    body = resp.get_json()
    assert resp.status_code == 200
    assert body["user_id"] == user["id"]
    assert isinstance(body["access_token"], str) and body["access_token"]
