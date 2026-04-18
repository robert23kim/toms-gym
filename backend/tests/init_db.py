import re
import time
import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text

# Migration files under backend/toms_gym/migrations/ applied after the inline
# base-schema setup below. Order matters.
MIGRATIONS_TO_APPLY = [
    "008_fairway_schema.sql",  # Phase B: Course/Tee/Round/HoleScore/HandicapSnapshot
]


_BEGIN_COMMIT_RE = re.compile(r"^\s*(BEGIN|COMMIT)\s*;", re.IGNORECASE | re.MULTILINE)


def _strip_transaction_boundaries(sql: str) -> str:
    """Remove top-level BEGIN; / COMMIT; lines from migration SQL.

    Migration files ship with `BEGIN; ... COMMIT;` so they're atomic when run
    standalone via `psql -f` or `apply_schema.py`. When we execute the same
    SQL via SQLAlchemy's `conn.execute(text(sql))`, an embedded COMMIT ends
    the implicit SQLAlchemy transaction early and leaves the connection in a
    state where the caller's subsequent `conn.commit()` is a no-op (or, on
    some psycopg2/SA versions, raises). Strip them here so the SQLAlchemy
    transaction remains the single source of commit truth; the migration
    file on disk is NOT touched (prod path stays atomic).
    """
    return _BEGIN_COMMIT_RE.sub("", sql)


def _apply_migration_files(conn):
    """Run each SQL file in MIGRATIONS_TO_APPLY against the given connection.

    Wraps each migration's execution in a SAVEPOINT so a BEGIN/COMMIT quirk
    or a DDL error can't poison the outer transaction that the caller will
    commit at the end of `init_db()`.
    """
    migrations_dir = Path(__file__).resolve().parents[1] / "toms_gym" / "migrations"
    # pg_trgm is required by migration 008's GIN index; ensure the extension
    # is available before the migration runs (test-DB user may not be
    # superuser, but the postgres:15 default image allows CREATE EXTENSION
    # for the postgres superuser used by docker-compose.test.yml).
    try:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
    except Exception as e:
        print(f"  Warning: could not pre-create pg_trgm extension: {e}")

    for filename in MIGRATIONS_TO_APPLY:
        path = migrations_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Migration file not found: {path}")
        print(f"Applying migration {filename}...")
        sql = _strip_transaction_boundaries(path.read_text())
        conn.execute(text(sql))
        print(f"  Applied {filename}")


