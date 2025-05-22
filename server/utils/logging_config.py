import os
import logging
from pythonjsonlogger import jsonlogger
from datetime import datetime
from logging.handlers import RotatingFileHandler
import sys
import re
import json
from typing import Any, Dict, Union
try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init()
except ImportError:
    class Fore:
        RED = ''
        GREEN = ''
        YELLOW = ''
        CYAN = ''
        MAGENTA = ''
        WHITE = ''
        LIGHTBLACK_EX = ''
    class Style:
        RESET_ALL = ''

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
            # Check against patterns
            for pattern_name, pattern in cls.SENSITIVE_PATTERNS.items():
                value = re.sub(pattern, f"[REDACTED_{pattern_name.upper()}]", value)
            return value
        elif isinstance(value, dict):
            return cls.sanitize_dict(value)
        elif isinstance(value, (list, tuple)):
            return [cls.sanitize_value(item) for item in value]
        return value
    
    @classmethod
    def sanitize_dict(cls, data: Dict) -> Dict:
        """Sanitize a dictionary recursively."""
        sanitized = {}
        for key, value in data.items():
            # Check if key is sensitive
            if any(field.lower() in key.lower() for field in cls.SENSITIVE_FIELDS):
                sanitized[key] = f"[REDACTED_{key.upper()}]"
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
    """Custom JSON formatter with standardized fields."""
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        
        # Add standard fields
        if not log_record.get('timestamp'):
            log_record['timestamp'] = datetime.utcnow().isoformat()
        if not log_record.get('level'):
            log_record['level'] = record.levelname.upper()
        if not log_record.get('source'):
            log_record['source'] = record.name
        
        # Add context if available
        if hasattr(record, 'context'):
            log_record['context'] = record.context
        
        # Add metadata if available
        if hasattr(record, 'metadata'):
            log_record['metadata'] = record.metadata

class SanitizingFilter(logging.Filter):
    """Filter to sanitize log records before they are processed."""
    def filter(self, record):
        LogSanitizer.sanitize_log_record(record)
        return True

def setup_logger(name: str = None, level: int = logging.INFO) -> logging.Logger:
    """
    Set up a logger with standardized configuration.
    
    Args:
        name: Logger name (defaults to 'app')
        level: Logging level (defaults to INFO)
    
    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(name or 'app')
    logger.setLevel(level)
    logger.handlers = []  # Remove any existing handlers
    
    # Create handlers
    console_handler = logging.StreamHandler(sys.stdout)
    file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, f"{name or 'app'}.log"),
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT
    )
    
    # Create formatter
    formatter = CustomJsonFormatter(
        fmt='%(timestamp)s %(level)s %(name)s %(message)s',
        json_ensure_ascii=False,
        reserved_attrs=[]
    )
    
    # Configure handlers
    for handler in [console_handler, file_handler]:
        handler.setFormatter(formatter)
        handler.addFilter(SanitizingFilter())
        handler.setLevel(level)
        logger.addHandler(handler)
    
    # Prevent propagation to avoid duplicate logs
    logger.propagate = False
    
    return logger

class ContextLogger:
    """Context manager for adding context to logs."""
    def __init__(self, logger, **context):
        self.logger = logger
        self.context = context
        self.old_context = {}
        
    def __enter__(self):
        # Store and update context
        self.old_context = getattr(self.logger, 'context', {}).copy()
        current_context = self.old_context.copy()
        current_context.update(self.context)
        setattr(self.logger, 'context', current_context)
        return self.logger
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original context
        setattr(self.logger, 'context', self.old_context)

def configure_third_party_loggers():
    """Configure logging levels for third-party libraries."""
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    logging.getLogger('flask_limiter').setLevel(logging.ERROR)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.pool').setLevel(logging.INFO)

# Configure third-party loggers
configure_third_party_loggers()

__all__ = ['ContextLogger', 'setup_logger', 'LogSanitizer'] 