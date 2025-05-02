import os
from flask_migrate import Migrate
from app import create_app
from server.config.database import db
from server.models.user import User  # Import User model explicitly

os.environ['DATABASE_URL'] = os.getenv('NEON_CONNECTION_STRING')
app = create_app()
migrate = Migrate(app, db)

if __name__ == '__main__':
    app.run() 