import pytest
from flask import Flask
from toms_gym.app import app
from toms_gym.config.database import pool
import sqlalchemy

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def db_connection():
    with pool.connect() as conn:
        yield conn
        conn.rollback()  # Rollback any changes made during tests

@pytest.fixture
def test_competition_data():
    return {
        "name": "Test Competition",
        "location": "Test Location",
        "lifttypes": ["Squat", "Bench", "Deadlift"],
        "weightclasses": ["93kg", "105kg"],
        "gender": "M",
        "start_date": "2024-04-01",
        "end_date": "2024-04-02"
    }

@pytest.fixture
def test_user_data():
    return {
        "gender": "M",
        "name": "Test User",
        "email": "test@example.com"
    }

@pytest.fixture
def test_attempt_data():
    return {
        "usercompetitionid": 1,
        "lift_type": "Squat",
        "weight_attempted": 100,
        "attempt_number": 1,
        "attempt_result": True,
        "video_link": "https://example.com/video.mp4"
    } 