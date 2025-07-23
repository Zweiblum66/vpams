"""
Integration tests for RBAC system

This module tests the complete RBAC flow including user creation,
role assignment, permission inheritance, and access control.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4
from datetime import datetime, timezone

from db.models import User, Role, Permission, Group, user_role_association, role_permission_association
from services.user_service import UserService
from services.rbac_service import RBACService
from services.group_service import GroupService
from services.inheritance_service import InheritanceService
from models.schemas import UserRegistrationRequest


class TestRBACIntegration:
    """Test complete RBAC system integration"""
    
    @pytest.fixture
    def user_service(self):
        """Create user service instance"""
        return UserService()
    
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
    async def test_permissions(self, test_db: AsyncSession, rbac_service):
        """Create test permissions"""
        permissions = []
        
        # Create various permissions
        permission_data = [
            ("users:read", "Read Users", "View user information", "users", "read"),
            ("users:write", "Write Users", "Create and update users", "users", "write"),
            ("users:delete", "Delete Users", "Delete users", "users", "delete"),
            ("assets:read", "Read Assets", "View assets", "assets", "read"),
            ("assets:write", "Write Assets", "Create and update assets", "assets", "write"),
            ("assets:delete", "Delete Assets", "Delete assets", "assets", "delete"),
            ("projects:read", "Read Projects", "View projects", "projects", "read"),
            ("projects:write", "Write Projects", "Create and update projects", "projects", "write"),
            ("admin:all", "Admin All", "Full admin access", "admin", "all"),
        ]
        
        for name, display_name, description, resource, action in permission_data:
            permission = await rbac_service.create_permission(
                test_db, name, display_name, description, resource, action
            )
            permissions.append(permission)
        
        return permissions
    
    @pytest.fixture
    async def test_roles(self, test_db: AsyncSession, rbac_service, test_permissions):
        """Create test roles with hierarchy"""
        roles = {}
        
        # Create base viewer role
        roles["viewer"] = await rbac_service.create_role(
            test_db,
            name="viewer",
            display_name="Viewer",
            description="Read-only access",
            role_type="system"
        )
        
        # Create editor role (inherits from viewer)
        roles["editor"] = await rbac_service.create_role(
            test_db,
            name="editor",
            display_name="Editor",
            description="Read and write access",
            role_type="system",
            parent_role_id=roles["viewer"].id
        )
        
        # Create admin role (inherits from editor)
        roles["admin"] = await rbac_service.create_role(
            test_db,
            name="admin",
            display_name="Administrator",
            description="Full access",
            role_type="system",
            parent_role_id=roles["editor"].id
        )
        
        # Create project manager role (custom role)
        roles["project_manager"] = await rbac_service.create_role(
            test_db,
            name="project_manager",
            display_name="Project Manager",
            description="Manage projects",
            role_type="custom"
        )
        
        # Assign permissions to roles
        # Viewer gets read permissions
        for perm in test_permissions:
            if perm.action == "read":
                await rbac_service.assign_permission_to_role(
                    test_db, roles["viewer"].id, perm.id
                )
        
        # Editor gets write permissions (inherits read from viewer)
        for perm in test_permissions:
            if perm.action == "write":
                await rbac_service.assign_permission_to_role(
                    test_db, roles["editor"].id, perm.id
                )
        
        # Admin gets all permissions
        admin_perm = next(p for p in test_permissions if p.name == "admin:all")
        await rbac_service.assign_permission_to_role(
            test_db, roles["admin"].id, admin_perm.id
        )
        
        # Project manager gets project permissions
        for perm in test_permissions:
            if perm.resource == "projects":
                await rbac_service.assign_permission_to_role(
                    test_db, roles["project_manager"].id, perm.id
                )
        
        return roles
    
    @pytest.fixture
    async def test_groups(self, test_db: AsyncSession, group_service, test_roles):
        """Create test groups with hierarchy"""
        groups = {}
        
        # Create department group
        groups["engineering"] = await group_service.create_group(
            test_db,
            name="engineering",
            display_name="Engineering Department",
            description="Engineering team",
            group_type="department"
        )
        
        # Create sub-department group
        groups["frontend"] = await group_service.create_group(
            test_db,
            name="frontend",
            display_name="Frontend Team",
            description="Frontend developers",
            group_type="team",
            parent_group_id=groups["engineering"].id
        )
        
        # Assign roles to groups
        await group_service.assign_role_to_group(
            test_db, groups["engineering"].id, test_roles["editor"].id
        )
        
        await group_service.assign_role_to_group(
            test_db, groups["frontend"].id, test_roles["viewer"].id
        )
        
        return groups
    
    @pytest.fixture
    async def test_users(self, test_db: AsyncSession, user_service):
        """Create test users"""
        users = {}
        
        # Create regular user
        user_data = UserRegistrationRequest(
            email="john.doe@example.com",
            username="johndoe",
            password="password123",
            first_name="John",
            last_name="Doe",
            department="Engineering",
            job_title="Developer"
        )
        users["john"] = await user_service.create_user(test_db, user_data)
        
        # Create admin user
        admin_data = UserRegistrationRequest(
            email="admin@example.com",
            username="admin",
            password="adminpass123",
            first_name="Admin",
            last_name="User",
            department="IT",
            job_title="System Administrator"
        )
        users["admin"] = await user_service.create_user(test_db, admin_data, is_superuser=True)
        
        # Create project manager
        pm_data = UserRegistrationRequest(
            email="pm@example.com",
            username="projectmgr",
            password="pmpass123",
            first_name="Project",
            last_name="Manager",
            department="Management",
            job_title="Project Manager"
        )
        users["pm"] = await user_service.create_user(test_db, pm_data)
        
        return users
    
    # Basic RBAC Flow Tests
    
    @pytest.mark.asyncio
    async def test_user_role_assignment_and_permissions(
        self, test_db, rbac_service, test_users, test_roles
    ):
        """Test assigning roles to users and checking permissions"""
        # Assign viewer role to John
        await rbac_service.assign_role_to_user(
            test_db, test_users["john"].id, test_roles["viewer"].id
        )
        
        # Check John's permissions
        permissions = await rbac_service.get_user_permissions(test_db, test_users["john"].id)
        
        # Verify John has all read permissions
        assert "users:read" in permissions
        assert "assets:read" in permissions
        assert "projects:read" in permissions
        
        # Verify John doesn't have write permissions
        assert "users:write" not in permissions
        assert "assets:write" not in permissions
    
    @pytest.mark.asyncio
    async def test_role_hierarchy_inheritance(
        self, test_db, rbac_service, test_users, test_roles
    ):
        """Test permission inheritance through role hierarchy"""
        # Assign editor role to John (inherits from viewer)
        await rbac_service.assign_role_to_user(
            test_db, test_users["john"].id, test_roles["editor"].id
        )
        
        # Check permissions with inheritance
        permissions = await rbac_service.get_user_permissions(
            test_db, test_users["john"].id, include_inherited=True
        )
        
        # Verify John has both read and write permissions
        assert "users:read" in permissions  # Inherited from viewer
        assert "users:write" in permissions  # Direct from editor
        assert "assets:read" in permissions  # Inherited
        assert "assets:write" in permissions  # Direct
        
        # Check without inheritance
        permissions_direct = await rbac_service.get_user_permissions(
            test_db, test_users["john"].id, include_inherited=False
        )
        
        # Should only have write permissions directly
        assert "users:write" in permissions_direct
        assert "users:read" not in permissions_direct  # This is inherited
    
    @pytest.mark.asyncio
    async def test_group_membership_permissions(
        self, test_db, rbac_service, group_service, test_users, test_groups
    ):
        """Test permissions through group membership"""
        # Add John to engineering group
        await group_service.add_user_to_group(
            test_db, test_users["john"].id, test_groups["engineering"].id
        )
        
        # Check permissions
        permissions = await rbac_service.get_user_permissions(test_db, test_users["john"].id)
        
        # Should have editor permissions from engineering group
        assert "users:read" in permissions
        assert "users:write" in permissions
        assert "assets:read" in permissions
        assert "assets:write" in permissions
    
    @pytest.mark.asyncio
    async def test_nested_group_inheritance(
        self, test_db, rbac_service, group_service, test_users, test_groups
    ):
        """Test permissions through nested group hierarchy"""
        # Add John to frontend team (child of engineering)
        await group_service.add_user_to_group(
            test_db, test_users["john"].id, test_groups["frontend"].id
        )
        
        # Check permissions with inheritance
        permissions = await rbac_service.get_user_permissions(
            test_db, test_users["john"].id, include_inherited=True
        )
        
        # Should have viewer permissions from frontend and editor from parent engineering
        assert "users:read" in permissions
        assert "users:write" in permissions  # From parent group
        assert "assets:read" in permissions
        assert "assets:write" in permissions  # From parent group
    
    @pytest.mark.asyncio
    async def test_multiple_role_assignments(
        self, test_db, rbac_service, test_users, test_roles
    ):
        """Test user with multiple roles"""
        # Assign both viewer and project manager roles
        await rbac_service.assign_role_to_user(
            test_db, test_users["pm"].id, test_roles["viewer"].id
        )
        await rbac_service.assign_role_to_user(
            test_db, test_users["pm"].id, test_roles["project_manager"].id
        )
        
        # Check combined permissions
        permissions = await rbac_service.get_user_permissions(test_db, test_users["pm"].id)
        
        # Should have viewer permissions plus project permissions
        assert "users:read" in permissions  # From viewer
        assert "assets:read" in permissions  # From viewer
        assert "projects:read" in permissions  # From both
        assert "projects:write" in permissions  # From project manager
        assert "users:write" not in permissions  # Not assigned
    
    @pytest.mark.asyncio
    async def test_permission_checking(
        self, test_db, rbac_service, test_users, test_roles
    ):
        """Test permission checking functionality"""
        # Assign admin role
        await rbac_service.assign_role_to_user(
            test_db, test_users["admin"].id, test_roles["admin"].id
        )
        
        # Check specific permissions
        assert await rbac_service.check_user_permission(
            test_db, test_users["admin"].id, "admin:all"
        )
        assert await rbac_service.check_user_permission(
            test_db, test_users["admin"].id, "users:read"
        )
        assert await rbac_service.check_user_permission(
            test_db, test_users["admin"].id, "users:write"
        )
        
        # Check permission they don't have
        assert not await rbac_service.check_user_permission(
            test_db, test_users["john"].id, "admin:all"
        )
    
    # Advanced Inheritance Tests
    
    @pytest.mark.asyncio
    async def test_inheritance_priority(
        self, test_db, rbac_service, group_service, inheritance_service, test_users, test_roles, test_groups
    ):
        """Test permission inheritance priority"""
        # Create conflicting permission assignments
        # Direct role: viewer
        await rbac_service.assign_role_to_user(
            test_db, test_users["john"].id, test_roles["viewer"].id
        )
        
        # Group role: editor (through engineering group)
        await group_service.add_user_to_group(
            test_db, test_users["john"].id, test_groups["engineering"].id
        )
        
        # Check effective permissions
        result = await inheritance_service.get_effective_permissions(
            test_db, test_users["john"].id, include_sources=True
        )
        
        # Verify permissions come from highest priority source
        assert "users:read" in result["permissions"]
        assert "users:write" in result["permissions"]
        
        # Check permission sources
        sources = result["sources"]
        read_sources = [s for s in sources if s["permission_name"] == "users:read"]
        write_sources = [s for s in sources if s["permission_name"] == "users:write"]
        
        # Read permission should have multiple sources
        assert len(read_sources) >= 2  # Direct and group
        
        # Write permission should come from group
        assert len(write_sources) >= 1
        assert any(s["source_type"] in ["group_role", "direct"] for s in write_sources)
    
    @pytest.mark.asyncio
    async def test_permission_conflict_detection(
        self, test_db, rbac_service, group_service, inheritance_service, test_users, test_roles, test_groups
    ):
        """Test detection of permission conflicts"""
        # Create user with overlapping permissions
        await rbac_service.assign_role_to_user(
            test_db, test_users["john"].id, test_roles["viewer"].id
        )
        await rbac_service.assign_role_to_user(
            test_db, test_users["john"].id, test_roles["editor"].id
        )
        await group_service.add_user_to_group(
            test_db, test_users["john"].id, test_groups["engineering"].id
        )
        
        # Check for conflicts
        conflicts = await inheritance_service.check_permission_conflicts(
            test_db, test_users["john"].id
        )
        
        # Should detect conflicts for overlapping permissions
        assert conflicts["conflicted_permissions"] > 0
        assert "conflicts" in conflicts
        
        # Verify specific conflicts
        for perm_name, sources in conflicts["conflicts"].items():
            assert len(sources) > 1  # Multiple sources for same permission
    
    @pytest.mark.asyncio
    async def test_inheritance_tree_visualization(
        self, test_db, inheritance_service, group_service, test_users, test_groups
    ):
        """Test getting complete inheritance tree"""
        # Add user to nested groups
        await group_service.add_user_to_group(
            test_db, test_users["john"].id, test_groups["frontend"].id
        )
        
        # Get inheritance tree
        tree = await inheritance_service.get_permission_inheritance_tree(
            test_db, test_users["john"].id
        )
        
        # Verify tree structure
        assert "tree" in tree
        user_tree = tree["tree"]
        assert "user_id" in user_tree
        assert "roles" in user_tree
        assert "groups" in user_tree
        
        # Check group hierarchy is represented
        groups = user_tree["groups"]
        assert len(groups) > 0
        
        # Frontend group should show parent
        frontend_group = next(g for g in groups if g["name"] == "frontend")
        assert frontend_group["parent"] is not None
        assert frontend_group["parent"]["name"] == "engineering"
    
    # Role and Permission Management Tests
    
    @pytest.mark.asyncio
    async def test_role_modification_affects_users(
        self, test_db, rbac_service, test_users, test_roles, test_permissions
    ):
        """Test that modifying role permissions affects users"""
        # Assign viewer role to user
        await rbac_service.assign_role_to_user(
            test_db, test_users["john"].id, test_roles["viewer"].id
        )
        
        # Check initial permissions
        permissions_before = await rbac_service.get_user_permissions(
            test_db, test_users["john"].id
        )
        assert "users:delete" not in permissions_before
        
        # Add delete permission to viewer role
        delete_perm = next(p for p in test_permissions if p.name == "users:delete")
        await rbac_service.assign_permission_to_role(
            test_db, test_roles["viewer"].id, delete_perm.id
        )
        
        # Check permissions after modification
        permissions_after = await rbac_service.get_user_permissions(
            test_db, test_users["john"].id
        )
        assert "users:delete" in permissions_after
    
    @pytest.mark.asyncio
    async def test_role_revocation(
        self, test_db, rbac_service, test_users, test_roles
    ):
        """Test revoking roles from users"""
        # Assign and then revoke role
        await rbac_service.assign_role_to_user(
            test_db, test_users["john"].id, test_roles["editor"].id
        )
        
        # Verify role assigned
        permissions = await rbac_service.get_user_permissions(test_db, test_users["john"].id)
        assert "users:write" in permissions
        
        # Revoke role
        await rbac_service.revoke_role_from_user(
            test_db, test_users["john"].id, test_roles["editor"].id
        )
        
        # Verify permissions removed
        permissions_after = await rbac_service.get_user_permissions(
            test_db, test_users["john"].id
        )
        assert "users:write" not in permissions_after
    
    # Statistics and Optimization Tests
    
    @pytest.mark.asyncio
    async def test_rbac_statistics(
        self, test_db, rbac_service, test_users, test_roles
    ):
        """Test RBAC statistics generation"""
        # Create some assignments
        for user in test_users.values():
            await rbac_service.assign_role_to_user(
                test_db, user.id, test_roles["viewer"].id
            )
        
        # Get statistics
        stats = await rbac_service.get_rbac_stats(test_db)
        
        # Verify statistics
        assert stats["total_roles"] >= 4  # At least our test roles
        assert stats["total_permissions"] >= 9  # At least our test permissions
        assert stats["total_role_assignments"] >= 3  # At least our test assignments
        assert stats["total_permission_grants"] > 0
    
    @pytest.mark.asyncio
    async def test_permission_optimization_recommendations(
        self, test_db, inheritance_service, rbac_service, test_users, test_roles, test_permissions
    ):
        """Test permission optimization recommendations"""
        # Create inefficient permission structure
        # Assign many direct permissions instead of using roles
        for perm in test_permissions[:6]:  # Assign 6 direct permissions
            # This would require direct permission assignment, which isn't in our RBAC service
            # So we'll assign multiple overlapping roles instead
            pass
        
        # Assign overlapping roles
        await rbac_service.assign_role_to_user(
            test_db, test_users["john"].id, test_roles["viewer"].id
        )
        await rbac_service.assign_role_to_user(
            test_db, test_users["john"].id, test_roles["editor"].id
        )
        
        # Get optimization recommendations
        recommendations = await inheritance_service.optimize_user_permissions(
            test_db, test_users["john"].id
        )
        
        # Should have recommendations
        assert "recommendations" in recommendations
        assert len(recommendations["recommendations"]) > 0
        
        # Check for redundancy detection
        assert recommendations["redundant_assignments"] > 0
    
    # Edge Cases and Error Handling
    
    @pytest.mark.asyncio
    async def test_circular_role_hierarchy_prevention(
        self, test_db, rbac_service, test_roles
    ):
        """Test that circular role hierarchies are prevented"""
        # Try to create circular hierarchy
        # Admin inherits from Editor, Editor inherits from Viewer
        # Try to make Viewer inherit from Admin (circular)
        
        with pytest.raises(ValueError):
            await rbac_service.update_role(
                test_db,
                test_roles["viewer"].id,
                {"parent_role_id": test_roles["admin"].id}
            )
    
    @pytest.mark.asyncio
    async def test_inactive_role_permissions_excluded(
        self, test_db, rbac_service, test_users, test_roles
    ):
        """Test that inactive roles don't grant permissions"""
        # Assign role to user
        await rbac_service.assign_role_to_user(
            test_db, test_users["john"].id, test_roles["editor"].id
        )
        
        # Deactivate the role
        await rbac_service.update_role(
            test_db,
            test_roles["editor"].id,
            {"is_active": False}
        )
        
        # Check permissions - should not include editor permissions
        permissions = await rbac_service.get_user_permissions(
            test_db, test_users["john"].id
        )
        
        # Editor write permissions should not be included
        assert "users:write" not in permissions
        assert "assets:write" not in permissions
    
    @pytest.mark.asyncio
    async def test_permission_assignment_idempotency(
        self, test_db, rbac_service, test_users, test_roles
    ):
        """Test that repeated permission assignments are idempotent"""
        # Assign same role multiple times
        for _ in range(3):
            result = await rbac_service.assign_role_to_user(
                test_db, test_users["john"].id, test_roles["viewer"].id
            )
            assert result is True
        
        # Check user still has role only once
        user = await test_db.get(User, test_users["john"].id)
        await test_db.refresh(user, ["roles"])
        
        viewer_roles = [r for r in user.roles if r.name == "viewer"]
        assert len(viewer_roles) == 1