"""
Tests for JWT Authentication Middleware

Tests authentication endpoints and middleware functionality.
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from jose import jwt
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.core.security import token_manager, password_manager
from src.core.exceptions import AuthenticationException, InvalidTokenException


class TestTokenManager:
    """Test JWT token management"""
    
    def test_create_access_token(self):
        """Test access token creation"""
        subject = "testuser"
        user_id = "12345"
        permissions = ["read", "write"]
        
        token = token_manager.create_access_token(
            subject=subject,
            user_id=user_id,
            permissions=permissions
        )
        
        # Decode token
        payload = jwt.decode(
            token,
            token_manager.secret_key,
            algorithms=[token_manager.algorithm]
        )
        
        assert payload["sub"] == subject
        assert payload["user_id"] == user_id
        assert payload["permissions"] == permissions
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload
    
    def test_create_refresh_token(self):
        """Test refresh token creation"""
        subject = "testuser"
        user_id = "12345"
        
        token = token_manager.create_refresh_token(
            subject=subject,
            user_id=user_id
        )
        
        # Decode token
        payload = jwt.decode(
            token,
            token_manager.secret_key,
            algorithms=[token_manager.algorithm]
        )
        
        assert payload["sub"] == subject
        assert payload["user_id"] == user_id
        assert payload["type"] == "refresh"
        assert "exp" in payload
        assert "iat" in payload
    
    def test_verify_access_token(self):
        """Test access token verification"""
        token = token_manager.create_access_token(
            subject="testuser",
            user_id="12345",
            permissions=["read"]
        )
        
        payload = token_manager.verify_token(token, "access")
        
        assert payload["sub"] == "testuser"
        assert payload["user_id"] == "12345"
        assert payload["permissions"] == ["read"]
        assert payload["type"] == "access"
    
    def test_verify_refresh_token(self):
        """Test refresh token verification"""
        token = token_manager.create_refresh_token(
            subject="testuser",
            user_id="12345"
        )
        
        payload = token_manager.verify_token(token, "refresh")
        
        assert payload["sub"] == "testuser"
        assert payload["user_id"] == "12345"
        assert payload["type"] == "refresh"
    
    def test_verify_expired_token(self):
        """Test expired token verification"""
        # Create token with negative expiration
        token = token_manager.create_access_token(
            subject="testuser",
            user_id="12345",
            expires_delta=timedelta(seconds=-1)
        )
        
        with pytest.raises(InvalidTokenException):
            token_manager.verify_token(token, "access")
    
    def test_verify_invalid_token(self):
        """Test invalid token verification"""
        with pytest.raises(InvalidTokenException):
            token_manager.verify_token("invalid.token.here", "access")
    
    def test_verify_wrong_token_type(self):
        """Test wrong token type verification"""
        # Create access token but verify as refresh
        token = token_manager.create_access_token(
            subject="testuser",
            user_id="12345"
        )
        
        with pytest.raises(InvalidTokenException) as exc_info:
            token_manager.verify_token(token, "refresh")
        
        assert "Invalid token type" in str(exc_info.value)
    
    def test_is_token_expired(self):
        """Test token expiration check"""
        # Valid token
        valid_token = token_manager.create_access_token(
            subject="testuser",
            user_id="12345"
        )
        assert not token_manager.is_token_expired(valid_token)
        
        # Expired token
        expired_token = token_manager.create_access_token(
            subject="testuser",
            user_id="12345",
            expires_delta=timedelta(seconds=-1)
        )
        assert token_manager.is_token_expired(expired_token)
        
        # Invalid token
        assert token_manager.is_token_expired("invalid.token")


class TestPasswordManager:
    """Test password hashing and verification"""
    
    def test_hash_password(self):
        """Test password hashing"""
        password = "SecurePassword123!"
        hashed = password_manager.hash_password(password)
        
        # Hash should be different from original
        assert hashed != password
        
        # Hash should be consistent format (bcrypt)
        assert hashed.startswith("$2b$")
    
    def test_verify_password(self):
        """Test password verification"""
        password = "SecurePassword123!"
        hashed = password_manager.hash_password(password)
        
        # Correct password should verify
        assert password_manager.verify_password(password, hashed)
        
        # Wrong password should not verify
        assert not password_manager.verify_password("WrongPassword", hashed)
    
    def test_generate_password(self):
        """Test password generation"""
        # Default length
        password = password_manager.generate_password()
        assert len(password) == 12
        
        # Custom length
        password = password_manager.generate_password(20)
        assert len(password) == 20
        
        # Should contain various character types
        assert any(c.isupper() for c in password)
        assert any(c.islower() for c in password)
        assert any(c.isdigit() for c in password)
        assert any(c in "!@#$%^&*" for c in password)


@pytest.mark.asyncio
class TestAuthenticationEndpoints:
    """Test authentication API endpoints"""
    
    @pytest.fixture
    def mock_user_service(self):
        """Mock user management service"""
        with patch('src.api.auth.get_service_client') as mock:
            client = AsyncMock()
            mock.return_value = client
            yield client
    
    @pytest.fixture
    def mock_cache(self):
        """Mock Redis cache"""
        with patch('src.api.auth.get_cache') as mock:
            cache = AsyncMock()
            mock.return_value = cache
            yield cache
    
    @pytest.fixture
    def app_client(self):
        """Create test client"""
        # Import here to avoid circular imports
        from src.main import app
        return TestClient(app)
    
    async def test_login_success(self, app_client, mock_user_service, mock_cache):
        """Test successful login"""
        # Mock user service response
        mock_user_service.post.return_value = AsyncMock(
            status_code=200,
            json=lambda: {
                "id": "12345",
                "username": "testuser",
                "permissions": ["read", "write"]
            }
        )
        
        # Make login request
        response = app_client.post(
            "/api/v1/auth/login",
            data={
                "username": "testuser",
                "password": "password123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user_id"] == "12345"
        assert data["username"] == "testuser"
        assert data["permissions"] == ["read", "write"]
    
    async def test_login_invalid_credentials(self, app_client, mock_user_service):
        """Test login with invalid credentials"""
        # Mock user service response
        mock_user_service.post.return_value = AsyncMock(
            status_code=401,
            json=lambda: {"detail": "Invalid credentials"}
        )
        
        response = app_client.post(
            "/api/v1/auth/login",
            data={
                "username": "testuser",
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == 401
    
    async def test_refresh_token(self, app_client, mock_cache, mock_user_service):
        """Test token refresh"""
        # Create refresh token
        refresh_token = token_manager.create_refresh_token(
            subject="testuser",
            user_id="12345"
        )
        
        # Mock cache check
        mock_cache.exists.return_value = True
        
        # Mock user service response
        mock_user_service.get.return_value = AsyncMock(
            status_code=200,
            json=lambda: {
                "id": "12345",
                "username": "testuser",
                "permissions": ["read", "write"]
            }
        )
        
        response = app_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert data["refresh_token"] == refresh_token
        assert data["user_id"] == "12345"
    
    async def test_logout(self, app_client, mock_cache):
        """Test logout"""
        # Create access token
        token = token_manager.create_access_token(
            subject="testuser",
            user_id="12345"
        )
        
        response = app_client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        
        # Check that token was blacklisted
        mock_cache.set.assert_called()
    
    async def test_get_current_user(self, app_client, mock_user_service):
        """Test get current user info"""
        # Create access token
        token = token_manager.create_access_token(
            subject="testuser",
            user_id="12345",
            permissions=["read"]
        )
        
        # Mock user service response
        mock_user_service.get.return_value = AsyncMock(
            status_code=200,
            json=lambda: {
                "id": "12345",
                "username": "testuser",
                "email": "test@example.com",
                "full_name": "Test User",
                "permissions": ["read"]
            }
        )
        
        response = app_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == "12345"
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"


class TestSecurityValidation:
    """Test security validation utilities"""
    
    def test_validate_password_strength(self):
        """Test password strength validation"""
        from src.core.security import security_validator
        
        # Weak password
        result = security_validator.validate_password_strength("weak")
        assert not result["is_valid"]
        assert len(result["errors"]) > 0
        
        # Strong password
        result = security_validator.validate_password_strength("StrongP@ssw0rd123")
        assert result["is_valid"]
        assert result["strength"] == "strong"
        
        # Check specific requirements
        result = security_validator.validate_password_strength("password")
        assert "uppercase letter" in str(result["errors"])
        assert "digit" in str(result["errors"])
        assert "special character" in str(result["errors"])
    
    def test_sanitize_input(self):
        """Test input sanitization"""
        from src.core.security import security_validator
        
        # XSS attempt
        malicious = '<script>alert("xss")</script>'
        sanitized = security_validator.sanitize_input(malicious)
        assert "<script>" not in sanitized
        assert "&lt;script&gt;" in sanitized
        
        # SQL injection attempt
        sql_injection = "'; DROP TABLE users; --"
        sanitized = security_validator.sanitize_input(sql_injection)
        assert "&#x27;" in sanitized  # Single quote escaped
    
    def test_validate_email(self):
        """Test email validation"""
        from src.core.security import security_validator
        
        # Valid emails
        assert security_validator.validate_email("user@example.com")
        assert security_validator.validate_email("test.user+tag@company.co.uk")
        
        # Invalid emails
        assert not security_validator.validate_email("invalid.email")
        assert not security_validator.validate_email("@example.com")
        assert not security_validator.validate_email("user@")
        assert not security_validator.validate_email("user@@example.com")