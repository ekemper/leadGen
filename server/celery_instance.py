from server.app import create_app
from server.celery_app import make_celery

flask_app = create_app()
celery_app = make_celery(flask_app)

import server.tasks  # Force task registration 