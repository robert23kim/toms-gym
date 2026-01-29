from flask import Blueprint, request, jsonify, Response, redirect
import sqlalchemy
from toms_gym.db import get_db_connection, Session
from google.cloud import storage
import random
import datetime
import urllib.parse
import os
import logging
import json
import uuid
from toms_gym.config import Config
import time
import string
import traceback  # Add this import for detailed stack traces

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use environment variable for bucket name
GCS_BUCKET_NAME = Config.GCS_BUCKET_NAME
# Video base URL from config
VIDEO_BASE_URL = Config.VIDEO_BASE_URL
# Local development flag
LOCAL_DEV = Config.LOCAL_DEV

# Global variable to store video blobs
_video_blobs = []
_current_video_index = 0
_video_blobs_cache = []
_video_blobs_last_updated = 0
_video_cache_ttl = 3600  # 1 hour cache

# Helper function to detect mobile devices
def is_mobile_device(request):
    """Check if the request is coming from a mobile device"""
    user_agent_string = request.user_agent.string.lower() if request.user_agent else ''
    platform = request.user_agent.platform.lower() if request.user_agent else ''
    
    # Check common mobile indicators
    mobile_platforms = ['android', 'iphone', 'ipad']
    mobile_keywords = ['mobile', 'android', 'iphone', 'ipad', 'phone', 'tablet', 'wv']
    
    is_mobile = (
        'mobile' in request.args or 
        platform in mobile_platforms or
        any(keyword in user_agent_string for keyword in mobile_keywords)
    )
    
    # Also consider Linux with small viewport as mobile
    is_linux_mobile = (
        (platform == 'linux' or 'x11' in user_agent_string) and
        'mobile' in user_agent_string
    )
    
    logger.debug(f"Mobile detection: UA={user_agent_string[:100]}, Platform={platform}, IsMobile={is_mobile or is_linux_mobile}")
    return is_mobile or is_linux_mobile

def _get_video_blobs():
    """
    Get a list of video blobs from the GCS bucket with caching.
    Refreshes the cache every 5 minutes.
    """
    global _video_blobs_cache, _video_blobs_last_updated
    
    # Check if we need to refresh the cache
    current_time = time.time()  # Use timestamp instead of datetime
    if (_video_blobs_cache is None or 
        _video_blobs_last_updated is None or 
        (current_time - _video_blobs_last_updated) > 300):  # 5 minutes
        
        try:
            logger.info(f"Refreshing video blobs from bucket: {GCS_BUCKET_NAME}")
            storage_client = storage.Client()
            bucket = storage_client.bucket(GCS_BUCKET_NAME)
            
            # List all blobs in the videos folder
            all_blobs = list(bucket.list_blobs(prefix='videos/'))
            
            # Filter for video files only
            _video_blobs_cache = [
                b for b in all_blobs 
                if b.name.lower().endswith(('.mp4', '.mov', '.webm'))
            ]
            _video_blobs_last_updated = current_time
            
            logger.info(f"Found {len(_video_blobs_cache)} videos in bucket")
        except Exception as e:
            logger.error(f"Error refreshing video blobs: {str(e)}")
            # If we have a cached version, use it; otherwise return empty list
            if _video_blobs_cache is None:
                _video_blobs_cache = []
    
    return _video_blobs_cache

# Central function for video URL transformation
def transform_video_url(url, blob_name=None, force_production=False):
    """
    Transforms video URLs based on various conditions.
    
    Args:
        url: Original URL (could be localhost or cloud storage)
        blob_name: Optional blob name for direct path construction
        force_production: Whether to force using production URL
    
    Returns:
        Transformed URL appropriate for the environment and client
    """
    # If we're in development and client is mobile or forcing production URL
    if (LOCAL_DEV and (is_mobile_device(request) or 'mobile' in request.args)) or force_production:
        # Use the production URL with the video path
        video_path = blob_name
        
        # If no blob name provided, try to extract from URL
        if not video_path and ('storage.googleapis.com' in url or 'localhost' in url):
            # For GCS URLs
            if 'storage.googleapis.com' in url and GCS_BUCKET_NAME in url:
                parts = url.split(GCS_BUCKET_NAME + '/')
                if len(parts) > 1:
                    video_path = parts[1]
            # For localhost URLs
            elif 'localhost' in url and '/video/' in url:
                parts = url.split('/video/')
                if len(parts) > 1:
                    video_path = parts[1]
        
        # If we have a valid path, construct production URL
        if video_path:
            if not video_path.startswith('video/') and not video_path.startswith('/video/'):
                video_path = f"video/{video_path}"
            
            # Create the final production URL
            transformed_url = f"{VIDEO_BASE_URL}/{video_path}"
            logger.info(f"Transformed URL: {url} -> {transformed_url}")
            return transformed_url
    
    # No transformation needed, return original URL
    return url

