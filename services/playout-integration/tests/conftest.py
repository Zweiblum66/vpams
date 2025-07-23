"""Test configuration and fixtures"""

import asyncio
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from src.main import app
from src.db.base import Base, get_db
from src.core.config import settings

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=True
)

# Create test session factory
TestAsyncSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture
async def async_session():
    """Create async test session"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestAsyncSessionLocal() as session:
        yield session
        await session.rollback()
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def test_client(async_session):
    """Create test client with database override"""
    
    async def get_test_db():
        yield async_session
    
    app.dependency_overrides[get_db] = get_test_db
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest.fixture
def mock_user():
    """Mock user for tests"""
    return {
        "id": "00000000-0000-0000-0000-000000000001",
        "username": "test-user",
        "roles": ["admin"]
    }


@pytest.fixture
def auth_headers(mock_user):
    """Authentication headers for tests"""
    # In real tests, you'd generate a proper JWT token
    return {
        "Authorization": "Bearer mock-jwt-token"
    }


@pytest_asyncio.fixture
async def sample_playout_system(async_session):
    """Create sample playout system for tests"""
    from src.db.models import PlayoutSystem, PlayoutSystemType, PlayoutProtocol
    
    system = PlayoutSystem(
        name="Test Playout System",
        slug="test-system",
        system_type=PlayoutSystemType.GENERIC,
        protocol=PlayoutProtocol.VDCP,
        host="localhost",
        port=8080,
        is_active=True
    )
    
    async_session.add(system)
    await async_session.commit()
    await async_session.refresh(system)
    
    return system


@pytest_asyncio.fixture  
async def sample_device(async_session, sample_playout_system):
    """Create sample device for tests"""
    from src.db.models import PlayoutDevice, DeviceStatus
    
    device = PlayoutDevice(
        playout_system_id=sample_playout_system.id,
        name="Test Device",
        device_id="DEV001",
        device_type="server",
        channel=1,
        status=DeviceStatus.ONLINE,
        is_active=True
    )
    
    async_session.add(device)
    await async_session.commit()
    await async_session.refresh(device)
    
    return device


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()