# Lead Generation Server

This is the server component of the Lead Generation application. It's built with Flask and provides the backend API services.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp example.env .env
# Edit .env with your configuration
```

4. Initialize the database:
```bash
flask db upgrade
```

5. Run the development server:
```bash
flask run
```

## Project Structure

- `api/` - API endpoints and route handlers
- `migrations/` - Database migration files
- `instance/` - Instance-specific configuration
- `logs/` - Application logs
- `utils/` - Utility functions and helpers
- `models.py` - Database models
- `app.py` - Main application file
- `migrations.py` - Database migration configuration

## Testing

Run tests with:
```bash
pytest
``` 