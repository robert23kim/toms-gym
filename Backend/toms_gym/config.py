import os
import secrets
from datetime import timedelta

class Config:
    """Base configuration class"""
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', secrets.token_hex(32))
    
    # JWT settings
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_BLACKLIST_ENABLED = True
    JWT_BLACKLIST_TOKEN_CHECKS = ['access', 'refresh']
    
    # OAuth settings
    OAUTH_CLIENT_ID = os.environ.get('OAUTH_CLIENT_ID')
    OAUTH_CLIENT_SECRET = os.environ.get('OAUTH_CLIENT_SECRET')
    OAUTH_REDIRECT_URI = os.environ.get('OAUTH_REDIRECT_URI')
    ALLOWED_EMAIL_DOMAINS = os.environ.get('ALLOWED_EMAIL_DOMAINS', '*').split(',')
    
    # Security settings
    RATE_LIMIT_LOGIN = "100/day"  # 100 attempts per day per IP
    RATE_LIMIT_REGISTER = "10/day"  # 10 registrations per day per IP
    FAILED_LOGIN_ATTEMPTS = 5  # Number of failed attempts before account lockout
    ACCOUNT_LOCKOUT_DURATION = timedelta(minutes=15)
    PASSWORD_RESET_TIMEOUT = timedelta(hours=1)
    
    # Database settings
    DATABASE_URL = os.environ.get('DATABASE_URL')
    USE_MOCK_DB = os.environ.get('USE_MOCK_DB', 'false').lower() == 'true'
    
    # Environment settings
    ENV = os.environ.get('FLASK_ENV', 'development')
    DEBUG = ENV == 'development'
    TESTING = ENV == 'testing'
    
    @property
    def IS_PRODUCTION(self):
        return self.ENV == 'production'
    
    @property
    def ENABLE_MOCK_AUTH(self):
        """Only enable mock authentication in development or testing"""
        return not self.IS_PRODUCTION

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    
    @property
    def ENABLE_MOCK_AUTH(self):
        return False

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DATABASE_URL = "sqlite:///test.db"
    
    @property
    def ENABLE_MOCK_AUTH(self):
        return False

class ProductionConfig(Config):
    """Production configuration"""
    @property
    def OAUTH_CLIENT_ID(self):
        client_id = os.environ.get('OAUTH_CLIENT_ID')
        if not client_id:
            raise ValueError("OAUTH_CLIENT_ID must be set in production")
        return client_id
    
    @property
    def OAUTH_CLIENT_SECRET(self):
        client_secret = os.environ.get('OAUTH_CLIENT_SECRET')
        if not client_secret:
            raise ValueError("OAUTH_CLIENT_SECRET must be set in production")
        return client_secret
    
    @property
    def JWT_SECRET_KEY(self):
        key = os.environ.get('JWT_SECRET_KEY')
        if not key:
            raise ValueError("JWT_SECRET_KEY must be set in production")
        return key

def get_config():
    """Get the appropriate configuration based on environment"""
    env = os.environ.get('FLASK_ENV', 'development')
    configs = {
        'development': DevelopmentConfig,
        'testing': TestingConfig,
        'production': ProductionConfig
    }
    return configs.get(env, DevelopmentConfig)() 