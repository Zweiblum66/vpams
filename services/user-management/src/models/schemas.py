"""
Pydantic schemas for User Management Service

This module defines all request and response schemas used by the API endpoints.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, validator, root_validator
import re


class BaseResponse(BaseModel):
    """Base response model with common fields"""
    success: bool = True
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginationMeta(BaseModel):
    """Pagination metadata"""
    page: int = Field(ge=1)
    limit: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    pages: int = Field(ge=0)


class PaginatedResponse(BaseResponse):
    """Base paginated response"""
    meta: PaginationMeta


# User Registration Models
class UserRegistrationRequest(BaseModel):
    """Request model for user registration"""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=8, max_length=128, description="User's password")
    confirm_password: str = Field(..., description="Password confirmation")
    first_name: str = Field(..., min_length=1, max_length=100, description="User's first name")
    last_name: str = Field(..., min_length=1, max_length=100, description="User's last name")
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="Unique username")
    organization: Optional[str] = Field(None, max_length=200, description="Organization name")
    department: Optional[str] = Field(None, max_length=100, description="Department")
    job_title: Optional[str] = Field(None, max_length=100, description="Job title")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    timezone: Optional[str] = Field(None, max_length=50, description="User's timezone")
    language: Optional[str] = Field("en", max_length=10, description="Preferred language")
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        # Check for at least one uppercase letter
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        # Check for at least one lowercase letter
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        
        # Check for at least one digit
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        
        # Check for at least one special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        
        return v
    
    @validator('username')
    def validate_username(cls, v):
        """Validate username format"""
        if v is None:
            return v
            
        # Check for valid characters (alphanumeric, underscore, dash)
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username can only contain letters, numbers, underscores, and dashes')
        
        # Must start with letter or number
        if not re.match(r'^[a-zA-Z0-9]', v):
            raise ValueError('Username must start with a letter or number')
        
        return v
    
    @validator('phone')
    def validate_phone(cls, v):
        """Validate phone number format"""
        if v is None:
            return v
            
        # Basic phone number validation
        phone_pattern = re.compile(r'^[\+]?[1-9][\d\s\-\(\)]{6,}$')
        if not phone_pattern.match(v):
            raise ValueError('Invalid phone number format')
        
        return v
    
    @root_validator
    def validate_passwords_match(cls, values):
        """Validate that password and confirm_password match"""
        password = values.get('password')
        confirm_password = values.get('confirm_password')
        
        if password != confirm_password:
            raise ValueError('Passwords do not match')
        
        return values
    
    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
                "first_name": "John",
                "last_name": "Doe",
                "username": "johndoe",
                "organization": "Acme Corp",
                "department": "Engineering",
                "job_title": "Software Developer",
                "phone": "+1-555-123-4567",
                "timezone": "America/New_York",
                "language": "en"
            }
        }


class UserRegistrationResponse(BaseResponse):
    """Response model for user registration"""
    data: Dict[str, Any] = Field(..., description="User registration data")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "User registered successfully. Please check your email for verification.",
                "timestamp": "2024-01-15T10:30:00Z",
                "data": {
                    "user_id": "123e4567-e89b-12d3-a456-426614174000",
                    "email": "user@example.com",
                    "username": "johndoe",
                    "first_name": "John",
                    "last_name": "Doe",
                    "is_active": True,
                    "is_verified": False,
                    "created_at": "2024-01-15T10:30:00Z",
                    "verification_required": True
                }
            }
        }


# User Login Models
class UserLoginRequest(BaseModel):
    """Request model for user login"""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")
    remember_me: bool = Field(False, description="Remember user login")
    device_info: Optional[Dict[str, str]] = Field(None, description="Device information")
    
    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123!",
                "remember_me": True,
                "device_info": {
                    "type": "desktop",
                    "os": "macOS",
                    "browser": "Chrome"
                }
            }
        }


class TokenResponse(BaseModel):
    """JWT token response model"""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    
    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "token_type": "bearer",
                "expires_in": 3600
            }
        }


class UserLoginResponse(BaseResponse):
    """Response model for user login"""
    data: Dict[str, Any] = Field(..., description="Login response data")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Login successful",
                "timestamp": "2024-01-15T10:30:00Z",
                "data": {
                    "user": {
                        "user_id": "123e4567-e89b-12d3-a456-426614174000",
                        "email": "user@example.com",
                        "username": "johndoe",
                        "first_name": "John",
                        "last_name": "Doe",
                        "display_name": "John Doe",
                        "is_active": True,
                        "is_verified": True,
                        "roles": ["user"]
                    },
                    "tokens": {
                        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        "token_type": "bearer",
                        "expires_in": 3600
                    }
                }
            }
        }


# User Profile Models
class UserResponse(BaseModel):
    """User response model"""
    user_id: UUID = Field(..., description="User ID")
    email: EmailStr = Field(..., description="User's email")
    username: Optional[str] = Field(None, description="Username")
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    display_name: Optional[str] = Field(None, description="Display name")
    is_active: bool = Field(..., description="Account active status")
    is_verified: bool = Field(..., description="Email verification status")
    is_superuser: bool = Field(..., description="Superuser status")
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "username": "johndoe",
                "first_name": "John",
                "last_name": "Doe",
                "display_name": "John Doe",
                "is_active": True,
                "is_verified": True,
                "is_superuser": False,
                "last_login_at": "2024-01-15T10:30:00Z",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }


class UserProfileResponse(BaseModel):
    """User profile response model"""
    user_id: UUID = Field(..., description="User ID")
    phone: Optional[str] = Field(None, description="Phone number")
    department: Optional[str] = Field(None, description="Department")
    job_title: Optional[str] = Field(None, description="Job title")
    organization: Optional[str] = Field(None, description="Organization")
    location: Optional[str] = Field(None, description="Location")
    timezone: Optional[str] = Field(None, description="Timezone")
    language: Optional[str] = Field(None, description="Language preference")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    bio: Optional[str] = Field(None, description="Biography")
    website: Optional[str] = Field(None, description="Website URL")
    preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences")
    created_at: datetime = Field(..., description="Profile creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        orm_mode = True


class UserUpdateRequest(BaseModel):
    """Request model for updating user information"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    display_name: Optional[str] = Field(None, max_length=200)
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)
    department: Optional[str] = Field(None, max_length=100)
    job_title: Optional[str] = Field(None, max_length=100)
    organization: Optional[str] = Field(None, max_length=200)
    location: Optional[str] = Field(None, max_length=200)
    timezone: Optional[str] = Field(None, max_length=50)
    language: Optional[str] = Field(None, max_length=10)
    bio: Optional[str] = Field(None, max_length=1000)
    website: Optional[str] = Field(None, max_length=500)
    preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences")
    
    @validator('username')
    def validate_username(cls, v):
        """Validate username format"""
        if v is None:
            return v
            
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username can only contain letters, numbers, underscores, and dashes')
        
        return v


