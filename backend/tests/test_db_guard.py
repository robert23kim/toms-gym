"""DB-free: the conftest guard that keeps init_db's DROP TABLE off Cloud SQL."""
import pytest

from db_guard import unsafe_database_reason


@pytest.mark.parametrize("url", [
    "postgresql://postgres:test@localhost:5434/toms_gym_test",
    "postgresql://postgres:test@127.0.0.1:5432/toms_gym_test",
    "postgresql://postgres:test@db-test:5432/toms_gym_test",
    "postgresql+pg8000://postgres:test@[::1]:5432/toms_gym_test",
])
def test_local_urls_are_allowed(url):
    assert unsafe_database_reason(url) is None


@pytest.mark.parametrize("url", [
    None,
    "",
    "postgresql://postgres:pw@10.1.2.3:5432/toms_gym",
    "postgresql://postgres:pw@toms-gym.example.com/toms_gym",
    "postgresql://postgres:pw@localhost.evil.com/toms_gym",
    "not a url",
])
def test_everything_else_is_refused(url):
    assert unsafe_database_reason(url)
