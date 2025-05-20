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
from server.utils.logging_config import app_logger
from server.api.openapi import create_spec, register_spec
from limits.storage import RedisStorage
import ssl

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
    
    # Ensure REDIS_URL is set in app.config from environment
    app.config['REDIS_URL'] = os.environ.get('REDIS_URL')
    
    # Initialize extensions with CORS config
    CORS(app, 
         resources={
             r"/*": {
                 "origins": [
                     "http://localhost", "http://127.0.0.1"#,
                    #  "http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://127.0.0.1:3000"
                 ],
                 "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
                 "allow_headers": ["Content-Type", "Authorization", "X-Request-ID"],
                 "expose_headers": ["Content-Type", "Authorization", "X-Request-ID"],
                 "supports_credentials": True,
                 "max_age": 3600
             }
         })
    
    # Add CORS headers to all responses
    @app.after_request
    def after_request(response):
        origin = request.headers.get('Origin')
        allowed_origins = ["http://localhost", "http://127.0.0.1"]#, "http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://127.0.0.1:3000"]
        if origin in allowed_origins:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, PATCH'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Request-ID'
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Max-Age'] = '3600'
            response.headers['Access-Control-Expose-Headers'] = 'Content-Type, Authorization, X-Request-ID'
        return response
    
    # Configure rate limiting (single source of truth)
    if app.config.get('RATELIMIT_ENABLED', True):
        redis_url = app.config.get('REDIS_URL', 'redis://localhost:6379/0')
        storage_options = {}
        if redis_url.startswith('rediss://'):
            cert_reqs = os.environ.get('REDIS_SSL_CERT_REQS', 'required')
            if cert_reqs == 'none':
                storage_options['ssl_cert_reqs'] = ssl.CERT_NONE
        limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            default_limits=["200 per day", "50 per hour"],
            storage_uri=redis_url,
            storage_options=storage_options,
            strategy="moving-window"
        )
        # Decorate /api/events with a higher limit
        from flask import Blueprint
        for rule in app.url_map.iter_rules():
            if rule.rule == '/api/events' and 'POST' in rule.methods:
                view_func = app.view_functions[rule.endpoint]
                app.view_functions[rule.endpoint] = limiter.limit("1000 per hour")(view_func)
        # Exempt /api/health from rate limiting
        @limiter.exempt
        @app.route('/api/health', methods=['GET'])
        def health_check():
            app_logger.debug('Health check endpoint called')
            return jsonify({
                'status': 'healthy',
                'message': 'API is running',
                'endpoint': '/api/health'
            }), 200
    else:
        @app.route('/api/health', methods=['GET'])
        def health_check():
            app_logger.debug('Health check endpoint called (no rate limit)')
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
        response = {
            'status': 'error',
            'error': {
                'code': error.code,
                'name': error.name,
                'message': error.description
            }
        }
        app_logger.error(
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
        app_logger.error(
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
        app_logger.error(
            "Unhandled exception",
            extra={
                'error_code': 500,
                'error_type': type(error).__name__,
                'error_message': str(error)
            }
        )
        return jsonify(response), 500
    
    # Log application startup
    app_logger.info("Flask application initialized")

    # Serve React build for all non-API routes
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_react_app(path):
        static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static'))
        file_path = os.path.join(static_dir, path)
        print(f"Serving from: {file_path}")  # Debug log
        if path and os.path.exists(file_path):
            return send_from_directory(static_dir, path)
        return send_from_directory(static_dir, 'index.html')

    return app

app = create_app()

# Only create the app if running directly
if __name__ == '__main__':
    app_logger.info('Starting application', extra={
        'environment': os.getenv('FLASK_ENV', 'development'),
        'debug_mode': os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    })
    
    if os.getenv('FLASK_ENV') == 'production':
        app.config['SESSION_COOKIE_SECURE'] = True
        app.config['SESSION_COOKIE_HTTPONLY'] = True
        app.config['SESSION_COOKIE_SAMESITE'] = 'Strict'
    
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5001)), use_reloader=True) 
    