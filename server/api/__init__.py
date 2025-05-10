from flask import Blueprint
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
    # No rate limiting logic here; handled in app.py
    # Get the API blueprint
    api = create_api_blueprint()
    # Register blueprint
    app.register_blueprint(api) 