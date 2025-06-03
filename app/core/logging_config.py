from __future__ import annotations

import os
import logging
from pythonjsonlogger import jsonlogger
from datetime import datetime
from logging.handlers import RotatingFileHandler
import sys
import re
import json
from typing import Any, Dict, Union

# Import settings for environment variable configuration
from app.core.config import settings

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

# Constants - now using environment variables from settings
LOG_DIR = os.path.abspath(settings.LOG_DIR)
# Ensure the directory exists at import time
os.makedirs(LOG_DIR, exist_ok=True)
# Use environment variables for rotation settings
MAX_BYTES = settings.LOG_ROTATION_SIZE
BACKUP_COUNT = settings.LOG_BACKUP_COUNT

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
        # Sanitize the log record first
        LogSanitizer.sanitize_log_record(record)
        
        # Also sanitize any extra fields that were added to the record
        # Get all attributes that aren't standard LogRecord attributes
        standard_attrs = {
            'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
            'module', 'exc_info', 'exc_text', 'stack_info', 'lineno', 'funcName',
            'created', 'msecs', 'relativeCreated', 'thread', 'threadName',
            'processName', 'process', 'message', 'asctime'
        }
        
        for attr_name in dir(record):
            if not attr_name.startswith('_') and attr_name not in standard_attrs:
                attr_value = getattr(record, attr_name)
                if not callable(attr_value):
                    # Check if this is a sensitive field
                    if any(sensitive in attr_name.lower() for sensitive in LogSanitizer.SENSITIVE_FIELDS):
                        # Sanitize sensitive field names
                        if 'email' in attr_name.lower():
                            setattr(record, attr_name, "[REDACTED_EMAIL]")
                        elif 'phone' in attr_name.lower():
                            setattr(record, attr_name, "[REDACTED_PHONE]")
                        elif 'api_key' in attr_name.lower():
                            setattr(record, attr_name, "[REDACTED_API_KEY]")
                        elif 'password' in attr_name.lower():
                            setattr(record, attr_name, "[REDACTED_PASSWORD]")
                        else:
                            setattr(record, attr_name, "[REDACTED]")
                    else:
                        # Sanitize the value
                        sanitized_value = LogSanitizer.sanitize_value(attr_value)
                        setattr(record, attr_name, sanitized_value)
        
        return True

class EnhancedColorFormatter(logging.Formatter):
    LEVEL_COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.MAGENTA
    }
    CONTEXT_COLOR = Fore.CYAN
    KEY_COLOR = Fore.YELLOW
    VALUE_COLOR = Fore.WHITE
    TIME_COLOR = Fore.LIGHTBLACK_EX

    def format(self, record):
        color = self.LEVEL_COLORS.get(record.levelname, '')
        reset = Style.RESET_ALL
        time_str = datetime.utcnow().isoformat()
        msg = record.getMessage()
        context = ''
        # Extract context from message prefix, e.g., [WEBHOOK]
        if msg.startswith('['):
            end = msg.find(']')
            if end != -1:
                context = msg[:end+1]
                msg = msg[end+2:].lstrip()
        # Pretty-print JSON if possible
        pretty_json = None
        try:
            if isinstance(record.msg, dict):
                pretty_json = json.dumps(record.msg, indent=2)
            else:
                # Try to parse as JSON
                parsed = json.loads(msg)
                pretty_json = json.dumps(parsed, indent=2)
        except Exception:
            pass  # Not JSON, leave as is
        # Colorize context
        context_str = f"{self.CONTEXT_COLOR}{context}{reset}" if context else ""
        # Colorize level
        level_str = f"{color}[{record.levelname}]{reset}"
        # Colorize time
        time_str_col = f"{self.TIME_COLOR}{time_str}{reset}"
        # If pretty_json, colorize keys/values
        if pretty_json:
            def colorize_json(json_str):
                lines = json_str.splitlines()
                colored = []
                for line in lines:
                    # Colorize keys and values
                    if ':' in line:
                        key, val = line.split(':', 1)
                        colored.append(f"{self.KEY_COLOR}{key}:{reset}{self.VALUE_COLOR}{val}{reset}")
                    else:
                        colored.append(f"{self.VALUE_COLOR}{line}{reset}")
                return '\n'.join(colored)
            msg = '\n' + colorize_json(pretty_json)
        return f"{level_str} {time_str_col} {context_str} {msg}"

def init_logging(level: int | None = None) -> logging.Logger:
    """Bootstrap application-wide logging. Safe to call multiple times."""

    # Resolve desired log level (use settings LOG_LEVEL with fallback to env var)
    if level is None:
        level_name = settings.LOG_LEVEL.upper()
        level = getattr(logging, level_name, logging.INFO)

    formatter = CustomJsonFormatter(
        fmt="%(timestamp)s %(level)s %(name)s %(message)s %(source)s %(component)s",
        json_ensure_ascii=False,
        reserved_attrs=[],
    )

    root_logger = logging.getLogger()

    # Idempotency – if we already added our sentinel handler, just return
    for h in root_logger.handlers:
        if getattr(h, "_is_central_handler", False):
            root_logger.setLevel(level)
            return logging.getLogger("app")

    # Console / docker-stdout
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    console_handler._is_central_handler = True  # sentinel attr

    # Shared rotating file – one file for all containers (same volume)
    combined_log_path = os.path.join(LOG_DIR, "combined.log")
    file_handler = RotatingFileHandler(
        combined_log_path,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    file_handler._is_central_handler = True

    # Reset existing handlers (avoid duplicate logs when reloaded)
    root_logger.handlers = []
    root_logger.setLevel(level)
    root_logger.addFilter(SanitizingFilter())
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Quiet noisy libraries
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    logging.getLogger("flask_limiter").setLevel(logging.ERROR)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.INFO)

    app_logger = logging.getLogger("app")
    app_logger.info("Centralised logger initialised", extra={"component": "logger"})
    return app_logger

# Backwards-compatibility for existing imports
setup_central_logger = init_logging

# Initialise at import time so any early imports get the logger
app_logger = init_logging() 