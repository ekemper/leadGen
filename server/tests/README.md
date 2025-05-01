# Testing Documentation

This directory contains the test suite for the authentication service. The tests are written using pytest and cover both functionality and security aspects of the API.

## Directory Structure

```
tests/
├── __init__.py          # Test package initialization
├── conftest.py          # Test fixtures and configuration
├── test_signup.py       # User registration endpoint tests
├── test_login.py        # User authentication endpoint tests
├── test_health.py       # Health check endpoint tests
└── README.md           # This documentation
```

## Running Tests

### Basic Test Execution

Run all tests with verbose output:
```bash
pytest -v
```
Run with log file:
```bash
pytest -v > test_output.log
```

Run tests with coverage report:
```bash
pytest --cov=app
```

### Running Specific Tests

Run tests for a specific endpoint:
```bash
# Signup tests
pytest tests/test_signup.py
# Login tests
pytest tests/test_login.py
# Health check tests
pytest tests/test_health.py
```

Run a specific test:
```bash
pytest tests/test_signup.py::test_signup_success
```

Run tests by marker:
```bash
# Signup tests
pytest -m signup
# Login tests
pytest -m login
# Health check tests
pytest -m health
```

### Test Categories

#### Signup Endpoint Tests (`test_signup.py`)
- Basic functionality:
  - Successful user registration
  - Missing required fields validation
  - Invalid email format handling
  - Password validation (complexity, matching)
  - Duplicate email prevention

- Edge cases:
  - Case-insensitive email handling
  - Email with whitespace
  - Very long inputs
  - Special characters in inputs

#### Login Endpoint Tests (`test_login.py`)
- Basic functionality:
  - Successful login with valid credentials
  - Failed login with wrong password
  - Failed login for non-existent user
  - Invalid JSON payload handling
  - Missing required fields validation

- Edge cases:
  - Case-insensitive email handling
  - Email with whitespace
  - Password with whitespace
  - Very long credentials
  - Special characters in credentials
  - Account lockout after multiple failed attempts
  - Lockout reset after successful login
  - Token expiration verification

#### Health Check Tests (`test_health.py`)
- API availability
- Response format validation

## Test Configuration

### Environment Setup

1. Create a `.env.test` file with test-specific settings:
```env
FLASK_ENV=testing
FLASK_DEBUG=0
SECRET_KEY=test-secret-key
ALLOWED_ORIGINS=http://localhost:5000
RATELIMIT_ENABLED=False
RATELIMIT_STORAGE_URL=memory://
TESTING=True
```

2. The test environment automatically:
   - Disables rate limiting
   - Uses in-memory storage
   - Sets secure defaults for testing

### Test Fixtures

Key fixtures in `conftest.py`:
- `app`: Flask application instance configured for testing
- `client`: Test client for making requests
- `registered_user`: Pre-registered user for login tests

## Adding New Tests

When adding new tests:

1. Add tests to the appropriate endpoint-specific test file
2. Use descriptive test names that indicate the scenario being tested
3. Include both positive and negative test cases
4. Add appropriate assertions for response status and content
5. Document any new fixtures in `conftest.py`
6. Add appropriate markers in `pytest.ini` if needed

Example test structure:
```python
@pytest.mark.signup  # Use appropriate marker
def test_descriptive_name(client, fixture1, fixture2):
    # Setup
    test_data = {...}
    
    # Execute
    response = client.post('/endpoint', json=test_data)
    
    # Assert
    assert response.status_code == expected_status
    assert response.json['key'] == expected_value
```

## Best Practices

1. Keep tests independent and isolated
2. Clean up any test data after each test
3. Use meaningful test data that reflects real-world scenarios
4. Add comments for complex test logic
5. Use appropriate markers for test categorization
6. Keep tests organized by endpoint

## Common Issues and Solutions

1. Rate limiting interfering with tests:
   - Ensure `RATELIMIT_ENABLED=False` in `.env.test`
   - Clear rate limit storage between tests

2. Test database conflicts:
   - Use unique test data for each test
   - Clean up test data in fixture teardown

3. JWT token issues:
   - Verify `SECRET_KEY` is set in test environment
   - Check token expiration settings

## Future Improvements

1. Add integration tests for:
   - Password reset flow
   - Email verification
   - User profile updates

2. Enhance coverage for:
   - Error handling paths
   - Edge cases in input validation
   - Security headers

3. Add performance tests for:
   - Concurrent user registration
   - Login under load
   - Rate limiting effectiveness

## Continuous Integration

For CI environments:
1. Use `pytest.ini` configuration
2. Generate coverage reports
3. Save test artifacts
4. Set appropriate timeouts

## Support

For issues with the test suite:
1. Check this documentation
2. Review test output logs
3. Verify environment configuration
4. Check for recent changes in dependencies 