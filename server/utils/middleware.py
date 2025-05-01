import uuid
import time
from functools import wraps
from flask import request, g
from .logger import logger

def generate_request_id():
    """Generate a unique request ID."""
    return str(uuid.uuid4())

def log_request_info():
    """Log information about the current request."""
    # Don't log health check endpoints to avoid noise
    if request.path == '/health':
        return
    
    extra = {}
    if hasattr(g, 'start_time'):
        extra['duration_ms'] = int((time.time() - g.start_time) * 1000)
    if hasattr(g, 'status_code'):
        extra['status_code'] = g.status_code
    
    logger.info('Request processed', extra=extra)

def request_middleware(app):
    """Configure request middleware for the Flask app."""
    
    @app.before_request
    def before_request():
        # Add request ID
        request.id = generate_request_id()
        # Store start time
        g.start_time = time.time()
        
        # Log incoming request
        if request.path != '/health':
            logger.info(
                'Request started',
                extra={
                    'method': request.method,
                    'path': request.path,
                    'remote_addr': request.remote_addr,
                    'request_id': request.id
                }
            )
    
    @app.after_request
    def after_request(response):
        # Store response status code
        g.status_code = response.status_code
        # Add request ID to response headers
        response.headers['X-Request-ID'] = request.id
        return response
    
    @app.teardown_request
    def teardown_request(exception=None):
        if exception:
            logger.error(
                'Request failed',
                extra={
                    'error': str(exception),
                    'request_id': getattr(request, 'id', None)
                }
            )
        else:
            log_request_info()

def log_function_call(func):
    """Decorator to log function calls with timing information."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration_ms = int((time.time() - start_time) * 1000)
            logger.info(
                f'Function {func.__name__} completed',
                extra={
                    'function': func.__name__,
                    'duration_ms': duration_ms,
                    'success': True
                }
            )
            return result
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                f'Function {func.__name__} failed',
                extra={
                    'function': func.__name__,
                    'duration_ms': duration_ms,
                    'error': str(e),
                    'success': False
                }
            )
            raise
    return wrapper 