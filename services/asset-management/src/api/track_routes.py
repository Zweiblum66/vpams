"""
Track Management API routes

This module provides API endpoints for managing timeline tracks in sequences.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, update
from pydantic import BaseModel, Field

from ..core.dependencies import get_db, get_current_user
from ..core.logging import get_logger
from ..db.models import (
    SequenceTimeline, 
    ProjectContainer,
    ContainerType
)
from ..services.project_service import ProjectService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/tracks", tags=["tracks"])


# Track schemas
class TrackInfo(BaseModel):
    """Track information schema"""
    track_number: int = Field(..., ge=0)
    track_type: str = Field(..., pattern="^(video|audio|subtitle)$")
    track_name: Optional[str] = None
    is_locked: bool = False
    is_muted: bool = False
    is_solo: bool = False
    height: int = Field(100, ge=50, le=500)  # Track height in pixels
    metadata: Optional[Dict[str, Any]] = None


class TrackCreate(BaseModel):
    """Schema for creating a track"""
    track_type: str = Field(..., pattern="^(video|audio|subtitle)$")
    track_name: Optional[str] = None
    position: Optional[int] = None  # Insert at specific position
    height: int = Field(100, ge=50, le=500)
    metadata: Optional[Dict[str, Any]] = None


class TrackUpdate(BaseModel):
    """Schema for updating a track"""
    track_name: Optional[str] = None
    is_locked: Optional[bool] = None
    is_muted: Optional[bool] = None
    is_solo: Optional[bool] = None
    height: Optional[int] = Field(None, ge=50, le=500)
    metadata: Optional[Dict[str, Any]] = None


class TrackReorder(BaseModel):
    """Schema for reordering tracks"""
    track_type: str = Field(..., pattern="^(video|audio|subtitle)$")
    new_order: List[int]  # List of track numbers in new order


class TrackResponse(TrackInfo):
    """Track response with additional info"""
    clip_count: int = 0
    total_duration: int = 0


@router.get("/{sequence_id}/tracks", response_model=List[TrackResponse])
async def get_sequence_tracks(
    sequence_id: UUID,
    track_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all tracks in a sequence with their information"""
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
        
        # Get sequence metadata to retrieve track info
        sequence = await db.get(ProjectContainer, sequence_id)
        if not sequence:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sequence not found"
            )
        
        # Initialize track metadata if not exists
        if not sequence.metadata:
            sequence.metadata = {}
        if "tracks" not in sequence.metadata:
            sequence.metadata["tracks"] = {}
        
        # Query to get track statistics
        stats_query = select(
            SequenceTimeline.track_number,
            SequenceTimeline.track_type,
            func.count(SequenceTimeline.id).label("clip_count"),
            func.sum(SequenceTimeline.end_time - SequenceTimeline.start_time).label("total_duration")
        ).where(
            SequenceTimeline.sequence_id == sequence_id
        ).group_by(
            SequenceTimeline.track_number,
            SequenceTimeline.track_type
        )
        
        if track_type:
            stats_query = stats_query.where(SequenceTimeline.track_type == track_type)
        
        result = await db.execute(stats_query)
        track_stats = {
            (row.track_type, row.track_number): {
                "clip_count": row.clip_count,
                "total_duration": row.total_duration or 0
            }
            for row in result
        }
        
        # Build track list from both metadata and actual usage
        tracks = []
        track_metadata = sequence.metadata.get("tracks", {})
        
        # Add tracks from metadata
        for track_key, track_info in track_metadata.items():
            track_type_key, track_num = track_key.split("_", 1)
            track_num = int(track_num)
            
            if track_type and track_type_key != track_type:
                continue
            
            stats = track_stats.get((track_type_key, track_num), {})
            
            track = TrackResponse(
                track_number=track_num,
                track_type=track_type_key,
                track_name=track_info.get("name"),
                is_locked=track_info.get("is_locked", False),
                is_muted=track_info.get("is_muted", False),
                is_solo=track_info.get("is_solo", False),
                height=track_info.get("height", 100),
                metadata=track_info.get("metadata"),
                clip_count=stats.get("clip_count", 0),
                total_duration=stats.get("total_duration", 0)
            )
            tracks.append(track)
        
        # Add tracks that have clips but no metadata
        for (t_type, t_num), stats in track_stats.items():
            track_key = f"{t_type}_{t_num}"
            if track_key not in track_metadata:
                if track_type and t_type != track_type:
                    continue
                
                track = TrackResponse(
                    track_number=t_num,
                    track_type=t_type,
                    track_name=f"{t_type.upper()} {t_num + 1}",
                    is_locked=False,
                    is_muted=False,
                    is_solo=False,
                    height=100,
                    metadata=None,
                    clip_count=stats["clip_count"],
                    total_duration=stats["total_duration"]
                )
                tracks.append(track)
        
        # Sort tracks by type and number
        tracks.sort(key=lambda t: (
            0 if t.track_type == "video" else 1 if t.track_type == "audio" else 2,
            t.track_number
        ))
        
        return tracks
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting sequence tracks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get sequence tracks"
        )


