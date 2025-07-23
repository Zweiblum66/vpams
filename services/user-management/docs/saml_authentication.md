# SAML Authentication

This document describes the SAML 2.0 authentication implementation in the User Management Service, providing Single Sign-On (SSO) integration with enterprise identity providers.

## Overview

The SAML authentication feature enables users to sign in using their enterprise identity provider accounts. This supports popular IdPs like Okta, OneLogin, Azure AD, ADFS, Ping Identity, and others that support SAML 2.0.

## Features

- **SAML 2.0 Support**: Full SAML 2.0 protocol implementation
- **Enterprise SSO**: Seamless integration with corporate identity providers
- **User Auto-Creation**: Automatically create local users from SAML assertions
- **User Auto-Update**: Keep local user information synchronized with IdP
- **Role Mapping**: Map SAML groups to local roles
- **Single Logout**: Support for SAML Single Logout (SLO)
- **Metadata Generation**: Automatic SP metadata generation
- **Flexible Configuration**: Support for various SAML configurations

## Supported Identity Providers

### Tested Providers
- **Okta**
- **Azure AD / Microsoft Entra ID**
- **OneLogin**
- **ADFS (Active Directory Federation Services)**
- **Google Workspace** (SAML apps)
- **Ping Identity**
- **Auth0**
- **SimpleSAMLphp**

### Requirements
- SAML 2.0 compliant identity provider
- Support for HTTP-POST binding (required)
- Support for HTTP-Redirect binding (optional, for logout)

## Configuration

### Environment Variables

#### Basic SAML Configuration
```bash
# Enable SAML authentication
ENABLE_SAML=true

# SAML behavior settings
SAML_AUTO_CREATE_USER=true
SAML_AUTO_UPDATE_USER=true
SAML_DEFAULT_ROLE=user
```

#### Service Provider (SP) Configuration
```bash
# SP Entity ID (your application's unique identifier)
SAML_SP_ENTITY_ID=http://localhost:8001/saml

# Assertion Consumer Service URL (where IdP sends responses)
SAML_SP_ACS_URL=http://localhost:8001/api/v1/saml/acs

# Single Logout Service URL (optional)
SAML_SP_SLS_URL=http://localhost:8001/api/v1/saml/sls

# SP X.509 Certificate (for signing requests)
SAML_SP_X509_CERT="-----BEGIN CERTIFICATE-----
MIIDXTCCAkWgAwIBAgIJAL...
-----END CERTIFICATE-----"

# SP Private Key (for signing requests)
SAML_SP_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQ...
-----END PRIVATE KEY-----"
```

#### Identity Provider (IdP) Configuration
```bash
# IdP Entity ID
SAML_IDP_ENTITY_ID=http://www.okta.com/exk1fxpvhzXXXXXXXXX

# IdP Single Sign-On URL
SAML_IDP_SSO_URL=https://yourcompany.okta.com/app/yourapp/exk1fxpvhzXXXXXXXXX/sso/saml

# IdP Single Logout URL (optional)
SAML_IDP_SLS_URL=https://yourcompany.okta.com/app/yourapp/exk1fxpvhzXXXXXXXXX/slo/saml

# IdP X.509 Certificate
SAML_IDP_X509_CERT="-----BEGIN CERTIFICATE-----
MIIDpDCCAoygAwIBAgIGAV...
-----END CERTIFICATE-----"
```

#### Advanced SAML Settings
```bash
# Name ID Format
SAML_NAME_ID_FORMAT=urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress

# Signature and encryption settings
SAML_AUTHN_REQUESTS_SIGNED=true
SAML_LOGOUT_REQUESTS_SIGNED=true
SAML_WANT_ASSERTIONS_SIGNED=true
SAML_WANT_ASSERTIONS_ENCRYPTED=false

# Signature algorithms
SAML_SIGNATURE_ALGORITHM=http://www.w3.org/2001/04/xmldsig-more#rsa-sha256
SAML_DIGEST_ALGORITHM=http://www.w3.org/2001/04/xmlenc#sha256

# Attribute mapping (JSON format)
SAML_ATTRIBUTE_MAPPING='{
  "email": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
  "first_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
  "last_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname",
  "display_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
  "groups": "http://schemas.microsoft.com/ws/2008/06/identity/claims/groups"
}'
```

## Identity Provider Setup

### Okta Setup

1. **Create SAML Application**:
   - Sign in to Okta Admin Console
   - Navigate to Applications > Applications
   - Click "Create App Integration"
   - Choose "SAML 2.0"

2. **Configure SAML Settings**:
   - **Single Sign On URL**: `https://yourdomain.com/api/v1/saml/acs`
   - **Audience URI (SP Entity ID)**: `https://yourdomain.com/saml`
   - **Name ID format**: EmailAddress
   - **Application username**: Email

