from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def init_db(app, test_config=None):
    """Initialize the database with the Flask app"""
    if test_config is None:
        # Use the configured database URL
        app.config['SQLALCHEMY_DATABASE_URI'] = app.config.get('DATABASE_URL', 'sqlite:///app.db')
    else:
        # Use test configuration if provided
        app.config['SQLALCHEMY_DATABASE_URI'] = test_config.get('DATABASE_URL', 'sqlite:///:memory:')
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app) 