"""
Background processor for lifting video analysis.

Polls the LiftingResult table for queued jobs and sends them
to the bowling-service's /analyze-lift endpoint for processing.

Config via environment variables:
    LIFTING_PROCESSOR_ENABLED: 'true' to enable (default: 'false')
    ANALYSIS_SERVICE_URL: URL of the processing service
    LIFTING_POLL_INTERVAL: seconds between polls (default: 5)
"""

import json
import logging
import os
import threading
import time

import requests
import sqlalchemy

logger = logging.getLogger(__name__)

LIFTING_PROCESSOR_ENABLED = os.environ.get('LIFTING_PROCESSOR_ENABLED', 'false').lower() == 'true'
ANALYSIS_SERVICE_URL = os.environ.get('ANALYSIS_SERVICE_URL', '')
LIFTING_POLL_INTERVAL = int(os.environ.get('LIFTING_POLL_INTERVAL', '5'))


def _get_id_token():
    """Get Google identity token for service-to-service auth."""
    from google.auth.transport.requests import Request as AuthRequest
    from google.oauth2 import id_token
    return id_token.fetch_id_token(AuthRequest(), ANALYSIS_SERVICE_URL)


def start_lifting_processor():
    """Start the lifting processor as a background daemon thread."""
    if not LIFTING_PROCESSOR_ENABLED:
        logger.info("Lifting processor is disabled")
        return

    if not ANALYSIS_SERVICE_URL:
        logger.warning("ANALYSIS_SERVICE_URL not configured, lifting processor cannot start")
        return

    thread = threading.Thread(target=_run_processor, daemon=True)
    thread.start()
    logger.info("Lifting processor started as background thread")


def _run_processor():
    """Main processor loop."""
    from toms_gym.db import get_db_connection
    while True:
        try:
            _poll_and_process(get_db_connection)
        except Exception as e:
            logger.error(f"Lifting processor error: {e}")
        time.sleep(LIFTING_POLL_INTERVAL)


def _poll_and_process(get_connection):
    """Poll for one queued job and process it."""
    session = get_connection()
    try:
        # Reset stuck jobs (processing > 5 minutes)
        session.execute(sqlalchemy.text("""
            UPDATE "LiftingResult"
            SET processing_status = 'queued', updated_at = now()
            WHERE processing_status = 'processing'
              AND updated_at < now() - interval '5 minutes'
        """))
        session.commit()

        # Grab one queued job with row-level lock
        row = session.execute(sqlalchemy.text("""
            SELECT lr.id, lr.attempt_id, a.video_url
            FROM "LiftingResult" lr
            JOIN "Attempt" a ON a.id = lr.attempt_id
            WHERE lr.processing_status = 'queued'
            ORDER BY lr.created_at ASC
            LIMIT 1
            FOR UPDATE OF lr SKIP LOCKED
        """)).fetchone()

        if not row:
            return

        result_id = row.id
        attempt_id = row.attempt_id
        video_url = row.video_url

        logger.info(f"Processing lifting job: result={result_id}, attempt={attempt_id}")

        # Mark as processing
        session.execute(sqlalchemy.text("""
            UPDATE "LiftingResult"
            SET processing_status = 'processing', updated_at = now()
            WHERE id = :id
        """), {"id": result_id})
        session.commit()

    except Exception as e:
        session.rollback()
        logger.error(f"Poll error: {e}")
        return
    finally:
        session.close()

    # Process with a fresh session (don't hold poll session open during HTTP call)
    _process_job(get_connection, result_id, attempt_id, video_url)


def _process_job(get_connection, result_id, attempt_id, video_url):
    """Call the analysis service and store results."""
    session = get_connection()
    try:
        id_token = _get_id_token()

        response = requests.post(
            f"{ANALYSIS_SERVICE_URL}/analyze-lift",
            json={
                "video_url": video_url,
                "attempt_id": str(attempt_id),
            },
            headers={"Authorization": f"Bearer {id_token}"},
            timeout=360,
        )

        if response.status_code != 200:
            raise RuntimeError(f"Service returned {response.status_code}: {response.text[:500]}")

        result = response.json()

        session.execute(sqlalchemy.text("""
            UPDATE "LiftingResult"
            SET processing_status = 'completed',
                annotated_video_url = :annotated_video_url,
                summary_url = :summary_url,
                report = :report,
                processing_time_s = :processing_time_s,
                updated_at = now()
            WHERE id = :id
        """), {
            "id": result_id,
            "annotated_video_url": result.get("annotated_video_url"),
            "summary_url": result.get("summary_url"),
            "report": json.dumps(result.get("report", {})),
            "processing_time_s": result.get("processing_time_s"),
        })
        session.commit()
        logger.info(f"Lifting analysis completed: result={result_id}")

    except Exception as e:
        error_msg = str(e)[:1000]
        logger.error(f"Lifting analysis failed: result={result_id}: {error_msg}")
        try:
            session.execute(sqlalchemy.text("""
                UPDATE "LiftingResult"
                SET processing_status = 'failed',
                    error_message = :error_message,
                    updated_at = now()
                WHERE id = :id
            """), {"id": result_id, "error_message": error_msg})
            session.commit()
        except Exception:
            session.rollback()
    finally:
        session.close()
