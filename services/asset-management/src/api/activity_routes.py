"""
Activity tracking API routes

Provides activity logging and retrieval for user actions.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_, or_, func
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any, Literal
from uuid import UUID, uuid4
from datetime import datetime, timedelta
import structlog

from src.db.base import get_db
from src.db.models import (
    User, Asset, ProjectContainer, AssetStatus
)
from src.api.dependencies import get_current_user, PaginationParams
from src.models.schemas import (
    ActivityLogResponse, ActivitySummaryResponse,
    ActivityFilterParams, PaginatedResponse
)


logger = structlog.get_logger()

router = APIRouter(
    prefix="/api/v1/activities",
    tags=["activities"]
)


# Activity types
ACTIVITY_TYPES = {
    # Asset activities
    "asset.created": "Created asset",
    "asset.updated": "Updated asset",
    "asset.deleted": "Deleted asset",
    "asset.viewed": "Viewed asset",
    "asset.downloaded": "Downloaded asset",
    "asset.shared": "Shared asset",
    "asset.uploaded": "Uploaded new version",
    "asset.metadata_updated": "Updated asset metadata",
    "asset.moved": "Moved asset",
    "asset.copied": "Copied asset",
    "asset.restored": "Restored asset",
    
    # Container activities
    "container.created": "Created container",
    "container.updated": "Updated container",
    "container.deleted": "Deleted container",
    "container.shared": "Shared container",
    "container.unshared": "Removed container share",
    "container.moved": "Moved container",
    "container.copied": "Copied container",
    
    # Timeline activities
    "timeline.created": "Created timeline",
    "timeline.updated": "Updated timeline",
    "timeline.clip_added": "Added clip to timeline",
    "timeline.clip_removed": "Removed clip from timeline",
    "timeline.clip_moved": "Moved clip in timeline",
    "timeline.transition_added": "Added transition",
    "timeline.effect_added": "Added effect",
    "timeline.version_saved": "Saved timeline version",
    "timeline.version_restored": "Restored timeline version",
    
    # Comment activities
    "comment.created": "Added comment",
    "comment.updated": "Updated comment",
    "comment.deleted": "Deleted comment",
    "comment.reaction_added": "Added reaction",
    
    # User activities
    "user.login": "Logged in",
    "user.logout": "Logged out",
    "user.profile_updated": "Updated profile",
    "user.password_changed": "Changed password",
    "user.settings_updated": "Updated settings",
    
    # Search activities
    "search.performed": "Performed search",
    "search.advanced": "Used advanced search",
    
    # Export activities
    "export.initiated": "Started export",
    "export.completed": "Completed export",
    "export.failed": "Export failed",
}


class ActivityLog:
    """Activity log data model"""
    def __init__(self, data: dict):
        self.id = data.get("id", str(uuid4()))
        self.user_id = data.get("user_id")
        self.activity_type = data.get("activity_type")
        self.resource_type = data.get("resource_type")  # 'asset', 'container', 'user', etc.
        self.resource_id = data.get("resource_id")
        self.resource_name = data.get("resource_name")
        self.description = data.get("description")
        self.metadata = data.get("metadata", {})
        self.ip_address = data.get("ip_address")
        self.user_agent = data.get("user_agent")
        self.created_at = data.get("created_at", datetime.utcnow())


async def log_activity(
    activity_type: str,
    resource_type: str,
    resource_id: Optional[UUID],
    user_id: UUID,
    description: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    db: AsyncSession = None,
    request_info: Optional[Dict[str, str]] = None
) -> ActivityLog:
    """Log an activity to the database"""
    # Get resource name if applicable
    resource_name = None
    if resource_id and db:
        if resource_type == "asset":
            asset = await db.get(Asset, resource_id)
            if asset:
                resource_name = asset.display_name or asset.name
        elif resource_type == "container":
            container = await db.get(ProjectContainer, resource_id)
            if container:
                resource_name = container.display_name or container.name
    
    # Create activity log
    activity = ActivityLog({
        "user_id": user_id,
        "activity_type": activity_type,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "resource_name": resource_name,
        "description": description or ACTIVITY_TYPES.get(activity_type, activity_type),
        "metadata": metadata or {},
        "ip_address": request_info.get("ip_address") if request_info else None,
        "user_agent": request_info.get("user_agent") if request_info else None
    })
    
    # Store in user's activity log
    if db:
        user = await db.get(User, user_id)
        if user:
            if not user.metadata:
                user.metadata = {}
            
            if "activity_log" not in user.metadata:
                user.metadata["activity_log"] = []
            
            # Convert to dict
            activity_dict = {
                "id": activity.id,
                "activity_type": activity.activity_type,
                "resource_type": activity.resource_type,
                "resource_id": str(activity.resource_id) if activity.resource_id else None,
                "resource_name": activity.resource_name,
                "description": activity.description,
                "metadata": activity.metadata,
                "ip_address": activity.ip_address,
                "user_agent": activity.user_agent,
                "created_at": activity.created_at.isoformat()
            }
            
            # Add to beginning of list (most recent first)
            user.metadata["activity_log"].insert(0, activity_dict)
            
            # Keep only last 1000 activities per user
            if len(user.metadata["activity_log"]) > 1000:
                user.metadata["activity_log"] = user.metadata["activity_log"][:1000]
            
            await db.commit()
    
    # Log to structured logger
    logger.info(
        "activity_logged",
        activity_id=activity.id,
        user_id=str(user_id),
        activity_type=activity_type,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else None
    )
    
    return activity


@router.get("/", response_model=PaginatedResponse)
async def get_activities(
    filters: ActivityFilterParams = Depends(),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get activity logs for the current user or their resources"""
    user_id = UUID(current_user["user_id"])
    all_activities = []
    
    # Get user's own activities
    user = await db.get(User, user_id)
    if user and user.metadata and "activity_log" in user.metadata:
        user_activities = user.metadata["activity_log"]
        
        # Apply filters
        filtered_activities = []
        for activity in user_activities:
            # Time range filter
            activity_time = datetime.fromisoformat(activity["created_at"])
            if filters.start_date and activity_time < filters.start_date:
                continue
            if filters.end_date and activity_time > filters.end_date:
                continue
            
            # Activity type filter
            if filters.activity_types and activity["activity_type"] not in filters.activity_types:
                continue
            
            # Resource type filter
            if filters.resource_type and activity["resource_type"] != filters.resource_type:
                continue
            
            # Resource ID filter
            if filters.resource_id and activity.get("resource_id") != str(filters.resource_id):
                continue
            
            filtered_activities.append(activity)
        
        all_activities.extend(filtered_activities)
    
    # If user is admin, optionally get activities from other users
    if current_user.get("is_admin") and filters.include_all_users:
        users_query = select(User).where(User.id != user_id)
        users_result = await db.execute(users_query)
        
        for other_user in users_result.scalars():
            if other_user.metadata and "activity_log" in other_user.metadata:
                for activity in other_user.metadata["activity_log"]:
                    # Apply same filters
                    activity_time = datetime.fromisoformat(activity["created_at"])
                    if filters.start_date and activity_time < filters.start_date:
                        continue
                    if filters.end_date and activity_time > filters.end_date:
                        continue
                    if filters.activity_types and activity["activity_type"] not in filters.activity_types:
                        continue
                    if filters.resource_type and activity["resource_type"] != filters.resource_type:
                        continue
                    if filters.resource_id and activity.get("resource_id") != str(filters.resource_id):
                        continue
                    
                    # Add user info
                    activity_copy = activity.copy()
                    activity_copy["user"] = {
                        "id": str(other_user.id),
                        "username": other_user.username,
                        "full_name": other_user.full_name
                    }
                    all_activities.append(activity_copy)
    
    # Sort by created_at descending
    all_activities.sort(
        key=lambda a: datetime.fromisoformat(a["created_at"]),
        reverse=True
    )
    
    # Apply pagination
    total = len(all_activities)
    start = pagination.offset
    end = start + pagination.limit
    paginated_activities = all_activities[start:end]
    
    # Convert to response format
    items = []
    for activity in paginated_activities:
        # Get user info if not present
        if "user" not in activity:
            activity["user"] = {
                "id": str(user_id),
                "username": current_user.get("username"),
                "full_name": current_user.get("full_name")
            }
        
        items.append(ActivityLogResponse(
            id=activity["id"],
            user=activity["user"],
            activity_type=activity["activity_type"],
            resource_type=activity["resource_type"],
            resource_id=activity.get("resource_id"),
            resource_name=activity.get("resource_name"),
            description=activity["description"],
            metadata=activity.get("metadata", {}),
            created_at=datetime.fromisoformat(activity["created_at"])
        ))
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        size=pagination.limit,
        pages=(total + pagination.limit - 1) // pagination.limit
    )