# Role and Permission Models
class RoleResponse(BaseModel):
    """Role response model"""
    role_id: UUID = Field(..., description="Role ID")
    name: str = Field(..., description="Role name")
    display_name: str = Field(..., description="Role display name")
    description: Optional[str] = Field(None, description="Role description")
    role_type: str = Field(..., description="Role type")
    is_active: bool = Field(..., description="Role active status")
    created_at: datetime = Field(..., description="Role creation timestamp")
    
    class Config:
        orm_mode = True


class PermissionResponse(BaseModel):
    """Permission response model"""
    permission_id: UUID = Field(..., description="Permission ID")
    name: str = Field(..., description="Permission name")
    display_name: str = Field(..., description="Permission display name")
    description: Optional[str] = Field(None, description="Permission description")
    resource: str = Field(..., description="Resource type")
    action: str = Field(..., description="Action type")
    category: str = Field(..., description="Permission category")
    scope: str = Field(..., description="Permission scope")
    
    class Config:
        orm_mode = True


# Authentication Flow Models
class EmailVerificationRequest(BaseModel):
    """Request model for email verification"""
    token: str = Field(..., description="Email verification token")
    
    class Config:
        schema_extra = {
            "example": {
                "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
            }
        }


class PasswordResetRequest(BaseModel):
    """Request model for password reset"""
    email: EmailStr = Field(..., description="User's email address")
    
    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com"
            }
        }


