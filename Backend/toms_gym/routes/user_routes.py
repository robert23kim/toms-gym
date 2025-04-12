from flask import Blueprint, request, jsonify
import sqlalchemy
from toms_gym.db import get_db_connection, Session
from google.cloud import storage
import random
import datetime
import urllib.parse
import os
import logging

user_bp = Blueprint('user', __name__)

@user_bp.route('/create_user', methods=['POST'])
def create_user():
    """
    Endpoint to create a new user.
    Expects JSON payload with user details.
    """
    try:
        data = request.json
        if not data or not all(k in data for k in ['gender', 'name', 'email']):
            return jsonify({"error": "Missing required fields"}), 400

        insert_query = sqlalchemy.text(
            """
            INSERT INTO \"User\" (gender, name, email)
            VALUES (:gender, :name, :email)
            RETURNING userid;
            """
        )

        session = get_db_connection()
        result = session.execute(insert_query, data)
        user_id = result.fetchone()[0]
        session.commit()
        session.close()

        return jsonify({"message": "User created successfully!", "user_id": user_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@user_bp.route('/users/<int:user_id>')
def get_user(user_id):
    """
    Endpoint that queries a single user by ID.
    """
    try:
        session = get_db_connection()
        result = session.execute(
            sqlalchemy.text("SELECT * FROM \"User\" WHERE userid = :id"),
            {"id": user_id}
        ).fetchone()
        session.close()
        
        if result is None:
            return {"error": "User not found"}, 404
            
        return {"user": dict(result)}
    except Exception as e:
        return {"error": str(e)}, 500

@user_bp.route('/users/<int:user_id>/competitions')
def get_user_competitions(user_id):
    """
    Endpoint that queries all competitions for a specific user.
    """
    try:
        session = get_db_connection()
        result = session.execute(
            sqlalchemy.text("""
                SELECT c.*, uc.weight_class
                FROM UserCompetition uc
                JOIN Competition c ON uc.competitionid = c.id
                WHERE uc.userid = :user_id
            """),
            {"user_id": user_id}
        )
        results = [dict(row) for row in result]
        session.close()
        return {"competitions": results}
    except Exception as e:
        return {"error": str(e)}, 500

@user_bp.route('/users/<int:user_id>/lifts')
def get_user_lifts(user_id):
    """
    Endpoint that queries all lifts for a specific user.
    """
    try:
        session = get_db_connection()
        result = session.execute(
            sqlalchemy.text("""
                SELECT a.attemptid as id, uc.competitionid as competition_id,
                       a.lift_type as type, a.weight_attempted as weight, a.attempt_result as success,
                       a.video_link as video_url
                FROM Attempts a
                JOIN UserCompetition uc ON a.usercompetitionid = uc.usercompetitionid
                WHERE uc.userid = :user_id
            """),
            {"user_id": user_id}
        )
        results = [dict(row) for row in result]
        session.close()
        return {"lifts": results}
    except Exception as e:
        return {"error": str(e)}, 500

@user_bp.route('/users/<int:user_id>')
def get_user_profile(user_id):
    """
    Endpoint that queries a user's profile including their competition history and achievements.
    """
    try:
        session = get_db_connection()
        # Get user basic info
        user_row = session.execute(
            sqlalchemy.text("SELECT * FROM \"User\" WHERE userid = :user_id"),
            {"user_id": user_id}
        ).fetchone()
        
        if user_row is None:
            return jsonify({"error": "User not found"}), 404
        
        user_data = user_row._asdict()

        # Get user's competition history
        competitions = session.execute(
            sqlalchemy.text("""
                SELECT c.id, c.name, c.start_date, c.end_date, c.location,
                       uc.weight_class, uc.status,
                       COALESCE(SUM(CASE WHEN a.attempt_result = 'true' THEN a.weight_attempted ELSE 0 END), 0) as total_weight,
                       COUNT(DISTINCT CASE WHEN a.attempt_result = 'true' THEN a.lift_type END) as successful_lifts
                FROM UserCompetition uc
                JOIN Competition c ON uc.competitionid = c.id
                LEFT JOIN Attempts a ON uc.usercompetitionid = a.usercompetitionid
                WHERE uc.userid = :user_id
                GROUP BY c.id, c.name, c.start_date, c.end_date, c.location, uc.weight_class, uc.status
                ORDER BY c.start_date DESC
            """),
            {"user_id": user_id}
        ).fetchall()

        # Get user's best lifts
        best_lifts = session.execute(
            sqlalchemy.text("""
                SELECT a.lift_type as type,
                       MAX(a.weight_attempted) as best_weight,
                       c.name as competition_name,
                       c.id as competition_id
                FROM Attempts a
                JOIN UserCompetition uc ON a.usercompetitionid = uc.usercompetitionid
                JOIN Competition c ON uc.competitionid = c.id
                WHERE uc.userid = :user_id
                AND a.attempt_result = 'true'
                GROUP BY a.lift_type, c.name, c.id
            """),
            {"user_id": user_id}
        ).fetchall()

        # Get user's achievements
        achievements = session.execute(
            sqlalchemy.text("""
                SELECT 
                    COALESCE(COUNT(DISTINCT c.id), 0) as total_competitions,
                    COALESCE(COUNT(DISTINCT CASE WHEN a.attempt_result = 'true' THEN a.lift_type END), 0) as total_successful_lifts,
                    COALESCE(MAX(a.weight_attempted), 0) as heaviest_lift,
                    COALESCE(COUNT(DISTINCT CASE WHEN a.attempt_result = 'true' AND a.lift_type = 'Squat' THEN a.lift_type END), 0) as best_squat,
                    COALESCE(COUNT(DISTINCT CASE WHEN a.attempt_result = 'true' AND a.lift_type = 'Bench Press' THEN a.lift_type END), 0) as best_bench,
                    COALESCE(COUNT(DISTINCT CASE WHEN a.attempt_result = 'true' AND a.lift_type = 'Deadlift' THEN a.lift_type END), 0) as best_deadlift
                FROM \"User\" u
                LEFT JOIN UserCompetition uc ON u.userid = uc.userid
                LEFT JOIN Competition c ON uc.competitionid = c.id
                LEFT JOIN Attempts a ON uc.usercompetitionid = a.usercompetitionid
                WHERE u.userid = :user_id
            """),
            {"user_id": user_id}
        ).fetchone()

        session.close()
        return jsonify({
            "user": user_data,
            "competitions": [row._asdict() for row in competitions] if competitions else [],
            "best_lifts": [row._asdict() for row in best_lifts] if best_lifts else [],
            "achievements": achievements._asdict() if achievements else {
                "total_competitions": 0,
                "total_successful_lifts": 0,
                "heaviest_lift": 0,
                "best_squat": 0,
                "best_bench": 0,
                "best_deadlift": 0
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500 