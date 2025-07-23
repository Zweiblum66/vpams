"""
Tests for LDAP authentication service
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from uuid import uuid4

from services.ldap_service import LDAPService, LDAPConnectionPool
from core.config import get_settings
from db.models import User, Role, Group
from core.exceptions import AuthenticationError, ValidationError


@pytest.fixture
def ldap_service():
    """Create LDAP service instance"""
    return LDAPService()


@pytest.fixture
def mock_ldap_settings():
    """Mock LDAP settings"""
    settings = get_settings()
    settings.enable_ldap = True
    settings.ldap_server = "ldap.example.com"
    settings.ldap_port = 389
    settings.ldap_use_ssl = False
    settings.ldap_use_tls = False
    settings.ldap_base_dn = "dc=example,dc=com"
    settings.ldap_bind_dn = "cn=admin,dc=example,dc=com"
    settings.ldap_bind_password = "admin_password"
    settings.ldap_user_search_base = "ou=users,dc=example,dc=com"
    settings.ldap_user_search_filter = "(uid={username})"
    settings.ldap_user_object_class = "inetOrgPerson"
    settings.ldap_username_attr = "uid"
    settings.ldap_email_attr = "mail"
    settings.ldap_first_name_attr = "givenName"
    settings.ldap_last_name_attr = "sn"
    settings.ldap_display_name_attr = "displayName"
    settings.ldap_phone_attr = "telephoneNumber"
    settings.ldap_department_attr = "department"
    settings.ldap_organization_attr = "organization"
    settings.ldap_groups_attr = "memberOf"
    settings.ldap_auto_create_user = True
    settings.ldap_auto_update_user = True
    settings.ldap_default_role = "user"
    settings.ldap_admin_groups = ["admins"]
    settings.ldap_editor_groups = ["editors"]
    settings.ldap_viewer_groups = ["viewers"]
    settings.ldap_group_search_base = "ou=groups,dc=example,dc=com"
    settings.ldap_group_search_filter = "(cn={groupname})"
    settings.ldap_group_object_class = "groupOfNames"
    settings.ldap_group_name_attr = "cn"
    settings.ldap_group_member_attr = "member"
    return settings


@pytest.fixture
def mock_ldap_connection():
    """Mock LDAP connection"""
    conn = Mock()
    conn.simple_bind_s = Mock()
    conn.search_s = Mock()
    conn.start_tls_s = Mock()
    conn.set_option = Mock()
    return conn


@pytest.fixture
def sample_ldap_user():
    """Sample LDAP user attributes"""
    return {
        'dn': 'uid=testuser,ou=users,dc=example,dc=com',
        'attributes': {
            'uid': [b'testuser'],
            'mail': [b'testuser@example.com'],
            'givenName': [b'Test'],
            'sn': [b'User'],
            'displayName': [b'Test User'],
            'telephoneNumber': [b'+1234567890'],
            'department': [b'IT'],
            'organization': [b'Example Corp'],
            'memberOf': [b'cn=users,ou=groups,dc=example,dc=com']
        }
    }


class TestLDAPConnectionPool:
    """Test LDAP connection pool"""

    def test_connection_pool_initialization(self):
        """Test connection pool initialization"""
        pool = LDAPConnectionPool(max_connections=3)
        assert pool.max_connections == 3
        assert pool.connections == []
        assert pool.in_use == set()

    @patch('services.ldap_service.ldap.initialize')
    def test_get_connection_creates_new(self, mock_initialize, mock_ldap_settings):
        """Test getting new connection from pool"""
        mock_conn = Mock()
        mock_initialize.return_value = mock_conn
        
        pool = LDAPConnectionPool(max_connections=2)
        
        with patch('services.ldap_service.settings', mock_ldap_settings):
            conn = pool.get_connection()
            
            assert conn == mock_conn
            assert len(pool.connections) == 1
            assert conn in pool.in_use

    @patch('services.ldap_service.ldap.initialize')
    def test_get_connection_reuses_existing(self, mock_initialize, mock_ldap_settings):
        """Test reusing existing connection from pool"""
        mock_conn = Mock()
        mock_initialize.return_value = mock_conn
        
        pool = LDAPConnectionPool(max_connections=2)
        
        with patch('services.ldap_service.settings', mock_ldap_settings):
            # Get first connection
            conn1 = pool.get_connection()
            pool.return_connection(conn1)
            
            # Get second connection (should reuse)
            conn2 = pool.get_connection()
            
            assert conn1 == conn2
            assert len(pool.connections) == 1

    def test_return_connection(self):
        """Test returning connection to pool"""
        pool = LDAPConnectionPool()
        mock_conn = Mock()
        pool.connections = [mock_conn]
        pool.in_use = {mock_conn}
        
        pool.return_connection(mock_conn)
        
        assert mock_conn not in pool.in_use


class TestLDAPService:
    """Test LDAP service functionality"""

    @pytest.mark.asyncio
    async def test_authenticate_user_disabled(self, ldap_service):
        """Test authentication when LDAP is disabled"""
        with patch('services.ldap_service.settings') as mock_settings:
            mock_settings.enable_ldap = False
            
            with pytest.raises(AuthenticationError, match="LDAP authentication is disabled"):
                await ldap_service.authenticate_user("testuser", "password")

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, ldap_service, mock_ldap_settings, sample_ldap_user):
        """Test successful LDAP authentication"""
        mock_conn = Mock()
        mock_conn.simple_bind_s.return_value = True
        mock_conn.search_s.return_value = [(sample_ldap_user['dn'], sample_ldap_user['attributes'])]
        
        with patch('services.ldap_service.settings', mock_ldap_settings):
            with patch.object(ldap_service.connection_pool, 'get_connection', return_value=mock_conn):
                with patch.object(ldap_service.connection_pool, 'return_connection'):
                    with patch.object(ldap_service, '_get_user_groups', return_value=['users']):
                        result = await ldap_service.authenticate_user("testuser", "password")
                        
                        assert result is not None
                        assert result['username'] == 'testuser'
                        assert result['email'] == 'testuser@example.com'
                        assert result['first_name'] == 'Test'
                        assert result['last_name'] == 'User'
                        assert result['auth_provider'] == 'ldap'

    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, ldap_service, mock_ldap_settings):
        """Test authentication when user not found"""
        mock_conn = Mock()
        mock_conn.simple_bind_s.return_value = True
        mock_conn.search_s.return_value = []  # No user found
        
        with patch('services.ldap_service.settings', mock_ldap_settings):
            with patch.object(ldap_service.connection_pool, 'get_connection', return_value=mock_conn):
                with patch.object(ldap_service.connection_pool, 'return_connection'):
                    result = await ldap_service.authenticate_user("nonexistent", "password")
                    
                    assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_password(self, ldap_service, mock_ldap_settings, sample_ldap_user):
        """Test authentication with invalid password"""
        mock_conn = Mock()
        mock_conn.simple_bind_s.side_effect = [True, Exception("Invalid credentials")]
        mock_conn.search_s.return_value = [(sample_ldap_user['dn'], sample_ldap_user['attributes'])]
        
        with patch('services.ldap_service.settings', mock_ldap_settings):
            with patch.object(ldap_service.connection_pool, 'get_connection', return_value=mock_conn):
                with patch.object(ldap_service.connection_pool, 'return_connection'):
                    result = await ldap_service.authenticate_user("testuser", "wrongpassword")
                    
                    assert result is None

    def test_extract_user_info(self, ldap_service, sample_ldap_user):
        """Test extracting user information from LDAP attributes"""
        groups = ['users', 'developers']
        
        result = ldap_service._extract_user_info(sample_ldap_user['attributes'], groups)
        
        assert result['username'] == 'testuser'
        assert result['email'] == 'testuser@example.com'
        assert result['first_name'] == 'Test'
        assert result['last_name'] == 'User'
        assert result['display_name'] == 'Test User'
        assert result['phone'] == '+1234567890'
        assert result['department'] == 'IT'
        assert result['organization'] == 'Example Corp'
        assert result['groups'] == groups
        assert result['role'] == 'user'  # default role
        assert result['is_active'] is True
        assert result['is_verified'] is True
        assert result['auth_provider'] == 'ldap'

    def test_determine_user_role_admin(self, ldap_service, mock_ldap_settings):
        """Test determining user role for admin user"""
        with patch('services.ldap_service.settings', mock_ldap_settings):
            groups = ['admins', 'users']
            role = ldap_service._determine_user_role(groups)
            assert role == 'admin'

    def test_determine_user_role_editor(self, ldap_service, mock_ldap_settings):
        """Test determining user role for editor user"""
        with patch('services.ldap_service.settings', mock_ldap_settings):
            groups = ['editors', 'users']
            role = ldap_service._determine_user_role(groups)
            assert role == 'editor'

    def test_determine_user_role_viewer(self, ldap_service, mock_ldap_settings):
        """Test determining user role for viewer user"""
        with patch('services.ldap_service.settings', mock_ldap_settings):
            groups = ['viewers', 'users']
            role = ldap_service._determine_user_role(groups)
            assert role == 'viewer'

    def test_determine_user_role_default(self, ldap_service, mock_ldap_settings):
        """Test determining user role with default role"""
        with patch('services.ldap_service.settings', mock_ldap_settings):
            groups = ['users']
            role = ldap_service._determine_user_role(groups)
            assert role == 'user'

    @pytest.mark.asyncio
    async def test_get_or_create_user_existing(self, ldap_service, mock_db_session):
        """Test getting existing user"""
        existing_user = User(
            id=uuid4(),
            email='testuser@example.com',
            first_name='Test',
            last_name='User',
            is_active=True,
            auth_provider='ldap'
        )
        
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = existing_user
        
        user_info = {
            'email': 'testuser@example.com',
            'first_name': 'Test Updated',
            'last_name': 'User Updated',
            'is_active': True,
            'auth_provider': 'ldap'
        }
        
        with patch('services.ldap_service.settings') as mock_settings:
            mock_settings.ldap_auto_update_user = True
            
            with patch.object(ldap_service, '_update_user_from_ldap') as mock_update:
                result = await ldap_service.get_or_create_user(mock_db_session, user_info)
                
                assert result == existing_user
                mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_create_user_new(self, ldap_service, mock_db_session):
        """Test creating new user"""
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
        
        user_info = {
            'email': 'newuser@example.com',
            'username': 'newuser',
            'first_name': 'New',
            'last_name': 'User',
            'is_active': True,
            'auth_provider': 'ldap'
        }
        
        with patch('services.ldap_service.settings') as mock_settings:
            mock_settings.ldap_auto_create_user = True
            
            with patch.object(ldap_service, '_create_user_from_ldap') as mock_create:
                mock_user = User(id=uuid4(), email='newuser@example.com')
                mock_create.return_value = mock_user
                
                result = await ldap_service.get_or_create_user(mock_db_session, user_info)
                
                assert result == mock_user
                mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_create_user_auto_create_disabled(self, ldap_service, mock_db_session):
        """Test error when auto-create is disabled"""
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
        
        user_info = {'email': 'newuser@example.com'}
        
        with patch('services.ldap_service.settings') as mock_settings:
            mock_settings.ldap_auto_create_user = False
            
            with pytest.raises(AuthenticationError, match="User not found and auto-creation is disabled"):
                await ldap_service.get_or_create_user(mock_db_session, user_info)

    @pytest.mark.asyncio
    async def test_test_connection_success(self, ldap_service, mock_ldap_settings):
        """Test successful connection test"""
        mock_conn = Mock()
        mock_conn.simple_bind_s.return_value = True
        
        with patch('services.ldap_service.settings', mock_ldap_settings):
            with patch.object(ldap_service.connection_pool, 'get_connection', return_value=mock_conn):
                with patch.object(ldap_service.connection_pool, 'return_connection'):
                    with patch.object(ldap_service, '_search_user', return_value=None):
                        result = await ldap_service.test_connection()
                        
                        assert result['status'] == 'success'
                        assert result['server'] == 'ldap.example.com'
                        assert result['port'] == 389

    @pytest.mark.asyncio
    async def test_test_connection_disabled(self, ldap_service):
        """Test connection test when LDAP is disabled"""
        with patch('services.ldap_service.settings') as mock_settings:
            mock_settings.enable_ldap = False
            
            result = await ldap_service.test_connection()
            
            assert result['status'] == 'disabled'
            assert 'LDAP authentication is disabled' in result['message']

    @pytest.mark.asyncio
    async def test_test_connection_error(self, ldap_service, mock_ldap_settings):
        """Test connection test with error"""
        mock_conn = Mock()
        mock_conn.simple_bind_s.side_effect = Exception("Connection failed")
        
        with patch('services.ldap_service.settings', mock_ldap_settings):
            with patch.object(ldap_service.connection_pool, 'get_connection', return_value=mock_conn):
                with patch.object(ldap_service.connection_pool, 'return_connection'):
                    result = await ldap_service.test_connection()
                    
                    assert result['status'] == 'error'
                    assert 'Connection failed' in result['message']

    @pytest.mark.asyncio
    async def test_sync_users_disabled(self, ldap_service, mock_db_session):
        """Test user sync when LDAP is disabled"""
        with patch('services.ldap_service.settings') as mock_settings:
            mock_settings.enable_ldap = False
            
            with pytest.raises(ValidationError, match="LDAP authentication is disabled"):
                await ldap_service.sync_users(mock_db_session)

    @pytest.mark.asyncio
    async def test_sync_users_success(self, ldap_service, mock_ldap_settings, mock_db_session, sample_ldap_user):
        """Test successful user sync"""
        mock_conn = Mock()
        mock_conn.simple_bind_s.return_value = True
        mock_conn.search_s.return_value = [(sample_ldap_user['dn'], sample_ldap_user['attributes'])]
        
        with patch('services.ldap_service.settings', mock_ldap_settings):
            with patch.object(ldap_service.connection_pool, 'get_connection', return_value=mock_conn):
                with patch.object(ldap_service.connection_pool, 'return_connection'):
                    with patch.object(ldap_service, '_get_user_groups', return_value=['users']):
                        with patch.object(ldap_service, 'get_or_create_user') as mock_get_or_create:
                            mock_user = User(id=uuid4(), email='testuser@example.com')
                            mock_get_or_create.return_value = mock_user
                            
                            result = await ldap_service.sync_users(mock_db_session)
                            
                            assert result['status'] == 'completed'
                            assert result['synced_users'] == 1
                            assert result['errors'] == 0
                            assert 'testuser@example.com' in result['users']


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    session = AsyncMock()
    session.execute.return_value.scalar_one_or_none = Mock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session