class PasswordResetConfirmRequest(BaseModel):
    """Request model for password reset confirmation"""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")
    confirm_password: str = Field(..., description="Password confirmation")
    
    @validator('new_password')
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        
        return v
    
    @root_validator
    def validate_passwords_match(cls, values):
        """Validate that password and confirm_password match"""
        password = values.get('new_password')
        confirm_password = values.get('confirm_password')
        
        if password != confirm_password:
            raise ValueError('Passwords do not match')
        
        return values
    
    class Config:
        schema_extra = {
            "example": {
                "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "new_password": "NewSecurePass123!",
                "confirm_password": "NewSecurePass123!"
            }
        }


class ChangePasswordRequest(BaseModel):
    """Request model for changing password"""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")
    confirm_password: str = Field(..., description="Password confirmation")
    
    @validator('new_password')
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        
        return v
    
    @root_validator
    def validate_passwords_match(cls, values):
        """Validate that password and confirm_password match"""
        password = values.get('new_password')
        confirm_password = values.get('confirm_password')
        
        if password != confirm_password:
            raise ValueError('Passwords do not match')
        
        return values
    
    class Config:
        schema_extra = {
            "example": {
                "current_password": "OldPassword123!",
                "new_password": "NewSecurePass123!",
                "confirm_password": "NewSecurePass123!"
            }
        }


# Error Response Models
class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = False
    error: Dict[str, Any] = Field(..., description="Error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        schema_extra = {
            "example": {
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": {
                        "field_errors": {
                            "email": ["Invalid email format"],
                            "password": ["Password must be at least 8 characters long"]
                        }
                    }
                },
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


# Pagination Models
class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(1, ge=1, description="Page number")
    limit: int = Field(20, ge=1, le=100, description="Items per page")
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


class SortParams(BaseModel):
    """Sorting parameters"""
    sort: Optional[str] = Field("created_at", description="Sort field")
    order: Optional[str] = Field("desc", regex="^(asc|desc)$", description="Sort order")


class FilterParams(BaseModel):
    """Filter parameters"""
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    is_verified: Optional[bool] = Field(None, description="Filter by verification status")
    role: Optional[str] = Field(None, description="Filter by role name")
    department: Optional[str] = Field(None, description="Filter by department")
    organization: Optional[str] = Field(None, description="Filter by organization")
    created_after: Optional[datetime] = Field(None, description="Filter by creation date")
    created_before: Optional[datetime] = Field(None, description="Filter by creation date")


class UserListResponse(PaginatedResponse):
    """User list response model"""
    data: List[UserResponse] = Field(..., description="List of users")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Users retrieved successfully",
                "timestamp": "2024-01-15T10:30:00Z",
                "data": [
                    {
                        "user_id": "123e4567-e89b-12d3-a456-426614174000",
                        "email": "user@example.com",
                        "username": "johndoe",
                        "first_name": "John",
                        "last_name": "Doe",
                        "display_name": "John Doe",
                        "is_active": True,
                        "is_verified": True,
                        "is_superuser": False,
                        "last_login_at": "2024-01-15T10:30:00Z",
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z"
                    }
                ],
                "meta": {
                    "page": 1,
                    "limit": 20,
                    "total": 1,
                    "pages": 1
                }
            }
        }


# RBAC Models
class RoleCreateRequest(BaseModel):
    """Request model for creating a role"""
    name: str = Field(..., min_length=1, max_length=100, description="Role name")
    display_name: str = Field(..., min_length=1, max_length=200, description="Role display name")
    description: Optional[str] = Field(None, max_length=1000, description="Role description")
    role_type: str = Field("custom", regex="^(system|built-in|custom)$", description="Role type")
    parent_role_id: Optional[UUID] = Field(None, description="Parent role ID for inheritance")
    
    class Config:
        schema_extra = {
            "example": {
                "name": "content_editor",
                "display_name": "Content Editor",
                "description": "Can edit and manage content",
                "role_type": "custom",
                "parent_role_id": None
            }
        }


class RoleUpdateRequest(BaseModel):
    """Request model for updating a role"""
    display_name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    parent_role_id: Optional[UUID] = Field(None)
    is_active: Optional[bool] = Field(None)
    
    class Config:
        schema_extra = {
            "example": {
                "display_name": "Senior Content Editor",
                "description": "Senior level content editor with additional permissions",
                "is_active": True
            }
        }