3. **Attribute Statements**:
   ```
   Name                 | Name format | Value
   email               | Basic       | user.email
   first_name          | Basic       | user.firstName
   last_name           | Basic       | user.lastName
   groups              | Basic       | appuser.groups
   ```

4. **Download Metadata**:
   - View Setup Instructions
   - Copy IdP metadata values to environment variables

### Azure AD Setup

1. **Register Application**:
   - Go to Azure Portal > Azure Active Directory
   - Navigate to Enterprise applications
   - Click "New application" > "Create your own application"
   - Choose "Integrate any other application (Non-gallery)"

2. **Configure SSO**:
   - Go to Single sign-on > SAML
   - Basic SAML Configuration:
     - **Identifier (Entity ID)**: `https://yourdomain.com/saml`
     - **Reply URL (ACS URL)**: `https://yourdomain.com/api/v1/saml/acs`
     - **Sign on URL**: `https://yourdomain.com/api/v1/saml/login`
     - **Logout URL**: `https://yourdomain.com/api/v1/saml/sls`

3. **User Attributes & Claims**:
   - Required claim: `emailaddress` (user.mail)
   - Additional claims:
     - `givenname` (user.givenname)
     - `surname` (user.surname)
     - `name` (user.displayname)
     - `groups` (user.groups)

4. **Download Certificate**:
   - Download Certificate (Base64)
   - Copy to `SAML_IDP_X509_CERT`

### OneLogin Setup

1. **Add Application**:
   - Applications > Add App
   - Search for "SAML Custom Connector (Advanced)"

2. **Configuration**:
   - **ACS (Consumer) URL**: `https://yourdomain.com/api/v1/saml/acs`
   - **ACS (Consumer) URL Validator**: `.*`
   - **Audience**: `https://yourdomain.com/saml`

3. **Parameters**:
   - Add custom parameters for attributes
   - Map to OneLogin user fields

4. **SSO Settings**:
   - Copy Issuer URL to `SAML_IDP_ENTITY_ID`
   - Copy SAML 2.0 Endpoint to `SAML_IDP_SSO_URL`
   - Copy X.509 Certificate to `SAML_IDP_X509_CERT`

## Usage

### Authentication Flow

1. **SP Metadata**:
   - Access metadata at: `GET /api/v1/saml/metadata`
   - Provide this URL to IdP administrators

2. **Login Flow**:
   - User accesses: `GET /api/v1/saml/login`
   - Redirected to IdP login page
   - After authentication, IdP posts to ACS endpoint
   - User receives JWT tokens

3. **Logout Flow**:
   - Initiate logout: `GET /api/v1/saml/logout?name_id={email}&session_index={index}`
   - Redirected to IdP for logout
   - IdP calls SLS endpoint
   - Local session terminated

### API Endpoints

#### Get SP Metadata
```http
GET /api/v1/saml/metadata
```

Response:
```xml
<?xml version="1.0"?>
<EntityDescriptor xmlns="urn:oasis:names:tc:SAML:2.0:metadata"
                  entityID="https://yourdomain.com/saml">
  <SPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
    <KeyDescriptor use="signing">
      <KeyInfo xmlns="http://www.w3.org/2000/09/xmldsig#">
        <X509Data>
          <X509Certificate>...</X509Certificate>
        </X509Data>
      </KeyInfo>
    </KeyDescriptor>
    <SingleLogoutService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                         Location="https://yourdomain.com/api/v1/saml/sls"/>
    <AssertionConsumerService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                              Location="https://yourdomain.com/api/v1/saml/acs"
                              index="1"/>
  </SPSSODescriptor>
</EntityDescriptor>
```

#### Initiate SAML Login
```http
GET /api/v1/saml/login?return_to=/dashboard
```
- Redirects to IdP login page
- Optional `return_to` parameter for post-login redirect

#### Assertion Consumer Service (ACS)
```http
POST /api/v1/saml/acs
Content-Type: application/x-www-form-urlencoded

SAMLResponse=PHNhbWxwOlJlc3BvbnNlIHhtbG5zOnNhbWxwPSJ1cm46b2FzaXM6bmFtZXM6dGM6U0FNTDoyLjA6cHJvdG9jb2wi...
```

