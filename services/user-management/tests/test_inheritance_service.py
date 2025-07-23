"""
Test cases for permission inheritance system

This module tests the advanced permission inheritance functionality
including role hierarchy, group hierarchy, and conflict resolution.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from services.inheritance_service import (
    InheritanceService,
    InheritanceType,
    InheritancePolicy,
    PermissionSource
)
from db.models import User, Role, Permission, Group


class TestInheritanceService:
    """Test permission inheritance service"""
    
    @pytest.fixture
    def inheritance_service(self):
        """Create inheritance service instance"""
        return InheritanceService()
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def mock_user(self):
        """Create mock user with roles and groups"""
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
        role.is_active = True
        role.permissions = []
        role.parent_role_id = None
        return role
    
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
    
    @pytest.fixture
    def mock_permission(self):
        """Create mock permission"""
        permission = MagicMock(spec=Permission)
        permission.id = uuid4()
        permission.name = "test:read"
        permission.is_active = True
        return permission
    
    @pytest.mark.asyncio
    async def test_get_effective_permissions_direct_role(
        self, 
        inheritance_service, 
        mock_db, 
        mock_user, 
        mock_role, 
        mock_permission
    ):
        """Test getting effective permissions from direct role assignment"""
        # Setup
        mock_role.permissions = [mock_permission]
        mock_user.roles = [mock_role]
        
        # Mock database query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result
        
        # Test
        result = await inheritance_service.get_effective_permissions(
            mock_db, mock_user.id, include_sources=True
        )
        
        # Verify
        assert result["total_count"] == 1
        assert "test:read" in result["permissions"]
        assert len(result["sources"]) == 1
        assert result["sources"][0]["source_type"] == InheritanceType.DIRECT.value
    
    @pytest.mark.asyncio
    async def test_get_effective_permissions_group_role(
        self, 
        inheritance_service, 
        mock_db, 
        mock_user, 
        mock_group, 
        mock_role, 
        mock_permission
    ):
        """Test getting effective permissions from group role assignment"""
        # Setup
        mock_role.permissions = [mock_permission]
        mock_group.roles = [mock_role]
        mock_user.groups = [mock_group]
        
        # Mock database query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result
        
        # Test
        result = await inheritance_service.get_effective_permissions(
            mock_db, mock_user.id, include_sources=True
        )
        
        # Verify
        assert result["total_count"] == 1
        assert "test:read" in result["permissions"]
        assert len(result["sources"]) == 1
        assert result["sources"][0]["source_type"] == InheritanceType.GROUP_ROLE.value
    
    @pytest.mark.asyncio
    async def test_get_effective_permissions_direct_group(
        self, 
        inheritance_service, 
        mock_db, 
        mock_user, 
        mock_group, 
        mock_permission
    ):
        """Test getting effective permissions from direct group assignment"""
        # Setup
        mock_group.permissions = [mock_permission]
        mock_user.groups = [mock_group]
        
        # Mock database query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result
        
        # Test
        result = await inheritance_service.get_effective_permissions(
            mock_db, mock_user.id, include_sources=True
        )
        
        # Verify
        assert result["total_count"] == 1
        assert "test:read" in result["permissions"]
        assert len(result["sources"]) == 1
        assert result["sources"][0]["source_type"] == InheritanceType.DIRECT.value
    
    @pytest.mark.asyncio
    async def test_resolve_permission_conflicts(self, inheritance_service):
        """Test permission conflict resolution"""
        # Setup conflicting permission sources
        sources = [
            PermissionSource(
                permission_name="test:read",
                source_type=InheritanceType.DIRECT,
                source_id=uuid4(),
                source_name="Direct Role",
                priority=10
            ),
            PermissionSource(
                permission_name="test:read",
                source_type=InheritanceType.GROUP_ROLE,
                source_id=uuid4(),
                source_name="Group Role",
                priority=7
            ),
            PermissionSource(
                permission_name="test:read",
                source_type=InheritanceType.ROLE_HIERARCHY,
                source_id=uuid4(),
                source_name="Inherited Role",
                priority=5
            )
        ]
        
        # Test conflict resolution
        resolved = inheritance_service._resolve_permission_conflicts(sources)
        
        # Verify highest priority wins
        assert len(resolved) == 1
        assert "test:read" in resolved
        assert resolved["test:read"].priority == 10
        assert resolved["test:read"].source_type == InheritanceType.DIRECT
    
    @pytest.mark.asyncio
    async def test_get_permission_inheritance_tree(
        self, 
        inheritance_service, 
        mock_db, 
        mock_user
    ):
        """Test getting permission inheritance tree"""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result
        
        # Mock tree building methods
        inheritance_service._build_role_tree = AsyncMock(return_value={
            "role_id": str(uuid4()),
            "name": "test_role",
            "permissions": ["test:read"],
            "parent": None
        })
        
        inheritance_service._build_group_tree = AsyncMock(return_value={
            "group_id": str(uuid4()),
            "name": "test_group",
            "permissions": ["test:write"],
            "parent": None
        })
        
        # Test
        result = await inheritance_service.get_permission_inheritance_tree(
            mock_db, mock_user.id
        )
        
        # Verify
        assert "tree" in result
        assert "user_id" in result["tree"]
        assert "roles" in result["tree"]
        assert "groups" in result["tree"]
    
    @pytest.mark.asyncio
    async def test_check_permission_conflicts_with_conflicts(
        self, 
        inheritance_service, 
        mock_db, 
        mock_user
    ):
        """Test checking permission conflicts when conflicts exist"""
        # Setup
        mock_effective_permissions = {
            "permissions": ["test:read", "test:write"],
            "sources": [
                {
                    "permission_name": "test:read",
                    "source_type": "direct",
                    "source_id": str(uuid4()),
                    "source_name": "Direct Role",
                    "priority": 10
                },
                {
                    "permission_name": "test:read",
                    "source_type": "group_role",
                    "source_id": str(uuid4()),
                    "source_name": "Group Role",
                    "priority": 7
                },
                {
                    "permission_name": "test:write",
                    "source_type": "direct",
                    "source_id": str(uuid4()),
                    "source_name": "Direct Role",
                    "priority": 10
                }
            ]
        }
        
        inheritance_service.get_effective_permissions = AsyncMock(
            return_value=mock_effective_permissions
        )
        
        # Test
        result = await inheritance_service.check_permission_conflicts(
            mock_db, mock_user.id
        )
        
        # Verify
        assert result["total_permissions"] == 2
        assert result["conflicted_permissions"] == 1
        assert "test:read" in result["conflicts"]
        assert "test:write" not in result["conflicts"]
    
    @pytest.mark.asyncio
    async def test_get_inheritance_statistics(
        self, 
        inheritance_service, 
        mock_db, 
        mock_user
    ):
        """Test getting inheritance statistics"""
        # Setup
        mock_effective_permissions = {
            "total_count": 5,
            "sources": [
                {"source_type": "direct"},
                {"source_type": "direct"},
                {"source_type": "group_role"},
                {"source_type": "role_hierarchy"},
                {"source_type": "group_hierarchy"}
            ]
        }
        
        mock_tree = {
            "tree": {
                "roles": [{"parent": {"parent": None}}],  # Depth 2
                "groups": [{"parent": {"parent": {"parent": None}}}]  # Depth 3
            }
        }
        
        inheritance_service.get_effective_permissions = AsyncMock(
            return_value=mock_effective_permissions
        )
        inheritance_service.get_permission_inheritance_tree = AsyncMock(
            return_value=mock_tree
        )
        
        # Test
        result = await inheritance_service.get_inheritance_statistics(
            mock_db, mock_user.id
        )
        
        # Verify
        assert result["total_permissions"] == 5
        assert result["source_breakdown"]["direct"] == 2
        assert result["source_breakdown"]["group_role"] == 1
        assert result["max_role_inheritance_depth"] == 2
        assert result["max_group_inheritance_depth"] == 3
        assert result["inheritance_complexity"] == 5
    
    @pytest.mark.asyncio
    async def test_optimize_user_permissions(
        self, 
        inheritance_service, 
        mock_db, 
        mock_user
    ):
        """Test permission optimization recommendations"""
        # Setup
        mock_effective_permissions = {
            "total_count": 15,
            "sources": [
                {
                    "permission_name": "test:read",
                    "source_type": "direct",
                    "priority": 10
                },
                {
                    "permission_name": "test:read",
                    "source_type": "group_role",
                    "priority": 7
                }
            ] + [
                {
                    "permission_name": f"perm_{i}",
                    "source_type": "direct",
                    "priority": 10
                }
                for i in range(12)
            ]
        }
        
        mock_conflicts = {
            "conflicted_permissions": 1
        }
        
        inheritance_service.get_effective_permissions = AsyncMock(
            return_value=mock_effective_permissions
        )
        inheritance_service.check_permission_conflicts = AsyncMock(
            return_value=mock_conflicts
        )
        
        # Test
        result = await inheritance_service.optimize_user_permissions(
            mock_db, mock_user.id
        )
        
        # Verify
        assert result["total_permissions"] == 15
        assert result["redundant_assignments"] == 1
        assert result["conflicts"] == 1
        assert len(result["recommendations"]) >= 1
        
        # Check for grouping recommendation
        grouping_rec = next(
            (r for r in result["recommendations"] if r["type"] == "grouping"), None
        )
        assert grouping_rec is not None
        assert "direct assignments" in grouping_rec["description"]
    
    def test_calculate_max_depth(self, inheritance_service):
        """Test calculating maximum depth in hierarchy"""
        # Setup test data
        items = [
            {
                "name": "item1",
                "parent": {
                    "name": "parent1",
                    "parent": {
                        "name": "grandparent1",
                        "parent": None
                    }
                }
            },
            {
                "name": "item2",
                "parent": {
                    "name": "parent2",
                    "parent": None
                }
            }
        ]
        
        # Test
        depth = inheritance_service._calculate_max_depth(items)
        
        # Verify
        assert depth == 3  # item1 -> parent1 -> grandparent1
    
    def test_calculate_max_depth_empty(self, inheritance_service):
        """Test calculating max depth with empty list"""
        depth = inheritance_service._calculate_max_depth([])
        assert depth == 0
    
    def test_calculate_max_depth_no_parents(self, inheritance_service):
        """Test calculating max depth with no parents"""
        items = [
            {"name": "item1", "parent": None},
            {"name": "item2", "parent": None}
        ]
        
        depth = inheritance_service._calculate_max_depth(items)
        assert depth == 1


class TestPermissionSource:
    """Test PermissionSource dataclass"""
    
    def test_permission_source_creation(self):
        """Test creating a permission source"""
        source_id = uuid4()
        source = PermissionSource(
            permission_name="test:read",
            source_type=InheritanceType.DIRECT,
            source_id=source_id,
            source_name="Test Role",
            priority=10
        )
        
        assert source.permission_name == "test:read"
        assert source.source_type == InheritanceType.DIRECT
        assert source.source_id == source_id
        assert source.source_name == "Test Role"
        assert source.priority == 10
        assert source.granted_at is None
        assert source.granted_by is None


class TestInheritanceEnums:
    """Test inheritance enums"""
    
    def test_inheritance_type_values(self):
        """Test inheritance type enum values"""
        assert InheritanceType.DIRECT.value == "direct"
        assert InheritanceType.ROLE_HIERARCHY.value == "role_hierarchy"
        assert InheritanceType.GROUP_HIERARCHY.value == "group_hierarchy"
        assert InheritanceType.GROUP_ROLE.value == "group_role"
        assert InheritanceType.MIXED.value == "mixed"
    
    def test_inheritance_policy_values(self):
        """Test inheritance policy enum values"""
        assert InheritancePolicy.ADDITIVE.value == "additive"
        assert InheritancePolicy.RESTRICTIVE.value == "restrictive"
        assert InheritancePolicy.OVERRIDE.value == "override"
        assert InheritancePolicy.PRIORITY.value == "priority"