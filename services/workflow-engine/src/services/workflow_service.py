"""
Workflow Service

This module handles workflow CRUD operations and management, including:
- Workflow creation and updates
- Version management
- Workflow validation
- Template management
"""

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, func
import structlog

from ..models.schemas import (
    WorkflowDefinition, WorkflowCreateRequest, WorkflowUpdateRequest,
    TaskConfig, TriggerConfig, WorkflowPriority, TriggerType
)
from ..db.models import (
    WorkflowDefinition as WorkflowDefinitionDB,
    WorkflowTemplate as WorkflowTemplateDB
)
from ..core.exceptions import (
    WorkflowNotFoundError, WorkflowValidationError
)

logger = structlog.get_logger()


class WorkflowService:
    """
    Service for managing workflow definitions
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def create_workflow(
        self,
        request: WorkflowCreateRequest
    ) -> WorkflowDefinition:
        """
        Create a new workflow definition
        """
        # Generate workflow ID
        workflow_id = str(uuid.uuid4())
        
        # Validate workflow
        await self._validate_workflow(request)
        
        # Create workflow definition
        workflow = WorkflowDefinitionDB(
            workflow_id=workflow_id,
            name=request.name,
            description=request.description,
            version=1,
            enabled=request.enabled,
            priority=request.priority or WorkflowPriority.MEDIUM,
            triggers=request.triggers or [],
            variables=request.variables or {},
            input_schema=request.input_schema,
            tasks=request.tasks,
            timeout=request.timeout,
            max_retries=request.max_retries or 3,
            retry_delay=request.retry_delay or 60,
            tags=request.tags or [],
            category=request.category,
            created_by=request.created_by or "system",
            deleted=False
        )
        
        self.db.add(workflow)
        await self.db.commit()
        await self.db.refresh(workflow)
        
        logger.info(
            "Workflow created",
            workflow_id=workflow_id,
            name=request.name
        )
        
        return self._to_workflow_definition(workflow)
    
    async def update_workflow(
        self,
        workflow_id: str,
        request: WorkflowUpdateRequest
    ) -> WorkflowDefinition:
        """
        Update workflow definition
        """
        # Load existing workflow
        result = await self.db.execute(
            select(WorkflowDefinitionDB).where(
                WorkflowDefinitionDB.workflow_id == workflow_id,
                WorkflowDefinitionDB.deleted == False
            )
        )
        workflow = result.scalar_one_or_none()
        
        if not workflow:
            raise WorkflowNotFoundError(f"Workflow {workflow_id} not found")
        
        # Check if tasks are being modified
        create_new_version = False
        if request.tasks is not None:
            # Compare task structure
            if self._tasks_modified(workflow.tasks, request.tasks):
                create_new_version = True
        
        if create_new_version:
            # Create new version
            new_workflow = WorkflowDefinitionDB(
                workflow_id=workflow_id,
                name=request.name or workflow.name,
                description=request.description or workflow.description,
                version=workflow.version + 1,
                enabled=request.enabled if request.enabled is not None else workflow.enabled,
                priority=request.priority or workflow.priority,
                triggers=request.triggers or workflow.triggers,
                variables=request.variables or workflow.variables,
                input_schema=request.input_schema or workflow.input_schema,
                tasks=request.tasks or workflow.tasks,
                timeout=request.timeout or workflow.timeout,
                max_retries=request.max_retries if request.max_retries is not None else workflow.max_retries,
                retry_delay=request.retry_delay if request.retry_delay is not None else workflow.retry_delay,
                tags=request.tags or workflow.tags,
                category=request.category or workflow.category,
                created_by=workflow.created_by,
                deleted=False
            )
            
            # Disable old version
            workflow.enabled = False
            
            self.db.add(new_workflow)
            await self.db.commit()
            await self.db.refresh(new_workflow)
            
            logger.info(
                "Workflow version created",
                workflow_id=workflow_id,
                version=new_workflow.version
            )
            
            return self._to_workflow_definition(new_workflow)
        else:
            # Update existing workflow
            update_data = {}
            
            if request.name is not None:
                update_data["name"] = request.name
            if request.description is not None:
                update_data["description"] = request.description
            if request.enabled is not None:
                update_data["enabled"] = request.enabled
            if request.priority is not None:
                update_data["priority"] = request.priority
            if request.triggers is not None:
                update_data["triggers"] = request.triggers
            if request.variables is not None:
                update_data["variables"] = request.variables
            if request.input_schema is not None:
                update_data["input_schema"] = request.input_schema
            if request.timeout is not None:
                update_data["timeout"] = request.timeout
            if request.max_retries is not None:
                update_data["max_retries"] = request.max_retries
            if request.retry_delay is not None:
                update_data["retry_delay"] = request.retry_delay
            if request.tags is not None:
                update_data["tags"] = request.tags
            if request.category is not None:
                update_data["category"] = request.category
            
            if update_data:
                update_data["updated_at"] = datetime.utcnow()
                
                await self.db.execute(
                    update(WorkflowDefinitionDB)
                    .where(WorkflowDefinitionDB.id == workflow.id)
                    .values(**update_data)
                )
                await self.db.commit()
                
                # Refresh workflow
                await self.db.refresh(workflow)
            
            logger.info(
                "Workflow updated",
                workflow_id=workflow_id,
                updates=list(update_data.keys())
            )
            
            return self._to_workflow_definition(workflow)
    
    async def delete_workflow(self, workflow_id: str):
        """
        Soft delete workflow definition
        """
        # Check if workflow exists
        result = await self.db.execute(
            select(WorkflowDefinitionDB).where(
                WorkflowDefinitionDB.workflow_id == workflow_id,
                WorkflowDefinitionDB.deleted == False
            )
        )
        workflow = result.scalar_one_or_none()
        
        if not workflow:
            raise WorkflowNotFoundError(f"Workflow {workflow_id} not found")
        
        # Soft delete
        await self.db.execute(
            update(WorkflowDefinitionDB)
            .where(WorkflowDefinitionDB.workflow_id == workflow_id)
            .values(
                deleted=True,
                deleted_at=datetime.utcnow(),
                enabled=False
            )
        )
        await self.db.commit()
        
        logger.info(
            "Workflow deleted",
            workflow_id=workflow_id
        )
    
    async def get_workflow(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """
        Get workflow definition by ID
        """
        result = await self.db.execute(
            select(WorkflowDefinitionDB).where(
                WorkflowDefinitionDB.workflow_id == workflow_id,
                WorkflowDefinitionDB.deleted == False
            ).order_by(WorkflowDefinitionDB.version.desc())
        )
        workflow = result.first()
        
        if not workflow:
            return None
        
        return self._to_workflow_definition(workflow[0])
    
    async def list_workflows(
        self,
        enabled: Optional[bool] = None,
        category: Optional[str] = None,
        tag: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[WorkflowDefinition], int]:
        """
        List workflow definitions with filtering
        """
        # Build base query - get latest version of each workflow
        subquery = (
            select(
                WorkflowDefinitionDB.workflow_id,
                func.max(WorkflowDefinitionDB.version).label("max_version")
            )
            .where(WorkflowDefinitionDB.deleted == False)
            .group_by(WorkflowDefinitionDB.workflow_id)
            .subquery()
        )
        
        query = select(WorkflowDefinitionDB).join(
            subquery,
            and_(
                WorkflowDefinitionDB.workflow_id == subquery.c.workflow_id,
                WorkflowDefinitionDB.version == subquery.c.max_version
            )
        )
        
        # Apply filters
        if enabled is not None:
            query = query.where(WorkflowDefinitionDB.enabled == enabled)
        
        if category:
            query = query.where(WorkflowDefinitionDB.category == category)
        
        if tag:
            query = query.where(
                WorkflowDefinitionDB.tags.contains([tag])
            )
        
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    WorkflowDefinitionDB.name.ilike(search_pattern),
                    WorkflowDefinitionDB.description.ilike(search_pattern)
                )
            )
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar()
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        query = query.order_by(WorkflowDefinitionDB.created_at.desc())
        
        # Execute query
        result = await self.db.execute(query)
        workflows = result.scalars().all()
        
        # Convert to response models
        workflow_list = [
            self._to_workflow_definition(workflow)
            for workflow in workflows
        ]
        
        return workflow_list, total
    
    async def get_workflow_versions(
        self,
        workflow_id: str
    ) -> List[WorkflowDefinition]:
        """
        Get all versions of a workflow
        """
        result = await self.db.execute(
            select(WorkflowDefinitionDB).where(
                WorkflowDefinitionDB.workflow_id == workflow_id,
                WorkflowDefinitionDB.deleted == False
            ).order_by(WorkflowDefinitionDB.version.desc())
        )
        workflows = result.scalars().all()
        
        return [
            self._to_workflow_definition(workflow)
            for workflow in workflows
        ]
    
    async def create_workflow_from_template(
        self,
        template_id: str,
        name: str,
        description: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
        created_by: Optional[str] = None
    ) -> WorkflowDefinition:
        """
        Create workflow from template
        """
        # Load template
        result = await self.db.execute(
            select(WorkflowTemplateDB).where(
                WorkflowTemplateDB.template_id == template_id
            )
        )
        template = result.scalar_one_or_none()
        
        if not template:
            raise WorkflowNotFoundError(f"Template {template_id} not found")
        
        # Create workflow from template
        request = WorkflowCreateRequest(
            name=name,
            description=description or template.description,
            enabled=True,
            priority=template.default_priority,
            triggers=template.triggers,
            variables={**template.variables, **(variables or {})},
            input_schema=template.input_schema,
            tasks=template.tasks,
            timeout=template.timeout,
            max_retries=template.max_retries,
            retry_delay=template.retry_delay,
            tags=template.tags,
            category=template.category,
            created_by=created_by
        )
        
        return await self.create_workflow(request)
    
    async def _validate_workflow(self, workflow: WorkflowCreateRequest):
        """
        Validate workflow definition
        """
        # Validate workflow name
        if not workflow.name or len(workflow.name) < 3:
            raise WorkflowValidationError("Workflow name must be at least 3 characters")
        
        # Validate tasks
        if not workflow.tasks:
            raise WorkflowValidationError("Workflow must have at least one task")
        
        # Validate task IDs are unique
        task_ids = set()
        for task in workflow.tasks:
            if task.task_id in task_ids:
                raise WorkflowValidationError(f"Duplicate task ID: {task.task_id}")
            task_ids.add(task.task_id)
        
        # Validate triggers
        if workflow.triggers:
            for trigger in workflow.triggers:
                if trigger.trigger_type == TriggerType.SCHEDULE:
                    if not trigger.schedule:
                        raise WorkflowValidationError("Schedule trigger must have schedule configuration")
                elif trigger.trigger_type == TriggerType.WEBHOOK:
                    if not trigger.webhook_config:
                        raise WorkflowValidationError("Webhook trigger must have webhook configuration")
                elif trigger.trigger_type == TriggerType.EVENT:
                    if not trigger.events:
                        raise WorkflowValidationError("Event trigger must have events configuration")
        
        # Validate timeout
        if workflow.timeout and workflow.timeout < 1:
            raise WorkflowValidationError("Workflow timeout must be at least 1 second")
        
        # Validate retry configuration
        if workflow.max_retries and workflow.max_retries < 0:
            raise WorkflowValidationError("Max retries cannot be negative")
        
        if workflow.retry_delay and workflow.retry_delay < 0:
            raise WorkflowValidationError("Retry delay cannot be negative")
    
    def _tasks_modified(
        self,
        old_tasks: List[Dict[str, Any]],
        new_tasks: List[Dict[str, Any]]
    ) -> bool:
        """
        Check if tasks have been modified
        """
        # Simple comparison - could be made more sophisticated
        if len(old_tasks) != len(new_tasks):
            return True
        
        # Compare task IDs and types
        old_task_ids = {task.get("task_id") for task in old_tasks}
        new_task_ids = {task.get("task_id") for task in new_tasks}
        
        if old_task_ids != new_task_ids:
            return True
        
        # Compare task configurations
        for old_task, new_task in zip(old_tasks, new_tasks):
            if old_task.get("task_type") != new_task.get("task_type"):
                return True
            if old_task.get("parameters") != new_task.get("parameters"):
                return True
        
        return False
    
    def _to_workflow_definition(self, db_workflow: WorkflowDefinitionDB) -> WorkflowDefinition:
        """
        Convert database model to schema model
        """
        return WorkflowDefinition(
            workflow_id=db_workflow.workflow_id,
            name=db_workflow.name,
            description=db_workflow.description,
            version=db_workflow.version,
            enabled=db_workflow.enabled,
            priority=db_workflow.priority,
            triggers=db_workflow.triggers,
            variables=db_workflow.variables,
            input_schema=db_workflow.input_schema,
            tasks=db_workflow.tasks,
            timeout=db_workflow.timeout,
            max_retries=db_workflow.max_retries,
            retry_delay=db_workflow.retry_delay,
            tags=db_workflow.tags,
            category=db_workflow.category,
            created_by=db_workflow.created_by,
            created_at=db_workflow.created_at,
            updated_at=db_workflow.updated_at
        )