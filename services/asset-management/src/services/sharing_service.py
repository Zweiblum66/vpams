"""
Container Sharing Service

This module handles all container sharing operations including granting,
revoking, and managing permissions.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, delete
from sqlalchemy.orm import selectinload
import structlog

from ..db.models import ProjectContainer, ContainerShare
from ..models.schemas import (
    ContainerShareCreate, ContainerShareUpdate, ContainerShareResponse,
    PaginationParams, PaginatedResponse
)
from ..core.exceptions import (
    ResourceNotFoundError, DuplicateResourceError, ValidationError,
    PermissionError, ConflictError
)

logger = structlog.get_logger()


class ContainerSharingService:
    """Service for managing container sharing"""
    
    def __init__(self, db: AsyncSession, current_user_id: UUID):
        self.db = db
        self.current_user_id = current_user_id
    
    async def create_share(
        self, 
        share_data: ContainerShareCreate
    ) -> ContainerShareResponse:
        """Create a new container share"""
        
        # Get container
        container = await self._get_container_by_id(share_data.container_id)
        if not container:
            raise ResourceNotFoundError(f"Container {share_data.container_id} not found")
        
        # Check permissions
        if not await self._can_share_container(container):
            raise PermissionError("You don't have permission to share this container")
        
        # Check if share already exists
        existing = await self.db.execute(
            select(ContainerShare).where(
                and_(
                    ContainerShare.container_id == share_data.container_id,
                    ContainerShare.shared_with_id == share_data.shared_with_id,
                    ContainerShare.shared_with_type == share_data.shared_with_type
                )
            )
        )
        if existing.scalar_one_or_none():
            raise DuplicateResourceError("Share already exists for this user/group")
        
        # Validate permissions hierarchy
        if not self._validate_permissions(share_data):
            raise ValidationError("Invalid permission combination")
        
        # Create share
        share = ContainerShare(
            container_id=share_data.container_id,
            shared_with_id=share_data.shared_with_id,
            shared_with_type=share_data.shared_with_type,
            can_view=share_data.can_view,
            can_add_assets=share_data.can_add_assets,
            can_edit=share_data.can_edit,
            can_delete=share_data.can_delete,
            can_share=share_data.can_share,
            expires_at=share_data.expires_at,
            note=share_data.note,
            shared_by=self.current_user_id
        )
        
        self.db.add(share)
        
        try:
            await self.db.commit()
            await self.db.refresh(share)
            
            logger.info(
                "container_shared",
                share_id=str(share.id),
                container_id=str(share.container_id),
                shared_with=str(share.shared_with_id),
                shared_by=str(share.shared_by)
            )
            
            return await self._to_response(share)
            
        except Exception as e:
            await self.db.rollback()
            logger.error("share_creation_failed", error=str(e))
            raise
    
    async def get_share(self, share_id: UUID) -> ContainerShareResponse:
        """Get a share by ID"""
        
        share = await self._get_share_by_id(share_id)
        if not share:
            raise ResourceNotFoundError(f"Share {share_id} not found")
        
        # Check if user can view this share
        if not await self._can_view_share(share):
            raise PermissionError("You don't have permission to view this share")
        
        return await self._to_response(share)
    
    async def list_container_shares(
        self,
        container_id: UUID,
        pagination: PaginationParams
    ) -> PaginatedResponse:
        """List all shares for a container"""
        
        # Get container
        container = await self._get_container_by_id(container_id)
        if not container:
            raise ResourceNotFoundError(f"Container {container_id} not found")
        
        # Check permissions
        if not await self._can_manage_shares(container):
            raise PermissionError("You don't have permission to view shares for this container")
        
        # Build query
        query = select(ContainerShare).where(
            ContainerShare.container_id == container_id
        ).options(selectinload(ContainerShare.container))
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)
        
        # Apply pagination
        query = query.offset(pagination.offset).limit(pagination.page_size)
        query = query.order_by(ContainerShare.created_at.desc())
        
        # Execute query
        result = await self.db.execute(query)
        shares = result.scalars().all()
        
        # Convert to response
        items = [await self._to_response(share) for share in shares]
        
        return PaginatedResponse(
            items=items,
            total=total or 0,
            page=pagination.page,
            page_size=pagination.page_size,
            pages=(total + pagination.page_size - 1) // pagination.page_size if total else 0
        )
    
    async def list_user_shares(
        self,
        pagination: PaginationParams,
        share_type: Optional[str] = None  # 'received' or 'given'
    ) -> PaginatedResponse:
        """List shares for the current user"""
        
        # Build query based on type
        if share_type == 'received':
            # Shares received by the user
            query = select(ContainerShare).where(
                and_(
                    ContainerShare.shared_with_id == self.current_user_id,
                    ContainerShare.shared_with_type == 'user',
                    or_(
                        ContainerShare.expires_at.is_(None),
                        ContainerShare.expires_at > datetime.utcnow()
                    )
                )
            )
        elif share_type == 'given':
            # Shares created by the user
            query = select(ContainerShare).where(
                ContainerShare.shared_by == self.current_user_id
            )
        else:
            # All shares involving the user
            query = select(ContainerShare).where(
                or_(
                    and_(
                        ContainerShare.shared_with_id == self.current_user_id,
                        ContainerShare.shared_with_type == 'user'
                    ),
                    ContainerShare.shared_by == self.current_user_id
                )
            )
        
        # Include container details
        query = query.options(selectinload(ContainerShare.container))
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)
        
        # Apply pagination
        query = query.offset(pagination.offset).limit(pagination.page_size)
        query = query.order_by(ContainerShare.created_at.desc())
        
        # Execute query
        result = await self.db.execute(query)
        shares = result.scalars().all()
        
        # Convert to response
        items = [await self._to_response(share) for share in shares]
        
        return PaginatedResponse(
            items=items,
            total=total or 0,
            page=pagination.page,
            page_size=pagination.page_size,
            pages=(total + pagination.page_size - 1) // pagination.page_size if total else 0
        )
    
    async def update_share(
        self,
        share_id: UUID,
        update_data: ContainerShareUpdate
    ) -> ContainerShareResponse:
        """Update share permissions"""
        
        # Get share
        share = await self._get_share_by_id(share_id)
        if not share:
            raise ResourceNotFoundError(f"Share {share_id} not found")
        
        # Check permissions
        container = await self._get_container_by_id(share.container_id)
        if not await self._can_manage_shares(container):
            raise PermissionError("You don't have permission to update this share")
        
        # Validate new permissions
        if update_data.model_dump(exclude_unset=True):
            # Create temporary object for validation
            temp_data = share.__dict__.copy()
            temp_data.update(update_data.model_dump(exclude_unset=True))
            
            if not self._validate_permissions_dict(temp_data):
                raise ValidationError("Invalid permission combination")
        
        # Update fields
        for field, value in update_data.model_dump(exclude_unset=True).items():
            setattr(share, field, value)
        
        try:
            await self.db.commit()
            await self.db.refresh(share)
            
            logger.info(
                "share_updated",
                share_id=str(share_id),
                updated_fields=list(update_data.model_dump(exclude_unset=True).keys())
            )
            
            return await self._to_response(share)
            
        except Exception as e:
            await self.db.rollback()
            logger.error("share_update_failed", error=str(e), share_id=str(share_id))
            raise
    
    async def revoke_share(self, share_id: UUID) -> None:
        """Revoke a share"""
        
        # Get share
        share = await self._get_share_by_id(share_id)
        if not share:
            raise ResourceNotFoundError(f"Share {share_id} not found")
        
        # Check permissions
        container = await self._get_container_by_id(share.container_id)
        if not await self._can_manage_shares(container):
            raise PermissionError("You don't have permission to revoke this share")
        
        # Delete share
        await self.db.delete(share)
        
        try:
            await self.db.commit()
            
            logger.info(
                "share_revoked",
                share_id=str(share_id),
                container_id=str(share.container_id),
                shared_with=str(share.shared_with_id)
            )
            
        except Exception as e:
            await self.db.rollback()
            logger.error("share_revocation_failed", error=str(e), share_id=str(share_id))
            raise
    
    async def record_access(self, share_id: UUID) -> None:
        """Record that a share was accessed"""
        
        # Get share
        share = await self._get_share_by_id(share_id)
        if share:
            share.last_accessed_at = datetime.utcnow()
            
            try:
                await self.db.commit()
            except Exception:
                await self.db.rollback()
                # Don't raise - this is just tracking
    
    async def cleanup_expired_shares(self) -> int:
        """Remove expired shares"""
        
        # Delete expired shares
        result = await self.db.execute(
            delete(ContainerShare).where(
                and_(
                    ContainerShare.expires_at.isnot(None),
                    ContainerShare.expires_at < datetime.utcnow()
                )
            )
        )
        
        deleted_count = result.rowcount
        
        if deleted_count > 0:
            await self.db.commit()
            logger.info("expired_shares_cleaned", count=deleted_count)
        
        return deleted_count
    
    # Helper methods
    
    async def _get_container_by_id(self, container_id: UUID) -> Optional[ProjectContainer]:
        """Get container by ID"""
        query = select(ProjectContainer).where(
            and_(
                ProjectContainer.id == container_id,
                ProjectContainer.deleted_at.is_(None)
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_share_by_id(self, share_id: UUID) -> Optional[ContainerShare]:
        """Get share by ID"""
        query = select(ContainerShare).where(
            ContainerShare.id == share_id
        ).options(selectinload(ContainerShare.container))
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def _can_share_container(self, container: ProjectContainer) -> bool:
        """Check if user can share container"""
        # Owner can always share
        if container.owner_id == self.current_user_id:
            return True
        
        # Check if user has share permission through existing share
        query = select(ContainerShare).where(
            and_(
                ContainerShare.container_id == container.id,
                ContainerShare.shared_with_id == self.current_user_id,
                ContainerShare.shared_with_type == 'user',
                ContainerShare.can_share == True,
                or_(
                    ContainerShare.expires_at.is_(None),
                    ContainerShare.expires_at > datetime.utcnow()
                )
            )
        )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None
    
    async def _can_manage_shares(self, container: ProjectContainer) -> bool:
        """Check if user can manage shares for container"""
        # Same as can_share for now
        return await self._can_share_container(container)
    
    async def _can_view_share(self, share: ContainerShare) -> bool:
        """Check if user can view a specific share"""
        # Can view if:
        # 1. User created the share
        # 2. User is the recipient
        # 3. User owns the container
        
        if share.shared_by == self.current_user_id:
            return True
        
        if share.shared_with_id == self.current_user_id and share.shared_with_type == 'user':
            return True
        
        if share.container.owner_id == self.current_user_id:
            return True
        
        return False
    
    def _validate_permissions(self, share_data: ContainerShareCreate) -> bool:
        """Validate permission hierarchy"""
        # Can't have higher permissions without lower ones
        if share_data.can_delete and not share_data.can_edit:
            return False
        
        if share_data.can_edit and not share_data.can_add_assets:
            return False
        
        if share_data.can_add_assets and not share_data.can_view:
            return False
        
        if share_data.can_share and not share_data.can_view:
            return False
        
        return True
    
    def _validate_permissions_dict(self, permissions: Dict[str, Any]) -> bool:
        """Validate permission hierarchy from dict"""
        # Can't have higher permissions without lower ones
        if permissions.get('can_delete') and not permissions.get('can_edit'):
            return False
        
        if permissions.get('can_edit') and not permissions.get('can_add_assets'):
            return False
        
        if permissions.get('can_add_assets') and not permissions.get('can_view'):
            return False
        
        if permissions.get('can_share') and not permissions.get('can_view'):
            return False
        
        return True
    
    async def _to_response(self, share: ContainerShare) -> ContainerShareResponse:
        """Convert share to response schema"""
        
        return ContainerShareResponse(
            id=share.id,
            container_id=share.container_id,
            container_name=share.container.display_name if share.container else None,
            shared_with_id=share.shared_with_id,
            shared_with_type=share.shared_with_type,
            can_view=share.can_view,
            can_add_assets=share.can_add_assets,
            can_edit=share.can_edit,
            can_delete=share.can_delete,
            can_share=share.can_share,
            expires_at=share.expires_at,
            note=share.note,
            shared_by=share.shared_by,
            created_at=share.created_at,
            last_accessed_at=share.last_accessed_at
        )