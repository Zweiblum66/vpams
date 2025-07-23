"""
Tests for notification routes and WebSocket functionality
"""

import pytest
import json
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient
from fastapi import WebSocket
from fastapi.testclient import TestClient

from src.db.models import User
from src.api.notification_routes import (
    create_notification, send_notification, manager, Notification,
    NOTIFICATION_TYPES
)
from src.models.schemas import NotificationPreferences


@pytest.fixture
def mock_user():
    """Create a mock user for testing"""
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.metadata = {
        "notifications": [],
        "unread_notifications": 0,
        "notification_preferences": {
            "email_enabled": True,
            "push_enabled": True,
            "in_app_enabled": True,
            "email_frequency": "immediate",
            "notification_types": {
                "asset_updates": True,
                "project_updates": True,
                "comments": True,
                "system_alerts": True,
                "workflow_updates": True
            }
        }
    }
    return user


@pytest.mark.asyncio
async def test_create_notification(mock_user):
    """Test notification creation"""
    # Mock database session
    db = AsyncMock(spec=AsyncSession)
    db.get = AsyncMock(return_value=mock_user)
    db.commit = AsyncMock()
    
    # Create notification
    notification = await create_notification(
        user_id=mock_user.id,
        notification_type="asset.created",
        title="New Asset",
        message="A new asset has been created",
        resource_type="asset",
        resource_id=uuid4(),
        priority="normal",
        metadata={"test": "data"},
        db=db
    )
    
    # Verify notification created
    assert notification.type == "asset.created"
    assert notification.title == "New Asset"
    assert notification.message == "A new asset has been created"
    assert notification.priority == "normal"
    assert notification.metadata["test"] == "data"
    
    # Verify notification added to user
    assert len(mock_user.metadata["notifications"]) == 1
    assert mock_user.metadata["unread_notifications"] == 1
    
    # Verify database operations
    db.get.assert_called_once_with(User, mock_user.id)
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_send_notification_multiple_users(mock_user):
    """Test sending notifications to multiple users"""
    # Mock database session
    db = AsyncMock(spec=AsyncSession)
    db.get = AsyncMock(return_value=mock_user)
    db.commit = AsyncMock()
    
    user_ids = [uuid4() for _ in range(3)]
    
    # Send notifications
    await send_notification(
        user_ids=user_ids,
        notification_type="system.update",
        title="System Update",
        message="System will be updated tonight",
        priority="high",
        db=db
    )
    
    # Verify database operations
    assert db.get.call_count == 3
    assert db.commit.call_count == 3


