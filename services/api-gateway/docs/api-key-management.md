# API Key Management

The MAMS API Gateway provides comprehensive API key management capabilities for secure, programmatic access to the system. This guide covers API key creation, management, and usage.

## Overview

API keys provide an alternative authentication method to JWT tokens, ideal for:
- Server-to-server communication
- CI/CD pipelines
- Third-party integrations
- Automated tools and scripts
- Mobile and desktop applications

## Key Features

### Security Features
- **Secure Generation**: Keys use cryptographically secure random generation
- **Hashed Storage**: Keys are hashed with SHA-256 before storage
- **Scoped Permissions**: Fine-grained access control with scopes
- **Expiration Support**: Optional expiration dates
- **Revocation**: Immediate key deactivation
- **Rotation**: Safe key rotation with rollover period

### Management Features
- **Usage Tracking**: Detailed usage statistics and analytics
- **Rate Limiting**: Per-key rate limit overrides
- **Audit Logging**: Complete audit trail of key operations
- **Metadata Support**: Custom metadata for organization
- **Admin Controls**: Administrative oversight and bulk operations

## API Key Format

API keys follow this format:
```
mams_<32-character-random-string>
```

**Example:**
```
mams_k7x9p2w5q8r3m6j4n1v8c9z2b5g7h0
```

## Scopes and Permissions

### Available Scopes
- `read` - Read access to resources
- `write` - Create and update resources
- `delete` - Delete resources
- `upload` - Upload files and assets
- `download` - Download files and assets
- `admin` - Administrative access

### Scope Combinations
- **Read-only**: `["read"]`
- **Standard**: `["read", "write", "upload", "download"]`
- **Admin**: `["read", "write", "upload", "download", "delete", "admin"]`

## API Endpoints

### Authentication

All API key management endpoints require JWT authentication (except for actual API key usage).

### Create API Key

```http
POST /api/v1/api-keys
Content-Type: application/json
Authorization: Bearer <jwt-token>

{
  "name": "My Application Key",
  "description": "API key for my application",
  "scopes": ["read", "write", "upload"],
  "expires_in_days": 90,
  "rate_limit_override": 1000,
  "metadata": {
    "application": "my-app",
    "environment": "production"
  }
}
```

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "key": "mams_k7x9p2w5q8r3m6j4n1v8c9z2b5g7h0",
  "name": "My Application Key",
  "description": "API key for my application",
  "prefix": "mams_",
  "last_four": "7h0",
  "scopes": ["read", "write", "upload"],
  "expires_at": "2024-04-15T10:30:00Z",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "last_used_at": null,
  "usage_count": 0
}
```

**⚠️ Important:** The raw API key is only returned during creation. Store it securely!

### List API Keys

```http
GET /api/v1/api-keys?skip=0&limit=20&is_active=true
Authorization: Bearer <jwt-token>
```

**Response:**
```json
{
  "items": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "key": null,
      "name": "My Application Key",
      "description": "API key for my application",
      "prefix": "mams_",
      "last_four": "7h0",
      "scopes": ["read", "write", "upload"],
      "expires_at": "2024-04-15T10:30:00Z",
      "is_active": true,
      "created_at": "2024-01-15T10:30:00Z",
      "last_used_at": "2024-01-16T14:22:00Z",
      "usage_count": 157
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 20
}
```

### Get API Key Details

```http
GET /api/v1/api-keys/{key-id}
Authorization: Bearer <jwt-token>
```

### Update API Key

```http
PATCH /api/v1/api-keys/{key-id}
Content-Type: application/json
Authorization: Bearer <jwt-token>

