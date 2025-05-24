# LeadGen Application

A modern lead generation platform with a Flask backend and React + Vite frontend.

## Features

- Secure user authentication
- Rate limiting
- CORS support
- Email validation
- JSON Web Token (JWT) based authentication
- PostgreSQL database integration
- Modern React frontend

## Prerequisites

- Python 3.9+
- Node.js 20.x+
- PostgreSQL 13+ (for production/local DB)

## Project Structure

```
leadGen/
├── server/         # Flask backend
├── frontend/       # React + Vite frontend
├── config/         # Shared configuration
├── documentation/  # Project documentation
├── migrations/     # Database migrations
├── logs/           # Log files
└── ...
```

## Environment Variables

- Copy `example.env` to `.env` and fill in secrets and DB connection info.
- Key variables: `DATABASE_URL`, `SECRET_KEY`, `ALLOWED_ORIGINS`, `FLASK_ENV`, `FLASK_DEBUG`, etc.

## Running the Application

### Backend (Flask API)
1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r server/requirements.txt
   ```
3. Run database migrations:
   ```bash
   flask db upgrade
   ```
4. Start the backend server:
   ```bash
   python server/app.py
   ```
   - Runs on port 5001 by default.
   - For production, use a WSGI server like gunicorn.

### Frontend (React + Vite)
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```
   - Runs on port 5173 by default.
   - For production, build with `npm run build` and serve the static files.

## Database
- Uses PostgreSQL in production, SQLite for tests.
- Migrations managed with Flask-Migrate:
  - `flask db migrate -m "message"`
  - `flask db upgrade`
- See `documentation/DATABASE_README.md` for advanced DB setup and management.

## Database Management (Unified)

Use the unified script for all local database reset, migration, and seeding tasks:

### Full Reset, Migrate, and Seed
```sh
python3 scripts/reset_and_seed.py --force
```

### Full Reset, Fresh Migrations, and Seed
```sh
python3 scripts/reset_and_seed.py --force --fresh-migrations
```

### Seed Only (no reset or migration)
```sh
python3 scripts/reset_and_seed.py --seed-only
```

**WARNING:** The `--force` flag is required for destructive actions. You will be prompted for confirmation.

### Deprecated Scripts
- `scripts/full_db_reset.py` (use `reset_and_seed.py` instead)
- `scripts/reset_migrate_seed.py` (seeding logic is now imported only)
- `scripts/seed_only.py` (use `reset_and_seed.py --seed-only`)
- `scripts/condense_migrations.py` (use `reset_and_seed.py --force --fresh-migrations`)

Please update any documentation or automation to use `reset_and_seed.py`.

## Database Management with Docker Compose (Local Development)

If you are running the application using Docker Compose, you should run the reset and seed script inside the backend container to ensure it connects to the database service correctly.

### Full Reset, Migrate, and Seed (Docker Compose)
```sh
docker compose run --rm backend python scripts/reset_and_seed.py
```

- This command will:
  - Reset the database (all data will be lost)
  - Apply all migrations
  - Seed the database with initial data
- You will be prompted for confirmation before destructive actions.
- Make sure your Docker Compose services are up (especially `db` and `backend`).

### Notes
- The script uses the `DATABASE_URL` from your `.env` file, which should point to the `db` service (e.g., `postgresql://myuser:mypassword@db:5432/mydb`).
- If you want to run the script from your host machine, you must update the `DATABASE_URL` to use `localhost` instead of `db`, or use an override as described in the script.
- For advanced options (fresh migrations, seed only), you can append flags as described above.

**WARNING:** This process is destructive and will delete all data in your database!

## Testing
- **Backend:** Run `pytest` in the project root (ensure venv is active).
- **Frontend:** Run `npm test` in the `frontend` directory.

## Production Deployment
- Use a production WSGI server (e.g., gunicorn) for Flask.
- Serve frontend static files with a web server (nginx, Vercel, Netlify, etc.).
- Set all environment variables to production values.

## Notes
- No Docker or container setup is required or supported.
- All CORS and session settings are managed via environment variables and `config/settings.py`.
- API base URL (dev): `http://localhost:5001/api`
- Frontend dev URL: `http://localhost:5173`

## Development Notes

- The backend runs on port 5001 to avoid conflicts with the frontend development server
- Frontend development server runs on port 3000
- API requests from frontend are proxied to the backend
- Hot reloading is enabled for both frontend and backend in development mode

## Security Features

- Password hashing with bcrypt
- JWT-based authentication
- Rate limiting
- CORS protection
- HTTP-only cookies
- Session security
- Account lockout after multiple failed login attempts

## License

[Your License Here]

## Contributing

[Your Contributing Guidelines]

## Logging and Observability

### Central logger + shared `combined.log`

Every Python process in LeadGen bootstrap's the same logger defined in `server/utils/logging_config.py`.  Two destinations are wired by default:

1. **stdout** — visible with Docker commands such as `docker compose logs -f`.
2. **`logs/combined.log`** — a host-side, 10 MiB rolling file that aggregates entries from _all_ containers.

This dual sink gives you real-time streaming in the terminal **and** a persistent history for grepping or shipping to ELK/Loki.

```sh
# live tail across stack
docker compose logs -f

# inspect only backend entries from the file
jq 'select(.name | test("^server"))' logs/combined.log | less -R
```

#### Log format (JSON-lines)

Key fields: `timestamp`, `level`, `name`, `message`, `source`, `component`.  Sensitive data is redacted automatically.

#### Override log level

Set `LOG_LEVEL=DEBUG` in your environment or `docker-compose.override.yml` to increase verbosity.

---