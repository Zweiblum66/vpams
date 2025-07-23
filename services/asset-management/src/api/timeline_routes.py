"""
Timeline API routes

This module provides API endpoints for managing sequence timelines.
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete
from sqlalchemy.orm import selectinload

from ..core.dependencies import get_db, get_current_user
from ..core.logging import get_logger
from ..db.models import (
    SequenceTimeline, 
    ProjectContainer, 
    ContainerType,
    ShotItem,
    Asset
)
from ..models.schemas import (
    TimelineItemCreate,
    TimelineItemUpdate,
    TimelineItemResponse
)
from ..services.project_service import ProjectService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/timelines", tags=["timelines"])


@router.post("/{sequence_id}/items", response_model=TimelineItemResponse)
async def create_timeline_item(
    sequence_id: UUID,
    timeline_item: TimelineItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new timeline item in a sequence"""
    try:
        # Verify sequence exists and is a sequence type
        sequence = await db.get(ProjectContainer, sequence_id)
        if not sequence:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sequence not found"
            )
        
        if sequence.container_type != ContainerType.SEQUENCE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Container is not a sequence: {sequence.container_type}"
            )
        
        # Check permissions
        project_service = ProjectService(db)
        has_permission = await project_service.check_container_access(
            sequence_id, current_user["user_id"], "can_edit"
        )
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to edit this sequence"
            )
        
        # Verify clip exists
        clip = await db.get(ShotItem, timeline_item.clip_id)
        if not clip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Clip not found"
            )
        
        # Validate timeline data
        if timeline_item.end_time <= timeline_item.start_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End time must be greater than start time"
            )
        
        # Check for overlapping clips on the same track
        overlap_query = select(SequenceTimeline).where(
            and_(
                SequenceTimeline.sequence_id == sequence_id,
                SequenceTimeline.track_number == timeline_item.track_number,
                SequenceTimeline.track_type == timeline_item.track_type,
                SequenceTimeline.start_time < timeline_item.end_time,
                SequenceTimeline.end_time > timeline_item.start_time
            )
        )
        result = await db.execute(overlap_query)
        overlapping = result.scalar_one_or_none()
        
        if overlapping:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Timeline position overlaps with existing clip"
            )
        
        # Create timeline item
        new_timeline_item = SequenceTimeline(
            sequence_id=sequence_id,
            clip_id=timeline_item.clip_id,
            track_number=timeline_item.track_number,
            track_type=timeline_item.track_type,
            track_name=timeline_item.track_name,
            start_time=timeline_item.start_time,
            end_time=timeline_item.end_time,
            source_in=timeline_item.source_in,
            source_out=timeline_item.source_out,
            speed=timeline_item.speed,
            is_enabled=timeline_item.is_enabled,
            is_locked=timeline_item.is_locked,
            opacity=timeline_item.opacity,
            effects=timeline_item.effects or [],
            transition_in=timeline_item.transition_in,
            transition_out=timeline_item.transition_out
        )
        
        db.add(new_timeline_item)
        await db.commit()
        await db.refresh(new_timeline_item)
        
        # Add clip info to response
        response = TimelineItemResponse.model_validate(new_timeline_item)
        response.clip_name = clip.name
        response.clip_asset_id = clip.asset_id
        
        logger.info(f"Created timeline item {new_timeline_item.id} in sequence {sequence_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating timeline item: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create timeline item"
        )


@router.get("/{sequence_id}/items", response_model=List[TimelineItemResponse])
async def get_sequence_timeline(
    sequence_id: UUID,
    track_type: Optional[str] = Query(None, pattern="^(video|audio|subtitle)$"),
    track_number: Optional[int] = Query(None, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all timeline items in a sequence"""
    try:
        # Check permissions
        project_service = ProjectService(db)
        has_permission = await project_service.check_container_access(
            sequence_id, current_user["user_id"], "can_view"
        )
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this sequence"
            )
        
        # Build query
        query = select(SequenceTimeline).where(
            SequenceTimeline.sequence_id == sequence_id
        ).options(
            selectinload(SequenceTimeline.clip)
        )
        
        # Apply filters
        if track_type:
            query = query.where(SequenceTimeline.track_type == track_type)
        if track_number is not None:
            query = query.where(SequenceTimeline.track_number == track_number)
        
        # Order by track and time
        query = query.order_by(
            SequenceTimeline.track_number,
            SequenceTimeline.start_time
        )
        
        result = await db.execute(query)
        timeline_items = result.scalars().all()
        
        # Build response with clip info
        response_items = []
        for item in timeline_items:
            response = TimelineItemResponse.model_validate(item)
            response.clip_name = item.clip.name if item.clip else None
            response.clip_asset_id = item.clip.asset_id if item.clip else None
            response_items.append(response)
        
        return response_items
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting timeline items: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get timeline items"
        )


@router.get("/items/{timeline_item_id}", response_model=TimelineItemResponse)
async def get_timeline_item(
    timeline_item_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get a single timeline item"""
    try:
        # Get timeline item with clip info
        query = select(SequenceTimeline).where(
            SequenceTimeline.id == timeline_item_id
        ).options(
            selectinload(SequenceTimeline.clip)
        )
        
        result = await db.execute(query)
        timeline_item = result.scalar_one_or_none()
        
        if not timeline_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Timeline item not found"
            )
        
        # Check permissions
        project_service = ProjectService(db)
        has_permission = await project_service.check_container_access(
            timeline_item.sequence_id, current_user["user_id"], "can_view"
        )
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this timeline item"
            )
        
        # Build response
        response = TimelineItemResponse.model_validate(timeline_item)
        response.clip_name = timeline_item.clip.name if timeline_item.clip else None
        response.clip_asset_id = timeline_item.clip.asset_id if timeline_item.clip else None
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting timeline item: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get timeline item"
        )


