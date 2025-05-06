from flask_sqlalchemy import SQLAlchemy
import os
from sqlalchemy.exc import SQLAlchemyError
from server.utils.logging_config import server_logger, combined_logger

# Create the SQLAlchemy instance without initializing it
db = SQLAlchemy()

def init_db(app, test_config=None):
    """Initialize the database with the given Flask app
    
    Args:
        app: Flask application instance
        test_config: Optional dictionary containing test configuration
    """
    try:
        db_url = os.getenv('NEON_CONNECTION_STRING')
        
        if os.getenv('FLASK_ENV') == 'testing':
            server_logger.info('Using in-memory SQLite database for testing.', extra={'component': 'server'})
            combined_logger.info('Using in-memory SQLite database for testing.', extra={'component': 'server'})
            db_url = 'sqlite:///:memory:'
        elif not db_url:
            error_msg = 'NEON_CONNECTION_STRING must be set for application runtime.'
            server_logger.error(error_msg, extra={'component': 'server'})
            combined_logger.error(error_msg, extra={'component': 'server'})
            raise ValueError(error_msg)
        elif not db_url.startswith('postgresql://'):
            error_msg = f'NEON_CONNECTION_STRING does not appear to be a Neon connection string: {db_url}'
            server_logger.error(error_msg, extra={'component': 'server'})
            combined_logger.error(error_msg, extra={'component': 'server'})
            raise ValueError(error_msg)
        else:
            server_logger.info(f'Using Neon database: {db_url}', extra={'component': 'server'})
            combined_logger.info(f'Using Neon database: {db_url}', extra={'component': 'server'})
        
        app.config['SQLALCHEMY_DATABASE_URI'] = db_url
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        db.init_app(app)
        
        with app.app_context():
            db.create_all()
            
        server_logger.info('Database initialized successfully.', extra={'component': 'server'})
        combined_logger.info('Database initialized successfully.', extra={'component': 'server'})
        
    except Exception as e:
        error_msg = f"Database initialization failed: {str(e)}"
        server_logger.error(error_msg, extra={'component': 'server'})
        combined_logger.error(error_msg, extra={'component': 'server'})
        raise 