import pytest
from flask import Flask
from sqlalchemy import text
from toms_gym.routes.user_routes import user_bp
import time

@pytest.fixture
def test_client():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(user_bp)
    return app.test_client()

def test_create_user(test_client, db_connection):
    """Test creating a new user"""
    timestamp = int(time.time())
    test_user = {
        "gender": "M",
        "name": "Test User",
        "email": f"test{timestamp}@example.com"
    }
    
    response = test_client.post('/create_user', json=test_user)
    assert response.status_code == 201
    data = response.get_json()
    assert "user_id" in data
    assert data["message"] == "User created successfully!"
    
    # Verify the user was actually created in the database
    with db_connection.connect() as conn:
        result = conn.execute(
            text("SELECT * FROM \"User\" WHERE userid = :user_id"),
            {"user_id": data["user_id"]}
        ).fetchone()
        assert result is not None
        assert result.name == test_user["name"]
        assert result.email == test_user["email"]
        assert result.gender == test_user["gender"]

def test_create_user_invalid_data(test_client):
    """Test creating a user with invalid data"""
    invalid_user = {
        "name": "Test User"  # Missing required fields
    }
    
    response = test_client.post('/create_user', json=invalid_user)
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert data["error"] == "Missing required fields"

def test_get_user_profile(test_client, db_connection, test_user_data):
    """Test getting a user's profile"""
    # First create a test user
    with db_connection.connect() as conn:
        result = conn.execute(
            text("INSERT INTO \"User\" (gender, name, email) VALUES (:gender, :name, :email) RETURNING userid"),
            test_user_data
        )
        user_id = result.fetchone()[0]
        conn.commit()
    
    response = test_client.get(f'/users/{user_id}')
    data = response.get_json()
    if response.status_code != 200:
        print(f"Error response: {data}")
    assert response.status_code == 200
    
    assert "user" in data
    assert "competitions" in data
    assert "best_lifts" in data
    assert "achievements" in data
    
    user = data["user"]
    assert user["name"] == test_user_data["name"]
    assert user["email"] == test_user_data["email"]
    assert user["gender"] == test_user_data["gender"]

def test_get_nonexistent_user_profile(test_client):
    """Test getting a profile for a non-existent user"""
    response = test_client.get('/users/999999')
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data
    assert data["error"] == "User not found" 