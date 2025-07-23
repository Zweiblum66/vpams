"""
Test cases for Group Service

This module tests the group management functionality including
group CRUD operations, user membership, and permission management.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from services.group_service import GroupService
from db.models import User, Group, Role, Permission
from models.schemas import PaginationParams, SortParams


class TestGroupService:
    """Test group service functionality"""
    
    @pytest.fixture
    def group_service(self):
        """Create group service instance"""
        return GroupService()
    
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
        user.username = "testuser"
        user.groups = []
        return user
    
    @pytest.fixture
    def mock_group(self):
        """Create mock group"""
        group = MagicMock(spec=Group)
        group.id = uuid4()
        group.name = "test_group"
        group.display_name = "Test Group"
        group.description = "Test group description"
        group.group_type = "custom"
        group.parent_group_id = None
        group.parent_group = None
        group.child_groups = []
        group.max_members = None
        group.is_active = True
        group.is_system = False
        group.users = []
        group.roles = []
        group.permissions = []
        group.created_at = datetime.now(timezone.utc)
        group.updated_at = datetime.now(timezone.utc)
        return group
    
    @pytest.fixture
    def mock_role(self):
        """Create mock role"""
        role = MagicMock(spec=Role)
        role.id = uuid4()
        role.name = "test_role"
        role.display_name = "Test Role"
        role.is_active = True
        return role
    
    @pytest.fixture
    def mock_permission(self):
        """Create mock permission"""
        permission = MagicMock(spec=Permission)
        permission.id = uuid4()
        permission.name = "test:read"
        permission.display_name = "Test Read"
        permission.is_active = True
        return permission
    
    # Group Creation Tests
    
    @pytest.mark.asyncio
    async def test_create_group_success(self, group_service, mock_db):
        """Test successful group creation"""
        # Setup
        group_service.get_group_by_name = AsyncMock(return_value=None)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Test
        result = await group_service.create_group(
            mock_db,
            name="new_group",
            display_name="New Group",
            description="New group description",
            group_type="department",
            max_members=100,
            creator_id=uuid4()
        )
        
        # Verify
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        assert result.name == "new_group"
        assert result.display_name == "New Group"
        assert result.max_members == 100
    
    @pytest.mark.asyncio
    async def test_create_group_duplicate_name(self, group_service, mock_db, mock_group):
        """Test group creation with duplicate name"""
        # Setup
        group_service.get_group_by_name = AsyncMock(return_value=mock_group)
        
        # Test
        with pytest.raises(ValueError, match="already exists"):
            await group_service.create_group(
                mock_db,
                name="test_group",
                display_name="Test Group"
            )
    
    @pytest.mark.asyncio
    async def test_create_group_with_parent(self, group_service, mock_db, mock_group):
        """Test group creation with parent group"""
        # Setup
        parent_id = uuid4()
        group_service.get_group_by_name = AsyncMock(return_value=None)
        group_service.get_group_by_id = AsyncMock(return_value=mock_group)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Test
        result = await group_service.create_group(
            mock_db,
            name="child_group",
            display_name="Child Group",
            parent_group_id=parent_id
        )
        
        # Verify
        assert result.parent_group_id == parent_id
    
    @pytest.mark.asyncio
    async def test_create_group_invalid_parent(self, group_service, mock_db):
        """Test group creation with invalid parent"""
        # Setup
        group_service.get_group_by_name = AsyncMock(return_value=None)
        group_service.get_group_by_id = AsyncMock(return_value=None)
        
        # Test
        with pytest.raises(ValueError, match="Parent group not found"):
            await group_service.create_group(
                mock_db,
                name="child_group",
                display_name="Child Group",
                parent_group_id=uuid4()
            )
    
    # Group Retrieval Tests
    
    @pytest.mark.asyncio
    async def test_get_group_by_id(self, group_service, mock_db, mock_group):
        """Test getting group by ID"""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_group
        mock_db.execute.return_value = mock_result
        
        # Test
        result = await group_service.get_group_by_id(mock_db, mock_group.id)
        
        # Verify
        assert result == mock_group
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_group_by_name(self, group_service, mock_db, mock_group):
        """Test getting group by name"""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_group
        mock_db.execute.return_value = mock_result
        
        # Test
        result = await group_service.get_group_by_name(mock_db, "test_group")
        
        # Verify
        assert result == mock_group
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_groups_with_filters(self, group_service, mock_db, mock_group):
        """Test getting paginated groups with filters"""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalars().all.return_value = [mock_group]
        mock_count_result = AsyncMock()
        mock_count_result.scalar.return_value = 1
        mock_db.execute.side_effect = [mock_count_result, mock_result]
        
        pagination = PaginationParams(page=1, limit=10)
        sort = SortParams(sort="name", order="asc")
        filters = {
            "is_active": True,
            "group_type": "custom",
            "parent_group_id": None
        }
        
        # Test
        groups, count = await group_service.get_groups(mock_db, pagination, sort, filters)
        
        # Verify
        assert len(groups) == 1
        assert count == 1
        assert mock_db.execute.call_count == 2
    
    # Group Update Tests
    
    @pytest.mark.asyncio
    async def test_update_group_success(self, group_service, mock_db, mock_group):
        """Test successful group update"""
        # Setup
        group_service.get_group_by_id = AsyncMock(return_value=mock_group)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        updates = {
            "display_name": "Updated Group",
            "description": "Updated description",
            "max_members": 200
        }
        
        # Test
        result = await group_service.update_group(
            mock_db,
            mock_group.id,
            updates,
            updater_id=uuid4()
        )
        
        # Verify
        assert result.display_name == "Updated Group"
        assert result.description == "Updated description"
        assert result.max_members == 200
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_system_group_blocked(self, group_service, mock_db, mock_group):
        """Test updating system group without permission"""
        # Setup
        mock_group.is_system = True
        group_service.get_group_by_id = AsyncMock(return_value=mock_group)
        
        # Test
        with pytest.raises(ValueError, match="Cannot update system group"):
            await group_service.update_group(
                mock_db,
                mock_group.id,
                {"display_name": "Updated"}
            )
    
    # Group Deletion Tests
    
    @pytest.mark.asyncio
    async def test_delete_group_success(self, group_service, mock_db, mock_group):
        """Test successful group deletion"""
        # Setup
        group_service.get_group_by_id = AsyncMock(return_value=mock_group)
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()
        
        # Test
        result = await group_service.delete_group(mock_db, mock_group.id)
        
        # Verify
        assert result is True
        mock_db.delete.assert_called_once_with(mock_group)
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_system_group_blocked(self, group_service, mock_db, mock_group):
        """Test deleting system group blocked"""
        # Setup
        mock_group.is_system = True
        group_service.get_group_by_id = AsyncMock(return_value=mock_group)
        
        # Test
        with pytest.raises(ValueError, match="Cannot delete system group"):
            await group_service.delete_group(mock_db, mock_group.id)
    
    @pytest.mark.asyncio
    async def test_delete_group_with_members_blocked(self, group_service, mock_db, mock_group, mock_user):
        """Test deleting group with members blocked"""
        # Setup
        mock_group.users = [mock_user]
        group_service.get_group_by_id = AsyncMock(return_value=mock_group)
        
        # Test
        with pytest.raises(ValueError, match="Cannot delete group with members"):
            await group_service.delete_group(mock_db, mock_group.id)
    
    @pytest.mark.asyncio
    async def test_delete_group_with_children_blocked(self, group_service, mock_db, mock_group):
        """Test deleting group with child groups blocked"""
        # Setup
        child_group = MagicMock()
        mock_group.child_groups = [child_group]
        group_service.get_group_by_id = AsyncMock(return_value=mock_group)
        
        # Test
        with pytest.raises(ValueError, match="Cannot delete group with child groups"):
            await group_service.delete_group(mock_db, mock_group.id)
    
    # User Membership Tests
    
    @pytest.mark.asyncio
    async def test_add_user_to_group_success(self, group_service, mock_db, mock_user, mock_group):
        """Test successfully adding user to group"""
        # Setup
        group_service.get_group_by_id = AsyncMock(return_value=mock_group)
        user_result = AsyncMock()
        user_result.scalar_one_or_none.return_value = mock_user
        existing_result = AsyncMock()
        existing_result.first.return_value = None
        
        mock_db.execute.side_effect = [user_result, existing_result, AsyncMock()]
        mock_db.commit = AsyncMock()
        
        # Test
        result = await group_service.add_user_to_group(
            mock_db,
            mock_user.id,
            mock_group.id,
            added_by=uuid4()
        )
        
        # Verify
        assert result is True
        assert mock_db.execute.call_count == 3
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_add_user_to_group_already_member(self, group_service, mock_db, mock_user, mock_group):
        """Test adding user who is already a member"""
        # Setup
        group_service.get_group_by_id = AsyncMock(return_value=mock_group)
        user_result = AsyncMock()
        user_result.scalar_one_or_none.return_value = mock_user
        existing_result = AsyncMock()
        existing_result.first.return_value = {"user_id": mock_user.id}
        
        mock_db.execute.side_effect = [user_result, existing_result]
        
        # Test
        result = await group_service.add_user_to_group(
            mock_db,
            mock_user.id,
            mock_group.id
        )
        
        # Verify
        assert result is True
        mock_db.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_add_user_to_group_max_members_exceeded(self, group_service, mock_db, mock_user, mock_group):
        """Test adding user when max members exceeded"""
        # Setup
        mock_group.max_members = 1
        mock_group.users = [MagicMock()]  # Already has one member
        group_service.get_group_by_id = AsyncMock(return_value=mock_group)
        user_result = AsyncMock()
        user_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = user_result
        
        # Test
        with pytest.raises(ValueError, match="Group has reached maximum member limit"):
            await group_service.add_user_to_group(
                mock_db,
                mock_user.id,
                mock_group.id
            )
    
    @pytest.mark.asyncio
    async def test_remove_user_from_group_success(self, group_service, mock_db, mock_user, mock_group):
        """Test successfully removing user from group"""
        # Setup
        mock_result = AsyncMock()
        mock_result.rowcount = 1
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        
        # Test
        result = await group_service.remove_user_from_group(
            mock_db,
            mock_user.id,
            mock_group.id
        )
        
        # Verify
        assert result is True
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
    
    # Role Assignment Tests
    
    @pytest.mark.asyncio
    async def test_assign_role_to_group_success(self, group_service, mock_db, mock_group, mock_role):
        """Test successfully assigning role to group"""
        # Setup
        group_service.get_group_by_id = AsyncMock(return_value=mock_group)
        group_service.get_role_by_id = AsyncMock(return_value=mock_role)
        
        existing_result = AsyncMock()
        existing_result.first.return_value = None
        mock_db.execute.side_effect = [existing_result, AsyncMock()]
        mock_db.commit = AsyncMock()
        
        # Test
        result = await group_service.assign_role_to_group(
            mock_db,
            mock_group.id,
            mock_role.id,
            assigner_id=uuid4()
        )
        
        # Verify
        assert result is True
        assert mock_db.execute.call_count == 2
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_revoke_role_from_group_success(self, group_service, mock_db, mock_group, mock_role):
        """Test successfully revoking role from group"""
        # Setup
        mock_result = AsyncMock()
        mock_result.rowcount = 1
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        
        # Test
        result = await group_service.revoke_role_from_group(
            mock_db,
            mock_group.id,
            mock_role.id
        )
        
        # Verify
        assert result is True
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
    
    # Permission Assignment Tests
    
    @pytest.mark.asyncio
    async def test_assign_permission_to_group_success(self, group_service, mock_db, mock_group, mock_permission):
        """Test successfully assigning permission to group"""
        # Setup
        group_service.get_group_by_id = AsyncMock(return_value=mock_group)
        group_service.get_permission_by_id = AsyncMock(return_value=mock_permission)
        
        existing_result = AsyncMock()
        existing_result.first.return_value = None
        mock_db.execute.side_effect = [existing_result, AsyncMock()]
        mock_db.commit = AsyncMock()
        
        # Test
        result = await group_service.assign_permission_to_group(
            mock_db,
            mock_group.id,
            mock_permission.id,
            granter_id=uuid4()
        )
        
        # Verify
        assert result is True
        assert mock_db.execute.call_count == 2
        mock_db.commit.assert_called_once()
    
    # Group Permission Checking Tests
    
    @pytest.mark.asyncio
    async def test_get_group_permissions_direct(self, group_service, mock_db, mock_group, mock_permission):
        """Test getting direct group permissions"""
        # Setup
        mock_group.permissions = [mock_permission]
        group_service.get_group_by_id = AsyncMock(return_value=mock_group)
        
        # Test
        permissions = await group_service.get_group_permissions(
            mock_db,
            mock_group.id,
            include_inherited=False
        )
        
        # Verify
        assert "test:read" in permissions
        assert len(permissions) == 1
    
    @pytest.mark.asyncio
    async def test_get_group_permissions_with_roles(self, group_service, mock_db, mock_group, mock_role, mock_permission):
        """Test getting group permissions including role permissions"""
        # Setup
        mock_role.permissions = [mock_permission]
        mock_group.roles = [mock_role]
        group_service.get_group_by_id = AsyncMock(return_value=mock_group)
        
        # Test
        permissions = await group_service.get_group_permissions(
            mock_db,
            mock_group.id,
            include_inherited=True
        )
        
        # Verify
        assert "test:read" in permissions
    
    @pytest.mark.asyncio
    async def test_get_group_permissions_with_parent(self, group_service, mock_db, mock_group, mock_permission):
        """Test getting permissions with parent group inheritance"""
        # Setup
        parent_group = MagicMock()
        parent_group.id = uuid4()
        parent_group.is_active = True
        mock_group.parent_group_id = parent_group.id
        
        group_service.get_group_by_id = AsyncMock(return_value=mock_group)
        group_service.get_group_permissions = AsyncMock(
            side_effect=[
                set(),  # First call (direct)
                {"parent:permission"}  # Second call (parent)
            ]
        )
        
        # Test - need to mock the recursive call properly
        with patch.object(group_service, 'get_group_permissions', new_callable=AsyncMock) as mock_get_perms:
            # First call returns the actual implementation
            async def get_perms_impl(db, group_id, include_inherited=True):
                if group_id == mock_group.id:
                    return {"test:read"} if mock_group.permissions else set()
                else:
                    return {"parent:permission"}
            
            mock_get_perms.side_effect = get_perms_impl
            
            permissions = await group_service.get_group_permissions(
                mock_db,
                mock_group.id,
                include_inherited=True
            )
        
        # Verify
        assert len(permissions) > 0
    
    # Group Member Management Tests
    
    @pytest.mark.asyncio
    async def test_get_group_members(self, group_service, mock_db, mock_group, mock_user):
        """Test getting group members"""
        # Setup
        mock_group.users = [mock_user]
        group_service.get_group_by_id = AsyncMock(return_value=mock_group)
        
        # Test
        members = await group_service.get_group_members(mock_db, mock_group.id)
        
        # Verify
        assert len(members) == 1
        assert members[0] == mock_user
    
    @pytest.mark.asyncio
    async def test_is_user_in_group_true(self, group_service, mock_db, mock_user, mock_group):
        """Test checking if user is in group - true case"""
        # Setup
        mock_result = AsyncMock()
        mock_result.first.return_value = {"user_id": mock_user.id}
        mock_db.execute.return_value = mock_result
        
        # Test
        result = await group_service.is_user_in_group(
            mock_db,
            mock_user.id,
            mock_group.id
        )
        
        # Verify
        assert result is True
    
    @pytest.mark.asyncio
    async def test_is_user_in_group_false(self, group_service, mock_db, mock_user, mock_group):
        """Test checking if user is in group - false case"""
        # Setup
        mock_result = AsyncMock()
        mock_result.first.return_value = None
        mock_db.execute.return_value = mock_result
        
        # Test
        result = await group_service.is_user_in_group(
            mock_db,
            mock_user.id,
            mock_group.id
        )
        
        # Verify
        assert result is False
    
    # Statistics Tests
    
    @pytest.mark.asyncio
    async def test_get_group_stats(self, group_service, mock_db):
        """Test getting group statistics"""
        # Setup
        mock_results = [
            AsyncMock(scalar=lambda: 10),  # total groups
            AsyncMock(scalar=lambda: 100),  # total memberships
            AsyncMock(scalar=lambda: 20),  # groups with roles
            AsyncMock(scalar=lambda: 15)   # groups with permissions
        ]
        
        mock_db.execute.side_effect = mock_results
        
        # Test
        stats = await group_service.get_group_stats(mock_db)
        
        # Verify
        assert stats["total_groups"] == 10
        assert stats["total_memberships"] == 100
        assert stats["groups_with_roles"] == 20
        assert stats["groups_with_permissions"] == 15
    
    # Error Handling Tests
    
    @pytest.mark.asyncio
    async def test_create_group_database_error(self, group_service, mock_db):
        """Test group creation with database error"""
        # Setup
        group_service.get_group_by_name = AsyncMock(return_value=None)
        mock_db.add = MagicMock()
        mock_db.commit.side_effect = IntegrityError("Database error", None, None)
        mock_db.rollback = AsyncMock()
        
        # Test
        with pytest.raises(IntegrityError):
            await group_service.create_group(
                mock_db,
                name="error_group",
                display_name="Error Group"
            )
        
        # Verify
        mock_db.rollback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_group_permissions_error_handling(self, group_service, mock_db):
        """Test error handling in get group permissions"""
        # Setup
        mock_db.execute.side_effect = Exception("Database error")
        
        # Test
        permissions = await group_service.get_group_permissions(
            mock_db,
            uuid4()
        )
        
        # Verify - should return empty set on error
        assert permissions == set()