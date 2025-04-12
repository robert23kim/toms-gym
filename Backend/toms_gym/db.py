import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Determine if we should use a mock/SQLite database for local development
USE_MOCK_DB = os.getenv('USE_MOCK_DB', 'false').lower() == 'true'
DATABASE_URL = os.getenv('DATABASE_URL')

if USE_MOCK_DB:
    logger.info(f"Using mock database with URL: {DATABASE_URL}")
    # SQLite connection
    engine = create_engine(DATABASE_URL)
elif DATABASE_URL:
    logger.info(f"Using direct database connection with URL: {DATABASE_URL}")
    engine = create_engine(DATABASE_URL)
else:
    # Cloud SQL connection with connector
    try:
        from google.cloud.sql.connector import Connector
        
        # Initialize the Cloud SQL Python Connector
        connector = Connector()
        
        def getconn():
            """
            Returns a secure connection to your Cloud SQL instance.
            """
            try:
                db_instance = os.getenv('DB_INSTANCE')
                db_user = os.getenv('DB_USER')
                db_pass = os.getenv('DB_PASS')
                db_name = os.getenv('DB_NAME')
                
                logger.info(f"Connecting to database: {db_instance}, user: {db_user}, db: {db_name}")
                
                if not db_instance or not db_user or not db_pass or not db_name:
                    raise ValueError("Missing required database environment variables")
                
                conn = connector.connect(
                    db_instance,  # project-id:region:instance-name
                    "pg8000",
                    user=db_user,
                    password=db_pass,
                    db=db_name
                )
                return conn
            except Exception as e:
                logger.error(f"Database connection error: {str(e)}")
                raise
                
        # Create a SQLAlchemy engine
        engine = sqlalchemy.create_engine(
            "postgresql+pg8000://",  # DSN prefix
            creator=getconn,        # uses the getconn() function to connect
        )
        logger.info("PostgreSQL connection engine created")
    except Exception as e:
        logger.error(f"Error setting up database connection: {str(e)}")
        raise

# Create a scoped session factory
Session = scoped_session(sessionmaker(bind=engine))

def get_db():
    """
    Returns the database engine.
    """
    return engine

def get_db_connection():
    """
    Returns a database session.
    This function is used by auth_routes.py.
    """
    try:
        session = Session()
        return session
    except Exception as e:
        logger.error(f"Error getting database session: {str(e)}")
        raise 