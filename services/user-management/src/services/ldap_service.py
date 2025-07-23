"""
LDAP Authentication Service

Service for handling LDAP authentication, user provisioning, and group synchronization.
"""

import ldap
import ldap.sasl
import ssl
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4
from datetime import datetime, timezone
import logging
import asyncio
from functools import wraps

from db.models import User, Role, Group, UserRole, UserGroup
from models.schemas import UserCreate, UserUpdate
from core.config import get_settings
from core.exceptions import AuthenticationError, AuthorizationError, ValidationError
from .user_service import UserService
from .rbac_service import RBACService

logger = logging.getLogger(__name__)
settings = get_settings()


def async_ldap_operation(func):
    """Decorator to run LDAP operations in thread pool"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)
    return wrapper


class LDAPConnectionPool:
    """Simple LDAP connection pool for better performance"""
    
    def __init__(self, max_connections: int = 5):
        self.max_connections = max_connections
        self.connections = []
        self.in_use = set()
    
    def get_connection(self) -> ldap.ldapobject.LDAPObject:
        """Get a connection from the pool"""
        # Try to get an existing connection
        for conn in self.connections:
            if conn not in self.in_use:
                self.in_use.add(conn)
                return conn
        
        # Create new connection if pool not full
        if len(self.connections) < self.max_connections:
            conn = self._create_connection()
            self.connections.append(conn)
            self.in_use.add(conn)
            return conn
        
        # Pool is full, create temporary connection
        return self._create_connection()
    
    def return_connection(self, conn: ldap.ldapobject.LDAPObject):
        """Return connection to pool"""
        if conn in self.in_use:
            self.in_use.remove(conn)
    
    def _create_connection(self) -> ldap.ldapobject.LDAPObject:
        """Create a new LDAP connection"""
        ldap_url = f"{'ldaps' if settings.ldap_use_ssl else 'ldap'}://{settings.ldap_server}:{settings.ldap_port}"
        
        conn = ldap.initialize(ldap_url)
        conn.protocol_version = ldap.VERSION3
        conn.set_option(ldap.OPT_REFERRALS, 0)
        conn.set_option(ldap.OPT_NETWORK_TIMEOUT, settings.ldap_connection_timeout)
        conn.set_option(ldap.OPT_TIMEOUT, settings.ldap_search_timeout)
        
        if settings.ldap_use_ssl:
            conn.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
        
        if settings.ldap_use_tls:
            conn.start_tls_s()
        
        return conn


class LDAPService:
    """Service for LDAP authentication and user management"""
    
    def __init__(self):
        self.user_service = UserService()
        self.rbac_service = RBACService()
        self.connection_pool = LDAPConnectionPool(settings.ldap_pool_size)
    
    @async_ldap_operation
    def _bind_connection(self, conn: ldap.ldapobject.LDAPObject, bind_dn: str, password: str) -> bool:
        """Bind to LDAP server with credentials"""
        try:
            conn.simple_bind_s(bind_dn, password)
            return True
        except ldap.INVALID_CREDENTIALS:
            return False
        except ldap.LDAPError as e:
            logger.error(f"LDAP bind error: {e}")
            raise AuthenticationError(f"LDAP connection failed: {e}")
    
    @async_ldap_operation
    def _search_user(self, conn: ldap.ldapobject.LDAPObject, username: str) -> Optional[Dict[str, Any]]:
        """Search for user in LDAP directory"""
        try:
            search_base = settings.ldap_user_search_base or settings.ldap_base_dn
            search_filter = settings.ldap_user_search_filter.format(username=username)
            
            attributes = [
                settings.ldap_username_attr,
                settings.ldap_email_attr,
                settings.ldap_first_name_attr,
                settings.ldap_last_name_attr,
                settings.ldap_display_name_attr,
                settings.ldap_phone_attr,
                settings.ldap_department_attr,
                settings.ldap_organization_attr,
                settings.ldap_groups_attr,
            ]
            
            result = conn.search_s(
                search_base,
                ldap.SCOPE_SUBTREE,
                search_filter,
                attributes
            )
            
            if result:
                dn, attrs = result[0]
                return {
                    'dn': dn,
                    'attributes': attrs
                }
            
            return None
            
        except ldap.LDAPError as e:
            logger.error(f"LDAP search error: {e}")
            raise AuthenticationError(f"LDAP search failed: {e}")
    
    @async_ldap_operation
    def _get_user_groups(self, conn: ldap.ldapobject.LDAPObject, user_dn: str) -> List[str]:
        """Get user's group memberships from LDAP"""
        try:
            if not settings.ldap_group_search_base:
                return []
            
            search_filter = f"(&(objectClass={settings.ldap_group_object_class})({settings.ldap_group_member_attr}={user_dn}))"
            
            result = conn.search_s(
                settings.ldap_group_search_base,
                ldap.SCOPE_SUBTREE,
                search_filter,
                [settings.ldap_group_name_attr]
            )
            
            groups = []
            for dn, attrs in result:
                group_name = attrs.get(settings.ldap_group_name_attr, [])
                if group_name:
                    groups.append(group_name[0].decode('utf-8'))
            
            return groups
            
        except ldap.LDAPError as e:
            logger.error(f"LDAP group search error: {e}")
            return []
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate user against LDAP directory
        
        Args:
            username: Username to authenticate
            password: Password to verify
            
        Returns:
            User object if authentication successful, None otherwise
        """
        if not settings.enable_ldap:
            raise AuthenticationError("LDAP authentication is disabled")
        
        conn = self.connection_pool.get_connection()
        try:
            # First bind with service account to search for user
            await self._bind_connection(conn, settings.ldap_bind_dn, settings.ldap_bind_password)
            
            # Search for user
            user_data = await self._search_user(conn, username)
            if not user_data:
                logger.warning(f"User {username} not found in LDAP")
                return None
            
            # Try to bind with user credentials
            user_dn = user_data['dn']
            auth_success = await self._bind_connection(conn, user_dn, password)
            
            if not auth_success:
                logger.warning(f"Authentication failed for user {username}")
                return None
            
            # Get user's groups
            user_groups = await self._get_user_groups(conn, user_dn)
            
            # Extract user attributes
            attrs = user_data['attributes']
            user_info = self._extract_user_info(attrs, user_groups)
            
            logger.info(f"LDAP authentication successful for user {username}")
            return user_info
            
        except Exception as e:
            logger.error(f"LDAP authentication error for user {username}: {e}")
            return None
        finally:
            self.connection_pool.return_connection(conn)
    
    def _extract_user_info(self, attrs: Dict[str, List[bytes]], groups: List[str]) -> Dict[str, Any]:
        """Extract user information from LDAP attributes"""
        def get_attr_value(attr_name: str, default: str = "") -> str:
            """Get attribute value, handling bytes and multiple values"""
            values = attrs.get(attr_name, [])
            if values:
                return values[0].decode('utf-8') if isinstance(values[0], bytes) else str(values[0])
            return default
        
        # Determine user role based on group membership
        user_role = self._determine_user_role(groups)
        
        return {
            'username': get_attr_value(settings.ldap_username_attr),
            'email': get_attr_value(settings.ldap_email_attr),
            'first_name': get_attr_value(settings.ldap_first_name_attr),
            'last_name': get_attr_value(settings.ldap_last_name_attr),
            'display_name': get_attr_value(settings.ldap_display_name_attr),
            'phone': get_attr_value(settings.ldap_phone_attr),
            'department': get_attr_value(settings.ldap_department_attr),
            'organization': get_attr_value(settings.ldap_organization_attr),
            'groups': groups,
            'role': user_role,
            'is_active': True,
            'is_verified': True,  # LDAP users are pre-verified
            'auth_provider': 'ldap'
        }
    
    def _determine_user_role(self, groups: List[str]) -> str:
        """Determine user role based on group membership"""
        # Check for admin groups
        if any(group in settings.ldap_admin_groups for group in groups):
            return 'admin'
        
        # Check for editor groups
        if any(group in settings.ldap_editor_groups for group in groups):
            return 'editor'
        
        # Check for viewer groups
        if any(group in settings.ldap_viewer_groups for group in groups):
            return 'viewer'
        
        # Default role
        return settings.ldap_default_role
    
    async def get_or_create_user(self, db: AsyncSession, user_info: Dict[str, Any]) -> User:
        """
        Get existing user or create new user from LDAP information
        
        Args:
            db: Database session
            user_info: User information from LDAP
            
        Returns:
            User object
        """
        # Try to find existing user by email or username
        email = user_info.get('email')
        username = user_info.get('username')
        
        existing_user = None
        if email:
            result = await db.execute(select(User).where(User.email == email))
            existing_user = result.scalar_one_or_none()
        
        if not existing_user and username:
            result = await db.execute(select(User).where(User.username == username))
            existing_user = result.scalar_one_or_none()
        
        if existing_user:
            # Update existing user if auto-update is enabled
            if settings.ldap_auto_update_user:
                await self._update_user_from_ldap(db, existing_user, user_info)
            return existing_user
        
        # Create new user if auto-create is enabled
        if settings.ldap_auto_create_user:
            return await self._create_user_from_ldap(db, user_info)
        
        raise AuthenticationError("User not found and auto-creation is disabled")
    
    async def _update_user_from_ldap(self, db: AsyncSession, user: User, user_info: Dict[str, Any]):
        """Update existing user with LDAP information"""
        try:
            # Update user attributes
            user.first_name = user_info.get('first_name') or user.first_name
            user.last_name = user_info.get('last_name') or user.last_name
            user.display_name = user_info.get('display_name') or user.display_name
            user.phone = user_info.get('phone') or user.phone
            user.department = user_info.get('department') or user.department
            user.organization = user_info.get('organization') or user.organization
            user.is_active = user_info.get('is_active', True)
            user.is_verified = user_info.get('is_verified', True)
            user.auth_provider = 'ldap'
            user.updated_at = datetime.now(timezone.utc)
            
            # Update user roles and groups
            await self._sync_user_roles_and_groups(db, user, user_info)
            
            await db.commit()
            logger.info(f"Updated user {user.email} from LDAP")
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to update user {user.email} from LDAP: {e}")
            raise
    
    async def _create_user_from_ldap(self, db: AsyncSession, user_info: Dict[str, Any]) -> User:
        """Create new user from LDAP information"""
        try:
            # Create new user
            user = User(
                user_id=uuid4(),
                email=user_info.get('email'),
                username=user_info.get('username'),
                first_name=user_info.get('first_name', ''),
                last_name=user_info.get('last_name', ''),
                display_name=user_info.get('display_name'),
                phone=user_info.get('phone'),
                department=user_info.get('department'),
                organization=user_info.get('organization'),
                is_active=user_info.get('is_active', True),
                is_verified=user_info.get('is_verified', True),
                auth_provider='ldap',
                password_hash=None,  # No password for LDAP users
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            db.add(user)
            await db.flush()  # Get user ID
            
            # Assign roles and groups
            await self._sync_user_roles_and_groups(db, user, user_info)
            
            await db.commit()
            logger.info(f"Created user {user.email} from LDAP")
            return user
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to create user from LDAP: {e}")
            raise
    
    async def _sync_user_roles_and_groups(self, db: AsyncSession, user: User, user_info: Dict[str, Any]):
        """Synchronize user roles and groups from LDAP"""
        # Get or create role
        role_name = user_info.get('role', settings.ldap_default_role)
        result = await db.execute(select(Role).where(Role.name == role_name))
        role = result.scalar_one_or_none()
        
        if not role:
            # Create default role if it doesn't exist
            role = Role(
                role_id=uuid4(),
                name=role_name,
                display_name=role_name.title(),
                description=f"Default {role_name} role from LDAP",
                role_type='ldap',
                is_active=True,
                created_at=datetime.now(timezone.utc)
            )
            db.add(role)
            await db.flush()
        
        # Assign role to user
        existing_role = await db.execute(
            select(UserRole).where(
                UserRole.user_id == user.user_id,
                UserRole.role_id == role.role_id
            )
        )
        
        if not existing_role.scalar_one_or_none():
            user_role = UserRole(
                user_id=user.user_id,
                role_id=role.role_id,
                assigned_at=datetime.now(timezone.utc)
            )
            db.add(user_role)
        
        # Sync groups
        ldap_groups = user_info.get('groups', [])
        for group_name in ldap_groups:
            # Get or create group
            result = await db.execute(select(Group).where(Group.name == group_name))
            group = result.scalar_one_or_none()
            
            if not group:
                group = Group(
                    group_id=uuid4(),
                    name=group_name,
                    display_name=group_name,
                    description=f"LDAP group: {group_name}",
                    group_type='ldap',
                    is_active=True,
                    is_system=False,
                    created_at=datetime.now(timezone.utc)
                )
                db.add(group)
                await db.flush()
            
            # Add user to group
            existing_membership = await db.execute(
                select(UserGroup).where(
                    UserGroup.user_id == user.user_id,
                    UserGroup.group_id == group.group_id
                )
            )
            
            if not existing_membership.scalar_one_or_none():
                user_group = UserGroup(
                    user_id=user.user_id,
                    group_id=group.group_id,
                    joined_at=datetime.now(timezone.utc)
                )
                db.add(user_group)
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test LDAP connection and configuration"""
        if not settings.enable_ldap:
            return {"status": "disabled", "message": "LDAP authentication is disabled"}
        
        conn = self.connection_pool.get_connection()
        try:
            # Test service account bind
            await self._bind_connection(conn, settings.ldap_bind_dn, settings.ldap_bind_password)
            
            # Test search
            search_result = await self._search_user(conn, "test")
            
            return {
                "status": "success",
                "message": "LDAP connection successful",
                "server": settings.ldap_server,
                "port": settings.ldap_port,
                "base_dn": settings.ldap_base_dn,
                "user_search_base": settings.ldap_user_search_base or settings.ldap_base_dn,
                "group_search_base": settings.ldap_group_search_base
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"LDAP connection failed: {str(e)}"
            }
        finally:
            self.connection_pool.return_connection(conn)
    
    async def sync_users(self, db: AsyncSession) -> Dict[str, Any]:
        """Synchronize all users from LDAP directory"""
        if not settings.enable_ldap:
            raise ValidationError("LDAP authentication is disabled")
        
        conn = self.connection_pool.get_connection()
        try:
            # Bind with service account
            await self._bind_connection(conn, settings.ldap_bind_dn, settings.ldap_bind_password)
            
            # Search for all users
            search_base = settings.ldap_user_search_base or settings.ldap_base_dn
            search_filter = f"(objectClass={settings.ldap_user_object_class})"
            
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: conn.search_s(
                    search_base,
                    ldap.SCOPE_SUBTREE,
                    search_filter,
                    [
                        settings.ldap_username_attr,
                        settings.ldap_email_attr,
                        settings.ldap_first_name_attr,
                        settings.ldap_last_name_attr,
                        settings.ldap_display_name_attr,
                        settings.ldap_phone_attr,
                        settings.ldap_department_attr,
                        settings.ldap_organization_attr,
                        settings.ldap_groups_attr,
                    ]
                )
            )
            
            synced_users = []
            errors = []
            
            for user_dn, attrs in result:
                try:
                    # Get user groups
                    user_groups = await self._get_user_groups(conn, user_dn)
                    
                    # Extract user info
                    user_info = self._extract_user_info(attrs, user_groups)
                    
                    # Create or update user
                    user = await self.get_or_create_user(db, user_info)
                    synced_users.append(user.email)
                    
                except Exception as e:
                    errors.append(f"Failed to sync user {user_dn}: {str(e)}")
                    logger.error(f"Failed to sync user {user_dn}: {e}")
            
            return {
                "status": "completed",
                "synced_users": len(synced_users),
                "errors": len(errors),
                "users": synced_users,
                "error_details": errors
            }
            
        except Exception as e:
            logger.error(f"LDAP sync failed: {e}")
            return {
                "status": "failed",
                "message": str(e)
            }
        finally:
            self.connection_pool.return_connection(conn)