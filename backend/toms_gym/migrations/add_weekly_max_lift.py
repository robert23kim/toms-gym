#!/usr/bin/env python3
"""
Migration script to add the WeeklyMaxLift table.
This is an incremental migration that does not drop existing tables.
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# SQL to create the weekly_lift_type enum and WeeklyMaxLift table
MIGRATION_SQL = """
-- Create enum for weekly lift types (if not exists)
DO $$ BEGIN
    CREATE TYPE weekly_lift_type AS ENUM ('bench', 'squat', 'deadlift', 'sitting_press');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create WeeklyMaxLift table for tracking weekly max lifts
CREATE TABLE IF NOT EXISTS "WeeklyMaxLift" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES "User"(id) ON DELETE CASCADE,
    week_start_date DATE NOT NULL,
    lift_type weekly_lift_type NOT NULL,
    weight_lbs DECIMAL(5,1) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, week_start_date, lift_type)
);

-- Create indexes if they don't exist
CREATE INDEX IF NOT EXISTS idx_weekly_max_lift_user_id ON "WeeklyMaxLift"(user_id);
CREATE INDEX IF NOT EXISTS idx_weekly_max_lift_user_week ON "WeeklyMaxLift"(user_id, week_start_date);

-- Create trigger for updating timestamps (drop and recreate to be safe)
DROP TRIGGER IF EXISTS update_weekly_max_lift_updated_at ON "WeeklyMaxLift";
CREATE TRIGGER update_weekly_max_lift_updated_at
    BEFORE UPDATE ON "WeeklyMaxLift"
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
"""


def get_gcp_connection():
    """Get a connection to a Google Cloud SQL database."""
    try:
        from google.cloud.sql.connector import Connector
        import pg8000

        db_instance = os.getenv('DB_INSTANCE')
        db_user = os.getenv('DB_USER', 'postgres')
        db_pass = os.getenv('DB_PASS')
        db_name = os.getenv('DB_NAME', 'postgres')

        if not db_instance:
            logger.error("DB_INSTANCE environment variable is required")
            return None

        if not db_pass:
            logger.error("DB_PASS environment variable is required")
            return None

        logger.info(f"Connecting to Google Cloud SQL instance: {db_instance}")
        connector = Connector()

        def getconn():
            conn = connector.connect(
                db_instance,
                "pg8000",
                user=db_user,
                password=db_pass,
                db=db_name
            )
            return conn

        conn = getconn()
        conn.autocommit = True
        logger.info(f"Successfully connected to GCP Cloud SQL instance: {db_instance}")
        return conn

    except ImportError as e:
        logger.error(f"Missing required packages: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to connect to Google Cloud SQL: {e}")
        return None


def run_migration():
    """Run the migration to add the WeeklyMaxLift table."""
    load_dotenv()

    conn = get_gcp_connection()
    if not conn:
        logger.error("Failed to establish database connection")
        sys.exit(1)

    try:
        cursor = conn.cursor()

        logger.info("Running WeeklyMaxLift migration...")
        cursor.execute(MIGRATION_SQL)

        logger.info("Migration completed successfully!")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    run_migration()
