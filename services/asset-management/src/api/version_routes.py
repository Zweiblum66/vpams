"""
Timeline versioning API routes

Provides version control for sequence timelines.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
import json

from src.db.base import get_db
from src.db.models import (
    ProjectContainer, SequenceTimeline, ShotItem, User,
    ContainerType, AssetStatus
)
from src.api.dependencies import get_current_user
from src.models.schemas import (
    TimelineVersionResponse, TimelineVersionCreate,
    TimelineVersionUpdate, TimelineVersionRestore,
    TimelineVersionCompare
)


router = APIRouter(
    prefix="/api/v1/timeline-versions",
    tags=["timeline-versions"]
)


class TimelineVersion:
    """Timeline version data model"""
    def __init__(self, data: dict):
        self.id = data.get("id", str(uuid4()))
        self.sequence_id = data.get("sequence_id")
        self.version_number = data.get("version_number", 1)
        self.name = data.get("name", "")
        self.description = data.get("description", "")
        self.created_by = data.get("created_by")
        self.created_at = data.get("created_at", datetime.utcnow())
        self.timeline_data = data.get("timeline_data", {})
        self.metadata = data.get("metadata", {})
        self.is_auto_save = data.get("is_auto_save", False)
        self.parent_version_id = data.get("parent_version_id")


async def get_sequence_or_404(
    sequence_id: UUID,
    db: AsyncSession,
    user: dict
) -> ProjectContainer:
    """Get sequence container or raise 404"""
    query = select(ProjectContainer).where(
        and_(
            ProjectContainer.id == sequence_id,
            ProjectContainer.container_type == ContainerType.SEQUENCE
        )
    )
    
    sequence = await db.scalar(query)
    if not sequence:
        raise HTTPException(
            status_code=404,
            detail="Sequence not found"
        )
    
    # Check permissions
    if str(sequence.owner_id) != user["user_id"] and not user.get("is_admin"):
        # Check if user has edit permission through sharing
        has_permission = False
        if hasattr(sequence, "shared_with"):
            for share in sequence.shared_with:
                if share.user_id == UUID(user["user_id"]) and share.permission in ["edit", "admin"]:
                    has_permission = True
                    break
        
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to manage versions for this sequence"
            )
    
    return sequence


async def get_timeline_items(
    sequence_id: UUID,
    db: AsyncSession
) -> List[Dict[str, Any]]:
    """Get all timeline items for a sequence"""
    query = select(SequenceTimeline).where(
        SequenceTimeline.sequence_id == sequence_id
    ).options(
        selectinload(SequenceTimeline.clip)
    ).order_by(
        SequenceTimeline.track_type,
        SequenceTimeline.track_number,
        SequenceTimeline.start_time
    )
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    # Convert to serializable format
    timeline_data = []
    for item in items:
        item_data = {
            "id": str(item.id),
            "clip_id": str(item.clip_id),
            "track_type": item.track_type,
            "track_number": item.track_number,
            "start_time": item.start_time,
            "end_time": item.end_time,
            "speed": item.speed,
            "is_enabled": item.is_enabled,
            "is_locked": item.is_locked,
            "transition_in": item.transition_in,
            "transition_out": item.transition_out,
            "effects": item.effects,
            "metadata": item.metadata
        }
        timeline_data.append(item_data)
    
    return timeline_data


async def save_version(
    sequence: ProjectContainer,
    version_data: TimelineVersion,
    db: AsyncSession
) -> TimelineVersion:
    """Save a timeline version"""
    # Get current timeline state
    timeline_data = await get_timeline_items(sequence.id, db)
    version_data.timeline_data = {"items": timeline_data}
    
    # Store version in sequence metadata
    if not sequence.metadata:
        sequence.metadata = {}
    
    if "versions" not in sequence.metadata:
        sequence.metadata["versions"] = []
    
    # Convert version to dict
    version_dict = {
        "id": version_data.id,
        "sequence_id": str(version_data.sequence_id),
        "version_number": version_data.version_number,
        "name": version_data.name,
        "description": version_data.description,
        "created_by": str(version_data.created_by),
        "created_at": version_data.created_at.isoformat(),
        "timeline_data": version_data.timeline_data,
        "metadata": version_data.metadata,
        "is_auto_save": version_data.is_auto_save,
        "parent_version_id": version_data.parent_version_id
    }
    
    sequence.metadata["versions"].append(version_dict)
    sequence.metadata["current_version_id"] = version_data.id
    
    await db.commit()
    return version_data


@router.post("/{sequence_id}/save", response_model=TimelineVersionResponse)
async def save_timeline_version(
    sequence_id: UUID,
    version_data: TimelineVersionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Save a new version of the timeline"""
    sequence = await get_sequence_or_404(sequence_id, db, current_user)
    
    # Get next version number
    versions = sequence.metadata.get("versions", []) if sequence.metadata else []
    next_version = len(versions) + 1
    
    # Create version
    version = TimelineVersion({
        "sequence_id": sequence_id,
        "version_number": next_version,
        "name": version_data.name or f"Version {next_version}",
        "description": version_data.description,
        "created_by": UUID(current_user["user_id"]),
        "metadata": version_data.metadata or {},
        "is_auto_save": version_data.is_auto_save,
        "parent_version_id": sequence.metadata.get("current_version_id") if sequence.metadata else None
    })
    
    saved_version = await save_version(sequence, version, db)
    
    return TimelineVersionResponse(
        id=saved_version.id,
        sequence_id=str(saved_version.sequence_id),
        version_number=saved_version.version_number,
        name=saved_version.name,
        description=saved_version.description,
        created_by=str(saved_version.created_by),
        created_at=saved_version.created_at,
        is_auto_save=saved_version.is_auto_save,
        parent_version_id=saved_version.parent_version_id,
        timeline_item_count=len(saved_version.timeline_data.get("items", [])),
        metadata=saved_version.metadata
    )


