"""Tests for migration 006: bowling annotations columns."""
import os
import pytest
from sqlalchemy import text
from toms_gym.db import get_db_connection, Session as DBSession


@pytest.fixture(autouse=True)
def ensure_bowling_result_table(db_session):
    """Ensure BowlingResult table and prior migrations exist before testing 006."""
    # Run migration 004 (creates BowlingResult table)
    migrations_dir = os.path.join(
        os.path.dirname(__file__), '..', 'toms_gym', 'migrations'
    )
    for migration in ['004_bowling_result.sql', '005_bowling_lane_edges.sql', '006_bowling_annotations.sql']:
        path = os.path.join(migrations_dir, migration)
        with open(path) as f:
            sql = f.read()
        db_session.execute(text(sql))
    db_session.commit()


class TestMigration006:
    """Verify annotation and frames_url columns exist after migration."""

    def test_annotation_column_exists(self, db_session):
        """annotation JSONB column exists on BowlingResult."""
        row = db_session.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'BowlingResult' AND column_name = 'annotation'
        """)).fetchone()
        assert row is not None, "annotation column missing from BowlingResult"
        # PostgreSQL reports jsonb as 'jsonb' in udt_name but 'USER-DEFINED' in data_type
        udt = db_session.execute(text("""
            SELECT udt_name
            FROM information_schema.columns
            WHERE table_name = 'BowlingResult' AND column_name = 'annotation'
        """)).fetchone()
        assert udt[0] == 'jsonb', f"Expected jsonb, got {udt[0]}"

    def test_frames_url_column_exists(self, db_session):
        """frames_url TEXT column exists on BowlingResult."""
        row = db_session.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'BowlingResult' AND column_name = 'frames_url'
        """)).fetchone()
        assert row is not None, "frames_url column missing from BowlingResult"
        assert row[1] == 'text', f"Expected text, got {row[1]}"

    def test_migration_is_idempotent(self, db_session):
        """Running migration SQL again does not error (IF NOT EXISTS)."""
        migration_sql = """
            ALTER TABLE "BowlingResult"
                ADD COLUMN IF NOT EXISTS annotation JSONB,
                ADD COLUMN IF NOT EXISTS frames_url TEXT;
        """
        # Should not raise
        db_session.execute(text(migration_sql))
        db_session.commit()
