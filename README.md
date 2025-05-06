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