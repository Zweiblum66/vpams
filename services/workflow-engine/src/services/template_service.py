"""
Workflow Template Service

This module handles workflow template management, including:
- Loading pre-defined templates
- Creating custom templates
- Template instantiation
"""

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, func
import structlog

from ..models.schemas import WorkflowCreateRequest, WorkflowPriority
from ..db.models import WorkflowTemplate as WorkflowTemplateDB
from ..templates import TEMPLATE_REGISTRY, TEMPLATES_BY_CATEGORY
from .workflow_service import WorkflowService

logger = structlog.get_logger()


class TemplateService:
    """
    Service for managing workflow templates
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.workflow_service = WorkflowService(db_session)
    
    async def initialize_templates(self):
        """
        Initialize pre-defined templates in the database
        """
        logger.info("Initializing workflow templates")
        
        for template_data in TEMPLATE_REGISTRY.values():
            # Check if template already exists
            result = await self.db.execute(
                select(WorkflowTemplateDB).where(
                    WorkflowTemplateDB.template_id == template_data["template_id"]
                )
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                # Create template
                definition = template_data["definition"]
                template = WorkflowTemplateDB(
                    template_id=template_data["template_id"],
                    name=template_data["name"],
                    description=template_data["description"],
                    category=template_data["category"],
                    definition=definition,
                    default_priority=definition.get("default_priority", WorkflowPriority.NORMAL),
                    triggers=definition.get("triggers", []),
                    variables=definition.get("variables", {}),
                    input_schema=definition.get("input_schema"),
                    tasks=definition.get("tasks", []),
                    timeout=definition.get("timeout", 3600),
                    max_retries=definition.get("max_retries", 3),
                    retry_delay=definition.get("retry_delay", 300),
                    tags=template_data["tags"],
                    is_public=template_data["is_public"],
                    created_by="system"
                )
                self.db.add(template)
                
                logger.info(
                    "Created template",
                    template_id=template_data["template_id"]
                )
        
        await self.db.commit()
        logger.info("Template initialization complete")
    
    async def list_templates(
        self,
        category: Optional[str] = None,
        tag: Optional[str] = None,
        search: Optional[str] = None,
        is_public: Optional[bool] = None,
        created_by: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[WorkflowTemplateDB], int]:
        """
        List workflow templates with filtering
        """
        # Build query
        query = select(WorkflowTemplateDB)
        
        # Apply filters
        filters = []
        
        if category:
            filters.append(WorkflowTemplateDB.category == category)
        
        if tag:
            filters.append(WorkflowTemplateDB.tags.contains([tag]))
        
        if search:
            search_pattern = f"%{search}%"
            filters.append(
                or_(
                    WorkflowTemplateDB.name.ilike(search_pattern),
                    WorkflowTemplateDB.description.ilike(search_pattern)
                )
            )
        
        if is_public is not None:
            filters.append(WorkflowTemplateDB.is_public == is_public)
        
        if created_by:
            filters.append(WorkflowTemplateDB.created_by == created_by)
        
        if filters:
            query = query.where(and_(*filters))
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar()
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        query = query.order_by(WorkflowTemplateDB.created_at.desc())
        
        # Execute query
        result = await self.db.execute(query)
        templates = result.scalars().all()
        
        return templates, total
    
    async def get_template(self, template_id: str) -> Optional[WorkflowTemplateDB]:
        """
        Get template by ID
        """
        result = await self.db.execute(
            select(WorkflowTemplateDB).where(
                WorkflowTemplateDB.template_id == template_id
            )
        )
        return result.scalar_one_or_none()
    
    async def create_template(
        self,
        name: str,
        description: str,
        category: str,
        definition: Dict[str, Any],
        tags: List[str] = None,
        is_public: bool = False,
        created_by: str = None
    ) -> WorkflowTemplateDB:
        """
        Create a custom workflow template
        """
        template_id = f"custom-{uuid.uuid4()}"
        
        template = WorkflowTemplateDB(
            template_id=template_id,
            name=name,
            description=description,
            category=category,
            definition=definition,
            tags=tags or [],
            is_public=is_public,
            created_by=created_by or "user"
        )
        
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        
        logger.info(
            "Created custom template",
            template_id=template_id,
            name=name
        )
        
        return template
    
    async def update_template(
        self,
        template_id: str,
        updates: Dict[str, Any]
    ) -> Optional[WorkflowTemplateDB]:
        """
        Update a template
        """
        template = await self.get_template(template_id)
        if not template:
            return None
        
        # Only allow updating custom templates
        if not template.template_id.startswith("custom-"):
            raise ValueError("Cannot update pre-defined templates")
        
        # Apply updates
        update_data = {}
        
        if "name" in updates:
            update_data["name"] = updates["name"]
        if "description" in updates:
            update_data["description"] = updates["description"]
        if "category" in updates:
            update_data["category"] = updates["category"]
        if "definition" in updates:
            update_data["definition"] = updates["definition"]
        if "tags" in updates:
            update_data["tags"] = updates["tags"]
        if "is_public" in updates:
            update_data["is_public"] = updates["is_public"]
        
        if update_data:
            update_data["updated_at"] = datetime.utcnow()
            
            await self.db.execute(
                update(WorkflowTemplateDB)
                .where(WorkflowTemplateDB.template_id == template_id)
                .values(**update_data)
            )
            await self.db.commit()
            
            # Refresh template
            await self.db.refresh(template)
        
        return template
    
    async def delete_template(self, template_id: str) -> bool:
        """
        Delete a custom template
        """
        template = await self.get_template(template_id)
        if not template:
            return False
        
        # Only allow deleting custom templates
        if not template.template_id.startswith("custom-"):
            raise ValueError("Cannot delete pre-defined templates")
        
        await self.db.delete(template)
        await self.db.commit()
        
        logger.info("Deleted template", template_id=template_id)
        return True
    
    async def instantiate_template(
        self,
        template_id: str,
        name: str,
        description: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
        enabled: bool = True,
        created_by: Optional[str] = None
    ) -> str:
        """
        Create a workflow from a template
        """
        template = await self.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")
        
        # Update usage stats
        await self.db.execute(
            update(WorkflowTemplateDB)
            .where(WorkflowTemplateDB.template_id == template_id)
            .values(
                usage_count=WorkflowTemplateDB.usage_count + 1,
                last_used_at=datetime.utcnow()
            )
        )
        await self.db.commit()
        
        # Create workflow from template
        definition = template.definition.copy()
        
        # Merge variables
        if variables and "variables" in definition:
            definition["variables"].update(variables)
        
        # Create workflow request
        request = WorkflowCreateRequest(
            name=name,
            description=description or template.description,
            enabled=enabled,
            priority=definition.get("default_priority"),
            triggers=definition.get("triggers", []),
            variables=definition.get("variables", {}),
            input_schema=definition.get("input_schema"),
            tasks=definition.get("tasks", []),
            timeout=definition.get("timeout"),
            max_retries=definition.get("max_retries"),
            retry_delay=definition.get("retry_delay"),
            tags=template.tags,
            category=template.category,
            created_by=created_by
        )
        
        # Create workflow
        workflow = await self.workflow_service.create_workflow(request)
        
        logger.info(
            "Instantiated template",
            template_id=template_id,
            workflow_id=workflow.workflow_id
        )
        
        return workflow.workflow_id
    
    async def get_template_stats(self) -> Dict[str, Any]:
        """
        Get template usage statistics
        """
        # Total templates
        total_templates = (await self.db.execute(
            select(func.count()).select_from(WorkflowTemplateDB)
        )).scalar()
        
        # Public templates
        public_templates = (await self.db.execute(
            select(func.count()).select_from(WorkflowTemplateDB)
            .where(WorkflowTemplateDB.is_public == True)
        )).scalar()
        
        # Templates by category
        category_result = await self.db.execute(
            select(
                WorkflowTemplateDB.category,
                func.count().label("count")
            ).group_by(WorkflowTemplateDB.category)
        )
        templates_by_category = {
            row.category: row.count
            for row in category_result
        }
        
        # Most used templates
        most_used_result = await self.db.execute(
            select(
                WorkflowTemplateDB.template_id,
                WorkflowTemplateDB.name,
                WorkflowTemplateDB.usage_count
            ).order_by(
                WorkflowTemplateDB.usage_count.desc()
            ).limit(5)
        )
        most_used = [
            {
                "template_id": row.template_id,
                "name": row.name,
                "usage_count": row.usage_count
            }
            for row in most_used_result
        ]
        
        # Recently used templates
        recently_used_result = await self.db.execute(
            select(
                WorkflowTemplateDB.template_id,
                WorkflowTemplateDB.name,
                WorkflowTemplateDB.last_used_at
            ).where(
                WorkflowTemplateDB.last_used_at.isnot(None)
            ).order_by(
                WorkflowTemplateDB.last_used_at.desc()
            ).limit(5)
        )
        recently_used = [
            {
                "template_id": row.template_id,
                "name": row.name,
                "last_used_at": row.last_used_at.isoformat() if row.last_used_at else None
            }
            for row in recently_used_result
        ]
        
        return {
            "total_templates": total_templates,
            "public_templates": public_templates,
            "custom_templates": total_templates - len(TEMPLATE_REGISTRY),
            "templates_by_category": templates_by_category,
            "most_used_templates": most_used,
            "recently_used_templates": recently_used
        }