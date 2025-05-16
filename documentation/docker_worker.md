# Running the Worker Process with Docker

This guide explains how to run the background worker process in a Docker container, isolating it from macOS-specific issues and ensuring a consistent, production-like environment.

---

## Preferred Method: Using Docker Compose

The recommended way to run the worker is with Docker Compose, which automatically starts both the worker and a Redis service. This ensures reliable connectivity and simplifies environment management.

### 1. Compose File

The `docker-compose.worker.yml` file is provided at the project root:

```yaml
version: '3.8'
services:
  worker:
    build:
      context: .
      dockerfile: Dockerfile.worker
    env_file: .env
    depends_on:
      - redis
    restart: unless-stopped
  redis:
    image: redis:7
    ports:
      - "6379:6379"
    restart: unless-stopped
```

### 2. How to Use

1. **Ensure your `.env` file is present at the project root.**
2. **Start the worker and Redis:**
   ```sh
   docker compose -f docker-compose.worker.yml up
   ```
   - This will build the worker image if needed and start both services.
   - Logs from both the worker and Redis will be shown in your terminal.
3. **To run in the background:**
   ```sh
   docker compose -f docker-compose.worker.yml up -d
   ```
4. **To stop the services:**
   ```sh
   docker compose -f docker-compose.worker.yml down
   ```

### 3. Environment Variables
- The worker will use the `.env` file for configuration.
- Redis will be available at `redis://redis:6379/0` inside the worker container (set `REDIS_HOST=redis` in your `.env`).

---

## Why Use Docker Compose?

- **Automatic Service Discovery:** The worker can always reach Redis at the hostname `redis`.
- **Simplified Startup:** One command starts both services.
- **Consistent Environment:** Matches production-like deployment.
- **Easy Cleanup:** One command stops and removes all containers.

---

## Manual Docker Usage (Alternative)

You can still build and run the worker manually, but you must ensure Redis is running and accessible (see previous section for details).

---

## Troubleshooting

- **Worker Crashes on macOS:**
  - This is often due to low-level threading or binary incompatibilities. Running in Docker (Linux) resolves these issues.
- **Cannot Connect to Redis:**
  - Ensure your `.env` has `REDIS_HOST=redis` when using Compose.
- **Environment Variables Not Loaded:**
  - Always use `--env-file .env` or set variables with `-e` flags.
- **Dependency Issues:**
  - Rebuild the image after changing `requirements.txt`.

---

## Summary

- **Use `docker compose -f docker-compose.worker.yml up` for the easiest, most reliable local worker setup.**
- **This approach ensures Redis is always available and environment variables are managed cleanly.**
- **For local services, use the service name (e.g., `redis`) as the hostname in your `.env`.**

If you encounter issues not covered here, check the logs and ensure all environment variables and services are correctly configured. 