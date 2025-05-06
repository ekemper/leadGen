# Deployment Guide

This project is now intended to be run and deployed without Docker or containers.

## Prerequisites
- Python 3.9+
- Node.js 20.x

## Backend Deployment
1. Set up a Python virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set environment variables as needed (see `.env` example).
4. Run database migrations:
   ```bash
   flask db upgrade
   ```
5. Start the Flask app:
   ```bash
   flask run --port 5001
   ```

## Frontend Deployment
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Build the frontend:
   ```bash
   npm run build
   ```
4. Serve the static files using your preferred web server or hosting platform.

## Production Notes
- Set all environment variables to production values.
- Use a production-ready WSGI server (e.g., gunicorn) for Flask in production.
- Use a reverse proxy (e.g., nginx) if needed.

---

All Docker, container, and cloud container registry instructions have been removed. Use standard Python and Node.js deployment practices. 