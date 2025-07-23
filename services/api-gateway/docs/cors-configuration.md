# CORS Configuration Guide

## Overview

Cross-Origin Resource Sharing (CORS) is a security feature implemented by web browsers to control access to resources from different origins. The MAMS API Gateway provides comprehensive CORS configuration to ensure secure cross-origin access while maintaining flexibility for different environments.

## What is CORS?

CORS is a mechanism that allows restricted resources on a web page to be requested from another domain outside the domain from which the first resource was served. It's a crucial security feature for modern web applications.

### Key Concepts

- **Origin**: The combination of protocol, domain, and port (e.g., `https://example.com:443`)
- **Preflight Request**: An OPTIONS request sent by browsers to check if the actual request is allowed
- **Simple Request**: Requests that don't trigger preflight (GET, HEAD, POST with certain content types)
- **Credentials**: Cookies, authorization headers, and TLS client certificates

## Configuration

### Environment Variables

Configure CORS using the following environment variables:

```env
# Allowed origins (comma-separated)
CORS_ORIGINS=https://app.mams.com,https://admin.mams.com

# Origin patterns (regex, comma-separated)
CORS_ORIGIN_PATTERNS=https://.*\.mams\.com,https://.*\.staging\.mams\.com

# Allow credentials (cookies, auth headers)
CORS_ALLOW_CREDENTIALS=true

# Allowed HTTP methods (comma-separated)
CORS_ALLOWED_METHODS=GET,POST,PUT,DELETE,OPTIONS,PATCH,HEAD

# Allowed request headers (comma-separated, or * for all)
CORS_ALLOWED_HEADERS=Content-Type,Authorization,X-API-Key,X-Request-ID

# Headers exposed to browser (comma-separated)
CORS_EXPOSED_HEADERS=X-Total-Count,X-Page-Count,X-Request-ID

# Preflight cache duration in seconds (24 hours)
CORS_MAX_AGE=86400
```

### Environment-Specific Configurations

#### Development Environment

```env
ENVIRONMENT=development
CORS_ORIGINS=*  # Allow all origins for development
CORS_ALLOW_CREDENTIALS=true
```

**Note**: Using wildcard (`*`) is only recommended for development environments.

#### Staging Environment

```env
ENVIRONMENT=staging
CORS_ORIGINS=https://staging.mams.com,https://staging-app.mams.com
CORS_ORIGIN_PATTERNS=https://.*\.staging\.mams\.com
CORS_ALLOW_CREDENTIALS=true
```

#### Production Environment

```env
ENVIRONMENT=production
CORS_ORIGINS=https://app.mams.com,https://www.mams.com
CORS_ORIGIN_PATTERNS=
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOWED_HEADERS=Content-Type,Authorization,X-API-Key,X-Request-ID,X-Client-Version
```

## How CORS Works

### 1. Simple Requests

For simple requests (GET, HEAD, or POST with specific content types), the browser sends the request directly:

```http
GET /api/v1/users HTTP/1.1
Host: api.mams.com
Origin: https://app.mams.com
```

The server responds with CORS headers:

```http
HTTP/1.1 200 OK
Access-Control-Allow-Origin: https://app.mams.com
Access-Control-Allow-Credentials: true
Access-Control-Expose-Headers: X-Total-Count, X-Request-ID
```

### 2. Preflight Requests

For complex requests, browsers send a preflight OPTIONS request first:

```http
OPTIONS /api/v1/users HTTP/1.1
Host: api.mams.com
Origin: https://app.mams.com
Access-Control-Request-Method: PUT
Access-Control-Request-Headers: Content-Type, Authorization
```

The server responds with allowed methods and headers:

```http
HTTP/1.1 200 OK
Access-Control-Allow-Origin: https://app.mams.com
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS, PATCH
Access-Control-Allow-Headers: Content-Type, Authorization
Access-Control-Allow-Credentials: true
Access-Control-Max-Age: 86400
```

## API Endpoints

### Get CORS Configuration

