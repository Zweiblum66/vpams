"""
Project Service

This module handles project-related operations including container access checks.
"""

from typing import Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from ..db.models import ProjectContainer, ContainerShare
from ..core.logging import get_logger

logger = get_logger(__name__)


class ProjectService:
    """Service for project-related operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def check_container_access(
        self,
        container_id: UUID,
        user_id: UUID,
        permission: str = "can_view"
    ) -> bool:
        """
        Check if a user has specific permission on a container
        
        Args:
            container_id: Container ID to check
            user_id: User ID to check access for
            permission: Permission to check (can_view, can_add_assets, can_edit, can_delete, can_share)
            
        Returns:
            bool: True if user has permission, False otherwise
        """
        try:
            # First check if user is the owner
            container = await self.db.get(ProjectContainer, container_id)
            if not container:
                return False
            
            if container.owner_id == user_id:
                return True
            
            # Check if container is public (only for view permission)
            if container.is_public and permission == "can_view":
                return True
            
            # Check container shares
            query = select(ContainerShare).where(
                and_(
                    ContainerShare.container_id == container_id,
                    ContainerShare.shared_with_id == user_id,
                    ContainerShare.shared_with_type == "user"
                )
            )
            
            result = await self.db.execute(query)
            share = result.scalar_one_or_none()
            
            if not share:
                # Also check parent containers for inherited permissions
                if container.parent_id:
                    return await self.check_container_access(
                        container.parent_id,
                        user_id,
                        permission
                    )
                return False
            
            # Check if share has expired
            if share.expires_at and share.expires_at < datetime.utcnow():
                return False
            
            # Check specific permission
            if permission == "can_view":
                return share.can_view
            elif permission == "can_add_assets":
                return share.can_add_assets
            elif permission == "can_edit":
                return share.can_edit
            elif permission == "can_delete":
                return share.can_delete
            elif permission == "can_share":
                return share.can_share
            else:
                return False
                
        except Exception as e:
            logger.error(f"Error checking container access: {e}")
            return False
    
    async def get_user_accessible_containers(
        self,
        user_id: UUID,
        container_type: Optional[str] = None,
        permission: str = "can_view"
    ) -> list[ProjectContainer]:
        """
        Get all containers a user has access to
        
        Args:
            user_id: User ID
            container_type: Optional filter by container type
            permission: Required permission level
            
        Returns:
            List of accessible containers
        """
        # Build query for owned containers
        owned_query = select(ProjectContainer).where(
            ProjectContainer.owner_id == user_id
        )
        
        # Build query for shared containers
        shared_query = select(ProjectContainer).join(
            ContainerShare,
            ProjectContainer.id == ContainerShare.container_id
        ).where(
            and_(
                ContainerShare.shared_with_id == user_id,
                ContainerShare.shared_with_type == "user",
                getattr(ContainerShare, permission) == True
            )
        )
        
        # Add public containers for view permission
        if permission == "can_view":
            public_query = select(ProjectContainer).where(
                ProjectContainer.is_public == True
            )
            
            # Combine all queries
            query = owned_query.union(shared_query).union(public_query)
        else:
            # Combine owned and shared
            query = owned_query.union(shared_query)
        
        # Filter by container type if specified
        if container_type:
            query = query.where(ProjectContainer.container_type == container_type)
        
        # Execute query
        result = await self.db.execute(query)
        containers = result.scalars().all()
        
        return containers