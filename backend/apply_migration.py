import os
import argparse
from dotenv import load_dotenv
import sqlalchemy
from sqlalchemy import text

load_dotenv()

def get_db_connection():
    # Get database connection parameters from env variables
    db_user = os.getenv('DB_USER', 'postgres')
    db_pass = os.getenv('DB_PASS', 'test')
    db_name = os.getenv('DB_NAME', 'postgres')
    db_instance = os.getenv('DB_INSTANCE')
    database_url = os.getenv('DATABASE_URL')
    
    # Use direct SQLite connection if specified
    if os.getenv('USE_MOCK_DB') == 'true':
        engine = sqlalchemy.create_engine("sqlite:///test.db")
        return engine.connect()
    
    # Use DATABASE_URL if provided
    if database_url:
        engine = sqlalchemy.create_engine(database_url)
        return engine.connect()
    
    # Otherwise use Google Cloud SQL instance
    if db_instance:
        from google.cloud.sql.connector import Connector
        import pg8000
        
        instance_connection_string = db_instance
        connector = Connector()
        
        def getconn():
            conn = connector.connect(
                instance_connection_string,
                "pg8000",
                user=db_user,
                password=db_pass,
                db=db_name
            )
            return conn
        
        engine = sqlalchemy.create_engine("postgresql+pg8000://", creator=getconn)
        return engine.connect()
    
    # Fallback to local PostgreSQL
    local_db_url = f"postgresql://{db_user}:{db_pass}@localhost:5432/{db_name}"
    engine = sqlalchemy.create_engine(local_db_url)
    return engine.connect()

def apply_migration(sql_file_path):
    print(f"Applying migration from {sql_file_path}")
    
    # Read SQL file
    with open(sql_file_path, 'r') as f:
        sql = f.read()
    
    # Execute SQL
    conn = get_db_connection()
    try:
        conn.execute(text(sql))
        conn.commit()
        print("Migration applied successfully")
    except Exception as e:
        print(f"Error applying migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Apply database migrations')
    parser.add_argument('sql_file', help='Path to the SQL file to apply')
    
    args = parser.parse_args()
    apply_migration(args.sql_file) 