{
  "name": "Updated Key Name",
  "description": "Updated description",
  "scopes": ["read", "write"],
  "rate_limit_override": 500
}
```

### Revoke API Key

```http
DELETE /api/v1/api-keys/{key-id}?reason=No longer needed
Authorization: Bearer <jwt-token>
```

### Rotate API Key

```http
POST /api/v1/api-keys/{key-id}/rotate?revoke_old=true
Authorization: Bearer <jwt-token>
```

**Response:**
```json
{
  "old_key_id": "123e4567-e89b-12d3-a456-426614174000",
  "old_key_revoked": true,
  "new_key": {
    "id": "456e7890-e12b-34c5-d678-901234567890",
    "key": "mams_n2x8p5w9q3r6m1j7n4v2c8z5b9g3h6",
    "name": "My Application Key (rotated)",
    "prefix": "mams_",
    "last_four": "3h6",
    "scopes": ["read", "write", "upload"],
    "expires_at": "2024-04-15T10:30:00Z",
    "is_active": true,
    "created_at": "2024-01-17T10:30:00Z",
    "last_used_at": null,
    "usage_count": 0
  }
}
```

### Get Usage Statistics

```http
GET /api/v1/api-keys/{key-id}/usage?days=30
Authorization: Bearer <jwt-token>
```

**Response:**
```json
{
  "total_requests": 1547,
  "successful_requests": 1523,
  "failed_requests": 24,
  "success_rate": 98.45,
  "status_codes": {
    "200": 1245,
    "201": 278,
    "400": 15,
    "401": 3,
    "404": 4,
    "500": 2
  },
  "average_response_time_ms": 245.67,
  "period_days": 30,
  "since": "2024-01-01T00:00:00Z"
}
```

## Using API Keys

### Header Authentication (Recommended)

```http
GET /api/v1/assets
X-API-Key: mams_k7x9p2w5q8r3m6j4n1v8c9z2b5g7h0
```

### Query Parameter Authentication

```http
GET /api/v1/assets?api_key=mams_k7x9p2w5q8r3m6j4n1v8c9z2b5g7h0
```

### Code Examples

#### Python
```python
import requests

api_key = "mams_k7x9p2w5q8r3m6j4n1v8c9z2b5g7h0"
base_url = "https://api.mams.example.com"

# Using headers (recommended)
headers = {
    "X-API-Key": api_key,
    "Content-Type": "application/json"
}

response = requests.get(f"{base_url}/api/v1/assets", headers=headers)
print(response.json())
```

#### JavaScript
```javascript
const apiKey = 'mams_k7x9p2w5q8r3m6j4n1v8c9z2b5g7h0';
const baseUrl = 'https://api.mams.example.com';

// Using headers (recommended)
const response = await fetch(`${baseUrl}/api/v1/assets`, {
  headers: {
    'X-API-Key': apiKey,
    'Content-Type': 'application/json'
  }
});

const data = await response.json();
console.log(data);
```

#### curl
```bash
# Using headers (recommended)
curl -H "X-API-Key: mams_k7x9p2w5q8r3m6j4n1v8c9z2b5g7h0" \
     -H "Content-Type: application/json" \
     https://api.mams.example.com/api/v1/assets

# Using query parameter
curl "https://api.mams.example.com/api/v1/assets?api_key=mams_k7x9p2w5q8r3m6j4n1v8c9z2b5g7h0"
```

## Rate Limiting

### Default Rate Limits
- **Standard Keys**: 100 requests per minute
- **Premium Keys**: 1000 requests per minute
- **Admin Keys**: 10000 requests per minute

### Custom Rate Limits
You can set custom rate limits when creating or updating API keys:

```json
{
  "name": "High Volume Key",
  "rate_limit_override": 5000,
  "scopes": ["read", "write"]
}
```

### Rate Limit Headers
API responses include rate limit information:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

## Security Best Practices

### Key Management
1. **Store Securely**: Never store API keys in code or version control
2. **Use Environment Variables**: Store keys in environment variables
3. **Rotate Regularly**: Rotate keys every 90 days
4. **Principle of Least Privilege**: Grant minimal required scopes
5. **Monitor Usage**: Regularly review usage statistics

### Environment Variables
```bash
# Development
MAMS_API_KEY=mams_dev_k7x9p2w5q8r3m6j4n1v8c9z2b5g7h0

