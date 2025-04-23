import pytest
import time
import json
import random
from flask import Flask
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
import os
import uuid
import jwt
import bcrypt
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Import the actual app instance and session factory
from toms_gym.app import app as application # Rename to avoid conflict
from toms_gym.db import Session as DBSession, engine as db_engine

# Assuming models might be needed for type hints or direct interaction (adjust path if necessary)
# from toms_gym.models import User

# Test Configuration
TEST_CONFIG = {
    'TESTING': True,
    # Use the DATABASE_URL from environment, default to the test DB used by docker-compose.test.yml
    'SQLALCHEMY_DATABASE_URI': os.environ.get('DATABASE_URL', 'postgresql://postgres:test@db-test:5432/toms_gym_test'),
    'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    'JWT_SECRET_KEY': os.getenv('JWT_SECRET_KEY', 'test-secret-key'),
    'SECRET_KEY': os.getenv('SECRET_KEY', 'test-secret-key'),
    'DEBUG_TB_ENABLED': False,
    'LIMITER_ENABLED': False,
    'WTF_CSRF_ENABLED': False, # Assuming no forms needing CSRF in API tests
    # Ensure environment reflects testing
    'FLASK_ENV': 'testing',
    'DEBUG': False, # Usually False for testing, unless debugging tests
}

@pytest.fixture(scope='session')
def app():
    """Session-wide test Flask application."""
    print("\nConfiguring Flask app for testing...")
    application.config.update(TEST_CONFIG)

    # Push an application context for the duration of the session
    # This context allows fixtures and tests to access `current_app`
    ctx = application.app_context()
    ctx.push()
    print("🚀 Pushed Flask application context for test session.")

    yield application # Provide the configured app instance

    ctx.pop()
    print("🏁 Popped Flask application context.")


