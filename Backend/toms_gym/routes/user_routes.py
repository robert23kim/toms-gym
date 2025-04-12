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

user_bp = Blueprint('user', __name__)

@user_bp.route('/users/<string:user_id>')
def get_user(user_id):
    """
    Endpoint that queries a single user by ID.
    """
    try:
        session = get_db_connection()
        result = session.execute(
            sqlalchemy.text("SELECT * FROM \"User\" WHERE id = :id"),
            {"id": user_id}
        ).fetchone()
        session.close()
        
        if result is None:
            return {"error": "User not found"}, 404
            
        # Convert result to dict properly
        user_data = {}
        for key in result._mapping.keys():
            user_data[key] = result._mapping[key]
            
        return {"user": user_data}
    except Exception as e:
        return {"error": str(e)}, 500

@user_bp.route('/users/<string:user_id>/competitions')
def get_user_competitions(user_id):
    """
    Endpoint that queries all competitions for a specific user.
    """
    try:
        session = get_db_connection()
        result = session.execute(
            sqlalchemy.text("""
                SELECT c.*, uc.weight_class
                FROM "UserCompetition" uc
                JOIN "Competition" c ON uc.competition_id = c.id
                WHERE uc.user_id = :user_id
            """),
            {"user_id": user_id}
        )
        results = [dict(row) for row in result]
        session.close()
        return {"competitions": results}
    except Exception as e:
        return {"error": str(e)}, 500

@user_bp.route('/users/<string:user_id>/lifts')
def get_user_lifts(user_id):
    """
    Endpoint that queries all lifts for a specific user.
    """
    try:
        session = get_db_connection()
        result = session.execute(
            sqlalchemy.text("""
                SELECT a.id, uc.competition_id,
                       a.lift_type, a.weight_kg as weight, a.status,
                       a.video_url
                FROM "Attempt" a
                JOIN "UserCompetition" uc ON a.user_competition_id = uc.id
                WHERE uc.user_id = :user_id
            """),
            {"user_id": user_id}
        )
        results = [dict(row) for row in result]
        session.close()
        return {"lifts": results}
    except Exception as e:
        return {"error": str(e)}, 500

