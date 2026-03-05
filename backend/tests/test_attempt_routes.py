import pytest
from flask import Flask
from sqlalchemy import text
from toms_gym.routes.attempt_routes import attempt_bp
import uuid

@pytest.fixture
def test_client():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(attempt_bp)
    return app.test_client()

def test_submit_attempt(client, create_test_setup):
    """Test submitting a new attempt"""
    setup_data = create_test_setup # Contains user_id, competition_id, user_competition_id
    attempt_payload = {
        "user_competition_id": setup_data["user_competition_id"],
        "lift_type": "Bench Press",
        "weight_kg": 100.5,
        "status": "pending",
        "video_url": "http://example.com/video1.mp4"
    }
    response = client.post('/attempts', json=attempt_payload) # Assuming endpoint is /attempts
    assert response.status_code == 201
    data = response.get_json()
    assert "attempt_id" in data
    assert data["message"] == "Attempt created successfully!" # Adjust message if different

    # Optional: Verify attempt in DB using db_session (if needed)
    # with app.app_context(): # Need app fixture if using app context here
    #    session = DBSession() 
    #    result = session.execute(text(...))
    #    attempt = result.fetchone()
    #    assert attempt is not None
    #    DBSession.remove()

def test_submit_attempt_invalid_data(client, create_test_setup):
    """Test submitting attempt with invalid data"""
    setup_data = create_test_setup
    invalid_payload = {
        "user_competition_id": setup_data["user_competition_id"],
        # Missing lift_type, weight_kg
    }
    response = client.post('/attempts', json=invalid_payload)
    assert response.status_code >= 400 # Expecting a client error

def test_submit_attempt_nonexistent_user_competition(client):
    """Test submitting attempt for a non-existent user_competition link"""
    non_existent_uc_id = str(uuid.uuid4())
    attempt_payload = {
        "user_competition_id": non_existent_uc_id,
        "lift_type": "Squat",
        "weight_kg": 150.0,
    }
    response = client.post('/attempts', json=attempt_payload)
    # Expecting 404 or potentially 500 if FK constraint fails or other internal error
    assert response.status_code in [404, 500, 400] 