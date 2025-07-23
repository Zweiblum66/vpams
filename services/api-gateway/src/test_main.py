"""
Basic test to verify FastAPI Gateway setup
"""

import asyncio
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

# Mock the Redis and service discovery during testing
with patch('core.redis.init_redis', new=AsyncMock()):
    with patch('core.service_discovery.init_service_discovery', new=AsyncMock()):
        from main import app

client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "MAMS API Gateway"
    assert data["version"] == "1.0.0"
    assert data["status"] == "healthy"


def test_health_endpoint():
    """Test health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "MAMS API Gateway"


def test_api_root():
    """Test API root endpoint"""
    response = client.get("/api/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "MAMS API Gateway"
    assert data["api_version"] == "v1"
    assert "available_services" in data


if __name__ == "__main__":
    pytest.main([__file__])