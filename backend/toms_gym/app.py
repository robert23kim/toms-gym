# app.py
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import datetime
import secrets
from toms_gym.utils.json_encoder import CustomJSONEncoder
import logging

# Import route blueprints
from toms_gym.routes.competition_routes import competition_bp
from toms_gym.routes.user_routes import user_bp
from toms_gym.routes.attempt_routes import attempt_bp
from toms_gym.routes.upload_routes import upload_bp
from toms_gym.routes.auth_routes import auth_bp
from toms_gym.routes.telemetry_routes import telemetry_bp
from toms_gym.routes.admin_routes import admin_bp
from toms_gym.routes.weekly_lifts_routes import weekly_lifts_bp
from toms_gym.config import get_config, Config
from toms_gym.db import cleanup_session

# Import integrations
from toms_gym.integrations.email_upload import email_upload_bp, start_background_processor
from toms_gym.integrations.bowling_processor import start_bowling_processor
from toms_gym.integrations.lifting_processor import start_lifting_processor
from toms_gym.routes.bowling_routes import bowling_bp
from toms_gym.routes.lifting_routes import lifting_bp
from toms_gym.routes.golf_routes import golf_bp
from toms_gym.routes.short_link_routes import short_link_bp

load_dotenv()

def run_startup_migrations():
    """Run any pending database migrations on startup"""
    try:
        from toms_gym.db import get_db_connection
        import sqlalchemy
        session = get_db_connection()

        # Add 'Bicep Curl' to lift_type enum if not exists
        try:
            session.execute(sqlalchemy.text("ALTER TYPE lift_type ADD VALUE IF NOT EXISTS 'Bicep Curl'"))
            session.commit()
            logging.info("Added 'Bicep Curl' to lift_type enum")
        except Exception as e:
            session.rollback()
            # Ignore if already exists or other non-critical errors
            logging.info(f"Enum migration note: {e}")

        # Add 'Bowling' to lift_type enum if not exists
        try:
            session.execute(sqlalchemy.text("ALTER TYPE lift_type ADD VALUE IF NOT EXISTS 'Bowling'"))
            session.commit()
            logging.info("Added 'Bowling' to lift_type enum")
        except Exception as e:
            session.rollback()
            logging.info(f"Bowling enum migration note: {e}")

        # Add 'Plank' to lift_type enum if not exists (migration 009)
        try:
            session.execute(sqlalchemy.text("ALTER TYPE lift_type ADD VALUE IF NOT EXISTS 'Plank'"))
            session.commit()
            logging.info("Added 'Plank' to lift_type enum")
        except Exception as e:
            session.rollback()
            logging.info(f"Plank enum migration note: {e}")

        # Create BowlingResult table if not exists
        try:
            session.execute(sqlalchemy.text("""
                CREATE TABLE IF NOT EXISTS "BowlingResult" (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    attempt_id UUID REFERENCES "Attempt"(id) UNIQUE,
                    processing_status TEXT DEFAULT 'queued',
                    debug_video_url TEXT,
                    trajectory_png_url TEXT,
                    board_at_pins DECIMAL(5,2),
                    entry_board DECIMAL(5,2),
                    processing_time_s DECIMAL(8,2),
                    detection_rate DECIMAL(5,2),
                    error_message TEXT,
                    created_at TIMESTAMPTZ DEFAULT now(),
                    updated_at TIMESTAMPTZ DEFAULT now()
                )
            """))
            session.execute(sqlalchemy.text("""
                CREATE INDEX IF NOT EXISTS idx_bowling_result_processing_status
                    ON "BowlingResult" (processing_status)
            """))
            session.commit()
            logging.info("BowlingResult table migration complete")
        except Exception as e:
            session.rollback()
            logging.info(f"BowlingResult migration note: {e}")

        # Add lane edge columns if not exists (migration 005)
        try:
            session.execute(sqlalchemy.text("""
                ALTER TABLE "BowlingResult"
                    ADD COLUMN IF NOT EXISTS lane_edges_auto JSONB,
                    ADD COLUMN IF NOT EXISTS lane_edges_manual JSONB,
                    ADD COLUMN IF NOT EXISTS frame_url TEXT
            """))
            session.commit()
            logging.info("Lane edge columns migration complete")
        except Exception as e:
            session.rollback()
            logging.info(f"Lane edge columns migration note: {e}")

        # Add annotation and frames_url columns (migration 006)
        try:
            session.execute(sqlalchemy.text("""
                ALTER TABLE "BowlingResult"
                    ADD COLUMN IF NOT EXISTS annotation JSONB,
                    ADD COLUMN IF NOT EXISTS frames_url TEXT
            """))
            session.commit()
            logging.info("Annotation columns migration complete")
        except Exception as e:
            session.rollback()
            logging.info(f"Annotation columns migration note: {e}")

        # Create ShortLink table if not exists (migration 010)
        try:
            session.execute(sqlalchemy.text("""
                CREATE TABLE IF NOT EXISTS "ShortLink" (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    short_code TEXT NOT NULL UNIQUE,
                    target_url TEXT NOT NULL,
                    created_by_user_id UUID REFERENCES "User"(id) ON DELETE SET NULL,
                    created_at TIMESTAMPTZ DEFAULT now()
                )
            """))
            session.execute(sqlalchemy.text("""
                CREATE INDEX IF NOT EXISTS idx_short_link_short_code
                    ON "ShortLink" (short_code)
            """))
            session.commit()
            logging.info("ShortLink table migration complete")
        except Exception as e:
            session.rollback()
            logging.info(f"ShortLink migration note: {e}")

        session.close()
    except Exception as e:
        logging.warning(f"Startup migration skipped: {e}")

