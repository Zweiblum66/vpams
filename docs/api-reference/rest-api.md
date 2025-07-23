# REST API Reference

## Overview

The MAMS REST API provides programmatic access to all platform features. This reference covers authentication, endpoints, request/response formats, and best practices.

## Base URL

```
https://api.mams.example.com/api/v1
```

For development:
```
http://localhost:8000/api/v1
```

## Authentication

All API requests require authentication using JWT tokens.

### Obtaining a Token

```bash
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "your-password"
}
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Using the Token

Include the token in the Authorization header:
```bash
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

## Common Endpoints

### Assets

#### List Assets
```http
GET /assets
```

Query Parameters:
- `page` (integer): Page number (default: 1)
- `limit` (integer): Items per page (default: 20, max: 100)
- `sort` (string): Sort field (created_at, name, size)
- `order` (string): Sort order (asc, desc)
- `filter[type]` (string): Filter by type (video, image, audio, document)
- `filter[status]` (string): Filter by status (active, archived, processing)
- `search` (string): Search query

Example:
```bash
GET /assets?page=1&limit=50&sort=created_at&order=desc&filter[type]=video
```

Response:
```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "sample-video.mp4",
      "type": "video",
      "size": 104857600,
      "mime_type": "video/mp4",
      "status": "active",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:35:00Z",
      "metadata": {
        "duration": 120.5,
        "width": 1920,
        "height": 1080,
        "fps": 30
      }
    }
  ],
  "meta": {
    "page": 1,
    "limit": 50,
    "total": 1234,
    "pages": 25
  },
  "links": {
    "self": "/api/v1/assets?page=1&limit=50",
    "next": "/api/v1/assets?page=2&limit=50",
    "prev": null,
    "first": "/api/v1/assets?page=1&limit=50",
    "last": "/api/v1/assets?page=25&limit=50"
  }
}
```

#### Get Asset Details
```http
GET /assets/{asset_id}
```

Parameters:
- `include` (string): Include related data (metadata,versions,permissions)

Example:
```bash
GET /assets/550e8400-e29b-41d4-a716-446655440000?include=metadata,versions
```

#### Create Asset
```http
POST /assets
```

Request Body (multipart/form-data):
- `file` (file): The file to upload
- `name` (string): Asset name
- `description` (string): Asset description
- `metadata` (json): Additional metadata
- `project_id` (uuid): Associated project
- `tags` (array): Tags to apply

Example using curl:
```bash
curl -X POST "https://api.mams.example.com/api/v1/assets" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@/path/to/video.mp4" \
  -F "name=My Video" \
  -F "description=Sample video upload" \
  -F 'metadata={"custom_field":"value"}' \
  -F 'tags=["tutorial","sample"]'
```

#### Update Asset
```http
PUT /assets/{asset_id}
```

Request Body:
```json
{
  "name": "Updated Name",
  "description": "Updated description",
  "metadata": {
    "custom_field": "new_value"
  },
  "tags": ["updated", "tags"]
}
```

#### Delete Asset
```http
DELETE /assets/{asset_id}
```

Query Parameters:
- `permanent` (boolean): Permanently delete (default: false)

### Projects

#### List Projects
```http
GET /projects
```

#### Create Project
```http
POST /projects
```

Request Body:
```json
{
  "name": "Project Alpha",
  "description": "Marketing campaign Q1 2024",
  "metadata": {
    "client": "ACME Corp",
    "deadline": "2024-03-31"
  }
}
```

#### Add Asset to Project
```http
POST /projects/{project_id}/assets
```

Request Body:
```json
{
  "asset_id": "550e8400-e29b-41d4-a716-446655440000",
  "position": 1
}
```

### Search

#### Search Assets
```http
POST /search
```

Request Body:
```json
{
  "query": "sunset beach",
  "filters": {
    "type": ["video", "image"],
    "date_range": {
      "start": "2024-01-01",
      "end": "2024-12-31"
    },
    "metadata": {
      "location": "California"
    }
  },
  "facets": ["type", "tags", "location"],
  "page": 1,
  "limit": 20
}
```

Response includes faceted results:
```json
{
  "data": [...],
  "facets": {
    "type": {
      "video": 45,
      "image": 123,
      "audio": 12
    },
    "tags": {
      "beach": 89,
      "sunset": 67,
      "california": 45
    }
  },
  "meta": {...}
}
```

### Users

#### Get Current User
```http
GET /users/me
```

#### Update Profile
```http
PUT /users/me
```

Request Body:
```json
{
  "name": "John Doe",
  "email": "john.doe@example.com",
  "preferences": {
    "theme": "dark",
    "language": "en",
    "notifications": {
      "email": true,
      "push": false
    }
  }
}
```

### Workflows

#### List Workflows
```http
GET /workflows
```

