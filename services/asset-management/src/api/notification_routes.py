"""
Real-time notification system API routes

Provides WebSocket and REST endpoints for notifications.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_, or_, func, update
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any, Literal, Set
from uuid import UUID, uuid4
from datetime import datetime, timedelta
import json
import asyncio
import structlog

from src.db.base import get_db
from src.db.models import User, Asset, ProjectContainer
from src.api.dependencies import get_current_user, PaginationParams
from src.models.schemas import (
    NotificationCreate, NotificationUpdate, NotificationResponse,
    NotificationPreferences, PaginatedResponse
)


logger = structlog.get_logger()

router = APIRouter(
    prefix="/api/v1/notifications",
    tags=["notifications"]
)


# WebSocket connection manager
class ConnectionManager:
    """Manages WebSocket connections for real-time notifications"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_subscriptions: Dict[str, Set[str]] = {}  # user_id -> set of channels
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.user_subscriptions[user_id] = set()
        logger.info("websocket_connected", user_id=user_id)
    
    def disconnect(self, user_id: str):
        """Remove WebSocket connection"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        if user_id in self.user_subscriptions:
            del self.user_subscriptions[user_id]
        logger.info("websocket_disconnected", user_id=user_id)
    
    async def send_personal_message(self, message: dict, user_id: str):
        """Send message to specific user"""
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)
    
    async def broadcast(self, message: dict, channel: str = None):
        """Broadcast message to all connected users or channel subscribers"""
        for user_id, connection in self.active_connections.items():
            if channel is None or (channel in self.user_subscriptions.get(user_id, set())):
                await connection.send_json(message)
    
    def subscribe(self, user_id: str, channel: str):
        """Subscribe user to a channel"""
        if user_id in self.user_subscriptions:
            self.user_subscriptions[user_id].add(channel)
    
    def unsubscribe(self, user_id: str, channel: str):
        """Unsubscribe user from a channel"""
        if user_id in self.user_subscriptions:
            self.user_subscriptions[user_id].discard(channel)


# Global connection manager instance
manager = ConnectionManager()


# Notification types
NOTIFICATION_TYPES = {
    # Asset notifications
    "asset.created": {"title": "New Asset", "icon": "file_upload"},
    "asset.updated": {"title": "Asset Updated", "icon": "edit"},
    "asset.deleted": {"title": "Asset Deleted", "icon": "delete"},
    "asset.shared": {"title": "Asset Shared", "icon": "share"},
    "asset.commented": {"title": "New Comment", "icon": "comment"},
    "asset.processing_complete": {"title": "Processing Complete", "icon": "check_circle"},
    "asset.processing_failed": {"title": "Processing Failed", "icon": "error"},
    
    # Project notifications
    "project.shared": {"title": "Project Shared", "icon": "folder_shared"},
    "project.updated": {"title": "Project Updated", "icon": "folder"},
    "project.member_added": {"title": "Member Added", "icon": "person_add"},
    "project.member_removed": {"title": "Member Removed", "icon": "person_remove"},
    
    # Timeline notifications
    "timeline.updated": {"title": "Timeline Updated", "icon": "timeline"},
    "timeline.version_saved": {"title": "Version Saved", "icon": "save"},
    "timeline.commented": {"title": "Timeline Comment", "icon": "comment"},
    
    # System notifications
    "system.maintenance": {"title": "System Maintenance", "icon": "build"},
    "system.update": {"title": "System Update", "icon": "system_update"},
    "storage.quota_warning": {"title": "Storage Warning", "icon": "warning"},
    "storage.quota_exceeded": {"title": "Storage Exceeded", "icon": "error"},
    
    # Workflow notifications
    "workflow.started": {"title": "Workflow Started", "icon": "play_circle"},
    "workflow.completed": {"title": "Workflow Completed", "icon": "check_circle"},
    "workflow.failed": {"title": "Workflow Failed", "icon": "error"},
    "workflow.approval_needed": {"title": "Approval Needed", "icon": "pending"},
}


class Notification:
    """Notification data model"""
    def __init__(self, data: dict):
        self.id = data.get("id", str(uuid4()))
        self.user_id = data.get("user_id")
        self.type = data.get("type")
        self.title = data.get("title")
        self.message = data.get("message")
        self.icon = data.get("icon")
        self.priority = data.get("priority", "normal")  # low, normal, high, urgent
        self.resource_type = data.get("resource_type")  # asset, project, etc.
        self.resource_id = data.get("resource_id")
        self.resource_name = data.get("resource_name")
        self.action_url = data.get("action_url")
        self.is_read = data.get("is_read", False)
        self.is_archived = data.get("is_archived", False)
        self.metadata = data.get("metadata", {})
        self.created_at = data.get("created_at", datetime.utcnow())
        self.read_at = data.get("read_at")
        self.expires_at = data.get("expires_at")


async def create_notification(
    user_id: UUID,
    notification_type: str,
    title: Optional[str] = None,
    message: str = "",
    resource_type: Optional[str] = None,
    resource_id: Optional[UUID] = None,
    priority: str = "normal",
    metadata: Optional[Dict[str, Any]] = None,
    db: AsyncSession = None
) -> Notification:
    """Create and store a notification"""
    # Get notification type info
    type_info = NOTIFICATION_TYPES.get(notification_type, {})
    
    # Get resource name if applicable
    resource_name = None
    if resource_id and resource_type and db:
        if resource_type == "asset":
            asset = await db.get(Asset, resource_id)
            if asset:
                resource_name = asset.display_name or asset.name
        elif resource_type == "project":
            project = await db.get(ProjectContainer, resource_id)
            if project:
                resource_name = project.display_name or project.name
    
    # Create notification
    notification = Notification({
        "user_id": user_id,
        "type": notification_type,
        "title": title or type_info.get("title", "Notification"),
        "message": message,
        "icon": type_info.get("icon", "notifications"),
        "priority": priority,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "resource_name": resource_name,
        "action_url": f"/{resource_type}/{resource_id}" if resource_type and resource_id else None,
        "metadata": metadata or {},
        "expires_at": datetime.utcnow() + timedelta(days=30)  # Expire after 30 days
    })
    
    # Store in user's notification list
    if db:
        user = await db.get(User, user_id)
        if user:
            if not user.metadata:
                user.metadata = {}
            
            if "notifications" not in user.metadata:
                user.metadata["notifications"] = []
            
            # Convert to dict
            notification_dict = {
                "id": notification.id,
                "type": notification.type,
                "title": notification.title,
                "message": notification.message,
                "icon": notification.icon,
                "priority": notification.priority,
                "resource_type": notification.resource_type,
                "resource_id": str(notification.resource_id) if notification.resource_id else None,
                "resource_name": notification.resource_name,
                "action_url": notification.action_url,
                "is_read": notification.is_read,
                "is_archived": notification.is_archived,
                "metadata": notification.metadata,
                "created_at": notification.created_at.isoformat(),
                "read_at": notification.read_at.isoformat() if notification.read_at else None,
                "expires_at": notification.expires_at.isoformat() if notification.expires_at else None
            }
            
            # Add to beginning of list (most recent first)
            user.metadata["notifications"].insert(0, notification_dict)
            
            # Keep only last 100 notifications per user
            if len(user.metadata["notifications"]) > 100:
                user.metadata["notifications"] = user.metadata["notifications"][:100]
            
            # Update unread count
            unread_count = sum(1 for n in user.metadata["notifications"] 
                             if not n.get("is_read", False) and not n.get("is_archived", False))
            user.metadata["unread_notifications"] = unread_count
            
            await db.commit()
    
    # Send real-time notification
    await send_realtime_notification(str(user_id), notification_dict)
    
    return notification


async def send_realtime_notification(user_id: str, notification: dict):
    """Send notification through WebSocket"""
    message = {
        "type": "notification",
        "data": notification
    }
    await manager.send_personal_message(message, user_id)


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """WebSocket endpoint for real-time notifications"""
    await manager.connect(websocket, user_id)
    
    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connection",
            "data": {"status": "connected", "user_id": user_id}
        })
        
        # Keep connection alive
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            # Handle different message types
            if data.get("type") == "subscribe":
                channel = data.get("channel")
                if channel:
                    manager.subscribe(user_id, channel)
                    await websocket.send_json({
                        "type": "subscribed",
                        "data": {"channel": channel}
                    })
            
            elif data.get("type") == "unsubscribe":
                channel = data.get("channel")
                if channel:
                    manager.unsubscribe(user_id, channel)
                    await websocket.send_json({
                        "type": "unsubscribed",
                        "data": {"channel": channel}
                    })
            
            elif data.get("type") == "ping":
                # Respond to ping with pong
                await websocket.send_json({
                    "type": "pong",
                    "data": {"timestamp": datetime.utcnow().isoformat()}
                })
    
    except WebSocketDisconnect:
        manager.disconnect(user_id)
        logger.info("websocket_disconnected", user_id=user_id, reason="client_disconnect")
    except Exception as e:
        manager.disconnect(user_id)
        logger.error("websocket_error", user_id=user_id, error=str(e))


@router.get("/", response_model=PaginatedResponse)
async def get_notifications(
    is_read: Optional[bool] = Query(None, description="Filter by read status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    notification_type: Optional[str] = Query(None, description="Filter by type"),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get notifications for the current user"""
    user_id = UUID(current_user["user_id"])
    user = await db.get(User, user_id)
    
    if not user or not user.metadata or "notifications" not in user.metadata:
        return PaginatedResponse(
            items=[],
            total=0,
            page=pagination.page,
            size=pagination.limit,
            pages=0
        )
    
    # Filter notifications
    notifications = user.metadata["notifications"]
    filtered_notifications = []
    
    for notif in notifications:
        # Skip archived or expired
        if notif.get("is_archived", False):
            continue
        
        if notif.get("expires_at"):
            expires_at = datetime.fromisoformat(notif["expires_at"])
            if expires_at < datetime.utcnow():
                continue
        
        # Apply filters
        if is_read is not None and notif.get("is_read", False) != is_read:
            continue
        
        if priority and notif.get("priority") != priority:
            continue
        
        if notification_type and notif.get("type") != notification_type:
            continue
        
        filtered_notifications.append(notif)
    
    # Apply pagination
    total = len(filtered_notifications)
    start = pagination.offset
    end = start + pagination.limit
    paginated_notifications = filtered_notifications[start:end]
    
    # Convert to response format
    items = []
    for notif in paginated_notifications:
        items.append(NotificationResponse(
            id=notif["id"],
            type=notif["type"],
            title=notif["title"],
            message=notif["message"],
            icon=notif["icon"],
            priority=notif["priority"],
            resource_type=notif.get("resource_type"),
            resource_id=notif.get("resource_id"),
            resource_name=notif.get("resource_name"),
            action_url=notif.get("action_url"),
            is_read=notif.get("is_read", False),
            metadata=notif.get("metadata", {}),
            created_at=datetime.fromisoformat(notif["created_at"]),
            read_at=datetime.fromisoformat(notif["read_at"]) if notif.get("read_at") else None
        ))
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        size=pagination.limit,
        pages=(total + pagination.limit - 1) // pagination.limit
    )


