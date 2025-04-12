from functools import wraps
from flask import request, jsonify, current_app
import redis
from datetime import datetime, timezone
import jwt
import logging
import json
from typing import Optional, Dict, Any
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Redis for rate limiting and token blacklist
redis_client = redis.from_url(
    os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
)

class RateLimiter:
    """Rate limiting implementation using Redis"""
    
    @staticmethod
    def get_rate_limit_key(endpoint: str, identifier: str) -> str:
        """Generate a rate limit key for Redis"""
        return f"rate_limit:{endpoint}:{identifier}"
    
    @staticmethod
    def parse_limit(limit: str) -> tuple[int, int]:
        """Parse rate limit string (e.g., '100/day') into count and seconds"""
        count, period = limit.split('/')
        periods = {
            'second': 1,
            'minute': 60,
            'hour': 3600,
            'day': 86400
        }
        return int(count), periods[period]
    
    @classmethod
    def is_rate_limited(cls, endpoint: str, identifier: str, limit: str) -> bool:
        """Check if the request is rate limited"""
        key = cls.get_rate_limit_key(endpoint, identifier)
        count, period = cls.parse_limit(limit)
        
        current = redis_client.get(key)
        if not current:
            redis_client.setex(key, period, 1)
            return False
        
        current = int(current)
        if current >= count:
            return True
        
        redis_client.incr(key)
        return False

def rate_limit(limit: str):
    """Rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_app.config['TESTING']:
                identifier = request.remote_addr
                if RateLimiter.is_rate_limited(f.__name__, identifier, limit):
                    return jsonify({
                        'error': 'Rate limit exceeded',
                        'retry_after': 'Please try again later'
                    }), 429
            return f(*args, **kwargs)
        return decorated_function
    return decorator

class TokenBlacklist:
    """Token blacklist implementation using Redis"""
    
    @staticmethod
    def add_to_blacklist(token: str, expires_in: int) -> None:
        """Add a token to the blacklist"""
        redis_client.setex(f"blacklist:{token}", expires_in, 1)
    
    @staticmethod
    def is_blacklisted(token: str) -> bool:
        """Check if a token is blacklisted"""
        return bool(redis_client.get(f"blacklist:{token}"))

class SecurityAudit:
    """Security audit logging"""
    
    @staticmethod
    def log_auth_event(
        event_type: str,
        user_id: Optional[str] = None,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log authentication events"""
        event = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'event_type': event_type,
            'user_id': user_id,
            'success': success,
            'ip_address': request.remote_addr,
            'user_agent': request.user_agent.string,
            'details': details or {}
        }
        logger.info(f"Auth event: {json.dumps(event)}")
        
        # Store in Redis for potential security analysis
        key = f"auth_events:{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        redis_client.lpush(key, json.dumps(event))
        redis_client.expire(key, 86400 * 30)  # Keep for 30 days

class FailedLoginTracker:
    """Track failed login attempts"""
    
    @staticmethod
    def get_attempts_key(identifier: str) -> str:
        """Get Redis key for failed attempts"""
        return f"failed_login:{identifier}"
    
    @classmethod
    def record_failed_attempt(cls, identifier: str) -> int:
        """Record a failed login attempt and return total attempts"""
        key = cls.get_attempts_key(identifier)
        current = redis_client.get(key)
        
        if not current:
            redis_client.setex(
                key,
                current_app.config['ACCOUNT_LOCKOUT_DURATION'].total_seconds(),
                1
            )
            return 1
        
        return redis_client.incr(key)
    
    @classmethod
    def clear_attempts(cls, identifier: str) -> None:
        """Clear failed login attempts"""
        redis_client.delete(cls.get_attempts_key(identifier))
    
    @classmethod
    def is_account_locked(cls, identifier: str) -> bool:
        """Check if account is locked due to too many failed attempts"""
        key = cls.get_attempts_key(identifier)
        attempts = redis_client.get(key)
        return attempts and int(attempts) >= current_app.config['FAILED_LOGIN_ATTEMPTS']

def require_auth(f):
    """Authentication decorator"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'No valid authorization header'}), 401
        
        token = auth_header.split(' ')[1]
        
        if TokenBlacklist.is_blacklisted(token):
            return jsonify({'error': 'Token has been revoked'}), 401
        
        try:
            payload = jwt.decode(
                token,
                current_app.config['JWT_SECRET_KEY'],
                algorithms=['HS256']
            )
            return f(payload, *args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
    
    return decorated 