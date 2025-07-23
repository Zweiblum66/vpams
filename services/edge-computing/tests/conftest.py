"""
Shared test fixtures for edge computing service
"""

import pytest
from unittest.mock import Mock, AsyncMock
import asyncio


@pytest.fixture
def mock_db():
    """Create mock database session"""
    db = AsyncMock()
    db.add = Mock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    db.get = AsyncMock()
    db.delete = AsyncMock()
    return db


@pytest.fixture
def mock_redis():
    """Create mock Redis client"""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    redis.setex = AsyncMock()
    redis.delete = AsyncMock()
    redis.exists = AsyncMock(return_value=False)
    redis.lpush = AsyncMock()
    redis.ltrim = AsyncMock()
    redis.hset = AsyncMock()
    redis.scan_iter = AsyncMock(return_value=AsyncIterator([]))
    return redis


class AsyncIterator:
    """Helper class for async iteration in tests"""
    def __init__(self, items):
        self.items = items
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        if not self.items:
            raise StopAsyncIteration
        return self.items.pop(0)


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()