# app.py
from flask import Flask, request
from google.cloud.sql.connector import Connector
import sqlalchemy
import json

app = Flask(__name__)

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

if __name__ == "__main__":
    # IMPORTANT: Cloud Run expects the app to listen on port 8080
    app.run(host="0.0.0.0", port=8080)


