# app.py
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import datetime

# Import route blueprints
from toms_gym.routes.competition_routes import competition_bp
from toms_gym.routes.user_routes import user_bp
from toms_gym.routes.attempt_routes import attempt_bp
from toms_gym.routes.upload_routes import upload_bp

load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Configure CORS with more permissive settings
# Update to allow all origins and expose all headers
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)


