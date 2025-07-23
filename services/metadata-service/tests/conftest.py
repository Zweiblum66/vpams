"""
Test configuration and fixtures for the metadata service
"""

import pytest
import asyncio
from typing import AsyncGenerator
from motor.motor_asyncio import AsyncIOMotorClient
from uuid import uuid4

from src.core.config import Settings
from src.db.database import get_db
from src.services.metadata_validator import MetadataValidator
from src.services.schema_service import SchemaService
from src.services.metadata_service import MetadataService


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings():
    """Test settings configuration"""
    return Settings(
        MONGODB_URL="mongodb://localhost:27017",
        MONGODB_DATABASE="test_mams_metadata",
        REDIS_URL="redis://localhost:6379/15",  # Use different DB for tests
        JWT_SECRET_KEY="test-secret-key",
        DEBUG=True,
        LOG_LEVEL="DEBUG"
    )


@pytest.fixture
async def db_client(test_settings):
    """Test database client"""
    client = AsyncIOMotorClient(test_settings.MONGODB_URL)
    yield client
    client.close()


@pytest.fixture
async def test_db(db_client, test_settings):
    """Test database instance"""
    db = db_client[test_settings.MONGODB_DATABASE]
    yield db
    
    # Cleanup: drop test database after test
    await db_client.drop_database(test_settings.MONGODB_DATABASE)


@pytest.fixture
def test_user_id():
    """Test user ID"""
    return uuid4()


@pytest.fixture
def metadata_validator():
    """Metadata validator instance"""
    return MetadataValidator()


@pytest.fixture
def schema_service(test_db, test_user_id):
    """Schema service instance"""
    return SchemaService(test_db, test_user_id)


@pytest.fixture
def metadata_service(test_db, test_user_id):
    """Metadata service instance"""
    return MetadataService(test_db, test_user_id)


@pytest.fixture
def test_auth_headers():
    """Test authentication headers"""
    return {
        "Authorization": "Bearer test-token",
        "Content-Type": "application/json"
    }


@pytest.fixture
def sample_metadata():
    """Sample metadata for testing"""
    return {
        "title": "Test Asset",
        "description": "Test description",
        "tags": ["test", "sample"],
        "priority": 5,
        "active": True,
        "created_date": "2024-01-01",
        "status": "draft"
    }


@pytest.fixture
def sample_schema_data():
    """Sample schema data for testing"""
    return {
        "name": "test_schema",
        "display_name": "Test Schema",
        "description": "Schema for testing",
        "category": "test",
        "asset_types": ["video", "image"],
        "fields": [
            {
                "name": "title",
                "display_name": "Title",
                "field_type": "string",
                "required": True,
                "constraints": {"min_length": 1, "max_length": 100}
            },
            {
                "name": "description",
                "display_name": "Description",
                "field_type": "text",
                "required": False,
                "constraints": {"max_length": 1000}
            },
            {
                "name": "tags",
                "display_name": "Tags",
                "field_type": "array",
                "array_type": "string",
                "required": False
            }
        ],
        "allow_custom_fields": True,
        "strict_mode": False
    }


@pytest.fixture
def sample_asset_id():
    """Sample asset ID for testing"""
    return uuid4()


@pytest.fixture
def sample_schema_id():
    """Sample schema ID for testing"""
    return uuid4()


# Async test utilities
@pytest.fixture
async def async_client():
    """Async HTTP client for testing"""
    # This would typically be a test client for FastAPI
    # For now, it's a placeholder
    yield None


# Database cleanup utilities
@pytest.fixture(autouse=True)
async def cleanup_db(test_db):
    """Clean up database before each test"""
    # Drop all collections before each test
    collections = await test_db.list_collection_names()
    for collection_name in collections:
        await test_db[collection_name].drop()
    
    yield
    
    # Cleanup after test (optional)
    # Collections will be dropped by test_db fixture anyway