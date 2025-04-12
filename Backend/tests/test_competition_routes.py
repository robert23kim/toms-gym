import json
import pytest
from flask import Flask
from toms_gym.app import app
from toms_gym.routes.competition_routes import competition_bp
import uuid

@pytest.fixture
def test_client():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(competition_bp)
    return app.test_client()

def test_get_competitions(test_client):
    """Test getting all competitions"""
    response = test_client.get('/competitions')
    assert response.status_code == 200
    data = response.get_json()
    assert "competitions" in data
    assert isinstance(data["competitions"], list)

def test_create_competition(test_client, test_competition_data):
    """Test creating a new competition"""
    response = test_client.post('/create_competition', json=test_competition_data)
    assert response.status_code == 201
    data = response.get_json()
    assert "competition_id" in data
    assert data["message"] == "Competition created successfully!"

def test_get_competition_by_id(test_client, test_competition_data):
    """Test getting a specific competition"""
    # First create a competition
    create_response = test_client.post('/create_competition', json=test_competition_data)
    assert create_response.status_code == 201
    data = create_response.get_json()
    competition_id = data["competition_id"]

    # Then get it by ID
    response = test_client.get(f'/competitions/{competition_id}')
    assert response.status_code == 200
    data = response.get_json()
    assert "competition" in data
    competition = data["competition"]
    assert competition["name"] == test_competition_data["name"]

def test_get_nonexistent_competition(test_client):
    """Test getting a non-existent competition"""
    # Use a valid UUID format that doesn't exist
    non_existent_id = str(uuid.uuid4())
    response = test_client.get(f'/competitions/{non_existent_id}')
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data
    assert data["error"] == "Competition not found" 