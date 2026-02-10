#!/usr/bin/env python3
"""
Script to find and delete orphaned videos from GCS and database.

Orphaned videos are:
1. Videos in GCS but with no matching Attempt record in the database
2. Attempt records with video_url but UserCompetition doesn't exist
3. UserCompetition records where Competition doesn't exist

Usage:
    python3 Backend/scripts/cleanup_orphaned_videos.py --dry-run   # Preview what would be deleted
    python3 Backend/scripts/cleanup_orphaned_videos.py              # Actually delete orphaned videos
"""

import argparse
import os
import sys
from urllib.parse import unquote

# Add Backend to path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from google.cloud import storage
import sqlalchemy
from toms_gym.db import get_db_connection

# Configuration
BUCKET_NAME = os.getenv('GCS_BUCKET_NAME', 'jtr-lift-u-4ever-cool-bucket')
VIDEO_PREFIX = 'videos/'


def get_storage_client():
    """Get Google Cloud Storage client."""
    return storage.Client()


def get_all_gcs_videos(bucket):
    """List all video blobs in GCS bucket."""
    print(f"Fetching all videos from GCS bucket: {bucket.name}")
    blobs = bucket.list_blobs(prefix=VIDEO_PREFIX)
    gcs_urls = set()

    for blob in blobs:
        url = f"https://storage.googleapis.com/{bucket.name}/{blob.name}"
        gcs_urls.add(url)

    print(f"Found {len(gcs_urls)} videos in GCS")
    return gcs_urls


def get_all_db_video_urls(session):
    """Get all video URLs from Attempt table."""
    print("Fetching all video URLs from database...")
    result = session.execute(
        sqlalchemy.text('SELECT video_url FROM "Attempt" WHERE video_url IS NOT NULL')
    ).fetchall()

    db_urls = {row[0] for row in result if row[0]}
    print(f"Found {len(db_urls)} video URLs in database")
    return db_urls


def find_orphaned_in_gcs(gcs_urls, db_urls):
    """Find GCS blobs with no matching database record."""
    orphaned = gcs_urls - db_urls
    print(f"Found {len(orphaned)} orphaned videos in GCS (no DB record)")
    return orphaned


def find_broken_attempts(session):
    """Find Attempt records with broken UserCompetition links."""
    print("Checking for Attempt records with broken UserCompetition links...")

    # Attempts where user_competition_id doesn't exist
    result = session.execute(
        sqlalchemy.text('''
            SELECT a.id, a.video_url, a.user_competition_id
            FROM "Attempt" a
            LEFT JOIN "UserCompetition" uc ON a.user_competition_id = uc.id
            WHERE uc.id IS NULL AND a.video_url IS NOT NULL
        ''')
    ).fetchall()

    broken = [(row[0], row[1], row[2]) for row in result]
    print(f"Found {len(broken)} Attempt records with broken UserCompetition links")
    return broken


def find_broken_user_competitions(session):
    """Find UserCompetition records with broken Competition links."""
    print("Checking for UserCompetition records with broken Competition links...")

    result = session.execute(
        sqlalchemy.text('''
            SELECT uc.id, uc.user_id, uc.competition_id
            FROM "UserCompetition" uc
            LEFT JOIN "Competition" c ON uc.competition_id = c.id
            WHERE c.id IS NULL
        ''')
    ).fetchall()

    broken = [(row[0], row[1], row[2]) for row in result]
    print(f"Found {len(broken)} UserCompetition records with broken Competition links")
    return broken


def delete_gcs_blob(bucket, url, dry_run=True):
    """Delete a blob from GCS."""
    # Extract blob name from URL
    prefix = f"https://storage.googleapis.com/{bucket.name}/"
    if url.startswith(prefix):
        blob_name = url[len(prefix):]
        blob_name = unquote(blob_name)  # Handle URL encoding

        if dry_run:
            print(f"  [DRY RUN] Would delete GCS blob: {blob_name}")
            return True
        else:
            try:
                blob = bucket.blob(blob_name)
                blob.delete()
                print(f"  Deleted GCS blob: {blob_name}")
                return True
            except Exception as e:
                print(f"  ERROR deleting GCS blob {blob_name}: {e}")
                return False
    else:
        print(f"  Skipping non-matching URL: {url}")
        return False


def delete_attempt(session, attempt_id, dry_run=True):
    """Delete an Attempt record."""
    if dry_run:
        print(f"  [DRY RUN] Would delete Attempt: {attempt_id}")
        return True
    else:
        try:
            session.execute(
                sqlalchemy.text('DELETE FROM "Attempt" WHERE id = :id'),
                {"id": attempt_id}
            )
            print(f"  Deleted Attempt: {attempt_id}")
            return True
        except Exception as e:
            print(f"  ERROR deleting Attempt {attempt_id}: {e}")
            return False


