"""
OAuth2 authentication API routes

This module provides REST API endpoints for OAuth2 authentication with
Google and Microsoft providers.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List

from db.base import get_db
from services.auth_service import AuthService
from core.exceptions import ValidationError, AuthenticationError
from core.security import get_current_admin_user
from db.models import User

logger = structlog.get_logger(__name__)

oauth2_router = APIRouter(prefix="/oauth2", tags=["OAuth2 Authentication"])


@oauth2_router.get("/providers", response_model=Dict[str, List[str]])
async def get_oauth2_providers():
    """Get list of available OAuth2 providers"""
    try:
        auth_service = AuthService()
        providers = auth_service.get_oauth2_providers()
        
        return {
            "success": True,
            "data": {
                "providers": providers
            }
        }
        
    except Exception as e:
        logger.error("Failed to get OAuth2 providers", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get OAuth2 providers"
        )


@oauth2_router.get("/auth/{provider}")
async def initiate_oauth2_auth(provider: str):
    """Initiate OAuth2 authentication with specified provider"""
    try:
        auth_service = AuthService()
        auth_data = auth_service.generate_oauth2_auth_url(provider)
        
        logger.info(
            "Generated OAuth2 authorization URL",
            provider=provider,
            state=auth_data["state"]
        )
        
        return {
            "success": True,
            "data": auth_data
        }
        
    except ValidationError as e:
        logger.warning(
            "OAuth2 validation error",
            provider=provider,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ValueError as e:
        logger.warning(
            "OAuth2 not enabled",
            provider=provider,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to initiate OAuth2 authentication",
            provider=provider,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate OAuth2 authentication"
        )


@oauth2_router.get("/callback/{provider}")
async def oauth2_callback(
    provider: str,
    code: str = Query(..., description="Authorization code"),
    state: str = Query(..., description="State parameter"),
    error: str = Query(None, description="Error from provider"),
    error_description: str = Query(None, description="Error description"),
    db: AsyncSession = Depends(get_db)
):
    """Handle OAuth2 callback from provider"""
    try:
        # Check for errors from provider
        if error:
            logger.warning(
                "OAuth2 provider returned error",
                provider=provider,
                error=error,
                description=error_description
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"OAuth2 error: {error_description or error}"
            )
        
        auth_service = AuthService()
        
        # Authenticate user with authorization code
        user = await auth_service.authenticate_oauth2_user(db, provider, code, state)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="OAuth2 authentication failed"
            )
        
        # Create user session
        session_data = await auth_service.create_user_session(db, user)
        
        logger.info(
            "OAuth2 authentication successful",
            provider=provider,
            user_id=user.id,
            email=user.email
        )
        
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
        logger.error(
            "OAuth2 authentication error",
            provider=provider,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(
            "OAuth2 validation error",
            provider=provider,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "OAuth2 callback failed",
            provider=provider,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth2 authentication failed"
        )


@oauth2_router.get("/config/{provider}")
async def get_oauth2_config(
    provider: str,
    current_user: User = Depends(get_current_admin_user)
):
    """Get OAuth2 provider configuration (admin only)"""
    try:
        auth_service = AuthService()
        config = await auth_service.get_oauth2_provider_info(provider)
        
        # Remove sensitive information
        safe_config = {
            "name": config.get("name"),
            "client_id": config.get("client_id"),
            "redirect_uri": config.get("redirect_uri"),
            "scopes": config.get("scopes"),
            "authorization_endpoint": config.get("authorization_endpoint"),
            "userinfo_endpoint": config.get("userinfo_endpoint")
        }
        
        return {
            "success": True,
            "data": safe_config
        }
        
    except ValidationError as e:
        logger.warning(
            "OAuth2 config validation error",
            provider=provider,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ValueError as e:
        logger.warning(
            "OAuth2 not enabled",
            provider=provider,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to get OAuth2 config",
            provider=provider,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get OAuth2 configuration"
        )


@oauth2_router.get("/test/{provider}")
async def test_oauth2_provider(
    provider: str,
    current_user: User = Depends(get_current_admin_user)
):
    """Test OAuth2 provider configuration (admin only)"""
    try:
        auth_service = AuthService()
        test_result = await auth_service.test_oauth2_provider(provider)
        
        return {
            "success": True,
            "data": test_result
        }
        
    except Exception as e:
        logger.error(
            "Failed to test OAuth2 provider",
            provider=provider,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test OAuth2 provider"
        )


# Frontend-friendly redirect endpoints for OAuth2 flows
@oauth2_router.get("/login/{provider}")
async def oauth2_login_redirect(provider: str):
    """Redirect to OAuth2 provider for authentication (frontend-friendly)"""
    try:
        auth_service = AuthService()
        auth_data = auth_service.generate_oauth2_auth_url(provider)
        
        # Store state in session/cache if needed
        # For now, return the URL for the frontend to handle
        return RedirectResponse(
            url=auth_data["authorization_url"],
            status_code=status.HTTP_302_FOUND
        )
        
    except ValidationError as e:
        logger.warning(
            "OAuth2 validation error during redirect",
            provider=provider,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ValueError as e:
        logger.warning(
            "OAuth2 not enabled during redirect",
            provider=provider,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed OAuth2 login redirect",
            provider=provider,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate OAuth2 authentication"
        )