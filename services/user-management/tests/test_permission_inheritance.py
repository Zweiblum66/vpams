"""
Test cases for Permission Inheritance

This module tests the permission inheritance system including
direct permissions, role hierarchy, group hierarchy, and mixed inheritance.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from services.rbac_service import RBACService
from services.group_service import GroupService
from services.inheritance_service import InheritanceService, InheritanceType
from db.models import User, Role, Permission, Group


class TestPermissionInheritance:
    """Test permission inheritance scenarios"""
    
    @pytest.fixture
    def rbac_service(self):
        """Create RBAC service instance"""
        return RBACService()
    
    @pytest.fixture
    def group_service(self):
        """Create group service instance"""
        return GroupService()
    
    @pytest.fixture
    def inheritance_service(self):
        """Create inheritance service instance"""
        return InheritanceService()
    
    @pytest.fixture
    async def complex_hierarchy(self, test_db: AsyncSession, rbac_service, group_service):
        """Create a complex permission hierarchy for testing"""
        data = {"users": {}, "roles": {}, "permissions": {}, "groups": {}}
        
        # Create permissions
        permissions = [
            ("read:all", "Read All", "Read everything"),
            ("write:all", "Write All", "Write everything"),
            ("delete:all", "Delete All", "Delete everything"),
            ("users:manage", "Manage Users", "User management"),
            ("projects:manage", "Manage Projects", "Project management"),
            ("assets:view", "View Assets", "View assets"),
            ("assets:edit", "Edit Assets", "Edit assets"),
            ("reports:view", "View Reports", "View reports"),
            ("reports:generate", "Generate Reports", "Generate reports"),
            ("settings:view", "View Settings", "View settings"),
            ("settings:edit", "Edit Settings", "Edit settings"),
        ]
        
        for name, display_name, description in permissions:
            perm = await rbac_service.create_permission(
                test_db, name, display_name, description
            )
            data["permissions"][name] = perm
        
        # Create role hierarchy
        # Base roles
        data["roles"]["viewer"] = await rbac_service.create_role(
            test_db, "viewer", "Viewer", "Basic viewing permissions"
        )
        
        data["roles"]["contributor"] = await rbac_service.create_role(
            test_db, "contributor", "Contributor", "Can contribute content",
            parent_role_id=data["roles"]["viewer"].id
        )
        
        data["roles"]["editor"] = await rbac_service.create_role(
            test_db, "editor", "Editor", "Can edit content",
            parent_role_id=data["roles"]["contributor"].id
        )
        
        data["roles"]["manager"] = await rbac_service.create_role(
            test_db, "manager", "Manager", "Can manage resources",
            parent_role_id=data["roles"]["editor"].id
        )
        
        data["roles"]["admin"] = await rbac_service.create_role(
            test_db, "admin", "Administrator", "Full admin access",
            parent_role_id=data["roles"]["manager"].id
        )
        
        # Specialized roles (not in main hierarchy)
        data["roles"]["reporter"] = await rbac_service.create_role(
            test_db, "reporter", "Reporter", "Can view and generate reports"
        )
        
        data["roles"]["project_lead"] = await rbac_service.create_role(
            test_db, "project_lead", "Project Lead", "Project leadership"
        )
        
        # Assign permissions to roles
        # Viewer: basic view permissions
        await rbac_service.assign_permission_to_role(
            test_db, data["roles"]["viewer"].id, data["permissions"]["assets:view"].id
        )
        await rbac_service.assign_permission_to_role(
            test_db, data["roles"]["viewer"].id, data["permissions"]["reports:view"].id
        )
        
        # Contributor: can edit assets (inherits view from viewer)
        await rbac_service.assign_permission_to_role(
            test_db, data["roles"]["contributor"].id, data["permissions"]["assets:edit"].id
        )
        
        # Editor: settings view (inherits from contributor)
        await rbac_service.assign_permission_to_role(
            test_db, data["roles"]["editor"].id, data["permissions"]["settings:view"].id
        )
        
        # Manager: user and project management (inherits from editor)
        await rbac_service.assign_permission_to_role(
            test_db, data["roles"]["manager"].id, data["permissions"]["users:manage"].id
        )
        await rbac_service.assign_permission_to_role(
            test_db, data["roles"]["manager"].id, data["permissions"]["projects:manage"].id
        )
        
        # Admin: all permissions (inherits from manager)
        await rbac_service.assign_permission_to_role(
            test_db, data["roles"]["admin"].id, data["permissions"]["read:all"].id
        )
        await rbac_service.assign_permission_to_role(
            test_db, data["roles"]["admin"].id, data["permissions"]["write:all"].id
        )
        await rbac_service.assign_permission_to_role(
            test_db, data["roles"]["admin"].id, data["permissions"]["delete:all"].id
        )
        await rbac_service.assign_permission_to_role(
            test_db, data["roles"]["admin"].id, data["permissions"]["settings:edit"].id
        )
        
        # Reporter: report permissions
        await rbac_service.assign_permission_to_role(
            test_db, data["roles"]["reporter"].id, data["permissions"]["reports:view"].id
        )
        await rbac_service.assign_permission_to_role(
            test_db, data["roles"]["reporter"].id, data["permissions"]["reports:generate"].id
        )
        
        # Project lead: project management
        await rbac_service.assign_permission_to_role(
            test_db, data["roles"]["project_lead"].id, data["permissions"]["projects:manage"].id
        )
        
        # Create group hierarchy
        data["groups"]["company"] = await group_service.create_group(
            test_db, "company", "Company", "Entire company"
        )
        
        data["groups"]["engineering"] = await group_service.create_group(
            test_db, "engineering", "Engineering", "Engineering department",
            parent_group_id=data["groups"]["company"].id
        )
        
        data["groups"]["qa"] = await group_service.create_group(
            test_db, "qa", "QA", "Quality Assurance",
            parent_group_id=data["groups"]["engineering"].id
        )
        
        data["groups"]["devops"] = await group_service.create_group(
            test_db, "devops", "DevOps", "DevOps team",
            parent_group_id=data["groups"]["engineering"].id
        )
        
        data["groups"]["management"] = await group_service.create_group(
            test_db, "management", "Management", "Management team",
            parent_group_id=data["groups"]["company"].id
        )
        
        # Assign roles to groups
        await group_service.assign_role_to_group(
            test_db, data["groups"]["company"].id, data["roles"]["viewer"].id
        )
        
        await group_service.assign_role_to_group(
            test_db, data["groups"]["engineering"].id, data["roles"]["contributor"].id
        )
        
        await group_service.assign_role_to_group(
            test_db, data["groups"]["qa"].id, data["roles"]["reporter"].id
        )
        
        await group_service.assign_role_to_group(
            test_db, data["groups"]["management"].id, data["roles"]["manager"].id
        )
        
        # Assign direct group permissions
        await group_service.assign_permission_to_group(
            test_db, data["groups"]["devops"].id, data["permissions"]["settings:edit"].id
        )
        
        # Create test users
        from models.schemas import UserRegistrationRequest
        from services.user_service import UserService
        user_service = UserService()
        
        users_data = [
            ("john", "john@example.com", "John", "Developer", ["engineering"]),
            ("jane", "jane@example.com", "Jane", "QA Engineer", ["qa"]),
            ("bob", "bob@example.com", "Bob", "DevOps Engineer", ["devops"]),
            ("alice", "alice@example.com", "Alice", "Manager", ["management"]),
            ("charlie", "charlie@example.com", "Charlie", "Admin", []),
        ]
        
        for username, email, first_name, job_title, groups in users_data:
            user_req = UserRegistrationRequest(
                email=email,
                username=username,
                password="password123",
                first_name=first_name,
                last_name="Doe",
                job_title=job_title
            )
            user = await user_service.create_user(test_db, user_req)
            data["users"][username] = user
            
            # Add to groups
            for group_name in groups:
                await group_service.add_user_to_group(
                    test_db, user.id, data["groups"][group_name].id
                )
        
        # Assign direct roles to some users
        await rbac_service.assign_role_to_user(
            test_db, data["users"]["charlie"].id, data["roles"]["admin"].id
        )
        
        await rbac_service.assign_role_to_user(
            test_db, data["users"]["alice"].id, data["roles"]["project_lead"].id
        )
        
        return data
    
    # Basic Inheritance Tests
    
    @pytest.mark.asyncio
    async def test_direct_role_permissions(
        self, test_db, rbac_service, complex_hierarchy
    ):
        """Test permissions from directly assigned roles"""
        charlie = complex_hierarchy["users"]["charlie"]
        
        # Check Charlie's permissions (admin role)
        permissions = await rbac_service.get_user_permissions(
            test_db, charlie.id, include_inherited=False
        )
        
        # Should have direct admin permissions only
        assert "read:all" in permissions
        assert "write:all" in permissions
        assert "delete:all" in permissions
        assert "settings:edit" in permissions
        
        # Should not have inherited permissions when include_inherited=False
        assert "assets:view" not in permissions
    
    @pytest.mark.asyncio
    async def test_role_hierarchy_inheritance(
        self, test_db, rbac_service, complex_hierarchy
    ):
        """Test permissions inherited through role hierarchy"""
        charlie = complex_hierarchy["users"]["charlie"]
        
        # Check with inheritance enabled
        permissions = await rbac_service.get_user_permissions(
            test_db, charlie.id, include_inherited=True
        )
        
        # Should have all permissions from admin and its parent roles
        expected = [
            "read:all", "write:all", "delete:all",  # Admin direct
            "users:manage", "projects:manage",  # Manager
            "settings:view", "settings:edit",  # Editor + Admin
            "assets:edit",  # Contributor
            "assets:view", "reports:view"  # Viewer
        ]
        
        for perm in expected:
            assert perm in permissions
    
    @pytest.mark.asyncio
    async def test_group_role_permissions(
        self, test_db, rbac_service, complex_hierarchy
    ):
        """Test permissions from group role assignments"""
        john = complex_hierarchy["users"]["john"]
        
        # John is in engineering group which has contributor role
        permissions = await rbac_service.get_user_permissions(
            test_db, john.id, include_inherited=True
        )
        
        # Should have contributor permissions and inherited viewer permissions
        assert "assets:view" in permissions  # From viewer (parent of contributor)
        assert "assets:edit" in permissions  # From contributor
        assert "reports:view" in permissions  # From viewer
    
    @pytest.mark.asyncio
    async def test_group_hierarchy_inheritance(
        self, test_db, rbac_service, complex_hierarchy
    ):
        """Test permissions inherited through group hierarchy"""
        jane = complex_hierarchy["users"]["jane"]
        
        # Jane is in QA (child of engineering, grandchild of company)
        permissions = await rbac_service.get_user_permissions(
            test_db, jane.id, include_inherited=True
        )
        
        # Should have:
        # - Reporter permissions from QA group
        # - Contributor permissions from parent engineering group
        # - Viewer permissions from grandparent company group
        assert "reports:view" in permissions  # Reporter
        assert "reports:generate" in permissions  # Reporter
        assert "assets:edit" in permissions  # Contributor (from engineering)
        assert "assets:view" in permissions  # Viewer (from company)
    
    @pytest.mark.asyncio
    async def test_direct_group_permissions(
        self, test_db, rbac_service, complex_hierarchy
    ):
        """Test direct permissions assigned to groups"""
        bob = complex_hierarchy["users"]["bob"]
        
        # Bob is in DevOps which has direct permission and inherits from engineering
        permissions = await rbac_service.get_user_permissions(
            test_db, bob.id, include_inherited=True
        )
        
        # Should have direct group permission
        assert "settings:edit" in permissions  # Direct from DevOps group
        
        # Plus inherited permissions
        assert "assets:edit" in permissions  # From engineering (contributor)
        assert "assets:view" in permissions  # From company (viewer)
    
    @pytest.mark.asyncio
    async def test_mixed_inheritance_sources(
        self, test_db, rbac_service, inheritance_service, complex_hierarchy
    ):
        """Test permissions from multiple inheritance sources"""
        alice = complex_hierarchy["users"]["alice"]
        
        # Alice has:
        # - Direct role: project_lead
        # - Group: management (with manager role, inheriting up to viewer)
        
        # Get effective permissions with sources
        result = await inheritance_service.get_effective_permissions(
            test_db, alice.id, include_sources=True
        )
        
        permissions = result["permissions"]
        sources = result["sources"]
        
        # Should have combined permissions
        assert "projects:manage" in permissions  # From both project_lead and manager
        assert "users:manage" in permissions  # From manager
        assert "assets:view" in permissions  # Inherited through manager
        
        # Check sources for projects:manage (should have multiple sources)
        project_sources = [s for s in sources if s["permission_name"] == "projects:manage"]
        assert len(project_sources) >= 2  # Direct role and group role
        
        source_types = [s["source_type"] for s in project_sources]
        assert "direct" in source_types
        assert any(t in ["group_role", "role_hierarchy"] for t in source_types)
    
    # Complex Inheritance Scenarios
    
    @pytest.mark.asyncio
    async def test_deep_hierarchy_inheritance(
        self, test_db, rbac_service, group_service, complex_hierarchy
    ):
        """Test inheritance through deep hierarchies"""
        # Create a user in the deepest group (QA)
        from models.schemas import UserRegistrationRequest
        from services.user_service import UserService
        user_service = UserService()
        
        deep_user_req = UserRegistrationRequest(
            email="deep@example.com",
            username="deepuser",
            password="password123",
            first_name="Deep",
            last_name="User"
        )
        deep_user = await user_service.create_user(test_db, deep_user_req)
        
        # Add to QA group (3 levels deep: company -> engineering -> QA)
        await group_service.add_user_to_group(
            test_db, deep_user.id, complex_hierarchy["groups"]["qa"].id
        )
        
        # Check permissions
        permissions = await rbac_service.get_user_permissions(
            test_db, deep_user.id, include_inherited=True
        )
        
        # Should have permissions from all levels
        assert "reports:generate" in permissions  # QA direct
        assert "assets:edit" in permissions  # Engineering
        assert "assets:view" in permissions  # Company
    
    @pytest.mark.asyncio
    async def test_inheritance_tree_depth(
        self, test_db, inheritance_service, complex_hierarchy
    ):
        """Test inheritance tree depth calculation"""
        alice = complex_hierarchy["users"]["alice"]
        
        # Get inheritance statistics
        stats = await inheritance_service.get_inheritance_statistics(
            test_db, alice.id
        )
        
        # Check depth metrics
        assert stats["max_role_inheritance_depth"] >= 4  # manager -> editor -> contributor -> viewer
        assert stats["max_group_inheritance_depth"] >= 2  # management -> company
        assert stats["inheritance_complexity"] > 0
    
    @pytest.mark.asyncio
    async def test_permission_priority_resolution(
        self, test_db, rbac_service, group_service, inheritance_service, complex_hierarchy
    ):
        """Test permission priority when same permission from multiple sources"""
        # Create a user with overlapping permissions
        from models.schemas import UserRegistrationRequest
        from services.user_service import UserService
        user_service = UserService()
        
        overlap_req = UserRegistrationRequest(
            email="overlap@example.com",
            username="overlapuser",
            password="password123",
            first_name="Overlap",
            last_name="User"
        )
        overlap_user = await user_service.create_user(test_db, overlap_req)
        
        # Assign viewer role directly (priority 10)
        await rbac_service.assign_role_to_user(
            test_db, overlap_user.id, complex_hierarchy["roles"]["viewer"].id
        )
        
        # Add to engineering group (has contributor which inherits viewer - priority 7)
        await group_service.add_user_to_group(
            test_db, overlap_user.id, complex_hierarchy["groups"]["engineering"].id
        )
        
        # Check effective permissions with sources
        result = await inheritance_service.get_effective_permissions(
            test_db, overlap_user.id, include_sources=True
        )
        
        # Find assets:view permission sources
        view_sources = [s for s in result["sources"] if s["permission_name"] == "assets:view"]
        
        # Should resolve to highest priority (direct role assignment)
        assert len(view_sources) > 0
        highest_priority_source = max(view_sources, key=lambda s: s.get("priority", 0))
        assert highest_priority_source["source_type"] == "direct"
    
    @pytest.mark.asyncio
    async def test_inactive_elements_excluded(
        self, test_db, rbac_service, group_service, complex_hierarchy
    ):
        """Test that inactive roles, groups, and permissions are excluded"""
        john = complex_hierarchy["users"]["john"]
        
        # Get initial permissions
        permissions_before = await rbac_service.get_user_permissions(
            test_db, john.id, include_inherited=True
        )
        assert "assets:edit" in permissions_before
        
        # Deactivate the contributor role
        await rbac_service.update_role(
            test_db,
            complex_hierarchy["roles"]["contributor"].id,
            {"is_active": False}
        )
        
        # Check permissions after deactivation
        permissions_after = await rbac_service.get_user_permissions(
            test_db, john.id, include_inherited=True
        )
        
        # Should not have contributor permissions anymore
        assert "assets:edit" not in permissions_after
        # But should still have viewer permissions from company group
        assert "assets:view" in permissions_after
    
    @pytest.mark.asyncio
    async def test_circular_inheritance_prevention(
        self, test_db, group_service, complex_hierarchy
    ):
        """Test that circular inheritance is prevented"""
        # Try to make company group a child of QA (which is already its grandchild)
        with pytest.raises(ValueError):
            await group_service.update_group(
                test_db,
                complex_hierarchy["groups"]["company"].id,
                {"parent_group_id": complex_hierarchy["groups"]["qa"].id}
            )
    
    @pytest.mark.asyncio
    async def test_optimization_recommendations(
        self, test_db, inheritance_service, rbac_service, complex_hierarchy
    ):
        """Test permission optimization recommendations"""
        # Create a user with redundant permissions
        from models.schemas import UserRegistrationRequest
        from services.user_service import UserService
        user_service = UserService()
        
        redundant_req = UserRegistrationRequest(
            email="redundant@example.com",
            username="redundantuser",
            password="password123",
            first_name="Redundant",
            last_name="User"
        )
        redundant_user = await user_service.create_user(test_db, redundant_req)
        
        # Assign both viewer and editor roles (editor inherits from viewer)
        await rbac_service.assign_role_to_user(
            test_db, redundant_user.id, complex_hierarchy["roles"]["viewer"].id
        )
        await rbac_service.assign_role_to_user(
            test_db, redundant_user.id, complex_hierarchy["roles"]["editor"].id
        )
        
        # Get optimization recommendations
        result = await inheritance_service.optimize_user_permissions(
            test_db, redundant_user.id
        )
        
        # Should detect redundancy
        assert result["redundant_assignments"] > 0
        assert len(result["recommendations"]) > 0
        
        # Should recommend removing viewer role
        redundancy_recs = [r for r in result["recommendations"] if r["type"] == "redundancy"]
        assert len(redundancy_recs) > 0