def delete_user_competition(session, uc_id, dry_run=True):
    """Delete a UserCompetition record."""
    if dry_run:
        print(f"  [DRY RUN] Would delete UserCompetition: {uc_id}")
        return True
    else:
        try:
            # First delete any attempts linked to this UserCompetition
            session.execute(
                sqlalchemy.text('DELETE FROM "Attempt" WHERE user_competition_id = :id'),
                {"id": uc_id}
            )
            # Then delete the UserCompetition
            session.execute(
                sqlalchemy.text('DELETE FROM "UserCompetition" WHERE id = :id'),
                {"id": uc_id}
            )
            print(f"  Deleted UserCompetition: {uc_id}")
            return True
        except Exception as e:
            print(f"  ERROR deleting UserCompetition {uc_id}: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description='Clean up orphaned videos from GCS and database')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview what would be deleted without actually deleting')
    args = parser.parse_args()

    dry_run = args.dry_run

    if dry_run:
        print("=" * 60)
        print("DRY RUN MODE - No changes will be made")
        print("=" * 60)
    else:
        print("=" * 60)
        print("LIVE MODE - Changes will be made!")
        print("=" * 60)
        response = input("Are you sure you want to proceed? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted.")
            return

    print()

    # Initialize clients
    storage_client = get_storage_client()
    bucket = storage_client.bucket(BUCKET_NAME)
    session = get_db_connection()

    try:
        # 1. Find and handle orphaned GCS blobs
        print("\n" + "=" * 60)
        print("STEP 1: Finding orphaned videos in GCS")
        print("=" * 60)

        gcs_urls = get_all_gcs_videos(bucket)
        db_urls = get_all_db_video_urls(session)
        orphaned_gcs = find_orphaned_in_gcs(gcs_urls, db_urls)

        if orphaned_gcs:
            print(f"\nOrphaned GCS videos ({len(orphaned_gcs)}):")
            deleted_count = 0
            for url in sorted(orphaned_gcs):
                if delete_gcs_blob(bucket, url, dry_run):
                    deleted_count += 1
            print(f"\n{'Would delete' if dry_run else 'Deleted'} {deleted_count} GCS blobs")

        # 2. Find and handle broken Attempts
        print("\n" + "=" * 60)
        print("STEP 2: Finding Attempts with broken UserCompetition links")
        print("=" * 60)

        broken_attempts = find_broken_attempts(session)

        if broken_attempts:
            print(f"\nBroken Attempt records ({len(broken_attempts)}):")
            deleted_count = 0
            for attempt_id, video_url, uc_id in broken_attempts:
                print(f"  Attempt {attempt_id}: video_url={video_url}, user_competition_id={uc_id}")
                # Delete the GCS blob first if it exists
                if video_url:
                    delete_gcs_blob(bucket, video_url, dry_run)
                # Then delete the attempt record
                if delete_attempt(session, attempt_id, dry_run):
                    deleted_count += 1

            if not dry_run:
                session.commit()
            print(f"\n{'Would delete' if dry_run else 'Deleted'} {deleted_count} Attempt records")

        # 3. Find and handle broken UserCompetitions
        print("\n" + "=" * 60)
        print("STEP 3: Finding UserCompetitions with broken Competition links")
        print("=" * 60)

        broken_ucs = find_broken_user_competitions(session)

        if broken_ucs:
            print(f"\nBroken UserCompetition records ({len(broken_ucs)}):")
            deleted_count = 0
            for uc_id, user_id, comp_id in broken_ucs:
                print(f"  UserCompetition {uc_id}: user_id={user_id}, competition_id={comp_id}")
                if delete_user_competition(session, uc_id, dry_run):
                    deleted_count += 1

            if not dry_run:
                session.commit()
            print(f"\n{'Would delete' if dry_run else 'Deleted'} {deleted_count} UserCompetition records")

        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Orphaned GCS videos: {len(orphaned_gcs)}")
        print(f"Broken Attempt records: {len(broken_attempts)}")
        print(f"Broken UserCompetition records: {len(broken_ucs)}")

        if dry_run:
            print("\nThis was a dry run. Run without --dry-run to actually delete.")
        else:
            print("\nCleanup completed.")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        if not dry_run:
            session.rollback()
    finally:
        session.close()


if __name__ == '__main__':
    main()
