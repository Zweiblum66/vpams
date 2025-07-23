# MAMS API Gateway - Usage Examples

This document provides comprehensive examples of how to use the MAMS API Gateway endpoints.

## Table of Contents

1. [Authentication](#authentication)
2. [Common Patterns](#common-patterns)
3. [Error Handling](#error-handling)
4. [Rate Limiting](#rate-limiting)
5. [Health Checks](#health-checks)
6. [User Management](#user-management)
7. [Asset Management](#asset-management)
8. [Search Operations](#search-operations)
9. [Administrative Operations](#administrative-operations)
10. [SDK Examples](#sdk-examples)

## Authentication

### JWT Bearer Token

```bash
# Login to get JWT token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user@example.com",
    "password": "password123"
  }'

# Response
{
  "data": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "bearer",
    "expires_in": 3600,
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  }
}

# Use token in subsequent requests
curl -X GET "http://localhost:8000/api/v1/users/profile" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
```

### API Key Authentication

```bash
# Use API key in header
curl -X GET "http://localhost:8000/api/v1/assets" \
  -H "X-API-Key: your-api-key-here"
```

### Refresh Token

```bash
# Refresh expired token
curl -X POST "http://localhost:8000/api/v1/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  }'
```

## Common Patterns

### Pagination

```bash
# Get paginated results
curl -X GET "http://localhost:8000/api/v1/assets?page=1&limit=20" \
  -H "Authorization: Bearer <token>"

# Response with pagination metadata
{
  "data": [...],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 100,
    "pages": 5
  },
  "links": {
    "self": "/api/v1/assets?page=1&limit=20",
    "next": "/api/v1/assets?page=2&limit=20",
    "prev": null,
    "first": "/api/v1/assets?page=1&limit=20",
    "last": "/api/v1/assets?page=5&limit=20"
  }
}
```

### Filtering and Sorting

```bash
# Filter and sort results
curl -X GET "http://localhost:8000/api/v1/assets?filter[type]=video&filter[status]=active&sort=created_at&order=desc" \
  -H "Authorization: Bearer <token>"
```

### Field Selection

```bash
# Select specific fields
curl -X GET "http://localhost:8000/api/v1/assets?fields=id,name,type,created_at" \
  -H "Authorization: Bearer <token>"
```

### Include Related Resources

```bash
# Include related resources
curl -X GET "http://localhost:8000/api/v1/assets?include=metadata,versions" \
  -H "Authorization: Bearer <token>"
```

## Error Handling

### Standard Error Response

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "The requested asset was not found",
    "details": {
      "asset_id": "123e4567-e89b-12d3-a456-426614174000"
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_abc123"
  }
}
```

### Validation Error Response

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": {
      "field_errors": {
        "name": ["This field is required"],
        "email": ["Invalid email format"]
      }
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_abc123"
  }
}
```

### Rate Limit Error Response

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Please try again later.",
    "details": {
      "limit": 100,
      "window": 3600,
      "retry_after": 3600
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_abc123"
  }
}
```

## Rate Limiting

### Check Rate Limit Headers

```bash
curl -X GET "http://localhost:8000/api/v1/assets" \
  -H "Authorization: Bearer <token>" \
  -I

# Response headers include:
# X-RateLimit-Limit: 100
# X-RateLimit-Remaining: 95
# X-RateLimit-Reset: 1642252800
```

### Handle Rate Limit Exceeded

```python
import requests
import time

def api_request_with_retry(url, headers, max_retries=3):
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)
        
        if response.status_code == 429:
            # Rate limited, wait and retry
            retry_after = int(response.headers.get('Retry-After', 60))
            time.sleep(retry_after)
            continue
        
        return response
    
    raise Exception("Max retries exceeded")
```

## Health Checks

### Basic Health Check

```bash
# Check API health
curl -X GET "http://localhost:8000/health"

# Response
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0",
  "environment": "production"
}
```

### Detailed Health Check

```bash
# Get detailed health information
curl -X GET "http://localhost:8000/health/detailed"

# Response
{
  "status": "healthy",
  "checks": {
    "database": "healthy",
    "redis": "healthy",
    "storage": "healthy",
    "downstream_services": {
      "user-management": "healthy",
      "asset-management": "healthy",
      "search-engine": "healthy"
    }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Service Status

```bash
# Get gateway status
curl -X GET "http://localhost:8000/api/status"

# Response
{
  "gateway": {
    "status": "healthy",
    "version": "1.0.0",
    "environment": "production",
    "uptime": 86400
  },
  "services": {
    "total_instances": 12,
    "healthy_instances": 11,
    "unhealthy_instances": 1
  }
}
```

## User Management

### User Registration

```bash
# Register new user
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123",
    "first_name": "John",
    "last_name": "Doe",
    "organization": "Acme Corp"
  }'
```

### User Profile

```bash
# Get user profile
curl -X GET "http://localhost:8000/api/v1/users/profile" \
  -H "Authorization: Bearer <token>"

# Update user profile
curl -X PATCH "http://localhost:8000/api/v1/users/profile" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Jane",
    "preferences": {
      "theme": "dark",
      "language": "en"
    }
  }'
```

### Password Reset

```bash
# Request password reset
curl -X POST "http://localhost:8000/api/v1/auth/password-reset" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com"
  }'

# Confirm password reset
curl -X POST "http://localhost:8000/api/v1/auth/password-reset/confirm" \
  -H "Content-Type: application/json" \
  -d '{
    "token": "reset-token-here",
    "new_password": "newpassword123"
  }'
```

## Asset Management

### Upload Asset

```bash
# Upload new asset
curl -X POST "http://localhost:8000/api/v1/assets" \
  -H "Authorization: Bearer <token>" \
  -F "file=@video.mp4" \
  -F "metadata={\"name\":\"My Video\",\"description\":\"A sample video file\"}"

# Response
{
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "My Video",
    "type": "video",
    "size": 1048576,
    "status": "processing",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

### Get Asset Details

```bash
# Get asset by ID
curl -X GET "http://localhost:8000/api/v1/assets/123e4567-e89b-12d3-a456-426614174000" \
  -H "Authorization: Bearer <token>"

# Get asset with metadata
curl -X GET "http://localhost:8000/api/v1/assets/123e4567-e89b-12d3-a456-426614174000?include=metadata,versions" \
  -H "Authorization: Bearer <token>"
```

### Update Asset

```bash
# Update asset metadata
curl -X PATCH "http://localhost:8000/api/v1/assets/123e4567-e89b-12d3-a456-426614174000" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Video Title",
    "description": "Updated description",
    "tags": ["video", "marketing", "2024"]
  }'
```

### Delete Asset

```bash
# Soft delete asset
curl -X DELETE "http://localhost:8000/api/v1/assets/123e4567-e89b-12d3-a456-426614174000" \
  -H "Authorization: Bearer <token>"

# Hard delete asset (admin only)
curl -X DELETE "http://localhost:8000/api/v1/assets/123e4567-e89b-12d3-a456-426614174000?hard=true" \
  -H "Authorization: Bearer <token>"
```

### Asset Versioning

```bash
# Create new version
curl -X POST "http://localhost:8000/api/v1/assets/123e4567-e89b-12d3-a456-426614174000/versions" \
  -H "Authorization: Bearer <token>" \
  -F "file=@video_v2.mp4" \
  -F "metadata={\"version_notes\":\"Updated with better quality\"}"

# Get version history
curl -X GET "http://localhost:8000/api/v1/assets/123e4567-e89b-12d3-a456-426614174000/versions" \
  -H "Authorization: Bearer <token>"
```

## Search Operations

### Basic Search

```bash
# Search assets
curl -X GET "http://localhost:8000/api/v1/search?q=video&type=asset" \
  -H "Authorization: Bearer <token>"

# Response
{
  "data": {
    "results": [...],
    "total": 42,
    "took": 15,
    "query": "video"
  },
  "meta": {
    "page": 1,
    "limit": 20
  }
}
```

### Advanced Search

```bash
# Advanced search with filters
curl -X POST "http://localhost:8000/api/v1/search/advanced" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "marketing video",
    "filters": {
      "type": ["video"],
      "created_after": "2024-01-01",
      "tags": ["marketing", "social"]
    },
    "sort": {
      "field": "relevance",
      "order": "desc"
    },
    "facets": ["type", "tags", "created_date"]
  }'
```

### Search Suggestions

```bash
# Get search suggestions
curl -X GET "http://localhost:8000/api/v1/search/suggestions?q=vide" \
  -H "Authorization: Bearer <token>"

# Response
{
  "data": {
    "suggestions": ["video", "videos", "video marketing", "video tutorial"]
  }
}
```

## Administrative Operations

### System Statistics

```bash
# Get system statistics (admin only)
curl -X GET "http://localhost:8000/api/v1/admin/stats" \
  -H "Authorization: Bearer <admin-token>"

# Response
{
  "data": {
    "users": {
      "total": 1250,
      "active": 892,
      "new_this_month": 45
    },
    "assets": {
      "total": 15420,
      "storage_used": "2.5TB",
      "processed_today": 89
    },
    "system": {
      "uptime": 2592000,
      "memory_usage": "75%",
      "cpu_usage": "45%"
    }
  }
}
```

### Rate Limit Management

```bash
# Get rate limit configuration
curl -X GET "http://localhost:8000/api/v1/admin/rate-limits" \
  -H "Authorization: Bearer <admin-token>"

# Update rate limits
curl -X POST "http://localhost:8000/api/v1/admin/rate-limits" \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "endpoint": "/api/v1/assets",
    "limit": 200,
    "window": 3600
  }'
```

### IP Whitelist Management

```bash
# Get IP whitelist status
curl -X GET "http://localhost:8000/api/v1/ip-whitelist/status" \
  -H "Authorization: Bearer <admin-token>"

# Add IP to whitelist
curl -X POST "http://localhost:8000/api/v1/ip-whitelist/ip/add" \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "ip": "192.168.1.100",
    "list_type": "allowed",
    "description": "Office network"
  }'
```

### Security Headers Management

```bash
# Get security configuration
curl -X GET "http://localhost:8000/api/v1/security/config" \
  -H "Authorization: Bearer <admin-token>"

# Update security configuration
curl -X POST "http://localhost:8000/api/v1/security/config/update" \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "csp_report_only": false,
    "log_security_headers": true
  }'
```

## SDK Examples

### Python SDK

```python
import requests
from typing import Dict, Any, Optional

class MAMSClient:
    def __init__(self, base_url: str, token: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.session = requests.Session()
        
        if token:
            self.session.headers.update({
                'Authorization': f'Bearer {token}'
            })
    
    def login(self, username: str, password: str) -> Dict[str, Any]:
        """Login and get access token"""
        response = self.session.post(
            f"{self.base_url}/api/v1/auth/login",
            json={
                "username": username,
                "password": password
            }
        )
        response.raise_for_status()
        
        data = response.json()
        self.token = data['data']['access_token']
        self.session.headers.update({
            'Authorization': f'Bearer {self.token}'
        })
        
        return data
    
    def get_assets(self, **params) -> Dict[str, Any]:
        """Get assets with optional parameters"""
        response = self.session.get(
            f"{self.base_url}/api/v1/assets",
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def upload_asset(self, file_path: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Upload an asset"""
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {'metadata': json.dumps(metadata)}
            
            response = self.session.post(
                f"{self.base_url}/api/v1/assets",
                files=files,
                data=data
            )
            response.raise_for_status()
            return response.json()
    
    def search(self, query: str, **params) -> Dict[str, Any]:
        """Search assets"""
        params['q'] = query
        response = self.session.get(
            f"{self.base_url}/api/v1/search",
            params=params
        )
        response.raise_for_status()
        return response.json()

# Usage example
client = MAMSClient("http://localhost:8000")
client.login("user@example.com", "password123")

# Get assets
assets = client.get_assets(limit=10, type="video")
print(f"Found {len(assets['data'])} assets")

# Upload asset
result = client.upload_asset(
    "video.mp4",
    {"name": "My Video", "description": "Sample video"}
)
print(f"Uploaded asset: {result['data']['id']}")

# Search
search_results = client.search("marketing video")
print(f"Search found {search_results['data']['total']} results")
```

### JavaScript SDK

```javascript
class MAMSClient {
    constructor(baseUrl, token = null) {
        this.baseUrl = baseUrl.replace(/\/$/, '');
        this.token = token;
        this.headers = {
            'Content-Type': 'application/json',
            ...(token && { 'Authorization': `Bearer ${token}` })
        };
    }
    
    async login(username, password) {
        const response = await fetch(`${this.baseUrl}/api/v1/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        if (!response.ok) {
            throw new Error(`Login failed: ${response.statusText}`);
        }
        
        const data = await response.json();
        this.token = data.data.access_token;
        this.headers.Authorization = `Bearer ${this.token}`;
        
        return data;
    }
    
    async getAssets(params = {}) {
        const url = new URL(`${this.baseUrl}/api/v1/assets`);
        Object.entries(params).forEach(([key, value]) => {
            url.searchParams.append(key, value);
        });
        
        const response = await fetch(url, {
            headers: this.headers
        });
        
        if (!response.ok) {
            throw new Error(`Failed to get assets: ${response.statusText}`);
        }
        
        return response.json();
    }
    
    async uploadAsset(file, metadata) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('metadata', JSON.stringify(metadata));
        
        const response = await fetch(`${this.baseUrl}/api/v1/assets`, {
            method: 'POST',
            headers: {
                'Authorization': this.headers.Authorization
            },
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`Upload failed: ${response.statusText}`);
        }
        
        return response.json();
    }
    
    async search(query, params = {}) {
        const url = new URL(`${this.baseUrl}/api/v1/search`);
        url.searchParams.append('q', query);
        Object.entries(params).forEach(([key, value]) => {
            url.searchParams.append(key, value);
        });
        
        const response = await fetch(url, {
            headers: this.headers
        });
        
        if (!response.ok) {
            throw new Error(`Search failed: ${response.statusText}`);
        }
        
        return response.json();
    }
}

// Usage example
const client = new MAMSClient('http://localhost:8000');

// Login
await client.login('user@example.com', 'password123');

// Get assets
const assets = await client.getAssets({ limit: 10, type: 'video' });
console.log(`Found ${assets.data.length} assets`);

// Upload asset
const fileInput = document.getElementById('file-input');
const file = fileInput.files[0];
const result = await client.uploadAsset(file, {
    name: 'My Video',
    description: 'Sample video'
});
console.log(`Uploaded asset: ${result.data.id}`);

// Search
const searchResults = await client.search('marketing video');
console.log(`Search found ${searchResults.data.total} results`);
```

## Error Handling Best Practices

### Python Error Handling

```python
import requests
from requests.exceptions import RequestException

def handle_api_response(response):
    """Handle API response with proper error handling"""
    try:
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if response.status_code == 400:
            error_data = response.json()
            raise ValueError(f"Bad request: {error_data['error']['message']}")
        elif response.status_code == 401:
            raise PermissionError("Authentication required")
        elif response.status_code == 403:
            raise PermissionError("Access forbidden")
        elif response.status_code == 404:
            raise ValueError("Resource not found")
        elif response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            raise Exception(f"Rate limited. Retry after {retry_after} seconds")
        else:
            raise Exception(f"HTTP error: {e}")
    except RequestException as e:
        raise Exception(f"Request failed: {e}")

# Usage
try:
    response = requests.get("http://localhost:8000/api/v1/assets")
    data = handle_api_response(response)
    print(data)
except ValueError as e:
    print(f"Validation error: {e}")
except PermissionError as e:
    print(f"Permission error: {e}")
except Exception as e:
    print(f"General error: {e}")
```

### JavaScript Error Handling

```javascript
async function handleApiResponse(response) {
    if (!response.ok) {
        const errorData = await response.json();
        
        switch (response.status) {
            case 400:
                throw new Error(`Bad request: ${errorData.error.message}`);
            case 401:
                throw new Error('Authentication required');
            case 403:
                throw new Error('Access forbidden');
            case 404:
                throw new Error('Resource not found');
            case 429:
                const retryAfter = response.headers.get('Retry-After') || 60;
                throw new Error(`Rate limited. Retry after ${retryAfter} seconds`);
            default:
                throw new Error(`HTTP error: ${response.status} ${response.statusText}`);
        }
    }
    
    return response.json();
}

// Usage
try {
    const response = await fetch('http://localhost:8000/api/v1/assets');
    const data = await handleApiResponse(response);
    console.log(data);
} catch (error) {
    console.error('API error:', error.message);
}
```

This comprehensive API documentation provides examples for all major operations and demonstrates best practices for error handling, authentication, and common patterns. Use these examples as starting points for integrating with the MAMS API Gateway.