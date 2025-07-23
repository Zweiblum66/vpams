"""
Integrations resource implementation
"""

from typing import Optional, Dict, Any, List
from ..resources.base import BaseResource
from ..models import Integration, IntegrationCreate, IntegrationUpdate


class IntegrationsResource(BaseResource[Integration]):
    """Integrations API resource"""
    
    def __init__(self, client):
        super().__init__(client)
        self.resource_name = "integrations"
        self.model_class = Integration
    
    def get_types(self) -> List[Dict[str, Any]]:
        """Get available integration types
        
        Returns:
            List of integration types
        """
        response = self._make_request(
            "GET",
            self._get_path("types")
        )
        
        return response.get("data", [])
    
    def test_connection(self, integration_id: str) -> Dict[str, Any]:
        """Test integration connection
        
        Args:
            integration_id: Integration ID
        
        Returns:
            Connection test result
        """
        response = self._make_request(
            "POST",
            self._get_path(integration_id, "test")
        )
        
        return response.get("data", {})
    
    def enable(self, integration_id: str) -> bool:
        """Enable integration
        
        Args:
            integration_id: Integration ID
        
        Returns:
            True if successful
        """
        self._make_request(
            "POST",
            self._get_path(integration_id, "enable")
        )
        return True
    
    def disable(self, integration_id: str) -> bool:
        """Disable integration
        
        Args:
            integration_id: Integration ID
        
        Returns:
            True if successful
        """
        self._make_request(
            "POST",
            self._get_path(integration_id, "disable")
        )
        return True
    
    def sync(
        self,
        integration_id: str,
        full_sync: bool = False
    ) -> Dict[str, Any]:
        """Trigger integration sync
        
        Args:
            integration_id: Integration ID
            full_sync: Whether to perform full sync
        
        Returns:
            Sync job information
        """
        data = {"full_sync": full_sync}
        
        response = self._make_request(
            "POST",
            self._get_path(integration_id, "sync"),
            json=data
        )
        
        return response.get("data", {})
    
    def get_sync_status(
        self,
        integration_id: str,
        sync_id: str
    ) -> Dict[str, Any]:
        """Get sync job status
        
        Args:
            integration_id: Integration ID
            sync_id: Sync job ID
        
        Returns:
            Sync status
        """
        response = self._make_request(
            "GET",
            self._get_path(integration_id, "syncs", sync_id)
        )
        
        return response.get("data", {})
    
    def get_sync_history(
        self,
        integration_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get sync history
        
        Args:
            integration_id: Integration ID
            limit: Results limit
        
        Returns:
            List of sync jobs
        """
        params = {"limit": limit}
        
        response = self._make_request(
            "GET",
            self._get_path(integration_id, "syncs"),
            params=params
        )
        
        return response.get("data", [])
    
    def get_webhooks(self, integration_id: str) -> List[Dict[str, Any]]:
        """Get integration webhooks
        
        Args:
            integration_id: Integration ID
        
        Returns:
            List of webhooks
        """
        response = self._make_request(
            "GET",
            self._get_path(integration_id, "webhooks")
        )
        
        return response.get("data", [])
    
    def create_webhook(
        self,
        integration_id: str,
        url: str,
        events: List[str],
        secret: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Create webhook
        
        Args:
            integration_id: Integration ID
            url: Webhook URL
            events: List of events to subscribe to
            secret: Optional webhook secret
            headers: Optional custom headers
        
        Returns:
            Created webhook
        """
        data = {
            "url": url,
            "events": events
        }
        
        if secret:
            data["secret"] = secret
        
        if headers:
            data["headers"] = headers
        
        response = self._make_request(
            "POST",
            self._get_path(integration_id, "webhooks"),
            json=data
        )
        
        return response.get("data", {})
    
    def update_webhook(
        self,
        integration_id: str,
        webhook_id: str,
        **updates
    ) -> Dict[str, Any]:
        """Update webhook
        
        Args:
            integration_id: Integration ID
            webhook_id: Webhook ID
            **updates: Fields to update
        
        Returns:
            Updated webhook
        """
        response = self._make_request(
            "PATCH",
            self._get_path(integration_id, "webhooks", webhook_id),
            json=updates
        )
        
        return response.get("data", {})
    
    def delete_webhook(
        self,
        integration_id: str,
        webhook_id: str
    ) -> bool:
        """Delete webhook
        
        Args:
            integration_id: Integration ID
            webhook_id: Webhook ID
        
        Returns:
            True if successful
        """
        self._make_request(
            "DELETE",
            self._get_path(integration_id, "webhooks", webhook_id)
        )
        return True
    
    def test_webhook(
        self,
        integration_id: str,
        webhook_id: str,
        event_type: str = "test"
    ) -> Dict[str, Any]:
        """Test webhook delivery
        
        Args:
            integration_id: Integration ID
            webhook_id: Webhook ID
            event_type: Event type to test
        
        Returns:
            Test result
        """
        data = {"event_type": event_type}
        
        response = self._make_request(
            "POST",
            self._get_path(integration_id, "webhooks", webhook_id, "test"),
            json=data
        )
        
        return response.get("data", {})
    
    def get_logs(
        self,
        integration_id: str,
        level: str = "info",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get integration logs
        
        Args:
            integration_id: Integration ID
            level: Log level filter (debug, info, warning, error)
            limit: Results limit
        
        Returns:
            List of log entries
        """
        params = {
            "level": level,
            "limit": limit
        }
        
        response = self._make_request(
            "GET",
            self._get_path(integration_id, "logs"),
            params=params
        )
        
        return response.get("data", [])
    
    def get_metrics(
        self,
        integration_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get integration metrics
        
        Args:
            integration_id: Integration ID
            start_date: Optional start date (ISO format)
            end_date: Optional end date (ISO format)
        
        Returns:
            Metrics data
        """
        params = {}
        
        if start_date:
            params["start_date"] = start_date
        
        if end_date:
            params["end_date"] = end_date
        
        response = self._make_request(
            "GET",
            self._get_path(integration_id, "metrics"),
            params=params
        )
        
        return response.get("data", {})
    
    def get_schema(self, integration_type: str) -> Dict[str, Any]:
        """Get integration configuration schema
        
        Args:
            integration_type: Integration type
        
        Returns:
            Configuration schema
        """
        response = self._make_request(
            "GET",
            self._get_path("types", integration_type, "schema")
        )
        
        return response.get("data", {})