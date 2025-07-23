# LDAP Authentication

This document describes the LDAP authentication implementation in the User Management Service.

## Overview

The LDAP authentication feature allows users to authenticate against an external LDAP directory server (such as Active Directory, OpenLDAP, or others) instead of using local passwords. This enables organizations to centralize user management and leverage existing identity infrastructure.

## Features

- **LDAP Authentication**: Authenticate users against external LDAP servers
- **User Auto-Creation**: Automatically create local users from LDAP directory
- **User Auto-Update**: Keep local user information synchronized with LDAP
- **Group Mapping**: Map LDAP groups to local roles
- **Connection Pooling**: Efficient connection management for better performance
- **SSL/TLS Support**: Secure connections to LDAP servers
- **Flexible Configuration**: Comprehensive configuration options for different LDAP schemas

## Configuration

### Environment Variables

The following environment variables configure LDAP authentication:

#### Basic Configuration
```bash
# Enable LDAP authentication
ENABLE_LDAP=true

# LDAP server connection
LDAP_SERVER=ldap.example.com
LDAP_PORT=389
LDAP_USE_SSL=false
LDAP_USE_TLS=true

# LDAP bind credentials (service account)
LDAP_BASE_DN=dc=example,dc=com
LDAP_BIND_DN=cn=service-account,ou=system,dc=example,dc=com
LDAP_BIND_PASSWORD=service-password
```

#### User Configuration
```bash
# User search settings
LDAP_USER_SEARCH_BASE=ou=users,dc=example,dc=com
LDAP_USER_SEARCH_FILTER=(uid={username})
LDAP_USER_OBJECT_CLASS=inetOrgPerson

# User attribute mappings
LDAP_USERNAME_ATTR=uid
LDAP_EMAIL_ATTR=mail
LDAP_FIRST_NAME_ATTR=givenName
LDAP_LAST_NAME_ATTR=sn
LDAP_DISPLAY_NAME_ATTR=displayName
LDAP_PHONE_ATTR=telephoneNumber
LDAP_DEPARTMENT_ATTR=department
LDAP_ORGANIZATION_ATTR=organization
LDAP_GROUPS_ATTR=memberOf
```

#### Group Configuration
```bash
# Group search settings
LDAP_GROUP_SEARCH_BASE=ou=groups,dc=example,dc=com
LDAP_GROUP_SEARCH_FILTER=(cn={groupname})
LDAP_GROUP_OBJECT_CLASS=groupOfNames
LDAP_GROUP_NAME_ATTR=cn
LDAP_GROUP_MEMBER_ATTR=member
```

#### Role Mapping
```bash
# Default role for new users
LDAP_DEFAULT_ROLE=user

# Group to role mappings (comma-separated)
LDAP_ADMIN_GROUPS=admins,administrators
LDAP_EDITOR_GROUPS=editors,content-managers
LDAP_VIEWER_GROUPS=viewers,read-only
```

#### Behavior Configuration
```bash
# User management behavior
LDAP_AUTO_CREATE_USER=true
LDAP_AUTO_UPDATE_USER=true

# Connection settings
LDAP_CONNECTION_TIMEOUT=30
LDAP_SEARCH_TIMEOUT=30
LDAP_POOL_SIZE=5
```

## Usage

### Authentication Flow

1. **User Login**: User provides username/email and password
2. **LDAP Lookup**: System searches for user in LDAP directory
3. **Authentication**: System attempts to bind to LDAP with user credentials
4. **User Creation/Update**: If successful, system creates or updates local user record
5. **Role Assignment**: System assigns roles based on LDAP group memberships
6. **Session Creation**: System creates user session and returns tokens

### API Endpoints

#### Test LDAP Connection
```http
GET /api/v1/ldap/test
Authorization: Bearer <admin_token>
```

Response:
```json
{
    "success": true,
    "data": {
        "status": "success",
        "message": "LDAP connection successful",
        "server": "ldap.example.com",
        "port": 389,
        "base_dn": "dc=example,dc=com"
    }
}
```

