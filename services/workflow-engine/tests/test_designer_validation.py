"""
Comprehensive tests for Workflow Designer and Validation Services
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from src.services.designer_validation_service import DesignerValidationService
from src.services.workflow_designer_service import WorkflowDesignerService
from src.models.schemas import (
    TaskConfig, TaskType, ConditionOperator,
    WorkflowTrigger, TriggerType
)
from src.core.exceptions import WorkflowValidationError


class TestDesignerValidationService:
    """Test workflow designer validation functionality"""
    
    @pytest.fixture
    def validation_service(self):
        """Create validation service instance"""
        return DesignerValidationService()
    
    @pytest.mark.asyncio
    async def test_validate_task_config_valid(self, validation_service):
        """Test validating valid task configurations"""
        # Valid simple task
        task = TaskConfig(
            task_id="task-1",
            task_type=TaskType.WAIT,
            name="Wait Task",
            parameters={"seconds": 5}
        )
        
        errors = await validation_service.validate_task_config(task)
        assert len(errors) == 0
        
        # Valid conditional task
        conditional_task = {
            "task_id": "cond-1",
            "task_type": TaskType.CONDITION,
            "name": "Check Status",
            "conditions": [{
                "field": "variables.status",
                "operator": ConditionOperator.EQUALS,
                "value": "active"
            }],
            "then_tasks": [{
                "task_id": "then-1",
                "task_type": TaskType.SEND_EMAIL,
                "name": "Send Success Email",
                "parameters": {"to": ["user@example.com"]}
            }],
            "else_tasks": []
        }
        
        errors = await validation_service.validate_task_config(conditional_task)
        assert len(errors) == 0
    
    @pytest.mark.asyncio
    async def test_validate_task_config_invalid(self, validation_service):
        """Test validating invalid task configurations"""
        # Missing required parameters
        task = TaskConfig(
            task_id="task-1",
            task_type=TaskType.TRANSCODE,
            name="Transcode Task",
            parameters={}  # Missing input_file, output_file
        )
        
        errors = await validation_service.validate_task_config(task)
        assert len(errors) > 0
        assert any("input_file" in str(e) for e in errors)
        
        # Invalid task type
        task_dict = {
            "task_id": "task-2",
            "task_type": "invalid_type",
            "name": "Invalid Task",
            "parameters": {}
        }
        
        errors = await validation_service.validate_task_config(task_dict)
        assert len(errors) > 0
        assert any("invalid_type" in str(e) for e in errors)
    
    @pytest.mark.asyncio
    async def test_validate_workflow_connections(self, validation_service):
        """Test validating workflow task connections"""
        tasks = [
            {
                "task_id": "task-1",
                "task_type": TaskType.WAIT,
                "name": "Start",
                "parameters": {"seconds": 1}
            },
            {
                "task_id": "task-2",
                "task_type": TaskType.CONDITION,
                "name": "Check",
                "conditions": [{"field": "var", "operator": "equals", "value": "1"}],
                "then_tasks": [{
                    "task_id": "task-3",
                    "task_type": TaskType.WAIT,
                    "name": "Then",
                    "parameters": {"seconds": 1}
                }],
                "else_tasks": [{
                    "task_id": "task-4",
                    "task_type": TaskType.WAIT,
                    "name": "Else",
                    "parameters": {"seconds": 1}
                }]
            }
        ]
        
        errors = await validation_service.validate_workflow_connections(tasks)
        assert len(errors) == 0
    
    @pytest.mark.asyncio
    async def test_detect_circular_dependencies(self, validation_service):
        """Test detecting circular dependencies in workflow"""
        # Workflow with circular dependency
        tasks = [
            {
                "task_id": "task-1",
                "task_type": TaskType.CONDITION,
                "name": "First",
                "conditions": [{"field": "var", "operator": "equals", "value": "1"}],
                "then_tasks": [{
                    "task_id": "task-2",
                    "task_type": TaskType.CONDITION,
                    "name": "Second",
                    "conditions": [{"field": "var", "operator": "equals", "value": "2"}],
                    "then_tasks": [{
                        "task_id": "task-1",  # Circular reference
                        "task_type": TaskType.WAIT,
                        "name": "Back to First",
                        "parameters": {"seconds": 1}
                    }]
                }]
            }
        ]
        
        has_circular = await validation_service.detect_circular_dependencies(tasks)
        assert has_circular is True
        
        # Workflow without circular dependency
        linear_tasks = [
            {
                "task_id": "task-1",
                "task_type": TaskType.WAIT,
                "name": "First",
                "parameters": {"seconds": 1}
            },
            {
                "task_id": "task-2",
                "task_type": TaskType.WAIT,
                "name": "Second",
                "parameters": {"seconds": 1}
            }
        ]
        
        has_circular = await validation_service.detect_circular_dependencies(linear_tasks)
        assert has_circular is False
    
    @pytest.mark.asyncio
    async def test_validate_task_parameters(self, validation_service):
        """Test validating task-specific parameters"""
        # Transcode task parameters
        params = {
            "input_file": "/input/video.mov",
            "output_file": "/output/video.mp4",
            "codec": "h264",
            "bitrate": "5M"
        }
        errors = await validation_service.validate_task_parameters(
            TaskType.TRANSCODE,
            params
        )
        assert len(errors) == 0
        
        # Invalid email parameters
        email_params = {
            "to": "not-an-email",  # Invalid email format
            "subject": "",  # Empty subject
            "body": "Test"
        }
        errors = await validation_service.validate_task_parameters(
            TaskType.SEND_EMAIL,
            email_params
        )
        assert len(errors) > 0
        
        # API call parameters
        api_params = {
            "endpoint": "not-a-url",  # Invalid URL
            "method": "INVALID",  # Invalid HTTP method
            "timeout": -1  # Invalid timeout
        }
        errors = await validation_service.validate_task_parameters(
            TaskType.API_CALL,
            api_params
        )
        assert len(errors) > 0
    
    @pytest.mark.asyncio
    async def test_validate_trigger_config(self, validation_service):
        """Test validating trigger configurations"""
        # Valid schedule trigger
        schedule_trigger = WorkflowTrigger(
            trigger_type=TriggerType.SCHEDULE,
            enabled=True,
            config={
                "cron": "0 0 * * *",
                "timezone": "UTC"
            }
        )
        errors = await validation_service.validate_trigger_config(schedule_trigger)
        assert len(errors) == 0
        
        # Invalid cron expression
        invalid_schedule = WorkflowTrigger(
            trigger_type=TriggerType.SCHEDULE,
            enabled=True,
            config={
                "cron": "invalid cron"
            }
        )
        errors = await validation_service.validate_trigger_config(invalid_schedule)
        assert len(errors) > 0
        
        # Valid webhook trigger
        webhook_trigger = WorkflowTrigger(
            trigger_type=TriggerType.WEBHOOK,
            enabled=True,
            config={
                "path": "/webhooks/github",
                "method": "POST",
                "secret": "webhook-secret"
            }
        )
        errors = await validation_service.validate_trigger_config(webhook_trigger)
        assert len(errors) == 0
        
        # File watch trigger
        file_trigger = WorkflowTrigger(
            trigger_type=TriggerType.FILE_WATCH,
            enabled=True,
            config={
                "path": "/watch/folder",
                "patterns": ["*.mp4", "*.mov"],
                "recursive": True
            }
        )
        errors = await validation_service.validate_trigger_config(file_trigger)
        assert len(errors) == 0
    
    @pytest.mark.asyncio
    async def test_validate_variable_references(self, validation_service):
        """Test validating variable references in parameters"""
        variables = {
            "input_path": "/input",
            "output_path": "/output",
            "format": "mp4"
        }
        
        # Valid references
        params = {
            "source": "$variables.input_path",
            "destination": "$variables.output_path/file.$variables.format"
        }
        errors = await validation_service.validate_variable_references(params, variables)
        assert len(errors) == 0
        
        # Invalid references
        invalid_params = {
            "source": "$variables.non_existent",
            "destination": "$invalid.syntax",
            "value": "$variables.missing_var"
        }
        errors = await validation_service.validate_variable_references(
            invalid_params,
            variables
        )
        assert len(errors) > 0
    
    @pytest.mark.asyncio
    async def test_validate_condition_logic(self, validation_service):
        """Test validating condition logic"""
        # Valid conditions
        conditions = [
            {
                "field": "variables.status",
                "operator": ConditionOperator.EQUALS,
                "value": "active"
            },
            {
                "field": "variables.count",
                "operator": ConditionOperator.GREATER_THAN,
                "value": 10,
                "logical_operator": "and"
            }
        ]
        errors = await validation_service.validate_condition_logic(conditions)
        assert len(errors) == 0
        
        # Invalid operator
        invalid_conditions = [
            {
                "field": "variables.status",
                "operator": "invalid_op",
                "value": "active"
            }
        ]
        errors = await validation_service.validate_condition_logic(invalid_conditions)
        assert len(errors) > 0
        
        # Type mismatch
        type_mismatch = [
            {
                "field": "variables.count",
                "operator": ConditionOperator.CONTAINS,  # String operator on number
                "value": "text"
            }
        ]
        errors = await validation_service.validate_condition_logic(type_mismatch)
        assert len(errors) == 0  # Should allow, as type checking is runtime


class TestWorkflowDesignerService:
    """Test workflow designer service functionality"""
    
    @pytest.fixture
    async def designer_service(self, test_db: AsyncSession):
        """Create designer service instance"""
        return WorkflowDesignerService(test_db)
    
    @pytest.mark.asyncio
    async def test_create_workflow_from_template(self, designer_service):
        """Test creating workflow from template"""
        template = {
            "name": "Media Processing Template",
            "description": "Standard media processing workflow",
            "tasks": [
                {
                    "task_id": "extract",
                    "task_type": TaskType.EXTRACT_METADATA,
                    "name": "Extract Metadata",
                    "parameters": {"file_path": "$variables.input_file"}
                },
                {
                    "task_id": "transcode",
                    "task_type": TaskType.TRANSCODE,
                    "name": "Transcode Video",
                    "parameters": {
                        "input_file": "$variables.input_file",
                        "output_file": "$variables.output_file",
                        "codec": "h264"
                    }
                }
            ],
            "variables": {
                "input_file": "",
                "output_file": ""
            }
        }
        
        workflow = await designer_service.create_workflow_from_template(
            template,
            name="My Media Workflow",
            variables={
                "input_file": "/my/input.mov",
                "output_file": "/my/output.mp4"
            }
        )
        
        assert workflow.name == "My Media Workflow"
        assert len(workflow.tasks) == 2
        assert workflow.variables["input_file"] == "/my/input.mov"
    
    @pytest.mark.asyncio
    async def test_optimize_workflow(self, designer_service):
        """Test workflow optimization"""
        # Workflow with redundant tasks
        tasks = [
            {
                "task_id": "wait-1",
                "task_type": TaskType.WAIT,
                "name": "Wait 5s",
                "parameters": {"seconds": 5}
            },
            {
                "task_id": "wait-2",
                "task_type": TaskType.WAIT,
                "name": "Wait 3s",
                "parameters": {"seconds": 3}
            },
            {
                "task_id": "process",
                "task_type": TaskType.TRANSCODE,
                "name": "Process",
                "parameters": {
                    "input_file": "/input.mp4",
                    "output_file": "/output.mp4"
                }
            }
        ]
        
        optimized_tasks = await designer_service.optimize_workflow(tasks)
        
        # Should combine consecutive wait tasks
        assert len(optimized_tasks) <= len(tasks)
    
    @pytest.mark.asyncio
    async def test_suggest_task_improvements(self, designer_service):
        """Test task improvement suggestions"""
        task = TaskConfig(
            task_id="email-task",
            task_type=TaskType.SEND_EMAIL,
            name="Send Email",
            parameters={
                "to": ["user@example.com"],
                "subject": "Notification",
                "body": "Task completed"
            },
            retry_count=0,  # No retries
            timeout=300
        )
        
        suggestions = await designer_service.suggest_task_improvements(task)
        
        # Should suggest adding retries for email tasks
        assert any("retry" in s.lower() for s in suggestions)
    
    @pytest.mark.asyncio
    async def test_generate_workflow_diagram(self, designer_service):
        """Test workflow diagram generation"""
        tasks = [
            {
                "task_id": "start",
                "task_type": TaskType.WAIT,
                "name": "Start",
                "parameters": {"seconds": 1}
            },
            {
                "task_id": "condition",
                "task_type": TaskType.CONDITION,
                "name": "Check Status",
                "conditions": [{"field": "status", "operator": "equals", "value": "ok"}],
                "then_tasks": [{
                    "task_id": "success",
                    "task_type": TaskType.SEND_NOTIFICATION,
                    "name": "Notify Success",
                    "parameters": {"message": "Success"}
                }],
                "else_tasks": [{
                    "task_id": "failure",
                    "task_type": TaskType.SEND_EMAIL,
                    "name": "Email Failure",
                    "parameters": {"to": ["admin@example.com"]}
                }]
            }
        ]
        
        diagram = await designer_service.generate_workflow_diagram(tasks)
        
        # Should generate some form of diagram representation
        assert diagram is not None
        assert "start" in str(diagram)
        assert "condition" in str(diagram)
    
    @pytest.mark.asyncio
    async def test_estimate_workflow_duration(self, designer_service):
        """Test workflow duration estimation"""
        tasks = [
            {
                "task_id": "wait-1",
                "task_type": TaskType.WAIT,
                "name": "Wait",
                "parameters": {"seconds": 10}
            },
            {
                "task_id": "transcode",
                "task_type": TaskType.TRANSCODE,
                "name": "Transcode",
                "parameters": {
                    "input_file": "/video.mp4",
                    "output_file": "/output.mp4"
                }
            },
            {
                "task_id": "parallel",
                "task_type": TaskType.PARALLEL,
                "name": "Parallel Tasks",
                "tasks": [
                    {
                        "task_id": "email",
                        "task_type": TaskType.SEND_EMAIL,
                        "name": "Email",
                        "parameters": {"to": ["user@example.com"]}
                    },
                    {
                        "task_id": "notify",
                        "task_type": TaskType.SEND_NOTIFICATION,
                        "name": "Notify",
                        "parameters": {"message": "Done"}
                    }
                ],
                "wait_for_all": True
            }
        ]
        
        estimation = await designer_service.estimate_workflow_duration(tasks)
        
        assert estimation["minimum_duration"] > 0
        assert estimation["average_duration"] >= estimation["minimum_duration"]
        assert estimation["maximum_duration"] >= estimation["average_duration"]
        assert "breakdown" in estimation
    
    @pytest.mark.asyncio
    async def test_validate_and_fix_workflow(self, designer_service):
        """Test workflow validation and auto-fix"""
        # Workflow with issues
        workflow = {
            "name": "",  # Empty name
            "tasks": [
                {
                    "task_id": "task-1",
                    "task_type": TaskType.SEND_EMAIL,
                    "name": "Email",
                    "parameters": {
                        "to": ["invalid-email"],  # Invalid email
                        "subject": "",  # Empty subject
                        "body": "Test"
                    },
                    "retry_count": 0  # No retries
                },
                {
                    "task_id": "task-2",
                    "task_type": TaskType.API_CALL,
                    "name": "API Call",
                    "parameters": {
                        "endpoint": "http://api.example.com",
                        "method": "GET"
                    },
                    "timeout": 5  # Very short timeout
                }
            ]
        }
        
        fixed_workflow, issues = await designer_service.validate_and_fix_workflow(workflow)
        
        assert fixed_workflow["name"] != ""  # Should generate name
        assert fixed_workflow["tasks"][0]["retry_count"] > 0  # Should add retries
        assert fixed_workflow["tasks"][1]["timeout"] > 5  # Should increase timeout
        assert len(issues) > 0  # Should report issues found