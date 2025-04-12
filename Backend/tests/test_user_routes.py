import pytest
from flask import Flask
from sqlalchemy import text
from toms_gym.routes.user_routes import user_bp
import time
import uuid
from datetime import datetime
import bcrypt

@pytest.fixture
def test_client():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(user_bp)
    return app.test_client()

def test_get_user_profile(client, db_session, test_auth_user_data):
    """Test retrieving a user profile"""
    # Create a user directly using the session for setup
    hashed_password = bcrypt.hashpw(test_auth_user_data["password"].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user_id = str(uuid.uuid4())
    db_session.execute(
        text("""
            INSERT INTO "User" (id, username, email, password_hash, name, auth_method, created_at, status, role)
            VALUES (:id, :username, :email, :password, :name, 'password', :created_at, 'active', 'user')
        """),
        {
            "id": user_id,
            "username": test_auth_user_data["username"],
            "email": test_auth_user_data["email"],
            "password": hashed_password,
            "name": test_auth_user_data["name"],
            "created_at": datetime.utcnow()
        }
    )
    db_session.commit() # Commit the user creation

    # Test getting the profile via API
    response = client.get(f'/users/{user_id}')
    assert response.status_code == 200
    data = response.get_json()
    assert data is not None
    assert "user" in data
    assert data["user"]["id"] == user_id
    assert data["user"]["email"] == test_auth_user_data["email"]

def test_get_nonexistent_user_profile(client):
    """Test retrieving a profile for a non-existent user"""
    non_existent_id = str(uuid.uuid4())
    response = client.get(f'/users/{non_existent_id}')
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data
    assert data["error"] == "User not found" 