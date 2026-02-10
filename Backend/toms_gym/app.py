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
from toms_gym.routes.admin_routes import admin_bp
from toms_gym.routes.weekly_lifts_routes import weekly_lifts_bp
from toms_gym.config import get_config, Config

# Import integrations
from toms_gym.integrations.email_upload import email_upload_bp, start_background_processor

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
        finally:
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

# Start email processor if enabled
start_background_processor()

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


