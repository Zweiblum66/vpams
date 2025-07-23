# Permission Inheritance System

The MAMS Permission Inheritance System provides advanced permission management with sophisticated inheritance patterns, conflict resolution, and optimization recommendations.

## Overview

The inheritance system extends the basic RBAC functionality to support complex organizational structures with multiple inheritance paths, priority-based conflict resolution, and comprehensive analysis tools.

## Key Features

- **Multi-Level Inheritance**: Role hierarchy and group hierarchy support
- **Conflict Resolution**: Priority-based resolution of permission conflicts
- **Source Tracking**: Detailed tracking of permission sources
- **Optimization**: Recommendations for permission assignment optimization
- **Analysis Tools**: Comprehensive permission analysis and statistics

## Inheritance Types

### 1. Direct Assignments
- **Role Assignments**: Direct role-to-user assignments
- **Group Memberships**: Direct group-to-user memberships
- **Group Permissions**: Direct permissions assigned to groups

### 2. Role Hierarchy
- **Parent-Child Roles**: Roles can inherit from parent roles
- **Recursive Inheritance**: Multi-level role inheritance
- **Permission Aggregation**: Child roles inherit all parent permissions

### 3. Group Hierarchy
- **Parent-Child Groups**: Groups can inherit from parent groups
- **Recursive Inheritance**: Multi-level group inheritance
- **Permission Aggregation**: Child groups inherit all parent permissions

### 4. Mixed Inheritance
- **Group Role Assignments**: Roles assigned to groups
- **Cross-Hierarchy**: Permissions from multiple inheritance paths

## Permission Priority System

The system uses a priority-based approach to resolve conflicts:

| Source Type | Priority | Description |
|-------------|----------|-------------|
| Direct Role | 10 | Highest priority - direct role assignments |
| Direct Group | 8 | High priority - direct group permissions |
| Group Role | 7 | Medium-high priority - roles assigned to groups |
| Role Hierarchy | 5 | Medium priority - inherited from parent roles |
| Group Hierarchy | 3 | Low priority - inherited from parent groups |

## Core Components

### InheritanceService

The main service class that handles all inheritance operations:

```python
from services.inheritance_service import InheritanceService

inheritance_service = InheritanceService()

# Get effective permissions for a user
result = await inheritance_service.get_effective_permissions(
    db, user_id, include_sources=True
)
```

### PermissionSource

Tracks the source of each permission:

```python
@dataclass
class PermissionSource:
    permission_name: str
    source_type: InheritanceType
    source_id: UUID
    source_name: str
    priority: int
    granted_at: Optional[datetime] = None
    granted_by: Optional[UUID] = None
```

### InheritanceType Enum

Defines the types of inheritance:

```python
class InheritanceType(Enum):
    DIRECT = "direct"
    ROLE_HIERARCHY = "role_hierarchy"
    GROUP_HIERARCHY = "group_hierarchy"
    GROUP_ROLE = "group_role"
    MIXED = "mixed"
```

## API Endpoints

### Get Effective Permissions

```http
GET /api/v1/inheritance/users/{user_id}/effective-permissions?include_sources=true
```

Returns all effective permissions for a user with optional source information.

**Response:**
```json
{
  "success": true,
  "data": {
    "permissions": ["user:read", "asset:write", "project:admin"],
    "total_count": 3,
    "sources": [
      {
        "permission_name": "user:read",
        "source_type": "direct",
        "source_id": "role-123",
        "source_name": "Role: Admin",
        "priority": 10,
        "granted_at": "2024-01-15T10:30:00Z"
      }
    ]
  }
}
```

### Get Inheritance Tree

```http
GET /api/v1/inheritance/users/{user_id}/inheritance-tree
```

Returns the complete inheritance hierarchy for a user.

