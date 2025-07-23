"""
Permission constants for MAMS system

This module defines all permission constants used throughout the application
to ensure consistency and avoid typos.
"""

# User Management Permissions
class UserPermissions:
    """User management related permissions"""
    READ = "user:read"
    WRITE = "user:write"
    DELETE = "user:delete"
    ADMIN = "user:admin"
    VIEW_PROFILE = "user:view_profile"
    EDIT_PROFILE = "user:edit_profile"
    MANAGE_ROLES = "user:manage_roles"
    MANAGE_PERMISSIONS = "user:manage_permissions"
    UNLOCK_ACCOUNTS = "user:unlock_accounts"
    VIEW_LOCKOUT_INFO = "user:view_lockout_info"
    RESET_PASSWORD = "user:reset_password"
    VERIFY_EMAIL = "user:verify_email"


# Asset Management Permissions
class AssetPermissions:
    """Asset management related permissions"""
    READ = "asset:read"
    WRITE = "asset:write"
    DELETE = "asset:delete"
    ADMIN = "asset:admin"
    CREATE = "asset:create"
    UPDATE = "asset:update"
    VIEW_METADATA = "asset:view_metadata"
    EDIT_METADATA = "asset:edit_metadata"
    UPLOAD = "asset:upload"
    DOWNLOAD = "asset:download"
    MOVE = "asset:move"
    COPY = "asset:copy"
    SHARE = "asset:share"
    APPROVE = "asset:approve"
    REJECT = "asset:reject"
    ARCHIVE = "asset:archive"
    RESTORE = "asset:restore"
    TRANSCODE = "asset:transcode"
    PROXY_GENERATE = "asset:proxy_generate"


# Project Management Permissions
class ProjectPermissions:
    """Project management related permissions"""
    READ = "project:read"
    WRITE = "project:write"
    DELETE = "project:delete"
    ADMIN = "project:admin"
    CREATE = "project:create"
    UPDATE = "project:update"
    MANAGE_MEMBERS = "project:manage_members"
    VIEW_MEMBERS = "project:view_members"
    ARCHIVE = "project:archive"
    RESTORE = "project:restore"
    EXPORT = "project:export"
    IMPORT = "project:import"


# Metadata Management Permissions
class MetadataPermissions:
    """Metadata management related permissions"""
    READ = "metadata:read"
    WRITE = "metadata:write"
    DELETE = "metadata:delete"
    ADMIN = "metadata:admin"
    CREATE_SCHEMA = "metadata:create_schema"
    UPDATE_SCHEMA = "metadata:update_schema"
    DELETE_SCHEMA = "metadata:delete_schema"
    EXTRACT = "metadata:extract"
    ENRICH = "metadata:enrich"
    VALIDATE = "metadata:validate"
    EXPORT = "metadata:export"
    IMPORT = "metadata:import"


# Search Permissions
class SearchPermissions:
    """Search related permissions"""
    READ = "search:read"
    ADMIN = "search:admin"
    BASIC_SEARCH = "search:basic"
    ADVANCED_SEARCH = "search:advanced"
    SEMANTIC_SEARCH = "search:semantic"
    VISUAL_SEARCH = "search:visual"
    SAVE_SEARCHES = "search:save"
    SHARE_SEARCHES = "search:share"
    MANAGE_INDEXES = "search:manage_indexes"


# Workflow Permissions
class WorkflowPermissions:
    """Workflow related permissions"""
    READ = "workflow:read"
    WRITE = "workflow:write"
    DELETE = "workflow:delete"
    ADMIN = "workflow:admin"
    CREATE = "workflow:create"
    UPDATE = "workflow:update"
    EXECUTE = "workflow:execute"
    APPROVE = "workflow:approve"
    REJECT = "workflow:reject"
    ASSIGN = "workflow:assign"
    MONITOR = "workflow:monitor"
    CONFIGURE = "workflow:configure"


# Storage Permissions
class StoragePermissions:
    """Storage related permissions"""
    READ = "storage:read"
    WRITE = "storage:write"
    DELETE = "storage:delete"
    ADMIN = "storage:admin"
    UPLOAD = "storage:upload"
    DOWNLOAD = "storage:download"
    MOVE = "storage:move"
    COPY = "storage:copy"
    CONFIGURE = "storage:configure"
    MANAGE_TIERS = "storage:manage_tiers"
    MANAGE_QUOTAS = "storage:manage_quotas"
    BACKUP = "storage:backup"
    RESTORE = "storage:restore"


# AI/ML Permissions
class AIMLPermissions:
    """AI/ML service related permissions"""
    READ = "aiml:read"
    WRITE = "aiml:write"
    ADMIN = "aiml:admin"
    AUTO_TAG = "aiml:auto_tag"
    TRANSCRIBE = "aiml:transcribe"
    ANALYZE = "aiml:analyze"
    TRAIN_MODEL = "aiml:train_model"
    DEPLOY_MODEL = "aiml:deploy_model"
    CONFIGURE = "aiml:configure"


