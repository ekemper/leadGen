import os
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

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