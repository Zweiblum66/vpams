"""
API routes for Workflow Engine Service
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Request, Header
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
import structlog

from ..db.base import get_db
from ..models.schemas import (
    WorkflowDefinition, WorkflowCreateRequest, WorkflowUpdateRequest,
    WorkflowResponse, WorkflowListResponse,
    WorkflowExecuteRequest, WorkflowInstance, WorkflowInstanceResponse,
    WorkflowInstanceListResponse, WorkflowStats,
    WorkflowStatus, TaskStatus, TriggerType, WorkflowPriority
)
from ..db.models import (
    WorkflowDefinition as WorkflowDefinitionDB,
    WorkflowInstance as WorkflowInstanceDB,
    TaskInstance as TaskInstanceDB,
    WorkflowEvent as WorkflowEventDB,
    WorkflowTemplate as WorkflowTemplateDB
)
from ..services.workflow_engine import WorkflowEngine
from ..services.workflow_service import WorkflowService
from ..core.exceptions import (
    WorkflowNotFoundError, WorkflowExecutionError,
    WorkflowValidationError
)

logger = structlog.get_logger()
router = APIRouter()


# Workflow Definition Endpoints

@router.post("/workflows", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    request: WorkflowCreateRequest,
    db: AsyncSession = Depends(get_db)
) -> WorkflowResponse:
    """
    Create a new workflow definition
    
    This endpoint creates a new workflow definition that can be executed multiple times.
    The workflow definition includes:
    - Basic metadata (name, description, tags)
    - Triggers that can automatically start the workflow
    - Variables and input schema
    - Task definitions and execution flow
    """
    try:
        service = WorkflowService(db)
        workflow = await service.create_workflow(request)
        
        return WorkflowResponse(
            workflow_id=workflow.workflow_id,
            name=workflow.name,
            description=workflow.description,
            version=workflow.version,
            enabled=workflow.enabled,
            priority=workflow.priority,
            triggers=workflow.triggers,
            variables=workflow.variables,
            task_count=len(workflow.tasks),
            tags=workflow.tags,
            category=workflow.category,
            created_by=workflow.created_by,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at
        )
        
    except WorkflowValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to create workflow", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create workflow")


@router.get("/workflows", response_model=WorkflowListResponse)
async def list_workflows(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    enabled: Optional[bool] = None,
    category: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
) -> WorkflowListResponse:
    """
    List workflow definitions with pagination and filtering
    
    Query parameters:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20, max: 100)
    - enabled: Filter by enabled status
    - category: Filter by category
    - tag: Filter by tag
    - search: Search in name and description
    """
    try:
        # Build query
        query = select(WorkflowDefinitionDB).where(
            WorkflowDefinitionDB.deleted == False
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
        total = (await db.execute(count_query)).scalar()
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        query = query.order_by(WorkflowDefinitionDB.created_at.desc())
        
        # Execute query
        result = await db.execute(query)
        workflows = result.scalars().all()
        
        # Convert to response models
        workflow_responses = []
        for workflow in workflows:
            workflow_responses.append(WorkflowResponse(
                workflow_id=workflow.workflow_id,
                name=workflow.name,
                description=workflow.description,
                version=workflow.version,
                enabled=workflow.enabled,
                priority=workflow.priority,
                triggers=workflow.triggers,
                variables=workflow.variables,
                task_count=len(workflow.tasks),
                tags=workflow.tags,
                category=workflow.category,
                created_by=workflow.created_by,
                created_at=workflow.created_at,
                updated_at=workflow.updated_at
            ))
        
        return WorkflowListResponse(
            workflows=workflow_responses,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error("Failed to list workflows", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list workflows")


@router.get("/workflows/{workflow_id}", response_model=WorkflowDefinition)
async def get_workflow(
    workflow_id: str = Path(..., description="Workflow ID"),
    db: AsyncSession = Depends(get_db)
) -> WorkflowDefinition:
    """
    Get workflow definition by ID
    
    Returns the complete workflow definition including all tasks and configuration.
    """
    try:
        result = await db.execute(
            select(WorkflowDefinitionDB).where(
                WorkflowDefinitionDB.workflow_id == workflow_id,
                WorkflowDefinitionDB.deleted == False
            )
        )
        workflow = result.scalar_one_or_none()
        
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        return WorkflowDefinition(
            workflow_id=workflow.workflow_id,
            name=workflow.name,
            description=workflow.description,
            version=workflow.version,
            enabled=workflow.enabled,
            priority=workflow.priority,
            triggers=workflow.triggers,
            variables=workflow.variables,
            input_schema=workflow.input_schema,
            tasks=workflow.tasks,
            timeout=workflow.timeout,
            max_retries=workflow.max_retries,
            retry_delay=workflow.retry_delay,
            tags=workflow.tags,
            category=workflow.category,
            created_by=workflow.created_by,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get workflow", workflow_id=workflow_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get workflow")


@router.patch("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: str = Path(..., description="Workflow ID"),
    request: WorkflowUpdateRequest = ...,
    db: AsyncSession = Depends(get_db)
) -> WorkflowResponse:
    """
    Update workflow definition
    
    Partial update of workflow definition. Only provided fields will be updated.
    Note: Updating a workflow creates a new version if tasks are modified.
    """
    try:
        service = WorkflowService(db)
        workflow = await service.update_workflow(workflow_id, request)
        
        return WorkflowResponse(
            workflow_id=workflow.workflow_id,
            name=workflow.name,
            description=workflow.description,
            version=workflow.version,
            enabled=workflow.enabled,
            priority=workflow.priority,
            triggers=workflow.triggers,
            variables=workflow.variables,
            task_count=len(workflow.tasks),
            tags=workflow.tags,
            category=workflow.category,
            created_by=workflow.created_by,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at
        )
        
    except WorkflowNotFoundError:
        raise HTTPException(status_code=404, detail="Workflow not found")
    except WorkflowValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to update workflow", workflow_id=workflow_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update workflow")


@router.delete("/workflows/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: str = Path(..., description="Workflow ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete workflow definition
    
    Soft deletes the workflow definition. Running instances will continue to execute.
    """
    try:
        service = WorkflowService(db)
        await service.delete_workflow(workflow_id)
        
    except WorkflowNotFoundError:
        raise HTTPException(status_code=404, detail="Workflow not found")
    except Exception as e:
        logger.error("Failed to delete workflow", workflow_id=workflow_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete workflow")


# Workflow Execution Endpoints

@router.post("/workflows/{workflow_id}/execute", response_model=WorkflowInstanceResponse)
async def execute_workflow(
    workflow_id: str = Path(..., description="Workflow ID"),
    request: WorkflowExecuteRequest = ...,
    db: AsyncSession = Depends(get_db)
) -> WorkflowInstanceResponse:
    """
    Execute a workflow
    
    Creates a new workflow instance and starts execution.
    The workflow can be executed immediately or scheduled for later.
    """
    try:
        # Validate workflow exists
        result = await db.execute(
            select(WorkflowDefinitionDB).where(
                WorkflowDefinitionDB.workflow_id == workflow_id,
                WorkflowDefinitionDB.enabled == True,
                WorkflowDefinitionDB.deleted == False
            )
        )
        workflow = result.scalar_one_or_none()
        
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found or disabled")
        
        # Create workflow engine
        engine = WorkflowEngine(db)
        
        # Create instance
        instance = await engine.create_workflow_instance(
            workflow_id=workflow_id,
            input_data=request.input_data,
            triggered_by="user",  # TODO: Get from auth context
            trigger_type=TriggerType.MANUAL,
            priority=request.priority,
            scheduled_at=request.scheduled_at,
            tags=request.tags,
            metadata=request.metadata
        )
        
        # Execute if not scheduled
        if not request.scheduled_at:
            await engine.execute_workflow(instance.instance_id, background=True)
        
        return WorkflowInstanceResponse(
            instance_id=instance.instance_id,
            workflow_id=instance.workflow_id,
            workflow_name=instance.workflow_name,
            workflow_version=instance.workflow_version,
            status=instance.status,
            priority=instance.priority,
            triggered_by=instance.triggered_by,
            trigger_type=instance.trigger_type,
            started_at=instance.started_at,
            completed_at=instance.completed_at,
            current_task=instance.current_task_id,
            progress=0.0,  # TODO: Calculate progress
            error_message=instance.error_message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to execute workflow", workflow_id=workflow_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to execute workflow")


@router.get("/instances", response_model=WorkflowInstanceListResponse)
async def list_workflow_instances(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    workflow_id: Optional[str] = None,
    status: Optional[WorkflowStatus] = None,
    triggered_by: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db)
) -> WorkflowInstanceListResponse:
    """
    List workflow instances with pagination and filtering
    
    Query parameters:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20, max: 100)
    - workflow_id: Filter by workflow ID
    - status: Filter by status
    - triggered_by: Filter by who triggered the workflow
    - start_date: Filter by start date (inclusive)
    - end_date: Filter by end date (inclusive)
    """
    try:
        # Build query
        query = select(WorkflowInstanceDB)
        
        # Apply filters
        if workflow_id:
            query = query.where(WorkflowInstanceDB.workflow_id == workflow_id)
        
        if status:
            query = query.where(WorkflowInstanceDB.status == status)
        
        if triggered_by:
            query = query.where(WorkflowInstanceDB.triggered_by == triggered_by)
        
        if start_date:
            query = query.where(WorkflowInstanceDB.created_at >= start_date)
        
        if end_date:
            query = query.where(WorkflowInstanceDB.created_at <= end_date)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar()
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        query = query.order_by(WorkflowInstanceDB.created_at.desc())
        
        # Execute query
        result = await db.execute(query)
        instances = result.scalars().all()
        
        # Convert to response models
        instance_responses = []
        for instance in instances:
            # Calculate progress
            if instance.status == WorkflowStatus.COMPLETED:
                progress = 1.0
            elif instance.status in [WorkflowStatus.PENDING, WorkflowStatus.SCHEDULED]:
                progress = 0.0
            else:
                # TODO: Calculate actual progress based on tasks
                progress = 0.5
            
            instance_responses.append(WorkflowInstanceResponse(
                instance_id=instance.instance_id,
                workflow_id=instance.workflow_id,
                workflow_name=instance.workflow_name,
                workflow_version=instance.workflow_version,
                status=instance.status,
                priority=instance.priority,
                triggered_by=instance.triggered_by,
                trigger_type=instance.trigger_type,
                started_at=instance.started_at,
                completed_at=instance.completed_at,
                current_task=instance.current_task_id,
                progress=progress,
                error_message=instance.error_message
            ))
        
        return WorkflowInstanceListResponse(
            instances=instance_responses,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error("Failed to list workflow instances", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list workflow instances")


@router.get("/instances/{instance_id}", response_model=WorkflowInstance)
async def get_workflow_instance(
    instance_id: str = Path(..., description="Workflow instance ID"),
    db: AsyncSession = Depends(get_db)
) -> WorkflowInstance:
    """
    Get workflow instance details
    
    Returns complete workflow instance information including execution state.
    """
    try:
        result = await db.execute(
            select(WorkflowInstanceDB).where(
                WorkflowInstanceDB.instance_id == instance_id
            )
        )
        instance = result.scalar_one_or_none()
        
        if not instance:
            raise HTTPException(status_code=404, detail="Workflow instance not found")
        
        return WorkflowInstance(
            instance_id=instance.instance_id,
            workflow_id=instance.workflow_id,
            workflow_name=instance.workflow_name,
            workflow_version=instance.workflow_version,
            status=instance.status,
            priority=instance.priority,
            input_data=instance.input_data,
            variables=instance.variables,
            output_data=instance.output_data,
            triggered_by=instance.triggered_by,
            trigger_type=instance.trigger_type,
            trigger_data=instance.trigger_data,
            scheduled_at=instance.scheduled_at,
            started_at=instance.started_at,
            completed_at=instance.completed_at,
            current_task_id=instance.current_task_id,
            execution_path=instance.execution_path,
            retry_count=instance.retry_count,
            error_message=instance.error_message,
            tags=instance.tags,
            metadata=instance.metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get workflow instance", instance_id=instance_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get workflow instance")


@router.post("/instances/{instance_id}/pause", response_model=WorkflowInstanceResponse)
async def pause_workflow_instance(
    instance_id: str = Path(..., description="Workflow instance ID"),
    db: AsyncSession = Depends(get_db)
) -> WorkflowInstanceResponse:
    """
    Pause a running workflow instance
    
    The workflow can be resumed later from where it was paused.
    """
    try:
        engine = WorkflowEngine(db)
        instance = await engine.pause_workflow(instance_id)
        
        return WorkflowInstanceResponse(
            instance_id=instance.instance_id,
            workflow_id=instance.workflow_id,
            workflow_name=instance.workflow_name,
            workflow_version=instance.workflow_version,
            status=instance.status,
            priority=instance.priority,
            triggered_by=instance.triggered_by,
            trigger_type=instance.trigger_type,
            started_at=instance.started_at,
            completed_at=instance.completed_at,
            current_task=instance.current_task_id,
            progress=0.5,  # TODO: Calculate progress
            error_message=instance.error_message
        )
        
    except WorkflowNotFoundError:
        raise HTTPException(status_code=404, detail="Workflow instance not found")
    except WorkflowExecutionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to pause workflow", instance_id=instance_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to pause workflow")


@router.post("/instances/{instance_id}/resume", response_model=WorkflowInstanceResponse)
async def resume_workflow_instance(
    instance_id: str = Path(..., description="Workflow instance ID"),
    db: AsyncSession = Depends(get_db)
) -> WorkflowInstanceResponse:
    """
    Resume a paused workflow instance
    
    Continues execution from where the workflow was paused.
    """
    try:
        engine = WorkflowEngine(db)
        instance = await engine.resume_workflow(instance_id)
        
        return WorkflowInstanceResponse(
            instance_id=instance.instance_id,
            workflow_id=instance.workflow_id,
            workflow_name=instance.workflow_name,
            workflow_version=instance.workflow_version,
            status=instance.status,
            priority=instance.priority,
            triggered_by=instance.triggered_by,
            trigger_type=instance.trigger_type,
            started_at=instance.started_at,
            completed_at=instance.completed_at,
            current_task=instance.current_task_id,
            progress=0.5,  # TODO: Calculate progress
            error_message=instance.error_message
        )
        
    except WorkflowNotFoundError:
        raise HTTPException(status_code=404, detail="Workflow instance not found")
    except WorkflowExecutionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to resume workflow", instance_id=instance_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to resume workflow")


