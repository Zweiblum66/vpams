"""
Test cases for RBAC Service

This module tests the Role-Based Access Control service functionality
including role management, permission management, and assignments.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from services.rbac_service import RBACService
from db.models import User, Role, Permission, Group
from models.schemas import PaginationParams, SortParams


class TestRBACService:
    """Test RBAC service functionality"""
    
    @pytest.fixture
    def rbac_service(self):
        """Create RBAC service instance"""
        return RBACService()
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def mock_user(self):
        """Create mock user"""
        user = MagicMock(spec=User)
        user.id = uuid4()
        user.email = "test@example.com"
        user.roles = []
        user.groups = []
        return user
    
    @pytest.fixture
    def mock_role(self):
        """Create mock role"""
        role = MagicMock(spec=Role)
        role.id = uuid4()
        role.name = "test_role"
        role.display_name = "Test Role"
        role.description = "Test role description"
        role.role_type = "custom"
        role.is_active = True
        role.is_system = False
        role.permissions = []
        role.users = []
        role.parent_role = None
        role.child_roles = []
        role.created_at = datetime.now(timezone.utc)
        role.updated_at = datetime.now(timezone.utc)
        return role
    
    @pytest.fixture
    def mock_permission(self):
        """Create mock permission"""
        permission = MagicMock(spec=Permission)
        permission.id = uuid4()
        permission.name = "test:read"
        permission.display_name = "Test Read"
        permission.description = "Test read permission"
        permission.resource = "test"
        permission.action = "read"
        permission.category = "general"
        permission.scope = "global"
        permission.is_active = True
        permission.is_system = False
        permission.roles = []
        return permission
    
    @pytest.fixture
    def mock_group(self):
        """Create mock group"""
        group = MagicMock(spec=Group)
        group.id = uuid4()
        group.name = "test_group"
        group.display_name = "Test Group"
        group.is_active = True
        group.permissions = []
        group.roles = []
        group.parent_group_id = None
        return group
    
    # Role Management Tests
    
    @pytest.mark.asyncio
    async def test_create_role_success(self, rbac_service, mock_db):
        """Test successful role creation"""
        # Setup
        rbac_service.get_role_by_name = AsyncMock(return_value=None)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Test
        result = await rbac_service.create_role(
            mock_db,
            name="new_role",
            display_name="New Role",
            description="New role description",
            role_type="custom",
            creator_id=uuid4()
        )
        
        # Verify
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        assert result.name == "new_role"
        assert result.display_name == "New Role"
    
    @pytest.mark.asyncio
    async def test_create_role_duplicate_name(self, rbac_service, mock_db, mock_role):
        """Test role creation with duplicate name"""
        # Setup
        rbac_service.get_role_by_name = AsyncMock(return_value=mock_role)
        
        # Test
        with pytest.raises(ValueError, match="already exists"):
            await rbac_service.create_role(
                mock_db,
                name="test_role",
                display_name="Test Role"
            )
    
    @pytest.mark.asyncio
    async def test_create_role_with_parent(self, rbac_service, mock_db, mock_role):
        """Test role creation with parent role"""
        # Setup
        parent_id = uuid4()
        rbac_service.get_role_by_name = AsyncMock(return_value=None)
        rbac_service.get_role_by_id = AsyncMock(return_value=mock_role)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Test
        result = await rbac_service.create_role(
            mock_db,
            name="child_role",
            display_name="Child Role",
            parent_role_id=parent_id
        )
        
        # Verify
        assert result.parent_role_id == parent_id
    
    @pytest.mark.asyncio
    async def test_create_role_invalid_parent(self, rbac_service, mock_db):
        """Test role creation with invalid parent"""
        # Setup
        rbac_service.get_role_by_name = AsyncMock(return_value=None)
        rbac_service.get_role_by_id = AsyncMock(return_value=None)
        
        # Test
        with pytest.raises(ValueError, match="Parent role not found"):
            await rbac_service.create_role(
                mock_db,
                name="child_role",
                display_name="Child Role",
                parent_role_id=uuid4()
            )
    
    @pytest.mark.asyncio
    async def test_get_role_by_id(self, rbac_service, mock_db, mock_role):
        """Test getting role by ID"""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_role
        mock_db.execute.return_value = mock_result
        
        # Test
        result = await rbac_service.get_role_by_id(mock_db, mock_role.id)
        
        # Verify
        assert result == mock_role
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_role_by_name(self, rbac_service, mock_db, mock_role):
        """Test getting role by name"""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_role
        mock_db.execute.return_value = mock_result
        
        # Test
        result = await rbac_service.get_role_by_name(mock_db, "test_role")
        
        # Verify
        assert result == mock_role
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_roles_with_filters(self, rbac_service, mock_db, mock_role):
        """Test getting paginated roles with filters"""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalars().all.return_value = [mock_role]
        mock_count_result = AsyncMock()
        mock_count_result.scalar.return_value = 1
        mock_db.execute.side_effect = [mock_count_result, mock_result]
        
        pagination = PaginationParams(page=1, limit=10)
        sort = SortParams(sort="name", order="asc")
        filters = {
            "is_active": True,
            "role_type": "custom",
            "is_system": False
        }
        
        # Test
        roles, count = await rbac_service.get_roles(mock_db, pagination, sort, filters)
        
        # Verify
        assert len(roles) == 1
        assert count == 1
        assert mock_db.execute.call_count == 2
    
    @pytest.mark.asyncio
    async def test_update_role_success(self, rbac_service, mock_db, mock_role):
        """Test successful role update"""
        # Setup
        rbac_service.get_role_by_id = AsyncMock(return_value=mock_role)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        updates = {
            "display_name": "Updated Role",
            "description": "Updated description"
        }
        
        # Test
        result = await rbac_service.update_role(
            mock_db,
            mock_role.id,
            updates,
            updater_id=uuid4()
        )
        
        # Verify
        assert result.display_name == "Updated Role"
        assert result.description == "Updated description"
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_system_role_blocked(self, rbac_service, mock_db, mock_role):
        """Test updating system role without permission"""
        # Setup
        mock_role.is_system = True
        rbac_service.get_role_by_id = AsyncMock(return_value=mock_role)
        
        # Test
        with pytest.raises(ValueError, match="Cannot update system role"):
            await rbac_service.update_role(
                mock_db,
                mock_role.id,
                {"display_name": "Updated"}
            )
    
    @pytest.mark.asyncio
    async def test_delete_role_success(self, rbac_service, mock_db, mock_role):
        """Test successful role deletion"""
        # Setup
        rbac_service.get_role_by_id = AsyncMock(return_value=mock_role)
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()
        
        # Test
        result = await rbac_service.delete_role(mock_db, mock_role.id)
        
        # Verify
        assert result is True
        mock_db.delete.assert_called_once_with(mock_role)
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_system_role_blocked(self, rbac_service, mock_db, mock_role):
        """Test deleting system role blocked"""
        # Setup
        mock_role.is_system = True
        rbac_service.get_role_by_id = AsyncMock(return_value=mock_role)
        
        # Test
        with pytest.raises(ValueError, match="Cannot delete system role"):
            await rbac_service.delete_role(mock_db, mock_role.id)
    
    @pytest.mark.asyncio
    async def test_delete_role_with_users_blocked(self, rbac_service, mock_db, mock_role, mock_user):
        """Test deleting role with assigned users blocked"""
        # Setup
        mock_role.users = [mock_user]
        rbac_service.get_role_by_id = AsyncMock(return_value=mock_role)
        
        # Test
        with pytest.raises(ValueError, match="Cannot delete role with assigned users"):
            await rbac_service.delete_role(mock_db, mock_role.id)
    
    @pytest.mark.asyncio
    async def test_delete_role_with_children_blocked(self, rbac_service, mock_db, mock_role):
        """Test deleting role with child roles blocked"""
        # Setup
        child_role = MagicMock()
        mock_role.child_roles = [child_role]
        rbac_service.get_role_by_id = AsyncMock(return_value=mock_role)
        
        # Test
        with pytest.raises(ValueError, match="Cannot delete role with child roles"):
            await rbac_service.delete_role(mock_db, mock_role.id)
    
    # Permission Management Tests
    
    @pytest.mark.asyncio
    async def test_create_permission_success(self, rbac_service, mock_db):
        """Test successful permission creation"""
        # Setup
        rbac_service.get_permission_by_name = AsyncMock(return_value=None)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Test
        result = await rbac_service.create_permission(
            mock_db,
            name="test:write",
            display_name="Test Write",
            description="Test write permission",
            resource="test",
            action="write",
            creator_id=uuid4()
        )
        
        # Verify
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert result.name == "test:write"
        assert result.action == "write"
    
    @pytest.mark.asyncio
    async def test_create_permission_duplicate_name(self, rbac_service, mock_db, mock_permission):
        """Test permission creation with duplicate name"""
        # Setup
        rbac_service.get_permission_by_name = AsyncMock(return_value=mock_permission)
        
        # Test
        with pytest.raises(ValueError, match="already exists"):
            await rbac_service.create_permission(
                mock_db,
                name="test:read",
                display_name="Test Read"
            )
    
    @pytest.mark.asyncio
    async def test_get_permissions_with_filters(self, rbac_service, mock_db, mock_permission):
        """Test getting paginated permissions with filters"""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalars().all.return_value = [mock_permission]
        mock_count_result = AsyncMock()
        mock_count_result.scalar.return_value = 1
        mock_db.execute.side_effect = [mock_count_result, mock_result]
        
        pagination = PaginationParams(page=1, limit=10)
        sort = SortParams(sort="name", order="asc")
        filters = {
            "resource": "test",
            "action": "read",
            "category": "general",
            "scope": "global"
        }
        
        # Test
        permissions, count = await rbac_service.get_permissions(
            mock_db, pagination, sort, filters
        )
        
        # Verify
        assert len(permissions) == 1
        assert count == 1
    
    # Assignment Tests
    
    @pytest.mark.asyncio
    async def test_assign_permission_to_role_success(
        self, rbac_service, mock_db, mock_role, mock_permission
    ):
        """Test successful permission assignment to role"""
        # Setup
        rbac_service.get_role_by_id = AsyncMock(return_value=mock_role)
        rbac_service.get_permission_by_id = AsyncMock(return_value=mock_permission)
        
        mock_result = AsyncMock()
        mock_result.first.return_value = None  # No existing assignment
        mock_db.execute.side_effect = [mock_result, AsyncMock()]
        mock_db.commit = AsyncMock()
        
        # Test
        result = await rbac_service.assign_permission_to_role(
            mock_db,
            mock_role.id,
            mock_permission.id,
            granter_id=uuid4()
        )
        
        # Verify
        assert result is True
        assert mock_db.execute.call_count == 2
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_assign_permission_to_role_already_assigned(
        self, rbac_service, mock_db, mock_role, mock_permission
    ):
        """Test permission assignment when already assigned"""
        # Setup
        rbac_service.get_role_by_id = AsyncMock(return_value=mock_role)
        rbac_service.get_permission_by_id = AsyncMock(return_value=mock_permission)
        
        mock_result = AsyncMock()
        mock_result.first.return_value = {"role_id": mock_role.id}  # Existing assignment
        mock_db.execute.return_value = mock_result
        
        # Test
        result = await rbac_service.assign_permission_to_role(
            mock_db,
            mock_role.id,
            mock_permission.id
        )
        
        # Verify
        assert result is True
        mock_db.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_revoke_permission_from_role_success(
        self, rbac_service, mock_db, mock_role, mock_permission
    ):
        """Test successful permission revocation from role"""
        # Setup
        mock_result = AsyncMock()
        mock_result.rowcount = 1
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        
        # Test
        result = await rbac_service.revoke_permission_from_role(
            mock_db,
            mock_role.id,
            mock_permission.id
        )
        
        # Verify
        assert result is True
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_assign_role_to_user_success(
        self, rbac_service, mock_db, mock_user, mock_role
    ):
        """Test successful role assignment to user"""
        # Setup
        rbac_service.get_role_by_id = AsyncMock(return_value=mock_role)
        
        user_result = AsyncMock()
        user_result.scalar_one_or_none.return_value = mock_user
        existing_result = AsyncMock()
        existing_result.first.return_value = None
        
        mock_db.execute.side_effect = [user_result, existing_result, AsyncMock()]
        mock_db.commit = AsyncMock()
        
        # Test
        result = await rbac_service.assign_role_to_user(
            mock_db,
            mock_user.id,
            mock_role.id,
            assigner_id=uuid4()
        )
        
        # Verify
        assert result is True
        assert mock_db.execute.call_count == 3
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_assign_role_to_user_invalid_role(self, rbac_service, mock_db, mock_user):
        """Test role assignment with invalid role"""
        # Setup
        rbac_service.get_role_by_id = AsyncMock(return_value=None)
        
        # Test
        with pytest.raises(ValueError, match="Role not found"):
            await rbac_service.assign_role_to_user(
                mock_db,
                mock_user.id,
                uuid4()
            )
    
    @pytest.mark.asyncio
    async def test_revoke_role_from_user_success(
        self, rbac_service, mock_db, mock_user, mock_role
    ):
        """Test successful role revocation from user"""
        # Setup
        mock_result = AsyncMock()
        mock_result.rowcount = 1
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        
        # Test
        result = await rbac_service.revoke_role_from_user(
            mock_db,
            mock_user.id,
            mock_role.id
        )
        
        # Verify
        assert result is True
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
    
    # Permission Checking Tests
    
    @pytest.mark.asyncio
    async def test_get_user_permissions_direct_roles(
        self, rbac_service, mock_db, mock_user, mock_role, mock_permission
    ):
        """Test getting user permissions from direct roles"""
        # Setup
        mock_role.permissions = [mock_permission]
        mock_user.roles = [mock_role]
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result
        
        # Test
        permissions = await rbac_service.get_user_permissions(
            mock_db,
            mock_user.id,
            include_inherited=False
        )
        
        # Verify
        assert "test:read" in permissions
        assert len(permissions) == 1
    
    @pytest.mark.asyncio
    async def test_get_user_permissions_with_groups(
        self, rbac_service, mock_db, mock_user, mock_group, mock_role, mock_permission
    ):
        """Test getting user permissions including group permissions"""
        # Setup
        mock_role.permissions = [mock_permission]
        mock_group.roles = [mock_role]
        mock_user.groups = [mock_group]
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result
        
        # Test
        permissions = await rbac_service.get_user_permissions(
            mock_db,
            mock_user.id,
            include_inherited=True
        )
        
        # Verify
        assert "test:read" in permissions
    
    @pytest.mark.asyncio
    async def test_get_user_permissions_with_inheritance(
        self, rbac_service, mock_db, mock_user, mock_role, mock_permission
    ):
        """Test getting user permissions with role inheritance"""
        # Setup
        parent_role = MagicMock(spec=Role)
        parent_role.id = uuid4()
        parent_role.is_active = True
        parent_role.permissions = [mock_permission]
        
        mock_role.parent_role_id = parent_role.id
        mock_user.roles = [mock_role]
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result
        
        # Mock recursive call for parent role
        rbac_service.get_role_permissions = AsyncMock(
            return_value={"test:read"}
        )
        
        # Test
        permissions = await rbac_service.get_user_permissions(
            mock_db,
            mock_user.id,
            include_inherited=True
        )
        
        # Verify
        assert "test:read" in permissions
    
    @pytest.mark.asyncio
    async def test_check_user_permission_true(
        self, rbac_service, mock_db, mock_user
    ):
        """Test checking user permission returns true"""
        # Setup
        rbac_service.get_user_permissions = AsyncMock(
            return_value={"test:read", "test:write"}
        )
        
        # Test
        result = await rbac_service.check_user_permission(
            mock_db,
            mock_user.id,
            "test:read"
        )
        
        # Verify
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_user_permission_false(
        self, rbac_service, mock_db, mock_user
    ):
        """Test checking user permission returns false"""
        # Setup
        rbac_service.get_user_permissions = AsyncMock(
            return_value={"test:read"}
        )
        
        # Test
        result = await rbac_service.check_user_permission(
            mock_db,
            mock_user.id,
            "test:delete"
        )
        
        # Verify
        assert result is False
    
    # Statistics Tests
    
    @pytest.mark.asyncio
    async def test_get_rbac_stats(self, rbac_service, mock_db):
        """Test getting RBAC statistics"""
        # Setup
        mock_results = [
            AsyncMock(scalar=lambda: 10),  # roles count
            AsyncMock(scalar=lambda: 25),  # permissions count
            AsyncMock(scalar=lambda: 50),  # role assignments
            AsyncMock(scalar=lambda: 100)  # permission grants
        ]
        
        mock_db.execute.side_effect = mock_results
        
        # Test
        stats = await rbac_service.get_rbac_stats(mock_db)
        
        # Verify
        assert stats["total_roles"] == 10
        assert stats["total_permissions"] == 25
        assert stats["total_role_assignments"] == 50
        assert stats["total_permission_grants"] == 100
    
    @pytest.mark.asyncio
    async def test_get_rbac_stats_error_handling(self, rbac_service, mock_db):
        """Test RBAC stats error handling"""
        # Setup
        mock_db.execute.side_effect = Exception("Database error")
        
        # Test
        stats = await rbac_service.get_rbac_stats(mock_db)
        
        # Verify - should return zeros on error
        assert stats["total_roles"] == 0
        assert stats["total_permissions"] == 0
        assert stats["total_role_assignments"] == 0
        assert stats["total_permission_grants"] == 0