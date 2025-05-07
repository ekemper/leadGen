from flask import Blueprint
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS

def create_api_blueprint():
    """Create and configure the API blueprint"""
    api = Blueprint('api', __name__, url_prefix='/api')
    # CORS is now handled at the app level
    # CORS(api)

    # Register routes
    from .routes import register_routes
    register_routes(api)

    return api

def init_api(app):
    """Initialize API blueprint and its configurations"""
    # CORS is now handled at the app level
    # Configure rate limiting
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["200 per day", "50 per hour"],
        storage_uri=app.config.get('RATELIMIT_STORAGE_URL', "memory://"),
        enabled=not app.config['TESTING']  # Disable rate limiting in test mode
    )

    # Get the API blueprint
    api = create_api_blueprint()

    # Apply rate limits to routes
    limiter.limit("10/minute", exempt_when=lambda: app.config['TESTING'])(api)
    
    # Special rate limit for events API to allow more frequent logging
    limiter.limit("1000 per hour", exempt_when=lambda: app.config['TESTING'])(api.route('/events', methods=['POST']))
    
    # Register blueprint
    app.register_blueprint(api) 