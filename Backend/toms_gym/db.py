import sqlalchemy
from google.cloud.sql.connector import Connector
import os

# Initialize the Cloud SQL Python Connector
connector = Connector()

def getconn():
    """
    Returns a secure connection to your Cloud SQL instance.
    """
    conn = connector.connect(
        os.getenv('DB_INSTANCE'),  # project-id:region:instance-name
        "pg8000",
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASS'),
        db=os.getenv('DB_NAME')
    )
    return conn

# Create a SQLAlchemy connection pool
pool = sqlalchemy.create_engine(
    "postgresql+pg8000://",  # DSN prefix
    creator=getconn,         # uses the getconn() function to connect
)

def get_db():
    """
    Returns the database connection pool.
    """
    return pool 