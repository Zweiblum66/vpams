"""
RBAC Service

Service for managing roles and permissions in the RBAC system.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_, or_, func, desc
from sqlalchemy.orm import selectinload, joinedload
from typing import Optional, List, Dict, Any, Set
from uuid import UUID
from datetime import datetime, timezone
import logging

from db.models import User, Role, Permission, Group, user_role_association, role_permission_association
from models.schemas import PaginationParams, SortParams, FilterParams

logger = logging.getLogger(__name__)


class RBACService:
    """Service for Role-Based Access Control management"""
    
    async def create_role(
        self,
        db: AsyncSession,
        name: str,
        display_name: str,
        description: Optional[str] = None,
        role_type: str = "custom",
        parent_role_id: Optional[UUID] = None,
        creator_id: Optional[UUID] = None
    ) -> Role:
        """Create a new role"""
        try:
            # Check if role name already exists
            existing_role = await self.get_role_by_name(db, name)
            if existing_role:
                raise ValueError(f"Role with name '{name}' already exists")
            
            # Validate parent role if provided
            if parent_role_id:
                parent_role = await self.get_role_by_id(db, parent_role_id)
                if not parent_role:
                    raise ValueError(f"Parent role not found")
            
            # Create new role
            role = Role(
                name=name,
                display_name=display_name,
                description=description,
                role_type=role_type,
                parent_role_id=parent_role_id,
                created_by=creator_id,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            db.add(role)
            await db.commit()
            await db.refresh(role)
            
            logger.info(f"Role created: {name}")
            return role
            
        except Exception as e:
            logger.error(f"Error creating role: {e}")
            await db.rollback()
            raise
    
    async def get_role_by_id(self, db: AsyncSession, role_id: UUID) -> Optional[Role]:
        """Get role by ID"""
        try:
            result = await db.execute(
                select(Role)
                .options(
                    selectinload(Role.permissions),
                    selectinload(Role.users),
                    selectinload(Role.parent_role),
                    selectinload(Role.child_roles)
                )
                .where(Role.id == role_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting role by ID: {e}")
            return None
    
    async def get_role_by_name(self, db: AsyncSession, name: str) -> Optional[Role]:
        """Get role by name"""
        try:
            result = await db.execute(
                select(Role)
                .options(
                    selectinload(Role.permissions),
                    selectinload(Role.users)
                )
                .where(Role.name == name)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting role by name: {e}")
            return None
    
    async def get_roles(
        self,
        db: AsyncSession,
        pagination: PaginationParams,
        sort: SortParams,
        filters: Optional[Dict[str, Any]] = None
    ) -> tuple[List[Role], int]:
        """Get paginated list of roles"""
        try:
            # Build base query
            query = select(Role).options(
                selectinload(Role.permissions),
                selectinload(Role.users),
                selectinload(Role.parent_role)
            )
            
            # Apply filters
            conditions = []
            if filters:
                if filters.get("is_active") is not None:
                    conditions.append(Role.is_active == filters["is_active"])
                if filters.get("role_type"):
                    conditions.append(Role.role_type == filters["role_type"])
                if filters.get("is_system") is not None:
                    conditions.append(Role.is_system == filters["is_system"])
                if filters.get("parent_role_id"):
                    conditions.append(Role.parent_role_id == filters["parent_role_id"])
            
            if conditions:
                query = query.where(and_(*conditions))
            
            # Apply sorting
            if sort.sort == "name":
                order_col = Role.name
            elif sort.sort == "display_name":
                order_col = Role.display_name
            elif sort.sort == "role_type":
                order_col = Role.role_type
            elif sort.sort == "created_at":
                order_col = Role.created_at
            else:
                order_col = Role.created_at
            
            if sort.order == "desc":
                query = query.order_by(desc(order_col))
            else:
                query = query.order_by(order_col)
            
            # Get total count
            count_query = select(func.count(Role.id))
            if conditions:
                count_query = count_query.where(and_(*conditions))
            
            total_result = await db.execute(count_query)
            total_count = total_result.scalar()
            
            # Apply pagination
            query = query.offset(pagination.offset).limit(pagination.limit)
            
            # Execute query
            result = await db.execute(query)
            roles = result.scalars().all()
            
            return list(roles), total_count
            
        except Exception as e:
            logger.error(f"Error getting roles: {e}")
            return [], 0
    
    async def update_role(
        self,
        db: AsyncSession,
        role_id: UUID,
        updates: Dict[str, Any],
        updater_id: Optional[UUID] = None
    ) -> Optional[Role]:
        """Update role information"""
        try:
            role = await self.get_role_by_id(db, role_id)
            if not role:
                return None
            
            # Check if role is system role
            if role.is_system and not updates.get("allow_system_update", False):
                raise ValueError("Cannot update system role")
            
            # Update fields
            for key, value in updates.items():
                if key == "allow_system_update":
                    continue
                if hasattr(role, key):
                    setattr(role, key, value)
            
            role.updated_at = datetime.now(timezone.utc)
            
            await db.commit()
            await db.refresh(role)
            
            logger.info(f"Role updated: {role.name}")
            return role
            
        except Exception as e:
            logger.error(f"Error updating role: {e}")
            await db.rollback()
            raise
    
    async def delete_role(self, db: AsyncSession, role_id: UUID) -> bool:
        """Delete a role"""
        try:
            role = await self.get_role_by_id(db, role_id)
            if not role:
                return False
            
            # Check if role is system role
            if role.is_system:
                raise ValueError("Cannot delete system role")
            
            # Check if role has users
            if role.users:
                raise ValueError("Cannot delete role with assigned users")
            
            # Check if role has child roles
            if role.child_roles:
                raise ValueError("Cannot delete role with child roles")
            
            await db.delete(role)
            await db.commit()
            
            logger.info(f"Role deleted: {role.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting role: {e}")
            await db.rollback()
            raise
    
    async def create_permission(
        self,
        db: AsyncSession,
        name: str,
        display_name: str,
        description: Optional[str] = None,
        resource: str = "general",
        action: str = "read",
        category: str = "general",
        scope: str = "global",
        creator_id: Optional[UUID] = None
    ) -> Permission:
        """Create a new permission"""
        try:
            # Check if permission already exists
            existing_permission = await self.get_permission_by_name(db, name)
            if existing_permission:
                raise ValueError(f"Permission with name '{name}' already exists")
            
            # Create new permission
            permission = Permission(
                name=name,
                display_name=display_name,
                description=description,
                resource=resource,
                action=action,
                category=category,
                scope=scope,
                created_by=creator_id,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            db.add(permission)
            await db.commit()
            await db.refresh(permission)
            
            logger.info(f"Permission created: {name}")
            return permission
            
        except Exception as e:
            logger.error(f"Error creating permission: {e}")
            await db.rollback()
            raise
    
    async def get_permission_by_id(self, db: AsyncSession, permission_id: UUID) -> Optional[Permission]:
        """Get permission by ID"""
        try:
            result = await db.execute(
                select(Permission)
                .options(selectinload(Permission.roles))
                .where(Permission.id == permission_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting permission by ID: {e}")
            return None
    
    async def get_permission_by_name(self, db: AsyncSession, name: str) -> Optional[Permission]:
        """Get permission by name"""
        try:
            result = await db.execute(
                select(Permission)
                .options(selectinload(Permission.roles))
                .where(Permission.name == name)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting permission by name: {e}")
            return None
    
    async def get_permissions(
        self,
        db: AsyncSession,
        pagination: PaginationParams,
        sort: SortParams,
        filters: Optional[Dict[str, Any]] = None
    ) -> tuple[List[Permission], int]:
        """Get paginated list of permissions"""
        try:
            # Build base query
            query = select(Permission).options(selectinload(Permission.roles))
            
            # Apply filters
            conditions = []
            if filters:
                if filters.get("is_active") is not None:
                    conditions.append(Permission.is_active == filters["is_active"])
                if filters.get("resource"):
                    conditions.append(Permission.resource == filters["resource"])
                if filters.get("action"):
                    conditions.append(Permission.action == filters["action"])
                if filters.get("category"):
                    conditions.append(Permission.category == filters["category"])
                if filters.get("scope"):
                    conditions.append(Permission.scope == filters["scope"])
                if filters.get("is_system") is not None:
                    conditions.append(Permission.is_system == filters["is_system"])
            
            if conditions:
                query = query.where(and_(*conditions))
            
            # Apply sorting
            if sort.sort == "name":
                order_col = Permission.name
            elif sort.sort == "resource":
                order_col = Permission.resource
            elif sort.sort == "action":
                order_col = Permission.action
            elif sort.sort == "category":
                order_col = Permission.category
            elif sort.sort == "created_at":
                order_col = Permission.created_at
            else:
                order_col = Permission.created_at
            
            if sort.order == "desc":
                query = query.order_by(desc(order_col))
            else:
                query = query.order_by(order_col)
            
            # Get total count
            count_query = select(func.count(Permission.id))
            if conditions:
                count_query = count_query.where(and_(*conditions))
            
            total_result = await db.execute(count_query)
            total_count = total_result.scalar()
            
            # Apply pagination
            query = query.offset(pagination.offset).limit(pagination.limit)
            
            # Execute query
            result = await db.execute(query)
            permissions = result.scalars().all()
            
            return list(permissions), total_count
            
        except Exception as e:
            logger.error(f"Error getting permissions: {e}")
            return [], 0
    
    async def assign_permission_to_role(
        self,
        db: AsyncSession,
        role_id: UUID,
        permission_id: UUID,
        granter_id: Optional[UUID] = None
    ) -> bool:
        """Assign a permission to a role"""
        try:
            # Check if role exists
            role = await self.get_role_by_id(db, role_id)
            if not role:
                raise ValueError("Role not found")
            
            # Check if permission exists
            permission = await self.get_permission_by_id(db, permission_id)
            if not permission:
                raise ValueError("Permission not found")
            
            # Check if permission is already assigned
            existing_result = await db.execute(
                select(role_permission_association)
                .where(
                    role_permission_association.c.role_id == role_id,
                    role_permission_association.c.permission_id == permission_id
                )
            )
            
            if existing_result.first():
                return True  # Already assigned
            
            # Assign permission to role
            assignment = role_permission_association.insert().values(
                role_id=role_id,
                permission_id=permission_id,
                granted_by=granter_id,
                granted_at=datetime.now(timezone.utc)
            )
            
            await db.execute(assignment)
            await db.commit()
            
            logger.info(f"Permission {permission.name} assigned to role {role.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error assigning permission to role: {e}")
            await db.rollback()
            raise
    
    async def revoke_permission_from_role(
        self,
        db: AsyncSession,
        role_id: UUID,
        permission_id: UUID
    ) -> bool:
        """Revoke a permission from a role"""
        try:
            # Remove the assignment
            delete_stmt = delete(role_permission_association).where(
                role_permission_association.c.role_id == role_id,
                role_permission_association.c.permission_id == permission_id
            )
            
            result = await db.execute(delete_stmt)
            await db.commit()
            
            if result.rowcount > 0:
                logger.info(f"Permission revoked from role")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error revoking permission from role: {e}")
            await db.rollback()
            raise
    
    async def assign_role_to_user(
        self,
        db: AsyncSession,
        user_id: UUID,
        role_id: UUID,
        assigner_id: Optional[UUID] = None
    ) -> bool:
        """Assign a role to a user"""
        try:
            # Check if role exists
            role = await self.get_role_by_id(db, role_id)
            if not role:
                raise ValueError("Role not found")
            
            # Check if user exists
            user_result = await db.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            if not user:
                raise ValueError("User not found")
            
            # Check if role is already assigned
            existing_result = await db.execute(
                select(user_role_association)
                .where(
                    user_role_association.c.user_id == user_id,
                    user_role_association.c.role_id == role_id
                )
            )
            
            if existing_result.first():
                return True  # Already assigned
            
            # Assign role to user
            assignment = user_role_association.insert().values(
                user_id=user_id,
                role_id=role_id,
                assigned_by=assigner_id,
                assigned_at=datetime.now(timezone.utc)
            )
            
            await db.execute(assignment)
            await db.commit()
            
            logger.info(f"Role {role.name} assigned to user {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Error assigning role to user: {e}")
            await db.rollback()
            raise
    
    async def revoke_role_from_user(
        self,
        db: AsyncSession,
        user_id: UUID,
        role_id: UUID
    ) -> bool:
        """Revoke a role from a user"""
        try:
            # Remove the assignment
            delete_stmt = delete(user_role_association).where(
                user_role_association.c.user_id == user_id,
                user_role_association.c.role_id == role_id
            )
            
            result = await db.execute(delete_stmt)
            await db.commit()
            
            if result.rowcount > 0:
                logger.info(f"Role revoked from user")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error revoking role from user: {e}")
            await db.rollback()
            raise
    
    async def get_user_permissions(
        self,
        db: AsyncSession,
        user_id: UUID,
        include_inherited: bool = True
    ) -> Set[str]:
        """Get all permissions for a user (including group permissions)"""
        try:
            # Get user with roles and groups
            user_result = await db.execute(
                select(User)
                .options(
                    selectinload(User.roles).selectinload(Role.permissions),
                    selectinload(User.groups).selectinload(Group.roles).selectinload(Role.permissions),
                    selectinload(User.groups).selectinload(Group.permissions)
                )
                .where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                return set()
            
            permissions = set()
            
            # Collect permissions from direct roles
            for role in user.roles:
                if not role.is_active:
                    continue
                
                # Add direct permissions
                for permission in role.permissions:
                    if permission.is_active:
                        permissions.add(permission.name)
                
                # Add inherited permissions if requested
                if include_inherited and role.parent_role_id:
                    inherited_perms = await self.get_role_permissions(
                        db, role.parent_role_id, include_inherited=True
                    )
                    permissions.update(inherited_perms)
            
            # Collect permissions from groups
            for group in user.groups:
                if not group.is_active:
                    continue
                
                # Add direct group permissions
                for permission in group.permissions:
                    if permission.is_active:
                        permissions.add(permission.name)
                
                # Add permissions from group roles
                for role in group.roles:
                    if not role.is_active:
                        continue
                    
                    for permission in role.permissions:
                        if permission.is_active:
                            permissions.add(permission.name)
                    
                    # Add inherited permissions from role hierarchy
                    if include_inherited and role.parent_role_id:
                        inherited_perms = await self.get_role_permissions(
                            db, role.parent_role_id, include_inherited=True
                        )
                        permissions.update(inherited_perms)
                
                # Add inherited permissions from group hierarchy
                if include_inherited and group.parent_group_id:
                    from .group_service import GroupService
                    group_service = GroupService()
                    inherited_perms = await group_service.get_group_permissions(
                        db, group.parent_group_id, include_inherited=True
                    )
                    permissions.update(inherited_perms)
            
            return permissions
            
        except Exception as e:
            logger.error(f"Error getting user permissions: {e}")
            return set()
    
    async def get_role_permissions(
        self,
        db: AsyncSession,
        role_id: UUID,
        include_inherited: bool = True
    ) -> Set[str]:
        """Get all permissions for a role"""
        try:
            role = await self.get_role_by_id(db, role_id)
            if not role or not role.is_active:
                return set()
            
            permissions = set()
            
            # Add direct permissions
            for permission in role.permissions:
                if permission.is_active:
                    permissions.add(permission.name)
            
            # Add inherited permissions if requested
            if include_inherited and role.parent_role_id:
                inherited_perms = await self.get_role_permissions(
                    db, role.parent_role_id, include_inherited=True
                )
                permissions.update(inherited_perms)
            
            return permissions
            
        except Exception as e:
            logger.error(f"Error getting role permissions: {e}")
            return set()
    
    async def check_user_permission(
        self,
        db: AsyncSession,
        user_id: UUID,
        permission_name: str,
        include_inherited: bool = True
    ) -> bool:
        """Check if user has a specific permission"""
        try:
            user_permissions = await self.get_user_permissions(
                db, user_id, include_inherited
            )
            return permission_name in user_permissions
            
        except Exception as e:
            logger.error(f"Error checking user permission: {e}")
            return False
    
    async def get_rbac_stats(self, db: AsyncSession) -> Dict[str, Any]:
        """Get RBAC system statistics"""
        try:
            # Count roles
            roles_result = await db.execute(select(func.count(Role.id)))
            roles_count = roles_result.scalar()
            
            # Count permissions
            permissions_result = await db.execute(select(func.count(Permission.id)))
            permissions_count = permissions_result.scalar()
            
            # Count role assignments
            assignments_result = await db.execute(
                select(func.count()).select_from(user_role_association)
            )
            assignments_count = assignments_result.scalar()
            
            # Count permission grants
            grants_result = await db.execute(
                select(func.count()).select_from(role_permission_association)
            )
            grants_count = grants_result.scalar()
            
            return {
                "total_roles": roles_count,
                "total_permissions": permissions_count,
                "total_role_assignments": assignments_count,
                "total_permission_grants": grants_count
            }
            
        except Exception as e:
            logger.error(f"Error getting RBAC stats: {e}")
            return {
                "total_roles": 0,
                "total_permissions": 0,
                "total_role_assignments": 0,
                "total_permission_grants": 0
            }