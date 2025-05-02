# Lead Generation Server

This is the server component of the Lead Generation application. It's built with Flask and provides the backend API services.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp example.env .env
# Edit .env with your configuration
```

4. Initialize the database:
```bash
flask db upgrade
```

5. Run the development server:
```bash
flask run
```

## Project Structure

- `api/` - API endpoints and route handlers
- `migrations/` - Database migration files
- `instance/` - Instance-specific configuration
- `logs/` - Application logs
- `utils/` - Utility functions and helpers
- `models.py` - Database models
- `app.py` - Main application file
- `migrations.py` - Database migration configuration

## Testing

Run tests with:
```bash
pytest
```

## Celery: Background Task Processing

Celery is used for running background tasks (such as lead fetching and enrichment) asynchronously. It requires a message broker (Redis) and is tightly integrated with the Flask app.

### 1. Install Celery and Redis dependencies

These are already included in `requirements.txt`, but if you need to install them manually:

```bash
pip install celery redis
```

### 2. Ensure Redis is running

Celery uses Redis as the default broker and result backend. You can start Redis locally (default port 6379):

```bash
redis-server
```

If you see an error about port 6379 being in use, stop the existing process or use another port.

### 3. Environment Variables

Celery will use the following environment variables (or their defaults):

- `CELERY_BROKER_URL` (default: `redis://localhost:6379/0`)
- `CELERY_RESULT_BACKEND` (default: `redis://localhost:6379/0`)

You can override these in your `.env` file if needed.

### 4. Start a Celery Worker

From the `server/` directory, run:

```bash
celery -A celery_instance.celery_app worker --loglevel=info
```

- `-A celery_instance.celery_app` tells Celery to use the app instance from `celery_instance.py`.
- `--loglevel=info` gives you useful output.

### 5. Triggering Tasks

Tasks are triggered automatically by the API (e.g., when creating a campaign). You do not need to manually enqueue tasks.

### 6. Troubleshooting

- **Redis connection errors:** Ensure Redis is running and accessible at the configured URL.
- **Import errors:** Make sure you run the worker from the `server/` directory so imports resolve correctly.
- **Port in use:** If Redis fails to start, check for existing processes on port 6379 (`lsof -i :6379`).

For more details, see the Celery and Redis documentation. 