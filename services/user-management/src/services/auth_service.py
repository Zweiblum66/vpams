"""
Authentication Service

Service for handling authentication and authorization logic.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from uuid import UUID
import logging

from db.models import User, UserSession, Role, Permission
from core.security import (
    create_access_token,
    create_refresh_token,
    verify_token,
    get_password_hash,
    verify_password,
    generate_verification_token,
    verify_verification_token,
    generate_reset_token,
    verify_reset_token
)
from core.config import get_settings
from .lockout_service import AccountLockoutService

logger = logging.getLogger(__name__)
settings = get_settings()

# Import LDAP service if enabled
if settings.enable_ldap:
    from .ldap_service import LDAPService

# Import OAuth2 service if enabled
if settings.enable_oauth2:
    from .oauth2_service import OAuth2Service

# Import SAML service if enabled
if settings.enable_saml:
    from .saml_service import SAMLService


class AuthService:
    """Service for authentication and authorization operations"""
    
    def __init__(self):
        self.lockout_service = AccountLockoutService()
        self.ldap_service = LDAPService() if settings.enable_ldap else None
        self.oauth2_service = OAuth2Service() if settings.enable_oauth2 else None
        self.saml_service = SAMLService() if settings.enable_saml else None
    
    async def authenticate_user(
        self, 
        db: AsyncSession, 
        email: str, 
        password: str
    ) -> tuple[Optional[User], Optional[Dict[str, Any]]]:
        """
        Authenticate user with email and password
        
        Returns:
            Tuple of (User object or None, lockout info or None)
        """
        try:
            # Try LDAP authentication first if enabled
            if self.ldap_service:
                ldap_user = await self._authenticate_with_ldap(db, email, password)
                if ldap_user:
                    return ldap_user, None
            
            # Fall back to local authentication
            return await self._authenticate_local(db, email, password)
            
        except Exception as e:
            logger.error(f"Authentication failed for {email}: {e}")
            return None, None
    
    async def _authenticate_with_ldap(
        self, 
        db: AsyncSession, 
        email: str, 
        password: str
    ) -> Optional[User]:
        """Authenticate user with LDAP"""
        try:
            # Extract username from email if needed
            username = email.split('@')[0] if '@' in email else email
            
            # Try LDAP authentication
            ldap_user_info = await self.ldap_service.authenticate_user(username, password)
            
            if ldap_user_info:
                # Get or create user in local database
                user = await self.ldap_service.get_or_create_user(db, ldap_user_info)
                
                # Record successful login
                await self.lockout_service.record_successful_login(db, user)
                
                logger.info(f"LDAP authentication successful for {email}")
                return user
            
            return None
            
        except Exception as e:
            logger.error(f"LDAP authentication failed for {email}: {e}")
            return None
    
    async def _authenticate_local(
        self, 
        db: AsyncSession, 
        email: str, 
        password: str
    ) -> tuple[Optional[User], Optional[Dict[str, Any]]]:
        """Authenticate user with local credentials"""
        try:
            # Get user by email
            result = await db.execute(
                select(User).where(User.email == email)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return None, None
            
            # Skip local auth for external auth provider users
            if user.auth_provider == 'ldap':
                return None, {"message": "LDAP users must authenticate through LDAP"}
            elif user.auth_provider == 'oauth2':
                return None, {"message": "OAuth2 users must authenticate through their provider"}
            elif user.auth_provider == 'saml':
                return None, {"message": "SAML users must authenticate through their identity provider"}
            
            # Check if account is locked
            if await self.lockout_service.is_account_locked(db, user):
                lockout_info = await self.lockout_service.get_lockout_info(user)
                return None, lockout_info
            
            # Check if user is active
            if not user.is_active:
                return None, {"message": "Account is deactivated"}
            
            # Verify password
            if not verify_password(password, user.password_hash):
                # Record failed login attempt
                lockout_info = await self.lockout_service.record_failed_attempt(db, user)
                return None, lockout_info
            
            # Record successful login (resets failed attempts)
            await self.lockout_service.record_successful_login(db, user)
            
            return user, None
            
        except Exception as e:
            logger.error(f"Local authentication failed for {email}: {e}")
            return None, None
    
    async def create_user_session(
        self,
        db: AsyncSession,
        user: User,
        device_info: Optional[Dict[str, str]] = None,
        remember_me: bool = False
    ) -> Dict[str, Any]:
        """Create user session and return tokens"""
        try:
            # Update last login
            user.last_login_at = datetime.now(timezone.utc)
            
            # Create tokens
            access_token = create_access_token(data={"sub": str(user.id)})
            refresh_token = create_refresh_token(data={"sub": str(user.id)})
            
            # Create session record
            session = UserSession(
                user_id=user.id,
                refresh_token=refresh_token,
                device_info=device_info or {},
                expires_at=datetime.now(timezone.utc) + timedelta(
                    days=settings.refresh_token_expiration_days
                ),
                is_active=True,
                created_at=datetime.now(timezone.utc)
            )
            
            db.add(session)
            await db.commit()
            
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": settings.jwt_expiration_minutes * 60,
                "session_id": str(session.id)
            }
            
        except Exception as e:
            logger.error(f"Failed to create user session: {e}")
            raise
    
    async def refresh_access_token(
        self,
        db: AsyncSession,
        refresh_token: str
    ) -> Optional[Dict[str, Any]]:
        """Refresh access token using refresh token"""
        try:
            # Verify refresh token
            token_data = verify_token(refresh_token)
            if not token_data:
                return None
            
            user_id = UUID(token_data.sub)
            
            # Get active session
            result = await db.execute(
                select(UserSession).where(
                    UserSession.user_id == user_id,
                    UserSession.refresh_token == refresh_token,
                    UserSession.is_active == True,
                    UserSession.expires_at > datetime.now(timezone.utc)
                )
            )
            session = result.scalar_one_or_none()
            
            if not session:
                return None
            
            # Get user
            result = await db.execute(
                select(User).where(
                    User.id == user_id,
                    User.is_active == True
                )
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return None
            
            # Create new access token
            access_token = create_access_token(data={"sub": str(user_id)})
            
            # Update session
            session.last_used_at = datetime.now(timezone.utc)
            await db.commit()
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": settings.jwt_expiration_minutes * 60
            }
            
        except Exception as e:
            logger.error(f"Failed to refresh access token: {e}")
            return None
    
    async def logout_user(
        self,
        db: AsyncSession,
        user_id: UUID,
        refresh_token: Optional[str] = None
    ) -> bool:
        """Logout user and invalidate session"""
        try:
            if refresh_token:
                # Invalidate specific session
                result = await db.execute(
                    select(UserSession).where(
                        UserSession.user_id == user_id,
                        UserSession.refresh_token == refresh_token,
                        UserSession.is_active == True
                    )
                )
                session = result.scalar_one_or_none()
                
                if session:
                    session.is_active = False
                    session.logged_out_at = datetime.now(timezone.utc)
            else:
                # Invalidate all sessions for user
                result = await db.execute(
                    select(UserSession).where(
                        UserSession.user_id == user_id,
                        UserSession.is_active == True
                    )
                )
                sessions = result.scalars().all()
                
                for session in sessions:
                    session.is_active = False
                    session.logged_out_at = datetime.now(timezone.utc)
            
            await db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to logout user: {e}")
            await db.rollback()
            return False
    
    async def get_user_permissions(
        self,
        db: AsyncSession,
        user: User
    ) -> set[str]:
        """Get all permissions for a user"""
        try:
            # Load user roles
            await db.refresh(user, ["roles"])
            
            permissions = set()
            for role in user.roles:
                # Load role permissions
                await db.refresh(role, ["permissions"])
                for permission in role.permissions:
                    permissions.add(permission.name)
            
            return permissions
            
        except Exception as e:
            logger.error(f"Failed to get user permissions: {e}")
            return set()
    
    async def check_user_permission(
        self,
        db: AsyncSession,
        user: User,
        permission_name: str
    ) -> bool:
        """Check if user has specific permission"""
        try:
            permissions = await self.get_user_permissions(db, user)
            return permission_name in permissions
            
        except Exception as e:
            logger.error(f"Failed to check user permission: {e}")
            return False
    
    async def check_user_role(
        self,
        db: AsyncSession,
        user: User,
        role_name: str
    ) -> bool:
        """Check if user has specific role"""
        try:
            # Load user roles
            await db.refresh(user, ["roles"])
            
            user_roles = {role.name for role in user.roles}
            return role_name in user_roles
            
        except Exception as e:
            logger.error(f"Failed to check user role: {e}")
            return False
    
    async def generate_email_verification_token(
        self,
        user_id: UUID
    ) -> str:
        """Generate email verification token"""
        try:
            return generate_verification_token(str(user_id))
        except Exception as e:
            logger.error(f"Failed to generate verification token: {e}")
            raise
    
    async def verify_email_token(
        self,
        db: AsyncSession,
        token: str
    ) -> Optional[User]:
        """Verify email verification token"""
        try:
            # Verify token
            user_id = verify_verification_token(token)
            if not user_id:
                return None
            
            # Get user
            result = await db.execute(
                select(User).where(User.id == UUID(user_id))
            )
            user = result.scalar_one_or_none()
            
            return user
            
        except Exception as e:
            logger.error(f"Failed to verify email token: {e}")
            return None
    
    async def generate_password_reset_token(
        self,
        user_id: UUID
    ) -> str:
        """Generate password reset token"""
        try:
            return generate_reset_token(str(user_id))
        except Exception as e:
            logger.error(f"Failed to generate reset token: {e}")
            raise
    
    async def verify_password_reset_token(
        self,
        db: AsyncSession,
        token: str
    ) -> Optional[User]:
        """Verify password reset token"""
        try:
            # Verify token
            user_id = verify_reset_token(token)
            if not user_id:
                return None
            
            # Get user
            result = await db.execute(
                select(User).where(User.id == UUID(user_id))
            )
            user = result.scalar_one_or_none()
            
            return user
            
        except Exception as e:
            logger.error(f"Failed to verify reset token: {e}")
            return None
    
    async def reset_user_password(
        self,
        db: AsyncSession,
        user: User,
        new_password: str
    ) -> bool:
        """Reset user password"""
        try:
            # Update password
            user.password_hash = get_password_hash(new_password)
            user.updated_at = datetime.now(timezone.utc)
            
            # Invalidate all sessions
            await self.logout_user(db, user.id)
            
            await db.commit()
            
            logger.info(f"Password reset successfully for user: {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset password: {e}")
            await db.rollback()
            return False
    
    async def cleanup_expired_sessions(self, db: AsyncSession) -> int:
        """Clean up expired sessions"""
        try:
            # Get expired sessions
            result = await db.execute(
                select(UserSession).where(
                    UserSession.expires_at < datetime.now(timezone.utc)
                )
            )
            expired_sessions = result.scalars().all()
            
            # Delete expired sessions
            for session in expired_sessions:
                await db.delete(session)
            
            await db.commit()
            
            count = len(expired_sessions)
            logger.info(f"Cleaned up {count} expired sessions")
            return count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            await db.rollback()
            return 0
    
    async def get_active_sessions(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> list[UserSession]:
        """Get active sessions for user"""
        try:
            result = await db.execute(
                select(UserSession).where(
                    UserSession.user_id == user_id,
                    UserSession.is_active == True,
                    UserSession.expires_at > datetime.now(timezone.utc)
                ).order_by(UserSession.created_at.desc())
            )
            sessions = result.scalars().all()
            
            return list(sessions)
            
        except Exception as e:
            logger.error(f"Failed to get active sessions: {e}")
            return []
    
    # OAuth2 authentication methods
    
    def get_oauth2_providers(self) -> list[str]:
        """Get list of available OAuth2 providers"""
        if not self.oauth2_service:
            return []
        
        return self.oauth2_service.get_available_providers()
    
    def generate_oauth2_auth_url(self, provider: str) -> Dict[str, str]:
        """Generate OAuth2 authorization URL"""
        if not self.oauth2_service:
            raise ValueError("OAuth2 authentication is not enabled")
        
        return self.oauth2_service.generate_auth_url(provider)
    
    async def authenticate_oauth2_user(
        self,
        db: AsyncSession,
        provider: str,
        code: str,
        state: str
    ) -> Optional[User]:
        """Authenticate user with OAuth2 authorization code"""
        if not self.oauth2_service:
            raise ValueError("OAuth2 authentication is not enabled")
        
        try:
            user = await self.oauth2_service.authenticate_with_code(provider, code, state, db)
            
            if user:
                # Record successful login
                await self.lockout_service.record_successful_login(db, user)
                logger.info(f"OAuth2 authentication successful for {user.email} via {provider}")
            
            return user
            
        except Exception as e:
            logger.error(f"OAuth2 authentication failed: {e}")
            raise
    
    async def get_oauth2_provider_info(self, provider: str) -> Dict[str, Any]:
        """Get OAuth2 provider information"""
        if not self.oauth2_service:
            raise ValueError("OAuth2 authentication is not enabled")
        
        return await self.oauth2_service.get_provider_info(provider)
    
    async def test_oauth2_provider(self, provider: str) -> Dict[str, Any]:
        """Test OAuth2 provider configuration"""
        if not self.oauth2_service:
            return {
                "status": "disabled",
                "message": "OAuth2 authentication is not enabled"
            }
        
        return await self.oauth2_service.test_provider_connection(provider)
    
    # SAML authentication methods
    
    def create_saml_auth_request(self, request_data: Dict[str, Any], 
                               return_to: Optional[str] = None) -> str:
        """Create SAML authentication request"""
        if not self.saml_service:
            raise ValueError("SAML authentication is not enabled")
        
        return self.saml_service.create_auth_request(request_data, return_to)
    
    async def process_saml_response(
        self,
        db: AsyncSession,
        request_data: Dict[str, Any]
    ) -> Optional[User]:
        """Process SAML authentication response"""
        if not self.saml_service:
            raise ValueError("SAML authentication is not enabled")
        
        try:
            user = await self.saml_service.process_auth_response(request_data, db)
            
            if user:
                # Record successful login
                await self.lockout_service.record_successful_login(db, user)
                logger.info(f"SAML authentication successful for {user.email}")
            
            return user
            
        except Exception as e:
            logger.error(f"SAML authentication failed: {e}")
            raise
    
    def create_saml_logout_request(self, request_data: Dict[str, Any],
                                 name_id: str, session_index: Optional[str] = None) -> str:
        """Create SAML logout request"""
        if not self.saml_service:
            raise ValueError("SAML authentication is not enabled")
        
        return self.saml_service.create_logout_request(request_data, name_id, session_index)
    
    async def process_saml_logout_response(self, request_data: Dict[str, Any]) -> bool:
        """Process SAML logout response"""
        if not self.saml_service:
            raise ValueError("SAML authentication is not enabled")
        
        return await self.saml_service.process_logout_response(request_data)
    
    def get_saml_metadata(self) -> str:
        """Get SAML SP metadata"""
        if not self.saml_service:
            raise ValueError("SAML authentication is not enabled")
        
        return self.saml_service.get_metadata()
    
    async def test_saml_configuration(self) -> Dict[str, Any]:
        """Test SAML configuration"""
        if not self.saml_service:
            return {
                "status": "disabled",
                "message": "SAML authentication is not enabled"
            }
        
        return await self.saml_service.test_configuration()