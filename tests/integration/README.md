# MAMS Integration Tests

This directory contains integration tests that verify the interaction between multiple microservices in the MAMS platform.

## Overview

Integration tests are designed to test complete user workflows and verify that services work correctly together. They differ from unit tests by:

- Testing actual service interactions over the network
- Using real databases and message queues
- Verifying end-to-end functionality
- Testing complex workflows across multiple services

## Test Structure

```
tests/integration/
├── conftest.py                      # Shared fixtures and configuration
├── run_integration_tests.py         # Test runner script
├── test_user_asset_flow.py         # User and asset management flow
├── test_workflow_execution_flow.py  # Workflow engine integration
├── test_search_integration.py       # Search functionality across services
└── README.md                        # This file
```

## Prerequisites

1. **Docker and Docker Compose**: All services run in containers
2. **Python 3.11+**: For running the test suite
3. **Services**: The microservices should be built and ready to run

## Running Tests

### Quick Start

```bash
# Run all integration tests
./run_integration_tests.py

# Run with coverage
./run_integration_tests.py --coverage

# Run specific test file
./run_integration_tests.py --test test_user_asset_flow.py

# Keep services running after tests
./run_integration_tests.py --keep-services

# Run tests in parallel
./run_integration_tests.py --parallel 4
```

### Manual Setup

If you prefer to manage services manually:

```bash
# Start all services
docker-compose up -d

# Run tests without service management
./run_integration_tests.py --no-services

# Or use pytest directly
pytest tests/integration -m integration -v
```

## Test Categories

### 1. User Asset Flow (`test_user_asset_flow.py`)
Tests the complete lifecycle of user registration, authentication, and asset management:
- User registration and login
- Asset upload with metadata
- Asset search and retrieval
- Asset versioning
- Permission checks

### 2. Workflow Execution (`test_workflow_execution_flow.py`)
Tests workflow engine integration:
- Media processing workflows
- Approval workflows with human tasks
- Scheduled workflow execution
- Error handling and retries

### 3. Search Integration (`test_search_integration.py`)
Tests search functionality across services:
- Full-text search in content and metadata
- Advanced filters and facets
- Natural language search
- Saved searches
- Search suggestions

## Writing New Integration Tests

### 1. Create a new test file:

```python
#!/usr/bin/env python3
"""
Integration Test: Your Feature

Description of what this integration test covers.
"""

import pytest
import httpx

class TestYourFeature:
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_your_workflow(self, auth_headers):
        """Test description."""
        async with httpx.AsyncClient() as client:
            # Your test implementation
            pass
```

### 2. Use provided fixtures:

- `auth_headers`: Authenticated request headers
- `test_project`: A test project for organizing assets
- `wait_for_services`: Ensures all services are healthy
- `cleanup_test_data`: Tracks and cleans up test data

### 3. Follow best practices:

- Use descriptive test names
- Clean up created resources
- Handle async operations properly
- Add appropriate markers (`@pytest.mark.integration`)
- Include timeout handling for long operations

## Environment Variables

Configure service URLs if running on non-default ports:

```bash
export API_GATEWAY_URL=http://localhost:8000
export USER_SERVICE_URL=http://localhost:8001
export ASSET_SERVICE_URL=http://localhost:8002
# ... etc
```

## CI/CD Integration

The integration tests are designed to work in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run Integration Tests
  run: |
    ./tests/integration/run_integration_tests.py \
      --junit \
      --coverage \
      --parallel 4
```

Test results are saved as:
- `integration_test_results.xml` - JUnit format for CI systems
- `integration_test_summary.json` - JSON summary
- `htmlcov_integration/` - HTML coverage report

## Troubleshooting

### Services not starting
```bash
# Check service logs
docker-compose logs service-name

# Verify services are healthy
curl http://localhost:8000/health
```

### Tests timing out
- Increase timeout in httpx.AsyncClient
- Check if services are overloaded
- Verify network connectivity

### Cleanup issues
```bash
# Manual cleanup of test data
docker-compose down -v
docker system prune -f
```

## Performance Considerations

- Integration tests are slower than unit tests
- Use `--parallel` flag to speed up execution
- Consider using test data factories for faster setup
- Mock external services when possible

## Future Improvements

1. Add performance benchmarking to integration tests
2. Implement test data seeding for complex scenarios
3. Add visual regression testing for UI components
4. Create integration tests for mobile app APIs
5. Add chaos testing scenarios