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
logger = logging.getLogger(__name__)

def is_valid_uuid(val):
    """Check if a string is a valid UUID."""
    try:
        uuid.UUID(str(val))
        return True
    except (ValueError, AttributeError):
        return False

@attempt_bp.route('/attempts/<string:attempt_id>')
def get_attempt(attempt_id):
    """
    Endpoint that queries a single attempt by ID.
    """
    session = None
    try:
        # Validate UUID format
        if not is_valid_uuid(attempt_id):
            return {"error": "Invalid attempt ID format"}, 400
            
        session = get_db_connection()
        result = session.execute(
            sqlalchemy.text("SELECT * FROM \"Attempt\" WHERE id = :id"),
            {"id": attempt_id}
        ).fetchone()
        
        if result is None:
            return {"error": "Attempt not found"}, 404
            
        return {"attempt": dict(result)}
    except Exception as e:
        logger.error(f"Error getting attempt: {str(e)}")
        if session:
            session.rollback()
        return {"error": str(e)}, 500
    finally:
        if session:
            session.close()

@attempt_bp.route('/attempts', methods=['POST'])
def create_attempt():
    """
    Endpoint to create a new attempt.
    """
    session = None
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
        
        return {"message": "Attempt created successfully!", "attempt_id": attempt_id}, 201
    except Exception as e:
        logger.error(f"Error creating attempt: {str(e)}")
        if session:
            session.rollback()
        return {"error": str(e)}, 500
    finally:
        if session:
            session.close()

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
    session = None
    try:
        # Validate UUID format
        if not is_valid_uuid(attempt_id):
            return {"error": "Invalid attempt ID format"}, 400
            
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
            return {"error": "Attempt not found"}, 404
            
        session.commit()
        return {"message": "Attempt updated successfully!"}, 200
    except Exception as e:
        logger.error(f"Error updating attempt: {str(e)}")
        if session:
            session.rollback()
        return {"error": str(e)}, 500
    finally:
        if session:
            session.close()

@attempt_bp.route('/attempts/<string:attempt_id>', methods=['DELETE'])
def delete_attempt(attempt_id):
    """
    Endpoint to delete an attempt.
    """
    session = None
    try:
        # Validate UUID format
        if not is_valid_uuid(attempt_id):
            return {"error": "Invalid attempt ID format"}, 400
            
        session = get_db_connection()
        result = session.execute(
            sqlalchemy.text("DELETE FROM \"Attempt\" WHERE id = :id RETURNING id;"),
            {"id": attempt_id}
        )
        
        if result.rowcount == 0:
            return {"error": "Attempt not found"}, 404
            
        session.commit()
        return {"message": "Attempt deleted successfully!"}, 200
    except Exception as e:
        logger.error(f"Error deleting attempt: {str(e)}")
        if session:
            session.rollback()
        return {"error": str(e)}, 500
    finally:
        if session:
            session.close() 