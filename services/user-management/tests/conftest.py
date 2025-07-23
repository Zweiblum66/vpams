"""Pytest configuration and fixtures for User Management service tests."""
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from src.main import app
from src.db.base import Base
from src.core.config import settings
from src.core.security import get_password_hash


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
async def test_user(test_db: AsyncSession) -> dict:
    """Create a test user."""
    from src.db.models import User
    
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("testpassword123"),
        full_name="Test User",
        is_active=True,
        is_superuser=False
    )
    
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    
    return {
        "id": str(user.id),
        "email": user.email,
        "username": user.username,
        "password": "testpassword123"
    }


@pytest.fixture
async def test_admin_user(test_db: AsyncSession) -> dict:
    """Create a test admin user."""
    from src.db.models import User
    
    user = User(
        email="admin@example.com",
        username="adminuser",
        hashed_password=get_password_hash("adminpassword123"),
        full_name="Admin User",
        is_active=True,
        is_superuser=True
    )
    
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    
    return {
        "id": str(user.id),
        "email": user.email,
        "username": user.username,
        "password": "adminpassword123"
    }


@pytest.fixture
async def auth_token(client: AsyncClient, test_user: dict) -> str:
    """Get authentication token for test user."""
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user["username"],
            "password": test_user["password"]
        }
    )
    return response.json()["access_token"]


@pytest.fixture
async def auth_headers(auth_token: str) -> dict:
    """Provide authentication headers for testing."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
async def admin_auth_token(client: AsyncClient, test_admin_user: dict) -> str:
    """Get authentication token for admin user."""
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": test_admin_user["username"],
            "password": test_admin_user["password"]
        }
    )
    return response.json()["access_token"]


@pytest.fixture
async def admin_auth_headers(admin_auth_token: str) -> dict:
    """Provide admin authentication headers for testing."""
    return {"Authorization": f"Bearer {admin_auth_token}"}