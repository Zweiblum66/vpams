"""
Sharded Asset Service for handling asset operations across database shards

This module extends the asset service with sharding capabilities for
improved performance and scalability.
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from uuid import UUID
import structlog

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from .asset_service import AssetService
from ..db.sharding import (
    ShardedSession, AssetShardedRepository, get_sharded_session,
    ShardRouter, ShardKey
)
from ..db.models import Asset, AssetStatus, AssetType
from ..models.schemas import (
    AssetCreate, AssetUpdate, AssetResponse, AssetListResponse,
    PaginationParams, PaginatedResponse, AssetSearchParams
)
from ..core.exceptions import AssetNotFoundError, StorageError

logger = structlog.get_logger()


class ShardedAssetService(AssetService):
    """Asset service with sharding support"""
    
    def __init__(self, sharded_session: ShardedSession, user_id: UUID):
        self.sharded_session = sharded_session
        self.repository = AssetShardedRepository(sharded_session)
        self.user_id = user_id
        self.settings = self._get_settings()
        self._storage_client = None
    
    def _get_settings(self):
        """Get application settings"""
        from ..core.config import get_settings
        return get_settings()
    
    async def create_asset_from_upload(
        self,
        asset_data: AssetCreate,
        file_info: Dict[str, Any]
    ) -> AssetResponse:
        """Create asset with sharding support"""
        try:
            # Prepare asset data
            asset_dict = {
                "id": UUID() if not hasattr(asset_data, 'id') else asset_data.id,
                "name": asset_data.name,
                "display_name": asset_data.display_name or asset_data.name,
                "description": asset_data.description,
                "file_path": file_info["path"],
                "file_size": file_info["size"],
                "file_hash": file_info.get("hash"),
                "mime_type": file_info.get("mime_type"),
                "file_extension": self._extract_extension(asset_data.name),
                "asset_type": self._determine_asset_type(
                    file_info.get("mime_type"), 
                    asset_data.name
                ),
                "status": AssetStatus.ACTIVE,
                "storage_driver": file_info.get("driver", self.settings.default_storage_driver),
                "storage_path": file_info["path"],
                "storage_tier": file_info.get("tier", "hot"),
                "owner_id": self.user_id,
                "project_id": asset_data.project_id,
                "is_public": asset_data.is_public or False,
                "technical_metadata": asset_data.metadata or {}
            }
            
            # Create asset on appropriate shard
            asset = await self.repository.create_asset(asset_dict)
            
            logger.info(
                "sharded_asset_created",
                asset_id=str(asset.id),
                project_id=str(asset.project_id) if asset.project_id else None,
                shard_key=self.sharded_session.router.shard_key.value,
                user_id=str(self.user_id)
            )
            
            return await self._asset_to_response(asset)
            
        except Exception as e:
            logger.error("sharded_asset_creation_failed", error=str(e))
            raise
    
    async def get_asset(self, asset_id: UUID, project_id: Optional[UUID] = None) -> AssetResponse:
        """Get asset from sharded database"""
        asset = await self.repository.get_asset(asset_id, project_id)
        
        if not asset:
            raise AssetNotFoundError(f"Asset {asset_id} not found")
        
        # Check permissions
        if not asset.is_public and asset.owner_id != self.user_id:
            # TODO: Check sharing permissions
            from ..core.exceptions import PermissionError
            raise PermissionError("You don't have permission to access this asset")
        
        return await self._asset_to_response(asset)
    
    async def list_assets(
        self,
        pagination: PaginationParams,
        search_params: Optional[AssetSearchParams] = None
    ) -> PaginatedResponse:
        """List assets across shards with filtering"""
        
        # If we have a project_id filter and shard by project, query only that shard
        if (search_params and search_params.project_id and 
            self.sharded_session.router.shard_key == ShardKey.PROJECT_ID):
            
            assets = await self.repository.get_assets_by_project(
                search_params.project_id,
                limit=pagination.page_size,
                offset=pagination.offset
            )
            
            # Get total count from the same shard
            async def count_query(session):
                stmt = select(func.count(Asset.id)).where(
                    and_(
                        Asset.project_id == search_params.project_id,
                        Asset.deleted_at.is_(None)
                    )
                )
                result = await session.execute(stmt)
                return result.scalar_one()
            
            total = await self.repository.query_shard(
                count_query, 
                search_params.project_id,
                read_only=True
            )
            
        else:
            # Cross-shard search
            search_dict = {}
            if search_params:
                if search_params.query:
                    search_dict['name'] = search_params.query
                if search_params.asset_type:
                    search_dict['asset_type'] = search_params.asset_type
                if search_params.status:
                    search_dict['status'] = search_params.status
                if search_params.owner_id:
                    search_dict['owner_id'] = search_params.owner_id
            
            # Get assets from all shards
            all_assets = await self.repository.search_assets(search_dict)
            
            # Apply client-side pagination
            # In production, this would be optimized with shard-aware pagination
            total = len(all_assets)
            start = pagination.offset
            end = start + pagination.page_size
            assets = all_assets[start:end]
        
        # Convert to response models
        items = [self._asset_to_list_response(asset) for asset in assets]
        
        return PaginatedResponse(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            pages=(total + pagination.page_size - 1) // pagination.page_size
        )
    
    async def update_asset(
        self,
        asset_id: UUID,
        update_data: AssetUpdate,
        project_id: Optional[UUID] = None
    ) -> AssetResponse:
        """Update asset on its shard"""
        # Get the asset first to find its shard
        asset = await self.repository.get_asset(asset_id, project_id)
        
        if not asset:
            raise AssetNotFoundError(f"Asset {asset_id} not found")
        
        # Check permissions
        if asset.owner_id != self.user_id:
            from ..core.exceptions import PermissionError
            raise PermissionError("You don't have permission to modify this asset")
        
        # Determine shard key for update
        shard_key_value = project_id or asset.project_id or asset.owner_id or asset_id
        
        # Update the asset
        async def update_query(session):
            # Re-fetch in the session
            result = await session.get(Asset, asset_id)
            if result:
                if update_data.display_name is not None:
                    result.display_name = update_data.display_name
                if update_data.description is not None:
                    result.description = update_data.description
                if update_data.is_public is not None:
                    result.is_public = update_data.is_public
                if update_data.metadata is not None:
                    result.technical_metadata = {
                        **result.technical_metadata, 
                        **update_data.metadata
                    }
                
                result.updated_at = datetime.utcnow()
                await session.commit()
                await session.refresh(result)
                return result
            return None
        
        updated_asset = await self.repository.query_shard(
            update_query,
            shard_key_value,
            read_only=False
        )
        
        if not updated_asset:
            raise AssetNotFoundError(f"Failed to update asset {asset_id}")
        
        logger.info(
            "sharded_asset_updated",
            asset_id=str(asset_id),
            user_id=str(self.user_id)
        )
        
        return await self._asset_to_response(updated_asset[0] if isinstance(updated_asset, list) else updated_asset)
    
    async def delete_asset(
        self, 
        asset_id: UUID, 
        permanent: bool = False,
        project_id: Optional[UUID] = None
    ) -> bool:
        """Delete asset from its shard"""
        # Get the asset first to find its shard
        asset = await self.repository.get_asset(asset_id, project_id)
        
        if not asset:
            raise AssetNotFoundError(f"Asset {asset_id} not found")
        
        # Check permissions
        if asset.owner_id != self.user_id:
            from ..core.exceptions import PermissionError
            raise PermissionError("You don't have permission to delete this asset")
        
        # Determine shard key
        shard_key_value = project_id or asset.project_id or asset.owner_id or asset_id
        
        # Delete the asset
        async def delete_query(session):
            result = await session.get(Asset, asset_id)
            if result:
                if permanent:
                    await session.delete(result)
                else:
                    result.deleted_at = datetime.utcnow()
                    result.status = AssetStatus.DELETED
                
                await session.commit()
                return True
            return False
        
        success = await self.repository.query_shard(
            delete_query,
            shard_key_value,
            read_only=False
        )
        
        if success:
            logger.info(
                "sharded_asset_deleted",
                asset_id=str(asset_id),
                permanent=permanent,
                user_id=str(self.user_id)
            )
        
        return bool(success)
    
    async def get_shard_statistics(self) -> Dict[str, Any]:
        """Get statistics about shard distribution"""
        async def stats_query(session):
            # Count assets per shard
            stmt = select(
                func.count(Asset.id).label('asset_count'),
                func.sum(Asset.file_size).label('total_size')
            ).where(Asset.deleted_at.is_(None))
            
            result = await session.execute(stmt)
            row = result.one()
            
            return {
                'asset_count': row.asset_count,
                'total_size': row.total_size or 0
            }
        
        # Get stats from all shards
        all_stats = await self.repository.query_all_shards(stats_query)
        
        # Aggregate results
        total_assets = 0
        total_size = 0
        shard_details = []
        
        for i, stats in enumerate(all_stats):
            if isinstance(stats, dict):
                total_assets += stats['asset_count']
                total_size += stats['total_size']
                shard_details.append({
                    'shard_index': i,
                    'asset_count': stats['asset_count'],
                    'total_size': stats['total_size']
                })
        
        return {
            'total_assets': total_assets,
            'total_size': total_size,
            'shard_count': len(all_stats),
            'shards': shard_details,
            'sharding_strategy': self.sharded_session.router.strategy.value,
            'shard_key': self.sharded_session.router.shard_key.value
        }
    
    def _extract_extension(self, filename: str) -> str:
        """Extract file extension from filename"""
        from pathlib import Path
        return Path(filename).suffix.lower()
    
    async def _asset_to_response(self, asset: Asset) -> AssetResponse:
        """Convert asset model to response schema"""
        return AssetResponse(
            id=asset.id,
            name=asset.name,
            display_name=asset.display_name,
            description=asset.description,
            file_path=asset.file_path,
            file_size=asset.file_size,
            file_hash=asset.file_hash,
            mime_type=asset.mime_type,
            file_extension=asset.file_extension,
            asset_type=asset.asset_type,
            status=asset.status,
            storage_driver=asset.storage_driver,
            storage_tier=asset.storage_tier,
            owner_id=asset.owner_id,
            project_id=asset.project_id,
            is_public=asset.is_public,
            technical_metadata=asset.technical_metadata,
            version_count=1,  # Would need to query versions
            tags=[],  # Would need to load tags
            created_at=asset.created_at,
            updated_at=asset.updated_at
        )
    
    def _asset_to_list_response(self, asset: Asset) -> AssetListResponse:
        """Convert asset model to list response schema"""
        return AssetListResponse(
            id=asset.id,
            name=asset.name,
            display_name=asset.display_name,
            asset_type=asset.asset_type,
            status=asset.status,
            file_size=asset.file_size,
            mime_type=asset.mime_type,
            owner_id=asset.owner_id,
            created_at=asset.created_at
        )