@router.get("/summary", response_model=ActivitySummaryResponse)
async def get_activity_summary(
    time_period: Literal["day", "week", "month"] = Query("week"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get activity summary for the current user"""
    user_id = UUID(current_user["user_id"])
    
    # Calculate date range
    end_date = datetime.utcnow()
    if time_period == "day":
        start_date = end_date - timedelta(days=1)
    elif time_period == "week":
        start_date = end_date - timedelta(weeks=1)
    else:  # month
        start_date = end_date - timedelta(days=30)
    
    # Get user's activities
    user = await db.get(User, user_id)
    if not user or not user.metadata or "activity_log" not in user.metadata:
        return ActivitySummaryResponse(
            total_activities=0,
            activities_by_type={},
            activities_by_resource={},
            most_active_hours=[],
            recent_resources=[]
        )
    
    # Filter activities by date range
    activities_in_range = []
    for activity in user.metadata["activity_log"]:
        activity_time = datetime.fromisoformat(activity["created_at"])
        if start_date <= activity_time <= end_date:
            activities_in_range.append(activity)
    
    # Calculate statistics
    activities_by_type = {}
    activities_by_resource = {}
    activities_by_hour = {}
    recent_resources = {}
    
    for activity in activities_in_range:
        # Count by type
        activity_type = activity["activity_type"]
        activities_by_type[activity_type] = activities_by_type.get(activity_type, 0) + 1
        
        # Count by resource type
        resource_type = activity["resource_type"]
        activities_by_resource[resource_type] = activities_by_resource.get(resource_type, 0) + 1
        
        # Count by hour
        activity_time = datetime.fromisoformat(activity["created_at"])
        hour = activity_time.hour
        activities_by_hour[hour] = activities_by_hour.get(hour, 0) + 1
        
        # Track recent resources
        if activity.get("resource_id") and activity.get("resource_name"):
            resource_key = f"{resource_type}:{activity['resource_id']}"
            if resource_key not in recent_resources:
                recent_resources[resource_key] = {
                    "resource_type": resource_type,
                    "resource_id": activity["resource_id"],
                    "resource_name": activity["resource_name"],
                    "last_activity": activity_time,
                    "activity_count": 0
                }
            recent_resources[resource_key]["activity_count"] += 1
            if activity_time > recent_resources[resource_key]["last_activity"]:
                recent_resources[resource_key]["last_activity"] = activity_time
    
    # Get most active hours
    most_active_hours = sorted(
        activities_by_hour.items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]
    
    # Get top recent resources
    recent_resources_list = sorted(
        recent_resources.values(),
        key=lambda x: x["last_activity"],
        reverse=True
    )[:10]
    
    return ActivitySummaryResponse(
        total_activities=len(activities_in_range),
        activities_by_type=activities_by_type,
        activities_by_resource=activities_by_resource,
        most_active_hours=[{"hour": h, "count": c} for h, c in most_active_hours],
        recent_resources=recent_resources_list
    )


@router.get("/timeline", response_model=List[Dict[str, Any]])
async def get_activity_timeline(
    days: int = Query(7, ge=1, le=30, description="Number of days to include"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get activity timeline grouped by day"""
    user_id = UUID(current_user["user_id"])
    
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Get user's activities
    user = await db.get(User, user_id)
    if not user or not user.metadata or "activity_log" not in user.metadata:
        return []
    
    # Group activities by day
    activities_by_day = {}
    
    for activity in user.metadata["activity_log"]:
        activity_time = datetime.fromisoformat(activity["created_at"])
        if start_date <= activity_time <= end_date:
            day_key = activity_time.date().isoformat()
            
            if day_key not in activities_by_day:
                activities_by_day[day_key] = {
                    "date": day_key,
                    "total_count": 0,
                    "activities": []
                }
            
            activities_by_day[day_key]["total_count"] += 1
            
            # Include abbreviated activity info
            activities_by_day[day_key]["activities"].append({
                "id": activity["id"],
                "time": activity_time.time().isoformat(),
                "type": activity["activity_type"],
                "resource_type": activity["resource_type"],
                "resource_name": activity.get("resource_name"),
                "description": activity["description"]
            })
    
    # Convert to list and sort by date
    timeline = list(activities_by_day.values())
    timeline.sort(key=lambda x: x["date"], reverse=True)
    
    # Limit activities per day to prevent huge responses
    for day in timeline:
        if len(day["activities"]) > 20:
            day["activities"] = day["activities"][:20]
            day["has_more"] = True
    
    return timeline


@router.get("/resource/{resource_type}/{resource_id}", response_model=List[ActivityLogResponse])
async def get_resource_activities(
    resource_type: Literal["asset", "container"],
    resource_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all activities for a specific resource"""
    # Check resource access
    if resource_type == "asset":
        resource = await db.get(Asset, resource_id)
        if not resource or resource.status == AssetStatus.DELETED:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        # Check permissions
        if str(resource.owner_id) != current_user["user_id"] and not current_user.get("is_admin"):
            raise HTTPException(status_code=403, detail="Access denied")
    
    elif resource_type == "container":
        resource = await db.get(ProjectContainer, resource_id)
        if not resource:
            raise HTTPException(status_code=404, detail="Container not found")
        
        # Check permissions
        has_access = str(resource.owner_id) == current_user["user_id"] or current_user.get("is_admin")
        # Add share check logic here if needed
        
        if not has_access:
            raise HTTPException(status_code=403, detail="Access denied")
    
    # Collect activities from all users who have interacted with this resource
    all_activities = []
    
    # This is inefficient for large deployments - in production use a dedicated activity table
    users_query = select(User)
    users_result = await db.execute(users_query)
    
    for user in users_result.scalars():
        if user.metadata and "activity_log" in user.metadata:
            for activity in user.metadata["activity_log"]:
                if (activity.get("resource_id") == str(resource_id) and
                    activity["resource_type"] == resource_type):
                    # Add user info
                    activity_copy = activity.copy()
                    activity_copy["user"] = {
                        "id": str(user.id),
                        "username": user.username,
                        "full_name": user.full_name
                    }
                    all_activities.append(activity_copy)
    
    # Sort by created_at descending
    all_activities.sort(
        key=lambda a: datetime.fromisoformat(a["created_at"]),
        reverse=True
    )
    
    # Apply limit
    limited_activities = all_activities[:limit]
    
    # Convert to response format
    items = []
    for activity in limited_activities:
        items.append(ActivityLogResponse(
            id=activity["id"],
            user=activity["user"],
            activity_type=activity["activity_type"],
            resource_type=activity["resource_type"],
            resource_id=activity.get("resource_id"),
            resource_name=activity.get("resource_name"),
            description=activity["description"],
            metadata=activity.get("metadata", {}),
            created_at=datetime.fromisoformat(activity["created_at"])
        ))
    
    return items


@router.post("/export")
async def export_activities(
    format: Literal["csv", "json"] = Query("csv"),
    filters: ActivityFilterParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Export activity logs in various formats"""
    # Get filtered activities (reuse logic from get_activities)
    user_id = UUID(current_user["user_id"])
    user = await db.get(User, user_id)
    
    if not user or not user.metadata or "activity_log" not in user.metadata:
        return {"message": "No activities to export"}
    
    # Apply filters
    filtered_activities = []
    for activity in user.metadata["activity_log"]:
        # Apply same filtering logic as get_activities
        activity_time = datetime.fromisoformat(activity["created_at"])
        if filters.start_date and activity_time < filters.start_date:
            continue
        if filters.end_date and activity_time > filters.end_date:
            continue
        if filters.activity_types and activity["activity_type"] not in filters.activity_types:
            continue
        if filters.resource_type and activity["resource_type"] != filters.resource_type:
            continue
        if filters.resource_id and activity.get("resource_id") != str(filters.resource_id):
            continue
        
        filtered_activities.append(activity)
    
    if format == "json":
        return {
            "export_date": datetime.utcnow().isoformat(),
            "user_id": str(user_id),
            "total_activities": len(filtered_activities),
            "activities": filtered_activities
        }
    
    elif format == "csv":
        # Generate CSV content
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            "Date", "Time", "Activity Type", "Resource Type",
            "Resource Name", "Description", "IP Address"
        ])
        
        # Write data
        for activity in filtered_activities:
            activity_datetime = datetime.fromisoformat(activity["created_at"])
            writer.writerow([
                activity_datetime.date().isoformat(),
                activity_datetime.time().isoformat(),
                activity["activity_type"],
                activity["resource_type"],
                activity.get("resource_name", ""),
                activity["description"],
                activity.get("ip_address", "")
            ])
        
        csv_content = output.getvalue()
        
        # In a real implementation, you'd return a file response
        # For now, return the content info
        return {
            "format": "csv",
            "content_length": len(csv_content),
            "preview": csv_content[:500] + "..." if len(csv_content) > 500 else csv_content
        }


# Helper function to be used by other routes
async def track_activity(
    request,
    activity_type: str,
    resource_type: str,
    resource_id: Optional[UUID],
    user_id: UUID,
    description: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    db: AsyncSession = None
):
    """Helper function to track activities from other routes"""
    request_info = {
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent")
    }
    
    await log_activity(
        activity_type=activity_type,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id,
        description=description,
        metadata=metadata,
        db=db,
        request_info=request_info
    )


# Export for use by other modules
__all__ = ["router", "track_activity", "log_activity"]