# API Versioning Guide

## Overview

The MAMS API Gateway implements a comprehensive versioning system that allows for backward compatibility while enabling the introduction of new features and improvements. This guide covers how API versioning works, how to use different versions, and how to migrate between versions.

## Versioning Strategy

MAMS uses **URL path versioning** as the primary versioning strategy:

- Format: `/api/v{major_version}/{resource}`
- Example: `/api/v1/users`, `/api/v2/assets`

### Supported Strategies

While URL path versioning is the default, the system also supports:

1. **Header Versioning**: `API-Version: 1`
2. **Query Parameter**: `?version=1`
3. **Content Negotiation**: `Accept: application/vnd.mams.v1+json`

## Current Versions

### Version 1 (Stable)
- **Status**: Stable, Production-ready
- **Path**: `/api/v1/`
- **Features**:
  - Basic CRUD operations
  - JWT authentication
  - Rate limiting
  - Health checks
  - Standard error responses

### Version 2 (Beta)
- **Status**: Beta
- **Path**: `/api/v2/`
- **Features**:
  - All v1 features
  - Enhanced error responses
  - Request context tracking
  - GraphQL support (coming soon)
  - WebSocket subscriptions (coming soon)
- **Breaking Changes**:
  - Changed authentication header format
  - Modified error response structure
  - Some endpoints renamed

## Version Discovery

### Get Version Information

```http
GET /api/version
```

Response:
```json
{
  "current_version": "v2",
  "default_version": "v1",
  "requested_version": "v1",
  "supported_versions": [
    {
      "version": "v1",
      "status": "stable",
      "deprecated": false,
      "features": ["Basic CRUD", "JWT auth", "Rate limiting"],
      "breaking_changes": []
    },
    {
      "version": "v2",
      "status": "beta",
      "deprecated": false,
      "features": ["All v1 features", "Enhanced errors", "Request context"],
      "breaking_changes": ["Auth header format", "Error response structure"]
    }
  ],
  "versioning_strategy": "URL path versioning (/api/v1/, /api/v2/)",
  "documentation_url": "/docs/api-versioning"
}
```

### List Supported Versions

```http
GET /api/versions
```

Response:
```json
{
  "versions": ["v1", "v2"],
  "current": "v2",
  "default": "v1"
}
```

## Using Different Versions

### URL Path Versioning (Recommended)

Include the version in the URL path:

```http
# Version 1
GET /api/v1/users
POST /api/v1/assets

# Version 2
GET /api/v2/users
POST /api/v2/assets
```

### Header Versioning

Include version in request headers:

```http
GET /api/users
API-Version: 2
```

### Query Parameter Versioning

Include version as query parameter:

```http
GET /api/users?version=2
```

## Version-Specific Changes

### Authentication Headers

**Version 1**:
```http
X-Auth-Token: your-jwt-token
```

**Version 2**:
```http
Authorization: Bearer your-jwt-token
```

### Error Response Format

**Version 1**:
```json
{
  "error": "Resource not found",
  "status": 404
}
```

**Version 2**:
```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "The requested resource was not found",
    "details": {
      "resource_type": "user",
      "resource_id": "123"
    },
    "suggestion": "Check if the resource ID is correct"
  }
}
```

### Request Headers

**Version 2** requires additional headers:
- `X-Request-ID`: Unique request identifier for tracing

## Migration Guide

### Migrating from v1 to v2

Get migration guidance:

```http
GET /api/version/migration-guide/v1/v2
```

Response:
```json
{
  "from_version": "v1",
  "to_version": "v2",
  "breaking_changes": [
    "Changed authentication header format",
    "Modified error response structure"
  ],
  "new_features": [
    "Enhanced error responses",
    "Request context tracking"
  ],
  "migration_steps": [
    "Update API endpoints from /api/v1/ to /api/v2/",
    "Update authentication headers from X-Auth-Token to Authorization: Bearer",
    "Update error handling to use new error response format",
    "Test all API integrations with v2 endpoints",
    "Update client libraries to support v2 features"
  ],
  "documentation_url": "/docs/migration/v1-to-v2"
}
```

### Step-by-Step Migration

1. **Update Authentication**:
   ```javascript
   // Old (v1)
   headers: {
     'X-Auth-Token': token
   }
   
   // New (v2)
   headers: {
     'Authorization': `Bearer ${token}`
   }
   ```

2. **Update Error Handling**:
   ```javascript
   // Old (v1)
   if (response.error) {
     console.error(response.error);
   }
   
   // New (v2)
   if (response.error) {
     console.error(response.error.message);
     console.log('Error code:', response.error.code);
   }
   ```

