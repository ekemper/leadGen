# API Documentation

> For setup, environment variables, and how to run the backend, see the main `README.md` in the project root.

## Environment Setup
1. Create a Python virtual environment:
```bash
python -m venv venv
```

2. Activate the virtual environment:
- On Linux/macOS:
```bash
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Base URL
```
Development: http://localhost:5001/api
Production: https://[your-app].herokuapp.com/api
```

## Authentication
All authenticated endpoints require a JWT token in the Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

## Rate Limiting
- 100 requests per minute for authenticated users
- 20 requests per minute for unauthenticated users

## Endpoints

### Authentication

#### POST /auth/register
Create a new user account.
```json
{
  "email": "user@example.com",
  "password": "securepassword",
  "name": "John Doe"
}
```

#### POST /auth/login
Login and receive JWT token.
```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```

### Leads

#### GET /leads
Get all leads for authenticated user.

Query Parameters:
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 20)
- `sort`: Sort field (default: "created_at")
- `order`: Sort order ("asc" or "desc")

#### POST /leads
Create a new lead.
```json
{
  "name": "John Smith",
  "email": "john@company.com",
  "company": "Tech Corp",
  "phone": "+1234567890",
  "status": "new",
  "source": "website"
}
```

#### GET /leads/{id}
Get specific lead by ID.

#### PUT /leads/{id}
Update a lead.
```json
{
  "status": "contacted",
  "notes": "Follow up scheduled"
}
```

#### DELETE /leads/{id}
Delete a lead.

### Analytics

#### GET /analytics/leads
Get lead statistics.

Query Parameters:
- `start_date`: Start date (YYYY-MM-DD)
- `end_date`: End date (YYYY-MM-DD)
- `group_by`: Group by field ("source", "status", "date")

### Scraping

#### POST /scrape
Scrape content from a provided URL.

Request body:
```json
{
  "url": "https://example.com"
}
```

Response:
```json
{
  "success": true,
  "data": {
    "text_content": "string",
    "title": "string",
    "metadata": {},
    "links": [],
    "tables": []
  },
  "file_location": "temp_scrape_results.json"
}
```

Example usage:
```bash
curl -X POST http://localhost:5000/api/scrape \
     -H "Content-Type: application/json" \
     -d '{"url": "https://example.com"}'
```

## Error Responses
All error responses follow this format:
```