@pytest.fixture(scope='session', autouse=True)
def init_db(app):
    """Initialize the test database schema once per session using raw SQL."""
    print(f"\n🔧 Initializing database schema via init_db fixture...")
    # Use a temporary session specifically for schema creation
    session = DBSession()
    try:
        # Ensure operations run within the application context established by the 'app' fixture
        with app.app_context():
            print("Executing raw SQL for schema creation within app context...")

            # Drop existing tables first (order matters for FKs)
            print("Dropping existing tables (if any)...")
            tables_to_drop = [
                "TokenBlacklist", "SecurityAudit", "UserSession", "Attempt",
                "UserCompetition", "Competition", "User"
            ]
            for table in tables_to_drop:
                try:
                    session.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE;'))
                    print(f"  Dropped table: {table}")
                except Exception as e:
                    print(f"  Warning: Error dropping table {table}: {e}")

            # Drop custom types if they exist (specific to PostgreSQL)
            if db_engine.dialect.name == 'postgresql':
                 print("Dropping custom types (PostgreSQL)...")
                 custom_types = [
                     "user_role", "user_status", "competition_status", "attempt_status",
                     "gender", "lift_type", "weight_class", "auth_method"
                 ]
                 for custom_type in custom_types:
                     try:
                         session.execute(text(f'DROP TYPE IF EXISTS {custom_type} CASCADE;'))
                         print(f"  Dropped type: {custom_type}")
                     except Exception as e:
                        print(f"  Warning: Error dropping type {custom_type}: {e}")

            # Recreate types (specific to PostgreSQL)
            if db_engine.dialect.name == 'postgresql':
                print("Creating custom types (PostgreSQL)...")
                session.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\""))
                session.execute(text("CREATE TYPE user_role AS ENUM ('admin', 'user', 'judge')"))
                session.execute(text("CREATE TYPE user_status AS ENUM ('active', 'inactive', 'locked')"))
                session.execute(text("CREATE TYPE competition_status AS ENUM ('upcoming', 'in_progress', 'completed', 'cancelled')"))
                session.execute(text("CREATE TYPE attempt_status AS ENUM ('pending', 'completed', 'failed')"))
                session.execute(text("CREATE TYPE gender AS ENUM ('male', 'female', 'other')"))
                session.execute(text("CREATE TYPE lift_type AS ENUM ('snatch', 'clean_and_jerk', 'Squat', 'Bench Press', 'Deadlift')"))
                # Note: weight_class enum might need adjustment if it differs from model/schema.sql
                session.execute(text("CREATE TYPE weight_class AS ENUM ('56kg', '62kg', '66kg', '69kg', '74kg', '77kg', '83kg', '85kg', '93kg', '94kg', '105kg', '120kg', '+120kg', 'plus_105kg')"))
                session.execute(text("CREATE TYPE auth_method AS ENUM ('google', 'password')"))
                print("✅ Types created.")

            # Create Tables (using simplified VARCHAR for enums for broad compatibility if needed, or use real types)
            print("Creating User table...")
            session.execute(text("""
            CREATE TABLE "User" (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                username VARCHAR(255) UNIQUE, email VARCHAR(255) UNIQUE NOT NULL, name VARCHAR(255) NOT NULL,
                password_hash VARCHAR(255), google_id VARCHAR(255) UNIQUE,
                role user_role NOT NULL DEFAULT 'user', status user_status NOT NULL DEFAULT 'active',
                auth_method auth_method, failed_login_attempts INTEGER DEFAULT 0,
                last_login_attempt TIMESTAMP WITH TIME ZONE, account_locked_until TIMESTAMP WITH TIME ZONE,
                password_reset_token VARCHAR(255), password_reset_expiry TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
            """)) # Add other tables (Competition, UserCompetition, Attempt, etc.) using similar CREATE TABLE statements
            print("Creating Competition table...")
            session.execute(text("""
            CREATE TABLE "Competition" (
                id UUID PRIMARY KEY, name VARCHAR(255) NOT NULL, description TEXT,
                start_date TIMESTAMP WITH TIME ZONE NOT NULL, end_date TIMESTAMP WITH TIME ZONE NOT NULL,
                status competition_status NOT NULL DEFAULT 'upcoming',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
            """))
            print("Creating UserCompetition table...")
            session.execute(text("""
            CREATE TABLE "UserCompetition" (
                id UUID PRIMARY KEY, user_id UUID REFERENCES "User"(id) ON DELETE CASCADE,
                competition_id UUID REFERENCES "Competition"(id) ON DELETE CASCADE,
                weight_class weight_class NOT NULL, gender gender, status VARCHAR(50) DEFAULT 'active',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, competition_id)
            )
            """))
            print("Creating Attempt table...")
            session.execute(text("""
            CREATE TABLE "Attempt" (
                id UUID PRIMARY KEY, user_competition_id UUID REFERENCES "UserCompetition"(id) ON DELETE CASCADE,
                lift_type VARCHAR(50) NOT NULL, weight_kg DECIMAL(5,2) NOT NULL,
                status attempt_status NOT NULL DEFAULT 'pending', video_url TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
            """))
            # ... Add CREATE TABLE for SecurityAudit, TokenBlacklist, UserSession ...
            print("Creating SecurityAudit table...")
            session.execute(text("""
            CREATE TABLE "SecurityAudit" ( id UUID PRIMARY KEY DEFAULT gen_random_uuid(), event_type VARCHAR(50) NOT NULL, user_id UUID REFERENCES "User"(id) ON DELETE SET NULL, ip_address VARCHAR(45), user_agent TEXT, details JSONB, success BOOLEAN NOT NULL, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP )
            """))
            print("Creating TokenBlacklist table...")
            session.execute(text("""
            CREATE TABLE "TokenBlacklist" ( id UUID PRIMARY KEY DEFAULT gen_random_uuid(), token_id VARCHAR(255) UNIQUE NOT NULL, user_id UUID REFERENCES "User"(id) ON DELETE CASCADE, expires_at TIMESTAMP WITH TIME ZONE NOT NULL, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP )
            """))
            print("Creating UserSession table...")
            session.execute(text("""
            CREATE TABLE "UserSession" ( id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID REFERENCES "User"(id) ON DELETE CASCADE, refresh_token_id VARCHAR(255) UNIQUE NOT NULL, ip_address VARCHAR(45), user_agent TEXT, expires_at TIMESTAMP WITH TIME ZONE NOT NULL, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP )
            """))

            # Create Indexes
            print("Creating indexes...")
            # Add CREATE INDEX statements here...
            session.execute(text('CREATE INDEX IF NOT EXISTS idx_user_email ON "User"(email)'))
            session.execute(text('CREATE INDEX IF NOT EXISTS idx_user_username ON "User"(username)'))
            # ... Add other indexes

            session.commit()
            print("COMMIT transaction for schema creation.")
            print("✅ Database schema initialization committed successfully.")
            # Optional short delay
            # print("⏳ Waiting 1 second after schema creation...")
            # time.sleep(1)

    except Exception as e:
        print(f"❌ Error during database schema initialization: {e}")
        session.rollback()
        raise
    finally:
        DBSession.remove() # Clean up the session used specifically for init_db
        print("init_db fixture finished, session removed.")


