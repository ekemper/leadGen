# Base stage for shared dependencies
FROM python:3.9-slim as base

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

# Copy only requirements first for better caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Development stage
FROM base as development
ENV FLASK_ENV=development \
    FLASK_DEBUG=1 \
    PYTHONPATH=/app

# Copy the rest of the code (this is the layer that changes most during dev)
COPY . /app

RUN chmod +x /app/server/startup.sh
RUN ls -l /app

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 5001

CMD ["/app/server/startup.sh"]

# Production stage
FROM base as production
ENV FLASK_ENV=production \
    PYTHONPATH=/app

COPY . /app

RUN chmod +x /app/server/startup.sh
RUN ls -l /app

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 5001

CMD ["/app/server/startup.sh"] 