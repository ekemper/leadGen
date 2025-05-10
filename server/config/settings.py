import os
from datetime import timedelta

# Flask settings
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

## Database settings are handled in the database config module.
## NEON_CONNECTION_STRING must be set for application runtime.

# JWT settings
# For testing with curl:
# 1. Generate token: python3 -c "import jwt; print(jwt.encode({'user_id': 1}, os.getenv('JWT_SECRET_KEY'), algorithm='HS256'))"
# 2. Use token: curl -H "Authorization: Bearer <token>" http://localhost:5001/api/leads
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')  # Must be set in .env
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
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0') 