# MAMS Plugin Service

The Plugin Service provides an extensible plugin architecture for the Media Asset Management System (MAMS), allowing third-party developers to extend the platform's functionality.

## Features

- **12 Plugin Types**: Support for various plugin types including Ingest, Processor, Storage, Metadata, Workflow, Search, Export, Analytics, Authentication, Notification, UI Component, and API Extension
- **Lifecycle Management**: Complete plugin lifecycle support (install, enable, disable, reload, uninstall)
- **Security**: Code validation, optional sandboxing, and capability-based permissions
- **Plugin Registry**: Marketplace functionality for plugin discovery and distribution
- **Developer Tools**: API for plugin development, webhook support, and developer accounts
- **Event System**: Event-driven communication between plugins and the core system
- **Hook System**: Decorator-based hooks for extending core functionality
- **Health Monitoring**: Real-time plugin health status and metrics

## Architecture

### Core Components

1. **Plugin Base** (`plugin_base.py`)
   - Abstract base classes for all plugin types
   - Plugin metadata and configuration structures
   - Hook and event system implementations
   - Context and result standardization

2. **Plugin Manager** (`plugin_manager.py`)
   - Plugin lifecycle management
   - Dynamic plugin loading and execution
   - Database persistence
   - Health monitoring

3. **Plugin Registry** (`plugin_registry.py`)
   - Plugin marketplace functionality
   - Search and discovery
   - Ratings and reviews
   - Download tracking

4. **Plugin Loader** (`plugin_loader.py`)
   - Dynamic module loading
   - Code validation and security checks
   - Sandbox environment management
   - Dependency management

## API Endpoints

### Plugin Management
- `GET /api/v1/plugins` - List installed plugins
- `GET /api/v1/plugins/{plugin_id}` - Get plugin details
- `POST /api/v1/plugins/install` - Install a plugin
- `DELETE /api/v1/plugins/{plugin_id}` - Uninstall a plugin
- `POST /api/v1/plugins/{plugin_id}/enable` - Enable a plugin
- `POST /api/v1/plugins/{plugin_id}/disable` - Disable a plugin
- `POST /api/v1/plugins/{plugin_id}/reload` - Reload a plugin
- `PUT /api/v1/plugins/{plugin_id}/config` - Update plugin configuration
- `GET /api/v1/plugins/{plugin_id}/health` - Get plugin health status
- `POST /api/v1/plugins/{plugin_id}/execute` - Execute a plugin hook

### Plugin Registry
- `GET /api/v1/registry/search` - Search for plugins
- `GET /api/v1/registry/featured` - Get featured plugins
- `GET /api/v1/registry/popular` - Get popular plugins
- `POST /api/v1/registry/{plugin_id}/install` - Install from registry
- `POST /api/v1/registry/{plugin_id}/review` - Add a review

### Developer APIs
- `GET /api/v1/developer/account` - Get developer account
- `POST /api/v1/developer/register` - Register as developer
- `POST /api/v1/webhooks` - Register a webhook
- `GET /api/v1/webhooks` - List webhooks
- `DELETE /api/v1/webhooks/{webhook_id}` - Delete a webhook

## Plugin Development

### Creating a Plugin

1. **Create plugin structure**:
```
my-plugin/
├── plugin.json       # Plugin metadata and configuration
├── main.py          # Plugin implementation
├── config.yaml      # Default configuration
└── requirements.txt # Python dependencies
```

2. **Define plugin metadata** (`plugin.json`):
```json
{
  "metadata": {
    "id": "my-plugin",
    "name": "My Plugin",
    "version": "1.0.0",
    "description": "Description of my plugin",
    "author": "Your Name",
    "author_email": "email@example.com"
  },
  "requirements": {
    "python": ">=3.11",
    "dependencies": ["pillow>=10.0.0"]
  },
  "capabilities": ["read_assets", "write_assets"],
  "hooks": [
    {
      "name": "pre_process",
      "description": "Called before processing"
    }
  ]
}
```

