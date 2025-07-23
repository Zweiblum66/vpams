"""
Commenting system API routes

Provides commenting functionality for assets and containers.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_, or_, func
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any, Literal
from uuid import UUID, uuid4
from datetime import datetime
import structlog

from src.db.base import get_db
from src.db.models import (
    User, Asset, ProjectContainer, AssetStatus
)
from src.api.dependencies import get_current_user, PaginationParams
from src.models.schemas import (
    CommentCreate, CommentUpdate, CommentResponse,
    CommentThreadResponse, PaginatedResponse
)


logger = structlog.get_logger()

router = APIRouter(
    prefix="/api/v1/comments",
    tags=["comments"]
)


class Comment:
    """Comment data model"""
    def __init__(self, data: dict):
        self.id = data.get("id", str(uuid4()))
        self.resource_type = data.get("resource_type")  # 'asset' or 'container'
        self.resource_id = data.get("resource_id")
        self.parent_comment_id = data.get("parent_comment_id")
        self.user_id = data.get("user_id")
        self.content = data.get("content")
        self.created_at = data.get("created_at", datetime.utcnow())
        self.updated_at = data.get("updated_at")
        self.is_edited = data.get("is_edited", False)
        self.is_deleted = data.get("is_deleted", False)
        self.mentions = data.get("mentions", [])  # List of mentioned user IDs
        self.attachments = data.get("attachments", [])  # List of attachment info
        self.reactions = data.get("reactions", {})  # Dict of emoji: [user_ids]
        self.metadata = data.get("metadata", {})


async def get_resource_or_404(
    resource_type: Literal["asset", "container"],
    resource_id: UUID,
    db: AsyncSession,
    user: dict
) -> Any:
    """Get resource (asset or container) or raise 404"""
    if resource_type == "asset":
        query = select(Asset).where(
            and_(
                Asset.id == resource_id,
                Asset.status != AssetStatus.DELETED
            )
        )
        resource = await db.scalar(query)
        if not resource:
            raise HTTPException(
                status_code=404,
                detail="Asset not found"
            )
        
        # Check permissions
        if str(resource.owner_id) != user["user_id"] and not user.get("is_admin"):
            # Check if user has view permission through container sharing
            # This would need to be implemented based on your sharing logic
            pass
    
    elif resource_type == "container":
        query = select(ProjectContainer).where(
            ProjectContainer.id == resource_id
        )
        resource = await db.scalar(query)
        if not resource:
            raise HTTPException(
                status_code=404,
                detail="Container not found"
            )
        
        # Check permissions
        if str(resource.owner_id) != user["user_id"] and not user.get("is_admin"):
            # Check if user has view permission through sharing
            has_permission = False
            if hasattr(resource, "shared_with"):
                for share in resource.shared_with:
                    if share.user_id == UUID(user["user_id"]) and share.can_view:
                        has_permission = True
                        break
            
            if not has_permission:
                raise HTTPException(
                    status_code=403,
                    detail="You don't have permission to view this resource"
                )
    
    return resource


async def save_comment(
    resource: Any,
    comment_data: Comment,
    db: AsyncSession
) -> Comment:
    """Save a comment to the resource's metadata"""
    if not resource.metadata:
        resource.metadata = {}
    
    if "comments" not in resource.metadata:
        resource.metadata["comments"] = []
    
    # Convert comment to dict
    comment_dict = {
        "id": comment_data.id,
        "resource_type": comment_data.resource_type,
        "resource_id": str(comment_data.resource_id),
        "parent_comment_id": comment_data.parent_comment_id,
        "user_id": str(comment_data.user_id),
        "content": comment_data.content,
        "created_at": comment_data.created_at.isoformat(),
        "updated_at": comment_data.updated_at.isoformat() if comment_data.updated_at else None,
        "is_edited": comment_data.is_edited,
        "is_deleted": comment_data.is_deleted,
        "mentions": comment_data.mentions,
        "attachments": comment_data.attachments,
        "reactions": comment_data.reactions,
        "metadata": comment_data.metadata
    }
    
    # Add or update comment
    existing_index = next(
        (i for i, c in enumerate(resource.metadata["comments"]) if c["id"] == comment_data.id),
        None
    )
    
    if existing_index is not None:
        resource.metadata["comments"][existing_index] = comment_dict
    else:
        resource.metadata["comments"].append(comment_dict)
    
    # Update comment count
    active_comments = [c for c in resource.metadata["comments"] if not c.get("is_deleted", False)]
    resource.metadata["comment_count"] = len(active_comments)
    
    await db.commit()
    return comment_data


