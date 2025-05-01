# Testing Documentation

## Overview
This document outlines the testing strategy and procedures for both frontend and backend components of the Lead Generation application.

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
Using Cypress:
```bash
# Open Cypress
npm run cypress:open

# Run Cypress tests headlessly
npm run cypress:run
```

## E2E Testing

### Setup
```bash
npm install -g cypress
```

### Running E2E Tests
```bash
# Start the application
docker-compose up -d

# Run E2E tests
cypress run
```

### Test Structure
```
cypress/
├── e2e/
│   ├── auth.cy.ts
│   ├── leads.cy.ts
│   └── analytics.cy.ts
├── fixtures/
│   └── testData.json
└── support/
    └── commands.ts
```

## CI/CD Integration

### GitHub Actions
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run backend tests
        run: |
          cd server
          python -m pytest
      - name: Run frontend tests
        run: |
          cd frontend
          npm test
```

## Best Practices

### General
1. Write tests before fixing bugs
2. Keep tests focused and atomic
3. Use meaningful test descriptions
4. Clean up test data
5. Don't test implementation details

### Backend
1. Use fixtures for test data
2. Test edge cases
3. Validate database state
4. Mock external services
5. Test error conditions

### Frontend
1. Test user interactions
2. Test accessibility
3. Test responsive behavior
4. Mock API calls
5. Test error states

## Performance Testing

### Tools
- k6 for API load testing
- Lighthouse for frontend performance
- New Relic for monitoring

### Example k6 Test
```javascript
import http from 'k6/http'
import { check } from 'k6'

export default function() {
  const res = http.get('http://localhost:5000/api/leads')
  check(res, {
    'status is 200': (r) => r.status === 200
  })
}
``` 