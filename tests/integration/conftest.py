"""
Integration Test Configuration

Shared fixtures and configuration for integration tests.
"""

import pytest
import asyncio
import httpx
import os
import time
import docker
from typing import Dict, Any
import subprocess


# Service health check URLs
SERVICE_HEALTH_CHECKS = {
    "api-gateway": "http://localhost:8000/health",
    "user-management": "http://localhost:8001/api/v1/health",
    "asset-management": "http://localhost:8002/api/v1/health",
    "storage-abstraction": "http://localhost:8003/api/v1/health",
    "metadata-service": "http://localhost:8004/api/v1/health",
    "search-engine": "http://localhost:8005/api/v1/health",
    "ingest-service": "http://localhost:8006/api/v1/health",
    "proxy-generation": "http://localhost:8007/api/v1/health",
    "workflow-engine": "http://localhost:8009/api/v1/health",
    "ai-ml-service": "http://localhost:8010/api/v1/health",
    "rights-management": "http://localhost:8011/api/v1/health",
}


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def docker_services():
    """Ensure all required Docker services are running."""
    client = docker.from_env()
    
    # Check if services are already running
    required_services = [
        "postgres", "mongodb", "redis", "opensearch", 
        "rabbitmq", "minio"
    ]
    
    running_containers = {c.name for c in client.containers.list()}
    missing_services = []
    
    for service in required_services:
        if not any(service in container for container in running_containers):
            missing_services.append(service)
    
    if missing_services:
        print(f"Starting missing services: {missing_services}")
        # Run docker-compose to start services
        subprocess.run(
            ["docker-compose", "-f", "docker-compose.yml", "up", "-d"] + missing_services,
            check=True,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        )
        
        # Wait for services to be ready
        await asyncio.sleep(10)
    
    yield
    
    # Don't stop services after tests (they might be used for development)


@pytest.fixture(scope="session")
async def wait_for_services(docker_services):
    """Wait for all microservices to be healthy."""
    print("Waiting for services to be ready...")
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        max_retries = 30
        retry_delay = 2
        
        for service_name, health_url in SERVICE_HEALTH_CHECKS.items():
            retries = 0
            while retries < max_retries:
                try:
                    response = await client.get(health_url)
                    if response.status_code == 200:
                        print(f"✓ {service_name} is ready")
                        break
                except (httpx.ConnectError, httpx.TimeoutException):
                    pass
                
                retries += 1
                if retries >= max_retries:
                    pytest.skip(f"Service {service_name} is not available")
                
                await asyncio.sleep(retry_delay)


@pytest.fixture
async def admin_auth_headers(wait_for_services):
    """Get authentication headers for admin user."""
    async with httpx.AsyncClient() as client:
        # Try to login with default admin
        try:
            login_response = await client.post(
                "http://localhost:8000/api/v1/auth/login",
                json={
                    "username": "admin",
                    "password": "admin123!@#"
                }
            )
            
            if login_response.status_code == 200:
                token = login_response.json()["data"]["access_token"]
                return {"Authorization": f"Bearer {token}"}
        except:
            pass
        
        # Create admin user if doesn't exist
        timestamp = int(time.time())
        admin_creds = {
            "username": f"admin_{timestamp}",
            "email": f"admin_{timestamp}@mams.test",
            "password": "Admin123!@#",
            "full_name": "Integration Test Admin",
            "is_admin": True
        }
        
        await client.post(
            "http://localhost:8000/api/v1/auth/register",
            json=admin_creds
        )
        
        login_response = await client.post(
            "http://localhost:8000/api/v1/auth/login",
            json={
                "username": admin_creds["username"],
                "password": admin_creds["password"]
            }
        )
        
        token = login_response.json()["data"]["access_token"]
        return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def test_project(admin_auth_headers):
    """Create a test project for integration tests."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/projects",
            json={
                "name": f"Integration Test Project {int(time.time())}",
                "description": "Project for integration testing",
                "type": "project"
            },
            headers=admin_auth_headers
        )
        
        project_data = response.json()["data"]
        yield project_data
        
        # Cleanup
        await client.delete(
            f"http://localhost:8000/api/v1/projects/{project_data['id']}",
            headers=admin_auth_headers
        )


@pytest.fixture
def integration_test_data() -> Dict[str, Any]:
    """Provide common test data for integration tests."""
    return {
        "test_users": [
            {
                "username": "test_editor",
                "email": "editor@test.com",
                "password": "Editor123!",
                "full_name": "Test Editor",
                "role": "editor"
            },
            {
                "username": "test_viewer",
                "email": "viewer@test.com",
                "password": "Viewer123!",
                "full_name": "Test Viewer",
                "role": "viewer"
            }
        ],
        "test_metadata": {
            "title": "Integration Test Asset",
            "description": "Asset created for integration testing",
            "keywords": ["test", "integration", "automated"],
            "copyright": "Test Copyright",
            "creator": "Integration Test Suite"
        },
        "workflow_templates": {
            "simple_processing": {
                "name": "Simple Processing",
                "tasks": [
                    {
                        "id": "extract",
                        "type": "metadata_extraction",
                        "name": "Extract Metadata"
                    },
                    {
                        "id": "thumbnail",
                        "type": "proxy_generation",
                        "name": "Generate Thumbnail",
                        "depends_on": ["extract"]
                    }
                ]
            }
        }
    }


@pytest.fixture
async def cleanup_test_data():
    """Cleanup any test data created during tests."""
    created_items = {
        "users": [],
        "assets": [],
        "projects": [],
        "workflows": []
    }
    
    yield created_items
    
    # Cleanup in reverse order of dependencies
    async with httpx.AsyncClient() as client:
        # Clean workflows
        for workflow_id in created_items["workflows"]:
            try:
                await client.delete(f"http://localhost:8000/api/v1/workflows/{workflow_id}")
            except:
                pass
        
        # Clean assets
        for asset_id in created_items["assets"]:
            try:
                await client.delete(f"http://localhost:8000/api/v1/assets/{asset_id}")
            except:
                pass
        
        # Clean projects
        for project_id in created_items["projects"]:
            try:
                await client.delete(f"http://localhost:8000/api/v1/projects/{project_id}")
            except:
                pass
        
        # Clean users
        for user_id in created_items["users"]:
            try:
                await client.delete(f"http://localhost:8000/api/v1/users/{user_id}")
            except:
                pass


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "requires_all_services: mark test as requiring all services"
    )