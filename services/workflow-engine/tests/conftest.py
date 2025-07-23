"""Pytest configuration and fixtures for Workflow Engine service tests."""
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from src.main import app
from src.db.base import Base
from src.core.config import settings


# Override database URL for testing
TEST_DATABASE_URL = settings.DATABASE_URL.replace(
    "postgresql+asyncpg://", "postgresql+asyncpg://test_"
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """Create test database and provide session."""
    # Create test engine
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async_session = async_sessionmaker(
        engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
    
    # Drop tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with test database."""
    # Override dependency
    from src.api.dependencies import get_db
    app.dependency_overrides[get_db] = lambda: test_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers() -> dict:
    """Provide authentication headers for testing."""
    # In a real scenario, this would generate a valid JWT token
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
async def sample_data(test_db: AsyncSession) -> dict:
    """Create sample data for testing."""
    # Service-specific sample data would be created here
    return {}