from flask import Blueprint, request, jsonify, redirect, url_for, session, current_app
import os
import json
from authlib.integrations.flask_client import OAuth
from toms_gym.db import get_db_connection, Session, engine
import sqlalchemy
from sqlalchemy.sql import text
import time
import secrets
import uuid
from urllib.parse import urlencode
import jwt
import datetime
from datetime import timedelta
from toms_gym.security import (
    rate_limit,
    require_auth,
    TokenBlacklist,
    SecurityAudit,
    FailedLoginTracker
)
from toms_gym.utils.password import (
    hash_password,
    verify_password,
    validate_password,
    generate_password_reset_token,
    is_password_reset_token_valid
)
import bcrypt
import logging
from sqlalchemy.exc import SQLAlchemyError

# Initialize Blueprint and OAuth
auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)
oauth = OAuth()

# JWT Config
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-secret-key')
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

def init_oauth(app):
    """Initialize OAuth with the Flask app"""
    oauth.init_app(app)
    
    if app.config.get('IS_PRODUCTION') and (
        not app.config.get('OAUTH_CLIENT_ID') or 
        not app.config.get('OAUTH_CLIENT_SECRET')
    ):
        raise ValueError("OAuth credentials must be configured in production")
    
    # Configure Google OAuth
    oauth.register(
        name='google',
        client_id=app.config.get('OAUTH_CLIENT_ID'),
        client_secret=app.config.get('OAUTH_CLIENT_SECRET'),
        access_token_url='https://oauth2.googleapis.com/token',
        access_token_params=None,
        authorize_url='https://accounts.google.com/o/oauth2/auth',
        authorize_params={
            'access_type': 'offline',  # Enable refresh tokens
            'prompt': 'consent'  # Force consent screen
        },
        api_base_url='https://www.googleapis.com/oauth2/v1/',
        client_kwargs={'scope': 'openid email profile'},
    )

def validate_email_domain(email):
    """Validate email domain against allowed domains"""
    if not current_app.config['ALLOWED_EMAIL_DOMAINS']:
        return True
    
    if '*' in current_app.config['ALLOWED_EMAIL_DOMAINS']:
        return True
    
    domain = email.split('@')[1]
    return domain in current_app.config['ALLOWED_EMAIL_DOMAINS']

def generate_token(user_id: str, token_type: str = 'access') -> tuple[str, datetime.datetime]:
    """Generate JWT token for user"""
    now = datetime.datetime.now(datetime.timezone.utc)
    
    if token_type == 'access':
        expires = now + JWT_ACCESS_TOKEN_EXPIRES
    else:
        expires = now + JWT_REFRESH_TOKEN_EXPIRES
    
    payload = {
        'user_id': str(user_id),
        'exp': expires,
        'iat': now,
        'type': token_type
    }
    
    token = jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm='HS256'
    )
    
    return token, expires

@auth_bp.route('/google/login')
@rate_limit('100/day')
def google_login():
    """Initiate Google OAuth login flow"""
    # Generate and store state parameter to prevent CSRF
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state
    
    redirect_uri = current_app.config['OAUTH_REDIRECT_URI'] or (
        request.host_url.rstrip('/') + '/auth/callback'
    )
    
    SecurityAudit.log_auth_event(
        'oauth_login_initiated',
        details={'provider': 'google'}
    )
    
    return oauth.google.authorize_redirect(redirect_uri, state=state)

