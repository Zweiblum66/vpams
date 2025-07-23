"""
Database models for User Management Service

This module contains all SQLAlchemy models for user management,
including users, roles, permissions, and related entities.
"""

from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID, uuid4

from sqlalchemy import (
    Column, String, Boolean, DateTime, Text, Integer, 
    ForeignKey, Table, Index, UniqueConstraint, JSON
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func

from .base import Base


# Association table for user-role many-to-many relationship
user_role_association = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', PostgresUUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('role_id', PostgresUUID(as_uuid=True), ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('assigned_at', DateTime(timezone=True), server_default=func.now()),
    Column('assigned_by', PostgresUUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL')),
    Index('idx_user_role_user_id', 'user_id'),
    Index('idx_user_role_role_id', 'role_id'),
)

# Association table for role-permission many-to-many relationship
role_permission_association = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', PostgresUUID(as_uuid=True), ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', PostgresUUID(as_uuid=True), ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True),
    Column('granted_at', DateTime(timezone=True), server_default=func.now()),
    Column('granted_by', PostgresUUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL')),
    Index('idx_role_permission_role_id', 'role_id'),
    Index('idx_role_permission_permission_id', 'permission_id'),
)

# Association table for user-group many-to-many relationship
user_group_association = Table(
    'user_groups',
    Base.metadata,
    Column('user_id', PostgresUUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('group_id', PostgresUUID(as_uuid=True), ForeignKey('groups.id', ondelete='CASCADE'), primary_key=True),
    Column('joined_at', DateTime(timezone=True), server_default=func.now()),
    Column('added_by', PostgresUUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL')),
    Index('idx_user_group_user_id', 'user_id'),
    Index('idx_user_group_group_id', 'group_id'),
)

# Association table for group-role many-to-many relationship
group_role_association = Table(
    'group_roles',
    Base.metadata,
    Column('group_id', PostgresUUID(as_uuid=True), ForeignKey('groups.id', ondelete='CASCADE'), primary_key=True),
    Column('role_id', PostgresUUID(as_uuid=True), ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('assigned_at', DateTime(timezone=True), server_default=func.now()),
    Column('assigned_by', PostgresUUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL')),
    Index('idx_group_role_group_id', 'group_id'),
    Index('idx_group_role_role_id', 'role_id'),
)

# Association table for group-permission many-to-many relationship
group_permission_association = Table(
    'group_permissions',
    Base.metadata,
    Column('group_id', PostgresUUID(as_uuid=True), ForeignKey('groups.id', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', PostgresUUID(as_uuid=True), ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True),
    Column('granted_at', DateTime(timezone=True), server_default=func.now()),
    Column('granted_by', PostgresUUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL')),
    Index('idx_group_permission_group_id', 'group_id'),
    Index('idx_group_permission_permission_id', 'permission_id'),
)


class User(Base):
    """
    User model for authentication and identification
    
    Represents a user in the system with authentication credentials,
    basic profile information, and account status.
    """
    __tablename__ = 'users'
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), 
        primary_key=True, 
        default=uuid4
    )
    
    # Authentication fields
    email: Mapped[str] = mapped_column(
        String(255), 
        unique=True, 
        nullable=False, 
        index=True
    )
    username: Mapped[Optional[str]] = mapped_column(
        String(50), 
        unique=True, 
        nullable=True, 
        index=True
    )
    password_hash: Mapped[Optional[str]] = mapped_column(
        String(255), 
        nullable=True
    )
    
    # Profile fields
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    display_name: Mapped[Optional[str]] = mapped_column(String(200))
    
    # Account status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Authentication provider
    auth_provider: Mapped[str] = mapped_column(String(50), default="local", nullable=False)
    
    # Security fields
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    account_locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    password_changed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Email verification
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    email_verification_token: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Password reset
    password_reset_token: Mapped[Optional[str]] = mapped_column(String(255))
    password_reset_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # MFA settings
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_secret: Mapped[Optional[str]] = mapped_column(String(255))
    backup_codes: Mapped[Optional[List[str]]] = mapped_column(JSON)
    
    # SAML session tracking
    saml_session_index: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now()
    )
    created_by: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True), 
        ForeignKey('users.id', ondelete='SET NULL')
    )
    
    # Relationships
    roles: Mapped[List["Role"]] = relationship(
        "Role",
        secondary=user_role_association,
        back_populates="users",
        lazy="selectin"
    )
    
    groups: Mapped[List["Group"]] = relationship(
        "Group",
        secondary=user_group_association,
        back_populates="users",
        lazy="selectin"
    )
    
    profile: Mapped[Optional["UserProfile"]] = relationship(
        "UserProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    sessions: Mapped[List["UserSession"]] = relationship(
        "UserSession",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    # Self-referential relationship for created_by
    created_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        remote_side=[id],
        back_populates="created_users"
    )
    
    created_users: Mapped[List["User"]] = relationship(
        "User",
        back_populates="created_by_user"
    )
    
    created_groups: Mapped[List["Group"]] = relationship(
        "Group",
        foreign_keys="Group.created_by",
        back_populates="created_by_user"
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_users_email', 'email'),
        Index('idx_users_username', 'username'),
        Index('idx_users_is_active', 'is_active'),
        Index('idx_users_created_at', 'created_at'),
        Index('idx_users_last_login', 'last_login_at'),
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, active={self.is_active})>"


class Role(Base):
    """
    Role model for authorization
    
    Represents a role that can be assigned to users,
    containing a set of permissions.
    """
    __tablename__ = 'roles'
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), 
        primary_key=True, 
        default=uuid4
    )
    
    # Role information
    name: Mapped[str] = mapped_column(
        String(100), 
        unique=True, 
        nullable=False, 
        index=True
    )
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Role type and hierarchy
    role_type: Mapped[str] = mapped_column(
        String(50), 
        nullable=False, 
        default='custom'
    )  # system, built-in, custom
    
    parent_role_id: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True), 
        ForeignKey('roles.id', ondelete='SET NULL')
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now()
    )
    created_by: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True), 
        ForeignKey('users.id', ondelete='SET NULL')
    )
    
    # Relationships
    users: Mapped[List["User"]] = relationship(
        "User",
        secondary=user_role_association,
        back_populates="roles"
    )
    
    permissions: Mapped[List["Permission"]] = relationship(
        "Permission",
        secondary=role_permission_association,
        back_populates="roles",
        lazy="selectin"
    )
    
    groups: Mapped[List["Group"]] = relationship(
        "Group",
        secondary=group_role_association,
        back_populates="roles",
        lazy="selectin"
    )
    
    # Self-referential relationship for role hierarchy
    parent_role: Mapped[Optional["Role"]] = relationship(
        "Role",
        remote_side=[id],
        back_populates="child_roles"
    )
    
    child_roles: Mapped[List["Role"]] = relationship(
        "Role",
        back_populates="parent_role"
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_roles_name', 'name'),
        Index('idx_roles_type', 'role_type'),
        Index('idx_roles_is_active', 'is_active'),
        Index('idx_roles_parent_id', 'parent_role_id'),
    )
    
    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name={self.name}, type={self.role_type})>"


