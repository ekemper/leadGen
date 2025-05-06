import logging
import os
from datetime import datetime
from pythonjsonlogger import jsonlogger
from flask import request, has_request_context

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
            
        # Add request information if available
        if has_request_context():
            log_record['request_id'] = getattr(request, 'id', None)
            log_record['method'] = request.method
            log_record['path'] = request.path
            log_record['remote_addr'] = request.remote_addr
            log_record['user_agent'] = request.user_agent.string
            
            # Add user information if authenticated
            if hasattr(request, 'user_id'):
                log_record['user_id'] = request.user_id

def setup_logger():
    """Configure the application logger."""
    logger = logging.getLogger('auth_app')
    logger.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO if os.getenv('FLASK_ENV') == 'development' else logging.ERROR)

    # Create formatter
    formatter = CustomJsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s',
        json_ensure_ascii=False
    )

    # Set formatter for console handler
    console_handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(console_handler)

    return logger

# Create logger instance
logger = setup_logger() 