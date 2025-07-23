"""Test configuration for MOS Integration Service"""

import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient
import redis.asyncio as redis

from src.main import app
from src.db.base import Base
from src.core.config import settings


# Test database URL (use in-memory SQLite for tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

# Create test session factory
TestSessionLocal = sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create test database session"""
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async with TestSessionLocal() as session:
        yield session
    
    # Drop tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def redis_client():
    """Create test Redis client"""
    try:
        client = redis.from_url("redis://localhost:6379/15")  # Use test database
        await client.ping()
        yield client
    except Exception:
        # If Redis is not available, use a mock
        from unittest.mock import AsyncMock
        client = AsyncMock()
        yield client
    finally:
        if hasattr(client, 'close'):
            await client.close()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_mos_obj_xml():
    """Sample MOS object XML message"""
    return """<?xml version="1.0" encoding="UTF-8"?>
<mosObj>
    <objID>test_obj_001</objID>
    <objSlug>Test Video Clip</objSlug>
    <objType>video</objType>
    <objTB>25</objTB>
    <objRev>1</objRev>
    <objDur>1500</objDur>
    <status>NEW</status>
    <objAir>READY</objAir>
    <mosAbstract>Test video clip for news story</mosAbstract>
    <objGroup>news</objGroup>
    <objPaths>
        <objPath Type="video">
            <Description>High quality video</Description>
            <Target>file:///storage/video/test_clip.mp4</Target>
        </objPath>
        <objPath Type="proxy">
            <Description>Proxy video</Description>
            <Target>file:///storage/proxy/test_clip_proxy.mp4</Target>
        </objPath>
    </objPaths>
    <createdBy>test_user</createdBy>
    <created>2024-01-15T10:30:00</created>
    <description>Test video clip for unit testing</description>
</mosObj>"""


@pytest.fixture
def sample_running_order_xml():
    """Sample running order XML message"""
    return """<?xml version="1.0" encoding="UTF-8"?>
<roCreate>
    <roID>RO_20240115_1800</roID>
    <roSlug>Evening News</roSlug>
    <roEditionID>MAIN</roEditionID>
    <roTitle>Evening News - January 15, 2024</roTitle>
    <roStartTime>2024-01-15T18:00:00</roStartTime>
    <roEndTime>2024-01-15T18:30:00</roEndTime>
    <roDur>1800</roDur>
    <story>
        <storyID>STORY_001</storyID>
        <storySlug>Breaking News</storySlug>
        <storyNum>1</storyNum>
        <storyBody>Breaking news story about local events</storyBody>
        <item>
            <itemID>ITEM_001</itemID>
            <itemSlug>News Clip</itemSlug>
            <itemChannel>V1</itemChannel>
            <objID>test_obj_001</objID>
            <mosAbstract>Video clip for breaking news</mosAbstract>
            <itemDur>120</itemDur>
        </item>
    </story>
</roCreate>"""


@pytest.fixture
def sample_heartbeat_xml():
    """Sample heartbeat XML message"""
    return """<?xml version="1.0" encoding="UTF-8"?>
<heartbeat>
    <mosID>test_mos_server</mosID>
    <nrcsID>test_nrcs_client</nrcsID>
    <time>2024-01-15T10:30:00</time>
    <status>OK</status>
</heartbeat>"""


@pytest.fixture
def sample_mos_ack_xml():
    """Sample MOS ACK XML message"""
    return """<?xml version="1.0" encoding="UTF-8"?>
<mosAck>
    <messageID>test_message_001</messageID>
    <status>ACK</status>
    <statusDescription>Message processed successfully</statusDescription>
</mosAck>"""