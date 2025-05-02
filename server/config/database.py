import os
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from urllib.parse import urlparse

db = SQLAlchemy()

def get_db_url():
    """Get database URL with proper SSL configuration for Neon"""
    # Try to get Neon connection string first, fall back to DATABASE_URL, then sqlite
    db_url = os.getenv('NEON_CONNECTION_STRING') or os.getenv('DATABASE_URL', 'sqlite:///app.db')
    
    if db_url.startswith('postgresql://'):
        # Parse the URL
        parsed = urlparse(db_url)
        
        # Add SSL mode if not already present
        if 'sslmode' not in parsed.query:
            if '?' in db_url:
                db_url += '&sslmode=require'
            else:
                db_url += '?sslmode=require'
    
    return db_url

def init_db(app, test_config=None):
    """Initialize the database with the Flask app"""
    if test_config is None:
        # Use the configured database URL with SSL for Neon
        app.config['SQLALCHEMY_DATABASE_URI'] = get_db_url()
        
        # Configure SQLAlchemy pool settings for Neon/PostgreSQL only
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_size': 5,  # Maximum number of connections in the pool
            'pool_timeout': 30,  # Seconds to wait before timing out
            'pool_recycle': 60,  # Recycle connections after 60 seconds
            'max_overflow': 2,  # Maximum number of connections that can be created beyond pool_size
            'pool_pre_ping': True,  # Check if connection is alive before using
        }
    else:
        # Use test configuration if provided
        app.config['SQLALCHEMY_DATABASE_URI'] = test_config.get('DATABASE_URL', 'sqlite:///:memory:')
        # No pool settings for SQLite test database
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {}
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    # Create tables if they don't exist
    with app.app_context():
        db.create_all() 