"""
Rights Management Service - Geo-blocking Service
"""

import asyncio
import json
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Union, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.orm import selectinload
import uuid
import ipaddress
import httpx

from ..models.schemas import User
from ..db.models import License, UsageRecord, ComplianceAlert
from ..core.config import settings
from ..core.exceptions import GeoBlockingError
from ..core.logger import get_logger

logger = get_logger(__name__)


class GeoBlockingService:
    """Service for geo-blocking and geographic access control"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ip_geolocation_cache = {}  # Simple in-memory cache
        self.cache_expiry = timedelta(hours=24)
    
    async def check_geographic_access(
        self,
        license_id: str,
        country_code: str,
        region_code: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_location: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Check if geographic access is allowed for a license"""
        try:
            logger.info(f"Checking geographic access for license {license_id} in {country_code}")
            
            # Get license
            result = await self.db.execute(
                select(License).where(License.id == license_id)
            )
            license = result.scalar_one_or_none()
            
            if not license:
                return {
                    "allowed": False,
                    "reason": "License not found",
                    "geo_info": {}
                }
            
            # Check basic geographic scope
            basic_check = await self._check_basic_geographic_scope(license, country_code)
            if not basic_check["allowed"]:
                return basic_check
            
            # Enhanced geo-blocking checks
            geo_result = {
                "allowed": True,
                "license_id": license_id,
                "country_code": country_code,
                "region_code": region_code,
                "violations": [],
                "warnings": [],
                "geo_info": {},
                "restrictions_applied": []
            }
            
            # Get geo-blocking configuration from license metadata
            geo_config = license.metadata.get("geo_blocking", {}) if license.metadata else {}
            
            # Check IP-based restrictions
            if ip_address and "ip_restrictions" in geo_config:
                ip_check = await self._check_ip_restrictions(geo_config["ip_restrictions"], ip_address)
                if not ip_check["allowed"]:
                    geo_result["allowed"] = False
                    geo_result["violations"].extend(ip_check["violations"])
                geo_result["geo_info"].update(ip_check.get("geo_info", {}))
                geo_result["restrictions_applied"].append("ip_restrictions")
            
            # Check regional restrictions
            if region_code and "regional_restrictions" in geo_config:
                region_check = await self._check_regional_restrictions(
                    geo_config["regional_restrictions"], 
                    country_code, 
                    region_code
                )
                if not region_check["allowed"]:
                    geo_result["allowed"] = False
                    geo_result["violations"].extend(region_check["violations"])
                geo_result["restrictions_applied"].append("regional_restrictions")
            
            # Check time-zone restrictions
            if user_location and "timezone_restrictions" in geo_config:
                timezone_check = await self._check_timezone_restrictions(
                    geo_config["timezone_restrictions"], 
                    user_location
                )
                if not timezone_check["allowed"]:
                    geo_result["allowed"] = False
                    geo_result["violations"].extend(timezone_check["violations"])
                geo_result["restrictions_applied"].append("timezone_restrictions")
            
            # Check sanctions and embargo restrictions
            sanctions_check = await self._check_sanctions_restrictions(country_code)
            if not sanctions_check["allowed"]:
                geo_result["allowed"] = False
                geo_result["violations"].extend(sanctions_check["violations"])
                geo_result["restrictions_applied"].append("sanctions_restrictions")
            
            # Check VPN/proxy detection if enabled
            if ip_address and geo_config.get("block_vpn", False):
                vpn_check = await self._check_vpn_proxy_detection(ip_address)
                if not vpn_check["allowed"]:
                    geo_result["allowed"] = False
                    geo_result["violations"].extend(vpn_check["violations"])
                geo_result["restrictions_applied"].append("vpn_detection")
            
            # Log access attempt
            await self._log_geographic_access_attempt(
                license_id, 
                country_code, 
                geo_result["allowed"], 
                ip_address
            )
            
            return geo_result
            
        except Exception as e:
            logger.error(f"Failed to check geographic access: {str(e)}")
            raise GeoBlockingError(f"Failed to check geographic access: {str(e)}")
    
    async def get_ip_geolocation(self, ip_address: str) -> Dict[str, Any]:
        """Get geolocation information for an IP address"""
        try:
            # Check cache first
            cache_key = ip_address
            if cache_key in self.ip_geolocation_cache:
                cached_data = self.ip_geolocation_cache[cache_key]
                if datetime.utcnow() - cached_data["cached_at"] < self.cache_expiry:
                    return cached_data["data"]
            
            # Validate IP address
            try:
                ipaddress.ip_address(ip_address)
            except ValueError:
                return {"error": "Invalid IP address format"}
            
            # Check if it's a private IP
            ip_obj = ipaddress.ip_address(ip_address)
            if ip_obj.is_private or ip_obj.is_loopback:
                return {
                    "ip": ip_address,
                    "country_code": "LOCAL",
                    "country_name": "Local/Private Network",
                    "region": "Private",
                    "city": "Local",
                    "is_private": True
                }
            
            # Use IP geolocation service (mock implementation - replace with real service)
            geo_data = await self._fetch_ip_geolocation(ip_address)
            
            # Cache the result
            self.ip_geolocation_cache[cache_key] = {
                "data": geo_data,
                "cached_at": datetime.utcnow()
            }
            
            return geo_data
            
        except Exception as e:
            logger.error(f"Failed to get IP geolocation: {str(e)}")
            return {"error": f"Geolocation lookup failed: {str(e)}"}
    
    async def create_geo_blocking_rule(
        self,
        license_id: str,
        rule_config: Dict[str, Any],
        user: User
    ) -> Dict[str, Any]:
        """Create a new geo-blocking rule for a license"""
        try:
            # Get license
            result = await self.db.execute(
                select(License).where(License.id == license_id)
            )
            license = result.scalar_one_or_none()
            
            if not license:
                raise GeoBlockingError("License not found")
            
            # Validate rule configuration
            validation_result = await self._validate_geo_blocking_rule(rule_config)
            if not validation_result["is_valid"]:
                return {
                    "success": False,
                    "errors": validation_result["errors"]
                }
            
            # Update license metadata with geo-blocking rules
            if not license.metadata:
                license.metadata = {}
            
            if "geo_blocking" not in license.metadata:
                license.metadata["geo_blocking"] = {}
            
            # Add the new rule
            rule_id = str(uuid.uuid4())
            rule_config["rule_id"] = rule_id
            rule_config["created_by"] = user.user_id
            rule_config["created_at"] = datetime.utcnow().isoformat()
            
            if "rules" not in license.metadata["geo_blocking"]:
                license.metadata["geo_blocking"]["rules"] = []
            
            license.metadata["geo_blocking"]["rules"].append(rule_config)
            
            # Mark metadata as modified for SQLAlchemy
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(license, "metadata")
            
            await self.db.commit()
            
            logger.info(f"Created geo-blocking rule {rule_id} for license {license_id}")
            
            return {
                "success": True,
                "rule_id": rule_id,
                "message": "Geo-blocking rule created successfully"
            }
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create geo-blocking rule: {str(e)}")
            raise GeoBlockingError(f"Failed to create geo-blocking rule: {str(e)}")
    
    async def update_geo_blocking_rule(
        self,
        license_id: str,
        rule_id: str,
        rule_updates: Dict[str, Any],
        user: User
    ) -> Dict[str, Any]:
        """Update an existing geo-blocking rule"""
        try:
            # Get license
            result = await self.db.execute(
                select(License).where(License.id == license_id)
            )
            license = result.scalar_one_or_none()
            
            if not license:
                raise GeoBlockingError("License not found")
            
            # Find and update the rule
            geo_blocking = license.metadata.get("geo_blocking", {}) if license.metadata else {}
            rules = geo_blocking.get("rules", [])
            
            rule_found = False
            for rule in rules:
                if rule.get("rule_id") == rule_id:
                    rule.update(rule_updates)
                    rule["updated_by"] = user.user_id
                    rule["updated_at"] = datetime.utcnow().isoformat()
                    rule_found = True
                    break
            
            if not rule_found:
                return {
                    "success": False,
                    "error": "Geo-blocking rule not found"
                }
            
            # Mark metadata as modified
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(license, "metadata")
            
            await self.db.commit()
            
            logger.info(f"Updated geo-blocking rule {rule_id} for license {license_id}")
            
            return {
                "success": True,
                "message": "Geo-blocking rule updated successfully"
            }
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update geo-blocking rule: {str(e)}")
            raise GeoBlockingError(f"Failed to update geo-blocking rule: {str(e)}")
    
    async def delete_geo_blocking_rule(
        self,
        license_id: str,
        rule_id: str,
        user: User
    ) -> Dict[str, Any]:
        """Delete a geo-blocking rule"""
        try:
            # Get license
            result = await self.db.execute(
                select(License).where(License.id == license_id)
            )
            license = result.scalar_one_or_none()
            
            if not license:
                raise GeoBlockingError("License not found")
            
            # Remove the rule
            geo_blocking = license.metadata.get("geo_blocking", {}) if license.metadata else {}
            rules = geo_blocking.get("rules", [])
            
            original_count = len(rules)
            rules[:] = [rule for rule in rules if rule.get("rule_id") != rule_id]
            
            if len(rules) == original_count:
                return {
                    "success": False,
                    "error": "Geo-blocking rule not found"
                }
            
            # Mark metadata as modified
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(license, "metadata")
            
            await self.db.commit()
            
            logger.info(f"Deleted geo-blocking rule {rule_id} for license {license_id}")
            
            return {
                "success": True,
                "message": "Geo-blocking rule deleted successfully"
            }
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to delete geo-blocking rule: {str(e)}")
            raise GeoBlockingError(f"Failed to delete geo-blocking rule: {str(e)}")
    
    async def get_geo_blocking_analytics(
        self,
        license_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Get analytics on geo-blocking activity"""
        try:
            # Build query for usage records
            query_filters = []
            
            if license_id:
                query_filters.append(UsageRecord.license_id == license_id)
            
            if start_date:
                query_filters.append(func.date(UsageRecord.usage_date) >= start_date)
            
            if end_date:
                query_filters.append(func.date(UsageRecord.usage_date) <= end_date)
            
            # Get usage records
            usage_query = select(UsageRecord)
            if query_filters:
                usage_query = usage_query.where(and_(*query_filters))
            
            usage_result = await self.db.execute(usage_query)
            usage_records = usage_result.scalars().all()
            
            # Get compliance alerts related to geo-blocking
            alerts_query = select(ComplianceAlert).where(
                ComplianceAlert.alert_type.in_([
                    'geographic_violation', 'geo_blocking_violation', 'vpn_detection'
                ])
            )
            
            if query_filters:
                # Apply same date filters to alerts
                if start_date:
                    alerts_query = alerts_query.where(func.date(ComplianceAlert.created_at) >= start_date)
                if end_date:
                    alerts_query = alerts_query.where(func.date(ComplianceAlert.created_at) <= end_date)
            
            alerts_result = await self.db.execute(alerts_query)
            alerts = alerts_result.scalars().all()
            
            # Analyze usage by country
            usage_by_country = {}
            blocked_attempts_by_country = {}
            
            for record in usage_records:
                country = record.country or "Unknown"
                usage_by_country[country] = usage_by_country.get(country, 0) + 1
            
            for alert in alerts:
                if alert.metadata and "country_code" in alert.metadata:
                    country = alert.metadata["country_code"]
                    blocked_attempts_by_country[country] = blocked_attempts_by_country.get(country, 0) + 1
            
            # Calculate blocking effectiveness
            total_attempts = len(usage_records) + len(alerts)
            blocked_attempts = len(alerts)
            blocking_rate = (blocked_attempts / total_attempts * 100) if total_attempts > 0 else 0
            
            analytics = {
                "summary": {
                    "total_usage_records": len(usage_records),
                    "total_blocked_attempts": blocked_attempts,
                    "blocking_rate_percentage": blocking_rate,
                    "unique_countries_accessed": len(usage_by_country),
                    "unique_countries_blocked": len(blocked_attempts_by_country)
                },
                "usage_by_country": usage_by_country,
                "blocked_attempts_by_country": blocked_attempts_by_country,
                "alert_breakdown": {
                    "geographic_violations": len([a for a in alerts if a.alert_type == "geographic_violation"]),
                    "vpn_detections": len([a for a in alerts if a.alert_type == "vpn_detection"]),
                    "other_geo_blocks": len([a for a in alerts if a.alert_type == "geo_blocking_violation"])
                },
                "time_period": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None
                }
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Failed to get geo-blocking analytics: {str(e)}")
            raise GeoBlockingError(f"Failed to get geo-blocking analytics: {str(e)}")
    
    # Private helper methods
    async def _check_basic_geographic_scope(self, license: License, country_code: str) -> Dict[str, Any]:
        """Check basic geographic scope from license"""
        if license.geographic_scope == "worldwide":
            return {"allowed": True}
        
        elif license.geographic_scope == "country_specific":
            if not license.countries or country_code not in license.countries:
                return {
                    "allowed": False,
                    "reason": f"Country {country_code} not in allowed countries",
                    "allowed_countries": license.countries or []
                }
            return {"allowed": True}
        
        else:
            # For other scopes, additional checks are needed
            return {"allowed": True}
    
    async def _check_ip_restrictions(self, ip_restrictions: Dict[str, Any], ip_address: str) -> Dict[str, Any]:
        """Check IP-based restrictions"""
        try:
            ip_obj = ipaddress.ip_address(ip_address)
            
            result = {
                "allowed": True,
                "violations": [],
                "geo_info": {}
            }
            
            # Check IP whitelist
            if "whitelisted_ips" in ip_restrictions:
                whitelisted = False
                for allowed_ip in ip_restrictions["whitelisted_ips"]:
                    try:
                        if "/" in allowed_ip:  # CIDR notation
                            if ip_obj in ipaddress.ip_network(allowed_ip):
                                whitelisted = True
                                break
                        else:  # Single IP
                            if ip_obj == ipaddress.ip_address(allowed_ip):
                                whitelisted = True
                                break
                    except ValueError:
                        continue
                
                if not whitelisted:
                    result["allowed"] = False
                    result["violations"].append(f"IP {ip_address} not in whitelist")
            
            # Check IP blacklist
            if "blacklisted_ips" in ip_restrictions:
                for blocked_ip in ip_restrictions["blacklisted_ips"]:
                    try:
                        if "/" in blocked_ip:  # CIDR notation
                            if ip_obj in ipaddress.ip_network(blocked_ip):
                                result["allowed"] = False
                                result["violations"].append(f"IP {ip_address} is blacklisted")
                                break
                        else:  # Single IP
                            if ip_obj == ipaddress.ip_address(blocked_ip):
                                result["allowed"] = False
                                result["violations"].append(f"IP {ip_address} is blacklisted")
                                break
                    except ValueError:
                        continue
            
            # Get geolocation info
            geo_info = await self.get_ip_geolocation(ip_address)
            result["geo_info"] = geo_info
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to check IP restrictions: {str(e)}")
            return {
                "allowed": False,
                "violations": [f"Error checking IP restrictions: {str(e)}"]
            }
    
    async def _check_regional_restrictions(
        self, 
        regional_restrictions: Dict[str, Any], 
        country_code: str, 
        region_code: str
    ) -> Dict[str, Any]:
        """Check regional restrictions"""
        result = {
            "allowed": True,
            "violations": []
        }
        
        # Check allowed regions
        if "allowed_regions" in regional_restrictions:
            allowed_regions = regional_restrictions["allowed_regions"]
            if region_code not in allowed_regions:
                result["allowed"] = False
                result["violations"].append(
                    f"Region {region_code} not in allowed regions: {', '.join(allowed_regions)}"
                )
        
        # Check blocked regions
        if "blocked_regions" in regional_restrictions:
            blocked_regions = regional_restrictions["blocked_regions"]
            if region_code in blocked_regions:
                result["allowed"] = False
                result["violations"].append(f"Region {region_code} is blocked")
        
        return result
    
    async def _check_timezone_restrictions(
        self, 
        timezone_restrictions: Dict[str, Any], 
        user_location: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check timezone-based restrictions"""
        result = {
            "allowed": True,
            "violations": []
        }
        
        user_timezone = user_location.get("timezone")
        if not user_timezone:
            return result
        
        # Check allowed timezones
        if "allowed_timezones" in timezone_restrictions:
            allowed_timezones = timezone_restrictions["allowed_timezones"]
            if user_timezone not in allowed_timezones:
                result["allowed"] = False
                result["violations"].append(
                    f"Timezone {user_timezone} not in allowed timezones"
                )
        
        # Check blocked timezones
        if "blocked_timezones" in timezone_restrictions:
            blocked_timezones = timezone_restrictions["blocked_timezones"]
            if user_timezone in blocked_timezones:
                result["allowed"] = False
                result["violations"].append(f"Timezone {user_timezone} is blocked")
        
        return result
    
    async def _check_sanctions_restrictions(self, country_code: str) -> Dict[str, Any]:
        """Check sanctions and embargo restrictions"""
        # This would typically integrate with a sanctions database
        # For now, we'll use a static list of commonly sanctioned countries
        sanctioned_countries = [
            "IR",  # Iran
            "KP",  # North Korea
            "SY",  # Syria
            "CU",  # Cuba (partial)
        ]
        
        result = {
            "allowed": True,
            "violations": []
        }
        
        if country_code in sanctioned_countries:
            result["allowed"] = False
            result["violations"].append(
                f"Country {country_code} is under sanctions restrictions"
            )
        
        return result
    
    async def _check_vpn_proxy_detection(self, ip_address: str) -> Dict[str, Any]:
        """Check for VPN/proxy usage (simplified implementation)"""
        # This would typically integrate with a VPN detection service
        # For now, we'll implement basic checks
        
        result = {
            "allowed": True,
            "violations": []
        }
        
        try:
            # Check against known VPN/proxy IP ranges (simplified)
            # In a real implementation, this would use a VPN detection API
            
            ip_obj = ipaddress.ip_address(ip_address)
            
            # Check for common VPN/proxy indicators
            # This is a simplified check - real implementation would be more sophisticated
            if ip_obj.is_private:
                return result  # Don't block private IPs
            
            # Mock VPN detection - in practice, use a service like MaxMind or similar
            geo_info = await self.get_ip_geolocation(ip_address)
            
            # Simple heuristics (replace with actual VPN detection service)
            if geo_info.get("org", "").lower() in ["cloudflare", "amazon", "google", "microsoft"]:
                result["allowed"] = False
                result["violations"].append("VPN/proxy usage detected")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed VPN detection check: {str(e)}")
            return {"allowed": True, "violations": []}  # Allow on error
    
    async def _fetch_ip_geolocation(self, ip_address: str) -> Dict[str, Any]:
        """Fetch IP geolocation from external service"""
        # Mock implementation - replace with actual geolocation service
        # Example services: MaxMind, IPInfo, IPGeolocation, etc.
        
        try:
            # This is a mock response - replace with actual API call
            mock_data = {
                "ip": ip_address,
                "country_code": "US",
                "country_name": "United States",
                "region": "California",
                "city": "San Francisco",
                "latitude": 37.7749,
                "longitude": -122.4194,
                "timezone": "America/Los_Angeles",
                "isp": "Example ISP",
                "org": "Example Organization",
                "as": "AS12345 Example AS"
            }
            
            return mock_data
            
        except Exception as e:
            logger.error(f"Failed to fetch IP geolocation: {str(e)}")
            return {
                "ip": ip_address,
                "error": "Geolocation service unavailable"
            }
    
    async def _validate_geo_blocking_rule(self, rule_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate geo-blocking rule configuration"""
        validation_result = {
            "is_valid": True,
            "errors": []
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
        
        # Validate IP addresses if present
        if "ip_addresses" in rule_config:
            for ip in rule_config["ip_addresses"]:
                try:
                    if "/" in ip:
                        ipaddress.ip_network(ip)
                    else:
                        ipaddress.ip_address(ip)
                except ValueError:
                    validation_result["is_valid"] = False
                    validation_result["errors"].append(f"Invalid IP address or CIDR: {ip}")
        
        return validation_result
    
    async def _log_geographic_access_attempt(
        self,
        license_id: str,
        country_code: str,
        allowed: bool,
        ip_address: Optional[str] = None
    ):
        """Log geographic access attempt for analytics"""
        try:
            # This would typically log to a dedicated access log table
            # For now, we'll create a compliance alert if blocked
            
            if not allowed:
                from ..models.schemas import ComplianceAlertCreate
                from .compliance_service import ComplianceService
                
                alert_data = ComplianceAlertCreate(
                    license_id=license_id,
                    alert_type="geographic_violation",
                    severity="medium",
                    title=f"Geographic Access Blocked: {country_code}",
                    description=f"Access attempt blocked from {country_code}",
                    metadata={
                        "country_code": country_code,
                        "ip_address": ip_address,
                        "blocked_at": datetime.utcnow().isoformat()
                    }
                )
                
                compliance_service = ComplianceService(self.db)
                await compliance_service.create_compliance_alert(
                    alert_data,
                    User(user_id="system", username="geo-blocking", email="system@mams.com")
                )
            
        except Exception as e:
            logger.error(f"Failed to log geographic access attempt: {str(e)}")
            # Don't raise error as this is just logging