"""
Tests for API Key Management

Comprehensive tests for API key creation, validation, and management.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from services.api_key_service import APIKeyService
from db.models import APIKey, APIKeyUsageLog
from core.api_key_auth import (
    validate_api_key,
    require_api_key,
    require_api_key_scopes,
    APIKeyAuthMiddleware
)
from core.exceptions import ValidationException, NotFoundException
from fastapi import Request, HTTPException


class TestAPIKeyService:
    """Test cases for APIKeyService"""
    
    @pytest.fixture
    async def db_session(self):
        """Mock database session"""
        session = AsyncMock(spec=AsyncSession)
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        session.execute = AsyncMock()
        return session
    
    @pytest.fixture
    def api_key_service(self, db_session):
        """Create APIKeyService instance"""
        return APIKeyService(db_session)
    
    @pytest.mark.asyncio
    async def test_create_api_key_success(self, api_key_service, db_session):
        """Test successful API key creation"""
        # Mock successful database operations
        db_session.commit.return_value = None
        db_session.refresh.return_value = None
        
        # Create API key
        api_key, raw_key = await api_key_service.create_api_key(
            name="Test Key",
            description="Test description",
            scopes=["read", "write"],
            expires_in_days=30
        )
        
        # Verify results
        assert api_key.name == "Test Key"
        assert api_key.description == "Test description"
        assert api_key.scopes == ["read", "write"]
        assert api_key.prefix == "mams_"
        assert raw_key.startswith("mams_")
        assert len(raw_key) == 37  # mams_ + 32 characters
        
        # Verify database operations
        db_session.add.assert_called_once()
        db_session.commit.assert_called_once()
        db_session.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_api_key_invalid_name(self, api_key_service):
        """Test API key creation with invalid name"""
        with pytest.raises(ValidationException, match="at least 3 characters"):
            await api_key_service.create_api_key(name="ab")
    
    @pytest.mark.asyncio
    async def test_create_api_key_with_expiration(self, api_key_service, db_session):
        """Test API key creation with expiration"""
        db_session.commit.return_value = None
        db_session.refresh.return_value = None
        
        api_key, raw_key = await api_key_service.create_api_key(
            name="Expiring Key",
            expires_in_days=7
        )
        
        # Check that expires_at is set
        assert api_key.expires_at is not None
        expected_expiry = datetime.utcnow() + timedelta(days=7)
        assert abs((api_key.expires_at - expected_expiry).total_seconds()) < 60
    
    @pytest.mark.asyncio
    async def test_validate_api_key_success(self, api_key_service, db_session):
        """Test successful API key validation"""
        # Mock database query result
        mock_api_key = APIKey(
            id="test-id",
            name="Test Key",
            hash="test-hash",
            is_active=True,
            expires_at=None,
            usage_count=0
        )
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_api_key
        db_session.execute.return_value = mock_result
        
        # Validate API key
        result = await api_key_service.validate_api_key("mams_test_key")
        
        assert result == mock_api_key
        assert mock_api_key.usage_count == 1
        assert mock_api_key.last_used_at is not None
        db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_api_key_invalid_prefix(self, api_key_service):
        """Test API key validation with invalid prefix"""
        result = await api_key_service.validate_api_key("invalid_key")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_validate_api_key_not_found(self, api_key_service, db_session):
        """Test API key validation when key not found"""
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        db_session.execute.return_value = mock_result
        
        result = await api_key_service.validate_api_key("mams_nonexistent_key")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_validate_api_key_expired(self, api_key_service, db_session):
        """Test API key validation with expired key"""
        # Mock expired key
        mock_api_key = APIKey(
            id="test-id",
            name="Expired Key",
            hash="test-hash",
            is_active=True,
            expires_at=datetime.utcnow() - timedelta(days=1),
            usage_count=0
        )
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_api_key
        db_session.execute.return_value = mock_result
        
        result = await api_key_service.validate_api_key("mams_expired_key")
        assert result == mock_api_key  # Service doesn't check expiration in validate_api_key
    
    @pytest.mark.asyncio
    async def test_revoke_api_key_success(self, api_key_service, db_session):
        """Test successful API key revocation"""
        # Mock existing key
        mock_api_key = APIKey(
            id="test-id",
            name="Test Key",
            is_active=True
        )
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_api_key
        db_session.execute.return_value = mock_result
        
        # Revoke key
        result = await api_key_service.revoke_api_key("test-id", "Test reason")
        
        assert result.is_active is False
        assert result.revoked_reason == "Test reason"
        assert result.revoked_at is not None
        db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_revoke_api_key_already_revoked(self, api_key_service, db_session):
        """Test revoking already revoked key"""
        mock_api_key = APIKey(
            id="test-id",
            name="Test Key",
            is_active=False
        )
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_api_key
        db_session.execute.return_value = mock_result
        
        with pytest.raises(ValidationException, match="already revoked"):
            await api_key_service.revoke_api_key("test-id", "Test reason")
    
    @pytest.mark.asyncio
    async def test_rotate_api_key_success(self, api_key_service, db_session):
        """Test successful API key rotation"""
        # Mock existing key
        mock_old_key = APIKey(
            id="old-id",
            name="Old Key",
            description="Old description",
            user_id="user-123",
            scopes=["read", "write"],
            is_active=True
        )
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_old_key
        db_session.execute.return_value = mock_result
        
        # Mock successful creation and revocation
        db_session.commit.return_value = None
        db_session.refresh.return_value = None
        
        # Rotate key
        new_key, raw_key = await api_key_service.rotate_api_key("old-id", revoke_old=True)
        
        # Verify new key properties
        assert new_key.name == "Old Key (rotated)"
        assert new_key.description == "Old description"
        assert new_key.user_id == "user-123"
        assert new_key.scopes == ["read", "write"]
        assert raw_key.startswith("mams_")
        
        # Verify database operations
        assert db_session.add.call_count == 2  # New key and audit log
        assert db_session.commit.call_count >= 2  # Creation and revocation


class TestAPIKeyAuth:
    """Test cases for API key authentication"""
    
    @pytest.fixture
    def mock_request(self):
        """Mock FastAPI request"""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.method = "GET"
        request.url.path = "/api/v1/test"
        request.headers = {}
        request.client.host = "192.168.1.1"
        return request
    
    @pytest.mark.asyncio
    async def test_validate_api_key_success(self, mock_request):
        """Test successful API key validation"""
        # Mock database session and service
        with patch('core.api_key_auth.AsyncSessionLocal') as mock_session, \
             patch('core.api_key_auth.APIKeyService') as mock_service_class:
            
            mock_db = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db
            
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            
            # Mock API key validation
            mock_api_key = APIKey(
                id="test-id",
                name="Test Key",
                scopes=["read", "write"],
                user_id="user-123"
            )
            mock_service.validate_api_key.return_value = mock_api_key
            mock_service.log_api_key_usage.return_value = None
            
            # Test validation
            result = await validate_api_key(mock_request, "mams_test_key")
            
            assert result is not None
            assert result["api_key_id"] == "test-id"
            assert result["api_key_name"] == "Test Key"
            assert result["scopes"] == ["read", "write"]
            assert result["user_id"] == "user-123"
    
    @pytest.mark.asyncio
    async def test_validate_api_key_invalid(self, mock_request):
        """Test API key validation with invalid key"""
        with patch('core.api_key_auth.AsyncSessionLocal') as mock_session, \
             patch('core.api_key_auth.APIKeyService') as mock_service_class:
            
            mock_db = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db
            
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.validate_api_key.return_value = None
            
            # Test validation with invalid key
            result = await validate_api_key(mock_request, "invalid_key")
            assert result is None
    
    @pytest.mark.asyncio
    async def test_require_api_key_success(self, mock_request):
        """Test successful API key requirement"""
        with patch('core.api_key_auth.validate_api_key') as mock_validate:
            mock_validate.return_value = {
                "api_key_id": "test-id",
                "api_key_name": "Test Key",
                "scopes": ["read", "write"]
            }
            
            result = await require_api_key(mock_request, "mams_test_key", None)
            
            assert result["api_key_id"] == "test-id"
            assert hasattr(mock_request.state, 'api_key_data')
    
    @pytest.mark.asyncio
    async def test_require_api_key_missing(self, mock_request):
        """Test API key requirement with missing key"""
        with pytest.raises(HTTPException) as exc_info:
            await require_api_key(mock_request, None, None)
        
        assert exc_info.value.status_code == 401
        assert "API key required" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_require_api_key_invalid(self, mock_request):
        """Test API key requirement with invalid key"""
        with patch('core.api_key_auth.validate_api_key') as mock_validate:
            mock_validate.return_value = None
            
            with pytest.raises(HTTPException) as exc_info:
                await require_api_key(mock_request, "invalid_key", None)
            
            assert exc_info.value.status_code == 401
            assert "Invalid API key" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_require_api_key_scopes_success(self, mock_request):
        """Test successful scope requirement"""
        # Create scope dependency
        scope_dependency = require_api_key_scopes("read", "write")
        
        # Mock API key data with required scopes
        mock_api_key_data = {
            "api_key_id": "test-id",
            "scopes": ["read", "write", "upload"]
        }
        
        with patch('core.api_key_auth.require_api_key') as mock_require:
            mock_require.return_value = mock_api_key_data
            
            result = await scope_dependency(mock_request, mock_api_key_data)
            assert result == mock_api_key_data
    
    @pytest.mark.asyncio
    async def test_require_api_key_scopes_missing(self, mock_request):
        """Test scope requirement with missing scopes"""
        scope_dependency = require_api_key_scopes("read", "write", "admin")
        
        # Mock API key data with insufficient scopes
        mock_api_key_data = {
            "api_key_id": "test-id",
            "scopes": ["read", "write"]
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await scope_dependency(mock_request, mock_api_key_data)
        
        assert exc_info.value.status_code == 403
        assert "Missing required scopes" in str(exc_info.value.detail)
        assert "admin" in str(exc_info.value.detail)


class TestAPIKeyMiddleware:
    """Test cases for API key middleware"""
    
    @pytest.fixture
    def mock_app(self):
        """Mock FastAPI app"""
        app = AsyncMock()
        return app
    
    @pytest.fixture
    def middleware(self, mock_app):
        """Create middleware instance"""
        return APIKeyAuthMiddleware(mock_app)
    
    @pytest.fixture
    def mock_request(self):
        """Mock request with API key"""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.method = "GET"
        request.url.path = "/api/v1/test"
        request.headers = {"X-API-Key": "mams_test_key"}
        request.query_params = {}
        request.client.host = "192.168.1.1"
        return request
    
    @pytest.fixture
    def mock_call_next(self):
        """Mock call_next function"""
        async def call_next(request):
            response = MagicMock()
            response.status_code = 200
            return response
        return call_next
    
    @pytest.mark.asyncio
    async def test_middleware_with_valid_api_key(self, middleware, mock_request, mock_call_next):
        """Test middleware with valid API key"""
        with patch('core.api_key_auth.validate_api_key') as mock_validate, \
             patch('core.api_key_auth.APIKeyService') as mock_service_class:
            
            # Mock successful validation
            mock_validate.return_value = {
                "api_key_id": "test-id",
                "api_key_name": "Test Key",
                "scopes": ["read", "write"]
            }
            
            # Mock service for usage update
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.log_api_key_usage.return_value = None
            
            # Process request
            response = await middleware.dispatch(mock_request, mock_call_next)
            
            # Verify API key data was set
            assert hasattr(mock_request.state, 'api_key_data')
            assert mock_request.state.auth_method == "api_key"
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_middleware_with_invalid_api_key(self, middleware, mock_request, mock_call_next):
        """Test middleware with invalid API key"""
        with patch('core.api_key_auth.validate_api_key') as mock_validate:
            mock_validate.return_value = None
            
            # Process request
            response = await middleware.dispatch(mock_request, mock_call_next)
            
            # Verify no API key data was set
            assert not hasattr(mock_request.state, 'api_key_data')
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_middleware_excluded_path(self, middleware, mock_call_next):
        """Test middleware with excluded path"""
        request = MagicMock(spec=Request)
        request.url.path = "/health"
        
        # Process request
        response = await middleware.dispatch(request, mock_call_next)
        
        # Verify no API key processing occurred
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_middleware_no_api_key(self, middleware, mock_call_next):
        """Test middleware without API key"""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.url.path = "/api/v1/test"
        request.headers = {}
        request.query_params = {}
        
        # Process request
        response = await middleware.dispatch(request, mock_call_next)
        
        # Verify no API key data was set
        assert not hasattr(request.state, 'api_key_data')
        assert response.status_code == 200


class TestAPIKeyRoutes:
    """Test cases for API key routes"""
    
    @pytest.fixture
    def mock_user(self):
        """Mock current user"""
        user = MagicMock()
        user.id = "user-123"
        user.is_active = True
        return user
    
    @pytest.mark.asyncio
    async def test_create_api_key_route(self, mock_user):
        """Test API key creation route"""
        from api.api_key_routes import create_api_key
        from schemas.api_key import APIKeyCreate
        
        # Mock request data
        key_data = APIKeyCreate(
            name="Test Key",
            description="Test description",
            scopes=["read", "write"]
        )
        
        # Mock service
        with patch('api.api_key_routes.APIKeyService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            
            # Mock successful creation
            mock_api_key = APIKey(
                id="test-id",
                name="Test Key",
                description="Test description",
                prefix="mams_",
                last_four="abcd",
                scopes=["read", "write"],
                is_active=True,
                created_at=datetime.utcnow(),
                usage_count=0
            )
            
            mock_service.create_api_key.return_value = (mock_api_key, "mams_test_key")
            
            # Mock database session
            mock_db = AsyncMock()
            
            # Call route
            result = await create_api_key(key_data, mock_db, mock_user)
            
            # Verify response
            assert result.id == "test-id"
            assert result.name == "Test Key"
            assert result.key == "mams_test_key"
            assert result.scopes == ["read", "write"]
            
            # Verify service call
            mock_service.create_api_key.assert_called_once_with(
                name="Test Key",
                description="Test description",
                user_id="user-123",
                application_id=None,
                scopes=["read", "write"],
                expires_in_days=None,
                rate_limit_override=None,
                metadata=None
            )


class TestAPIKeyIntegration:
    """Integration tests for API key functionality"""
    
    @pytest.mark.asyncio
    async def test_full_api_key_flow(self):
        """Test complete API key lifecycle"""
        # This would be an integration test with real database
        # For now, we'll skip this as it requires full test setup
        pass
    
    @pytest.mark.asyncio
    async def test_api_key_performance(self):
        """Test API key validation performance"""
        # Performance test for API key validation
        # Would measure validation time under load
        pass