@pytest.fixture(scope='function')
def db_session(app):
    """Provides a transactional session per test function, ensuring cleanup."""
    session = DBSession()
    print(f"  SETUP test: db_session fixture created session {id(session)}")
    yield session # Provide the session object to the test

    # Cleanup after test function finishes
    # session.rollback() # Rollback any uncommitted changes from the test - REMOVED AS REQUESTED
    DBSession.remove() # Remove the session, ensures next test gets a fresh one
    print(f"  TEARDOWN test: db_session fixture removed session {id(session)} (NO ROLLBACK)")


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def test_auth_user_data():
    """Generate unique data for an authentication test user."""
    timestamp = int(time.time() * 1000) # Use milliseconds for higher uniqueness
    unique_id = uuid.uuid4().hex[:8]
    return {
        "username": f"testauth_{timestamp}_{unique_id}",
        "email": f"testauth_{timestamp}_{unique_id}@example.com",
        "password": "TestPassword123!",
        "name": "Test Auth User"
    }

@pytest.fixture
def create_auth_user(db_session, test_auth_user_data):
    """Create a test user using the function-scoped db_session."""
    print(f"  SETUP fixture create_auth_user: Using session {id(db_session)}")
    hashed_password = bcrypt.hashpw(
        test_auth_user_data["password"].encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')
    user_id = str(uuid.uuid4())

    try:
        db_session.execute(
            text("""
                INSERT INTO "User" (id, username, email, password_hash, name, auth_method, created_at, status, role)
                VALUES (:id, :username, :email, :password, :name, 'password', :created_at, 'active', 'user')
            """),
            {
                "id": user_id,
                "username": test_auth_user_data["username"],
                "email": test_auth_user_data["email"],
                "password": hashed_password,
                "name": test_auth_user_data["name"],
                "created_at": datetime.utcnow()
            }
        )
        db_session.commit() # Commit this user creation specifically
        print(f"  ✅ Committed user in create_auth_user fixture: {user_id} (Session: {id(db_session)})")
        # Return ID, useful for referencing in tests
        return user_id
    except Exception as e:
        print(f"  ❌ Error in create_auth_user fixture: {e} (Session: {id(db_session)})")
        db_session.rollback() # Rollback this fixture's changes on error
        raise


@pytest.fixture
def auth_app():
    """Create a Flask app with auth blueprints registered"""
    from toms_gym.routes.auth_routes import auth_bp
    from toms_gym.app import app as base_app
    
    # Create app with appropriate configuration
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['JWT_SECRET'] = 'test-secret-key'
    app.config['JWT_SECRET_KEY'] = 'test-secret-key' 
    app.config['JWT_ALGORITHM'] = 'HS256'
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7)  # Updated to match production
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=90)  # Updated to match production
    app.config['DEBUG'] = True
    
    # Copy over any database connection settings from main app
    app.config['DATABASE_URL'] = base_app.config.get('DATABASE_URL', os.environ.get('DATABASE_URL'))
    app.config['GCS_BUCKET'] = base_app.config.get('GCS_BUCKET', 'test-bucket')
    
    # Register auth blueprint
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    print(f"JWT_SECRET_KEY configured as: {app.config['JWT_SECRET_KEY']}")
    
    return app

@pytest.fixture
def auth_client(auth_app):
    """Create a test client for auth routes"""
    return auth_app.test_client()

# Fixture for competition data (if needed by other tests)
@pytest.fixture
def test_competition_data():
    start_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S%z") # Use ISO format
    end_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S%z")
    return {
        "id": str(uuid.uuid4()),
        "name": "Test Competition",
        "start_date": start_date,
        "end_date": end_date,
        "status": "upcoming",
    }

# Fixture for attempt data setup (depends on User and Competition)
# This needs careful handling to ensure prerequisite data exists and is committed
# It might be better to create these within the specific tests needing them
# or use a more robust fixture that creates User, Competition, and UserCompetition first.

# Example (needs refinement based on actual models/logic):
@pytest.fixture
def create_test_setup(db_session, create_auth_user, test_competition_data):
    """Creates User, Competition, UserCompetition for tests needing all."""
    print(f"  SETUP fixture create_test_setup: Using session {id(db_session)}")
    # User is already created and committed by the create_auth_user fixture dependency
    user_id = create_auth_user # The user_id is passed from the fixture

    # Create Competition
    comp_id = test_competition_data['id']
    try:
        db_session.execute(
            text('INSERT INTO "Competition" (id, name, start_date, end_date, status) VALUES (:id, :name, :start_date, :end_date, :status)'),
            test_competition_data
        )

        # Create UserCompetition link
        user_comp_id = str(uuid.uuid4())
        db_session.execute(
            text('INSERT INTO "UserCompetition" (id, user_id, competition_id, weight_class, gender) VALUES (:id, :user_id, :competition_id, :weight_class, :gender)'),
            {"id": user_comp_id, "user_id": user_id, "competition_id": comp_id, "weight_class": "74kg", "gender": "male"}
        )

        db_session.commit()
        print(f"  ✅ Committed Competition & UserCompetition in create_test_setup (Session: {id(db_session)})")
        return {"user_id": user_id, "competition_id": comp_id, "user_competition_id": user_comp_id}
    except Exception as e:
        print(f"  ❌ Error in create_test_setup fixture: {e} (Session: {id(db_session)})")
        db_session.rollback()
        raise

