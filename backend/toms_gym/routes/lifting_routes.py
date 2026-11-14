"""Lifting analysis routes — trigger analysis and poll for results."""

import logging
import uuid
import sqlalchemy
from flask import Blueprint, jsonify, request
from toms_gym.db import get_db_connection
from toms_gym.services.analysis_dispatch import enqueue_analysis_job
from toms_gym.services.lift_type_auto import needs_lift_type

lifting_bp = Blueprint('lifting', __name__, url_prefix='/lifting')
logger = logging.getLogger(__name__)


def queue_lifting_analysis(session, attempt_id):
    """Create or re-queue the attempt's LiftingResult and enqueue the job.

    Returns (result_id, processing_status, outcome), outcome one of
    'created' | 'requeued' | 'in_progress'. Commits the caller's session.
    """
    existing = session.execute(
        sqlalchemy.text("""
            SELECT id, processing_status FROM "LiftingResult"
            WHERE attempt_id = :attempt_id
        """),
        {"attempt_id": attempt_id}
    ).fetchone()

    if existing:
        if existing.processing_status not in ('completed', 'failed'):
            return str(existing.id), existing.processing_status, "in_progress"
        session.execute(
            sqlalchemy.text("""
                UPDATE "LiftingResult"
                SET processing_status = 'queued',
                    annotated_video_url = NULL,
                    summary_url = NULL,
                    report = NULL,
                    processing_time_s = NULL,
                    error_message = NULL,
                    updated_at = now()
                WHERE id = :id
            """),
            {"id": existing.id}
        )
        session.commit()
        enqueue_analysis_job('lifting', str(existing.id))
        return str(existing.id), "queued", "requeued"

    result_id = str(uuid.uuid4())
    session.execute(
        sqlalchemy.text("""
            INSERT INTO "LiftingResult" (id, attempt_id, processing_status)
            VALUES (:id, :attempt_id, 'queued')
        """),
        {"id": result_id, "attempt_id": attempt_id}
    )
    session.commit()
    enqueue_analysis_job('lifting', result_id)
    return result_id, "queued", "created"


@lifting_bp.route('/analyze/<string:attempt_id>', methods=['POST'])
def trigger_analysis(attempt_id):
    """Trigger lifting analysis for an attempt. Creates LiftingResult if not exists."""
    session = None
    try:
        session = get_db_connection()

        # Verify attempt exists and has a video
        attempt = session.execute(
            sqlalchemy.text("""
                SELECT id, video_url FROM "Attempt" WHERE id = :attempt_id
            """),
            {"attempt_id": attempt_id}
        ).fetchone()

        if not attempt:
            return jsonify({"error": "Attempt not found"}), 404

        if not attempt.video_url:
            return jsonify({"error": "Attempt has no video"}), 400

        result_id, status, outcome = queue_lifting_analysis(session, attempt_id)
        if outcome == "requeued":
            return jsonify({
                "lifting_result_id": result_id,
                "status": "queued",
                "message": "Re-queued for analysis"
            })
        if outcome == "in_progress":
            return jsonify({
                "lifting_result_id": result_id,
                "status": status,
                "message": "Analysis already in progress"
            })
        return jsonify({
            "lifting_result_id": result_id,
            "status": "queued"
        }), 201

    except Exception as e:
        if session:
            session.rollback()
        logger.error(f"Error triggering lifting analysis: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if session:
            session.close()


@lifting_bp.route('/result/<string:attempt_id>', methods=['GET'])
def get_lifting_result(attempt_id):
    """Get lifting analysis result for an attempt."""
    session = None
    try:
        session = get_db_connection()
        row = session.execute(
            sqlalchemy.text("""
                SELECT lr.id, lr.attempt_id, lr.processing_status,
                       lr.annotated_video_url, lr.summary_url,
                       lr.report, lr.processing_time_s,
                       lr.error_message, lr.created_at, lr.updated_at,
                       a.created_at AS attempt_created_at,
                       a.lift_type, a.lift_type_source, a.lift_type_confidence,
                       uc.user_id, uc.competition_id
                FROM "LiftingResult" lr
                LEFT JOIN "Attempt" a ON a.id = lr.attempt_id
                LEFT JOIN "UserCompetition" uc ON uc.id = a.user_competition_id
                WHERE lr.attempt_id = :attempt_id
            """),
            {"attempt_id": attempt_id}
        ).fetchone()

        if not row:
            return jsonify({"error": "No lifting result found"}), 404

        return jsonify({
            "id": str(row.id),
            "attempt_id": str(row.attempt_id),
            "processing_status": row.processing_status,
            "annotated_video_url": row.annotated_video_url,
            "summary_url": row.summary_url,
            "report": row.report,
            "processing_time_s": float(row.processing_time_s) if row.processing_time_s else None,
            "error_message": row.error_message,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            "attempt_created_at": row.attempt_created_at.isoformat() if row.attempt_created_at else None,
            "user_id": str(row.user_id) if row.user_id else None,
            "competition_id": str(row.competition_id) if row.competition_id else None,
            "lift_type": row.lift_type,
            "lift_type_source": row.lift_type_source,
            "lift_type_confidence": row.lift_type_confidence,
            "needs_lift_type": needs_lift_type(row.lift_type, row.processing_status),
        })

    except Exception as e:
        logger.error(f"Error getting lifting result: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if session:
            session.close()
