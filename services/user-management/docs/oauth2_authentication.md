# OAuth2 Authentication

This document describes the OAuth2 authentication implementation in the User Management Service, providing integration with Google and Microsoft identity providers.

## Overview

The OAuth2 authentication feature allows users to sign in using their existing Google or Microsoft accounts instead of creating local passwords. This provides a seamless login experience and leverages trusted identity providers for authentication.

## Features

- **Google OAuth2**: Authenticate using Google accounts
- **Microsoft OAuth2**: Authenticate using Microsoft/Azure AD accounts
- **User Auto-Creation**: Automatically create local users from OAuth2 accounts
- **User Auto-Update**: Keep local user information synchronized with OAuth2 providers
- **Secure Token Handling**: Proper OAuth2 flow implementation with state validation
- **Provider Testing**: Built-in endpoints to test OAuth2 configuration
- **Flexible Configuration**: Support for multiple tenants and custom scopes

## Supported Providers

### Google OAuth2
- **Provider**: Google Identity Platform
- **Scopes**: `openid`, `email`, `profile`
- **User Info**: Name, email, profile picture, locale
- **Documentation**: [Google OAuth2 Guide](https://developers.google.com/identity/protocols/oauth2)

### Microsoft OAuth2
- **Provider**: Microsoft Azure AD / Office 365
- **Scopes**: `openid`, `email`, `profile`
- **User Info**: Name, email, phone, job title, department, office location
- **Documentation**: [Microsoft OAuth2 Guide](https://docs.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-auth-code-flow)

## Configuration

### Environment Variables

#### Basic OAuth2 Configuration
```bash
# Enable OAuth2 authentication
ENABLE_OAUTH2=true

# OAuth2 behavior settings
OAUTH2_AUTO_CREATE_USER=true
OAUTH2_AUTO_UPDATE_USER=true
OAUTH2_DEFAULT_ROLE=user
OAUTH2_SESSION_TIMEOUT=3600
```

#### Google OAuth2 Configuration
```bash
# Enable Google OAuth2
GOOGLE_OAUTH2_ENABLED=true

# Google OAuth2 credentials (from Google Cloud Console)
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8001/api/v1/oauth2/callback/google

# Google OAuth2 scopes (comma-separated)
GOOGLE_SCOPES=openid,email,profile
```

#### Microsoft OAuth2 Configuration
```bash
# Enable Microsoft OAuth2
MICROSOFT_OAUTH2_ENABLED=true

# Microsoft OAuth2 credentials (from Azure App Registration)
MICROSOFT_CLIENT_ID=your-microsoft-application-id
MICROSOFT_CLIENT_SECRET=your-microsoft-client-secret
MICROSOFT_REDIRECT_URI=http://localhost:8001/api/v1/oauth2/callback/microsoft

# Microsoft tenant (use "common" for multi-tenant)
MICROSOFT_TENANT_ID=common

# Microsoft OAuth2 scopes (comma-separated)
MICROSOFT_SCOPES=openid,email,profile
```

## Provider Setup

### Google OAuth2 Setup

1. **Create Google Cloud Project**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one

2. **Enable Google+ API**:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Google+ API" and enable it

3. **Create OAuth2 Credentials**:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth 2.0 Client IDs"
   - Choose "Web application"
   - Add authorized redirect URIs:
     - `http://localhost:8001/api/v1/oauth2/callback/google` (development)
     - `https://yourdomain.com/api/v1/oauth2/callback/google` (production)

4. **Configure Consent Screen**:
   - Go to "OAuth consent screen"
   - Fill in application details
   - Add scopes: `openid`, `email`, `profile`

### Microsoft OAuth2 Setup

1. **Register Azure AD Application**:
   - Go to [Azure Portal](https://portal.azure.com/)
   - Navigate to "Azure Active Directory" > "App registrations"
   - Click "New registration"

2. **Configure Application**:
   - Name: Your application name
   - Supported account types: Choose based on your needs
     - "Accounts in this organizational directory only" (single tenant)
     - "Accounts in any organizational directory" (multi-tenant)
     - "Accounts in any organizational directory and personal Microsoft accounts" (consumer + business)

3. **Set Redirect URIs**:
   - Go to "Authentication"
   - Add platform: "Web"
   - Add redirect URIs:
     - `http://localhost:8001/api/v1/oauth2/callback/microsoft` (development)
     - `https://yourdomain.com/api/v1/oauth2/callback/microsoft` (production)

4. **Create Client Secret**:
   - Go to "Certificates & secrets"
   - Click "New client secret"
   - Copy the secret value (shown only once)

5. **Configure API Permissions**:
   - Go to "API permissions"
   - Add permissions: Microsoft Graph
   - Add scopes: `openid`, `email`, `profile`
   - Grant admin consent if required

## Usage

### Authentication Flow

1. **Initiate Authentication**:
   ```http
   GET /api/v1/oauth2/auth/{provider}
   ```
   - Returns authorization URL and state parameter
   - User is redirected to provider's login page

2. **Provider Authentication**:
   - User logs in with their provider account
   - Provider redirects back to callback URL with authorization code

3. **Token Exchange**:
   ```http
   GET /api/v1/oauth2/callback/{provider}?code={code}&state={state}
   ```
   - System exchanges code for access token
   - Retrieves user information from provider
   - Creates or updates local user account
   - Returns JWT tokens for API access

### API Endpoints

#### Get Available Providers
```http
GET /api/v1/oauth2/providers
```

Response:
```json
{
    "success": true,
    "data": {
        "providers": ["google", "microsoft"]
    }
}
```

#### Initiate OAuth2 Authentication
```http
GET /api/v1/oauth2/auth/{provider}
```

Response:
```json
{
    "success": true,
    "data": {
        "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
        "state": "random_state_string",
        "provider": "google"
    }
}
```

#### OAuth2 Callback
```http
GET /api/v1/oauth2/callback/{provider}?code={code}&state={state}
```

Response:
```json
{
    "success": true,
    "data": {
        "user": {
            "id": "uuid",
            "email": "user@gmail.com",
            "first_name": "John",
            "last_name": "Doe",
            "display_name": "John Doe",
            "is_active": true,
            "is_verified": true,
            "auth_provider": "oauth2",
            "role": "user"
        },
        "tokens": {
            "access_token": "jwt_access_token",
            "refresh_token": "jwt_refresh_token",
            "token_type": "bearer",
            "expires_in": 3600
        }
    }
}
```

#### Get Provider Configuration (Admin Only)
```http
GET /api/v1/oauth2/config/{provider}
Authorization: Bearer <admin_token>
```

Response:
```json
{
    "success": true,
    "data": {
        "name": "google",
        "client_id": "your-client-id.apps.googleusercontent.com",
        "redirect_uri": "http://localhost:8001/api/v1/oauth2/callback/google",
        "scopes": ["openid", "email", "profile"],
        "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
        "userinfo_endpoint": "https://www.googleapis.com/oauth2/v2/userinfo"
    }
}
```

#### Test Provider Configuration (Admin Only)
```http
GET /api/v1/oauth2/test/{provider}
Authorization: Bearer <admin_token>
```

Response:
```json
{
    "success": true,
    "data": {
        "status": "success",
        "message": "Provider 'google' is configured correctly",
        "provider": "google",
        "client_id": "your-client-id.apps.googleusercontent.com",
        "redirect_uri": "http://localhost:8001/api/v1/oauth2/callback/google",
        "scopes": ["openid", "email", "profile"],
        "test_auth_url": "https://accounts.google.com/o/oauth2/v2/auth?..."
    }
}
```

#### Frontend-Friendly Login Redirect
```http
GET /api/v1/oauth2/login/{provider}
```
- Redirects directly to provider's authorization URL
- Useful for frontend applications

## Frontend Integration

### React Example

```javascript
import React, { useEffect } from 'react';

const OAuth2Login = () => {
    const handleGoogleLogin = async () => {
        try {
            const response = await fetch('/api/v1/oauth2/auth/google');
            const data = await response.json();
            
            if (data.success) {
                // Store state in session storage for validation
                sessionStorage.setItem('oauth2_state', data.data.state);
                
                // Redirect to provider
                window.location.href = data.data.authorization_url;
            }
        } catch (error) {
            console.error('OAuth2 login failed:', error);
        }
    };

    const handleMicrosoftLogin = async () => {
        try {
            const response = await fetch('/api/v1/oauth2/auth/microsoft');
            const data = await response.json();
            
            if (data.success) {
                sessionStorage.setItem('oauth2_state', data.data.state);
                window.location.href = data.data.authorization_url;
            }
        } catch (error) {
            console.error('OAuth2 login failed:', error);
        }
    };

    // Handle OAuth2 callback
    useEffect(() => {
        const urlParams = new URLSearchParams(window.location.search);
        const code = urlParams.get('code');
        const state = urlParams.get('state');
        const provider = window.location.pathname.split('/').pop();

        if (code && state) {
            const storedState = sessionStorage.getItem('oauth2_state');
            
            if (state === storedState) {
                // Exchange code for tokens
                handleOAuth2Callback(provider, code, state);
            } else {
                console.error('OAuth2 state mismatch');
            }
        }
    }, []);

    const handleOAuth2Callback = async (provider, code, state) => {
        try {
            const response = await fetch(
                `/api/v1/oauth2/callback/${provider}?code=${code}&state=${state}`
            );
            const data = await response.json();
            
            if (data.success) {
                // Store tokens
                localStorage.setItem('access_token', data.data.tokens.access_token);
                localStorage.setItem('refresh_token', data.data.tokens.refresh_token);
                
                // Redirect to dashboard
                window.location.href = '/dashboard';
            }
        } catch (error) {
            console.error('OAuth2 callback failed:', error);
        }
    };

    return (
        <div>
            <button onClick={handleGoogleLogin}>
                Sign in with Google
            </button>
            <button onClick={handleMicrosoftLogin}>
                Sign in with Microsoft
            </button>
        </div>
    );
};

export default OAuth2Login;
```

### Vue.js Example

```vue
<template>
  <div>
    <button @click="loginWithGoogle">Sign in with Google</button>
    <button @click="loginWithMicrosoft">Sign in with Microsoft</button>
  </div>
</template>

<script>
export default {
  methods: {
    async loginWithGoogle() {
      await this.initiateOAuth2Login('google');
    },
    
    async loginWithMicrosoft() {
      await this.initiateOAuth2Login('microsoft');
    },
    
    async initiateOAuth2Login(provider) {
      try {
        const response = await this.$http.get(`/api/v1/oauth2/auth/${provider}`);
        
        if (response.data.success) {
          // Store state for validation
          sessionStorage.setItem('oauth2_state', response.data.data.state);
          
          // Redirect to provider
          window.location.href = response.data.data.authorization_url;
        }
      } catch (error) {
        console.error('OAuth2 login failed:', error);
      }
    }
  },
  
  mounted() {
    // Handle OAuth2 callback
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    const state = urlParams.get('state');
    
    if (code && state) {
      this.handleOAuth2Callback(code, state);
    }
  }
};
</script>
```

## Security Considerations

### State Parameter Validation
- Always validate the state parameter to prevent CSRF attacks
- Use cryptographically secure random state values
- Store state in session or local storage for validation

### Token Security
- Access tokens should be stored securely (not in localStorage for production)
- Use HttpOnly cookies for token storage when possible
- Implement proper token refresh logic

### Redirect URI Validation
- Configure exact redirect URIs in provider settings
- Never use wildcard redirect URIs
- Use HTTPS in production

### Scope Management
- Request only necessary scopes
- Document what information is accessed
- Respect user privacy and data minimization principles

## Error Handling

### Common Errors

#### Provider Configuration Errors
```json
{
    "error": "OAuth2 error: invalid_client",
    "description": "Client authentication failed"
}
```
**Solution**: Check client ID and client secret configuration

#### Redirect URI Mismatch
```json
{
    "error": "OAuth2 error: redirect_uri_mismatch",
    "description": "The redirect URI provided does not match"
}
```
**Solution**: Ensure redirect URI in code matches provider configuration

#### Invalid Authorization Code
```json
{
    "error": "OAuth2 error: invalid_grant",
    "description": "The provided authorization grant is invalid"
}
```
**Solution**: Code may be expired or already used. Restart the flow.

#### State Mismatch
```json
{
    "error": "OAuth2 error: invalid_request",
    "description": "State parameter mismatch"
}
```
**Solution**: Ensure state parameter is properly stored and validated

### Error Response Format
```json
{
    "success": false,
    "error": {
        "code": "OAUTH2_AUTHENTICATION_FAILED",
        "message": "OAuth2 authentication failed",
        "details": {
            "provider": "google",
            "error": "invalid_grant"
        }
    }
}
```

## Troubleshooting

### Debug Mode
Enable debug logging to troubleshoot OAuth2 issues:
```bash
LOG_LEVEL=DEBUG
```

### Testing Configuration
Use the test endpoints to verify provider configuration:
```bash
curl -H "Authorization: Bearer <admin_token>" \
     http://localhost:8001/api/v1/oauth2/test/google
```

### Common Issues

1. **"OAuth2 authentication is disabled"**
   - Set `ENABLE_OAUTH2=true`
   - Set provider-specific enabled flags

2. **"Provider 'google' is not available"**
   - Check provider configuration
   - Ensure client ID and secret are set

3. **"Failed to fetch user information"**
   - Check API permissions in provider settings
   - Ensure scopes include necessary permissions

4. **"User not found and auto-creation is disabled"**
   - Set `OAUTH2_AUTO_CREATE_USER=true` or create user manually

## Performance Considerations

### Token Caching
- User information is cached in the local database
- Tokens are not stored (for security)
- Consider implementing rate limiting for auth endpoints

### Connection Pooling
- HTTP clients use connection pooling for provider API calls
- Configure appropriate timeouts for provider requests

### Async Operations
- All OAuth2 operations are asynchronous
- Database operations use async SQLAlchemy

## Monitoring and Metrics

### Key Metrics
- OAuth2 authentication attempts by provider
- Success/failure rates
- Token exchange response times
- User creation/update rates

### Logging
- All OAuth2 operations are logged with structured logging
- Include provider, user email, and operation status
- Log errors with detailed error information

### Health Checks
- Provider configuration validation
- Test authentication flow endpoints
- Monitor provider API availability

## Best Practices

1. **Security**:
   - Use HTTPS in production
   - Validate all OAuth2 parameters
   - Implement proper state validation
   - Store secrets securely

2. **User Experience**:
   - Provide clear error messages
   - Handle provider errors gracefully
   - Support multiple providers
   - Implement progressive enhancement

3. **Reliability**:
   - Handle provider downtime gracefully
   - Implement proper retry logic
   - Cache user information appropriately
   - Monitor provider API limits

4. **Maintenance**:
   - Keep provider configurations updated
   - Monitor for provider API changes
   - Regular security reviews
   - Update dependencies regularly

## Migration Guide

### From Local to OAuth2 Authentication

1. **Enable OAuth2**: Configure providers and enable OAuth2
2. **Test Configuration**: Use test endpoints to verify setup
3. **Update Frontend**: Add OAuth2 login buttons
4. **Migrate Users**: Existing users can link OAuth2 accounts
5. **Monitor Usage**: Track adoption and issues

### Adding New Providers

1. **Create Provider Class**: Extend `OAuth2Provider` base class
2. **Add Configuration**: Add provider-specific settings
3. **Update Service**: Register provider in `OAuth2Service`
4. **Add Tests**: Create comprehensive test suite
5. **Update Documentation**: Document new provider setup

## Example Configurations

### Development Configuration
```bash
# Basic setup for local development
ENABLE_OAUTH2=true
GOOGLE_OAUTH2_ENABLED=true
GOOGLE_CLIENT_ID=dev-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=dev-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8001/api/v1/oauth2/callback/google
```

### Production Configuration
```bash
# Production setup with Microsoft and Google
ENABLE_OAUTH2=true

# Google OAuth2
GOOGLE_OAUTH2_ENABLED=true
GOOGLE_CLIENT_ID=prod-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=prod-client-secret
GOOGLE_REDIRECT_URI=https://yourdomain.com/api/v1/oauth2/callback/google

# Microsoft OAuth2
MICROSOFT_OAUTH2_ENABLED=true
MICROSOFT_CLIENT_ID=prod-microsoft-app-id
MICROSOFT_CLIENT_SECRET=prod-microsoft-secret
MICROSOFT_REDIRECT_URI=https://yourdomain.com/api/v1/oauth2/callback/microsoft
MICROSOFT_TENANT_ID=your-tenant-id

# Security settings
OAUTH2_AUTO_CREATE_USER=true
OAUTH2_AUTO_UPDATE_USER=true
OAUTH2_DEFAULT_ROLE=user
```