# Backend Tests

This directory contains all backend unit and integration tests.

## Setup

Install test dependencies:

```bash
cd backend
pip install -r requirements-test.txt
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run with coverage
```bash
pytest --cov=app --cov-report=html --cov-report=term-missing
```

### Run specific test file
```bash
pytest tests/test_async_tasks.py
pytest tests/test_chunking_service.py
pytest tests/test_async_processing.py
```

### Run specific test
```bash
pytest tests/test_async_tasks.py::test_job_service_create_job
```

## Test Structure

- `conftest.py` - Shared fixtures and test configuration
- `test_async_tasks.py` - Unit tests for async task functions
- `test_chunking_service.py` - Unit tests for PDF chunking
- `test_async_processing.py` - Integration tests for async processing
- `test_services.py` - Tests for existing services
- `test_credit_system.py` - Tests for credit system
- `test_p1_features.py` - Tests for P1 features

## Fixtures

Common fixtures available from `conftest.py`:

- `app` - Flask application instance with test config
- `client` - Test client for making requests
- `test_user` - Pre-created test user
- `auth_headers` - Authentication headers for API requests
- `temp_pdf` - Small temporary PDF (10 pages)
- `large_pdf` - Large temporary PDF (100 pages)

## Writing Tests

Example test using fixtures:

```python
def test_something(app, test_user):
    """Test description"""
    with app.app_context():
        # Your test code here
        assert True
```

## Coverage

Generate HTML coverage report:

```bash
pytest --cov=app --cov-report=html
```

View report:
```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## Continuous Integration

Tests are automatically run in CI/CD pipelines. Ensure all tests pass before submitting PRs.

Target coverage: 80%+