@router.post("/{sequence_id}/tracks", response_model=TrackResponse)
async def create_track(
    sequence_id: UUID,
    track_data: TrackCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new track in a sequence"""
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
        
        # Get sequence
        sequence = await db.get(ProjectContainer, sequence_id)
        if not sequence:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sequence not found"
            )
        
        if sequence.container_type != ContainerType.SEQUENCE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Container is not a sequence"
            )
        
        # Initialize metadata
        if not sequence.metadata:
            sequence.metadata = {}
        if "tracks" not in sequence.metadata:
            sequence.metadata["tracks"] = {}
        
        # Find next available track number
        existing_tracks = [
            int(key.split("_", 1)[1])
            for key in sequence.metadata["tracks"]
            if key.startswith(f"{track_data.track_type}_")
        ]
        
        # Also check for tracks with clips
        clips_query = select(SequenceTimeline.track_number).where(
            and_(
                SequenceTimeline.sequence_id == sequence_id,
                SequenceTimeline.track_type == track_data.track_type
            )
        ).distinct()
        result = await db.execute(clips_query)
        tracks_with_clips = [row.track_number for row in result]
        
        all_track_numbers = list(set(existing_tracks + tracks_with_clips))
        
        if track_data.position is not None:
            # Insert at specific position
            track_number = track_data.position
            if track_number in all_track_numbers:
                # Shift existing tracks
                for i in sorted(all_track_numbers, reverse=True):
                    if i >= track_number:
                        # Update track metadata
                        old_key = f"{track_data.track_type}_{i}"
                        new_key = f"{track_data.track_type}_{i + 1}"
                        if old_key in sequence.metadata["tracks"]:
                            sequence.metadata["tracks"][new_key] = sequence.metadata["tracks"].pop(old_key)
                        
                        # Update clips
                        await db.execute(
                            update(SequenceTimeline)
                            .where(
                                and_(
                                    SequenceTimeline.sequence_id == sequence_id,
                                    SequenceTimeline.track_type == track_data.track_type,
                                    SequenceTimeline.track_number == i
                                )
                            )
                            .values(track_number=i + 1)
                        )
        else:
            # Add at the end
            track_number = max(all_track_numbers, default=-1) + 1
        
        # Create track metadata
        track_key = f"{track_data.track_type}_{track_number}"
        sequence.metadata["tracks"][track_key] = {
            "name": track_data.track_name or f"{track_data.track_type.upper()} {track_number + 1}",
            "is_locked": False,
            "is_muted": False,
            "is_solo": False,
            "height": track_data.height,
            "metadata": track_data.metadata or {}
        }
        
        # Update sequence
        sequence.metadata = dict(sequence.metadata)  # Ensure it's marked as modified
        await db.commit()
        await db.refresh(sequence)
        
        # Return track info
        track_info = sequence.metadata["tracks"][track_key]
        return TrackResponse(
            track_number=track_number,
            track_type=track_data.track_type,
            track_name=track_info["name"],
            is_locked=track_info["is_locked"],
            is_muted=track_info["is_muted"],
            is_solo=track_info["is_solo"],
            height=track_info["height"],
            metadata=track_info.get("metadata"),
            clip_count=0,
            total_duration=0
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating track: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create track"
        )


@router.put("/{sequence_id}/tracks/{track_type}/{track_number}", response_model=TrackResponse)
async def update_track(
    sequence_id: UUID,
    track_type: str,
    track_number: int,
    update_data: TrackUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update track properties"""
    try:
        # Validate track type
        if track_type not in ["video", "audio", "subtitle"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid track type"
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
        
        # Get sequence
        sequence = await db.get(ProjectContainer, sequence_id)
        if not sequence:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sequence not found"
            )
        
        # Initialize metadata
        if not sequence.metadata:
            sequence.metadata = {}
        if "tracks" not in sequence.metadata:
            sequence.metadata["tracks"] = {}
        
        track_key = f"{track_type}_{track_number}"
        
        # Create track metadata if it doesn't exist
        if track_key not in sequence.metadata["tracks"]:
            sequence.metadata["tracks"][track_key] = {
                "name": f"{track_type.upper()} {track_number + 1}",
                "is_locked": False,
                "is_muted": False,
                "is_solo": False,
                "height": 100,
                "metadata": {}
            }
        
        # Update track properties
        track_info = sequence.metadata["tracks"][track_key]
        
        for field, value in update_data.model_dump(exclude_unset=True).items():
            if field == "track_name":
                track_info["name"] = value
            else:
                track_info[field] = value
        
        # If track is being locked, also lock all clips on the track
        if update_data.is_locked is True:
            await db.execute(
                update(SequenceTimeline)
                .where(
                    and_(
                        SequenceTimeline.sequence_id == sequence_id,
                        SequenceTimeline.track_type == track_type,
                        SequenceTimeline.track_number == track_number
                    )
                )
                .values(is_locked=True)
            )
        
        # Handle solo mode - only one track of each type can be solo
        if update_data.is_solo is True:
            for key, info in sequence.metadata["tracks"].items():
                if key != track_key and key.startswith(f"{track_type}_"):
                    info["is_solo"] = False
        
        # Update sequence
        sequence.metadata = dict(sequence.metadata)
        await db.commit()
        await db.refresh(sequence)
        
        # Get track statistics
        stats_result = await db.execute(
            select(
                func.count(SequenceTimeline.id).label("clip_count"),
                func.sum(SequenceTimeline.end_time - SequenceTimeline.start_time).label("total_duration")
            ).where(
                and_(
                    SequenceTimeline.sequence_id == sequence_id,
                    SequenceTimeline.track_type == track_type,
                    SequenceTimeline.track_number == track_number
                )
            )
        )
        stats = stats_result.one()
        
        # Return updated track info
        return TrackResponse(
            track_number=track_number,
            track_type=track_type,
            track_name=track_info["name"],
            is_locked=track_info["is_locked"],
            is_muted=track_info["is_muted"],
            is_solo=track_info["is_solo"],
            height=track_info["height"],
            metadata=track_info.get("metadata"),
            clip_count=stats.clip_count or 0,
            total_duration=stats.total_duration or 0
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating track: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update track"
        )


@router.delete("/{sequence_id}/tracks/{track_type}/{track_number}")
async def delete_track(
    sequence_id: UUID,
    track_type: str,
    track_number: int,
    force: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete a track and optionally its clips"""
    try:
        # Validate track type
        if track_type not in ["video", "audio", "subtitle"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid track type"
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
        
        # Check if track has clips
        clip_count_result = await db.execute(
            select(func.count(SequenceTimeline.id)).where(
                and_(
                    SequenceTimeline.sequence_id == sequence_id,
                    SequenceTimeline.track_type == track_type,
                    SequenceTimeline.track_number == track_number
                )
            )
        )
        clip_count = clip_count_result.scalar()
        
        if clip_count > 0 and not force:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Track has {clip_count} clips. Use force=true to delete track and clips"
            )
        
        # Delete clips if force is true
        if force and clip_count > 0:
            await db.execute(
                delete(SequenceTimeline).where(
                    and_(
                        SequenceTimeline.sequence_id == sequence_id,
                        SequenceTimeline.track_type == track_type,
                        SequenceTimeline.track_number == track_number
                    )
                )
            )
        
        # Remove track metadata
        sequence = await db.get(ProjectContainer, sequence_id)
        if sequence and sequence.metadata and "tracks" in sequence.metadata:
            track_key = f"{track_type}_{track_number}"
            if track_key in sequence.metadata["tracks"]:
                del sequence.metadata["tracks"][track_key]
                sequence.metadata = dict(sequence.metadata)
        
        # Renumber higher tracks
        if sequence and sequence.metadata and "tracks" in sequence.metadata:
            # Get all tracks of the same type
            tracks_to_renumber = []
            for key in list(sequence.metadata["tracks"].keys()):
                if key.startswith(f"{track_type}_"):
                    t_num = int(key.split("_", 1)[1])
                    if t_num > track_number:
                        tracks_to_renumber.append((key, t_num))
            
            # Renumber tracks
            for old_key, old_num in sorted(tracks_to_renumber, key=lambda x: x[1]):
                new_num = old_num - 1
                new_key = f"{track_type}_{new_num}"
                
                # Update metadata
                sequence.metadata["tracks"][new_key] = sequence.metadata["tracks"].pop(old_key)
                
                # Update clips
                await db.execute(
                    update(SequenceTimeline)
                    .where(
                        and_(
                            SequenceTimeline.sequence_id == sequence_id,
                            SequenceTimeline.track_type == track_type,
                            SequenceTimeline.track_number == old_num
                        )
                    )
                    .values(track_number=new_num)
                )
        
        await db.commit()
        
        return {
            "detail": f"Track deleted successfully",
            "clips_deleted": clip_count if force else 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting track: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete track"
        )


@router.put("/{sequence_id}/tracks/reorder")
async def reorder_tracks(
    sequence_id: UUID,
    reorder_data: TrackReorder,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Reorder tracks within a track type"""
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
        
        # Get sequence
        sequence = await db.get(ProjectContainer, sequence_id)
        if not sequence:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sequence not found"
            )
        
        # Get all existing track numbers for this type
        existing_tracks = set()
        if sequence.metadata and "tracks" in sequence.metadata:
            for key in sequence.metadata["tracks"]:
                if key.startswith(f"{reorder_data.track_type}_"):
                    existing_tracks.add(int(key.split("_", 1)[1]))
        
        # Also get tracks with clips
        clips_result = await db.execute(
            select(SequenceTimeline.track_number).where(
                and_(
                    SequenceTimeline.sequence_id == sequence_id,
                    SequenceTimeline.track_type == reorder_data.track_type
                )
            ).distinct()
        )
        for row in clips_result:
            existing_tracks.add(row.track_number)
        
        # Validate new order
        if set(reorder_data.new_order) != existing_tracks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New order must contain all existing track numbers"
            )
        
        # Create mapping from old to new positions
        track_mapping = {
            old_num: new_idx
            for new_idx, old_num in enumerate(reorder_data.new_order)
        }
        
        # Temporarily move clips to negative track numbers to avoid conflicts
        for old_num in existing_tracks:
            await db.execute(
                update(SequenceTimeline)
                .where(
                    and_(
                        SequenceTimeline.sequence_id == sequence_id,
                        SequenceTimeline.track_type == reorder_data.track_type,
                        SequenceTimeline.track_number == old_num
                    )
                )
                .values(track_number=-old_num - 1)
            )
        
        # Move clips to final positions
        for old_num, new_num in track_mapping.items():
            await db.execute(
                update(SequenceTimeline)
                .where(
                    and_(
                        SequenceTimeline.sequence_id == sequence_id,
                        SequenceTimeline.track_type == reorder_data.track_type,
                        SequenceTimeline.track_number == -old_num - 1
                    )
                )
                .values(track_number=new_num)
            )
        
        # Update track metadata
        if sequence.metadata and "tracks" in sequence.metadata:
            old_tracks = {}
            # Save old track metadata
            for key in list(sequence.metadata["tracks"].keys()):
                if key.startswith(f"{reorder_data.track_type}_"):
                    old_num = int(key.split("_", 1)[1])
                    old_tracks[old_num] = sequence.metadata["tracks"].pop(key)
            
            # Restore with new numbers
            for old_num, new_num in track_mapping.items():
                if old_num in old_tracks:
                    new_key = f"{reorder_data.track_type}_{new_num}"
                    sequence.metadata["tracks"][new_key] = old_tracks[old_num]
            
            sequence.metadata = dict(sequence.metadata)
        
        await db.commit()
        
        return {
            "detail": "Tracks reordered successfully",
            "new_order": reorder_data.new_order
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reordering tracks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reorder tracks"
        )


