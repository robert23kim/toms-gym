# app.py
from flask import Flask
from google.cloud.sql.connector import Connector
import sqlalchemy

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
        user="my_user",
        password="tomsgym",
        db="my-db"
    )
    return conn

# Create a SQLAlchemy connection pool 
pool = sqlalchemy.create_engine(
    "postgresql+pg8000://",  # DSN prefix
    creator=getconn,         # uses the getconn() function to connect
)

@app.route('/')
def hello():
    return "Hello from Flask + Cloud SQL (Postgres)!"

@app.route('/users')
def get_users():
    """
    Example endpoint that queries a 'users' table.
    """
    try:
        with pool.connect() as conn:
            rows = conn.execute(sqlalchemy.text("SELECT * FROM users"))
            results = [dict(row) for row in rows]
        return {"users": results}
    except Exception as e:
        return {"error": str(e)}, 500

if __name__ == "__main__":
    # IMPORTANT: Cloud Run expects the app to listen on port 8080
    app.run(host="0.0.0.0", port=8080)

