"""
CORS Management API

Provides endpoints for viewing and managing CORS configuration.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, validator
import re

from core.config import get_settings
from core.cors import get_cors_config, validate_origin
from api.dependencies import require_permissions

settings = get_settings()
router = APIRouter(prefix="/api/v1/cors", tags=["cors-management"])


class CORSOriginRequest(BaseModel):
    """Request model for adding/removing CORS origins"""
    origin: str = Field(..., description="Origin URL to add/remove")
    
    @validator("origin")
    def validate_origin_format(cls, v):
        """Validate origin URL format"""
        if not validate_origin(v):
            raise ValueError("Invalid origin URL format")
        return v


class CORSPatternRequest(BaseModel):
    """Request model for adding/removing CORS patterns"""
    pattern: str = Field(..., description="Regex pattern for origins")
    
    @validator("pattern")
    def validate_pattern(cls, v):
        """Validate regex pattern"""
        try:
            re.compile(v)
        except re.error:
            raise ValueError("Invalid regular expression pattern")
        return v


class CORSConfigResponse(BaseModel):
    """CORS configuration response model"""
    allowed_origins: List[str]
    allowed_origin_patterns: List[str]
    allowed_methods: List[str]
    allowed_headers: List[str]
    exposed_headers: List[str]
    allow_credentials: bool
    max_age: int
    environment: str
    is_permissive: bool


@router.get("/config", response_model=CORSConfigResponse)
async def get_cors_configuration(
    current_user: Dict = Depends(require_permissions("admin", "cors.read"))
):
    """
    Get current CORS configuration
    
    Returns the active CORS configuration including all allowed origins,
    patterns, methods, and headers.
    """
    config = get_cors_config()
    
    return CORSConfigResponse(
        allowed_origins=config.allowed_origins,
        allowed_origin_patterns=config.allowed_origin_patterns,
        allowed_methods=config.allowed_methods,
        allowed_headers=config.allowed_headers,
        exposed_headers=config.exposed_headers,
        allow_credentials=config.allow_credentials,
        max_age=config.max_age,
        environment=settings.environment,
        is_permissive=config.allow_all_origins or "*" in config.allowed_origins
    )


@router.post("/validate-origin")
async def validate_cors_origin(
    origin: str,
    current_user: Dict = Depends(require_permissions("admin", "cors.read"))
):
    """
    Validate if an origin is allowed by current CORS configuration
    
    Useful for testing CORS configuration without making actual requests.
    """
    config = get_cors_config()
    is_allowed = config.is_origin_allowed(origin)
    
    return {
        "origin": origin,
        "is_allowed": is_allowed,
        "reason": "Allowed by configuration" if is_allowed else "Origin not in allowed list or patterns"
    }


@router.get("/test")
async def test_cors_endpoint():
    """
    Test endpoint for CORS
    
    This endpoint can be used to test CORS configuration from browser applications.
    It returns information about the request including headers.
    """
    return {
        "message": "CORS test successful",
        "cors_enabled": True,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/preflight-info")
async def get_preflight_info(
    current_user: Dict = Depends(require_permissions("admin", "cors.read"))
):
    """
    Get information about CORS preflight requests
    
    Returns details about how preflight requests are handled.
    """
    config = get_cors_config()
    
    return {
        "preflight_cache_duration": config.max_age,
        "preflight_cache_duration_human": f"{config.max_age // 3600} hours",
        "credentials_allowed": config.allow_credentials,
        "preflight_methods": config.allowed_methods,
        "preflight_headers": config.allowed_headers,
        "notes": [
            "Preflight requests are OPTIONS requests sent by browsers",
            "They check if the actual request is allowed before sending it",
            f"Responses are cached for {config.max_age} seconds",
            "Credentials include cookies, authorization headers, and TLS certificates"
        ]
    }


@router.get("/troubleshooting")
async def cors_troubleshooting_guide():
    """
    Get CORS troubleshooting guide
    
    Returns common CORS issues and their solutions.
    """
    return {
        "common_issues": [
            {
                "issue": "No 'Access-Control-Allow-Origin' header",
                "causes": [
                    "Origin not in allowed list",
                    "CORS middleware not properly configured",
                    "Request doesn't include Origin header"
                ],
                "solutions": [
                    "Add origin to CORS_ORIGINS environment variable",
                    "Check if CORS middleware is enabled",
                    "Ensure client sends Origin header"
                ]
            },
            {
                "issue": "Credentials not working",
                "causes": [
                    "allow_credentials is false",
                    "Using wildcard (*) with credentials",
                    "Cookie SameSite attribute too restrictive"
                ],
                "solutions": [
                    "Set CORS_ALLOW_CREDENTIALS=true",
                    "Use specific origins instead of wildcard",
                    "Adjust cookie SameSite attribute"
                ]
            },
            {
                "issue": "Preflight request fails",
                "causes": [
                    "Requested method not in allowed methods",
                    "Custom header not in allowed headers",
                    "Preflight response missing required headers"
                ],
                "solutions": [
                    "Add method to CORS_ALLOWED_METHODS",
                    "Add header to CORS_ALLOWED_HEADERS",
                    "Check preflight response headers"
                ]
            }
        ],
        "debugging_tips": [
            "Use browser developer tools Network tab",
            "Check for CORS errors in browser console",
            "Test with curl to see actual headers",
            "Use online CORS testing tools",
            "Check server logs for CORS-related warnings"
        ],
        "test_commands": {
            "preflight": "curl -X OPTIONS -H 'Origin: https://example.com' -H 'Access-Control-Request-Method: POST' -H 'Access-Control-Request-Headers: Content-Type' -i https://api.mams.example.com/api/v1/users",
            "actual_request": "curl -X POST -H 'Origin: https://example.com' -H 'Content-Type: application/json' -i https://api.mams.example.com/api/v1/users"
        }
    }


@router.get("/security-best-practices")
async def cors_security_best_practices():
    """
    Get CORS security best practices
    
    Returns recommendations for secure CORS configuration.
    """
    return {
        "best_practices": [
            {
                "practice": "Never use wildcard (*) in production",
                "reason": "Allows any website to access your API",
                "recommendation": "Use specific origin URLs"
            },
            {
                "practice": "Be careful with credentials",
                "reason": "Credentials + wildcard is not allowed by browsers",
                "recommendation": "Use specific origins when allowing credentials"
            },
            {
                "practice": "Validate origin patterns carefully",
                "reason": "Overly broad patterns can allow unintended origins",
                "recommendation": "Use restrictive regex patterns"
            },
            {
                "practice": "Limit allowed headers",
                "reason": "Reduces attack surface",
                "recommendation": "Only allow headers your API actually uses"
            },
            {
                "practice": "Use HTTPS for all origins",
                "reason": "Prevents MITM attacks",
                "recommendation": "Require HTTPS in production"
            },
            {
                "practice": "Regularly review allowed origins",
                "reason": "Remove unused or old origins",
                "recommendation": "Audit CORS configuration quarterly"
            }
        ],
        "environment_recommendations": {
            "development": {
                "allowed_origins": ["http://localhost:3000", "http://localhost:3001"],
                "allow_credentials": True,
                "notes": "Permissive for local development"
            },
            "staging": {
                "allowed_origins": ["https://staging.yourapp.com"],
                "allowed_patterns": ["https://*.staging.yourapp.com"],
                "allow_credentials": True,
                "notes": "More restrictive than development"
            },
            "production": {
                "allowed_origins": ["https://app.yourcompany.com", "https://www.yourcompany.com"],
                "allowed_patterns": [],
                "allow_credentials": True,
                "notes": "Highly restrictive, specific origins only"
            }
        }
    }


# Import datetime for timestamp
from datetime import datetime

# Export router
cors_management_router = router