def _get_video_data(blob):
    """Helper function to create video response data"""
    # Default to GCS URL
    url = f"https://storage.googleapis.com/{blob.bucket.name}/{blob.name}"
    
    # For debugging - log the URL
    logger.info(f"Generated video URL: {url}")
    
    return {
        "video_id": 1,
        "participant_id": 1,
        "competition_id": 1,
        "video_url": url,
        "participant_name": "Random Athlete",
        "lift_type": "snatch",
        "weight": 100,
        "status": "completed",
        "total_videos": len(_video_blobs_cache),
        "current_index": _current_video_index
    }

competition_bp = Blueprint('competition', __name__)

@competition_bp.route('/competitions')
def get_competitions():
    """
    Endpoint that queries all competitions.
    """
    try:
        session = get_db_connection()
        result = session.execute(sqlalchemy.text("SELECT * FROM \"Competition\""))
        # Explicitly convert each row to a dict to avoid conversion issues
        results = []
        for row in result:
            row_dict = {}
            for column, value in row._mapping.items():
                # Handle special types that might not be JSON serializable
                if isinstance(value, (datetime.datetime, datetime.date)):
                    row_dict[column] = value.isoformat()
                else:
                    row_dict[column] = value
            results.append(row_dict)
        session.close()
        return {"competitions": results}
    except Exception as e:
        logger.error(f"Error fetching competitions: {str(e)}")
        return {"error": str(e)}, 500

@competition_bp.route('/competitions/<string:competition_id>')
def get_competition_by_id(competition_id):
    """
    Endpoint that queries a single competition by ID.
    """
    try:
        logger.info(f"Fetching competition with ID: {competition_id}")
        session = get_db_connection()
        result = session.execute(
            sqlalchemy.text("SELECT * FROM \"Competition\" WHERE id = :id"),
            {"id": competition_id}
        ).fetchone()
        
        if result is None:
            logger.warning(f"Competition not found with ID: {competition_id}")
            return {"error": "Competition not found"}, 404
            
        # Log successful query
        logger.info(f"Found competition with ID: {competition_id}, name: {result._mapping.get('name', 'unknown')}")
        
        # Convert result to dict properly with safer approach
        competition_data = {}
        for key in result._mapping.keys():
            competition_data[key] = result._mapping[key]
            # Log column types for debugging
            logger.debug(f"Column {key}: value={result._mapping[key]}, type={type(result._mapping[key])}")
        
        # Try to extract metadata from description
        try:
            if competition_data.get('description') and ' - ' in competition_data['description']:
                logger.debug(f"Parsing description with metadata: {competition_data['description']}")
                parts = competition_data['description'].split(' - ', 1)
                if len(parts) == 2:
                    location, metadata_json = parts
                    try:
                        logger.debug(f"Attempting to parse JSON metadata: {metadata_json}")
                        metadata = json.loads(metadata_json)
                        
                        # Add the metadata fields directly to the competition data
                        competition_data['location'] = location
                        competition_data['lifttypes'] = metadata.get('lifttypes', [])
                        competition_data['weightclasses'] = metadata.get('weightclasses', [])
                        competition_data['gender'] = metadata.get('gender', 'M')
                        logger.debug(f"Successfully parsed metadata: {metadata}")
                    except json.JSONDecodeError as json_err:
                        # If JSON parsing fails, just use the description as location
                        logger.error(f"JSON parsing error in competition metadata: {str(json_err)}, metadata string: '{metadata_json}'")
                        competition_data['location'] = competition_data.get('description', '')
                        competition_data['lifttypes'] = []
                        competition_data['weightclasses'] = []
                        competition_data['gender'] = 'M'
                else:
                    logger.debug(f"Description doesn't contain metadata in expected format: {competition_data['description']}")
                    competition_data['location'] = competition_data.get('description', '')
                    competition_data['lifttypes'] = []
                    competition_data['weightclasses'] = []
                    competition_data['gender'] = 'M'
            else:
                # No metadata in description
                logger.debug(f"No metadata in description: {competition_data.get('description', 'None')}")
                competition_data['location'] = competition_data.get('description', '')
                competition_data['lifttypes'] = []
                competition_data['weightclasses'] = []
                competition_data['gender'] = 'M'
        except Exception as e:
            logger.error(f"Error parsing competition metadata: {str(e)}, traceback: {traceback.format_exc()}")
            competition_data['location'] = competition_data.get('description', '')
            competition_data['lifttypes'] = []
            competition_data['weightclasses'] = []
            competition_data['gender'] = 'M'
        
        session.close()
        logger.info(f"Successfully processed competition data for ID: {competition_id}")
        return {"competition": competition_data}
    except Exception as e:
        error_details = {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": traceback.format_exc(),
            "competition_id": competition_id,
            "request_path": request.path,
            "request_args": dict(request.args),
            "request_headers": {k: v for k, v in request.headers.items()},
        }
        logger.error(f"Error fetching competition by ID: {str(e)}")
        logger.error(f"Detailed error info: {json.dumps(error_details, default=str)}")
        return {"error": f"Server error: {type(e).__name__} - {str(e)}"}, 500

