"""Pure, DB-free helpers for passwordless magic-link sign-in (T15).

The route layer (routes/auth_routes.py) does all DB + SMTP work; this module
holds only the pure decisions so they can be unit-tested without a database:
token generation, hashing, expiry math, single-use/expiry validity, and the
per-email rate-limit predicate.

Token approach — TABLE, not a stateless JWT. Single-use invalidation is a
stateful requirement (a signed JWT can't be marked "used" without a
server-side ledger anyway), and a table also makes per-email rate-limiting a
trivial COUNT and lets us store only a SHA-256 hash of the token so a DB leak
never exposes a live sign-in link. See migration 014_magic_link_tokens.sql.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

# 15-minute expiry (task T15 security requirement).
MAGIC_LINK_TTL_MINUTES = 15

# Rate-limit by email: at most this many links per rolling window. A user who
# keeps clicking "email me a link" can't be used to spam an inbox.
MAGIC_LINK_MAX_PER_WINDOW = 3
MAGIC_LINK_RATE_WINDOW_MINUTES = 15

# Generic response for POST /auth/magic-link — identical whether or not the
# email maps to a real account (no enumeration).
GENERIC_MAGIC_LINK_MESSAGE = (
    "If an account exists for that email, a sign-in link has been sent."
)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def generate_raw_token() -> str:
    """Return a fresh, high-entropy URL-safe token (the value emailed to the user)."""
    return secrets.token_urlsafe(32)


def hash_token(raw_token: str) -> str:
    """SHA-256 of the raw token. Only the hash is ever stored / queried."""
    return hashlib.sha256((raw_token or "").encode("utf-8")).hexdigest()


def compute_expiry(now: datetime) -> datetime:
    return now + timedelta(minutes=MAGIC_LINK_TTL_MINUTES)


def rate_window_start(now: datetime) -> datetime:
    return now - timedelta(minutes=MAGIC_LINK_RATE_WINDOW_MINUTES)


def is_token_usable(used_at, expires_at, now: datetime) -> bool:
    """True only if the token is unused (single-use) AND not expired.

    Mirrors the atomic guard in the consume SQL
    (`used_at IS NULL AND expires_at > now()`). Tested directly so single-use
    and expiry are covered without a database.
    """
    if used_at is not None:
        return False
    if expires_at is None:
        return False
    return expires_at > now


def is_rate_limited(recent_count: int) -> bool:
    """True when this email already hit its link quota for the current window."""
    return recent_count >= MAGIC_LINK_MAX_PER_WINDOW
