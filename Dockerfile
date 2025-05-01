# Base stage for shared dependencies
FROM python:3.9-slim as base

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        python3-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Development stage
FROM base as development
ENV FLASK_ENV=development \
    FLASK_DEBUG=1

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user but allow write permissions for development
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Production stage
FROM base as production
ENV FLASK_ENV=production

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY server/ .

# Create non-root user for security
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose port (Heroku will override this with $PORT)
EXPOSE 5000

# Run the application using Heroku's $PORT
CMD gunicorn --bind 0.0.0.0:$PORT app:app 