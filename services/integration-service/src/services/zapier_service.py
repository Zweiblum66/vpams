"""
Zapier service implementation
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from ..db.models import Integration, IntegrationType as DBIntegrationType
from ..models.schemas import IntegrationType, AuthType
from ..services.integration_service import IntegrationService
from ..integrations.zapier_integration import ZapierIntegration
from ..core.integration_framework import (
    IntegrationConfig, IntegrationEvent, EventType
)
from ..core.auth import decrypt_data
import structlog

logger = structlog.get_logger()


class ZapierService:
    """Service for managing Zapier integrations"""
    
    def __init__(self, db: Optional[AsyncSession]):
        self.db = db
        if db:
            self.integration_service = IntegrationService(db)
    
    async def handle_incoming_webhook(
        self,
        integration_id: UUID,
        headers: Dict[str, str],
        body: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle incoming webhook from Zapier"""
        if not self.db:
            return {"success": False, "error": "Database not available"}
        
        # Get integration
        result = await self.db.execute(
            select(Integration).where(Integration.id == integration_id)
        )
        integration = result.scalar()
        
        if not integration:
            return {"success": False, "error": "Integration not found"}
        
        # Create Zapier integration instance
        config = IntegrationConfig(
            name=integration.name,
            type=IntegrationType.ZAPIER,
            enabled=integration.enabled,
            auth_type=AuthType(integration.auth_type) if integration.auth_type else AuthType.NONE,
            auth_config=decrypt_data(integration.auth_config) if integration.auth_config else {},
            custom_config=integration.config
        )
        
        zapier = ZapierIntegration(config)
        await zapier.connect()
        
        try:
            result = await zapier.handle_incoming_webhook(headers, body)
            
            # Log the webhook event
            logger.info(
                "Zapier webhook processed",
                integration_id=integration_id,
                action=body.get("action"),
                success=result.get("success")
            )
            
            return result
        except Exception as e:
            logger.error(f"Failed to process Zapier webhook: {e}")
            return {"success": False, "error": str(e)}
        finally:
            await zapier.disconnect()
    
    async def create_trigger(
        self,
        user_id: str,
        event_types: List[str],
        target_url: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a Zapier trigger"""
        # This would typically store trigger in database
        # For now, return mock response
        trigger_id = f"trigger_{datetime.utcnow().timestamp()}"
        
        logger.info(
            "Zapier trigger created",
            trigger_id=trigger_id,
            user_id=user_id,
            event_types=event_types
        )
        
        return {
            "success": True,
            "trigger_id": trigger_id,
            "event_types": event_types,
            "target_url": target_url,
            "created_at": datetime.utcnow().isoformat()
        }
    
    async def list_triggers(self, user_id: str) -> List[Dict[str, Any]]:
        """List all Zapier triggers for a user"""
        # This would fetch from database
        # For now, return empty list
        return []
    
    async def delete_trigger(self, trigger_id: str, user_id: str) -> bool:
        """Delete a Zapier trigger"""
        logger.info(
            "Zapier trigger deleted",
            trigger_id=trigger_id,
            user_id=user_id
        )
        return True
    
    async def get_sample_data(self, event_type: str) -> Optional[Dict[str, Any]]:
        """Get sample data for an event type"""
        samples = {
            "asset.created": {
                "id": "evt_sample_asset_created",
                "type": "asset.created",
                "timestamp": datetime.utcnow().isoformat(),
                "source": "mams",
                "asset_id": "asset_abc123def456",
                "asset_name": "sample_video.mp4",
                "asset_type": "video",
                "file_size": 104857600,
                "file_path": "/storage/videos/2024/01/sample_video.mp4",
                "data_mime_type": "video/mp4",
                "data_duration": 120.5,
                "data_resolution": "1920x1080",
                "data_frame_rate": 30,
                "data_bit_rate": 5000000,
                "data_codec": "h264",
                "meta_project_id": "proj_xyz789",
                "meta_project_name": "Sample Project",
                "meta_uploaded_by": "user@example.com",
                "meta_upload_source": "web_ui",
                "meta_tags": '["sample", "demo", "video"]'
            },
            "asset.updated": {
                "id": "evt_sample_asset_updated",
                "type": "asset.updated",
                "timestamp": datetime.utcnow().isoformat(),
                "source": "mams",
                "asset_id": "asset_abc123def456",
                "asset_name": "sample_video_edited.mp4",
                "changes": '{"name": {"old": "sample_video.mp4", "new": "sample_video_edited.mp4"}}',
                "meta_updated_by": "editor@example.com",
                "meta_update_reason": "Name correction"
            },
            "workflow.completed": {
                "id": "evt_sample_workflow_completed",
                "type": "workflow.completed",
                "timestamp": datetime.utcnow().isoformat(),
                "source": "mams",
                "workflow_id": "wf_transcode_123",
                "workflow_type": "video_transcoding",
                "workflow_result": "success",
                "workflow_duration": 300.5,
                "data_input_asset": "asset_abc123def456",
                "data_output_assets": '["asset_proxy_hd", "asset_proxy_sd", "asset_thumbnail"]',
                "data_profiles": '["1080p", "720p", "thumbnail"]',
                "meta_triggered_by": "auto",
                "meta_priority": "normal"
            },
            "project.created": {
                "id": "evt_sample_project_created",
                "type": "project.created",
                "timestamp": datetime.utcnow().isoformat(),
                "source": "mams",
                "project_id": "proj_new123",
                "project_name": "New Documentary Project",
                "project_description": "A documentary about technology",
                "data_type": "documentary",
                "data_expected_duration": 3600,
                "data_deadline": "2024-12-31",
                "meta_created_by": "producer@example.com",
                "meta_team_size": 5,
                "meta_budget": 50000
            }
        }
        
        return samples.get(event_type)
    
    async def test_integration(
        self,
        integration_id: UUID,
        user_id: str,
        test_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Test Zapier integration"""
        if not self.db:
            return {"success": False, "error": "Database not available"}
        
        # Get integration
        integration_data = await self.integration_service.get_integration(
            integration_id, user_id
        )
        
        if not integration_data:
            return {"success": False, "error": "Integration not found"}
        
        # Create test event
        test_event = IntegrationEvent(
            id=f"test_{datetime.utcnow().timestamp()}",
            type=EventType.CUSTOM,
            source="zapier-test",
            data=test_data or {
                "test": True,
                "timestamp": datetime.utcnow().isoformat(),
                "message": "This is a test event from MAMS"
            }
        )
        
        # Send test event
        result = await self.integration_service.send_event(
            integration_id=integration_id,
            event_type=test_event.type,
            event_data=test_event.data,
            metadata=test_event.metadata
        )
        
        return result
    
    async def verify_api_key(self, api_key: str) -> bool:
        """Verify Zapier API key"""
        if not self.db:
            return False
        
        # Check if API key belongs to any integration
        # This would typically check against a dedicated API keys table
        # For now, check if any Zapier integration has this API key
        result = await self.db.execute(
            select(Integration).where(
                and_(
                    Integration.type == DBIntegrationType.ZAPIER,
                    Integration.enabled == True
                )
            )
        )
        integrations = result.scalars().all()
        
        for integration in integrations:
            if integration.auth_config:
                try:
                    auth_config = decrypt_data(integration.auth_config)
                    if auth_config.get("api_key") == api_key:
                        return True
                except:
                    continue
        
        return False
    
    async def search_assets(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search assets for Zapier"""
        # This would integrate with the asset service
        # For now, return mock data
        search_term = query.get("search", "")
        asset_type = query.get("type", "all")
        
        mock_assets = [
            {
                "id": "asset_search_result_1",
                "name": f"Video matching '{search_term}'",
                "type": "video",
                "created_at": datetime.utcnow().isoformat(),
                "file_size": 52428800,
                "duration": 60.0,
                "tags": ["search", "result", "video"]
            },
            {
                "id": "asset_search_result_2",
                "name": f"Image matching '{search_term}'",
                "type": "image",
                "created_at": datetime.utcnow().isoformat(),
                "file_size": 2097152,
                "resolution": "1920x1080",
                "tags": ["search", "result", "image"]
            }
        ]
        
        # Filter by type if specified
        if asset_type != "all":
            mock_assets = [a for a in mock_assets if a["type"] == asset_type]
        
        return mock_assets[:10]  # Zapier typically expects max 10 results
    
    async def search_projects(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search projects for Zapier"""
        # This would integrate with the project service
        # For now, return mock data
        search_term = query.get("search", "")
        status = query.get("status", "all")
        
        mock_projects = [
            {
                "id": "proj_search_result_1",
                "name": f"Project matching '{search_term}'",
                "description": "A sample project for Zapier integration",
                "status": "active",
                "created_at": datetime.utcnow().isoformat(),
                "asset_count": 42,
                "team_size": 5
            },
            {
                "id": "proj_search_result_2",
                "name": f"Another project with '{search_term}'",
                "description": "Another sample project",
                "status": "completed",
                "created_at": datetime.utcnow().isoformat(),
                "asset_count": 128,
                "team_size": 8
            }
        ]
        
        # Filter by status if specified
        if status != "all":
            mock_projects = [p for p in mock_projects if p["status"] == status]
        
        return mock_projects[:10]
    
    async def create_asset(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create asset from Zapier"""
        # This would integrate with the asset service
        # For now, return mock response
        asset_id = f"asset_created_{datetime.utcnow().timestamp()}"
        
        return {
            "success": True,
            "asset": {
                "id": asset_id,
                "name": data.get("name", "Untitled Asset"),
                "type": data.get("type", "unknown"),
                "created_at": datetime.utcnow().isoformat(),
                "source": "zapier",
                "metadata": data.get("metadata", {})
            }
        }
    
    async def update_asset_metadata(
        self,
        asset_id: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update asset metadata from Zapier"""
        # This would integrate with the metadata service
        # For now, return mock response
        return {
            "success": True,
            "asset_id": asset_id,
            "updated_fields": list(metadata.keys()),
            "updated_at": datetime.utcnow().isoformat()
        }
    
    async def send_event_to_zapier(
        self,
        event: IntegrationEvent,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Send an event to all active Zapier integrations"""
        if not self.db:
            return []
        
        # Get all active Zapier integrations
        query = select(Integration).where(
            and_(
                Integration.type == DBIntegrationType.ZAPIER,
                Integration.enabled == True
            )
        )
        
        if user_id:
            query = query.where(Integration.user_id == user_id)
        
        result = await self.db.execute(query)
        integrations = result.scalars().all()
        
        results = []
        
        for integration in integrations:
            try:
                # Send event via integration service
                result = await self.integration_service.send_event(
                    integration_id=integration.id,
                    event_type=event.type,
                    event_data=event.data,
                    metadata=event.metadata
                )
                
                results.append({
                    "integration_id": str(integration.id),
                    "integration_name": integration.name,
                    "success": result.get("success", False),
                    "error": result.get("error")
                })
                
            except Exception as e:
                logger.error(
                    f"Failed to send event to Zapier integration {integration.id}: {e}"
                )
                results.append({
                    "integration_id": str(integration.id),
                    "integration_name": integration.name,
                    "success": False,
                    "error": str(e)
                })
        
        return results