@competition_bp.route('/competitions/<string:competition_id>/participants')
def get_competition_participants(competition_id):
    """
    Endpoint that queries all participants for a specific competition.
    """
    try:
        logger.info(f"Fetching participants for competition ID: {competition_id}")
        session = get_db_connection()
        result = session.execute(
            sqlalchemy.text("""
                SELECT u.id, u.name, uc.weight_class,
                       COALESCE(SUM(CASE WHEN a.status = 'completed' THEN a.weight_kg ELSE 0 END), 0) as total_weight,
                       CASE 
                           WHEN COUNT(a.id) > 0 THEN 
                               json_agg(
                                   json_build_object(
                                       'lift_type', a.lift_type,
                                       'weight', a.weight_kg,
                                       'status', a.status
                                   )
                               )
                           ELSE '[]'::json
                       END as attempts
                FROM "UserCompetition" uc
                JOIN "User" u ON uc.user_id = u.id
                LEFT JOIN "Attempt" a ON uc.id = a.user_competition_id
                WHERE uc.competition_id = :competition_id
                GROUP BY u.id, u.name, uc.weight_class
            """),
            {"competition_id": competition_id}
        )
        
        # Safely convert rows to dicts
        results = []
        for row in result:
            try:
                row_dict = {}
                for column, value in row._mapping.items():
                    # Handle special cases for JSON field
                    if column == 'attempts' and value is None:
                        row_dict[column] = []
                    else:
                        row_dict[column] = value
                results.append(row_dict)
            except Exception as e:
                logger.error(f"Error converting participant row to dict: {str(e)}")
                # Skip this row if there's an error
                continue
                
        session.close()
        return {"participants": results}
    except Exception as e:
        error_details = {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": traceback.format_exc(),
            "competition_id": competition_id,
            "request_path": request.path,
        }
        logger.error(f"Error fetching competition participants: {str(e)}")
        logger.error(f"Detailed error info: {json.dumps(error_details, default=str)}")
        return {"error": f"Server error: {type(e).__name__} - {str(e)}"}, 500

