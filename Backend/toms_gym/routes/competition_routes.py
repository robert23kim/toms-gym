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

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use environment variable for bucket name
GCS_BUCKET_NAME = os.environ.get('GCS_BUCKET', 'jtr-lift-u-4ever-cool-bucket')

# Global variable to store video blobs
_video_blobs = []
_current_video_index = 0
_video_blobs_cache = None
_last_refresh_time = None

def _get_video_blobs():
    """
    Get a list of video blobs from the GCS bucket with caching.
    Refreshes the cache every 5 minutes.
    """
    global _video_blobs_cache, _last_refresh_time
    
    # Check if we need to refresh the cache
    current_time = datetime.datetime.now()
    if (_video_blobs_cache is None or 
        _last_refresh_time is None or 
        (current_time - _last_refresh_time).total_seconds() > 300):  # 5 minutes
        
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
            _last_refresh_time = current_time
            
            logger.info(f"Found {len(_video_blobs_cache)} videos in bucket")
        except Exception as e:
            logger.error(f"Error refreshing video blobs: {str(e)}")
            # If we have a cached version, use it; otherwise return empty list
            if _video_blobs_cache is None:
                _video_blobs_cache = []
    
    return _video_blobs_cache

def _get_video_data(blob):
    """Helper function to create video response data"""
    # Create a public URL with https to ensure it works on all browsers
    # The format is https://storage.googleapis.com/BUCKET_NAME/OBJECT_NAME
    url = f"https://storage.googleapis.com/{blob.bucket.name}/{blob.name}"
    
    # For debugging - log the URL
    print(f"Generated video URL: {url}")
    
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
        session = get_db_connection()
        result = session.execute(
            sqlalchemy.text("SELECT * FROM \"Competition\" WHERE id = :id"),
            {"id": competition_id}
        ).fetchone()
        
        if result is None:
            return {"error": "Competition not found"}, 404
            
        # Convert result to dict properly with safer approach
        competition_data = {}
        for key in result._mapping.keys():
            competition_data[key] = result._mapping[key]
        
        # Try to extract metadata from description
        try:
            if competition_data.get('description') and ' - ' in competition_data['description']:
                parts = competition_data['description'].split(' - ', 1)
                if len(parts) == 2:
                    location, metadata_json = parts
                    try:
                        metadata = json.loads(metadata_json)
                        
                        # Add the metadata fields directly to the competition data
                        competition_data['location'] = location
                        competition_data['lifttypes'] = metadata.get('lifttypes', [])
                        competition_data['weightclasses'] = metadata.get('weightclasses', [])
                        competition_data['gender'] = metadata.get('gender', 'M')
                    except json.JSONDecodeError:
                        # If JSON parsing fails, just use the description as location
                        competition_data['location'] = competition_data.get('description', '')
                        competition_data['lifttypes'] = []
                        competition_data['weightclasses'] = []
                        competition_data['gender'] = 'M'
                else:
                    competition_data['location'] = competition_data.get('description', '')
                    competition_data['lifttypes'] = []
                    competition_data['weightclasses'] = []
                    competition_data['gender'] = 'M'
            else:
                # No metadata in description
                competition_data['location'] = competition_data.get('description', '')
                competition_data['lifttypes'] = []
                competition_data['weightclasses'] = []
                competition_data['gender'] = 'M'
        except Exception as e:
            logger.error(f"Error parsing competition metadata: {str(e)}")
            competition_data['location'] = competition_data.get('description', '')
            competition_data['lifttypes'] = []
            competition_data['weightclasses'] = []
            competition_data['gender'] = 'M'
        
        session.close()
        return {"competition": competition_data}
    except Exception as e:
        logger.error(f"Error fetching competition by ID: {str(e)}")
        return {"error": str(e)}, 500

@competition_bp.route('/competitions/<string:competition_id>/participants')
def get_competition_participants(competition_id):
    """
    Endpoint that queries all participants for a specific competition.
    """
    try:
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
        logger.error(f"Error fetching competition participants: {str(e)}")
        return {"error": str(e)}, 500

@competition_bp.route('/competitions/<string:competition_id>/lifts')
def get_competition_lifts(competition_id):
    """
    Endpoint that queries all lifts for a specific competition.
    """
    try:
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
        results = [dict(row) for row in result]
        session.close()
        return {"lifts": results}
    except Exception as e:
        return {"error": str(e)}, 500

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
                return jsonify({"error": "Attempt not found"}), 404
                
            # Convert row to dict
            result = {}
            for column, value in row._mapping.items():
                # Handle non-JSON serializable types
                if isinstance(value, (datetime.datetime, datetime.date)):
                    result[column] = value.isoformat()
                else:
                    result[column] = value
                    
            return jsonify(result)
        except Exception as e:
            logger.error(f"Database error getting attempt details: {str(e)}")
            raise
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Error getting attempt details: {str(e)}")
        return jsonify({"error": str(e)}), 500

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
        
        # Return the video data
        return jsonify(_get_video_data(blob))
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
        
        # Return the video data
        return jsonify(_get_video_data(blob))
    except Exception as e:
        logger.error(f"Error getting next video: {str(e)}")
        return jsonify({"error": str(e)}), 500

