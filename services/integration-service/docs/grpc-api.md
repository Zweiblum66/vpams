# gRPC API Documentation

## Overview

The Integration Service provides a high-performance gRPC API alongside REST and GraphQL APIs. The gRPC API is ideal for:

- Service-to-service communication
- Real-time event streaming
- High-throughput operations
- Binary data efficiency

## Setup

### Server Configuration

Enable gRPC in your environment:

```env
GRPC_ENABLED=true
GRPC_PORT=50051
```

### Client Installation

```bash
pip install grpcio
```

## Authentication

All gRPC calls require authentication via metadata:

```python
metadata = [("authorization", f"Bearer {jwt_token}")]
```

## Service Definition

The complete service definition is in `integration_service.proto`.

### Available Methods

#### Integration Management
- `ListIntegrations` - List all integrations
- `GetIntegration` - Get integration details
- `CreateIntegration` - Create new integration
- `UpdateIntegration` - Update integration
- `DeleteIntegration` - Delete integration
- `TestIntegration` - Test integration connection

#### Webhook Management
- `ListWebhooks` - List webhooks
- `GetWebhook` - Get webhook details
- `CreateWebhook` - Create webhook
- `UpdateWebhook` - Update webhook
- `DeleteWebhook` - Delete webhook
- `TestWebhook` - Test webhook

#### Event Management
- `SendEvent` - Send event to integration
- `ListEvents` - List integration events
- `StreamEvents` - Real-time event streaming

## Python Client Usage

### Basic Example

```python
import asyncio
from mams.integration.client import IntegrationServiceClient
from mams.integration import integration_service_pb2 as proto

async def main():
    # Create client
    client = IntegrationServiceClient(
        host="localhost",
        port=50051,
        auth_token="your-jwt-token"
    )
    
    async with client:
        # List integrations
        integrations = await client.list_integrations(
            integration_type=proto.INTEGRATION_TYPE_SLACK,
            enabled_only=True
        )
        
        for integration in integrations:
            print(f"{integration.name}: {integration.enabled}")

asyncio.run(main())
```

### Creating Integrations

```python
# Create Slack integration
slack = await client.create_integration(
    name="Company Slack",
    integration_type=proto.INTEGRATION_TYPE_SLACK,
    description="Main Slack workspace",
    config={
        "workspace_id": "T12345",
        "default_channel": "#general"
    },
    auth_type=proto.AUTH_TYPE_OAUTH2,
    auth_config={
        "access_token": "xoxb-...",
        "refresh_token": "xoxr-..."
    }
)

# Create webhook
webhook = await client.create_webhook(
    name="Status Updates",
    url="https://example.com/webhook",
    events=["asset.created", "workflow.completed"],
    secret="webhook-secret"
)
```

### Sending Events

```python
# Send event to integration
response = await client.send_event(
    integration_id=integration.id,
    event_type=proto.EVENT_TYPE_ASSET_CREATED,
    event_data={
        "asset_id": "asset123",
        "asset_name": "video.mp4",
        "asset_type": "video",
        "file_size": 1048576
    },
    metadata={
        "user_id": "user456",
        "project_id": "proj789"
    }
)

if response.success:
    print(f"Event sent: {response.event_id}")
else:
    print(f"Error: {response.error}")
```

### Event Streaming

```python
# Stream real-time events
async for event in client.stream_events(
    integration_id=integration.id,
    event_types=[
        proto.EVENT_TYPE_ASSET_CREATED,
        proto.EVENT_TYPE_WORKFLOW_COMPLETED
    ],
    include_historical=True  # Include last 100 events
):
    print(f"Event: {event.id}")
    print(f"Type: {event.event_type}")
    print(f"Data: {dict(event.event_data)}")
    
    # Process event...
```

## Direct gRPC Usage

For languages other than Python or custom implementations:

### Node.js Example

```javascript
const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');

// Load proto file
const packageDefinition = protoLoader.loadSync(
    'integration_service.proto',
    {
        keepCase: true,
        longs: String,
        enums: String,
        defaults: true,
        oneofs: true
    }
);

const proto = grpc.loadPackageDefinition(packageDefinition).mams.integration.v1;

// Create client
const client = new proto.IntegrationService(
    'localhost:50051',
    grpc.credentials.createInsecure()
);

// Add authentication
const metadata = new grpc.Metadata();
metadata.add('authorization', 'Bearer ' + token);

// List integrations
client.listIntegrations({
    page_size: 20,
    enabled_only: true
}, metadata, (error, response) => {
    if (error) {
        console.error(error);
        return;
    }
    console.log('Integrations:', response.integrations);
});
```