Response:
```json
{
    "success": true,
    "data": {
        "user": {
            "id": "uuid",
            "email": "user@company.com",
            "first_name": "John",
            "last_name": "Doe",
            "display_name": "John Doe",
            "is_active": true,
            "is_verified": true,
            "auth_provider": "saml",
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

#### Initiate SAML Logout
```http
GET /api/v1/saml/logout?name_id=user@company.com&session_index=_8e8dc5f69a98cc4c1ff3427e5ce34606fd033f091e
```
- Redirects to IdP logout page
- Required: `name_id` (user's email)
- Optional: `session_index` (from login response)

#### Single Logout Service (SLS)
```http
GET /api/v1/saml/sls?SAMLRequest=...
POST /api/v1/saml/sls
```
- Handles logout responses from IdP
- Supports both GET and POST bindings

#### Test Configuration (Admin Only)
```http
GET /api/v1/saml/test
Authorization: Bearer <admin_token>
```

Response:
```json
{
    "success": true,
    "data": {
        "status": "success",
        "message": "SAML configuration is valid",
        "sp_entity_id": "https://yourdomain.com/saml",
        "idp_entity_id": "http://www.okta.com/exk1fxpvhz...",
        "has_metadata": true
    }
}
```

#### Get Configuration (Admin Only)
```http
GET /api/v1/saml/config
Authorization: Bearer <admin_token>
```

Response:
```json
{
    "success": true,
    "data": {
        "enabled": true,
        "sp_entity_id": "https://yourdomain.com/saml",
        "sp_acs_url": "https://yourdomain.com/api/v1/saml/acs",
        "idp_entity_id": "http://www.okta.com/exk1fxpvhz...",
        "idp_sso_url": "https://company.okta.com/app/...",
        "name_id_format": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
        "metadata_url": "https://yourdomain.com/api/v1/saml/metadata"
    }
}
```

## Frontend Integration

### React Example

```javascript
import React from 'react';
import { Button } from '@mui/material';

const SAMLLogin = () => {
    const handleSAMLLogin = () => {
        // Redirect to SAML login endpoint
        window.location.href = '/api/v1/saml/login?return_to=' + 
            encodeURIComponent(window.location.pathname);
    };

    return (
        <Button 
            variant="outlined" 
            onClick={handleSAMLLogin}
            fullWidth
        >
            Sign in with SSO
        </Button>
    );
};

// Handle SAML callback
const SAMLCallback = () => {
    React.useEffect(() => {
        // The ACS endpoint returns tokens
        // In production, you might redirect from backend
        const handleCallback = async () => {
            try {
                const response = await fetch('/api/v1/auth/me', {
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                    }
                });
                
                if (response.ok) {
                    window.location.href = '/dashboard';
                }
            } catch (error) {
                console.error('SAML callback error:', error);
            }
        };
        
        handleCallback();
    }, []);
    
    return <div>Processing SSO login...</div>;
};
```

### Vue.js Example

```vue
<template>
  <div>
    <button @click="loginWithSAML" class="sso-button">
      Sign in with SSO
    </button>
  </div>
</template>

<script>
export default {
  methods: {
    loginWithSAML() {
      // Store current location for return
      sessionStorage.setItem('saml_return_to', this.$route.fullPath);
      
      // Redirect to SAML login
      window.location.href = '/api/v1/saml/login';
    }
  }
};
</script>
```

## Attribute Mapping

### Standard Attributes

The default attribute mapping supports common SAML attributes:

| Local Attribute | SAML Attribute | Description |
|----------------|----------------|-------------|
| email | http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress | User's email address |
| first_name | http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname | First/given name |
| last_name | http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname | Last/family name |
| display_name | http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name | Full display name |
| groups | http://schemas.microsoft.com/ws/2008/06/identity/claims/groups | Group memberships |

### Custom Attribute Mapping

Configure custom mappings via environment variable:

```bash
SAML_ATTRIBUTE_MAPPING='{
  "email": "urn:oid:0.9.2342.19200300.100.1.3",
  "first_name": "urn:oid:2.5.4.42",
  "last_name": "urn:oid:2.5.4.4",
  "department": "urn:oid:2.5.4.11",
  "employee_id": "urn:oid:2.16.840.1.113730.3.1.3"
}'
```

### Common Attribute OIDs

| Attribute | OID | Description |
|-----------|-----|-------------|
| mail | 0.9.2342.19200300.100.1.3 | Email address |
| givenName | 2.5.4.42 | Given name |
| sn | 2.5.4.4 | Surname |
| cn | 2.5.4.3 | Common name |
| o | 2.5.4.10 | Organization |
| ou | 2.5.4.11 | Organizational unit |
| title | 2.5.4.12 | Job title |

## Role Mapping

### Automatic Role Assignment

Roles are assigned based on SAML group memberships:

1. **Admin Role**: Groups containing "admin", "administrator", "superuser"
2. **Editor Role**: Groups containing "editor", "contributor", "writer"
3. **Viewer Role**: Groups containing "viewer", "reader", "readonly"
4. **Default Role**: Configured via `SAML_DEFAULT_ROLE`

### Custom Role Mapping

For complex scenarios, implement custom logic in `_determine_user_role()`:

```python
def _determine_user_role(self, groups: list) -> str:
    """Custom role determination logic"""
    # Map specific AD groups to roles
    role_mapping = {
        "MAMS-Admins": "admin",
        "MAMS-Editors": "editor",
        "MAMS-Viewers": "viewer",
        "MAMS-Users": "user"
    }
    
    for group in groups:
        if group in role_mapping:
            return role_mapping[group]
    
    return self.settings.saml_default_role
