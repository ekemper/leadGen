# Testing Guide

## Prerequisites
- Python 3.11 or higher installed
- All backend dependencies installed (see requirements.txt)
- Node.js 20.x+
- All frontend dependencies installed (see frontend/package.json)

## Running Backend Tests

1. Activate your virtual environment:
   ```bash
   source venv/bin/activate
   ```
2. Run the test suite:
   ```bash
   pytest
   ```

- Ensure your environment variables are set as needed for testing (see `.env`).
- No Docker or container setup is required or supported.

## Backend Testing

### Setup
```bash
cd server
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Test Structure
```
server/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
```

### Running Tests
```bash
pytest
```

### Test Database
- Uses SQLite for testing
- Automatically sets up and tears down test database
- Migrations are applied before tests run

### Mocking
- External API calls should be mocked
- Use `pytest-mock` for mocking

## Frontend Testing

### Setup
```bash
cd frontend
npm install
```

### Running Tests
```bash
npm test
```

### Component Testing
Using React Testing Library:
```typescript
import { render, screen } from '@testing-library/react'
import { Button } from '../components/Button'

test('renders button with text', () => {
  render(<Button>Click me</Button>)
  expect(screen.getByText('Click me')).toBeInTheDocument()
})
```

## E2E Testing

### Setup
```