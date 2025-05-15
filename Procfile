release: flask db upgrade
worker: python3 server/run_worker.py
web: gunicorn server.app:app 