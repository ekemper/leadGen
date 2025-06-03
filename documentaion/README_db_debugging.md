# Database Connection Debugging Guide (Docker Compose)

This guide provides a systematic approach to debugging database connection issues in containerized environments, especially when using Docker Compose with services like FastAPI, Celery, and PostgreSQL. Follow each step, run the provided commands, and carefully parse the output for errors or warnings.

---

## 1. Reset the Database Volume (If Possible)

**Purpose:** Ensure the database container initializes with the correct user and database. This is often necessary if you see errors about missing users or databases.

**Instructions:**
- Run the following commands to stop all containers and remove the database volume:
  ```sh
  docker-compose down -v
  docker-compose up -d
  ```
- **Warning:** This will delete all data in the database volume. Only do this if you are okay with losing the data.

**What to look for:**
- After running `docker-compose up -d`, check the logs (see Step 5) for messages indicating successful database initialization and user/database creation.
- If errors persist, proceed to the next steps.

---

## 2. Check Connection Strings

**Purpose:** Ensure all services use the correct database connection string.

**Instructions:**
- Locate your environment variables or configuration files (e.g., `.env`, `docker-compose.yml`, or app config files).
- The connection string should follow this format:
  ```
  postgresql://<user>:<password>@<host>:5432/<database>
  ```
- **Apply to Docker Compose:**
  - `<host>` should be the service name of the PostgreSQL container (e.g., `postgres`), **not** `localhost`.
  - Example:
    ```
    DATABASE_URL=postgresql://myuser:mypassword@postgres:5432/mydb
    ```

**What to look for:**
- Typos in variable names or values.
- Mismatched hostnames (e.g., using `localhost` instead of the service name).
- Inconsistent credentials between services and the database container.

---

## 3. Manually Create the User/Database (If Needed)

**Purpose:** If you cannot reset the volume, manually create the required user and database inside the running PostgreSQL container.

**Instructions:**
- Exec into the PostgreSQL container:
  ```sh
  docker-compose exec postgres psql -U postgres
  ```
- In the PostgreSQL shell, run:
  ```sql
  CREATE USER <user> WITH PASSWORD '<password>';
  CREATE DATABASE <database> OWNER <user>;
  ```
  Replace `<user>`, `<password>`, and `<database>` with your actual values.
- Exit the shell with `\q`.

**What to look for:**
- Success messages after each SQL command.
- If you see errors (e.g., user/database already exists), adjust your commands accordingly (e.g., use `ALTER USER` or skip creation).

---

## 4. Check Service Dependencies

**Purpose:** Ensure services start in the correct order and wait for the database to be ready before attempting to connect.

**Instructions:**
- In your `docker-compose.yml`, confirm that API and worker services have:
  ```yaml
  depends_on:
    - postgres
  ```
- **Optional:** Add health checks or use a wait-for-it script to delay service startup until PostgreSQL is ready. Example using [wait-for-it](https://github.com/vishnubob/wait-for-it):
  ```yaml
  command: ["./wait-for-it.sh", "postgres:5432", "--", "your-start-command"]
  ```

**What to look for:**
- Services should not attempt to connect to the database before it is ready.
- If you see connection refused or timeout errors, consider increasing wait times or improving health checks.

---

## 5. Inspect Logs for Errors

**Purpose:** Identify and diagnose connection, authentication, or network issues.

**Instructions:**
- Check logs for each service:
  ```sh
  docker-compose logs api
  docker-compose logs worker
  docker-compose logs postgres
  ```
- Parse the output for:
  - `FATAL` or `ERROR` messages
  - Authentication failures (e.g., `password authentication failed for user`)
  - Connection errors (e.g., `could not connect to server`)
  - Network issues (e.g., `Connection refused`)

**What to look for:**
- The specific error message and which service it comes from.
- Patterns such as repeated authentication failures or network timeouts.
- Any indication that the service is retrying or failing to connect.

---

## 6. Additional Debugging Tips

- **Test connectivity from inside a container:**
  ```sh
  docker-compose exec api bash
  apt-get update && apt-get install -y postgresql-client
  psql -h postgres -U <user> -d <database>
  ```
  - Replace `<user>` and `<database>` with your actual values.
  - Look for successful connection or error messages.

- **Check for port conflicts:**
  ```sh
  lsof -i :5432
  ```
  - Ensure no other service is using the same port on your host.

- **Review Docker Compose and Dockerfiles:**
  - Ensure environment variables are passed correctly.
  - Avoid hardcoded credentials in code or Dockerfiles.

---

## 7. Common Error Patterns and Solutions

| Symptom                                      | Likely Cause                        | Fix/Check                                      |
|-----------------------------------------------|-------------------------------------|------------------------------------------------|
| `Role "myuser" does not exist`                | User not created in DB              | Recreate DB container with correct env, or manually create user |
| `password authentication failed`              | Wrong password or user              | Check `.env` and Docker Compose env vars       |
| `could not connect to server`                 | Wrong host/port, DB not running     | Check service name, port, and DB container logs|
| API/worker container crashes on startup       | DB not ready yet                    | Add `depends_on`, health checks, or wait script|
| Alembic migration fails                       | DB unreachable or permission denied | Check DB connectivity and user permissions     |

---

## 8. When to Ask for Help

If you have followed all steps and still cannot resolve the issue, collect the following information before seeking help:
- The exact error messages from logs
- Your `.env` and `docker-compose.yml` (redact sensitive info)
- The output of `docker-compose ps` and `docker-compose logs postgres`

Share these details with your team or support channel for more targeted assistance.

---

**End of Guide** 