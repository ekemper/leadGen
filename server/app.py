import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from dotenv import load_dotenv
from server.utils.middleware import request_middleware
from server.config.database import db, init_db
from server.api import create_api_blueprint
from werkzeug.exceptions import HTTPException, BadRequest
from server.utils.logging_config import setup_logger, ContextLogger
from server.api.openapi import create_spec, register_spec
from limits.storage import RedisStorage
import ssl
from server.extensions import limiter

# Set up application logger
logger = setup_logger('flask.app')

def create_app(test_config=None):
    """Create and configure the Flask application"""
    with ContextLogger(logger, phase='initialization'):
        try:
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
            
            # Ensure REDIS_URL is set in app.config from environment
            app.config['REDIS_URL'] = os.environ.get('REDIS_URL')
            
            # Initialize extensions with CORS config
            CORS(app, 
                 resources={
                     r"/*": {
                         "origins": [
                             "http://localhost", "http://127.0.0.1", "http://localhost:5173", "http://127.0.0.1:5173"
                         ],
                         "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
                         "allow_headers": ["Content-Type", "Authorization", "X-Request-ID"],
                         "expose_headers": ["Content-Type", "Authorization", "X-Request-ID"],
                         "supports_credentials": True,
                         "max_age": 3600
                     }
                 })
            
            # Configure rate limiting (single source of truth)
            limiter.init_app(app)
            if app.config.get('RATELIMIT_ENABLED', True):
                redis_url = app.config.get('REDIS_URL', 'redis://localhost:6379/0')
                storage_options = {}
                if redis_url.startswith('rediss://'):
                    cert_reqs = os.environ.get('REDIS_SSL_CERT_REQS', 'required')
                    if cert_reqs == 'none':
                        storage_options['ssl_cert_reqs'] = ssl.CERT_NONE
                limiter.storage_uri = redis_url
                limiter.storage_options = storage_options
                limiter.strategy = "moving-window"
                # Exempt /api/health from rate limiting
                @limiter.exempt
                @app.route('/api/health', methods=['GET'])
                def health_check():
                    logger.debug('Health check endpoint called')
                    return jsonify({
                        'status': 'healthy',
                        'message': 'API is running',
                        'endpoint': '/api/health'
                    }), 200
            else:
                @app.route('/api/health', methods=['GET'])
                def health_check():
                    logger.debug('Health check endpoint called (no rate limit)')
                    return jsonify({
                        'status': 'healthy',
                        'message': 'API is running',
                        'endpoint': '/api/health'
                    }), 200
            
            # Initialize database
            init_db(app)
            migrate = Migrate(app, db)
            
            # Create and register OpenAPI spec
            spec = create_spec()
            register_spec(app, spec)
            
            # Register blueprints
            api_blueprint = create_api_blueprint()
            app.register_blueprint(api_blueprint, url_prefix='/api')
            
            # Register error handlers
            @app.errorhandler(HTTPException)
            def handle_http_error(error):
                """Handle HTTP exceptions."""
                with ContextLogger(logger, error_type='http'):
                    response = {
                        'status': 'error',
                        'error': {
                            'code': error.code,
                            'name': error.name,
                            'message': error.description
                        }
                    }
                    logger.error("HTTP error", extra={
                        'metadata': {
                            'error_code': error.code,
                            'error_name': error.name,
                            'error_message': error.description
                        }
                    })
                    return jsonify(response), error.code

            @app.errorhandler(BadRequest)
            def handle_bad_request(error):
                """Handle bad request errors."""
                with ContextLogger(logger, error_type='bad_request'):
                    response = {
                        'status': 'error',
                        'error': {
                            'code': 400,
                            'name': 'Bad Request',
                            'message': str(error.description)
                        }
                    }
                    logger.error("Bad request error", extra={
                        'metadata': {
                            'error_code': 400,
                            'error_message': str(error.description)
                        }
                    })
                    return jsonify(response), 400

            @app.errorhandler(Exception)
            def handle_generic_error(error):
                """Handle generic exceptions."""
                with ContextLogger(logger, error_type='unhandled'):
                    response = {
                        'status': 'error',
                        'error': {
                            'code': 500,
                            'name': 'Internal Server Error',
                            'message': str(error)
                        }
                    }
                    logger.error("Unhandled exception", extra={
                        'metadata': {
                            'error_code': 500,
                            'error_type': type(error).__name__,
                            'error_message': str(error)
                        }
                    }, exc_info=True)
                    return jsonify(response), 500
            
            logger.info("Application initialized successfully")
            return app
            
        except Exception as e:
            logger.error("Failed to initialize application", exc_info=True)
            raise

app = create_app()

# Only create the app if running directly
if __name__ == '__main__':
    logger.info('Starting application', extra={
        'metadata': {
            'environment': os.getenv('FLASK_ENV', 'development'),
            'debug_mode': os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
        }
    })
    
    if os.getenv('FLASK_ENV') == 'production':
        app.config['SESSION_COOKIE_SECURE'] = True
        app.config['SESSION_COOKIE_HTTPONLY'] = True
        app.config['SESSION_COOKIE_SAMESITE'] = 'Strict'
    
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5001)), use_reloader=True) 
    