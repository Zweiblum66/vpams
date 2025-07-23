"""
OAuth2 authentication service for Google and Microsoft providers

This module provides OAuth2 authentication integration with popular identity providers
including Google and Microsoft Azure AD/Office 365.
"""

import asyncio
import json
import secrets
import structlog
from datetime import datetime, timezone
from typing import Dict, Optional, Any, List
from urllib.parse import urlencode

import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.oauth2.rfc6749.errors import OAuth2Error
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.config import settings
from core.exceptions import AuthenticationError, ValidationError
from db.models import User, Role
from .auth_service import AuthService

logger = structlog.get_logger(__name__)


class OAuth2Provider:
    """Base OAuth2 provider class"""
    
    def __init__(self, name: str, client_id: str, client_secret: str, 
                 redirect_uri: str, scopes: List[str]):
        self.name = name
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scopes = scopes
        self.client = None
    
    def get_authorization_url(self, state: str) -> str:
        """Get OAuth2 authorization URL"""
        raise NotImplementedError
    
    async def exchange_code_for_token(self, code: str, state: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        raise NotImplementedError
    
    async def get_user_info(self, token: Dict[str, Any]) -> Dict[str, Any]:
        """Get user information using access token"""
        raise NotImplementedError


class GoogleOAuth2Provider(OAuth2Provider):
    """Google OAuth2 provider implementation"""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str, scopes: List[str]):
        super().__init__("google", client_id, client_secret, redirect_uri, scopes)
        self.authorization_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_endpoint = "https://oauth2.googleapis.com/token"
        self.userinfo_endpoint = "https://www.googleapis.com/oauth2/v2/userinfo"
        
        self.client = AsyncOAuth2Client(
            client_id=client_id,
            client_secret=client_secret,
            scope=" ".join(scopes)
        )
    
    def get_authorization_url(self, state: str) -> str:
        """Get Google OAuth2 authorization URL"""
        try:
            authorization_url, _ = self.client.create_authorization_url(
                self.authorization_endpoint,
                redirect_uri=self.redirect_uri,
                state=state,
                access_type="offline",  # Request refresh token
                prompt="consent"  # Force consent screen to get refresh token
            )
            
            logger.info(
                "Generated Google OAuth2 authorization URL",
                provider="google",
                state=state,
                scopes=self.scopes
            )
            
            return authorization_url
            
        except Exception as e:
            logger.error(
                "Failed to generate Google authorization URL",
                provider="google",
                error=str(e)
            )
            raise AuthenticationError("Failed to generate authorization URL")
    
    async def exchange_code_for_token(self, code: str, state: str) -> Dict[str, Any]:
        """Exchange Google authorization code for access token"""
        try:
            token = await self.client.fetch_token(
                self.token_endpoint,
                authorization_response=None,
                code=code,
                redirect_uri=self.redirect_uri
            )
            
            logger.info(
                "Successfully exchanged code for token",
                provider="google",
                state=state,
                token_type=token.get("token_type"),
                expires_in=token.get("expires_in")
            )
            
            return token
            
        except OAuth2Error as e:
            logger.error(
                "OAuth2 error during token exchange",
                provider="google",
                error=e.error,
                description=e.description
            )
            raise AuthenticationError(f"OAuth2 error: {e.description}")
        except Exception as e:
            logger.error(
                "Failed to exchange code for token",
                provider="google",
                error=str(e)
            )
            raise AuthenticationError("Failed to exchange authorization code")
    
    async def get_user_info(self, token: Dict[str, Any]) -> Dict[str, Any]:
        """Get user information from Google using access token"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.userinfo_endpoint,
                    headers={"Authorization": f"Bearer {token['access_token']}"}
                )
                response.raise_for_status()
                user_data = response.json()
            
            # Map Google user data to our user model
            user_info = {
                "provider_id": user_data.get("id"),
                "email": user_data.get("email"),
                "first_name": user_data.get("given_name", ""),
                "last_name": user_data.get("family_name", ""),
                "display_name": user_data.get("name", ""),
                "picture": user_data.get("picture"),
                "email_verified": user_data.get("verified_email", False),
                "locale": user_data.get("locale"),
                "provider": "google",
                "auth_provider": "oauth2"
            }
            
            logger.info(
                "Retrieved user info from Google",
                provider="google",
                user_id=user_info["provider_id"],
                email=user_info["email"],
                verified=user_info["email_verified"]
            )
            
            return user_info
            
        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP error while fetching user info",
                provider="google",
                status_code=e.response.status_code,
                error=str(e)
            )
            raise AuthenticationError("Failed to fetch user information")
        except Exception as e:
            logger.error(
                "Failed to get user info from Google",
                provider="google",
                error=str(e)
            )
            raise AuthenticationError("Failed to retrieve user information")


class MicrosoftOAuth2Provider(OAuth2Provider):
    """Microsoft OAuth2 provider implementation"""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str, 
                 scopes: List[str], tenant_id: str = "common"):
        super().__init__("microsoft", client_id, client_secret, redirect_uri, scopes)
        self.tenant_id = tenant_id
        self.authorization_endpoint = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"
        self.token_endpoint = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        self.userinfo_endpoint = "https://graph.microsoft.com/v1.0/me"
        
        self.client = AsyncOAuth2Client(
            client_id=client_id,
            client_secret=client_secret,
            scope=" ".join(scopes)
        )
    
    def get_authorization_url(self, state: str) -> str:
        """Get Microsoft OAuth2 authorization URL"""
        try:
            authorization_url, _ = self.client.create_authorization_url(
                self.authorization_endpoint,
                redirect_uri=self.redirect_uri,
                state=state,
                response_mode="query"
            )
            
            logger.info(
                "Generated Microsoft OAuth2 authorization URL",
                provider="microsoft",
                tenant_id=self.tenant_id,
                state=state,
                scopes=self.scopes
            )
            
            return authorization_url
            
        except Exception as e:
            logger.error(
                "Failed to generate Microsoft authorization URL",
                provider="microsoft",
                error=str(e)
            )
            raise AuthenticationError("Failed to generate authorization URL")
    
    async def exchange_code_for_token(self, code: str, state: str) -> Dict[str, Any]:
        """Exchange Microsoft authorization code for access token"""
        try:
            token = await self.client.fetch_token(
                self.token_endpoint,
                authorization_response=None,
                code=code,
                redirect_uri=self.redirect_uri
            )
            
            logger.info(
                "Successfully exchanged code for token",
                provider="microsoft",
                tenant_id=self.tenant_id,
                state=state,
                token_type=token.get("token_type"),
                expires_in=token.get("expires_in")
            )
            
            return token
            
        except OAuth2Error as e:
            logger.error(
                "OAuth2 error during token exchange",
                provider="microsoft",
                error=e.error,
                description=e.description
            )
            raise AuthenticationError(f"OAuth2 error: {e.description}")
        except Exception as e:
            logger.error(
                "Failed to exchange code for token",
                provider="microsoft",
                error=str(e)
            )
            raise AuthenticationError("Failed to exchange authorization code")
    
    async def get_user_info(self, token: Dict[str, Any]) -> Dict[str, Any]:
        """Get user information from Microsoft Graph using access token"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.userinfo_endpoint,
                    headers={"Authorization": f"Bearer {token['access_token']}"}
                )
                response.raise_for_status()
                user_data = response.json()
            
            # Map Microsoft user data to our user model
            user_info = {
                "provider_id": user_data.get("id"),
                "email": user_data.get("mail") or user_data.get("userPrincipalName"),
                "first_name": user_data.get("givenName", ""),
                "last_name": user_data.get("surname", ""),
                "display_name": user_data.get("displayName", ""),
                "phone": user_data.get("businessPhones", [None])[0],
                "job_title": user_data.get("jobTitle"),
                "department": user_data.get("department"),
                "office_location": user_data.get("officeLocation"),
                "preferred_language": user_data.get("preferredLanguage"),
                "provider": "microsoft",
                "auth_provider": "oauth2"
            }
            
            logger.info(
                "Retrieved user info from Microsoft",
                provider="microsoft",
                user_id=user_info["provider_id"],
                email=user_info["email"],
                tenant_id=self.tenant_id
            )
            
            return user_info
            
        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP error while fetching user info",
                provider="microsoft",
                status_code=e.response.status_code,
                error=str(e)
            )
            raise AuthenticationError("Failed to fetch user information")
        except Exception as e:
            logger.error(
                "Failed to get user info from Microsoft",
                provider="microsoft",
                error=str(e)
            )
            raise AuthenticationError("Failed to retrieve user information")


