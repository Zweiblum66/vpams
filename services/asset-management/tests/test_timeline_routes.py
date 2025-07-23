"""
Tests for timeline API routes
"""

import pytest
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import (
    ProjectContainer, Asset, ShotItem, SequenceTimeline,
    ContainerType, AssetType, AssetStatus
)
from src.models.schemas import TimelineItemCreate


@pytest.fixture
async def test_sequence(db_session: AsyncSession, test_user):
    """Create a test sequence container"""
    sequence = ProjectContainer(
        id=uuid4(),
        name="test-sequence",
        display_name="Test Sequence",
        container_type=ContainerType.SEQUENCE,
        owner_id=test_user["user_id"]
    )
    db_session.add(sequence)
    await db_session.commit()
    return sequence


@pytest.fixture
async def test_video_asset(db_session: AsyncSession, test_user):
    """Create a test video asset"""
    asset = Asset(
        id=uuid4(),
        name="test-video.mp4",
        display_name="Test Video",
        file_path="/storage/test-video.mp4",
        file_size=1000000,
        asset_type=AssetType.VIDEO,
        status=AssetStatus.ACTIVE,
        storage_driver="local",
        storage_path="/storage/test-video.mp4",
        owner_id=test_user["user_id"],
        technical_metadata={
            "duration": 120.5,
            "resolution": "1920x1080",
            "framerate": 25
        }
    )
    db_session.add(asset)
    await db_session.commit()
    return asset


@pytest.fixture
async def test_shot(db_session: AsyncSession, test_sequence, test_video_asset, test_user):
    """Create a test shot item"""
    shot = ShotItem(
        id=uuid4(),
        container_id=test_sequence.id,  # Shot in sequence for timeline testing
        asset_id=test_video_asset.id,
        name="Test Shot",
        description="A test shot item",
        in_point=0,
        out_point=5000,  # 5 seconds at 1000 timebase
        duration=5000,
        created_by=test_user["user_id"]
    )
    db_session.add(shot)
    await db_session.commit()
    return shot


@pytest.fixture
async def test_timeline_item(db_session: AsyncSession, test_sequence, test_shot):
    """Create a test timeline item"""
    timeline_item = SequenceTimeline(
        id=uuid4(),
        sequence_id=test_sequence.id,
        clip_id=test_shot.id,
        track_number=0,
        track_type="video",
        track_name="V1",
        start_time=0,
        end_time=5000,
        speed=1.0,
        is_enabled=True,
        is_locked=False,
        opacity=1.0
    )
    db_session.add(timeline_item)
    await db_session.commit()
    return timeline_item