@competition_bp.route('/competitions/<string:competition_id>/lifts')
def get_competition_lifts(competition_id):
    """
    Endpoint that queries all lifts for a specific competition.
    """
    try:
        logger.info(f"Fetching lifts for competition ID: {competition_id}")
        session = get_db_connection()
        result = session.execute(
            sqlalchemy.text("""
                SELECT a.id, uc.user_id as participant_id, uc.competition_id,
                       a.lift_type, a.weight_kg as weight, a.status,
                       a.video_url
                FROM "Attempt" a
                JOIN "UserCompetition" uc ON a.user_competition_id = uc.id
                WHERE uc.competition_id = :competition_id
            """),
            {"competition_id": competition_id}
        )
        
        # Safer conversion from Row objects to dictionaries
        results = []
        for row in result:
            row_dict = {}
            for column, value in row._mapping.items():
                # Handle special types that might not be JSON serializable
                if isinstance(value, (datetime.datetime, datetime.date)):
                    row_dict[column] = value.isoformat()
                else:
                    row_dict[column] = value
            results.append(row_dict)
            
        session.close()
        logger.info(f"Successfully fetched {len(results)} lifts for competition {competition_id}")
        return {"lifts": results}
    except Exception as e:
        error_details = {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": traceback.format_exc(),
            "competition_id": competition_id,
            "request_path": request.path,
        }
        logger.error(f"Error fetching competition lifts: {str(e)}")
        logger.error(f"Detailed error info: {json.dumps(error_details, default=str)}")
        return {"error": f"Server error: {type(e).__name__} - {str(e)}"}, 500

@competition_bp.route('/create_competition', methods=['POST'])
def create_competition():
    """
    Endpoint to insert a new competition entry.
    Expects JSON payload with competition details.
    """
    try:
        request_data = request.json
        
        # Generate a UUID for the competition
        competition_id = str(uuid.uuid4())
        
        # Map incoming fields to expected database fields
        data = {
            "id": competition_id,  # Add the generated UUID
            "name": request_data.get("name"),
            "description": request_data.get("description", request_data.get("location", "")),  # Use location as fallback
            "start_date": request_data.get("start_date"),
            "end_date": request_data.get("end_date"),
            "status": request_data.get("status", "upcoming")  # Default status
        }
        
        # Store additional metadata as JSON in the description if needed
        if "lifttypes" in request_data or "weightclasses" in request_data or "gender" in request_data:
            metadata = {
                "lifttypes": request_data.get("lifttypes", []),
                "weightclasses": request_data.get("weightclasses", []),
                "gender": request_data.get("gender", "")
            }
            # Append metadata to description if description exists
            if data["description"]:
                data["description"] = f"{data['description']} - {json.dumps(metadata)}"
            else:
                data["description"] = json.dumps(metadata)
        
        session = get_db_connection()
        result = session.execute(
            sqlalchemy.text(
                """
                INSERT INTO "Competition" (id, name, description, start_date, end_date, status)
                VALUES (:id, :name, :description, :start_date, :end_date, :status)
                RETURNING id;
                """
            ),
            data
        )
        inserted_id = result.fetchone()[0]
        session.commit()
        session.close()

        return {"message": "Competition created successfully!", "competition_id": inserted_id}, 201
    except Exception as e:
        logger.error(f"Error creating competition: {str(e)}")
        return {"error": str(e)}, 500

@competition_bp.route('/competitions/<string:competition_id>', methods=['DELETE'])
def delete_competition(competition_id):
    """
    Endpoint to delete a competition by ID.
    This will cascade delete all associated UserCompetitions and Attempts.
    """
    try:
        logger.info(f"Deleting competition with ID: {competition_id}")
        session = get_db_connection()
        
        # First check if the competition exists
        result = session.execute(
            sqlalchemy.text("SELECT id, name FROM \"Competition\" WHERE id = :id"),
            {"id": competition_id}
        ).fetchone()
        
        if result is None:
            session.close()
            logger.warning(f"Competition not found with ID: {competition_id}")
            return {"error": "Competition not found"}, 404
        
        competition_name = result._mapping.get('name', 'unknown')
        
        # Delete the competition (cascades to UserCompetition and Attempt)
        session.execute(
            sqlalchemy.text("DELETE FROM \"Competition\" WHERE id = :id"),
            {"id": competition_id}
        )
        session.commit()
        session.close()
        
        logger.info(f"Successfully deleted competition: {competition_name} (ID: {competition_id})")
        return {"message": f"Competition '{competition_name}' deleted successfully", "competition_id": competition_id}, 200
    except Exception as e:
        logger.error(f"Error deleting competition: {str(e)}")
        return {"error": str(e)}, 500

