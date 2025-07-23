# API Gateway Authentication Guide

## Overview

The MAMS API Gateway implements a comprehensive JWT-based authentication system with support for refresh tokens, API keys, and fine-grained permissions.

## Authentication Methods

### 1. JWT Token Authentication (Primary)

The gateway uses JWT (JSON Web Tokens) for stateless authentication. Tokens are issued after successful login and must be included in the Authorization header for protected endpoints.

#### Token Types

- **Access Token**: Short-lived token (1 hour) for API access
- **Refresh Token**: Long-lived token (30 days) for obtaining new access tokens

#### Token Structure

```json
{
  "sub": "username",
  "user_id": "uuid",
  "permissions": ["read", "write", "admin"],
  "exp": 1640995200,
  "iat": 1640991600,
  "type": "access"
}
```

### 2. API Key Authentication (Secondary)

API keys can be used for service-to-service communication or automated systems. They are passed in the `X-API-Key` header.

## Authentication Flow

### 1. User Login

```mermaid
sequenceDiagram
    participant Client
    participant Gateway
    participant UserService
    participant Redis
    
    Client->>Gateway: POST /api/v1/auth/login
    Gateway->>UserService: Validate credentials
    UserService-->>Gateway: User data + permissions
    Gateway->>Redis: Store refresh token
    Gateway-->>Client: Access + Refresh tokens
```

### 2. Token Refresh

```mermaid
sequenceDiagram
    participant Client
    participant Gateway
    participant Redis
    participant UserService
    
    Client->>Gateway: POST /api/v1/auth/refresh
    Gateway->>Gateway: Verify refresh token
    Gateway->>Redis: Check token validity
    Gateway->>UserService: Get user permissions
    Gateway-->>Client: New access token
```

## API Endpoints

### Authentication Endpoints

#### Login
```http
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=testuser&password=secretpassword
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "username": "testuser",
  "permissions": ["assets.read", "assets.write"]
}
```

#### Register
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "username": "newuser",
  "email": "user@example.com",
  "password": "SecureP@ssw0rd123",
  "full_name": "New User"
}
```

#### Refresh Token
```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

#### Logout
```http
POST /api/v1/auth/logout
Authorization: Bearer <access_token>
```

#### Get Current User
```http
GET /api/v1/auth/me
Authorization: Bearer <access_token>
```

#### Change Password
```http
POST /api/v1/auth/change-password
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "old_password": "currentpassword",
  "new_password": "NewSecureP@ssw0rd123"
}
```

#### Request Password Reset
```http
POST /api/v1/auth/request-password-reset
Content-Type: application/json

{
  "email": "user@example.com"
}
```

#### Confirm Password Reset
```http
POST /api/v1/auth/reset-password
Content-Type: application/json

{
  "token": "reset-token-from-email",
  "new_password": "NewSecureP@ssw0rd123"
}
```

#### Validate Token
```http
POST /api/v1/auth/validate-token
Authorization: Bearer <access_token>
```

## Using Authentication

### 1. Include Token in Requests

After login, include the access token in the Authorization header:

