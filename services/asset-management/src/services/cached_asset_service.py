"""
Cached implementation of the Asset Management Service.

This module extends the base asset service with caching capabilities
to improve performance and reduce database load.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.schemas import (
    AssetCreate, AssetUpdate, AssetResponse,
    AssetSearchParams, PaginatedAssetResponse
)
from .asset_service import AssetService
from services.common.cache.query_cache import QueryCache, CacheKey, cached
from services.common.cache.cache_config import ServiceCacheConfig, CacheKeyBuilder

logger = logging.getLogger(__name__)


class CachedAssetService(AssetService):
    """Asset service with caching layer."""
    
    def __init__(self, db: AsyncSession, cache: QueryCache):
        """
        Initialize cached asset service.
        
        Args:
            db: Database session
            cache: Query cache instance
        """
        super().__init__(db)
        self.cache = cache
        self.key_builder = CacheKeyBuilder(cache.namespace)
        self.ttl_config = ServiceCacheConfig.ASSET_CACHE
        
    async def get_asset(
        self,
        asset_id: UUID,
        include_metadata: bool = True,
        include_versions: bool = False,
        user_id: Optional[UUID] = None
    ) -> Optional[AssetResponse]:
        """
        Get asset by ID with caching.
        
        Args:
            asset_id: Asset ID
            include_metadata: Include metadata in response
            include_versions: Include version history
            user_id: User ID for permission check
            
        Returns:
            Asset response or None
        """
        # Build cache key
        cache_key = self.key_builder.build(
            'asset', 'details',
            str(asset_id),
            metadata=include_metadata,
            versions=include_versions
        )
        
        # Try cache first
        cached_asset = await self.cache.get(cache_key)
        if cached_asset is not None:
            logger.debug(f"Cache hit for asset {asset_id}")
            # Still need to check permissions
            if user_id and not await self._check_asset_permission(
                UUID(cached_asset['id']), user_id, 'read'
            ):
                return None
            return AssetResponse(**cached_asset)
            
        logger.debug(f"Cache miss for asset {asset_id}")
        
        # Fetch from database
        asset = await super().get_asset(
            asset_id, include_metadata, include_versions, user_id
        )
        
        if asset:
            # Cache the result
            await self.cache.set(
                cache_key,
                asset.dict(),
                ttl=self.ttl_config['asset_details']
            )
            
        return asset
        
    async def list_assets(
        self,
        search_params: AssetSearchParams,
        user_id: UUID
    ) -> PaginatedAssetResponse:
        """
        List assets with caching.
        
        Args:
            search_params: Search parameters
            user_id: User ID for filtering
            
        Returns:
            Paginated asset response
        """
        # Build cache key from search parameters
        cache_key = CacheKey.generate(
            'asset_list',
            str(user_id),
            page=search_params.page,
            limit=search_params.limit,
            sort=search_params.sort,
            order=search_params.order,
            filters=search_params.dict(exclude_none=True)
        )
        
        # Try cache for list results
        cached_result = await self.cache.get(cache_key)
        if cached_result is not None:
            logger.debug("Cache hit for asset list")
            return PaginatedAssetResponse(**cached_result)
            
        logger.debug("Cache miss for asset list")
        
        # Fetch from database
        result = await super().list_assets(search_params, user_id)
        
        # Cache the result
        await self.cache.set(
            cache_key,
            result.dict(),
            ttl=self.ttl_config['asset_list']
        )
        
        return result
        
    async def create_asset(
        self,
        asset_data: AssetCreate,
        user_id: UUID
    ) -> AssetResponse:
        """
        Create asset and invalidate relevant caches.
        
        Args:
            asset_data: Asset creation data
            user_id: User ID of creator
            
        Returns:
            Created asset
        """
        # Create asset
        asset = await super().create_asset(asset_data, user_id)
        
        # Invalidate list caches
        await self._invalidate_list_caches(user_id)
        
        # Also invalidate user's asset count cache
        await self.cache.delete_pattern(f'stats:user:{user_id}:*')
        
        return asset
        
    async def update_asset(
        self,
        asset_id: UUID,
        asset_update: AssetUpdate,
        user_id: UUID
    ) -> Optional[AssetResponse]:
        """
        Update asset and invalidate caches.
        
        Args:
            asset_id: Asset ID
            asset_update: Update data
            user_id: User ID for permission check
            
        Returns:
            Updated asset or None
        """
        # Update asset
        asset = await super().update_asset(asset_id, asset_update, user_id)
        
        if asset:
            # Invalidate asset caches
            await self._invalidate_asset_caches(asset_id)
            
            # Invalidate list caches
            await self._invalidate_list_caches(user_id)
            
        return asset
        
    async def delete_asset(
        self,
        asset_id: UUID,
        user_id: UUID,
        soft_delete: bool = True
    ) -> bool:
        """
        Delete asset and invalidate caches.
        
        Args:
            asset_id: Asset ID
            user_id: User ID for permission check
            soft_delete: Whether to soft delete
            
        Returns:
            Success boolean
        """
        # Delete asset
        success = await super().delete_asset(asset_id, user_id, soft_delete)
        
        if success:
            # Invalidate asset caches
            await self._invalidate_asset_caches(asset_id)
            
            # Invalidate list caches
            await self._invalidate_list_caches(user_id)
            
        return success
        
    @cached('asset_search', ttl=60)
    async def search_assets(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        user_id: Optional[UUID] = None,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Search assets with caching.
        
        Args:
            query: Search query
            filters: Additional filters
            user_id: User ID for filtering
            page: Page number
            limit: Items per page
            
        Returns:
            Search results
        """
        # Note: The @cached decorator handles caching automatically
        return await super().search_assets(query, filters, user_id, page, limit)
        
    async def get_asset_by_hash(
        self,
        file_hash: str,
        user_id: Optional[UUID] = None
    ) -> Optional[AssetResponse]:
        """
        Get asset by file hash with caching.
        
        Args:
            file_hash: File hash
            user_id: User ID for permission check
            
        Returns:
            Asset or None
        """
        # Build cache key
        cache_key = f'asset_hash:{file_hash}'
        
        # Try cache
        cached_id = await self.cache.get(cache_key)
        if cached_id:
            return await self.get_asset(UUID(cached_id), user_id=user_id)
            
        # Search by hash
        asset = await super().get_asset_by_hash(file_hash, user_id)
        
        if asset:
            # Cache the mapping
            await self.cache.set(
                cache_key,
                str(asset.id),
                ttl=self.ttl_config['duplicate_check']
            )
            
        return asset
        
    async def get_asset_statistics(
        self,
        user_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Get asset statistics with caching.
        
        Args:
            user_id: Filter by user
            project_id: Filter by project
            
        Returns:
            Statistics dictionary
        """
        # Build cache key
        cache_key = CacheKey.generate(
            'stats',
            user=str(user_id) if user_id else 'all',
            project=str(project_id) if project_id else 'all'
        )
        
        # Try cache
        cached_stats = await self.cache.get(cache_key)
        if cached_stats:
            return cached_stats
            
        # Calculate statistics
        stats = await super().get_asset_statistics(user_id, project_id)
        
        # Cache results
        await self.cache.set(
            cache_key,
            stats,
            ttl=ServiceCacheConfig.SYSTEM_CACHE['statistics']
        )
        
        return stats
        
    # Cache invalidation helpers
    
    async def _invalidate_asset_caches(self, asset_id: UUID):
        """Invalidate all caches for a specific asset."""
        patterns = [
            f'asset:details:{asset_id}:*',
            f'asset_hash:*',  # Hash lookups might be affected
            f'asset_versions:{asset_id}:*',
            f'asset_metadata:{asset_id}:*',
        ]
        
        for pattern in patterns:
            await self.cache.delete_pattern(pattern)
            
    async def _invalidate_list_caches(self, user_id: Optional[UUID] = None):
        """Invalidate list caches."""
        if user_id:
            # Invalidate specific user's lists
            await self.cache.delete_pattern(f'asset_list:{user_id}:*')
        else:
            # Invalidate all lists
            await self.cache.delete_pattern('asset_list:*')
            
        # Also invalidate search results
        await self.cache.delete_pattern('asset_search:*')
        
    async def warm_cache(self, asset_ids: List[UUID]):
        """
        Pre-warm cache with specific assets.
        
        Args:
            asset_ids: List of asset IDs to cache
        """
        for asset_id in asset_ids:
            try:
                await self.get_asset(asset_id, include_metadata=True)
                logger.info(f"Warmed cache for asset {asset_id}")
            except Exception as e:
                logger.error(f"Failed to warm cache for asset {asset_id}: {e}")


# Factory function
def create_cached_asset_service(
    db: AsyncSession,
    cache: QueryCache
) -> CachedAssetService:
    """
    Create a cached asset service instance.
    
    Args:
        db: Database session
        cache: Query cache instance
        
    Returns:
        Cached asset service
    """
    # Set cache instance for decorators
    CachedAssetService.search_assets._cache = cache
    
    return CachedAssetService(db, cache)


# Example usage
"""
# In your FastAPI app
from services.common.cache.cache_config import init_service_cache

# Initialize cache
cache = await init_service_cache('asset-management')

# Create service
@app.on_event("startup")
async def startup():
    app.state.cache = await init_service_cache('asset-management')

# Dependency
async def get_asset_service(
    db: AsyncSession = Depends(get_db),
    cache: QueryCache = Depends(lambda: request.app.state.cache)
) -> CachedAssetService:
    return create_cached_asset_service(db, cache)

# Use in endpoints
@router.get("/assets/{asset_id}")
async def get_asset(
    asset_id: UUID,
    service: CachedAssetService = Depends(get_asset_service),
    current_user: User = Depends(get_current_user)
):
    asset = await service.get_asset(
        asset_id,
        include_metadata=True,
        user_id=current_user.id
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset

# Warm cache on startup
@app.on_event("startup")
async def warm_popular_assets():
    # Get most accessed assets from analytics
    popular_ids = await get_popular_asset_ids(limit=100)
    
    async with get_db() as db:
        service = create_cached_asset_service(db, app.state.cache)
        await service.warm_cache(popular_ids)
"""