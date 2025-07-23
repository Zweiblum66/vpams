"""
Group Service

Service for managing user groups in the RBAC system.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_, or_, func, desc
from sqlalchemy.orm import selectinload, joinedload
from typing import Optional, List, Dict, Any, Set
from uuid import UUID
from datetime import datetime, timezone
import logging

from db.models import (
    User, Group, Role, Permission, 
    user_group_association, group_role_association, group_permission_association
)
from models.schemas import PaginationParams, SortParams

logger = logging.getLogger(__name__)


class GroupService:
    """Service for managing user groups"""
    
    async def create_group(
        self,
        db: AsyncSession,
        name: str,
        display_name: str,
        description: Optional[str] = None,
        group_type: str = "custom",
        parent_group_id: Optional[UUID] = None,
        max_members: Optional[int] = None,
        creator_id: Optional[UUID] = None
    ) -> Group:
        """Create a new group"""
        try:
            # Check if group name already exists
            existing_group = await self.get_group_by_name(db, name)
            if existing_group:
                raise ValueError(f"Group with name '{name}' already exists")
            
            # Validate parent group if provided
            if parent_group_id:
                parent_group = await self.get_group_by_id(db, parent_group_id)
                if not parent_group:
                    raise ValueError("Parent group not found")
            
            # Create new group
            group = Group(
                name=name,
                display_name=display_name,
                description=description,
                group_type=group_type,
                parent_group_id=parent_group_id,
                max_members=max_members,
                created_by=creator_id,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            db.add(group)
            await db.commit()
            await db.refresh(group)
            
            logger.info(f"Group created: {name}")
            return group
            
        except Exception as e:
            logger.error(f"Error creating group: {e}")
            await db.rollback()
            raise
    
    async def get_group_by_id(self, db: AsyncSession, group_id: UUID) -> Optional[Group]:
        """Get group by ID"""
        try:
            result = await db.execute(
                select(Group)
                .options(
                    selectinload(Group.users),
                    selectinload(Group.roles),
                    selectinload(Group.permissions),
                    selectinload(Group.parent_group),
                    selectinload(Group.child_groups)
                )
                .where(Group.id == group_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting group by ID: {e}")
            return None
    
    async def get_group_by_name(self, db: AsyncSession, name: str) -> Optional[Group]:
        """Get group by name"""
        try:
            result = await db.execute(
                select(Group)
                .options(
                    selectinload(Group.users),
                    selectinload(Group.roles),
                    selectinload(Group.permissions)
                )
                .where(Group.name == name)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting group by name: {e}")
            return None
    
    async def get_groups(
        self,
        db: AsyncSession,
        pagination: PaginationParams,
        sort: SortParams,
        filters: Optional[Dict[str, Any]] = None
    ) -> tuple[List[Group], int]:
        """Get paginated list of groups"""
        try:
            # Build base query
            query = select(Group).options(
                selectinload(Group.users),
                selectinload(Group.roles),
                selectinload(Group.permissions),
                selectinload(Group.parent_group)
            )
            
            # Apply filters
            conditions = []
            if filters:
                if filters.get("is_active") is not None:
                    conditions.append(Group.is_active == filters["is_active"])
                if filters.get("group_type"):
                    conditions.append(Group.group_type == filters["group_type"])
                if filters.get("is_system") is not None:
                    conditions.append(Group.is_system == filters["is_system"])
                if filters.get("parent_group_id"):
                    conditions.append(Group.parent_group_id == filters["parent_group_id"])
            
            if conditions:
                query = query.where(and_(*conditions))
            
            # Apply sorting
            if sort.sort == "name":
                order_col = Group.name
            elif sort.sort == "display_name":
                order_col = Group.display_name
            elif sort.sort == "group_type":
                order_col = Group.group_type
            elif sort.sort == "created_at":
                order_col = Group.created_at
            else:
                order_col = Group.created_at
            
            if sort.order == "desc":
                query = query.order_by(desc(order_col))
            else:
                query = query.order_by(order_col)
            
            # Get total count
            count_query = select(func.count(Group.id))
            if conditions:
                count_query = count_query.where(and_(*conditions))
            
            total_result = await db.execute(count_query)
            total_count = total_result.scalar()
            
            # Apply pagination
            query = query.offset(pagination.offset).limit(pagination.limit)
            
            # Execute query
            result = await db.execute(query)
            groups = result.scalars().all()
            
            return list(groups), total_count
            
        except Exception as e:
            logger.error(f"Error getting groups: {e}")
            return [], 0
    
    async def update_group(
        self,
        db: AsyncSession,
        group_id: UUID,
        updates: Dict[str, Any],
        updater_id: Optional[UUID] = None
    ) -> Optional[Group]:
        """Update group information"""
        try:
            group = await self.get_group_by_id(db, group_id)
            if not group:
                return None
            
            # Check if group is system group
            if group.is_system and not updates.get("allow_system_update", False):
                raise ValueError("Cannot update system group")
            
            # Update fields
            for key, value in updates.items():
                if key == "allow_system_update":
                    continue
                if hasattr(group, key):
                    setattr(group, key, value)
            
            group.updated_at = datetime.now(timezone.utc)
            
            await db.commit()
            await db.refresh(group)
            
            logger.info(f"Group updated: {group.name}")
            return group
            
        except Exception as e:
            logger.error(f"Error updating group: {e}")
            await db.rollback()
            raise
    
    async def delete_group(self, db: AsyncSession, group_id: UUID) -> bool:
        """Delete a group"""
        try:
            group = await self.get_group_by_id(db, group_id)
            if not group:
                return False
            
            # Check if group is system group
            if group.is_system:
                raise ValueError("Cannot delete system group")
            
            # Check if group has users
            if group.users:
                raise ValueError("Cannot delete group with members")
            
            # Check if group has child groups
            if group.child_groups:
                raise ValueError("Cannot delete group with child groups")
            
            await db.delete(group)
            await db.commit()
            
            logger.info(f"Group deleted: {group.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting group: {e}")
            await db.rollback()
            raise
    
    async def add_user_to_group(
        self,
        db: AsyncSession,
        group_id: UUID,
        user_id: UUID,
        adder_id: Optional[UUID] = None
    ) -> bool:
        """Add a user to a group"""
        try:
            # Check if group exists
            group = await self.get_group_by_id(db, group_id)
            if not group:
                raise ValueError("Group not found")
            
            # Check if user exists
            user_result = await db.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            if not user:
                raise ValueError("User not found")
            
            # Check max members limit
            if group.max_members and len(group.users) >= group.max_members:
                raise ValueError("Group has reached maximum member limit")
            
            # Check if user is already in group
            existing_result = await db.execute(
                select(user_group_association)
                .where(
                    user_group_association.c.user_id == user_id,
                    user_group_association.c.group_id == group_id
                )
            )
            
            if existing_result.first():
                return True  # Already in group
            
            # Add user to group
            membership = user_group_association.insert().values(
                user_id=user_id,
                group_id=group_id,
                added_by=adder_id,
                joined_at=datetime.now(timezone.utc)
            )
            
            await db.execute(membership)
            await db.commit()
            
            logger.info(f"User {user.email} added to group {group.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding user to group: {e}")
            await db.rollback()
            raise
    
    async def remove_user_from_group(
        self,
        db: AsyncSession,
        group_id: UUID,
        user_id: UUID
    ) -> bool:
        """Remove a user from a group"""
        try:
            # Remove the membership
            delete_stmt = delete(user_group_association).where(
                user_group_association.c.user_id == user_id,
                user_group_association.c.group_id == group_id
            )
            
            result = await db.execute(delete_stmt)
            await db.commit()
            
            if result.rowcount > 0:
                logger.info(f"User removed from group")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error removing user from group: {e}")
            await db.rollback()
            raise
    
    async def assign_role_to_group(
        self,
        db: AsyncSession,
        group_id: UUID,
        role_id: UUID,
        assigner_id: Optional[UUID] = None
    ) -> bool:
        """Assign a role to a group"""
        try:
            # Check if group exists
            group = await self.get_group_by_id(db, group_id)
            if not group:
                raise ValueError("Group not found")
            
            # Check if role exists
            role_result = await db.execute(
                select(Role).where(Role.id == role_id)
            )
            role = role_result.scalar_one_or_none()
            if not role:
                raise ValueError("Role not found")
            
            # Check if role is already assigned
            existing_result = await db.execute(
                select(group_role_association)
                .where(
                    group_role_association.c.group_id == group_id,
                    group_role_association.c.role_id == role_id
                )
            )
            
            if existing_result.first():
                return True  # Already assigned
            
            # Assign role to group
            assignment = group_role_association.insert().values(
                group_id=group_id,
                role_id=role_id,
                assigned_by=assigner_id,
                assigned_at=datetime.now(timezone.utc)
            )
            
            await db.execute(assignment)
            await db.commit()
            
            logger.info(f"Role {role.name} assigned to group {group.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error assigning role to group: {e}")
            await db.rollback()
            raise
    
    async def revoke_role_from_group(
        self,
        db: AsyncSession,
        group_id: UUID,
        role_id: UUID
    ) -> bool:
        """Revoke a role from a group"""
        try:
            # Remove the assignment
            delete_stmt = delete(group_role_association).where(
                group_role_association.c.group_id == group_id,
                group_role_association.c.role_id == role_id
            )
            
            result = await db.execute(delete_stmt)
            await db.commit()
            
            if result.rowcount > 0:
                logger.info(f"Role revoked from group")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error revoking role from group: {e}")
            await db.rollback()
            raise
    
    async def assign_permission_to_group(
        self,
        db: AsyncSession,
        group_id: UUID,
        permission_id: UUID,
        granter_id: Optional[UUID] = None
    ) -> bool:
        """Assign a permission to a group"""
        try:
            # Check if group exists
            group = await self.get_group_by_id(db, group_id)
            if not group:
                raise ValueError("Group not found")
            
            # Check if permission exists
            permission_result = await db.execute(
                select(Permission).where(Permission.id == permission_id)
            )
            permission = permission_result.scalar_one_or_none()
            if not permission:
                raise ValueError("Permission not found")
            
            # Check if permission is already assigned
            existing_result = await db.execute(
                select(group_permission_association)
                .where(
                    group_permission_association.c.group_id == group_id,
                    group_permission_association.c.permission_id == permission_id
                )
            )
            
            if existing_result.first():
                return True  # Already assigned
            
            # Assign permission to group
            assignment = group_permission_association.insert().values(
                group_id=group_id,
                permission_id=permission_id,
                granted_by=granter_id,
                granted_at=datetime.now(timezone.utc)
            )
            
            await db.execute(assignment)
            await db.commit()
            
            logger.info(f"Permission {permission.name} assigned to group {group.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error assigning permission to group: {e}")
            await db.rollback()
            raise
    
    async def revoke_permission_from_group(
        self,
        db: AsyncSession,
        group_id: UUID,
        permission_id: UUID
    ) -> bool:
        """Revoke a permission from a group"""
        try:
            # Remove the assignment
            delete_stmt = delete(group_permission_association).where(
                group_permission_association.c.group_id == group_id,
                group_permission_association.c.permission_id == permission_id
            )
            
            result = await db.execute(delete_stmt)
            await db.commit()
            
            if result.rowcount > 0:
                logger.info(f"Permission revoked from group")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error revoking permission from group: {e}")
            await db.rollback()
            raise
    
    async def get_user_groups(self, db: AsyncSession, user_id: UUID) -> List[Group]:
        """Get all groups a user belongs to"""
        try:
            result = await db.execute(
                select(Group)
                .join(user_group_association)
                .where(
                    user_group_association.c.user_id == user_id,
                    Group.is_active == True
                )
                .options(
                    selectinload(Group.roles),
                    selectinload(Group.permissions)
                )
            )
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting user groups: {e}")
            return []
    
    async def get_group_permissions(
        self,
        db: AsyncSession,
        group_id: UUID,
        include_inherited: bool = True
    ) -> Set[str]:
        """Get all permissions for a group"""
        try:
            group = await self.get_group_by_id(db, group_id)
            if not group or not group.is_active:
                return set()
            
            permissions = set()
            
            # Add direct permissions
            for permission in group.permissions:
                if permission.is_active:
                    permissions.add(permission.name)
            
            # Add permissions from roles
            for role in group.roles:
                if role.is_active:
                    for permission in role.permissions:
                        if permission.is_active:
                            permissions.add(permission.name)
            
            # Add inherited permissions if requested
            if include_inherited and group.parent_group_id:
                inherited_perms = await self.get_group_permissions(
                    db, group.parent_group_id, include_inherited=True
                )
                permissions.update(inherited_perms)
            
            return permissions
            
        except Exception as e:
            logger.error(f"Error getting group permissions: {e}")
            return set()
    
    async def get_user_permissions_from_groups(
        self,
        db: AsyncSession,
        user_id: UUID,
        include_inherited: bool = True
    ) -> Set[str]:
        """Get all permissions a user has through group memberships"""
        try:
            user_groups = await self.get_user_groups(db, user_id)
            permissions = set()
            
            for group in user_groups:
                group_permissions = await self.get_group_permissions(
                    db, group.id, include_inherited
                )
                permissions.update(group_permissions)
            
            return permissions
            
        except Exception as e:
            logger.error(f"Error getting user permissions from groups: {e}")
            return set()
    
    async def get_group_stats(self, db: AsyncSession) -> Dict[str, Any]:
        """Get group system statistics"""
        try:
            # Count groups
            groups_result = await db.execute(select(func.count(Group.id)))
            groups_count = groups_result.scalar()
            
            # Count active groups
            active_groups_result = await db.execute(
                select(func.count(Group.id)).where(Group.is_active == True)
            )
            active_groups_count = active_groups_result.scalar()
            
            # Count group memberships
            memberships_result = await db.execute(
                select(func.count()).select_from(user_group_association)
            )
            memberships_count = memberships_result.scalar()
            
            # Count group role assignments
            role_assignments_result = await db.execute(
                select(func.count()).select_from(group_role_association)
            )
            role_assignments_count = role_assignments_result.scalar()
            
            # Count group permission grants
            permission_grants_result = await db.execute(
                select(func.count()).select_from(group_permission_association)
            )
            permission_grants_count = permission_grants_result.scalar()
            
            return {
                "total_groups": groups_count,
                "active_groups": active_groups_count,
                "total_memberships": memberships_count,
                "total_role_assignments": role_assignments_count,
                "total_permission_grants": permission_grants_count
            }
            
        except Exception as e:
            logger.error(f"Error getting group stats: {e}")
            return {
                "total_groups": 0,
                "active_groups": 0,
                "total_memberships": 0,
                "total_role_assignments": 0,
                "total_permission_grants": 0
            }