@competition_bp.route('/competitions/cleanup', methods=['DELETE'])
def cleanup_competitions():
    """
    Endpoint to delete all competitions except the default one (ID '1').
    This will cascade delete all associated UserCompetitions and Attempts.
    Query params:
        - keep_id: ID of the competition to keep (default: '1')
    """
    try:
        keep_id = request.args.get('keep_id', '1')
        logger.info(f"Cleaning up competitions, keeping ID: {keep_id}")
        session = get_db_connection()
        
        # First get all competitions that will be deleted
        result = session.execute(
            sqlalchemy.text("SELECT id, name FROM \"Competition\" WHERE id != :keep_id"),
            {"keep_id": keep_id}
        )
        
        competitions_to_delete = []
        for row in result:
            competitions_to_delete.append({
                "id": row._mapping.get('id'),
                "name": row._mapping.get('name')
            })
        
        if not competitions_to_delete:
            session.close()
            return {"message": "No competitions to delete", "deleted": []}, 200
        
        # Delete all competitions except the one to keep
        session.execute(
            sqlalchemy.text("DELETE FROM \"Competition\" WHERE id != :keep_id"),
            {"keep_id": keep_id}
        )
        session.commit()
        session.close()
        
        logger.info(f"Successfully deleted {len(competitions_to_delete)} competitions")
        return {
            "message": f"Deleted {len(competitions_to_delete)} competitions, kept ID: {keep_id}",
            "deleted": competitions_to_delete,
            "kept_id": keep_id
        }, 200
    except Exception as e:
        logger.error(f"Error cleaning up competitions: {str(e)}")
        return {"error": str(e)}, 500

@competition_bp.route('/join_competition', methods=['POST'])
def join_competition():
    """
    Endpoint to join a competition.
    Expects JSON payload with user competition details.
    """
    try:
        request_data = request.json
        
        # Generate a UUID for the user competition
        usercomp_id = str(uuid.uuid4())
        
        # Prepare data with proper UUID format
        data = {
            "id": usercomp_id,
            "user_id": request_data.get("user_id"),
            "competition_id": request_data.get("competition_id"),
            "weight_class": request_data.get("weight_class"),
            "gender": request_data.get("gender")
        }
        
        insert_query = sqlalchemy.text(
            """
            INSERT INTO "UserCompetition" (id, user_id, competition_id, weight_class, gender)
            VALUES (:id, :user_id, :competition_id, :weight_class, :gender)
            RETURNING id;
            """
        )

        session = get_db_connection()
        try:
            result = session.execute(insert_query, data)
            user_competition_id = result.fetchone()[0]
            session.commit()
            
            return {"message": "Joined competition successfully!", "usercompetition_id": str(user_competition_id)}, 201
        except Exception as e:
            session.rollback()
            logger.error(f"Database error joining competition: {str(e)}")
            raise
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Error joining competition: {str(e)}")
        return {"error": str(e)}, 500

