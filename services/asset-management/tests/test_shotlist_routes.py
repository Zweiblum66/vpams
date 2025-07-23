"""
Tests for shotlist API routes
"""

import pytest
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import ProjectContainer, Asset, ShotItem, ContainerType, AssetType, AssetStatus
from src.models.schemas import ShotItemCreate


@pytest.fixture
async def test_container(db_session: AsyncSession, test_user):
    """Create a test shotlist container"""
    container = ProjectContainer(
        id=uuid4(),
        name="test-shotlist",
        display_name="Test Shotlist",
        container_type=ContainerType.SHOTLIST,
        owner_id=test_user["user_id"]
    )
    db_session.add(container)
    await db_session.commit()
    return container


@pytest.fixture
async def test_bin(db_session: AsyncSession, test_user):
    """Create a test bin container"""
    container = ProjectContainer(
        id=uuid4(),
        name="test-bin",
        display_name="Test Bin",
        container_type=ContainerType.BIN,
        owner_id=test_user["user_id"]
    )
    db_session.add(container)
    await db_session.commit()
    return container


@pytest.fixture
async def test_asset(db_session: AsyncSession, test_user):
    """Create a test asset"""
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
async def test_shot(db_session: AsyncSession, test_container, test_asset, test_user):
    """Create a test shot item"""
    shot = ShotItem(
        id=uuid4(),
        container_id=test_container.id,
        asset_id=test_asset.id,
        name="Test Shot",
        description="A test shot item",
        in_point=0,
        out_point=2500,
        duration=2500,
        created_by=test_user["user_id"]
    )
    db_session.add(shot)
    await db_session.commit()
    return shot