```http
GET /api/v1/cors/config
Authorization: Bearer {admin_token}
```

Response:
```json
{
  "allowed_origins": ["https://app.mams.com"],
  "allowed_origin_patterns": ["https://.*\\.mams\\.com"],
  "allowed_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
  "allowed_headers": ["Content-Type", "Authorization", "X-API-Key"],
  "exposed_headers": ["X-Total-Count", "X-Request-ID"],
  "allow_credentials": true,
  "max_age": 86400,
  "environment": "production",
  "is_permissive": false
}
```

### Validate Origin

```http
POST /api/v1/cors/validate-origin?origin=https://app.mams.com
Authorization: Bearer {admin_token}
```

Response:
```json
{
  "origin": "https://app.mams.com",
  "is_allowed": true,
  "reason": "Allowed by configuration"
}
```

### Test CORS

```http
GET /api/v1/cors/test
Origin: https://app.mams.com
```

This endpoint can be used from browser applications to test CORS configuration.

## Common Issues and Solutions

### Issue 1: "No 'Access-Control-Allow-Origin' header"

**Causes**:
- Origin not in allowed list
- CORS middleware not configured
- Request missing Origin header

**Solutions**:
1. Add origin to `CORS_ORIGINS`
2. Check middleware configuration
3. Ensure browser sends Origin header

### Issue 2: "CORS policy: credentials mode is 'include'"

**Causes**:
- Using wildcard (`*`) with credentials
- `CORS_ALLOW_CREDENTIALS` not set to true

**Solutions**:
1. Use specific origins instead of wildcard
2. Set `CORS_ALLOW_CREDENTIALS=true`

### Issue 3: "Method not allowed by CORS"

**Causes**:
- HTTP method not in `CORS_ALLOWED_METHODS`
- Preflight request failing

**Solutions**:
1. Add method to `CORS_ALLOWED_METHODS`
2. Check preflight response

### Issue 4: "Request header not allowed"

**Causes**:
- Custom header not in `CORS_ALLOWED_HEADERS`
- Using wildcard incorrectly

**Solutions**:
1. Add header to `CORS_ALLOWED_HEADERS`
2. Or use `CORS_ALLOWED_HEADERS=*`

## Security Best Practices

### 1. Never Use Wildcard in Production

```env
# Bad for production
CORS_ORIGINS=*

# Good for production
CORS_ORIGINS=https://app.mams.com,https://admin.mams.com
```

### 2. Be Specific with Origins

Instead of broad patterns, use specific origins when possible:

```env
# Less secure
CORS_ORIGIN_PATTERNS=https://.*

# More secure
CORS_ORIGIN_PATTERNS=https://.*\.mams\.com
```

### 3. Limit Allowed Headers

Only allow headers your API actually uses:

```env
# Too permissive
CORS_ALLOWED_HEADERS=*

# Better
CORS_ALLOWED_HEADERS=Content-Type,Authorization,X-API-Key,X-Request-ID
```

### 4. Use HTTPS in Production

Always require HTTPS for production origins:

```env
# Good
CORS_ORIGINS=https://app.mams.com

# Bad (unless for local development)
CORS_ORIGINS=http://app.mams.com
```

### 5. Regular Audits

Periodically review and clean up allowed origins:
- Remove unused origins
- Update patterns as needed
- Check for overly permissive configurations

## Testing CORS

### Using cURL

Test preflight request:
```bash
curl -X OPTIONS \
  -H "Origin: https://app.mams.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -i https://api.mams.com/api/v1/users
```

Test actual request:
```bash
curl -X POST \
  -H "Origin: https://app.mams.com" \
  -H "Content-Type: application/json" \
  -d '{"name":"test"}' \
  -i https://api.mams.com/api/v1/users
```

### Using Browser Console

```javascript
// Test from browser console
fetch('https://api.mams.com/api/v1/cors/test', {
  method: 'GET',
  credentials: 'include',
  headers: {
    'Content-Type': 'application/json'
  }
})
.then(response => response.json())
.then(data => console.log(data))
.catch(error => console.error('CORS error:', error));
```

