#!/bin/bash
# Run tests for Rights Management Service

set -e  # Exit on error

echo "Running Rights Management Service Tests"
echo "======================================="

# Set test environment variables
export ENVIRONMENT=test
export DATABASE_URL="postgresql+asyncpg://test_user:test_pass@localhost:5432/test_rights_management"
export JWT_SECRET_KEY="test-secret-key-for-testing"
export LOG_LEVEL=INFO

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install test dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov httpx

# Run tests with coverage
echo ""
echo "Running tests with coverage..."
echo ""

# Run specific test suites
if [ "$1" == "unit" ]; then
    echo "Running unit tests only..."
    pytest tests/test_*_service.py -v --cov=src --cov-report=term-missing
elif [ "$1" == "integration" ]; then
    echo "Running integration tests only..."
    pytest tests/test_*_endpoints.py tests/test_compliance.py tests/test_analytics.py -v --cov=src --cov-report=term-missing
elif [ "$1" == "edge" ]; then
    echo "Running edge case tests only..."
    pytest tests/test_edge_cases.py -v --cov=src --cov-report=term-missing
elif [ "$1" == "specific" ] && [ -n "$2" ]; then
    echo "Running specific test file: $2"
    pytest "tests/$2" -v --cov=src --cov-report=term-missing
else
    echo "Running all tests..."
    pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html
fi

# Generate coverage report
echo ""
echo "Coverage Summary:"
echo "================="
coverage report

# Check coverage threshold
COVERAGE_THRESHOLD=90
COVERAGE_PERCENT=$(coverage report | grep TOTAL | awk '{print $4}' | sed 's/%//')

if [ -n "$COVERAGE_PERCENT" ] && [ "$COVERAGE_PERCENT" -lt "$COVERAGE_THRESHOLD" ]; then
    echo ""
    echo "WARNING: Coverage is below ${COVERAGE_THRESHOLD}% threshold!"
    echo "Current coverage: ${COVERAGE_PERCENT}%"
    exit 1
else
    echo ""
    echo "Coverage meets threshold! Current: ${COVERAGE_PERCENT}%"
fi

echo ""
echo "Tests completed successfully!"
echo ""
echo "HTML coverage report available at: htmlcov/index.html"