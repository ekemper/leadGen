# Unified Logging in Dockerized LeadGen Application

## Overview

All application logs—including backend (Flask server), worker processes, and frontend browser event logs (sent to the backend)—are now written to **stdout only**. This means:

- All logs are available via Docker's logging system.
- There are no separate log files created by the application inside the containers.
- You can view and collect logs for all services using Docker-native commands.
- This approach unifies application and container logs, making it easier to monitor, aggregate, and forward logs.

---

## How to View Logs

### View All Logs in Real Time
To view logs for all services as they are generated:
```sh
docker-compose logs -f
```

### View Logs for a Specific Service
To view logs for a specific service (e.g., backend):
```sh
docker-compose logs -f backend
```
To view worker logs:
```sh
docker-compose logs -f worker
```

### Collect All Logs to a File
To collect all logs (from all containers) into a single file on the host:
```sh
docker-compose logs --no-color -t > ./logs/combined.log
```

---

## Log Format

- All application logs are in **JSON format** with the following fields:
  - `timestamp`: ISO8601 timestamp of the log entry
  - `level`: Log level (e.g., INFO, ERROR)
  - `message`: Log message
  - `source`: Source of the log (e.g., backend, worker, browser)
  - `component`: Application component (e.g., auth_service, event_service)
- Docker logs from other containers (Redis, Postgres, Nginx, etc.) are in their default format.

---

## Why Use stdout-Only Logging?

- **Unified view:** All logs (application and container) are available in one place.
- **Easy aggregation:** You can forward or process logs using Docker-native tools or external log shippers.
- **No need to manage log files or rotation inside containers.**
- **Production best practice:** This approach is recommended for containerized applications and works seamlessly with log aggregation platforms (ELK, Loki, Datadog, etc.).

---

## Example: Log Entry

A typical application log entry (as seen in `docker-compose logs`):
```json
{"timestamp": "2025-05-20T13:16:25.897615", "level": "INFO", "name": "app", "message": "Centralized logger initialized", "source": "app", "component": "app"}
```

---

## Migrating from File-Based Logging

- All previous references to log files like `server.log`, `worker.log`, `browser.log`, or `combined.log` are obsolete.
- All logging is now handled via stdout and Docker's logging system.
- If you need to collect logs into a file, use the Docker command above to redirect logs to a file on the host.

---

## Troubleshooting

- If you do not see logs, ensure your containers are running and that you are using the correct Docker Compose project.
- For more advanced log aggregation, consider using a log shipper (e.g., Fluentd, Filebeat) to forward Docker logs to your preferred log management platform.

--- 