"""
Patch for Heroku DATABASE_URL compatibility:
Heroku provides the DATABASE_URL environment variable with the legacy 'postgres://' prefix, but SQLAlchemy requires 'postgresql://'.
This patch rewrites the prefix if necessary before SQLAlchemy is initialized.
"""
import os
# Patch DATABASE_URL for SQLAlchemy compatibility with Heroku
_db_url = os.environ.get('DATABASE_URL')
if _db_url and _db_url.startswith('postgres://'):
    os.environ['DATABASE_URL'] = _db_url.replace('postgres://', 'postgresql://', 1)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from server.utils.logging_config import setup_logger, ContextLogger

db = SQLAlchemy()

# Set up logger
logger = setup_logger('database')

def get_database_url():
    """Get the database URL from environment variables."""
    with ContextLogger(logger, phase='url_validation'):
        # Check if we're in test mode
        if os.environ.get('TESTING') == 'true':
            # Use in-memory SQLite for testing
            db_url = 'sqlite:///:memory:'
            logger.info('Using in-memory SQLite database for testing')
            return db_url
        
        # Get database URL from environment
        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            error_msg = 'DATABASE_URL environment variable not set'
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Validate database URL
        if not db_url.startswith('postgresql://'):
            error_msg = f'Invalid database URL: {db_url}. Must be a PostgreSQL URL.'
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info("Database URL validated", extra={
            'metadata': {
                'url_type': 'postgresql',
                'is_test': False
            }
        })
        return db_url

def init_database():
    """Initialize the database connection."""
    with ContextLogger(logger, phase='initialization'):
        try:
            # Get database URL
            db_url = get_database_url()
            
            # Create engine and session factory
            engine = create_engine(db_url)
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            
            logger.info("Database initialized successfully", extra={
                'metadata': {
                    'engine_type': engine.name,
                    'pool_size': engine.pool.size()
                }
            })
            return engine, SessionLocal
            
        except Exception as e:
            error_msg = f'Failed to initialize database: {str(e)}'
            logger.error(error_msg, extra={
                'metadata': {'error': str(e)}
            }, exc_info=True)
            raise RuntimeError(error_msg) from e

def get_db_url():
    """Get the database URL: use Neon for runtime, sqlite for tests."""
    if os.getenv('FLASK_ENV') == 'test':
        return 'sqlite:///:memory:'
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        raise RuntimeError('DATABASE_URL must be set for application runtime.')
    return db_url

def init_db(app, test_config=None):
    """Initialize the database with the Flask app"""
    if test_config is None:
        app.config['SQLALCHEMY_DATABASE_URI'] = get_db_url()
        # Only use connection pool settings for non-SQLite databases
        if not app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite'):
            app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
                'pool_size': 5,
                'pool_timeout': 30,
                'pool_recycle': 60,
                'max_overflow': 2,
                'pool_pre_ping': True,
            }
        else:
            app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {}
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {}
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    # with app.app_context():
    #     db.create_all() 