"""
Tests for transition API routes
"""

import pytest
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import (
    ProjectContainer, Asset, ShotItem, SequenceTimeline,
    ContainerType, AssetType, AssetStatus
)


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
async def test_timeline_items(db_session: AsyncSession, test_sequence, test_user):
    """Create test timeline items"""
    # Create asset
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
        owner_id=test_user["user_id"]
    )
    db_session.add(asset)
    
    # Create shots
    shots = []
    for i in range(3):
        shot = ShotItem(
            id=uuid4(),
            container_id=test_sequence.id,
            asset_id=asset.id,
            name=f"Shot {i+1}",
            in_point=i * 5000,
            out_point=(i + 1) * 5000,
            duration=5000,
            created_by=test_user["user_id"]
        )
        shots.append(shot)
        db_session.add(shot)
    
    # Create timeline items
    timeline_items = []
    for i, shot in enumerate(shots):
        item = SequenceTimeline(
            id=uuid4(),
            sequence_id=test_sequence.id,
            clip_id=shot.id,
            track_number=0,
            track_type="video",
            start_time=i * 6000,  # 1000ms gap between clips
            end_time=(i * 6000) + 5000,
            speed=1.0,
            is_enabled=True,
            is_locked=False
        )
        timeline_items.append(item)
        db_session.add(item)
    
    await db_session.commit()
    
    return {
        "asset": asset,
        "shots": shots,
        "timeline_items": timeline_items
    }


