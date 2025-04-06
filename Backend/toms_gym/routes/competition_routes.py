from flask import Blueprint, request, jsonify
import sqlalchemy
from toms_gym.db import pool
from google.cloud import storage
import random
import datetime

# Global variable to store video blobs
_video_blobs = []
_current_video_index = 0

def _get_video_blobs():
    """Helper function to get and cache video blobs"""
    global _video_blobs
    # Always refresh the video list to ensure we have all videos
    storage_client = storage.Client()
    bucket = storage_client.bucket('jtr-lift-u-4ever-cool-bucket')
    blobs = list(bucket.list_blobs(prefix='videos/'))
    _video_blobs = [blob for blob in blobs if blob.name.lower().endswith(('.mp4', '.mov'))]
    random.shuffle(_video_blobs)  # Shuffle the list to ensure random order
    return _video_blobs

def _get_video_data(blob):
    """Helper function to create video response data"""
    # Create a public URL with https to ensure it works on all browsers
    # The format is https://storage.googleapis.com/BUCKET_NAME/OBJECT_NAME
    url = f"https://storage.googleapis.com/{blob.bucket.name}/{blob.name}"
    
    # For debugging - log the URL
    print(f"Generated video URL: {url}")
    
    return {
        "video_id": 1,
        "participant_id": 1,
        "competition_id": 1,
        "video_url": url,
        "participant_name": "Random Athlete",
        "lift_type": "Squat",
        "weight": 100,
        "success": True,
        "total_videos": len(_video_blobs),
        "current_index": _current_video_index
    }

competition_bp = Blueprint('competition', __name__)

@competition_bp.route('/competitions')
def get_competitions():
    """
    Endpoint that queries all competitions.
    """
    try:
        with pool.connect() as conn:
            rows = conn.execute(sqlalchemy.text("SELECT * FROM Competition"))
            results = [row._asdict() for row in rows]
        return {"competitions": results}
    except Exception as e:
        return {"error": str(e)}, 500

@competition_bp.route('/competitions/<int:competition_id>')
def get_competition_by_id(competition_id):
    """
    Endpoint that queries a single competition by ID.
    """
    try:
        with pool.connect() as conn:
            row = conn.execute(
                sqlalchemy.text("SELECT * FROM Competition WHERE id = :id"),
                {"id": competition_id}
            ).fetchone()
            
            if row is None:
                return {"error": "Competition not found"}, 404
                
            result = row._asdict()
            return {"competition": result}
    except Exception as e:
        return {"error": str(e)}, 500

@competition_bp.route('/competitions/<int:competition_id>/participants')
def get_competition_participants(competition_id):
    """
    Endpoint that queries all participants for a specific competition.
    """
    try:
        with pool.connect() as conn:
            rows = conn.execute(
                sqlalchemy.text("""
                    SELECT u.userid, u.name, uc.weight_class,
                           COALESCE(SUM(CASE WHEN a.attempt_result = 'true' THEN a.weight_attempted ELSE 0 END), 0) as total_weight,
                           json_agg(
                               json_build_object(
                                   'lift_type', a.lift_type,
                                   'weight', a.weight_attempted,
                                   'success', a.attempt_result
                               )
                           ) as attempts
                    FROM UserCompetition uc
                    JOIN \"User\" u ON uc.userid = u.userid
                    LEFT JOIN Attempts a ON uc.usercompetitionid = a.usercompetitionid
                    WHERE uc.competitionid = :competition_id
                    GROUP BY u.userid, u.name, uc.weight_class
                """),
                {"competition_id": competition_id}
            )
            results = [row._asdict() for row in rows]
        return {"participants": results}
    except Exception as e:
        return {"error": str(e)}, 500

@competition_bp.route('/competitions/<int:competition_id>/lifts')
def get_competition_lifts(competition_id):
    """
    Endpoint that queries all lifts for a specific competition.
    """
    try:
        with pool.connect() as conn:
            rows = conn.execute(
                sqlalchemy.text("""
                    SELECT a.attemptid as id, uc.userid as participant_id, uc.competitionid as competition_id,
                           a.lift_type as type, a.weight_attempted as weight, a.attempt_result as success,
                           a.video_link as video_url
                    FROM Attempts a
                    JOIN UserCompetition uc ON a.usercompetitionid = uc.usercompetitionid
                    WHERE uc.competitionid = :competition_id
                """),
                {"competition_id": competition_id}
            )
            results = [row._asdict() for row in rows]
        return {"lifts": results}
    except Exception as e:
        return {"error": str(e)}, 500

