from flask import Blueprint, request, jsonify
import sqlalchemy
from db import pool

attempt_bp = Blueprint('attempt', __name__)

@attempt_bp.route('/submit_attempt', methods=['POST'])
def submit_attempt():
    """
    Endpoint to submit an attempt for a competition.
    Expects JSON payload with attempt details.
    """
    try:
        data = request.json
        insert_query = sqlalchemy.text(
            """
            INSERT INTO Attempts (usercompetitionid, lift_type, weight_attempted, attempt_number, attempt_result, video_link)
            VALUES (:usercompetitionid, :lift_type, :weight_attempted, :attempt_number, :attempt_result, :video_link)
            RETURNING attemptid;
            """
        )

        with pool.connect() as conn:
            result = conn.execute(insert_query, data)
            attempt_id = result.fetchone()[0]
            conn.commit()

        return {"message": "Attempt submitted successfully!", "attempt_id": attempt_id}, 201
    except Exception as e:
        return {"error": str(e)}, 500 