class Group(Base):
    """
    Group model for organizing users
    
    Represents a group of users that can be assigned roles and permissions
    collectively, providing a convenient way to manage access control
    for sets of users.
    """
    __tablename__ = 'groups'
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), 
        primary_key=True, 
        default=uuid4
    )
    
    # Group information
    name: Mapped[str] = mapped_column(
        String(100), 
        unique=True, 
        nullable=False, 
        index=True
    )
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Group type and hierarchy
    group_type: Mapped[str] = mapped_column(
        String(50), 
        nullable=False, 
        default="custom",
        index=True
    )
    parent_group_id: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True), 
        ForeignKey('groups.id', ondelete='SET NULL')
    )
    
    # Status and settings
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    max_members: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now()
    )
    created_by: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True), 
        ForeignKey('users.id', ondelete='SET NULL')
    )
    
    # Relationships
    users: Mapped[List["User"]] = relationship(
        "User",
        secondary=user_group_association,
        back_populates="groups",
        lazy="selectin"
    )
    
    roles: Mapped[List["Role"]] = relationship(
        "Role",
        secondary=group_role_association,
        back_populates="groups",
        lazy="selectin"
    )
    
    permissions: Mapped[List["Permission"]] = relationship(
        "Permission",
        secondary=group_permission_association,
        back_populates="groups",
        lazy="selectin"
    )
    
    # Self-referential relationship for hierarchy
    parent_group: Mapped[Optional["Group"]] = relationship(
        "Group",
        remote_side=[id],
        back_populates="child_groups"
    )
    
    child_groups: Mapped[List["Group"]] = relationship(
        "Group",
        back_populates="parent_group"
    )
    
    # Creator relationship
    created_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by],
        back_populates="created_groups"
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_groups_name', 'name'),
        Index('idx_groups_type', 'group_type'),
        Index('idx_groups_is_active', 'is_active'),
        Index('idx_groups_created_at', 'created_at'),
        Index('idx_groups_parent_group', 'parent_group_id'),
        UniqueConstraint('name', name='uq_groups_name'),
    )
    
    def __repr__(self) -> str:
        return f"<Group(id={self.id}, name={self.name}, type={self.group_type})>"


