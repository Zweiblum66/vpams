"""
Tests for health check endpoints
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
import time

from core.health import HealthStatus, ComponentHealth


@pytest.mark.asyncio
async def test_basic_health_check(client: AsyncClient):
    """Test basic health check endpoint"""
    response = await client.get("/health/")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] in ["healthy", "degraded", "unhealthy"]
    assert "timestamp" in data
    assert "version" in data
    assert "environment" in data
    assert "uptime_seconds" in data
    assert "response_time_ms" in data


@pytest.mark.asyncio
async def test_health_check_with_details(client: AsyncClient):
    """Test health check with component details"""
    response = await client.get("/health/?include_details=true")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "components" in data
    assert isinstance(data["components"], list)
    
    # Check for expected components
    component_names = [c["name"] for c in data["components"]]
    assert "database" in component_names
    assert "redis" in component_names
    assert "disk_space" in component_names
    assert "memory" in component_names
    assert "cpu" in component_names


@pytest.mark.asyncio
async def test_health_check_with_dependencies(client: AsyncClient, auth_headers):
    """Test health check with dependency checks"""
    response = await client.get(
        "/health/?check_dependencies=true",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # When dependencies are checked, should have dependencies field
    if "dependencies" in data:
        assert isinstance(data["dependencies"], list)


@pytest.mark.asyncio
async def test_readiness_check_healthy(client: AsyncClient):
    """Test readiness check when service is healthy"""
    response = await client.get("/health/ready")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "ready" in data
    assert "status" in data
    assert "timestamp" in data
    assert "checks" in data


@pytest.mark.asyncio
async def test_readiness_check_unhealthy(client: AsyncClient):
    """Test readiness check when service is unhealthy"""
    # Mock unhealthy components
    with patch('core.health.health_checker.check_health') as mock_check:
        mock_check.return_value = {
            "status": "unhealthy",
            "timestamp": "2024-01-15T10:00:00Z",
            "components": [
                {
                    "name": "database",
                    "status": "unhealthy",
                    "message": "Connection failed"
                }
            ]
        }
        
        response = await client.get("/health/ready")
        
        assert response.status_code == 503
        data = response.json()
        assert data["ready"] is False


@pytest.mark.asyncio
async def test_liveness_check(client: AsyncClient):
    """Test liveness check endpoint"""
    response = await client.get("/health/live")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "alive"
    assert data["service"] == "MAMS API Gateway"
    assert "version" in data
    assert "timestamp" in data
    assert "uptime" in data


@pytest.mark.asyncio
async def test_startup_check(client: AsyncClient):
    """Test startup check endpoint"""
    response = await client.get("/health/startup")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "started"
    assert "timestamp" in data
    assert "version" in data
    assert "environment" in data


@pytest.mark.asyncio
async def test_service_health_status(client: AsyncClient, auth_headers):
    """Test service health status endpoint"""
    response = await client.get("/health/services", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    
    assert "status" in data
    assert "timestamp" in data
    assert "services" in data


@pytest.mark.asyncio
async def test_service_health_without_auth(client: AsyncClient):
    """Test service health endpoint requires authentication"""
    response = await client.get("/health/services")
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_health_metrics(client: AsyncClient):
    """Test health metrics endpoint"""
    response = await client.get("/health/metrics")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "timestamp" in data
    assert "gateway" in data
    assert "redis" in data
    assert "services" in data
    
    # Check service metrics structure
    services = data["services"]
    assert "total_healthy" in services
    assert "total_unhealthy" in services
    assert "total_instances" in services
    assert "by_service" in services


@pytest.mark.asyncio
async def test_diagnostics_requires_admin(client: AsyncClient, auth_headers):
    """Test diagnostics endpoint requires admin permissions"""
    # Regular user should not have access
    response = await client.get("/health/diagnostics", headers=auth_headers)
    
    # Assuming regular test user doesn't have admin permissions
    assert response.status_code in [403, 401]


@pytest.mark.asyncio
async def test_diagnostics_with_admin(client: AsyncClient, admin_headers):
    """Test diagnostics endpoint with admin permissions"""
    response = await client.get("/health/diagnostics", headers=admin_headers)
    
    assert response.status_code == 200
    data = response.json()
    
    assert "status" in data
    assert "configuration" in data
    assert "performance" in data
    assert "errors" in data
    assert "connections" in data


@pytest.mark.asyncio
async def test_health_history(client: AsyncClient, auth_headers):
    """Test health history endpoint"""
    response = await client.get("/health/history?hours=24", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    
    assert "requested_hours" in data
    assert data["requested_hours"] == 24
    assert "data_points" in data
    assert "summary" in data


@pytest.mark.asyncio
async def test_health_history_max_hours(client: AsyncClient, auth_headers):
    """Test health history with maximum hours limit"""
    response = await client.get("/health/history?hours=200", headers=auth_headers)
    
    # Should be limited to 168 hours (7 days)
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_custom_health_check_registration(client: AsyncClient, admin_headers):
    """Test custom health check registration"""
    response = await client.post(
        "/health/checks/my_custom_check",
        headers=admin_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["check_name"] == "my_custom_check"


@pytest.mark.asyncio
async def test_component_health_caching():
    """Test that component health checks are cached"""
    from core.health import health_checker
    
    # Mock a component check
    call_count = 0
    
    async def mock_check():
        nonlocal call_count
        call_count += 1
        return ComponentHealth(
            name="test_component",
            status=HealthStatus.HEALTHY,
            message="Test successful"
        )
    
    health_checker.register_check("test_component", mock_check)
    
    # First call
    await health_checker.check_health()
    assert call_count == 1
    
    # Second call within cache TTL should use cache
    await health_checker.check_health()
    assert call_count == 1
    
    # Clear cache
    health_checker.cache.clear()
    
    # Third call should execute check again
    await health_checker.check_health()
    assert call_count == 2


@pytest.mark.asyncio
async def test_health_status_calculation():
    """Test overall health status calculation"""
    from core.health import health_checker, HealthStatus
    
    # Test all healthy
    results = [
        ComponentHealth("comp1", HealthStatus.HEALTHY),
        ComponentHealth("comp2", HealthStatus.HEALTHY)
    ]
    status = health_checker._calculate_overall_status(results)
    assert status == HealthStatus.HEALTHY
    
    # Test with degraded
    results = [
        ComponentHealth("comp1", HealthStatus.HEALTHY),
        ComponentHealth("comp2", HealthStatus.DEGRADED)
    ]
    status = health_checker._calculate_overall_status(results)
    assert status == HealthStatus.HEALTHY
    
    # Test with critical component unhealthy
    results = [
        ComponentHealth("database", HealthStatus.UNHEALTHY),
        ComponentHealth("comp2", HealthStatus.HEALTHY)
    ]
    status = health_checker._calculate_overall_status(results)
    assert status == HealthStatus.UNHEALTHY
    
    # Test with many unhealthy
    results = [
        ComponentHealth("comp1", HealthStatus.UNHEALTHY),
        ComponentHealth("comp2", HealthStatus.UNHEALTHY),
        ComponentHealth("comp3", HealthStatus.HEALTHY)
    ]
    status = health_checker._calculate_overall_status(results)
    assert status == HealthStatus.UNHEALTHY