# REMOVE OBSOLETE FIXTURES
# Remove: db_connection, db_engine, auth_app, auth_db_cleanup, test_user_data (if replaced by test_auth_user_data)
# Remove: old test_attempt_data (if replaced or handled differently)

# Add session-scoped fixture to ensure database is ready for auth tests
@pytest.fixture(scope="session", autouse=True)
def ensure_test_environment():
    """Ensure test environment is ready - runs once per test session"""
    # Check if backend service is running via Docker
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=toms-gym-backend", "--format", "{{.Status}}"],
            capture_output=True,
            text=True,
            check=True
        )
        if "Up" not in result.stdout:
            print("⚠️ Backend service not running, some tests might fail")
    except Exception as e:
        print(f"⚠️ Failed to check Docker status: {e}")
        print("Some tests that require a running backend might fail")

@pytest.fixture
def test_auth_user_data():
    """Provide test authentication user data"""
    timestamp = int(time.time())
    unique_id = uuid.uuid4().hex[:8]  # Add unique ID to prevent collisions
    return {
        "username": f"testauthuser_{timestamp}_{unique_id}",
        "email": f"testauthuser_{timestamp}_{unique_id}@example.com",
        "password": "TestPassword123!",
        "name": "Test Auth User"
    }

@pytest.fixture
def auth_db_cleanup():
    """Clean up authentication-related database tables at the beginning of the test session"""
    db_url = os.environ.get('DATABASE_URL', 'postgresql://postgres:test@db-test:5432/toms_gym_test')
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        try:
            conn.execute(text("SET session_replication_role = 'replica';"))
            
            # Delete all data from auth-related tables
            tables = [
                "TokenBlacklist",
                "SecurityAudit",
                "UserSession"
            ]
            for table in tables:
                conn.execute(text(f'DELETE FROM "{table}";'))
            
            # Clean up test users (optional, based on naming convention)
            conn.execute(text('DELETE FROM "User" WHERE email LIKE \'testauthuser_%\';'))
            
            conn.execute(text("SET session_replication_role = 'origin';"))
            conn.commit()
            
            print("✅ Authentication database tables cleaned up")
        except Exception as e:
            print(f"⚠️ Database cleanup error: {e}")
            conn.rollback()

@pytest.fixture
def generate_auth_token():
    """Generate a JWT token for testing"""
    def _generate_token(user_id, token_type='access', expire_days=None):
        secret = 'test-secret-key'
        now = datetime.utcnow()
        
        # Set defaults based on token type
        if expire_days is None:
            if token_type == 'access':
                expire_days = 7  # Default access token lifetime: 7 days
            else:
                expire_days = 90  # Default refresh token lifetime: 90 days
        
        if expire_days > 0:
            exp = now + timedelta(days=expire_days)
        else:
            # For expired tokens (testing)
            exp = now + timedelta(days=expire_days)
        
        token_id = str(uuid.uuid4())
        payload = {
            "user_id": str(user_id),
            "exp": exp,
            "iat": now,
            "jti": token_id,
            "type": token_type
        }
        
        token = jwt.encode(payload, secret, algorithm='HS256')
        print(f"Generated {token_type} token for user {user_id}: {token[:20]}... (expires in {expire_days} days)")
        return token
    
    return _generate_token

@pytest.fixture(scope='session', autouse=True)
def mock_redis():
    """Mock Redis client for all tests to avoid Redis connection failures."""
    from toms_gym.security import redis_client
    
    # Create a mock Redis client
    mock_client = MagicMock()
    
    # Configure the mock to return expected values for common Redis operations
    # lpush: Used for logging auth events
    mock_client.lpush.return_value = 1
    
    # get: Used for token blacklist checks and rate limiting
    mock_client.get.return_value = None  # Default to None (token not blacklisted)
    
    # setex: Used for token blacklisting and rate limiting
    mock_client.setex.return_value = True
    
    # incr: Used for failed login tracking
    mock_client.incr.return_value = 1
    
    # delete: Used to clear failed login attempts
    mock_client.delete.return_value = 1
    
    # expire: Used to set expiry on keys
    mock_client.expire.return_value = True
    
    # Store the original Redis client
    original_redis = redis_client
    
    # Replace with our mock
    import toms_gym.security
    toms_gym.security.redis_client = mock_client
    
    # Yield control to tests
    yield mock_client
    
    # Restore the original client after tests complete (optional)
    toms_gym.security.redis_client = original_redis 