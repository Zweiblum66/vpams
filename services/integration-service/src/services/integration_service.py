"""
Integration service for managing all integrations
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from ..db.models import Integration, IntegrationEvent, IntegrationType as DBIntegrationType
from ..models.schemas import (
    IntegrationCreate, IntegrationUpdate, IntegrationResponse,
    IntegrationTestResponse, IntegrationType, AuthType
)
from ..core.integration_framework import (
    IntegrationConfig, IntegrationRegistry,
    IntegrationEvent as FrameworkEvent, EventType,
    IntegrationType as FrameworkIntegrationType,
    BaseIntegration
)
from ..integrations.slack_integration import SlackIntegration
from ..integrations.teams_integration import TeamsIntegration
from ..integrations.zapier_integration import ZapierIntegration
from ..core.auth import encrypt_data, decrypt_data
import structlog

logger = structlog.get_logger()


class IntegrationService:
    """Service for managing integrations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.registry = IntegrationRegistry()
        
        # Register integration factories
        self.registry.register_factory(
            FrameworkIntegrationType.WEBHOOK,
            lambda config: WebhookIntegration(config)
        )
    
    async def list_integrations(
        self,
        skip: int = 0,
        limit: int = 20,
        integration_type: Optional[str] = None,
        enabled: Optional[bool] = None,
        user_id: Optional[str] = None
    ) -> List[IntegrationResponse]:
        """List integrations with filters"""
        query = select(Integration)
        
        # Apply filters
        filters = []
        if user_id:
            filters.append(Integration.user_id == user_id)
        if integration_type:
            filters.append(Integration.type == integration_type)
        if enabled is not None:
            filters.append(Integration.enabled == enabled)
        
        if filters:
            query = query.where(and_(*filters))
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        integrations = result.scalars().all()
        
        return [
            IntegrationResponse(
                id=i.id,
                name=i.name,
                type=i.type.value,
                description=i.description,
                enabled=i.enabled,
                config=i.config,
                auth_type=i.auth_type or AuthType.NONE,
                auth_config={},  # Don't expose auth config in list
                user_id=i.user_id,
                created_at=i.created_at,
                updated_at=i.updated_at,
                last_used_at=i.last_used_at,
                event_count=i.event_count,
                error_count=i.error_count
            )
            for i in integrations
        ]
    
    async def create_integration(
        self,
        data: IntegrationCreate,
        user_id: str
    ) -> IntegrationResponse:
        """Create a new integration"""
        # Check if name already exists for user
        existing = await self.db.execute(
            select(Integration).where(
                and_(
                    Integration.name == data.name,
                    Integration.user_id == user_id
                )
            )
        )
        if existing.scalar():
            raise ValueError(f"Integration with name '{data.name}' already exists")
        
        # Encrypt sensitive auth config
        encrypted_auth_config = None
        if data.auth_config:
            encrypted_auth_config = encrypt_data(data.auth_config)
        
        # Create database record
        integration = Integration(
            name=data.name,
            type=DBIntegrationType(data.type.value),
            description=data.description,
            enabled=data.enabled,
            config=data.config,
            auth_type=data.auth_type.value if data.auth_type else None,
            auth_config=encrypted_auth_config,
            user_id=user_id
        )
        
        self.db.add(integration)
        await self.db.commit()
        await self.db.refresh(integration)
        
        # Create integration instance in registry
        framework_config = IntegrationConfig(
            name=integration.name,
            type=self._map_integration_type(integration.type),
            enabled=integration.enabled,
            auth_type=self._map_auth_type(data.auth_type),
            auth_config=data.auth_config,
            endpoint=data.config.get("endpoint") if data.config else None,
            headers=data.config.get("headers") if data.config else None,
            custom_config=data.config
        )
        
        # Create the appropriate integration instance
        integration_instance = self._create_integration_instance(data.type, framework_config)
        
        # Initialize and add to registry
        await integration_instance.connect()
        self.registry._integrations[integration.name] = integration_instance
        
        return IntegrationResponse(
            id=integration.id,
            name=integration.name,
            type=integration.type.value,
            description=integration.description,
            enabled=integration.enabled,
            config=integration.config,
            auth_type=data.auth_type,
            auth_config={},  # Don't expose auth config
            user_id=integration.user_id,
            created_at=integration.created_at,
            updated_at=integration.updated_at,
            event_count=0,
            error_count=0
        )
    
    async def get_integration(
        self,
        integration_id: UUID,
        user_id: str
    ) -> Optional[IntegrationResponse]:
        """Get integration details"""
        result = await self.db.execute(
            select(Integration).where(
                and_(
                    Integration.id == integration_id,
                    Integration.user_id == user_id
                )
            )
        )
        integration = result.scalar()
        
        if not integration:
            return None
        
        # Decrypt auth config for response
        auth_config = {}
        if integration.auth_config:
            try:
                auth_config = decrypt_data(integration.auth_config)
            except:
                logger.error(f"Failed to decrypt auth config for integration {integration_id}")
        
        return IntegrationResponse(
            id=integration.id,
            name=integration.name,
            type=integration.type.value,
            description=integration.description,
            enabled=integration.enabled,
            config=integration.config,
            auth_type=AuthType(integration.auth_type) if integration.auth_type else AuthType.NONE,
            auth_config=auth_config,
            user_id=integration.user_id,
            created_at=integration.created_at,
            updated_at=integration.updated_at,
            last_used_at=integration.last_used_at,
            event_count=integration.event_count,
            error_count=integration.error_count
        )
    
    async def update_integration(
        self,
        integration_id: UUID,
        data: IntegrationUpdate,
        user_id: str
    ) -> Optional[IntegrationResponse]:
        """Update an integration"""
        result = await self.db.execute(
            select(Integration).where(
                and_(
                    Integration.id == integration_id,
                    Integration.user_id == user_id
                )
            )
        )
        integration = result.scalar()
        
        if not integration:
            return None
        
        # Update fields
        if data.name is not None:
            # Check if new name already exists
            existing = await self.db.execute(
                select(Integration).where(
                    and_(
                        Integration.name == data.name,
                        Integration.user_id == user_id,
                        Integration.id != integration_id
                    )
                )
            )
            if existing.scalar():
                raise ValueError(f"Integration with name '{data.name}' already exists")
            integration.name = data.name
        
        if data.description is not None:
            integration.description = data.description
        
        if data.enabled is not None:
            integration.enabled = data.enabled
        
        if data.config is not None:
            integration.config = data.config
        
        if data.auth_config is not None:
            integration.auth_config = encrypt_data(data.auth_config)
        
        integration.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(integration)
        
        return await self.get_integration(integration_id, user_id)
    
    async def delete_integration(
        self,
        integration_id: UUID,
        user_id: str
    ) -> bool:
        """Delete an integration"""
        result = await self.db.execute(
            select(Integration).where(
                and_(
                    Integration.id == integration_id,
                    Integration.user_id == user_id
                )
            )
        )
        integration = result.scalar()
        
        if not integration:
            return False
        
        # Remove from registry
        await self.registry.remove_integration(integration.name)
        
        # Delete from database
        await self.db.delete(integration)
        await self.db.commit()
        
        return True
    
    async def test_integration(
        self,
        integration_id: UUID,
        user_id: str
    ) -> Optional[IntegrationTestResponse]:
        """Test an integration connection"""
        integration_data = await self.get_integration(integration_id, user_id)
        
        if not integration_data:
            return None
        
        # Get integration from registry or create temporary one
        integration = self.registry.get_integration(integration_data.name)
        
        if not integration:
            # Create temporary integration for testing
            framework_config = IntegrationConfig(
                name=integration_data.name,
                type=self._map_integration_type(IntegrationType(integration_data.type)),
                enabled=True,
                auth_type=self._map_auth_type(integration_data.auth_type),
                auth_config=integration_data.auth_config,
                endpoint=integration_data.config.get("endpoint") if integration_data.config else None,
                custom_config=integration_data.config
            )
            
            # Create the appropriate integration instance
            integration = self._create_integration_instance(
                IntegrationType(integration_data.type),
                framework_config
            )
        
        # Test the connection
        try:
            success = await integration.test_connection()
            
            return IntegrationTestResponse(
                success=success,
                message="Connection successful" if success else "Connection failed",
                details={
                    "integration_type": integration_data.type,
                    "tested_at": datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            return IntegrationTestResponse(
                success=False,
                message=f"Test failed: {str(e)}",
                details={
                    "error": str(e),
                    "integration_type": integration_data.type
                }
            )
    
    async def enable_integration(
        self,
        integration_id: UUID,
        user_id: str
    ) -> Optional[IntegrationResponse]:
        """Enable an integration"""
        update_data = IntegrationUpdate(enabled=True)
        return await self.update_integration(integration_id, update_data, user_id)
    
    async def disable_integration(
        self,
        integration_id: UUID,
        user_id: str
    ) -> Optional[IntegrationResponse]:
        """Disable an integration"""
        update_data = IntegrationUpdate(enabled=False)
        return await self.update_integration(integration_id, update_data, user_id)
    
    async def get_integration_events(
        self,
        integration_id: UUID,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
        event_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """Get events for an integration"""
        # Verify integration belongs to user
        integration = await self.db.execute(
            select(Integration).where(
                and_(
                    Integration.id == integration_id,
                    Integration.user_id == user_id
                )
            )
        )
        if not integration.scalar():
            return None
        
        # Query events
        query = select(IntegrationEvent).where(
            IntegrationEvent.integration_id == integration_id
        )
        
        if event_type:
            query = query.where(IntegrationEvent.event_type == event_type)
        if status:
            query = query.where(IntegrationEvent.status == status)
        
        query = query.order_by(IntegrationEvent.created_at.desc())
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        events = result.scalars().all()
        
        return [
            {
                "id": event.id,
                "event_type": event.event_type,
                "event_data": event.event_data,
                "status": event.status,
                "attempts": event.attempts,
                "response_status": event.response_status,
                "error_message": event.error_message,
                "created_at": event.created_at,
                "sent_at": event.sent_at,
                "completed_at": event.completed_at
            }
            for event in events
        ]
    
    async def send_event(
        self,
        integration_id: UUID,
        event_type: EventType,
        event_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send an event to an integration"""
        # Get integration
        result = await self.db.execute(
            select(Integration).where(Integration.id == integration_id)
        )
        integration = result.scalar()
        
        if not integration or not integration.enabled:
            return {"success": False, "error": "Integration not found or disabled"}
        
        # Create framework event
        framework_event = FrameworkEvent(
            id=str(UUID()),
            type=event_type,
            source="mams",
            data=event_data,
            metadata=metadata or {}
        )
        
        # Get integration from registry
        integration_instance = self.registry.get_integration(integration.name)
        
        if not integration_instance:
            # Create if not in registry
            framework_config = IntegrationConfig(
                name=integration.name,
                type=self._map_integration_type(integration.type),
                enabled=integration.enabled,
                auth_type=self._map_auth_type(AuthType(integration.auth_type) if integration.auth_type else AuthType.NONE),
                auth_config=decrypt_data(integration.auth_config) if integration.auth_config else {},
                custom_config=integration.config
            )
            # Create the appropriate integration instance
            db_type = IntegrationType(integration.type.value)
            integration_instance = self._create_integration_instance(db_type, framework_config)
            
            # Initialize it
            await integration_instance.connect()
            
            # Add to registry
            self.registry._integrations[integration.name] = integration_instance
        
        # Send event
        response = await integration_instance.send_event(framework_event)
        
        # Log event
        db_event = IntegrationEvent(
            integration_id=integration_id,
            event_type=event_type.value,
            event_data=event_data,
            status="success" if response.success else "failed",
            response_status=response.status_code,
            response_body=json.dumps(response.data) if response.data else None,
            error_message=response.error,
            sent_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        self.db.add(db_event)
        
        # Update integration stats
        integration.last_used_at = datetime.utcnow()
        integration.event_count += 1
        if not response.success:
            integration.error_count += 1
        
        await self.db.commit()
        
        return {
            "success": response.success,
            "integration_id": integration_id,
            "event_id": framework_event.id,
            "response": response.data,
            "error": response.error
        }
    
    def _map_integration_type(self, db_type: DBIntegrationType) -> FrameworkIntegrationType:
        """Map database integration type to framework type"""
        mapping = {
            DBIntegrationType.WEBHOOK: FrameworkIntegrationType.WEBHOOK,
            DBIntegrationType.SLACK: FrameworkIntegrationType.CUSTOM,
            DBIntegrationType.TEAMS: FrameworkIntegrationType.CUSTOM,
            DBIntegrationType.EMAIL: FrameworkIntegrationType.CUSTOM,
            DBIntegrationType.REST_API: FrameworkIntegrationType.REST_API,
            DBIntegrationType.GRAPHQL: FrameworkIntegrationType.GRAPHQL,
            DBIntegrationType.GRPC: FrameworkIntegrationType.GRPC,
            DBIntegrationType.ZAPIER: FrameworkIntegrationType.WEBHOOK,
            DBIntegrationType.CUSTOM: FrameworkIntegrationType.CUSTOM,
        }
        return mapping.get(db_type, FrameworkIntegrationType.CUSTOM)
    
    def _map_auth_type(self, auth_type: AuthType) -> AuthType:
        """Map schema auth type to framework auth type"""
        # They're the same in this case
        return auth_type
    
    def _create_integration_instance(
        self,
        integration_type: IntegrationType,
        config: IntegrationConfig
    ) -> BaseIntegration:
        """Create the appropriate integration instance based on type"""
        if integration_type == IntegrationType.SLACK:
            return SlackIntegration(config)
        elif integration_type == IntegrationType.TEAMS:
            return TeamsIntegration(config)
        elif integration_type == IntegrationType.ZAPIER:
            return ZapierIntegration(config)
        elif integration_type == IntegrationType.WEBHOOK:
            from ..core.integration_framework import WebhookIntegration
            return WebhookIntegration(config)
        else:
            # For other types, try to use the registry
            if config.type in self.registry._factories:
                return self.registry._factories[config.type](config)
            else:
                raise ValueError(f"Unsupported integration type: {integration_type}")