# Permission Checking Middleware

This document describes the permission checking middleware system implemented for the MAMS User Management Service.

## Overview

The permission checking middleware provides comprehensive access control for API endpoints using Role-Based Access Control (RBAC) with support for permission inheritance and flexible authorization patterns.

## Key Features

- **Role-Based Access Control**: Fine-grained permissions organized by roles
- **Permission Inheritance**: Automatic permission inheritance through role hierarchies
- **Multiple Authorization Patterns**: Support for various authorization scenarios
- **Resource Ownership**: Combine ownership checks with permission requirements
- **Comprehensive Logging**: Detailed access control logging for security auditing
- **Performance Optimized**: Efficient permission checking with caching support

## Available Middleware Functions

### Basic Permission Checking

#### `require_permission(permission_name, include_inherited=True)`
Checks if the current user has a specific permission.

```python
from api.dependencies import require_permission
from core.permissions import UserPermissions

@router.get("/users")
async def get_users(
    current_user: User = Depends(require_permission(UserPermissions.READ))
):
    # Only users with 'user:read' permission can access this endpoint
    pass
```

#### `require_role(role_name, include_inherited=True)`
Checks if the current user has a specific role.

```python
from api.dependencies import require_role

@router.get("/admin/stats")
async def get_admin_stats(
    current_user: User = Depends(require_role("admin"))
):
    # Only users with 'admin' role can access this endpoint
    pass
```

### Advanced Permission Checking

#### `require_any_permission(*permission_names, include_inherited=True)`
Checks if the current user has ANY of the specified permissions.

```python
from api.dependencies import require_any_permission
from core.permissions import UserPermissions, AssetPermissions

@router.get("/content")
async def get_content(
    current_user: User = Depends(require_any_permission(
        UserPermissions.READ,
        AssetPermissions.READ
    ))
):
    # User needs either 'user:read' OR 'asset:read' permission
    pass
```

#### `require_all_permissions(*permission_names, include_inherited=True)`
Checks if the current user has ALL of the specified permissions.

```python
from api.dependencies import require_all_permissions
from core.permissions import AssetPermissions, ProjectPermissions

@router.post("/assets/{asset_id}/publish")
async def publish_asset(
    current_user: User = Depends(require_all_permissions(
        AssetPermissions.WRITE,
        ProjectPermissions.ADMIN
    ))
):
    # User needs both 'asset:write' AND 'project:admin' permissions
    pass
```

#### `require_resource_permission(resource, action, include_inherited=True)`
Convenient wrapper for resource:action permission format.

```python
from api.dependencies import require_resource_permission

@router.get("/assets")
async def get_assets(
    current_user: User = Depends(require_resource_permission("asset", "read"))
):
    # Equivalent to require_permission("asset:read")
    pass
```

### Ownership-Based Authorization

#### `check_ownership_or_permission(permission_name, user_id_field="user_id")`
Checks if the user owns the resource OR has the required permission.

```python
from api.dependencies import check_ownership_or_permission
from core.permissions import AssetPermissions

@router.get("/assets/{asset_id}")
async def get_asset(
    asset_id: UUID,
    current_user: User = Depends(check_ownership_or_permission(
        AssetPermissions.READ,
        "owner_id"
    ))
):
    # User can access if they own the asset OR have 'asset:read' permission
    pass
```

### Utility Functions

#### `get_user_permissions(current_user, db)`
Returns all permissions for the current user.

```python
from api.dependencies import get_user_permissions

@router.get("/me/permissions")
async def get_my_permissions(
    permissions: List[str] = Depends(get_user_permissions)
):
    return {"permissions": permissions}
```

#### `get_user_roles(current_user, db)`
Returns all roles for the current user.

```python
from api.dependencies import get_user_roles

@router.get("/me/roles")
async def get_my_roles(
    roles: List[str] = Depends(get_user_roles)
):
    return {"roles": roles}
```

## Permission Constants

The system provides predefined permission constants organized by resource type:

```python
from core.permissions import (
    UserPermissions,
    AssetPermissions,
    ProjectPermissions,
    MetadataPermissions,
    # ... other permission classes
)

# Usage examples
UserPermissions.READ          # "user:read"
UserPermissions.WRITE         # "user:write"
AssetPermissions.UPLOAD       # "asset:upload"
ProjectPermissions.ADMIN      # "project:admin"
```

### Permission Categories

- **UserPermissions**: User management operations
- **AssetPermissions**: Asset management operations
- **ProjectPermissions**: Project management operations
- **MetadataPermissions**: Metadata operations
- **SearchPermissions**: Search operations
- **WorkflowPermissions**: Workflow operations
- **StoragePermissions**: Storage operations
- **AIMLPermissions**: AI/ML operations
- **RightsPermissions**: Rights management operations
- **SystemPermissions**: System administration
- **IntegrationPermissions**: Integration operations

## Common Permission Groups

Predefined permission groups for typical user roles:

```python
from core.permissions import CommonPermissionGroups

# Basic user permissions
CommonPermissionGroups.BASIC_USER

# Content editor permissions
CommonPermissionGroups.CONTENT_EDITOR

# Project manager permissions
CommonPermissionGroups.PROJECT_MANAGER

# System administrator permissions
CommonPermissionGroups.SYSTEM_ADMIN
```

