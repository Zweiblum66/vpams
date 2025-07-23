"""
Database query optimization utilities for the Asset Management Service.

This module provides optimized query patterns and utilities to improve
database performance by addressing common issues like N+1 queries,
missing indexes, and inefficient joins.
"""

from typing import List, Optional, Dict, Any, Type
from uuid import UUID
from sqlalchemy import select, func, and_, or_, exists, Index
from sqlalchemy.orm import selectinload, joinedload, contains_eager, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from .models import Asset, Tag, AssetVersion, asset_tags


class QueryOptimizer:
    """Provides optimized query building methods for asset operations."""
    
    @staticmethod
    def build_asset_query_with_relations(
        base_query: Optional[Select] = None,
        include_tags: bool = True,
        include_versions: bool = True,
        include_metadata: bool = True
    ) -> Select:
        """
        Build an optimized query that eager loads related entities to avoid N+1 problems.
        
        Args:
            base_query: Base query to optimize (defaults to select(Asset))
            include_tags: Whether to eager load tags
            include_versions: Whether to eager load versions
            include_metadata: Whether to eager load metadata
            
        Returns:
            Optimized SQLAlchemy query
        """
        if base_query is None:
            base_query = select(Asset)
            
        # Add eager loading options
        options = []
        
        if include_tags:
            # Use selectinload for many-to-many relationships
            options.append(selectinload(Asset.tags))
            
        if include_versions:
            # Use selectinload for one-to-many relationships
            options.append(selectinload(Asset.versions))
            
        if include_metadata:
            # Use joinedload for one-to-one relationships
            options.append(joinedload(Asset.metadata))
            
        if options:
            base_query = base_query.options(*options)
            
        return base_query
    
    @staticmethod
    def build_tag_filter_query(
        base_query: Select,
        tag_names: List[str],
        match_all: bool = True
    ) -> Select:
        """
        Build an optimized query for filtering assets by tags using EXISTS subquery.
        
        Args:
            base_query: Base query to filter
            tag_names: List of tag names to filter by
            match_all: If True, asset must have ALL tags. If False, ANY tag.
            
        Returns:
            Filtered query
        """
        if not tag_names:
            return base_query
            
        if match_all:
            # Asset must have ALL specified tags
            tag_subquery = (
                select(1)
                .select_from(asset_tags)
                .join(Tag)
                .where(
                    and_(
                        asset_tags.c.asset_id == Asset.id,
                        Tag.name.in_(tag_names)
                    )
                )
                .group_by(asset_tags.c.asset_id)
                .having(func.count(Tag.id) == len(tag_names))
                .exists()
            )
        else:
            # Asset must have ANY of the specified tags
            tag_subquery = (
                select(1)
                .select_from(asset_tags)
                .join(Tag)
                .where(
                    and_(
                        asset_tags.c.asset_id == Asset.id,
                        Tag.name.in_(tag_names)
                    )
                )
                .exists()
            )
            
        return base_query.where(tag_subquery)
    
    @staticmethod
    def build_paginated_query(
        base_query: Select,
        page: int,
        page_size: int,
        include_total: bool = True
    ) -> Select:
        """
        Build a paginated query with optional total count using window functions.
        
        Args:
            base_query: Base query to paginate
            page: Page number (1-indexed)
            page_size: Number of items per page
            include_total: Whether to include total count in results
            
        Returns:
            Paginated query
        """
        offset = (page - 1) * page_size
        
        # Add pagination
        query = base_query.offset(offset).limit(page_size)
        
        if include_total:
            # Use window function to get total count without separate query
            query = query.add_columns(
                func.count().over().label('_total_count')
            )
            
        return query
    
    @staticmethod
    def build_search_query(
        search_term: str,
        search_fields: List[str] = None
    ) -> Select:
        """
        Build an optimized full-text search query.
        
        Args:
            search_term: Term to search for
            search_fields: List of field names to search in
            
        Returns:
            Search query
        """
        if search_fields is None:
            search_fields = ['name', 'description']
            
        # Build OR conditions for each field
        conditions = []
        for field in search_fields:
            conditions.append(
                getattr(Asset, field).ilike(f'%{search_term}%')
            )
            
        return select(Asset).where(or_(*conditions))


class IndexDefinitions:
    """Defines optimal indexes for the Asset Management database."""
    
    # Composite indexes for common query patterns
    INDEXES = [
        # For status + owner + date queries (common in dashboards)
        Index(
            'idx_asset_status_owner_created',
            'status', 'owner_id', 'created_at'
        ),
        
        # For duplicate detection queries
        Index(
            'idx_asset_file_hash_deleted',
            'file_hash', 'deleted_at'
        ),
        
        # For project/type filtering with dates
        Index(
            'idx_asset_project_type_created',
            'project_id', 'asset_type', 'created_at'
        ),
        
        # For efficient sorting of shots in containers
        Index(
            'idx_shot_container_sort',
            'container_id', 'sort_order'
        ),
        
        # For metadata queries
        Index(
            'idx_asset_metadata_status',
            'id', 'status',
            postgresql_where='deleted_at IS NULL'
        ),
    ]


