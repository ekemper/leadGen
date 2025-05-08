import os
import logging
from pythonjsonlogger import jsonlogger
from datetime import datetime
from logging.handlers import RotatingFileHandler
import sys
import re
import json
from typing import Any, Dict, Union

# Constants
LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs'))
MAX_BYTES = 10 * 1024 * 1024  # 10MB
BACKUP_COUNT = 5

class LogSanitizer:
    """Utility class for sanitizing sensitive data in logs."""
    
    # Patterns for sensitive data
    SENSITIVE_PATTERNS = {
        'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        'phone': r'(?:\+?[1-9]\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        'credit_card': r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
        'api_key': r'(?i)(api[_-]?key|apikey|token|secret)[_-]?[=:]\s*[\w\-\.]+',
        'password': r'(?i)(password|passwd|pwd)[_-]?[=:]\s*[\w\-\.]+',
        'jwt': r'eyJ[A-Za-z0-9-_=]+\.eyJ[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*',
        'uuid': r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
    }
    
    # Fields that should always be redacted
    SENSITIVE_FIELDS = {
        'password', 'token', 'secret', 'api_key', 'apikey', 'auth_token',
        'access_token', 'refresh_token', 'authorization', 'credit_card',
        'ssn', 'social_security', 'phone', 'email', 'address'
    }
    
    @classmethod
    def sanitize_value(cls, value: Any) -> Any:
        """Sanitize a single value."""
        if isinstance(value, str):
            # Check for sensitive patterns
            for pattern_name, pattern in cls.SENSITIVE_PATTERNS.items():
                if re.search(pattern, value):
                    return f"[REDACTED_{pattern_name.upper()}]"
            return value
        elif isinstance(value, dict):
            return cls.sanitize_dict(value)
        elif isinstance(value, list):
            return [cls.sanitize_value(item) for item in value]
        return value
    
    @classmethod
    def sanitize_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize a dictionary of data."""
        if not isinstance(data, dict):
            return data
            
        sanitized = {}
        for key, value in data.items():
            # Check if the key itself is sensitive
            if any(sensitive in key.lower() for sensitive in cls.SENSITIVE_FIELDS):
                # Use specific redaction message based on the field type
                if 'email' in key.lower():
                    sanitized[key] = "[REDACTED_EMAIL]"
                elif 'phone' in key.lower():
                    sanitized[key] = "[REDACTED_PHONE]"
                elif 'api_key' in key.lower():
                    sanitized[key] = "[REDACTED_API_KEY]"
                elif 'password' in key.lower():
                    sanitized[key] = "[REDACTED_PASSWORD]"
                else:
                    sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = cls.sanitize_value(value)
        return sanitized
    
    @classmethod
    def sanitize_log_record(cls, record: logging.LogRecord) -> logging.LogRecord:
        """Sanitize a log record."""
        # Sanitize the message
        if isinstance(record.msg, dict):
            record.msg = cls.sanitize_dict(record.msg)
        elif isinstance(record.msg, str):
            for pattern_name, pattern in cls.SENSITIVE_PATTERNS.items():
                record.msg = re.sub(pattern, f"[REDACTED_{pattern_name.upper()}]", record.msg)
        
        # Sanitize args if they exist
        if record.args:
            if isinstance(record.args, tuple):
                record.args = tuple(cls.sanitize_value(arg) for arg in record.args)
            else:
                record.args = cls.sanitize_value(record.args)
        
        # Sanitize extra fields
        if hasattr(record, 'data'):
            record.data = cls.sanitize_dict(record.data)
        
        return record

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        # Add basic fields first
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        
        # Add timestamp if not present
        if not log_record.get('timestamp'):
            log_record['timestamp'] = datetime.utcnow().isoformat()
        
        # Add log level if not present
        if not log_record.get('level'):
            log_record['level'] = record.levelname.upper()
            
        # Add source name if not present
        if not log_record.get('source'):
            log_record['source'] = record.name
            
        # Handle message field properly
        if 'message' in message_dict:
            log_record['message'] = message_dict['message']
        elif hasattr(record, 'message'):
            log_record['message'] = record.message

class SanitizingFilter(logging.Filter):
    """Filter to sanitize log records before they are processed."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter and sanitize the log record."""
        LogSanitizer.sanitize_log_record(record)
        return True

def setup_logger(name, log_file, level=logging.INFO):
    """Set up a logger with JSON formatting and file output."""
    # Create logs directory if it doesn't exist
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    # Create formatter with explicit format string
    formatter = CustomJsonFormatter(
        fmt='%(timestamp)s %(level)s %(name)s %(message)s %(source)s',
        json_ensure_ascii=False,
        reserved_attrs=[]  # Allow all attributes to be processed
    )

    # Create rotating file handler with explicit mode
    log_path = os.path.join(LOG_DIR, log_file)
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding='utf-8',
        mode='a'  # Append mode
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers = []
    
    # Add sanitizing filter
    logger.addFilter(SanitizingFilter())
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    # Verify file handler is working
    try:
        logger.info(f"Logger {name} initialized", extra={'component': name})
        # Ensure the file exists and is writable
        if not os.path.exists(log_path):
            raise IOError(f"Log file {log_path} was not created")
        if not os.access(log_path, os.W_OK):
            raise IOError(f"Log file {log_path} is not writable")
    except Exception as e:
        console_handler.setLevel(logging.ERROR)
        logger.error(f"Failed to initialize logger: {str(e)}", extra={'component': name})
        raise

    return logger

# Create loggers for different components
browser_logger = setup_logger('browser', 'browser.log')
server_logger = setup_logger('server', 'server.log')
worker_logger = setup_logger('worker', 'worker.log')

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.WARNING)
root_logger.addFilter(SanitizingFilter())

# Configure third-party loggers
logging.getLogger('werkzeug').setLevel(logging.ERROR)
logging.getLogger('flask_limiter').setLevel(logging.ERROR)
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.pool').setLevel(logging.INFO)

def get_logger(component):
    """Get the appropriate logger for a component."""
    # Map component names to their canonical form
    component_map = {
        'auth_service': 'server',  # Map auth_service to server component
        'browser': 'browser',
        'server': 'server',
        'worker': 'worker'
    }
    
    # Get the canonical component name
    canonical_component = component_map.get(component, 'server')
    
    # Get the appropriate logger
    loggers = {
        'browser': browser_logger,
        'server': server_logger,
        'worker': worker_logger
    }
    logger = loggers.get(canonical_component, server_logger)
    
    # Ensure component is set in extra data
    def log_with_component(level, msg, *args, **kwargs):
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        kwargs['extra']['component'] = canonical_component
        return getattr(logger, level)(msg, *args, **kwargs)
    
    # Add component-specific logging methods
    logger.info = lambda msg, *args, **kwargs: log_with_component('info', msg, *args, **kwargs)
    logger.error = lambda msg, *args, **kwargs: log_with_component('error', msg, *args, **kwargs)
    logger.warning = lambda msg, *args, **kwargs: log_with_component('warning', msg, *args, **kwargs)
    logger.debug = lambda msg, *args, **kwargs: log_with_component('debug', msg, *args, **kwargs)
    
    return logger 