3. **Add Required Headers**:
   ```javascript
   // v2 requires request ID
   headers: {
     'X-Request-ID': generateUUID()
   }
   ```

## Deprecation Policy

When an API version is deprecated:

1. **Deprecation Notice**: At least 6 months before removal
2. **Deprecation Headers**: Responses include deprecation warnings
3. **Migration Support**: Detailed migration guides provided
4. **Sunset Date**: Clear timeline for version removal

### Deprecation Headers

Deprecated versions include these headers:

```http
X-API-Deprecation: true
X-API-Deprecation-Date: 2024-12-31
X-API-Deprecation-Info: API version v1 is deprecated and will be removed on 2024-12-31
X-API-Sunset: 2024-12-31
```

## Version Metrics

Track API version usage:

```http
GET /api/version/metrics
Authorization: Bearer {token}
```

Response:
```json
{
  "total_requests": 10000,
  "by_version": {
    "v1": {
      "requests": 7000,
      "usage_percentage": 70,
      "error_rate": 1.2
    },
    "v2": {
      "requests": 3000,
      "usage_percentage": 30,
      "error_rate": 0.8
    }
  }
}
```

## Client Version Requirements

Some API versions may require minimum client versions:

```http
GET /api/v2/users
X-Client-Version: 1.0.0
```

If client version is too old:
```json
{
  "error": {
    "code": "VERSION_VALIDATION_ERROR",
    "message": "Client version 1.0.0 is too old. Minimum required: 2.0.0"
  }
}
```

## Best Practices

### For API Consumers

1. **Always specify version explicitly**:
   ```http
   GET /api/v1/users  # Good
   GET /api/users     # Bad - relies on default
   ```

2. **Handle version-specific responses**:
   ```javascript
   const apiVersion = response.headers['x-api-version'];
   if (apiVersion === 'v2') {
     // Handle v2 response format
   }
   ```

3. **Monitor deprecation warnings**:
   ```javascript
   if (response.headers['x-api-deprecation']) {
     console.warn('API version is deprecated:', 
       response.headers['x-api-deprecation-info']);
   }
   ```

4. **Test with multiple versions** during migration

5. **Keep client libraries updated**

### For API Development

1. **Maintain backward compatibility** within major versions
2. **Document all breaking changes**
3. **Provide migration tools and guides**
4. **Use feature flags** for gradual rollout
5. **Monitor version usage** metrics

## Changelog

View changelog for specific versions:

```http
GET /api/version/changelog/v2
```

Response:
```json
{
  "version": "v2",
  "status": "beta",
  "release_date": "2024-01-15",
  "changes": {
    "features": [
      "Enhanced error response format",
      "Request context tracking",
      "Performance improvements"
    ],
    "breaking_changes": [
      "Changed authentication header format",
      "Modified error response structure"
    ],
    "improvements": [
      "Better request validation",
      "Performance improvements"
    ],
    "security": [
      "Improved authentication token handling",
      "Added request signing support"
    ]
  }
}
```

## Troubleshooting

### Common Issues

1. **"Unsupported API Version" Error**:
   - Check supported versions: `GET /api/versions`
   - Ensure version format is correct (e.g., "v1", not "1.0")

2. **Authentication Failures After Migration**:
   - Update authentication headers for v2
   - Check token format and placement

3. **Missing Required Headers**:
   - v2 requires `X-Request-ID` header
   - Add UUID or unique identifier

4. **Unexpected Response Format**:
   - Check `X-API-Version` response header
   - Update response parsing for version

### Debug Headers

Include debug headers for troubleshooting:

```http
X-Debug-Mode: true
X-Verbose-Errors: true
```

## SDK Support

Client SDKs with version support:

- **JavaScript/TypeScript**: `npm install @mams/api-client`
- **Python**: `pip install mams-api-client`
- **Go**: `go get github.com/mams/api-client-go`

Example with JavaScript SDK:

```javascript
import { MAMSClient } from '@mams/api-client';

// Specify version
const client = new MAMSClient({
  apiVersion: 'v2',
  baseURL: 'https://api.mams.example.com'
});

// SDK handles version-specific details
const users = await client.users.list();
```

## Future Versions

### Version 3 (Planned)

Planned features:
- GraphQL API
- Real-time subscriptions
- Advanced search capabilities
- AI-powered features
- Blockchain integration

Stay updated on future versions by subscribing to our API changelog.