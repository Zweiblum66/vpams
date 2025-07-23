"""
Tests for timeline versioning API routes
"""

import pytest
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from src.db.models import (
    ProjectContainer, Asset, ShotItem, SequenceTimeline,
    ContainerType, AssetType, AssetStatus
)


@pytest.fixture
async def test_sequence_with_timeline(db_session: AsyncSession, test_user):
    """Create a test sequence with timeline items"""
    # Create sequence
    sequence = ProjectContainer(
        id=uuid4(),
        name="test-sequence",
        display_name="Test Sequence",
        container_type=ContainerType.SEQUENCE,
        owner_id=test_user["user_id"],
        metadata={}
    )
    db_session.add(sequence)
    
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
            container_id=sequence.id,
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
            sequence_id=sequence.id,
            clip_id=shot.id,
            track_number=0,
            track_type="video",
            start_time=i * 5000,
            end_time=(i + 1) * 5000,
            speed=1.0,
            is_enabled=True,
            is_locked=False
        )
        timeline_items.append(item)
        db_session.add(item)
    
    await db_session.commit()
    
    return {
        "sequence": sequence,
        "asset": asset,
        "shots": shots,
        "timeline_items": timeline_items
    }


class TestVersionCreation:
    """Test timeline version creation"""
    
    async def test_save_first_version(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence_with_timeline
    ):
        """Test saving the first version of a timeline"""
        sequence = test_sequence_with_timeline["sequence"]
        
        version_data = {
            "name": "Initial Version",
            "description": "First save of the timeline",
            "metadata": {"milestone": "v1.0"}
        }
        
        response = await client.post(
            f"/api/v1/timeline-versions/{sequence.id}/save",
            json=version_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Initial Version"
        assert data["description"] == "First save of the timeline"
        assert data["version_number"] == 1
        assert data["timeline_item_count"] == 3
        assert data["is_auto_save"] is False
        assert data["metadata"]["milestone"] == "v1.0"
    
    async def test_save_subsequent_versions(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence_with_timeline,
        db_session: AsyncSession
    ):
        """Test saving multiple versions"""
        sequence = test_sequence_with_timeline["sequence"]
        
        # Save first version
        response1 = await client.post(
            f"/api/v1/timeline-versions/{sequence.id}/save",
            json={"name": "Version 1"},
            headers=auth_headers
        )
        assert response1.status_code == 200
        version1 = response1.json()
        
        # Modify timeline
        timeline_items = test_sequence_with_timeline["timeline_items"]
        timeline_items[0].start_time = 1000
        timeline_items[0].end_time = 6000
        await db_session.commit()
        
        # Save second version
        response2 = await client.post(
            f"/api/v1/timeline-versions/{sequence.id}/save",
            json={"name": "Version 2", "description": "Modified timeline"},
            headers=auth_headers
        )
        assert response2.status_code == 200
        version2 = response2.json()
        
        assert version2["version_number"] == 2
        assert version2["parent_version_id"] == version1["id"]
    
    async def test_auto_save_version(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence_with_timeline
    ):
        """Test creating an auto-save version"""
        sequence = test_sequence_with_timeline["sequence"]
        
        response = await client.post(
            f"/api/v1/timeline-versions/{sequence.id}/auto-save",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "Auto-save created" in data["message"]
        assert "version_id" in data
        assert "version_number" in data


class TestVersionListing:
    """Test listing timeline versions"""
    
    async def test_list_versions(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence_with_timeline
    ):
        """Test listing all versions"""
        sequence = test_sequence_with_timeline["sequence"]
        
        # Create multiple versions
        for i in range(3):
            await client.post(
                f"/api/v1/timeline-versions/{sequence.id}/save",
                json={"name": f"Version {i+1}"},
                headers=auth_headers
            )
        
        # List versions
        response = await client.get(
            f"/api/v1/timeline-versions/{sequence.id}/list",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        versions = response.json()
        assert len(versions) == 3
        
        # Check they're sorted by version number descending
        assert versions[0]["version_number"] == 3
        assert versions[1]["version_number"] == 2
        assert versions[2]["version_number"] == 1
    
    async def test_list_versions_with_auto_saves(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence_with_timeline
    ):
        """Test filtering auto-saves"""
        sequence = test_sequence_with_timeline["sequence"]
        
        # Create manual version
        await client.post(
            f"/api/v1/timeline-versions/{sequence.id}/save",
            json={"name": "Manual Version"},
            headers=auth_headers
        )
        
        # Create auto-save
        await client.post(
            f"/api/v1/timeline-versions/{sequence.id}/auto-save",
            headers=auth_headers
        )
        
        # List without auto-saves
        response1 = await client.get(
            f"/api/v1/timeline-versions/{sequence.id}/list?include_auto_saves=false",
            headers=auth_headers
        )
        versions1 = response1.json()
        assert len(versions1) == 1
        assert versions1[0]["name"] == "Manual Version"
        
        # List with auto-saves
        response2 = await client.get(
            f"/api/v1/timeline-versions/{sequence.id}/list?include_auto_saves=true",
            headers=auth_headers
        )
        versions2 = response2.json()
        assert len(versions2) == 2


class TestVersionRetrieval:
    """Test getting specific versions"""
    
    async def test_get_specific_version(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence_with_timeline
    ):
        """Test retrieving a specific version"""
        sequence = test_sequence_with_timeline["sequence"]
        
        # Save a version
        save_response = await client.post(
            f"/api/v1/timeline-versions/{sequence.id}/save",
            json={"name": "Test Version"},
            headers=auth_headers
        )
        version = save_response.json()
        
        # Get the version
        response = await client.get(
            f"/api/v1/timeline-versions/{sequence.id}/version/{version['id']}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "timeline_data" in data
        assert data["version"]["id"] == version["id"]
        assert len(data["timeline_data"]["items"]) == 3
    
    async def test_get_nonexistent_version(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence_with_timeline
    ):
        """Test getting a version that doesn't exist"""
        sequence = test_sequence_with_timeline["sequence"]
        
        response = await client.get(
            f"/api/v1/timeline-versions/{sequence.id}/version/nonexistent",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        assert "Version not found" in response.json()["detail"]


class TestVersionRestore:
    """Test restoring timeline versions"""
    
    async def test_restore_version(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence_with_timeline,
        db_session: AsyncSession
    ):
        """Test restoring a previous version"""
        sequence = test_sequence_with_timeline["sequence"]
        timeline_items = test_sequence_with_timeline["timeline_items"]
        
        # Save initial version
        save_response = await client.post(
            f"/api/v1/timeline-versions/{sequence.id}/save",
            json={"name": "Original"},
            headers=auth_headers
        )
        original_version = save_response.json()
        
        # Modify timeline
        timeline_items[0].start_time = 2000
        timeline_items[0].end_time = 7000
        await db_session.commit()
        
        # Save modified version
        await client.post(
            f"/api/v1/timeline-versions/{sequence.id}/save",
            json={"name": "Modified"},
            headers=auth_headers
        )
        
        # Restore original version
        restore_response = await client.post(
            f"/api/v1/timeline-versions/{sequence.id}/restore/{original_version['id']}",
            json={"save_current": True},
            headers=auth_headers
        )
        
        assert restore_response.status_code == 200
        data = restore_response.json()
        assert "Timeline restored" in data["message"]
        assert data["items_restored"] == 3
        
        # Verify timeline was restored
        await db_session.refresh(timeline_items[0])
        assert timeline_items[0].start_time == 0
        assert timeline_items[0].end_time == 5000
    
    async def test_restore_without_saving_current(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence_with_timeline
    ):
        """Test restoring without saving current state"""
        sequence = test_sequence_with_timeline["sequence"]
        
        # Save a version
        save_response = await client.post(
            f"/api/v1/timeline-versions/{sequence.id}/save",
            json={"name": "Version 1"},
            headers=auth_headers
        )
        version = save_response.json()
        
        # Restore it without saving current
        restore_response = await client.post(
            f"/api/v1/timeline-versions/{sequence.id}/restore/{version['id']}",
            json={"save_current": False},
            headers=auth_headers
        )
        
        assert restore_response.status_code == 200
        
        # Check that no new version was created
        list_response = await client.get(
            f"/api/v1/timeline-versions/{sequence.id}/list?include_auto_saves=true",
            headers=auth_headers
        )
        versions = list_response.json()
        assert len(versions) == 1


class TestVersionUpdate:
    """Test updating version metadata"""
    
    async def test_update_version_metadata(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence_with_timeline
    ):
        """Test updating version name and description"""
        sequence = test_sequence_with_timeline["sequence"]
        
        # Save a version
        save_response = await client.post(
            f"/api/v1/timeline-versions/{sequence.id}/save",
            json={"name": "Original Name"},
            headers=auth_headers
        )
        version = save_response.json()
        
        # Update it
        update_response = await client.patch(
            f"/api/v1/timeline-versions/{sequence.id}/version/{version['id']}",
            json={
                "name": "Updated Name",
                "description": "New description",
                "metadata": {"status": "approved"}
            },
            headers=auth_headers
        )
        
        assert update_response.status_code == 200
        updated = update_response.json()
        assert updated["name"] == "Updated Name"
        assert updated["description"] == "New description"
        assert updated["metadata"]["status"] == "approved"


class TestVersionDeletion:
    """Test deleting versions"""
    
    async def test_delete_version(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence_with_timeline
    ):
        """Test deleting a version"""
        sequence = test_sequence_with_timeline["sequence"]
        
        # Save two versions
        await client.post(
            f"/api/v1/timeline-versions/{sequence.id}/save",
            json={"name": "Version 1"},
            headers=auth_headers
        )
        
        save_response2 = await client.post(
            f"/api/v1/timeline-versions/{sequence.id}/save",
            json={"name": "Version 2"},
            headers=auth_headers
        )
        version2 = save_response2.json()
        
        # Delete first version (not current)
        response = await client.delete(
            f"/api/v1/timeline-versions/{sequence.id}/version/{version2['parent_version_id']}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert "deleted" in response.json()["message"]
        
        # Verify it's gone
        list_response = await client.get(
            f"/api/v1/timeline-versions/{sequence.id}/list",
            headers=auth_headers
        )
        versions = list_response.json()
        assert len(versions) == 1
        assert versions[0]["name"] == "Version 2"
    
    async def test_cannot_delete_current_version(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence_with_timeline
    ):
        """Test that current version cannot be deleted"""
        sequence = test_sequence_with_timeline["sequence"]
        
        # Save a version
        save_response = await client.post(
            f"/api/v1/timeline-versions/{sequence.id}/save",
            json={"name": "Current Version"},
            headers=auth_headers
        )
        version = save_response.json()
        
        # Try to delete it
        response = await client.delete(
            f"/api/v1/timeline-versions/{sequence.id}/version/{version['id']}",
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "Cannot delete the current version" in response.json()["detail"]


class TestVersionComparison:
    """Test comparing versions"""
    
    async def test_compare_versions(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence_with_timeline,
        db_session: AsyncSession
    ):
        """Test comparing two versions"""
        sequence = test_sequence_with_timeline["sequence"]
        timeline_items = test_sequence_with_timeline["timeline_items"]
        
        # Save version 1
        save_response1 = await client.post(
            f"/api/v1/timeline-versions/{sequence.id}/save",
            json={"name": "Version 1"},
            headers=auth_headers
        )
        version1 = save_response1.json()
        
        # Modify timeline: move item, delete item, add transition
        timeline_items[0].start_time = 1000
        timeline_items[0].end_time = 6000
        timeline_items[1].is_enabled = False
        timeline_items[2].transition_in = {"type": "fade", "duration": 500}
        await db_session.commit()
        
        # Save version 2
        save_response2 = await client.post(
            f"/api/v1/timeline-versions/{sequence.id}/save",
            json={"name": "Version 2"},
            headers=auth_headers
        )
        version2 = save_response2.json()
        
        # Compare versions
        compare_response = await client.post(
            f"/api/v1/timeline-versions/{sequence.id}/compare",
            json={
                "version1_id": version1["id"],
                "version2_id": version2["id"]
            },
            headers=auth_headers
        )
        
        assert compare_response.status_code == 200
        comparison = compare_response.json()["comparison"]
        assert comparison["total_items_version1"] == 3
        assert comparison["total_items_version2"] == 3
        assert len(comparison["modified_items"]) == 1  # Item that moved
    
    async def test_compare_with_current(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence_with_timeline
    ):
        """Test comparing a version with current timeline"""
        sequence = test_sequence_with_timeline["sequence"]
        
        # Save a version
        save_response = await client.post(
            f"/api/v1/timeline-versions/{sequence.id}/save",
            json={"name": "Saved Version"},
            headers=auth_headers
        )
        version = save_response.json()
        
        # Compare with current
        compare_response = await client.post(
            f"/api/v1/timeline-versions/{sequence.id}/compare",
            json={
                "version1_id": version["id"],
                "version2_id": "current"
            },
            headers=auth_headers
        )
        
        assert compare_response.status_code == 200
        comparison = compare_response.json()["comparison"]
        assert comparison["unchanged_items"] == 3  # Nothing changed


class TestAutoSave:
    """Test auto-save functionality"""
    
    async def test_auto_save_cleanup(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence_with_timeline,
        db_session: AsyncSession
    ):
        """Test that old auto-saves are cleaned up"""
        sequence = test_sequence_with_timeline["sequence"]
        
        # Create 7 auto-saves
        for i in range(7):
            # Modify timeline slightly to trigger auto-save
            timeline_items = test_sequence_with_timeline["timeline_items"]
            timeline_items[0].metadata = {"iteration": i}
            await db_session.commit()
            
            await client.post(
                f"/api/v1/timeline-versions/{sequence.id}/auto-save",
                headers=auth_headers
            )
        
        # List all versions including auto-saves
        response = await client.get(
            f"/api/v1/timeline-versions/{sequence.id}/list?include_auto_saves=true",
            headers=auth_headers
        )
        
        versions = response.json()
        auto_saves = [v for v in versions if v["is_auto_save"]]
        
        # Should only keep last 5 auto-saves
        assert len(auto_saves) == 5
    
    async def test_auto_save_skip_if_no_changes(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence_with_timeline
    ):
        """Test that auto-save is skipped if no changes"""
        sequence = test_sequence_with_timeline["sequence"]
        
        # Create first auto-save
        response1 = await client.post(
            f"/api/v1/timeline-versions/{sequence.id}/auto-save",
            headers=auth_headers
        )
        assert response1.status_code == 200
        
        # Try again without changes
        response2 = await client.post(
            f"/api/v1/timeline-versions/{sequence.id}/auto-save",
            headers=auth_headers
        )
        
        assert response2.status_code == 200
        assert "No changes detected" in response2.json()["message"]


class TestPermissions:
    """Test permission checks"""
    
    async def test_unauthorized_access(
        self,
        client: AsyncClient,
        test_sequence_with_timeline
    ):
        """Test accessing versions without authentication"""
        sequence = test_sequence_with_timeline["sequence"]
        
        response = await client.post(
            f"/api/v1/timeline-versions/{sequence.id}/save",
            json={"name": "Test"}
        )
        
        assert response.status_code == 401
    
    async def test_forbidden_access(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_sequence_with_timeline,
        db_session: AsyncSession
    ):
        """Test accessing versions without permission"""
        sequence = test_sequence_with_timeline["sequence"]
        
        # Change owner
        sequence.owner_id = uuid4()
        await db_session.commit()
        
        response = await client.post(
            f"/api/v1/timeline-versions/{sequence.id}/save",
            json={"name": "Test"},
            headers=auth_headers
        )
        
        assert response.status_code == 403
        assert "don't have permission" in response.json()["detail"]