## Usage Examples

### Basic API Endpoint Protection

```python
from fastapi import APIRouter, Depends
from api.dependencies import require_permission
from core.permissions import UserPermissions

router = APIRouter()

@router.get("/users")
async def list_users(
    current_user: User = Depends(require_permission(UserPermissions.READ))
):
    """List users - requires 'user:read' permission"""
    pass

@router.post("/users")
async def create_user(
    current_user: User = Depends(require_permission(UserPermissions.WRITE))
):
    """Create user - requires 'user:write' permission"""
    pass

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(require_permission(UserPermissions.DELETE))
):
    """Delete user - requires 'user:delete' permission"""
    pass
```

### Advanced Authorization Scenarios

```python
from api.dependencies import require_any_permission, require_all_permissions
from core.permissions import AssetPermissions, ProjectPermissions

@router.get("/dashboard")
async def get_dashboard(
    current_user: User = Depends(require_any_permission(
        AssetPermissions.READ,
        ProjectPermissions.READ,
        UserPermissions.READ
    ))
):
    """Dashboard - requires any content access permission"""
    pass

@router.post("/assets/{asset_id}/approve")
async def approve_asset(
    asset_id: UUID,
    current_user: User = Depends(require_all_permissions(
        AssetPermissions.APPROVE,
        ProjectPermissions.ADMIN
    ))
):
    """Approve asset - requires both asset approval and project admin permissions"""
    pass
```

### Resource Ownership Patterns

```python
from api.dependencies import check_ownership_or_permission

@router.get("/assets/{asset_id}")
async def get_asset(
    asset_id: UUID,
    current_user: User = Depends(check_ownership_or_permission(
        AssetPermissions.READ,
        "created_by"
    ))
):
    """Get asset - accessible to owner or users with read permission"""
    # Logic to check if current_user.id == asset.created_by
    pass
```

### Role-Based Access

```python
from api.dependencies import require_role

@router.get("/admin/system-stats")
async def get_system_stats(
    current_user: User = Depends(require_role("system_admin"))
):
    """System stats - requires system admin role"""
    pass
```

## Error Handling

The middleware returns appropriate HTTP status codes:

- **401 Unauthorized**: Invalid or missing authentication token
- **403 Forbidden**: Valid authentication but insufficient permissions
- **500 Internal Server Error**: Permission check system failure

Example error responses:

```json
{
  "detail": "Permission 'asset:write' required"
}
```

```json
{
  "detail": "One of the following permissions required: user:read, asset:read"
}
```

```json
{
  "detail": "Resource ownership or permission 'asset:read' required"
}
```

## Performance Considerations

1. **Permission Caching**: User permissions are cached during request processing
2. **Efficient Queries**: Optimized database queries for permission checking
3. **Inheritance Optimization**: Smart inheritance calculation to minimize database hits
4. **Logging Efficiency**: Structured logging for security auditing without performance impact

## Security Best Practices

1. **Principle of Least Privilege**: Grant minimum permissions needed
2. **Regular Permission Audits**: Monitor and review permission assignments
3. **Secure Defaults**: Deny access by default, require explicit permission grants
4. **Comprehensive Logging**: Log all permission checks for security monitoring
5. **Permission Validation**: Validate permission names and formats

## Testing

The middleware includes comprehensive test coverage:

```python
# Run permission middleware tests
pytest tests/test_permission_middleware.py -v

# Run with coverage
pytest tests/test_permission_middleware.py --cov=api.dependencies --cov-report=html
```

## Migration Guide

### From Basic Auth to RBAC

1. **Replace Simple Decorators**:
   ```python
   # Old
   @require_admin
   
   # New
   @Depends(require_permission(UserPermissions.ADMIN))
   ```

2. **Update Permission Checks**:
   ```python
   # Old
   if not user.is_admin:
       raise HTTPException(403, "Admin required")
   
   # New
   current_user: User = Depends(require_permission(UserPermissions.ADMIN))
   ```

3. **Add Resource-Specific Permissions**:
   ```python
   # Old
   @require_authenticated
   
   # New
   @Depends(require_resource_permission("asset", "read"))
   ```

## Troubleshooting

### Common Issues

1. **Permission Denied for Valid Users**:
   - Check if user has active roles
   - Verify permission inheritance is working
   - Check role-permission assignments

2. **Performance Issues**:
   - Review permission check frequency
   - Consider permission caching
   - Optimize database queries

3. **Testing Difficulties**:
   - Use mock RBAC service for unit tests
   - Test permission inheritance scenarios
   - Verify error handling

### Debug Logging

Enable debug logging for permission checks:

```python
import logging

logging.getLogger("api.dependencies").setLevel(logging.DEBUG)
```

## Future Enhancements

1. **Conditional Permissions**: Context-aware permission checking
2. **Time-Based Permissions**: Temporary permission grants
3. **Attribute-Based Access Control**: ABAC integration
4. **Performance Monitoring**: Permission check performance metrics
5. **Advanced Caching**: Redis-based permission caching