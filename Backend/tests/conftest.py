import pytest
from sqlalchemy import text
from toms_gym.db import pool
import time
import random

@pytest.fixture
def db_connection():
    return pool

@pytest.fixture
def test_competition_data():
    return {
        "name": "Test Competition",
        "location": "Test Location",
        "lifttypes": ["Squat", "Bench Press", "Deadlift"],
        "weightclasses": ["66kg", "74kg", "83kg", "93kg", "105kg", "120kg", "+120kg"],
        "gender": "M",
        "start_date": "2024-04-01",
        "end_date": "2024-04-02"
    }

@pytest.fixture
def test_user_data():
    timestamp = int(time.time())
    random_num = random.randint(1000, 9999)
    return {
        "gender": "M",
        "name": "Test User",
        "email": f"test{timestamp}_{random_num}@example.com"
    }

@pytest.fixture
def test_attempt_data(db_connection, test_user_data, test_competition_data):
    # First create a test user
    with db_connection.connect() as conn:
        user_result = conn.execute(
            text("INSERT INTO \"User\" (gender, name, email) VALUES (:gender, :name, :email) RETURNING userid"),
            test_user_data
        )
        user_id = user_result.fetchone()[0]

        # Create a test competition
        comp_result = conn.execute(
            text("""
            INSERT INTO Competition (name, location, start_date, end_date)
            VALUES (:name, :location, :start_date, :end_date)
            RETURNING id
            """),
            test_competition_data
        )
        competition_id = comp_result.fetchone()[0]

        # Create a user competition entry
        usercomp_result = conn.execute(
            text("""
            INSERT INTO UserCompetition (userid, competitionid, weight_class, status)
            VALUES (:userid, :competitionid, :weight_class, :status)
            RETURNING usercompetitionid
            """),
            {
                "userid": user_id,
                "competitionid": competition_id,
                "weight_class": "93kg",
                "status": "registered"
            }
        )
        usercompetition_id = usercomp_result.fetchone()[0]
        conn.commit()

    return {
        "usercompetitionid": usercompetition_id,
        "lift_type": "Squat",
        "weight_attempted": 100.0,
        "attempt_number": 1,
        "attempt_result": "true",
        "video_link": "https://example.com/video.mp4"
    } 