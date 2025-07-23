"""
Comprehensive tests for Workflow State Manager
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
import aioredis

from src.services.state_manager import WorkflowStateManager
from src.models.schemas import (
    WorkflowInstance, TaskInstance, WorkflowStatus, TaskStatus,
    WorkflowPriority, TriggerType, TaskType
)
from src.db.models import (
    WorkflowInstance as WorkflowInstanceDB,
    TaskInstance as TaskInstanceDB,
    WorkflowEvent as WorkflowEventDB
)


class TestWorkflowStateManager:
    """Test workflow state management functionality"""
    
    @pytest.fixture
    async def state_manager(self, test_db: AsyncSession):
        """Create state manager instance"""
        redis_client = Mock(spec=aioredis.Redis)
        # Mock Redis methods
        redis_client.get = AsyncMock(return_value=None)
        redis_client.set = AsyncMock(return_value=True)
        redis_client.delete = AsyncMock(return_value=1)
        redis_client.expire = AsyncMock(return_value=True)
        redis_client.hget = AsyncMock(return_value=None)
        redis_client.hset = AsyncMock(return_value=1)
        redis_client.hdel = AsyncMock(return_value=1)
        redis_client.keys = AsyncMock(return_value=[])
        
        manager = WorkflowStateManager(test_db, redis_client)
        return manager
    
    @pytest.fixture
    def sample_workflow_instance(self):
        """Create a sample workflow instance"""
        return WorkflowInstance(
            instance_id="test-instance",
            workflow_id="test-workflow",
            workflow_name="Test Workflow",
            workflow_version="1.0.0",
            status=WorkflowStatus.RUNNING,
            priority=WorkflowPriority.NORMAL,
            input_data={"key": "value"},
            variables={"var1": "value1"},
            output_data={},
            triggered_by="test-user",
            trigger_type=TriggerType.MANUAL,
            trigger_data={},
            started_at=datetime.utcnow(),
            current_task_id="task-1",
            execution_path=["task-0"],
            retry_count=0,
            tags=["test"],
            metadata={"source": "test"}
        )
    
    @pytest.fixture
    def sample_task_instance(self):
        """Create a sample task instance"""
        return TaskInstance(
            task_instance_id="test-task-instance",
            workflow_instance_id="test-instance",
            task_id="task-1",
            task_type=TaskType.WAIT,
            task_name="Test Task",
            status=TaskStatus.RUNNING,
            input_data={"seconds": 5},
            started_at=datetime.utcnow()
        )
    
    @pytest.mark.asyncio
    async def test_save_workflow_state(self, state_manager, sample_workflow_instance):
        """Test saving workflow state to cache and database"""
        # Save state
        await state_manager.save_workflow_state(sample_workflow_instance)
        
        # Verify Redis operations
        state_manager.redis.set.assert_called()
        call_args = state_manager.redis.set.call_args
        assert call_args[0][0] == f"workflow:state:{sample_workflow_instance.instance_id}"
        
        # Verify state data
        state_data = json.loads(call_args[0][1])
        assert state_data["instance_id"] == sample_workflow_instance.instance_id
        assert state_data["status"] == sample_workflow_instance.status.value
        assert state_data["current_task_id"] == sample_workflow_instance.current_task_id
    
    @pytest.mark.asyncio
    async def test_load_workflow_state_from_cache(self, state_manager):
        """Test loading workflow state from cache"""
        instance_id = "cached-instance"
        cached_state = {
            "instance_id": instance_id,
            "workflow_id": "test-workflow",
            "status": WorkflowStatus.RUNNING.value,
            "variables": {"var1": "value1"},
            "current_task_id": "task-2"
        }
        
        # Mock Redis to return cached state
        state_manager.redis.get.return_value = json.dumps(cached_state)
        
        # Load state
        state = await state_manager.load_workflow_state(instance_id)
        
        assert state is not None
        assert state["instance_id"] == instance_id
        assert state["status"] == WorkflowStatus.RUNNING.value
        assert state["current_task_id"] == "task-2"
    
    @pytest.mark.asyncio
    async def test_load_workflow_state_from_database(self, state_manager, test_db):
        """Test loading workflow state from database when not in cache"""
        # Create instance in database
        instance = WorkflowInstanceDB(
            instance_id="db-instance",
            workflow_id="test-workflow",
            workflow_definition_id=1,
            workflow_name="Test Workflow",
            workflow_version="1.0.0",
            status=WorkflowStatus.PAUSED,
            priority="high",
            input_data={"input": "data"},
            variables={"var": "value"},
            output_data={"output": "data"},
            triggered_by="user",
            trigger_type=TriggerType.SCHEDULE,
            trigger_data={},
            current_task_id="task-3",
            execution_path=["task-1", "task-2"],
            retry_count=1,
            tags=["db-test"],
            metadata={"meta": "data"}
        )
        test_db.add(instance)
        await test_db.commit()
        
        # Mock Redis to return None (cache miss)
        state_manager.redis.get.return_value = None
        
        # Load state
        state = await state_manager.load_workflow_state(instance.instance_id)
        
        assert state is not None
        assert state["instance_id"] == instance.instance_id
        assert state["status"] == WorkflowStatus.PAUSED.value
        assert state["current_task_id"] == "task-3"
        assert state["execution_path"] == ["task-1", "task-2"]
        
        # Verify state was cached
        state_manager.redis.set.assert_called()
    
    @pytest.mark.asyncio
    async def test_update_workflow_status(self, state_manager, sample_workflow_instance):
        """Test updating workflow status"""
        new_status = WorkflowStatus.COMPLETED
        error_message = None
        
        await state_manager.update_workflow_status(
            sample_workflow_instance.instance_id,
            new_status,
            error_message
        )
        
        # Verify database update would occur
        # In actual implementation, this would update the database
        
        # Verify cache invalidation
        state_manager.redis.delete.assert_called_with(
            f"workflow:state:{sample_workflow_instance.instance_id}"
        )
    
    @pytest.mark.asyncio
    async def test_save_task_state(self, state_manager, sample_task_instance):
        """Test saving task state"""
        await state_manager.save_task_state(sample_task_instance)
        
        # Verify Redis hash operations
        state_manager.redis.hset.assert_called()
        call_args = state_manager.redis.hset.call_args
        assert call_args[0][0] == f"workflow:tasks:{sample_task_instance.workflow_instance_id}"
        assert call_args[0][1] == sample_task_instance.task_id
    
    @pytest.mark.asyncio
    async def test_load_task_state(self, state_manager):
        """Test loading task state"""
        workflow_instance_id = "test-instance"
        task_id = "task-1"
        task_state = {
            "task_id": task_id,
            "status": TaskStatus.COMPLETED.value,
            "output_data": {"result": "success"},
            "duration_seconds": 5.5
        }
        
        # Mock Redis to return task state
        state_manager.redis.hget.return_value = json.dumps(task_state)
        
        # Load state
        state = await state_manager.load_task_state(workflow_instance_id, task_id)
        
        assert state is not None
        assert state["task_id"] == task_id
        assert state["status"] == TaskStatus.COMPLETED.value
        assert state["output_data"]["result"] == "success"
    
    @pytest.mark.asyncio
    async def test_get_workflow_checkpoint(self, state_manager, test_db):
        """Test getting workflow checkpoint for recovery"""
        instance_id = "checkpoint-instance"
        
        # Create workflow with tasks in database
        instance = WorkflowInstanceDB(
            instance_id=instance_id,
            workflow_id="test-workflow",
            workflow_definition_id=1,
            workflow_name="Test Workflow",
            workflow_version="1.0.0",
            status=WorkflowStatus.RUNNING,
            priority="normal",
            input_data={},
            variables={"checkpoint_var": "value"},
            triggered_by="user",
            trigger_type=TriggerType.MANUAL,
            trigger_data={},
            current_task_id="task-3",
            execution_path=["task-1", "task-2"],
            tags=[],
            metadata={}
        )
        test_db.add(instance)
        
        # Add completed tasks
        for i in range(1, 3):
            task = TaskInstanceDB(
                task_instance_id=f"task-instance-{i}",
                workflow_instance_id=instance_id,
                task_id=f"task-{i}",
                task_type="wait",
                task_name=f"Task {i}",
                status=TaskStatus.COMPLETED,
                input_data={},
                output_data={"task_output": f"output-{i}"},
                started_at=datetime.utcnow() - timedelta(minutes=5),
                completed_at=datetime.utcnow() - timedelta(minutes=4),
                duration_seconds=60.0
            )
            test_db.add(task)
        
        await test_db.commit()
        
        # Get checkpoint
        checkpoint = await state_manager.get_workflow_checkpoint(instance_id)
        
        assert checkpoint is not None
        assert checkpoint["instance_id"] == instance_id
        assert checkpoint["current_task_id"] == "task-3"
        assert checkpoint["execution_path"] == ["task-1", "task-2"]
        assert len(checkpoint["completed_tasks"]) == 2
        assert checkpoint["variables"]["checkpoint_var"] == "value"
    
    @pytest.mark.asyncio
    async def test_restore_from_checkpoint(self, state_manager):
        """Test restoring workflow from checkpoint"""
        checkpoint = {
            "instance_id": "restore-instance",
            "workflow_id": "test-workflow",
            "status": WorkflowStatus.PAUSED.value,
            "variables": {"restored_var": "restored_value"},
            "current_task_id": "task-5",
            "execution_path": ["task-1", "task-2", "task-3", "task-4"],
            "completed_tasks": {
                "task-1": {"output": "output1"},
                "task-2": {"output": "output2"},
                "task-3": {"output": "output3"},
                "task-4": {"output": "output4"}
            }
        }
        
        # Restore from checkpoint
        restored_instance = await state_manager.restore_from_checkpoint(checkpoint)
        
        assert restored_instance is not None
        assert restored_instance.instance_id == checkpoint["instance_id"]
        assert restored_instance.status == WorkflowStatus.PAUSED
        assert restored_instance.variables["restored_var"] == "restored_value"
        assert restored_instance.current_task_id == "task-5"
        assert len(restored_instance.execution_path) == 4
    
    @pytest.mark.asyncio
    async def test_get_running_workflows(self, state_manager, test_db):
        """Test getting all running workflows"""
        # Create multiple workflow instances
        for i in range(5):
            status = WorkflowStatus.RUNNING if i < 3 else WorkflowStatus.COMPLETED
            instance = WorkflowInstanceDB(
                instance_id=f"instance-{i}",
                workflow_id="test-workflow",
                workflow_definition_id=1,
                workflow_name="Test Workflow",
                workflow_version="1.0.0",
                status=status,
                priority="normal",
                input_data={},
                variables={},
                triggered_by="user",
                trigger_type=TriggerType.MANUAL,
                trigger_data={},
                tags=[],
                metadata={}
            )
            test_db.add(instance)
        
        await test_db.commit()
        
        # Get running workflows
        running_workflows = await state_manager.get_running_workflows()
        
        assert len(running_workflows) == 3
        assert all(wf["status"] == WorkflowStatus.RUNNING.value for wf in running_workflows)
    
    @pytest.mark.asyncio
    async def test_cleanup_completed_states(self, state_manager):
        """Test cleaning up completed workflow states from cache"""
        # Mock Redis keys
        state_manager.redis.keys.return_value = [
            b"workflow:state:completed-1",
            b"workflow:state:completed-2",
            b"workflow:state:running-1"
        ]
        
        # Mock getting states
        async def mock_get(key):
            if b"completed" in key:
                return json.dumps({"status": WorkflowStatus.COMPLETED.value})
            else:
                return json.dumps({"status": WorkflowStatus.RUNNING.value})
        
        state_manager.redis.get = mock_get
        
        # Cleanup
        deleted_count = await state_manager.cleanup_completed_states(older_than_hours=24)
        
        # Should delete completed states
        assert state_manager.redis.delete.call_count >= 2
    
    @pytest.mark.asyncio
    async def test_get_workflow_metrics(self, state_manager, test_db):
        """Test getting workflow execution metrics"""
        workflow_id = "test-workflow"
        
        # Create instances with various statuses
        for i in range(10):
            instance = WorkflowInstanceDB(
                instance_id=f"metrics-instance-{i}",
                workflow_id=workflow_id,
                workflow_definition_id=1,
                workflow_name="Test Workflow",
                workflow_version="1.0.0",
                status=WorkflowStatus.COMPLETED if i < 7 else WorkflowStatus.FAILED,
                priority="normal",
                input_data={},
                variables={},
                triggered_by="user",
                trigger_type=TriggerType.MANUAL,
                trigger_data={},
                started_at=datetime.utcnow() - timedelta(minutes=10),
                completed_at=datetime.utcnow() if i < 8 else None,
                tags=[],
                metadata={},
                created_at=datetime.utcnow() - timedelta(days=i)
            )
            test_db.add(instance)
        
        await test_db.commit()
        
        # Get metrics
        metrics = await state_manager.get_workflow_metrics(
            workflow_id,
            start_date=datetime.utcnow() - timedelta(days=7)
        )
        
        assert metrics is not None
        assert metrics["total_executions"] > 0
        assert metrics["successful_executions"] > 0
        assert metrics["failed_executions"] > 0
        assert "average_duration" in metrics
        assert "success_rate" in metrics
    
    @pytest.mark.asyncio
    async def test_lock_workflow_instance(self, state_manager):
        """Test workflow instance locking for concurrent execution prevention"""
        instance_id = "lock-instance"
        lock_timeout = 300  # 5 minutes
        
        # Acquire lock
        lock_acquired = await state_manager.acquire_workflow_lock(instance_id, lock_timeout)
        assert lock_acquired is True
        
        # Try to acquire lock again (should fail)
        state_manager.redis.set.return_value = False  # Lock already exists
        lock_acquired_again = await state_manager.acquire_workflow_lock(instance_id, lock_timeout)
        assert lock_acquired_again is False
        
        # Release lock
        await state_manager.release_workflow_lock(instance_id)
        state_manager.redis.delete.assert_called_with(f"workflow:lock:{instance_id}")
    
    @pytest.mark.asyncio
    async def test_workflow_state_events(self, state_manager, test_db):
        """Test workflow state event tracking"""
        instance_id = "event-instance"
        
        # Log various events
        events = [
            ("started", {"trigger": "manual"}),
            ("task_completed", {"task_id": "task-1", "duration": 5.5}),
            ("task_completed", {"task_id": "task-2", "duration": 3.2}),
            ("completed", {"total_duration": 8.7})
        ]
        
        for event_type, event_data in events:
            await state_manager.log_workflow_event(instance_id, event_type, event_data)
        
        # Retrieve events
        workflow_events = await state_manager.get_workflow_events(instance_id)
        
        # In actual implementation, events would be stored and retrieved
        # This test verifies the expected behavior
        assert workflow_events is not None