class PermissionCreateRequest(BaseModel):
    """Request model for creating a permission"""
    name: str = Field(..., min_length=1, max_length=100, description="Permission name")
    display_name: str = Field(..., min_length=1, max_length=200, description="Permission display name")
    description: Optional[str] = Field(None, max_length=1000, description="Permission description")
    resource: str = Field(..., min_length=1, max_length=50, description="Resource type")
    action: str = Field(..., min_length=1, max_length=50, description="Action type")
    category: str = Field("general", max_length=50, description="Permission category")
    scope: str = Field("global", regex="^(global|tenant|project|personal)$", description="Permission scope")
    
    class Config:
        schema_extra = {
            "example": {
                "name": "asset:read",
                "display_name": "Read Assets",
                "description": "Can view and read asset information",
                "resource": "asset",
                "action": "read",
                "category": "content",
                "scope": "global"
            }
        }


class PermissionUpdateRequest(BaseModel):
    """Request model for updating a permission"""
    display_name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    category: Optional[str] = Field(None, max_length=50)
    scope: Optional[str] = Field(None, regex="^(global|tenant|project|personal)$")
    is_active: Optional[bool] = Field(None)
    
    class Config:
        schema_extra = {
            "example": {
                "display_name": "View Assets",
                "description": "Can view asset information and metadata",
                "category": "content",
                "is_active": True
            }
        }


class RoleAssignmentRequest(BaseModel):
    """Request model for assigning role to user"""
    user_id: UUID = Field(..., description="User ID")
    role_id: UUID = Field(..., description="Role ID")
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "role_id": "987fcdeb-51d2-43a1-b456-426614174000"
            }
        }


class PermissionAssignmentRequest(BaseModel):
    """Request model for assigning permission to role"""
    role_id: UUID = Field(..., description="Role ID")
    permission_id: UUID = Field(..., description="Permission ID")
    
    class Config:
        schema_extra = {
            "example": {
                "role_id": "987fcdeb-51d2-43a1-b456-426614174000",
                "permission_id": "456e7890-ab12-34cd-ef56-426614174000"
            }
        }


class RoleListResponse(PaginatedResponse):
    """Role list response model"""
    data: List[RoleResponse] = Field(..., description="List of roles")


class PermissionListResponse(PaginatedResponse):
    """Permission list response model"""
    data: List[PermissionResponse] = Field(..., description="List of permissions")


class UserPermissionsResponse(BaseModel):
    """User permissions response model"""
    user_id: UUID = Field(..., description="User ID")
    permissions: List[str] = Field(..., description="List of permission names")
    roles: List[RoleResponse] = Field(..., description="List of user roles")
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "permissions": ["asset:read", "asset:write", "user:read"],
                "roles": [
                    {
                        "role_id": "987fcdeb-51d2-43a1-b456-426614174000",
                        "name": "content_editor",
                        "display_name": "Content Editor",
                        "description": "Can edit and manage content",
                        "role_type": "custom",
                        "is_active": True,
                        "created_at": "2024-01-15T10:30:00Z"
                    }
                ]
            }
        }


class RolePermissionsResponse(BaseModel):
    """Role permissions response model"""
    role_id: UUID = Field(..., description="Role ID")
    role_name: str = Field(..., description="Role name")
    permissions: List[PermissionResponse] = Field(..., description="List of permissions")
    inherited_permissions: List[str] = Field(..., description="List of inherited permission names")
    
    class Config:
        schema_extra = {
            "example": {
                "role_id": "987fcdeb-51d2-43a1-b456-426614174000",
                "role_name": "content_editor",
                "permissions": [
                    {
                        "permission_id": "456e7890-ab12-34cd-ef56-426614174000",
                        "name": "asset:read",
                        "display_name": "Read Assets",
                        "description": "Can view asset information",
                        "resource": "asset",
                        "action": "read",
                        "category": "content",
                        "scope": "global"
                    }
                ],
                "inherited_permissions": ["user:read", "system:access"]
            }
        }


