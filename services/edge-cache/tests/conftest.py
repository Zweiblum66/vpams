"""
Test configuration for edge cache service
"""

import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient
from unittest.mock import Mock, AsyncMock

from src.main import app
from src.core.config import Settings, CacheStrategy, StorageBackend
from src.core.cache_manager import CacheManager
from src.core.origin_client import OriginClient


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings():
    """Test settings"""
    return Settings(
        service_name="edge-cache-test",
        debug=True,
        cache_strategy=CacheStrategy.LRU,
        cache_size_mb=10,
        cache_ttl_seconds=300,
        storage_backend=StorageBackend.MEMORY,
        edge_location="test-location",
        edge_region="test-region",
        origin_url="http://test-origin",
        redis_url="redis://localhost:6379/15"  # Use test database
    )


@pytest.fixture
async def cache_manager(test_settings):
    """Create test cache manager"""
    manager = CacheManager(test_settings)
    await manager.initialize()
    yield manager
    await manager.shutdown()


@pytest.fixture
async def origin_client(test_settings):
    """Create test origin client"""
    client = OriginClient(test_settings)
    await client.initialize()
    yield client
    await client.shutdown()


@pytest.fixture
async def mock_origin_client():
    """Create mock origin client"""
    mock = AsyncMock(spec=OriginClient)
    
    # Default responses
    mock.fetch.return_value = (b"test content", 200, {"content-type": "text/plain"})
    mock.should_cache.return_value = True
    mock.calculate_ttl.return_value = 300
    
    return mock


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create test client"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_cache_data():
    """Sample data for cache testing"""
    return {
        "text": {
            "content": b"Hello, World!",
            "content_type": "text/plain",
            "headers": {"content-type": "text/plain", "cache-control": "max-age=300"}
        },
        "json": {
            "content": b'{"message": "test"}',
            "content_type": "application/json",
            "headers": {"content-type": "application/json", "cache-control": "max-age=600"}
        },
        "image": {
            "content": b"\x89PNG\r\n\x1a\n" + b"\x00" * 100,  # Minimal PNG
            "content_type": "image/png",
            "headers": {"content-type": "image/png", "cache-control": "max-age=3600"}
        }
    }