@user_bp.route('/users/<string:user_id>/profile')
def get_user_profile(user_id):
    """
    Endpoint that queries a user's profile including their competition history and achievements.
    """
    try:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Fetching profile for user_id: {user_id}")
        
        # Get user basic info
        user_data = {}
        try:
            session = get_db_connection()
            user_row = session.execute(
                sqlalchemy.text("SELECT * FROM \"User\" WHERE id = :user_id"),
                {"user_id": user_id}
            ).fetchone()
            
            if user_row is None:
                return jsonify({"error": "User not found"}), 404
            
            # Convert to dict properly with explicit handling of non-serializable types
            try:
                for key in user_row._mapping.keys():
                    value = user_row._mapping[key]
                    # Handle datetime objects
                    if isinstance(value, (datetime.datetime, datetime.date)):
                        user_data[key] = value.isoformat()
                    else:
                        user_data[key] = value
            except Exception as e:
                logger.error(f"Error converting user data: {str(e)}")
                user_data = {
                    "id": user_id,
                    "name": "Unknown",
                    "email": "unknown@example.com"
                }
            session.close()
        except Exception as e:
            logger.error(f"Error fetching user data: {str(e)}")
            user_data = {
                "id": user_id,
                "name": "Unknown",
                "email": "unknown@example.com"
            }

        # Get user's competition history
        competitions_list = []
        try:
            session = get_db_connection()
            competitions = session.execute(
                sqlalchemy.text("""
                    SELECT c.id, c.name, c.start_date, c.end_date, c.description,
                           uc.weight_class, c.status,
                           COALESCE(SUM(CASE WHEN a.status = 'completed' THEN a.weight_kg ELSE 0 END), 0) as total_weight,
                           COUNT(DISTINCT CASE WHEN a.status = 'completed' THEN a.lift_type END) as successful_lifts
                    FROM "UserCompetition" uc
                    JOIN "Competition" c ON uc.competition_id = c.id
                    LEFT JOIN "Attempt" a ON uc.id = a.user_competition_id
                    WHERE uc.user_id = :user_id
                    GROUP BY c.id, c.name, c.start_date, c.end_date, c.description, uc.weight_class, c.status
                    ORDER BY c.start_date DESC
                """),
                {"user_id": user_id}
            ).fetchall()
            
            # Convert result rows to dicts with serializable values
            try:
                for row in competitions:
                    comp_dict = {}
                    for key in row._mapping.keys():
                        value = row._mapping[key]
                        # Handle non-serializable types
                        if isinstance(value, (datetime.datetime, datetime.date)):
                            comp_dict[key] = value.isoformat()
                        else:
                            comp_dict[key] = value
                    competitions_list.append(comp_dict)
            except Exception as e:
                logger.error(f"Error processing competitions: {str(e)}")
            
            session.close()
        except Exception as e:
            logger.error(f"Error fetching competition history: {str(e)}")

        # Get user's best lifts
        best_lifts_list = []
        try:
            session = get_db_connection()
            best_lifts = session.execute(
                sqlalchemy.text("""
                    SELECT a.lift_type as type,
                           MAX(a.weight_kg) as best_weight,
                           c.name as competition_name,
                           c.id as competition_id
                    FROM "Attempt" a
                    JOIN "UserCompetition" uc ON a.user_competition_id = uc.id
                    JOIN "Competition" c ON uc.competition_id = c.id
                    WHERE uc.user_id = :user_id
                    AND a.status = 'completed'
                    GROUP BY a.lift_type, c.name, c.id
                """),
                {"user_id": user_id}
            ).fetchall()
            
            # Convert to dicts
            try:
                for row in best_lifts:
                    lift_dict = {}
                    for key in row._mapping.keys():
                        value = row._mapping[key]
                        # Handle non-serializable types
                        if isinstance(value, (datetime.datetime, datetime.date)):
                            lift_dict[key] = value.isoformat()
                        else:
                            lift_dict[key] = value
                    best_lifts_list.append(lift_dict)
            except Exception as e:
                logger.error(f"Error processing best lifts: {str(e)}")
            
            session.close()
        except Exception as e:
            logger.error(f"Error fetching best lifts: {str(e)}")

        # Get user's achievements
        achievements_dict = {
            "total_competitions": 0,
            "total_successful_lifts": 0,
            "heaviest_lift": 0,
            "best_snatch": 0,
            "best_clean_and_jerk": 0
        }
        
        try:
            session = get_db_connection()
            achievements = session.execute(
                sqlalchemy.text("""
                    SELECT 
                        COALESCE(COUNT(DISTINCT c.id), 0) as total_competitions,
                        COALESCE(COUNT(DISTINCT CASE WHEN a.status = 'completed' THEN a.lift_type END), 0) as total_successful_lifts,
                        COALESCE(MAX(a.weight_kg), 0) as heaviest_lift,
                        COALESCE(COUNT(DISTINCT CASE WHEN a.status = 'completed' AND a.lift_type = 'snatch' THEN a.lift_type END), 0) as best_snatch,
                        COALESCE(COUNT(DISTINCT CASE WHEN a.status = 'completed' AND a.lift_type = 'clean_and_jerk' THEN a.lift_type END), 0) as best_clean_and_jerk
                    FROM \"User\" u
                    LEFT JOIN "UserCompetition" uc ON u.id = uc.user_id
                    LEFT JOIN "Competition" c ON uc.competition_id = c.id
                    LEFT JOIN "Attempt" a ON uc.id = a.user_competition_id
                    WHERE u.id = :user_id
                """),
                {"user_id": user_id}
            ).fetchone()
            
            try:
                if achievements:
                    for key in achievements._mapping.keys():
                        achievements_dict[key] = achievements._mapping[key]
            except Exception as e:
                logger.error(f"Error processing achievements: {str(e)}")
            
            session.close()
        except Exception as e:
            logger.error(f"Error fetching achievements: {str(e)}")
            
        return jsonify({
            "user": user_data,
            "competitions": competitions_list,
            "best_lifts": best_lifts_list,
            "achievements": achievements_dict
        })
    except Exception as e:
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f"Error in get_user_profile: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500 