from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os
from toms_gym.storage import bucket, ALLOWED_EXTENSIONS

upload_bp = Blueprint('upload', __name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@upload_bp.route('/upload', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400
        
    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
        
    try:
        # Secure the filename
        filename = secure_filename(file.filename)
        
        # Create a new blob and upload the file's content
        blob = bucket.blob(filename)
        blob.upload_from_string(
            file.read(),
            content_type=file.content_type
        )
        
        # Make the blob publicly viewable
        blob.make_public()
        
        # Return the public URL
        return jsonify({
            'message': 'File uploaded successfully',
            'url': blob.public_url
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500 