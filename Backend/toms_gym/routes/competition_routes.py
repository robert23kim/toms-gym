from flask import Blueprint, request, jsonify, Response, redirect
import sqlalchemy
from toms_gym.db import pool
from google.cloud import storage
import random
import datetime
import urllib.parse
import os
import logging

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
        "lift_type": "Squat",
        "weight": 100,
        "success": True,
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
        with pool.connect() as conn:
            rows = conn.execute(sqlalchemy.text("SELECT * FROM Competition"))
            results = [row._asdict() for row in rows]
        return {"competitions": results}
    except Exception as e:
        return {"error": str(e)}, 500

@competition_bp.route('/competitions/<int:competition_id>')
def get_competition_by_id(competition_id):
    """
    Endpoint that queries a single competition by ID.
    """
    try:
        with pool.connect() as conn:
            row = conn.execute(
                sqlalchemy.text("SELECT * FROM Competition WHERE id = :id"),
                {"id": competition_id}
            ).fetchone()
            
            if row is None:
                return {"error": "Competition not found"}, 404
                
            result = row._asdict()
            return {"competition": result}
    except Exception as e:
        return {"error": str(e)}, 500

@competition_bp.route('/competitions/<int:competition_id>/participants')
def get_competition_participants(competition_id):
    """
    Endpoint that queries all participants for a specific competition.
    """
    try:
        with pool.connect() as conn:
            rows = conn.execute(
                sqlalchemy.text("""
                    SELECT u.userid, u.name, uc.weight_class,
                           COALESCE(SUM(CASE WHEN a.attempt_result = 'true' THEN a.weight_attempted ELSE 0 END), 0) as total_weight,
                           json_agg(
                               json_build_object(
                                   'lift_type', a.lift_type,
                                   'weight', a.weight_attempted,
                                   'success', a.attempt_result
                               )
                           ) as attempts
                    FROM UserCompetition uc
                    JOIN \"User\" u ON uc.userid = u.userid
                    LEFT JOIN Attempts a ON uc.usercompetitionid = a.usercompetitionid
                    WHERE uc.competitionid = :competition_id
                    GROUP BY u.userid, u.name, uc.weight_class
                """),
                {"competition_id": competition_id}
            )
            results = [row._asdict() for row in rows]
        return {"participants": results}
    except Exception as e:
        return {"error": str(e)}, 500

@competition_bp.route('/competitions/<int:competition_id>/lifts')
def get_competition_lifts(competition_id):
    """
    Endpoint that queries all lifts for a specific competition.
    """
    try:
        with pool.connect() as conn:
            rows = conn.execute(
                sqlalchemy.text("""
                    SELECT a.attemptid as id, uc.userid as participant_id, uc.competitionid as competition_id,
                           a.lift_type as type, a.weight_attempted as weight, a.attempt_result as success,
                           a.video_link as video_url
                    FROM Attempts a
                    JOIN UserCompetition uc ON a.usercompetitionid = uc.usercompetitionid
                    WHERE uc.competitionid = :competition_id
                """),
                {"competition_id": competition_id}
            )
            results = [row._asdict() for row in rows]
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
        data = request.json
        insert_query = sqlalchemy.text(
            """
            INSERT INTO Competition (name, location, lifttypes, weightclasses, gender, start_date, end_date)
            VALUES (:name, :location, :lifttypes, :weightclasses, :gender, :start_date, :end_date)
            RETURNING id;
            """
        )

        with pool.connect() as conn:
            result = conn.execute(insert_query, data)
            inserted_id = result.fetchone()[0]
            conn.commit()

        return {"message": "Competition created successfully!", "competition_id": inserted_id}, 201
    except Exception as e:
        return {"error": str(e)}, 500

@competition_bp.route('/join_competition', methods=['POST'])
def join_competition():
    """
    Endpoint to join a competition.
    Expects JSON payload with user competition details.
    """
    try:
        data = request.json
        insert_query = sqlalchemy.text(
            """
            INSERT INTO UserCompetition (userid, competitionid, weight_class, gender, age, status)
            VALUES (:userid, :competitionid, :weight_class, :gender, :age, :status)
            RETURNING usercompetitionid;
            """
        )

        with pool.connect() as conn:
            result = conn.execute(insert_query, data)
            user_competition_id = result.fetchone()[0]
            conn.commit()

        return {"message": "Joined competition successfully!", "usercompetition_id": user_competition_id}, 201
    except Exception as e:
        return {"error": str(e)}, 500