class TestTransitionTypes:
    """Test transition type endpoints"""
    
    async def test_get_transition_types(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """Test getting all transition types"""
        response = await client.get(
            "/api/v1/transitions/types",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        
        # Check for basic transitions
        transition_ids = [t["id"] for t in data]
        assert "fade" in transition_ids
        assert "dissolve" in transition_ids
        assert "wipe" in transition_ids
        
        # Check transition structure
        fade = next(t for t in data if t["id"] == "fade")
        assert fade["name"] == "Fade"
        assert fade["category"] == "basic"
        assert fade["supports_duration"] is True
        assert "parameters" in fade
    
    async def test_get_transition_types_by_category(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """Test filtering transition types by category"""
        response = await client.get(
            "/api/v1/transitions/types?category=basic",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert all(t["category"] == "basic" for t in data)
    
    async def test_get_specific_transition_type(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """Test getting details of a specific transition type"""
        response = await client.get(
            "/api/v1/transitions/types/dissolve",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "dissolve"
        assert data["name"] == "Cross Dissolve"
        assert "curve" in data["parameters"]
    
    async def test_get_nonexistent_transition_type(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """Test getting nonexistent transition type"""
        response = await client.get(
            "/api/v1/transitions/types/nonexistent",
            headers=auth_headers
        )
        
        assert response.status_code == 404


class TestTransitionCreation:
    """Test transition creation"""
    
    async def test_add_fade_in_transition(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence,
        test_timeline_items
    ):
        """Test adding a fade in transition"""
        first_item = test_timeline_items["timeline_items"][0]
        
        transition_data = {
            "timeline_item_id": str(first_item.id),
            "transition_type": "fade",
            "position": "in",
            "duration": 1000,
            "parameters": {"color": "#FFFFFF"}
        }
        
        response = await client.post(
            f"/api/v1/transitions/{test_sequence.id}/add",
            json=transition_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["timeline_item_id"] == str(first_item.id)
        assert data["position"] == "in"
        assert data["type"] == "fade"
        assert data["duration"] == 1000
        assert data["parameters"]["color"] == "#FFFFFF"
    
    async def test_add_dissolve_transition(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence,
        test_timeline_items
    ):
        """Test adding a dissolve out transition"""
        first_item = test_timeline_items["timeline_items"][0]
        
        transition_data = {
            "timeline_item_id": str(first_item.id),
            "transition_type": "dissolve",
            "position": "out",
            "duration": 800
        }
        
        response = await client.post(
            f"/api/v1/transitions/{test_sequence.id}/add",
            json=transition_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "dissolve"
        assert data["duration"] == 800
        assert "curve" in data["parameters"]  # Default parameter added
    
    async def test_add_transition_insufficient_gap(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence,
        test_timeline_items
    ):
        """Test that transitions requiring too much space are rejected"""
        first_item = test_timeline_items["timeline_items"][0]
        
        # Try to add a 2-second transition when gap is only 1 second
        transition_data = {
            "timeline_item_id": str(first_item.id),
            "transition_type": "dissolve",
            "position": "out",
            "duration": 2000
        }
        
        response = await client.post(
            f"/api/v1/transitions/{test_sequence.id}/add",
            json=transition_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "Not enough space" in response.json()["detail"]
    
    async def test_add_transition_to_locked_item(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence,
        test_timeline_items,
        db_session: AsyncSession
    ):
        """Test that transitions cannot be added to locked items"""
        first_item = test_timeline_items["timeline_items"][0]
        
        # Lock the item
        first_item.is_locked = True
        await db_session.commit()
        
        transition_data = {
            "timeline_item_id": str(first_item.id),
            "transition_type": "fade",
            "position": "in",
            "duration": 500
        }
        
        response = await client.post(
            f"/api/v1/transitions/{test_sequence.id}/add",
            json=transition_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "locked" in response.json()["detail"]
    
    async def test_add_transition_invalid_type(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence,
        test_timeline_items
    ):
        """Test adding transition with invalid type"""
        first_item = test_timeline_items["timeline_items"][0]
        
        transition_data = {
            "timeline_item_id": str(first_item.id),
            "transition_type": "invalid_type",
            "position": "in",
            "duration": 1000
        }
        
        response = await client.post(
            f"/api/v1/transitions/{test_sequence.id}/add",
            json=transition_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error


class TestTransitionUpdate:
    """Test transition updates"""
    
    async def test_update_transition_duration(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence,
        test_timeline_items,
        db_session: AsyncSession
    ):
        """Test updating transition duration"""
        first_item = test_timeline_items["timeline_items"][0]
        
        # Add a transition first
        first_item.transition_in = {
            "type": "fade",
            "duration": 1000,
            "parameters": {"color": "#000000"}
        }
        await db_session.commit()
        
        # Update the transition
        update_data = {"duration": 1500}
        
        response = await client.put(
            f"/api/v1/transitions/{test_sequence.id}/update/{first_item.id}/in",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["duration"] == 1500
        assert data["parameters"]["color"] == "#000000"  # Unchanged
    
    async def test_update_transition_parameters(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence,
        test_timeline_items,
        db_session: AsyncSession
    ):
        """Test updating transition parameters"""
        first_item = test_timeline_items["timeline_items"][0]
        
        # Add a wipe transition
        first_item.transition_out = {
            "type": "wipe",
            "duration": 1000,
            "parameters": {"direction": "left", "angle": 0, "feather": 0}
        }
        await db_session.commit()
        
        # Update parameters
        update_data = {
            "parameters": {"direction": "right", "angle": 45}
        }
        
        response = await client.put(
            f"/api/v1/transitions/{test_sequence.id}/update/{first_item.id}/out",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["parameters"]["direction"] == "right"
        assert data["parameters"]["angle"] == 45
        assert data["parameters"]["feather"] == 0  # Unchanged
    
    async def test_update_nonexistent_transition(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence,
        test_timeline_items
    ):
        """Test updating a transition that doesn't exist"""
        first_item = test_timeline_items["timeline_items"][0]
        
        update_data = {"duration": 1500}
        
        response = await client.put(
            f"/api/v1/transitions/{test_sequence.id}/update/{first_item.id}/in",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 404
        assert "No in transition found" in response.json()["detail"]


class TestTransitionRemoval:
    """Test transition removal"""
    
    async def test_remove_transition(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence,
        test_timeline_items,
        db_session: AsyncSession
    ):
        """Test removing a transition"""
        first_item = test_timeline_items["timeline_items"][0]
        
        # Add transitions
        first_item.transition_in = {"type": "fade", "duration": 500, "parameters": {}}
        first_item.transition_out = {"type": "fade", "duration": 500, "parameters": {}}
        await db_session.commit()
        
        # Remove in transition
        response = await client.delete(
            f"/api/v1/transitions/{test_sequence.id}/remove/{first_item.id}/in",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Verify it's removed
        await db_session.refresh(first_item)
        assert first_item.transition_in is None
        assert first_item.transition_out is not None  # Out transition still there
    
    async def test_remove_transition_from_locked_item(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence,
        test_timeline_items,
        db_session: AsyncSession
    ):
        """Test that transitions cannot be removed from locked items"""
        first_item = test_timeline_items["timeline_items"][0]
        
        # Add transition and lock item
        first_item.transition_in = {"type": "fade", "duration": 500, "parameters": {}}
        first_item.is_locked = True
        await db_session.commit()
        
        response = await client.delete(
            f"/api/v1/transitions/{test_sequence.id}/remove/{first_item.id}/in",
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "locked" in response.json()["detail"]


class TestSequenceTransitions:
    """Test sequence-wide transition operations"""
    
    async def test_get_sequence_transitions(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence,
        test_timeline_items,
        db_session: AsyncSession
    ):
        """Test getting all transitions in a sequence"""
        # Add some transitions
        items = test_timeline_items["timeline_items"]
        items[0].transition_in = {"type": "fade", "duration": 500, "parameters": {"color": "#000000"}}
        items[0].transition_out = {"type": "dissolve", "duration": 1000, "parameters": {"curve": "linear"}}
        items[1].transition_in = {"type": "wipe", "duration": 800, "parameters": {"direction": "left"}}
        await db_session.commit()
        
        response = await client.get(
            f"/api/v1/transitions/{test_sequence.id}/transitions",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        
        # Check transitions are correctly returned
        fade_in = next(t for t in data if t["type"] == "fade" and t["position"] == "in")
        assert fade_in["timeline_item_id"] == str(items[0].id)
        assert fade_in["duration"] == 500
        
    async def test_get_transitions_by_track(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence,
        test_timeline_items,
        db_session: AsyncSession
    ):
        """Test filtering transitions by track"""
        # Add transition to video track
        items = test_timeline_items["timeline_items"]
        items[0].transition_in = {"type": "fade", "duration": 500, "parameters": {}}
        
        # Add audio track item with transition
        shot = test_timeline_items["shots"][0]
        audio_item = SequenceTimeline(
            sequence_id=test_sequence.id,
            clip_id=shot.id,
            track_number=0,
            track_type="audio",
            start_time=0,
            end_time=5000,
            transition_in={"type": "fade", "duration": 300, "parameters": {}}
        )
        db_session.add(audio_item)
        await db_session.commit()
        
        # Get only video transitions
        response = await client.get(
            f"/api/v1/transitions/{test_sequence.id}/transitions?track_type=video",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["track_type"] == "video"


class TestTransitionPresets:
    """Test transition preset functionality"""
    
    async def test_apply_fade_all_preset(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence,
        test_timeline_items
    ):
        """Test applying fade all preset"""
        response = await client.post(
            f"/api/v1/transitions/{test_sequence.id}/apply-preset?preset_name=fade_all",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["transitions_added"] > 0
        assert "fade_all" in data["detail"]
        
        # Verify transitions were added
        transitions_response = await client.get(
            f"/api/v1/transitions/{test_sequence.id}/transitions",
            headers=auth_headers
        )
        
        transitions = transitions_response.json()
        assert len(transitions) > 0
        assert all(t["type"] == "fade" for t in transitions)
    
    async def test_apply_dissolve_between_preset(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence,
        test_timeline_items
    ):
        """Test applying dissolve between clips preset"""
        response = await client.post(
            f"/api/v1/transitions/{test_sequence.id}/apply-preset?preset_name=dissolve_between",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that dissolves were added between clips
        transitions_response = await client.get(
            f"/api/v1/transitions/{test_sequence.id}/transitions",
            headers=auth_headers
        )
        
        transitions = transitions_response.json()
        dissolves = [t for t in transitions if t["type"] == "dissolve"]
        assert len(dissolves) > 0
    
    async def test_apply_preset_to_specific_track(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence,
        test_timeline_items,
        db_session: AsyncSession
    ):
        """Test applying preset to specific track"""
        # Add audio track item
        shot = test_timeline_items["shots"][0]
        audio_item = SequenceTimeline(
            sequence_id=test_sequence.id,
            clip_id=shot.id,
            track_number=0,
            track_type="audio",
            start_time=0,
            end_time=5000
        )
        db_session.add(audio_item)
        await db_session.commit()
        
        # Apply preset only to video track
        response = await client.post(
            f"/api/v1/transitions/{test_sequence.id}/apply-preset"
            f"?preset_name=quick_cuts&track_type=video",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Verify only video track got transitions
        transitions_response = await client.get(
            f"/api/v1/transitions/{test_sequence.id}/transitions",
            headers=auth_headers
        )
        
        transitions = transitions_response.json()
        assert all(t["track_type"] == "video" for t in transitions)
    
    async def test_apply_unknown_preset(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence
    ):
        """Test applying unknown preset"""
        response = await client.post(
            f"/api/v1/transitions/{test_sequence.id}/apply-preset?preset_name=unknown",
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "Unknown preset" in response.json()["detail"]


class TestPermissions:
    """Test permission checks"""
    
    async def test_unauthorized_access(
        self,
        client: AsyncClient,
        test_sequence,
        test_timeline_items
    ):
        """Test accessing transitions without authentication"""
        first_item = test_timeline_items["timeline_items"][0]
        
        transition_data = {
            "timeline_item_id": str(first_item.id),
            "transition_type": "fade",
            "position": "in",
            "duration": 1000
        }
        
        response = await client.post(
            f"/api/v1/transitions/{test_sequence.id}/add",
            json=transition_data
        )
        
        assert response.status_code == 401
    
    async def test_forbidden_edit(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence,
        test_timeline_items,
        db_session: AsyncSession
    ):
        """Test editing transitions without permission"""
        # Change sequence owner
        test_sequence.owner_id = uuid4()
        await db_session.commit()
        
        first_item = test_timeline_items["timeline_items"][0]
        
        transition_data = {
            "timeline_item_id": str(first_item.id),
            "transition_type": "fade",
            "position": "in",
            "duration": 1000
        }
        
        response = await client.post(
            f"/api/v1/transitions/{test_sequence.id}/add",
            json=transition_data,
            headers=auth_headers
        )
        
        assert response.status_code == 403
        assert "don't have permission" in response.json()["detail"]