class Permission(Base):
    """
    Permission model for fine-grained access control
    
    Represents a specific permission that can be granted to roles,
    following the resource:action pattern.
    """
    __tablename__ = 'permissions'
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), 
        primary_key=True, 
        default=uuid4
    )
    
    # Permission information
    name: Mapped[str] = mapped_column(
        String(100), 
        unique=True, 
        nullable=False, 
        index=True
    )
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Permission structure
    resource: Mapped[str] = mapped_column(
        String(50), 
        nullable=False, 
        index=True
    )  # e.g., 'asset', 'user', 'project'
    
    action: Mapped[str] = mapped_column(
        String(50), 
        nullable=False, 
        index=True
    )  # e.g., 'read', 'write', 'delete', 'admin'
    
    # Permission category and scope
    category: Mapped[str] = mapped_column(
        String(50), 
        nullable=False, 
        default='general'
    )  # system, content, admin, etc.
    
    scope: Mapped[str] = mapped_column(
        String(50), 
        nullable=False, 
        default='global'
    )  # global, tenant, project, personal
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now()
    )
    created_by: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True), 
        ForeignKey('users.id', ondelete='SET NULL')
    )
    
    # Relationships
    roles: Mapped[List["Role"]] = relationship(
        "Role",
        secondary=role_permission_association,
        back_populates="permissions"
    )
    
    groups: Mapped[List["Group"]] = relationship(
        "Group",
        secondary=group_permission_association,
        back_populates="permissions",
        lazy="selectin"
    )
    
    # Indexes and constraints
    __table_args__ = (
        Index('idx_permissions_name', 'name'),
        Index('idx_permissions_resource', 'resource'),
        Index('idx_permissions_action', 'action'),
        Index('idx_permissions_category', 'category'),
        Index('idx_permissions_scope', 'scope'),
        Index('idx_permissions_resource_action', 'resource', 'action'),
        UniqueConstraint('resource', 'action', name='uq_permission_resource_action'),
    )
    
    def __repr__(self) -> str:
        return f"<Permission(id={self.id}, name={self.name}, resource={self.resource}, action={self.action})>"