```http
GET /api/v1/assets
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

### 2. Handle Token Expiration

When the access token expires (401 response), use the refresh token to get a new one:

```javascript
async function makeAuthenticatedRequest(url, options = {}) {
  let response = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${getAccessToken()}`
    }
  });
  
  if (response.status === 401) {
    // Token expired, try to refresh
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      // Retry with new token
      response = await fetch(url, {
        ...options,
        headers: {
          ...options.headers,
          'Authorization': `Bearer ${getAccessToken()}`
        }
      });
    }
  }
  
  return response;
}
```

### 3. API Key Usage

For service-to-service communication:

```http
GET /api/v1/assets
X-API-Key: your-api-key-here
```

## Security Features

### 1. Password Requirements

Passwords must meet the following criteria:
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character (!@#$%^&*)

### 2. Token Security

- **Access tokens** expire after 1 hour
- **Refresh tokens** expire after 30 days
- Tokens are blacklisted on logout
- Tokens include user permissions for authorization

### 3. Rate Limiting

Authentication endpoints have specific rate limits:
- Login: 5 attempts per minute per IP
- Register: 3 attempts per minute per IP
- Password reset: 3 attempts per hour per email

### 4. Security Headers

The gateway adds security headers to all responses:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000`

## Permission System

### Permission Format

Permissions follow the format: `resource.action`

Examples:
- `assets.read` - Read access to assets
- `assets.write` - Write access to assets
- `users.admin` - Admin access to user management
- `*.admin` - Global admin access

### Checking Permissions

The gateway validates permissions on each request. To require specific permissions:

```python
from api.auth import require_permission

@router.get("/admin/users")
async def get_users(
    current_user: Dict = Depends(require_permission("users.admin"))
):
    # Only users with 'users.admin' permission can access
    pass
```

## Error Handling

### Authentication Errors

| Status Code | Error Code | Description |
|-------------|-----------|-------------|
| 401 | `AUTHENTICATION_REQUIRED` | No authentication provided |
| 401 | `INVALID_TOKEN` | Token is invalid or expired |
| 401 | `TOKEN_REVOKED` | Token has been revoked |
| 403 | `INSUFFICIENT_PERMISSIONS` | User lacks required permissions |
| 429 | `RATE_LIMIT_EXCEEDED` | Too many authentication attempts |

### Error Response Format

```json
{
  "error": {
    "code": "INVALID_TOKEN",
    "message": "Token has expired",
    "details": {
      "expired_at": "2024-01-15T10:30:00Z"
    },
    "timestamp": 1640995200,
    "request_id": "req_abc123"
  }
}
```

## Best Practices

### 1. Token Storage

**Client-side:**
- Store access token in memory or sessionStorage
- Store refresh token in httpOnly cookie or secure storage
- Never store tokens in localStorage for sensitive applications

**Server-side:**
- Use Redis for token blacklisting
- Implement token rotation on refresh
- Log all authentication events

### 2. Security Recommendations

1. **Use HTTPS** in production
2. **Implement CSRF protection** for web applications
3. **Rotate secrets** regularly
4. **Monitor failed login attempts**
5. **Implement account lockout** after repeated failures
6. **Use strong JWT secrets** (minimum 32 characters)

### 3. Integration Examples

#### Python (requests)
```python
import requests

# Login
response = requests.post(
    "https://api.mams.com/api/v1/auth/login",
    data={"username": "user", "password": "pass"}
)
tokens = response.json()

# Use token
headers = {"Authorization": f"Bearer {tokens['access_token']}"}
assets = requests.get(
    "https://api.mams.com/api/v1/assets",
    headers=headers
)
```

#### JavaScript (fetch)
```javascript
// Login
const response = await fetch('https://api.mams.com/api/v1/auth/login', {
  method: 'POST',
  headers: {'Content-Type': 'application/x-www-form-urlencoded'},
  body: 'username=user&password=pass'
});
const tokens = await response.json();

// Use token
const assets = await fetch('https://api.mams.com/api/v1/assets', {
  headers: {
    'Authorization': `Bearer ${tokens.access_token}`
  }
});
```

#### cURL
```bash
# Login
curl -X POST https://api.mams.com/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user&password=pass"

# Use token
curl -X GET https://api.mams.com/api/v1/assets \
  -H "Authorization: Bearer <access_token>"
```

## Configuration

### Environment Variables

```env
# JWT Configuration
JWT_SECRET_KEY=your-very-secret-key-minimum-32-chars
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60
REFRESH_TOKEN_EXPIRATION_DAYS=30

# Authentication Settings
AUTH_HEADER_NAME=Authorization
AUTH_HEADER_PREFIX=Bearer
API_KEY_HEADER_NAME=X-API-Key

# Security
ENABLE_API_KEYS=true
ENABLE_MFA=false
PASSWORD_MIN_LENGTH=8
```

## Troubleshooting

### Common Issues

1. **"Invalid token" error**
   - Check token expiration
   - Verify token format (Bearer prefix)
   - Ensure token hasn't been blacklisted

2. **"Authentication required" on public endpoints**
   - Check middleware exclusion list
   - Verify endpoint configuration

3. **"Rate limit exceeded"**
   - Wait for rate limit window to reset
   - Check Redis connection for rate limiting

4. **Token refresh fails**
   - Ensure refresh token is valid
   - Check if refresh token exists in cache
   - Verify user still has permissions

## Advanced Features

### Multi-Factor Authentication (MFA)

*Coming in future release*

### OAuth2 / SAML Integration

*Coming in future release*

### API Key Management

*Coming in future release*