@router.post("/mark-read/{notification_id}")
async def mark_notification_read(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Mark a notification as read"""
    user_id = UUID(current_user["user_id"])
    user = await db.get(User, user_id)
    
    if not user or not user.metadata or "notifications" not in user.metadata:
        raise HTTPException(status_code=404, detail="Notifications not found")
    
    # Find and update notification
    notification_found = False
    for notif in user.metadata["notifications"]:
        if notif["id"] == notification_id:
            notif["is_read"] = True
            notif["read_at"] = datetime.utcnow().isoformat()
            notification_found = True
            break
    
    if not notification_found:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    # Update unread count
    unread_count = sum(1 for n in user.metadata["notifications"] 
                     if not n.get("is_read", False) and not n.get("is_archived", False))
    user.metadata["unread_notifications"] = unread_count
    
    await db.commit()
    
    # Send real-time update
    await manager.send_personal_message({
        "type": "notification_read",
        "data": {"notification_id": notification_id, "unread_count": unread_count}
    }, str(user_id))
    
    return {"message": "Notification marked as read"}


@router.post("/mark-all-read")
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Mark all notifications as read"""
    user_id = UUID(current_user["user_id"])
    user = await db.get(User, user_id)
    
    if not user or not user.metadata or "notifications" not in user.metadata:
        return {"message": "No notifications to mark as read"}
    
    # Mark all as read
    read_at = datetime.utcnow().isoformat()
    for notif in user.metadata["notifications"]:
        if not notif.get("is_read", False) and not notif.get("is_archived", False):
            notif["is_read"] = True
            notif["read_at"] = read_at
    
    # Update unread count
    user.metadata["unread_notifications"] = 0
    
    await db.commit()
    
    # Send real-time update
    await manager.send_personal_message({
        "type": "all_notifications_read",
        "data": {"unread_count": 0}
    }, str(user_id))
    
    return {"message": "All notifications marked as read"}


@router.delete("/{notification_id}")
async def archive_notification(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Archive (soft delete) a notification"""
    user_id = UUID(current_user["user_id"])
    user = await db.get(User, user_id)
    
    if not user or not user.metadata or "notifications" not in user.metadata:
        raise HTTPException(status_code=404, detail="Notifications not found")
    
    # Find and archive notification
    notification_found = False
    for notif in user.metadata["notifications"]:
        if notif["id"] == notification_id:
            notif["is_archived"] = True
            notification_found = True
            break
    
    if not notification_found:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    # Update unread count if necessary
    unread_count = sum(1 for n in user.metadata["notifications"] 
                     if not n.get("is_read", False) and not n.get("is_archived", False))
    user.metadata["unread_notifications"] = unread_count
    
    await db.commit()
    
    return {"message": "Notification archived"}


@router.get("/preferences", response_model=NotificationPreferences)
async def get_notification_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get user's notification preferences"""
    user_id = UUID(current_user["user_id"])
    user = await db.get(User, user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get preferences from user metadata
    preferences = user.metadata.get("notification_preferences", {}) if user.metadata else {}
    
    # Set defaults
    default_preferences = {
        "email_enabled": True,
        "push_enabled": True,
        "in_app_enabled": True,
        "email_frequency": "immediate",  # immediate, daily, weekly
        "notification_types": {
            "asset_updates": True,
            "project_updates": True,
            "comments": True,
            "system_alerts": True,
            "workflow_updates": True
        },
        "quiet_hours": {
            "enabled": False,
            "start_time": "22:00",
            "end_time": "08:00",
            "timezone": "UTC"
        }
    }
    
    # Merge with defaults
    for key, value in default_preferences.items():
        if key not in preferences:
            preferences[key] = value
    
    return NotificationPreferences(**preferences)


@router.put("/preferences")
async def update_notification_preferences(
    preferences: NotificationPreferences,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update user's notification preferences"""
    user_id = UUID(current_user["user_id"])
    user = await db.get(User, user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.metadata:
        user.metadata = {}
    
    # Update preferences
    user.metadata["notification_preferences"] = preferences.dict()
    
    await db.commit()
    
    return {"message": "Preferences updated successfully"}


@router.get("/unread-count")
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get count of unread notifications"""
    user_id = UUID(current_user["user_id"])
    user = await db.get(User, user_id)
    
    if not user or not user.metadata:
        return {"unread_count": 0}
    
    unread_count = user.metadata.get("unread_notifications", 0)
    
    return {"unread_count": unread_count}


@router.post("/test")
async def send_test_notification(
    notification_data: NotificationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Send a test notification (for testing purposes)"""
    user_id = UUID(current_user["user_id"])
    
    notification = await create_notification(
        user_id=user_id,
        notification_type=notification_data.type,
        title=notification_data.title,
        message=notification_data.message,
        priority=notification_data.priority,
        metadata=notification_data.metadata,
        db=db
    )
    
    return {
        "message": "Test notification sent",
        "notification_id": notification.id
    }


# Helper function to send notifications from other services
async def send_notification(
    user_ids: List[UUID],
    notification_type: str,
    title: Optional[str] = None,
    message: str = "",
    resource_type: Optional[str] = None,
    resource_id: Optional[UUID] = None,
    priority: str = "normal",
    metadata: Optional[Dict[str, Any]] = None,
    db: AsyncSession = None
):
    """Send notification to multiple users"""
    for user_id in user_ids:
        try:
            await create_notification(
                user_id=user_id,
                notification_type=notification_type,
                title=title,
                message=message,
                resource_type=resource_type,
                resource_id=resource_id,
                priority=priority,
                metadata=metadata,
                db=db
            )
        except Exception as e:
            logger.error(
                "notification_send_failed",
                user_id=str(user_id),
                notification_type=notification_type,
                error=str(e)
            )


# Export for use by other modules
__all__ = ["router", "send_notification", "manager"]