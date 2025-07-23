"""
Database query optimization utilities for the User Management Service.

This module provides optimized query patterns to improve database performance
for user-related operations.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy import select, func, and_, or_, exists, Index, update
from sqlalchemy.orm import selectinload, joinedload, contains_eager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from .models import User, Role, Permission, UserRole, Profile


class UserQueryOptimizer:
    """Provides optimized query building methods for user operations."""
    
    @staticmethod
    def build_user_query_with_relations(
        base_query: Optional[Select] = None,
        include_profile: bool = True,
        include_roles: bool = True,
        include_permissions: bool = False
    ) -> Select:
        """
        Build an optimized query that eager loads related entities.
        
        Args:
            base_query: Base query to optimize
            include_profile: Whether to eager load profile
            include_roles: Whether to eager load roles
            include_permissions: Whether to eager load permissions through roles
            
        Returns:
            Optimized query
        """
        if base_query is None:
            base_query = select(User)
            
        options = []
        
        if include_profile:
            # One-to-one relationship
            options.append(joinedload(User.profile))
            
        if include_roles:
            # Many-to-many relationship
            if include_permissions:
                # Load roles and their permissions
                options.append(
                    selectinload(User.roles).selectinload(Role.permissions)
                )
            else:
                options.append(selectinload(User.roles))
                
        if options:
            base_query = base_query.options(*options)
            
        return base_query
    
    @staticmethod
    def build_permission_check_query(
        user_id: UUID,
        permission_name: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[UUID] = None
    ) -> Select:
        """
        Build an optimized query to check if user has specific permission.
        
        Args:
            user_id: User ID to check
            permission_name: Name of the permission
            resource_type: Optional resource type
            resource_id: Optional specific resource ID
            
        Returns:
            Query that returns boolean result
        """
        # Build subquery for permission check
        permission_subquery = (
            select(1)
            .select_from(UserRole)
            .join(Role)
            .join(Role.permissions)
            .where(
                and_(
                    UserRole.user_id == user_id,
                    Permission.name == permission_name,
                    Role.is_active == True
                )
            )
        )
        
        if resource_type:
            permission_subquery = permission_subquery.where(
                or_(
                    Permission.resource_type == resource_type,
                    Permission.resource_type == '*'
                )
            )
            
        return select(exists(permission_subquery))
    
    @staticmethod
    def build_user_search_query(
        search_term: str,
        include_inactive: bool = False
    ) -> Select:
        """
        Build optimized user search query across multiple fields.
        
        Args:
            search_term: Search term
            include_inactive: Whether to include inactive users
            
        Returns:
            Search query
        """
        search_pattern = f'%{search_term}%'
        
        query = select(User).where(
            or_(
                User.email.ilike(search_pattern),
                User.username.ilike(search_pattern),
                User.first_name.ilike(search_pattern),
                User.last_name.ilike(search_pattern),
                # Search in concatenated full name
                func.concat(User.first_name, ' ', User.last_name).ilike(search_pattern)
            )
        )
        
        if not include_inactive:
            query = query.where(User.is_active == True)
            
        return query


class UserIndexDefinitions:
    """Optimal indexes for the User Management database."""
    
    INDEXES = [
        # For user search queries
        Index(
            'idx_user_search',
            'email', 'username', 'first_name', 'last_name'
        ),
        
        # For common filter combinations
        Index(
            'idx_user_active_verified',
            'is_active', 'is_verified'
        ),
        
        # For login queries
        Index(
            'idx_user_email_active',
            'email', 'is_active',
            postgresql_where='is_active = true'
        ),
        
        # For role assignments
        Index(
            'idx_user_role_active',
            'user_id', 'role_id',
            postgresql_where='deleted_at IS NULL'
        ),
        
        # For permission lookups
        Index(
            'idx_permission_name_resource',
            'name', 'resource_type'
        ),
    ]


class UserBulkOperations:
    """Optimized bulk operations for user management."""
    
    @staticmethod
    async def bulk_assign_role(
        db: AsyncSession,
        user_ids: List[UUID],
        role_id: UUID
    ) -> int:
        """
        Bulk assign a role to multiple users.
        
        Args:
            db: Database session
            user_ids: List of user IDs
            role_id: Role ID to assign
            
        Returns:
            Number of assignments created
        """
        from sqlalchemy.dialects.postgresql import insert
        
        if not user_ids:
            return 0
            
        # Build values for bulk insert
        values = [
            {'user_id': user_id, 'role_id': role_id}
            for user_id in user_ids
        ]
        
        # Insert with ON CONFLICT DO NOTHING
        stmt = insert(UserRole).values(values)
        stmt = stmt.on_conflict_do_nothing()
        
        result = await db.execute(stmt)
        await db.commit()
        
        return result.rowcount
    
    @staticmethod
    async def bulk_update_users(
        db: AsyncSession,
        user_ids: List[UUID],
        update_data: Dict[str, Any]
    ) -> int:
        """
        Bulk update multiple users.
        
        Args:
            db: Database session
            user_ids: List of user IDs
            update_data: Fields to update
            
        Returns:
            Number of updated users
        """
        if not user_ids or not update_data:
            return 0
            
        # Filter out None values
        update_data = {k: v for k, v in update_data.items() if v is not None}
        
        stmt = (
            update(User)
            .where(User.id.in_(user_ids))
            .values(**update_data)
        )
        
        result = await db.execute(stmt)
        await db.commit()
        
        return result.rowcount
    
    @staticmethod
    async def bulk_deactivate_users(
        db: AsyncSession,
        user_ids: List[UUID],
        reason: Optional[str] = None
    ) -> int:
        """
        Bulk deactivate users with optional reason.
        
        Args:
            db: Database session
            user_ids: List of user IDs
            reason: Optional deactivation reason
            
        Returns:
            Number of deactivated users
        """
        from datetime import datetime
        
        update_data = {
            'is_active': False,
            'updated_at': datetime.utcnow()
        }
        
        if reason:
            # Store reason in user profile or audit log
            pass
            
        return await UserBulkOperations.bulk_update_users(
            db, user_ids, update_data
        )


class UserQueryCache:
    """User-specific query caching patterns."""
    
    @staticmethod
    def get_user_cache_key(user_id: UUID, suffix: str = '') -> str:
        """Generate cache key for user data."""
        base_key = f'user:{user_id}'
        return f'{base_key}:{suffix}' if suffix else base_key
    
    @staticmethod
    def get_permission_cache_key(
        user_id: UUID,
        permission: str,
        resource: Optional[str] = None
    ) -> str:
        """Generate cache key for permission checks."""
        key = f'perm:{user_id}:{permission}'
        if resource:
            key += f':{resource}'
        return key
    
    @staticmethod
    async def cache_user_permissions(
        redis_client,
        user_id: UUID,
        permissions: List[Dict[str, Any]],
        ttl: int = 3600
    ):
        """
        Cache user permissions for fast lookup.
        
        Args:
            redis_client: Redis client
            user_id: User ID
            permissions: List of permission dictionaries
            ttl: Cache TTL in seconds
        """
        import json
        
        # Create a permissions map
        perm_map = {}
        for perm in permissions:
            key = f"{perm['name']}:{perm.get('resource_type', '*')}"
            perm_map[key] = True
            
        cache_key = f'user:{user_id}:permissions'
        await redis_client.setex(
            cache_key,
            ttl,
            json.dumps(perm_map)
        )


# Example usage patterns
"""
# 1. Fetch user with all relations efficiently
optimizer = UserQueryOptimizer()
query = optimizer.build_user_query_with_relations(
    include_profile=True,
    include_roles=True,
    include_permissions=True
)
query = query.where(User.id == user_id)
result = await db.execute(query)
user = result.scalar_one()

# 2. Check user permission efficiently
has_permission = await db.scalar(
    optimizer.build_permission_check_query(
        user_id=user.id,
        permission_name='asset.create',
        resource_type='asset'
    )
)

# 3. Search users efficiently
search_query = optimizer.build_user_search_query(
    search_term='john',
    include_inactive=False
)
results = await db.execute(search_query.limit(20))

# 4. Bulk operations
bulk_ops = UserBulkOperations()
assigned = await bulk_ops.bulk_assign_role(
    db,
    user_ids=[user1_id, user2_id, user3_id],
    role_id=editor_role_id
)

# 5. Cache user permissions
cache = UserQueryCache()
await cache.cache_user_permissions(
    redis_client,
    user_id=user.id,
    permissions=user_permissions,
    ttl=3600
)
"""