@router.post("/{sequence_id}/tracks/move-clips")
async def move_clips_between_tracks(
    sequence_id: UUID,
    source_track_type: str,
    source_track_number: int,
    target_track_type: str,
    target_track_number: int,
    clip_ids: List[UUID] = Body(..., description="List of clip IDs to move"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Move clips from one track to another"""
    try:
        # Validate track types
        valid_types = ["video", "audio", "subtitle"]
        if source_track_type not in valid_types or target_track_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid track type"
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
        
        # Get clips to move
        clips_query = select(SequenceTimeline).where(
            and_(
                SequenceTimeline.sequence_id == sequence_id,
                SequenceTimeline.track_type == source_track_type,
                SequenceTimeline.track_number == source_track_number,
                SequenceTimeline.id.in_(clip_ids)
            )
        )
        result = await db.execute(clips_query)
        clips_to_move = result.scalars().all()
        
        if len(clips_to_move) != len(clip_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Some clips not found on the source track"
            )
        
        # Check for overlaps on target track
        for clip in clips_to_move:
            overlap_query = select(SequenceTimeline).where(
                and_(
                    SequenceTimeline.sequence_id == sequence_id,
                    SequenceTimeline.track_type == target_track_type,
                    SequenceTimeline.track_number == target_track_number,
                    SequenceTimeline.start_time < clip.end_time,
                    SequenceTimeline.end_time > clip.start_time,
                    SequenceTimeline.id != clip.id
                )
            )
            overlap_result = await db.execute(overlap_query)
            if overlap_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Clip {clip.id} would overlap with existing clips on target track"
                )
        
        # Move clips
        moved_count = 0
        for clip in clips_to_move:
            clip.track_type = target_track_type
            clip.track_number = target_track_number
            moved_count += 1
        
        await db.commit()
        
        return {
            "detail": f"Moved {moved_count} clips successfully",
            "moved_clips": clip_ids
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error moving clips between tracks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to move clips"
        )