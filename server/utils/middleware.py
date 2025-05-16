import uuid
import time
from functools import wraps
from flask import request, g
from server.utils.logging_config import app_logger

def generate_request_id():
    """Generate a unique request ID."""
    return str(uuid.uuid4())

def log_request_info():
    """Log information about the current request."""
    # Don't log health check endpoints to avoid noise
    if request.path == '/health':
        return
    
    extra = dict(g.request_context)
    if hasattr(g, 'start_time'):
        extra['duration_ms'] = int((time.time() - g.start_time) * 1000)
    if hasattr(g, 'status_code'):
        extra['status_code'] = g.status_code
    
    app_logger.info('Request processed', extra=extra)

def request_middleware(app):
    """Configure request middleware for the Flask app."""
    
    @app.before_request
    def before_request():
        # Accept request ID from header or generate new
        request_id = request.headers.get('X-Request-ID') or generate_request_id()
        g.request_id = request_id
        # Build context object
        g.request_context = {
            'request_id': request_id,
            'user_id': getattr(getattr(g, 'current_user', None), 'id', None),
            'session_id': request.cookies.get('session'),
            'client_ip': request.remote_addr,
            'user_agent': request.user_agent.string,
        }
        g.start_time = time.time()
        
        # Log incoming request
        if request.path != '/health':
            extra = dict(g.request_context)
            app_logger.info('Request started', extra=extra)
    
    @app.after_request
    def after_request(response):
        # Store response status code
        g.status_code = response.status_code
        # Add request ID to response headers
        response.headers['X-Request-ID'] = g.request_id
        return response
    
    @app.teardown_request
    def teardown_request(exception=None):
        if exception:
            extra = dict(g.request_context)
            extra['error'] = str(exception)
            app_logger.error('Request failed', extra=extra)
        else:
            log_request_info()

def log_function_call(func):
    """Decorator to log function calls with timing information and request context."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration_ms = int((time.time() - start_time) * 1000)
            extra = dict(getattr(g, 'request_context', {}))
            extra.update({
                'function': func.__name__,
                'duration_ms': duration_ms,
                'success': True
            })
            app_logger.info(f'Function {func.__name__} completed', extra=extra)
            return result
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            extra = dict(getattr(g, 'request_context', {}))
            extra.update({
                'function': func.__name__,
                'duration_ms': duration_ms,
                'error': str(e),
                'success': False
            })
            app_logger.error(f'Function {func.__name__} failed', extra=extra)
            raise
    return wrapper 