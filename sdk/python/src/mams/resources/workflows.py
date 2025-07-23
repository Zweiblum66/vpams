"""
Workflows resource implementation
"""

from typing import Optional, Dict, Any, List
from ..resources.base import BaseResource
from ..models import Workflow, WorkflowCreate, WorkflowUpdate


class WorkflowsResource(BaseResource[Workflow]):
    """Workflows API resource"""
    
    def __init__(self, client):
        super().__init__(client)
        self.resource_name = "workflows"
        self.model_class = Workflow
    
    def start_workflow(
        self,
        workflow_id: str,
        context: Dict[str, Any],
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """Start workflow execution
        
        Args:
            workflow_id: Workflow ID
            context: Workflow context data
            priority: Execution priority (low, normal, high, urgent)
        
        Returns:
            Workflow execution object
        """
        data = {
            "context": context,
            "priority": priority
        }
        
        response = self._make_request(
            "POST",
            self._get_path(workflow_id, "start"),
            json=data
        )
        
        return response.get("data", {})
    
    def get_executions(
        self,
        workflow_id: Optional[str] = None,
        status: Optional[str] = None,
        **filters
    ) -> List[Dict[str, Any]]:
        """Get workflow executions
        
        Args:
            workflow_id: Optional workflow ID filter
            status: Optional status filter
            **filters: Additional filters
        
        Returns:
            List of workflow executions
        """
        params = filters.copy()
        
        if workflow_id:
            params["workflow_id"] = workflow_id
        
        if status:
            params["status"] = status
        
        response = self._make_request(
            "GET",
            self._get_path("executions"),
            params=params
        )
        
        return response.get("data", [])
    
    def get_execution(self, execution_id: str) -> Dict[str, Any]:
        """Get workflow execution details
        
        Args:
            execution_id: Execution ID
        
        Returns:
            Execution details
        """
        response = self._make_request(
            "GET",
            self._get_path("executions", execution_id)
        )
        
        return response.get("data", {})
    
    def cancel_execution(self, execution_id: str) -> bool:
        """Cancel workflow execution
        
        Args:
            execution_id: Execution ID
        
        Returns:
            True if successful
        """
        self._make_request(
            "POST",
            self._get_path("executions", execution_id, "cancel")
        )
        return True
    
    def retry_execution(
        self,
        execution_id: str,
        from_step: Optional[str] = None
    ) -> Dict[str, Any]:
        """Retry failed workflow execution
        
        Args:
            execution_id: Execution ID
            from_step: Optional step to retry from
        
        Returns:
            New execution object
        """
        data = {}
        if from_step:
            data["from_step"] = from_step
        
        response = self._make_request(
            "POST",
            self._get_path("executions", execution_id, "retry"),
            json=data
        )
        
        return response.get("data", {})
    
    def get_steps(self, execution_id: str) -> List[Dict[str, Any]]:
        """Get workflow execution steps
        
        Args:
            execution_id: Execution ID
        
        Returns:
            List of execution steps
        """
        response = self._make_request(
            "GET",
            self._get_path("executions", execution_id, "steps")
        )
        
        return response.get("data", [])
    
    def get_step_logs(
        self,
        execution_id: str,
        step_id: str
    ) -> List[str]:
        """Get step execution logs
        
        Args:
            execution_id: Execution ID
            step_id: Step ID
        
        Returns:
            List of log entries
        """
        response = self._make_request(
            "GET",
            self._get_path("executions", execution_id, "steps", step_id, "logs")
        )
        
        return response.get("data", [])
    
    def approve_step(
        self,
        execution_id: str,
        step_id: str,
        comment: Optional[str] = None
    ) -> bool:
        """Approve pending workflow step
        
        Args:
            execution_id: Execution ID
            step_id: Step ID
            comment: Optional approval comment
        
        Returns:
            True if successful
        """
        data = {"action": "approve"}
        if comment:
            data["comment"] = comment
        
        self._make_request(
            "POST",
            self._get_path("executions", execution_id, "steps", step_id, "action"),
            json=data
        )
        return True
    
    def reject_step(
        self,
        execution_id: str,
        step_id: str,
        comment: Optional[str] = None
    ) -> bool:
        """Reject pending workflow step
        
        Args:
            execution_id: Execution ID
            step_id: Step ID
            comment: Optional rejection comment
        
        Returns:
            True if successful
        """
        data = {"action": "reject"}
        if comment:
            data["comment"] = comment
        
        self._make_request(
            "POST",
            self._get_path("executions", execution_id, "steps", step_id, "action"),
            json=data
        )
        return True
    
    def get_templates(self) -> List[Dict[str, Any]]:
        """Get workflow templates
        
        Returns:
            List of workflow templates
        """
        response = self._make_request(
            "GET",
            self._get_path("templates")
        )
        
        return response.get("data", [])
    
    def create_from_template(
        self,
        template_id: str,
        name: str,
        description: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Workflow:
        """Create workflow from template
        
        Args:
            template_id: Template ID
            name: Workflow name
            description: Optional description
            parameters: Optional template parameters
        
        Returns:
            Created workflow
        """
        data = {
            "template_id": template_id,
            "name": name
        }
        
        if description:
            data["description"] = description
        
        if parameters:
            data["parameters"] = parameters
        
        response = self._make_request(
            "POST",
            self._get_path("from-template"),
            json=data
        )
        
        return self._parse_response(response)
    
    def validate_workflow(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate workflow definition
        
        Args:
            workflow_data: Workflow definition
        
        Returns:
            Validation result
        """
        response = self._make_request(
            "POST",
            self._get_path("validate"),
            json=workflow_data
        )
        
        return response.get("data", {})
    
    def get_metrics(
        self,
        workflow_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get workflow execution metrics
        
        Args:
            workflow_id: Optional workflow ID filter
            start_date: Optional start date (ISO format)
            end_date: Optional end date (ISO format)
        
        Returns:
            Metrics data
        """
        params = {}
        
        if workflow_id:
            params["workflow_id"] = workflow_id
        
        if start_date:
            params["start_date"] = start_date
        
        if end_date:
            params["end_date"] = end_date
        
        response = self._make_request(
            "GET",
            self._get_path("metrics"),
            params=params
        )
        
        return response.get("data", {})