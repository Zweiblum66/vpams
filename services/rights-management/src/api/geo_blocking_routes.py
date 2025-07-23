"""
Rights Management Service - Geo-blocking API Routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import date
import uuid

from ..core.database import get_db
from ..core.auth import get_current_user
from ..core.logger import get_logger
from ..models.schemas import User
from ..services.geo_blocking_service import GeoBlockingService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/rights/geo-blocking", tags=["geo-blocking"])


@router.post("/check/{license_id}")
async def check_geographic_access(
    license_id: str,
    country_code: str = Query(..., min_length=2, max_length=3, description="ISO country code"),
    region_code: Optional[str] = Query(None, description="Region/state code"),
    ip_address: Optional[str] = Query(None, description="IP address for geolocation"),
    user_location: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check if geographic access is allowed for a license"""
    try:
        geo_service = GeoBlockingService(db)
        result = await geo_service.check_geographic_access(
            license_id=license_id,
            country_code=country_code,
            region_code=region_code,
            ip_address=ip_address,
            user_location=user_location
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to check geographic access: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check geographic access: {str(e)}"
        )


@router.get("/ip-geolocation/{ip_address}")
async def get_ip_geolocation(
    ip_address: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get geolocation information for an IP address"""
    try:
        geo_service = GeoBlockingService(db)
        geo_info = await geo_service.get_ip_geolocation(ip_address)
        
        return geo_info
        
    except Exception as e:
        logger.error(f"Failed to get IP geolocation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get IP geolocation: {str(e)}"
        )


@router.post("/rules/{license_id}")
async def create_geo_blocking_rule(
    license_id: str,
    rule_config: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new geo-blocking rule for a license"""
    try:
        geo_service = GeoBlockingService(db)
        result = await geo_service.create_geo_blocking_rule(
            license_id=license_id,
            rule_config=rule_config,
            user=current_user
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("errors", ["Failed to create rule"])
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create geo-blocking rule: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create geo-blocking rule: {str(e)}"
        )


@router.put("/rules/{license_id}/{rule_id}")
async def update_geo_blocking_rule(
    license_id: str,
    rule_id: str,
    rule_updates: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an existing geo-blocking rule"""
    try:
        geo_service = GeoBlockingService(db)
        result = await geo_service.update_geo_blocking_rule(
            license_id=license_id,
            rule_id=rule_id,
            rule_updates=rule_updates,
            user=current_user
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result.get("error", "Rule not found")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update geo-blocking rule: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update geo-blocking rule: {str(e)}"
        )


@router.delete("/rules/{license_id}/{rule_id}")
async def delete_geo_blocking_rule(
    license_id: str,
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a geo-blocking rule"""
    try:
        geo_service = GeoBlockingService(db)
        result = await geo_service.delete_geo_blocking_rule(
            license_id=license_id,
            rule_id=rule_id,
            user=current_user
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result.get("error", "Rule not found")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete geo-blocking rule: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete geo-blocking rule: {str(e)}"
        )


@router.get("/rules/{license_id}")
async def get_geo_blocking_rules(
    license_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all geo-blocking rules for a license"""
    try:
        from sqlalchemy import select
        from ..db.models import License
        
        # Get license
        result = await db.execute(
            select(License).where(License.id == license_id)
        )
        license = result.scalar_one_or_none()
        
        if not license:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="License not found"
            )
        
        # Extract geo-blocking rules from metadata
        geo_blocking = license.metadata.get("geo_blocking", {}) if license.metadata else {}
        rules = geo_blocking.get("rules", [])
        
        return {
            "license_id": license_id,
            "total_rules": len(rules),
            "rules": rules,
            "geo_blocking_config": {
                "block_vpn": geo_blocking.get("block_vpn", False),
                "ip_restrictions": geo_blocking.get("ip_restrictions", {}),
                "regional_restrictions": geo_blocking.get("regional_restrictions", {}),
                "timezone_restrictions": geo_blocking.get("timezone_restrictions", {})
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get geo-blocking rules: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get geo-blocking rules: {str(e)}"
        )


@router.get("/analytics")
async def get_geo_blocking_analytics(
    license_id: Optional[str] = Query(None, description="Filter by license ID"),
    start_date: Optional[date] = Query(None, description="Start date for analytics"),
    end_date: Optional[date] = Query(None, description="End date for analytics"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get analytics on geo-blocking activity"""
    try:
        geo_service = GeoBlockingService(db)
        analytics = await geo_service.get_geo_blocking_analytics(
            license_id=license_id,
            start_date=start_date,
            end_date=end_date
        )
        
        return analytics
        
    except Exception as e:
        logger.error(f"Failed to get geo-blocking analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get geo-blocking analytics: {str(e)}"
        )


@router.post("/check-by-ip")
async def check_access_by_ip(
    request: Request,
    license_id: str = Query(..., description="License ID to check"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check geographic access based on request IP address"""
    try:
        # Get client IP from request
        client_ip = request.client.host
        
        # Handle proxy headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            client_ip = forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            client_ip = real_ip
        
        # Get geolocation for IP
        geo_service = GeoBlockingService(db)
        geo_info = await geo_service.get_ip_geolocation(client_ip)
        
        if "error" in geo_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to get geolocation: {geo_info['error']}"
            )
        
        # Check access with geolocation
        result = await geo_service.check_geographic_access(
            license_id=license_id,
            country_code=geo_info.get("country_code", "UNKNOWN"),
            region_code=geo_info.get("region"),
            ip_address=client_ip,
            user_location={
                "timezone": geo_info.get("timezone"),
                "latitude": geo_info.get("latitude"),
                "longitude": geo_info.get("longitude")
            }
        )
        
        return {
            "check_result": result,
            "ip_info": {
                "ip_address": client_ip,
                "country": geo_info.get("country_name"),
                "country_code": geo_info.get("country_code"),
                "region": geo_info.get("region"),
                "city": geo_info.get("city")
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to check access by IP: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check access by IP: {str(e)}"
        )


@router.get("/countries/sanctioned")
async def get_sanctioned_countries(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of sanctioned countries"""
    # This would typically be managed in a database
    # For now, return a static list
    sanctioned_countries = [
        {"code": "IR", "name": "Iran", "sanctions_type": "comprehensive"},
        {"code": "KP", "name": "North Korea", "sanctions_type": "comprehensive"},
        {"code": "SY", "name": "Syria", "sanctions_type": "comprehensive"},
        {"code": "CU", "name": "Cuba", "sanctions_type": "partial"},
        {"code": "VE", "name": "Venezuela", "sanctions_type": "partial"},
        {"code": "RU", "name": "Russia", "sanctions_type": "sectoral"}
    ]
    
    return {
        "total": len(sanctioned_countries),
        "countries": sanctioned_countries,
        "last_updated": "2025-07-18",
        "note": "This list is for demonstration. Implement proper sanctions database integration."
    }


@router.post("/validate-rule")
async def validate_geo_blocking_rule(
    rule_config: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Validate a geo-blocking rule configuration"""
    try:
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": []
        }
        
        # Check required fields
        if "rule_type" not in rule_config:
            validation_result["is_valid"] = False
            validation_result["errors"].append("rule_type is required")
        
        if "rule_name" not in rule_config:
            validation_result["is_valid"] = False
            validation_result["errors"].append("rule_name is required")
        
        # Validate rule type
        valid_rule_types = [
            "country_block", "country_allow", "ip_block", "ip_allow",
            "region_block", "region_allow", "vpn_block"
        ]
        
        if rule_config.get("rule_type") not in valid_rule_types:
            validation_result["is_valid"] = False
            validation_result["errors"].append(
                f"Invalid rule_type. Valid options: {', '.join(valid_rule_types)}"
            )
        
        # Validate countries if present
        if "countries" in rule_config:
            countries = rule_config["countries"]
            if not isinstance(countries, list):
                validation_result["is_valid"] = False
                validation_result["errors"].append("countries must be a list")
            elif not countries:
                validation_result["warnings"].append("Empty countries list - rule will have no effect")
            else:
                for country in countries:
                    if not isinstance(country, str) or len(country) not in [2, 3]:
                        validation_result["warnings"].append(
                            f"Country code '{country}' should be 2 or 3 characters (ISO standard)"
                        )
        
        # Validate IP addresses if present
        if "ip_addresses" in rule_config:
            import ipaddress
            for ip in rule_config["ip_addresses"]:
                try:
                    if "/" in ip:
                        ipaddress.ip_network(ip)
                    else:
                        ipaddress.ip_address(ip)
                except ValueError:
                    validation_result["is_valid"] = False
                    validation_result["errors"].append(f"Invalid IP address or CIDR: {ip}")
        
        # Add suggestions
        if validation_result["is_valid"]:
            if rule_config.get("rule_type") == "vpn_block":
                validation_result["suggestions"].append(
                    "Consider using a professional VPN detection service for better accuracy"
                )
            
            if "countries" in rule_config and len(rule_config["countries"]) > 50:
                validation_result["suggestions"].append(
                    "Large country lists may impact performance. Consider using 'country_allow' instead"
                )
        
        return validation_result
        
    except Exception as e:
        logger.error(f"Failed to validate geo-blocking rule: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate geo-blocking rule: {str(e)}"
        )


@router.get("/rule-types")
async def get_geo_blocking_rule_types():
    """Get available geo-blocking rule types and their descriptions"""
    rule_types = {
        "country_block": {
            "description": "Block access from specific countries",
            "required_fields": ["countries"],
            "optional_fields": ["description", "enabled"]
        },
        "country_allow": {
            "description": "Allow access only from specific countries",
            "required_fields": ["countries"],
            "optional_fields": ["description", "enabled"]
        },
        "ip_block": {
            "description": "Block specific IP addresses or ranges",
            "required_fields": ["ip_addresses"],
            "optional_fields": ["description", "enabled"]
        },
        "ip_allow": {
            "description": "Allow only specific IP addresses or ranges",
            "required_fields": ["ip_addresses"],
            "optional_fields": ["description", "enabled"]
        },
        "region_block": {
            "description": "Block access from specific regions within countries",
            "required_fields": ["regions"],
            "optional_fields": ["country", "description", "enabled"]
        },
        "region_allow": {
            "description": "Allow access only from specific regions",
            "required_fields": ["regions"],
            "optional_fields": ["country", "description", "enabled"]
        },
        "vpn_block": {
            "description": "Block access from VPN and proxy connections",
            "required_fields": [],
            "optional_fields": ["detection_level", "whitelist_ips", "description", "enabled"]
        }
    }
    
    return {
        "rule_types": rule_types,
        "metadata": {
            "total_types": len(rule_types),
            "version": "1.0"
        }
    }