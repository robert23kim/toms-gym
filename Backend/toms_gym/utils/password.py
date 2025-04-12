import bcrypt
import secrets
from datetime import datetime, timedelta
from typing import Tuple, Optional
from toms_gym.config import Config

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def generate_password_reset_token() -> Tuple[str, datetime]:
    """Generate a password reset token and its expiry time"""
    token = secrets.token_urlsafe(32)
    expiry = datetime.utcnow() + timedelta(hours=1)  # Token valid for 1 hour
    return token, expiry

def validate_password(password: str) -> Tuple[bool, str]:
    """Validate password strength
    
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        return False, "Password must contain at least one special character"
    return True, ""

def is_password_reset_token_valid(token: str, expiry: Optional[datetime]) -> bool:
    """Check if a password reset token is valid"""
    if not token or not expiry:
        return False
    return datetime.utcnow() < expiry 