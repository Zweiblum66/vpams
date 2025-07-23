"""
Base Plugin Architecture for MAMS
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
from datetime import datetime
import asyncio
import inspect
from dataclasses import dataclass
import uuid


class PluginType(Enum):
    """Types of plugins supported by MAMS"""
    INGEST = "ingest"
    PROCESSOR = "processor"
    STORAGE = "storage"
    METADATA = "metadata"
    WORKFLOW = "workflow"
    SEARCH = "search"
    EXPORT = "export"
    ANALYTICS = "analytics"
    AUTHENTICATION = "authentication"
    NOTIFICATION = "notification"
    UI_COMPONENT = "ui_component"
    API_EXTENSION = "api_extension"


class PluginStatus(Enum):
    """Plugin lifecycle status"""
    INSTALLED = "installed"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"
    UPDATING = "updating"
    UNINSTALLED = "uninstalled"


class PluginCapability(Enum):
    """Plugin capabilities/permissions"""
    READ_ASSETS = "read_assets"
    WRITE_ASSETS = "write_assets"
    DELETE_ASSETS = "delete_assets"
    READ_METADATA = "read_metadata"
    WRITE_METADATA = "write_metadata"
    EXECUTE_WORKFLOWS = "execute_workflows"
    ACCESS_STORAGE = "access_storage"
    SEND_NOTIFICATIONS = "send_notifications"
    ACCESS_ANALYTICS = "access_analytics"
    MODIFY_SETTINGS = "modify_settings"
    ACCESS_USER_DATA = "access_user_data"
    REGISTER_WEBHOOKS = "register_webhooks"


@dataclass
class PluginMetadata:
    """Plugin metadata information"""
    id: str
    name: str
    version: str
    description: str
    author: str
    author_email: str
    homepage: Optional[str] = None
    documentation_url: Optional[str] = None
    icon_url: Optional[str] = None
    license: str = "Proprietary"
    min_mams_version: str = "1.0.0"
    max_mams_version: Optional[str] = None
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.utcnow()
        if not self.updated_at:
            self.updated_at = datetime.utcnow()


@dataclass
class PluginConfig:
    """Plugin configuration"""
    enabled: bool = True
    settings: Dict[str, Any] = None
    capabilities: List[PluginCapability] = None
    api_key: Optional[str] = None
    webhook_url: Optional[str] = None
    rate_limit: Optional[int] = None  # Requests per minute
    timeout: int = 30  # Seconds
    retry_count: int = 3
    priority: int = 0  # Higher priority plugins execute first
    
    def __post_init__(self):
        if self.settings is None:
            self.settings = {}
        if self.capabilities is None:
            self.capabilities = []


class PluginHook:
    """Decorator for plugin hook methods"""
    def __init__(self, hook_name: str, priority: int = 0):
        self.hook_name = hook_name
        self.priority = priority
    
    def __call__(self, func):
        func._plugin_hook = self.hook_name
        func._hook_priority = self.priority
        return func


class PluginEvent:
    """Base class for plugin events"""
    def __init__(self, event_type: str, data: Dict[str, Any]):
        self.event_type = event_type
        self.data = data
        self.timestamp = datetime.utcnow()
        self.event_id = str(uuid.uuid4())


class PluginContext:
    """Context passed to plugin methods"""
    def __init__(
        self,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        request_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.request_id = request_id or str(uuid.uuid4())
        self.metadata = metadata or {}
        self.start_time = datetime.utcnow()


class PluginResult:
    """Result returned by plugin methods"""
    def __init__(
        self,
        success: bool,
        data: Any = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.success = success
        self.data = data
        self.error = error
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()


class PluginInterface(ABC):
    """Base interface that all plugins must implement"""
    
    def __init__(self, metadata: PluginMetadata, config: PluginConfig):
        self.metadata = metadata
        self.config = config
        self.status = PluginStatus.INSTALLED
        self._hooks: Dict[str, List[Callable]] = {}
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._discover_hooks()
    
    @abstractmethod
    def get_type(self) -> PluginType:
        """Return the plugin type"""
        pass
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the plugin"""
        pass
    
    @abstractmethod
    async def shutdown(self) -> bool:
        """Cleanup plugin resources"""
        pass
    
    @abstractmethod
    async def validate_config(self) -> bool:
        """Validate plugin configuration"""
        pass
    
    @abstractmethod
    def get_health_status(self) -> Dict[str, Any]:
        """Get plugin health status"""
        pass
    
    def _discover_hooks(self):
        """Discover methods decorated with @PluginHook"""
        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if hasattr(method, '_plugin_hook'):
                hook_name = method._plugin_hook
                priority = method._hook_priority
                if hook_name not in self._hooks:
                    self._hooks[hook_name] = []
                self._hooks[hook_name].append((priority, method))
        
        # Sort hooks by priority
        for hook_name in self._hooks:
            self._hooks[hook_name].sort(key=lambda x: x[0], reverse=True)
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register an event handler"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
    
    async def handle_event(self, event: PluginEvent) -> List[PluginResult]:
        """Handle an event"""
        results = []
        handlers = self._event_handlers.get(event.event_type, [])
        
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(event)
                else:
                    result = handler(event)
                results.append(result)
            except Exception as e:
                results.append(PluginResult(
                    success=False,
                    error=str(e)
                ))
        
        return results
    
    async def execute_hook(self, hook_name: str, context: PluginContext, **kwargs) -> PluginResult:
        """Execute a hook"""
        hooks = self._hooks.get(hook_name, [])
        
        for priority, hook_method in hooks:
            try:
                result = await hook_method(context, **kwargs)
                if not result.success:
                    return result
            except Exception as e:
                return PluginResult(
                    success=False,
                    error=str(e)
                )
        
        return PluginResult(success=True)
    
    def has_capability(self, capability: PluginCapability) -> bool:
        """Check if plugin has a specific capability"""
        return capability in self.config.capabilities
    
    def get_settings_schema(self) -> Dict[str, Any]:
        """Get JSON schema for plugin settings"""
        return {
            "type": "object",
            "properties": {},
            "required": []
        }
    
    def validate_settings(self, settings: Dict[str, Any]) -> bool:
        """Validate plugin settings"""
        # Override in subclasses for custom validation
        return True


