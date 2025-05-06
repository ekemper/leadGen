#!/bin/sh
set -e

# Truncate the log file at startup
: > /app/docker.log

# Wait for the database to be ready
if [ -n "$DB_HOST" ]; then
  echo "Waiting for database at $DB_HOST..."
  until PGPASSWORD=$POSTGRES_PASSWORD psql -h "$DB_HOST" -U "$POSTGRES_USER" -c '\q' 2>/dev/null; do
    >&2 echo "Postgres is unavailable - sleeping"
    sleep 1
  done
  echo "Database is up - running migrations"
else
  echo "DB_HOST not set, skipping DB wait"
fi

export PYTHONPATH=/app
export FLASK_APP=server.app

flask db upgrade

echo "Starting server"
exec gunicorn --bind 0.0.0.0:${PORT:-5001} 'server.app:create_app()' 