# Rights Management Permissions
class RightsPermissions:
    """Rights management related permissions"""
    READ = "rights:read"
    WRITE = "rights:write"
    DELETE = "rights:delete"
    ADMIN = "rights:admin"
    CREATE_LICENSE = "rights:create_license"
    UPDATE_LICENSE = "rights:update_license"
    TRACK_USAGE = "rights:track_usage"
    COMPLIANCE_CHECK = "rights:compliance_check"
    REPORT = "rights:report"
    CONFIGURE = "rights:configure"


# System Permissions
class SystemPermissions:
    """System-wide permissions"""
    READ = "system:read"
    WRITE = "system:write"
    ADMIN = "system:admin"
    MONITOR = "system:monitor"
    CONFIGURE = "system:configure"
    BACKUP = "system:backup"
    RESTORE = "system:restore"
    MAINTENANCE = "system:maintenance"
    LOGS_VIEW = "system:logs_view"
    LOGS_DOWNLOAD = "system:logs_download"
    METRICS_VIEW = "system:metrics_view"
    HEALTH_CHECK = "system:health_check"
    SECURITY_AUDIT = "system:security_audit"


# Integration Permissions
class IntegrationPermissions:
    """Integration related permissions"""
    READ = "integration:read"
    WRITE = "integration:write"
    DELETE = "integration:delete"
    ADMIN = "integration:admin"
    CONFIGURE = "integration:configure"
    EXPORT = "integration:export"
    IMPORT = "integration:import"
    SYNC = "integration:sync"
    CONNECT = "integration:connect"
    DISCONNECT = "integration:disconnect"


# Common permission groups for convenience
class CommonPermissionGroups:
    """Common permission groups for easier management"""
    
    # Basic user permissions
    BASIC_USER = [
        UserPermissions.READ,
        UserPermissions.VIEW_PROFILE,
        UserPermissions.EDIT_PROFILE,
        AssetPermissions.READ,
        AssetPermissions.DOWNLOAD,
        ProjectPermissions.READ,
        MetadataPermissions.READ,
        SearchPermissions.BASIC_SEARCH,
    ]
    
    # Content editor permissions
    CONTENT_EDITOR = BASIC_USER + [
        AssetPermissions.WRITE,
        AssetPermissions.CREATE,
        AssetPermissions.UPDATE,
        AssetPermissions.UPLOAD,
        AssetPermissions.EDIT_METADATA,
        ProjectPermissions.WRITE,
        ProjectPermissions.CREATE,
        ProjectPermissions.UPDATE,
        WorkflowPermissions.EXECUTE,
        SearchPermissions.ADVANCED_SEARCH,
        SearchPermissions.SAVE_SEARCHES,
    ]
    
    # Project manager permissions
    PROJECT_MANAGER = CONTENT_EDITOR + [
        ProjectPermissions.ADMIN,
        ProjectPermissions.MANAGE_MEMBERS,
        WorkflowPermissions.ADMIN,
        WorkflowPermissions.ASSIGN,
        WorkflowPermissions.APPROVE,
        AssetPermissions.APPROVE,
        AssetPermissions.REJECT,
    ]
    
    # System administrator permissions
    SYSTEM_ADMIN = [
        UserPermissions.ADMIN,
        AssetPermissions.ADMIN,
        ProjectPermissions.ADMIN,
        MetadataPermissions.ADMIN,
        SearchPermissions.ADMIN,
        WorkflowPermissions.ADMIN,
        StoragePermissions.ADMIN,
        AIMLPermissions.ADMIN,
        RightsPermissions.ADMIN,
        SystemPermissions.ADMIN,
        IntegrationPermissions.ADMIN,
    ]


# Permission validation utilities
def validate_permission(permission_name: str) -> bool:
    """
    Validate if a permission name follows the correct format
    
    Args:
        permission_name: Permission name to validate
    
    Returns:
        True if valid, False otherwise
    """
    import re
    
    # Permission format: resource:action
    pattern = r'^[a-z_]+:[a-z_]+$'
    return bool(re.match(pattern, permission_name))


def get_resource_from_permission(permission_name: str) -> str:
    """
    Extract resource name from permission
    
    Args:
        permission_name: Permission name
    
    Returns:
        Resource name
    """
    return permission_name.split(':')[0] if ':' in permission_name else ''


def get_action_from_permission(permission_name: str) -> str:
    """
    Extract action name from permission
    
    Args:
        permission_name: Permission name
    
    Returns:
        Action name
    """
    return permission_name.split(':')[1] if ':' in permission_name else ''


def create_permission_name(resource: str, action: str) -> str:
    """
    Create a permission name from resource and action
    
    Args:
        resource: Resource name
        action: Action name
    
    Returns:
        Permission name
    """
    return f"{resource}:{action}"