# Run migrations
run_startup_migrations()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Load configuration
config = get_config()
app.config.from_object(config)

# Override JWT_SECRET_KEY from env if explicitly set (otherwise config default is used)
if os.environ.get('JWT_SECRET_KEY'):
    app.config['JWT_SECRET_KEY'] = os.environ['JWT_SECRET_KEY']

# Set custom JSON encoder
app.json_encoder = CustomJSONEncoder

# Basic configuration
app.secret_key = os.environ.get('APP_SECRET_KEY', secrets.token_hex(16))
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB max upload size
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Frontend URL for redirects
app.config['FRONTEND_URL'] = os.environ.get('FRONTEND_URL', 'http://localhost:3000')

# Configure CORS with more permissive settings
CORS(app, resources={
    r"/*": {
        "origins": ["*", "http://localhost:8085", "http://localhost:3000", "http://localhost:8080", "http://localhost:8082"],
        "allow_headers": "*",
        "expose_headers": "*",
        "supports_credentials": True
    }
})

# Register blueprints
app.register_blueprint(competition_bp)
app.register_blueprint(user_bp)
app.register_blueprint(attempt_bp)
app.register_blueprint(upload_bp)
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(admin_bp)
app.register_blueprint(weekly_lifts_bp)
app.register_blueprint(email_upload_bp, url_prefix='/integrations')
app.register_blueprint(bowling_bp)
app.register_blueprint(lifting_bp)
app.register_blueprint(golf_bp)
app.register_blueprint(telemetry_bp)
app.register_blueprint(short_link_bp)

# Start email processor if enabled
start_background_processor()

# Start bowling processor if enabled
start_bowling_processor()

# Start lifting processor if enabled
start_lifting_processor()

# Clean up scoped DB session after every request to prevent
# broken transactions from leaking across requests
app.teardown_appcontext(cleanup_session)

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "service": "toms-gym-backend",
        "status": "healthy",
        "timestamp": str(datetime.datetime.now())
    })

@app.route('/')
def hello():
    return "Hello from Toms Gym!"

@app.after_request
def after_request(response):
    # Log request info
    logger.info(f"Request: {request.method} {request.path}")
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)


