"""
Users database models for migrations
"""
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .base import UsersBase, TimestampMixin, UUIDMixin, users_metadata

# Export metadata for alembic
metadata = users_metadata

class Organization(UsersBase, UUIDMixin, TimestampMixin):
    __tablename__ = 'organizations'
    
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, unique=True)
    description = Column(Text)
    settings = Column(JSONB, default={})
    is_active = Column(Boolean, default=True)

class User(UsersBase, UUIDMixin, TimestampMixin):
    __tablename__ = 'users'
    
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'))
    email = Column(String(255), nullable=False, unique=True)
    username = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(255))
    last_name = Column(String(255))
    display_name = Column(String(255))
    avatar_url = Column(String(1024))
    phone = Column(String(50))
    language = Column(String(10), default='en')
    timezone = Column(String(50), default='UTC')
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    email_verified_at = Column(DateTime(timezone=True))
    last_login_at = Column(DateTime(timezone=True))
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True))
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(255))
    settings = Column(JSONB, default={})

class Role(UsersBase, UUIDMixin, TimestampMixin):
    __tablename__ = 'roles'
    
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'))
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False)
    description = Column(Text)
    is_system = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

class Permission(UsersBase, UUIDMixin):
    __tablename__ = 'permissions'
    
    name = Column(String(255), nullable=False, unique=True)
    slug = Column(String(255), nullable=False, unique=True)
    resource = Column(String(255), nullable=False)
    action = Column(String(255), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class RolePermission(UsersBase):
    __tablename__ = 'role_permissions'
    
    role_id = Column(UUID(as_uuid=True), ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True)
    permission_id = Column(UUID(as_uuid=True), ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class UserRole(UsersBase):
    __tablename__ = 'user_roles'
    
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    role_id = Column(UUID(as_uuid=True), ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))

class Group(UsersBase, UUIDMixin, TimestampMixin):
    __tablename__ = 'groups'
    
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    parent_id = Column(UUID(as_uuid=True), ForeignKey('groups.id', ondelete='CASCADE'))
    is_active = Column(Boolean, default=True)

class UserGroup(UsersBase):
    __tablename__ = 'user_groups'
    
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    group_id = Column(UUID(as_uuid=True), ForeignKey('groups.id', ondelete='CASCADE'), primary_key=True)
    added_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    added_at = Column(DateTime(timezone=True), server_default=func.now())

class APIKey(UsersBase, UUIDMixin, TimestampMixin):
    __tablename__ = 'api_keys'
    
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'))
    name = Column(String(255), nullable=False)
    key_hash = Column(String(255), nullable=False, unique=True)
    prefix = Column(String(20), nullable=False)
    last_used_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    scopes = Column(JSONB, default=[])

class Session(UsersBase, UUIDMixin):
    __tablename__ = 'sessions'
    
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'))
    token_hash = Column(String(255), nullable=False, unique=True)
    ip_address = Column(String(45))  # INET type
    user_agent = Column(Text)
    device_info = Column(JSONB, default={})
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())