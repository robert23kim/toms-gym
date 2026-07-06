"""Email the uploader a short link when a lifting or bowling analysis completes.

T9 (docs/plans/2026-07-06-ux-roadmap.md): turn the dead-end wait after upload
into a retention loop. Called from the jobs-pipeline completion hooks
(lifting_processor._process_job and bowling_processor.process_bowling_video).

Design guards (all mandatory — see task T9):
  * Best-effort: notify_analysis_complete NEVER raises and NEVER blocks the
    completion transaction. All work is wrapped; failures log a warning.
  * No email to bot/test users: skip when User.is_test is true, when there is
    no email on file, or when the address is a synthetic/undeliverable bot
    address (e2e-lift-*, *.local).
  * Idempotent: a completion that runs twice (Cloud Tasks retry, poller reset)
    reserves a unique (result_type, attempt_id) row before sending, so the
    email goes out at most once.
"""

import logging
import os

import sqlalchemy

logger = logging.getLogger(__name__)

# Reuse the SMTP config + frontend-base resolution already used by the
# email-upload integration so there is a single source of truth for creds.
from toms_gym.integrations.email_upload import (
    EMAIL_SMTP_SERVER,
    EMAIL_SMTP_PORT,
    EMAIL_USERNAME,
    EMAIL_PASSWORD,
    _get_frontend_base,
)
# Reuse the short-link code generator so codes match the /s/<code> format.
from toms_gym.routes.short_link_routes import _generate_code, _MAX_COLLISION_RETRIES

ANALYSIS_NOTIFY_ENABLED = os.environ.get('ANALYSIS_NOTIFY_ENABLED', 'true').lower() == 'true'

# Marker header so a future inbound processor can recognize/skip these.
_NOTIFY_HEADER_KEY = 'X-Toms-Gym-Email'
_NOTIFY_HEADER_VALUE = 'analysis-ready'


def _is_bot_or_undeliverable(email: str) -> bool:
    """True for synthetic bot/e2e addresses and non-routable local domains.

    Backstop for User.is_test: mirrors the bot patterns in migration 013 and
    also drops *.local addresses (golf guests @guest.tomsgym.local, e2e
    @e2e.tomsgym.local) which are never deliverable.
    """
    if not email:
        return True
    e = email.strip().lower()
    if not e or '@' not in e:
        return True
    if e.startswith('e2e-lift-'):
        return True
    domain = e.rsplit('@', 1)[-1]
    if domain.endswith('.local'):
        return True
    return False


def _ensure_notification_table(session):
    """Create the idempotency ledger lazily (startup-migration-free)."""
    session.execute(sqlalchemy.text("""
        CREATE TABLE IF NOT EXISTS "AnalysisNotification" (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            result_type TEXT NOT NULL,
            attempt_id UUID NOT NULL,
            email TEXT,
            short_code TEXT,
            created_at TIMESTAMPTZ DEFAULT now(),
            UNIQUE (result_type, attempt_id)
        )
    """))
    session.commit()


def _lookup_uploader(get_connection, attempt_id):
    """Return {user_id, email, is_test, competition_id} for an attempt, or None."""
    session = get_connection()
    try:
        row = session.execute(
            sqlalchemy.text("""
                SELECT u.id AS user_id,
                       u.email AS email,
                       COALESCE(u.is_test, false) AS is_test,
                       uc.competition_id AS competition_id
                FROM "Attempt" a
                JOIN "UserCompetition" uc ON uc.id = a.user_competition_id
                JOIN "User" u ON u.id = uc.user_id
                WHERE a.id = :attempt_id
            """),
            {"attempt_id": attempt_id},
        ).fetchone()
        if not row:
            return None
        return {
            "user_id": str(row.user_id),
            "email": row.email,
            "is_test": bool(row.is_test),
            "competition_id": str(row.competition_id) if row.competition_id else None,
        }
    finally:
        session.close()


