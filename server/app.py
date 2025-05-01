import os
from flask import Flask
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
from utils.middleware import request_middleware
from config.database import db, init_db
from api import create_api_blueprint

def create_app(test_config=None):
    """Create and configure the Flask application"""
    # Load environment variables
    if test_config is None:
        load_dotenv()
    
    # Create Flask app
    app = Flask(__name__)
    
    # Load configuration
    if test_config is None:
        app.config.from_object('config.settings')
    else:
        app.config.update(test_config)
    
    # Initialize extensions
    CORS(app)
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://"
    )
    
    # Initialize database
    init_db(app, test_config)
    
    # Register blueprints
    api = create_api_blueprint()
    limiter.limit("100/day;30/hour")(api)
    app.register_blueprint(api, url_prefix='/api')
    
    # Configure middleware
    request_middleware(app)

    # Add security headers
    @app.after_request
    def add_security_headers(response):
        """Add security headers to all responses."""
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Content-Security-Policy'] = "default-src 'self'"
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response

    return app

# Only create the app if running directly
if __name__ == '__main__':
    from utils.logger import logger
    
    app = create_app()
    
    logger.info('Starting application', extra={
        'environment': os.getenv('FLASK_ENV', 'development'),
        'debug_mode': os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    })
    
    if os.getenv('FLASK_ENV') == 'production':
        app.config['SESSION_COOKIE_SECURE'] = True
        app.config['SESSION_COOKIE_HTTPONLY'] = True
        app.config['SESSION_COOKIE_SAMESITE'] = 'Strict'
    
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000))) 