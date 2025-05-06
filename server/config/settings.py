import os
from datetime import timedelta

# Flask settings
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

## Database settings are handled in the database config module.
## NEON_CONNECTION_STRING must be set for application runtime.

# JWT settings
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key')
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

# Security settings
SESSION_COOKIE_SECURE = os.getenv('FLASK_ENV') == 'production'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'  # Use 'Strict' in production

# CORS settings
CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')

# Rate limiting
RATELIMIT_DEFAULT = "200 per day;50 per hour"
RATELIMIT_STORAGE_URL = os.getenv('REDIS_URL', 'memory://') 