# Group Management Models
class GroupCreateRequest(BaseModel):
    """Request model for creating a group"""
    name: str = Field(..., min_length=1, max_length=100, description="Group name")
    display_name: str = Field(..., min_length=1, max_length=200, description="Group display name")
    description: Optional[str] = Field(None, max_length=1000, description="Group description")
    group_type: str = Field("custom", regex="^(system|department|project|custom)$", description="Group type")
    parent_group_id: Optional[UUID] = Field(None, description="Parent group ID for hierarchy")
    max_members: Optional[int] = Field(None, ge=1, le=10000, description="Maximum number of members")
    
    class Config:
        schema_extra = {
            "example": {
                "name": "engineering_team",
                "display_name": "Engineering Team",
                "description": "Software engineering team members",
                "group_type": "department",
                "parent_group_id": None,
                "max_members": 50
            }
        }


class GroupUpdateRequest(BaseModel):
    """Request model for updating a group"""
    display_name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    parent_group_id: Optional[UUID] = Field(None)
    max_members: Optional[int] = Field(None, ge=1, le=10000)
    is_active: Optional[bool] = Field(None)
    
    class Config:
        schema_extra = {
            "example": {
                "display_name": "Senior Engineering Team",
                "description": "Senior software engineering team members",
                "max_members": 25,
                "is_active": True
            }
        }


class GroupResponse(BaseModel):
    """Group response model"""
    group_id: UUID = Field(..., description="Group ID")
    name: str = Field(..., description="Group name")
    display_name: str = Field(..., description="Group display name")
    description: Optional[str] = Field(None, description="Group description")
    group_type: str = Field(..., description="Group type")
    parent_group_id: Optional[UUID] = Field(None, description="Parent group ID")
    max_members: Optional[int] = Field(None, description="Maximum members")
    is_active: bool = Field(..., description="Group active status")
    is_system: bool = Field(..., description="System group flag")
    member_count: Optional[int] = Field(None, description="Current member count")
    created_at: datetime = Field(..., description="Group creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "group_id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "engineering_team",
                "display_name": "Engineering Team",
                "description": "Software engineering team members",
                "group_type": "department",
                "parent_group_id": None,
                "max_members": 50,
                "is_active": True,
                "is_system": False,
                "member_count": 12,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }


class GroupMembershipRequest(BaseModel):
    """Request model for group membership operations"""
    user_id: UUID = Field(..., description="User ID")
    group_id: UUID = Field(..., description="Group ID")
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "group_id": "987fcdeb-51d2-43a1-b456-426614174000"
            }
        }


class GroupRoleAssignmentRequest(BaseModel):
    """Request model for assigning role to group"""
    group_id: UUID = Field(..., description="Group ID")
    role_id: UUID = Field(..., description="Role ID")
    
    class Config:
        schema_extra = {
            "example": {
                "group_id": "987fcdeb-51d2-43a1-b456-426614174000",
                "role_id": "456e7890-ab12-34cd-ef56-426614174000"
            }
        }


class GroupPermissionAssignmentRequest(BaseModel):
    """Request model for assigning permission to group"""
    group_id: UUID = Field(..., description="Group ID")
    permission_id: UUID = Field(..., description="Permission ID")
    
    class Config:
        schema_extra = {
            "example": {
                "group_id": "987fcdeb-51d2-43a1-b456-426614174000",
                "permission_id": "789a1234-bc56-78de-f901-426614174000"
            }
        }


class GroupListResponse(PaginatedResponse):
    """Group list response model"""
    data: List[GroupResponse] = Field(..., description="List of groups")


class GroupMembersResponse(PaginatedResponse):
    """Group members response model"""
    data: List[UserResponse] = Field(..., description="List of group members")


class GroupPermissionsResponse(BaseModel):
    """Group permissions response model"""
    group_id: UUID = Field(..., description="Group ID")
    group_name: str = Field(..., description="Group name")
    direct_permissions: List[str] = Field(..., description="Direct permissions")
    role_permissions: List[str] = Field(..., description="Permissions from roles")
    inherited_permissions: List[str] = Field(..., description="Inherited permissions")
    all_permissions: List[str] = Field(..., description="All effective permissions")
    
    class Config:
        schema_extra = {
            "example": {
                "group_id": "987fcdeb-51d2-43a1-b456-426614174000",
                "group_name": "engineering_team",
                "direct_permissions": ["project:read", "asset:read"],
                "role_permissions": ["user:read", "metadata:read"],
                "inherited_permissions": ["system:access"],
                "all_permissions": ["project:read", "asset:read", "user:read", "metadata:read", "system:access"]
            }
        }


