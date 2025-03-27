# app.py
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from google.cloud.sql.connector import Connector
from google.cloud import storage
from dotenv import load_dotenv
import sqlalchemy
from werkzeug.utils import secure_filename
import json

load_dotenv()

ALLOWED_EXTENSIONS = {'mov', 'mp4', 'avi', 'mkv'}  # Explicitly allowed formats

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
CORS(app)  # Enable CORS for all routes

# Initialize Google Cloud Storage client
storage_client = storage.Client.from_service_account_json(
    os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
)
bucket_name = os.getenv('GCS_BUCKET_NAME')
bucket = storage_client.bucket(bucket_name)

# Initialize the Cloud SQL Python Connector
connector = Connector()

def getconn():
    """
    Returns a secure connection to your Cloud SQL instance.
    Replace 'project-id:region:instance-id' with your actual instance details.
    """
    conn = connector.connect(
        "toms-gym:us-east1:my-db",  # project-id:region:instance-name
        "pg8000",
        user="postgres",
        password="test",
        db="postgres"
    )
    return conn

# Create a SQLAlchemy connection pool
pool = sqlalchemy.create_engine(
    "postgresql+pg8000://",
    creator=getconn,
)

@app.route('/')
def hello():
    return "Hello from Flask + Cloud SQL (Postgres)!"

@app.route('/competitions')
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

@app.route('/competitions/<int:competition_id>')
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

@app.route('/competitions/<int:competition_id>/participants')
def get_competition_participants(competition_id):
    """
    Endpoint that queries all participants for a specific competition.
    """
    try:
        with pool.connect() as conn:
            rows = conn.execute(
                sqlalchemy.text("""
                    SELECT u.id, u.name, u.avatar, uc.weight_class, u.country,
                           COALESCE(SUM(CASE WHEN a.attempt_result = true THEN a.weight_attempted ELSE 0 END), 0) as total_weight,
                           json_object_agg(
                               a.lift_type,
                               json_agg(
                                   json_build_object(
                                       'weight', a.weight_attempted,
                                       'success', a.attempt_result
                                   )
                               )
                           ) as attempts
                    FROM UserCompetition uc
                    JOIN Users u ON uc.userid = u.id
                    LEFT JOIN Attempts a ON uc.usercompetitionid = a.usercompetitionid
                    WHERE uc.competitionid = :competition_id
                    GROUP BY u.id, u.name, u.avatar, uc.weight_class, u.country
                """),
                {"competition_id": competition_id}
            )
            results = [row._asdict() for row in rows]
        return {"participants": results}
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/competitions/<int:competition_id>/lifts')
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
                           a.video_link as video_url, a.timestamp
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

@app.route('/create_competition', methods=['POST'])
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

@app.route('/create_user', methods=['POST'])
def create_user():
    """
    Endpoint to create a new user.
    Expects JSON payload with user details.
    """
    try:
        data = request.json
        insert_query = sqlalchemy.text(
            """
            INSERT INTO \"User\" (gender, name, email)
            VALUES (:gender, :name, :email)
            RETURNING userid;
            """
        )

        with pool.connect() as conn:
            result = conn.execute(insert_query, data)
            user_id = result.fetchone()[0]
            conn.commit()

        return {"message": "User created successfully!", "user_id": user_id}, 201
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/join_competition', methods=['POST'])
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

