"""DB-free unit tests for the analysis-complete email notifier (T9).

Runs under run_ci_tests.sh with --noconftest: no live DB. The DB-touching
helpers (_lookup_uploader, _reserve_notification, _create_short_link) are
patched so we exercise only the orchestration + guard logic.
"""

from unittest import mock

import pytest

from toms_gym.integrations import analysis_notify as an


DUMMY_CONN = object()  # never used — DB helpers are patched


def _uploader(email="golfer@example.com", is_test=False):
    return {
        "user_id": "11111111-1111-1111-1111-111111111111",
        "email": email,
        "is_test": is_test,
        "competition_id": "22222222-2222-2222-2222-222222222222",
    }


# --- bot / undeliverable classification -----------------------------------

@pytest.mark.parametrize("email,expected", [
    ("real.person@gmail.com", False),
    ("", True),
    (None, True),
    ("no-at-sign", True),
    ("e2e-lift-1772469238377@gmail.com", True),
    ("someone@guest.tomsgym.local", True),
    ("bot@e2e.tomsgym.local", True),
])
def test_is_bot_or_undeliverable(email, expected):
    assert an._is_bot_or_undeliverable(email) is expected


# --- (a) skip for test users ----------------------------------------------

def test_skips_email_for_is_test_user():
    with mock.patch.object(an, '_lookup_uploader', return_value=_uploader(is_test=True)), \
         mock.patch.object(an, '_reserve_notification') as reserve, \
         mock.patch.object(an, '_send_ready_email') as send:
        an.notify_analysis_complete(DUMMY_CONN, 'lifting', 'attempt-1')
    reserve.assert_not_called()
    send.assert_not_called()


def test_skips_email_for_bot_address():
    with mock.patch.object(an, '_lookup_uploader',
                           return_value=_uploader(email='e2e-lift-9@gmail.com')), \
         mock.patch.object(an, '_reserve_notification') as reserve, \
         mock.patch.object(an, '_send_ready_email') as send:
        an.notify_analysis_complete(DUMMY_CONN, 'lifting', 'attempt-1')
    reserve.assert_not_called()
    send.assert_not_called()


def test_skips_email_when_no_email_on_file():
    with mock.patch.object(an, '_lookup_uploader', return_value=_uploader(email=None)), \
         mock.patch.object(an, '_send_ready_email') as send:
        an.notify_analysis_complete(DUMMY_CONN, 'lifting', 'attempt-1')
    send.assert_not_called()


# --- (b) completion survives a failing email sender -----------------------

def test_completion_survives_smtp_failure():
    with mock.patch.object(an, '_lookup_uploader', return_value=_uploader()), \
         mock.patch.object(an, '_reserve_notification', return_value=True), \
         mock.patch.object(an, '_create_short_link', return_value='abc123'), \
         mock.patch.object(an, '_send_ready_email',
                           side_effect=RuntimeError("SMTP down")) as send:
        # Must NOT raise — analysis completion has to proceed normally.
        an.notify_analysis_complete(DUMMY_CONN, 'lifting', 'attempt-1')
    send.assert_called_once()


def test_lookup_failure_does_not_raise():
    with mock.patch.object(an, '_lookup_uploader',
                           side_effect=RuntimeError("db exploded")), \
         mock.patch.object(an, '_send_ready_email') as send:
        an.notify_analysis_complete(DUMMY_CONN, 'bowling', 'attempt-1')
    send.assert_not_called()


# --- idempotency -----------------------------------------------------------

def test_idempotent_skip_when_already_reserved():
    with mock.patch.object(an, '_lookup_uploader', return_value=_uploader()), \
         mock.patch.object(an, '_reserve_notification', return_value=False), \
         mock.patch.object(an, '_create_short_link') as short, \
         mock.patch.object(an, '_send_ready_email') as send:
        an.notify_analysis_complete(DUMMY_CONN, 'lifting', 'attempt-1')
    short.assert_not_called()
    send.assert_not_called()


# --- happy path: sends with a short link ----------------------------------

def test_sends_email_with_short_link():
    with mock.patch.object(an, '_lookup_uploader', return_value=_uploader()), \
         mock.patch.object(an, '_reserve_notification', return_value=True), \
         mock.patch.object(an, '_create_short_link', return_value='abc123') as short, \
         mock.patch.object(an, '_get_frontend_base', return_value='https://front.example'), \
         mock.patch.object(an, '_send_ready_email') as send:
        an.notify_analysis_complete(DUMMY_CONN, 'lifting', 'attempt-1')
    short.assert_called_once()
    send.assert_called_once()
    to_email, result_type, link = send.call_args.args
    assert to_email == 'golfer@example.com'
    assert result_type == 'lifting'
    assert link == 'https://front.example/s/abc123'


def test_falls_back_to_direct_url_when_short_link_fails():
    with mock.patch.object(an, '_lookup_uploader', return_value=_uploader()), \
         mock.patch.object(an, '_reserve_notification', return_value=True), \
         mock.patch.object(an, '_create_short_link', return_value=None), \
         mock.patch.object(an, '_get_frontend_base', return_value='https://front.example'), \
         mock.patch.object(an, '_send_ready_email') as send:
        an.notify_analysis_complete(DUMMY_CONN, 'bowling', 'attempt-9')
    _, _, link = send.call_args.args
    assert link == 'https://front.example/bowling/result/attempt-9'


def test_disabled_flag_short_circuits():
    with mock.patch.object(an, 'ANALYSIS_NOTIFY_ENABLED', False), \
         mock.patch.object(an, '_lookup_uploader') as lookup:
        an.notify_analysis_complete(DUMMY_CONN, 'lifting', 'attempt-1')
    lookup.assert_not_called()