class UserProfile(Base):
    """
    Extended user profile information
    
    Contains additional user information beyond basic authentication data,
    including preferences, settings, and extended profile data.
    """
    __tablename__ = 'user_profiles'
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), 
        primary_key=True, 
        default=uuid4
    )
    
    # Foreign key to user
    user_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), 
        ForeignKey('users.id', ondelete='CASCADE'), 
        unique=True
    )
    
    # Extended profile fields
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    department: Mapped[Optional[str]] = mapped_column(String(100))
    job_title: Mapped[Optional[str]] = mapped_column(String(100))
    organization: Mapped[Optional[str]] = mapped_column(String(200))
    location: Mapped[Optional[str]] = mapped_column(String(200))
    timezone: Mapped[Optional[str]] = mapped_column(String(50))
    language: Mapped[Optional[str]] = mapped_column(String(10), default='en')
    
    # Contact information
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500))
    bio: Mapped[Optional[str]] = mapped_column(Text)
    website: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Preferences
    preferences: Mapped[Optional[dict]] = mapped_column(JSON)
    ui_settings: Mapped[Optional[dict]] = mapped_column(JSON)
    notification_settings: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Activity tracking
    last_activity_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    login_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now()
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="profile"
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_user_profiles_user_id', 'user_id'),
        Index('idx_user_profiles_department', 'department'),
        Index('idx_user_profiles_organization', 'organization'),
        Index('idx_user_profiles_last_activity', 'last_activity_at'),
    )
    
    def __repr__(self) -> str:
        return f"<UserProfile(id={self.id}, user_id={self.user_id})>"


class UserSession(Base):
    """
    User session tracking
    
    Tracks active user sessions for security and audit purposes.
    """
    __tablename__ = 'user_sessions'
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), 
        primary_key=True, 
        default=uuid4
    )
    
    # Foreign key to user
    user_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), 
        ForeignKey('users.id', ondelete='CASCADE')
    )
    
    # Session information
    session_token: Mapped[str] = mapped_column(
        String(255), 
        unique=True, 
        nullable=False, 
        index=True
    )
    refresh_token: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Session metadata
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    device_type: Mapped[Optional[str]] = mapped_column(String(50))
    device_id: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Session lifecycle
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    
    # Session status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    end_reason: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="sessions"
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_user_sessions_user_id', 'user_id'),
        Index('idx_user_sessions_token', 'session_token'),
        Index('idx_user_sessions_is_active', 'is_active'),
        Index('idx_user_sessions_expires_at', 'expires_at'),
        Index('idx_user_sessions_last_activity', 'last_activity_at'),
    )
    
    def __repr__(self) -> str:
        return f"<UserSession(id={self.id}, user_id={self.user_id}, active={self.is_active})>"


# Additional association models for audit trails
class UserRole(Base):
    """
    User-Role association with audit information
    
    Tracks when roles are assigned/removed from users and by whom.
    """
    __tablename__ = 'user_role_history'
    
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), 
        primary_key=True, 
        default=uuid4
    )
    
    user_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), 
        ForeignKey('users.id', ondelete='CASCADE')
    )
    
    role_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), 
        ForeignKey('roles.id', ondelete='CASCADE')
    )
    
    # Audit fields
    action: Mapped[str] = mapped_column(String(20))  # 'assigned', 'removed'
    reason: Mapped[Optional[str]] = mapped_column(Text)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    created_by: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True), 
        ForeignKey('users.id', ondelete='SET NULL')
    )
    
    __table_args__ = (
        Index('idx_user_role_history_user_id', 'user_id'),
        Index('idx_user_role_history_role_id', 'role_id'),
        Index('idx_user_role_history_created_at', 'created_at'),
    )


class RolePermission(Base):
    """
    Role-Permission association with audit information
    
    Tracks when permissions are granted/revoked from roles and by whom.
    """
    __tablename__ = 'role_permission_history'
    
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), 
        primary_key=True, 
        default=uuid4
    )
    
    role_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), 
        ForeignKey('roles.id', ondelete='CASCADE')
    )
    
    permission_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), 
        ForeignKey('permissions.id', ondelete='CASCADE')
    )
    
    # Audit fields
    action: Mapped[str] = mapped_column(String(20))  # 'granted', 'revoked'
    reason: Mapped[Optional[str]] = mapped_column(Text)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    created_by: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True), 
        ForeignKey('users.id', ondelete='SET NULL')
    )
    
    __table_args__ = (
        Index('idx_role_permission_history_role_id', 'role_id'),
        Index('idx_role_permission_history_permission_id', 'permission_id'),
        Index('idx_role_permission_history_created_at', 'created_at'),
    )