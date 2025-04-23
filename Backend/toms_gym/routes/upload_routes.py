from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os
import logging
from datetime import datetime, timedelta
from toms_gym.storage import bucket, ALLOWED_EXTENSIONS
from toms_gym.db import get_db_connection
import sqlalchemy
import uuid

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

upload_bp = Blueprint('upload', __name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@upload_bp.route('/upload', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400
        
    file = request.files['video']
    competition_id = request.form.get('competition_id', '1')  # Default to '1' if not provided
    user_id = request.form.get('user_id', '1')  # Default to '1' if not provided
    lift_type = request.form.get('lift_type', 'snatch')  # Default to 'snatch' if not provided
    weight = request.form.get('weight', '0')  # Default to '0' if not provided
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
        
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
        
        # Generate a signed URL that will be valid for 7 days
        url = f"https://storage.googleapis.com/{bucket.name}/{filename}"
        
        logger.info(f"File uploaded successfully: {filename}")
        
        # Get the user_competition_id for the user and competition
        session = get_db_connection()
        
        try:
            # First, check if a UserCompetition record exists
            user_competition = session.execute(
                sqlalchemy.text("""
                    SELECT id FROM "UserCompetition" 
                    WHERE user_id = :user_id AND competition_id = :competition_id
                """),
                {"user_id": user_id, "competition_id": competition_id}
            ).fetchone()
            
            user_competition_id = None
            
            # If no UserCompetition exists, create one
            if not user_competition:
                logger.info(f"Creating UserCompetition record for user {user_id} and competition {competition_id}")
                
                # Generate a UUID for the user competition
                usercomp_id = str(uuid.uuid4())
                
                # Get default weight class if possible
                weight_class_result = session.execute(
                    sqlalchemy.text("""
                        SELECT weight_class FROM "UserCompetition" 
                        WHERE user_id = :user_id 
                        ORDER BY created_at DESC LIMIT 1
                    """),
                    {"user_id": user_id}
                ).fetchone()
                
                weight_class = "83kg"  # Default weight class
                if weight_class_result:
                    weight_class = weight_class_result[0]
                
                # Create UserCompetition record
                result = session.execute(
                    sqlalchemy.text("""
                        INSERT INTO "UserCompetition" (id, user_id, competition_id, weight_class, gender)
                        VALUES (:id, :user_id, :competition_id, :weight_class, :gender)
                        RETURNING id
                    """),
                    {
                        "id": usercomp_id,
                        "user_id": user_id,
                        "competition_id": competition_id,
                        "weight_class": weight_class,
                        "gender": "male"  # Default gender
                    }
                )
                session.commit()
                user_competition_id = usercomp_id
            else:
                user_competition_id = user_competition[0]
                
            logger.info(f"Found/Created UserCompetition ID: {user_competition_id}")
            
            # Create an attempt record with the video URL
            attempt_id = str(uuid.uuid4())
            
            result = session.execute(
                sqlalchemy.text("""
                    INSERT INTO "Attempt" (id, user_competition_id, lift_type, weight_kg, status, video_url)
                    VALUES (:id, :user_competition_id, :lift_type, :weight_kg, :status, :video_url)
                    RETURNING id
                """),
                {
                    "id": attempt_id,
                    "user_competition_id": user_competition_id,
                    "lift_type": lift_type,
                    "weight_kg": float(weight),
                    "status": "pending",
                    "video_url": url
                }
            )
            session.commit()
            
            logger.info(f"Created attempt record with ID: {attempt_id}")
            
            # Return the file information along with the attempt ID
            return jsonify({
                'message': 'File uploaded successfully and attempt created',
                'url': url,
                'filename': filename,
                'attempt_id': attempt_id,
                'user_competition_id': user_competition_id
            }), 200
            
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {str(e)}")
            raise
        finally:
            session.close()
        
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': str(e)}), 500 