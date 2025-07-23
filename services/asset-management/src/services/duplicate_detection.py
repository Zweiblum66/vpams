"""
Duplicate detection service for Asset Management

This module provides functionality to detect duplicate assets based on
file hash, content similarity, and metadata.
"""

from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
from datetime import datetime, timedelta
import hashlib
import structlog
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Asset, AssetVersion, AssetStatus
from ..models.schemas import AssetResponse, DuplicateDetectionResult

logger = structlog.get_logger()


class DuplicateDetectionService:
    """Service for detecting duplicate assets"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def find_duplicates_by_hash(
        self,
        file_hash: str,
        exclude_asset_id: Optional[UUID] = None
    ) -> List[Asset]:
        """
        Find assets with the same file hash
        
        Args:
            file_hash: SHA-256 hash of the file
            exclude_asset_id: Asset ID to exclude from results
            
        Returns:
            List of assets with matching hash
        """
        query = select(Asset).where(
            and_(
                Asset.file_hash == file_hash,
                Asset.deleted_at.is_(None),
                Asset.status != AssetStatus.DELETED
            )
        )
        
        if exclude_asset_id:
            query = query.where(Asset.id != exclude_asset_id)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def find_duplicates_by_name(
        self,
        filename: str,
        project_id: Optional[UUID] = None,
        exclude_asset_id: Optional[UUID] = None
    ) -> List[Asset]:
        """
        Find assets with the same or similar filename
        
        Args:
            filename: Filename to search for
            project_id: Limit search to specific project
            exclude_asset_id: Asset ID to exclude from results
            
        Returns:
            List of assets with matching names
        """
        # Exact match query
        query = select(Asset).where(
            and_(
                Asset.name == filename,
                Asset.deleted_at.is_(None),
                Asset.status != AssetStatus.DELETED
            )
        )
        
        if project_id:
            query = query.where(Asset.project_id == project_id)
        
        if exclude_asset_id:
            query = query.where(Asset.id != exclude_asset_id)
        
        result = await self.db.execute(query)
        exact_matches = result.scalars().all()
        
        # Similar name query (using ILIKE for case-insensitive pattern matching)
        # Remove extension for similarity search
        base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
        
        similar_query = select(Asset).where(
            and_(
                Asset.name.ilike(f"{base_name}%"),
                Asset.deleted_at.is_(None),
                Asset.status != AssetStatus.DELETED
            )
        )
        
        if project_id:
            similar_query = similar_query.where(Asset.project_id == project_id)
        
        if exclude_asset_id:
            similar_query = similar_query.where(Asset.id != exclude_asset_id)
        
        similar_result = await self.db.execute(similar_query)
        similar_matches = similar_result.scalars().all()
        
        # Combine results, preserving order (exact matches first)
        all_matches = list(exact_matches)
        for asset in similar_matches:
            if asset not in all_matches:
                all_matches.append(asset)
        
        return all_matches
    
    async def find_duplicates_by_size(
        self,
        file_size: int,
        tolerance_percent: float = 0.0,
        exclude_asset_id: Optional[UUID] = None
    ) -> List[Asset]:
        """
        Find assets with similar file size
        
        Args:
            file_size: File size in bytes
            tolerance_percent: Size tolerance as percentage (0-100)
            exclude_asset_id: Asset ID to exclude from results
            
        Returns:
            List of assets with similar size
        """
        if tolerance_percent > 0:
            min_size = int(file_size * (1 - tolerance_percent / 100))
            max_size = int(file_size * (1 + tolerance_percent / 100))
            
            query = select(Asset).where(
                and_(
                    Asset.file_size >= min_size,
                    Asset.file_size <= max_size,
                    Asset.deleted_at.is_(None),
                    Asset.status != AssetStatus.DELETED
                )
            )
        else:
            query = select(Asset).where(
                and_(
                    Asset.file_size == file_size,
                    Asset.deleted_at.is_(None),
                    Asset.status != AssetStatus.DELETED
                )
            )
        
        if exclude_asset_id:
            query = query.where(Asset.id != exclude_asset_id)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def check_for_duplicates(
        self,
        filename: str,
        file_size: int,
        file_hash: Optional[str] = None,
        project_id: Optional[UUID] = None,
        check_hash: bool = True,
        check_name: bool = True,
        check_size: bool = True,
        size_tolerance: float = 1.0
    ) -> DuplicateDetectionResult:
        """
        Comprehensive duplicate check
        
        Args:
            filename: Name of the file
            file_size: Size of the file in bytes
            file_hash: SHA-256 hash of the file
            project_id: Project to limit search to
            check_hash: Whether to check by hash
            check_name: Whether to check by name
            check_size: Whether to check by size
            size_tolerance: Size tolerance percentage
            
        Returns:
            DuplicateDetectionResult with findings
        """
        result = DuplicateDetectionResult(
            has_exact_duplicates=False,
            has_similar_duplicates=False,
            exact_duplicates=[],
            similar_duplicates=[],
            duplicate_count=0
        )
        
        exact_matches = set()
        similar_matches = set()
        
        # Check by hash (most reliable)
        if check_hash and file_hash:
            hash_duplicates = await self.find_duplicates_by_hash(file_hash)
            for asset in hash_duplicates:
                exact_matches.add(asset)
                logger.info(
                    "exact_duplicate_found_by_hash",
                    asset_id=str(asset.id),
                    hash=file_hash
                )
        
        # Check by name
        if check_name:
            name_duplicates = await self.find_duplicates_by_name(
                filename,
                project_id
            )
            for asset in name_duplicates:
                if asset.name == filename:
                    # Exact name match
                    if check_size and abs(asset.file_size - file_size) <= file_size * 0.01:
                        # Same name and very similar size - likely duplicate
                        exact_matches.add(asset)
                    else:
                        similar_matches.add(asset)
                else:
                    # Similar name
                    similar_matches.add(asset)
        
        # Check by size
        if check_size and len(exact_matches) == 0:
            size_duplicates = await self.find_duplicates_by_size(
                file_size,
                size_tolerance
            )
            for asset in size_duplicates:
                if asset not in exact_matches:
                    similar_matches.add(asset)
        
        # Remove exact matches from similar matches
        similar_matches = similar_matches - exact_matches
        
        # Build result
        result.exact_duplicates = list(exact_matches)
        result.similar_duplicates = list(similar_matches)
        result.has_exact_duplicates = len(exact_matches) > 0
        result.has_similar_duplicates = len(similar_matches) > 0
        result.duplicate_count = len(exact_matches) + len(similar_matches)
        
        if result.has_exact_duplicates:
            logger.warning(
                "exact_duplicates_detected",
                count=len(exact_matches),
                filename=filename
            )
        
        return result
    
    async def find_all_duplicate_groups(
        self,
        project_id: Optional[UUID] = None,
        min_group_size: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Find all groups of duplicate assets in the system
        
        Args:
            project_id: Limit to specific project
            min_group_size: Minimum number of duplicates to form a group
            
        Returns:
            List of duplicate groups with asset information
        """
        # Query to find all hashes with multiple assets
        hash_query = (
            select(
                Asset.file_hash,
                func.count(Asset.id).label('count'),
                func.array_agg(Asset.id).label('asset_ids')
            )
            .where(
                and_(
                    Asset.file_hash.isnot(None),
                    Asset.deleted_at.is_(None),
                    Asset.status != AssetStatus.DELETED
                )
            )
            .group_by(Asset.file_hash)
            .having(func.count(Asset.id) >= min_group_size)
        )
        
        if project_id:
            hash_query = hash_query.where(Asset.project_id == project_id)
        
        result = await self.db.execute(hash_query)
        duplicate_groups = []
        
        for row in result:
            # Get full asset information for each group
            assets_query = select(Asset).where(
                Asset.id.in_(row.asset_ids)
            )
            assets_result = await self.db.execute(assets_query)
            assets = assets_result.scalars().all()
            
            group_info = {
                "file_hash": row.file_hash,
                "duplicate_count": row.count,
                "total_size": sum(a.file_size for a in assets),
                "wasted_space": sum(a.file_size for a in assets[1:]),  # All but one copy
                "assets": [
                    {
                        "id": str(a.id),
                        "name": a.name,
                        "size": a.file_size,
                        "created_at": a.created_at,
                        "owner_id": str(a.owner_id),
                        "project_id": str(a.project_id) if a.project_id else None
                    }
                    for a in assets
                ]
            }
            duplicate_groups.append(group_info)
        
        # Sort by wasted space descending
        duplicate_groups.sort(key=lambda x: x["wasted_space"], reverse=True)
        
        return duplicate_groups
    
    async def get_duplicate_statistics(
        self,
        project_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Get statistics about duplicates in the system
        
        Args:
            project_id: Limit to specific project
            
        Returns:
            Dictionary with duplicate statistics
        """
        # Count total assets
        total_query = select(func.count(Asset.id)).where(
            and_(
                Asset.deleted_at.is_(None),
                Asset.status != AssetStatus.DELETED
            )
        )
        if project_id:
            total_query = total_query.where(Asset.project_id == project_id)
        
        total_result = await self.db.execute(total_query)
        total_assets = total_result.scalar_one()
        
        # Find duplicate groups
        duplicate_groups = await self.find_all_duplicate_groups(project_id)
        
        # Calculate statistics
        total_duplicates = sum(g["duplicate_count"] for g in duplicate_groups)
        unique_duplicates = len(duplicate_groups)
        total_wasted_space = sum(g["wasted_space"] for g in duplicate_groups)
        
        return {
            "total_assets": total_assets,
            "total_duplicate_assets": total_duplicates,
            "unique_duplicate_groups": unique_duplicates,
            "total_wasted_space_bytes": total_wasted_space,
            "total_wasted_space_gb": round(total_wasted_space / (1024**3), 2),
            "duplicate_percentage": round(
                (total_duplicates / total_assets * 100) if total_assets > 0 else 0,
                2
            ),
            "largest_duplicate_group": max(
                (g["duplicate_count"] for g in duplicate_groups),
                default=0
            ),
            "project_id": str(project_id) if project_id else None
        }
    
    async def suggest_duplicates_for_removal(
        self,
        file_hash: str
    ) -> Tuple[Asset, List[Asset]]:
        """
        Suggest which duplicate to keep and which to remove
        
        Uses criteria:
        1. Keep the oldest (original)
        2. Keep the one with most relationships
        3. Keep the one with most metadata
        
        Args:
            file_hash: Hash of duplicate group
            
        Returns:
            Tuple of (asset_to_keep, assets_to_remove)
        """
        # Get all assets with this hash
        duplicates = await self.find_duplicates_by_hash(file_hash)
        
        if len(duplicates) <= 1:
            return None, []
        
        # Score each asset
        scored_assets = []
        for asset in duplicates:
            score = 0
            
            # Older is better (original)
            age_score = (datetime.utcnow() - asset.created_at).days
            score += age_score * 10
            
            # More metadata is better
            if asset.technical_metadata:
                score += len(asset.technical_metadata) * 5
            
            # Being in a project is better
            if asset.project_id:
                score += 50
            
            # Having tags is better
            if hasattr(asset, 'tags') and asset.tags:
                score += len(asset.tags) * 10
            
            scored_assets.append((score, asset))
        
        # Sort by score descending
        scored_assets.sort(key=lambda x: x[0], reverse=True)
        
        # Best asset to keep
        asset_to_keep = scored_assets[0][1]
        assets_to_remove = [sa[1] for sa in scored_assets[1:]]
        
        logger.info(
            "duplicate_removal_suggestion",
            keep_asset_id=str(asset_to_keep.id),
            remove_count=len(assets_to_remove),
            file_hash=file_hash
        )
        
        return asset_to_keep, assets_to_remove