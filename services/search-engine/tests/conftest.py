"""Pytest configuration and fixtures for Search Engine service tests."""
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from httpx import AsyncClient
from unittest.mock import AsyncMock

from src.main import app
from src.core.config import settings


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_headers() -> dict:
    """Provide authentication headers for testing."""
    # In a real scenario, this would generate a valid JWT token
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
def mock_opensearch_client():
    """Mock OpenSearch client for unit tests."""
    client = AsyncMock()
    # Set up default responses
    client.indices.exists.return_value = True
    client.info.return_value = {"version": {"number": "2.11.0"}}
    return client


@pytest.fixture
async def sample_search_response() -> dict:
    """Sample OpenSearch search response."""
    return {
        "took": 10,
        "timed_out": False,
        "hits": {
            "total": {"value": 2, "relation": "eq"},
            "max_score": 2.5,
            "hits": [
                {
                    "_index": "mams_assets",
                    "_id": "asset-123",
                    "_score": 2.5,
                    "_source": {
                        "asset_id": "asset-123",
                        "title": "Test Video",
                        "description": "A test video file",
                        "asset_type": "video",
                        "created_at": "2024-01-15T10:00:00Z"
                    }
                },
                {
                    "_index": "mams_assets",
                    "_id": "asset-456",
                    "_score": 1.8,
                    "_source": {
                        "asset_id": "asset-456",
                        "title": "Another Test",
                        "description": "Another test asset",
                        "asset_type": "image",
                        "created_at": "2024-01-14T15:30:00Z"
                    }
                }
            ]
        }
    }