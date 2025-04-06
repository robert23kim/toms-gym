import pytest
from flask import Flask
from sqlalchemy import text
from toms_gym.routes.attempt_routes import attempt_bp

@pytest.fixture
def test_client():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(attempt_bp)
    return app.test_client()

def test_submit_attempt(test_client, db_connection, test_attempt_data):
    """Test submitting a new attempt"""
    response = test_client.post('/submit_attempt', json=test_attempt_data)
    assert response.status_code == 201
    data = response.get_json()
    assert "attempt_id" in data
    assert data["message"] == "Attempt submitted successfully!"
    
    # Verify the attempt was actually created in the database
    with db_connection.connect() as conn:
        result = conn.execute(
            text("SELECT * FROM Attempts WHERE attemptid = :attempt_id"),
            {"attempt_id": data["attempt_id"]}
        ).fetchone()
        assert result is not None
        assert result.lift_type == test_attempt_data["lift_type"]
        assert float(result.weight_attempted) == test_attempt_data["weight_attempted"]
        assert result.attempt_number == test_attempt_data["attempt_number"]
        # Convert PostgreSQL's string boolean to Python boolean
        assert str(result.attempt_result).lower() == str(test_attempt_data["attempt_result"]).lower()
        assert result.video_link == test_attempt_data["video_link"]

def test_submit_attempt_invalid_data(test_client):
    """Test submitting an attempt with invalid data"""
    invalid_attempt = {
        "lift_type": "Squat",  # Missing required fields
        "weight_attempted": 100
    }
    
    response = test_client.post('/submit_attempt', json=invalid_attempt)
    assert response.status_code == 500

def test_submit_attempt_nonexistent_user_competition(test_client, test_attempt_data):
    """Test submitting an attempt for a non-existent user competition"""
    invalid_data = test_attempt_data.copy()
    invalid_data["usercompetitionid"] = 999999  # Non-existent ID
    
    response = test_client.post('/submit_attempt', json=invalid_data)
    assert response.status_code == 500 