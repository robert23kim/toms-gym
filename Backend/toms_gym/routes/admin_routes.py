"""
Admin routes for maintenance operations.
"""

from flask import Blueprint, request, jsonify
from google.cloud import storage
import sqlalchemy
from urllib.parse import unquote
import os
import logging

from toms_gym.db import get_db_connection

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/admin/migrate/weekly-lifts', methods=['POST'])
def migrate_weekly_lifts():
    """
    Run migration to add the WeeklyMaxLift table.
    This is an idempotent migration - safe to run multiple times.
    """
    migration_sql = """
    -- Create function to update timestamps (if not exists)
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = CURRENT_TIMESTAMP;
        RETURN NEW;
    END;
    $$ language 'plpgsql';

    -- Create enum for weekly lift types (if not exists)
    DO $$ BEGIN
        CREATE TYPE weekly_lift_type AS ENUM ('bench', 'squat', 'deadlift', 'sitting_press');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;

    -- Create WeeklyMaxLift table for tracking weekly max lifts
    CREATE TABLE IF NOT EXISTS "WeeklyMaxLift" (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES "User"(id) ON DELETE CASCADE,
        week_start_date DATE NOT NULL,
        lift_type weekly_lift_type NOT NULL,
        weight_lbs DECIMAL(5,1) NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, week_start_date, lift_type)
    );

    -- Create indexes if they don't exist
    CREATE INDEX IF NOT EXISTS idx_weekly_max_lift_user_id ON "WeeklyMaxLift"(user_id);
    CREATE INDEX IF NOT EXISTS idx_weekly_max_lift_user_week ON "WeeklyMaxLift"(user_id, week_start_date);

    -- Create trigger for updating timestamps (drop and recreate to be safe)
    DROP TRIGGER IF EXISTS update_weekly_max_lift_updated_at ON "WeeklyMaxLift";
    CREATE TRIGGER update_weekly_max_lift_updated_at
        BEFORE UPDATE ON "WeeklyMaxLift"
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """

    try:
        session = get_db_connection()
        session.execute(sqlalchemy.text(migration_sql))
        session.commit()
        session.close()

        logger.info("WeeklyMaxLift migration completed successfully")
        return jsonify({
            "success": True,
            "message": "WeeklyMaxLift table and indexes created successfully"
        }), 200

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# Configuration
BUCKET_NAME = os.getenv('GCS_BUCKET_NAME', 'jtr-lift-u-4ever-cool-bucket')
VIDEO_PREFIX = 'videos/'


def get_storage_client():
    """Get Google Cloud Storage client."""
    return storage.Client()


def get_all_gcs_videos(bucket):
    """List all video blobs in GCS bucket."""
    logger.info(f"Fetching all videos from GCS bucket: {bucket.name}")
    blobs = list(bucket.list_blobs(prefix=VIDEO_PREFIX))
    gcs_urls = set()

    for blob in blobs:
        url = f"https://storage.googleapis.com/{bucket.name}/{blob.name}"
        gcs_urls.add(url)

    logger.info(f"Found {len(gcs_urls)} videos in GCS")
    return gcs_urls


def get_all_db_video_urls(session):
    """Get all video URLs from Attempt table."""
    logger.info("Fetching all video URLs from database...")
    result = session.execute(
        sqlalchemy.text('SELECT video_url FROM "Attempt" WHERE video_url IS NOT NULL')
    ).fetchall()

    db_urls = {row[0] for row in result if row[0]}
    logger.info(f"Found {len(db_urls)} video URLs in database")
    return db_urls


def find_orphaned_in_gcs(gcs_urls, db_urls):
    """Find GCS blobs with no matching database record."""
    orphaned = gcs_urls - db_urls
    logger.info(f"Found {len(orphaned)} orphaned videos in GCS (no DB record)")
    return orphaned


def find_broken_attempts(session):
    """Find Attempt records with broken UserCompetition links."""
    logger.info("Checking for Attempt records with broken UserCompetition links...")

    result = session.execute(
        sqlalchemy.text('''
            SELECT a.id, a.video_url, a.user_competition_id
            FROM "Attempt" a
            LEFT JOIN "UserCompetition" uc ON a.user_competition_id = uc.id
            WHERE uc.id IS NULL AND a.video_url IS NOT NULL
        ''')
    ).fetchall()

    broken = [(row[0], row[1], row[2]) for row in result]
    logger.info(f"Found {len(broken)} Attempt records with broken UserCompetition links")
    return broken


def find_broken_user_competitions(session):
    """Find UserCompetition records with broken Competition links."""
    logger.info("Checking for UserCompetition records with broken Competition links...")

    result = session.execute(
        sqlalchemy.text('''
            SELECT uc.id, uc.user_id, uc.competition_id
            FROM "UserCompetition" uc
            LEFT JOIN "Competition" c ON uc.competition_id = c.id
            WHERE c.id IS NULL
        ''')
    ).fetchall()

    broken = [(row[0], row[1], row[2]) for row in result]
    logger.info(f"Found {len(broken)} UserCompetition records with broken Competition links")
    return broken


