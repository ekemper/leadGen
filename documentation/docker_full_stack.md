# Full Stack Docker Deployment Guide

This guide explains how to run the entire application stack—backend (Flask API), worker, frontend (Nginx), and Redis—using Docker Compose.

---

## Architecture Overview

- **backend**: Flask API server (Python)
- **worker**: Background job processor (Python)
- **frontend**: Static frontend (built with Node, served by Nginx)
- **redis**: Message broker for background jobs

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- `.env` file at the project root (copy from `example.env` and adjust as needed)

---

## Environment Variables

- The backend and worker both use the same `.env` file.
- **Important:** Set `REDIS_HOST=redis` in your `.env` for container-to-container communication.

---

## Building and Running the Stack

1. **Build and start all services:**
   ```sh
   docker compose up --build
   ```
   - This will build images for backend, worker, and frontend, and start Redis.
   - Logs from all services will be shown in your terminal.

2. **Run in the background:**
   ```sh
   docker compose up -d
   ```

3. **Stop all services:**
   ```sh
   docker compose down
   ```

---

## Service URLs

- **Frontend (Nginx):** [http://localhost/](http://localhost/)
- **Backend (Flask API):** [http://localhost:5001/](http://localhost:5001/)
- **Redis:** localhost:6379 (for debugging/inspection)

---

## How It Works

- The frontend is built with Node, then served as static files by Nginx.
- The backend and worker both connect to Redis using the hostname `redis`.
- The worker processes background jobs enqueued by the backend.

---

## Troubleshooting

- **Frontend not updating after code changes:**
  - Rebuild the frontend service: `docker compose build frontend`
- **Backend/worker can't connect to Redis:**
  - Ensure `REDIS_HOST=redis` in your `.env`.
- **Port conflicts:**
  - Make sure ports 80 (frontend), 5001 (backend), and 6379 (Redis) are free.
- **Dependency changes:**
  - Rebuild affected services after changing `requirements.txt` or `package.json`.

---

## Advanced

- To view logs for a specific service:
  ```sh
  docker compose logs backend
  docker compose logs worker
  docker compose logs frontend
  docker compose logs redis
  ```
- To rebuild only one service:
  ```sh
  docker compose build backend
  ```

---

## Summary

- Use `docker compose up --build` for a one-command, production-like local environment.
- All services are isolated, reproducible, and easy to manage.
- For any issues, check logs and ensure your `.env` is correct. 