@competition_bp.route('/competitions/<int:competition_id>/participants/<int:participant_id>/attempts/<int:attempt_id>')
def get_attempt_details(competition_id, participant_id, attempt_id):
    """
    Endpoint that queries details for a specific attempt including video URL.
    """
    try:
        with pool.connect() as conn:
            row = conn.execute(
                sqlalchemy.text("""
                    SELECT a.attemptid as id, 
                           uc.userid as participant_id, 
                           uc.competitionid as competition_id,
                           u.name as participant_name,
                           a.lift_type, 
                           a.weight_attempted as weight, 
                           a.attempt_result as success,
                           a.video_link as video_url
                    FROM Attempts a
                    JOIN UserCompetition uc ON a.usercompetitionid = uc.usercompetitionid
                    JOIN "User" u ON uc.userid = u.userid
                    WHERE uc.competitionid = :competition_id
                    AND uc.userid = :participant_id
                    AND a.attemptid = :attempt_id
                """),
                {
                    "competition_id": competition_id,
                    "participant_id": participant_id,
                    "attempt_id": attempt_id
                }
            ).fetchone()
            
            if row is None:
                return {"error": "Attempt not found"}, 404
                
            return {"attempt": row._asdict()}
    except Exception as e:
        return {"error": str(e)}, 500

@competition_bp.route('/random-video')
def get_random_video():
    """
    Endpoint that returns a random video from the GCS bucket.
    """
    try:
        global _current_video_index
        is_mobile = 'mobile' in request.args or request.user_agent.platform in ['android', 'iphone', 'ipad']
        lift_type_filter = request.args.get('lift_type')
        
        # Refresh video list if needed
        video_blobs = _get_video_blobs()
        
        if not video_blobs:
            return jsonify({"error": "No videos found in bucket"}), 404
        
        # Filter videos by lift type if requested
        filtered_blobs = video_blobs
        if lift_type_filter:
            try:
                # Connect to database to match videos with lift types
                with pool.connect() as conn:
                    # Get all video IDs with matching lift types
                    query = sqlalchemy.text(
                        "SELECT video_url FROM attempts WHERE lift_type = :lift_type"
                    )
                    
                    result = conn.execute(query, {"lift_type": lift_type_filter}).fetchall()
                    
                    if result:
                        video_urls = [row[0] for row in result]
                        filtered_blobs = [blob for blob in video_blobs if any(url in blob.name for url in video_urls)]
            except Exception as db_error:
                # Log but don't fail completely, fall back to all videos
                print(f"Database error when filtering videos: {db_error}")
        
        # If filtering resulted in no videos, fall back to all videos
        if not filtered_blobs:
            filtered_blobs = video_blobs
        
        # Select a random video and update current index
        random_blob = random.choice(filtered_blobs)
        _current_video_index = video_blobs.index(random_blob)
        
        # Add mobile-specific parameters if needed
        video_data = _get_video_data(random_blob)
        if is_mobile:
            # Add cache control headers for mobile
            video_data['cache_control'] = 'no-store, no-cache, must-revalidate'
            
        return jsonify(video_data)
    except Exception as e:
        print(f"Error in random-video endpoint: {str(e)}")
        return jsonify({"error": str(e), "stack_trace": str(e.__traceback__)}), 500

@competition_bp.route('/next-video')
def get_next_video():
    """
    Endpoint that returns the next video in sequence.
    """
    try:
        global _current_video_index
        video_blobs = _get_video_blobs()
        
        if not video_blobs:
            return jsonify({"error": "No videos found in bucket"}), 404
        
        # Move to next video (with wraparound)
        _current_video_index = (_current_video_index + 1) % len(video_blobs)
        next_blob = video_blobs[_current_video_index]
        
        return jsonify(_get_video_data(next_blob))
    except Exception as e:
        return {"error": str(e)}, 500

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