@router.post("/instances/{instance_id}/cancel", response_model=WorkflowInstanceResponse)
async def cancel_workflow_instance(
    instance_id: str = Path(..., description="Workflow instance ID"),
    db: AsyncSession = Depends(get_db)
) -> WorkflowInstanceResponse:
    """
    Cancel a workflow instance
    
    Stops the workflow execution. The workflow cannot be resumed after cancellation.
    """
    try:
        engine = WorkflowEngine(db)
        instance = await engine.cancel_workflow(instance_id)
        
        return WorkflowInstanceResponse(
            instance_id=instance.instance_id,
            workflow_id=instance.workflow_id,
            workflow_name=instance.workflow_name,
            workflow_version=instance.workflow_version,
            status=instance.status,
            priority=instance.priority,
            triggered_by=instance.triggered_by,
            trigger_type=instance.trigger_type,
            started_at=instance.started_at,
            completed_at=instance.completed_at,
            current_task=instance.current_task_id,
            progress=0.0,
            error_message=instance.error_message
        )
        
    except WorkflowNotFoundError:
        raise HTTPException(status_code=404, detail="Workflow instance not found")
    except WorkflowExecutionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to cancel workflow", instance_id=instance_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to cancel workflow")


# Workflow Statistics Endpoint

@router.get("/stats", response_model=WorkflowStats)
async def get_workflow_stats(
    db: AsyncSession = Depends(get_db)
) -> WorkflowStats:
    """
    Get workflow system statistics
    
    Returns comprehensive statistics about workflows and their executions.
    """
    try:
        # Get workflow counts
        total_workflows = (await db.execute(
            select(func.count()).select_from(WorkflowDefinitionDB).where(
                WorkflowDefinitionDB.deleted == False
            )
        )).scalar()
        
        active_workflows = (await db.execute(
            select(func.count()).select_from(WorkflowDefinitionDB).where(
                WorkflowDefinitionDB.enabled == True,
                WorkflowDefinitionDB.deleted == False
            )
        )).scalar()
        
        # Get execution counts
        total_executions = (await db.execute(
            select(func.count()).select_from(WorkflowInstanceDB)
        )).scalar()
        
        running_executions = (await db.execute(
            select(func.count()).select_from(WorkflowInstanceDB).where(
                WorkflowInstanceDB.status == WorkflowStatus.RUNNING
            )
        )).scalar()
        
        completed_executions = (await db.execute(
            select(func.count()).select_from(WorkflowInstanceDB).where(
                WorkflowInstanceDB.status == WorkflowStatus.COMPLETED
            )
        )).scalar()
        
        failed_executions = (await db.execute(
            select(func.count()).select_from(WorkflowInstanceDB).where(
                WorkflowInstanceDB.status == WorkflowStatus.FAILED
            )
        )).scalar()
        
        # Calculate average duration
        avg_duration_result = await db.execute(
            select(func.avg(
                func.extract('epoch', WorkflowInstanceDB.completed_at) -
                func.extract('epoch', WorkflowInstanceDB.started_at)
            )).where(
                WorkflowInstanceDB.status == WorkflowStatus.COMPLETED,
                WorkflowInstanceDB.completed_at.isnot(None),
                WorkflowInstanceDB.started_at.isnot(None)
            )
        )
        avg_duration = avg_duration_result.scalar() or 0
        
        # Calculate success rate
        success_rate = 0.0
        if total_executions > 0:
            success_rate = (completed_executions / total_executions) * 100
        
        # Get executions by status
        status_counts = {}
        for status in WorkflowStatus:
            count = (await db.execute(
                select(func.count()).select_from(WorkflowInstanceDB).where(
                    WorkflowInstanceDB.status == status
                )
            )).scalar()
            status_counts[status] = count
        
        # Get executions by priority
        priority_counts = {}
        for priority in WorkflowPriority:
            count = (await db.execute(
                select(func.count()).select_from(WorkflowInstanceDB).where(
                    WorkflowInstanceDB.priority == priority
                )
            )).scalar()
            priority_counts[priority] = count
        
        # Get executions by trigger type
        trigger_counts = {}
        for trigger in TriggerType:
            count = (await db.execute(
                select(func.count()).select_from(WorkflowInstanceDB).where(
                    WorkflowInstanceDB.trigger_type == trigger
                )
            )).scalar()
            trigger_counts[trigger] = count
        
        # Get time-based stats
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1)
        
        executions_today = (await db.execute(
            select(func.count()).select_from(WorkflowInstanceDB).where(
                WorkflowInstanceDB.created_at >= today_start
            )
        )).scalar()
        
        executions_this_week = (await db.execute(
            select(func.count()).select_from(WorkflowInstanceDB).where(
                WorkflowInstanceDB.created_at >= week_start
            )
        )).scalar()
        
        executions_this_month = (await db.execute(
            select(func.count()).select_from(WorkflowInstanceDB).where(
                WorkflowInstanceDB.created_at >= month_start
            )
        )).scalar()
        
        # Get most used workflows
        most_used_result = await db.execute(
            select(
                WorkflowInstanceDB.workflow_id,
                WorkflowInstanceDB.workflow_name,
                func.count().label('count')
            ).group_by(
                WorkflowInstanceDB.workflow_id,
                WorkflowInstanceDB.workflow_name
            ).order_by(
                func.count().desc()
            ).limit(5)
        )
        most_used_workflows = [
            {
                "workflow_id": row.workflow_id,
                "workflow_name": row.workflow_name,
                "execution_count": row.count
            }
            for row in most_used_result
        ]
        
        # Get most failed workflows
        most_failed_result = await db.execute(
            select(
                WorkflowInstanceDB.workflow_id,
                WorkflowInstanceDB.workflow_name,
                func.count().label('count')
            ).where(
                WorkflowInstanceDB.status == WorkflowStatus.FAILED
            ).group_by(
                WorkflowInstanceDB.workflow_id,
                WorkflowInstanceDB.workflow_name
            ).order_by(
                func.count().desc()
            ).limit(5)
        )
        most_failed_workflows = [
            {
                "workflow_id": row.workflow_id,
                "workflow_name": row.workflow_name,
                "failure_count": row.count
            }
            for row in most_failed_result
        ]
        
        # TODO: Calculate average task duration
        avg_task_duration = 0.0
        
        return WorkflowStats(
            total_workflows=total_workflows,
            active_workflows=active_workflows,
            total_executions=total_executions,
            running_executions=running_executions,
            completed_executions=completed_executions,
            failed_executions=failed_executions,
            average_duration_seconds=avg_duration,
            success_rate=success_rate,
            executions_by_status=status_counts,
            executions_by_priority=priority_counts,
            executions_by_trigger=trigger_counts,
            executions_today=executions_today,
            executions_this_week=executions_this_week,
            executions_this_month=executions_this_month,
            average_task_duration=avg_task_duration,
            most_used_workflows=most_used_workflows,
            most_failed_workflows=most_failed_workflows
        )
        
    except Exception as e:
        logger.error("Failed to get workflow stats", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get workflow statistics")


# Webhook endpoints

@router.post("/webhooks/{webhook_path:path}")
async def handle_webhook(
    webhook_path: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle incoming webhooks
    
    This endpoint receives webhooks and triggers associated workflows.
    """
    try:
        # Get trigger service
        from ..services.trigger_service import TriggerService
        trigger_service = TriggerService(db)
        
        # Get request data
        headers = dict(request.headers)
        body = await request.json() if request.headers.get("content-type") == "application/json" else await request.body()
        
        # Handle webhook
        result = await trigger_service.handle_webhook(
            path=f"/webhooks/{webhook_path}",
            method=request.method,
            headers=headers,
            body=body
        )
        
        return result
        
    except Exception as e:
        logger.error("Failed to handle webhook", webhook_path=webhook_path, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to process webhook")


# API trigger endpoint

@router.post("/trigger/{workflow_id}")
async def trigger_workflow_api(
    workflow_id: str = Path(..., description="Workflow ID"),
    api_key: str = Header(..., description="API key for authentication"),
    input_data: Dict[str, Any] = {},
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger workflow via API
    
    This endpoint allows external systems to trigger workflows using an API key.
    """
    try:
        # Get trigger service
        from ..services.trigger_service import TriggerService
        trigger_service = TriggerService(db)
        
        # Trigger workflow
        instance_id = await trigger_service.trigger_api_workflow(
            workflow_id=workflow_id,
            api_key=api_key,
            input_data=input_data
        )
        
        return {
            "status": "success",
            "instance_id": instance_id
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to trigger workflow", workflow_id=workflow_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to trigger workflow")


# Template Endpoints

@router.get("/templates", response_model=Dict[str, Any])
async def list_templates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    is_public: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    List workflow templates
    
    Query parameters:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20, max: 100)
    - category: Filter by category
    - tag: Filter by tag
    - search: Search in name and description
    - is_public: Filter by public status
    """
    try:
        from ..services.template_service import TemplateService
        service = TemplateService(db)
        
        templates, total = await service.list_templates(
            category=category,
            tag=tag,
            search=search,
            is_public=is_public,
            page=page,
            page_size=page_size
        )
        
        # Convert to response format
        template_list = []
        for template in templates:
            template_list.append({
                "template_id": template.template_id,
                "name": template.name,
                "description": template.description,
                "category": template.category,
                "tags": template.tags,
                "is_public": template.is_public,
                "created_by": template.created_by,
                "usage_count": template.usage_count,
                "created_at": template.created_at,
                "updated_at": template.updated_at
            })
        
        return {
            "templates": template_list,
            "total": total,
            "page": page,
            "page_size": page_size
        }
        
    except Exception as e:
        logger.error("Failed to list templates", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list templates")


@router.get("/templates/{template_id}", response_model=Dict[str, Any])
async def get_template(
    template_id: str = Path(..., description="Template ID"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get workflow template by ID
    """
    try:
        from ..services.template_service import TemplateService
        service = TemplateService(db)
        
        template = await service.get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return {
            "template_id": template.template_id,
            "name": template.name,
            "description": template.description,
            "category": template.category,
            "definition": template.definition,
            "tags": template.tags,
            "is_public": template.is_public,
            "created_by": template.created_by,
            "usage_count": template.usage_count,
            "created_at": template.created_at,
            "updated_at": template.updated_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get template", template_id=template_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get template")


@router.post("/templates", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_template(
    request: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Create a custom workflow template
    """
    try:
        from ..services.template_service import TemplateService
        service = TemplateService(db)
        
        template = await service.create_template(
            name=request["name"],
            description=request["description"],
            category=request["category"],
            definition=request["definition"],
            tags=request.get("tags", []),
            is_public=request.get("is_public", False),
            created_by=request.get("created_by", "user")
        )
        
        return {
            "template_id": template.template_id,
            "name": template.name,
            "description": template.description,
            "category": template.category,
            "tags": template.tags,
            "is_public": template.is_public,
            "created_by": template.created_by,
            "created_at": template.created_at
        }
        
    except Exception as e:
        logger.error("Failed to create template", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create template")


@router.post("/templates/{template_id}/instantiate", response_model=Dict[str, Any])
async def instantiate_template(
    template_id: str = Path(..., description="Template ID"),
    request: Dict[str, Any] = {},
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Create a workflow from a template
    
    Request body:
    - name: Workflow name (required)
    - description: Optional workflow description
    - variables: Optional variable overrides
    - enabled: Whether to enable the workflow (default: true)
    """
    try:
        from ..services.template_service import TemplateService
        service = TemplateService(db)
        
        workflow_id = await service.instantiate_template(
            template_id=template_id,
            name=request["name"],
            description=request.get("description"),
            variables=request.get("variables"),
            enabled=request.get("enabled", True),
            created_by=request.get("created_by", "user")
        )
        
        return {
            "workflow_id": workflow_id,
            "template_id": template_id,
            "message": "Workflow created successfully from template"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to instantiate template", template_id=template_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to instantiate template")


@router.get("/templates/stats", response_model=Dict[str, Any])
async def get_template_stats(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get template usage statistics
    """
    try:
        from ..services.template_service import TemplateService
        service = TemplateService(db)
        
        stats = await service.get_template_stats()
        return stats
        
    except Exception as e:
        logger.error("Failed to get template stats", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get template statistics")


# Monitoring Endpoints

@router.get("/monitoring/dashboard", response_model=Dict[str, Any])
async def get_monitoring_dashboard(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get monitoring dashboard metrics
    
    Returns comprehensive metrics for dashboard display including:
    - Summary statistics
    - Workflow metrics
    - Task metrics
    - Performance metrics
    - Recent events
    - Trending workflows
    """
    try:
        from ..services.monitoring_service import MonitoringService
        service = MonitoringService(db)
        
        metrics = await service.get_dashboard_metrics()
        return metrics
        
    except Exception as e:
        logger.error("Failed to get dashboard metrics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get dashboard metrics")


@router.get("/monitoring/workflows/{workflow_id}", response_model=Dict[str, Any])
async def get_workflow_metrics(
    workflow_id: str = Path(..., description="Workflow ID"),
    start_date: Optional[datetime] = Query(None, description="Start date for metrics"),
    end_date: Optional[datetime] = Query(None, description="End date for metrics"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get metrics for a specific workflow
    
    Query parameters:
    - start_date: Start date for metrics (default: 7 days ago)
    - end_date: End date for metrics (default: now)
    """
    try:
        from ..services.monitoring_service import MonitoringService
        service = MonitoringService(db)
        
        metrics = await service.get_workflow_metrics(
            workflow_id=workflow_id,
            start_date=start_date,
            end_date=end_date
        )
        return metrics
        
    except Exception as e:
        logger.error("Failed to get workflow metrics", workflow_id=workflow_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get workflow metrics")


@router.get("/monitoring/health", response_model=Dict[str, Any])
async def get_system_health(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get system health status
    
    Returns health status of various system components.
    """
    try:
        from ..services.monitoring_service import MonitoringService
        service = MonitoringService(db)
        
        health = await service.check_health()
        return health
        
    except Exception as e:
        logger.error("Failed to check system health", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to check system health")


# Health check
@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "workflow-engine"}