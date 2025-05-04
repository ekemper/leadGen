import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from flask import Flask, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from dotenv import load_dotenv
from server.utils.middleware import request_middleware
from server.config.database import db, init_db
from server.api import create_api_blueprint
from werkzeug.exceptions import HTTPException, BadRequest
import logging

print('sys.path:', sys.path)
print('CWD:', os.getcwd())

# Set global log level to WARNING to reduce noise
logging.basicConfig(level=logging.WARNING)

# Reduce noise from specific libraries
logging.getLogger('werkzeug').setLevel(logging.ERROR)
logging.getLogger('flask_limiter').setLevel(logging.ERROR)
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

# Enable SQLAlchemy engine and pool logging for debugging SQL connection errors
logging.getLogger('sqlalchemy.pool').setLevel(logging.INFO)

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
        return jsonify(response), 500
    
    return app

# Only create the app if running directly
if __name__ == '__main__':
    from server.utils.logger import logger
    
    app = create_app()
    
    logger.info('Starting application', extra={
        'environment': os.getenv('FLASK_ENV', 'development'),
        'debug_mode': os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    })
    
    if os.getenv('FLASK_ENV') == 'production':
        app.config['SESSION_COOKIE_SECURE'] = True
        app.config['SESSION_COOKIE_HTTPONLY'] = True
        app.config['SESSION_COOKIE_SAMESITE'] = 'Strict'
    
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5001))) 