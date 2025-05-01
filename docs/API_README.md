# API Documentation

## Base URL
```
Development: http://localhost:5000/api
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

## Error Responses
All error responses follow this format:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": {} // Optional additional information
  }
}
```

Common Error Codes:
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `429`: Too Many Requests
- `500`: Internal Server Error

## Data Models

### Lead
```json
{
  "id": "uuid",
  "name": "string",
  "email": "string",
  "company": "string",
  "phone": "string",
  "status": "enum(new, contacted, qualified, lost)",
  "source": "string",
  "notes": "string",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

## Webhooks
Webhooks are available for real-time notifications of lead updates.

### Configuration
POST /webhooks/configure
```json
{
  "url": "https://your-server.com/webhook",
  "events": ["lead.created", "lead.updated", "lead.deleted"],
  "secret": "your_webhook_secret"
}
```

## Best Practices
1. Always validate request data
2. Use appropriate HTTP methods
3. Include error handling
4. Implement rate limiting
5. Use pagination for large datasets
6. Keep endpoints versioned
7. Use HTTPS in production
8. Implement proper authentication 