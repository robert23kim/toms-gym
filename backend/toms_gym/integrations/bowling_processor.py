"""
Bowling Video Processor for Tom's Gym

Background daemon that polls for queued BowlingResult rows and sends them
to the bowling Cloud Run service for processing.

Configuration via environment variables:
    BOWLING_PROCESSOR_ENABLED  - 'true' to enable (default 'false')
    BOWLING_POLL_INTERVAL      - seconds between polls (default 5)
    ANALYSIS_SERVICE_URL        - URL of the bowling Cloud Run service
"""

import os
import threading
import time
import logging

import sqlalchemy

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment
BOWLING_PROCESSOR_ENABLED = os.environ.get('BOWLING_PROCESSOR_ENABLED', 'false').lower() == 'true'
BOWLING_POLL_INTERVAL = int(os.environ.get('BOWLING_POLL_INTERVAL', '5'))
ANALYSIS_SERVICE_URL = os.environ.get('ANALYSIS_SERVICE_URL', '')

# Timeout for stuck jobs (seconds)
STUCK_PROCESSING_TIMEOUT = 300  # 5 minutes


def _get_id_token():
    """Get an identity token for service-to-service authentication."""
    import google.auth.transport.requests
    import google.oauth2.id_token
    auth_request = google.auth.transport.requests.Request()
    return google.oauth2.id_token.fetch_id_token(auth_request, ANALYSIS_SERVICE_URL)


def start_bowling_processor():
    """Start the bowling processor as a background daemon thread."""
    if not BOWLING_PROCESSOR_ENABLED:
        logger.info("Bowling processor is disabled")
        return

    if not ANALYSIS_SERVICE_URL:
        logger.warning("ANALYSIS_SERVICE_URL not configured, skipping bowling processor")
        return

    thread = threading.Thread(target=run_bowling_processor, daemon=True)
    thread.start()
    logger.info("Bowling processor started as background thread")


def run_bowling_processor():
    """Infinite loop: poll for queued jobs, process them, sleep."""
    logger.info(f"Bowling processor running (poll every {BOWLING_POLL_INTERVAL}s)")

    while True:
        try:
            _poll_and_process()
        except Exception as e:
            logger.error(f"Error in bowling processor loop: {e}")

        time.sleep(BOWLING_POLL_INTERVAL)


def _poll_and_process():
    """
    Poll for one queued BowlingResult and process it.
    Also resets rows stuck in 'processing' for too long.
    """
    from toms_gym.db import get_db_connection

    session = get_db_connection()
    try:
        # Reset stuck processing rows back to queued
        session.execute(sqlalchemy.text("""
            UPDATE "BowlingResult"
            SET processing_status = 'queued', updated_at = now()
            WHERE processing_status = 'processing'
              AND updated_at < now() - interval '5 minutes'
        """))
        session.commit()

        # Grab one queued row with row-level lock (skip already-locked rows)
        row = session.execute(sqlalchemy.text("""
            SELECT br.id, br.attempt_id, a.video_url, br.lane_edges_manual
            FROM "BowlingResult" br
            JOIN "Attempt" a ON a.id = br.attempt_id
            WHERE br.processing_status = 'queued'
            ORDER BY br.created_at ASC
            LIMIT 1
            FOR UPDATE OF br SKIP LOCKED
        """)).fetchone()

        if not row:
            session.close()
            return

        result_id, attempt_id, video_url, lane_edges_manual = (
            str(row[0]), str(row[1]), row[2], row[3]
        )

        # Mark as processing
        session.execute(sqlalchemy.text("""
            UPDATE "BowlingResult"
            SET processing_status = 'processing', updated_at = now()
            WHERE id = :id
        """), {"id": result_id})
        session.commit()
        session.close()

        logger.info(f"Processing bowling video: result_id={result_id}, attempt_id={attempt_id}")
        process_bowling_video(result_id, attempt_id, video_url, lane_edges_manual)

    except Exception as e:
        logger.error(f"Error polling bowling jobs: {e}")
        try:
            session.rollback()
        except Exception:
            pass
        finally:
            session.close()


def process_bowling_video(result_id, attempt_id, video_url, lane_edges_manual=None):
    """
    Send video to the bowling service for processing, then update DB with results.
    """
    import json
    import requests
    from toms_gym.db import get_db_connection

    start_time = time.time()

    try:
        # Get identity token for service-to-service auth
        id_token = _get_id_token()

        # Build payload with optional manual lane edges
        payload = {"video_url": video_url, "attempt_id": attempt_id}
        if lane_edges_manual:
            payload["lane_edges"] = lane_edges_manual

        # Call bowling service
        response = requests.post(
            f"{ANALYSIS_SERVICE_URL}/analyze",
            json=payload,
            headers={"Authorization": f"Bearer {id_token}"},
            timeout=360,
        )

        if response.status_code != 200:
            error_body = response.text[:500]
            raise RuntimeError(
                f"Bowling service returned {response.status_code}: {error_body}"
            )

        result = response.json()
        logger.info(f"Bowling service response: {result}")

        # Check for service-level error
        if "error" in result:
            raise RuntimeError(f"Bowling service error: {result['error']}")

        processing_time = time.time() - start_time

        # Update BowlingResult with success
        session = get_db_connection()
        try:
            session.execute(sqlalchemy.text("""
                UPDATE "BowlingResult"
                SET processing_status = 'completed',
                    debug_video_url = :debug_video_url,
                    trajectory_png_url = :trajectory_png_url,
                    board_at_pins = :board_at_pins,
                    entry_board = :entry_board,
                    processing_time_s = :processing_time_s,
                    detection_rate = :detection_rate,
                    lane_edges_auto = :lane_edges_auto,
                    frame_url = :frame_url,
                    updated_at = now()
                WHERE id = :id
            """), {
                "id": result_id,
                "debug_video_url": result.get("debug_video_url"),
                "trajectory_png_url": result.get("trajectory_png_url"),
                "board_at_pins": result.get("board_at_pins"),
                "entry_board": result.get("entry_board"),
                "processing_time_s": round(processing_time, 2),
                "detection_rate": result.get("detection_rate"),
                "lane_edges_auto": json.dumps(result["lane_edges"]) if result.get("lane_edges") else None,
                "frame_url": result.get("frame_url"),
            })
            session.commit()
            logger.info(f"Bowling processing completed: result_id={result_id}, time={processing_time:.1f}s")
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()

    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Bowling processing failed for result_id={result_id}: {e}")

        # Update BowlingResult with failure
        from toms_gym.db import get_db_connection
        session = get_db_connection()
        try:
            session.execute(sqlalchemy.text("""
                UPDATE "BowlingResult"
                SET processing_status = 'failed',
                    error_message = :error_message,
                    processing_time_s = :processing_time_s,
                    updated_at = now()
                WHERE id = :id
            """), {
                "id": result_id,
                "error_message": str(e)[:1000],
                "processing_time_s": round(processing_time, 2),
            })
            session.commit()
        except Exception as db_err:
            logger.error(f"Failed to update BowlingResult status: {db_err}")
            session.rollback()
        finally:
            session.close()