@competition_bp.route('/competitions/<string:competition_id>/participants/<string:participant_id>/attempts/<string:attempt_id>')
def get_attempt_details(competition_id, participant_id, attempt_id):
    """
    Endpoint that queries details for a specific attempt including video URL.
    """
    try:
        logger.info(f"Fetching attempt details: competition_id={competition_id}, participant_id={participant_id}, attempt_id={attempt_id}")
        session = get_db_connection()
        try:
            row = session.execute(
                sqlalchemy.text("""
                    SELECT a.id, 
                           uc.user_id as participant_id, 
                           uc.competition_id,
                           u.name as participant_name,
                           a.lift_type, 
                           a.weight_kg as weight, 
                           a.status,
                           a.video_url
                    FROM "Attempt" a
                    JOIN "UserCompetition" uc ON a.user_competition_id = uc.id
                    JOIN "User" u ON uc.user_id = u.id
                    WHERE uc.competition_id = :competition_id
                    AND uc.user_id = :participant_id
                    AND a.id = :attempt_id
                """),
                {
                    "competition_id": competition_id,
                    "participant_id": participant_id,
                    "attempt_id": attempt_id
                }
            ).fetchone()
            
            if not row:
                logger.warning(f"Attempt not found: competition_id={competition_id}, participant_id={participant_id}, attempt_id={attempt_id}")
                return jsonify({"error": "Attempt not found"}), 404
                
            # Convert row to dict
            result = {}
            for column, value in row._mapping.items():
                # Handle non-JSON serializable types
                if isinstance(value, (datetime.datetime, datetime.date)):
                    result[column] = value.isoformat()
                else:
                    result[column] = value
                
            # Process video URL if available
            if result.get('video_url'):
                logger.info(f"Original video URL: {result['video_url']}")
                
                # Ensure the URL is properly formatted
                video_url = result['video_url']
                
                # Detect if mobile client
                is_mobile = is_mobile_device(request)
                
                # Transform URL for client device
                if is_mobile:
                    logger.info(f"Mobile device detected, transforming URL")
                    video_url = transform_video_url(video_url)
                    result['video_url'] = video_url
                
                logger.info(f"Final video URL: {result['video_url']}")
            else:
                logger.warning(f"No video URL found for attempt: {attempt_id}")
            
            logger.info(f"Successfully retrieved attempt details for {attempt_id}")
            return jsonify(result)
        except Exception as e:
            logger.error(f"Database error getting attempt details: {str(e)}, traceback: {traceback.format_exc()}")
            raise
        finally:
            session.close()
    except Exception as e:
        error_details = {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": traceback.format_exc(),
            "competition_id": competition_id,
            "participant_id": participant_id,
            "attempt_id": attempt_id,
            "request_path": request.path,
            "request_args": dict(request.args),
            "request_headers": {k: v for k, v in request.headers.items()},
        }
        logger.error(f"Error getting attempt details: {str(e)}")
        logger.error(f"Detailed error info: {json.dumps(error_details, default=str)}")
        return jsonify({"error": f"Server error: {type(e).__name__} - {str(e)}"}), 500

@competition_bp.route('/random-video')
def get_random_video():
    """
    Endpoint that returns a random video from the bucket
    """
    global _current_video_index
    try:
        # Get video blobs with caching
        video_blobs = _get_video_blobs()
        
        if not video_blobs:
            return jsonify({"error": "No videos available"}), 404
            
        # Pick a random video
        index = random.randint(0, len(video_blobs) - 1)
        _current_video_index = index
        blob = video_blobs[index]
        
        # Get basic video data
        video_data = _get_video_data(blob)
        
        # Transform the URL before returning it to client
        video_data['video_url'] = transform_video_url(
            video_data['video_url'], 
            blob_name=blob.name
        )
        
        # Return the video data
        return jsonify(video_data)
    except Exception as e:
        logger.error(f"Error getting random video: {str(e)}")
        return jsonify({"error": str(e)}), 500

@competition_bp.route('/next-video')
def get_next_video():
    """
    Endpoint that returns the next video in sequence
    """
    global _current_video_index
    try:
        # Get video blobs with caching
        video_blobs = _get_video_blobs()
        
        if not video_blobs:
            return jsonify({"error": "No videos available"}), 404
            
        # Move to next video
        _current_video_index = (_current_video_index + 1) % len(video_blobs)
        blob = video_blobs[_current_video_index]
        
        # Get basic video data
        video_data = _get_video_data(blob)
        
        # Transform the URL before returning it to client
        video_data['video_url'] = transform_video_url(
            video_data['video_url'], 
            blob_name=blob.name
        )
        
        # Return the video data
        return jsonify(video_data)
    except Exception as e:
        logger.error(f"Error getting next video: {str(e)}")
        return jsonify({"error": str(e)}), 500

