# Test Commands

Run comprehensive tests for all COTAI services.

## Usage
`/test` - Run all tests
`/test backend` - Run backend tests only
`/test frontend` - Run frontend tests only
`/test integration` - Run integration tests
`/test coverage` - Run tests with coverage reports
`/test specific <pattern>` - Run specific test files

## Commands Executed

### Run All Tests
```bash
# Backend tests
cd backend && poetry shell && pytest

# Frontend tests  
cd frontend && npm test -- --watchAll=false

# Go service tests
cd services/go-pdf-processor && go test ./...

# Rust service tests
cd services/security-rust && cargo test
```

### Backend Tests Only
```bash
cd backend
poetry shell
pytest
pytest -v
pytest tests/test_specific.py -v
pytest -k "test_function_name"
```

### Frontend Tests Only
```bash
cd frontend
npm test -- --watchAll=false
npm test -- --coverage
```

### Integration Tests
```bash
cd backend
poetry shell
pytest tests/integration/
```

### Coverage Reports
```bash
# Backend coverage
cd backend && poetry shell && pytest --cov=app tests/

# Frontend coverage
cd frontend && npm test -- --coverage --watchAll=false
```

### Specific Test Pattern
```bash
# Backend specific tests
cd backend && poetry shell && pytest tests/test_auth.py -v

# Frontend specific tests
cd frontend && npm test -- --testNamePattern="UserAuth" --watchAll=false
```

## Test Results
- Backend: pytest output with coverage
- Frontend: Jest test results with coverage
- Integration: Full stack test results
- Services: Go and Rust test outputs