# Production
MAMS_API_KEY=mams_prod_n2x8p5w9q3r6m1j7n4v2c8z5b9g3h6
```

### Key Rotation Strategy
1. **Create New Key**: Generate a new key with same settings
2. **Update Applications**: Deploy new key to all applications
3. **Monitor Usage**: Verify new key is being used
4. **Revoke Old Key**: Deactivate the old key

## Admin Operations

### List All API Keys (Admin)

```http
GET /api/v1/api-keys/admin/all?skip=0&limit=50&user_id=123&is_active=true
X-API-Key: <admin-api-key>
```

### Admin Revoke API Key

```http
DELETE /api/v1/api-keys/admin/{key-id}?reason=Security violation
X-API-Key: <admin-api-key>
```

## Error Handling

### Common Error Responses

#### Invalid API Key
```json
{
  "error": {
    "code": "INVALID_API_KEY",
    "message": "Invalid API key",
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_123456"
  }
}
```

#### API Key Required
```json
{
  "error": {
    "code": "API_KEY_REQUIRED",
    "message": "API key required",
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_123456"
  }
}
```

#### Insufficient Permissions
```json
{
  "error": {
    "code": "INSUFFICIENT_PERMISSIONS",
    "message": "Missing required scopes: delete",
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_123456"
  }
}
```

#### Rate Limit Exceeded
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Try again in 60 seconds.",
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_123456"
  }
}
```

## Monitoring and Analytics

### Usage Metrics
- Total requests per key
- Success/failure rates
- Response times
- Most used endpoints
- Geographic distribution

### Audit Events
- Key creation/update/deletion
- Authentication attempts
- Permission violations
- Rate limit exceeded
- Suspicious activity

### Alerting
Set up alerts for:
- High failure rates
- Unusual usage patterns
- Multiple failed authentication attempts
- Keys approaching expiration

## Integration Examples

### CI/CD Pipeline
```yaml
# GitHub Actions example
name: Deploy to MAMS
steps:
  - name: Upload Assets
    run: |
      curl -H "X-API-Key: ${{ secrets.MAMS_API_KEY }}" \
           -F "file=@./build/assets.zip" \
           https://api.mams.example.com/api/v1/assets/upload
```

### Application Integration
```python
class MAMSClient:
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'X-API-Key': api_key,
            'Content-Type': 'application/json'
        })
    
    def get_assets(self, limit: int = 20) -> dict:
        response = self.session.get(
            f"{self.base_url}/api/v1/assets",
            params={'limit': limit}
        )
        response.raise_for_status()
        return response.json()
```

## Troubleshooting

### Common Issues

1. **401 Unauthorized**
   - Check API key format
   - Verify key is active
   - Confirm key hasn't expired

2. **403 Forbidden**
   - Check required scopes
   - Verify user permissions
   - Confirm key ownership

3. **429 Too Many Requests**
   - Check rate limit headers
   - Implement exponential backoff
   - Consider rate limit override

### Debug Information
Enable debug logging to see:
- API key validation steps
- Scope checking
- Rate limit calculations
- Request routing

## Migration Guide

### From JWT to API Keys
1. Create API key with equivalent permissions
2. Update application configuration
3. Test all functionality
4. Monitor usage patterns
5. Deactivate JWT authentication

### From Other Systems
1. Audit existing key usage
2. Map permissions to MAMS scopes
3. Create equivalent keys
4. Update integrations
5. Migrate gradually

## FAQ

**Q: Can I use both JWT and API keys simultaneously?**
A: Yes, the gateway supports both authentication methods. API key authentication is checked first, followed by JWT if no API key is present.

**Q: How often should I rotate API keys?**
A: We recommend rotating keys every 90 days for production use, or immediately if compromised.

**Q: Can I create API keys programmatically?**
A: Yes, use the POST /api/v1/api-keys endpoint with JWT authentication.

**Q: What happens to usage logs when I revoke a key?**
A: Usage logs are preserved for audit purposes even after key revocation.

**Q: Can I recover a deleted API key?**
A: No, deleted keys cannot be recovered. You must create a new key.

**Q: How do I handle API key rotation in production?**
A: Use the rotation endpoint to create a new key, deploy it to all services, then revoke the old key.

## Support

For additional support:
- API Documentation: `/docs`
- Health Check: `/health`
- Status: `/api/status`
- Contact: api-support@mams.example.com
