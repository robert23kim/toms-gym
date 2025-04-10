from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timedelta
from toms_gym.storage import bucket, ALLOWED_EXTENSIONS
from toms_gym.db import get_db

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
    lift_type = request.form.get('lift_type', 'Squat')  # Default to 'Squat' if not provided
    weight = request.form.get('weight', '0')  # Default to '0' if not provided
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
        
    try:
        # Secure the filename and add timestamp
        original_filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"videos/{timestamp}_{original_filename}"
        
        # Create a new blob and upload the file's content
        blob = bucket.blob(filename)
        blob.upload_from_string(
            file.read(),
            content_type=file.content_type
        )
        
        # Generate a signed URL that expires in 1 hour
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(hours=1),
            method="GET"
        )
        
        # Store video metadata in the database
        with get_db().connect() as conn:
            # First, get or create the usercompetition_id
            result = conn.execute(
                """
                SELECT id FROM UserCompetition 
                WHERE user_id = %s AND competition_id = %s
                """,
                [int(user_id), int(competition_id)]  # Convert to integers and use list
            ).fetchone()
            
            if not result:
                # Create a new UserCompetition entry if it doesn't exist
                conn.execute(
                    """
                    INSERT INTO UserCompetition (user_id, competition_id)
                    VALUES (%s, %s)
                    """,
                    [int(user_id), int(competition_id)]  # Use list
                )
                result = conn.execute(
                    """
                    SELECT id FROM UserCompetition 
                    WHERE user_id = %s AND competition_id = %s
                    """,
                    [int(user_id), int(competition_id)]  # Use list
                ).fetchone()
                
            usercompetition_id = result[0]
            
            # Get the next attempt number for this user in this competition
            result = conn.execute(
                """
                SELECT COALESCE(MAX(attempt_number), 0) + 1
                FROM Attempts
                WHERE usercompetition_id = %s AND lift_type = %s
                """,
                [int(usercompetition_id), lift_type]  # Use list
            ).fetchone()
            
            attempt_number = result[0]
            
            # Insert the attempt
            conn.execute(
                """
                INSERT INTO Attempts (
                    usercompetition_id, lift_type, weight, 
                    video_url, attempt_number, attempt_result,
                    created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """,
                [int(usercompetition_id), lift_type, float(weight), filename, 
                 int(attempt_number), 'pending']  # Use list
            )
            conn.commit()
        
        # Return the signed URL and success message
        return jsonify({
            'message': 'File uploaded successfully',
            'url': signed_url,
            'attempt_number': attempt_number
        }), 200
        
    except Exception as e:
        print(f"Upload error: {str(e)}")  # Add error logging
        return jsonify({'error': str(e)}), 500 