async def get_user_info(user_id: UUID, db: AsyncSession) -> Optional[Dict[str, Any]]:
    """Get basic user information for comment display"""
    query = select(User).where(User.id == user_id)
    user = await db.scalar(query)
    
    if user:
        return {
            "id": str(user.id),
            "username": user.username,
            "full_name": user.full_name,
            "avatar_url": user.metadata.get("avatar_url") if user.metadata else None
        }
    return None


@router.post("/", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    comment_data: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new comment on an asset or container"""
    # Get the resource
    resource = await get_resource_or_404(
        comment_data.resource_type,
        comment_data.resource_id,
        db,
        current_user
    )
    
    # If this is a reply, verify parent comment exists
    if comment_data.parent_comment_id:
        comments = resource.metadata.get("comments", []) if resource.metadata else []
        parent_comment = next(
            (c for c in comments if c["id"] == comment_data.parent_comment_id and not c.get("is_deleted", False)),
            None
        )
        if not parent_comment:
            raise HTTPException(
                status_code=404,
                detail="Parent comment not found"
            )
    
    # Extract mentions from content (e.g., @username)
    mentions = []  # TODO: Implement mention extraction
    
    # Create comment
    comment = Comment({
        "resource_type": comment_data.resource_type,
        "resource_id": comment_data.resource_id,
        "parent_comment_id": comment_data.parent_comment_id,
        "user_id": UUID(current_user["user_id"]),
        "content": comment_data.content,
        "mentions": mentions,
        "attachments": comment_data.attachments or [],
        "metadata": comment_data.metadata or {}
    })
    
    saved_comment = await save_comment(resource, comment, db)
    
    # Get user info for response
    user_info = await get_user_info(UUID(current_user["user_id"]), db)
    
    # Log activity
    logger.info(
        "comment_created",
        comment_id=saved_comment.id,
        resource_type=saved_comment.resource_type,
        resource_id=str(saved_comment.resource_id),
        user_id=current_user["user_id"]
    )
    
    return CommentResponse(
        id=saved_comment.id,
        resource_type=saved_comment.resource_type,
        resource_id=str(saved_comment.resource_id),
        parent_comment_id=saved_comment.parent_comment_id,
        user=user_info,
        content=saved_comment.content,
        created_at=saved_comment.created_at,
        updated_at=saved_comment.updated_at,
        is_edited=saved_comment.is_edited,
        mentions=saved_comment.mentions,
        attachments=saved_comment.attachments,
        reactions=saved_comment.reactions,
        reply_count=0,
        metadata=saved_comment.metadata
    )


@router.get("/{resource_type}/{resource_id}", response_model=List[CommentThreadResponse])
async def get_comments(
    resource_type: Literal["asset", "container"],
    resource_id: UUID,
    include_deleted: bool = Query(False, description="Include deleted comments"),
    sort_order: Literal["asc", "desc"] = Query("asc", description="Sort order by creation time"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all comments for a resource in threaded format"""
    # Get the resource
    resource = await get_resource_or_404(
        resource_type,
        resource_id,
        db,
        current_user
    )
    
    comments = resource.metadata.get("comments", []) if resource.metadata else []
    
    # Filter deleted comments if needed
    if not include_deleted:
        comments = [c for c in comments if not c.get("is_deleted", False)]
    
    # Build comment threads
    comment_map = {c["id"]: c for c in comments}
    threads = []
    
    for comment in comments:
        if not comment.get("parent_comment_id"):
            # This is a top-level comment
            thread = await build_comment_thread(comment, comment_map, db)
            threads.append(thread)
    
    # Sort threads
    threads.sort(
        key=lambda t: datetime.fromisoformat(t.created_at.isoformat()),
        reverse=(sort_order == "desc")
    )
    
    return threads


async def build_comment_thread(
    comment_data: dict,
    comment_map: dict,
    db: AsyncSession
) -> CommentThreadResponse:
    """Build a comment thread with replies"""
    # Get user info
    user_info = await get_user_info(UUID(comment_data["user_id"]), db)
    
    # Find replies
    replies = []
    for c in comment_map.values():
        if c.get("parent_comment_id") == comment_data["id"]:
            reply_thread = await build_comment_thread(c, comment_map, db)
            replies.append(reply_thread)
    
    # Sort replies
    replies.sort(key=lambda r: datetime.fromisoformat(r.created_at.isoformat()))
    
    return CommentThreadResponse(
        id=comment_data["id"],
        resource_type=comment_data["resource_type"],
        resource_id=comment_data["resource_id"],
        parent_comment_id=comment_data.get("parent_comment_id"),
        user=user_info,
        content=comment_data["content"] if not comment_data.get("is_deleted") else "[deleted]",
        created_at=datetime.fromisoformat(comment_data["created_at"]),
        updated_at=datetime.fromisoformat(comment_data["updated_at"]) if comment_data.get("updated_at") else None,
        is_edited=comment_data.get("is_edited", False),
        is_deleted=comment_data.get("is_deleted", False),
        mentions=comment_data.get("mentions", []),
        attachments=comment_data.get("attachments", []),
        reactions=comment_data.get("reactions", {}),
        replies=replies,
        reply_count=len(replies),
        metadata=comment_data.get("metadata", {})
    )


@router.put("/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_id: str,
    update_data: CommentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update a comment (edit content)"""
    # Find the comment across all resources
    # This is inefficient but works for MVP - in production, use a dedicated comments table
    comment_found = None
    resource = None
    
    # Search in assets
    assets_query = select(Asset).where(Asset.status != AssetStatus.DELETED)
    assets_result = await db.execute(assets_query)
    for asset in assets_result.scalars():
        if asset.metadata and "comments" in asset.metadata:
            for comment in asset.metadata["comments"]:
                if comment["id"] == comment_id:
                    comment_found = comment
                    resource = asset
                    break
            if comment_found:
                break
    
    # Search in containers if not found
    if not comment_found:
        containers_query = select(ProjectContainer)
        containers_result = await db.execute(containers_query)
        for container in containers_result.scalars():
            if container.metadata and "comments" in container.metadata:
                for comment in container.metadata["comments"]:
                    if comment["id"] == comment_id:
                        comment_found = comment
                        resource = container
                        break
                if comment_found:
                    break
    
    if not comment_found:
        raise HTTPException(
            status_code=404,
            detail="Comment not found"
        )
    
    # Check if user can edit this comment
    if str(comment_found["user_id"]) != current_user["user_id"] and not current_user.get("is_admin"):
        raise HTTPException(
            status_code=403,
            detail="You can only edit your own comments"
        )
    
    # Check if comment is deleted
    if comment_found.get("is_deleted", False):
        raise HTTPException(
            status_code=400,
            detail="Cannot edit deleted comment"
        )
    
    # Update comment
    comment_found["content"] = update_data.content
    comment_found["updated_at"] = datetime.utcnow().isoformat()
    comment_found["is_edited"] = True
    
    if update_data.metadata:
        comment_found["metadata"].update(update_data.metadata)
    
    await db.commit()
    
    # Get user info for response
    user_info = await get_user_info(UUID(comment_found["user_id"]), db)
    
    return CommentResponse(
        id=comment_found["id"],
        resource_type=comment_found["resource_type"],
        resource_id=comment_found["resource_id"],
        parent_comment_id=comment_found.get("parent_comment_id"),
        user=user_info,
        content=comment_found["content"],
        created_at=datetime.fromisoformat(comment_found["created_at"]),
        updated_at=datetime.fromisoformat(comment_found["updated_at"]),
        is_edited=comment_found["is_edited"],
        mentions=comment_found.get("mentions", []),
        attachments=comment_found.get("attachments", []),
        reactions=comment_found.get("reactions", {}),
        reply_count=0,  # Would need to calculate
        metadata=comment_found.get("metadata", {})
    )


@router.delete("/{comment_id}")
async def delete_comment(
    comment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Soft delete a comment"""
    # Find the comment (same inefficient search as update)
    comment_found = None
    resource = None
    
    # Search in assets and containers (same as update_comment)
    # ... (abbreviated for brevity, same logic as update_comment)
    
    assets_query = select(Asset).where(Asset.status != AssetStatus.DELETED)
    assets_result = await db.execute(assets_query)
    for asset in assets_result.scalars():
        if asset.metadata and "comments" in asset.metadata:
            for comment in asset.metadata["comments"]:
                if comment["id"] == comment_id:
                    comment_found = comment
                    resource = asset
                    break
            if comment_found:
                break
    
    if not comment_found:
        containers_query = select(ProjectContainer)
        containers_result = await db.execute(containers_query)
        for container in containers_result.scalars():
            if container.metadata and "comments" in container.metadata:
                for comment in container.metadata["comments"]:
                    if comment["id"] == comment_id:
                        comment_found = comment
                        resource = container
                        break
                if comment_found:
                    break
    
    if not comment_found:
        raise HTTPException(
            status_code=404,
            detail="Comment not found"
        )
    
    # Check if user can delete this comment
    is_owner = str(resource.owner_id) == current_user["user_id"]
    is_comment_author = str(comment_found["user_id"]) == current_user["user_id"]
    is_admin = current_user.get("is_admin", False)
    
    if not (is_owner or is_comment_author or is_admin):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to delete this comment"
        )
    
    # Soft delete
    comment_found["is_deleted"] = True
    comment_found["updated_at"] = datetime.utcnow().isoformat()
    
    # Update comment count
    active_comments = [c for c in resource.metadata["comments"] if not c.get("is_deleted", False)]
    resource.metadata["comment_count"] = len(active_comments)
    
    await db.commit()
    
    return {"message": "Comment deleted successfully"}


@router.post("/{comment_id}/react")
async def add_reaction(
    comment_id: str,
    emoji: str = Query(..., description="Emoji reaction"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Add or toggle a reaction to a comment"""
    # Validate emoji (basic validation)
    if len(emoji) > 4:  # Most emojis are 1-4 characters
        raise HTTPException(
            status_code=400,
            detail="Invalid emoji"
        )
    
    # Find the comment
    comment_found = None
    resource = None
    
    # Search logic (same as update/delete)
    assets_query = select(Asset).where(Asset.status != AssetStatus.DELETED)
    assets_result = await db.execute(assets_query)
    for asset in assets_result.scalars():
        if asset.metadata and "comments" in asset.metadata:
            for comment in asset.metadata["comments"]:
                if comment["id"] == comment_id:
                    comment_found = comment
                    resource = asset
                    break
            if comment_found:
                break
    
    if not comment_found:
        containers_query = select(ProjectContainer)
        containers_result = await db.execute(containers_query)
        for container in containers_result.scalars():
            if container.metadata and "comments" in container.metadata:
                for comment in container.metadata["comments"]:
                    if comment["id"] == comment_id:
                        comment_found = comment
                        resource = container
                        break
                if comment_found:
                    break
    
    if not comment_found:
        raise HTTPException(
            status_code=404,
            detail="Comment not found"
        )
    
    # Toggle reaction
    if "reactions" not in comment_found:
        comment_found["reactions"] = {}
    
    user_id = current_user["user_id"]
    
    if emoji not in comment_found["reactions"]:
        comment_found["reactions"][emoji] = []
    
    if user_id in comment_found["reactions"][emoji]:
        # Remove reaction
        comment_found["reactions"][emoji].remove(user_id)
        if not comment_found["reactions"][emoji]:
            del comment_found["reactions"][emoji]
        action = "removed"
    else:
        # Add reaction
        comment_found["reactions"][emoji].append(user_id)
        action = "added"
    
    await db.commit()
    
    return {
        "message": f"Reaction {action}",
        "emoji": emoji,
        "reactions": comment_found["reactions"]
    }


@router.get("/search", response_model=PaginatedResponse)
async def search_comments(
    q: str = Query(..., min_length=2, description="Search query"),
    resource_type: Optional[Literal["asset", "container"]] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Search comments across all resources"""
    all_comments = []
    
    # Search in assets
    if not resource_type or resource_type == "asset":
        assets_query = select(Asset).where(Asset.status != AssetStatus.DELETED)
        assets_result = await db.execute(assets_query)
        for asset in assets_result.scalars():
            # Check if user has permission to view this asset
            if str(asset.owner_id) == current_user["user_id"] or current_user.get("is_admin"):
                if asset.metadata and "comments" in asset.metadata:
                    for comment in asset.metadata["comments"]:
                        if not comment.get("is_deleted", False) and q.lower() in comment["content"].lower():
                            comment_copy = comment.copy()
                            comment_copy["resource_name"] = asset.display_name or asset.name
                            all_comments.append(comment_copy)
    
    # Search in containers
    if not resource_type or resource_type == "container":
        containers_query = select(ProjectContainer)
        containers_result = await db.execute(containers_query)
        for container in containers_result.scalars():
            # Check if user has permission to view this container
            has_permission = str(container.owner_id) == current_user["user_id"] or current_user.get("is_admin")
            
            if not has_permission and hasattr(container, "shared_with"):
                for share in container.shared_with:
                    if share.user_id == UUID(current_user["user_id"]) and share.can_view:
                        has_permission = True
                        break
            
            if has_permission and container.metadata and "comments" in container.metadata:
                for comment in container.metadata["comments"]:
                    if not comment.get("is_deleted", False) and q.lower() in comment["content"].lower():
                        comment_copy = comment.copy()
                        comment_copy["resource_name"] = container.display_name or container.name
                        all_comments.append(comment_copy)
    
    # Sort by creation date descending
    all_comments.sort(
        key=lambda c: datetime.fromisoformat(c["created_at"]),
        reverse=True
    )
    
    # Apply pagination
    total = len(all_comments)
    start = pagination.offset
    end = start + pagination.limit
    paginated_comments = all_comments[start:end]
    
    # Convert to response format
    items = []
    for comment in paginated_comments:
        user_info = await get_user_info(UUID(comment["user_id"]), db)
        items.append(CommentResponse(
            id=comment["id"],
            resource_type=comment["resource_type"],
            resource_id=comment["resource_id"],
            parent_comment_id=comment.get("parent_comment_id"),
            user=user_info,
            content=comment["content"],
            created_at=datetime.fromisoformat(comment["created_at"]),
            updated_at=datetime.fromisoformat(comment["updated_at"]) if comment.get("updated_at") else None,
            is_edited=comment.get("is_edited", False),
            mentions=comment.get("mentions", []),
            attachments=comment.get("attachments", []),
            reactions=comment.get("reactions", {}),
            reply_count=0,
            metadata={**comment.get("metadata", {}), "resource_name": comment.get("resource_name")}
        ))
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        size=pagination.limit,
        pages=(total + pagination.limit - 1) // pagination.limit
    )


@router.get("/recent", response_model=List[CommentResponse])
async def get_recent_comments(
    limit: int = Query(10, ge=1, le=50, description="Number of recent comments"),
    resource_type: Optional[Literal["asset", "container"]] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get recent comments across resources the user has access to"""
    all_comments = []
    
    # Get comments from assets
    if not resource_type or resource_type == "asset":
        assets_query = select(Asset).where(
            and_(
                Asset.status != AssetStatus.DELETED,
                Asset.owner_id == UUID(current_user["user_id"])
            )
        )
        assets_result = await db.execute(assets_query)
        for asset in assets_result.scalars():
            if asset.metadata and "comments" in asset.metadata:
                for comment in asset.metadata["comments"]:
                    if not comment.get("is_deleted", False):
                        comment_copy = comment.copy()
                        comment_copy["resource_name"] = asset.display_name or asset.name
                        all_comments.append(comment_copy)
    
    # Get comments from containers
    if not resource_type or resource_type == "container":
        containers_query = select(ProjectContainer).where(
            ProjectContainer.owner_id == UUID(current_user["user_id"])
        )
        containers_result = await db.execute(containers_query)
        for container in containers_result.scalars():
            if container.metadata and "comments" in container.metadata:
                for comment in container.metadata["comments"]:
                    if not comment.get("is_deleted", False):
                        comment_copy = comment.copy()
                        comment_copy["resource_name"] = container.display_name or container.name
                        all_comments.append(comment_copy)
    
    # Sort by creation date descending and take limit
    all_comments.sort(
        key=lambda c: datetime.fromisoformat(c["created_at"]),
        reverse=True
    )
    recent_comments = all_comments[:limit]
    
    # Convert to response format
    items = []
    for comment in recent_comments:
        user_info = await get_user_info(UUID(comment["user_id"]), db)
        items.append(CommentResponse(
            id=comment["id"],
            resource_type=comment["resource_type"],
            resource_id=comment["resource_id"],
            parent_comment_id=comment.get("parent_comment_id"),
            user=user_info,
            content=comment["content"],
            created_at=datetime.fromisoformat(comment["created_at"]),
            updated_at=datetime.fromisoformat(comment["updated_at"]) if comment.get("updated_at") else None,
            is_edited=comment.get("is_edited", False),
            mentions=comment.get("mentions", []),
            attachments=comment.get("attachments", []),
            reactions=comment.get("reactions", {}),
            reply_count=0,
            metadata={**comment.get("metadata", {}), "resource_name": comment.get("resource_name")}
        ))
    
    return items