class BulkOperations:
    """Provides optimized bulk operation methods."""
    
    @staticmethod
    async def bulk_update_assets(
        db: AsyncSession,
        asset_ids: List[UUID],
        update_data: Dict[str, Any]
    ) -> int:
        """
        Perform bulk update on multiple assets in a single query.
        
        Args:
            db: Database session
            asset_ids: List of asset IDs to update
            update_data: Dictionary of fields to update
            
        Returns:
            Number of updated assets
        """
        from sqlalchemy import update
        
        # Remove None values
        update_data = {k: v for k, v in update_data.items() if v is not None}
        
        if not update_data or not asset_ids:
            return 0
            
        stmt = (
            update(Asset)
            .where(Asset.id.in_(asset_ids))
            .values(**update_data)
        )
        
        result = await db.execute(stmt)
        await db.commit()
        
        return result.rowcount
    
    @staticmethod
    async def bulk_tag_assets(
        db: AsyncSession,
        asset_ids: List[UUID],
        tag_names: List[str],
        replace: bool = False
    ) -> None:
        """
        Bulk add tags to multiple assets efficiently.
        
        Args:
            db: Database session
            asset_ids: List of asset IDs to tag
            tag_names: List of tag names to add
            replace: If True, replace existing tags. If False, append.
        """
        if not asset_ids or not tag_names:
            return
            
        # Get or create tags
        tag_query = select(Tag).where(Tag.name.in_(tag_names))
        result = await db.execute(tag_query)
        existing_tags = {tag.name: tag for tag in result.scalars()}
        
        # Create missing tags
        new_tags = []
        for tag_name in tag_names:
            if tag_name not in existing_tags:
                new_tag = Tag(name=tag_name)
                new_tags.append(new_tag)
                db.add(new_tag)
                
        if new_tags:
            await db.flush()
            
        # Build tag IDs list
        all_tags = list(existing_tags.values()) + new_tags
        tag_ids = [tag.id for tag in all_tags]
        
        if replace:
            # Delete existing tags
            from sqlalchemy import delete
            stmt = delete(asset_tags).where(
                asset_tags.c.asset_id.in_(asset_ids)
            )
            await db.execute(stmt)
            
        # Insert new tags (using INSERT ... ON CONFLICT DO NOTHING)
        from sqlalchemy.dialects.postgresql import insert
        
        values = []
        for asset_id in asset_ids:
            for tag_id in tag_ids:
                values.append({
                    'asset_id': asset_id,
                    'tag_id': tag_id
                })
                
        if values:
            stmt = insert(asset_tags).values(values)
            stmt = stmt.on_conflict_do_nothing()
            await db.execute(stmt)
            
        await db.commit()


class QueryCache:
    """Provides query result caching utilities."""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.default_ttl = 300  # 5 minutes
        
    async def get_or_fetch(
        self,
        key: str,
        fetch_func,
        ttl: Optional[int] = None
    ):
        """
        Get cached result or fetch and cache if not found.
        
        Args:
            key: Cache key
            fetch_func: Async function to fetch data if not cached
            ttl: Time to live in seconds (defaults to 5 minutes)
            
        Returns:
            Cached or fetched data
        """
        import json
        
        # Try to get from cache
        cached = await self.redis.get(key)
        if cached:
            return json.loads(cached)
            
        # Fetch fresh data
        data = await fetch_func()
        
        # Cache the result
        ttl = ttl or self.default_ttl
        await self.redis.setex(
            key,
            ttl,
            json.dumps(data, default=str)
        )
        
        return data
    
    async def invalidate(self, pattern: str):
        """Invalidate cache entries matching pattern."""
        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(
                cursor,
                match=pattern,
                count=100
            )
            
            if keys:
                await self.redis.delete(*keys)
                
            if cursor == 0:
                break


# Example usage patterns
"""
# 1. Optimized asset fetching with relations
optimizer = QueryOptimizer()
query = optimizer.build_asset_query_with_relations(
    include_tags=True,
    include_versions=True
)
query = query.where(Asset.id == asset_id)
result = await db.execute(query)
asset = result.scalar_one()

# 2. Efficient tag filtering
query = select(Asset)
query = optimizer.build_tag_filter_query(
    query,
    tag_names=['video', 'approved'],
    match_all=True
)
results = await db.execute(query)

# 3. Paginated queries with total count
query = optimizer.build_paginated_query(
    select(Asset).where(Asset.status == 'active'),
    page=1,
    page_size=20,
    include_total=True
)
results = await db.execute(query)

# 4. Bulk operations
bulk_ops = BulkOperations()
updated_count = await bulk_ops.bulk_update_assets(
    db,
    asset_ids=[uuid1, uuid2, uuid3],
    update_data={'status': 'archived'}
)

# 5. Cached queries
cache = QueryCache(redis_client)
assets = await cache.get_or_fetch(
    f'assets:user:{user_id}:page:1',
    lambda: fetch_user_assets(user_id, page=1),
    ttl=600  # 10 minutes
)
"""