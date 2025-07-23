# MAMS Python SDK

Official Python SDK for MAMS (Media Asset Management System).

## Installation

```bash
pip install mams-sdk
```

For additional features:
```bash
# For gRPC support
pip install mams-sdk[grpc]

# For WebSocket support
pip install mams-sdk[websocket]

# For development
pip install mams-sdk[dev]
```

## Quick Start

```python
from mams import MAMSClient

# Initialize client
client = MAMSClient(
    base_url="https://api.mams.io",
    api_key="your-api-key"
)

# List assets
assets = client.assets.list(limit=10)
for asset in assets:
    print(f"{asset.name}: {asset.type}")

# Upload an asset
with open("video.mp4", "rb") as f:
    asset = client.assets.upload(
        file=f,
        name="My Video",
        project_id="proj_123"
    )
    print(f"Uploaded: {asset.id}")

# Search assets
results = client.assets.search(
    query="interview",
    type="video",
    project_id="proj_123"
)
```

## Authentication

The SDK supports multiple authentication methods:

### API Key
```python
client = MAMSClient(api_key="your-api-key")
```

### JWT Token
```python
client = MAMSClient(jwt_token="your-jwt-token")
```

### OAuth2
```python
from mams.auth import OAuth2Provider

auth = OAuth2Provider(
    client_id="your-client-id",
    client_secret="your-client-secret",
    redirect_uri="http://localhost:8000/callback"
)

# Get authorization URL
auth_url = auth.get_authorization_url()

# Exchange code for token
token = auth.exchange_code(code)
client = MAMSClient(auth=auth)
```

## Resources

### Assets
```python
# List assets
assets = client.assets.list(
    limit=20,
    offset=0,
    project_id="proj_123",
    type="video"
)

# Get asset
asset = client.assets.get("asset_123")

# Create asset
asset = client.assets.create(
    name="New Asset",
    type="video",
    metadata={"description": "Test video"}
)

# Update asset
asset = client.assets.update(
    "asset_123",
    name="Updated Name",
    metadata={"tags": ["demo", "test"]}
)

# Delete asset
client.assets.delete("asset_123")

# Upload asset
with open("file.mp4", "rb") as f:
    asset = client.assets.upload(
        file=f,
        name="Uploaded Video",
        project_id="proj_123"
    )

# Download asset
client.assets.download("asset_123", "output.mp4")
```

### Projects
```python
# List projects
projects = client.projects.list()

# Create project
project = client.projects.create(
    name="New Project",
    description="Project description"
)

# Add asset to project
client.projects.add_asset("proj_123", "asset_456")
```

### Workflows
```python
# Start workflow
workflow = client.workflows.start(
    type="transcoding",
    asset_id="asset_123",
    params={"profile": "1080p"}
)

# Get workflow status
status = client.workflows.get_status(workflow.id)

# List workflows
workflows = client.workflows.list(
    asset_id="asset_123",
    status="completed"
)
```

### Integrations
```python
# List integrations
integrations = client.integrations.list()

# Create Slack integration
slack = client.integrations.create(
    type="slack",
    name="Team Slack",
    config={
        "webhook_url": "https://hooks.slack.com/..."
    }
)

# Send event
client.integrations.send_event(
    integration_id=slack.id,
    event_type="asset.created",
    data={"asset_id": "asset_123"}
)
```

## Async Support

The SDK provides async versions of all methods:

```python
import asyncio
from mams import AsyncMAMSClient

async def main():
    client = AsyncMAMSClient(api_key="your-api-key")
    
    # Async operations
    assets = await client.assets.list()
    
    # Upload with progress
    async def progress_callback(bytes_uploaded, total_bytes):
        percent = (bytes_uploaded / total_bytes) * 100
        print(f"Upload progress: {percent:.1f}%")
    
    with open("large_file.mp4", "rb") as f:
        asset = await client.assets.upload(
            file=f,
            name="Large Video",
            progress_callback=progress_callback
        )

asyncio.run(main())
```

## Pagination

The SDK handles pagination automatically:

```python
# Iterate through all assets
for asset in client.assets.iter_all():
    print(asset.name)

# Manual pagination
page1 = client.assets.list(limit=20, offset=0)
page2 = client.assets.list(limit=20, offset=20)
```

## Error Handling

```python
from mams.exceptions import (
    MAMSError,
    AuthenticationError,
    NotFoundError,
    ValidationError,
    RateLimitError
)

try:
    asset = client.assets.get("invalid_id")
except NotFoundError:
    print("Asset not found")
except AuthenticationError:
    print("Authentication failed")
except RateLimitError as e:
    print(f"Rate limited. Retry after: {e.retry_after}")
except MAMSError as e:
    print(f"API error: {e}")
```

## Webhooks

```python
from mams.webhooks import WebhookHandler

handler = WebhookHandler(secret="webhook-secret")

@handler.on("asset.created")
def handle_asset_created(event):
    print(f"New asset: {event.data['asset_id']}")

@handler.on("workflow.completed")
def handle_workflow_completed(event):
    print(f"Workflow done: {event.data['workflow_id']}")

# In your web framework
def webhook_endpoint(request):
    signature = request.headers.get("X-MAMS-Signature")
    body = request.body
    
    handler.handle(body, signature)
```

## Configuration

```python
from mams import MAMSClient, Config

config = Config(
    base_url="https://api.mams.io",
    api_key="your-api-key",
    timeout=30,
    max_retries=3,
    verify_ssl=True
)

client = MAMSClient(config=config)
```

## Examples

See the [examples](examples/) directory for more detailed examples:

- [Basic Usage](examples/basic_usage.py)
- [Async Operations](examples/async_operations.py)
- [File Upload/Download](examples/file_operations.py)
- [Webhook Handling](examples/webhook_handler.py)
- [Error Handling](examples/error_handling.py)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.