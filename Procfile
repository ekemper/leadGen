release: flask db upgrade
worker: python server/run_worker.py
web: gunicorn -b 0.0.0.0:$PORT server.app:app 