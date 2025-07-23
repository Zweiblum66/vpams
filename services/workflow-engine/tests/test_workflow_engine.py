"""
Comprehensive tests for the Workflow Execution Engine
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
import aioredis

from src.services.workflow_engine import WorkflowEngine
from src.services.task_executor import TaskExecutor
from src.services.state_manager import WorkflowStateManager
from src.models.schemas import (
    WorkflowDefinition, WorkflowInstance, TaskInstance,
    WorkflowStatus, TaskStatus, TaskType, TaskConfig,
    ConditionalTask, ParallelTask, LoopTask,
    ConditionOperator, WorkflowPriority, TriggerType,
    ConditionConfig
)
from src.db.models import (
    WorkflowDefinition as WorkflowDefinitionDB,
    WorkflowInstance as WorkflowInstanceDB,
    WorkflowEvent as WorkflowEventDB
)
from src.core.exceptions import (
    WorkflowNotFoundError, WorkflowExecutionError,
    TaskExecutionError, WorkflowTimeoutError
)


class TestWorkflowEngine:
    """Test core workflow engine functionality"""
    
    @pytest.fixture
    async def workflow_engine(self, test_db: AsyncSession):
        """Create workflow engine instance"""
        redis_client = Mock(spec=aioredis.Redis)
        engine = WorkflowEngine(test_db, redis_client)
        return engine
    
    @pytest.fixture
    async def sample_workflow_definition(self, test_db: AsyncSession):
        """Create a sample workflow definition"""
        workflow = WorkflowDefinitionDB(
            workflow_id="test-workflow",
            name="Test Workflow",
            description="Test workflow for unit tests",
            version="1.0.0",
            enabled=True,
            priority="normal",
            triggers=[],
            variables={"default_var": "default_value"},
            tasks=[
                {
                    "task_id": "task-1",
                    "task_type": "wait",
                    "name": "Wait Task",
                    "parameters": {"seconds": 1}
                },
                {
                    "task_id": "task-2",
                    "task_type": "copy_file",
                    "name": "Copy File",
                    "parameters": {
                        "source": "$variables.source_path",
                        "destination": "$variables.dest_path"
                    }
                }
            ],
            timeout=3600,
            max_retries=3,
            retry_delay=60,
            tags=["test"],
            category="test",
            created_by="test-user"
        )
        test_db.add(workflow)
        await test_db.commit()
        return workflow
    
    @pytest.mark.asyncio
    async def test_create_workflow_instance(self, workflow_engine, sample_workflow_definition):
        """Test creating a workflow instance"""
        input_data = {
            "source_path": "/test/source",
            "dest_path": "/test/dest"
        }
        
        instance = await workflow_engine.create_workflow_instance(
            workflow_id=sample_workflow_definition.workflow_id,
            input_data=input_data,
            triggered_by="test-user",
            trigger_type=TriggerType.MANUAL,
            priority=WorkflowPriority.HIGH,
            tags=["test-execution"],
            metadata={"test": "metadata"}
        )
        
        assert instance.workflow_id == sample_workflow_definition.workflow_id
        assert instance.workflow_name == sample_workflow_definition.name
        assert instance.status == WorkflowStatus.PENDING
        assert instance.priority == WorkflowPriority.HIGH
        assert instance.input_data == input_data
        assert instance.variables["default_var"] == "default_value"
        assert instance.variables["source_path"] == input_data["source_path"]
        assert instance.triggered_by == "test-user"
        assert instance.trigger_type == TriggerType.MANUAL
        assert instance.tags == ["test-execution"]
        assert instance.metadata == {"test": "metadata"}
    
    @pytest.mark.asyncio
    async def test_create_scheduled_workflow_instance(self, workflow_engine, sample_workflow_definition):
        """Test creating a scheduled workflow instance"""
        scheduled_time = datetime.utcnow() + timedelta(hours=1)
        
        instance = await workflow_engine.create_workflow_instance(
            workflow_id=sample_workflow_definition.workflow_id,
            input_data={},
            triggered_by="test-user",
            trigger_type=TriggerType.SCHEDULE,
            scheduled_at=scheduled_time
        )
        
        assert instance.status == WorkflowStatus.SCHEDULED
        assert instance.scheduled_at == scheduled_time
    
    @pytest.mark.asyncio
    async def test_create_workflow_instance_not_found(self, workflow_engine):
        """Test creating instance for non-existent workflow"""
        with pytest.raises(WorkflowNotFoundError):
            await workflow_engine.create_workflow_instance(
                workflow_id="non-existent",
                input_data={},
                triggered_by="test-user",
                trigger_type=TriggerType.MANUAL
            )
    
    @pytest.mark.asyncio
    async def test_create_workflow_instance_disabled(self, workflow_engine, sample_workflow_definition, test_db):
        """Test creating instance for disabled workflow"""
        sample_workflow_definition.enabled = False
        await test_db.commit()
        
        with pytest.raises(WorkflowExecutionError):
            await workflow_engine.create_workflow_instance(
                workflow_id=sample_workflow_definition.workflow_id,
                input_data={},
                triggered_by="test-user",
                trigger_type=TriggerType.MANUAL
            )
    
    @pytest.mark.asyncio
    async def test_execute_workflow_simple(self, workflow_engine, sample_workflow_definition):
        """Test executing a simple workflow"""
        # Create instance
        instance = await workflow_engine.create_workflow_instance(
            workflow_id=sample_workflow_definition.workflow_id,
            input_data={"source_path": "/test/source", "dest_path": "/test/dest"},
            triggered_by="test-user",
            trigger_type=TriggerType.MANUAL
        )
        
        # Mock task executor
        with patch.object(workflow_engine.task_executor, 'execute_task', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {"result": "success"}
            
            # Execute workflow synchronously
            result = await workflow_engine.execute_workflow(instance.instance_id, background=False)
            
            assert result.status == WorkflowStatus.COMPLETED
            assert result.started_at is not None
            assert result.completed_at is not None
            assert len(result.execution_path) == 2
            assert mock_execute.call_count == 2
    
    @pytest.mark.asyncio
    async def test_execute_workflow_background(self, workflow_engine, sample_workflow_definition):
        """Test executing a workflow in background"""
        # Create instance
        instance = await workflow_engine.create_workflow_instance(
            workflow_id=sample_workflow_definition.workflow_id,
            input_data={},
            triggered_by="test-user",
            trigger_type=TriggerType.MANUAL
        )
        
        # Execute workflow in background
        result = await workflow_engine.execute_workflow(instance.instance_id, background=True)
        
        assert result.status == WorkflowStatus.RUNNING
        assert instance.instance_id in workflow_engine.running_workflows
        
        # Clean up background task
        workflow_engine.running_workflows[instance.instance_id].cancel()
    
    @pytest.mark.asyncio
    async def test_execute_workflow_already_running(self, workflow_engine, test_db):
        """Test executing an already running workflow"""
        # Create running instance
        instance = WorkflowInstanceDB(
            instance_id="running-instance",
            workflow_id="test-workflow",
            workflow_definition_id=1,
            workflow_name="Test Workflow",
            workflow_version="1.0.0",
            status=WorkflowStatus.RUNNING,
            priority="normal",
            input_data={},
            variables={},
            triggered_by="test-user",
            trigger_type=TriggerType.MANUAL,
            trigger_data={},
            tags=[],
            metadata={}
        )
        test_db.add(instance)
        await test_db.commit()
        
        # Try to execute again
        result = await workflow_engine.execute_workflow(instance.instance_id)
        assert result.status == WorkflowStatus.RUNNING
    
    @pytest.mark.asyncio
    async def test_execute_workflow_invalid_status(self, workflow_engine, test_db):
        """Test executing workflow with invalid status"""
        # Create completed instance
        instance = WorkflowInstanceDB(
            instance_id="completed-instance",
            workflow_id="test-workflow",
            workflow_definition_id=1,
            workflow_name="Test Workflow",
            workflow_version="1.0.0",
            status=WorkflowStatus.COMPLETED,
            priority="normal",
            input_data={},
            variables={},
            triggered_by="test-user",
            trigger_type=TriggerType.MANUAL,
            trigger_data={},
            tags=[],
            metadata={}
        )
        test_db.add(instance)
        await test_db.commit()
        
        with pytest.raises(WorkflowExecutionError):
            await workflow_engine.execute_workflow(instance.instance_id)
    
    @pytest.mark.asyncio
    async def test_execute_workflow_with_failure(self, workflow_engine, sample_workflow_definition):
        """Test workflow execution with task failure"""
        # Create instance
        instance = await workflow_engine.create_workflow_instance(
            workflow_id=sample_workflow_definition.workflow_id,
            input_data={},
            triggered_by="test-user",
            trigger_type=TriggerType.MANUAL
        )
        
        # Mock task executor to fail
        with patch.object(workflow_engine.task_executor, 'execute_task', new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = TaskExecutionError("Task failed")
            
            # Execute workflow
            result = await workflow_engine.execute_workflow(instance.instance_id, background=False)
            
            assert result.status == WorkflowStatus.FAILED
            assert result.error_message == "Task failed"
            assert result.retry_count == 1  # Should attempt retry
    
    @pytest.mark.asyncio
    async def test_execute_workflow_timeout(self, workflow_engine, test_db):
        """Test workflow execution timeout"""
        # Create workflow with short timeout
        workflow = WorkflowDefinitionDB(
            workflow_id="timeout-workflow",
            name="Timeout Test",
            description="Test timeout",
            version="1.0.0",
            enabled=True,
            priority="normal",
            triggers=[],
            variables={},
            tasks=[{
                "task_id": "slow-task",
                "task_type": "wait",
                "name": "Slow Task",
                "parameters": {"seconds": 10}
            }],
            timeout=1,  # 1 second timeout
            max_retries=0,
            retry_delay=60,
            tags=[],
            category="test",
            created_by="test-user"
        )
        test_db.add(workflow)
        await test_db.commit()
        
        # Create instance
        instance = await workflow_engine.create_workflow_instance(
            workflow_id=workflow.workflow_id,
            input_data={},
            triggered_by="test-user",
            trigger_type=TriggerType.MANUAL
        )
        
        # Mock task executor to be slow
        with patch.object(workflow_engine.task_executor, 'execute_task', new_callable=AsyncMock) as mock_execute:
            async def slow_task(*args, **kwargs):
                await asyncio.sleep(2)
                return {"result": "success"}
            
            mock_execute.side_effect = slow_task
            
            # Execute workflow
            result = await workflow_engine.execute_workflow(instance.instance_id, background=False)
            
            assert result.status == WorkflowStatus.FAILED
            assert "timed out" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_execute_conditional_task(self, workflow_engine, test_db):
        """Test executing conditional tasks"""
        # Create workflow with conditional logic
        workflow = WorkflowDefinitionDB(
            workflow_id="conditional-workflow",
            name="Conditional Test",
            description="Test conditional execution",
            version="1.0.0",
            enabled=True,
            priority="normal",
            triggers=[],
            variables={},
            tasks=[{
                "task_id": "conditional-1",
                "task_type": "condition",
                "name": "Check Condition",
                "conditions": [{
                    "field": "variables.check_value",
                    "operator": "equals",
                    "value": "yes"
                }],
                "then_tasks": [{
                    "task_id": "then-task",
                    "task_type": "wait",
                    "name": "Then Task",
                    "parameters": {"seconds": 1}
                }],
                "else_tasks": [{
                    "task_id": "else-task",
                    "task_type": "wait",
                    "name": "Else Task",
                    "parameters": {"seconds": 1}
                }]
            }],
            timeout=3600,
            max_retries=0,
            retry_delay=60,
            tags=[],
            category="test",
            created_by="test-user"
        )
        test_db.add(workflow)
        await test_db.commit()
        
        # Test with condition true
        instance = await workflow_engine.create_workflow_instance(
            workflow_id=workflow.workflow_id,
            input_data={"check_value": "yes"},
            triggered_by="test-user",
            trigger_type=TriggerType.MANUAL
        )
        
        with patch.object(workflow_engine.task_executor, 'execute_task', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {"result": "success"}
            
            result = await workflow_engine.execute_workflow(instance.instance_id, background=False)
            
            assert result.status == WorkflowStatus.COMPLETED
            # Should execute then-task
            executed_task_ids = [call[0][1].task_id for call in mock_execute.call_args_list]
            assert "then-task" in executed_task_ids
            assert "else-task" not in executed_task_ids
        
        # Test with condition false
        instance2 = await workflow_engine.create_workflow_instance(
            workflow_id=workflow.workflow_id,
            input_data={"check_value": "no"},
            triggered_by="test-user",
            trigger_type=TriggerType.MANUAL
        )
        
        with patch.object(workflow_engine.task_executor, 'execute_task', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {"result": "success"}
            
            result = await workflow_engine.execute_workflow(instance2.instance_id, background=False)
            
            assert result.status == WorkflowStatus.COMPLETED
            # Should execute else-task
            executed_task_ids = [call[0][1].task_id for call in mock_execute.call_args_list]
            assert "else-task" in executed_task_ids
            assert "then-task" not in executed_task_ids
    
    @pytest.mark.asyncio
    async def test_execute_parallel_tasks(self, workflow_engine, test_db):
        """Test executing parallel tasks"""
        # Create workflow with parallel tasks
        workflow = WorkflowDefinitionDB(
            workflow_id="parallel-workflow",
            name="Parallel Test",
            description="Test parallel execution",
            version="1.0.0",
            enabled=True,
            priority="normal",
            triggers=[],
            variables={},
            tasks=[{
                "task_id": "parallel-group",
                "task_type": "parallel",
                "name": "Parallel Tasks",
                "tasks": [
                    {
                        "task_id": "parallel-1",
                        "task_type": "wait",
                        "name": "Parallel Task 1",
                        "parameters": {"seconds": 1}
                    },
                    {
                        "task_id": "parallel-2",
                        "task_type": "wait",
                        "name": "Parallel Task 2",
                        "parameters": {"seconds": 1}
                    },
                    {
                        "task_id": "parallel-3",
                        "task_type": "wait",
                        "name": "Parallel Task 3",
                        "parameters": {"seconds": 1}
                    }
                ],
                "wait_for_all": True,
                "max_concurrent": 2
            }],
            timeout=3600,
            max_retries=0,
            retry_delay=60,
            tags=[],
            category="test",
            created_by="test-user"
        )
        test_db.add(workflow)
        await test_db.commit()
        
        # Create instance
        instance = await workflow_engine.create_workflow_instance(
            workflow_id=workflow.workflow_id,
            input_data={},
            triggered_by="test-user",
            trigger_type=TriggerType.MANUAL
        )
        
        # Track execution order
        execution_order = []
        
        async def mock_execute_task(task_instance, task_config, context):
            execution_order.append(task_config.task_id)
            await asyncio.sleep(0.1)  # Simulate work
            return {"task_id": task_config.task_id, "result": "success"}
        
        with patch.object(workflow_engine.task_executor, 'execute_task', new=mock_execute_task):
            result = await workflow_engine.execute_workflow(instance.instance_id, background=False)
            
            assert result.status == WorkflowStatus.COMPLETED
            # All parallel tasks should be executed
            assert len(execution_order) == 3
            assert all(task_id in execution_order for task_id in ["parallel-1", "parallel-2", "parallel-3"])
    
    @pytest.mark.asyncio
    async def test_execute_loop_task(self, workflow_engine, test_db):
        """Test executing loop tasks"""
        # Create workflow with loop
        workflow = WorkflowDefinitionDB(
            workflow_id="loop-workflow",
            name="Loop Test",
            description="Test loop execution",
            version="1.0.0",
            enabled=True,
            priority="normal",
            triggers=[],
            variables={"items": ["item1", "item2", "item3"]},
            tasks=[{
                "task_id": "loop-1",
                "task_type": "loop",
                "name": "Process Items",
                "items_source": "variables.items",
                "item_variable": "current_item",
                "tasks": [{
                    "task_id": "process-item",
                    "task_type": "wait",
                    "name": "Process Item",
                    "parameters": {
                        "seconds": 1,
                        "item": "$variables.current_item"
                    }
                }],
                "max_iterations": 5,
                "parallel_execution": False
            }],
            timeout=3600,
            max_retries=0,
            retry_delay=60,
            tags=[],
            category="test",
            created_by="test-user"
        )
        test_db.add(workflow)
        await test_db.commit()
        
        # Create instance
        instance = await workflow_engine.create_workflow_instance(
            workflow_id=workflow.workflow_id,
            input_data={},
            triggered_by="test-user",
            trigger_type=TriggerType.MANUAL
        )
        
        # Track processed items
        processed_items = []
        
        async def mock_execute_task(task_instance, task_config, context):
            if "item" in task_config.parameters:
                processed_items.append(task_config.parameters["item"])
            return {"result": "success"}
        
        with patch.object(workflow_engine.task_executor, 'execute_task', new=mock_execute_task):
            result = await workflow_engine.execute_workflow(instance.instance_id, background=False)
            
            assert result.status == WorkflowStatus.COMPLETED
            # Should process all items
            assert len(processed_items) == 3
            assert processed_items == ["item1", "item2", "item3"]
    
    @pytest.mark.asyncio
    async def test_pause_resume_workflow(self, workflow_engine, sample_workflow_definition, test_db):
        """Test pausing and resuming a workflow"""
        # Create and start instance
        instance = await workflow_engine.create_workflow_instance(
            workflow_id=sample_workflow_definition.workflow_id,
            input_data={},
            triggered_by="test-user",
            trigger_type=TriggerType.MANUAL
        )
        
        # Update to running state
        instance_db = await test_db.get(WorkflowInstanceDB, instance.instance_id)
        instance_db.status = WorkflowStatus.RUNNING
        await test_db.commit()
        
        # Pause workflow
        paused_instance = await workflow_engine.pause_workflow(instance.instance_id)
        assert paused_instance.status == WorkflowStatus.PAUSED
        
        # Resume workflow
        with patch.object(workflow_engine, 'execute_workflow', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = paused_instance
            resumed_instance = await workflow_engine.resume_workflow(instance.instance_id)
            assert resumed_instance.status == WorkflowStatus.PAUSED  # Mock doesn't change status
            mock_execute.assert_called_once_with(instance.instance_id)
    
    @pytest.mark.asyncio
    async def test_cancel_workflow(self, workflow_engine, sample_workflow_definition, test_db):
        """Test cancelling a workflow"""
        # Create and start instance
        instance = await workflow_engine.create_workflow_instance(
            workflow_id=sample_workflow_definition.workflow_id,
            input_data={},
            triggered_by="test-user",
            trigger_type=TriggerType.MANUAL
        )
        
        # Update to running state
        instance_db = await test_db.get(WorkflowInstanceDB, instance.instance_id)
        instance_db.status = WorkflowStatus.RUNNING
        await test_db.commit()
        
        # Add to running workflows
        mock_task = Mock()
        workflow_engine.running_workflows[instance.instance_id] = mock_task
        
        # Cancel workflow
        cancelled_instance = await workflow_engine.cancel_workflow(instance.instance_id)
        assert cancelled_instance.status == WorkflowStatus.CANCELLED
        assert cancelled_instance.completed_at is not None
        mock_task.cancel.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_evaluate_conditions(self, workflow_engine):
        """Test condition evaluation logic"""
        context = {
            "variables": {
                "status": "active",
                "count": 10,
                "tags": ["tag1", "tag2"],
                "name": "test_name",
                "empty_value": "",
                "null_value": None
            }
        }
        
        # Test equals
        conditions = [{
            "field": "variables.status",
            "operator": ConditionOperator.EQUALS,
            "value": "active"
        }]
        assert await workflow_engine._evaluate_conditions(conditions, context) is True
        
        # Test not equals
        conditions = [{
            "field": "variables.status",
            "operator": ConditionOperator.NOT_EQUALS,
            "value": "inactive"
        }]
        assert await workflow_engine._evaluate_conditions(conditions, context) is True
        
        # Test greater than
        conditions = [{
            "field": "variables.count",
            "operator": ConditionOperator.GREATER_THAN,
            "value": 5
        }]
        assert await workflow_engine._evaluate_conditions(conditions, context) is True
        
        # Test contains
        conditions = [{
            "field": "variables.name",
            "operator": ConditionOperator.CONTAINS,
            "value": "test"
        }]
        assert await workflow_engine._evaluate_conditions(conditions, context) is True
        
        # Test in
        conditions = [{
            "field": "tag1",
            "operator": ConditionOperator.IN,
            "value": ["tag1", "tag2", "tag3"]
        }]
        assert await workflow_engine._evaluate_conditions(conditions, context) is True
        
        # Test exists
        conditions = [{
            "field": "variables.status",
            "operator": ConditionOperator.EXISTS,
            "value": None
        }]
        assert await workflow_engine._evaluate_conditions(conditions, context) is True
        
        # Test is empty
        conditions = [{
            "field": "variables.empty_value",
            "operator": ConditionOperator.IS_EMPTY,
            "value": None
        }]
        assert await workflow_engine._evaluate_conditions(conditions, context) is True
        
        # Test multiple conditions with AND
        conditions = [
            {
                "field": "variables.status",
                "operator": ConditionOperator.EQUALS,
                "value": "active",
                "logical_operator": "and"
            },
            {
                "field": "variables.count",
                "operator": ConditionOperator.GREATER_THAN,
                "value": 5,
                "logical_operator": "and"
            }
        ]
        assert await workflow_engine._evaluate_conditions(conditions, context) is True
        
        # Test multiple conditions with OR
        conditions = [
            {
                "field": "variables.status",
                "operator": ConditionOperator.EQUALS,
                "value": "inactive",
                "logical_operator": "or"
            },
            {
                "field": "variables.count",
                "operator": ConditionOperator.GREATER_THAN,
                "value": 5,
                "logical_operator": "or"
            }
        ]
        assert await workflow_engine._evaluate_conditions(conditions, context) is True
    
    @pytest.mark.asyncio
    async def test_resolve_variable(self, workflow_engine):
        """Test variable resolution"""
        context = {
            "workflow": {
                "id": "workflow-123",
                "instance_id": "instance-456"
            },
            "variables": {
                "nested": {
                    "value": "test_value"
                },
                "array": [1, 2, 3]
            },
            "output": {
                "task1": {"result": "success"}
            }
        }
        
        # Test simple variable
        assert workflow_engine._resolve_variable("variables.nested.value", context) == "test_value"
        
        # Test array access
        assert workflow_engine._resolve_variable("variables.array", context) == [1, 2, 3]
        
        # Test output access
        assert workflow_engine._resolve_variable("output.task1.result", context) == "success"
        
        # Test special variables
        assert workflow_engine._resolve_variable("$workflow_id", context) == "workflow-123"
        assert workflow_engine._resolve_variable("$instance_id", context) == "instance-456"
        assert isinstance(workflow_engine._resolve_variable("$now", context), datetime)
        
        # Test non-existent path
        assert workflow_engine._resolve_variable("variables.non_existent", context) is None
        
        # Test empty path
        assert workflow_engine._resolve_variable("", context) is None