"""Cloud Tasks push handlers for analysis jobs.

Cloud Tasks POSTs here with an OIDC token (see services/analysis_dispatch.py).
Handlers run the same process functions the daemon pollers used; Cloud Tasks
owns retries: 200 = done/don't retry, 500 = retry (up to queue max-attempts).
"""
import logging
import os

import sqlalchemy
from flask import Blueprint, jsonify, request

jobs_bp = Blueprint('jobs', __name__, url_prefix='/jobs')
logger = logging.getLogger(__name__)


def _verify_oidc(req) -> bool:
    """Verify the Cloud Tasks OIDC token: audience + expected service account."""
    auth = req.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return False
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as gauth_requests
        claims = id_token.verify_oauth2_token(
            auth.split(' ', 1)[1],
            gauth_requests.Request(),
            audience=os.environ.get('TASKS_TARGET_BASE_URL', ''),
        )
        return (claims.get('email') == os.environ.get('TASKS_SERVICE_ACCOUNT', '')
                and claims.get('email_verified', False))
    except Exception as e:
        logger.warning(f"/jobs OIDC verification failed: {e}")
        return False


def _load_and_mark_processing(select_sql, update_sql, result_id):
    """Fetch the job row and flip it to 'processing'. Returns row or None."""
    from toms_gym.db import get_db_connection
    session = get_db_connection()
    try:
        row = session.execute(sqlalchemy.text(select_sql), {"id": result_id}).fetchone()
        if not row or row.processing_status == 'completed':
            return row, False
        session.execute(sqlalchemy.text(update_sql), {"id": result_id})
        session.commit()
        return row, True
    finally:
        session.close()


def _final_status(table, result_id):
    from toms_gym.db import get_db_connection
    session = get_db_connection()
    try:
        return session.execute(
            sqlalchemy.text(f'SELECT processing_status FROM "{table}" WHERE id = :id'),
            {"id": result_id},
        ).scalar()
    finally:
        session.close()


@jobs_bp.route('/lifting/<string:result_id>', methods=['POST'])
def run_lifting_job(result_id):
    if not _verify_oidc(request):
        return jsonify({"error": "unauthorized"}), 403
    row, should_run = _load_and_mark_processing(
        """
        SELECT lr.id, lr.attempt_id, lr.processing_status, a.video_url, a.lift_type
        FROM "LiftingResult" lr JOIN "Attempt" a ON a.id = lr.attempt_id
        WHERE lr.id = :id
        """,
        'UPDATE "LiftingResult" SET processing_status = \'processing\', updated_at = now() WHERE id = :id',
        result_id,
    )
    if row is None:
        return jsonify({"status": "gone"}), 200  # deleted row: don't retry
    if not should_run:
        return jsonify({"status": "already completed"}), 200

    from toms_gym.db import get_db_connection
    from toms_gym.integrations import lifting_processor
    lifting_processor._process_job(get_db_connection, row.id, row.attempt_id,
                                   row.video_url, row.lift_type)

    status = _final_status("LiftingResult", result_id)
    if status == 'completed':
        return jsonify({"status": "completed"}), 200
    return jsonify({"status": status}), 500  # Cloud Tasks retries


@jobs_bp.route('/bowling/<string:result_id>', methods=['POST'])
def run_bowling_job(result_id):
    if not _verify_oidc(request):
        return jsonify({"error": "unauthorized"}), 403
    row, should_run = _load_and_mark_processing(
        """
        SELECT br.id, br.attempt_id, br.processing_status, a.video_url, br.lane_edges_manual
        FROM "BowlingResult" br JOIN "Attempt" a ON a.id = br.attempt_id
        WHERE br.id = :id
        """,
        'UPDATE "BowlingResult" SET processing_status = \'processing\', updated_at = now() WHERE id = :id',
        result_id,
    )
    if row is None:
        return jsonify({"status": "gone"}), 200
    if not should_run:
        return jsonify({"status": "already completed"}), 200

    from toms_gym.integrations import bowling_processor
    bowling_processor.process_bowling_video(str(row.id), str(row.attempt_id),
                                            row.video_url, row.lane_edges_manual)

    status = _final_status("BowlingResult", result_id)
    if status == 'completed':
        return jsonify({"status": "completed"}), 200
    return jsonify({"status": status}), 500
