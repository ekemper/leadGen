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
    
    if test_config is not None:
        # Use test configuration if provided
        app.config.update(test_config)
    else:
        # Get database URL from environment or use SQLite for development
        database_url = os.getenv('DATABASE_URL')
        if database_url and database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///dev.db'
    
    try:
        # Initialize the SQLAlchemy app
        db.init_app(app)
        
        # Create tables if they don't exist
        with app.app_context():
            db.create_all()
            
    except SQLAlchemyError as e:
        logging.error(f"Database initialization failed: {str(e)}")
        raise 