#### Sync Users from LDAP
```http
POST /api/v1/ldap/sync
Authorization: Bearer <admin_token>
```

Response:
```json
{
    "success": true,
    "data": {
        "status": "completed",
        "synced_users": 150,
        "errors": 2,
        "users": ["user1@example.com", "user2@example.com", "..."],
        "error_details": ["Failed to sync user: invalid email"]
    }
}
```

#### Get LDAP Configuration
```http
GET /api/v1/ldap/config
Authorization: Bearer <admin_token>
```

Response:
```json
{
    "success": true,
    "data": {
        "enabled": true,
        "server": "ldap.example.com",
        "port": 389,
        "use_ssl": false,
        "use_tls": true,
        "base_dn": "dc=example,dc=com",
        "user_search_base": "ou=users,dc=example,dc=com",
        "auto_create_user": true,
        "auto_update_user": true,
        "default_role": "user",
        "admin_groups": ["admins"],
        "attribute_mappings": {
            "username": "uid",
            "email": "mail",
            "first_name": "givenName",
            "last_name": "sn"
        }
    }
}
```

#### Test User Authentication
```http
POST /api/v1/ldap/authenticate
Authorization: Bearer <admin_token>
Content-Type: application/json

{
    "username": "testuser",
    "password": "testpass"
}
```

Response:
```json
{
    "success": true,
    "authenticated": true,
    "user_info": {
        "username": "testuser",
        "email": "testuser@example.com",
        "first_name": "Test",
        "last_name": "User",
        "groups": ["users", "developers"],
        "role": "user"
    }
}
```

### Login Process

Users with LDAP accounts can login using the standard login endpoint:

```http
POST /api/v1/auth/login
Content-Type: application/json

{
    "email": "user@example.com",
    "password": "ldap_password"
}
```

The system will:
1. First attempt LDAP authentication
2. If LDAP fails, fall back to local authentication
3. Return standard JWT tokens on success

## LDAP Schema Support

### Common Schema Formats

#### OpenLDAP / RFC 2307
```bash
LDAP_USER_OBJECT_CLASS=inetOrgPerson
LDAP_USERNAME_ATTR=uid
LDAP_EMAIL_ATTR=mail
LDAP_FIRST_NAME_ATTR=givenName
LDAP_LAST_NAME_ATTR=sn
LDAP_DISPLAY_NAME_ATTR=displayName
```

#### Active Directory
```bash
LDAP_USER_OBJECT_CLASS=person
LDAP_USERNAME_ATTR=sAMAccountName
LDAP_EMAIL_ATTR=mail
LDAP_FIRST_NAME_ATTR=givenName
LDAP_LAST_NAME_ATTR=sn
LDAP_DISPLAY_NAME_ATTR=displayName
LDAP_GROUPS_ATTR=memberOf
```

#### Custom Schema
```bash
LDAP_USER_OBJECT_CLASS=customPerson
LDAP_USERNAME_ATTR=customUsername
LDAP_EMAIL_ATTR=customEmail
LDAP_FIRST_NAME_ATTR=customFirstName
LDAP_LAST_NAME_ATTR=customLastName
```

## Security Considerations

### Connection Security
- Use TLS/SSL for all LDAP connections in production
- Properly secure LDAP bind credentials
- Use service accounts with minimal required permissions

### Authentication Security
- LDAP passwords are never stored locally
- Failed authentication attempts are logged
- Account lockout policies still apply to LDAP users

### Authorization Security
- Role mappings are enforced locally
- Group memberships are synchronized from LDAP
- Local permissions override LDAP group permissions

## Troubleshooting

### Common Issues

#### Connection Errors
```
Error: LDAP connection failed: Connection refused
```
**Solution**: Check LDAP server address, port, and network connectivity

#### Authentication Errors
```
Error: LDAP bind failed: Invalid credentials
```
**Solution**: Verify LDAP bind DN and password

#### User Not Found
```
Error: User not found in LDAP
```
**Solution**: Check user search base and filter configuration

#### Permission Errors
```
Error: Insufficient permissions to search LDAP
```
**Solution**: Verify service account has search permissions

