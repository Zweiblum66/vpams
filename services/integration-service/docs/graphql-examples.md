# GraphQL API Examples

The Integration Service provides a GraphQL API at `/api/v1/graphql` for flexible querying and mutations.

## Authentication

All GraphQL requests require authentication. Include the JWT token in the Authorization header:

```
Authorization: Bearer YOUR_JWT_TOKEN
```

## Queries

### List Integrations

```graphql
query ListIntegrations {
  integrations(limit: 20, enabled: true) {
    id
    name
    type
    description
    enabled
    createdAt
    eventCount
    errorCount
  }
}
```

### Get Integration Details

```graphql
query GetIntegration($id: UUID!) {
  integration(id: $id) {
    id
    name
    type
    description
    enabled
    userId
    createdAt
    updatedAt
    lastUsedAt
    eventCount
    errorCount
  }
}
```

### List Webhooks

```graphql
query ListWebhooks {
  webhooks(limit: 10, enabled: true) {
    id
    integrationId
    name
    url
    events
    enabled
    verified
    createdAt
    successCount
    failureCount
  }
}
```

### Get Integration Events

```graphql
query GetIntegrationEvents($integrationId: UUID!) {
  integrationEvents(integrationId: $integrationId, limit: 50) {
    id
    eventType
    eventData
    status
    attempts
    responseStatus
    errorMessage
    createdAt
    sentAt
    completedAt
  }
}
```

## Mutations

### Create Integration

```graphql
mutation CreateIntegration {
  createIntegration(input: {
    name: "My Slack Workspace"
    type: SLACK
    description: "Main company Slack"
    enabled: true
    authType: OAUTH2
    config: {
      workspace_id: "T12345"
    }
  }) {
    id
    name
    type
    enabled
  }
}
```

### Update Integration

```graphql
mutation UpdateIntegration($id: UUID!) {
  updateIntegration(id: $id, input: {
    name: "Updated Name"
    enabled: false
    config: {
      new_setting: "value"
    }
  }) {
    id
    name
    enabled
  }
}
```

### Create Webhook

```graphql
mutation CreateWebhook {
  createWebhook(input: {
    name: "Asset Upload Webhook"
    url: "https://example.com/webhook"
    events: ["asset.created", "asset.updated"]
    secret: "webhook_secret"
    enabled: true
  }) {
    id
    name
    url
    events
    verified
  }
}
```

### Test Integration

```graphql
mutation TestIntegration($id: UUID!) {
  testIntegration(id: $id) {
    success
    message
    details
  }
}
```

### Send Event

```graphql
mutation SendEvent {
  sendEvent(input: {
    integrationId: "123e4567-e89b-12d3-a456-426614174000"
    eventType: ASSET_CREATED
    eventData: {
      assetId: "asset123"
      assetName: "video.mp4"
      assetType: "video"
      fileSize: 1024000
    }
    metadata: {
      userId: "user123"
      projectId: "project456"
    }
  })
}
```

## Subscriptions

### Subscribe to Integration Events

```graphql
subscription WatchIntegrationEvents($integrationId: UUID!) {
  integrationEvents(integrationId: $integrationId) {
    id
    eventType
    eventData
    status
    errorMessage
    createdAt
  }
}
```

### Watch Webhook Status

```graphql
subscription WatchWebhookStatus($webhookId: UUID!) {
  webhookStatus(webhookId: $webhookId) {
    id
    enabled
    verified
    lastTriggeredAt
    successCount
    failureCount
  }
}
```

## Complex Queries

### Get Integration with Events and Webhooks

```graphql
query GetIntegrationDetails($id: UUID!) {
  integration(id: $id) {
    id
    name
    type
    enabled
    eventCount
  }
  
  integrationEvents(integrationId: $id, limit: 10) {
    id
    eventType
    status
    createdAt
  }
  
  webhooks(limit: 10) {
    id
    name
    url
    events
  }
}
```

## Error Handling

GraphQL errors are returned in the standard format:

```json
{
  "errors": [{
    "message": "Integration not found",
    "path": ["integration"],
    "extensions": {
      "code": "NOT_FOUND"
    }
  }]
}
```

## Rate Limiting

The GraphQL API follows the same rate limiting rules as the REST API:
- 1000 requests per hour for authenticated users
- Complex queries count as multiple requests based on complexity

## Introspection

The GraphQL schema supports introspection in development mode. Use your favorite GraphQL client to explore the schema:

```graphql
query IntrospectionQuery {
  __schema {
    types {
      name
      description
      fields {
        name
        description
        type {
          name
        }
      }
    }
  }
}
```