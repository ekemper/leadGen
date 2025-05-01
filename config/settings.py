"""
Flask application settings.
"""
import os
from datetime import timedelta

# Basic Flask settings
DEBUG = os.getenv('FLASK_DEBUG', '0') == '1'
TESTING = False
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')

# Security settings
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
PERMANENT_SESSION_LIFETIME = timedelta(days=1)

# CORS settings
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', '*').split(',')

# Rate limiting settings
RATELIMIT_STORAGE_URL = os.getenv('RATELIMIT_STORAGE_URL', 'memory://')
RATELIMIT_DEFAULT = "200 per day;50 per hour"
RATELIMIT_HEADERS_ENABLED = True

# JWT settings
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', SECRET_KEY)
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

# Database settings
SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///app.db')
SQLALCHEMY_TRACK_MODIFICATIONS = False 