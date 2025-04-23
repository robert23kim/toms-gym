import pytest
from flask import Flask
from io import BytesIO
from toms_gym.routes.upload_routes import upload_bp
from unittest.mock import patch, MagicMock
import uuid

@pytest.fixture
def test_client():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(upload_bp)
    return app.test_client()

@patch('toms_gym.routes.upload_routes.bucket')
@patch('toms_gym.routes.upload_routes.get_db_connection')
def test_upload_video(mock_db_connection, mock_bucket, test_client):
    """Test uploading a valid video file"""
    # Mock the blob object
    mock_blob = MagicMock()
    mock_blob.public_url = "https://storage.googleapis.com/test-bucket/test_video.mp4"
    mock_bucket.blob.return_value = mock_blob
    
    # Mock the database session and queries
    mock_session = MagicMock()
    mock_db_connection.return_value = mock_session
    
    # Mock the UserCompetition query result
    mock_session.execute.return_value.fetchone.return_value = (str(uuid.uuid4()),)
    
    # Create test user and competition UUIDs
    test_user_id = str(uuid.uuid4())
    test_competition_id = str(uuid.uuid4())
    
    data = {
        'video': (BytesIO(b'test video content'), 'test_video.mp4'),
        'user_id': test_user_id,
        'competition_id': test_competition_id
    }
    response = test_client.post('/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 200
    data = response.get_json()
    assert "url" in data
    assert "attempt_id" in data
    assert "user_competition_id" in data
    assert data["message"] == "File uploaded successfully and attempt created"
    
    # Verify the mock was called correctly
    mock_bucket.blob.assert_called_once()
    mock_blob.upload_from_string.assert_called_once()
    
    # Verify database interactions
    mock_session.execute.assert_called()
    mock_session.commit.assert_called()
    mock_session.close.assert_called()

def test_upload_no_file(test_client):
    """Test uploading with no file"""
    response = test_client.post('/upload', data={}, content_type='multipart/form-data')
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "No video file provided"

def test_upload_empty_filename(test_client):
    """Test uploading with empty filename"""
    data = {
        'video': (BytesIO(b''), '')
    }
    response = test_client.post('/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "No selected file"

def test_upload_invalid_extension(test_client):
    """Test uploading a file with invalid extension"""
    data = {
        'video': (BytesIO(b'test content'), 'test.txt')
    }
    response = test_client.post('/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "File type not allowed" 