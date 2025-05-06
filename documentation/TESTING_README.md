# Testing Guide

## Prerequisites
- Python 3.9+
- All backend dependencies installed (see requirements.txt)

## Running Tests

1. Activate your virtual environment:
   ```bash
   source venv/bin/activate
   ```
2. Run the test suite:
   ```bash
   pytest
   ```

## Notes
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
│   │   ├── test_models.py
│   │   ├── test_utils.py
│   │   └── test_services.py
│   ├── integration/
│   │   ├── test_api.py
│   │   └── test_database.py
│   └── conftest.py
```

### Running Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_models.py

# Run with coverage report
pytest --cov=app tests/

# Generate HTML coverage report
pytest --cov=app --cov-report=html tests/
```

### Test Database
- Uses SQLite for testing
- Automatically sets up and tears down test database
- Migrations are applied before tests run

### Mocking
- External API calls should be mocked
- Use `pytest-mock` for mocking
- Example:
```python
def test_external_api(mocker):
    mock_response = mocker.patch('requests.get')
    mock_response.return_value.json.return_value = {'data': 'test'}
    # Test implementation
```

## Frontend Testing

### Setup
```bash
cd frontend
npm install
```

### Test Structure
```
frontend/
├── tests/
│   ├── unit/
│   │   ├── components/
│   │   ├── hooks/
│   │   └── utils/
│   ├── integration/
│   │   └── flows/
│   └── setup.ts
```

### Running Tests
```bash
# Run all tests
npm test

# Run specific test file
npm test -- components/Button.test.tsx

# Run with coverage
npm test -- --coverage

# Watch mode
npm test -- --watch
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

### Integration Testing
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