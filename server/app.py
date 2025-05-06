import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from dotenv import load_dotenv
from server.utils.middleware import request_middleware
from server.config.database import db, init_db
from server.api import create_api_blueprint
from werkzeug.exceptions import HTTPException, BadRequest
from server.utils.logging_config import server_logger, combined_logger

print('sys.path:', sys.path)
print('CWD:', os.getcwd())

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
    
    # Initialize extensions with CORS config
    CORS(app, 
         resources={
             r"/*": {
                 "origins": ["http://localhost:5173", "http://127.0.0.1:5173"],
                 "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                 "allow_headers": ["Content-Type", "Authorization"],
                 "expose_headers": ["Content-Type", "Authorization"],
                 "supports_credentials": True,
                 "allow_credentials": True,
                 "max_age": 3600
             }
         })
    
    # Add CORS headers to all responses
    @app.after_request
    def after_request(response):
        origin = request.headers.get('Origin')
        if origin in ["http://localhost:5173", "http://127.0.0.1:5173"]:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Max-Age'] = '3600'
        return response
    
    # Configure rate limiting
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"]
    )
    
    # Initialize database
    init_db(app)
    migrate = Migrate(app, db)
    
    # Register blueprints
    api_blueprint = create_api_blueprint()
    app.register_blueprint(api_blueprint, url_prefix='/api')
    
    # Register error handlers
    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        """Handle HTTP exceptions."""
        response = {
            'status': 'error',
            'error': {
                'code': error.code,
                'name': error.name,
                'message': error.description
            }
        }
        server_logger.error(
            f"HTTP error: {error.name}",
            extra={
                'error_code': error.code,
                'error_name': error.name,
                'error_message': error.description
            }
        )
        return jsonify(response), error.code

    @app.errorhandler(BadRequest)
    def handle_bad_request(error):
        """Handle bad request errors."""
        response = {
            'status': 'error',
            'error': {
                'code': 400,
                'name': 'Bad Request',
                'message': str(error.description)
            }
        }
        server_logger.error(
            "Bad request error",
            extra={
                'error_code': 400,
                'error_message': str(error.description)
            }
        )
        return jsonify(response), 400

    @app.errorhandler(Exception)
    def handle_generic_error(error):
        """Handle generic exceptions."""
        response = {
            'status': 'error',
            'error': {
                'code': 500,
                'name': 'Internal Server Error',
                'message': str(error)
            }
        }
        server_logger.error(
            "Unhandled exception",
            extra={
                'error_code': 500,
                'error_type': type(error).__name__,
                'error_message': str(error)
            }
        )
        return jsonify(response), 500
    
    # Log application startup
    server_logger.info("Flask application initialized")
    combined_logger.info(
        "Flask application initialized",
        extra={
            'component': 'server',
            'config': {
                'debug': app.debug,
                'testing': app.testing,
                'environment': os.getenv('FLASK_ENV', 'development')
            }
        }
    )

    return app

# Only create the app if running directly
if __name__ == '__main__':
    app = create_app()
    
    server_logger.info('Starting application', extra={
        'environment': os.getenv('FLASK_ENV', 'development'),
        'debug_mode': os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    })
    
    if os.getenv('FLASK_ENV') == 'production':
        app.config['SESSION_COOKIE_SECURE'] = True
        app.config['SESSION_COOKIE_HTTPONLY'] = True
        app.config['SESSION_COOKIE_SAMESITE'] = 'Strict'
    
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5001))) 