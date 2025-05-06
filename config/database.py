from flask_sqlalchemy import SQLAlchemy
import os
from sqlalchemy.exc import SQLAlchemyError
import logging

# Create the SQLAlchemy instance without initializing it
db = SQLAlchemy()

def init_db(app, test_config=None):
    """Initialize the database with the given Flask app
    
    Args:
        app: Flask application instance
        test_config: Optional dictionary containing test configuration
    """
    # Configure SQLAlchemy
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    logger = logging.getLogger('database_config')
    
    if test_config is not None:
        # Use test configuration if provided
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {}
        logger.info('Using in-memory SQLite database for testing.')
    else:
        # Get database URL from environment or use SQLite for development
        db_url = os.getenv('NEON_CONNECTION_STRING')
        if not db_url:
            logger.error('NEON_CONNECTION_STRING must be set for application runtime.')
            raise RuntimeError('NEON_CONNECTION_STRING must be set for application runtime.')
        if 'neon.tech' not in db_url:
            logger.error(f'NEON_CONNECTION_STRING does not appear to be a Neon connection string: {db_url}')
            raise RuntimeError('NEON_CONNECTION_STRING does not appear to be a Neon connection string.')
        app.config['SQLALCHEMY_DATABASE_URI'] = db_url
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_size': 5,
            'pool_timeout': 30,
            'pool_recycle': 60,
            'max_overflow': 2,
            'pool_pre_ping': True,
        }
        logger.info(f'Using Neon database: {db_url}')
    
    try:
        # Initialize the SQLAlchemy app
        db.init_app(app)
        
        # Create tables if they don't exist
        with app.app_context():
            db.create_all()
            
        logger.info('Database initialized successfully.')
    except SQLAlchemyError as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise 