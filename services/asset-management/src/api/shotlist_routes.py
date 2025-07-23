"""
API routes for shotlist and shot item management
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload

from ..db.session import get_db
from ..db.models import ShotItem, ProjectContainer, Asset, ContainerType
from ..models.schemas import (
    ShotItemCreate,
    ShotItemUpdate,
    ShotItemResponse,
    PaginationParams
)
from .dependencies import get_current_user, require_permissions
from ..services.project_service import ProjectService
from ..core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/shotlists", tags=["shotlists"])


@router.post("/{container_id}/shots", response_model=ShotItemResponse)
async def create_shot_item(
    container_id: UUID,
    shot_data: ShotItemCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new shot item in a shotlist or bin"""
    try:
        # Verify container exists and user has access
        container = await db.get(ProjectContainer, container_id)
        if not container:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Container not found"
            )
        
        # Check if user has permission to add to this container
        if container.owner_id != UUID(current_user["user_id"]):
            # Check if user has shared access with add permission
            project_service = ProjectService(db)
            has_access = await project_service.check_container_access(
                container_id=container_id,
                user_id=UUID(current_user["user_id"]),
                permission="can_add_assets"
            )
            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to add shots to this container"
                )
        
        # Verify container type (must be BIN or SHOTLIST)
        if container.container_type not in [ContainerType.BIN, ContainerType.SHOTLIST]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot add shots to container type: {container.container_type.value}"
            )
        
        # Verify asset exists and user has access
        asset = await db.get(Asset, shot_data.asset_id)
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Asset not found"
            )
        
        # Create shot item
        shot_item = ShotItem(
            container_id=container_id,
            asset_id=shot_data.asset_id,
            name=shot_data.name,
            description=shot_data.description,
            in_point=shot_data.in_point,
            out_point=shot_data.out_point,
            metadata=shot_data.metadata or {},
            markers=shot_data.markers or [],
            sort_order=shot_data.sort_order or 0,
            color_label=shot_data.color_label,
            created_by=UUID(current_user["user_id"])
        )
        
        # Calculate duration if out_point is provided
        if shot_item.out_point:
            shot_item.duration = shot_item.out_point - shot_item.in_point
        
        db.add(shot_item)
        await db.commit()
        await db.refresh(shot_item)
        
        logger.info(
            "shot_item_created",
            shot_id=str(shot_item.id),
            container_id=str(container_id),
            asset_id=str(shot_data.asset_id),
            user_id=current_user["user_id"]
        )
        
        return shot_item
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create shot item: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create shot item"
        )


@router.get("/{container_id}/shots", response_model=List[ShotItemResponse])
async def get_container_shots(
    container_id: UUID,
    pagination: PaginationParams = Depends(),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all shot items in a container"""
    try:
        # Verify container exists and user has access
        container = await db.get(ProjectContainer, container_id)
        if not container:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Container not found"
            )
        
        # Check access
        if container.owner_id != UUID(current_user["user_id"]):
            project_service = ProjectService(db)
            has_access = await project_service.check_container_access(
                container_id=container_id,
                user_id=UUID(current_user["user_id"]),
                permission="can_view"
            )
            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to view this container"
                )
        
        # Query shot items
        query = select(ShotItem).where(
            ShotItem.container_id == container_id
        ).order_by(ShotItem.sort_order, ShotItem.created_at)
        
        # Apply pagination
        query = query.offset(pagination.offset).limit(pagination.limit)
        
        result = await db.execute(query)
        shot_items = result.scalars().all()
        
        return shot_items
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get shot items: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get shot items"
        )


@router.get("/shots/{shot_id}", response_model=ShotItemResponse)
async def get_shot_item(
    shot_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific shot item"""
    try:
        # Get shot item with asset and container info
        query = select(ShotItem).where(
            ShotItem.id == shot_id
        ).options(selectinload(ShotItem.asset), selectinload(ShotItem.container))
        
        result = await db.execute(query)
        shot_item = result.scalar_one_or_none()
        
        if not shot_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shot item not found"
            )
        
        # Check access via container
        if shot_item.container.owner_id != UUID(current_user["user_id"]):
            project_service = ProjectService(db)
            has_access = await project_service.check_container_access(
                container_id=shot_item.container_id,
                user_id=UUID(current_user["user_id"]),
                permission="can_view"
            )
            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to view this shot"
                )
        
        return shot_item
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get shot item: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get shot item"
        )


