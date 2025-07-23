"""
SAML authentication API routes

This module provides REST API endpoints for SAML authentication with
enterprise identity providers.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import RedirectResponse, PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional

from db.base import get_db
from services.auth_service import AuthService
from core.exceptions import ValidationError, AuthenticationError
from core.security import get_current_admin_user
from db.models import User

logger = structlog.get_logger(__name__)

saml_router = APIRouter(prefix="/saml", tags=["SAML Authentication"])


def _prepare_saml_request_data(request: Request) -> Dict[str, Any]:
    """Prepare request data for python3-saml from FastAPI request"""
    # Determine if HTTPS
    https = request.url.scheme == "https"
    
    # Extract host and port
    host_header = request.headers.get("host", "")
    if ":" in host_header:
        http_host, server_port = host_header.split(":", 1)
        server_port = int(server_port)
    else:
        http_host = host_header
        server_port = 443 if https else 80
    
    return {
        "https": "on" if https else "off",
        "http_host": http_host,
        "server_port": server_port,
        "script_name": str(request.url.path),
        "get_data": dict(request.query_params),
        "post_data": {}  # Will be populated for POST requests
    }


@saml_router.get("/metadata", response_class=PlainTextResponse)
async def get_saml_metadata():
    """Get SAML Service Provider metadata"""
    try:
        auth_service = AuthService()
        metadata = auth_service.get_saml_metadata()
        
        return Response(
            content=metadata,
            media_type="application/xml",
            headers={"Content-Disposition": "inline; filename=sp-metadata.xml"}
        )
        
    except ValueError as e:
        logger.warning("SAML not enabled", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except ValidationError as e:
        logger.error("Failed to generate SAML metadata", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate SAML metadata"
        )


@saml_router.get("/login")
async def initiate_saml_login(
    request: Request,
    return_to: Optional[str] = None
):
    """Initiate SAML authentication flow"""
    try:
        auth_service = AuthService()
        request_data = _prepare_saml_request_data(request)
        
        # Generate SAML authentication request
        sso_url = auth_service.create_saml_auth_request(request_data, return_to)
        
        logger.info(
            "Initiated SAML login",
            return_to=return_to
        )
        
        # Redirect to IdP
        return RedirectResponse(url=sso_url, status_code=status.HTTP_302_FOUND)
        
    except ValueError as e:
        logger.warning("SAML not enabled", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except AuthenticationError as e:
        logger.error("Failed to initiate SAML login", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate SAML login"
        )


@saml_router.post("/acs")
async def saml_assertion_consumer_service(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """SAML Assertion Consumer Service (ACS) endpoint"""
    try:
        auth_service = AuthService()
        
        # Get form data
        form_data = await request.form()
        
        # Prepare request data
        request_data = _prepare_saml_request_data(request)
        request_data["post_data"] = dict(form_data)
        
        # Process SAML response
        user = await auth_service.process_saml_response(db, request_data)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="SAML authentication failed"
            )
        
        # Create user session
        session_data = await auth_service.create_user_session(db, user)
        
        logger.info(
            "SAML authentication successful",
            user_id=user.id,
            email=user.email
        )
        
        # Return tokens in response
        # In production, you might want to redirect to a frontend URL with tokens
        return {
            "success": True,
            "data": {
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "display_name": user.display_name,
                    "is_active": user.is_active,
                    "is_verified": user.is_verified,
                    "auth_provider": user.auth_provider,
                    "role": user.role.name if user.role else None
                },
                "tokens": {
                    "access_token": session_data["access_token"],
                    "refresh_token": session_data["refresh_token"],
                    "token_type": "bearer",
                    "expires_in": session_data["expires_in"]
                }
            }
        }
        
    except AuthenticationError as e:
        logger.error("SAML authentication error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning("SAML validation error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("SAML ACS failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SAML authentication failed"
        )


@saml_router.get("/logout")
async def initiate_saml_logout(
    request: Request,
    name_id: str,
    session_index: Optional[str] = None
):
    """Initiate SAML logout flow"""
    try:
        auth_service = AuthService()
        request_data = _prepare_saml_request_data(request)
        
        # Generate SAML logout request
        slo_url = auth_service.create_saml_logout_request(
            request_data, name_id, session_index
        )
        
        logger.info(
            "Initiated SAML logout",
            name_id=name_id,
            session_index=session_index
        )
        
        # Redirect to IdP for logout
        return RedirectResponse(url=slo_url, status_code=status.HTTP_302_FOUND)
        
    except ValueError as e:
        logger.warning("SAML not enabled", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except AuthenticationError as e:
        logger.error("Failed to initiate SAML logout", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate SAML logout"
        )


@saml_router.get("/sls")
@saml_router.post("/sls")
async def saml_single_logout_service(
    request: Request
):
    """SAML Single Logout Service (SLS) endpoint"""
    try:
        auth_service = AuthService()
        
        # Prepare request data
        request_data = _prepare_saml_request_data(request)
        
        # Handle POST request
        if request.method == "POST":
            form_data = await request.form()
            request_data["post_data"] = dict(form_data)
        
        # Process logout response
        success = await auth_service.process_saml_logout_response(request_data)
        
        if success:
            logger.info("SAML logout completed successfully")
            return {
                "success": True,
                "message": "Logout successful"
            }
        else:
            logger.warning("SAML logout failed")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Logout failed"
            )
            
    except ValueError as e:
        logger.warning("SAML not enabled", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        logger.error("SAML SLS failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout processing failed"
        )


@saml_router.get("/test")
async def test_saml_configuration(
    current_user: User = Depends(get_current_admin_user)
):
    """Test SAML configuration (admin only)"""
    try:
        auth_service = AuthService()
        test_result = await auth_service.test_saml_configuration()
        
        return {
            "success": True,
            "data": test_result
        }
        
    except Exception as e:
        logger.error("Failed to test SAML configuration", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test SAML configuration"
        )


@saml_router.get("/config")
async def get_saml_configuration(
    current_user: User = Depends(get_current_admin_user)
):
    """Get SAML configuration details (admin only)"""
    try:
        from core.config import settings
        
        if not settings.enable_saml:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="SAML authentication is not enabled"
            )
        
        # Return safe configuration details
        return {
            "success": True,
            "data": {
                "enabled": settings.enable_saml,
                "sp_entity_id": settings.saml_sp_entity_id,
                "sp_acs_url": settings.saml_sp_acs_url,
                "sp_sls_url": settings.saml_sp_sls_url,
                "idp_entity_id": settings.saml_idp_entity_id,
                "idp_sso_url": settings.saml_idp_sso_url,
                "idp_sls_url": settings.saml_idp_sls_url,
                "name_id_format": settings.saml_name_id_format,
                "authn_requests_signed": settings.saml_authn_requests_signed,
                "logout_requests_signed": settings.saml_logout_requests_signed,
                "want_assertions_signed": settings.saml_want_assertions_signed,
                "want_assertions_encrypted": settings.saml_want_assertions_encrypted,
                "auto_create_user": settings.saml_auto_create_user,
                "auto_update_user": settings.saml_auto_update_user,
                "default_role": settings.saml_default_role,
                "has_sp_cert": bool(settings.saml_sp_x509_cert),
                "has_sp_key": bool(settings.saml_sp_private_key),
                "has_idp_cert": bool(settings.saml_idp_x509_cert),
                "metadata_url": f"{settings.api_gateway_url}/api/v1/saml/metadata"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get SAML configuration", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get SAML configuration"
        )