3. **Implement plugin class** (`main.py`):
```python
from plugin_base import ProcessorPlugin, PluginHook, PluginResult

class MyPlugin(ProcessorPlugin):
    async def initialize(self) -> bool:
        # Initialize plugin
        return True
    
    async def process_asset(self, asset_id: str, context) -> PluginResult:
        # Process asset
        return PluginResult(success=True, data={"processed": True})
    
    @PluginHook("pre_process")
    async def pre_process_hook(self, context, **kwargs):
        # Hook implementation
        return PluginResult(success=True)
```

### Plugin Types

Each plugin type has specific methods to implement:

- **IngestPlugin**: `ingest_file()`, `validate_file()`
- **ProcessorPlugin**: `process_asset()`, `get_supported_formats()`
- **StoragePlugin**: `store_file()`, `retrieve_file()`, `delete_file()`
- **MetadataPlugin**: `extract_metadata()`, `enrich_metadata()`
- **WorkflowPlugin**: `execute_step()`, `get_step_schema()`
- **SearchPlugin**: `search()`, `index_asset()`
- **ExportPlugin**: `export_asset()`, `get_supported_formats()`
- **NotificationPlugin**: `send_notification()`, `get_notification_types()`

## Configuration

### Environment Variables
- `PLUGINS_DIR` - Directory for installed plugins (default: `/app/plugins`)
- `PLUGIN_SANDBOX_ENABLED` - Enable plugin sandboxing (default: `true`)
- `PLUGIN_SANDBOX_DIR` - Directory for sandboxes (default: `/app/sandboxes`)
- `PLUGIN_MAX_EXECUTION_TIME` - Maximum execution time in seconds (default: `300`)
- `PLUGIN_MAX_MEMORY_MB` - Maximum memory per plugin (default: `512`)

### Plugin Configuration

Plugins can be configured through their `config.yaml` file or via the API:

```yaml
enabled: true
settings:
  quality: 85
  format: jpg
  enable_optimization: true
capabilities:
  - read_assets
  - write_assets
rate_limit: 100  # requests per minute
timeout: 30      # seconds
priority: 5      # execution priority
```

## Security

### Code Validation
- AST parsing to detect dangerous imports and function calls
- Whitelist of allowed packages for sandboxed plugins
- Manifest validation for required fields and formats

### Sandboxing
- Isolated virtual environments per plugin
- Resource limits (CPU, memory, execution time)
- Restricted network access
- File system isolation

### Permissions
- Capability-based permission system
- Fine-grained access control
- API key authentication for developers
- Webhook secret validation

## Deployment

### Docker
```bash
docker-compose up plugin-service
```

### Kubernetes
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: plugin-service
spec:
  replicas: 2
  selector:
    matchLabels:
      app: plugin-service
  template:
    metadata:
      labels:
        app: plugin-service
    spec:
      containers:
      - name: plugin-service
        image: mams/plugin-service:latest
        ports:
        - containerPort: 8013
        env:
        - name: DATABASE_URL
          value: postgresql://...
        volumeMounts:
        - name: plugins
          mountPath: /app/plugins
      volumes:
      - name: plugins
        persistentVolumeClaim:
          claimName: plugin-storage
```

## Example Plugin

See the `examples/example_plugin` directory for a complete example of a processor plugin that demonstrates:
- Plugin structure and metadata
- Hook implementation
- Event handling
- Configuration management
- Error handling
- Health reporting

## Monitoring

The plugin service exposes Prometheus metrics:
- `plugin_execution_total` - Total plugin executions
- `plugin_execution_duration_seconds` - Execution duration histogram
- `plugin_errors_total` - Total plugin errors
- `plugin_status` - Current plugin status (1=enabled, 0=disabled)

## License

This service is part of the MAMS project and follows the same license terms.