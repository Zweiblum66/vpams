"""
SAML authentication service for Single Sign-On

This module provides SAML 2.0 authentication integration for enterprise
identity providers like Okta, OneLogin, Azure AD, and others.
"""

import asyncio
import base64
import structlog
from datetime import datetime, timezone
from typing import Dict, Optional, Any, Tuple
from urllib.parse import urlparse

from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.settings import OneLogin_Saml2_Settings
from onelogin.saml2.utils import OneLogin_Saml2_Utils
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.config import settings
from core.exceptions import AuthenticationError, ValidationError
from db.models import User, Role

logger = structlog.get_logger(__name__)


class SAMLService:
    """Service for SAML authentication"""
    
    def __init__(self):
        self.settings = settings
        self._saml_settings = None
        self._initialize_saml_settings()
    
    def _initialize_saml_settings(self):
        """Initialize SAML settings from configuration"""
        if not self.settings.enable_saml:
            logger.info("SAML authentication is disabled")
            return
        
        try:
            # Build default attribute mapping if not provided
            attribute_mapping = self.settings.saml_attribute_mapping
            if not attribute_mapping:
                attribute_mapping = {
                    "email": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
                    "first_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
                    "last_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname",
                    "display_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
                    "groups": "http://schemas.microsoft.com/ws/2008/06/identity/claims/groups"
                }
            
            # Parse base URL from ACS URL
            parsed_url = urlparse(self.settings.saml_sp_acs_url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            self._saml_settings = {
                "strict": True,  # Enable strict mode for production
                "debug": self.settings.debug,
                
                # Service Provider (SP) Data
                "sp": {
                    "entityId": self.settings.saml_sp_entity_id,
                    "assertionConsumerService": {
                        "url": self.settings.saml_sp_acs_url,
                        "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                    },
                    "singleLogoutService": {
                        "url": self.settings.saml_sp_sls_url,
                        "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                    } if self.settings.saml_sp_sls_url else None,
                    "NameIDFormat": self.settings.saml_name_id_format,
                    "x509cert": self.settings.saml_sp_x509_cert,
                    "privateKey": self.settings.saml_sp_private_key,
                },
                
                # Identity Provider (IdP) Data
                "idp": {
                    "entityId": self.settings.saml_idp_entity_id,
                    "singleSignOnService": {
                        "url": self.settings.saml_idp_sso_url,
                        "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                    },
                    "singleLogoutService": {
                        "url": self.settings.saml_idp_sls_url,
                        "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                    } if self.settings.saml_idp_sls_url else None,
                    "x509cert": self.settings.saml_idp_x509_cert,
                },
                
                # Security settings
                "security": {
                    "nameIdEncrypted": False,
                    "authnRequestsSigned": self.settings.saml_authn_requests_signed,
                    "logoutRequestSigned": self.settings.saml_logout_requests_signed,
                    "logoutResponseSigned": self.settings.saml_logout_requests_signed,
                    "signMetadata": False,
                    "wantMessagesSigned": False,
                    "wantAssertionsSigned": self.settings.saml_want_assertions_signed,
                    "wantAssertionsEncrypted": self.settings.saml_want_assertions_encrypted,
                    "wantNameId": True,
                    "wantAttributeStatement": True,
                    "requestedAuthnContext": True,
                    "requestedAuthnContextComparison": "exact",
                    "signatureAlgorithm": self.settings.saml_signature_algorithm,
                    "digestAlgorithm": self.settings.saml_digest_algorithm,
                }
            }
            
            # Store attribute mapping
            self._attribute_mapping = attribute_mapping
            
            logger.info(
                "SAML settings initialized",
                sp_entity_id=self.settings.saml_sp_entity_id,
                idp_entity_id=self.settings.saml_idp_entity_id
            )
            
        except Exception as e:
            logger.error("Failed to initialize SAML settings", error=str(e))
            raise ValidationError(f"Invalid SAML configuration: {str(e)}")
    
    def _prepare_flask_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare request data in Flask format for python3-saml"""
        return {
            "https": request_data.get("https", "on"),
            "http_host": request_data.get("http_host", ""),
            "server_port": request_data.get("server_port", 443),
            "script_name": request_data.get("script_name", ""),
            "get_data": request_data.get("get_data", {}),
            "post_data": request_data.get("post_data", {})
        }
    
    def create_auth_request(self, request_data: Dict[str, Any], 
                          return_to: Optional[str] = None) -> str:
        """Create SAML authentication request"""
        if not self.settings.enable_saml:
            raise ValidationError("SAML authentication is disabled")
        
        try:
            # Prepare request
            req = self._prepare_flask_request(request_data)
            
            # Create OneLogin_Saml2_Auth instance
            auth = OneLogin_Saml2_Auth(req, self._saml_settings)
            
            # Generate authentication request URL
            sso_url = auth.login(return_to=return_to)
            
            logger.info(
                "Created SAML authentication request",
                return_to=return_to
            )
            
            return sso_url
            
        except Exception as e:
            logger.error("Failed to create SAML auth request", error=str(e))
            raise AuthenticationError(f"Failed to create SAML request: {str(e)}")
    
    async def process_auth_response(self, request_data: Dict[str, Any], 
                                  db: AsyncSession) -> Optional[User]:
        """Process SAML authentication response"""
        if not self.settings.enable_saml:
            raise ValidationError("SAML authentication is disabled")
        
        try:
            # Prepare request
            req = self._prepare_flask_request(request_data)
            
            # Create OneLogin_Saml2_Auth instance
            auth = OneLogin_Saml2_Auth(req, self._saml_settings)
            
            # Process response
            auth.process_response()
            
            # Check for errors
            errors = auth.get_errors()
            if errors:
                logger.error(
                    "SAML authentication failed",
                    errors=errors,
                    last_error_reason=auth.get_last_error_reason()
                )
                raise AuthenticationError(f"SAML authentication failed: {', '.join(errors)}")
            
            # Check if authenticated
            if not auth.is_authenticated():
                raise AuthenticationError("SAML authentication failed: User not authenticated")
            
            # Get user attributes
            attributes = auth.get_attributes()
            nameid = auth.get_nameid()
            nameid_format = auth.get_nameid_format()
            session_index = auth.get_session_index()
            
            logger.info(
                "SAML authentication successful",
                nameid=nameid,
                nameid_format=nameid_format,
                session_index=session_index
            )
            
            # Extract user information
            user_info = self._extract_user_info(nameid, attributes)
            
            # Get or create user
            user = await self.get_or_create_user(db, user_info)
            
            # Store SAML session info if needed
            if user and session_index:
                user.saml_session_index = session_index
                await db.commit()
            
            return user
            
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error("Failed to process SAML response", error=str(e))
            raise AuthenticationError(f"Failed to process SAML response: {str(e)}")
    
    def _extract_user_info(self, nameid: str, attributes: Dict[str, list]) -> Dict[str, Any]:
        """Extract user information from SAML attributes"""
        # Use attribute mapping to extract values
        user_info = {
            "nameid": nameid,
            "email": nameid,  # Default to nameid if email not in attributes
            "auth_provider": "saml"
        }
        
        # Map attributes based on configuration
        for local_attr, saml_attr in self._attribute_mapping.items():
            if saml_attr in attributes:
                values = attributes[saml_attr]
                if values:
                    # Take first value for most attributes
                    if local_attr == "groups":
                        user_info[local_attr] = values  # Keep as list
                    else:
                        user_info[local_attr] = values[0]
        
        # Ensure we have an email
        if not user_info.get("email"):
            if "@" in nameid:
                user_info["email"] = nameid
            else:
                raise ValidationError("No email address found in SAML response")
        
        # Set defaults for missing values
        user_info.setdefault("first_name", "")
        user_info.setdefault("last_name", "")
        user_info.setdefault("display_name", "")
        user_info.setdefault("groups", [])
        user_info.setdefault("is_active", True)
        user_info.setdefault("is_verified", True)  # Trust SAML IdP verification
        
        logger.debug(
            "Extracted user info from SAML",
            email=user_info.get("email"),
            has_groups=bool(user_info.get("groups"))
        )
        
        return user_info
    
    async def get_or_create_user(self, db: AsyncSession, user_info: Dict[str, Any]) -> User:
        """Get existing user or create new user from SAML information"""
        email = user_info.get("email")
        if not email:
            raise ValidationError("Email is required for SAML authentication")
        
        # Look for existing user by email
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            # Update existing user if auto-update is enabled
            if self.settings.saml_auto_update_user:
                await self._update_user_from_saml(db, existing_user, user_info)
            
            logger.info(
                "Found existing user for SAML authentication",
                user_id=existing_user.id,
                email=email
            )
            
            return existing_user
        
        else:
            # Create new user if auto-create is enabled
            if not self.settings.saml_auto_create_user:
                raise AuthenticationError("User not found and auto-creation is disabled")
            
            new_user = await self._create_user_from_saml(db, user_info)
            
            logger.info(
                "Created new user from SAML authentication",
                user_id=new_user.id,
                email=email
            )
            
            return new_user
    
    async def _create_user_from_saml(self, db: AsyncSession, user_info: Dict[str, Any]) -> User:
        """Create new user from SAML information"""
        # Get default role
        stmt = select(Role).where(Role.name == self.settings.saml_default_role)
        result = await db.execute(stmt)
        default_role = result.scalar_one_or_none()
        
        if not default_role:
            raise ValidationError(f"Default role '{self.settings.saml_default_role}' not found")
        
        # Determine role from groups if available
        groups = user_info.get("groups", [])
        role = self._determine_user_role(groups) if groups else self.settings.saml_default_role
        
        # Get the determined role
        stmt = select(Role).where(Role.name == role)
        result = await db.execute(stmt)
        user_role = result.scalar_one_or_none() or default_role
        
        # Create user
        new_user = User(
            email=user_info["email"],
            first_name=user_info.get("first_name", ""),
            last_name=user_info.get("last_name", ""),
            display_name=user_info.get("display_name", ""),
            is_active=user_info.get("is_active", True),
            is_verified=user_info.get("is_verified", True),
            auth_provider="saml",
            password_hash=None,  # SAML users don't have passwords
            role_id=user_role.id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        db.add(new_user)
        await db.flush()  # Get the user ID
        await db.commit()
        
        return new_user
    
    async def _update_user_from_saml(self, db: AsyncSession, user: User, user_info: Dict[str, Any]):
        """Update existing user with SAML information"""
        # Update user fields that may have changed
        user.first_name = user_info.get("first_name", user.first_name)
        user.last_name = user_info.get("last_name", user.last_name)
        user.display_name = user_info.get("display_name", user.display_name)
        user.updated_at = datetime.now(timezone.utc)
        
        # Update role based on groups if available
        groups = user_info.get("groups", [])
        if groups:
            role_name = self._determine_user_role(groups)
            stmt = select(Role).where(Role.name == role_name)
            result = await db.execute(stmt)
            new_role = result.scalar_one_or_none()
            
            if new_role and new_role.id != user.role_id:
                user.role_id = new_role.id
                logger.info(
                    "Updated user role from SAML groups",
                    user_id=user.id,
                    new_role=role_name
                )
        
        # Update auth provider if it was local before
        if user.auth_provider == "local":
            user.auth_provider = "saml"
            user.password_hash = None  # Remove password for SAML users
        
        await db.commit()
    
    def _determine_user_role(self, groups: list) -> str:
        """Determine user role based on SAML groups"""
        # This is a simple implementation - customize based on your IdP groups
        # Priority: admin > editor > viewer > user
        
        group_names = [g.lower() for g in groups]
        
        # Check for admin groups
        admin_keywords = ["admin", "administrator", "superuser"]
        if any(keyword in group for group in group_names for keyword in admin_keywords):
            return "admin"
        
        # Check for editor groups
        editor_keywords = ["editor", "contributor", "writer"]
        if any(keyword in group for group in group_names for keyword in editor_keywords):
            return "editor"
        
        # Check for viewer groups
        viewer_keywords = ["viewer", "reader", "readonly"]
        if any(keyword in group for group in group_names for keyword in viewer_keywords):
            return "viewer"
        
        # Default to user role
        return self.settings.saml_default_role
    
    def create_logout_request(self, request_data: Dict[str, Any], 
                            name_id: str, session_index: Optional[str] = None) -> str:
        """Create SAML logout request"""
        if not self.settings.enable_saml:
            raise ValidationError("SAML authentication is disabled")
        
        try:
            # Prepare request
            req = self._prepare_flask_request(request_data)
            
            # Create OneLogin_Saml2_Auth instance
            auth = OneLogin_Saml2_Auth(req, self._saml_settings)
            
            # Generate logout request URL
            slo_url = auth.logout(
                name_id=name_id,
                session_index=session_index
            )
            
            logger.info(
                "Created SAML logout request",
                name_id=name_id,
                session_index=session_index
            )
            
            return slo_url
            
        except Exception as e:
            logger.error("Failed to create SAML logout request", error=str(e))
            raise AuthenticationError(f"Failed to create SAML logout request: {str(e)}")
    
    async def process_logout_response(self, request_data: Dict[str, Any]) -> bool:
        """Process SAML logout response"""
        if not self.settings.enable_saml:
            raise ValidationError("SAML authentication is disabled")
        
        try:
            # Prepare request
            req = self._prepare_flask_request(request_data)
            
            # Create OneLogin_Saml2_Auth instance
            auth = OneLogin_Saml2_Auth(req, self._saml_settings)
            
            # Process SLO response
            url = auth.process_slo(keep_local_session=False)
            
            # Check for errors
            errors = auth.get_errors()
            if errors:
                logger.error(
                    "SAML logout failed",
                    errors=errors,
                    last_error_reason=auth.get_last_error_reason()
                )
                return False
            
            logger.info("SAML logout successful")
            return True
            
        except Exception as e:
            logger.error("Failed to process SAML logout response", error=str(e))
            return False
    
    def get_metadata(self) -> str:
        """Generate SAML SP metadata"""
        if not self.settings.enable_saml:
            raise ValidationError("SAML authentication is disabled")
        
        try:
            saml_settings = OneLogin_Saml2_Settings(
                self._saml_settings,
                custom_base_path=None,
                sp_validation_only=True
            )
            
            metadata = saml_settings.get_sp_metadata()
            errors = saml_settings.validate_metadata(metadata)
            
            if errors:
                raise ValidationError(f"Invalid metadata: {', '.join(errors)}")
            
            return metadata
            
        except Exception as e:
            logger.error("Failed to generate SAML metadata", error=str(e))
            raise ValidationError(f"Failed to generate metadata: {str(e)}")
    
    async def test_configuration(self) -> Dict[str, Any]:
        """Test SAML configuration"""
        if not self.settings.enable_saml:
            return {
                "status": "disabled",
                "message": "SAML authentication is disabled"
            }
        
        try:
            # Validate settings
            saml_settings = OneLogin_Saml2_Settings(
                self._saml_settings,
                custom_base_path=None,
                sp_validation_only=True
            )
            
            errors = saml_settings.check_settings()
            
            if errors:
                return {
                    "status": "error",
                    "message": "Invalid SAML configuration",
                    "errors": errors
                }
            
            # Generate and validate metadata
            metadata = self.get_metadata()
            
            return {
                "status": "success",
                "message": "SAML configuration is valid",
                "sp_entity_id": self.settings.saml_sp_entity_id,
                "idp_entity_id": self.settings.saml_idp_entity_id,
                "has_metadata": bool(metadata)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Configuration test failed: {str(e)}"
            }