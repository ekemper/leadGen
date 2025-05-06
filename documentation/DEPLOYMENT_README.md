# Deployment Guide

This project is intended to be run and deployed without Docker or containers.

## Prerequisites
- Python 3.9+
- Node.js 20.x+
- PostgreSQL 13+

## Backend Deployment
1. Set up a Python virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r server/requirements.txt
   ```
3. Set environment variables as needed (see `example.env`).
4. Run database migrations:
   ```bash
   flask db upgrade
   ```
5. Start the Flask app:
   ```bash
   python server/app.py
   ```
   - Runs on port 5001 by default.
   - For production, use a WSGI server like gunicorn.

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