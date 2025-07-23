"""
Tests for SAML authentication service
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from uuid import uuid4
import base64

from services.saml_service import SAMLService
from core.config import get_settings
from db.models import User, Role
from core.exceptions import AuthenticationError, ValidationError


@pytest.fixture
def saml_service():
    """Create SAML service instance"""
    return SAMLService()


@pytest.fixture
def mock_saml_settings():
    """Mock SAML settings"""
    settings = get_settings()
    settings.enable_saml = True
    settings.saml_sp_entity_id = "http://localhost:8001/saml"
    settings.saml_sp_acs_url = "http://localhost:8001/api/v1/saml/acs"
    settings.saml_sp_sls_url = "http://localhost:8001/api/v1/saml/sls"
    settings.saml_sp_x509_cert = "-----BEGIN CERTIFICATE-----\nMIIC...SP CERT...\n-----END CERTIFICATE-----"
    settings.saml_sp_private_key = "-----BEGIN PRIVATE KEY-----\nMIIE...SP KEY...\n-----END PRIVATE KEY-----"
    
    settings.saml_idp_entity_id = "http://idp.example.com"
    settings.saml_idp_sso_url = "http://idp.example.com/sso"
    settings.saml_idp_sls_url = "http://idp.example.com/sls"
    settings.saml_idp_x509_cert = "-----BEGIN CERTIFICATE-----\nMIIC...IDP CERT...\n-----END CERTIFICATE-----"
    
    settings.saml_auto_create_user = True
    settings.saml_auto_update_user = True
    settings.saml_default_role = "user"
    settings.saml_attribute_mapping = {
        "email": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
        "first_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
        "last_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname",
        "groups": "http://schemas.microsoft.com/ws/2008/06/identity/claims/groups"
    }
    
    settings.saml_name_id_format = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
    settings.saml_authn_requests_signed = True
    settings.saml_logout_requests_signed = True
    settings.saml_want_assertions_signed = True
    settings.saml_want_assertions_encrypted = False
    
    return settings


@pytest.fixture
def sample_saml_attributes():
    """Sample SAML response attributes"""
    return {
        "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress": ["testuser@example.com"],
        "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname": ["Test"],
        "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname": ["User"],
        "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name": ["Test User"],
        "http://schemas.microsoft.com/ws/2008/06/identity/claims/groups": [
            "users",
            "developers"
        ]
    }


@pytest.fixture
def mock_request_data():
    """Mock request data for SAML"""
    return {
        "https": "on",
        "http_host": "localhost:8001",
        "server_port": 8001,
        "script_name": "/api/v1/saml/acs",
        "get_data": {},
        "post_data": {}
    }


class TestSAMLService:
    """Test SAML service functionality"""

    @pytest.mark.asyncio
    async def test_initialization_disabled(self):
        """Test service initialization when SAML is disabled"""
        with patch('services.saml_service.settings') as mock_settings:
            mock_settings.enable_saml = False
            
            service = SAMLService()
            
            assert service._saml_settings is None

    @pytest.mark.asyncio
    async def test_initialization_enabled(self, mock_saml_settings):
        """Test service initialization when SAML is enabled"""
        with patch('services.saml_service.settings', mock_saml_settings):
            service = SAMLService()
            
            assert service._saml_settings is not None
            assert service._saml_settings["sp"]["entityId"] == mock_saml_settings.saml_sp_entity_id
            assert service._saml_settings["idp"]["entityId"] == mock_saml_settings.saml_idp_entity_id

    def test_prepare_flask_request(self, saml_service):
        """Test preparing Flask-style request for python3-saml"""
        request_data = {
            "https": "on",
            "http_host": "example.com",
            "server_port": 443,
            "script_name": "/saml/acs",
            "get_data": {"foo": "bar"},
            "post_data": {"SAMLResponse": "base64encoded"}
        }
        
        prepared = saml_service._prepare_flask_request(request_data)
        
        assert prepared["https"] == "on"
        assert prepared["http_host"] == "example.com"
        assert prepared["server_port"] == 443
        assert prepared["get_data"] == {"foo": "bar"}
        assert prepared["post_data"] == {"SAMLResponse": "base64encoded"}

    def test_create_auth_request_disabled(self, saml_service):
        """Test creating auth request when SAML is disabled"""
        with patch('services.saml_service.settings') as mock_settings:
            mock_settings.enable_saml = False
            service = SAMLService()
            
            with pytest.raises(ValidationError, match="SAML authentication is disabled"):
                service.create_auth_request({})

    @patch('services.saml_service.OneLogin_Saml2_Auth')
    def test_create_auth_request_success(self, mock_auth_class, saml_service, mock_saml_settings, mock_request_data):
        """Test successful auth request creation"""
        with patch('services.saml_service.settings', mock_saml_settings):
            service = SAMLService()
            service._initialize_saml_settings()
            
            # Mock auth instance
            mock_auth = Mock()
            mock_auth.login.return_value = "https://idp.example.com/sso?SAMLRequest=..."
            mock_auth_class.return_value = mock_auth
            
            sso_url = service.create_auth_request(mock_request_data, return_to="/dashboard")
            
            assert sso_url.startswith("https://idp.example.com/sso")
            mock_auth.login.assert_called_once_with(return_to="/dashboard")

    @pytest.mark.asyncio
    @patch('services.saml_service.OneLogin_Saml2_Auth')
    async def test_process_auth_response_success(self, mock_auth_class, saml_service, mock_saml_settings, 
                                               mock_request_data, sample_saml_attributes, mock_db_session):
        """Test successful auth response processing"""
        with patch('services.saml_service.settings', mock_saml_settings):
            service = SAMLService()
            service._initialize_saml_settings()
            
            # Mock auth instance
            mock_auth = Mock()
            mock_auth.process_response.return_value = None
            mock_auth.get_errors.return_value = []
            mock_auth.is_authenticated.return_value = True
            mock_auth.get_attributes.return_value = sample_saml_attributes
            mock_auth.get_nameid.return_value = "testuser@example.com"
            mock_auth.get_nameid_format.return_value = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
            mock_auth.get_session_index.return_value = "session_12345"
            mock_auth_class.return_value = mock_auth
            
            # Mock user creation
            with patch.object(service, 'get_or_create_user', new_callable=AsyncMock) as mock_get_or_create:
                mock_user = User(id=uuid4(), email="testuser@example.com")
                mock_get_or_create.return_value = mock_user
                
                user = await service.process_auth_response(mock_request_data, mock_db_session)
                
                assert user == mock_user
                assert user.saml_session_index == "session_12345"
                mock_auth.process_response.assert_called_once()
                mock_get_or_create.assert_called_once()

    @pytest.mark.asyncio
    @patch('services.saml_service.OneLogin_Saml2_Auth')
    async def test_process_auth_response_error(self, mock_auth_class, saml_service, mock_saml_settings, 
                                             mock_request_data, mock_db_session):
        """Test auth response processing with errors"""
        with patch('services.saml_service.settings', mock_saml_settings):
            service = SAMLService()
            service._initialize_saml_settings()
            
            # Mock auth instance with errors
            mock_auth = Mock()
            mock_auth.process_response.return_value = None
            mock_auth.get_errors.return_value = ["Invalid SAML response"]
            mock_auth.get_last_error_reason.return_value = "Signature validation failed"
            mock_auth_class.return_value = mock_auth
            
            with pytest.raises(AuthenticationError, match="SAML authentication failed"):
                await service.process_auth_response(mock_request_data, mock_db_session)

    def test_extract_user_info(self, saml_service, sample_saml_attributes):
        """Test extracting user info from SAML attributes"""
        with patch('services.saml_service.settings') as mock_settings:
            mock_settings.enable_saml = True
            service = SAMLService()
            service._attribute_mapping = {
                "email": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
                "first_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
                "last_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname",
                "groups": "http://schemas.microsoft.com/ws/2008/06/identity/claims/groups"
            }
            
            user_info = service._extract_user_info("testuser@example.com", sample_saml_attributes)
            
            assert user_info["email"] == "testuser@example.com"
            assert user_info["first_name"] == "Test"
            assert user_info["last_name"] == "User"
            assert user_info["groups"] == ["users", "developers"]
            assert user_info["auth_provider"] == "saml"

    def test_determine_user_role_admin(self, saml_service, mock_saml_settings):
        """Test determining admin role from groups"""
        with patch('services.saml_service.settings', mock_saml_settings):
            service = SAMLService()
            
            groups = ["users", "administrators", "developers"]
            role = service._determine_user_role(groups)
            
            assert role == "admin"

    def test_determine_user_role_editor(self, saml_service, mock_saml_settings):
        """Test determining editor role from groups"""
        with patch('services.saml_service.settings', mock_saml_settings):
            service = SAMLService()
            
            groups = ["users", "editors", "content-team"]
            role = service._determine_user_role(groups)
            
            assert role == "editor"

    def test_determine_user_role_default(self, saml_service, mock_saml_settings):
        """Test determining default role"""
        with patch('services.saml_service.settings', mock_saml_settings):
            service = SAMLService()
            
            groups = ["users", "employees"]
            role = service._determine_user_role(groups)
            
            assert role == "user"

    @pytest.mark.asyncio
    async def test_get_or_create_user_existing(self, saml_service, mock_saml_settings, mock_db_session):
        """Test getting existing user"""
        with patch('services.saml_service.settings', mock_saml_settings):
            service = SAMLService()
            
            existing_user = User(
                id=uuid4(),
                email='testuser@example.com',
                first_name='Test',
                last_name='User',
                is_active=True,
                auth_provider='saml'
            )
            
            mock_db_session.execute.return_value.scalar_one_or_none.return_value = existing_user
            
            user_info = {
                'email': 'testuser@example.com',
                'first_name': 'Test Updated',
                'last_name': 'User Updated',
                'auth_provider': 'saml'
            }
            
            with patch.object(service, '_update_user_from_saml', new_callable=AsyncMock) as mock_update:
                result = await service.get_or_create_user(mock_db_session, user_info)
                
                assert result == existing_user
                mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_create_user_new(self, saml_service, mock_saml_settings, mock_db_session):
        """Test creating new user"""
        with patch('services.saml_service.settings', mock_saml_settings):
            service = SAMLService()
            
            # No existing user
            mock_db_session.execute.return_value.scalar_one_or_none.side_effect = [
                None,  # No existing user
                Mock(scalar_one_or_none=Mock(return_value=Mock(id=uuid4(), name="user")))  # Default role
            ]
            
            user_info = {
                'email': 'newuser@example.com',
                'first_name': 'New',
                'last_name': 'User',
                'auth_provider': 'saml',
                'groups': []
            }
            
            result = await service.get_or_create_user(mock_db_session, user_info)
            
            assert result.email == 'newuser@example.com'
            assert result.auth_provider == 'saml'
            assert result.is_verified is True

    @pytest.mark.asyncio
    async def test_get_or_create_user_auto_create_disabled(self, saml_service, mock_saml_settings, mock_db_session):
        """Test error when auto-create is disabled"""
        mock_saml_settings.saml_auto_create_user = False
        
        with patch('services.saml_service.settings', mock_saml_settings):
            service = SAMLService()
            
            mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
            
            user_info = {'email': 'newuser@example.com'}
            
            with pytest.raises(AuthenticationError, match="User not found and auto-creation is disabled"):
                await service.get_or_create_user(mock_db_session, user_info)

    @patch('services.saml_service.OneLogin_Saml2_Auth')
    def test_create_logout_request_success(self, mock_auth_class, saml_service, mock_saml_settings, mock_request_data):
        """Test successful logout request creation"""
        with patch('services.saml_service.settings', mock_saml_settings):
            service = SAMLService()
            service._initialize_saml_settings()
            
            # Mock auth instance
            mock_auth = Mock()
            mock_auth.logout.return_value = "https://idp.example.com/sls?SAMLRequest=..."
            mock_auth_class.return_value = mock_auth
            
            slo_url = service.create_logout_request(
                mock_request_data, 
                name_id="testuser@example.com",
                session_index="session_12345"
            )
            
            assert slo_url.startswith("https://idp.example.com/sls")
            mock_auth.logout.assert_called_once_with(
                name_id="testuser@example.com",
                session_index="session_12345"
            )

    @patch('services.saml_service.OneLogin_Saml2_Settings')
    def test_get_metadata_success(self, mock_settings_class, saml_service, mock_saml_settings):
        """Test successful metadata generation"""
        with patch('services.saml_service.settings', mock_saml_settings):
            service = SAMLService()
            service._initialize_saml_settings()
            
            # Mock settings instance
            mock_settings = Mock()
            mock_settings.get_sp_metadata.return_value = "<EntityDescriptor>...</EntityDescriptor>"
            mock_settings.validate_metadata.return_value = []
            mock_settings_class.return_value = mock_settings
            
            metadata = service.get_metadata()
            
            assert metadata == "<EntityDescriptor>...</EntityDescriptor>"
            mock_settings.get_sp_metadata.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_configuration_disabled(self, saml_service):
        """Test configuration test when SAML is disabled"""
        with patch('services.saml_service.settings') as mock_settings:
            mock_settings.enable_saml = False
            service = SAMLService()
            
            result = await service.test_configuration()
            
            assert result["status"] == "disabled"
            assert "SAML authentication is disabled" in result["message"]

    @pytest.mark.asyncio
    @patch('services.saml_service.OneLogin_Saml2_Settings')
    async def test_test_configuration_success(self, mock_settings_class, saml_service, mock_saml_settings):
        """Test successful configuration test"""
        with patch('services.saml_service.settings', mock_saml_settings):
            service = SAMLService()
            service._initialize_saml_settings()
            
            # Mock settings instance
            mock_settings = Mock()
            mock_settings.check_settings.return_value = []
            mock_settings_class.return_value = mock_settings
            
            with patch.object(service, 'get_metadata') as mock_get_metadata:
                mock_get_metadata.return_value = "<EntityDescriptor>...</EntityDescriptor>"
                
                result = await service.test_configuration()
                
                assert result["status"] == "success"
                assert result["sp_entity_id"] == mock_saml_settings.saml_sp_entity_id
                assert result["idp_entity_id"] == mock_saml_settings.saml_idp_entity_id
                assert result["has_metadata"] is True


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