class OAuth2Service:
    """OAuth2 authentication service"""
    
    def __init__(self):
        self.providers: Dict[str, OAuth2Provider] = {}
        self.auth_service = AuthService()
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize OAuth2 providers based on configuration"""
        if not settings.enable_oauth2:
            logger.info("OAuth2 authentication is disabled")
            return
        
        # Initialize Google provider
        if settings.google_oauth2_enabled:
            try:
                google_provider = GoogleOAuth2Provider(
                    client_id=settings.google_client_id,
                    client_secret=settings.google_client_secret,
                    redirect_uri=settings.google_redirect_uri,
                    scopes=settings.google_scopes
                )
                self.providers["google"] = google_provider
                logger.info("Initialized Google OAuth2 provider")
            except Exception as e:
                logger.error("Failed to initialize Google OAuth2 provider", error=str(e))
        
        # Initialize Microsoft provider
        if settings.microsoft_oauth2_enabled:
            try:
                microsoft_provider = MicrosoftOAuth2Provider(
                    client_id=settings.microsoft_client_id,
                    client_secret=settings.microsoft_client_secret,
                    redirect_uri=settings.microsoft_redirect_uri,
                    scopes=settings.microsoft_scopes,
                    tenant_id=settings.microsoft_tenant_id
                )
                self.providers["microsoft"] = microsoft_provider
                logger.info("Initialized Microsoft OAuth2 provider")
            except Exception as e:
                logger.error("Failed to initialize Microsoft OAuth2 provider", error=str(e))
        
        logger.info(
            "OAuth2 service initialized",
            enabled_providers=list(self.providers.keys()),
            total_providers=len(self.providers)
        )
    
    def get_available_providers(self) -> List[str]:
        """Get list of available OAuth2 providers"""
        return list(self.providers.keys())
    
    def generate_auth_url(self, provider_name: str) -> Dict[str, str]:
        """Generate OAuth2 authorization URL for specified provider"""
        if not settings.enable_oauth2:
            raise ValidationError("OAuth2 authentication is disabled")
        
        if provider_name not in self.providers:
            raise ValidationError(f"Provider '{provider_name}' is not available")
        
        provider = self.providers[provider_name]
        state = secrets.token_urlsafe(32)  # Generate secure random state
        
        try:
            auth_url = provider.get_authorization_url(state)
            
            logger.info(
                "Generated OAuth2 authorization URL",
                provider=provider_name,
                state=state
            )
            
            return {
                "authorization_url": auth_url,
                "state": state,
                "provider": provider_name
            }
            
        except Exception as e:
            logger.error(
                "Failed to generate authorization URL",
                provider=provider_name,
                error=str(e)
            )
            raise AuthenticationError(f"Failed to generate authorization URL for {provider_name}")
    
    async def authenticate_with_code(self, provider_name: str, code: str, 
                                   state: str, db: AsyncSession) -> Optional[User]:
        """Authenticate user using OAuth2 authorization code"""
        if not settings.enable_oauth2:
            raise ValidationError("OAuth2 authentication is disabled")
        
        if provider_name not in self.providers:
            raise ValidationError(f"Provider '{provider_name}' is not available")
        
        provider = self.providers[provider_name]
        
        try:
            # Exchange code for token
            token = await provider.exchange_code_for_token(code, state)
            
            # Get user information
            user_info = await provider.get_user_info(token)
            
            # Get or create user
            user = await self.get_or_create_user(db, user_info)
            
            logger.info(
                "OAuth2 authentication successful",
                provider=provider_name,
                user_id=user.id,
                email=user.email
            )
            
            return user
            
        except Exception as e:
            logger.error(
                "OAuth2 authentication failed",
                provider=provider_name,
                error=str(e)
            )
            raise AuthenticationError(f"OAuth2 authentication failed: {str(e)}")
    
    async def get_or_create_user(self, db: AsyncSession, user_info: Dict[str, Any]) -> User:
        """Get existing user or create new user from OAuth2 information"""
        email = user_info.get("email")
        if not email:
            raise ValidationError("Email is required for OAuth2 authentication")
        
        # Look for existing user by email
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            # Update existing user if auto-update is enabled
            if settings.oauth2_auto_update_user:
                await self._update_user_from_oauth2(db, existing_user, user_info)
            
            logger.info(
                "Found existing user for OAuth2 authentication",
                user_id=existing_user.id,
                email=email,
                provider=user_info.get("provider")
            )
            
            return existing_user
        
        else:
            # Create new user if auto-create is enabled
            if not settings.oauth2_auto_create_user:
                raise AuthenticationError("User not found and auto-creation is disabled")
            
            new_user = await self._create_user_from_oauth2(db, user_info)
            
            logger.info(
                "Created new user from OAuth2 authentication",
                user_id=new_user.id,
                email=email,
                provider=user_info.get("provider")
            )
            
            return new_user
    
    async def _create_user_from_oauth2(self, db: AsyncSession, user_info: Dict[str, Any]) -> User:
        """Create new user from OAuth2 information"""
        # Get default role
        stmt = select(Role).where(Role.name == settings.oauth2_default_role)
        result = await db.execute(stmt)
        default_role = result.scalar_one_or_none()
        
        if not default_role:
            raise ValidationError(f"Default role '{settings.oauth2_default_role}' not found")
        
        # Create user
        new_user = User(
            email=user_info["email"],
            first_name=user_info.get("first_name", ""),
            last_name=user_info.get("last_name", ""),
            display_name=user_info.get("display_name", ""),
            phone=user_info.get("phone", ""),
            department=user_info.get("department", ""),
            organization=user_info.get("organization", ""),
            is_active=True,
            is_verified=user_info.get("email_verified", True),  # Trust OAuth2 providers
            auth_provider="oauth2",
            password_hash=None,  # OAuth2 users don't have passwords
            role_id=default_role.id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        db.add(new_user)
        await db.flush()  # Get the user ID
        await db.commit()
        
        return new_user
    
    async def _update_user_from_oauth2(self, db: AsyncSession, user: User, user_info: Dict[str, Any]):
        """Update existing user with OAuth2 information"""
        # Update user fields that may have changed
        user.first_name = user_info.get("first_name", user.first_name)
        user.last_name = user_info.get("last_name", user.last_name)
        user.display_name = user_info.get("display_name", user.display_name)
        user.phone = user_info.get("phone", user.phone)
        user.department = user_info.get("department", user.department)
        user.organization = user_info.get("organization", user.organization)
        user.updated_at = datetime.now(timezone.utc)
        
        # Update auth provider if it was local before
        if user.auth_provider == "local":
            user.auth_provider = "oauth2"
            user.password_hash = None  # Remove password for OAuth2 users
        
        await db.commit()
    
    async def get_provider_info(self, provider_name: str) -> Dict[str, Any]:
        """Get information about an OAuth2 provider"""
        if not settings.enable_oauth2:
            raise ValidationError("OAuth2 authentication is disabled")
        
        if provider_name not in self.providers:
            raise ValidationError(f"Provider '{provider_name}' is not available")
        
        provider = self.providers[provider_name]
        
        return {
            "name": provider.name,
            "client_id": provider.client_id,
            "redirect_uri": provider.redirect_uri,
            "scopes": provider.scopes,
            "authorization_endpoint": getattr(provider, "authorization_endpoint", ""),
            "token_endpoint": getattr(provider, "token_endpoint", ""),
            "userinfo_endpoint": getattr(provider, "userinfo_endpoint", "")
        }
    
    async def test_provider_connection(self, provider_name: str) -> Dict[str, Any]:
        """Test OAuth2 provider configuration"""
        if not settings.enable_oauth2:
            return {
                "status": "disabled",
                "message": "OAuth2 authentication is disabled",
                "provider": provider_name
            }
        
        if provider_name not in self.providers:
            return {
                "status": "error",
                "message": f"Provider '{provider_name}' is not configured",
                "provider": provider_name
            }
        
        try:
            provider = self.providers[provider_name]
            
            # Test generating authorization URL
            state = "test_state"
            auth_url = provider.get_authorization_url(state)
            
            return {
                "status": "success",
                "message": f"Provider '{provider_name}' is configured correctly",
                "provider": provider_name,
                "client_id": provider.client_id,
                "redirect_uri": provider.redirect_uri,
                "scopes": provider.scopes,
                "test_auth_url": auth_url
            }
            
        except Exception as e:
            logger.error(
                "Failed to test OAuth2 provider",
                provider=provider_name,
                error=str(e)
            )
            return {
                "status": "error",
                "message": f"Provider test failed: {str(e)}",
                "provider": provider_name
            }