"""
Tests for track management API routes
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
        owner_id=test_user["user_id"],
        metadata={}
    )
    db_session.add(sequence)
    await db_session.commit()
    return sequence


@pytest.fixture
async def test_sequence_with_tracks(db_session: AsyncSession, test_user):
    """Create a test sequence with predefined tracks"""
    sequence = ProjectContainer(
        id=uuid4(),
        name="test-sequence-tracks",
        display_name="Test Sequence with Tracks",
        container_type=ContainerType.SEQUENCE,
        owner_id=test_user["user_id"],
        metadata={
            "tracks": {
                "video_0": {
                    "name": "V1",
                    "is_locked": False,
                    "is_muted": False,
                    "is_solo": False,
                    "height": 120,
                    "metadata": {"color": "#FF0000"}
                },
                "audio_0": {
                    "name": "A1",
                    "is_locked": False,
                    "is_muted": True,
                    "is_solo": False,
                    "height": 80,
                    "metadata": {}
                }
            }
        }
    )
    db_session.add(sequence)
    await db_session.commit()
    return sequence


@pytest.fixture
async def test_clips(db_session: AsyncSession, test_sequence_with_tracks, test_user):
    """Create test clips on tracks"""
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
    
    # Create shot
    shot = ShotItem(
        id=uuid4(),
        container_id=test_sequence_with_tracks.id,
        asset_id=asset.id,
        name="Test Shot",
        in_point=0,
        out_point=10000,
        duration=10000,
        created_by=test_user["user_id"]
    )
    db_session.add(shot)
    
    # Create timeline items
    video_clip = SequenceTimeline(
        id=uuid4(),
        sequence_id=test_sequence_with_tracks.id,
        clip_id=shot.id,
        track_number=0,
        track_type="video",
        start_time=0,
        end_time=5000
    )
    
    audio_clip = SequenceTimeline(
        id=uuid4(),
        sequence_id=test_sequence_with_tracks.id,
        clip_id=shot.id,
        track_number=0,
        track_type="audio",
        start_time=0,
        end_time=5000
    )
    
    db_session.add_all([video_clip, audio_clip])
    await db_session.commit()
    
    return {
        "video_clip": video_clip,
        "audio_clip": audio_clip,
        "shot": shot,
        "asset": asset
    }


class TestTrackRetrieval:
    """Test track retrieval operations"""
    
    async def test_get_empty_sequence_tracks(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence
    ):
        """Test getting tracks from empty sequence"""
        response = await client.get(
            f"/api/v1/tracks/{test_sequence.id}/tracks",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data == []
    
    async def test_get_sequence_tracks_with_metadata(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence_with_tracks
    ):
        """Test getting tracks with metadata"""
        response = await client.get(
            f"/api/v1/tracks/{test_sequence_with_tracks.id}/tracks",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        
        # Check video track
        video_track = next(t for t in data if t["track_type"] == "video")
        assert video_track["track_number"] == 0
        assert video_track["track_name"] == "V1"
        assert video_track["is_muted"] is False
        assert video_track["height"] == 120
        assert video_track["metadata"]["color"] == "#FF0000"
        
        # Check audio track
        audio_track = next(t for t in data if t["track_type"] == "audio")
        assert audio_track["track_number"] == 0
        assert audio_track["track_name"] == "A1"
        assert audio_track["is_muted"] is True
        assert audio_track["height"] == 80
    
    async def test_get_tracks_with_clips(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence_with_tracks,
        test_clips
    ):
        """Test getting tracks with clip statistics"""
        response = await client.get(
            f"/api/v1/tracks/{test_sequence_with_tracks.id}/tracks",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check video track has clip count
        video_track = next(t for t in data if t["track_type"] == "video")
        assert video_track["clip_count"] == 1
        assert video_track["total_duration"] == 5000
        
        # Check audio track has clip count
        audio_track = next(t for t in data if t["track_type"] == "audio")
        assert audio_track["clip_count"] == 1
        assert audio_track["total_duration"] == 5000
    
    async def test_get_tracks_by_type(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence_with_tracks
    ):
        """Test filtering tracks by type"""
        response = await client.get(
            f"/api/v1/tracks/{test_sequence_with_tracks.id}/tracks?track_type=video",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["track_type"] == "video"


class TestTrackCreation:
    """Test track creation operations"""
    
    async def test_create_track(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence
    ):
        """Test creating a new track"""
        track_data = {
            "track_type": "video",
            "track_name": "Main Video",
            "height": 150,
            "metadata": {"description": "Main video track"}
        }
        
        response = await client.post(
            f"/api/v1/tracks/{test_sequence.id}/tracks",
            json=track_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["track_number"] == 0
        assert data["track_type"] == "video"
        assert data["track_name"] == "Main Video"
        assert data["height"] == 150
        assert data["metadata"]["description"] == "Main video track"
    
    async def test_create_track_at_position(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence_with_tracks,
        test_clips
    ):
        """Test creating a track at specific position"""
        # Create track at position 0 (should shift existing track)
        track_data = {
            "track_type": "video",
            "track_name": "New V1",
            "position": 0,
            "height": 100
        }
        
        response = await client.post(
            f"/api/v1/tracks/{test_sequence_with_tracks.id}/tracks",
            json=track_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["track_number"] == 0
        assert data["track_name"] == "New V1"
        
        # Verify existing track was shifted
        tracks_response = await client.get(
            f"/api/v1/tracks/{test_sequence_with_tracks.id}/tracks?track_type=video",
            headers=auth_headers
        )
        
        tracks = tracks_response.json()
        assert len(tracks) == 2
        assert tracks[0]["track_name"] == "New V1"
        assert tracks[1]["track_name"] == "V1"
        assert tracks[1]["track_number"] == 1
    
    async def test_create_multiple_tracks(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence
    ):
        """Test creating multiple tracks of same type"""
        # Create first video track
        response1 = await client.post(
            f"/api/v1/tracks/{test_sequence.id}/tracks",
            json={"track_type": "video"},
            headers=auth_headers
        )
        assert response1.status_code == 200
        assert response1.json()["track_number"] == 0
        
        # Create second video track
        response2 = await client.post(
            f"/api/v1/tracks/{test_sequence.id}/tracks",
            json={"track_type": "video"},
            headers=auth_headers
        )
        assert response2.status_code == 200
        assert response2.json()["track_number"] == 1
        
        # Create audio track
        response3 = await client.post(
            f"/api/v1/tracks/{test_sequence.id}/tracks",
            json={"track_type": "audio"},
            headers=auth_headers
        )
        assert response3.status_code == 200
        assert response3.json()["track_number"] == 0  # First audio track


class TestTrackUpdate:
    """Test track update operations"""
    
    async def test_update_track_properties(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence_with_tracks
    ):
        """Test updating track properties"""
        update_data = {
            "track_name": "Updated V1",
            "is_locked": True,
            "height": 200,
            "metadata": {"color": "#00FF00"}
        }
        
        response = await client.put(
            f"/api/v1/tracks/{test_sequence_with_tracks.id}/tracks/video/0",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["track_name"] == "Updated V1"
        assert data["is_locked"] is True
        assert data["height"] == 200
        assert data["metadata"]["color"] == "#00FF00"
    
    async def test_update_track_solo(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence_with_tracks
    ):
        """Test solo mode behavior"""
        # Create another video track
        await client.post(
            f"/api/v1/tracks/{test_sequence_with_tracks.id}/tracks",
            json={"track_type": "video", "track_name": "V2"},
            headers=auth_headers
        )
        
        # Set first track to solo
        response1 = await client.put(
            f"/api/v1/tracks/{test_sequence_with_tracks.id}/tracks/video/0",
            json={"is_solo": True},
            headers=auth_headers
        )
        assert response1.status_code == 200
        assert response1.json()["is_solo"] is True
        
        # Set second track to solo (should unset first)
        response2 = await client.put(
            f"/api/v1/tracks/{test_sequence_with_tracks.id}/tracks/video/1",
            json={"is_solo": True},
            headers=auth_headers
        )
        assert response2.status_code == 200
        assert response2.json()["is_solo"] is True
        
        # Verify first track is no longer solo
        tracks_response = await client.get(
            f"/api/v1/tracks/{test_sequence_with_tracks.id}/tracks?track_type=video",
            headers=auth_headers
        )
        tracks = tracks_response.json()
        assert tracks[0]["is_solo"] is False
        assert tracks[1]["is_solo"] is True
    
    async def test_update_locked_track_locks_clips(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence_with_tracks,
        test_clips,
        db_session: AsyncSession
    ):
        """Test that locking a track also locks its clips"""
        # Lock the video track
        response = await client.put(
            f"/api/v1/tracks/{test_sequence_with_tracks.id}/tracks/video/0",
            json={"is_locked": True},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Check that clips are locked
        await db_session.refresh(test_clips["video_clip"])
        assert test_clips["video_clip"].is_locked is True


class TestTrackDeletion:
    """Test track deletion operations"""
    
    async def test_delete_empty_track(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence_with_tracks
    ):
        """Test deleting a track without clips"""
        # Create a new track
        await client.post(
            f"/api/v1/tracks/{test_sequence_with_tracks.id}/tracks",
            json={"track_type": "subtitle", "track_name": "S1"},
            headers=auth_headers
        )
        
        # Delete the track
        response = await client.delete(
            f"/api/v1/tracks/{test_sequence_with_tracks.id}/tracks/subtitle/0",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json()["clips_deleted"] == 0
    
    async def test_delete_track_with_clips_requires_force(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence_with_tracks,
        test_clips
    ):
        """Test that deleting track with clips requires force flag"""
        # Try to delete without force
        response = await client.delete(
            f"/api/v1/tracks/{test_sequence_with_tracks.id}/tracks/video/0",
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "force=true" in response.json()["detail"]
    
    async def test_delete_track_with_force(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence_with_tracks,
        test_clips
    ):
        """Test force deleting track with clips"""
        response = await client.delete(
            f"/api/v1/tracks/{test_sequence_with_tracks.id}/tracks/video/0?force=true",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json()["clips_deleted"] == 1
        
        # Verify track is gone
        tracks_response = await client.get(
            f"/api/v1/tracks/{test_sequence_with_tracks.id}/tracks?track_type=video",
            headers=auth_headers
        )
        assert len(tracks_response.json()) == 0


class TestTrackReordering:
    """Test track reordering operations"""
    
    async def test_reorder_tracks(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence
    ):
        """Test reordering tracks"""
        # Create multiple video tracks
        for i in range(3):
            await client.post(
                f"/api/v1/tracks/{test_sequence.id}/tracks",
                json={"track_type": "video", "track_name": f"V{i+1}"},
                headers=auth_headers
            )
        
        # Reorder tracks (reverse order)
        reorder_data = {
            "track_type": "video",
            "new_order": [2, 1, 0]
        }
        
        response = await client.put(
            f"/api/v1/tracks/{test_sequence.id}/tracks/reorder",
            json=reorder_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Verify new order
        tracks_response = await client.get(
            f"/api/v1/tracks/{test_sequence.id}/tracks?track_type=video",
            headers=auth_headers
        )
        tracks = tracks_response.json()
        assert tracks[0]["track_name"] == "V3"
        assert tracks[1]["track_name"] == "V2"
        assert tracks[2]["track_name"] == "V1"
    
    async def test_reorder_tracks_invalid_order(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence_with_tracks
    ):
        """Test that invalid reorder is rejected"""
        # Try to reorder with missing track
        reorder_data = {
            "track_type": "video",
            "new_order": [0, 1]  # Missing track 0, extra track 1
        }
        
        response = await client.put(
            f"/api/v1/tracks/{test_sequence_with_tracks.id}/tracks/reorder",
            json=reorder_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "must contain all existing track numbers" in response.json()["detail"]


class TestClipMoving:
    """Test moving clips between tracks"""
    
    async def test_move_clips_between_tracks(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence_with_tracks,
        test_clips
    ):
        """Test moving clips to another track"""
        # Create another video track
        await client.post(
            f"/api/v1/tracks/{test_sequence_with_tracks.id}/tracks",
            json={"track_type": "video", "track_name": "V2"},
            headers=auth_headers
        )
        
        # Move clip to new track
        response = await client.post(
            f"/api/v1/tracks/{test_sequence_with_tracks.id}/tracks/move-clips"
            f"?source_track_type=video&source_track_number=0"
            f"&target_track_type=video&target_track_number=1",
            json=[str(test_clips["video_clip"].id)],
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json()["moved_clips"][0] == str(test_clips["video_clip"].id)
        
        # Verify clip moved
        tracks_response = await client.get(
            f"/api/v1/tracks/{test_sequence_with_tracks.id}/tracks?track_type=video",
            headers=auth_headers
        )
        tracks = tracks_response.json()
        assert tracks[0]["clip_count"] == 0  # Source track
        assert tracks[1]["clip_count"] == 1  # Target track
    
    async def test_move_clips_overlap_detection(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence_with_tracks,
        test_clips,
        db_session: AsyncSession
    ):
        """Test that overlapping moves are rejected"""
        # Create another video track with a clip in same time range
        await client.post(
            f"/api/v1/tracks/{test_sequence_with_tracks.id}/tracks",
            json={"track_type": "video", "track_name": "V2"},
            headers=auth_headers
        )
        
        # Add a clip to the new track that would overlap
        new_clip = SequenceTimeline(
            sequence_id=test_sequence_with_tracks.id,
            clip_id=test_clips["shot"].id,
            track_number=1,
            track_type="video",
            start_time=2500,  # Overlaps with existing clip (0-5000)
            end_time=7500
        )
        db_session.add(new_clip)
        await db_session.commit()
        
        # Try to move clip that would overlap
        response = await client.post(
            f"/api/v1/tracks/{test_sequence_with_tracks.id}/tracks/move-clips"
            f"?source_track_type=video&source_track_number=0"
            f"&target_track_type=video&target_track_number=1",
            json=[str(test_clips["video_clip"].id)],
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "would overlap" in response.json()["detail"]


class TestPermissions:
    """Test permission checks"""
    
    async def test_unauthorized_access(
        self,
        client: AsyncClient,
        test_sequence
    ):
        """Test accessing tracks without authentication"""
        response = await client.get(
            f"/api/v1/tracks/{test_sequence.id}/tracks"
        )
        
        assert response.status_code == 401
    
    async def test_forbidden_edit(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence_with_tracks,
        db_session: AsyncSession
    ):
        """Test editing tracks without permission"""
        # Change sequence owner
        test_sequence_with_tracks.owner_id = uuid4()
        await db_session.commit()
        
        response = await client.post(
            f"/api/v1/tracks/{test_sequence_with_tracks.id}/tracks",
            json={"track_type": "video"},
            headers=auth_headers
        )
        
        assert response.status_code == 403
        assert "don't have permission" in response.json()["detail"]