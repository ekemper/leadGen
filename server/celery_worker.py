from server.celery_instance import celery_app
import server.tasks

flask_app = create_app()
celery_app = make_celery(flask_app) 