class TestShotItemCreation:
    """Test shot item creation"""
    
    async def test_create_shot_item(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_container,
        test_asset
    ):
        """Test creating a shot item"""
        shot_data = {
            "container_id": str(test_container.id),
            "asset_id": str(test_asset.id),
            "name": "New Shot",
            "description": "A new shot",
            "in_point": 1000,
            "out_point": 3000
        }
        
        response = await client.post(
            f"/api/v1/shotlists/{test_container.id}/shots",
            json=shot_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Shot"
        assert data["in_point"] == 1000
        assert data["out_point"] == 3000
        assert data["duration"] == 2000
    
    async def test_create_shot_in_bin(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_bin,
        test_asset
    ):
        """Test creating a shot item in a bin"""
        shot_data = {
            "container_id": str(test_bin.id),
            "asset_id": str(test_asset.id),
            "name": "Bin Shot",
            "in_point": 0,
            "out_point": 1500
        }
        
        response = await client.post(
            f"/api/v1/shotlists/{test_bin.id}/shots",
            json=shot_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Bin Shot"
        assert data["duration"] == 1500
    
    async def test_create_shot_invalid_container_type(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_asset,
        test_user,
        db_session: AsyncSession
    ):
        """Test creating a shot in invalid container type"""
        # Create a project container (not valid for shots)
        project = ProjectContainer(
            id=uuid4(),
            name="test-project",
            display_name="Test Project",
            container_type=ContainerType.PROJECT,
            owner_id=test_user["user_id"]
        )
        db_session.add(project)
        await db_session.commit()
        
        shot_data = {
            "container_id": str(project.id),
            "asset_id": str(test_asset.id),
            "name": "Invalid Shot",
            "in_point": 0,
            "out_point": 1000
        }
        
        response = await client.post(
            f"/api/v1/shotlists/{project.id}/shots",
            json=shot_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "Cannot add shots to container type: project" in response.json()["detail"]
    
    async def test_create_shot_nonexistent_asset(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_container
    ):
        """Test creating a shot with nonexistent asset"""
        shot_data = {
            "container_id": str(test_container.id),
            "asset_id": str(uuid4()),
            "name": "Invalid Shot",
            "in_point": 0,
            "out_point": 1000
        }
        
        response = await client.post(
            f"/api/v1/shotlists/{test_container.id}/shots",
            json=shot_data,
            headers=auth_headers
        )
        
        assert response.status_code == 404
        assert "Asset not found" in response.json()["detail"]


class TestShotItemRetrieval:
    """Test shot item retrieval"""
    
    async def test_get_container_shots(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_container,
        test_shot
    ):
        """Test getting all shots in a container"""
        response = await client.get(
            f"/api/v1/shotlists/{test_container.id}/shots",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == str(test_shot.id)
        assert data[0]["name"] == test_shot.name
    
    async def test_get_single_shot(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_shot
    ):
        """Test getting a single shot item"""
        response = await client.get(
            f"/api/v1/shotlists/shots/{test_shot.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_shot.id)
        assert data["name"] == test_shot.name
        assert data["in_point"] == test_shot.in_point
        assert data["out_point"] == test_shot.out_point
    
    async def test_get_nonexistent_shot(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """Test getting a nonexistent shot"""
        response = await client.get(
            f"/api/v1/shotlists/shots/{uuid4()}",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        assert "Shot item not found" in response.json()["detail"]


class TestShotItemUpdate:
    """Test shot item updates"""
    
    async def test_update_shot(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_shot
    ):
        """Test updating a shot item"""
        update_data = {
            "name": "Updated Shot",
            "description": "Updated description",
            "in_point": 500,
            "out_point": 2000
        }
        
        response = await client.put(
            f"/api/v1/shotlists/shots/{test_shot.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Shot"
        assert data["description"] == "Updated description"
        assert data["in_point"] == 500
        assert data["out_point"] == 2000
        assert data["duration"] == 1500
    
    async def test_partial_update_shot(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_shot
    ):
        """Test partial update of a shot item"""
        update_data = {
            "name": "Partially Updated Shot"
        }
        
        response = await client.put(
            f"/api/v1/shotlists/shots/{test_shot.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Partially Updated Shot"
        # Other fields should remain unchanged
        assert data["in_point"] == test_shot.in_point
        assert data["out_point"] == test_shot.out_point


class TestShotItemDeletion:
    """Test shot item deletion"""
    
    async def test_delete_shot(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_shot
    ):
        """Test deleting a shot item"""
        response = await client.delete(
            f"/api/v1/shotlists/shots/{test_shot.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json()["detail"] == "Shot item deleted successfully"
        
        # Verify deletion
        get_response = await client.get(
            f"/api/v1/shotlists/shots/{test_shot.id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404


class TestShotItemDuplication:
    """Test shot item duplication"""
    
    async def test_duplicate_shot(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_shot
    ):
        """Test duplicating a shot item"""
        response = await client.post(
            f"/api/v1/shotlists/shots/{test_shot.id}/duplicate",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == f"{test_shot.name} (copy)"
        assert data["in_point"] == test_shot.in_point
        assert data["out_point"] == test_shot.out_point
        assert data["id"] != str(test_shot.id)
    
    async def test_duplicate_shot_to_different_container(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_shot,
        test_bin
    ):
        """Test duplicating a shot to a different container"""
        response = await client.post(
            f"/api/v1/shotlists/shots/{test_shot.id}/duplicate",
            json={"target_container_id": str(test_bin.id)},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["container_id"] == str(test_bin.id)
        assert data["name"] == f"{test_shot.name} (copy)"


class TestShotReordering:
    """Test shot reordering"""
    
    async def test_reorder_shots(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_container,
        test_asset,
        db_session: AsyncSession
    ):
        """Test reordering shots in a container"""
        # Create multiple shots
        shots = []
        for i in range(3):
            shot = ShotItem(
                id=uuid4(),
                container_id=test_container.id,
                asset_id=test_asset.id,
                name=f"Shot {i}",
                in_point=i * 1000,
                out_point=(i + 1) * 1000,
                sort_order=i,
                created_by=test_asset.owner_id
            )
            db_session.add(shot)
            shots.append(shot)
        
        await db_session.commit()
        
        # Reverse the order
        new_order = [str(s.id) for s in reversed(shots)]
        
        response = await client.put(
            f"/api/v1/shotlists/{test_container.id}/shots/reorder",
            json=new_order,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Verify new order
        get_response = await client.get(
            f"/api/v1/shotlists/{test_container.id}/shots",
            headers=auth_headers
        )
        
        reordered_shots = get_response.json()
        assert reordered_shots[0]["id"] == new_order[0]
        assert reordered_shots[1]["id"] == new_order[1]
        assert reordered_shots[2]["id"] == new_order[2]


class TestBatchOperations:
    """Test batch shot operations"""
    
    async def test_batch_create_shots(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_container,
        test_asset,
        db_session: AsyncSession
    ):
        """Test creating multiple shots at once"""
        # Create another asset
        asset2 = Asset(
            id=uuid4(),
            name="test-video2.mp4",
            display_name="Test Video 2",
            file_path="/storage/test-video2.mp4",
            file_size=2000000,
            asset_type=AssetType.VIDEO,
            status=AssetStatus.ACTIVE,
            storage_driver="local",
            storage_path="/storage/test-video2.mp4",
            owner_id=test_asset.owner_id
        )
        db_session.add(asset2)
        await db_session.commit()
        
        shots_data = [
            {
                "container_id": str(test_container.id),
                "asset_id": str(test_asset.id),
                "name": "Batch Shot 1",
                "in_point": 0,
                "out_point": 1000
            },
            {
                "container_id": str(test_container.id),
                "asset_id": str(asset2.id),
                "name": "Batch Shot 2",
                "in_point": 2000,
                "out_point": 4000
            }
        ]
        
        response = await client.post(
            f"/api/v1/shotlists/{test_container.id}/shots/batch",
            json=shots_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "Batch Shot 1"
        assert data[1]["name"] == "Batch Shot 2"
        assert data[0]["duration"] == 1000
        assert data[1]["duration"] == 2000


class TestPermissions:
    """Test permission checks"""
    
    async def test_unauthorized_access(
        self,
        client: AsyncClient,
        test_shot
    ):
        """Test accessing shots without authentication"""
        response = await client.get(
            f"/api/v1/shotlists/shots/{test_shot.id}"
        )
        
        assert response.status_code == 401
    
    async def test_forbidden_update(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_shot,
        test_user,
        db_session: AsyncSession
    ):
        """Test updating shot without permission"""
        # Create another user
        other_user_id = uuid4()
        
        # Update container owner to other user
        container = await db_session.get(ProjectContainer, test_shot.container_id)
        container.owner_id = other_user_id
        await db_session.commit()
        
        update_data = {"name": "Forbidden Update"}
        
        response = await client.put(
            f"/api/v1/shotlists/shots/{test_shot.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 403
        assert "don't have permission" in response.json()["detail"]