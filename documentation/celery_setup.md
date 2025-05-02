# Celery Setup & Usage Guide

This guide explains how to configure and run Celery for background task processing in the Lead Generation Server.

---

## 1. Install Celery and Redis dependencies

These are included in `requirements.txt`, but you can install them manually if needed:

```bash
pip install celery redis
```

---

## 2. Ensure Redis is Running

Celery uses Redis as the default broker and result backend. Start Redis locally (default port 6379):

```bash
redis-server
```

If you see an error about port 6379 being in use, stop the existing process or use another port.

---

## 3. Environment Variables

Celery uses the following environment variables (or their defaults):

- `CELERY_BROKER_URL` (default: `redis://localhost:6379/0`)
- `CELERY_RESULT_BACKEND` (default: `redis://localhost:6379/0`)

Override these in your `.env` file if needed.

---

## 4. Start a Celery Worker

From the `server/` directory, run:

```bash
celery -A celery_instance.celery_app worker --loglevel=info
```

- `-A celery_instance.celery_app` tells Celery to use the app instance from `celery_instance.py`.
- `--loglevel=info` gives you useful output.

---

## 5. Triggering Tasks

Tasks are triggered automatically by the API (e.g., when creating a campaign). You do not need to manually enqueue tasks.

---

## 6. Troubleshooting

- **Redis connection errors:** Ensure Redis is running and accessible at the configured URL.
- **Import errors:** Make sure you run the worker from the `server/` directory so imports resolve correctly.
- **Port in use:** If Redis fails to start, check for existing processes on port 6379 (`lsof -i :6379`).

For more details, see the [Celery documentation](https://docs.celeryq.dev/) and [Redis documentation](https://redis.io/docs/).

---

## 7. Advanced Troubleshooting: Database SSL Errors

If you see errors like:

```
(psycopg2.OperationalError) SSL error: decryption failed or bad record mac
```

This is usually caused by stale or dropped database connections, especially with cloud Postgres providers. To mitigate this:

- The SQLAlchemy `pool_recycle` setting has been lowered to 60 seconds in `server/config/database.py`:
  ```python
  'pool_recycle': 60,  # Recycle connections after 1 minute
  ```
- This helps ensure connections are regularly refreshed, reducing the chance of SSL errors.
- If you still see errors, check your database connection string and network stability.

---

## 8. Running Celery with the Correct PYTHONPATH

If you run the Celery worker from inside the `server/` directory, you must set the `PYTHONPATH` so that imports work correctly:

```bash
PYTHONPATH=.. celery -A celery_instance.celery_app worker --loglevel=info
```

If you run from the project root (`leadGen/`), use:

```bash
celery -A server.celery_instance.celery_app worker --loglevel=info
```

--- 