# Testing in fastapi-k8-proto

This project supports two main methods for running tests in Docker:

- **Isolated, production-like testing with `scripts/test-docker.sh`**
- **Quick development testing with `make docker-test`**

Below you'll find a detailed explanation of each method, their purposes, usage instructions, and when to use which.

---

## 1. Isolated, Production-like Testing: `scripts/test-docker.sh`

### **Purpose**
- Runs tests in a clean, isolated Docker Compose environment using `docker/docker-compose.test.yml`.
- Ensures all dependencies (Postgres, Redis) are started fresh for each test run.
- Runs Alembic migrations before tests.
- Generates a coverage report (`htmlcov/index.html`).
- Cleans up all containers and volumes after the run.
- Mimics a CI or production environment for robust, repeatable test results.

### **Usage**
```bash
./scripts/test-docker.sh
```

### **What Happens**
1. Builds and starts `test-db`, `test-redis`, and `test-runner` containers.
2. The `test-runner` waits for the database and Redis to be ready.
3. Runs Alembic migrations.
4. Runs all tests with coverage.
5. Outputs a coverage report to `htmlcov/index.html`.
6. Cleans up all containers and volumes.

### **When to Use**
- Before merging code (pre-commit/CI checks).
- When you want a clean slate for every test run.
- To ensure migrations and dependencies are correct.
- When you need a coverage report.
- For debugging issues that may be caused by leftover data or state.

---

## 2. Quick Development Testing: `make docker-test`

### **Purpose**
- Runs tests inside the existing `api` service container using the main `docker/docker-compose.yml`.
- Fast feedback loop for development.
- Uses the current state of your dev containers and volumes.
- Does **not** run Alembic migrations or generate a coverage report by default.

### **Usage**
```bash
make docker-test
```

### **What Happens**
1. Calls `./scripts/docker-dev.sh test`, which runs:
   ```bash
   cd docker && docker compose run --rm api pytest tests/ -v
   ```
2. Spins up a new `api` container (with the current code) and runs tests.
3. Uses the existing dev database and Redis containers (and their data).
4. Cleans up only the test container after the run.

### **When to Use**
- For quick, iterative development and testing.
- When you want to test code changes without resetting the environment.
- When you don't need a coverage report or to run migrations every time.
- For local development convenience.

---

## Comparison Table

| Feature                | `test-docker.sh` (test stack) | `make docker-test` (dev stack) |
|------------------------|:-----------------------------:|:------------------------------:|
| Isolated test DB/Redis | Yes                           | No                             |
| Runs migrations        | Yes                           | No                             |
| Coverage report        | Yes                           | No (unless added)              |
| Cleans up everything   | Yes                           | No                             |
| Fast for dev           | No (slower, full stack)       | Yes                            |
| CI/Prod-like           | Yes                           | No                             |

---

## Recommendations
- Use `./scripts/test-docker.sh` for CI, pre-merge, or when you need a clean, production-like test run.
- Use `make docker-test` for fast, local development testing.
- Both methods are valuable for different stages of development. Choose the one that fits your workflow.

---

## Troubleshooting
- If you encounter issues with services not being ready, ensure Docker is running and ports are not in use.
- For persistent errors, try cleaning up with `make docker-clean` or restarting Docker.
- Coverage reports are available in `htmlcov/index.html` after running `test-docker.sh`.

---

For further details, see the scripts and Docker Compose files referenced above, or ask your team for workflow recommendations. 