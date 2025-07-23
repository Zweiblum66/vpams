"""
Unit tests for Container Sharing Service
"""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.sharing_service import ContainerSharingService
from src.models.schemas import ContainerShareCreate, ContainerShareUpdate
from src.db.models import ProjectContainer, ContainerType, ContainerShare
from src.core.exceptions import (
    ResourceNotFoundError, DuplicateResourceError, ValidationError, PermissionError
)


@pytest.fixture
def sharing_service(db_session: AsyncSession):
    """Create sharing service instance"""
    user_id = uuid4()
    return ContainerSharingService(db_session, user_id), user_id


@pytest.fixture
async def test_container(db_session: AsyncSession):
    """Create a test container"""
    owner_id = uuid4()
    container = ProjectContainer(
        name="test-project",
        display_name="Test Project",
        container_type=ContainerType.PROJECT,
        owner_id=owner_id,
        path="test-project",
        is_public=False
    )
    db_session.add(container)
    await db_session.commit()
    return container, owner_id


@pytest.mark.asyncio
class TestContainerSharingService:
    """Test container sharing service operations"""
    
    async def test_create_share(self, sharing_service, test_container, db_session):
        """Test creating a new share"""
        service, _ = sharing_service
        container, owner_id = test_container
        
        # Set service user as owner to have permission to share
        service.current_user_id = owner_id
        
        share_data = ContainerShareCreate(
            container_id=container.id,
            shared_with_id=uuid4(),
            shared_with_type="user",
            can_view=True,
            can_add_assets=True,
            can_edit=False,
            note="Test share"
        )
        
        result = await service.create_share(share_data)
        
        assert result.id is not None
        assert result.container_id == container.id
        assert result.shared_with_id == share_data.shared_with_id
        assert result.can_view is True
        assert result.can_add_assets is True
        assert result.can_edit is False
        assert result.shared_by == owner_id
    
    async def test_create_duplicate_share_fails(self, sharing_service, test_container, db_session):
        """Test that creating duplicate shares fails"""
        service, _ = sharing_service
        container, owner_id = test_container
        service.current_user_id = owner_id
        
        shared_with_id = uuid4()
        
        # Create first share
        share = ContainerShare(
            container_id=container.id,
            shared_with_id=shared_with_id,
            shared_with_type="user",
            shared_by=owner_id
        )
        db_session.add(share)
        await db_session.commit()
        
        # Try to create duplicate
        share_data = ContainerShareCreate(
            container_id=container.id,
            shared_with_id=shared_with_id,
            shared_with_type="user"
        )
        
        with pytest.raises(DuplicateResourceError) as exc_info:
            await service.create_share(share_data)
        
        assert "already exists" in str(exc_info.value)
    
    async def test_invalid_permissions_hierarchy(self, sharing_service, test_container):
        """Test that invalid permission combinations are rejected"""
        service, _ = sharing_service
        container, owner_id = test_container
        service.current_user_id = owner_id
        
        # Try to grant delete without edit
        share_data = ContainerShareCreate(
            container_id=container.id,
            shared_with_id=uuid4(),
            shared_with_type="user",
            can_view=True,
            can_add_assets=True,
            can_edit=False,
            can_delete=True  # Invalid: requires can_edit
        )
        
        with pytest.raises(ValidationError) as exc_info:
            await service.create_share(share_data)
        
        assert "Invalid permission combination" in str(exc_info.value)
    
    async def test_share_with_expiration(self, sharing_service, test_container):
        """Test creating a share with expiration date"""
        service, _ = sharing_service
        container, owner_id = test_container
        service.current_user_id = owner_id
        
        expires_at = datetime.utcnow() + timedelta(days=7)
        
        share_data = ContainerShareCreate(
            container_id=container.id,
            shared_with_id=uuid4(),
            shared_with_type="user",
            expires_at=expires_at
        )
        
        result = await service.create_share(share_data)
        
        assert result.expires_at is not None
        assert result.expires_at == expires_at
    
    async def test_list_user_shares_received(self, sharing_service, test_container, db_session):
        """Test listing shares received by a user"""
        service, user_id = sharing_service
        container, owner_id = test_container
        
        # Create shares for the test user
        shares = []
        for i in range(3):
            share = ContainerShare(
                container_id=container.id,
                shared_with_id=user_id,
                shared_with_type="user",
                shared_by=owner_id,
                note=f"Share {i}"
            )
            shares.append(share)
            db_session.add(share)
        
        # Create a share for a different user
        other_share = ContainerShare(
            container_id=container.id,
            shared_with_id=uuid4(),
            shared_with_type="user",
            shared_by=owner_id
        )
        db_session.add(other_share)
        
        await db_session.commit()
        
        # List received shares
        from src.models.schemas import PaginationParams
        pagination = PaginationParams(page=1, page_size=10)
        
        result = await service.list_user_shares(pagination, share_type="received")
        
        assert result.total == 3
        assert all(item.shared_with_id == user_id for item in result.items)
    
    async def test_list_user_shares_given(self, sharing_service, test_container, db_session):
        """Test listing shares created by a user"""
        service, user_id = sharing_service
        container, owner_id = test_container
        
        # User needs to own the container to share it
        container.owner_id = user_id
        await db_session.commit()
        
        # Create shares by the test user
        for i in range(2):
            share = ContainerShare(
                container_id=container.id,
                shared_with_id=uuid4(),
                shared_with_type="user",
                shared_by=user_id
            )
            db_session.add(share)
        
        await db_session.commit()
        
        # List given shares
        from src.models.schemas import PaginationParams
        pagination = PaginationParams(page=1, page_size=10)
        
        result = await service.list_user_shares(pagination, share_type="given")
        
        assert result.total == 2
        assert all(item.shared_by == user_id for item in result.items)
    
    async def test_update_share_permissions(self, sharing_service, test_container, db_session):
        """Test updating share permissions"""
        service, _ = sharing_service
        container, owner_id = test_container
        service.current_user_id = owner_id
        
        # Create share
        share = ContainerShare(
            container_id=container.id,
            shared_with_id=uuid4(),
            shared_with_type="user",
            shared_by=owner_id,
            can_view=True,
            can_add_assets=False,
            can_edit=False
        )
        db_session.add(share)
        await db_session.commit()
        
        # Update permissions
        update_data = ContainerShareUpdate(
            can_add_assets=True,
            can_edit=True,
            note="Updated permissions"
        )
        
        result = await service.update_share(share.id, update_data)
        
        assert result.can_add_assets is True
        assert result.can_edit is True
        assert result.note == "Updated permissions"
    
    async def test_revoke_share(self, sharing_service, test_container, db_session):
        """Test revoking a share"""
        service, _ = sharing_service
        container, owner_id = test_container
        service.current_user_id = owner_id
        
        # Create share
        share = ContainerShare(
            container_id=container.id,
            shared_with_id=uuid4(),
            shared_with_type="user",
            shared_by=owner_id
        )
        db_session.add(share)
        await db_session.commit()
        share_id = share.id
        
        # Revoke share
        await service.revoke_share(share_id)
        
        # Verify deleted
        result = await db_session.get(ContainerShare, share_id)
        assert result is None
    
    async def test_permission_denied_for_non_owner(self, sharing_service, test_container):
        """Test that non-owners cannot share containers"""
        service, user_id = sharing_service
        container, owner_id = test_container
        
        # User is not the owner
        assert user_id != owner_id
        
        share_data = ContainerShareCreate(
            container_id=container.id,
            shared_with_id=uuid4(),
            shared_with_type="user"
        )
        
        with pytest.raises(PermissionError) as exc_info:
            await service.create_share(share_data)
        
        assert "don't have permission to share" in str(exc_info.value)
    
    async def test_user_with_share_permission_can_reshare(self, sharing_service, test_container, db_session):
        """Test that users with share permission can create new shares"""
        service, user_id = sharing_service
        container, owner_id = test_container
        
        # Give user share permission
        share = ContainerShare(
            container_id=container.id,
            shared_with_id=user_id,
            shared_with_type="user",
            shared_by=owner_id,
            can_view=True,
            can_share=True
        )
        db_session.add(share)
        await db_session.commit()
        
        # Now user should be able to share
        share_data = ContainerShareCreate(
            container_id=container.id,
            shared_with_id=uuid4(),
            shared_with_type="user"
        )
        
        result = await service.create_share(share_data)
        
        assert result.shared_by == user_id
    
    async def test_cleanup_expired_shares(self, sharing_service, test_container, db_session):
        """Test cleaning up expired shares"""
        service, _ = sharing_service
        container, owner_id = test_container
        
        # Create expired share
        expired_share = ContainerShare(
            container_id=container.id,
            shared_with_id=uuid4(),
            shared_with_type="user",
            shared_by=owner_id,
            expires_at=datetime.utcnow() - timedelta(days=1)  # Expired yesterday
        )
        
        # Create valid share
        valid_share = ContainerShare(
            container_id=container.id,
            shared_with_id=uuid4(),
            shared_with_type="user",
            shared_by=owner_id,
            expires_at=datetime.utcnow() + timedelta(days=1)  # Expires tomorrow
        )
        
        db_session.add_all([expired_share, valid_share])
        await db_session.commit()
        
        # Cleanup expired shares
        deleted_count = await service.cleanup_expired_shares()
        
        assert deleted_count == 1
        
        # Verify only expired share was deleted
        assert await db_session.get(ContainerShare, expired_share.id) is None
        assert await db_session.get(ContainerShare, valid_share.id) is not None
    
    async def test_record_access(self, sharing_service, test_container, db_session):
        """Test recording share access"""
        service, _ = sharing_service
        container, owner_id = test_container
        
        # Create share
        share = ContainerShare(
            container_id=container.id,
            shared_with_id=uuid4(),
            shared_with_type="user",
            shared_by=owner_id
        )
        db_session.add(share)
        await db_session.commit()
        
        # Record access
        await service.record_access(share.id)
        
        # Verify last_accessed_at was updated
        await db_session.refresh(share)
        assert share.last_accessed_at is not None