### Go Example

```go
package main

import (
    "context"
    "log"
    "google.golang.org/grpc"
    "google.golang.org/grpc/metadata"
    pb "mams/integration/v1"
)

func main() {
    // Connect to server
    conn, err := grpc.Dial("localhost:50051", grpc.WithInsecure())
    if err != nil {
        log.Fatalf("Failed to connect: %v", err)
    }
    defer conn.Close()
    
    client := pb.NewIntegrationServiceClient(conn)
    
    // Add authentication
    ctx := metadata.AppendToOutgoingContext(
        context.Background(),
        "authorization", "Bearer "+token,
    )
    
    // List integrations
    resp, err := client.ListIntegrations(ctx, &pb.ListIntegrationsRequest{
        PageSize: 20,
        EnabledOnly: true,
    })
    
    if err != nil {
        log.Fatalf("Error: %v", err)
    }
    
    for _, integration := range resp.Integrations {
        log.Printf("%s: %v", integration.Name, integration.Enabled)
    }
}
```

## Performance Considerations

### Streaming
- Use streaming for real-time updates
- Implement backpressure handling
- Set appropriate timeouts

### Connection Pooling
```python
# Reuse client connections
client = IntegrationServiceClient(host="localhost")
await client.connect()

# Use for multiple operations
for i in range(100):
    await client.send_event(...)

await client.close()
```

### Batch Operations
- Use repeated fields for bulk operations
- Implement client-side batching for efficiency

## Error Handling

### Status Codes
- `UNAUTHENTICATED` - Invalid or missing token
- `NOT_FOUND` - Resource not found
- `INVALID_ARGUMENT` - Invalid request data
- `ALREADY_EXISTS` - Duplicate resource
- `PERMISSION_DENIED` - Insufficient permissions

### Example Error Handling

```python
import grpc

try:
    integration = await client.get_integration("invalid-id")
except grpc.RpcError as e:
    if e.code() == grpc.StatusCode.NOT_FOUND:
        print("Integration not found")
    elif e.code() == grpc.StatusCode.UNAUTHENTICATED:
        print("Authentication failed")
    else:
        print(f"Error: {e.details()}")
```

## Advanced Features

### Interceptors

```python
class LoggingInterceptor(grpc.UnaryUnaryClientInterceptor):
    def intercept_unary_unary(self, continuation, client_call_details, request):
        print(f"Calling {client_call_details.method}")
        response = continuation(client_call_details, request)
        print(f"Received response")
        return response

# Use with client
channel = grpc.insecure_channel('localhost:50051')
intercept_channel = grpc.intercept_channel(channel, LoggingInterceptor())
```

### Health Checking

```proto
service Health {
    rpc Check(HealthCheckRequest) returns (HealthCheckResponse);
    rpc Watch(HealthCheckRequest) returns (stream HealthCheckResponse);
}
```

### Load Balancing

```python
# Client-side load balancing
options = [
    ('grpc.lb_policy_name', 'round_robin'),
]
channel = grpc.insecure_channel(
    'dns:///integration-service:50051',
    options=options
)
```

## Debugging

### Enable Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Use gRPC Reflection

```bash
# List services
grpcurl -plaintext localhost:50051 list

# Describe service
grpcurl -plaintext localhost:50051 describe mams.integration.v1.IntegrationService

# Call method
grpcurl -plaintext \
  -H "authorization: Bearer $TOKEN" \
  -d '{"page_size": 10}' \
  localhost:50051 \
  mams.integration.v1.IntegrationService/ListIntegrations
```

## Migration Guide

### From REST to gRPC

REST:
```python
response = requests.get(
    "http://localhost:8000/api/v1/integrations",
    headers={"Authorization": f"Bearer {token}"}
)
integrations = response.json()
```

gRPC:
```python
integrations = await client.list_integrations()
```

### From GraphQL to gRPC

GraphQL:
```graphql
query {
  integrations(limit: 20, enabled: true) {
    id
    name
    type
  }
}
```

gRPC:
```python
response = await client.list_integrations(
    page_size=20,
    enabled_only=True
)
```