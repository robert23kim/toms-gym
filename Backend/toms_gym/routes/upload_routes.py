from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os
import logging
from datetime import datetime, timedelta
from toms_gym.storage import bucket, ALLOWED_EXTENSIONS
from toms_gym.db import get_db_connection
import sqlalchemy
import uuid
import traceback
import sys

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

upload_bp = Blueprint('upload', __name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@upload_bp.route('/upload', methods=['POST'])
def upload_video():
    logger.info("=== UPLOAD VIDEO FUNCTION STARTED ===")
    
    # Log request details
    logger.info(f"Request headers: {dict(request.headers)}")
    logger.info(f"Request form data: {dict(request.form)}")
    logger.info(f"Request files: {list(request.files.keys())}")
    
    if 'video' not in request.files:
        logger.error("No video file in request")
        return jsonify({'error': 'No video file provided'}), 400
        
    file = request.files['video']
    competition_id = request.form.get('competition_id', '1')  # Default to '1' if not provided
    user_id = request.form.get('user_id', '1')  # Default to '1' if not provided
    lift_type = request.form.get('lift_type', 'snatch')  # Default to 'snatch' if not provided
    weight = request.form.get('weight', '0')  # Default to '0' if not provided
    
    # Log received data
    logger.info(f"Received data - competition_id: {competition_id}, user_id: {user_id}")
    logger.info(f"Received data - lift_type: {lift_type}, weight: {weight}")
    
    # Convert frontend lift_type to database enum values
    lift_type_mapping = {
        "Squat": "Squat", 
        "Bench": "Bench Press",  # "Bench" from frontend becomes "Bench Press" for database
        "Deadlift": "Deadlift",
        "Clean": "Clean & Jerk",
        "Snatch": "snatch",
        "Overhead": "Overhead Press"
    }
    
    # Map the lift type or default to "snatch" if not found
    database_lift_type = lift_type_mapping.get(lift_type, "snatch")
    
    logger.info(f"Upload request received - user_id: {user_id}, competition_id: {competition_id}")
    logger.info(f"Original lift_type: {lift_type}, Mapped to DB lift_type: {database_lift_type}, weight: {weight}")
    
    if file.filename == '':
        logger.error("Empty filename")
        return jsonify({'error': 'No selected file'}), 400
        
    if not allowed_file(file.filename):
        logger.error(f"File type not allowed: {file.filename}")
        return jsonify({'error': 'File type not allowed'}), 400
    
    video_url = None
    attempt_id = None
    user_competition_id = None
        
    try:
        # Create a timestamp-based unique filename to avoid collisions
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        original_filename = secure_filename(file.filename)
        filename = f"videos/{timestamp}_{original_filename}"
        
        logger.info(f"Uploading file: {filename}")
        
        # Create a new blob and upload the file's content
        blob = bucket.blob(filename)
        blob.upload_from_string(
            file.read(),
            content_type=file.content_type
        )
        
        # Generate a URL for the file
        video_url = f"https://storage.googleapis.com/{bucket.name}/{filename}"
        
        logger.info(f"File uploaded successfully to URL: {video_url}")
        
        # Get the user_competition_id for the user and competition
        session = get_db_connection()
        logger.info(f"Database connection established.")
        
        try:
            # First, check if a UserCompetition record exists
            logger.info(f"Checking for existing UserCompetition record for user {user_id} and competition {competition_id}")
            user_competition_query = """
                SELECT id FROM "UserCompetition" 
                WHERE user_id = :user_id AND competition_id = :competition_id
            """
            
            user_competition = session.execute(
                sqlalchemy.text(user_competition_query),
                {"user_id": user_id, "competition_id": competition_id}
            ).fetchone()
            
            # If no UserCompetition exists, create one
            if not user_competition:
                logger.info(f"No UserCompetition found, creating new record")
                
                # Generate a UUID for the user competition
                usercomp_id = str(uuid.uuid4())
                
                # Get default weight class if possible
                weight_class_query = """
                    SELECT weight_class FROM "UserCompetition" 
                    WHERE user_id = :user_id 
                    ORDER BY created_at DESC LIMIT 1
                """
                
                weight_class_result = session.execute(
                    sqlalchemy.text(weight_class_query),
                    {"user_id": user_id}
                ).fetchone()
                
                weight_class = "83kg"  # Default weight class
                if weight_class_result:
                    weight_class = weight_class_result[0]
                    logger.info(f"Using weight class from previous competition: {weight_class}")
                else:
                    logger.info(f"Using default weight class: {weight_class}")
                
                # Create UserCompetition record
                insert_usercomp_query = """
                    INSERT INTO "UserCompetition" (id, user_id, competition_id, weight_class, gender)
                    VALUES (:id, :user_id, :competition_id, :weight_class, :gender)
                    RETURNING id
                """
                
                result = session.execute(
                    sqlalchemy.text(insert_usercomp_query),
                    {
                        "id": usercomp_id,
                        "user_id": user_id,
                        "competition_id": competition_id,
                        "weight_class": weight_class,
                        "gender": "male"  # Default gender
                    }
                )
                user_competition_id = usercomp_id
                logger.info(f"Created UserCompetition with ID: {user_competition_id}")
            else:
                user_competition_id = user_competition[0]
                logger.info(f"Found existing UserCompetition with ID: {user_competition_id}")
            
            # Create an attempt record with the video URL
            attempt_id = str(uuid.uuid4())
            logger.info(f"Creating new attempt with ID: {attempt_id}")
            
            # Convert weight to float safely
            try:
                weight_kg = float(weight)
                logger.info(f"Converted weight {weight} to float: {weight_kg}")
            except (ValueError, TypeError):
                logger.warning(f"Invalid weight value: {weight}, defaulting to 0")
                weight_kg = 0
                
            insert_attempt_query = """
                INSERT INTO "Attempt" (id, user_competition_id, lift_type, weight_kg, status, video_url)
                VALUES (:id, :user_competition_id, :lift_type, :weight_kg, :status, :video_url)
                RETURNING id
            """
            
            # Add additional logging before commit
            logger.info("Committing UserCompetition transaction")
            
            # Explicitly commit the UserCompetition transaction first
            session.commit()
            
            # Log the parameters for the insert attempt query for debugging
            insert_params = {
                "id": attempt_id,
                "user_competition_id": user_competition_id,
                "lift_type": database_lift_type,
                "weight_kg": weight_kg,
                "status": "pending",
                "video_url": video_url
            }
            logger.info(f"Attempt insert parameters: {insert_params}")
            
            # Now create the attempt
            logger.info("Executing attempt insert query")
            result = session.execute(
                sqlalchemy.text(insert_attempt_query),
                insert_params
            )
            
            # Explicitly commit the Attempt transaction
            logger.info("Committing Attempt transaction")
            session.commit()
            logger.info(f"Successfully created attempt record with ID: {attempt_id}")
            
            # Return the file information along with the attempt ID
            logger.info("=== UPLOAD VIDEO FUNCTION COMPLETED SUCCESSFULLY ===")
            return jsonify({
                'message': 'File uploaded successfully and attempt created',
                'url': video_url,
                'filename': filename,
                'attempt_id': attempt_id,
                'user_competition_id': user_competition_id
            }), 200
            
        except Exception as e:
            session.rollback()
            error_details = traceback.format_exc()
            logger.error(f"Database error: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error details: {error_details}")
            
            # Print exception details to stderr for immediate visibility
            print(f"CRITICAL ERROR in upload_video: {str(e)}", file=sys.stderr)
            print(f"Error details: {error_details}", file=sys.stderr)
            
            # If we've already uploaded the file but failed to create the records,
            # return information about the uploaded file so it's not lost
            if video_url:
                logger.info("=== UPLOAD VIDEO FUNCTION COMPLETED WITH DATABASE ERROR ===")
                return jsonify({
                    'message': 'File uploaded but database record creation failed',
                    'error': str(e),
                    'url': video_url,
                    'filename': filename
                }), 500
            raise
        finally:
            session.close()
            logger.info("Database session closed")
        
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Upload error: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error details: {error_details}")
        
        # Print exception details to stderr for immediate visibility
        print(f"CRITICAL ERROR in upload_video: {str(e)}", file=sys.stderr)
        print(f"Error details: {error_details}", file=sys.stderr)
        
        logger.info("=== UPLOAD VIDEO FUNCTION COMPLETED WITH ERROR ===")
        return jsonify({'error': str(e)}), 500 