#### Start Workflow
```http
POST /workflows/{workflow_id}/execute
```

Request Body:
```json
{
  "assets": [
    "550e8400-e29b-41d4-a716-446655440000"
  ],
  "parameters": {
    "priority": "high",
    "notify_on_complete": true
  }
}
```

### Metadata

#### Get Metadata Schema
```http
GET /metadata/schemas/{schema_id}
```

#### Create Custom Field
```http
POST /metadata/fields
```

Request Body:
```json
{
  "name": "shoot_location",
  "label": "Shoot Location",
  "type": "string",
  "required": false,
  "searchable": true,
  "facetable": true
}
```

## Error Handling

All errors follow a consistent format:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Asset not found",
    "details": {
      "asset_id": "550e8400-e29b-41d4-a716-446655440000"
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_abc123xyz"
  }
}
```

Common error codes:
- `AUTHENTICATION_REQUIRED` - No valid token provided
- `PERMISSION_DENIED` - Insufficient permissions
- `RESOURCE_NOT_FOUND` - Resource doesn't exist
- `VALIDATION_ERROR` - Invalid request data
- `RATE_LIMIT_EXCEEDED` - Too many requests
- `INTERNAL_ERROR` - Server error

## Rate Limiting

API requests are rate limited:
- **Standard**: 1000 requests/hour
- **Premium**: 10000 requests/hour
- **Enterprise**: Unlimited

Rate limit headers:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642089600
```

## Pagination

All list endpoints support pagination:

```json
{
  "data": [...],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 1234,
    "pages": 62
  },
  "links": {
    "self": "...",
    "next": "...",
    "prev": "...",
    "first": "...",
    "last": "..."
  }
}
```

## Filtering

Use the `filter` parameter for filtering:

```
GET /assets?filter[type]=video&filter[status]=active
```

Operators:
- `eq`: Equals (default)
- `ne`: Not equals
- `gt`: Greater than
- `gte`: Greater than or equal
- `lt`: Less than
- `lte`: Less than or equal
- `in`: In array
- `like`: Pattern matching

Example:
```
GET /assets?filter[created_at][gte]=2024-01-01&filter[size][lt]=1000000
```

## Sorting

Use `sort` and `order` parameters:

```
GET /assets?sort=created_at&order=desc
```

Multiple sort fields:
```
GET /assets?sort=type,created_at&order=asc,desc
```

## Field Selection

Limit returned fields using `fields`:

```
GET /assets?fields=id,name,type,created_at
```

## Relationships

Include related resources using `include`:

```
GET /assets/123?include=metadata,versions,project
```

## Webhooks

Register webhooks for real-time notifications:

```http
POST /webhooks
```

Request Body:
```json
{
  "url": "https://your-app.com/webhook",
  "events": ["asset.created", "asset.updated"],
  "secret": "your-webhook-secret"
}
```

## API Versioning

The API version is included in the URL path:
- Current: `/api/v1`
- Legacy: `/api/v0` (deprecated)

Version headers:
```
X-API-Version: 1.0
X-API-Deprecation: false
```

## SDK Examples

### JavaScript/TypeScript
```javascript
import { MAMSClient } from '@mams/sdk';

const client = new MAMSClient({
  apiKey: 'your-api-key',
  baseUrl: 'https://api.mams.example.com'
});

// List assets
const assets = await client.assets.list({
  page: 1,
  limit: 50,
  filter: { type: 'video' }
});

// Upload asset
const asset = await client.assets.create({
  file: fileObject,
  name: 'My Video',
  metadata: { project: 'Alpha' }
});
```

### Python
```python
from mams_sdk import MAMSClient

client = MAMSClient(
    api_key='your-api-key',
    base_url='https://api.mams.example.com'
)

# List assets
assets = client.assets.list(
    page=1,
    limit=50,
    filter={'type': 'video'}
)

# Upload asset
with open('video.mp4', 'rb') as f:
    asset = client.assets.create(
        file=f,
        name='My Video',
        metadata={'project': 'Alpha'}
    )
```

## Best Practices

1. **Use pagination** for large result sets
2. **Cache responses** when appropriate
3. **Handle rate limits** gracefully
4. **Use field selection** to reduce payload size
5. **Implement exponential backoff** for retries
6. **Validate inputs** before sending requests
7. **Use webhooks** for real-time updates
8. **Batch operations** when possible

## OpenAPI Specification

The complete OpenAPI 3.0 specification is available at:
- Interactive docs: `/docs`
- OpenAPI JSON: `/openapi.json`
- ReDoc: `/redoc`

---

For more information:
- [Authentication Guide](./authentication.md)
- [Error Handling](./error-handling.md)
- [Rate Limiting](./rate-limiting.md)
- [GraphQL API](./graphql.md)