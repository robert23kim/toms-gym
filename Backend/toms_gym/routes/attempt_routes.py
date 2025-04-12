from flask import Blueprint, request, jsonify
import sqlalchemy
from toms_gym.db import get_db_connection, Session
from google.cloud import storage
import random
import datetime
import urllib.parse
import os
import logging
import uuid

attempt_bp = Blueprint('attempt', __name__)

@attempt_bp.route('/attempts/<string:attempt_id>')
def get_attempt(attempt_id):
    """
    Endpoint that queries a single attempt by ID.
    """
    try:
        session = get_db_connection()
        result = session.execute(
            sqlalchemy.text("SELECT * FROM \"Attempt\" WHERE id = :id"),
            {"id": attempt_id}
        ).fetchone()
        session.close()
        
        if result is None:
            return {"error": "Attempt not found"}, 404
            
        return {"attempt": dict(result)}
    except Exception as e:
        return {"error": str(e)}, 500

@attempt_bp.route('/attempts', methods=['POST'])
def create_attempt():
    """
    Endpoint to create a new attempt.
    """
    try:
        request_data = request.json
        
        # Generate a UUID for the attempt
        attempt_id = str(uuid.uuid4())
        
        # Map incoming fields
        data = {
            "id": attempt_id,
            "user_competition_id": request_data.get("user_competition_id"),
            "lift_type": request_data.get("lift_type"),
            "weight_kg": request_data.get("weight_kg"),
            "status": request_data.get("status", "pending"),
            "video_url": request_data.get("video_url")
        }
        
        session = get_db_connection()
        result = session.execute(
            sqlalchemy.text("""
                INSERT INTO "Attempt" (id, user_competition_id, lift_type, weight_kg, status, video_url)
                VALUES (:id, :user_competition_id, :lift_type, :weight_kg, :status, :video_url)
                RETURNING id;
            """),
            data
        )
        attempt_id = result.fetchone()[0]
        session.commit()
        session.close()
        
        return {"message": "Attempt created successfully!", "attempt_id": attempt_id}, 201
    except Exception as e:
        return {"error": str(e)}, 500

# Add an alias for submit_attempt that maps to create_attempt for compatibility with tests
@attempt_bp.route('/submit_attempt', methods=['POST'])
def submit_attempt():
    """
    Endpoint alias for creating a new attempt.
    """
    response, status_code = create_attempt()
    # Adjust message for test compatibility if needed
    if isinstance(response, dict) and "message" in response and response["message"] == "Attempt created successfully!":
        response["message"] = "Attempt submitted successfully!"
    
    return response, status_code

@attempt_bp.route('/attempts/<string:attempt_id>', methods=['PUT'])
def update_attempt(attempt_id):
    """
    Endpoint to update an existing attempt.
    """
    try:
        request_data = request.json
        data = {
            "attempt_id": attempt_id,
            "lift_type": request_data.get("lift_type"),
            "weight_kg": request_data.get("weight_kg"),
            "status": request_data.get("status"),
            "video_url": request_data.get("video_url")
        }
        
        session = get_db_connection()
        result = session.execute(
            sqlalchemy.text("""
                UPDATE "Attempt"
                SET lift_type = :lift_type,
                    weight_kg = :weight_kg,
                    status = :status,
                    video_url = :video_url
                WHERE id = :attempt_id
                RETURNING id;
            """),
            data
        )
        
        if result.rowcount == 0:
            session.close()
            return {"error": "Attempt not found"}, 404
            
        session.commit()
        session.close()
        return {"message": "Attempt updated successfully!"}, 200
    except Exception as e:
        return {"error": str(e)}, 500

@attempt_bp.route('/attempts/<string:attempt_id>', methods=['DELETE'])
def delete_attempt(attempt_id):
    """
    Endpoint to delete an attempt.
    """
    try:
        session = get_db_connection()
        result = session.execute(
            sqlalchemy.text("DELETE FROM \"Attempt\" WHERE id = :id RETURNING id;"),
            {"id": attempt_id}
        )
        
        if result.rowcount == 0:
            session.close()
            return {"error": "Attempt not found"}, 404
            
        session.commit()
        session.close()
        return {"message": "Attempt deleted successfully!"}, 200
    except Exception as e:
        return {"error": str(e)}, 500 