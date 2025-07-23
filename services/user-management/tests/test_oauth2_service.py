"""
Tests for OAuth2 authentication service
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from uuid import uuid4

from services.oauth2_service import OAuth2Service, GoogleOAuth2Provider, MicrosoftOAuth2Provider
from core.config import get_settings
from db.models import User, Role
from core.exceptions import AuthenticationError, ValidationError


@pytest.fixture
def oauth2_service():
    """Create OAuth2 service instance"""
    return OAuth2Service()


@pytest.fixture
def mock_oauth2_settings():
    """Mock OAuth2 settings"""
    settings = get_settings()
    settings.enable_oauth2 = True
    settings.google_oauth2_enabled = True
    settings.google_client_id = "test_google_client_id"
    settings.google_client_secret = "test_google_client_secret"
    settings.google_redirect_uri = "http://localhost:8000/api/v1/oauth2/callback/google"
    settings.google_scopes = ["openid", "email", "profile"]
    
    settings.microsoft_oauth2_enabled = True
    settings.microsoft_client_id = "test_microsoft_client_id"
    settings.microsoft_client_secret = "test_microsoft_client_secret"
    settings.microsoft_redirect_uri = "http://localhost:8000/api/v1/oauth2/callback/microsoft"
    settings.microsoft_tenant_id = "common"
    settings.microsoft_scopes = ["openid", "email", "profile"]
    
    settings.oauth2_auto_create_user = True
    settings.oauth2_auto_update_user = True
    settings.oauth2_default_role = "user"
    
    return settings


@pytest.fixture
def sample_google_user():
    """Sample Google user data"""
    return {
        "id": "google_user_123",
        "email": "testuser@gmail.com",
        "given_name": "Test",
        "family_name": "User",
        "name": "Test User",
        "picture": "https://example.com/avatar.jpg",
        "verified_email": True,
        "locale": "en"
    }


@pytest.fixture
def sample_microsoft_user():
    """Sample Microsoft user data"""
    return {
        "id": "microsoft_user_123",
        "mail": "testuser@outlook.com",
        "givenName": "Test",
        "surname": "User",
        "displayName": "Test User",
        "businessPhones": ["+1234567890"],
        "jobTitle": "Developer",
        "department": "IT",
        "officeLocation": "Building 1",
        "preferredLanguage": "en-US"
    }


@pytest.fixture
def mock_oauth2_token():
    """Mock OAuth2 token response"""
    return {
        "access_token": "test_access_token",
        "token_type": "Bearer",
        "expires_in": 3600,
        "refresh_token": "test_refresh_token",
        "scope": "openid email profile"
    }


class TestGoogleOAuth2Provider:
    """Test Google OAuth2 provider"""

    def test_initialization(self):
        """Test Google provider initialization"""
        provider = GoogleOAuth2Provider(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="http://localhost:8000/callback",
            scopes=["openid", "email", "profile"]
        )
        
        assert provider.name == "google"
        assert provider.client_id == "test_client_id"
        assert provider.client_secret == "test_client_secret"
        assert provider.redirect_uri == "http://localhost:8000/callback"
        assert provider.scopes == ["openid", "email", "profile"]
        assert provider.client is not None

    def test_get_authorization_url(self):
        """Test generating Google authorization URL"""
        provider = GoogleOAuth2Provider(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="http://localhost:8000/callback",
            scopes=["openid", "email", "profile"]
        )
        
        with patch.object(provider.client, 'create_authorization_url') as mock_create_url:
            mock_create_url.return_value = ("https://accounts.google.com/oauth2/auth?...", "state")
            
            auth_url = provider.get_authorization_url("test_state")
            
            assert auth_url.startswith("https://accounts.google.com/oauth2/auth")
            mock_create_url.assert_called_once()

    @pytest.mark.asyncio
    async def test_exchange_code_for_token_success(self, mock_oauth2_token):
        """Test successful token exchange"""
        provider = GoogleOAuth2Provider(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="http://localhost:8000/callback",
            scopes=["openid", "email", "profile"]
        )
        
        with patch.object(provider.client, 'fetch_token', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_oauth2_token
            
            token = await provider.exchange_code_for_token("test_code", "test_state")
            
            assert token == mock_oauth2_token
            mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_info_success(self, mock_oauth2_token, sample_google_user):
        """Test successful user info retrieval"""
        provider = GoogleOAuth2Provider(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="http://localhost:8000/callback",
            scopes=["openid", "email", "profile"]
        )
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = sample_google_user
            mock_response.raise_for_status.return_value = None
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            user_info = await provider.get_user_info(mock_oauth2_token)
            
            assert user_info["provider_id"] == "google_user_123"
            assert user_info["email"] == "testuser@gmail.com"
            assert user_info["first_name"] == "Test"
            assert user_info["last_name"] == "User"
            assert user_info["provider"] == "google"
            assert user_info["auth_provider"] == "oauth2"


class TestMicrosoftOAuth2Provider:
    """Test Microsoft OAuth2 provider"""

    def test_initialization(self):
        """Test Microsoft provider initialization"""
        provider = MicrosoftOAuth2Provider(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="http://localhost:8000/callback",
            scopes=["openid", "email", "profile"],
            tenant_id="common"
        )
        
        assert provider.name == "microsoft"
        assert provider.client_id == "test_client_id"
        assert provider.tenant_id == "common"
        assert provider.authorization_endpoint.endswith("common/oauth2/v2.0/authorize")

    @pytest.mark.asyncio
    async def test_get_user_info_success(self, mock_oauth2_token, sample_microsoft_user):
        """Test successful user info retrieval"""
        provider = MicrosoftOAuth2Provider(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="http://localhost:8000/callback",
            scopes=["openid", "email", "profile"],
            tenant_id="common"
        )
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = sample_microsoft_user
            mock_response.raise_for_status.return_value = None
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            user_info = await provider.get_user_info(mock_oauth2_token)
            
            assert user_info["provider_id"] == "microsoft_user_123"
            assert user_info["email"] == "testuser@outlook.com"
            assert user_info["first_name"] == "Test"
            assert user_info["last_name"] == "User"
            assert user_info["provider"] == "microsoft"
            assert user_info["auth_provider"] == "oauth2"


class TestOAuth2Service:
    """Test OAuth2 service functionality"""

    @pytest.mark.asyncio
    async def test_service_initialization_disabled(self):
        """Test service initialization when OAuth2 is disabled"""
        with patch('services.oauth2_service.settings') as mock_settings:
            mock_settings.enable_oauth2 = False
            
            service = OAuth2Service()
            
            assert len(service.providers) == 0
            assert service.get_available_providers() == []

    @pytest.mark.asyncio
    async def test_service_initialization_enabled(self, mock_oauth2_settings):
        """Test service initialization when OAuth2 is enabled"""
        with patch('services.oauth2_service.settings', mock_oauth2_settings):
            service = OAuth2Service()
            
            assert "google" in service.providers
            assert "microsoft" in service.providers
            assert len(service.providers) == 2

    def test_get_available_providers(self, mock_oauth2_settings):
        """Test getting available providers"""
        with patch('services.oauth2_service.settings', mock_oauth2_settings):
            service = OAuth2Service()
            providers = service.get_available_providers()
            
            assert "google" in providers
            assert "microsoft" in providers

    def test_generate_auth_url_disabled(self):
        """Test generating auth URL when OAuth2 is disabled"""
        with patch('services.oauth2_service.settings') as mock_settings:
            mock_settings.enable_oauth2 = False
            
            service = OAuth2Service()
            
            with pytest.raises(ValidationError, match="OAuth2 authentication is disabled"):
                service.generate_auth_url("google")

    def test_generate_auth_url_invalid_provider(self, mock_oauth2_settings):
        """Test generating auth URL with invalid provider"""
        with patch('services.oauth2_service.settings', mock_oauth2_settings):
            service = OAuth2Service()
            
            with pytest.raises(ValidationError, match="Provider 'invalid' is not available"):
                service.generate_auth_url("invalid")

    def test_generate_auth_url_success(self, mock_oauth2_settings):
        """Test successful auth URL generation"""
        with patch('services.oauth2_service.settings', mock_oauth2_settings):
            service = OAuth2Service()
            
            with patch.object(service.providers["google"], 'get_authorization_url') as mock_get_url:
                mock_get_url.return_value = "https://accounts.google.com/oauth2/auth?..."
                
                result = service.generate_auth_url("google")
                
                assert "authorization_url" in result
                assert "state" in result
                assert "provider" in result
                assert result["provider"] == "google"

    @pytest.mark.asyncio
    async def test_authenticate_with_code_success(self, mock_oauth2_settings, mock_db_session, sample_google_user):
        """Test successful OAuth2 authentication"""
        with patch('services.oauth2_service.settings', mock_oauth2_settings):
            service = OAuth2Service()
            
            # Mock provider methods
            with patch.object(service.providers["google"], 'exchange_code_for_token', new_callable=AsyncMock) as mock_exchange:
                with patch.object(service.providers["google"], 'get_user_info', new_callable=AsyncMock) as mock_get_info:
                    with patch.object(service, 'get_or_create_user', new_callable=AsyncMock) as mock_get_or_create:
                        
                        mock_exchange.return_value = {"access_token": "test_token"}
                        mock_get_info.return_value = {
                            "email": "testuser@gmail.com",
                            "first_name": "Test",
                            "last_name": "User",
                            "provider": "google",
                            "auth_provider": "oauth2"
                        }
                        
                        mock_user = User(id=uuid4(), email="testuser@gmail.com")
                        mock_get_or_create.return_value = mock_user
                        
                        user = await service.authenticate_with_code("google", "test_code", "test_state", mock_db_session)
                        
                        assert user == mock_user
                        mock_exchange.assert_called_once()
                        mock_get_info.assert_called_once()
                        mock_get_or_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_create_user_existing(self, mock_oauth2_settings, mock_db_session):
        """Test getting existing user"""
        with patch('services.oauth2_service.settings', mock_oauth2_settings):
            service = OAuth2Service()
            
            existing_user = User(
                id=uuid4(),
                email='testuser@gmail.com',
                first_name='Test',
                last_name='User',
                is_active=True,
                auth_provider='oauth2'
            )
            
            mock_db_session.execute.return_value.scalar_one_or_none.return_value = existing_user
            
            user_info = {
                'email': 'testuser@gmail.com',
                'first_name': 'Test Updated',
                'last_name': 'User Updated',
                'auth_provider': 'oauth2'
            }
            
            with patch.object(service, '_update_user_from_oauth2', new_callable=AsyncMock) as mock_update:
                result = await service.get_or_create_user(mock_db_session, user_info)
                
                assert result == existing_user
                mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_create_user_new(self, mock_oauth2_settings, mock_db_session):
        """Test creating new user"""
        with patch('services.oauth2_service.settings', mock_oauth2_settings):
            service = OAuth2Service()
            
            mock_db_session.execute.return_value.scalar_one_or_none.side_effect = [
                None,  # No existing user
                Mock(scalar_one_or_none=Mock(return_value=Mock(id=uuid4(), name="user")))  # Default role
            ]
            
            user_info = {
                'email': 'newuser@gmail.com',
                'first_name': 'New',
                'last_name': 'User',
                'auth_provider': 'oauth2',
                'email_verified': True
            }
            
            result = await service.get_or_create_user(mock_db_session, user_info)
            
            assert result.email == 'newuser@gmail.com'
            assert result.auth_provider == 'oauth2'
            assert result.is_verified is True

    @pytest.mark.asyncio
    async def test_get_or_create_user_auto_create_disabled(self, mock_oauth2_settings, mock_db_session):
        """Test error when auto-create is disabled"""
        mock_oauth2_settings.oauth2_auto_create_user = False
        
        with patch('services.oauth2_service.settings', mock_oauth2_settings):
            service = OAuth2Service()
            
            mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
            
            user_info = {'email': 'newuser@gmail.com'}
            
            with pytest.raises(AuthenticationError, match="User not found and auto-creation is disabled"):
                await service.get_or_create_user(mock_db_session, user_info)

    @pytest.mark.asyncio
    async def test_test_provider_connection_disabled(self):
        """Test provider connection test when OAuth2 is disabled"""
        with patch('services.oauth2_service.settings') as mock_settings:
            mock_settings.enable_oauth2 = False
            
            service = OAuth2Service()
            result = await service.test_provider_connection("google")
            
            assert result["status"] == "disabled"
            assert "OAuth2 authentication is disabled" in result["message"]

    @pytest.mark.asyncio
    async def test_test_provider_connection_success(self, mock_oauth2_settings):
        """Test successful provider connection test"""
        with patch('services.oauth2_service.settings', mock_oauth2_settings):
            service = OAuth2Service()
            
            with patch.object(service.providers["google"], 'get_authorization_url') as mock_get_url:
                mock_get_url.return_value = "https://accounts.google.com/oauth2/auth?..."
                
                result = await service.test_provider_connection("google")
                
                assert result["status"] == "success"
                assert result["provider"] == "google"
                assert "test_auth_url" in result


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    session = AsyncMock()
    session.execute.return_value.scalar_one_or_none = Mock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.add = Mock()
    return session