@competition_bp.route('/create_competition', methods=['POST'])
def create_competition():
    """
    Endpoint to insert a new competition entry.
    Expects JSON payload with competition details.
    """
    try:
        data = request.json
        insert_query = sqlalchemy.text(
            """
            INSERT INTO Competition (name, location, lifttypes, weightclasses, gender, start_date, end_date)
            VALUES (:name, :location, :lifttypes, :weightclasses, :gender, :start_date, :end_date)
            RETURNING id;
            """
        )

        with pool.connect() as conn:
            result = conn.execute(insert_query, data)
            inserted_id = result.fetchone()[0]
            conn.commit()

        return {"message": "Competition created successfully!", "competition_id": inserted_id}, 201
    except Exception as e:
        return {"error": str(e)}, 500

@competition_bp.route('/join_competition', methods=['POST'])
def join_competition():
    """
    Endpoint to join a competition.
    Expects JSON payload with user competition details.
    """
    try:
        data = request.json
        insert_query = sqlalchemy.text(
            """
            INSERT INTO UserCompetition (userid, competitionid, weight_class, gender, age, status)
            VALUES (:userid, :competitionid, :weight_class, :gender, :age, :status)
            RETURNING usercompetitionid;
            """
        )

        with pool.connect() as conn:
            result = conn.execute(insert_query, data)
            user_competition_id = result.fetchone()[0]
            conn.commit()

        return {"message": "Joined competition successfully!", "usercompetition_id": user_competition_id}, 201
    except Exception as e:
        return {"error": str(e)}, 500

@competition_bp.route('/competitions/<int:competition_id>/participants/<int:participant_id>/attempts/<int:attempt_id>')
def get_attempt_details(competition_id, participant_id, attempt_id):
    """
    Endpoint that queries details for a specific attempt including video URL.
    """
    try:
        with pool.connect() as conn:
            row = conn.execute(
                sqlalchemy.text("""
                    SELECT a.attemptid as id, 
                           uc.userid as participant_id, 
                           uc.competitionid as competition_id,
                           u.name as participant_name,
                           a.lift_type, 
                           a.weight_attempted as weight, 
                           a.attempt_result as success,
                           a.video_link as video_url
                    FROM Attempts a
                    JOIN UserCompetition uc ON a.usercompetitionid = uc.usercompetitionid
                    JOIN "User" u ON uc.userid = u.userid
                    WHERE uc.competitionid = :competition_id
                    AND uc.userid = :participant_id
                    AND a.attemptid = :attempt_id
                """),
                {
                    "competition_id": competition_id,
                    "participant_id": participant_id,
                    "attempt_id": attempt_id
                }
            ).fetchone()
            
            if row is None:
                return {"error": "Attempt not found"}, 404
                
            return {"attempt": row._asdict()}
    except Exception as e:
        return {"error": str(e)}, 500

@competition_bp.route('/random-video')
def get_random_video():
    """
    Endpoint that returns a random video from the GCS bucket.
    """
    try:
        global _current_video_index
        video_blobs = _get_video_blobs()
        
        if not video_blobs:
            return jsonify({"error": "No videos found in bucket"}), 404
        
        # Select a random video and update current index
        random_blob = random.choice(video_blobs)
        _current_video_index = video_blobs.index(random_blob)
        
        return jsonify(_get_video_data(random_blob))
    except Exception as e:
        return {"error": str(e)}, 500

@competition_bp.route('/next-video')
def get_next_video():
    """
    Endpoint that returns the next video in sequence.
    """
    try:
        global _current_video_index
        video_blobs = _get_video_blobs()
        
        if not video_blobs:
            return jsonify({"error": "No videos found in bucket"}), 404
        
        # Move to next video (with wraparound)
        _current_video_index = (_current_video_index + 1) % len(video_blobs)
        next_blob = video_blobs[_current_video_index]
        
        return jsonify(_get_video_data(next_blob))
    except Exception as e:
        return {"error": str(e)}, 500 