```

## Security Considerations

### Certificate Management

1. **Generate SP Certificates**:
```bash
# Generate private key
openssl genrsa -out sp.key 2048

# Generate certificate
openssl req -new -x509 -key sp.key -out sp.crt -days 365
```

2. **Store Securely**:
- Use environment variables or secrets management
- Never commit certificates to version control
- Rotate certificates periodically

### Signature Validation

- Always validate IdP signatures: `SAML_WANT_ASSERTIONS_SIGNED=true`
- Use strong algorithms: RSA-SHA256 or better
- Verify certificate chain if using certificate hierarchy

### Session Security

- SAML session index is stored for Single Logout
- Local sessions are independent of SAML sessions
- Implement session timeout policies

## Troubleshooting

### Common Issues

#### "Invalid SAML Response"
- Check IdP certificate configuration
- Verify ACS URL matches exactly
- Ensure clock synchronization (NTP)

#### "User not found and auto-creation is disabled"
- Set `SAML_AUTO_CREATE_USER=true`
- Or pre-create users with matching emails

#### "Signature validation failed"
- Verify IdP X.509 certificate is correct
- Check certificate formatting (no extra spaces)
- Ensure `SAML_WANT_ASSERTIONS_SIGNED` matches IdP config

#### "Missing required attribute: email"
- Check attribute mapping configuration
- Verify IdP sends email attribute
- Review SAML response in debug mode

### Debug Mode

Enable debug logging:
```bash
LOG_LEVEL=DEBUG
# In development only:
DEBUG=true
```

### SAML Response Inspection

Use browser developer tools:
1. Open Network tab
2. Preserve log
3. Complete SAML login
4. Find POST to `/api/v1/saml/acs`
5. Decode SAMLResponse parameter

Online tools (for development only):
- [SAML Developer Tools](https://www.samltool.com/)
- [OneLogin SAML Tools](https://www.samltool.com/decode.php)

## Performance Optimization

### Metadata Caching
- SP metadata is generated once and cached
- Regenerate after certificate changes

### User Synchronization
- Users are created/updated on first login
- Consider batch sync for large organizations

### Session Management
- SAML sessions are separate from application sessions
- Implement efficient session storage (Redis)

## Migration Guide

### From Local to SAML Authentication

1. **Enable SAML**: Configure IdP and SP settings
2. **Test Configuration**: Use test endpoint
3. **Pilot Users**: Test with small group
4. **Communicate Change**: Notify users
5. **Full Rollout**: Enable for all users
6. **Monitor**: Track login success rates

### Existing User Migration

Users with matching emails are automatically linked:
1. Existing user with email `user@company.com`
2. SAML login with same email
3. User linked to SAML (auth_provider updated)
4. Password disabled for SAML users

## Best Practices

1. **Use HTTPS**: Always use HTTPS in production
2. **Validate Metadata**: Regularly verify IdP metadata
3. **Monitor Certificates**: Set expiration alerts
4. **Test Logout**: Verify Single Logout works
5. **Document Setup**: Keep IdP configuration documented
6. **Regular Reviews**: Audit user access and roles

## Example Configurations

### Okta Configuration
```bash
ENABLE_SAML=true
SAML_SP_ENTITY_ID=https://myapp.com/saml
SAML_SP_ACS_URL=https://myapp.com/api/v1/saml/acs
SAML_IDP_ENTITY_ID=http://www.okta.com/exk1fxpvhzABCDEFGHI
SAML_IDP_SSO_URL=https://company.okta.com/app/myapp/exk1fxpvhzABCDEFGHI/sso/saml
SAML_IDP_X509_CERT="-----BEGIN CERTIFICATE-----..."
```

### Azure AD Configuration
```bash
ENABLE_SAML=true
SAML_SP_ENTITY_ID=https://myapp.com/saml
SAML_SP_ACS_URL=https://myapp.com/api/v1/saml/acs
SAML_IDP_ENTITY_ID=https://sts.windows.net/12345678-1234-1234-1234-123456789012/
SAML_IDP_SSO_URL=https://login.microsoftonline.com/12345678-1234-1234-1234-123456789012/saml2
SAML_IDP_X509_CERT="-----BEGIN CERTIFICATE-----..."
SAML_NAME_ID_FORMAT=urn:oasis:names:tc:SAML:2.0:nameid-format:persistent
```