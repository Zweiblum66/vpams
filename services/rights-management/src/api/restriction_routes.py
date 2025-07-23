"""
Rights Management Service - Usage Restriction API Routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import uuid

from ..core.database import get_db
from ..core.auth import get_current_user
from ..core.logger import get_logger
from ..models.schemas import (
    RightsComplianceCheck, RightsComplianceResult, User
)
from ..services.restriction_service import RestrictionService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/rights/restrictions", tags=["restrictions"])


@router.post("/check", response_model=RightsComplianceResult)
async def check_usage_restrictions(
    compliance_check: RightsComplianceCheck,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check all usage restrictions for a compliance request"""
    try:
        restriction_service = RestrictionService(db)
        result = await restriction_service.check_usage_restrictions(compliance_check)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to check usage restrictions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check usage restrictions: {str(e)}"
        )


@router.post("/temporal/{license_id}")
async def check_temporal_restrictions(
    license_id: str,
    requested_datetime: datetime,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check temporal restrictions for a specific license"""
    try:
        restriction_service = RestrictionService(db)
        result = await restriction_service.enforce_temporal_restrictions(
            license_id, 
            requested_datetime
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to check temporal restrictions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check temporal restrictions: {str(e)}"
        )


@router.post("/quotas/{license_id}")
async def check_usage_quotas(
    license_id: str,
    usage_count: int = Query(1, ge=1),
    duration_seconds: Optional[int] = Query(None, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check usage quotas for a specific license"""
    try:
        restriction_service = RestrictionService(db)
        result = await restriction_service.enforce_usage_quotas(
            license_id,
            usage_count,
            duration_seconds
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to check usage quotas: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check usage quotas: {str(e)}"
        )


@router.post("/geographic/{license_id}")
async def check_geographic_restrictions(
    license_id: str,
    country: str = Query(..., min_length=2, max_length=3),
    region: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check geographic restrictions for a specific license"""
    try:
        restriction_service = RestrictionService(db)
        result = await restriction_service.enforce_geographic_restrictions(
            license_id,
            country,
            region
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to check geographic restrictions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check geographic restrictions: {str(e)}"
        )


@router.post("/platform/{license_id}")
async def check_platform_restrictions(
    license_id: str,
    platform: str = Query(..., min_length=1),
    platform_metadata: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check platform-specific restrictions for a license"""
    try:
        restriction_service = RestrictionService(db)
        result = await restriction_service.enforce_platform_restrictions(
            license_id,
            platform,
            platform_metadata
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to check platform restrictions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check platform restrictions: {str(e)}"
        )


@router.post("/content/{license_id}")
async def check_content_restrictions(
    license_id: str,
    content_metadata: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check content-specific restrictions for a license"""
    try:
        restriction_service = RestrictionService(db)
        result = await restriction_service.check_content_restrictions(
            license_id,
            content_metadata
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to check content restrictions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check content restrictions: {str(e)}"
        )


@router.get("/license/{license_id}/summary")
async def get_license_restrictions_summary(
    license_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a summary of all restrictions for a license"""
    try:
        # Get license from database
        from sqlalchemy import select
        from ..db.models import License
        
        result = await db.execute(
            select(License).where(License.id == license_id)
        )
        license = result.scalar_one_or_none()
        
        if not license:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="License not found"
            )
        
        # Extract restriction information from license
        restrictions_summary = {
            "license_id": license_id,
            "license_number": license.license_number,
            "status": license.status,
            "geographic_scope": license.geographic_scope,
            "countries": license.countries,
            "exclusivity": license.exclusivity,
            "sublicensing_allowed": license.sublicensing_allowed,
            "usage_limits": {
                "max_usage_count": license.max_usage_count,
                "max_duration_seconds": license.max_duration_seconds
            },
            "validity_period": {
                "start_date": license.start_date.isoformat() if license.start_date else None,
                "end_date": license.end_date.isoformat() if license.end_date else None
            },
            "financial_terms": {
                "license_fee": license.license_fee,
                "currency": license.currency,
                "royalty_rate": license.royalty_rate,
                "minimum_guarantee": license.minimum_guarantee
            },
            "custom_restrictions": license.metadata.get("restrictions", {}) if license.metadata else {}
        }
        
        return restrictions_summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get license restrictions summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get license restrictions summary: {str(e)}"
        )


@router.get("/compliance-report")
async def generate_compliance_report(
    asset_id: Optional[str] = Query(None),
    license_id: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate a compliance report for restrictions"""
    try:
        from sqlalchemy import select, and_, func
        from ..db.models import License, UsageRecord, ComplianceAlert
        
        # Build query filters
        filters = []
        if asset_id:
            filters.append(License.asset_id == asset_id)
        if license_id:
            filters.append(License.id == license_id)
        if start_date:
            filters.append(License.created_at >= start_date)
        if end_date:
            filters.append(License.created_at <= end_date)
        
        # Get licenses
        license_query = select(License)
        if filters:
            license_query = license_query.where(and_(*filters))
        
        licenses_result = await db.execute(license_query)
        licenses = licenses_result.scalars().all()
        
        # Get compliance alerts
        alerts_result = await db.execute(
            select(ComplianceAlert).where(
                ComplianceAlert.alert_type.in_([
                    'usage_limit_exceeded', 'geographic_violation', 
                    'temporal_restriction', 'platform_restriction'
                ])
            )
        )
        alerts = alerts_result.scalars().all()
        
        # Generate report
        report = {
            "report_metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "generated_by": current_user.user_id,
                "filters": {
                    "asset_id": asset_id,
                    "license_id": license_id,
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None
                }
            },
            "summary": {
                "total_licenses": len(licenses),
                "active_licenses": len([l for l in licenses if l.status == "active"]),
                "total_compliance_alerts": len(alerts),
                "critical_alerts": len([a for a in alerts if a.severity == "critical"]),
                "unresolved_alerts": len([a for a in alerts if not a.is_resolved])
            },
            "license_restrictions": [],
            "compliance_violations": []
        }
        
        # Add license restriction details
        for license in licenses:
            license_info = {
                "license_id": license.id,
                "license_number": license.license_number,
                "asset_id": license.asset_id,
                "status": license.status,
                "restrictions": {
                    "geographic": {
                        "scope": license.geographic_scope,
                        "countries": license.countries
                    },
                    "usage_limits": {
                        "max_usage_count": license.max_usage_count,
                        "max_duration_seconds": license.max_duration_seconds
                    },
                    "exclusivity": license.exclusivity,
                    "sublicensing_allowed": license.sublicensing_allowed,
                    "custom_restrictions": license.metadata.get("restrictions", {}) if license.metadata else {}
                }
            }
            report["license_restrictions"].append(license_info)
        
        # Add compliance violations
        for alert in alerts:
            violation_info = {
                "alert_id": alert.id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "title": alert.title,
                "description": alert.description,
                "license_id": alert.license_id,
                "asset_id": alert.asset_id,
                "created_at": alert.created_at.isoformat(),
                "is_resolved": alert.is_resolved,
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None
            }
            report["compliance_violations"].append(violation_info)
        
        return report
        
    except Exception as e:
        logger.error(f"Failed to generate compliance report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate compliance report: {str(e)}"
        )


@router.get("/restrictions/types")
async def get_restriction_types():
    """Get available restriction types and their descriptions"""
    restriction_types = {
        "temporal_restrictions": {
            "description": "Time-based restrictions (hours, days, blackout periods)",
            "supported_configs": [
                "allowed_hours", "allowed_days", "blackout_periods", "seasonal_restrictions"
            ]
        },
        "usage_quotas": {
            "description": "Usage count and duration limits",
            "supported_configs": [
                "max_usage_count", "max_duration_seconds", "daily_limit", "monthly_limit"
            ]
        },
        "geographic_restrictions": {
            "description": "Country and region-based restrictions",
            "supported_configs": [
                "geographic_scope", "countries", "blocked_countries", "allowed_regions"
            ]
        },
        "platform_restrictions": {
            "description": "Platform-specific usage restrictions",
            "supported_configs": [
                "allowed_platforms", "blocked_platforms", "platform_quotas", "delivery_restrictions"
            ]
        },
        "content_restrictions": {
            "description": "Content rating, genre, and language restrictions",
            "supported_configs": [
                "allowed_ratings", "allowed_genres", "allowed_languages", "duration_limits"
            ]
        },
        "financial_restrictions": {
            "description": "Revenue and royalty-based restrictions",
            "supported_configs": [
                "minimum_revenue", "maximum_royalty", "revenue_sharing"
            ]
        }
    }
    
    return {
        "restriction_types": restriction_types,
        "metadata": {
            "total_types": len(restriction_types),
            "last_updated": "2025-07-18"
        }
    }


@router.post("/validate-config")
async def validate_restriction_config(
    restriction_config: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Validate a restriction configuration"""
    try:
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": []
        }
        
        # Validate temporal restrictions
        if "temporal_restrictions" in restriction_config:
            temporal = restriction_config["temporal_restrictions"]
            
            if "allowed_hours" in temporal:
                allowed_hours = temporal["allowed_hours"]
                if not isinstance(allowed_hours, dict) or "start" not in allowed_hours or "end" not in allowed_hours:
                    validation_result["is_valid"] = False
                    validation_result["errors"].append("allowed_hours must have 'start' and 'end' fields")
                elif not (0 <= allowed_hours["start"] <= 23 and 0 <= allowed_hours["end"] <= 23):
                    validation_result["is_valid"] = False
                    validation_result["errors"].append("allowed_hours start and end must be between 0 and 23")
            
            if "blackout_periods" in temporal:
                blackout_periods = temporal["blackout_periods"]
                if not isinstance(blackout_periods, list):
                    validation_result["is_valid"] = False
                    validation_result["errors"].append("blackout_periods must be a list")
                else:
                    for period in blackout_periods:
                        if "start" not in period or "end" not in period:
                            validation_result["is_valid"] = False
                            validation_result["errors"].append("Each blackout period must have 'start' and 'end' dates")
        
        # Validate geographic restrictions
        if "geographic_restrictions" in restriction_config:
            geo = restriction_config["geographic_restrictions"]
            
            if "countries" in geo:
                countries = geo["countries"]
                if not isinstance(countries, list):
                    validation_result["is_valid"] = False
                    validation_result["errors"].append("countries must be a list")
                elif any(len(country) not in [2, 3] for country in countries):
                    validation_result["warnings"].append("Country codes should be 2 or 3 characters (ISO standard)")
        
        # Validate platform restrictions
        if "platform_restrictions" in restriction_config:
            platform = restriction_config["platform_restrictions"]
            
            if "delivery_restrictions" in platform:
                delivery = platform["delivery_restrictions"]
                if "quality" in delivery and "max_resolution" in delivery["quality"]:
                    max_res = delivery["quality"]["max_resolution"]
                    valid_resolutions = ["240p", "360p", "480p", "720p", "1080p", "1440p", "4k", "8k"]
                    if max_res not in valid_resolutions:
                        validation_result["warnings"].append(
                            f"Unknown resolution '{max_res}'. Valid options: {', '.join(valid_resolutions)}"
                        )
        
        # Add suggestions
        if validation_result["is_valid"]:
            validation_result["suggestions"].append("Configuration is valid and ready to use")
        
        if not restriction_config:
            validation_result["warnings"].append("Empty restriction configuration - no restrictions will be enforced")
        
        return validation_result
        
    except Exception as e:
        logger.error(f"Failed to validate restriction config: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate restriction config: {str(e)}"
        )