@router.put("/items/{timeline_item_id}", response_model=TimelineItemResponse)
async def update_timeline_item(
    timeline_item_id: UUID,
    update_data: TimelineItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update a timeline item"""
    try:
        # Get timeline item
        timeline_item = await db.get(SequenceTimeline, timeline_item_id)
        if not timeline_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Timeline item not found"
            )
        
        # Check permissions
        project_service = ProjectService(db)
        has_permission = await project_service.check_container_access(
            timeline_item.sequence_id, current_user["user_id"], "can_edit"
        )
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to edit this timeline item"
            )
        
        # Check if item is locked
        if timeline_item.is_locked and not update_data.is_locked == False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Timeline item is locked"
            )
        
        # Validate timeline data if updating times
        if update_data.start_time is not None or update_data.end_time is not None:
            new_start = update_data.start_time if update_data.start_time is not None else timeline_item.start_time
            new_end = update_data.end_time if update_data.end_time is not None else timeline_item.end_time
            
            if new_end <= new_start:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="End time must be greater than start time"
                )
            
            # Check for overlaps if changing position
            overlap_query = select(SequenceTimeline).where(
                and_(
                    SequenceTimeline.sequence_id == timeline_item.sequence_id,
                    SequenceTimeline.track_number == (
                        update_data.track_number if update_data.track_number is not None 
                        else timeline_item.track_number
                    ),
                    SequenceTimeline.id != timeline_item_id,
                    SequenceTimeline.start_time < new_end,
                    SequenceTimeline.end_time > new_start
                )
            )
            result = await db.execute(overlap_query)
            overlapping = result.scalar_one_or_none()
            
            if overlapping:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="New position overlaps with existing clip"
                )
        
        # Update fields
        for field, value in update_data.model_dump(exclude_unset=True).items():
            setattr(timeline_item, field, value)
        
        await db.commit()
        await db.refresh(timeline_item)
        
        # Load clip info
        await db.refresh(timeline_item, ["clip"])
        
        # Build response
        response = TimelineItemResponse.model_validate(timeline_item)
        response.clip_name = timeline_item.clip.name if timeline_item.clip else None
        response.clip_asset_id = timeline_item.clip.asset_id if timeline_item.clip else None
        
        logger.info(f"Updated timeline item {timeline_item_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating timeline item: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update timeline item"
        )


@router.delete("/items/{timeline_item_id}")
async def delete_timeline_item(
    timeline_item_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete a timeline item"""
    try:
        # Get timeline item
        timeline_item = await db.get(SequenceTimeline, timeline_item_id)
        if not timeline_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Timeline item not found"
            )
        
        # Check permissions
        project_service = ProjectService(db)
        has_permission = await project_service.check_container_access(
            timeline_item.sequence_id, current_user["user_id"], "can_edit"
        )
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to edit this sequence"
            )
        
        # Check if item is locked
        if timeline_item.is_locked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete locked timeline item"
            )
        
        await db.delete(timeline_item)
        await db.commit()
        
        logger.info(f"Deleted timeline item {timeline_item_id}")
        return {"detail": "Timeline item deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting timeline item: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete timeline item"
        )


