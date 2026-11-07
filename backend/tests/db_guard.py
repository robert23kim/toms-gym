"""Refuse to run the DB-backed test suite against anything but a local Postgres.

tests/conftest.py drops and recreates the core tables. With DATABASE_URL unset,
toms_gym.db falls back to the Cloud SQL connector named in backend/.env.
"""
from typing import Optional
from urllib.parse import urlsplit

LOCAL_DB_HOSTS = {"localhost", "127.0.0.1", "::1", "db-test"}


def unsafe_database_reason(database_url: Optional[str]) -> Optional[str]:
    """None when the URL names a local test database, else why it is refused."""
    if not database_url:
        return (
            "DATABASE_URL is unset, so toms_gym.db would use the Cloud SQL connector "
            "from backend/.env"
        )
    try:
        host = urlsplit(database_url).hostname
    except ValueError:
        host = None
    if host not in LOCAL_DB_HOSTS:
        return f"DATABASE_URL host {host!r} is not one of {sorted(LOCAL_DB_HOSTS)}"
    return None