@competition_bp.route('/video/<path:video_path>')
def serve_video(video_path):
    """
    Endpoint to serve a video from GCS.
    For mobile devices, streams content directly.
    For desktop, redirects to a signed URL.
    """
    try:
        # Check if the request is from a mobile device
        is_mobile = 'mobile' in request.args or request.user_agent.platform in ['android', 'iphone', 'ipad']
        logger.info(f"Request is from mobile device: {is_mobile}")
        
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
        if clean_path.lower().endswith('.mov'):
            content_type = "video/quicktime"
        elif clean_path.lower().endswith('.webm'):
            content_type = "video/webm"
            
        logger.info(f"Content type: {content_type}")
        
        # Check if using local development environment
        is_local_env = os.environ.get('FLASK_ENV') == 'development' or os.environ.get('USE_MOCK_DB') == 'true'
        
        # Check for range request
        range_header = request.headers.get('Range', None)
        
        # For mobile devices, range requests, or in development mode, stream the content directly
        if is_mobile or range_header or is_local_env:
            logger.info(f"Streaming content directly (mobile={is_mobile}, range={bool(range_header)}, local={is_local_env})")
            
            # Get file size
            try:
                blob.reload()  # Refresh metadata
                file_size = blob.size
                
                if file_size is None or file_size == 0:
                    raise ValueError("Invalid file size")
            except Exception as size_error:
                logger.error(f"Error getting file size: {str(size_error)}")
                # Fallback - download the file and get its size
                content = blob.download_as_bytes()
                file_size = len(content)
                
                # Return the full content for non-range request
                if not range_header:
                    response = Response(
                        content,
                        mimetype=content_type,
                        content_type=content_type,
                        direct_passthrough=True
                    )
                    response.headers['Content-Length'] = str(file_size)
                    response.headers['Accept-Ranges'] = 'bytes'
                    
                    # Add common headers
                    response.headers['Content-Type'] = content_type
                    response.headers['Access-Control-Allow-Origin'] = '*'
                    response.headers['Access-Control-Allow-Methods'] = 'GET, HEAD, OPTIONS'
                    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Range, Content-Length, Accept-Ranges'
                    response.headers['Access-Control-Expose-Headers'] = 'Content-Range'
                    
                    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                        
                    return response
            
            # Handle range request
            if range_header:
                # Parse range header
                ranges = range_header.replace('bytes=', '').split('-')
                start_byte = int(ranges[0]) if ranges[0] else 0
                end_byte = int(ranges[1]) if len(ranges) > 1 and ranges[1] else file_size - 1
                
                # Ensure end byte doesn't exceed file size
                end_byte = min(end_byte, file_size - 1)
                
                # Calculate length of the response
                content_length = end_byte - start_byte + 1
                
                try:
                    # Download only the requested bytes
                    download_args = {"start": start_byte, "end": end_byte}
                    content = blob.download_as_bytes(**download_args)
                    
                    # Prepare response with correct status and headers
                    response = Response(
                        content,
                        status=206,
                        mimetype=content_type,
                        content_type=content_type,
                        direct_passthrough=True
                    )
                    
                    # Set Content-Range header
                    response.headers['Content-Range'] = f'bytes {start_byte}-{end_byte}/{file_size}'
                    response.headers['Content-Length'] = str(content_length)
                    response.headers['Accept-Ranges'] = 'bytes'
                except Exception as range_error:
                    logger.error(f"Range request failed: {str(range_error)}")
                    # Fallback to full download if range request fails
                    content = blob.download_as_bytes()
                    response = Response(
                        content,
                        mimetype=content_type,
                        content_type=content_type,
                        direct_passthrough=True
                    )
                    response.headers['Content-Length'] = str(len(content))
                    response.headers['Accept-Ranges'] = 'bytes'
            else:
                # Download full file for non-range requests
                content = blob.download_as_bytes()
                response = Response(
                    content,
                    mimetype=content_type,
                    content_type=content_type,
                    direct_passthrough=True
                )
                # Ensure Content-Length is set correctly
                content_length = len(content)
                response.headers['Content-Length'] = str(content_length)
                response.headers['Accept-Ranges'] = 'bytes'
            
            # Add common headers
            response.headers['Content-Type'] = content_type
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, HEAD, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Range, Content-Length, Accept-Ranges'
            response.headers['Access-Control-Expose-Headers'] = 'Content-Range'
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                
            return response
        else:
            # For desktop in production, use direct URL instead of signed URL
            # (Signed URL has been causing issues)
            logger.info("Using direct GCS URL for desktop")
            direct_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{clean_path}"
            
            # Add headers
            response = redirect(direct_url, code=302)
            response.headers['Content-Type'] = content_type
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, HEAD, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Range, Content-Length, Accept-Ranges'
            response.headers['Accept-Ranges'] = 'bytes'
            response.headers['Cache-Control'] = 'public, max-age=3600'
                
            return response
    except Exception as e:
        import traceback
        logger.error(f"Error serving video: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

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