@app.route('/submit_attempt', methods=['POST'])
def submit_attempt():
    """
    Endpoint to submit an attempt for a competition.
    Expects JSON payload with attempt details.
    """
    try:
        data = request.json
        insert_query = sqlalchemy.text(
            """
            INSERT INTO Attempts (usercompetitionid, lift_type, weight_attempted, attempt_number, attempt_result, video_link)
            VALUES (:usercompetitionid, :lift_type, :weight_attempted, :attempt_number, :attempt_result, :video_link)
            RETURNING attemptid;
            """
        )

        with pool.connect() as conn:
            result = conn.execute(insert_query, data)
            attempt_id = result.fetchone()[0]
            conn.commit()

        return {"message": "Attempt submitted successfully!", "attempt_id": attempt_id}, 201
    except Exception as e:
        return {"error": str(e)}, 500

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400

    video = request.files['video']

    if video.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if not allowed_file(video.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    filename = secure_filename(video.filename)
    local_file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    video.save(local_file_path)

    blob = bucket.blob(f'videos/{filename}')

    # Explicitly set correct MIME type
    mime_type = 'video/quicktime' if filename.lower().endswith('.mov') else video.mimetype
    blob.upload_from_filename(local_file_path, content_type=mime_type)
    print('Video uploaded')

    #blob.make_public()
    #print('Public blob created')
    #public_url = blob.public_url

    print('Cleaning up temp files')
    os.remove(local_file_path)
    print('Clean up completed')

    return jsonify({
        'message': 'Video successfully uploaded'
    }), 200

@app.route('/users/<int:user_id>')
def get_user_profile(user_id):
    """
    Endpoint that queries a user's profile including their competition history and achievements.
    """
    try:
        with pool.connect() as conn:
            # Get user basic info
            user_row = conn.execute(
                sqlalchemy.text("SELECT * FROM \"User\" WHERE userid = :user_id"),
                {"user_id": user_id}
            ).fetchone()
            
            if user_row is None:
                return {"error": "User not found"}, 404
            
            user_data = user_row._asdict()

            # Get user's competition history
            competitions = conn.execute(
                sqlalchemy.text("""
                    SELECT c.id, c.name, c.start_date, c.end_date, c.location,
                           uc.weight_class, uc.status,
                           COALESCE(SUM(CASE WHEN a.attempt_result = true THEN a.weight_attempted ELSE 0 END), 0) as total_weight,
                           COUNT(DISTINCT CASE WHEN a.attempt_result = true THEN a.lift_type END) as successful_lifts
                    FROM UserCompetition uc
                    JOIN Competition c ON uc.competitionid = c.id
                    LEFT JOIN Attempts a ON uc.usercompetitionid = a.usercompetitionid
                    WHERE uc.userid = :user_id
                    GROUP BY c.id, c.name, c.start_date, c.end_date, c.location, uc.weight_class, uc.status
                    ORDER BY c.start_date DESC
                """),
                {"user_id": user_id}
            ).fetchall()

            # Get user's best lifts
            best_lifts = conn.execute(
                sqlalchemy.text("""
                    SELECT a.lift_type as type,
                           MAX(a.weight_attempted) as best_weight,
                           c.name as competition_name,
                           c.id as competition_id
                    FROM Attempts a
                    JOIN UserCompetition uc ON a.usercompetitionid = uc.usercompetitionid
                    JOIN Competition c ON uc.competitionid = c.id
                    WHERE uc.userid = :user_id
                    AND a.attempt_result = true
                    GROUP BY a.lift_type, c.name, c.id
                """),
                {"user_id": user_id}
            ).fetchall()

            # Get user's achievements
            achievements = conn.execute(
                sqlalchemy.text("""
                    SELECT 
                        COUNT(DISTINCT c.id) as total_competitions,
                        COUNT(DISTINCT CASE WHEN a.attempt_result = true THEN a.lift_type END) as total_successful_lifts,
                        MAX(a.weight_attempted) as heaviest_lift,
                        COUNT(DISTINCT CASE WHEN a.attempt_result = true THEN a.lift_type END) FILTER (WHERE a.lift_type = 'Squat') as best_squat,
                        COUNT(DISTINCT CASE WHEN a.attempt_result = true THEN a.lift_type END) FILTER (WHERE a.lift_type = 'Bench Press') as best_bench,
                        COUNT(DISTINCT CASE WHEN a.attempt_result = true THEN a.lift_type END) FILTER (WHERE a.lift_type = 'Deadlift') as best_deadlift
                    FROM UserCompetition uc
                    JOIN Competition c ON uc.competitionid = c.id
                    LEFT JOIN Attempts a ON uc.usercompetitionid = a.usercompetitionid
                    WHERE uc.userid = :user_id
                """),
                {"user_id": user_id}
            ).fetchone()

            return {
                "user": user_data,
                "competitions": [row._asdict() for row in competitions],
                "best_lifts": [row._asdict() for row in best_lifts],
                "achievements": achievements._asdict() if achievements else {}
            }
    except Exception as e:
        return {"error": str(e)}, 500

if __name__ == "__main__":
    # IMPORTANT: Cloud Run expects the app to listen on port 8080
    app.run(host="0.0.0.0", port=8080)