class TestTimelineItemCreation:
    """Test timeline item creation"""
    
    async def test_create_timeline_item(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence,
        test_shot
    ):
        """Test creating a timeline item"""
        timeline_data = {
            "sequence_id": str(test_sequence.id),
            "clip_id": str(test_shot.id),
            "track_number": 1,
            "track_type": "video",
            "track_name": "V2",
            "start_time": 5000,
            "end_time": 10000,
            "speed": 1.0,
            "is_enabled": True,
            "is_locked": False,
            "opacity": 1.0
        }
        
        response = await client.post(
            f"/api/v1/timelines/{test_sequence.id}/items",
            json=timeline_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["track_number"] == 1
        assert data["track_type"] == "video"
        assert data["start_time"] == 5000
        assert data["end_time"] == 10000
        assert data["clip_name"] == test_shot.name
        assert data["clip_asset_id"] == str(test_shot.asset_id)
    
    async def test_create_timeline_item_with_effects(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence,
        test_shot
    ):
        """Test creating a timeline item with effects and transitions"""
        timeline_data = {
            "sequence_id": str(test_sequence.id),
            "clip_id": str(test_shot.id),
            "track_number": 0,
            "track_type": "video",
            "start_time": 10000,
            "end_time": 15000,
            "speed": 2.0,
            "effects": [
                {"type": "color_correction", "params": {"brightness": 1.2}},
                {"type": "blur", "params": {"radius": 5}}
            ],
            "transition_in": {"type": "fade", "duration": 1000},
            "transition_out": {"type": "dissolve", "duration": 500}
        }
        
        response = await client.post(
            f"/api/v1/timelines/{test_sequence.id}/items",
            json=timeline_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["speed"] == 2.0
        assert len(data["effects"]) == 2
        assert data["transition_in"]["type"] == "fade"
        assert data["transition_out"]["type"] == "dissolve"
    
    async def test_create_overlapping_timeline_item(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence,
        test_shot,
        test_timeline_item
    ):
        """Test that overlapping timeline items are rejected"""
        timeline_data = {
            "sequence_id": str(test_sequence.id),
            "clip_id": str(test_shot.id),
            "track_number": 0,  # Same track as existing item
            "track_type": "video",
            "start_time": 2500,  # Overlaps with existing item (0-5000)
            "end_time": 7500
        }
        
        response = await client.post(
            f"/api/v1/timelines/{test_sequence.id}/items",
            json=timeline_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "overlaps with existing clip" in response.json()["detail"]
    
    async def test_create_timeline_item_invalid_sequence_type(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_shot,
        test_user,
        db_session: AsyncSession
    ):
        """Test creating timeline item in non-sequence container"""
        # Create a shotlist container (not valid for timelines)
        shotlist = ProjectContainer(
            id=uuid4(),
            name="test-shotlist",
            display_name="Test Shotlist",
            container_type=ContainerType.SHOTLIST,
            owner_id=test_user["user_id"]
        )
        db_session.add(shotlist)
        await db_session.commit()
        
        timeline_data = {
            "sequence_id": str(shotlist.id),
            "clip_id": str(test_shot.id),
            "track_number": 0,
            "track_type": "video",
            "start_time": 0,
            "end_time": 1000
        }
        
        response = await client.post(
            f"/api/v1/timelines/{shotlist.id}/items",
            json=timeline_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "Container is not a sequence" in response.json()["detail"]
    
    async def test_create_timeline_invalid_time(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence,
        test_shot
    ):
        """Test creating timeline item with invalid time range"""
        timeline_data = {
            "sequence_id": str(test_sequence.id),
            "clip_id": str(test_shot.id),
            "track_number": 0,
            "track_type": "video",
            "start_time": 5000,
            "end_time": 5000  # Same as start time
        }
        
        response = await client.post(
            f"/api/v1/timelines/{test_sequence.id}/items",
            json=timeline_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "End time must be greater than start time" in response.json()["detail"]


class TestTimelineItemRetrieval:
    """Test timeline item retrieval"""
    
    async def test_get_sequence_timeline(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence,
        test_timeline_item
    ):
        """Test getting all timeline items in a sequence"""
        response = await client.get(
            f"/api/v1/timelines/{test_sequence.id}/items",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == str(test_timeline_item.id)
        assert data[0]["track_number"] == test_timeline_item.track_number
        assert data[0]["clip_name"] is not None
    
    async def test_get_timeline_by_track(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence,
        test_shot,
        db_session: AsyncSession
    ):
        """Test filtering timeline items by track"""
        # Create items on different tracks
        video_item = SequenceTimeline(
            sequence_id=test_sequence.id,
            clip_id=test_shot.id,
            track_number=0,
            track_type="video",
            start_time=0,
            end_time=1000
        )
        audio_item = SequenceTimeline(
            sequence_id=test_sequence.id,
            clip_id=test_shot.id,
            track_number=0,
            track_type="audio",
            start_time=0,
            end_time=1000
        )
        db_session.add_all([video_item, audio_item])
        await db_session.commit()
        
        # Get only video tracks
        response = await client.get(
            f"/api/v1/timelines/{test_sequence.id}/items?track_type=video",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert all(item["track_type"] == "video" for item in data)
        
        # Get specific track number
        response = await client.get(
            f"/api/v1/timelines/{test_sequence.id}/items?track_number=0",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert all(item["track_number"] == 0 for item in data)
    
    async def test_get_single_timeline_item(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_timeline_item
    ):
        """Test getting a single timeline item"""
        response = await client.get(
            f"/api/v1/timelines/items/{test_timeline_item.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_timeline_item.id)
        assert data["start_time"] == test_timeline_item.start_time
        assert data["end_time"] == test_timeline_item.end_time
    
    async def test_get_nonexistent_timeline_item(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """Test getting a nonexistent timeline item"""
        response = await client.get(
            f"/api/v1/timelines/items/{uuid4()}",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        assert "Timeline item not found" in response.json()["detail"]


class TestTimelineItemUpdate:
    """Test timeline item updates"""
    
    async def test_update_timeline_item(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_timeline_item
    ):
        """Test updating a timeline item"""
        update_data = {
            "start_time": 1000,
            "end_time": 6000,
            "speed": 1.5,
            "opacity": 0.8
        }
        
        response = await client.put(
            f"/api/v1/timelines/items/{test_timeline_item.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["start_time"] == 1000
        assert data["end_time"] == 6000
        assert data["speed"] == 1.5
        assert data["opacity"] == 0.8
    
    async def test_update_locked_timeline_item(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence,
        test_shot,
        db_session: AsyncSession
    ):
        """Test that locked timeline items cannot be updated"""
        # Create a locked item
        locked_item = SequenceTimeline(
            sequence_id=test_sequence.id,
            clip_id=test_shot.id,
            track_number=0,
            track_type="video",
            start_time=0,
            end_time=1000,
            is_locked=True
        )
        db_session.add(locked_item)
        await db_session.commit()
        
        update_data = {"start_time": 500}
        
        response = await client.put(
            f"/api/v1/timelines/items/{locked_item.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "Timeline item is locked" in response.json()["detail"]
    
    async def test_unlock_timeline_item(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence,
        test_shot,
        db_session: AsyncSession
    ):
        """Test unlocking a timeline item"""
        # Create a locked item
        locked_item = SequenceTimeline(
            sequence_id=test_sequence.id,
            clip_id=test_shot.id,
            track_number=0,
            track_type="video",
            start_time=0,
            end_time=1000,
            is_locked=True
        )
        db_session.add(locked_item)
        await db_session.commit()
        
        # Unlock it
        update_data = {"is_locked": False}
        
        response = await client.put(
            f"/api/v1/timelines/items/{locked_item.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json()["is_locked"] is False
    
    async def test_update_creates_overlap(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence,
        test_shot,
        test_timeline_item,
        db_session: AsyncSession
    ):
        """Test that updates creating overlaps are rejected"""
        # Create another item on same track
        other_item = SequenceTimeline(
            sequence_id=test_sequence.id,
            clip_id=test_shot.id,
            track_number=0,
            track_type="video",
            start_time=10000,
            end_time=15000
        )
        db_session.add(other_item)
        await db_session.commit()
        
        # Try to extend test_timeline_item to overlap
        update_data = {"end_time": 12000}
        
        response = await client.put(
            f"/api/v1/timelines/items/{test_timeline_item.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "overlaps with existing clip" in response.json()["detail"]


class TestTimelineItemDeletion:
    """Test timeline item deletion"""
    
    async def test_delete_timeline_item(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_timeline_item
    ):
        """Test deleting a timeline item"""
        response = await client.delete(
            f"/api/v1/timelines/items/{test_timeline_item.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["detail"]
        
        # Verify deletion
        get_response = await client.get(
            f"/api/v1/timelines/items/{test_timeline_item.id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404
    
    async def test_delete_locked_timeline_item(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence,
        test_shot,
        db_session: AsyncSession
    ):
        """Test that locked timeline items cannot be deleted"""
        # Create a locked item
        locked_item = SequenceTimeline(
            sequence_id=test_sequence.id,
            clip_id=test_shot.id,
            track_number=0,
            track_type="video",
            start_time=0,
            end_time=1000,
            is_locked=True
        )
        db_session.add(locked_item)
        await db_session.commit()
        
        response = await client.delete(
            f"/api/v1/timelines/items/{locked_item.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "Cannot delete locked timeline item" in response.json()["detail"]


class TestBatchOperations:
    """Test batch timeline operations"""
    
    async def test_batch_create_timeline_items(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence,
        test_shot,
        db_session: AsyncSession
    ):
        """Test creating multiple timeline items at once"""
        # Create another shot
        shot2 = ShotItem(
            id=uuid4(),
            container_id=test_sequence.id,
            asset_id=test_shot.asset_id,
            name="Test Shot 2",
            in_point=0,
            out_point=3000,
            duration=3000,
            created_by=test_shot.created_by
        )
        db_session.add(shot2)
        await db_session.commit()
        
        items_data = [
            {
                "sequence_id": str(test_sequence.id),
                "clip_id": str(test_shot.id),
                "track_number": 0,
                "track_type": "video",
                "start_time": 0,
                "end_time": 5000
            },
            {
                "sequence_id": str(test_sequence.id),
                "clip_id": str(shot2.id),
                "track_number": 0,
                "track_type": "video",
                "start_time": 5000,
                "end_time": 8000
            }
        ]
        
        response = await client.post(
            f"/api/v1/timelines/{test_sequence.id}/items/batch",
            json=items_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["start_time"] == 0
        assert data[1]["start_time"] == 5000
    
    async def test_batch_create_with_overlap(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence,
        test_shot
    ):
        """Test that batch creation detects overlaps within the batch"""
        items_data = [
            {
                "sequence_id": str(test_sequence.id),
                "clip_id": str(test_shot.id),
                "track_number": 0,
                "track_type": "video",
                "start_time": 0,
                "end_time": 5000
            },
            {
                "sequence_id": str(test_sequence.id),
                "clip_id": str(test_shot.id),
                "track_number": 0,
                "track_type": "video",
                "start_time": 3000,  # Overlaps with first item
                "end_time": 8000
            }
        ]
        
        response = await client.post(
            f"/api/v1/timelines/{test_sequence.id}/items/batch",
            json=items_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "overlap" in response.json()["detail"]
    
    async def test_clear_sequence_timeline(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence,
        test_shot,
        db_session: AsyncSession
    ):
        """Test clearing timeline tracks"""
        # Create items on different tracks
        items = []
        for i in range(3):
            for track_type in ["video", "audio"]:
                item = SequenceTimeline(
                    sequence_id=test_sequence.id,
                    clip_id=test_shot.id,
                    track_number=i,
                    track_type=track_type,
                    start_time=i * 1000,
                    end_time=(i + 1) * 1000
                )
                items.append(item)
        
        db_session.add_all(items)
        await db_session.commit()
        
        # Clear all video tracks
        response = await client.delete(
            f"/api/v1/timelines/{test_sequence.id}/items?track_type=video",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json()["deleted_count"] == 3
        
        # Verify only audio tracks remain
        get_response = await client.get(
            f"/api/v1/timelines/{test_sequence.id}/items",
            headers=auth_headers
        )
        
        remaining = get_response.json()
        assert len(remaining) == 3
        assert all(item["track_type"] == "audio" for item in remaining)


class TestRippleDelete:
    """Test ripple delete functionality"""
    
    async def test_ripple_delete_timeline_item(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence,
        test_shot,
        db_session: AsyncSession
    ):
        """Test ripple delete shifts subsequent items"""
        # Create a sequence of items
        items = []
        for i in range(4):
            item = SequenceTimeline(
                sequence_id=test_sequence.id,
                clip_id=test_shot.id,
                track_number=0,
                track_type="video",
                start_time=i * 1000,
                end_time=(i + 1) * 1000
            )
            items.append(item)
        
        db_session.add_all(items)
        await db_session.commit()
        
        # Ripple delete the second item (1000-2000)
        response = await client.post(
            f"/api/v1/timelines/{test_sequence.id}/ripple-delete/{items[1].id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json()["shifted_items_count"] == 2
        assert response.json()["gap_closed"] == 1000
        
        # Verify timeline is now continuous
        timeline_response = await client.get(
            f"/api/v1/timelines/{test_sequence.id}/items",
            headers=auth_headers
        )
        
        timeline = timeline_response.json()
        assert len(timeline) == 3
        # Items should now be at 0-1000, 1000-2000, 2000-3000
        assert timeline[0]["start_time"] == 0
        assert timeline[1]["start_time"] == 1000
        assert timeline[2]["start_time"] == 2000


class TestPermissions:
    """Test permission checks"""
    
    async def test_unauthorized_access(
        self,
        client: AsyncClient,
        test_sequence
    ):
        """Test accessing timeline without authentication"""
        response = await client.get(
            f"/api/v1/timelines/{test_sequence.id}/items"
        )
        
        assert response.status_code == 401
    
    async def test_forbidden_edit(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_timeline_item,
        db_session: AsyncSession
    ):
        """Test editing timeline without permission"""
        # Change sequence owner
        sequence = await db_session.get(ProjectContainer, test_timeline_item.sequence_id)
        sequence.owner_id = uuid4()
        await db_session.commit()
        
        update_data = {"start_time": 2000}
        
        response = await client.put(
            f"/api/v1/timelines/items/{test_timeline_item.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 403
        assert "don't have permission" in response.json()["detail"]