**Response:**
```json
{
  "success": true,
  "data": {
    "tree": {
      "user_id": "user-123",
      "roles": [
        {
          "role_id": "role-123",
          "name": "admin",
          "permissions": ["user:admin", "system:admin"],
          "parent": {
            "role_id": "role-456",
            "name": "user",
            "permissions": ["user:read"],
            "parent": null
          }
        }
      ],
      "groups": [
        {
          "group_id": "group-789",
          "name": "engineering",
          "permissions": ["project:read"],
          "roles": [
            {
              "role_id": "role-101",
              "name": "developer",
              "permissions": ["asset:read", "asset:write"]
            }
          ],
          "parent": null
        }
      ]
    }
  }
}
```

### Check Permission Conflicts

```http
GET /api/v1/inheritance/users/{user_id}/permission-conflicts
```

Identifies conflicts where the same permission comes from multiple sources.

**Response:**
```json
{
  "success": true,
  "data": {
    "total_permissions": 25,
    "conflicted_permissions": 3,
    "conflicts": {
      "user:read": {
        "sources": [
          {
            "permission_name": "user:read",
            "source_type": "direct",
            "priority": 10
          },
          {
            "permission_name": "user:read",
            "source_type": "group_role",
            "priority": 7
          }
        ],
        "resolution": "highest_priority",
        "chosen_source": {
          "source_type": "direct",
          "priority": 10
        }
      }
    }
  }
}
```

### Get Inheritance Statistics

```http
GET /api/v1/inheritance/users/{user_id}/inheritance-statistics
```

Provides detailed statistics about permission inheritance.

**Response:**
```json
{
  "success": true,
  "data": {
    "total_permissions": 25,
    "source_breakdown": {
      "direct": 10,
      "group_role": 8,
      "role_hierarchy": 5,
      "group_hierarchy": 2
    },
    "max_role_inheritance_depth": 3,
    "max_group_inheritance_depth": 2,
    "inheritance_complexity": 5
  }
}
```

### Get Optimization Recommendations

```http
GET /api/v1/inheritance/users/{user_id}/optimization-recommendations
```

Provides recommendations for optimizing permission assignments.

**Response:**
```json
{
  "success": true,
  "data": {
    "total_permissions": 25,
    "redundant_assignments": 5,
    "conflicts": 2,
    "recommendations": [
      {
        "type": "consolidation",
        "description": "Remove 5 redundant permission assignments",
        "details": [
          {
            "permission": "user:read",
            "redundant_source": {
              "source_type": "group_role",
              "priority": 7
            },
            "reason": "Lower priority than existing assignment"
          }
        ]
      },
      {
        "type": "grouping",
        "description": "Consider creating groups for 15 direct assignments",
        "details": {
          "direct_assignments": 15
        }
      }
    ]
  }
}
```

### Get Permissions Summary

```http
GET /api/v1/inheritance/users/{user_id}/permissions/summary
```

Comprehensive summary combining all inheritance analysis.

## Usage Examples

### Basic Permission Analysis

```python
from services.inheritance_service import InheritanceService

inheritance_service = InheritanceService()

# Get effective permissions with sources
result = await inheritance_service.get_effective_permissions(
    db, user_id, include_sources=True
)

print(f"User has {result['total_count']} effective permissions")
for source in result['sources']:
    print(f"  {source['permission_name']} from {source['source_name']}")
```

### Conflict Detection

```python
# Check for permission conflicts
conflicts = await inheritance_service.check_permission_conflicts(db, user_id)

if conflicts['conflicted_permissions'] > 0:
    print(f"Found {conflicts['conflicted_permissions']} conflicts")
    for perm, conflict in conflicts['conflicts'].items():
        print(f"  {perm}: {len(conflict['sources'])} sources")
```

### Permission Optimization

```python
# Get optimization recommendations
recommendations = await inheritance_service.optimize_user_permissions(db, user_id)

for rec in recommendations['recommendations']:
    print(f"{rec['type']}: {rec['description']}")
```

### Inheritance Tree Analysis

