"""
Comprehensive integration tests for Workflow Engine Service
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import Mock, AsyncMock, patch
import aioredis

from src.services.workflow_engine import WorkflowEngine
from src.services.workflow_service import WorkflowService
from src.services.task_executor import TaskExecutor
from src.services.trigger_service import TriggerService
from src.models.schemas import (
    WorkflowCreateRequest, WorkflowTrigger, TaskConfig,
    TriggerType, TaskType, WorkflowStatus, TaskStatus,
    WorkflowPriority, ConditionOperator
)
from src.db.models import (
    WorkflowDefinition as WorkflowDefinitionDB,
    WorkflowInstance as WorkflowInstanceDB,
    TaskInstance as TaskInstanceDB
)


class TestWorkflowIntegration:
    """Integration tests for complete workflow execution"""
    
    @pytest.fixture
    async def setup_services(self, test_db: AsyncSession):
        """Setup all required services"""
        redis_client = Mock(spec=aioredis.Redis)
        redis_client.get = AsyncMock(return_value=None)
        redis_client.set = AsyncMock(return_value=True)
        redis_client.delete = AsyncMock(return_value=1)
        
        workflow_service = WorkflowService(test_db)
        workflow_engine = WorkflowEngine(test_db, redis_client)
        task_executor = TaskExecutor(test_db, redis_client)
        trigger_service = TriggerService(test_db)
        
        return {
            "workflow_service": workflow_service,
            "workflow_engine": workflow_engine,
            "task_executor": task_executor,
            "trigger_service": trigger_service,
            "redis": redis_client
        }
    
    @pytest.mark.asyncio
    async def test_complete_workflow_execution(self, setup_services, client: AsyncClient, auth_headers):
        """Test complete workflow execution from API to completion"""
        services = await setup_services
        
        # 1. Create workflow via API
        workflow_data = {
            "name": "Integration Test Workflow",
            "description": "End-to-end test workflow",
            "enabled": True,
            "priority": "high",
            "triggers": [
                {
                    "trigger_type": "manual",
                    "enabled": True,
                    "config": {}
                }
            ],
            "variables": {
                "test_mode": True,
                "notification_email": "test@example.com"
            },
            "tasks": [
                {
                    "task_id": "validate",
                    "task_type": "wait",
                    "name": "Initial Validation",
                    "parameters": {"seconds": 0.1}
                },
                {
                    "task_id": "check-mode",
                    "task_type": "condition",
                    "name": "Check Test Mode",
                    "conditions": [{
                        "field": "variables.test_mode",
                        "operator": "equals",
                        "value": True
                    }],
                    "then_tasks": [{
                        "task_id": "test-process",
                        "task_type": "wait",
                        "name": "Test Processing",
                        "parameters": {"seconds": 0.1}
                    }],
                    "else_tasks": [{
                        "task_id": "real-process",
                        "task_type": "wait",
                        "name": "Real Processing",
                        "parameters": {"seconds": 1}
                    }]
                },
                {
                    "task_id": "notify",
                    "task_type": "send_email",
                    "name": "Send Completion Email",
                    "parameters": {
                        "to": ["$variables.notification_email"],
                        "subject": "Workflow Complete",
                        "body": "The workflow has completed successfully."
                    }
                }
            ],
            "tags": ["integration-test"]
        }
        
        # Create workflow
        response = await client.post(
            "/api/v1/workflows",
            json=workflow_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        workflow = response.json()
        workflow_id = workflow["workflow_id"]
        
        # 2. Execute workflow via API
        execute_data = {
            "input_data": {
                "custom_email": "custom@example.com"
            },
            "priority": "critical",
            "tags": ["test-execution"],
            "metadata": {"test_run": True}
        }
        
        # Mock task execution
        with patch.object(services["task_executor"], '_execute_wait', new_callable=AsyncMock) as mock_wait, \
             patch.object(services["task_executor"], '_execute_send_email', new_callable=AsyncMock) as mock_email:
            
            mock_wait.return_value = {"waited": True}
            mock_email.return_value = {"sent": True, "message_id": "test-123"}
            
            response = await client.post(
                f"/api/v1/workflows/{workflow_id}/execute",
                json=execute_data,
                headers=auth_headers
            )
            assert response.status_code == 200
            instance = response.json()
            instance_id = instance["instance_id"]
            
            # Wait for execution to complete
            await asyncio.sleep(1)
            
            # 3. Check instance status
            response = await client.get(
                f"/api/v1/instances/{instance_id}",
                headers=auth_headers
            )
            assert response.status_code == 200
            completed_instance = response.json()
            
            # Verify execution results
            assert completed_instance["status"] in ["completed", "running"]
            assert completed_instance["workflow_id"] == workflow_id
            
            # Verify task execution
            assert mock_wait.call_count >= 2  # Initial validation + test process
            assert mock_email.call_count == 1
    
    @pytest.mark.asyncio
    async def test_workflow_with_parallel_execution(self, setup_services, test_db):
        """Test workflow with parallel task execution"""
        services = await setup_services
        
        # Create workflow with parallel tasks
        workflow_request = WorkflowCreateRequest(
            name="Parallel Execution Test",
            description="Test parallel task execution",
            tasks=[
                {
                    "task_id": "parallel-group",
                    "task_type": "parallel",
                    "name": "Process Multiple Files",
                    "tasks": [
                        {
                            "task_id": "process-1",
                            "task_type": "transcode",
                            "name": "Transcode File 1",
                            "parameters": {
                                "input_file": "/input/file1.mp4",
                                "output_file": "/output/file1_transcoded.mp4"
                            }
                        },
                        {
                            "task_id": "process-2",
                            "task_type": "transcode",
                            "name": "Transcode File 2",
                            "parameters": {
                                "input_file": "/input/file2.mp4",
                                "output_file": "/output/file2_transcoded.mp4"
                            }
                        },
                        {
                            "task_id": "process-3",
                            "task_type": "extract_metadata",
                            "name": "Extract Metadata",
                            "parameters": {
                                "file_path": "/input/file1.mp4"
                            }
                        }
                    ],
                    "wait_for_all": True,
                    "max_concurrent": 2
                }
            ]
        )
        
        # Create and execute workflow
        workflow = await services["workflow_service"].create_workflow(workflow_request)
        
        instance = await services["workflow_engine"].create_workflow_instance(
            workflow_id=workflow.workflow_id,
            input_data={},
            triggered_by="test-user",
            trigger_type=TriggerType.MANUAL
        )
        
        # Mock parallel task execution
        execution_times = []
        
        async def mock_transcode(*args, **kwargs):
            start = datetime.utcnow()
            await asyncio.sleep(0.2)  # Simulate work
            execution_times.append((start, datetime.utcnow()))
            return {"transcoded": True}
        
        async def mock_extract(*args, **kwargs):
            start = datetime.utcnow()
            await asyncio.sleep(0.1)
            execution_times.append((start, datetime.utcnow()))
            return {"metadata": {"duration": 120}}
        
        with patch.object(services["task_executor"], '_execute_transcode', new=mock_transcode), \
             patch.object(services["task_executor"], '_execute_extract_metadata', new=mock_extract):
            
            result = await services["workflow_engine"].execute_workflow(
                instance.instance_id,
                background=False
            )
            
            assert result.status == WorkflowStatus.COMPLETED
            
            # Verify parallel execution (some tasks should overlap)
            assert len(execution_times) == 3
            # Check for overlapping execution times
            overlaps = 0
            for i in range(len(execution_times)):
                for j in range(i + 1, len(execution_times)):
                    start1, end1 = execution_times[i]
                    start2, end2 = execution_times[j]
                    if start1 < end2 and start2 < end1:
                        overlaps += 1
            assert overlaps > 0  # At least some tasks ran in parallel
    
    @pytest.mark.asyncio
    async def test_workflow_error_handling_and_retry(self, setup_services, test_db):
        """Test workflow error handling and retry logic"""
        services = await setup_services
        
        # Create workflow with retry configuration
        workflow_request = WorkflowCreateRequest(
            name="Error Handling Test",
            description="Test error handling and retries",
            tasks=[
                {
                    "task_id": "unreliable-task",
                    "task_type": "api_call",
                    "name": "Call Unreliable API",
                    "parameters": {
                        "endpoint": "https://api.example.com/unreliable",
                        "method": "POST",
                        "body": {"data": "test"}
                    },
                    "retry_count": 3,
                    "retry_delay": 1,
                    "continue_on_error": False
                },
                {
                    "task_id": "cleanup",
                    "task_type": "wait",
                    "name": "Cleanup",
                    "parameters": {"seconds": 0.1}
                }
            ]
        )
        
        workflow = await services["workflow_service"].create_workflow(workflow_request)
        
        instance = await services["workflow_engine"].create_workflow_instance(
            workflow_id=workflow.workflow_id,
            input_data={},
            triggered_by="test-user",
            trigger_type=TriggerType.MANUAL
        )
        
        # Mock API call to fail twice then succeed
        call_count = 0
        
        async def mock_api_call(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("API temporarily unavailable")
            return {"status_code": 200, "response": {"success": True}}
        
        with patch.object(services["task_executor"], '_execute_api_call', new=mock_api_call), \
             patch.object(services["task_executor"], '_execute_wait', new_callable=AsyncMock) as mock_wait:
            
            mock_wait.return_value = {"waited": True}
            
            # Execute workflow (should retry and eventually succeed)
            result = await services["workflow_engine"].execute_workflow(
                instance.instance_id,
                background=False
            )
            
            # Should eventually succeed after retries
            assert call_count == 3  # Failed twice, succeeded on third try
    
    @pytest.mark.asyncio
    async def test_scheduled_workflow_execution(self, setup_services, test_db):
        """Test scheduled workflow execution"""
        services = await setup_services
        
        # Create workflow with schedule trigger
        workflow_request = WorkflowCreateRequest(
            name="Scheduled Workflow",
            description="Runs on schedule",
            triggers=[
                WorkflowTrigger(
                    trigger_type=TriggerType.SCHEDULE,
                    enabled=True,
                    config={
                        "cron": "*/5 * * * *",  # Every 5 minutes
                        "timezone": "UTC"
                    }
                )
            ],
            tasks=[
                {
                    "task_id": "scheduled-task",
                    "task_type": "wait",
                    "name": "Scheduled Task",
                    "parameters": {"seconds": 1}
                }
            ]
        )
        
        workflow = await services["workflow_service"].create_workflow(workflow_request)
        
        # Simulate schedule trigger
        scheduled_time = datetime.utcnow() + timedelta(minutes=5)
        
        instance = await services["workflow_engine"].create_workflow_instance(
            workflow_id=workflow.workflow_id,
            input_data={},
            triggered_by="scheduler",
            trigger_type=TriggerType.SCHEDULE,
            scheduled_at=scheduled_time
        )
        
        assert instance.status == WorkflowStatus.SCHEDULED
        assert instance.scheduled_at == scheduled_time
    
    @pytest.mark.asyncio
    async def test_workflow_with_approval_step(self, setup_services, test_db):
        """Test workflow with human approval step"""
        services = await setup_services
        
        # Create workflow requiring approval
        workflow_request = WorkflowCreateRequest(
            name="Approval Workflow",
            description="Requires manager approval",
            tasks=[
                {
                    "task_id": "prepare",
                    "task_type": "wait",
                    "name": "Prepare Data",
                    "parameters": {"seconds": 0.1}
                },
                {
                    "task_id": "approval",
                    "task_type": "approval",
                    "name": "Manager Approval",
                    "parameters": {
                        "approvers": ["manager-123", "manager-456"],
                        "approval_type": "any",
                        "timeout_hours": 24,
                        "message": "Please approve the processed data"
                    }
                },
                {
                    "task_id": "publish",
                    "task_type": "publish_asset",
                    "name": "Publish Asset",
                    "parameters": {
                        "asset_id": "asset-123",
                        "channel": "production"
                    }
                }
            ]
        )
        
        workflow = await services["workflow_service"].create_workflow(workflow_request)
        
        instance = await services["workflow_engine"].create_workflow_instance(
            workflow_id=workflow.workflow_id,
            input_data={},
            triggered_by="test-user",
            trigger_type=TriggerType.MANUAL
        )
        
        # Mock task execution
        async def mock_approval(*args, **kwargs):
            # Simulate waiting for approval
            await asyncio.sleep(0.2)
            return {
                "approved": True,
                "approver": "manager-123",
                "approval_time": datetime.utcnow().isoformat(),
                "comments": "Approved for production"
            }
        
        with patch.object(services["task_executor"], '_execute_wait', new_callable=AsyncMock) as mock_wait, \
             patch.object(services["task_executor"], '_execute_approval', new=mock_approval), \
             patch.object(services["task_executor"], '_execute_publish_asset', new_callable=AsyncMock) as mock_publish:
            
            mock_wait.return_value = {"waited": True}
            mock_publish.return_value = {"published": True}
            
            result = await services["workflow_engine"].execute_workflow(
                instance.instance_id,
                background=False
            )
            
            assert result.status == WorkflowStatus.COMPLETED
            assert mock_publish.called  # Should proceed after approval
    
    @pytest.mark.asyncio
    async def test_workflow_monitoring_and_stats(self, client: AsyncClient, auth_headers, test_db):
        """Test workflow monitoring and statistics"""
        # Create and execute multiple workflows
        workflow_ids = []
        instance_ids = []
        
        for i in range(5):
            # Create workflow
            workflow_data = {
                "name": f"Stats Test Workflow {i}",
                "enabled": True,
                "tasks": [{
                    "task_type": "wait",
                    "name": "Wait Task",
                    "parameters": {"seconds": 0.1}
                }]
            }
            
            response = await client.post(
                "/api/v1/workflows",
                json=workflow_data,
                headers=auth_headers
            )
            workflow = response.json()
            workflow_ids.append(workflow["workflow_id"])
            
            # Execute workflow
            response = await client.post(
                f"/api/v1/workflows/{workflow['workflow_id']}/execute",
                json={"input_data": {}},
                headers=auth_headers
            )
            instance = response.json()
            instance_ids.append(instance["instance_id"])
        
        # Wait for executions
        await asyncio.sleep(0.5)
        
        # Get statistics
        response = await client.get(
            "/api/v1/stats",
            headers=auth_headers
        )
        assert response.status_code == 200
        stats = response.json()
        
        assert stats["total_workflows"] >= 5
        assert stats["total_executions"] >= 5
        
        # Get monitoring dashboard
        response = await client.get(
            "/api/v1/monitoring/dashboard",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # Get specific workflow metrics
        response = await client.get(
            f"/api/v1/monitoring/workflows/{workflow_ids[0]}",
            headers=auth_headers
        )
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_workflow_pause_resume_cancel(self, setup_services, client: AsyncClient, auth_headers):
        """Test workflow pause, resume, and cancel operations"""
        services = await setup_services
        
        # Create long-running workflow
        workflow_data = {
            "name": "Long Running Workflow",
            "enabled": True,
            "tasks": [
                {
                    "task_id": "task-1",
                    "task_type": "wait",
                    "name": "Wait 10s",
                    "parameters": {"seconds": 10}
                },
                {
                    "task_id": "task-2",
                    "task_type": "wait",
                    "name": "Wait 5s",
                    "parameters": {"seconds": 5}
                }
            ]
        }
        
        # Create and start workflow
        response = await client.post(
            "/api/v1/workflows",
            json=workflow_data,
            headers=auth_headers
        )
        workflow = response.json()
        
        response = await client.post(
            f"/api/v1/workflows/{workflow['workflow_id']}/execute",
            json={"input_data": {}},
            headers=auth_headers
        )
        instance = response.json()
        instance_id = instance["instance_id"]
        
        # Wait a bit then pause
        await asyncio.sleep(0.5)
        
        response = await client.post(
            f"/api/v1/instances/{instance_id}/pause",
            headers=auth_headers
        )
        assert response.status_code in [200, 400]  # Depends on execution state
        
        # Try to resume
        response = await client.post(
            f"/api/v1/instances/{instance_id}/resume",
            headers=auth_headers
        )
        assert response.status_code in [200, 400]
        
        # Cancel workflow
        response = await client.post(
            f"/api/v1/instances/{instance_id}/cancel",
            headers=auth_headers
        )
        assert response.status_code in [200, 400]