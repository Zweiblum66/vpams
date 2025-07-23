"""
Tests for activity tracking API routes
"""

import pytest
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from src.db.models import (
    User, Asset, ProjectContainer,
    AssetType, AssetStatus, ContainerType
)
from src.api.activity_routes import log_activity


@pytest.fixture
async def test_user_with_activities(db_session: AsyncSession, test_user):
    """Create a test user with some activity logs"""
    user_id = UUID(test_user["user_id"])
    user = await db_session.get(User, user_id)
    
    # Add sample activities
    activities = [
        {
            "activity_type": "asset.created",
            "resource_type": "asset",
            "resource_id": str(uuid4()),
            "resource_name": "test-image.jpg",
            "description": "Created asset",
            "created_at": (datetime.utcnow() - timedelta(hours=1)).isoformat()
        },
        {
            "activity_type": "asset.viewed",
            "resource_type": "asset",
            "resource_id": str(uuid4()),
            "resource_name": "video-file.mp4",
            "description": "Viewed asset",
            "created_at": (datetime.utcnow() - timedelta(hours=2)).isoformat()
        },
        {
            "activity_type": "container.created",
            "resource_type": "container",
            "resource_id": str(uuid4()),
            "resource_name": "New Project",
            "description": "Created container",
            "created_at": (datetime.utcnow() - timedelta(hours=3)).isoformat()
        },
        {
            "activity_type": "user.login",
            "resource_type": "user",
            "resource_id": None,
            "description": "Logged in",
            "created_at": (datetime.utcnow() - timedelta(hours=4)).isoformat()
        }
    ]
    
    # Add ID to each activity
    for activity in activities:
        activity["id"] = str(uuid4())
        activity["metadata"] = {}
        activity["ip_address"] = "127.0.0.1"
        activity["user_agent"] = "Test Client"
    
    user.metadata = {"activity_log": activities}
    await db_session.commit()
    
    return {"user": user, "activities": activities}


class TestActivityLogging:
    """Test activity logging functionality"""
    
    async def test_log_activity(
        self,
        db_session: AsyncSession,
        test_user
    ):
        """Test logging a new activity"""
        user_id = UUID(test_user["user_id"])
        resource_id = uuid4()
        
        # Create an asset for testing
        asset = Asset(
            id=resource_id,
            name="test-asset.jpg",
            display_name="Test Asset",
            file_path="/storage/test-asset.jpg",
            file_size=100000,
            asset_type=AssetType.IMAGE,
            status=AssetStatus.ACTIVE,
            storage_driver="local",
            storage_path="/storage/test-asset.jpg",
            owner_id=user_id
        )
        db_session.add(asset)
        await db_session.commit()
        
        # Log activity
        activity = await log_activity(
            activity_type="asset.viewed",
            resource_type="asset",
            resource_id=resource_id,
            user_id=user_id,
            description="Viewed test asset",
            metadata={"source": "test"},
            db=db_session,
            request_info={"ip_address": "192.168.1.1", "user_agent": "Test Agent"}
        )
        
        assert activity.activity_type == "asset.viewed"
        assert activity.resource_type == "asset"
        assert activity.resource_id == resource_id
        assert activity.resource_name == "Test Asset"
        assert activity.metadata["source"] == "test"
        
        # Check it was saved to user metadata
        user = await db_session.get(User, user_id)
        assert "activity_log" in user.metadata
        assert len(user.metadata["activity_log"]) == 1
        assert user.metadata["activity_log"][0]["id"] == activity.id


