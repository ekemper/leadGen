# LeadGen Logging — 2025-05 overhaul

This document describes the **single-source, structured logging** used throughout the LeadGen stack after the 2025-05 consolidation.

## Quick facts

• Every Python process (Flask API, RQ worker, ad-hoc scripts) uses the same logging bootstrap in `server/utils/logging_config.py`.
• Two handlers are attached to the **root logger**:
  1. `StreamHandler` → `stdout` (picked up by Docker ‑ view with `docker compose logs`).
  2. `RotatingFileHandler` → `logs/combined.log` (shared bind-mount across containers, 10 MiB × 5 files).
• Log entries are JSON lines with mandatory keys:

| key        | description                     |
|------------|---------------------------------|
| timestamp  | ISO-8601 in UTC                 |
| level      | INFO, ERROR, …                  |
| name       | `logger.name`                   |
| message    | human-readable text             |
| source     | same as `name` unless overridden|
| component  | optional subsystem tag          |

• Sensitive data (emails, tokens, passwords, etc.) is **redacted automatically** by a `SanitizingFilter` before the record is serialised.
• Noise from `werkzeug`, `flask_limiter`, `sqlalchemy.engine`, and `sqlalchemy.pool` is reduced to WARNING/ERROR.

## Using the logger in code

```python
from server.utils.logger import get_logger

logger = get_logger(__name__)

logger.info("User logged in", extra={"component": "auth_service"})
logger.error("Database timeout", exc_info=True)
```

Why `get_logger()`? Importing that helper guarantees that logging is **initialised once** (idempotently) before you obtain the logger.

### Do **not**

* call `logging.basicConfig()` — it would clobber the global configuration;
* write your own `FileHandler` — use `extra={"component": …}` instead for categorisation;
* litter production code with `print()`; use the logger.

## Viewing logs

### Tail live logs from all containers

```sh
docker compose logs -f
```

### View only backend (Flask) logs

```sh
docker compose logs -f backend
```

### Inspect the shared file on the host

```sh
tail -F logs/combined.log | jq .
```

The file is rotated automatically once it reaches 10 MiB (`combined.log.1`, …, `combined.log.5`).

## Environment variables

* `LOG_LEVEL` — overrides the default level (INFO) for all handlers, e.g. `LOG_LEVEL=DEBUG` in `docker-compose.override.yml`.

## Migrating old code / docs

Legacy references to module-specific files such as `server.log`, `worker.log`, `browser.log`, or guidance that claimed "stdout-only logging" have been removed.  If you spot such text, update it to match the above rules.

## Extending

Want to ship logs to ELK, Loki, Datadog, etc.? Point a side-car (Fluent-Bit, Vector) at **either** `stdout` **or** `logs/combined.log` — both contain the same JSON lines. 