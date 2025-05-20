from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from server.utils.logging_config import server_logger

def get_database_url():
    """Get the database URL from environment variables."""
    import os
    
    # Check if we're in test mode
    if os.environ.get('TESTING') == 'true':
        # Use in-memory SQLite for testing
        db_url = 'sqlite:///:memory:'
        server_logger.info('Using in-memory SQLite database for testing.')
        return db_url
    
    # Get database URL from environment
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        error_msg = 'DATABASE_URL environment variable not set'
        server_logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Validate database URL
    if not db_url.startswith('postgresql://'):
        error_msg = f'Invalid database URL: {db_url}. Must be a PostgreSQL URL.'
        server_logger.error(error_msg)
        raise ValueError(error_msg)
    
    server_logger.info(f'Using database: {db_url}')
    return db_url

def init_database():
    """Initialize the database connection."""
    try:
        # Get database URL
        db_url = get_database_url()
        
        # Create engine and session factory
        engine = create_engine(db_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        server_logger.info('Database initialized successfully.')
        return engine, SessionLocal
        
    except Exception as e:
        error_msg = f'Failed to initialize database: {str(e)}'
        server_logger.error(error_msg)
        raise RuntimeError(error_msg) from e 