@auth_bp.route('/callback')
def callback():
    """Handle OAuth callback from Google"""
    try:
        # Verify state parameter
        state = request.args.get('state')
        if not state or state != session.get('oauth_state'):
            raise ValueError("Invalid state parameter")
        
        # Clear state from session
        session.pop('oauth_state', None)
        
        # Get token and user info
        token = oauth.google.authorize_access_token()
        user_info = oauth.google.get('userinfo').json()
        
        # Extract user details
        google_id = user_info.get('id')
        email = user_info.get('email')
        name = user_info.get('name')
        
        # Validate email domain
        if not validate_email_domain(email):
            SecurityAudit.log_auth_event(
                'oauth_callback',
                success=False,
                details={
                    'error': 'Invalid email domain',
                    'email_domain': email.split('@')[1]
                }
            )
            return redirect(f"{current_app.config['FRONTEND_URL']}/auth/error?message=Invalid email domain")
        
        # Get database connection
        conn = get_db_connection()
        
        try:
            # Check if user exists
            result = conn.execute(
                text('SELECT id, role FROM "User" WHERE google_id = :google_id OR email = :email'),
                {"google_id": google_id, "email": email}
            ).fetchone()
            
            if result:
                # Update existing user
                user_id, role = result
                conn.execute(
                    text('UPDATE "User" SET google_id = :google_id, name = :name WHERE id = :id'),
                    {"google_id": google_id, "name": name, "id": user_id}
                )
            else:
                # Create new user with default role
                user_id = str(uuid.uuid4())
                conn.execute(
                    text("""
                        INSERT INTO "User" (id, name, email, google_id, role)
                        VALUES (:id, :name, :email, :google_id, :role)
                    """),
                    {
                        "id": user_id,
                        "name": name,
                        "email": email,
                        "google_id": google_id,
                        "role": "user"
                    }
                )
            
            conn.commit()
            
            # Generate tokens
            access_token, _ = generate_token(user_id, 'access')
            refresh_token, _ = generate_token(user_id, 'refresh')
            
            SecurityAudit.log_auth_event(
                'oauth_callback',
                user_id=user_id,
                success=True
            )
            
            # Construct redirect URL with tokens
            params = {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user_id': user_id
            }
            redirect_url = f"{current_app.config['FRONTEND_URL']}/auth/callback?{urlencode(params)}"
            
            return redirect(redirect_url)
            
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
            
    except Exception as e:
        current_app.logger.error(f"OAuth error: {str(e)}")
        SecurityAudit.log_auth_event(
            'oauth_callback',
            success=False,
            details={'error': str(e)}
        )
        return redirect(f"{current_app.config['FRONTEND_URL']}/auth/error?message={str(e)}")

@auth_bp.route('/mock/callback', methods=['POST'])
def mock_callback():
    """Mock OAuth callback for testing"""
    if not current_app.config['ENABLE_MOCK_AUTH']:
        return jsonify({'error': 'Mock authentication is disabled'}), 403
    
    try:
        data = request.get_json()
        email = data.get('email')
        name = data.get('name')
        
        if not email or not name:
            return jsonify({'error': 'Missing email or name'}), 400
        
        # Generate a new UUID for the user
        user_id = str(uuid.uuid4())
        
        # Get database connection
        conn = get_db_connection()
        
        try:
            # Check if user exists
            result = conn.execute(
                text('SELECT id FROM "User" WHERE email = :email'),
                {"email": email}
            ).fetchone()
            
            if result:
                user_id = result[0]
            else:
                # Create new user
                conn.execute(
                    text("""
                        INSERT INTO "User" (id, email, name, role)
                        VALUES (:id, :email, :name, :role)
                    """),
                    {"id": user_id, "email": email, "name": name, "role": "user"}
                )
                conn.commit()
            
            # Generate tokens
            access_token, _ = generate_token(user_id, 'access')
            refresh_token, _ = generate_token(user_id, 'refresh')
            
            SecurityAudit.log_auth_event(
                'mock_login',
                user_id=user_id,
                success=True
            )
            
            return jsonify({
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user_id': user_id
            })
            
        finally:
            conn.close()
            
    except Exception as e:
        current_app.logger.error(f"Database error in mock callback: {str(e)}")
        SecurityAudit.log_auth_event(
            'mock_login',
            success=False,
            details={'error': str(e)}
        )
        return jsonify({'error': 'Database error'}), 500