@router.get("/{sequence_id}/list", response_model=List[TimelineVersionResponse])
async def list_timeline_versions(
    sequence_id: UUID,
    include_auto_saves: bool = Query(False, description="Include auto-saved versions"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List all versions of a timeline"""
    sequence = await get_sequence_or_404(sequence_id, db, current_user)
    
    versions = sequence.metadata.get("versions", []) if sequence.metadata else []
    
    # Filter out auto-saves if requested
    if not include_auto_saves:
        versions = [v for v in versions if not v.get("is_auto_save", False)]
    
    # Sort by version number descending
    versions.sort(key=lambda v: v.get("version_number", 0), reverse=True)
    
    # Apply pagination
    paginated_versions = versions[offset:offset + limit]
    
    # Convert to response models
    response_versions = []
    for v in paginated_versions:
        response_versions.append(TimelineVersionResponse(
            id=v["id"],
            sequence_id=v["sequence_id"],
            version_number=v["version_number"],
            name=v["name"],
            description=v.get("description", ""),
            created_by=v["created_by"],
            created_at=datetime.fromisoformat(v["created_at"]),
            is_auto_save=v.get("is_auto_save", False),
            parent_version_id=v.get("parent_version_id"),
            timeline_item_count=len(v.get("timeline_data", {}).get("items", [])),
            metadata=v.get("metadata", {})
        ))
    
    return response_versions


@router.get("/{sequence_id}/version/{version_id}", response_model=Dict[str, Any])
async def get_timeline_version(
    sequence_id: UUID,
    version_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get a specific version of the timeline"""
    sequence = await get_sequence_or_404(sequence_id, db, current_user)
    
    versions = sequence.metadata.get("versions", []) if sequence.metadata else []
    version = next((v for v in versions if v["id"] == version_id), None)
    
    if not version:
        raise HTTPException(
            status_code=404,
            detail="Version not found"
        )
    
    return {
        "version": TimelineVersionResponse(
            id=version["id"],
            sequence_id=version["sequence_id"],
            version_number=version["version_number"],
            name=version["name"],
            description=version.get("description", ""),
            created_by=version["created_by"],
            created_at=datetime.fromisoformat(version["created_at"]),
            is_auto_save=version.get("is_auto_save", False),
            parent_version_id=version.get("parent_version_id"),
            timeline_item_count=len(version.get("timeline_data", {}).get("items", [])),
            metadata=version.get("metadata", {})
        ),
        "timeline_data": version.get("timeline_data", {})
    }


@router.post("/{sequence_id}/restore/{version_id}")
async def restore_timeline_version(
    sequence_id: UUID,
    version_id: str,
    restore_data: TimelineVersionRestore,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Restore a timeline to a specific version"""
    sequence = await get_sequence_or_404(sequence_id, db, current_user)
    
    versions = sequence.metadata.get("versions", []) if sequence.metadata else []
    version = next((v for v in versions if v["id"] == version_id), None)
    
    if not version:
        raise HTTPException(
            status_code=404,
            detail="Version not found"
        )
    
    # Save current state as a new version if requested
    if restore_data.save_current:
        current_version = TimelineVersion({
            "sequence_id": sequence_id,
            "version_number": len(versions) + 1,
            "name": f"Before restore to {version['name']}",
            "description": f"Auto-saved before restoring to version {version['version_number']}",
            "created_by": UUID(current_user["user_id"]),
            "metadata": {"auto_save_reason": "before_restore"},
            "is_auto_save": True,
            "parent_version_id": sequence.metadata.get("current_version_id") if sequence.metadata else None
        })
        await save_version(sequence, current_version, db)
    
    # Delete existing timeline items
    from sqlalchemy import delete
    await db.execute(
        delete(SequenceTimeline).where(
            SequenceTimeline.sequence_id == sequence_id
        )
    )
    
    # Restore timeline items from version
    timeline_items = version.get("timeline_data", {}).get("items", [])
    for item_data in timeline_items:
        item = SequenceTimeline(
            id=UUID(item_data["id"]) if restore_data.preserve_ids else uuid4(),
            sequence_id=sequence_id,
            clip_id=UUID(item_data["clip_id"]),
            track_type=item_data["track_type"],
            track_number=item_data["track_number"],
            start_time=item_data["start_time"],
            end_time=item_data["end_time"],
            speed=item_data.get("speed", 1.0),
            is_enabled=item_data.get("is_enabled", True),
            is_locked=item_data.get("is_locked", False),
            transition_in=item_data.get("transition_in"),
            transition_out=item_data.get("transition_out"),
            effects=item_data.get("effects"),
            metadata=item_data.get("metadata")
        )
        db.add(item)
    
    # Update current version
    sequence.metadata["current_version_id"] = version_id
    sequence.metadata["last_restored_at"] = datetime.utcnow().isoformat()
    sequence.metadata["last_restored_by"] = current_user["user_id"]
    
    await db.commit()
    
    return {
        "message": f"Timeline restored to version {version['version_number']}",
        "version_id": version_id,
        "items_restored": len(timeline_items)
    }


@router.patch("/{sequence_id}/version/{version_id}", response_model=TimelineVersionResponse)
async def update_timeline_version(
    sequence_id: UUID,
    version_id: str,
    update_data: TimelineVersionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update version metadata (name, description)"""
    sequence = await get_sequence_or_404(sequence_id, db, current_user)
    
    versions = sequence.metadata.get("versions", []) if sequence.metadata else []
    version_index = next((i for i, v in enumerate(versions) if v["id"] == version_id), None)
    
    if version_index is None:
        raise HTTPException(
            status_code=404,
            detail="Version not found"
        )
    
    version = versions[version_index]
    
    # Update fields
    if update_data.name is not None:
        version["name"] = update_data.name
    if update_data.description is not None:
        version["description"] = update_data.description
    if update_data.metadata is not None:
        version["metadata"].update(update_data.metadata)
    
    # Save back to database
    sequence.metadata["versions"][version_index] = version
    await db.commit()
    
    return TimelineVersionResponse(
        id=version["id"],
        sequence_id=version["sequence_id"],
        version_number=version["version_number"],
        name=version["name"],
        description=version.get("description", ""),
        created_by=version["created_by"],
        created_at=datetime.fromisoformat(version["created_at"]),
        is_auto_save=version.get("is_auto_save", False),
        parent_version_id=version.get("parent_version_id"),
        timeline_item_count=len(version.get("timeline_data", {}).get("items", [])),
        metadata=version.get("metadata", {})
    )


@router.delete("/{sequence_id}/version/{version_id}")
async def delete_timeline_version(
    sequence_id: UUID,
    version_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete a timeline version"""
    sequence = await get_sequence_or_404(sequence_id, db, current_user)
    
    versions = sequence.metadata.get("versions", []) if sequence.metadata else []
    version_index = next((i for i, v in enumerate(versions) if v["id"] == version_id), None)
    
    if version_index is None:
        raise HTTPException(
            status_code=404,
            detail="Version not found"
        )
    
    # Don't delete if it's the current version
    if sequence.metadata.get("current_version_id") == version_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete the current version"
        )
    
    # Remove version
    deleted_version = versions.pop(version_index)
    sequence.metadata["versions"] = versions
    
    await db.commit()
    
    return {
        "message": f"Version '{deleted_version['name']}' deleted",
        "version_id": version_id
    }


@router.post("/{sequence_id}/compare", response_model=Dict[str, Any])
async def compare_timeline_versions(
    sequence_id: UUID,
    compare_data: TimelineVersionCompare,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Compare two timeline versions"""
    sequence = await get_sequence_or_404(sequence_id, db, current_user)
    
    versions = sequence.metadata.get("versions", []) if sequence.metadata else []
    
    # Handle special case for current timeline
    if compare_data.version1_id == "current":
        version1_items = await get_timeline_items(sequence_id, db)
    else:
        version1 = next((v for v in versions if v["id"] == compare_data.version1_id), None)
        if not version1:
            raise HTTPException(status_code=404, detail="Version 1 not found")
        version1_items = version1.get("timeline_data", {}).get("items", [])
    
    if compare_data.version2_id == "current":
        version2_items = await get_timeline_items(sequence_id, db)
    else:
        version2 = next((v for v in versions if v["id"] == compare_data.version2_id), None)
        if not version2:
            raise HTTPException(status_code=404, detail="Version 2 not found")
        version2_items = version2.get("timeline_data", {}).get("items", [])
    
    # Compare versions
    version1_ids = {item.get("id") if isinstance(item, dict) else str(item.id) for item in version1_items}
    version2_ids = {item.get("id") if isinstance(item, dict) else str(item.id) for item in version2_items}
    
    added_items = version2_ids - version1_ids
    removed_items = version1_ids - version2_ids
    common_items = version1_ids & version2_ids
    
    # Check for modifications in common items
    modified_items = []
    for item_id in common_items:
        item1 = next((i for i in version1_items if (i.get("id") if isinstance(i, dict) else str(i.id)) == item_id), None)
        item2 = next((i for i in version2_items if (i.get("id") if isinstance(i, dict) else str(i.id)) == item_id), None)
        
        if item1 and item2:
            # Convert to dict if needed
            if not isinstance(item1, dict):
                item1 = {
                    "start_time": item1.start_time,
                    "end_time": item1.end_time,
                    "track_number": item1.track_number,
                    "track_type": item1.track_type
                }
            if not isinstance(item2, dict):
                item2 = {
                    "start_time": item2.start_time,
                    "end_time": item2.end_time,
                    "track_number": item2.track_number,
                    "track_type": item2.track_type
                }
            
            # Check for differences
            if (item1["start_time"] != item2["start_time"] or
                item1["end_time"] != item2["end_time"] or
                item1["track_number"] != item2["track_number"] or
                item1["track_type"] != item2["track_type"]):
                modified_items.append(item_id)
    
    return {
        "comparison": {
            "version1_id": compare_data.version1_id,
            "version2_id": compare_data.version2_id,
            "total_items_version1": len(version1_items),
            "total_items_version2": len(version2_items),
            "added_items": list(added_items),
            "removed_items": list(removed_items),
            "modified_items": modified_items,
            "unchanged_items": len(common_items) - len(modified_items)
        }
    }


@router.post("/{sequence_id}/auto-save")
async def auto_save_timeline(
    sequence_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create an auto-save version of the timeline"""
    sequence = await get_sequence_or_404(sequence_id, db, current_user)
    
    # Get existing versions
    versions = sequence.metadata.get("versions", []) if sequence.metadata else []
    
    # Check if we need to create an auto-save
    # (e.g., if timeline has changed since last version)
    current_timeline = await get_timeline_items(sequence_id, db)
    
    # Get last version's timeline
    last_version = None
    if versions:
        last_version = max(versions, key=lambda v: v.get("version_number", 0))
        last_timeline = last_version.get("timeline_data", {}).get("items", [])
        
        # Compare current with last version
        if json.dumps(current_timeline, sort_keys=True) == json.dumps(last_timeline, sort_keys=True):
            return {
                "message": "No changes detected, auto-save skipped",
                "last_version_id": last_version["id"]
            }
    
    # Create auto-save version
    auto_save_version = TimelineVersion({
        "sequence_id": sequence_id,
        "version_number": len(versions) + 1,
        "name": f"Auto-save {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
        "description": "Automatic save",
        "created_by": UUID(current_user["user_id"]),
        "metadata": {"auto_save_timestamp": datetime.utcnow().isoformat()},
        "is_auto_save": True,
        "parent_version_id": last_version["id"] if last_version else None
    })
    
    saved_version = await save_version(sequence, auto_save_version, db)
    
    # Clean up old auto-saves (keep only last 5)
    auto_saves = [v for v in sequence.metadata["versions"] if v.get("is_auto_save", False)]
    if len(auto_saves) > 5:
        auto_saves.sort(key=lambda v: v.get("version_number", 0))
        to_remove = auto_saves[:-5]
        
        # Remove old auto-saves
        sequence.metadata["versions"] = [
            v for v in sequence.metadata["versions"]
            if not v.get("is_auto_save", False) or v["id"] not in [r["id"] for r in to_remove]
        ]
        await db.commit()
    
    return {
        "message": "Auto-save created",
        "version_id": saved_version.id,
        "version_number": saved_version.version_number
    }