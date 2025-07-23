"""
Transition API routes

This module provides API endpoints for managing transitions in sequence timelines.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from pydantic import BaseModel, Field, validator

from ..core.dependencies import get_db, get_current_user
from ..core.logging import get_logger
from ..db.models import (
    SequenceTimeline,
    ProjectContainer,
    ContainerType
)
from ..services.project_service import ProjectService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/transitions", tags=["transitions"])


# Transition schemas
class TransitionType(BaseModel):
    """Available transition type"""
    id: str
    name: str
    category: str
    description: str
    parameters: Dict[str, Any]
    supports_duration: bool = True
    min_duration: int = 0
    max_duration: Optional[int] = None
    default_duration: int = 1000


class TransitionCreate(BaseModel):
    """Schema for creating a transition"""
    timeline_item_id: UUID
    transition_type: str = Field(..., description="Type of transition (fade, dissolve, wipe, etc.)")
    position: str = Field(..., pattern="^(in|out)$", description="Transition position (in or out)")
    duration: int = Field(1000, ge=0, description="Duration in milliseconds")
    parameters: Optional[Dict[str, Any]] = None
    
    @validator("transition_type")
    def validate_transition_type(cls, v):
        valid_types = ["fade", "dissolve", "wipe", "slide", "push", "zoom", "blur", "flash", "dip"]
        if v not in valid_types:
            raise ValueError(f"Invalid transition type. Must be one of: {', '.join(valid_types)}")
        return v


class TransitionUpdate(BaseModel):
    """Schema for updating a transition"""
    duration: Optional[int] = Field(None, ge=0)
    parameters: Optional[Dict[str, Any]] = None


class TransitionResponse(BaseModel):
    """Transition response schema"""
    timeline_item_id: UUID
    position: str
    type: str
    duration: int
    parameters: Dict[str, Any]


# Predefined transition types
TRANSITION_TYPES = {
    "fade": TransitionType(
        id="fade",
        name="Fade",
        category="basic",
        description="Fade to/from black",
        parameters={
            "color": {"type": "color", "default": "#000000", "description": "Fade color"}
        },
        default_duration=1000
    ),
    "dissolve": TransitionType(
        id="dissolve",
        name="Cross Dissolve",
        category="basic",
        description="Dissolve between clips",
        parameters={
            "curve": {"type": "string", "default": "linear", "options": ["linear", "ease-in", "ease-out", "ease-in-out"]}
        },
        default_duration=1000
    ),
    "wipe": TransitionType(
        id="wipe",
        name="Wipe",
        category="geometric",
        description="Wipe transition with direction",
        parameters={
            "direction": {"type": "string", "default": "left", "options": ["left", "right", "up", "down", "diagonal"]},
            "angle": {"type": "number", "default": 0, "min": 0, "max": 360},
            "feather": {"type": "number", "default": 0, "min": 0, "max": 100}
        },
        default_duration=1000
    ),
    "slide": TransitionType(
        id="slide",
        name="Slide",
        category="motion",
        description="Slide in/out transition",
        parameters={
            "direction": {"type": "string", "default": "left", "options": ["left", "right", "up", "down"]},
            "overlap": {"type": "boolean", "default": False}
        },
        default_duration=500
    ),
    "push": TransitionType(
        id="push",
        name="Push",
        category="motion",
        description="Push transition",
        parameters={
            "direction": {"type": "string", "default": "left", "options": ["left", "right", "up", "down"]}
        },
        default_duration=500
    ),
    "zoom": TransitionType(
        id="zoom",
        name="Zoom",
        category="scale",
        description="Zoom in/out transition",
        parameters={
            "center_x": {"type": "number", "default": 0.5, "min": 0, "max": 1},
            "center_y": {"type": "number", "default": 0.5, "min": 0, "max": 1},
            "zoom_factor": {"type": "number", "default": 2.0, "min": 0.1, "max": 10}
        },
        default_duration=1000
    ),
    "blur": TransitionType(
        id="blur",
        name="Blur",
        category="filter",
        description="Blur transition",
        parameters={
            "intensity": {"type": "number", "default": 20, "min": 0, "max": 100}
        },
        default_duration=500
    ),
    "flash": TransitionType(
        id="flash",
        name="Flash",
        category="special",
        description="Flash/dip to white",
        parameters={
            "color": {"type": "color", "default": "#FFFFFF"},
            "peak_position": {"type": "number", "default": 0.5, "min": 0, "max": 1}
        },
        default_duration=250,
        min_duration=100,
        max_duration=1000
    ),
    "dip": TransitionType(
        id="dip",
        name="Dip to Color",
        category="special",
        description="Dip to custom color",
        parameters={
            "color": {"type": "color", "default": "#000000"},
            "hold_duration": {"type": "number", "default": 0, "min": 0, "max": 1000}
        },
        default_duration=1000
    )
}


@router.get("/types", response_model=List[TransitionType])
async def get_transition_types(
    category: Optional[str] = None
):
    """Get available transition types"""
    transitions = list(TRANSITION_TYPES.values())
    
    if category:
        transitions = [t for t in transitions if t.category == category]
    
    return transitions


@router.get("/types/{transition_id}", response_model=TransitionType)
async def get_transition_type(
    transition_id: str
):
    """Get details of a specific transition type"""
    if transition_id not in TRANSITION_TYPES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transition type not found"
        )
    
    return TRANSITION_TYPES[transition_id]


@router.post("/{sequence_id}/add", response_model=TransitionResponse)
async def add_transition(
    sequence_id: UUID,
    transition: TransitionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Add a transition to a timeline item"""
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
        
        # Get timeline item
        timeline_item = await db.get(SequenceTimeline, transition.timeline_item_id)
        if not timeline_item or timeline_item.sequence_id != sequence_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Timeline item not found in this sequence"
            )
        
        # Check if item is locked
        if timeline_item.is_locked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot add transition to locked timeline item"
            )
        
        # Get transition type info
        transition_type = TRANSITION_TYPES.get(transition.transition_type)
        if not transition_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid transition type"
            )
        
        # Validate duration
        if transition.duration < transition_type.min_duration:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Duration must be at least {transition_type.min_duration}ms"
            )
        
        if transition_type.max_duration and transition.duration > transition_type.max_duration:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Duration cannot exceed {transition_type.max_duration}ms"
            )
        
        # Check for overlap with adjacent clips
        if transition.position == "out":
            # Check next clip on same track
            next_clip_query = select(SequenceTimeline).where(
                and_(
                    SequenceTimeline.sequence_id == sequence_id,
                    SequenceTimeline.track_type == timeline_item.track_type,
                    SequenceTimeline.track_number == timeline_item.track_number,
                    SequenceTimeline.start_time >= timeline_item.end_time
                )
            ).order_by(SequenceTimeline.start_time).limit(1)
            
            result = await db.execute(next_clip_query)
            next_clip = result.scalar_one_or_none()
            
            if next_clip:
                gap = next_clip.start_time - timeline_item.end_time
                if gap < transition.duration:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Not enough space for transition. Gap is {gap}ms, need {transition.duration}ms"
                    )
        
        elif transition.position == "in":
            # Check previous clip on same track
            prev_clip_query = select(SequenceTimeline).where(
                and_(
                    SequenceTimeline.sequence_id == sequence_id,
                    SequenceTimeline.track_type == timeline_item.track_type,
                    SequenceTimeline.track_number == timeline_item.track_number,
                    SequenceTimeline.end_time <= timeline_item.start_time
                )
            ).order_by(SequenceTimeline.end_time.desc()).limit(1)
            
            result = await db.execute(prev_clip_query)
            prev_clip = result.scalar_one_or_none()
            
            if prev_clip:
                gap = timeline_item.start_time - prev_clip.end_time
                if gap < transition.duration:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Not enough space for transition. Gap is {gap}ms, need {transition.duration}ms"
                    )
        
        # Prepare transition data
        transition_data = {
            "type": transition.transition_type,
            "duration": transition.duration,
            "parameters": transition.parameters or {}
        }
        
        # Add default parameters if not provided
        for param_name, param_info in transition_type.parameters.items():
            if param_name not in transition_data["parameters"]:
                transition_data["parameters"][param_name] = param_info.get("default")
        
        # Update timeline item
        if transition.position == "in":
            timeline_item.transition_in = transition_data
        else:
            timeline_item.transition_out = transition_data
        
        await db.commit()
        await db.refresh(timeline_item)
        
        # Return transition info
        return TransitionResponse(
            timeline_item_id=timeline_item.id,
            position=transition.position,
            type=transition_data["type"],
            duration=transition_data["duration"],
            parameters=transition_data["parameters"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding transition: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add transition"
        )


@router.put("/{sequence_id}/update/{timeline_item_id}/{position}", response_model=TransitionResponse)
async def update_transition(
    sequence_id: UUID,
    timeline_item_id: UUID,
    position: str,
    update_data: TransitionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update an existing transition"""
    try:
        # Validate position
        if position not in ["in", "out"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Position must be 'in' or 'out'"
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
        
        # Get timeline item
        timeline_item = await db.get(SequenceTimeline, timeline_item_id)
        if not timeline_item or timeline_item.sequence_id != sequence_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Timeline item not found in this sequence"
            )
        
        # Check if item is locked
        if timeline_item.is_locked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update transition on locked timeline item"
            )
        
        # Get existing transition
        existing_transition = timeline_item.transition_in if position == "in" else timeline_item.transition_out
        if not existing_transition:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No {position} transition found on this timeline item"
            )
        
        # Update transition data
        if update_data.duration is not None:
            existing_transition["duration"] = update_data.duration
        
        if update_data.parameters is not None:
            existing_transition["parameters"].update(update_data.parameters)
        
        # Update timeline item
        if position == "in":
            timeline_item.transition_in = existing_transition
        else:
            timeline_item.transition_out = existing_transition
        
        await db.commit()
        await db.refresh(timeline_item)
        
        # Return updated transition
        return TransitionResponse(
            timeline_item_id=timeline_item.id,
            position=position,
            type=existing_transition["type"],
            duration=existing_transition["duration"],
            parameters=existing_transition["parameters"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating transition: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update transition"
        )


@router.delete("/{sequence_id}/remove/{timeline_item_id}/{position}")
async def remove_transition(
    sequence_id: UUID,
    timeline_item_id: UUID,
    position: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Remove a transition from a timeline item"""
    try:
        # Validate position
        if position not in ["in", "out"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Position must be 'in' or 'out'"
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
        
        # Get timeline item
        timeline_item = await db.get(SequenceTimeline, timeline_item_id)
        if not timeline_item or timeline_item.sequence_id != sequence_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Timeline item not found in this sequence"
            )
        
        # Check if item is locked
        if timeline_item.is_locked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove transition from locked timeline item"
            )
        
        # Remove transition
        if position == "in":
            timeline_item.transition_in = None
        else:
            timeline_item.transition_out = None
        
        await db.commit()
        
        return {"detail": f"Transition removed successfully from {position} position"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing transition: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove transition"
        )


@router.get("/{sequence_id}/transitions", response_model=List[Dict[str, Any]])
async def get_sequence_transitions(
    sequence_id: UUID,
    track_type: Optional[str] = None,
    track_number: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all transitions in a sequence"""
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
            and_(
                SequenceTimeline.sequence_id == sequence_id,
                or_(
                    SequenceTimeline.transition_in.isnot(None),
                    SequenceTimeline.transition_out.isnot(None)
                )
            )
        )
        
        # Apply filters
        if track_type:
            query = query.where(SequenceTimeline.track_type == track_type)
        if track_number is not None:
            query = query.where(SequenceTimeline.track_number == track_number)
        
        # Order by timeline position
        query = query.order_by(
            SequenceTimeline.track_number,
            SequenceTimeline.start_time
        )
        
        result = await db.execute(query)
        timeline_items = result.scalars().all()
        
        # Build response
        transitions = []
        for item in timeline_items:
            if item.transition_in:
                transitions.append({
                    "timeline_item_id": str(item.id),
                    "track_type": item.track_type,
                    "track_number": item.track_number,
                    "timeline_position": item.start_time,
                    "position": "in",
                    "type": item.transition_in["type"],
                    "duration": item.transition_in["duration"],
                    "parameters": item.transition_in["parameters"]
                })
            
            if item.transition_out:
                transitions.append({
                    "timeline_item_id": str(item.id),
                    "track_type": item.track_type,
                    "track_number": item.track_number,
                    "timeline_position": item.end_time,
                    "position": "out",
                    "type": item.transition_out["type"],
                    "duration": item.transition_out["duration"],
                    "parameters": item.transition_out["parameters"]
                })
        
        return transitions
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting sequence transitions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get sequence transitions"
        )


@router.post("/{sequence_id}/apply-preset")
async def apply_transition_preset(
    sequence_id: UUID,
    preset_name: str,
    track_type: Optional[str] = None,
    track_number: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Apply a transition preset to multiple clips"""
    try:
        # Define presets
        presets = {
            "fade_all": {
                "description": "Add fade in/out to all clips",
                "in_transition": {"type": "fade", "duration": 500},
                "out_transition": {"type": "fade", "duration": 500}
            },
            "dissolve_between": {
                "description": "Add dissolve between adjacent clips",
                "out_transition": {"type": "dissolve", "duration": 1000}
            },
            "quick_cuts": {
                "description": "Quick cuts with flash transitions",
                "out_transition": {"type": "flash", "duration": 100}
            }
        }
        
        if preset_name not in presets:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown preset. Available presets: {', '.join(presets.keys())}"
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
        
        # Get timeline items
        query = select(SequenceTimeline).where(
            and_(
                SequenceTimeline.sequence_id == sequence_id,
                SequenceTimeline.is_locked == False
            )
        )
        
        if track_type:
            query = query.where(SequenceTimeline.track_type == track_type)
        if track_number is not None:
            query = query.where(SequenceTimeline.track_number == track_number)
        
        query = query.order_by(
            SequenceTimeline.track_number,
            SequenceTimeline.start_time
        )
        
        result = await db.execute(query)
        timeline_items = result.scalars().all()
        
        if not timeline_items:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No unlocked timeline items found"
            )
        
        # Apply preset
        preset = presets[preset_name]
        transitions_added = 0
        
        for i, item in enumerate(timeline_items):
            # Apply in transition
            if "in_transition" in preset and (i == 0 or timeline_items[i-1].track_number != item.track_number):
                transition_data = preset["in_transition"].copy()
                transition_type = TRANSITION_TYPES[transition_data["type"]]
                
                # Add default parameters
                transition_data["parameters"] = {}
                for param_name, param_info in transition_type.parameters.items():
                    transition_data["parameters"][param_name] = param_info.get("default")
                
                item.transition_in = transition_data
                transitions_added += 1
            
            # Apply out transition
            if "out_transition" in preset:
                # Check if there's a next clip on the same track
                has_next = (i < len(timeline_items) - 1 and 
                           timeline_items[i + 1].track_number == item.track_number and
                           timeline_items[i + 1].track_type == item.track_type)
                
                if has_next or preset_name == "fade_all":
                    transition_data = preset["out_transition"].copy()
                    transition_type = TRANSITION_TYPES[transition_data["type"]]
                    
                    # Add default parameters
                    transition_data["parameters"] = {}
                    for param_name, param_info in transition_type.parameters.items():
                        transition_data["parameters"][param_name] = param_info.get("default")
                    
                    item.transition_out = transition_data
                    transitions_added += 1
        
        await db.commit()
        
        return {
            "detail": f"Applied '{preset_name}' preset successfully",
            "transitions_added": transitions_added,
            "clips_affected": len(timeline_items)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying transition preset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to apply transition preset"
        )