"""
Tests for database schema and models

This module tests the database schema, models, and relationships
to ensure they work correctly.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text

from db.base import Base
from db.models import User, Role, Permission, UserProfile, UserSession
from core.config import Settings


# Test database URL (use in-memory SQLite for testing)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False}
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine):
    """Create test database session"""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session


@pytest.mark.asyncio
async def test_user_model_creation(test_session):
    """Test User model creation and basic operations"""
    user = User(
        id=uuid4(),
        email="test@example.com",
        username="testuser",
        password_hash="hashed_password",
        first_name="Test",
        last_name="User",
        display_name="Test User",
        is_active=True,
        is_verified=True
    )
    
    test_session.add(user)
    await test_session.commit()
    
    # Verify user was created
    result = await test_session.execute(
        text("SELECT * FROM users WHERE email = :email"),
        {"email": "test@example.com"}
    )
    db_user = result.fetchone()
    
    assert db_user is not None
    assert db_user.email == "test@example.com"
    assert db_user.username == "testuser"
    assert db_user.first_name == "Test"
    assert db_user.last_name == "User"
    assert db_user.is_active is True
    assert db_user.is_verified is True


@pytest.mark.asyncio
async def test_role_model_creation(test_session):
    """Test Role model creation and basic operations"""
    role = Role(
        id=uuid4(),
        name="test_role",
        display_name="Test Role",
        description="A test role",
        role_type="custom",
        is_active=True
    )
    
    test_session.add(role)
    await test_session.commit()
    
    # Verify role was created
    result = await test_session.execute(
        text("SELECT * FROM roles WHERE name = :name"),
        {"name": "test_role"}
    )
    db_role = result.fetchone()
    
    assert db_role is not None
    assert db_role.name == "test_role"
    assert db_role.display_name == "Test Role"
    assert db_role.description == "A test role"
    assert db_role.role_type == "custom"
    assert db_role.is_active is True


@pytest.mark.asyncio
async def test_permission_model_creation(test_session):
    """Test Permission model creation and basic operations"""
    permission = Permission(
        id=uuid4(),
        name="test:read",
        display_name="Test Read",
        description="Test read permission",
        resource="test",
        action="read",
        category="testing",
        scope="global",
        is_active=True
    )
    
    test_session.add(permission)
    await test_session.commit()
    
    # Verify permission was created
    result = await test_session.execute(
        text("SELECT * FROM permissions WHERE name = :name"),
        {"name": "test:read"}
    )
    db_permission = result.fetchone()
    
    assert db_permission is not None
    assert db_permission.name == "test:read"
    assert db_permission.display_name == "Test Read"
    assert db_permission.resource == "test"
    assert db_permission.action == "read"
    assert db_permission.category == "testing"
    assert db_permission.scope == "global"


@pytest.mark.asyncio
async def test_user_profile_relationship(test_session):
    """Test User-UserProfile relationship"""
    user = User(
        id=uuid4(),
        email="profile@example.com",
        password_hash="hashed_password",
        first_name="Profile",
        last_name="User"
    )
    
    profile = UserProfile(
        id=uuid4(),
        user_id=user.id,
        phone="+1234567890",
        department="Engineering",
        job_title="Developer",
        organization="Test Corp",
        timezone="UTC",
        language="en",
        preferences={"theme": "dark", "notifications": {"email": True}}
    )
    
    test_session.add(user)
    test_session.add(profile)
    await test_session.commit()
    
    # Test relationship loading
    await test_session.refresh(user, ["profile"])
    
    assert user.profile is not None
    assert user.profile.phone == "+1234567890"
    assert user.profile.department == "Engineering"
    assert user.profile.preferences["theme"] == "dark"


@pytest.mark.asyncio
async def test_user_session_relationship(test_session):
    """Test User-UserSession relationship"""
    user = User(
        id=uuid4(),
        email="session@example.com",
        password_hash="hashed_password",
        first_name="Session",
        last_name="User"
    )
    
    session1 = UserSession(
        id=uuid4(),
        user_id=user.id,
        session_token="token1",
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0",
        expires_at=datetime.now(timezone.utc),
        is_active=True
    )
    
    session2 = UserSession(
        id=uuid4(),
        user_id=user.id,
        session_token="token2",
        ip_address="192.168.1.2",
        user_agent="Chrome/91.0",
        expires_at=datetime.now(timezone.utc),
        is_active=True
    )
    
    test_session.add(user)
    test_session.add(session1)
    test_session.add(session2)
    await test_session.commit()
    
    # Test relationship loading
    await test_session.refresh(user, ["sessions"])
    
    assert len(user.sessions) == 2
    assert user.sessions[0].session_token in ["token1", "token2"]
    assert user.sessions[1].session_token in ["token1", "token2"]


@pytest.mark.asyncio
async def test_user_role_many_to_many(test_session):
    """Test User-Role many-to-many relationship"""
    user = User(
        id=uuid4(),
        email="roles@example.com",
        password_hash="hashed_password",
        first_name="Roles",
        last_name="User"
    )
    
    role1 = Role(
        id=uuid4(),
        name="role1",
        display_name="Role 1",
        role_type="custom"
    )
    
    role2 = Role(
        id=uuid4(),
        name="role2",
        display_name="Role 2",
        role_type="custom"
    )
    
    # Add roles to user
    user.roles.append(role1)
    user.roles.append(role2)
    
    test_session.add(user)
    test_session.add(role1)
    test_session.add(role2)
    await test_session.commit()
    
    # Test relationship loading
    await test_session.refresh(user, ["roles"])
    await test_session.refresh(role1, ["users"])
    
    assert len(user.roles) == 2
    assert role1 in user.roles
    assert role2 in user.roles
    assert user in role1.users


@pytest.mark.asyncio
async def test_role_permission_many_to_many(test_session):
    """Test Role-Permission many-to-many relationship"""
    role = Role(
        id=uuid4(),
        name="test_role",
        display_name="Test Role",
        role_type="custom"
    )
    
    perm1 = Permission(
        id=uuid4(),
        name="perm1:read",
        display_name="Permission 1",
        resource="perm1",
        action="read",
        category="testing"
    )
    
    perm2 = Permission(
        id=uuid4(),
        name="perm2:write",
        display_name="Permission 2",
        resource="perm2",
        action="write",
        category="testing"
    )
    
    # Add permissions to role
    role.permissions.append(perm1)
    role.permissions.append(perm2)
    
    test_session.add(role)
    test_session.add(perm1)
    test_session.add(perm2)
    await test_session.commit()
    
    # Test relationship loading
    await test_session.refresh(role, ["permissions"])
    await test_session.refresh(perm1, ["roles"])
    
    assert len(role.permissions) == 2
    assert perm1 in role.permissions
    assert perm2 in role.permissions
    assert role in perm1.roles


@pytest.mark.asyncio
async def test_role_hierarchy(test_session):
    """Test Role hierarchy (parent-child relationships)"""
    parent_role = Role(
        id=uuid4(),
        name="parent_role",
        display_name="Parent Role",
        role_type="custom"
    )
    
    child_role = Role(
        id=uuid4(),
        name="child_role",
        display_name="Child Role",
        role_type="custom",
        parent_role_id=parent_role.id
    )
    
    test_session.add(parent_role)
    test_session.add(child_role)
    await test_session.commit()
    
    # Test relationship loading
    await test_session.refresh(parent_role, ["child_roles"])
    await test_session.refresh(child_role, ["parent_role"])
    
    assert len(parent_role.child_roles) == 1
    assert child_role in parent_role.child_roles
    assert child_role.parent_role == parent_role


@pytest.mark.asyncio
async def test_database_indexes(test_session):
    """Test that database indexes work correctly"""
    # Create test data
    user = User(
        id=uuid4(),
        email="index@example.com",
        username="indexuser",
        password_hash="hashed_password",
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    
    test_session.add(user)
    await test_session.commit()
    
    # Test email index
    result = await test_session.execute(
        text("SELECT * FROM users WHERE email = :email"),
        {"email": "index@example.com"}
    )
    assert result.fetchone() is not None
    
    # Test username index
    result = await test_session.execute(
        text("SELECT * FROM users WHERE username = :username"),
        {"username": "indexuser"}
    )
    assert result.fetchone() is not None
    
    # Test is_active index
    result = await test_session.execute(
        text("SELECT * FROM users WHERE is_active = :is_active"),
        {"is_active": True}
    )
    assert result.fetchone() is not None


@pytest.mark.asyncio
async def test_unique_constraints(test_session):
    """Test unique constraints on models"""
    # Test unique email constraint
    user1 = User(
        id=uuid4(),
        email="unique@example.com",
        password_hash="hashed_password"
    )
    
    user2 = User(
        id=uuid4(),
        email="unique@example.com",  # Same email
        password_hash="hashed_password"
    )
    
    test_session.add(user1)
    await test_session.commit()
    
    # Adding second user with same email should fail
    test_session.add(user2)
    with pytest.raises(Exception):  # Should raise integrity error
        await test_session.commit()


@pytest.mark.asyncio
async def test_model_representations(test_session):
    """Test model __repr__ methods"""
    user = User(
        id=uuid4(),
        email="repr@example.com",
        password_hash="hashed_password",
        is_active=True
    )
    
    role = Role(
        id=uuid4(),
        name="repr_role",
        display_name="Repr Role",
        role_type="custom"
    )
    
    permission = Permission(
        id=uuid4(),
        name="repr:read",
        display_name="Repr Read",
        resource="repr",
        action="read"
    )
    
    # Test __repr__ methods
    user_repr = repr(user)
    role_repr = repr(role)
    permission_repr = repr(permission)
    
    assert "User" in user_repr
    assert "repr@example.com" in user_repr
    assert "True" in user_repr
    
    assert "Role" in role_repr
    assert "repr_role" in role_repr
    assert "custom" in role_repr
    
    assert "Permission" in permission_repr
    assert "repr:read" in permission_repr
    assert "repr" in permission_repr
    assert "read" in permission_repr