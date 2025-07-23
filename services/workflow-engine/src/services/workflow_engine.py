"""
Core Workflow Execution Engine

This module implements the core workflow execution logic, including:
- Workflow instance creation and management
- Task execution and orchestration
- State management and persistence
- Error handling and retry logic
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import structlog
import aioredis

from ..models.schemas import (
    WorkflowDefinition, WorkflowInstance, TaskInstance,
    WorkflowStatus, TaskStatus, TaskType, TaskConfig,
    ConditionalTask, ParallelTask, LoopTask,
    ConditionOperator, WorkflowPriority
)
from ..db.models import (
    WorkflowDefinition as WorkflowDefinitionDB,
    WorkflowInstance as WorkflowInstanceDB,
    TaskInstance as TaskInstanceDB,
    WorkflowEvent as WorkflowEventDB
)
from ..core.config import settings
from .task_executor import TaskExecutor
from .state_manager import WorkflowStateManager
from ..core.exceptions import (
    WorkflowNotFoundError, WorkflowExecutionError,
    TaskExecutionError, WorkflowTimeoutError
)

logger = structlog.get_logger()


class WorkflowEngine:
    """
    Core workflow execution engine
    """
    
    def __init__(self, db_session: AsyncSession, redis_client: aioredis.Redis = None):
        self.db = db_session
        self.redis = redis_client
        self.task_executor = TaskExecutor(db_session, redis_client)
        self.state_manager = WorkflowStateManager(db_session, redis_client)
        self.running_workflows: Dict[str, asyncio.Task] = {}
        
    async def create_workflow_instance(
        self,
        workflow_id: str,
        input_data: Dict[str, Any],
        triggered_by: str,
        trigger_type: str,
        trigger_data: Dict[str, Any] = None,
        priority: WorkflowPriority = None,
        scheduled_at: datetime = None,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> WorkflowInstance:
        """
        Create a new workflow instance
        """
        # Load workflow definition
        workflow_def = await self._load_workflow_definition(workflow_id)
        if not workflow_def:
            raise WorkflowNotFoundError(f"Workflow {workflow_id} not found")
        
        if not workflow_def.enabled:
            raise WorkflowExecutionError(f"Workflow {workflow_id} is disabled")
        
        # Create instance
        instance = WorkflowInstance(
            workflow_id=workflow_id,
            workflow_name=workflow_def.name,
            workflow_version=workflow_def.version,
            status=WorkflowStatus.PENDING if not scheduled_at else WorkflowStatus.SCHEDULED,
            priority=priority or workflow_def.priority,
            input_data=input_data,
            variables={**workflow_def.variables, **input_data},
            triggered_by=triggered_by,
            trigger_type=trigger_type,
            trigger_data=trigger_data or {},
            scheduled_at=scheduled_at,
            tags=tags or [],
            metadata=metadata or {}
        )
        
        # Save to database
        db_instance = WorkflowInstanceDB(
            instance_id=instance.instance_id,
            workflow_id=instance.workflow_id,
            workflow_definition_id=workflow_def.id,
            workflow_name=instance.workflow_name,
            workflow_version=instance.workflow_version,
            status=instance.status,
            priority=instance.priority,
            input_data=instance.input_data,
            variables=instance.variables,
            triggered_by=instance.triggered_by,
            trigger_type=instance.trigger_type,
            trigger_data=instance.trigger_data,
            scheduled_at=instance.scheduled_at,
            tags=instance.tags,
            metadata=instance.metadata
        )
        
        self.db.add(db_instance)
        await self.db.commit()
        
        # Log event
        await self._log_workflow_event(
            instance.instance_id,
            "created",
            {"triggered_by": triggered_by, "input_data": input_data}
        )
        
        logger.info(
            "Workflow instance created",
            instance_id=instance.instance_id,
            workflow_id=workflow_id,
            status=instance.status.value
        )
        
        return instance
    
    async def execute_workflow(
        self,
        instance_id: str,
        background: bool = True
    ) -> Optional[WorkflowInstance]:
        """
        Execute a workflow instance
        """
        # Load instance
        instance = await self._load_workflow_instance(instance_id)
        if not instance:
            raise WorkflowNotFoundError(f"Workflow instance {instance_id} not found")
        
        # Check if already running
        if instance.status == WorkflowStatus.RUNNING:
            logger.warning("Workflow already running", instance_id=instance_id)
            return instance
        
        # Check if can be executed
        if instance.status not in [WorkflowStatus.PENDING, WorkflowStatus.SCHEDULED, WorkflowStatus.FAILED]:
            raise WorkflowExecutionError(
                f"Cannot execute workflow in status {instance.status}"
            )
        
        # Update status
        instance.status = WorkflowStatus.RUNNING
        instance.started_at = datetime.utcnow()
        await self._update_workflow_instance(instance)
        
        # Log event
        await self._log_workflow_event(instance_id, "started", {})
        
        if background:
            # Execute in background
            task = asyncio.create_task(self._execute_workflow_async(instance))
            self.running_workflows[instance_id] = task
            return instance
        else:
            # Execute synchronously
            return await self._execute_workflow_async(instance)
    
    async def _execute_workflow_async(self, instance: WorkflowInstance) -> WorkflowInstance:
        """
        Execute workflow asynchronously
        """
        try:
            # Load workflow definition
            workflow_def = await self._load_workflow_definition(instance.workflow_id)
            
            # Set up timeout
            timeout = workflow_def.timeout or settings.DEFAULT_WORKFLOW_TIMEOUT
            
            # Execute with timeout
            try:
                await asyncio.wait_for(
                    self._execute_workflow_tasks(instance, workflow_def),
                    timeout=timeout
                )
                
                # Mark as completed
                instance.status = WorkflowStatus.COMPLETED
                instance.completed_at = datetime.utcnow()
                
                logger.info(
                    "Workflow completed successfully",
                    instance_id=instance.instance_id
                )
                
            except asyncio.TimeoutError:
                raise WorkflowTimeoutError(
                    f"Workflow timed out after {timeout} seconds"
                )
            
        except Exception as e:
            # Handle failure
            instance.status = WorkflowStatus.FAILED
            instance.error_message = str(e)
            
            logger.error(
                "Workflow execution failed",
                instance_id=instance.instance_id,
                error=str(e)
            )
            
            # Check retry
            if instance.retry_count < workflow_def.max_retries:
                instance.retry_count += 1
                instance.status = WorkflowStatus.PENDING
                
                # Schedule retry
                retry_delay = workflow_def.retry_delay * instance.retry_count
                instance.scheduled_at = datetime.utcnow() + timedelta(seconds=retry_delay)
                
                logger.info(
                    "Scheduling workflow retry",
                    instance_id=instance.instance_id,
                    retry_count=instance.retry_count,
                    retry_at=instance.scheduled_at
                )
        
        finally:
            # Update instance
            await self._update_workflow_instance(instance)
            
            # Log event
            event_type = "completed" if instance.status == WorkflowStatus.COMPLETED else "failed"
            await self._log_workflow_event(
                instance.instance_id,
                event_type,
                {"status": instance.status.value, "error": instance.error_message}
            )
            
            # Remove from running workflows
            self.running_workflows.pop(instance.instance_id, None)
        
        return instance
    
    async def _execute_workflow_tasks(
        self,
        instance: WorkflowInstance,
        workflow_def: WorkflowDefinition
    ):
        """
        Execute workflow tasks in order
        """
        # Initialize task context
        context = {
            "workflow": {
                "id": instance.workflow_id,
                "instance_id": instance.instance_id,
                "name": instance.workflow_name,
                "version": instance.workflow_version
            },
            "variables": instance.variables,
            "input": instance.input_data,
            "output": {}
        }
        
        # Execute tasks
        for task_config in workflow_def.tasks:
            # Check if workflow is still running
            if instance.status != WorkflowStatus.RUNNING:
                logger.info(
                    "Workflow stopped",
                    instance_id=instance.instance_id,
                    status=instance.status.value
                )
                break
            
            # Update current task
            instance.current_task_id = task_config.task_id
            await self._update_workflow_instance(instance)
            
            # Execute task
            task_result = await self._execute_task(
                instance,
                task_config,
                context
            )
            
            # Update context with task output
            context["output"][task_config.task_id] = task_result
            context["last_output"] = task_result
            
            # Add to execution path
            instance.execution_path.append(task_config.task_id)
        
        # Update final output
        instance.output_data = context["output"]
        instance.variables = context["variables"]
    
    async def _execute_task(
        self,
        workflow_instance: WorkflowInstance,
        task_config: TaskConfig,
        context: Dict[str, Any]
    ) -> Any:
        """
        Execute a single task
        """
        # Create task instance
        task_instance = await self._create_task_instance(
            workflow_instance,
            task_config,
            context
        )
        
        try:
            # Log task start
            await self._log_workflow_event(
                workflow_instance.instance_id,
                "task_started",
                {"task_id": task_config.task_id, "task_type": task_config.task_type}
            )
            
            # Handle different task types
            if isinstance(task_config, ConditionalTask):
                result = await self._execute_conditional_task(
                    workflow_instance,
                    task_config,
                    context
                )
            elif isinstance(task_config, ParallelTask):
                result = await self._execute_parallel_task(
                    workflow_instance,
                    task_config,
                    context
                )
            elif isinstance(task_config, LoopTask):
                result = await self._execute_loop_task(
                    workflow_instance,
                    task_config,
                    context
                )
            else:
                # Execute regular task
                result = await self.task_executor.execute_task(
                    task_instance,
                    task_config,
                    context
                )
            
            # Update task instance
            task_instance.status = TaskStatus.COMPLETED
            task_instance.output_data = result if isinstance(result, dict) else {"result": result}
            task_instance.completed_at = datetime.utcnow()
            task_instance.duration_seconds = (
                task_instance.completed_at - task_instance.started_at
            ).total_seconds()
            
            # Log task completion
            await self._log_workflow_event(
                workflow_instance.instance_id,
                "task_completed",
                {
                    "task_id": task_config.task_id,
                    "duration": task_instance.duration_seconds
                }
            )
            
            return result
            
        except Exception as e:
            # Handle task failure
            task_instance.status = TaskStatus.FAILED
            task_instance.error_message = str(e)
            
            # Log task failure
            await self._log_workflow_event(
                workflow_instance.instance_id,
                "task_failed",
                {
                    "task_id": task_config.task_id,
                    "error": str(e)
                }
            )
            
            # Check if should continue on error
            if not task_config.continue_on_error:
                raise TaskExecutionError(
                    f"Task {task_config.task_id} failed: {str(e)}"
                )
            
            return None
            
        finally:
            # Save task instance
            await self._update_task_instance(task_instance)
    
    async def _execute_conditional_task(
        self,
        workflow_instance: WorkflowInstance,
        task_config: ConditionalTask,
        context: Dict[str, Any]
    ) -> Any:
        """
        Execute conditional task
        """
        # Evaluate conditions
        condition_met = await self._evaluate_conditions(
            task_config.conditions,
            context
        )
        
        # Execute appropriate branch
        if condition_met:
            tasks = task_config.then_tasks
        else:
            tasks = task_config.else_tasks
        
        # Execute tasks in branch
        results = []
        for task in tasks:
            result = await self._execute_task(
                workflow_instance,
                task,
                context
            )
            results.append(result)
        
        return results
    
    async def _execute_parallel_task(
        self,
        workflow_instance: WorkflowInstance,
        task_config: ParallelTask,
        context: Dict[str, Any]
    ) -> List[Any]:
        """
        Execute parallel tasks
        """
        # Create tasks
        tasks = []
        for task in task_config.tasks:
            task_coro = self._execute_task(
                workflow_instance,
                task,
                context.copy()  # Each parallel task gets its own context
            )
            tasks.append(task_coro)
        
        # Execute in parallel with concurrency limit
        if task_config.max_concurrent:
            results = []
            for i in range(0, len(tasks), task_config.max_concurrent):
                batch = tasks[i:i + task_config.max_concurrent]
                batch_results = await asyncio.gather(*batch, return_exceptions=True)
                results.extend(batch_results)
        else:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions if wait_for_all is True
        if task_config.wait_for_all:
            exceptions = [r for r in results if isinstance(r, Exception)]
            if exceptions:
                raise TaskExecutionError(
                    f"Parallel task failed with {len(exceptions)} errors"
                )
        
        return results
    
    async def _execute_loop_task(
        self,
        workflow_instance: WorkflowInstance,
        task_config: LoopTask,
        context: Dict[str, Any]
    ) -> List[Any]:
        """
        Execute loop task
        """
        # Get items to iterate over
        items = self._resolve_variable(task_config.items_source, context)
        if not isinstance(items, list):
            items = [items]
        
        # Apply max iterations limit
        if task_config.max_iterations:
            items = items[:task_config.max_iterations]
        
        results = []
        
        if task_config.parallel_execution:
            # Execute iterations in parallel
            tasks = []
            for item in items:
                loop_context = context.copy()
                loop_context["variables"][task_config.item_variable] = item
                
                for task in task_config.tasks:
                    task_coro = self._execute_task(
                        workflow_instance,
                        task,
                        loop_context
                    )
                    tasks.append(task_coro)
            
            results = await asyncio.gather(*tasks)
        else:
            # Execute iterations sequentially
            for item in items:
                # Update loop variable
                context["variables"][task_config.item_variable] = item
                
                # Execute tasks in loop
                iteration_results = []
                for task in task_config.tasks:
                    result = await self._execute_task(
                        workflow_instance,
                        task,
                        context
                    )
                    iteration_results.append(result)
                
                results.append(iteration_results)
        
        return results
    
    async def _evaluate_conditions(
        self,
        conditions: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> bool:
        """
        Evaluate conditions
        """
        results = []
        logical_operator = "and"
        
        for condition in conditions:
            # Get field value
            field_value = self._resolve_variable(condition.field, context)
            condition_value = condition.value
            operator = condition.operator
            
            # Evaluate condition
            result = self._evaluate_condition(
                field_value,
                operator,
                condition_value
            )
            results.append(result)
            
            # Update logical operator
            if "logical_operator" in condition:
                logical_operator = condition.logical_operator
        
        # Apply logical operator
        if logical_operator == "and":
            return all(results)
        else:
            return any(results)
    
    def _evaluate_condition(
        self,
        field_value: Any,
        operator: ConditionOperator,
        condition_value: Any
    ) -> bool:
        """
        Evaluate a single condition
        """
        if operator == ConditionOperator.EQUALS:
            return field_value == condition_value
        elif operator == ConditionOperator.NOT_EQUALS:
            return field_value != condition_value
        elif operator == ConditionOperator.GREATER_THAN:
            return field_value > condition_value
        elif operator == ConditionOperator.LESS_THAN:
            return field_value < condition_value
        elif operator == ConditionOperator.GREATER_OR_EQUAL:
            return field_value >= condition_value
        elif operator == ConditionOperator.LESS_OR_EQUAL:
            return field_value <= condition_value
        elif operator == ConditionOperator.CONTAINS:
            return condition_value in str(field_value)
        elif operator == ConditionOperator.NOT_CONTAINS:
            return condition_value not in str(field_value)
        elif operator == ConditionOperator.STARTS_WITH:
            return str(field_value).startswith(condition_value)
        elif operator == ConditionOperator.ENDS_WITH:
            return str(field_value).endswith(condition_value)
        elif operator == ConditionOperator.IN:
            return field_value in condition_value
        elif operator == ConditionOperator.NOT_IN:
            return field_value not in condition_value
        elif operator == ConditionOperator.EXISTS:
            return field_value is not None
        elif operator == ConditionOperator.NOT_EXISTS:
            return field_value is None
        elif operator == ConditionOperator.IS_EMPTY:
            return not field_value
        elif operator == ConditionOperator.IS_NOT_EMPTY:
            return bool(field_value)
        else:
            return False
    
    def _resolve_variable(self, path: str, context: Dict[str, Any]) -> Any:
        """
        Resolve variable from context using dot notation
        """
        if not path:
            return None
        
        # Handle special variables
        if path.startswith("$"):
            if path == "$now":
                return datetime.utcnow()
            elif path == "$today":
                return datetime.utcnow().date()
            elif path == "$workflow_id":
                return context["workflow"]["id"]
            elif path == "$instance_id":
                return context["workflow"]["instance_id"]
        
        # Navigate through context
        parts = path.split(".")
        current = context
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        
        return current
    
    async def _create_task_instance(
        self,
        workflow_instance: WorkflowInstance,
        task_config: TaskConfig,
        context: Dict[str, Any]
    ) -> TaskInstance:
        """
        Create task instance
        """
        # Resolve parameters
        resolved_params = {}
        for key, value in task_config.parameters.items():
            if isinstance(value, str) and value.startswith("$"):
                resolved_params[key] = self._resolve_variable(value, context)
            else:
                resolved_params[key] = value
        
        task_instance = TaskInstance(
            workflow_instance_id=workflow_instance.instance_id,
            task_id=task_config.task_id,
            task_type=task_config.task_type,
            task_name=task_config.name,
            status=TaskStatus.PENDING,
            input_data=resolved_params,
            started_at=datetime.utcnow()
        )
        
        # Save to database
        db_task = TaskInstanceDB(
            task_instance_id=task_instance.task_instance_id,
            workflow_instance_id=workflow_instance.instance_id,
            task_id=task_instance.task_id,
            task_type=task_instance.task_type,
            task_name=task_instance.task_name,
            status=task_instance.status,
            input_data=task_instance.input_data,
            started_at=task_instance.started_at
        )
        
        self.db.add(db_task)
        await self.db.commit()
        
        return task_instance
    
    async def _load_workflow_definition(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """
        Load workflow definition from database
        """
        result = await self.db.execute(
            select(WorkflowDefinitionDB).where(
                WorkflowDefinitionDB.workflow_id == workflow_id,
                WorkflowDefinitionDB.enabled == True,
                WorkflowDefinitionDB.deleted == False
            )
        )
        db_workflow = result.scalar_one_or_none()
        
        if not db_workflow:
            return None
        
        return WorkflowDefinition(
            workflow_id=db_workflow.workflow_id,
            name=db_workflow.name,
            description=db_workflow.description,
            version=db_workflow.version,
            enabled=db_workflow.enabled,
            priority=db_workflow.priority,
            triggers=db_workflow.triggers,
            variables=db_workflow.variables,
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
    
    async def _load_workflow_instance(self, instance_id: str) -> Optional[WorkflowInstance]:
        """
        Load workflow instance from database
        """
        result = await self.db.execute(
            select(WorkflowInstanceDB).where(
                WorkflowInstanceDB.instance_id == instance_id
            )
        )
        db_instance = result.scalar_one_or_none()
        
        if not db_instance:
            return None
        
        return WorkflowInstance(
            instance_id=db_instance.instance_id,
            workflow_id=db_instance.workflow_id,
            workflow_name=db_instance.workflow_name,
            workflow_version=db_instance.workflow_version,
            status=db_instance.status,
            priority=db_instance.priority,
            input_data=db_instance.input_data,
            variables=db_instance.variables,
            output_data=db_instance.output_data,
            triggered_by=db_instance.triggered_by,
            trigger_type=db_instance.trigger_type,
            trigger_data=db_instance.trigger_data,
            scheduled_at=db_instance.scheduled_at,
            started_at=db_instance.started_at,
            completed_at=db_instance.completed_at,
            current_task_id=db_instance.current_task_id,
            execution_path=db_instance.execution_path,
            retry_count=db_instance.retry_count,
            error_message=db_instance.error_message,
            tags=db_instance.tags,
            metadata=db_instance.metadata
        )
    
    async def _update_workflow_instance(self, instance: WorkflowInstance):
        """
        Update workflow instance in database
        """
        await self.db.execute(
            update(WorkflowInstanceDB)
            .where(WorkflowInstanceDB.instance_id == instance.instance_id)
            .values(
                status=instance.status,
                variables=instance.variables,
                output_data=instance.output_data,
                started_at=instance.started_at,
                completed_at=instance.completed_at,
                current_task_id=instance.current_task_id,
                execution_path=instance.execution_path,
                retry_count=instance.retry_count,
                error_message=instance.error_message,
                updated_at=datetime.utcnow()
            )
        )
        await self.db.commit()
    
    async def _update_task_instance(self, task_instance: TaskInstance):
        """
        Update task instance in database
        """
        await self.db.execute(
            update(TaskInstanceDB)
            .where(TaskInstanceDB.task_instance_id == task_instance.task_instance_id)
            .values(
                status=task_instance.status,
                output_data=task_instance.output_data,
                error_message=task_instance.error_message,
                completed_at=task_instance.completed_at,
                duration_seconds=task_instance.duration_seconds,
                retry_count=task_instance.retry_count,
                last_retry_at=task_instance.last_retry_at,
                resource_usage=task_instance.resource_usage,
                updated_at=datetime.utcnow()
            )
        )
        await self.db.commit()
    
    async def _log_workflow_event(
        self,
        instance_id: str,
        event_type: str,
        event_data: Dict[str, Any]
    ):
        """
        Log workflow event
        """
        event = WorkflowEventDB(
            workflow_instance_id=instance_id,
            event_type=event_type,
            event_data=event_data
        )
        self.db.add(event)
        await self.db.commit()
    
    async def pause_workflow(self, instance_id: str) -> WorkflowInstance:
        """
        Pause a running workflow
        """
        instance = await self._load_workflow_instance(instance_id)
        if not instance:
            raise WorkflowNotFoundError(f"Workflow instance {instance_id} not found")
        
        if instance.status != WorkflowStatus.RUNNING:
            raise WorkflowExecutionError(
                f"Cannot pause workflow in status {instance.status}"
            )
        
        instance.status = WorkflowStatus.PAUSED
        await self._update_workflow_instance(instance)
        
        await self._log_workflow_event(instance_id, "paused", {})
        
        return instance
    
    async def resume_workflow(self, instance_id: str) -> WorkflowInstance:
        """
        Resume a paused workflow
        """
        instance = await self._load_workflow_instance(instance_id)
        if not instance:
            raise WorkflowNotFoundError(f"Workflow instance {instance_id} not found")
        
        if instance.status != WorkflowStatus.PAUSED:
            raise WorkflowExecutionError(
                f"Cannot resume workflow in status {instance.status}"
            )
        
        instance.status = WorkflowStatus.RUNNING
        await self._update_workflow_instance(instance)
        
        await self._log_workflow_event(instance_id, "resumed", {})
        
        # Continue execution
        return await self.execute_workflow(instance_id)
    
    async def cancel_workflow(self, instance_id: str) -> WorkflowInstance:
        """
        Cancel a workflow
        """
        instance = await self._load_workflow_instance(instance_id)
        if not instance:
            raise WorkflowNotFoundError(f"Workflow instance {instance_id} not found")
        
        if instance.status in [WorkflowStatus.COMPLETED, WorkflowStatus.CANCELLED]:
            raise WorkflowExecutionError(
                f"Cannot cancel workflow in status {instance.status}"
            )
        
        instance.status = WorkflowStatus.CANCELLED
        instance.completed_at = datetime.utcnow()
        await self._update_workflow_instance(instance)
        
        await self._log_workflow_event(instance_id, "cancelled", {})
        
        # Cancel running task if any
        if instance_id in self.running_workflows:
            self.running_workflows[instance_id].cancel()
        
        return instance