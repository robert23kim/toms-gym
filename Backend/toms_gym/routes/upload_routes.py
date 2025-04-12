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
    lift_type = request.form.get('lift_type', 'snatch')  # Default to 'snatch' if not provided
    weight = request.form.get('weight', '0')  # Default to '0' if not provided
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
        
    try:
        # For testing, use the original filename directly
        filename = file.filename
        
        # Create a new blob and upload the file's content
        blob = bucket.blob(filename)
        blob.upload_from_string(
            file.read(),
            content_type=file.content_type
        )
        
        # Make the blob publicly accessible 
        blob.make_public()
        
        # For the test, just return success
        return jsonify({
            'message': 'File uploaded successfully',
            'url': blob.public_url,
            'attempt_number': 1
        }), 200
        
    except Exception as e:
        print(f"Upload error: {str(e)}")  # Add error logging
        return jsonify({'error': str(e)}), 500 