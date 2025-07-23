"""
Comprehensive tests for Workflow Service
"""

import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from unittest.mock import Mock, AsyncMock, patch

from src.services.workflow_service import WorkflowService
from src.models.schemas import (
    WorkflowCreateRequest, WorkflowUpdateRequest,
    WorkflowTrigger, TaskConfig, TriggerType, TaskType,
    WorkflowPriority
)
from src.db.models import (
    WorkflowDefinition as WorkflowDefinitionDB,
    WorkflowInstance as WorkflowInstanceDB
)
from src.core.exceptions import (
    WorkflowNotFoundError, WorkflowValidationError
)


class TestWorkflowService:
    """Test workflow service functionality"""
    
    @pytest.fixture
    async def workflow_service(self, test_db: AsyncSession):
        """Create workflow service instance"""
        service = WorkflowService(test_db)
        return service
    
    @pytest.fixture
    def sample_workflow_request(self):
        """Create a sample workflow create request"""
        return WorkflowCreateRequest(
            name="Test Workflow",
            description="Test workflow for unit tests",
            enabled=True,
            priority=WorkflowPriority.NORMAL,
            triggers=[
                WorkflowTrigger(
                    trigger_type=TriggerType.MANUAL,
                    enabled=True,
                    config={}
                )
            ],
            variables={
                "default_path": "/default",
                "timeout": 300
            },
            tasks=[
                TaskConfig(
                    task_id="task-1",
                    task_type=TaskType.EXTRACT_METADATA,
                    name="Extract Metadata",
                    parameters={
                        "file_path": "$variables.input_file"
                    }
                ),
                TaskConfig(
                    task_id="task-2",
                    task_type=TaskType.GENERATE_PROXY,
                    name="Generate Proxy",
                    parameters={
                        "input_file": "$variables.input_file",
                        "output_path": "$variables.default_path"
                    }
                )
            ],
            tags=["test", "media-processing"]
        )
    
    @pytest.mark.asyncio
    async def test_create_workflow(self, workflow_service, sample_workflow_request):
        """Test creating a new workflow"""
        workflow = await workflow_service.create_workflow(sample_workflow_request)
        
        assert workflow.workflow_id is not None
        assert workflow.name == sample_workflow_request.name
        assert workflow.description == sample_workflow_request.description
        assert workflow.enabled == sample_workflow_request.enabled
        assert workflow.priority == sample_workflow_request.priority
        assert len(workflow.triggers) == 1
        assert workflow.triggers[0]["trigger_type"] == TriggerType.MANUAL.value
        assert len(workflow.tasks) == 2
        assert workflow.variables == sample_workflow_request.variables
        assert workflow.tags == sample_workflow_request.tags
        assert workflow.version == "1.0.0"
    
    @pytest.mark.asyncio
    async def test_create_workflow_with_schedule_trigger(self, workflow_service):
        """Test creating workflow with schedule trigger"""
        request = WorkflowCreateRequest(
            name="Scheduled Workflow",
            description="Runs on schedule",
            triggers=[
                WorkflowTrigger(
                    trigger_type=TriggerType.SCHEDULE,
                    enabled=True,
                    config={
                        "cron": "0 0 * * *",  # Daily at midnight
                        "timezone": "UTC"
                    }
                )
            ],
            tasks=[
                TaskConfig(
                    task_type=TaskType.DELETE_FILE,
                    name="Cleanup Old Files",
                    parameters={"path": "/temp", "older_than_days": 7}
                )
            ]
        )
        
        workflow = await workflow_service.create_workflow(request)
        
        assert workflow.triggers[0]["trigger_type"] == TriggerType.SCHEDULE.value
        assert workflow.triggers[0]["config"]["cron"] == "0 0 * * *"
    
    @pytest.mark.asyncio
    async def test_create_workflow_with_complex_tasks(self, workflow_service):
        """Test creating workflow with conditional and parallel tasks"""
        request = WorkflowCreateRequest(
            name="Complex Workflow",
            description="Workflow with complex task flow",
            tasks=[
                {
                    "task_id": "check-format",
                    "task_type": TaskType.CONDITION,
                    "name": "Check File Format",
                    "conditions": [{
                        "field": "variables.file_format",
                        "operator": "equals",
                        "value": "mp4"
                    }],
                    "then_tasks": [{
                        "task_id": "transcode-mp4",
                        "task_type": TaskType.TRANSCODE,
                        "name": "Transcode MP4",
                        "parameters": {"codec": "h264"}
                    }],
                    "else_tasks": [{
                        "task_id": "transcode-other",
                        "task_type": TaskType.TRANSCODE,
                        "name": "Transcode Other",
                        "parameters": {"codec": "h265"}
                    }]
                },
                {
                    "task_id": "parallel-processing",
                    "task_type": TaskType.PARALLEL,
                    "name": "Parallel Processing",
                    "tasks": [
                        {
                            "task_id": "generate-thumbnail",
                            "task_type": TaskType.GENERATE_THUMBNAIL,
                            "name": "Generate Thumbnail",
                            "parameters": {}
                        },
                        {
                            "task_id": "extract-audio",
                            "task_type": TaskType.EXTRACT_METADATA,
                            "name": "Extract Audio",
                            "parameters": {"extract_audio": True}
                        }
                    ],
                    "wait_for_all": True
                }
            ]
        )
        
        workflow = await workflow_service.create_workflow(request)
        
        assert len(workflow.tasks) == 2
        assert workflow.tasks[0]["task_type"] == TaskType.CONDITION
        assert workflow.tasks[1]["task_type"] == TaskType.PARALLEL
    
    @pytest.mark.asyncio
    async def test_create_workflow_validation_error(self, workflow_service):
        """Test workflow creation with invalid data"""
        # Workflow with no tasks
        request = WorkflowCreateRequest(
            name="Invalid Workflow",
            description="No tasks",
            tasks=[]
        )
        
        with pytest.raises(WorkflowValidationError):
            await workflow_service.create_workflow(request)
    
    @pytest.mark.asyncio
    async def test_update_workflow(self, workflow_service, test_db):
        """Test updating an existing workflow"""
        # Create workflow
        workflow = WorkflowDefinitionDB(
            workflow_id="update-test",
            name="Original Name",
            description="Original description",
            version="1.0.0",
            enabled=True,
            priority="normal",
            triggers=[],
            variables={},
            tasks=[{
                "task_id": "task-1",
                "task_type": "wait",
                "name": "Wait Task",
                "parameters": {"seconds": 5}
            }],
            tags=["original"],
            category="test",
            created_by="user"
        )
        test_db.add(workflow)
        await test_db.commit()
        
        # Update workflow
        update_request = WorkflowUpdateRequest(
            name="Updated Name",
            description="Updated description",
            enabled=False,
            priority=WorkflowPriority.HIGH,
            tags=["updated", "modified"]
        )
        
        updated_workflow = await workflow_service.update_workflow(
            workflow.workflow_id,
            update_request
        )
        
        assert updated_workflow.name == update_request.name
        assert updated_workflow.description == update_request.description
        assert updated_workflow.enabled == update_request.enabled
        assert updated_workflow.priority == update_request.priority
        assert updated_workflow.tags == update_request.tags
        assert updated_workflow.version == "1.0.0"  # Version unchanged
    
    @pytest.mark.asyncio
    async def test_update_workflow_tasks_increments_version(self, workflow_service, test_db):
        """Test that updating tasks increments the version"""
        # Create workflow
        workflow = WorkflowDefinitionDB(
            workflow_id="version-test",
            name="Version Test",
            description="Test version increment",
            version="1.0.0",
            enabled=True,
            priority="normal",
            triggers=[],
            variables={},
            tasks=[{
                "task_id": "task-1",
                "task_type": "wait",
                "name": "Original Task",
                "parameters": {"seconds": 5}
            }],
            tags=[],
            category="test",
            created_by="user"
        )
        test_db.add(workflow)
        await test_db.commit()
        
        # Update with new tasks
        update_request = WorkflowUpdateRequest(
            tasks=[
                {
                    "task_id": "task-1",
                    "task_type": "wait",
                    "name": "Updated Task",
                    "parameters": {"seconds": 10}
                },
                {
                    "task_id": "task-2",
                    "task_type": "send_email",
                    "name": "New Email Task",
                    "parameters": {"to": ["test@example.com"]}
                }
            ]
        )
        
        updated_workflow = await workflow_service.update_workflow(
            workflow.workflow_id,
            update_request
        )
        
        assert updated_workflow.version == "1.1.0"  # Minor version increment
        assert len(updated_workflow.tasks) == 2
    
    @pytest.mark.asyncio
    async def test_update_non_existent_workflow(self, workflow_service):
        """Test updating a non-existent workflow"""
        update_request = WorkflowUpdateRequest(name="New Name")
        
        with pytest.raises(WorkflowNotFoundError):
            await workflow_service.update_workflow(
                "non-existent-id",
                update_request
            )
    
    @pytest.mark.asyncio
    async def test_delete_workflow(self, workflow_service, test_db):
        """Test soft deleting a workflow"""
        # Create workflow
        workflow = WorkflowDefinitionDB(
            workflow_id="delete-test",
            name="To Delete",
            description="Will be deleted",
            version="1.0.0",
            enabled=True,
            priority="normal",
            triggers=[],
            variables={},
            tasks=[],
            tags=[],
            category="test",
            created_by="user",
            deleted=False
        )
        test_db.add(workflow)
        await test_db.commit()
        
        # Delete workflow
        await workflow_service.delete_workflow(workflow.workflow_id)
        
        # Verify soft delete
        result = await test_db.execute(
            select(WorkflowDefinitionDB).where(
                WorkflowDefinitionDB.workflow_id == workflow.workflow_id
            )
        )
        deleted_workflow = result.scalar_one()
        assert deleted_workflow.deleted is True
        assert deleted_workflow.enabled is False
    
    @pytest.mark.asyncio
    async def test_delete_non_existent_workflow(self, workflow_service):
        """Test deleting a non-existent workflow"""
        with pytest.raises(WorkflowNotFoundError):
            await workflow_service.delete_workflow("non-existent-id")
    
    @pytest.mark.asyncio
    async def test_validate_workflow_definition(self, workflow_service):
        """Test workflow definition validation"""
        # Valid workflow
        valid_workflow = WorkflowCreateRequest(
            name="Valid Workflow",
            tasks=[
                TaskConfig(
                    task_type=TaskType.WAIT,
                    name="Wait Task",
                    parameters={"seconds": 5}
                )
            ]
        )
        
        # Should not raise exception
        await workflow_service.validate_workflow_definition(valid_workflow)
        
        # Invalid workflow - no name
        invalid_workflow = WorkflowCreateRequest(
            name="",
            tasks=[
                TaskConfig(
                    task_type=TaskType.WAIT,
                    name="Wait Task",
                    parameters={"seconds": 5}
                )
            ]
        )
        
        with pytest.raises(WorkflowValidationError):
            await workflow_service.validate_workflow_definition(invalid_workflow)
        
        # Invalid workflow - circular dependency
        circular_workflow = WorkflowCreateRequest(
            name="Circular Workflow",
            tasks=[
                {
                    "task_id": "task-1",
                    "task_type": TaskType.CONDITION,
                    "name": "Condition",
                    "conditions": [{"field": "var", "operator": "equals", "value": "1"}],
                    "then_tasks": [{
                        "task_id": "task-2",
                        "task_type": TaskType.CONDITION,
                        "name": "Nested Condition",
                        "conditions": [{"field": "var", "operator": "equals", "value": "2"}],
                        "then_tasks": [{
                            "task_id": "task-1",  # Circular reference
                            "task_type": TaskType.WAIT,
                            "name": "Wait",
                            "parameters": {"seconds": 1}
                        }]
                    }]
                }
            ]
        )
        
        with pytest.raises(WorkflowValidationError):
            await workflow_service.validate_workflow_definition(circular_workflow)
    
    @pytest.mark.asyncio
    async def test_get_workflow_by_id(self, workflow_service, test_db):
        """Test getting workflow by ID"""
        # Create workflow
        workflow = WorkflowDefinitionDB(
            workflow_id="get-test",
            name="Get Test",
            description="Test getting workflow",
            version="1.0.0",
            enabled=True,
            priority="normal",
            triggers=[],
            variables={"test": "value"},
            tasks=[],
            tags=["test"],
            category="test",
            created_by="user"
        )
        test_db.add(workflow)
        await test_db.commit()
        
        # Get workflow
        retrieved = await workflow_service.get_workflow_by_id(workflow.workflow_id)
        
        assert retrieved is not None
        assert retrieved.workflow_id == workflow.workflow_id
        assert retrieved.name == workflow.name
        assert retrieved.variables == workflow.variables
    
    @pytest.mark.asyncio
    async def test_get_workflows_by_category(self, workflow_service, test_db):
        """Test getting workflows by category"""
        # Create workflows in different categories
        categories = ["media", "media", "data", "notification"]
        for i, category in enumerate(categories):
            workflow = WorkflowDefinitionDB(
                workflow_id=f"category-test-{i}",
                name=f"Workflow {i}",
                description=f"Category {category}",
                version="1.0.0",
                enabled=True,
                priority="normal",
                triggers=[],
                variables={},
                tasks=[],
                tags=[],
                category=category,
                created_by="user"
            )
            test_db.add(workflow)
        await test_db.commit()
        
        # Get workflows by category
        media_workflows = await workflow_service.get_workflows_by_category("media")
        
        assert len(media_workflows) == 2
        assert all(w.category == "media" for w in media_workflows)
    
    @pytest.mark.asyncio
    async def test_get_workflows_by_trigger_type(self, workflow_service, test_db):
        """Test getting workflows by trigger type"""
        # Create workflows with different triggers
        trigger_configs = [
            [{"trigger_type": "manual", "enabled": True, "config": {}}],
            [{"trigger_type": "schedule", "enabled": True, "config": {"cron": "* * * * *"}}],
            [{"trigger_type": "webhook", "enabled": True, "config": {"path": "/hook"}}],
            [
                {"trigger_type": "manual", "enabled": True, "config": {}},
                {"trigger_type": "schedule", "enabled": True, "config": {"cron": "0 0 * * *"}}
            ]
        ]
        
        for i, triggers in enumerate(trigger_configs):
            workflow = WorkflowDefinitionDB(
                workflow_id=f"trigger-test-{i}",
                name=f"Workflow {i}",
                description="Trigger test",
                version="1.0.0",
                enabled=True,
                priority="normal",
                triggers=triggers,
                variables={},
                tasks=[],
                tags=[],
                category="test",
                created_by="user"
            )
            test_db.add(workflow)
        await test_db.commit()
        
        # Get workflows with schedule trigger
        schedule_workflows = await workflow_service.get_workflows_by_trigger_type(
            TriggerType.SCHEDULE
        )
        
        assert len(schedule_workflows) == 2
    
    @pytest.mark.asyncio
    async def test_duplicate_workflow(self, workflow_service, test_db):
        """Test duplicating a workflow"""
        # Create original workflow
        original = WorkflowDefinitionDB(
            workflow_id="original",
            name="Original Workflow",
            description="To be duplicated",
            version="1.0.0",
            enabled=True,
            priority="high",
            triggers=[{"trigger_type": "manual", "enabled": True, "config": {}}],
            variables={"var1": "value1"},
            tasks=[
                {
                    "task_id": "task-1",
                    "task_type": "wait",
                    "name": "Wait Task",
                    "parameters": {"seconds": 10}
                }
            ],
            tags=["original", "template"],
            category="templates",
            created_by="user"
        )
        test_db.add(original)
        await test_db.commit()
        
        # Duplicate workflow
        duplicate = await workflow_service.duplicate_workflow(
            original.workflow_id,
            new_name="Duplicated Workflow"
        )
        
        assert duplicate.workflow_id != original.workflow_id
        assert duplicate.name == "Duplicated Workflow"
        assert duplicate.description == original.description
        assert duplicate.tasks == original.tasks
        assert duplicate.variables == original.variables
        assert duplicate.enabled is False  # Duplicates start disabled
        assert duplicate.version == "1.0.0"  # Reset version