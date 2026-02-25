"""
Bowling Routes for Tom's Gym

Handles bowling video uploads, result retrieval, and competition leaderboards.
"""

import json
import os
import uuid
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import sqlalchemy

from toms_gym.db import get_db_connection
from toms_gym.storage import bucket, ALLOWED_EXTENSIONS

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bowling_bp = Blueprint('bowling', __name__, url_prefix='/bowling')


def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@bowling_bp.route('/upload', methods=['POST'])
def upload_bowling_video():
    """
    Upload a bowling video for processing.

    Accepts multipart form: video file, competition_id, user_id OR email.
    Creates Attempt + BowlingResult and queues for processing.
    """
    # Validate video file
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400

    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if not _allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    competition_id = request.form.get('competition_id')
    user_id = request.form.get('user_id')
    email = request.form.get('email')

    if not competition_id:
        return jsonify({'error': 'competition_id is required'}), 400

    # Resolve user: user_id > email lookup > auto-create from email
    session = get_db_connection()
    try:
        if not user_id and email:
            # Look up existing user by email
            user_row = session.execute(
                sqlalchemy.text('SELECT id FROM "User" WHERE LOWER(email) = :email'),
                {"email": email.lower()}
            ).fetchone()

            if user_row:
                user_id = str(user_row[0])
                logger.info(f"Found existing user by email: {user_id}")
            else:
                # Auto-create user from email
                user_id = str(uuid.uuid4())
                name = email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
                session.execute(
                    sqlalchemy.text("""
                        INSERT INTO "User" (id, email, name, username, auth_method, status, role, created_at)
                        VALUES (:id, :email, :name, :username, 'email', 'active', 'user', NOW())
                    """),
                    {
                        "id": user_id,
                        "email": email.lower(),
                        "name": name,
                        "username": email.lower(),
                    }
                )
                session.commit()
                logger.info(f"Auto-created user: {user_id} for email {email}")

        if not user_id:
            return jsonify({'error': 'user_id or email is required'}), 400

        # Find or create UserCompetition
        uc_row = session.execute(
            sqlalchemy.text("""
                SELECT id FROM "UserCompetition"
                WHERE user_id = :user_id AND competition_id = :competition_id
            """),
            {"user_id": user_id, "competition_id": competition_id}
        ).fetchone()

        if uc_row:
            user_competition_id = str(uc_row[0])
        else:
            user_competition_id = str(uuid.uuid4())
            session.execute(
                sqlalchemy.text("""
                    INSERT INTO "UserCompetition" (id, user_id, competition_id, weight_class, gender)
                    VALUES (:id, :user_id, :competition_id, '85kg', 'male')
                """),
                {
                    "id": user_competition_id,
                    "user_id": user_id,
                    "competition_id": competition_id,
                }
            )
            session.commit()
            logger.info(f"Created UserCompetition: {user_competition_id}")

        # Upload video to GCS
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        original_filename = secure_filename(file.filename)
        gcs_path = f'bowling/input/{timestamp}_{original_filename}'

        blob = bucket.blob(gcs_path)
        content_type = file.content_type or 'video/mp4'
        blob.upload_from_string(file.read(), content_type=content_type)
        video_url = f'https://storage.googleapis.com/{bucket.name}/{gcs_path}'
        logger.info(f"Uploaded bowling video: {video_url}")

        # Create Attempt
        attempt_id = str(uuid.uuid4())
        session.execute(
            sqlalchemy.text("""
                INSERT INTO "Attempt" (id, user_competition_id, lift_type, weight_kg, status, video_url)
                VALUES (:id, :user_competition_id, 'Bowling', 0, 'pending', :video_url)
                RETURNING id
            """),
            {
                "id": attempt_id,
                "user_competition_id": user_competition_id,
                "video_url": video_url,
            }
        )
        session.commit()

        # Create BowlingResult (queued for processing)
        bowling_result_id = str(uuid.uuid4())
        session.execute(
            sqlalchemy.text("""
                INSERT INTO "BowlingResult" (id, attempt_id, processing_status)
                VALUES (:id, :attempt_id, 'queued')
                RETURNING id
            """),
            {
                "id": bowling_result_id,
                "attempt_id": attempt_id,
            }
        )
        session.commit()

        logger.info(f"Created bowling attempt={attempt_id}, result={bowling_result_id}")

        return jsonify({
            'attempt_id': attempt_id,
            'bowling_result_id': bowling_result_id,
            'video_url': video_url,
        }), 200

    except Exception as e:
        session.rollback()
        logger.error(f"Error in bowling upload: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@bowling_bp.route('/result/<attempt_id>', methods=['GET'])
def get_bowling_result(attempt_id):
    """Get bowling processing result for an attempt."""
    session = get_db_connection()
    try:
        row = session.execute(
            sqlalchemy.text("""
                SELECT id, attempt_id, processing_status, debug_video_url,
                       trajectory_png_url, board_at_pins, entry_board,
                       processing_time_s, detection_rate, error_message,
                       created_at, updated_at,
                       lane_edges_auto, lane_edges_manual, frame_url
                FROM "BowlingResult"
                WHERE attempt_id = :attempt_id
            """),
            {"attempt_id": attempt_id}
        ).fetchone()

        if not row:
            return jsonify({'error': 'Bowling result not found'}), 404

        return jsonify({
            'id': str(row[0]),
            'attempt_id': str(row[1]),
            'processing_status': row[2],
            'debug_video_url': row[3],
            'trajectory_png_url': row[4],
            'board_at_pins': float(row[5]) if row[5] is not None else None,
            'entry_board': float(row[6]) if row[6] is not None else None,
            'processing_time_s': float(row[7]) if row[7] is not None else None,
            'detection_rate': float(row[8]) if row[8] is not None else None,
            'error_message': row[9],
            'created_at': str(row[10]) if row[10] else None,
            'updated_at': str(row[11]) if row[11] else None,
            'lane_edges_auto': row[12],
            'lane_edges_manual': row[13],
            'frame_url': row[14],
        }), 200

    except Exception as e:
        logger.error(f"Error fetching bowling result: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@bowling_bp.route('/results', methods=['GET'])
def get_bowling_results():
    """
    Get all bowling results for a competition.

    Query param: competition_id (required)
    Returns array of results with user info.
    """
    competition_id = request.args.get('competition_id')
    if not competition_id:
        return jsonify({'error': 'competition_id query parameter is required'}), 400

    session = get_db_connection()
    try:
        rows = session.execute(
            sqlalchemy.text("""
                SELECT
                    br.id,
                    br.attempt_id,
                    br.processing_status,
                    br.debug_video_url,
                    br.trajectory_png_url,
                    br.board_at_pins,
                    br.entry_board,
                    br.processing_time_s,
                    br.detection_rate,
                    br.error_message,
                    br.created_at,
                    u.name AS user_name,
                    u.email AS user_email
                FROM "BowlingResult" br
                JOIN "Attempt" a ON a.id = br.attempt_id
                JOIN "UserCompetition" uc ON uc.id = a.user_competition_id
                JOIN "User" u ON u.id = uc.user_id
                WHERE uc.competition_id = :competition_id
                ORDER BY br.created_at DESC
            """),
            {"competition_id": competition_id}
        ).fetchall()

        results = []
        for row in rows:
            results.append({
                'id': str(row[0]),
                'attempt_id': str(row[1]),
                'processing_status': row[2],
                'debug_video_url': row[3],
                'trajectory_png_url': row[4],
                'board_at_pins': float(row[5]) if row[5] is not None else None,
                'entry_board': float(row[6]) if row[6] is not None else None,
                'processing_time_s': float(row[7]) if row[7] is not None else None,
                'detection_rate': float(row[8]) if row[8] is not None else None,
                'error_message': row[9],
                'created_at': str(row[10]) if row[10] else None,
                'user_name': row[11],
                'user_email': row[12],
            })

        return jsonify(results), 200

    except Exception as e:
        logger.error(f"Error fetching bowling results: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@bowling_bp.route('/result/<result_id>/lane-edges', methods=['PUT'])
def save_lane_edges(result_id):
    """Save manually corrected lane edges for a bowling result."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON body required'}), 400

    lane_edges = data.get('lane_edges')
    if not lane_edges:
        return jsonify({'error': 'lane_edges is required'}), 400

    # Validate shape
    required_keys = ['top_left', 'top_right', 'bottom_left', 'bottom_right']
    for key in required_keys:
        if key not in lane_edges:
            return jsonify({'error': f'Missing key: {key}'}), 400
        if not isinstance(lane_edges[key], list) or len(lane_edges[key]) != 2:
            return jsonify({'error': f'Invalid {key}: expected [x, y]'}), 400

    session = get_db_connection()
    try:
        session.execute(sqlalchemy.text("""
            UPDATE "BowlingResult"
            SET lane_edges_manual = :edges, updated_at = now()
            WHERE id = :id
        """), {
            "id": result_id,
            "edges": json.dumps(lane_edges),
        })
        session.commit()
        return jsonify({'status': 'saved'}), 200
    except Exception as e:
        session.rollback()
        logger.error(f"Error saving lane edges: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@bowling_bp.route('/result/<result_id>/reanalyze', methods=['POST'])
def reanalyze_bowling(result_id):
    """Re-queue a bowling result for processing with manual lane edges."""
    session = get_db_connection()
    try:
        # Verify result exists
        row = session.execute(sqlalchemy.text("""
            SELECT id, lane_edges_manual
            FROM "BowlingResult"
            WHERE id = :id
        """), {"id": result_id}).fetchone()

        if not row:
            return jsonify({'error': 'Result not found'}), 404

        # Re-queue for processing
        session.execute(sqlalchemy.text("""
            UPDATE "BowlingResult"
            SET processing_status = 'queued', updated_at = now()
            WHERE id = :id
        """), {"id": result_id})
        session.commit()

        return jsonify({'status': 'queued'}), 200
    except Exception as e:
        session.rollback()
        logger.error(f"Error reanalyzing bowling result: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()