### Debug Configuration

Enable debug logging to troubleshoot issues:

```bash
LOG_LEVEL=DEBUG
```

This will provide detailed LDAP operation logs.

### Testing LDAP Configuration

Use the test endpoints to verify configuration:

1. Test connection: `GET /api/v1/ldap/test`
2. Test authentication: `POST /api/v1/ldap/authenticate`
3. Sync users: `POST /api/v1/ldap/sync`

## Performance Optimization

### Connection Pooling
- Configure appropriate pool size: `LDAP_POOL_SIZE=10`
- Adjust timeouts for your network: `LDAP_CONNECTION_TIMEOUT=30`

### Search Optimization
- Use specific search bases to reduce scope
- Optimize LDAP filters for your directory structure
- Consider LDAP server indexing for search attributes

### Caching
- User information is cached locally in the database
- Group memberships are synchronized on each login
- Consider implementing additional caching layers for high-traffic scenarios

## Migration Guide

### From Local to LDAP Authentication

1. **Backup existing users**: Export current user data
2. **Configure LDAP**: Set up LDAP connection and mappings
3. **Test configuration**: Use test endpoints to verify setup
4. **Migrate users**: Use sync endpoint to create LDAP user records
5. **Update user records**: Set `auth_provider='ldap'` for migrated users
6. **Verify access**: Test login with LDAP credentials

### From LDAP to Local Authentication

1. **Export LDAP users**: Sync all users from LDAP
2. **Generate passwords**: Create temporary passwords for users
3. **Update records**: Set `auth_provider='local'` and add password hashes
4. **Notify users**: Inform users about password change process
5. **Disable LDAP**: Set `ENABLE_LDAP=false`

## Monitoring and Metrics

### Key Metrics
- LDAP authentication attempts
- LDAP connection failures
- User synchronization success/failure rates
- Authentication response times

### Logging
- All LDAP operations are logged
- Authentication attempts are audited
- Connection errors are logged with details

### Health Checks
- LDAP connection status
- Service account credential validation
- Directory server response times

## Best Practices

1. **Security**:
   - Use TLS/SSL for all connections
   - Secure service account credentials
   - Implement proper access controls

2. **Performance**:
   - Configure appropriate connection pooling
   - Optimize LDAP search filters
   - Monitor connection timeouts

3. **Reliability**:
   - Implement proper error handling
   - Use health checks for monitoring
   - Plan for LDAP server downtime

4. **Maintenance**:
   - Regular user synchronization
   - Monitor for schema changes
   - Update group mappings as needed

## Example Configurations

### OpenLDAP Configuration
```bash
ENABLE_LDAP=true
LDAP_SERVER=ldap.company.com
LDAP_PORT=636
LDAP_USE_SSL=true
LDAP_BASE_DN=dc=company,dc=com
LDAP_BIND_DN=cn=admin,dc=company,dc=com
LDAP_BIND_PASSWORD=admin_password
LDAP_USER_SEARCH_BASE=ou=people,dc=company,dc=com
LDAP_USER_SEARCH_FILTER=(uid={username})
LDAP_GROUP_SEARCH_BASE=ou=groups,dc=company,dc=com
LDAP_ADMIN_GROUPS=admins,sysadmins
```

### Active Directory Configuration
```bash
ENABLE_LDAP=true
LDAP_SERVER=ad.company.com
LDAP_PORT=389
LDAP_USE_TLS=true
LDAP_BASE_DN=dc=company,dc=com
LDAP_BIND_DN=cn=service-account,ou=service-accounts,dc=company,dc=com
LDAP_BIND_PASSWORD=service_password
LDAP_USER_SEARCH_BASE=ou=users,dc=company,dc=com
LDAP_USER_SEARCH_FILTER=(sAMAccountName={username})
LDAP_USERNAME_ATTR=sAMAccountName
LDAP_GROUP_SEARCH_BASE=ou=groups,dc=company,dc=com
LDAP_ADMIN_GROUPS=Domain Admins,MAMS Admins
```