@pytest.mark.asyncio
async def test_get_notifications(client: AsyncClient, auth_headers, mock_user):
    """Test getting notifications list"""
    # Add test notifications to user
    mock_user.metadata["notifications"] = [
        {
            "id": str(uuid4()),
            "type": "asset.created",
            "title": "New Asset",
            "message": "Asset uploaded",
            "icon": "file_upload",
            "priority": "normal",
            "is_read": False,
            "created_at": datetime.utcnow().isoformat(),
            "metadata": {}
        },
        {
            "id": str(uuid4()),
            "type": "project.shared",
            "title": "Project Shared",
            "message": "Project shared with you",
            "icon": "folder_shared",
            "priority": "high",
            "is_read": True,
            "created_at": datetime.utcnow().isoformat(),
            "metadata": {}
        }
    ]
    mock_user.metadata["unread_notifications"] = 1
    
    with patch("src.api.notification_routes.get_db") as mock_get_db:
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.get = AsyncMock(return_value=mock_user)
        mock_get_db.return_value = mock_db
        
        # Get all notifications
        response = await client.get(
            "/api/v1/notifications",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        
        # Get unread only
        response = await client.get(
            "/api/v1/notifications?is_read=false",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["is_read"] is False


@pytest.mark.asyncio
async def test_mark_notification_read(client: AsyncClient, auth_headers, mock_user):
    """Test marking notification as read"""
    notification_id = str(uuid4())
    mock_user.metadata["notifications"] = [
        {
            "id": notification_id,
            "type": "asset.created",
            "title": "New Asset",
            "message": "Asset uploaded",
            "icon": "file_upload",
            "priority": "normal",
            "is_read": False,
            "created_at": datetime.utcnow().isoformat(),
            "metadata": {}
        }
    ]
    mock_user.metadata["unread_notifications"] = 1
    
    with patch("src.api.notification_routes.get_db") as mock_get_db:
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.get = AsyncMock(return_value=mock_user)
        mock_db.commit = AsyncMock()
        mock_get_db.return_value = mock_db
        
        response = await client.post(
            f"/api/v1/notifications/mark-read/{notification_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert mock_user.metadata["notifications"][0]["is_read"] is True
        assert mock_user.metadata["unread_notifications"] == 0
        mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_mark_all_notifications_read(client: AsyncClient, auth_headers, mock_user):
    """Test marking all notifications as read"""
    mock_user.metadata["notifications"] = [
        {
            "id": str(uuid4()),
            "type": "asset.created",
            "title": "New Asset",
            "message": "Asset uploaded",
            "icon": "file_upload",
            "priority": "normal",
            "is_read": False,
            "created_at": datetime.utcnow().isoformat(),
            "metadata": {}
        },
        {
            "id": str(uuid4()),
            "type": "project.shared",
            "title": "Project Shared",
            "message": "Project shared with you",
            "icon": "folder_shared",
            "priority": "high",
            "is_read": False,
            "created_at": datetime.utcnow().isoformat(),
            "metadata": {}
        }
    ]
    mock_user.metadata["unread_notifications"] = 2
    
    with patch("src.api.notification_routes.get_db") as mock_get_db:
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.get = AsyncMock(return_value=mock_user)
        mock_db.commit = AsyncMock()
        mock_get_db.return_value = mock_db
        
        response = await client.post(
            "/api/v1/notifications/mark-all-read",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert all(n["is_read"] for n in mock_user.metadata["notifications"])
        assert mock_user.metadata["unread_notifications"] == 0
        mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_archive_notification(client: AsyncClient, auth_headers, mock_user):
    """Test archiving a notification"""
    notification_id = str(uuid4())
    mock_user.metadata["notifications"] = [
        {
            "id": notification_id,
            "type": "asset.created",
            "title": "New Asset",
            "message": "Asset uploaded",
            "icon": "file_upload",
            "priority": "normal",
            "is_read": False,
            "is_archived": False,
            "created_at": datetime.utcnow().isoformat(),
            "metadata": {}
        }
    ]
    mock_user.metadata["unread_notifications"] = 1
    
    with patch("src.api.notification_routes.get_db") as mock_get_db:
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.get = AsyncMock(return_value=mock_user)
        mock_db.commit = AsyncMock()
        mock_get_db.return_value = mock_db
        
        response = await client.delete(
            f"/api/v1/notifications/{notification_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert mock_user.metadata["notifications"][0]["is_archived"] is True
        mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_notification_preferences(client: AsyncClient, auth_headers, mock_user):
    """Test getting notification preferences"""
    with patch("src.api.notification_routes.get_db") as mock_get_db:
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.get = AsyncMock(return_value=mock_user)
        mock_get_db.return_value = mock_db
        
        response = await client.get(
            "/api/v1/notifications/preferences",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email_enabled"] is True
        assert data["push_enabled"] is True
        assert data["in_app_enabled"] is True
        assert data["email_frequency"] == "immediate"
        assert data["notification_types"]["asset_updates"] is True


@pytest.mark.asyncio
async def test_update_notification_preferences(client: AsyncClient, auth_headers, mock_user):
    """Test updating notification preferences"""
    with patch("src.api.notification_routes.get_db") as mock_get_db:
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.get = AsyncMock(return_value=mock_user)
        mock_db.commit = AsyncMock()
        mock_get_db.return_value = mock_db
        
        new_preferences = {
            "email_enabled": False,
            "push_enabled": True,
            "in_app_enabled": True,
            "email_frequency": "daily",
            "notification_types": {
                "asset_updates": False,
                "project_updates": True,
                "comments": True,
                "system_alerts": True,
                "workflow_updates": False
            },
            "quiet_hours": {
                "enabled": True,
                "start_time": "22:00",
                "end_time": "08:00",
                "timezone": "UTC"
            }
        }
        
        response = await client.put(
            "/api/v1/notifications/preferences",
            json=new_preferences,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert mock_user.metadata["notification_preferences"]["email_enabled"] is False
        assert mock_user.metadata["notification_preferences"]["email_frequency"] == "daily"
        assert mock_user.metadata["notification_preferences"]["quiet_hours"]["enabled"] is True
        mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_unread_count(client: AsyncClient, auth_headers, mock_user):
    """Test getting unread notification count"""
    mock_user.metadata["unread_notifications"] = 5
    
    with patch("src.api.notification_routes.get_db") as mock_get_db:
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.get = AsyncMock(return_value=mock_user)
        mock_get_db.return_value = mock_db
        
        response = await client.get(
            "/api/v1/notifications/unread-count",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["unread_count"] == 5


@pytest.mark.asyncio
async def test_send_test_notification(client: AsyncClient, auth_headers, mock_user):
    """Test sending a test notification"""
    with patch("src.api.notification_routes.get_db") as mock_get_db:
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.get = AsyncMock(return_value=mock_user)
        mock_db.commit = AsyncMock()
        mock_get_db.return_value = mock_db
        
        test_notification = {
            "type": "test.notification",
            "title": "Test Notification",
            "message": "This is a test notification",
            "priority": "normal",
            "metadata": {"test": True}
        }
        
        response = await client.post(
            "/api/v1/notifications/test",
            json=test_notification,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "notification_id" in data
        assert len(mock_user.metadata["notifications"]) == 1
        mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_notification_expiration():
    """Test that expired notifications are filtered out"""
    mock_user = MagicMock(spec=User)
    mock_user.id = uuid4()
    mock_user.metadata = {
        "notifications": [
            {
                "id": str(uuid4()),
                "type": "asset.created",
                "title": "Old Notification",
                "message": "This should be filtered",
                "icon": "file_upload",
                "priority": "normal",
                "is_read": False,
                "is_archived": False,
                "created_at": (datetime.utcnow() - timedelta(days=40)).isoformat(),
                "expires_at": (datetime.utcnow() - timedelta(days=10)).isoformat(),
                "metadata": {}
            },
            {
                "id": str(uuid4()),
                "type": "asset.created",
                "title": "Current Notification",
                "message": "This should be visible",
                "icon": "file_upload",
                "priority": "normal",
                "is_read": False,
                "is_archived": False,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(days=20)).isoformat(),
                "metadata": {}
            }
        ],
        "unread_notifications": 2
    }
    
    # Create a mock client to test the filtering logic
    from src.api.notification_routes import router
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    
    app = FastAPI()
    app.include_router(router)
    
    with TestClient(app) as test_client:
        with patch("src.api.notification_routes.get_db") as mock_get_db:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_db.get = AsyncMock(return_value=mock_user)
            mock_get_db.return_value = mock_db
            
            with patch("src.api.dependencies.get_current_user") as mock_get_current_user:
                mock_get_current_user.return_value = {"user_id": str(mock_user.id)}
                
                response = test_client.get(
                    "/api/v1/notifications",
                    headers={"Authorization": "Bearer test-token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["total"] == 1  # Only one non-expired notification
                assert data["items"][0]["title"] == "Current Notification"


def test_notification_types():
    """Test that all notification types are properly defined"""
    required_types = [
        "asset.created", "asset.updated", "asset.deleted", "asset.shared",
        "project.shared", "project.updated",
        "timeline.updated", "timeline.version_saved",
        "system.maintenance", "system.update",
        "workflow.started", "workflow.completed", "workflow.failed"
    ]
    
    for notification_type in required_types:
        assert notification_type in NOTIFICATION_TYPES
        assert "title" in NOTIFICATION_TYPES[notification_type]
        assert "icon" in NOTIFICATION_TYPES[notification_type]


def test_notification_model():
    """Test Notification model initialization"""
    notification_data = {
        "user_id": str(uuid4()),
        "type": "asset.created",
        "title": "Test Title",
        "message": "Test Message",
        "priority": "high",
        "metadata": {"key": "value"}
    }
    
    notification = Notification(notification_data)
    
    assert notification.user_id == notification_data["user_id"]
    assert notification.type == notification_data["type"]
    assert notification.title == notification_data["title"]
    assert notification.message == notification_data["message"]
    assert notification.priority == notification_data["priority"]
    assert notification.metadata == notification_data["metadata"]
    assert notification.is_read is False
    assert notification.is_archived is False
    assert isinstance(notification.created_at, datetime)


@pytest.mark.asyncio
async def test_websocket_connection():
    """Test WebSocket connection and disconnection"""
    from src.api.notification_routes import manager
    
    # Mock WebSocket
    websocket = AsyncMock(spec=WebSocket)
    websocket.accept = AsyncMock()
    websocket.send_json = AsyncMock()
    
    user_id = str(uuid4())
    
    # Test connection
    await manager.connect(websocket, user_id)
    websocket.accept.assert_called_once()
    assert user_id in manager.active_connections
    assert user_id in manager.user_subscriptions
    
    # Test disconnection
    manager.disconnect(user_id)
    assert user_id not in manager.active_connections
    assert user_id not in manager.user_subscriptions


@pytest.mark.asyncio
async def test_websocket_messaging():
    """Test WebSocket message handling"""
    from src.api.notification_routes import manager
    
    # Mock WebSocket
    websocket = AsyncMock(spec=WebSocket)
    websocket.accept = AsyncMock()
    websocket.send_json = AsyncMock()
    
    user_id = str(uuid4())
    
    # Connect
    await manager.connect(websocket, user_id)
    
    # Test personal message
    test_message = {"type": "test", "data": {"message": "Hello"}}
    await manager.send_personal_message(test_message, user_id)
    websocket.send_json.assert_called_with(test_message)
    
    # Test subscription
    manager.subscribe(user_id, "test-channel")
    assert "test-channel" in manager.user_subscriptions[user_id]
    
    # Test unsubscription
    manager.unsubscribe(user_id, "test-channel")
    assert "test-channel" not in manager.user_subscriptions[user_id]
    
    # Clean up
    manager.disconnect(user_id)