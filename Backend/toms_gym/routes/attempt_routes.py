from flask import Blueprint, request, jsonify
import sqlalchemy
from toms_gym.db import get_db_connection, Session
from google.cloud import storage
import random
import datetime
import urllib.parse
import os
import logging

attempt_bp = Blueprint('attempt', __name__)

@attempt_bp.route('/attempts/<int:attempt_id>')
def get_attempt(attempt_id):
    """
    Endpoint that queries a single attempt by ID.
    """
    try:
        session = get_db_connection()
        result = session.execute(
            sqlalchemy.text("SELECT * FROM Attempts WHERE attemptid = :id"),
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
        data = request.json
        session = get_db_connection()
        result = session.execute(
            sqlalchemy.text("""
                INSERT INTO Attempts (usercompetitionid, lift_type, weight_attempted, attempt_result, video_link)
                VALUES (:usercompetitionid, :lift_type, :weight_attempted, :attempt_result, :video_link)
                RETURNING attemptid;
            """),
            data
        )
        attempt_id = result.fetchone()[0]
        session.commit()
        session.close()
        
        return {"message": "Attempt created successfully!", "attempt_id": attempt_id}, 201
    except Exception as e:
        return {"error": str(e)}, 500

@attempt_bp.route('/attempts/<int:attempt_id>', methods=['PUT'])
def update_attempt(attempt_id):
    """
    Endpoint to update an existing attempt.
    """
    try:
        data = request.json
        data['attempt_id'] = attempt_id
        
        session = get_db_connection()
        result = session.execute(
            sqlalchemy.text("""
                UPDATE Attempts
                SET lift_type = :lift_type,
                    weight_attempted = :weight_attempted,
                    attempt_result = :attempt_result,
                    video_link = :video_link
                WHERE attemptid = :attempt_id
                RETURNING attemptid;
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

@attempt_bp.route('/attempts/<int:attempt_id>', methods=['DELETE'])
def delete_attempt(attempt_id):
    """
    Endpoint to delete an attempt.
    """
    try:
        session = get_db_connection()
        result = session.execute(
            sqlalchemy.text("DELETE FROM Attempts WHERE attemptid = :id RETURNING attemptid;"),
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