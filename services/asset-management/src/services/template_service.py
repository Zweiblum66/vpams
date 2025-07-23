"""
Project Template Service

This module handles all project template operations including CRUD
and system template initialization.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, distinct
from sqlalchemy.orm import selectinload
import structlog

from ..db.models import ProjectTemplate, ContainerType
from ..models.schemas import (
    ProjectTemplateCreate, ProjectTemplateUpdate, ProjectTemplateResponse,
    PaginationParams, PaginatedResponse
)
from ..core.exceptions import (
    ResourceNotFoundError, DuplicateResourceError, ValidationError,
    PermissionError
)

logger = structlog.get_logger()


class ProjectTemplateService:
    """Service for managing project templates"""
    
    def __init__(self, db: AsyncSession, current_user_id: UUID):
        self.db = db
        self.current_user_id = current_user_id
    
    async def create_template(
        self, 
        template_data: ProjectTemplateCreate
    ) -> ProjectTemplateResponse:
        """Create a new project template"""
        
        # Check if template name already exists
        existing = await self.db.execute(
            select(ProjectTemplate).where(ProjectTemplate.name == template_data.name)
        )
        if existing.scalar_one_or_none():
            raise DuplicateResourceError(f"Template with name '{template_data.name}' already exists")
        
        # Validate structure
        if not self._validate_template_structure(template_data.structure):
            raise ValidationError("Invalid template structure")
        
        # Create template
        template = ProjectTemplate(
            name=template_data.name,
            description=template_data.description,
            category=template_data.category,
            structure=template_data.structure,
            default_settings=template_data.default_settings or {},
            is_system=False,
            is_public=template_data.is_public,
            owner_id=self.current_user_id
        )
        
        self.db.add(template)
        
        try:
            await self.db.commit()
            await self.db.refresh(template)
            
            logger.info(
                "project_template_created",
                template_id=str(template.id),
                template_name=template.name,
                owner_id=str(template.owner_id)
            )
            
            return self._to_response(template)
            
        except Exception as e:
            await self.db.rollback()
            logger.error("template_creation_failed", error=str(e))
            raise
    
    async def get_template(self, template_id: UUID) -> ProjectTemplateResponse:
        """Get a template by ID"""
        
        query = select(ProjectTemplate).where(
            and_(
                ProjectTemplate.id == template_id,
                or_(
                    ProjectTemplate.is_public == True,
                    ProjectTemplate.owner_id == self.current_user_id,
                    ProjectTemplate.is_system == True
                )
            )
        )
        
        result = await self.db.execute(query)
        template = result.scalar_one_or_none()
        
        if not template:
            raise ResourceNotFoundError(f"Template {template_id} not found or not accessible")
        
        return self._to_response(template)
    
    async def list_templates(
        self,
        pagination: PaginationParams,
        category: Optional[str] = None,
        search: Optional[str] = None,
        is_system: Optional[bool] = None
    ) -> PaginatedResponse:
        """List templates with filtering"""
        
        # Build query
        query = select(ProjectTemplate).where(
            or_(
                ProjectTemplate.is_public == True,
                ProjectTemplate.owner_id == self.current_user_id,
                ProjectTemplate.is_system == True
            )
        )
        
        # Apply filters
        if category:
            query = query.where(ProjectTemplate.category == category)
        
        if is_system is not None:
            query = query.where(ProjectTemplate.is_system == is_system)
        
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    ProjectTemplate.name.ilike(search_pattern),
                    ProjectTemplate.description.ilike(search_pattern)
                )
            )
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)
        
        # Apply pagination
        query = query.offset(pagination.offset).limit(pagination.page_size)
        query = query.order_by(ProjectTemplate.name)
        
        # Execute query
        result = await self.db.execute(query)
        templates = result.scalars().all()
        
        # Convert to response
        items = [self._to_response(template) for template in templates]
        
        return PaginatedResponse(
            items=items,
            total=total or 0,
            page=pagination.page,
            page_size=pagination.page_size,
            pages=(total + pagination.page_size - 1) // pagination.page_size if total else 0
        )
    
    async def update_template(
        self,
        template_id: UUID,
        update_data: ProjectTemplateUpdate
    ) -> ProjectTemplateResponse:
        """Update a template"""
        
        # Get template
        query = select(ProjectTemplate).where(ProjectTemplate.id == template_id)
        result = await self.db.execute(query)
        template = result.scalar_one_or_none()
        
        if not template:
            raise ResourceNotFoundError(f"Template {template_id} not found")
        
        # Check permissions
        if template.is_system:
            raise PermissionError("System templates cannot be modified")
        
        if template.owner_id != self.current_user_id:
            raise PermissionError("You can only modify your own templates")
        
        # Check name uniqueness if changing
        if update_data.name and update_data.name != template.name:
            existing = await self.db.execute(
                select(ProjectTemplate).where(ProjectTemplate.name == update_data.name)
            )
            if existing.scalar_one_or_none():
                raise DuplicateResourceError(f"Template with name '{update_data.name}' already exists")
        
        # Validate structure if provided
        if update_data.structure and not self._validate_template_structure(update_data.structure):
            raise ValidationError("Invalid template structure")
        
        # Update fields
        for field, value in update_data.model_dump(exclude_unset=True).items():
            setattr(template, field, value)
        
        template.updated_at = datetime.utcnow()
        
        try:
            await self.db.commit()
            await self.db.refresh(template)
            
            logger.info(
                "project_template_updated",
                template_id=str(template_id),
                updated_fields=list(update_data.model_dump(exclude_unset=True).keys())
            )
            
            return self._to_response(template)
            
        except Exception as e:
            await self.db.rollback()
            logger.error("template_update_failed", error=str(e), template_id=str(template_id))
            raise
    
    async def delete_template(self, template_id: UUID) -> None:
        """Delete a template"""
        
        # Get template
        query = select(ProjectTemplate).where(ProjectTemplate.id == template_id)
        result = await self.db.execute(query)
        template = result.scalar_one_or_none()
        
        if not template:
            raise ResourceNotFoundError(f"Template {template_id} not found")
        
        # Check permissions
        if template.is_system:
            raise PermissionError("System templates cannot be deleted")
        
        if template.owner_id != self.current_user_id:
            raise PermissionError("You can only delete your own templates")
        
        # Delete template
        await self.db.delete(template)
        
        try:
            await self.db.commit()
            
            logger.info(
                "project_template_deleted",
                template_id=str(template_id),
                template_name=template.name
            )
            
        except Exception as e:
            await self.db.rollback()
            logger.error("template_deletion_failed", error=str(e), template_id=str(template_id))
            raise
    
    async def duplicate_template(
        self,
        template_id: UUID,
        new_name: str
    ) -> ProjectTemplateResponse:
        """Duplicate an existing template"""
        
        # Get original template
        original = await self.get_template(template_id)
        
        # Check if new name already exists
        existing = await self.db.execute(
            select(ProjectTemplate).where(ProjectTemplate.name == new_name)
        )
        if existing.scalar_one_or_none():
            raise DuplicateResourceError(f"Template with name '{new_name}' already exists")
        
        # Create new template
        template_data = ProjectTemplateCreate(
            name=new_name,
            description=f"Duplicated from: {original.name}",
            category=original.category,
            structure=original.structure,
            default_settings=original.default_settings,
            is_public=False  # Duplicated templates are private by default
        )
        
        return await self.create_template(template_data)
    
    async def get_categories(self) -> List[str]:
        """Get all unique template categories"""
        
        query = select(distinct(ProjectTemplate.category)).where(
            and_(
                ProjectTemplate.category.isnot(None),
                or_(
                    ProjectTemplate.is_public == True,
                    ProjectTemplate.owner_id == self.current_user_id,
                    ProjectTemplate.is_system == True
                )
            )
        ).order_by(ProjectTemplate.category)
        
        result = await self.db.execute(query)
        categories = result.scalars().all()
        
        return list(categories)
    
    async def initialize_system_templates(self) -> List[ProjectTemplateResponse]:
        """Initialize default system templates"""
        
        system_templates = [
            {
                "name": "Basic Video Project",
                "description": "A simple video project structure",
                "category": "Video Production",
                "structure": {
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
                                },
                                {
                                    "name": "camera-b",
                                    "display_name": "Camera B",
                                    "type": "bin"
                                },
                                {
                                    "name": "b-roll",
                                    "display_name": "B-Roll",
                                    "type": "bin"
                                }
                            ]
                        },
                        {
                            "name": "audio",
                            "display_name": "Audio",
                            "type": "folder",
                            "children": [
                                {
                                    "name": "music",
                                    "display_name": "Music",
                                    "type": "bin"
                                },
                                {
                                    "name": "sfx",
                                    "display_name": "Sound Effects",
                                    "type": "bin"
                                },
                                {
                                    "name": "voiceover",
                                    "display_name": "Voiceover",
                                    "type": "bin"
                                }
                            ]
                        },
                        {
                            "name": "graphics",
                            "display_name": "Graphics",
                            "type": "folder",
                            "children": [
                                {
                                    "name": "logos",
                                    "display_name": "Logos",
                                    "type": "bin"
                                },
                                {
                                    "name": "titles",
                                    "display_name": "Titles",
                                    "type": "bin"
                                },
                                {
                                    "name": "overlays",
                                    "display_name": "Overlays",
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
                                },
                                {
                                    "name": "fine-cut",
                                    "display_name": "Fine Cut",
                                    "type": "sequence"
                                },
                                {
                                    "name": "final",
                                    "display_name": "Final",
                                    "type": "sequence"
                                }
                            ]
                        },
                        {
                            "name": "exports",
                            "display_name": "Exports",
                            "type": "folder"
                        }
                    ]
                },
                "default_settings": {
                    "video_format": "1920x1080",
                    "frame_rate": "23.976",
                    "color_space": "Rec.709"
                }
            },
            {
                "name": "Documentary Project",
                "description": "Structure for documentary production",
                "category": "Video Production",
                "structure": {
                    "children": [
                        {
                            "name": "interviews",
                            "display_name": "Interviews",
                            "type": "folder",
                            "children": [
                                {
                                    "name": "subject-a",
                                    "display_name": "Subject A",
                                    "type": "bin"
                                },
                                {
                                    "name": "subject-b",
                                    "display_name": "Subject B",
                                    "type": "bin"
                                }
                            ]
                        },
                        {
                            "name": "b-roll",
                            "display_name": "B-Roll",
                            "type": "folder",
                            "children": [
                                {
                                    "name": "locations",
                                    "display_name": "Locations",
                                    "type": "bin"
                                },
                                {
                                    "name": "archival",
                                    "display_name": "Archival",
                                    "type": "bin"
                                }
                            ]
                        },
                        {
                            "name": "research",
                            "display_name": "Research",
                            "type": "folder"
                        },
                        {
                            "name": "selects",
                            "display_name": "Selects",
                            "type": "shotlist"
                        },
                        {
                            "name": "assembly",
                            "display_name": "Assembly",
                            "type": "sequence"
                        }
                    ]
                }
            },
            {
                "name": "News Package",
                "description": "Quick turnaround news story structure",
                "category": "News Production",
                "structure": {
                    "children": [
                        {
                            "name": "field-footage",
                            "display_name": "Field Footage",
                            "type": "bin"
                        },
                        {
                            "name": "interviews",
                            "display_name": "Interviews",
                            "type": "bin"
                        },
                        {
                            "name": "graphics",
                            "display_name": "Graphics",
                            "type": "bin"
                        },
                        {
                            "name": "vo-script",
                            "display_name": "VO Script",
                            "type": "bin"
                        },
                        {
                            "name": "package",
                            "display_name": "Package",
                            "type": "sequence"
                        }
                    ]
                }
            },
            {
                "name": "Music Video",
                "description": "Music video production structure",
                "category": "Music Production",
                "structure": {
                    "children": [
                        {
                            "name": "performance",
                            "display_name": "Performance",
                            "type": "folder",
                            "children": [
                                {
                                    "name": "take-1",
                                    "display_name": "Take 1",
                                    "type": "bin"
                                },
                                {
                                    "name": "take-2",
                                    "display_name": "Take 2",
                                    "type": "bin"
                                },
                                {
                                    "name": "take-3",
                                    "display_name": "Take 3",
                                    "type": "bin"
                                }
                            ]
                        },
                        {
                            "name": "narrative",
                            "display_name": "Narrative",
                            "type": "bin"
                        },
                        {
                            "name": "effects",
                            "display_name": "Effects",
                            "type": "bin"
                        },
                        {
                            "name": "color-grade",
                            "display_name": "Color Grade",
                            "type": "folder"
                        },
                        {
                            "name": "edit",
                            "display_name": "Edit",
                            "type": "sequence"
                        }
                    ]
                }
            },
            {
                "name": "Podcast Episode",
                "description": "Audio podcast production structure",
                "category": "Audio Production",
                "structure": {
                    "children": [
                        {
                            "name": "raw-audio",
                            "display_name": "Raw Audio",
                            "type": "bin"
                        },
                        {
                            "name": "intro-outro",
                            "display_name": "Intro/Outro",
                            "type": "bin"
                        },
                        {
                            "name": "music-beds",
                            "display_name": "Music Beds",
                            "type": "bin"
                        },
                        {
                            "name": "sound-effects",
                            "display_name": "Sound Effects",
                            "type": "bin"
                        },
                        {
                            "name": "edit",
                            "display_name": "Edit",
                            "type": "sequence"
                        },
                        {
                            "name": "exports",
                            "display_name": "Exports",
                            "type": "folder"
                        }
                    ]
                }
            }
        ]
        
        created_templates = []
        
        for template_def in system_templates:
            # Check if template already exists
            existing = await self.db.execute(
                select(ProjectTemplate).where(
                    and_(
                        ProjectTemplate.name == template_def["name"],
                        ProjectTemplate.is_system == True
                    )
                )
            )
            
            if not existing.scalar_one_or_none():
                # Create system template
                template = ProjectTemplate(
                    name=template_def["name"],
                    description=template_def["description"],
                    category=template_def["category"],
                    structure=template_def["structure"],
                    default_settings=template_def.get("default_settings", {}),
                    is_system=True,
                    is_public=True,
                    owner_id=None
                )
                
                self.db.add(template)
                created_templates.append(template)
        
        if created_templates:
            try:
                await self.db.commit()
                
                logger.info(
                    "system_templates_initialized",
                    count=len(created_templates),
                    templates=[t.name for t in created_templates]
                )
                
            except Exception as e:
                await self.db.rollback()
                logger.error("system_template_init_failed", error=str(e))
                raise
        
        return [self._to_response(t) for t in created_templates]
    
    # Helper methods
    
    def _validate_template_structure(self, structure: Dict[str, Any]) -> bool:
        """Validate template structure is valid"""
        
        def validate_node(node: Dict[str, Any]) -> bool:
            # Required fields
            if "name" not in node or "type" not in node:
                return False
            
            # Valid type
            try:
                container_type = ContainerType(node["type"])
            except ValueError:
                return False
            
            # Validate children if present
            if "children" in node:
                if not isinstance(node["children"], list):
                    return False
                
                # Check hierarchy rules
                if container_type in [ContainerType.BIN, ContainerType.SHOTLIST, ContainerType.SEQUENCE]:
                    # These types can't have children
                    return False
                
                # Validate each child
                for child in node["children"]:
                    if not validate_node(child):
                        return False
            
            return True
        
        # Validate root structure
        if not isinstance(structure, dict):
            return False
        
        if "children" in structure:
            if not isinstance(structure["children"], list):
                return False
            
            for child in structure["children"]:
                if not validate_node(child):
                    return False
        
        return True
    
    def _to_response(self, template: ProjectTemplate) -> ProjectTemplateResponse:
        """Convert template to response schema"""
        
        return ProjectTemplateResponse(
            id=template.id,
            name=template.name,
            description=template.description,
            category=template.category,
            structure=template.structure,
            default_settings=template.default_settings,
            is_system=template.is_system,
            is_public=template.is_public,
            owner_id=template.owner_id,
            usage_count=template.usage_count,
            created_at=template.created_at,
            updated_at=template.updated_at
        )