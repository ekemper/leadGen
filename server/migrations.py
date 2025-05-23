import os
from flask_migrate import Migrate
from server.app import create_app
from server.config.database import db
from server.models.user import User  # Import User model explicitly

app = create_app()
migrate = Migrate(app, db)

if __name__ == '__main__':
    app.run() 