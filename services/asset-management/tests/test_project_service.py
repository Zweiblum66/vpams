"""
Unit tests for Project Container Service
"""

import pytest
from uuid import uuid4
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.project_service import ProjectContainerService
from src.models.schemas import ProjectContainerCreate, ProjectContainerUpdate
from src.db.models import ProjectContainer, ContainerType
from src.core.exceptions import (
    ResourceNotFoundError, ValidationError, PermissionError, ConflictError
)


@pytest.fixture
def project_service(db_session: AsyncSession):
    """Create project service instance"""
    user_id = uuid4()
    return ProjectContainerService(db_session, user_id), user_id


@pytest.mark.asyncio
class TestProjectContainerService:
    """Test project container service operations"""
    
    async def test_create_project_container(self, project_service):
        """Test creating a new project container"""
        service, user_id = project_service
        
        # Create project
        project_data = ProjectContainerCreate(
            name="test-project",
            display_name="Test Project",
            description="A test project",
            container_type=ContainerType.PROJECT,
            is_public=False
        )
        
        result = await service.create_container(project_data)
        
        assert result.id is not None
        assert result.name == "test-project"
        assert result.display_name == "Test Project"
        assert result.container_type == ContainerType.PROJECT
        assert result.owner_id == user_id
        assert result.path == "test-project"
        assert result.parent_id is None
    
    async def test_create_folder_in_project(self, project_service, db_session):
        """Test creating a folder inside a project"""
        service, user_id = project_service
        
        # Create project first
        project = ProjectContainer(
            name="parent-project",
            display_name="Parent Project",
            container_type=ContainerType.PROJECT,
            owner_id=user_id,
            path="parent-project"
        )
        db_session.add(project)
        await db_session.commit()
        
        # Create folder in project
        folder_data = ProjectContainerCreate(
            name="assets",
            display_name="Assets Folder",
            container_type=ContainerType.FOLDER,
            parent_id=project.id
        )
        
        result = await service.create_container(folder_data)
        
        assert result.parent_id == project.id
        assert result.path == "parent-project/assets"
        assert result.container_type == ContainerType.FOLDER
    
    async def test_invalid_hierarchy(self, project_service, db_session):
        """Test that invalid container hierarchies are rejected"""
        service, user_id = project_service
        
        # Create a bin
        bin_container = ProjectContainer(
            name="test-bin",
            display_name="Test Bin",
            container_type=ContainerType.BIN,
            owner_id=user_id,
            path="test-bin"
        )
        db_session.add(bin_container)
        await db_session.commit()
        
        # Try to create a folder inside a bin (invalid)
        folder_data = ProjectContainerCreate(
            name="invalid-folder",
            container_type=ContainerType.FOLDER,
            parent_id=bin_container.id
        )
        
        with pytest.raises(ValidationError) as exc_info:
            await service.create_container(folder_data)
        
        assert "Cannot create folder inside bin" in str(exc_info.value)
    
    async def test_get_container(self, project_service, db_session):
        """Test retrieving a container"""
        service, user_id = project_service
        
        # Create container
        container = ProjectContainer(
            name="test-container",
            display_name="Test Container",
            container_type=ContainerType.PROJECT,
            owner_id=user_id,
            path="test-container"
        )
        db_session.add(container)
        await db_session.commit()
        
        # Get container
        result = await service.get_container(container.id)
        
        assert result.id == container.id
        assert result.name == "test-container"
        assert result.asset_count == 0
        assert result.child_count == 0
    
    async def test_get_nonexistent_container(self, project_service):
        """Test retrieving a non-existent container"""
        service, _ = project_service
        
        with pytest.raises(ResourceNotFoundError):
            await service.get_container(uuid4())
    
    async def test_update_container(self, project_service, db_session):
        """Test updating container properties"""
        service, user_id = project_service
        
        # Create container
        container = ProjectContainer(
            name="test-container",
            display_name="Original Name",
            container_type=ContainerType.PROJECT,
            owner_id=user_id,
            path="test-container"
        )
        db_session.add(container)
        await db_session.commit()
        
        # Update container
        update_data = ProjectContainerUpdate(
            display_name="Updated Name",
            description="New description",
            metadata={"key": "value"}
        )
        
        result = await service.update_container(container.id, update_data)
        
        assert result.display_name == "Updated Name"
        assert result.description == "New description"
        assert result.metadata["key"] == "value"
    
    async def test_delete_empty_container(self, project_service, db_session):
        """Test deleting an empty container"""
        service, user_id = project_service
        
        # Create container
        container = ProjectContainer(
            name="test-container",
            display_name="Test Container",
            container_type=ContainerType.PROJECT,
            owner_id=user_id,
            path="test-container"
        )
        db_session.add(container)
        await db_session.commit()
        
        # Delete container
        await service.delete_container(container.id)
        
        # Verify soft delete
        await db_session.refresh(container)
        assert container.deleted_at is not None
    
    async def test_delete_container_with_children_fails(self, project_service, db_session):
        """Test that deleting a container with children fails without force"""
        service, user_id = project_service
        
        # Create parent and child
        parent = ProjectContainer(
            name="parent",
            display_name="Parent",
            container_type=ContainerType.PROJECT,
            owner_id=user_id,
            path="parent"
        )
        db_session.add(parent)
        await db_session.commit()
        
        child = ProjectContainer(
            name="child",
            display_name="Child",
            container_type=ContainerType.FOLDER,
            parent_id=parent.id,
            owner_id=user_id,
            path="parent/child"
        )
        db_session.add(child)
        await db_session.commit()
        
        # Try to delete parent without force
        with pytest.raises(ConflictError) as exc_info:
            await service.delete_container(parent.id, force=False)
        
        assert "has children" in str(exc_info.value)
    
    async def test_move_container(self, project_service, db_session):
        """Test moving a container to a new parent"""
        service, user_id = project_service
        
        # Create containers
        project1 = ProjectContainer(
            name="project1",
            display_name="Project 1",
            container_type=ContainerType.PROJECT,
            owner_id=user_id,
            path="project1"
        )
        project2 = ProjectContainer(
            name="project2",
            display_name="Project 2",
            container_type=ContainerType.PROJECT,
            owner_id=user_id,
            path="project2"
        )
        folder = ProjectContainer(
            name="folder",
            display_name="Folder",
            container_type=ContainerType.FOLDER,
            parent_id=project1.id,
            owner_id=user_id,
            path="project1/folder"
        )
        
        db_session.add_all([project1, project2, folder])
        await db_session.commit()
        
        # Move folder from project1 to project2
        result = await service.move_container(folder.id, project2.id)
        
        assert result.parent_id == project2.id
        assert result.path == "project2/folder"
    
    async def test_circular_reference_prevention(self, project_service, db_session):
        """Test that circular references are prevented when moving containers"""
        service, user_id = project_service
        
        # Create parent and child
        parent = ProjectContainer(
            name="parent",
            display_name="Parent",
            container_type=ContainerType.FOLDER,
            owner_id=user_id,
            path="parent"
        )
        db_session.add(parent)
        await db_session.commit()
        
        child = ProjectContainer(
            name="child",
            display_name="Child",
            container_type=ContainerType.FOLDER,
            parent_id=parent.id,
            owner_id=user_id,
            path="parent/child"
        )
        db_session.add(child)
        await db_session.commit()
        
        # Try to move parent into child (would create cycle)
        with pytest.raises(ValidationError) as exc_info:
            await service.move_container(parent.id, child.id)
        
        assert "circular reference" in str(exc_info.value)
    
    async def test_list_containers_with_filters(self, project_service, db_session):
        """Test listing containers with various filters"""
        service, user_id = project_service
        
        # Create multiple containers
        project = ProjectContainer(
            name="project",
            display_name="Test Project",
            container_type=ContainerType.PROJECT,
            owner_id=user_id,
            path="project"
        )
        folder = ProjectContainer(
            name="folder",
            display_name="Test Folder",
            container_type=ContainerType.FOLDER,
            owner_id=user_id,
            path="folder"
        )
        public_project = ProjectContainer(
            name="public",
            display_name="Public Project",
            container_type=ContainerType.PROJECT,
            owner_id=uuid4(),  # Different owner
            is_public=True,
            path="public"
        )
        
        db_session.add_all([project, folder, public_project])
        await db_session.commit()
        
        # Test filtering by type
        from src.models.schemas import PaginationParams
        pagination = PaginationParams(page=1, page_size=10)
        
        result = await service.list_containers(
            pagination=pagination,
            container_type=ContainerType.PROJECT
        )
        
        assert result.total == 2  # User's project + public project
        assert all(item.container_type == ContainerType.PROJECT for item in result.items)
        
        # Test search
        result = await service.list_containers(
            pagination=pagination,
            search="Public"
        )
        
        assert result.total == 1
        assert result.items[0].name == "public"
    
    async def test_permission_checks(self, project_service, db_session):
        """Test that permission checks work correctly"""
        service, user_id = project_service
        
        # Create container owned by different user
        other_container = ProjectContainer(
            name="other",
            display_name="Other User's Container",
            container_type=ContainerType.PROJECT,
            owner_id=uuid4(),
            is_public=False,
            path="other"
        )
        db_session.add(other_container)
        await db_session.commit()
        
        # Try to update container owned by another user
        update_data = ProjectContainerUpdate(display_name="Hacked!")
        
        with pytest.raises(PermissionError):
            await service.update_container(other_container.id, update_data)
        
        # Try to delete container owned by another user
        with pytest.raises(PermissionError):
            await service.delete_container(other_container.id)