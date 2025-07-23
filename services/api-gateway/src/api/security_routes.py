"""
Security Management Routes

Provides endpoints for managing security headers, CSP violations,
and security monitoring.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, HTTPException, status, Depends
from pydantic import BaseModel, Field
import logging

from core.security_headers import (
    get_csp_reporter,
    get_security_headers_config,
    SecurityHeadersConfig,
    CSPViolationReporter
)
from core.auth import get_current_active_user
from models.user import User
from core.exceptions import ValidationException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/security", tags=["security"])


class CSPViolationReport(BaseModel):
    """CSP violation report schema"""
    document_uri: str = Field(..., description="URI of the document")
    referrer: Optional[str] = Field(None, description="Referrer URL")
    violated_directive: str = Field(..., description="Violated CSP directive")
    effective_directive: str = Field(..., description="Effective CSP directive")
    original_policy: str = Field(..., description="Original CSP policy")
    blocked_uri: str = Field(..., description="Blocked URI")
    status_code: int = Field(..., description="HTTP status code")
    source_file: Optional[str] = Field(None, description="Source file")
    line_number: Optional[int] = Field(None, description="Line number")
    column_number: Optional[int] = Field(None, description="Column number")
    sample: Optional[str] = Field(None, description="Sample of blocked content")


class CSPViolationResponse(BaseModel):
    """CSP violation response schema"""
    timestamp: str = Field(..., description="Violation timestamp")
    client_ip: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="User agent")
    referer: Optional[str] = Field(None, description="Referer header")
    violation: CSPViolationReport = Field(..., description="Violation details")


class SecurityHeadersStatus(BaseModel):
    """Security headers status schema"""
    environment: str = Field(..., description="Environment name")
    csp_enabled: bool = Field(..., description="CSP enabled status")
    csp_report_only: bool = Field(..., description="CSP report-only mode")
    hsts_enabled: bool = Field(..., description="HSTS enabled status")
    frame_options_enabled: bool = Field(..., description="X-Frame-Options enabled")
    content_type_options_enabled: bool = Field(..., description="X-Content-Type-Options enabled")
    xss_protection_enabled: bool = Field(..., description="X-XSS-Protection enabled")
    referrer_policy_enabled: bool = Field(..., description="Referrer Policy enabled")
    permissions_policy_enabled: bool = Field(..., description="Permissions Policy enabled")
    cross_origin_policies_enabled: bool = Field(..., description="Cross-Origin policies enabled")
    additional_headers_enabled: bool = Field(..., description="Additional headers enabled")
    total_violations: int = Field(..., description="Total CSP violations")
    recent_violations: int = Field(..., description="Recent violations (last 24h)")


class SecurityHeadersConfigResponse(BaseModel):
    """Security headers configuration response"""
    environment: str = Field(..., description="Environment name")
    csp_policy: Optional[str] = Field(None, description="Current CSP policy")
    hsts_policy: Optional[str] = Field(None, description="Current HSTS policy")
    permissions_policy: Optional[str] = Field(None, description="Current Permissions Policy")
    enabled_features: List[str] = Field(..., description="List of enabled security features")
    configuration: Dict[str, Any] = Field(..., description="Full configuration")


class ViolationStats(BaseModel):
    """Violation statistics schema"""
    total: int = Field(..., description="Total violations")
    by_type: Dict[str, int] = Field(..., description="Violations by type")
    by_ip: Dict[str, int] = Field(..., description="Violations by IP")
    latest: Optional[str] = Field(None, description="Latest violation timestamp")
    time_period: str = Field(..., description="Time period for statistics")


class SecurityConfigUpdate(BaseModel):
    """Security configuration update schema"""
    csp_report_only: Optional[bool] = Field(None, description="Enable CSP report-only mode")
    log_security_headers: Optional[bool] = Field(None, description="Enable security headers logging")
    log_violations: Optional[bool] = Field(None, description="Enable violation logging")
    csp_script_src: Optional[List[str]] = Field(None, description="CSP script-src directive")
    csp_style_src: Optional[List[str]] = Field(None, description="CSP style-src directive")
    csp_img_src: Optional[List[str]] = Field(None, description="CSP img-src directive")
    csp_connect_src: Optional[List[str]] = Field(None, description="CSP connect-src directive")


@router.post("/csp-report", status_code=status.HTTP_204_NO_CONTENT)
async def report_csp_violation(
    request: Request,
    violation_data: Dict[str, Any]
):
    """
    Receive CSP violation reports
    
    This endpoint receives CSP violation reports from browsers
    and stores them for analysis.
    """
    try:
        # Get CSP reporter
        reporter = get_csp_reporter()
        
        # Extract the csp-report from the request
        csp_report = violation_data.get('csp-report', violation_data)
        
        # Validate and store the violation
        await reporter.report_violation(request, csp_report)
        
        logger.info(
            "CSP violation reported",
            extra={
                "client_ip": request.client.host if request.client else None,
                "violated_directive": csp_report.get('violated-directive', 'unknown'),
                "blocked_uri": csp_report.get('blocked-uri', 'unknown')
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to process CSP violation report: {e}")
        # Don't return error to avoid browser retry loops


@router.get("/status", response_model=SecurityHeadersStatus)
async def get_security_status(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get security headers status
    
    Returns the current status of security headers and violation statistics.
    Requires authentication.
    """
    try:
        config = get_security_headers_config()
        reporter = get_csp_reporter()
        
        # Get violation statistics
        violations = reporter.get_violations()
        recent_violations = reporter.get_violations(
            since=datetime.utcnow() - timedelta(hours=24)
        )
        
        return SecurityHeadersStatus(
            environment=config.environment,
            csp_enabled=config.enable_csp,
            csp_report_only=config.csp_report_only,
            hsts_enabled=config.enable_hsts,
            frame_options_enabled=config.enable_frame_options,
            content_type_options_enabled=config.enable_content_type_options,
            xss_protection_enabled=config.enable_xss_protection,
            referrer_policy_enabled=config.enable_referrer_policy,
            permissions_policy_enabled=config.enable_permissions_policy,
            cross_origin_policies_enabled=config.enable_cross_origin_policies,
            additional_headers_enabled=config.enable_additional_headers,
            total_violations=len(violations),
            recent_violations=len(recent_violations)
        )
        
    except Exception as e:
        logger.error(f"Failed to get security status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get security status"
        )