```python
# Get full inheritance tree
tree = await inheritance_service.get_permission_inheritance_tree(db, user_id)

# Analyze role hierarchy
for role in tree['tree']['roles']:
    print(f"Role: {role['name']}")
    if role['parent']:
        print(f"  Inherits from: {role['parent']['name']}")
```

## Advanced Features

### Circular Reference Detection

The system automatically detects and handles circular references in role and group hierarchies:

```python
# This will be detected and handled gracefully
role_a.parent_role_id = role_b.id
role_b.parent_role_id = role_a.id  # Circular reference
```

### Performance Optimization

- **Efficient Queries**: Optimized database queries with proper joins
- **Caching**: Permission results can be cached for performance
- **Lazy Loading**: Relationships loaded only when needed
- **Depth Limiting**: Prevents infinite recursion with depth limits

### Permission Inheritance Rules

The system follows these inheritance rules:

1. **Additive Inheritance**: Child inherits all parent permissions
2. **Active Only**: Only active roles, groups, and permissions are considered
3. **Priority Resolution**: Higher priority sources override lower priority
4. **Recursive Processing**: Inheritance is processed recursively up the hierarchy

## Security Considerations

### Access Control

All inheritance endpoints require superuser privileges:

```python
@inheritance_router.get("/users/{user_id}/effective-permissions")
async def get_user_effective_permissions(
    current_user: User = Depends(require_superuser)
):
    # Only superusers can access inheritance analysis
```

### Audit Trail

The system maintains detailed audit information:

- **Permission Sources**: Track where each permission comes from
- **Timestamps**: When permissions were granted
- **Granters**: Who granted the permissions
- **Changes**: Track all inheritance changes

### Privilege Escalation Protection

- **No Self-Modification**: Users cannot modify their own permissions
- **Hierarchy Validation**: Prevents creation of privilege escalation paths
- **System Role Protection**: System roles cannot be modified

## Troubleshooting

### Common Issues

1. **Circular References**
   - **Symptom**: Inheritance tree shows circular_reference flag
   - **Solution**: Review role/group hierarchy and remove circular dependencies

2. **Performance Issues**
   - **Symptom**: Slow inheritance calculations
   - **Solution**: Optimize hierarchy depth and consider caching

3. **Permission Conflicts**
   - **Symptom**: Unexpected permission denials
   - **Solution**: Use conflict detection to identify and resolve conflicts

### Debug Tools

```python
# Get detailed inheritance statistics
stats = await inheritance_service.get_inheritance_statistics(db, user_id)
print(f"Inheritance complexity: {stats['inheritance_complexity']}")

# Check for conflicts
conflicts = await inheritance_service.check_permission_conflicts(db, user_id)
if conflicts['conflicted_permissions'] > 0:
    print("Conflicts detected - review assignments")
```

## Best Practices

### Hierarchy Design

1. **Shallow Hierarchies**: Keep inheritance depth reasonable (< 5 levels)
2. **Clear Naming**: Use descriptive names for roles and groups
3. **Logical Structure**: Mirror organizational structure
4. **Regular Review**: Periodically review and optimize assignments

### Permission Management

1. **Principle of Least Privilege**: Grant minimum required permissions
2. **Group-Based Assignment**: Prefer group assignments over direct assignments
3. **Regular Audits**: Use inheritance analysis tools regularly
4. **Conflict Resolution**: Address conflicts promptly

### Performance Optimization

1. **Cache Results**: Cache permission calculations where appropriate
2. **Batch Operations**: Process multiple users together when possible
3. **Monitor Complexity**: Track inheritance complexity metrics
4. **Optimize Queries**: Use efficient database queries

## Future Enhancements

1. **Time-Based Permissions**: Temporary permission grants
2. **Conditional Inheritance**: Context-aware permission inheritance
3. **Advanced Caching**: Redis-based permission caching
4. **Real-Time Updates**: Live updates of permission changes
5. **Machine Learning**: AI-powered permission optimization