@router.post("/{sequence_id}/items/batch", response_model=List[TimelineItemResponse])
async def batch_create_timeline_items(
    sequence_id: UUID,
    timeline_items: List[TimelineItemCreate],
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create multiple timeline items at once"""
    try:
        # Verify sequence and permissions
        sequence = await db.get(ProjectContainer, sequence_id)
        if not sequence:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sequence not found"
            )
        
        if sequence.container_type != ContainerType.SEQUENCE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Container is not a sequence: {sequence.container_type}"
            )
        
        project_service = ProjectService(db)
        has_permission = await project_service.check_container_access(
            sequence_id, current_user["user_id"], "can_edit"
        )
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to edit this sequence"
            )
        
        # Validate all items first
        for item in timeline_items:
            if item.end_time <= item.start_time:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"End time must be greater than start time for all items"
                )
        
        # Check for overlaps within the batch
        for i, item1 in enumerate(timeline_items):
            for j, item2 in enumerate(timeline_items[i+1:], i+1):
                if (item1.track_number == item2.track_number and 
                    item1.track_type == item2.track_type and
                    item1.start_time < item2.end_time and 
                    item1.end_time > item2.start_time):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Timeline items {i} and {j} overlap on track {item1.track_number}"
                    )
        
        # Create all items
        created_items = []
        for item_data in timeline_items:
            # Verify clip exists
            clip = await db.get(ShotItem, item_data.clip_id)
            if not clip:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Clip {item_data.clip_id} not found"
                )
            
            new_item = SequenceTimeline(
                sequence_id=sequence_id,
                clip_id=item_data.clip_id,
                track_number=item_data.track_number,
                track_type=item_data.track_type,
                track_name=item_data.track_name,
                start_time=item_data.start_time,
                end_time=item_data.end_time,
                source_in=item_data.source_in,
                source_out=item_data.source_out,
                speed=item_data.speed,
                is_enabled=item_data.is_enabled,
                is_locked=item_data.is_locked,
                opacity=item_data.opacity,
                effects=item_data.effects or [],
                transition_in=item_data.transition_in,
                transition_out=item_data.transition_out
            )
            db.add(new_item)
            created_items.append((new_item, clip))
        
        await db.commit()
        
        # Build response
        response_items = []
        for item, clip in created_items:
            await db.refresh(item)
            response = TimelineItemResponse.model_validate(item)
            response.clip_name = clip.name
            response.clip_asset_id = clip.asset_id
            response_items.append(response)
        
        logger.info(f"Created {len(created_items)} timeline items in sequence {sequence_id}")
        return response_items
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error batch creating timeline items: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create timeline items"
        )


@router.delete("/{sequence_id}/items")
async def clear_sequence_timeline(
    sequence_id: UUID,
    track_type: Optional[str] = Query(None, pattern="^(video|audio|subtitle)$"),
    track_number: Optional[int] = Query(None, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Clear all or specific tracks in a sequence timeline"""
    try:
        # Check permissions
        project_service = ProjectService(db)
        has_permission = await project_service.check_container_access(
            sequence_id, current_user["user_id"], "can_edit"
        )
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to edit this sequence"
            )
        
        # Build delete query
        delete_query = delete(SequenceTimeline).where(
            and_(
                SequenceTimeline.sequence_id == sequence_id,
                SequenceTimeline.is_locked == False  # Don't delete locked items
            )
        )
        
        # Apply filters
        if track_type:
            delete_query = delete_query.where(SequenceTimeline.track_type == track_type)
        if track_number is not None:
            delete_query = delete_query.where(SequenceTimeline.track_number == track_number)
        
        result = await db.execute(delete_query)
        await db.commit()
        
        deleted_count = result.rowcount
        logger.info(f"Cleared {deleted_count} timeline items from sequence {sequence_id}")
        
        return {
            "detail": f"Deleted {deleted_count} timeline items",
            "deleted_count": deleted_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing timeline: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear timeline"
        )


@router.post("/{sequence_id}/ripple-delete/{timeline_item_id}")
async def ripple_delete_timeline_item(
    sequence_id: UUID,
    timeline_item_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete a timeline item and shift subsequent items to fill the gap"""
    try:
        # Check permissions
        project_service = ProjectService(db)
        has_permission = await project_service.check_container_access(
            sequence_id, current_user["user_id"], "can_edit"
        )
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to edit this sequence"
            )
        
        # Get the item to delete
        item_to_delete = await db.get(SequenceTimeline, timeline_item_id)
        if not item_to_delete or item_to_delete.sequence_id != sequence_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Timeline item not found in this sequence"
            )
        
        if item_to_delete.is_locked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete locked timeline item"
            )
        
        # Calculate the gap
        gap_duration = item_to_delete.end_time - item_to_delete.start_time
        
        # Get all items after this one on the same track
        subsequent_query = select(SequenceTimeline).where(
            and_(
                SequenceTimeline.sequence_id == sequence_id,
                SequenceTimeline.track_number == item_to_delete.track_number,
                SequenceTimeline.track_type == item_to_delete.track_type,
                SequenceTimeline.start_time >= item_to_delete.end_time
            )
        ).order_by(SequenceTimeline.start_time)
        
        result = await db.execute(subsequent_query)
        subsequent_items = result.scalars().all()
        
        # Delete the item
        await db.delete(item_to_delete)
        
        # Shift subsequent items
        for item in subsequent_items:
            item.start_time -= gap_duration
            item.end_time -= gap_duration
        
        await db.commit()
        
        logger.info(f"Ripple deleted timeline item {timeline_item_id}, shifted {len(subsequent_items)} items")
        
        return {
            "detail": "Timeline item deleted and subsequent items shifted",
            "deleted_item_id": timeline_item_id,
            "shifted_items_count": len(subsequent_items),
            "gap_closed": gap_duration
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ripple deleting timeline item: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ripple delete timeline item"
        )