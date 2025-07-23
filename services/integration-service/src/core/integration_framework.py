"""
Core integration framework for MAMS

This module provides the foundation for building integrations with external systems.
It includes base classes, interfaces, and utilities for creating robust integrations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable, TypeVar, Generic
from datetime import datetime
from enum import Enum
import asyncio
import httpx
import json
from pydantic import BaseModel, Field
import structlog
from dataclasses import dataclass
from contextlib import asynccontextmanager

logger = structlog.get_logger()

T = TypeVar('T')


class IntegrationType(str, Enum):
    """Types of integrations supported"""
    WEBHOOK = "webhook"
    REST_API = "rest_api"
    GRAPHQL = "graphql"
    GRPC = "grpc"
    WEBSOCKET = "websocket"
    MESSAGE_QUEUE = "message_queue"
    DATABASE = "database"
    FILE_SYNC = "file_sync"


class IntegrationStatus(str, Enum):
    """Integration connection status"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    AUTHENTICATING = "authenticating"
    RATE_LIMITED = "rate_limited"


class AuthType(str, Enum):
    """Authentication types"""
    NONE = "none"
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    OAUTH2 = "oauth2"
    BASIC = "basic"
    CUSTOM = "custom"


class EventType(str, Enum):
    """Integration event types"""
    ASSET_CREATED = "asset.created"
    ASSET_UPDATED = "asset.updated"
    ASSET_DELETED = "asset.deleted"
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    PROJECT_CREATED = "project.created"
    PROJECT_UPDATED = "project.updated"
    CUSTOM = "custom"


@dataclass
class IntegrationConfig:
    """Configuration for an integration"""
    name: str
    type: IntegrationType
    enabled: bool = True
    auth_type: AuthType = AuthType.NONE
    auth_config: Dict[str, Any] = None
    endpoint: Optional[str] = None
    headers: Dict[str, str] = None
    timeout: int = 30
    retry_count: int = 3
    retry_delay: int = 1
    rate_limit: Optional[int] = None  # requests per minute
    custom_config: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.auth_config is None:
            self.auth_config = {}
        if self.headers is None:
            self.headers = {}
        if self.custom_config is None:
            self.custom_config = {}


class IntegrationEvent(BaseModel):
    """Event that triggers an integration"""
    id: str
    type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: str
    data: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IntegrationResponse(BaseModel):
    """Response from an integration"""
    success: bool
    status_code: Optional[int] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    duration_ms: Optional[float] = None