class TestActivityRetrieval:
    """Test getting activities"""
    
    async def test_get_user_activities(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user_with_activities
    ):
        """Test getting activities for current user"""
        response = await client.get(
            "/api/v1/activities/",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 4
        assert len(data["items"]) == 4
        
        # Check order (most recent first)
        assert data["items"][0]["activity_type"] == "asset.created"
        assert data["items"][3]["activity_type"] == "user.login"
    
    async def test_filter_activities_by_type(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user_with_activities
    ):
        """Test filtering activities by type"""
        response = await client.get(
            "/api/v1/activities/?activity_types=asset.created&activity_types=asset.viewed",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all(item["activity_type"].startswith("asset.") for item in data["items"])
    
    async def test_filter_activities_by_resource_type(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user_with_activities
    ):
        """Test filtering activities by resource type"""
        response = await client.get(
            "/api/v1/activities/?resource_type=asset",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all(item["resource_type"] == "asset" for item in data["items"])
    
    async def test_filter_activities_by_date_range(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user_with_activities
    ):
        """Test filtering activities by date range"""
        # Get activities from last 2.5 hours
        start_date = (datetime.utcnow() - timedelta(hours=2, minutes=30)).isoformat()
        
        response = await client.get(
            f"/api/v1/activities/?start_date={start_date}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2  # Only activities from last 2.5 hours
    
    async def test_pagination(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user_with_activities
    ):
        """Test activity pagination"""
        response = await client.get(
            "/api/v1/activities/?page=1&limit=2",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 4
        assert len(data["items"]) == 2
        assert data["pages"] == 2


class TestActivitySummary:
    """Test activity summary endpoint"""
    
    async def test_get_activity_summary(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user_with_activities
    ):
        """Test getting activity summary"""
        response = await client.get(
            "/api/v1/activities/summary?time_period=day",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_activities"] == 1  # Only 1 activity in last day
        assert "asset.created" in data["activities_by_type"]
        assert "asset" in data["activities_by_resource"]
        assert "most_active_hours" in data
        assert "recent_resources" in data
    
    async def test_activity_summary_week(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user_with_activities
    ):
        """Test weekly activity summary"""
        response = await client.get(
            "/api/v1/activities/summary?time_period=week",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_activities"] == 4  # All activities in last week
        assert len(data["activities_by_type"]) == 4
        assert data["activities_by_resource"]["asset"] == 2
        assert data["activities_by_resource"]["container"] == 1
        assert data["activities_by_resource"]["user"] == 1


class TestActivityTimeline:
    """Test activity timeline endpoint"""
    
    async def test_get_activity_timeline(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user_with_activities
    ):
        """Test getting activity timeline"""
        response = await client.get(
            "/api/v1/activities/timeline?days=7",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        timeline = response.json()
        assert len(timeline) >= 1  # At least today
        
        # Check structure
        today = timeline[0]
        assert "date" in today
        assert "total_count" in today
        assert "activities" in today
        assert today["total_count"] == len(today["activities"])
        
        # Check activity structure
        if today["activities"]:
            activity = today["activities"][0]
            assert "id" in activity
            assert "time" in activity
            assert "type" in activity
            assert "resource_type" in activity
            assert "description" in activity


class TestResourceActivities:
    """Test getting activities for specific resources"""
    
    async def test_get_asset_activities(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user
    ):
        """Test getting activities for a specific asset"""
        user_id = UUID(test_user["user_id"])
        
        # Create an asset
        asset = Asset(
            id=uuid4(),
            name="tracked-asset.jpg",
            display_name="Tracked Asset",
            file_path="/storage/tracked-asset.jpg",
            file_size=100000,
            asset_type=AssetType.IMAGE,
            status=AssetStatus.ACTIVE,
            storage_driver="local",
            storage_path="/storage/tracked-asset.jpg",
            owner_id=user_id
        )
        db_session.add(asset)
        await db_session.commit()
        
        # Log some activities for this asset
        await log_activity(
            activity_type="asset.created",
            resource_type="asset",
            resource_id=asset.id,
            user_id=user_id,
            db=db_session
        )
        
        await log_activity(
            activity_type="asset.viewed",
            resource_type="asset",
            resource_id=asset.id,
            user_id=user_id,
            db=db_session
        )
        
        # Get activities for this asset
        response = await client.get(
            f"/api/v1/activities/resource/asset/{asset.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        activities = response.json()
        assert len(activities) == 2
        assert activities[0]["activity_type"] == "asset.viewed"  # Most recent first
        assert activities[1]["activity_type"] == "asset.created"
        assert all(a["resource_id"] == str(asset.id) for a in activities)
    
    async def test_get_activities_access_denied(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession
    ):
        """Test access denied when getting activities for others' resources"""
        # Create an asset owned by another user
        other_user_id = uuid4()
        asset = Asset(
            id=uuid4(),
            name="other-asset.jpg",
            display_name="Other Asset",
            file_path="/storage/other-asset.jpg",
            file_size=100000,
            asset_type=AssetType.IMAGE,
            status=AssetStatus.ACTIVE,
            storage_driver="local",
            storage_path="/storage/other-asset.jpg",
            owner_id=other_user_id
        )
        db_session.add(asset)
        await db_session.commit()
        
        # Try to get activities
        response = await client.get(
            f"/api/v1/activities/resource/asset/{asset.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]


class TestActivityExport:
    """Test activity export functionality"""
    
    async def test_export_activities_json(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user_with_activities
    ):
        """Test exporting activities as JSON"""
        response = await client.post(
            "/api/v1/activities/export?format=json",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "export_date" in data
        assert "user_id" in data
        assert "total_activities" in data
        assert data["total_activities"] == 4
        assert len(data["activities"]) == 4
    
    async def test_export_activities_csv(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user_with_activities
    ):
        """Test exporting activities as CSV"""
        response = await client.post(
            "/api/v1/activities/export?format=csv",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "csv"
        assert "content_length" in data
        assert "preview" in data
        assert "Date,Time,Activity Type" in data["preview"]
    
    async def test_export_filtered_activities(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user_with_activities
    ):
        """Test exporting filtered activities"""
        response = await client.post(
            "/api/v1/activities/export?format=json&resource_type=asset",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_activities"] == 2
        assert all(a["resource_type"] == "asset" for a in data["activities"])


class TestPermissions:
    """Test permission checks"""
    
    async def test_activities_without_auth(
        self,
        client: AsyncClient
    ):
        """Test that authentication is required"""
        response = await client.get("/api/v1/activities/")
        assert response.status_code == 401
    
    async def test_admin_view_all_activities(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user_with_activities,
        db_session: AsyncSession
    ):
        """Test admin can view activities from all users"""
        # This would require setting up admin user and testing include_all_users parameter
        # Simplified for MVP
        pass


# Add missing import
from uuid import UUID