import uuid
import time
from functools import wraps
from flask import request, g
from server.utils.logging_config import server_logger, combined_logger

def generate_request_id():
    """Generate a unique request ID."""
    return str(uuid.uuid4())

def log_request_info():
    """Log information about the current request."""
    # Don't log health check endpoints to avoid noise
    if request.path == '/health':
        return
    
    extra = {
        'method': request.method,
        'path': request.path,
        'remote_addr': request.remote_addr,
        'request_id': getattr(g, 'request_id', None),
    }
    
    if hasattr(g, 'start_time'):
        extra['duration_ms'] = int((time.time() - g.start_time) * 1000)
    if hasattr(g, 'status_code'):
        extra['status_code'] = g.status_code
    
    server_logger.info('Request processed', extra=extra)
    combined_logger.info('Request processed', extra={
        'component': 'server',
        **extra
    })

def request_middleware(app):
    """Configure request middleware for the Flask app."""
    
    @app.before_request
    def before_request():
        # Add request ID to g
        g.request_id = generate_request_id()
        # Store start time
        g.start_time = time.time()
        
        # Log incoming request
        if request.path != '/health':
            extra = {
                'method': request.method,
                'path': request.path,
                'remote_addr': request.remote_addr,
                'request_id': g.request_id,
                'user_agent': request.user_agent.string
            }
            server_logger.info('Request started', extra=extra)
            combined_logger.info('Request started', extra={
                'component': 'server',
                **extra
            })
    
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
            extra = {
                'error': str(exception),
                'request_id': getattr(g, 'request_id', None),
                'method': request.method,
                'path': request.path,
                'remote_addr': request.remote_addr,
                'user_agent': request.user_agent.string
            }
            server_logger.error('Request failed', extra=extra)
            combined_logger.error('Request failed', extra={
                'component': 'server',
                **extra
            })
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
            extra = {
                'function': func.__name__,
                'duration_ms': duration_ms,
                'success': True,
                'request_id': getattr(g, 'request_id', None)
            }
            server_logger.info(f'Function {func.__name__} completed', extra=extra)
            combined_logger.info(f'Function {func.__name__} completed', extra={
                'component': 'server',
                **extra
            })
            return result
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            extra = {
                'function': func.__name__,
                'duration_ms': duration_ms,
                'error': str(e),
                'success': False,
                'request_id': getattr(g, 'request_id', None)
            }
            server_logger.error(f'Function {func.__name__} failed', extra=extra)
            combined_logger.error(f'Function {func.__name__} failed', extra={
                'component': 'server',
                **extra
            })
            raise
    return wrapper 