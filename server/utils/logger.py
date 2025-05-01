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
    
    # Create logs directory if it doesn't exist
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    # File handler for all logs
    all_logs_file = os.path.join(log_dir, 'auth.log')
    file_handler = logging.FileHandler(all_logs_file)
    file_handler.setLevel(logging.INFO)
    
    # Error log file handler
    error_logs_file = os.path.join(log_dir, 'error.log')
    error_file_handler = logging.FileHandler(error_logs_file)
    error_file_handler.setLevel(logging.ERROR)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO if os.getenv('FLASK_ENV') == 'development' else logging.ERROR)
    
    # Create formatter
    formatter = CustomJsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s',
        json_ensure_ascii=False
    )
    
    # Set formatter for all handlers
    file_handler.setFormatter(formatter)
    error_file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(error_file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Create logger instance
logger = setup_logger() 