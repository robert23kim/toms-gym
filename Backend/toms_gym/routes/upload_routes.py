from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os
import logging
from datetime import datetime, timedelta
from toms_gym.storage import bucket, ALLOWED_EXTENSIONS
from toms_gym.db import get_db

# Set up logging
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
        
        # Return the file information
        return jsonify({
            'message': 'File uploaded successfully',
            'url': url,
            'filename': filename,
            'attempt_number': 1
        }), 200
        
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': str(e)}), 500 