class IngestPlugin(PluginInterface):
    """Base class for ingest plugins"""
    
    def get_type(self) -> PluginType:
        return PluginType.INGEST
    
    @abstractmethod
    async def ingest_file(self, file_path: str, context: PluginContext) -> PluginResult:
        """Ingest a file"""
        pass
    
    @abstractmethod
    async def validate_file(self, file_path: str, context: PluginContext) -> PluginResult:
        """Validate a file before ingest"""
        pass


class ProcessorPlugin(PluginInterface):
    """Base class for processor plugins"""
    
    def get_type(self) -> PluginType:
        return PluginType.PROCESSOR
    
    @abstractmethod
    async def process_asset(self, asset_id: str, context: PluginContext) -> PluginResult:
        """Process an asset"""
        pass
    
    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """Get list of supported file formats"""
        pass


class StoragePlugin(PluginInterface):
    """Base class for storage plugins"""
    
    def get_type(self) -> PluginType:
        return PluginType.STORAGE
    
    @abstractmethod
    async def store_file(self, file_path: str, key: str, context: PluginContext) -> PluginResult:
        """Store a file"""
        pass
    
    @abstractmethod
    async def retrieve_file(self, key: str, context: PluginContext) -> PluginResult:
        """Retrieve a file"""
        pass
    
    @abstractmethod
    async def delete_file(self, key: str, context: PluginContext) -> PluginResult:
        """Delete a file"""
        pass


class MetadataPlugin(PluginInterface):
    """Base class for metadata plugins"""
    
    def get_type(self) -> PluginType:
        return PluginType.METADATA
    
    @abstractmethod
    async def extract_metadata(self, file_path: str, context: PluginContext) -> PluginResult:
        """Extract metadata from file"""
        pass
    
    @abstractmethod
    async def enrich_metadata(self, metadata: Dict[str, Any], context: PluginContext) -> PluginResult:
        """Enrich existing metadata"""
        pass


class WorkflowPlugin(PluginInterface):
    """Base class for workflow plugins"""
    
    def get_type(self) -> PluginType:
        return PluginType.WORKFLOW
    
    @abstractmethod
    async def execute_step(self, step_data: Dict[str, Any], context: PluginContext) -> PluginResult:
        """Execute a workflow step"""
        pass
    
    @abstractmethod
    def get_step_schema(self) -> Dict[str, Any]:
        """Get schema for workflow step configuration"""
        pass


class SearchPlugin(PluginInterface):
    """Base class for search plugins"""
    
    def get_type(self) -> PluginType:
        return PluginType.SEARCH
    
    @abstractmethod
    async def search(self, query: str, filters: Dict[str, Any], context: PluginContext) -> PluginResult:
        """Perform search"""
        pass
    
    @abstractmethod
    async def index_asset(self, asset_id: str, metadata: Dict[str, Any], context: PluginContext) -> PluginResult:
        """Index an asset"""
        pass


class ExportPlugin(PluginInterface):
    """Base class for export plugins"""
    
    def get_type(self) -> PluginType:
        return PluginType.EXPORT
    
    @abstractmethod
    async def export_asset(self, asset_id: str, format: str, context: PluginContext) -> PluginResult:
        """Export an asset"""
        pass
    
    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """Get list of supported export formats"""
        pass


class NotificationPlugin(PluginInterface):
    """Base class for notification plugins"""
    
    def get_type(self) -> PluginType:
        return PluginType.NOTIFICATION
    
    @abstractmethod
    async def send_notification(self, recipient: str, message: Dict[str, Any], context: PluginContext) -> PluginResult:
        """Send a notification"""
        pass
    
    @abstractmethod
    def get_notification_types(self) -> List[str]:
        """Get supported notification types"""
        pass