def init_db():
    """Initialize the test database with required tables"""
    print("Starting database initialization...")
    
    # Get the database URL from environment or use default test DB
    db_url = os.environ.get('DATABASE_URL', 'postgresql://postgres:test@db-test:5432/toms_gym_test')
    print(f"Using database URL: {db_url}")
    
    try:
        engine = create_engine(db_url)
        print("Created database engine")
    except Exception as e:
        print(f"Error creating database engine: {e}")
        return False
    
    for i in range(10):
        try:
            print(f"Attempt {i+1} to create tables...")
            with engine.connect() as conn:
                # Create extensions if they don't exist
                print("Creating uuid-ossp extension...")
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"))
                
                # Clean up old tables to avoid constraint issues
                print("Dropping existing tables if they exist...")
                conn.execute(text("""
                -- Drop dependent tables first to avoid constraint issues
                DROP TABLE IF EXISTS "TokenBlacklist" CASCADE;
                DROP TABLE IF EXISTS "SecurityAudit" CASCADE;
                DROP TABLE IF EXISTS "UserSession" CASCADE;
                DROP TABLE IF EXISTS "Attempt" CASCADE;
                DROP TABLE IF EXISTS "UserCompetition" CASCADE;
                DROP TABLE IF EXISTS "Competition" CASCADE;
                DROP TABLE IF EXISTS "User" CASCADE;
                
                -- Drop enum types if they exist
                DROP TYPE IF EXISTS user_role CASCADE;
                DROP TYPE IF EXISTS user_status CASCADE;
                DROP TYPE IF EXISTS competition_status CASCADE;
                DROP TYPE IF EXISTS attempt_status CASCADE;
                DROP TYPE IF EXISTS gender CASCADE;
                DROP TYPE IF EXISTS lift_type CASCADE;
                DROP TYPE IF EXISTS weight_class CASCADE;
                DROP TYPE IF EXISTS auth_method CASCADE;
                """))
                
                # Create enum types
                print("Creating enum types...")
                conn.execute(text("""
                CREATE TYPE user_role AS ENUM ('admin', 'user', 'judge');
                CREATE TYPE user_status AS ENUM ('active', 'inactive', 'suspended');
                CREATE TYPE competition_status AS ENUM ('upcoming', 'active', 'completed', 'cancelled');
                CREATE TYPE attempt_status AS ENUM ('pending', 'approved', 'rejected');
                CREATE TYPE gender AS ENUM ('male', 'female', 'other');
                CREATE TYPE lift_type AS ENUM ('Squat', 'Bench Press', 'Deadlift');
                CREATE TYPE weight_class AS ENUM ('66kg', '74kg', '83kg', '93kg', '105kg', '120kg', '+120kg');
                CREATE TYPE auth_method AS ENUM ('password', 'google', 'facebook');
                """))
                
                # Create tables
                print("Creating tables...")
                conn.execute(text("""
                CREATE TABLE "User" (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    username VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255),
                    name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    gender gender,
                    auth_method auth_method DEFAULT 'password',
                    role user_role DEFAULT 'user',
                    status user_status DEFAULT 'active',
                    failed_login_attempts INTEGER DEFAULT 0,
                    last_login_attempt TIMESTAMP,
                    account_locked_until TIMESTAMP,
                    password_reset_token VARCHAR(255),
                    password_reset_expiry TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE "Competition" (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    start_date DATE,
                    end_date DATE,
                    status competition_status DEFAULT 'upcoming'
                );

                CREATE TABLE "UserCompetition" (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    user_id UUID REFERENCES "User"(id) ON DELETE CASCADE,
                    competition_id UUID REFERENCES "Competition"(id) ON DELETE CASCADE,
                    weight_class weight_class,
                    status user_status DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, competition_id)
                );

                CREATE TABLE "Attempt" (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    user_competition_id UUID REFERENCES "UserCompetition"(id) ON DELETE CASCADE,
                    lift_type lift_type,
                    weight_kg FLOAT,
                    video_url TEXT,
                    status attempt_status DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE "SecurityAudit" (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    event_type VARCHAR(50) NOT NULL,
                    user_id UUID REFERENCES "User"(id) ON DELETE SET NULL,
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    details JSONB,
                    success BOOLEAN NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE "TokenBlacklist" (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    token_id VARCHAR(255) UNIQUE NOT NULL,
                    user_id UUID REFERENCES "User"(id) ON DELETE CASCADE,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE "UserSession" (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    user_id UUID REFERENCES "User"(id) ON DELETE CASCADE,
                    refresh_token_id VARCHAR(255) UNIQUE NOT NULL,
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Create indexes for better performance
                CREATE INDEX idx_user_email ON "User" (email);
                CREATE INDEX idx_user_username ON "User" (username);
                CREATE INDEX idx_competition_status ON "Competition" (status);
                CREATE INDEX idx_usercomp_user ON "UserCompetition" (user_id);
                CREATE INDEX idx_usercomp_competition ON "UserCompetition" (competition_id);
                CREATE INDEX idx_attempt_usercomp ON "Attempt" (user_competition_id);
                """))

                # Apply migration files (Phase B schema, etc.)
                _apply_migration_files(conn)

                conn.commit()
                print("Tables created and committed successfully")
            print("Connection closed successfully")
            return True
        except Exception as e:
            print(f"Error in attempt {i+1}: {e}")
            if i < 9:  # Don't sleep on the last attempt
                print(f"Waiting for database... (attempt {i+1}/10)")
                time.sleep(2)
    
    print("Failed to initialize database after multiple attempts")
    return False

if __name__ == "__main__":
    success = init_db()
    if not success:
        print("Database initialization failed")
        sys.exit(1)
    print("Database initialization completed successfully")
    sys.exit(0) 