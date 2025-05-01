# Auth Template Application

A modern authentication template built with Flask (Backend) and React + Vite (Frontend).

## Features

- Secure user authentication
- Rate limiting
- CORS support
- Email validation
- JSON Web Token (JWT) based authentication
- PostgreSQL database integration
- Modern React frontend

## Prerequisites

- Docker and Docker Compose
- Node.js 20.x (for local development without Docker)
- Python 3.9+ (for local development without Docker)

## Project Structure

```
auth-template/
├── api/            # Backend API modules
├── config/         # Configuration files
├── frontend/       # React + Vite frontend
├── tests/         # Test files
└── utils/         # Utility functions
```

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
FLASK_DEBUG=1
SECRET_KEY=your-secret-key-here
ALLOWED_ORIGINS=http://localhost:3000
DATABASE_URL=sqlite:///app.db
```

## Running with Docker (Recommended)

1. Build and start the containers:
   ```bash
   docker-compose up --build
   ```

2. Access the applications:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:5001

3. Stop the containers:
   ```bash
   docker-compose down
   ```

## Running Locally (Without Docker)

### Backend Setup

1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the Flask application:
   ```bash
   flask run --port 5001
   ```

### Database Migrations

The application uses Flask-Migrate for database migrations. Here are the key commands:

1. Initialize migrations (first time only):
   ```bash
   flask db init
   ```

2. Create a new migration:
   ```bash
   flask db migrate -m "Description of the changes"
   ```

3. Apply migrations:
   ```bash
   flask db upgrade
   ```

4. Reverse migrations:
   ```bash
   flask db downgrade
   ```

Note: Make sure to set the `FLASK_APP=migrations.py` environment variable before running migration commands.

### Frontend Setup

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

## Testing

Run the test suite:
```bash
pytest
```

## API Endpoints

### Authentication Endpoints

- `POST /api/auth/signup`: Register a new user
  - Required fields: email, password, confirm_password
  - Returns: User registration confirmation

- `POST /api/auth/login`: Login user
  - Required fields: email, password
  - Returns: JWT access token

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

## Production Deployment

For production deployment:

1. Update environment variables with production values
2. Build production images:
   ```bash
   docker-compose -f docker-compose.prod.yml build
   ```
3. Deploy using your preferred hosting service

## Troubleshooting

1. If the frontend can't connect to the backend:
   - Check if both services are running
   - Verify CORS settings in backend
   - Check if VITE_API_URL is correctly set

2. If containers fail to start:
   - Check if ports 3000 and 5001 are available
   - Verify environment variables
   - Check Docker logs: `docker-compose logs`

## License

[Your License Here]

## Contributing

[Your Contributing Guidelines]