@competition_bp.route('/video/<path:video_path>')
def serve_video(video_path):
    """
    Endpoint to serve a video from GCS.
    For mobile devices, always use direct streaming for better compatibility.
    """
    try:
        # Use our helper to detect mobile devices
        is_mobile = is_mobile_device(request)
        is_android = 'android' in request.user_agent.string.lower() if request.user_agent else False
        is_linux = ('linux' in request.user_agent.platform.lower() if request.user_agent else False) or \
                   ('x11' in request.user_agent.string.lower() if request.user_agent else False)
        
        logger.info(f"Video request from: UA={request.user_agent.string[:100] if request.user_agent else 'Unknown'}")
        logger.info(f"Device detection: Mobile={is_mobile}, Android={is_android}, Linux={is_linux}")
        
        # Clean the path to ensure it's properly formatted
        clean_path = video_path.strip('/')
        if not clean_path.startswith('videos/'):
            clean_path = f"videos/{clean_path}"
        
        logger.info(f"Serving video: {clean_path}")
        
        # Get the video from GCS
        try:
            storage_client = storage.Client()
            bucket = storage_client.bucket(GCS_BUCKET_NAME)
            blob = bucket.blob(clean_path)
            
            if not blob.exists():
                logger.warning(f"Video not found at path: {clean_path}")
                # Try listing files in the bucket to debug
                all_blobs = list(bucket.list_blobs(prefix='videos/'))
                video_blobs = [b.name for b in all_blobs if b.name.lower().endswith(('.mp4', '.mov'))]
                logger.info(f"Available videos: {video_blobs[:10]}...")
                return jsonify({"error": "Video not found", "path": clean_path}), 404
        except Exception as blob_error:
            logger.error(f"Error accessing GCS: {str(blob_error)}")
            return jsonify({"error": "Storage access error", "details": str(blob_error)}), 500
            
        # Determine content type based on file extension
        content_type = "video/mp4"
        file_extension = clean_path.lower().split('.')[-1]
        
        if file_extension == 'mov':
            # For Android or Linux, use more compatible MIME type
            if is_android or is_linux:
                content_type = "video/mp4"  # More compatible with Android and Linux
                logger.info(f"Android or Linux detected, using content_type: {content_type}")
            else:
                content_type = "video/quicktime"
        elif file_extension == 'webm':
            content_type = "video/webm"
            
        logger.info(f"Content type: {content_type}")
        
        # Generate direct URL for access
        direct_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{clean_path}"
        
        # For mobile devices, transform URL if needed
        if is_mobile or 'mobile' in request.args:
            # Apply our URL transformation to ensure consistent handling 
            direct_url = transform_video_url(direct_url, blob_name=clean_path, force_production=True)
        
        # For all devices, use enhanced headers
        logger.info(f"Using direct GCS URL for {'mobile' if is_mobile else 'desktop'} device")
            
        # Create response with appropriate headers for the device
        response = redirect(direct_url, code=302)
        response.headers['Content-Type'] = content_type
        response.headers['Accept-Ranges'] = 'bytes'
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, HEAD, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Range, Content-Length, Accept-Ranges'
        response.headers['Access-Control-Expose-Headers'] = 'Content-Range, Content-Length, Accept-Ranges'
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            
        # For Android or Linux, set additional compatibility headers
        if is_android or is_linux:
            # Ensure proper caching and avoid unnecessary redirects
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['Content-Disposition'] = f'inline; filename="{clean_path.split("/")[-1]}"'
            logger.info(f"Adding {'Android' if is_android else 'Linux'}-specific headers for compatibility")
        
        # Add extra debug info in the headers
        response.headers['X-Video-Path'] = clean_path
        response.headers['X-Content-Type-Detected'] = content_type
        response.headers['X-Device-Type'] = 'mobile' if is_mobile else 'desktop'
        
        return response
                
    except Exception as e:
        logger.error(f"Error serving video: {str(e)}")
        return jsonify({"error": "Error serving video", "details": str(e)}), 500

@competition_bp.route('/health')
def health_check():
    """
    Simple health check endpoint for monitoring
    """
    return jsonify({
        "status": "healthy", 
        "timestamp": datetime.datetime.now().isoformat(),
        "service": "toms-gym-backend"
    }) 