class RateLimiter:
    """Simple rate limiter for integrations"""
    
    def __init__(self, rate: int, per_minutes: int = 1):
        self.rate = rate
        self.per_minutes = per_minutes
        self.calls = []
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Wait if necessary to respect rate limit"""
        async with self._lock:
            now = datetime.utcnow()
            cutoff = now.timestamp() - (self.per_minutes * 60)
            
            # Remove old calls
            self.calls = [call for call in self.calls if call > cutoff]
            
            if len(self.calls) >= self.rate:
                # Calculate wait time
                oldest_call = min(self.calls)
                wait_time = (oldest_call + (self.per_minutes * 60)) - now.timestamp()
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                    # Retry after waiting
                    return await self.acquire()
            
            self.calls.append(now.timestamp())


class BaseIntegration(ABC, Generic[T]):
    """Base class for all integrations"""
    
    def __init__(self, config: IntegrationConfig):
        self.config = config
        self.status = IntegrationStatus.DISCONNECTED
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limiter: Optional[RateLimiter] = None
        
        if config.rate_limit:
            self._rate_limiter = RateLimiter(config.rate_limit)
    
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the external system"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the external system"""
        pass
    
    @abstractmethod
    async def send_event(self, event: IntegrationEvent) -> IntegrationResponse:
        """Send an event to the external system"""
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """Test if the connection is working"""
        pass
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers based on auth type"""
        headers = self.config.headers.copy()
        
        if self.config.auth_type == AuthType.API_KEY:
            key_header = self.config.auth_config.get("header_name", "X-API-Key")
            headers[key_header] = self.config.auth_config.get("api_key", "")
        
        elif self.config.auth_type == AuthType.BEARER_TOKEN:
            headers["Authorization"] = f"Bearer {self.config.auth_config.get('token', '')}"
        
        elif self.config.auth_type == AuthType.BASIC:
            import base64
            username = self.config.auth_config.get("username", "")
            password = self.config.auth_config.get("password", "")
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"
        
        return headers
    
    async def _make_request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """Make an HTTP request with retry logic"""
        if self._rate_limiter:
            await self._rate_limiter.acquire()
        
        if not self._client:
            self._client = httpx.AsyncClient(timeout=self.config.timeout)
        
        headers = self._get_auth_headers()
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))
        
        last_error = None
        for attempt in range(self.config.retry_count):
            try:
                response = await self._client.request(
                    method,
                    url,
                    headers=headers,
                    **kwargs
                )
                
                if response.status_code == 429:  # Rate limited
                    self.status = IntegrationStatus.RATE_LIMITED
                    retry_after = int(response.headers.get("Retry-After", 60))
                    await asyncio.sleep(retry_after)
                    continue
                
                return response
                
            except Exception as e:
                last_error = e
                if attempt < self.config.retry_count - 1:
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                    continue
                raise
        
        raise last_error


class WebhookIntegration(BaseIntegration[httpx.Response]):
    """Integration for sending webhooks"""
    
    async def connect(self) -> bool:
        """Initialize HTTP client"""
        try:
            self._client = httpx.AsyncClient(timeout=self.config.timeout)
            self.status = IntegrationStatus.CONNECTED
            return True
        except Exception as e:
            logger.error(f"Failed to create HTTP client: {e}")
            self.status = IntegrationStatus.ERROR
            return False
    
    async def disconnect(self) -> None:
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None
        self.status = IntegrationStatus.DISCONNECTED
    
    async def send_event(self, event: IntegrationEvent) -> IntegrationResponse:
        """Send webhook event"""
        start_time = datetime.utcnow()
        
        try:
            response = await self._make_request(
                "POST",
                self.config.endpoint,
                json={
                    "event_id": event.id,
                    "event_type": event.type.value,
                    "timestamp": event.timestamp.isoformat(),
                    "source": event.source,
                    "data": event.data,
                    "metadata": event.metadata
                }
            )
            
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return IntegrationResponse(
                success=response.status_code < 400,
                status_code=response.status_code,
                data=response.json() if response.headers.get("content-type", "").startswith("application/json") else None,
                duration_ms=duration_ms
            )
            
        except Exception as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"Webhook failed: {e}")
            return IntegrationResponse(
                success=False,
                error=str(e),
                duration_ms=duration_ms
            )
    
    async def test_connection(self) -> bool:
        """Test webhook endpoint"""
        try:
            # Send a test event
            test_event = IntegrationEvent(
                id="test",
                type=EventType.CUSTOM,
                source="integration-test",
                data={"test": True}
            )
            
            response = await self.send_event(test_event)
            return response.success
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False


class IntegrationRegistry:
    """Registry for managing integrations"""
    
    def __init__(self):
        self._integrations: Dict[str, BaseIntegration] = {}
        self._factories: Dict[IntegrationType, Callable[[IntegrationConfig], BaseIntegration]] = {
            IntegrationType.WEBHOOK: WebhookIntegration,
        }
    
    def register_factory(
        self,
        integration_type: IntegrationType,
        factory: Callable[[IntegrationConfig], BaseIntegration]
    ):
        """Register a factory for creating integrations"""
        self._factories[integration_type] = factory
    
    async def add_integration(self, config: IntegrationConfig) -> BaseIntegration:
        """Add and initialize an integration"""
        if config.type not in self._factories:
            raise ValueError(f"No factory registered for integration type: {config.type}")
        
        factory = self._factories[config.type]
        integration = factory(config)
        
        if config.enabled:
            await integration.connect()
        
        self._integrations[config.name] = integration
        return integration
    
    def get_integration(self, name: str) -> Optional[BaseIntegration]:
        """Get an integration by name"""
        return self._integrations.get(name)
    
    async def remove_integration(self, name: str) -> bool:
        """Remove and disconnect an integration"""
        integration = self._integrations.get(name)
        if integration:
            await integration.disconnect()
            del self._integrations[name]
            return True
        return False
    
    async def broadcast_event(
        self,
        event: IntegrationEvent,
        integration_names: Optional[List[str]] = None
    ) -> Dict[str, IntegrationResponse]:
        """Broadcast an event to multiple integrations"""
        responses = {}
        
        integrations = self._integrations.items()
        if integration_names:
            integrations = [
                (name, intg) for name, intg in integrations
                if name in integration_names
            ]
        
        # Send events concurrently
        tasks = []
        for name, integration in integrations:
            if integration.config.enabled and integration.status == IntegrationStatus.CONNECTED:
                tasks.append((name, integration.send_event(event)))
        
        if tasks:
            results = await asyncio.gather(
                *[task[1] for task in tasks],
                return_exceptions=True
            )
            
            for (name, _), result in zip(tasks, results):
                if isinstance(result, Exception):
                    responses[name] = IntegrationResponse(
                        success=False,
                        error=str(result)
                    )
                else:
                    responses[name] = result
        
        return responses
    
    async def close_all(self):
        """Disconnect all integrations"""
        tasks = [
            integration.disconnect()
            for integration in self._integrations.values()
        ]
        await asyncio.gather(*tasks, return_exceptions=True)