@router.put("/shots/{shot_id}", response_model=ShotItemResponse)
async def update_shot_item(
    shot_id: UUID,
    shot_update: ShotItemUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a shot item"""
    try:
        # Get shot item
        shot_item = await db.get(ShotItem, shot_id)
        if not shot_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shot item not found"
            )
        
        # Get container for permission check
        container = await db.get(ProjectContainer, shot_item.container_id)
        
        # Check permission
        if container.owner_id != UUID(current_user["user_id"]):
            project_service = ProjectService(db)
            has_access = await project_service.check_container_access(
                container_id=shot_item.container_id,
                user_id=UUID(current_user["user_id"]),
                permission="can_edit"
            )
            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to edit this shot"
                )
        
        # Update fields
        update_data = shot_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(shot_item, field, value)
        
        # Recalculate duration if in/out points changed
        if "in_point" in update_data or "out_point" in update_data:
            if shot_item.out_point and shot_item.in_point is not None:
                shot_item.duration = shot_item.out_point - shot_item.in_point
        
        await db.commit()
        await db.refresh(shot_item)
        
        logger.info(
            "shot_item_updated",
            shot_id=str(shot_id),
            user_id=current_user["user_id"],
            updated_fields=list(update_data.keys())
        )
        
        return shot_item
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update shot item: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update shot item"
        )


@router.delete("/shots/{shot_id}")
async def delete_shot_item(
    shot_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a shot item"""
    try:
        # Get shot item
        shot_item = await db.get(ShotItem, shot_id)
        if not shot_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shot item not found"
            )
        
        # Get container for permission check
        container = await db.get(ProjectContainer, shot_item.container_id)
        
        # Check permission
        if container.owner_id != UUID(current_user["user_id"]):
            project_service = ProjectService(db)
            has_access = await project_service.check_container_access(
                container_id=shot_item.container_id,
                user_id=UUID(current_user["user_id"]),
                permission="can_delete"
            )
            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to delete this shot"
                )
        
        await db.delete(shot_item)
        await db.commit()
        
        logger.info(
            "shot_item_deleted",
            shot_id=str(shot_id),
            container_id=str(shot_item.container_id),
            user_id=current_user["user_id"]
        )
        
        return {"detail": "Shot item deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete shot item: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete shot item"
        )


