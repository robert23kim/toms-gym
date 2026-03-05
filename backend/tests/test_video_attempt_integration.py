import pytest
from flask import Flask
from io import BytesIO
import uuid
from sqlalchemy import text
from unittest.mock import patch, MagicMock

@pytest.fixture
def test_integrated_app(app):
    """Setup an integrated testing app with all required blueprints registered"""
    # Since we're testing integration, ensure all needed blueprints are registered
    from toms_gym.routes.upload_routes import upload_bp
    from toms_gym.routes.attempt_routes import attempt_bp
    
    # Register blueprints if not already registered
    if 'upload' not in app.blueprints:
        app.register_blueprint(upload_bp)
    if 'attempt' not in app.blueprints:
        app.register_blueprint(attempt_bp)
    
    return app

@pytest.fixture
def integrated_client(test_integrated_app):
    """A test client for the integrated app"""
    return test_integrated_app.test_client()

@patch('toms_gym.routes.upload_routes.bucket')
def test_upload_creates_attempt_record(mock_bucket, integrated_client, create_test_setup, db_session):
    """Test that uploading a video creates a corresponding attempt record in the database"""
    # Setup test data
    setup_data = create_test_setup  # Contains user_id, competition_id
    user_id = setup_data["user_id"]
    competition_id = setup_data["competition_id"]
    
    # Mock the GCS functionality
    mock_blob = MagicMock()
    mock_blob.public_url = f"https://storage.googleapis.com/test-bucket/test_video_{uuid.uuid4()}.mp4"
    mock_bucket.blob.return_value = mock_blob
    
    # Prepare test video data
    test_video_content = b'fake video content for testing'
    test_video_filename = 'test_video.mp4'
    
    # Create form data with the video file and metadata
    data = {
        'video': (BytesIO(test_video_content), test_video_filename),
        'user_id': user_id,
        'competition_id': competition_id,
        'lift_type': 'Snatch',
        'weight': '100.5'
    }
    
    # Capture attempt count before upload
    attempts_before_query = """
        SELECT COUNT(*) FROM "Attempt" 
        WHERE user_competition_id IN (
            SELECT id FROM "UserCompetition" 
            WHERE user_id = :user_id AND competition_id = :competition_id
        )
    """
    result_before = db_session.execute(
        text(attempts_before_query),
        {"user_id": user_id, "competition_id": competition_id}
    ).fetchone()
    attempts_before = result_before[0] if result_before else 0
    
    # Send the upload request
    response = integrated_client.post('/upload', data=data, content_type='multipart/form-data')
    
    # Verify response is successful
    assert response.status_code == 200
    response_data = response.get_json()
    assert "url" in response_data
    assert "attempt_id" in response_data
    assert "user_competition_id" in response_data
    assert response_data["message"] == "File uploaded successfully and attempt created"
    
    # Verify the mock was called correctly for storage
    mock_bucket.blob.assert_called_once()
    mock_blob.upload_from_string.assert_called_once()
    
    # Verify a new attempt record was created in the database
    attempts_after_query = """
        SELECT COUNT(*) FROM "Attempt" 
        WHERE user_competition_id IN (
            SELECT id FROM "UserCompetition" 
            WHERE user_id = :user_id AND competition_id = :competition_id
        )
    """
    result_after = db_session.execute(
        text(attempts_after_query),
        {"user_id": user_id, "competition_id": competition_id}
    ).fetchone()
    attempts_after = result_after[0] if result_after else 0
    
    # Assert that we have one more attempt record after the upload
    assert attempts_after == attempts_before + 1
    
    # Verify the attempt record details
    attempt_query = """
        SELECT a.id, a.lift_type, a.weight_kg, a.status, a.video_url 
        FROM "Attempt" a
        JOIN "UserCompetition" uc ON a.user_competition_id = uc.id
        WHERE uc.user_id = :user_id AND uc.competition_id = :competition_id
        ORDER BY a.created_at DESC
        LIMIT 1
    """
    attempt = db_session.execute(
        text(attempt_query),
        {"user_id": user_id, "competition_id": competition_id}
    ).fetchone()
    
    assert attempt is not None
    assert str(attempt.id) == response_data["attempt_id"]
    assert attempt.lift_type == "snatch"  # Mapped from 'Snatch' to database enum
    assert float(attempt.weight_kg) == 100.5
    assert attempt.status == "pending"
    assert attempt.video_url is not None
    assert "videos/" in attempt.video_url  # Videos are stored in the 'videos/' folder

@patch('toms_gym.routes.upload_routes.bucket')
def test_failed_upload_no_attempt_record(mock_bucket, integrated_client, create_test_setup, db_session):
    """Test that when a video upload fails, no attempt record is created"""
    # Setup test data
    setup_data = create_test_setup
    user_id = setup_data["user_id"]
    competition_id = setup_data["competition_id"]
    
    # Mock the GCS blob to raise an exception on upload
    mock_blob = MagicMock()
    mock_blob.upload_from_string.side_effect = Exception("Simulated storage failure")
    mock_bucket.blob.return_value = mock_blob
    
    # Prepare test video data with invalid extension
    test_video_content = b'fake video content for testing'
    
    # Create form data with the video file and metadata
    data = {
        'video': (BytesIO(test_video_content), 'test_video.mp4'),
        'user_id': user_id,
        'competition_id': competition_id,
        'lift_type': 'Snatch',
        'weight': '100.5'
    }
    
    # Capture attempt count before upload
    attempts_before_query = """
        SELECT COUNT(*) FROM "Attempt" 
        WHERE user_competition_id IN (
            SELECT id FROM "UserCompetition" 
            WHERE user_id = :user_id AND competition_id = :competition_id
        )
    """
    result_before = db_session.execute(
        text(attempts_before_query),
        {"user_id": user_id, "competition_id": competition_id}
    ).fetchone()
    attempts_before = result_before[0] if result_before else 0
    
    # Send the upload request - should fail due to simulated storage exception
    response = integrated_client.post('/upload', data=data, content_type='multipart/form-data')
    
    # Verify response indicates an error
    assert response.status_code == 500
    
    # Verify the mock was called correctly for storage attempt
    mock_bucket.blob.assert_called_once()
    mock_blob.upload_from_string.assert_called_once()
    
    # Verify no new attempt record was created
    attempts_after_query = """
        SELECT COUNT(*) FROM "Attempt" 
        WHERE user_competition_id IN (
            SELECT id FROM "UserCompetition" 
            WHERE user_id = :user_id AND competition_id = :competition_id
        )
    """
    result_after = db_session.execute(
        text(attempts_after_query),
        {"user_id": user_id, "competition_id": competition_id}
    ).fetchone()
    attempts_after = result_after[0] if result_after else 0
    
    # Assert that the attempt count is unchanged
    assert attempts_after == attempts_before, "No attempt record should be created for failed upload" 