@router.get("/config", response_model=SecurityHeadersConfigResponse)
async def get_security_config(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get security headers configuration
    
    Returns the current security headers configuration.
    Requires authentication.
    """
    try:
        config = get_security_headers_config()
        
        from core.security_headers import SecurityHeadersBuilder
        builder = SecurityHeadersBuilder(config)
        
        # Build current policies
        csp_policy = builder.build_csp_header() if config.enable_csp else None
        hsts_policy = builder.build_hsts_header() if config.enable_hsts else None
        permissions_policy = builder.build_permissions_policy_header() if config.enable_permissions_policy else None
        
        # Get enabled features
        enabled_features = []
        if config.enable_csp:
            enabled_features.append("Content Security Policy")
        if config.enable_hsts:
            enabled_features.append("HTTP Strict Transport Security")
        if config.enable_frame_options:
            enabled_features.append("X-Frame-Options")
        if config.enable_content_type_options:
            enabled_features.append("X-Content-Type-Options")
        if config.enable_xss_protection:
            enabled_features.append("X-XSS-Protection")
        if config.enable_referrer_policy:
            enabled_features.append("Referrer Policy")
        if config.enable_permissions_policy:
            enabled_features.append("Permissions Policy")
        if config.enable_cross_origin_policies:
            enabled_features.append("Cross-Origin Policies")
        if config.enable_additional_headers:
            enabled_features.append("Additional Security Headers")
        
        return SecurityHeadersConfigResponse(
            environment=config.environment,
            csp_policy=csp_policy,
            hsts_policy=hsts_policy,
            permissions_policy=permissions_policy,
            enabled_features=enabled_features,
            configuration=config.dict()
        )
        
    except Exception as e:
        logger.error(f"Failed to get security config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get security config"
        )


@router.get("/violations", response_model=List[CSPViolationResponse])
async def get_csp_violations(
    hours: int = 24,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get CSP violations
    
    Returns recent CSP violations for analysis.
    Requires authentication.
    """
    try:
        reporter = get_csp_reporter()
        
        # Get violations from the specified time period
        since = datetime.utcnow() - timedelta(hours=hours)
        violations = reporter.get_violations(since=since)
        
        # Limit results
        violations = violations[-limit:] if len(violations) > limit else violations
        
        # Convert to response format
        response_violations = []
        for violation in violations:
            try:
                response_violations.append(
                    CSPViolationResponse(
                        timestamp=violation["timestamp"],
                        client_ip=violation["client_ip"],
                        user_agent=violation["user_agent"],
                        referer=violation["referer"],
                        violation=CSPViolationReport(
                            document_uri=violation["violation"].get("document-uri", ""),
                            referrer=violation["violation"].get("referrer"),
                            violated_directive=violation["violation"].get("violated-directive", ""),
                            effective_directive=violation["violation"].get("effective-directive", ""),
                            original_policy=violation["violation"].get("original-policy", ""),
                            blocked_uri=violation["violation"].get("blocked-uri", ""),
                            status_code=violation["violation"].get("status-code", 0),
                            source_file=violation["violation"].get("source-file"),
                            line_number=violation["violation"].get("line-number"),
                            column_number=violation["violation"].get("column-number"),
                            sample=violation["violation"].get("sample")
                        )
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to parse violation: {e}")
                continue
        
        return response_violations
        
    except Exception as e:
        logger.error(f"Failed to get CSP violations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get CSP violations"
        )


@router.get("/violations/stats", response_model=ViolationStats)
async def get_violation_stats(
    hours: int = 24,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get CSP violation statistics
    
    Returns aggregated statistics about CSP violations.
    Requires authentication.
    """
    try:
        reporter = get_csp_reporter()
        
        # Get violations from the specified time period
        since = datetime.utcnow() - timedelta(hours=hours)
        violations = reporter.get_violations(since=since)
        
        # Calculate statistics
        stats = reporter.get_violation_stats()
        
        # Filter by time period
        filtered_stats = {
            "total": len(violations),
            "by_type": {},
            "by_ip": {},
            "latest": None
        }
        
        for violation in violations:
            # Count by violation type
            violated_directive = violation["violation"].get("violated-directive", "unknown")
            filtered_stats["by_type"][violated_directive] = filtered_stats["by_type"].get(violated_directive, 0) + 1
            
            # Count by IP
            ip = violation["client_ip"] or "unknown"
            filtered_stats["by_ip"][ip] = filtered_stats["by_ip"].get(ip, 0) + 1
            
            # Update latest timestamp
            if not filtered_stats["latest"] or violation["timestamp"] > filtered_stats["latest"]:
                filtered_stats["latest"] = violation["timestamp"]
        
        return ViolationStats(
            total=filtered_stats["total"],
            by_type=filtered_stats["by_type"],
            by_ip=filtered_stats["by_ip"],
            latest=filtered_stats["latest"],
            time_period=f"last {hours} hours"
        )
        
    except Exception as e:
        logger.error(f"Failed to get violation stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get violation stats"
        )


@router.post("/config/update", response_model=SecurityHeadersConfigResponse)
async def update_security_config(
    config_update: SecurityConfigUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Update security headers configuration
    
    Updates the security headers configuration.
    Requires authentication with admin privileges.
    
    Note: This endpoint updates the runtime configuration only.
    For persistent changes, update the configuration file.
    """
    try:
        # Check if user has admin privileges
        if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )
        
        config = get_security_headers_config()
        
        # Update configuration
        if config_update.csp_report_only is not None:
            config.csp_report_only = config_update.csp_report_only
        
        if config_update.log_security_headers is not None:
            config.log_security_headers = config_update.log_security_headers
        
        if config_update.log_violations is not None:
            config.log_violations = config_update.log_violations
        
        if config_update.csp_script_src is not None:
            config.csp_script_src = config_update.csp_script_src
        
        if config_update.csp_style_src is not None:
            config.csp_style_src = config_update.csp_style_src
        
        if config_update.csp_img_src is not None:
            config.csp_img_src = config_update.csp_img_src
        
        if config_update.csp_connect_src is not None:
            config.csp_connect_src = config_update.csp_connect_src
        
        # Log configuration change
        logger.info(
            "Security configuration updated",
            extra={
                "user_id": str(current_user.id),
                "changes": config_update.dict(exclude_none=True)
            }
        )
        
        # Return updated configuration
        return await get_security_config(current_user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update security config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update security config"
        )


@router.delete("/violations", status_code=status.HTTP_204_NO_CONTENT)
async def clear_violations(
    current_user: User = Depends(get_current_active_user)
):
    """
    Clear CSP violations
    
    Clears all stored CSP violations.
    Requires authentication with admin privileges.
    """
    try:
        # Check if user has admin privileges
        if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )
        
        reporter = get_csp_reporter()
        reporter.violations.clear()
        
        logger.info(
            "CSP violations cleared",
            extra={
                "user_id": str(current_user.id)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clear violations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear violations"
        )


@router.get("/headers/test")
async def test_security_headers(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """
    Test security headers
    
    Returns a test response to verify security headers are being applied.
    Requires authentication.
    """
    return {
        "message": "Security headers test",
        "timestamp": datetime.utcnow().isoformat(),
        "request_url": str(request.url),
        "user_agent": request.headers.get("user-agent"),
        "note": "Check response headers to verify security headers are applied"
    }
