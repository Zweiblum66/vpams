"""
Test cases for permission checking middleware

This module tests the permission checking middleware to ensure proper
access control functionality.
"""

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, MagicMock

from api.dependencies import (
    require_permission,
    require_role,
    require_any_permission,
    require_all_permissions,
    require_resource_permission,
    check_ownership_or_permission,
    get_user_permissions,
    get_user_roles
)
from core.permissions import UserPermissions, AssetPermissions
from db.models import User, Role, Permission
from services.rbac_service import RBACService


class TestPermissionMiddleware:
    """Test permission checking middleware"""
    
    @pytest.fixture
    def mock_user(self):
        """Create a mock user"""
        user = MagicMock(spec=User)
        user.id = "user-123"
        user.email = "test@example.com"
        user.is_active = True
        user.is_verified = True
        user.roles = []
        return user
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session"""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def mock_rbac_service(self):
        """Create a mock RBAC service"""
        return AsyncMock(spec=RBACService)
    
    @pytest.mark.asyncio
    async def test_require_permission_success(self, mock_user, mock_db, mock_rbac_service):
        """Test successful permission check"""
        # Mock RBAC service to return True for permission check
        mock_rbac_service.check_user_permission.return_value = True
        
        # Create permission checker
        permission_checker = require_permission(UserPermissions.READ)
        
        # Mock the dependency injection
        with pytest.MonkeyPatch.context() as m:
            m.setattr("api.dependencies.RBACService", lambda: mock_rbac_service)
            
            # Should not raise exception
            result = await permission_checker(mock_user, mock_db)
            assert result == mock_user
    
    @pytest.mark.asyncio
    async def test_require_permission_denied(self, mock_user, mock_db, mock_rbac_service):
        """Test permission check denial"""
        # Mock RBAC service to return False for permission check
        mock_rbac_service.check_user_permission.return_value = False
        
        # Create permission checker
        permission_checker = require_permission(UserPermissions.ADMIN)
        
        # Mock the dependency injection
        with pytest.MonkeyPatch.context() as m:
            m.setattr("api.dependencies.RBACService", lambda: mock_rbac_service)
            
            # Should raise 403 exception
            with pytest.raises(HTTPException) as exc_info:
                await permission_checker(mock_user, mock_db)
            
            assert exc_info.value.status_code == 403
            assert "Permission 'user:admin' required" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_require_role_success(self, mock_user, mock_db):
        """Test successful role check"""
        # Mock user roles
        mock_role = MagicMock(spec=Role)
        mock_role.name = "admin"
        mock_role.is_active = True
        mock_user.roles = [mock_role]
        
        # Create role checker
        role_checker = require_role("admin")
        
        # Should not raise exception
        result = await role_checker(mock_user, mock_db)
        assert result == mock_user
    
    @pytest.mark.asyncio
    async def test_require_role_denied(self, mock_user, mock_db):
        """Test role check denial"""
        # Mock user with no roles
        mock_user.roles = []
        
        # Create role checker
        role_checker = require_role("admin")
        
        # Should raise 403 exception
        with pytest.raises(HTTPException) as exc_info:
            await role_checker(mock_user, mock_db)
        
        assert exc_info.value.status_code == 403
        assert "Role 'admin' required" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_require_any_permission_success(self, mock_user, mock_db, mock_rbac_service):
        """Test successful any permission check"""
        # Mock RBAC service to return True for second permission
        mock_rbac_service.check_user_permission.side_effect = [False, True]
        
        # Create permission checker
        permission_checker = require_any_permission(UserPermissions.ADMIN, UserPermissions.READ)
        
        # Mock the dependency injection
        with pytest.MonkeyPatch.context() as m:
            m.setattr("api.dependencies.RBACService", lambda: mock_rbac_service)
            
            # Should not raise exception
            result = await permission_checker(mock_user, mock_db)
            assert result == mock_user
    
    @pytest.mark.asyncio
    async def test_require_any_permission_denied(self, mock_user, mock_db, mock_rbac_service):
        """Test any permission check denial"""
        # Mock RBAC service to return False for all permissions
        mock_rbac_service.check_user_permission.return_value = False
        
        # Create permission checker
        permission_checker = require_any_permission(UserPermissions.ADMIN, UserPermissions.WRITE)
        
        # Mock the dependency injection
        with pytest.MonkeyPatch.context() as m:
            m.setattr("api.dependencies.RBACService", lambda: mock_rbac_service)
            
            # Should raise 403 exception
            with pytest.raises(HTTPException) as exc_info:
                await permission_checker(mock_user, mock_db)
            
            assert exc_info.value.status_code == 403
            assert "One of the following permissions required" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_require_all_permissions_success(self, mock_user, mock_db, mock_rbac_service):
        """Test successful all permissions check"""
        # Mock RBAC service to return True for all permissions
        mock_rbac_service.check_user_permission.return_value = True
        
        # Create permission checker
        permission_checker = require_all_permissions(UserPermissions.READ, UserPermissions.WRITE)
        
        # Mock the dependency injection
        with pytest.MonkeyPatch.context() as m:
            m.setattr("api.dependencies.RBACService", lambda: mock_rbac_service)
            
            # Should not raise exception
            result = await permission_checker(mock_user, mock_db)
            assert result == mock_user
    
    @pytest.mark.asyncio
    async def test_require_all_permissions_denied(self, mock_user, mock_db, mock_rbac_service):
        """Test all permissions check denial"""
        # Mock RBAC service to return False for second permission
        mock_rbac_service.check_user_permission.side_effect = [True, False]
        
        # Create permission checker
        permission_checker = require_all_permissions(UserPermissions.READ, UserPermissions.WRITE)
        
        # Mock the dependency injection
        with pytest.MonkeyPatch.context() as m:
            m.setattr("api.dependencies.RBACService", lambda: mock_rbac_service)
            
            # Should raise 403 exception
            with pytest.raises(HTTPException) as exc_info:
                await permission_checker(mock_user, mock_db)
            
            assert exc_info.value.status_code == 403
            assert "Permission 'user:write' required" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_require_resource_permission(self, mock_user, mock_db, mock_rbac_service):
        """Test resource permission check"""
        # Mock RBAC service to return True
        mock_rbac_service.check_user_permission.return_value = True
        
        # Create resource permission checker
        permission_checker = require_resource_permission("asset", "read")
        
        # Mock the dependency injection
        with pytest.MonkeyPatch.context() as m:
            m.setattr("api.dependencies.RBACService", lambda: mock_rbac_service)
            
            # Should not raise exception
            result = await permission_checker(mock_user, mock_db)
            assert result == mock_user
            
            # Verify correct permission was checked
            mock_rbac_service.check_user_permission.assert_called_once_with(
                mock_db, mock_user.id, "asset:read", True
            )
    
    @pytest.mark.asyncio
    async def test_check_ownership_or_permission_owner(self, mock_user, mock_db):
        """Test ownership check success"""
        # Create ownership checker
        ownership_checker = check_ownership_or_permission(AssetPermissions.READ, "owner_id")
        
        # Should not raise exception when user owns resource
        result = await ownership_checker(mock_user, mock_db, owner_id=mock_user.id)
        assert result == mock_user
    
    @pytest.mark.asyncio
    async def test_check_ownership_or_permission_permission(self, mock_user, mock_db, mock_rbac_service):
        """Test ownership check with permission fallback"""
        # Mock RBAC service to return True
        mock_rbac_service.check_user_permission.return_value = True
        
        # Create ownership checker
        ownership_checker = check_ownership_or_permission(AssetPermissions.READ, "owner_id")
        
        # Mock the dependency injection
        with pytest.MonkeyPatch.context() as m:
            m.setattr("api.dependencies.RBACService", lambda: mock_rbac_service)
            
            # Should not raise exception when user has permission
            result = await ownership_checker(mock_user, mock_db, owner_id="different-user")
            assert result == mock_user
    
    @pytest.mark.asyncio
    async def test_check_ownership_or_permission_denied(self, mock_user, mock_db, mock_rbac_service):
        """Test ownership check denial"""
        # Mock RBAC service to return False
        mock_rbac_service.check_user_permission.return_value = False
        
        # Create ownership checker
        ownership_checker = check_ownership_or_permission(AssetPermissions.READ, "owner_id")
        
        # Mock the dependency injection
        with pytest.MonkeyPatch.context() as m:
            m.setattr("api.dependencies.RBACService", lambda: mock_rbac_service)
            
            # Should raise 403 exception
            with pytest.raises(HTTPException) as exc_info:
                await ownership_checker(mock_user, mock_db, owner_id="different-user")
            
            assert exc_info.value.status_code == 403
            assert "Resource ownership or permission" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_user_permissions(self, mock_user, mock_db, mock_rbac_service):
        """Test get user permissions"""
        # Mock RBAC service to return permissions
        mock_rbac_service.get_user_permissions.return_value = {
            UserPermissions.READ,
            UserPermissions.WRITE,
            AssetPermissions.READ
        }
        
        # Mock the dependency injection
        with pytest.MonkeyPatch.context() as m:
            m.setattr("api.dependencies.RBACService", lambda: mock_rbac_service)
            
            # Get permissions
            permissions = await get_user_permissions(mock_user, mock_db)
            
            # Verify permissions returned
            assert len(permissions) == 3
            assert UserPermissions.READ in permissions
            assert UserPermissions.WRITE in permissions
            assert AssetPermissions.READ in permissions
    
    @pytest.mark.asyncio
    async def test_get_user_roles(self, mock_user, mock_db):
        """Test get user roles"""
        # Mock user roles
        mock_role1 = MagicMock(spec=Role)
        mock_role1.name = "admin"
        mock_role1.is_active = True
        
        mock_role2 = MagicMock(spec=Role)
        mock_role2.name = "editor"
        mock_role2.is_active = True
        
        mock_role3 = MagicMock(spec=Role)
        mock_role3.name = "inactive"
        mock_role3.is_active = False
        
        mock_user.roles = [mock_role1, mock_role2, mock_role3]
        
        # Get roles
        roles = await get_user_roles(mock_user, mock_db)
        
        # Verify only active roles returned
        assert len(roles) == 2
        assert "admin" in roles
        assert "editor" in roles
        assert "inactive" not in roles


class TestPermissionValidation:
    """Test permission validation utilities"""
    
    def test_validate_permission_valid(self):
        """Test valid permission format"""
        from core.permissions import validate_permission
        
        assert validate_permission("user:read") is True
        assert validate_permission("asset:write") is True
        assert validate_permission("project:admin") is True
        assert validate_permission("metadata:create_schema") is True
    
    def test_validate_permission_invalid(self):
        """Test invalid permission format"""
        from core.permissions import validate_permission
        
        assert validate_permission("user") is False
        assert validate_permission("user:") is False
        assert validate_permission(":read") is False
        assert validate_permission("user:read:extra") is False
        assert validate_permission("user-read") is False
        assert validate_permission("USER:READ") is False
    
    def test_get_resource_from_permission(self):
        """Test extracting resource from permission"""
        from core.permissions import get_resource_from_permission
        
        assert get_resource_from_permission("user:read") == "user"
        assert get_resource_from_permission("asset:write") == "asset"
        assert get_resource_from_permission("invalid") == ""
    
    def test_get_action_from_permission(self):
        """Test extracting action from permission"""
        from core.permissions import get_action_from_permission
        
        assert get_action_from_permission("user:read") == "read"
        assert get_action_from_permission("asset:write") == "write"
        assert get_action_from_permission("invalid") == ""
    
    def test_create_permission_name(self):
        """Test creating permission name"""
        from core.permissions import create_permission_name
        
        assert create_permission_name("user", "read") == "user:read"
        assert create_permission_name("asset", "write") == "asset:write"
        assert create_permission_name("project", "admin") == "project:admin"