def _reserve_notification(get_connection, result_type, attempt_id, email):
    """Atomically claim the (result_type, attempt_id) slot.

    Returns True if this caller won the claim (should send), False if a
    notification was already reserved (skip — idempotency guard).
    """
    session = get_connection()
    try:
        _ensure_notification_table(session)
        inserted = session.execute(
            sqlalchemy.text("""
                INSERT INTO "AnalysisNotification" (result_type, attempt_id, email)
                VALUES (:result_type, :attempt_id, :email)
                ON CONFLICT (result_type, attempt_id) DO NOTHING
                RETURNING id
            """),
            {"result_type": result_type, "attempt_id": attempt_id, "email": email},
        ).fetchone()
        session.commit()
        return inserted is not None
    finally:
        session.close()


def _create_short_link(get_connection, target_url):
    """Insert a ShortLink row and return its code, or None on failure."""
    session = get_connection()
    try:
        for _ in range(_MAX_COLLISION_RETRIES):
            code = _generate_code()
            try:
                session.execute(
                    sqlalchemy.text(
                        'INSERT INTO "ShortLink" (short_code, target_url) '
                        'VALUES (:short_code, :target_url)'
                    ),
                    {"short_code": code, "target_url": target_url},
                )
                session.commit()
                return code
            except sqlalchemy.exc.IntegrityError:
                session.rollback()
                continue
        return None
    finally:
        session.close()


def _build_result_url(result_type, info, attempt_id):
    base = _get_frontend_base()
    if result_type == 'bowling':
        return f"{base}/bowling/result/{attempt_id}"
    # lifting
    competition_id = info.get("competition_id")
    user_id = info.get("user_id")
    if competition_id and user_id:
        return f"{base}/challenges/{competition_id}/participants/{user_id}/video/{attempt_id}"
    return f"{base}/challenges"


def _send_ready_email(to_email, result_type, link):
    """Send the 'analysis is ready' email. Raises on SMTP failure (caller isolates)."""
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    import smtplib

    if not EMAIL_USERNAME or not EMAIL_PASSWORD:
        logger.warning("Cannot send analysis-ready email: SMTP credentials not configured")
        return

    label = "bowling" if result_type == 'bowling' else "lift"
    msg = MIMEMultipart()
    msg['From'] = EMAIL_USERNAME
    msg['To'] = to_email
    msg['Subject'] = "Your Tom's Gym analysis is ready"
    msg[_NOTIFY_HEADER_KEY] = _NOTIFY_HEADER_VALUE
    msg['Auto-Submitted'] = 'auto-generated'

    body = f"""Your {label} analysis is ready!

View your results here:
{link}

Thanks for using Tom's Gym.

—
You're receiving this because you uploaded a video for analysis. To stop
these emails, reply with "unsubscribe" and we'll take you off the list.
"""
    msg.attach(MIMEText(body, 'plain'))

    with smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
        server.send_message(msg)

    logger.info(f"Analysis-ready email sent to {to_email} ({result_type})")


def notify_analysis_complete(get_connection, result_type, attempt_id):
    """Best-effort: email the uploader a short link to their completed analysis.

    result_type: 'lifting' | 'bowling'. NEVER raises — analysis completion must
    proceed normally even when SMTP or the DB lookup fails.
    """
    try:
        if not ANALYSIS_NOTIFY_ENABLED:
            return

        info = _lookup_uploader(get_connection, attempt_id)
        if info is None:
            logger.info(f"Analysis-ready email skipped: no uploader for {result_type} {attempt_id}")
            return

        if info["is_test"]:
            logger.info(f"Analysis-ready email skipped: test user ({result_type} {attempt_id})")
            return

        email = info["email"]
        if _is_bot_or_undeliverable(email):
            logger.info(f"Analysis-ready email skipped: no/undeliverable email ({result_type} {attempt_id})")
            return

        # Idempotency: claim the slot before sending so a re-run can't double-send.
        if not _reserve_notification(get_connection, result_type, attempt_id, email):
            logger.info(f"Analysis-ready email already sent for {result_type} {attempt_id}")
            return

        result_url = _build_result_url(result_type, info, attempt_id)
        short_code = _create_short_link(get_connection, result_url)
        link = f"{_get_frontend_base()}/s/{short_code}" if short_code else result_url

        _send_ready_email(email, result_type, link)

    except Exception as e:
        # Guard: analysis completion must never fail on email trouble.
        logger.warning(f"Analysis-ready email failed for {result_type} {attempt_id}: {e}")