@router.post("/shots/{shot_id}/duplicate", response_model=ShotItemResponse)
async def duplicate_shot_item(
    shot_id: UUID,
    target_container_id: Optional[UUID] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Duplicate a shot item"""
    try:
        # Get original shot item
        original_shot = await db.get(ShotItem, shot_id)
        if not original_shot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shot item not found"
            )
        
        # Use same container if target not specified
        target_container_id = target_container_id or original_shot.container_id
        
        # Check permissions on both containers
        containers_to_check = [original_shot.container_id]
        if target_container_id != original_shot.container_id:
            containers_to_check.append(target_container_id)
        
        project_service = ProjectService(db)
        for container_id in containers_to_check:
            container = await db.get(ProjectContainer, container_id)
            if not container:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Container {container_id} not found"
                )
            
            # Check permission
            if container.owner_id != UUID(current_user["user_id"]):
                has_access = await project_service.check_container_access(
                    container_id=container_id,
                    user_id=UUID(current_user["user_id"]),
                    permission="can_add_assets" if container_id == target_container_id else "can_view"
                )
                if not has_access:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Insufficient permissions for container {container_id}"
                    )
        
        # Create duplicate
        new_shot = ShotItem(
            container_id=target_container_id,
            asset_id=original_shot.asset_id,
            name=f"{original_shot.name} (copy)",
            description=original_shot.description,
            in_point=original_shot.in_point,
            out_point=original_shot.out_point,
            duration=original_shot.duration,
            metadata=original_shot.metadata.copy() if original_shot.metadata else {},
            markers=original_shot.markers.copy() if original_shot.markers else [],
            sort_order=original_shot.sort_order,
            color_label=original_shot.color_label,
            created_by=UUID(current_user["user_id"])
        )
        
        db.add(new_shot)
        await db.commit()
        await db.refresh(new_shot)
        
        logger.info(
            "shot_item_duplicated",
            original_shot_id=str(shot_id),
            new_shot_id=str(new_shot.id),
            target_container_id=str(target_container_id),
            user_id=current_user["user_id"]
        )
        
        return new_shot
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to duplicate shot item: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to duplicate shot item"
        )


@router.put("/{container_id}/shots/reorder")
async def reorder_shots(
    container_id: UUID,
    shot_order: List[UUID],
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Reorder shots in a container"""
    try:
        # Verify container and permissions
        container = await db.get(ProjectContainer, container_id)
        if not container:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Container not found"
            )
        
        # Check permission
        if container.owner_id != UUID(current_user["user_id"]):
            project_service = ProjectService(db)
            has_access = await project_service.check_container_access(
                container_id=container_id,
                user_id=UUID(current_user["user_id"]),
                permission="can_edit"
            )
            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to reorder shots in this container"
                )
        
        # Get all shots in container
        query = select(ShotItem).where(ShotItem.container_id == container_id)
        result = await db.execute(query)
        shots = {shot.id: shot for shot in result.scalars().all()}
        
        # Verify all provided shot IDs belong to this container
        for shot_id in shot_order:
            if shot_id not in shots:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Shot {shot_id} not found in this container"
                )
        
        # Update sort order
        for index, shot_id in enumerate(shot_order):
            shots[shot_id].sort_order = index
        
        await db.commit()
        
        logger.info(
            "shots_reordered",
            container_id=str(container_id),
            user_id=current_user["user_id"],
            shot_count=len(shot_order)
        )
        
        return {"detail": f"Reordered {len(shot_order)} shots successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reorder shots: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reorder shots"
        )


@router.post("/{container_id}/shots/batch", response_model=List[ShotItemResponse])
async def create_batch_shots(
    container_id: UUID,
    shots_data: List[ShotItemCreate],
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create multiple shot items at once"""
    try:
        # Verify container and permissions
        container = await db.get(ProjectContainer, container_id)
        if not container:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Container not found"
            )
        
        # Check permission
        if container.owner_id != UUID(current_user["user_id"]):
            project_service = ProjectService(db)
            has_access = await project_service.check_container_access(
                container_id=container_id,
                user_id=UUID(current_user["user_id"]),
                permission="can_add_assets"
            )
            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to add shots to this container"
                )
        
        # Verify container type
        if container.container_type not in [ContainerType.BIN, ContainerType.SHOTLIST]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot add shots to container type: {container.container_type.value}"
            )
        
        # Verify all assets exist
        asset_ids = {shot.asset_id for shot in shots_data}
        query = select(Asset.id).where(Asset.id.in_(asset_ids))
        result = await db.execute(query)
        existing_asset_ids = set(result.scalars().all())
        
        missing_assets = asset_ids - existing_asset_ids
        if missing_assets:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assets not found: {', '.join(str(id) for id in missing_assets)}"
            )
        
        # Create shot items
        created_shots = []
        for index, shot_data in enumerate(shots_data):
            shot_item = ShotItem(
                container_id=container_id,
                asset_id=shot_data.asset_id,
                name=shot_data.name,
                description=shot_data.description,
                in_point=shot_data.in_point,
                out_point=shot_data.out_point,
                metadata=shot_data.metadata or {},
                markers=shot_data.markers or [],
                sort_order=shot_data.sort_order if shot_data.sort_order is not None else index,
                color_label=shot_data.color_label,
                created_by=UUID(current_user["user_id"])
            )
            
            # Calculate duration
            if shot_item.out_point:
                shot_item.duration = shot_item.out_point - shot_item.in_point
            
            db.add(shot_item)
            created_shots.append(shot_item)
        
        await db.commit()
        
        # Refresh all created shots
        for shot in created_shots:
            await db.refresh(shot)
        
        logger.info(
            "batch_shots_created",
            container_id=str(container_id),
            shot_count=len(created_shots),
            user_id=current_user["user_id"]
        )
        
        return created_shots
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create batch shots: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create batch shots"
        )