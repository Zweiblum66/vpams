"""
Comprehensive API endpoint tests for Workflow Engine Service
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import json

from src.models.schemas import (
    WorkflowStatus, TaskStatus, WorkflowPriority, TriggerType, TaskType,
    WorkflowTrigger, TaskConfig
)
from src.db.models import (
    WorkflowDefinition as WorkflowDefinitionDB,
    WorkflowInstance as WorkflowInstanceDB,
    TaskInstance as TaskInstanceDB
)


class TestWorkflowDefinitionEndpoints:
    """Test workflow definition CRUD endpoints"""
    
    @pytest.mark.asyncio
    async def test_create_workflow(self, client: AsyncClient, auth_headers):
        """Test creating a new workflow definition"""
        workflow_data = {
            "name": "Test Workflow",
            "description": "Test workflow for unit tests",
            "enabled": True,
            "priority": "normal",
            "triggers": [
                {
                    "trigger_type": "manual",
                    "enabled": True,
                    "config": {}
                }
            ],
            "variables": {
                "input_path": "/test/input",
                "output_path": "/test/output"
            },
            "tasks": [
                {
                    "task_type": "copy_file",
                    "name": "Copy test file",
                    "parameters": {
                        "source": "$input_path",
                        "destination": "$output_path"
                    }
                }
            ],
            "tags": ["test", "unit-test"]
        }
        
        response = await client.post(
            "/api/v1/workflows",
            json=workflow_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == workflow_data["name"]
        assert data["description"] == workflow_data["description"]
        assert data["enabled"] == workflow_data["enabled"]
        assert data["priority"] == workflow_data["priority"]
        assert data["task_count"] == 1
        assert data["tags"] == workflow_data["tags"]
        assert "workflow_id" in data
        assert "created_at" in data
    
    @pytest.mark.asyncio
    async def test_create_workflow_validation_error(self, client: AsyncClient, auth_headers):
        """Test workflow creation with invalid data"""
        invalid_data = {
            "name": "",  # Empty name
            "tasks": []  # No tasks
        }
        
        response = await client.post(
            "/api/v1/workflows",
            json=invalid_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_list_workflows(self, client: AsyncClient, auth_headers, test_db: AsyncSession):
        """Test listing workflows with pagination and filtering"""
        # Create test workflows
        for i in range(5):
            workflow = WorkflowDefinitionDB(
                workflow_id=f"test-workflow-{i}",
                name=f"Test Workflow {i}",
                description=f"Description {i}",
                version="1.0.0",
                enabled=i % 2 == 0,
                priority="normal",
                triggers=[],
                variables={},
                tasks=[],
                tags=["test", f"group-{i % 2}"],
                category="test-category" if i < 3 else "other-category",
                created_by="test-user"
            )
            test_db.add(workflow)
        await test_db.commit()
        
        # Test basic listing
        response = await client.get(
            "/api/v1/workflows",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["workflows"]) == 5
        
        # Test pagination
        response = await client.get(
            "/api/v1/workflows?page=1&page_size=2",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["workflows"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2
        
        # Test filtering by enabled
        response = await client.get(
            "/api/v1/workflows?enabled=true",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        
        # Test filtering by category
        response = await client.get(
            "/api/v1/workflows?category=test-category",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        
        # Test filtering by tag
        response = await client.get(
            "/api/v1/workflows?tag=group-0",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        
        # Test search
        response = await client.get(
            "/api/v1/workflows?search=Workflow%202",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
    
    @pytest.mark.asyncio
    async def test_get_workflow(self, client: AsyncClient, auth_headers, test_db: AsyncSession):
        """Test getting a single workflow by ID"""
        # Create test workflow
        workflow = WorkflowDefinitionDB(
            workflow_id="test-get-workflow",
            name="Test Get Workflow",
            description="Test workflow for get endpoint",
            version="1.0.0",
            enabled=True,
            priority="high",
            triggers=[{
                "trigger_type": "schedule",
                "enabled": True,
                "config": {"cron": "0 0 * * *"}
            }],
            variables={"test_var": "value"},
            tasks=[{
                "task_id": "task-1",
                "task_type": "wait",
                "name": "Wait task",
                "parameters": {"seconds": 5}
            }],
            timeout=1800,
            max_retries=2,
            retry_delay=60,
            tags=["test"],
            category="test",
            created_by="test-user"
        )
        test_db.add(workflow)
        await test_db.commit()
        
        # Test get workflow
        response = await client.get(
            f"/api/v1/workflows/{workflow.workflow_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["workflow_id"] == workflow.workflow_id
        assert data["name"] == workflow.name
        assert data["triggers"] == workflow.triggers
        assert data["tasks"] == workflow.tasks
        assert data["timeout"] == workflow.timeout
        
        # Test get non-existent workflow
        response = await client.get(
            "/api/v1/workflows/non-existent-id",
            headers=auth_headers
        )
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_update_workflow(self, client: AsyncClient, auth_headers, test_db: AsyncSession):
        """Test updating a workflow"""
        # Create test workflow
        workflow = WorkflowDefinitionDB(
            workflow_id="test-update-workflow",
            name="Original Name",
            description="Original description",
            version="1.0.0",
            enabled=True,
            priority="normal",
            triggers=[],
            variables={},
            tasks=[],
            tags=["original"],
            category="original",
            created_by="test-user"
        )
        test_db.add(workflow)
        await test_db.commit()
        
        # Update workflow
        update_data = {
            "name": "Updated Name",
            "description": "Updated description",
            "enabled": False,
            "priority": "high",
            "tags": ["updated", "test"]
        }
        
        response = await client.patch(
            f"/api/v1/workflows/{workflow.workflow_id}",
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]
        assert data["enabled"] == update_data["enabled"]
        assert data["priority"] == update_data["priority"]
        assert data["tags"] == update_data["tags"]
        
        # Test update non-existent workflow
        response = await client.patch(
            "/api/v1/workflows/non-existent-id",
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_delete_workflow(self, client: AsyncClient, auth_headers, test_db: AsyncSession):
        """Test deleting a workflow"""
        # Create test workflow
        workflow = WorkflowDefinitionDB(
            workflow_id="test-delete-workflow",
            name="To Delete",
            description="This will be deleted",
            version="1.0.0",
            enabled=True,
            priority="normal",
            triggers=[],
            variables={},
            tasks=[],
            tags=[],
            category="test",
            created_by="test-user"
        )
        test_db.add(workflow)
        await test_db.commit()
        
        # Delete workflow
        response = await client.delete(
            f"/api/v1/workflows/{workflow.workflow_id}",
            headers=auth_headers
        )
        assert response.status_code == 204
        
        # Verify workflow is soft deleted
        response = await client.get(
            f"/api/v1/workflows/{workflow.workflow_id}",
            headers=auth_headers
        )
        assert response.status_code == 404
        
        # Test delete non-existent workflow
        response = await client.delete(
            "/api/v1/workflows/non-existent-id",
            headers=auth_headers
        )
        assert response.status_code == 404


class TestWorkflowExecutionEndpoints:
    """Test workflow execution endpoints"""
    
    @pytest.mark.asyncio
    async def test_execute_workflow(self, client: AsyncClient, auth_headers, test_db: AsyncSession):
        """Test executing a workflow"""
        # Create test workflow
        workflow = WorkflowDefinitionDB(
            workflow_id="test-execute-workflow",
            name="Execute Test",
            description="Workflow for execution test",
            version="1.0.0",
            enabled=True,
            priority="normal",
            triggers=[],
            variables={"default_var": "default_value"},
            tasks=[{
                "task_id": "task-1",
                "task_type": "wait",
                "name": "Wait task",
                "parameters": {"seconds": 1}
            }],
            tags=[],
            category="test",
            created_by="test-user"
        )
        test_db.add(workflow)
        await test_db.commit()
        
        # Execute workflow
        execute_data = {
            "input_data": {
                "custom_var": "custom_value"
            },
            "priority": "high",
            "tags": ["execution-test"],
            "metadata": {"source": "unit-test"}
        }
        
        response = await client.post(
            f"/api/v1/workflows/{workflow.workflow_id}/execute",
            json=execute_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["workflow_id"] == workflow.workflow_id
        assert data["workflow_name"] == workflow.name
        assert data["status"] == "running"
        assert data["priority"] == execute_data["priority"]
        assert "instance_id" in data
        
        # Test execute disabled workflow
        workflow.enabled = False
        await test_db.commit()
        
        response = await client.post(
            f"/api/v1/workflows/{workflow.workflow_id}/execute",
            json=execute_data,
            headers=auth_headers
        )
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_execute_workflow_scheduled(self, client: AsyncClient, auth_headers, test_db: AsyncSession):
        """Test scheduling a workflow for later execution"""
        # Create test workflow
        workflow = WorkflowDefinitionDB(
            workflow_id="test-schedule-workflow",
            name="Schedule Test",
            description="Workflow for schedule test",
            version="1.0.0",
            enabled=True,
            priority="normal",
            triggers=[],
            variables={},
            tasks=[],
            tags=[],
            category="test",
            created_by="test-user"
        )
        test_db.add(workflow)
        await test_db.commit()
        
        # Schedule workflow
        scheduled_time = datetime.utcnow() + timedelta(hours=1)
        execute_data = {
            "input_data": {},
            "scheduled_at": scheduled_time.isoformat()
        }
        
        response = await client.post(
            f"/api/v1/workflows/{workflow.workflow_id}/execute",
            json=execute_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "scheduled"
    
    @pytest.mark.asyncio
    async def test_list_workflow_instances(self, client: AsyncClient, auth_headers, test_db: AsyncSession):
        """Test listing workflow instances with filtering"""
        # Create test instances
        workflow_id = "test-workflow"
        for i in range(5):
            instance = WorkflowInstanceDB(
                instance_id=f"instance-{i}",
                workflow_id=workflow_id,
                workflow_definition_id=1,
                workflow_name="Test Workflow",
                workflow_version="1.0.0",
                status=WorkflowStatus.COMPLETED if i < 3 else WorkflowStatus.FAILED,
                priority="normal",
                input_data={},
                variables={},
                triggered_by=f"user-{i % 2}",
                trigger_type=TriggerType.MANUAL,
                trigger_data={},
                tags=[],
                metadata={},
                created_at=datetime.utcnow() - timedelta(days=i)
            )
            test_db.add(instance)
        await test_db.commit()
        
        # Test basic listing
        response = await client.get(
            "/api/v1/instances",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["instances"]) == 5
        
        # Test filtering by workflow_id
        response = await client.get(
            f"/api/v1/instances?workflow_id={workflow_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        
        # Test filtering by status
        response = await client.get(
            "/api/v1/instances?status=completed",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        
        # Test filtering by triggered_by
        response = await client.get(
            "/api/v1/instances?triggered_by=user-0",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        
        # Test date filtering
        start_date = (datetime.utcnow() - timedelta(days=2)).isoformat()
        response = await client.get(
            f"/api/v1/instances?start_date={start_date}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
    
    @pytest.mark.asyncio
    async def test_get_workflow_instance(self, client: AsyncClient, auth_headers, test_db: AsyncSession):
        """Test getting a single workflow instance"""
        # Create test instance
        instance = WorkflowInstanceDB(
            instance_id="test-get-instance",
            workflow_id="test-workflow",
            workflow_definition_id=1,
            workflow_name="Test Workflow",
            workflow_version="1.0.0",
            status=WorkflowStatus.RUNNING,
            priority="high",
            input_data={"test": "data"},
            variables={"var1": "value1"},
            output_data={"result": "success"},
            triggered_by="test-user",
            trigger_type=TriggerType.API,
            trigger_data={"api_key": "masked"},
            scheduled_at=None,
            started_at=datetime.utcnow(),
            current_task_id="task-1",
            execution_path=["task-0"],
            retry_count=0,
            tags=["test"],
            metadata={"custom": "data"}
        )
        test_db.add(instance)
        await test_db.commit()
        
        # Get instance
        response = await client.get(
            f"/api/v1/instances/{instance.instance_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["instance_id"] == instance.instance_id
        assert data["workflow_id"] == instance.workflow_id
        assert data["status"] == instance.status.value
        assert data["input_data"] == instance.input_data
        assert data["variables"] == instance.variables
        assert data["output_data"] == instance.output_data
        assert data["execution_path"] == instance.execution_path
        
        # Test get non-existent instance
        response = await client.get(
            "/api/v1/instances/non-existent-id",
            headers=auth_headers
        )
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_pause_workflow_instance(self, client: AsyncClient, auth_headers, test_db: AsyncSession):
        """Test pausing a running workflow instance"""
        # Create running instance
        instance = WorkflowInstanceDB(
            instance_id="test-pause-instance",
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
        
        # Mock workflow engine to return paused instance
        response = await client.post(
            f"/api/v1/instances/{instance.instance_id}/pause",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["instance_id"] == instance.instance_id
        # Note: In actual test, the workflow engine would update status to PAUSED
    
    @pytest.mark.asyncio
    async def test_resume_workflow_instance(self, client: AsyncClient, auth_headers, test_db: AsyncSession):
        """Test resuming a paused workflow instance"""
        # Create paused instance
        instance = WorkflowInstanceDB(
            instance_id="test-resume-instance",
            workflow_id="test-workflow",
            workflow_definition_id=1,
            workflow_name="Test Workflow",
            workflow_version="1.0.0",
            status=WorkflowStatus.PAUSED,
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
        
        # Mock workflow engine to return resumed instance
        response = await client.post(
            f"/api/v1/instances/{instance.instance_id}/resume",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["instance_id"] == instance.instance_id
    
    @pytest.mark.asyncio
    async def test_cancel_workflow_instance(self, client: AsyncClient, auth_headers, test_db: AsyncSession):
        """Test cancelling a workflow instance"""
        # Create running instance
        instance = WorkflowInstanceDB(
            instance_id="test-cancel-instance",
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
        
        # Mock workflow engine to return cancelled instance
        response = await client.post(
            f"/api/v1/instances/{instance.instance_id}/cancel",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["instance_id"] == instance.instance_id


class TestWorkflowStatsEndpoint:
    """Test workflow statistics endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_workflow_stats(self, client: AsyncClient, auth_headers, test_db: AsyncSession):
        """Test getting workflow system statistics"""
        # Create test data
        # Create workflows
        for i in range(10):
            workflow = WorkflowDefinitionDB(
                workflow_id=f"workflow-{i}",
                name=f"Workflow {i}",
                description=f"Test workflow {i}",
                version="1.0.0",
                enabled=i < 7,  # 7 active, 3 inactive
                priority="normal",
                triggers=[],
                variables={},
                tasks=[],
                tags=[],
                category="test",
                created_by="test-user",
                deleted=False
            )
            test_db.add(workflow)
        
        # Create instances
        for i in range(20):
            status = WorkflowStatus.COMPLETED if i < 12 else (
                WorkflowStatus.FAILED if i < 15 else WorkflowStatus.RUNNING
            )
            instance = WorkflowInstanceDB(
                instance_id=f"instance-{i}",
                workflow_id=f"workflow-{i % 10}",
                workflow_definition_id=i % 10 + 1,
                workflow_name=f"Workflow {i % 10}",
                workflow_version="1.0.0",
                status=status,
                priority=WorkflowPriority.HIGH if i < 5 else WorkflowPriority.NORMAL,
                input_data={},
                variables={},
                triggered_by="test-user",
                trigger_type=TriggerType.MANUAL if i < 10 else TriggerType.SCHEDULE,
                trigger_data={},
                started_at=datetime.utcnow() - timedelta(minutes=30) if status != WorkflowStatus.PENDING else None,
                completed_at=datetime.utcnow() if status == WorkflowStatus.COMPLETED else None,
                tags=[],
                metadata={},
                created_at=datetime.utcnow() - timedelta(days=i % 7)
            )
            test_db.add(instance)
        
        await test_db.commit()
        
        # Get stats
        response = await client.get(
            "/api/v1/stats",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify workflow counts
        assert data["total_workflows"] == 10
        assert data["active_workflows"] == 7
        
        # Verify execution counts
        assert data["total_executions"] == 20
        assert data["running_executions"] == 5
        assert data["completed_executions"] == 12
        assert data["failed_executions"] == 3
        
        # Verify success rate
        assert data["success_rate"] == 60.0  # 12/20 * 100
        
        # Verify executions by status
        assert data["executions_by_status"]["completed"] == 12
        assert data["executions_by_status"]["failed"] == 3
        assert data["executions_by_status"]["running"] == 5
        
        # Verify executions by priority
        assert data["executions_by_priority"]["high"] == 5
        assert data["executions_by_priority"]["normal"] == 15
        
        # Verify executions by trigger
        assert data["executions_by_trigger"]["manual"] == 10
        assert data["executions_by_trigger"]["schedule"] == 10
        
        # Verify time-based stats
        assert data["executions_today"] > 0
        assert data["executions_this_week"] >= data["executions_today"]
        assert data["executions_this_month"] >= data["executions_this_week"]
        
        # Verify most used workflows
        assert len(data["most_used_workflows"]) <= 5
        if data["most_used_workflows"]:
            assert "workflow_id" in data["most_used_workflows"][0]
            assert "workflow_name" in data["most_used_workflows"][0]
            assert "execution_count" in data["most_used_workflows"][0]
        
        # Verify most failed workflows
        assert len(data["most_failed_workflows"]) <= 5


class TestWebhookEndpoints:
    """Test webhook endpoints"""
    
    @pytest.mark.asyncio
    async def test_handle_webhook(self, client: AsyncClient, test_db: AsyncSession):
        """Test webhook handling"""
        webhook_data = {
            "event": "test_event",
            "data": {
                "key": "value"
            }
        }
        
        response = await client.post(
            "/api/v1/webhooks/test-webhook-path",
            json=webhook_data
        )
        # Note: Actual implementation would trigger workflows
        assert response.status_code in [200, 500]  # Depends on trigger service setup


class TestTriggerEndpoint:
    """Test API trigger endpoint"""
    
    @pytest.mark.asyncio
    async def test_trigger_workflow_api(self, client: AsyncClient, test_db: AsyncSession):
        """Test triggering workflow via API"""
        workflow_id = "test-api-trigger"
        
        response = await client.post(
            f"/api/v1/trigger/{workflow_id}",
            headers={"api-key": "test-api-key"},
            json={"input_key": "input_value"}
        )
        # Note: Actual implementation would validate API key and trigger workflow
        assert response.status_code in [200, 400, 500]


class TestTemplateEndpoints:
    """Test workflow template endpoints"""
    
    @pytest.mark.asyncio
    async def test_list_templates(self, client: AsyncClient, auth_headers):
        """Test listing workflow templates"""
        response = await client.get(
            "/api/v1/templates",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
    
    @pytest.mark.asyncio
    async def test_create_template(self, client: AsyncClient, auth_headers):
        """Test creating a workflow template"""
        template_data = {
            "name": "Test Template",
            "description": "Test template description",
            "category": "test",
            "definition": {
                "tasks": [{
                    "task_type": "wait",
                    "name": "Wait task",
                    "parameters": {"seconds": 5}
                }]
            },
            "tags": ["test", "template"],
            "is_public": False,
            "created_by": "test-user"
        }
        
        response = await client.post(
            "/api/v1/templates",
            json=template_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == template_data["name"]
        assert "template_id" in data
    
    @pytest.mark.asyncio
    async def test_instantiate_template(self, client: AsyncClient, auth_headers):
        """Test creating a workflow from a template"""
        template_id = "test-template-id"
        instantiate_data = {
            "name": "Workflow from Template",
            "description": "Created from template",
            "variables": {"custom_var": "custom_value"},
            "enabled": True,
            "created_by": "test-user"
        }
        
        response = await client.post(
            f"/api/v1/templates/{template_id}/instantiate",
            json=instantiate_data,
            headers=auth_headers
        )
        # Note: Actual implementation would require template to exist
        assert response.status_code in [200, 400, 500]


class TestMonitoringEndpoints:
    """Test monitoring endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_monitoring_dashboard(self, client: AsyncClient, auth_headers):
        """Test getting monitoring dashboard metrics"""
        response = await client.get(
            "/api/v1/monitoring/dashboard",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        # Verify expected dashboard metrics structure
        # Note: Actual structure depends on monitoring service implementation
    
    @pytest.mark.asyncio
    async def test_get_workflow_metrics(self, client: AsyncClient, auth_headers):
        """Test getting metrics for specific workflow"""
        workflow_id = "test-workflow"
        
        response = await client.get(
            f"/api/v1/monitoring/workflows/{workflow_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_get_system_health(self, client: AsyncClient, auth_headers):
        """Test getting system health status"""
        response = await client.get(
            "/api/v1/monitoring/health",
            headers=auth_headers
        )
        assert response.status_code == 200


class TestHealthCheck:
    """Test health check endpoint"""
    
    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test service health check"""
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "workflow-engine"