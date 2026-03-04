"""Lifting analysis routes — trigger analysis and poll for results."""

import logging
import uuid
import sqlalchemy
from flask import Blueprint, jsonify, request
from toms_gym.db import get_db_connection

lifting_bp = Blueprint('lifting', __name__, url_prefix='/lifting')
logger = logging.getLogger(__name__)


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

        # Check if LiftingResult already exists
        existing = session.execute(
            sqlalchemy.text("""
                SELECT id, processing_status FROM "LiftingResult"
                WHERE attempt_id = :attempt_id
            """),
            {"attempt_id": attempt_id}
        ).fetchone()

        if existing:
            if existing.processing_status in ('completed', 'failed'):
                # Re-queue for re-analysis — clear stale results
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
                return jsonify({
                    "lifting_result_id": str(existing.id),
                    "status": "queued",
                    "message": "Re-queued for analysis"
                })
            else:
                return jsonify({
                    "lifting_result_id": str(existing.id),
                    "status": existing.processing_status,
                    "message": "Analysis already in progress"
                })

        # Create new LiftingResult
        result_id = str(uuid.uuid4())
        session.execute(
            sqlalchemy.text("""
                INSERT INTO "LiftingResult" (id, attempt_id, processing_status)
                VALUES (:id, :attempt_id, 'queued')
            """),
            {"id": result_id, "attempt_id": attempt_id}
        )
        session.commit()

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
                       lr.error_message, lr.created_at, lr.updated_at
                FROM "LiftingResult" lr
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
        })

    except Exception as e:
        logger.error(f"Error getting lifting result: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if session:
            session.close()