### Browser Developer Tools

1. Open Network tab in browser developer tools
2. Look for OPTIONS requests (preflight)
3. Check response headers for CORS headers
4. Look for CORS errors in console

## Integration Examples

### React Application

```javascript
// Configure fetch for CORS
const apiCall = async () => {
  const response = await fetch('https://api.mams.com/api/v1/users', {
    method: 'GET',
    credentials: 'include',  // Include cookies
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    }
  });
  
  if (!response.ok) {
    throw new Error('API request failed');
  }
  
  return response.json();
};
```

### Axios Configuration

```javascript
// Configure axios for CORS
import axios from 'axios';

const api = axios.create({
  baseURL: 'https://api.mams.com/api/v1',
  withCredentials: true,  // Include cookies
  headers: {
    'Content-Type': 'application/json'
  }
});

// Add auth token
api.interceptors.request.use(config => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

### Angular HttpClient

```typescript
// Configure Angular HttpClient for CORS
import { HttpClient, HttpHeaders } from '@angular/common/http';

const httpOptions = {
  headers: new HttpHeaders({
    'Content-Type': 'application/json'
  }),
  withCredentials: true  // Include cookies
};

this.http.get<any>('https://api.mams.com/api/v1/users', httpOptions)
  .subscribe(data => console.log(data));
```

## Troubleshooting Checklist

1. **Check Origin Header**
   - Is the Origin header being sent?
   - Is it in the allowed list?

2. **Verify Configuration**
   - Check environment variables
   - Confirm middleware is loaded

3. **Test Preflight**
   - Use cURL to test OPTIONS request
   - Check response headers

4. **Browser Console**
   - Look for CORS errors
   - Check network tab

5. **Server Logs**
   - Check for CORS warnings
   - Look for configuration errors

## Advanced Features

### Dynamic Origin Validation

The MAMS API Gateway supports regex patterns for dynamic origin validation:

```env
# Allow all subdomains
CORS_ORIGIN_PATTERNS=https://.*\.mams\.com

# Allow specific subdomain patterns
CORS_ORIGIN_PATTERNS=https://(app|admin|api)\.mams\.com

# Multiple patterns
CORS_ORIGIN_PATTERNS=https://.*\.mams\.com,https://.*\.partner\.com
```

### Custom Headers

Expose custom headers to browser applications:

```env
CORS_EXPOSED_HEADERS=X-Total-Count,X-Page-Count,X-Request-ID,X-RateLimit-Remaining
```

### Conditional CORS

The gateway can apply different CORS policies based on:
- Environment (dev, staging, production)
- API version
- Authentication status
- Request path

## Monitoring and Logging

The API Gateway logs CORS-related events:

- Blocked requests from unauthorized origins
- Preflight request handling
- Origin validation results
- Configuration changes

Check logs for CORS issues:
```bash
grep "CORS" /var/log/api-gateway/app.log
```

## Migration Guide

### Moving from Development to Production

1. **Update Origins**:
   ```env
   # From
   CORS_ORIGINS=*
   
   # To
   CORS_ORIGINS=https://app.yourcompany.com
   ```

2. **Restrict Headers**:
   ```env
   # From
   CORS_ALLOWED_HEADERS=*
   
   # To
   CORS_ALLOWED_HEADERS=Content-Type,Authorization,X-API-Key
   ```

3. **Remove Patterns** (if not needed):
   ```env
   # From
   CORS_ORIGIN_PATTERNS=https://.*
   
   # To
   CORS_ORIGIN_PATTERNS=
   ```

4. **Test Thoroughly**:
   - Test from actual domain
   - Verify all features work
   - Check for CORS errors

## References

- [MDN Web Docs - CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
- [CORS Specification](https://www.w3.org/TR/cors/)
- [OWASP CORS Security](https://owasp.org/www-community/attacks/CORS_OriginHeaderScrutiny)