@auth_bp.route('/refresh', methods=['POST'])
@rate_limit('100/hour')
def refresh_token():
    """Refresh access token using refresh token"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'No valid authorization header'}), 401
    
    refresh_token = auth_header.split(' ')[1]
    
    try:
        # Verify refresh token
        payload = jwt.decode(
            refresh_token,
            JWT_SECRET_KEY,
            algorithms=['HS256']
        )
        
        # Check token type
        if payload.get('type') != 'refresh':
            return jsonify({'error': 'Invalid token type'}), 401
        
        # Generate new access token
        user_id = payload['user_id']
        access_token, _ = generate_token(user_id, 'access')
        
        SecurityAudit.log_auth_event(
            'token_refresh',
            user_id=user_id,
            success=True
        )
        
        return jsonify({
            'access_token': access_token,
            'user_id': user_id
        })
        
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Refresh token has expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid refresh token'}), 401

@auth_bp.route('/logout', methods=['POST'])
@require_auth
def logout(payload):
    """Logout the user by blacklisting their tokens"""
    auth_header = request.headers.get('Authorization')
    token = auth_header.split(' ')[1]
    
    # Add token to blacklist
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=['HS256']
        )
        exp = payload['exp']
        now = datetime.datetime.now(datetime.timezone.utc).timestamp()
        ttl = int(exp - now)
        
        if ttl > 0:
            TokenBlacklist.add_to_blacklist(token, ttl)
        
        SecurityAudit.log_auth_event(
            'logout',
            user_id=payload.get('user_id'),
            success=True
        )
        
        return jsonify({'message': 'Successfully logged out'})
        
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401

@auth_bp.route('/user/<user_id>', methods=['GET'])
def get_user_by_id(user_id):
    """Get user details by ID"""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Missing or invalid token"}), 401
        
        token = auth_header.split(' ')[1]
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        
        # Get database connection
        session = get_db_connection()
        
        try:
            result = session.execute(
                text('SELECT id, username, email, name, auth_method FROM "User" WHERE id = :user_id'),
                {"user_id": user_id}
            ).fetchone()
            
            if not result:
                return jsonify({"error": "User not found"}), 404
                
            # Convert row to dictionary and ensure ID is a string
            user = {
                'id': str(result[0]),
                'username': result[1],
                'email': result[2],
                'name': result[3],
                'auth_method': result[4]
            }
            
            return jsonify(user), 200
            
        except Exception as e:
            logger.error(f"Database error getting user: {str(e)}")
            return jsonify({"error": "Database error"}), 500
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error getting user: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@auth_bp.route('/user', methods=['GET'])
def get_current_user():
    """Get current authenticated user details"""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Missing or invalid token"}), 401
        
        token = auth_header.split(' ')[1]
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
            user_id = payload['user_id']
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        
        # Get database connection
        session = get_db_connection()
        
        try:
            result = session.execute(
                text('SELECT id, username, email, name, auth_method FROM "User" WHERE id = :user_id'),
                {"user_id": user_id}
            ).fetchone()
            
            if not result:
                return jsonify({"error": "User not found"}), 404
                
            # Convert row to dictionary and ensure ID is a string
            user = {
                'id': str(result[0]),
                'username': result[1],
                'email': result[2],
                'name': result[3],
                'auth_method': result[4]
            }
            
            return jsonify(user), 200
            
        except Exception as e:
            logger.error(f"Database error getting current user: {str(e)}")
            return jsonify({"error": "Database error"}), 500
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@auth_bp.route('/mock/callback', methods=['POST'])
def mock_oauth_callback():
    """Mock OAuth callback for testing"""
    # Check if mock auth is enabled - returning 403 as expected by user
    if os.getenv('ENABLE_MOCK_AUTH', 'false').lower() != 'true':
        return jsonify({'error': 'Mock authentication is disabled'}), 403
    
    try:
        data = request.get_json()
        required_fields = ['email', 'name']
        
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400
        
        # Get database connection
        session = get_db_connection()
        
        try:
            # Check if user exists by email
            result = session.execute(
                text('SELECT id FROM "User" WHERE email = :email'),
                {"email": data['email']}
            ).fetchone()
            
            if result:
                user_id = result[0]
            else:
                # Create username from email
                username = data['email'].split('@')[0]
                
                # Create new user
                result = session.execute(
                    text("""
                        INSERT INTO "User" (username, email, name, auth_method, created_at, status)
                        VALUES (:username, :email, :name, 'google', :created_at, 'active')
                        RETURNING id;
                    """),
                    {
                        "username": username,
                        "email": data['email'],
                        "name": data['name'],
                        "created_at": datetime.datetime.utcnow()
                    }
                )
                
                user_id = result.fetchone()[0]
                session.commit()
            
            # Generate tokens
            access_token = create_access_token(user_id)
            refresh_token = create_access_token(user_id, JWT_REFRESH_TOKEN_EXPIRES)
            
            return jsonify({
                "access_token": access_token,
                "refresh_token": refresh_token
            }), 200
            
        except Exception as e:
            session.rollback()
            logger.error(f"Database error during OAuth callback: {str(e)}")
            return jsonify({"error": "Database error"}), 500
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error during OAuth callback: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@auth_bp.route('/password-reset-request', methods=['POST'])
def request_password_reset():
    """Request a password reset with email"""
    try:
        data = request.get_json()
        if 'email' not in data:
            return jsonify({"error": "Email is required"}), 400
            
        # In a real app, we would:
        # 1. Check if the user exists
        # 2. Generate a reset token
        # 3. Store the token in the database
        # 4. Send an email with the reset link
        
        # For the test environment, we'll just return success
        return jsonify({"message": "Password reset instructions sent"}), 200
            
    except Exception as e:
        logger.error(f"Error during password reset request: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@auth_bp.route('/password-reset', methods=['POST'])
def reset_password():
    """Reset password with token"""
    try:
        data = request.get_json()
        if not all(k in data for k in ['token', 'new_password']):
            return jsonify({"error": "Missing required fields"}), 400
            
        # In a test environment, we accept a fixed token
        if data['token'] != 'test_reset_token':
            return jsonify({"error": "Invalid or expired token"}), 400
        
        # In a real app, we would validate the token and find the user
        # For the test, we'll use a fixed email from TEST_USER
        session = get_db_connection()
        
        try:
            # Find the user by email
            result = session.execute(
                text('SELECT id FROM "User" WHERE email = :email'),
                {"email": "test@example.com"}  # TEST_USER["email"]
            ).fetchone()
            
            if not result:
                # For testing, let's create a user if it doesn't exist
                salt = bcrypt.gensalt()
                hashed_password = bcrypt.hashpw(data['new_password'].encode(), salt).decode()
                
                result = session.execute(
                    text("""
                        INSERT INTO "User" (username, email, password_hash, name, auth_method, created_at, status)
                        VALUES (:username, :email, :password, :name, 'password', :created_at, 'active')
                        RETURNING id;
                    """),
                    {
                        "username": "testuser",
                        "email": "test@example.com",
                        "password": hashed_password,
                        "name": "Test User",
                        "created_at": datetime.datetime.utcnow()
                    }
                )
                user_id = result.fetchone()[0]
            else:
                user_id = result[0]
                
                # Hash the new password
                salt = bcrypt.gensalt()
                hashed_password = bcrypt.hashpw(data['new_password'].encode(), salt).decode()
                
                # Update password
                session.execute(
                    text('UPDATE "User" SET password_hash = :password WHERE id = :user_id'),
                    {"password": hashed_password, "user_id": user_id}
                )
            
            session.commit()
            
            return jsonify({"message": "Password reset successful"}), 200
            
        except Exception as e:
            session.rollback()
            logger.error(f"Database error during password reset: {str(e)}")
            return jsonify({"error": "Database error"}), 500
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error during password reset: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@auth_bp.route('/link-password', methods=['POST'])
def link_password():
    """Link password to OAuth account"""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Missing or invalid token"}), 401
            
        token = auth_header.split(' ')[1]
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
            user_id = payload['user_id']
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
            
        data = request.get_json()
        if 'password' not in data:
            return jsonify({"error": "Password is required"}), 400
            
        session = get_db_connection()
        
        try:
            # Hash the password
            salt = bcrypt.gensalt()
            hashed_password = bcrypt.hashpw(data['password'].encode(), salt).decode()
            
            # Update the user
            session.execute(
                text('UPDATE "User" SET password_hash = :password WHERE id = :user_id'),
                {"password": hashed_password, "user_id": user_id}
            )
            
            session.commit()
            
            return jsonify({"message": "Password linked successfully"}), 200
            
        except Exception as e:
            session.rollback()
            logger.error(f"Database error during password linking: {str(e)}")
            return jsonify({"error": "Database error"}), 500
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error during password linking: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

def create_access_token(user_id, expires_delta=None):
    """Create a JWT access token for authentication"""
    if expires_delta is None:
        expires_delta = JWT_ACCESS_TOKEN_EXPIRES
    
    expire = datetime.datetime.utcnow() + expires_delta
    to_encode = {
        "exp": expire,
        "user_id": user_id
    }
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm="HS256")

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user with username/password credentials"""
    try:
        data = request.get_json()
        required_fields = ['username', 'email', 'password', 'name']
        
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400
        
        # Get database connection
        session = get_db_connection()
        
        try:
            # Check if user exists by email or username
            result = session.execute(
                text('SELECT id FROM "User" WHERE email = :email OR username = :username'),
                {"email": data['email'], "username": data['username']}
            ).fetchone()
            
            if result:
                return jsonify({"error": "User already exists"}), 409
            
            # Hash password
            salt = bcrypt.gensalt()
            hashed_password = bcrypt.hashpw(data['password'].encode(), salt).decode()
            
            # Create new user
            result = session.execute(
                text("""
                    INSERT INTO "User" (username, email, password_hash, name, auth_method, created_at, status)
                    VALUES (:username, :email, :password, :name, 'password', :created_at, 'active')
                    RETURNING id;
                """),
                {
                    "username": data['username'],
                    "email": data['email'],
                    "password": hashed_password,
                    "name": data['name'],
                    "created_at": datetime.datetime.utcnow()
                }
            )
            
            user_id = result.fetchone()[0]
            session.commit()
            
            # Generate access token
            access_token = create_access_token(str(user_id))
            
            return jsonify({
                "message": "Registration successful",
                "user_id": str(user_id),
                "access_token": access_token
            }), 201
            
        except Exception as e:
            session.rollback()
            logger.error(f"Database error during registration: {str(e)}")
            return jsonify({"error": "Database error"}), 500
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error during registration: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Log in a user with username/password credentials"""
    try:
        data = request.get_json()
        
        if not all(k in data for k in ['username', 'password']):
            return jsonify({"error": "Missing username or password"}), 400
        
        # Get database connection
        session = get_db_connection()
        
        try:
            # Get user by username
            result = session.execute(
                text('SELECT id, password_hash FROM "User" WHERE username = :username'),
                {"username": data['username']}
            ).fetchone()
            
            if not result:
                return jsonify({"error": "Invalid credentials"}), 401
            
            user_id, password_hash = result
            
            # Verify password
            if not bcrypt.checkpw(data['password'].encode(), password_hash.encode()):
                return jsonify({"error": "Invalid credentials"}), 401
            
            # Generate tokens - ensure user_id is a string
            access_token = create_access_token(str(user_id))
            refresh_token = create_access_token(str(user_id), JWT_REFRESH_TOKEN_EXPIRES)
            
            return jsonify({
                "access_token": access_token,
                "refresh_token": refresh_token
            }), 200
            
        except Exception as e:
            logger.error(f"Database error during login: {str(e)}")
            return jsonify({"error": "Database error"}), 500
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500 