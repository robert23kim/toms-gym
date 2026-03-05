#!/usr/bin/env python3
"""
Script to apply the enum fixes to an existing database.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

# Add parent directory to sys.path to import from apply_schema
sys.path.append(str(Path(__file__).parent.absolute()))
from apply_schema import get_db_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def apply_enum_updates(conn, update_file: str):
    """Apply the enum updates to the database."""
    try:
        with open(update_file, 'r') as f:
            update_sql = f.read()
        
        cursor = conn.cursor()
        
        # Split SQL into individual statements
        statements = update_sql.split(';')
        
        for statement in statements:
            if statement.strip():
                try:
                    cursor.execute(statement)
                    logger.info(f"Executed statement successfully")
                except Exception as e:
                    logger.error(f"Error executing statement: {e}")
                    logger.debug(f"Statement: {statement}")
                    raise
        
        conn.commit()
        logger.info("✅ Enum updates applied successfully!")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error applying enum updates: {e}")
        raise

def main():
    """Main function to apply the enum updates."""
    # Load environment variables
    load_dotenv()
    
    # Get database type from environment or default to PostgreSQL
    db_type = os.getenv('DB_TYPE', 'postgres').lower()
    
    if db_type != 'postgres':
        logger.error(f"This script only supports PostgreSQL databases.")
        sys.exit(1)
    
    # Get update file path
    update_file = os.path.join(
        Path(__file__).parent.absolute(),
        'update_enums.sql'
    )
    
    if not os.path.exists(update_file):
        logger.error(f"Update file not found: {update_file}")
        sys.exit(1)
    
    # Get database connection
    conn = get_db_connection(db_type)
    if not conn:
        logger.error("Failed to establish database connection")
        sys.exit(1)
    
    try:
        # Ask for confirmation before applying updates
        should_update = os.getenv('FORCE_UPDATE', '').lower() in ('true', 'yes', '1')
        
        if not should_update:
            confirm = input("⚠️ WARNING: This will modify database enums. Backup your database first. Continue? (y/N): ")
            should_update = confirm.lower() in ('y', 'yes')
        
        if should_update:
            # Apply enum updates
            apply_enum_updates(conn, update_file)
        else:
            logger.info("Operation cancelled by user.")
            sys.exit(0)
    finally:
        conn.close()

if __name__ == '__main__':
    main() 