class UserGroupsResponse(BaseModel):
    """User groups response model"""
    user_id: UUID = Field(..., description="User ID")
    groups: List[GroupResponse] = Field(..., description="List of user groups")
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "groups": [
                    {
                        "group_id": "987fcdeb-51d2-43a1-b456-426614174000",
                        "name": "engineering_team",
                        "display_name": "Engineering Team",
                        "description": "Software engineering team members",
                        "group_type": "department",
                        "parent_group_id": None,
                        "max_members": 50,
                        "is_active": True,
                        "is_system": False,
                        "member_count": 12,
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z"
                    }
                ]
            }
        }


# MFA Models
class MFASetupRequest(BaseModel):
    """Request model for initiating MFA setup"""
    pass


class MFASetupResponse(BaseResponse):
    """Response model for MFA setup"""
    data: Dict[str, Any] = Field(..., description="MFA setup data")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "MFA setup initiated",
                "timestamp": "2024-01-15T10:30:00Z",
                "data": {
                    "secret": "JBSWY3DPEHPK3PXP",
                    "qr_code": "data:image/png;base64,...",
                    "backup_codes": [
                        "ABCD-1234",
                        "EFGH-5678",
                        "IJKL-9012"
                    ]
                }
            }
        }


class MFAVerifySetupRequest(BaseModel):
    """Request model for verifying MFA setup"""
    code: str = Field(..., min_length=6, max_length=6, description="TOTP code")
    
    class Config:
        schema_extra = {
            "example": {
                "code": "123456"
            }
        }


class MFALoginRequest(BaseModel):
    """Request model for MFA verification during login"""
    code: str = Field(..., min_length=4, max_length=10, description="MFA code (TOTP or backup)")
    code_type: Optional[str] = Field("totp", regex="^(totp|backup|sms)$", description="Type of MFA code")
    
    class Config:
        schema_extra = {
            "example": {
                "code": "123456",
                "code_type": "totp"
            }
        }


class MFAStatusResponse(BaseResponse):
    """Response model for MFA status"""
    data: Dict[str, Any] = Field(..., description="MFA status data")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "MFA status retrieved",
                "timestamp": "2024-01-15T10:30:00Z",
                "data": {
                    "mfa_enabled": True,
                    "backup_codes_count": 10,
                    "methods": ["totp"]
                }
            }
        }


class MFADisableRequest(BaseModel):
    """Request model for disabling MFA"""
    password: str = Field(..., description="User's password for verification")
    
    class Config:
        schema_extra = {
            "example": {
                "password": "SecurePass123!"
            }
        }


class MFARegenerateBackupCodesRequest(BaseModel):
    """Request model for regenerating backup codes"""
    password: str = Field(..., description="User's password for verification")
    
    class Config:
        schema_extra = {
            "example": {
                "password": "SecurePass123!"
            }
        }


class MFARegenerateBackupCodesResponse(BaseResponse):
    """Response model for regenerated backup codes"""
    data: Dict[str, Any] = Field(..., description="New backup codes")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Backup codes regenerated successfully",
                "timestamp": "2024-01-15T10:30:00Z",
                "data": {
                    "backup_codes": [
                        "MNOP-3456",
                        "QRST-7890",
                        "UVWX-1234"
                    ]
                }
            }
        }


class SMSSendCodeRequest(BaseModel):
    """Request model for sending SMS code"""
    phone_number: str = Field(..., description="Phone number to send SMS to")
    
    @validator('phone_number')
    def validate_phone(cls, v):
        """Validate phone number format"""
        # Basic phone number validation
        phone_pattern = re.compile(r'^[\+]?[1-9][\d\s\-\(\)]{6,}$')
        if not phone_pattern.match(v):
            raise ValueError('Invalid phone number format')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "phone_number": "+1-555-123-4567"
            }
        }


class SMSVerifyCodeRequest(BaseModel):
    """Request model for verifying SMS code"""
    code: str = Field(..., min_length=6, max_length=6, description="SMS verification code")
    
    class Config:
        schema_extra = {
            "example": {
                "code": "123456"
            }
        }