def delete_gcs_blob(bucket, url, dry_run=True):
    """Delete a blob from GCS."""
    prefix = f"https://storage.googleapis.com/{bucket.name}/"
    if url.startswith(prefix):
        blob_name = url[len(prefix):]
        blob_name = unquote(blob_name)

        if dry_run:
            logger.info(f"[DRY RUN] Would delete GCS blob: {blob_name}")
            return True
        else:
            try:
                blob = bucket.blob(blob_name)
                blob.delete()
                logger.info(f"Deleted GCS blob: {blob_name}")
                return True
            except Exception as e:
                logger.error(f"ERROR deleting GCS blob {blob_name}: {e}")
                return False
    else:
        logger.warning(f"Skipping non-matching URL: {url}")
        return False


@admin_bp.route('/admin/cleanup-orphaned-videos', methods=['POST', 'DELETE'])
def cleanup_orphaned_videos():
    """
    Delete orphaned videos from GCS and database.

    Query params:
        dry_run: If 'true', only report what would be deleted (default: true)

    Returns:
        JSON with counts of orphaned items found/deleted
    """
    dry_run = request.args.get('dry_run', 'true').lower() == 'true'

    logger.info(f"Cleanup orphaned videos called. dry_run={dry_run}")

    results = {
        'dry_run': dry_run,
        'orphaned_gcs_videos': [],
        'broken_attempts': [],
        'broken_user_competitions': [],
        'deleted': {
            'gcs_blobs': 0,
            'attempts': 0,
            'user_competitions': 0
        },
        'errors': []
    }

    try:
        # Initialize clients
        storage_client = get_storage_client()
        bucket = storage_client.bucket(BUCKET_NAME)
        session = get_db_connection()

        try:
            # 1. Find orphaned GCS blobs
            gcs_urls = get_all_gcs_videos(bucket)
            db_urls = get_all_db_video_urls(session)
            orphaned_gcs = find_orphaned_in_gcs(gcs_urls, db_urls)

            results['orphaned_gcs_videos'] = sorted(list(orphaned_gcs))

            # Delete orphaned GCS blobs
            for url in orphaned_gcs:
                if delete_gcs_blob(bucket, url, dry_run):
                    results['deleted']['gcs_blobs'] += 1

            # 2. Find broken Attempts
            broken_attempts = find_broken_attempts(session)
            results['broken_attempts'] = [
                {'id': str(a[0]), 'video_url': a[1], 'user_competition_id': str(a[2])}
                for a in broken_attempts
            ]

            # Delete broken attempts
            for attempt_id, video_url, uc_id in broken_attempts:
                # Delete GCS blob if exists
                if video_url:
                    delete_gcs_blob(bucket, video_url, dry_run)

                if not dry_run:
                    try:
                        session.execute(
                            sqlalchemy.text('DELETE FROM "Attempt" WHERE id = :id'),
                            {"id": attempt_id}
                        )
                        results['deleted']['attempts'] += 1
                    except Exception as e:
                        results['errors'].append(f"Error deleting attempt {attempt_id}: {str(e)}")
                else:
                    results['deleted']['attempts'] += 1

            # 3. Find broken UserCompetitions
            broken_ucs = find_broken_user_competitions(session)
            results['broken_user_competitions'] = [
                {'id': str(uc[0]), 'user_id': str(uc[1]), 'competition_id': str(uc[2])}
                for uc in broken_ucs
            ]

            # Delete broken UserCompetitions
            for uc_id, user_id, comp_id in broken_ucs:
                if not dry_run:
                    try:
                        # First delete attempts linked to this UserCompetition
                        session.execute(
                            sqlalchemy.text('DELETE FROM "Attempt" WHERE user_competition_id = :id'),
                            {"id": uc_id}
                        )
                        # Then delete the UserCompetition
                        session.execute(
                            sqlalchemy.text('DELETE FROM "UserCompetition" WHERE id = :id'),
                            {"id": uc_id}
                        )
                        results['deleted']['user_competitions'] += 1
                    except Exception as e:
                        results['errors'].append(f"Error deleting UserCompetition {uc_id}: {str(e)}")
                else:
                    results['deleted']['user_competitions'] += 1

            # Commit if not dry run
            if not dry_run:
                session.commit()
                logger.info("Changes committed to database")

            # Summary
            results['summary'] = {
                'total_orphaned_gcs': len(orphaned_gcs),
                'total_broken_attempts': len(broken_attempts),
                'total_broken_user_competitions': len(broken_ucs)
            }

            return jsonify(results), 200

        except Exception as e:
            if not dry_run:
                session.rollback()
            logger.error(f"Error during cleanup: {e}")
            results['errors'].append(str(e))
            return jsonify(results), 500
        finally:
            session.close()

    except Exception as e:
        logger.error(f"Error initializing cleanup: {e}")
        results['errors'].append(str(e))
        return jsonify(results), 500
