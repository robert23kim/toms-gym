#!/usr/bin/env python3
"""
Script to apply database schema to different database types.
Supports PostgreSQL, SQLite, and other SQL databases.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional
import sqlite3
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_gcp_connection() -> Optional[psycopg2.extensions.connection]:
    """Get a connection to a Google Cloud SQL database."""
    try:
        # Import libraries for Google Cloud SQL
        from google.cloud.sql.connector import Connector
        import pg8000
        
        # Get connection parameters from environment
        db_instance = os.getenv('DB_INSTANCE')  # format: project:region:instance
        db_user = os.getenv('DB_USER', 'postgres')
        db_pass = os.getenv('DB_PASS')
        db_name = os.getenv('DB_NAME', 'postgres')
        
        if not db_instance:
            logger.error("DB_INSTANCE environment variable is required for GCP connections")
            logger.info("Format: project-id:region:instance-name (e.g., toms-gym:us-central1:toms-gym-db)")
            return None
            
        if not db_pass:
            logger.error("DB_PASS environment variable is required for GCP connections")
            return None
        
        # Initialize the connector
        logger.info(f"Connecting to Google Cloud SQL instance: {db_instance}")
        connector = Connector()
        
        # Function to return the database connection
        def getconn():
            conn = connector.connect(
                db_instance,  # Cloud SQL instance connection name
                "pg8000",  # PostgreSQL database driver
                user=db_user,
                password=db_pass,
                db=db_name
            )
            return conn
        
        # Get connection
        conn = getconn()
        conn.autocommit = True
        logger.info(f"Successfully connected to GCP Cloud SQL instance: {db_instance}")
        return conn
    
    except ImportError as e:
        logger.error(f"Missing required packages for GCP connection: {e}")
        logger.info("Install with: pip install cloud-sql-python-connector pg8000")
        return None
    except Exception as e:
        logger.error(f"Failed to connect to Google Cloud SQL: {e}")
        return None

def get_db_connection(db_type: str) -> Optional[sqlite3.Connection | psycopg2.extensions.connection]:
    """Get a database connection based on the database type."""
    if db_type == 'sqlite':
        db_path = os.getenv('SQLITE_DB_PATH', 'toms_gym.db')
        return sqlite3.connect(db_path)
    
    elif db_type == 'postgres':
        # Check if we should use GCP Cloud SQL connector
        use_gcp = os.getenv('USE_GCP', '').lower() in ('true', 'yes', '1')
        if use_gcp:
            return get_gcp_connection()
            
        # Otherwise use direct PostgreSQL connection
        try:
            conn = psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                database=os.getenv('DB_NAME', 'postgres'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASS', 'postgres'),
                port=os.getenv('DB_PORT', '5432')
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            return conn
        except psycopg2.OperationalError as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            return None
    
    else:
        logger.error(f"Unsupported database type: {db_type}")
        return None

def drop_existing_tables(conn, db_type: str):
    """Drop all existing tables in the correct order to respect foreign key constraints."""
    try:
        cursor = conn.cursor()
        
        # For PostgreSQL, also drop custom types and functions
        if db_type == 'postgres':
            logger.info("Dropping existing tables and custom types...")
            
            # Tables with foreign key dependencies should be dropped first
            # Order matters to avoid foreign key constraint violations
            tables_to_drop = [
                "TokenBlacklist",
                "SecurityAudit",
                "UserSession",
                "Attempt",
                "UserCompetition",
                "Competition",
                "User"
            ]
            
            for table in tables_to_drop:
                try:
                    cursor.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE;')
                    logger.info(f"Dropped table: {table}")
                except Exception as e:
                    logger.warning(f"Error dropping table {table}: {e}")
            
            # Drop custom functions
            cursor.execute('DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;')
            cursor.execute('DROP FUNCTION IF EXISTS cleanup_expired_sessions() CASCADE;')
            
            # Drop custom types
            custom_types = [
                "user_role",
                "user_status",
                "competition_status",
                "attempt_status",
                "gender",
                "lift_type",
                "weight_class",
                "auth_method"
            ]
            
            for custom_type in custom_types:
                try:
                    cursor.execute(f'DROP TYPE IF EXISTS {custom_type} CASCADE;')
                    logger.info(f"Dropped custom type: {custom_type}")
                except Exception as e:
                    logger.warning(f"Error dropping type {custom_type}: {e}")
                
        elif db_type == 'sqlite':
            # SQLite doesn't support DROP TYPE, but we can drop tables
            logger.info("Dropping existing tables...")
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            # Enable foreign key pragma temporarily
            cursor.execute("PRAGMA foreign_keys = OFF;")
            
            for table in tables:
                table_name = table[0]
                if table_name != 'sqlite_sequence':  # Skip internal SQLite tables
                    cursor.execute(f'DROP TABLE IF EXISTS "{table_name}";')
                    logger.info(f"Dropped table: {table_name}")
            
            # Re-enable foreign key pragma
            cursor.execute("PRAGMA foreign_keys = ON;")
        
        conn.commit()
        logger.info("All existing tables dropped successfully")
        
    except Exception as e:
        logger.error(f"Error dropping existing tables: {e}")
        raise

def apply_schema(conn, schema_file: str, db_type: str):
    """Apply the schema to the database."""
    try:
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        # Modify SQL for SQLite if needed
        if db_type == 'sqlite':
            # Replace PostgreSQL-specific syntax with SQLite equivalents
            schema_sql = schema_sql.replace('UUID', 'TEXT')
            schema_sql = schema_sql.replace('uuid_generate_v4()', "lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))")
            schema_sql = schema_sql.replace('TIMESTAMP WITH TIME ZONE', 'TIMESTAMP')
            schema_sql = schema_sql.replace('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";', '')
            schema_sql = schema_sql.replace('CREATE TYPE', '-- CREATE TYPE')  # Comment out ENUM types
            schema_sql = schema_sql.replace('$$ language', '$$ LANGUAGE')  # Fix case sensitivity
        
        cursor = conn.cursor()
        
        # Split SQL into individual statements
        statements = schema_sql.split(';')
        
        for statement in statements:
            if statement.strip():
                try:
                    cursor.execute(statement)
                except Exception as e:
                    logger.warning(f"Error executing statement: {e}")
                    logger.debug(f"Statement: {statement}")
        
        conn.commit()
        logger.info("Schema applied successfully!")
        
    except Exception as e:
        logger.error(f"Error applying schema: {e}")
        raise

def main():
    """Main function to apply the schema."""
    # Load environment variables
    load_dotenv()
    
    # Get database type from environment or default to PostgreSQL
    db_type = os.getenv('DB_TYPE', 'postgres').lower()
    
    # Check for GCP project
    gcp_project = os.getenv('GCP_PROJECT')
    if gcp_project:
        logger.info(f"GCP project specified: {gcp_project}")
        os.environ['USE_GCP'] = 'true'
        
        # Set DB_INSTANCE if not already set
        if not os.getenv('DB_INSTANCE'):
            # Default instance pattern for Cloud SQL in GCP
            region = os.getenv('GCP_REGION', 'us-central1')
            db_instance = f"{gcp_project}:{region}:{gcp_project}-db"
            os.environ['DB_INSTANCE'] = db_instance
            logger.info(f"Using DB instance: {db_instance}")
    
    # Get schema file path
    schema_file = os.path.join(
        Path(__file__).parent.absolute(),
        'schema.sql'
    )
    
    if not os.path.exists(schema_file):
        logger.error(f"Schema file not found: {schema_file}")
        sys.exit(1)
    
    # Get database connection
    conn = get_db_connection(db_type)
    if not conn:
        logger.error("Failed to establish database connection")
        sys.exit(1)
    
    try:
        # Ask for confirmation before dropping tables
        should_drop = os.getenv('DROP_TABLES', '').lower() in ('true', 'yes', '1')
        
        if not should_drop:
            confirm = input("⚠️ WARNING: This will drop all existing tables and data. Are you sure? (y/N): ")
            should_drop = confirm.lower() in ('y', 'yes')
        
        if should_drop:
            # Drop existing tables
            drop_existing_tables(conn, db_type)
            
            # Apply schema
            apply_schema(conn, schema_file, db_type)
            logger.info("✅ Schema reset and reapplied successfully!")
        else:
            logger.info("Operation cancelled by user.")
            sys.exit(0)
    finally:
        conn.close()

if __name__ == '__main__':
    main() 