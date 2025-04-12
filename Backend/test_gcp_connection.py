#!/usr/bin/env python3
"""
Test script to verify connection to GCP Cloud SQL instance.
This script will attempt to connect to your GCP Cloud SQL instance
using the Cloud SQL Python Connector.
"""

import os
import sys
from dotenv import load_dotenv
from google.cloud.sql.connector import Connector

# Load environment variables from .env file
load_dotenv()

# Required environment variables
required_vars = ['DB_INSTANCE', 'DB_USER', 'DB_PASS', 'DB_NAME']
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    print(f"ERROR: Missing required environment variables: {', '.join(missing_vars)}")
    print("Please set these variables in your .env file")
    sys.exit(1)

# Get environment variables
db_instance = os.getenv('DB_INSTANCE')
db_user = os.getenv('DB_USER')
db_pass = os.getenv('DB_PASS')
db_name = os.getenv('DB_NAME')

print(f"Attempting to connect to Cloud SQL instance: {db_instance}")
print(f"Using database: {db_name}, user: {db_user}")

# Initialize the connector
connector = Connector()

# Function to establish a connection to a Cloud SQL instance
def getconn():
    try:
        conn = connector.connect(
            db_instance,
            "pg8000",
            user=db_user,
            password=db_pass,
            db=db_name
        )
        print("✅ Successfully connected to the database!")
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        raise

try:
    # Test the connection
    conn = getconn()
    
    # Execute a simple query
    cursor = conn.cursor()
    cursor.execute('SELECT version();')
    version = cursor.fetchone()[0]
    print(f"PostgreSQL version: {version}")
    
    # Check for User table
    cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'User')")
    user_table_exists = cursor.fetchone()[0]
    
    if user_table_exists:
        print("✅ User table exists")
        
        # Check User table structure
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'User'
        """)
        columns = cursor.fetchall()
        print("User table columns:")
        for col in columns:
            print(f"  - {col[0]} ({col[1]})")
    else:
        print("❌ User table does not exist")
        
    # Close the cursor and connection
    cursor.close()
    conn.close()
    print("Connection closed")
    
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)

print("\nGCP Cloud SQL connection test completed successfully! 🎉") 