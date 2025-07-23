"""
Unit tests for Project Template Service
"""

import pytest
from uuid import uuid4
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.template_service import ProjectTemplateService
from src.models.schemas import ProjectTemplateCreate, ProjectTemplateUpdate
from src.db.models import ProjectTemplate
from src.core.exceptions import (
    ResourceNotFoundError, DuplicateResourceError, ValidationError, PermissionError
)


@pytest.fixture
def template_service(db_session: AsyncSession):
    """Create template service instance"""
    user_id = uuid4()
    return ProjectTemplateService(db_session, user_id), user_id


@pytest.fixture
def valid_template_structure():
    """Valid template structure for testing"""
    return {
        "children": [
            {
                "name": "raw-footage",
                "display_name": "Raw Footage",
                "type": "folder",
                "children": [
                    {
                        "name": "camera-a",
                        "display_name": "Camera A",
                        "type": "bin"
                    }
                ]
            },
            {
                "name": "sequences",
                "display_name": "Sequences",
                "type": "folder",
                "children": [
                    {
                        "name": "rough-cut",
                        "display_name": "Rough Cut",
                        "type": "sequence"
                    }
                ]
            }
        ]
    }


@pytest.mark.asyncio
class TestProjectTemplateService:
    """Test project template service operations"""
    
    async def test_create_template(self, template_service, valid_template_structure):
        """Test creating a new template"""
        service, user_id = template_service
        
        template_data = ProjectTemplateCreate(
            name="Test Template",
            description="A test template",
            category="Test Category",
            structure=valid_template_structure,
            default_settings={"format": "1080p"},
            is_public=True
        )
        
        result = await service.create_template(template_data)
        
        assert result.id is not None
        assert result.name == "Test Template"
        assert result.category == "Test Category"
        assert result.structure == valid_template_structure
        assert result.owner_id == user_id
        assert result.is_public is True
        assert result.is_system is False
    
    async def test_create_duplicate_template_fails(self, template_service, db_session, valid_template_structure):
        """Test that creating a template with duplicate name fails"""
        service, user_id = template_service
        
        # Create first template
        template = ProjectTemplate(
            name="Existing Template",
            description="Existing",
            structure=valid_template_structure,
            owner_id=user_id
        )
        db_session.add(template)
        await db_session.commit()
        
        # Try to create duplicate
        template_data = ProjectTemplateCreate(
            name="Existing Template",
            structure=valid_template_structure
        )
        
        with pytest.raises(DuplicateResourceError) as exc_info:
            await service.create_template(template_data)
        
        assert "already exists" in str(exc_info.value)
    
    async def test_validate_template_structure(self, template_service):
        """Test template structure validation"""
        service, _ = template_service
        
        # Invalid structure - bin with children
        invalid_structure = {
            "children": [
                {
                    "name": "bin-with-children",
                    "type": "bin",
                    "children": [
                        {
                            "name": "invalid-child",
                            "type": "folder"
                        }
                    ]
                }
            ]
        }
        
        template_data = ProjectTemplateCreate(
            name="Invalid Template",
            structure=invalid_structure
        )
        
        with pytest.raises(ValidationError) as exc_info:
            await service.create_template(template_data)
        
        assert "Invalid template structure" in str(exc_info.value)
    
    async def test_get_template(self, template_service, db_session, valid_template_structure):
        """Test retrieving a template"""
        service, user_id = template_service
        
        # Create template
        template = ProjectTemplate(
            name="Test Template",
            structure=valid_template_structure,
            owner_id=user_id,
            is_public=True
        )
        db_session.add(template)
        await db_session.commit()
        
        # Get template
        result = await service.get_template(template.id)
        
        assert result.id == template.id
        assert result.name == "Test Template"
    
    async def test_get_private_template_fails(self, template_service, db_session, valid_template_structure):
        """Test that accessing another user's private template fails"""
        service, _ = template_service
        
        # Create template owned by different user
        template = ProjectTemplate(
            name="Private Template",
            structure=valid_template_structure,
            owner_id=uuid4(),  # Different user
            is_public=False
        )
        db_session.add(template)
        await db_session.commit()
        
        with pytest.raises(ResourceNotFoundError):
            await service.get_template(template.id)
    
    async def test_list_templates(self, template_service, db_session, valid_template_structure):
        """Test listing templates with various filters"""
        service, user_id = template_service
        
        # Create multiple templates
        templates = [
            ProjectTemplate(
                name="Public Template 1",
                category="Video",
                structure=valid_template_structure,
                owner_id=uuid4(),
                is_public=True
            ),
            ProjectTemplate(
                name="Public Template 2",
                category="Audio",
                structure=valid_template_structure,
                owner_id=uuid4(),
                is_public=True
            ),
            ProjectTemplate(
                name="User Template",
                category="Video",
                structure=valid_template_structure,
                owner_id=user_id,
                is_public=False
            ),
            ProjectTemplate(
                name="System Template",
                category="Video",
                structure=valid_template_structure,
                is_system=True,
                is_public=True
            )
        ]
        
        for template in templates:
            db_session.add(template)
        await db_session.commit()
        
        # Test listing all accessible templates
        from src.models.schemas import PaginationParams
        pagination = PaginationParams(page=1, page_size=10)
        
        result = await service.list_templates(pagination)
        assert result.total == 4  # All templates are accessible
        
        # Test filtering by category
        result = await service.list_templates(pagination, category="Video")
        assert result.total == 3
        
        # Test filtering by system templates
        result = await service.list_templates(pagination, is_system=True)
        assert result.total == 1
        assert result.items[0].name == "System Template"
        
        # Test search
        result = await service.list_templates(pagination, search="Public")
        assert result.total == 2
    
    async def test_update_template(self, template_service, db_session, valid_template_structure):
        """Test updating a template"""
        service, user_id = template_service
        
        # Create template
        template = ProjectTemplate(
            name="Original Name",
            description="Original description",
            structure=valid_template_structure,
            owner_id=user_id
        )
        db_session.add(template)
        await db_session.commit()
        
        # Update template
        update_data = ProjectTemplateUpdate(
            name="Updated Name",
            description="Updated description",
            category="New Category"
        )
        
        result = await service.update_template(template.id, update_data)
        
        assert result.name == "Updated Name"
        assert result.description == "Updated description"
        assert result.category == "New Category"
    
    async def test_update_system_template_fails(self, template_service, db_session, valid_template_structure):
        """Test that updating system templates is not allowed"""
        service, _ = template_service
        
        # Create system template
        template = ProjectTemplate(
            name="System Template",
            structure=valid_template_structure,
            is_system=True,
            is_public=True
        )
        db_session.add(template)
        await db_session.commit()
        
        update_data = ProjectTemplateUpdate(name="Hacked!")
        
        with pytest.raises(PermissionError) as exc_info:
            await service.update_template(template.id, update_data)
        
        assert "System templates cannot be modified" in str(exc_info.value)
    
    async def test_delete_template(self, template_service, db_session, valid_template_structure):
        """Test deleting a template"""
        service, user_id = template_service
        
        # Create template
        template = ProjectTemplate(
            name="To Delete",
            structure=valid_template_structure,
            owner_id=user_id
        )
        db_session.add(template)
        await db_session.commit()
        template_id = template.id
        
        # Delete template
        await service.delete_template(template_id)
        
        # Verify deleted
        result = await db_session.get(ProjectTemplate, template_id)
        assert result is None
    
    async def test_duplicate_template(self, template_service, db_session, valid_template_structure):
        """Test duplicating a template"""
        service, user_id = template_service
        
        # Create original template
        original = ProjectTemplate(
            name="Original Template",
            description="Original description",
            category="Test",
            structure=valid_template_structure,
            default_settings={"format": "1080p"},
            owner_id=uuid4(),
            is_public=True
        )
        db_session.add(original)
        await db_session.commit()
        
        # Duplicate template
        result = await service.duplicate_template(original.id, "Duplicated Template")
        
        assert result.name == "Duplicated Template"
        assert result.description == "Duplicated from: Original Template"
        assert result.category == "Test"
        assert result.structure == valid_template_structure
        assert result.default_settings == {"format": "1080p"}
        assert result.owner_id == user_id
        assert result.is_public is False  # Duplicates are private by default
    
    async def test_get_categories(self, template_service, db_session, valid_template_structure):
        """Test getting unique categories"""
        service, user_id = template_service
        
        # Create templates with various categories
        categories = ["Video Production", "Audio Production", "Video Production", "News", None]
        
        for i, category in enumerate(categories):
            template = ProjectTemplate(
                name=f"Template {i}",
                structure=valid_template_structure,
                category=category,
                owner_id=user_id if i % 2 == 0 else uuid4(),
                is_public=True
            )
            db_session.add(template)
        
        await db_session.commit()
        
        # Get categories
        result = await service.get_categories()
        
        assert len(result) == 3  # Unique categories, excluding None
        assert "Video Production" in result
        assert "Audio Production" in result
        assert "News" in result
        assert None not in result
    
    async def test_initialize_system_templates(self, template_service):
        """Test initializing system templates"""
        service, _ = template_service
        
        # Initialize system templates
        result = await service.initialize_system_templates()
        
        assert len(result) > 0
        
        # Verify all are system templates
        for template in result:
            assert template.is_system is True
            assert template.is_public is True
            assert template.owner_id is None
        
        # Verify no duplicates on second run
        result2 = await service.initialize_system_templates()
        assert len(result2) == 0  # No new templates created