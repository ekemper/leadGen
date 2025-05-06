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
LOG_DIR = os.path.join(os.getcwd(), 'logs')
MAX_BYTES = 10 * 1024 * 1024  # 10MB
BACKUP_COUNT = 5

class LogSanitizer:
    """Utility class for sanitizing sensitive data in logs."""
    
    # Patterns for sensitive data
    SENSITIVE_PATTERNS = {
        'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        'phone': r'\+?[1-9]\d{1,14}',
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
        sanitized = {}
        for key, value in data.items():
            # Check if the key itself is sensitive
            if any(sensitive in key.lower() for sensitive in cls.SENSITIVE_FIELDS):
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
        if hasattr(record, 'extra'):
            record.extra = cls.sanitize_dict(record.extra)
        
        return record

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        
        # Add timestamp
        if not log_record.get('timestamp'):
            log_record['timestamp'] = datetime.utcnow().isoformat()
        
        # Add log level
        if log_record.get('level'):
            log_record['level'] = log_record['level'].upper()
        else:
            log_record['level'] = record.levelname
            
        # Add component name
        if not log_record.get('component'):
            log_record['component'] = record.name

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

    # Create formatter
    formatter = CustomJsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s',
        json_ensure_ascii=False
    )

    # Create rotating file handler
    file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, log_file),
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

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

    return logger

# Create loggers for different components
browser_logger = setup_logger('browser', 'browser.log')
server_logger = setup_logger('server', 'server.log')
worker_logger = setup_logger('worker', 'worker.log')
combined_logger = setup_logger('combined', 'combined.log')

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
    loggers = {
        'browser': browser_logger,
        'server': server_logger,
        'worker': worker_logger,
        'combined': combined_logger
    }
    return loggers.get(component, combined_logger) 