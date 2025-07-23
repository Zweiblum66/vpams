"""
Rights Management Service - Usage Restriction Service
"""

import asyncio
from datetime import datetime, date, timedelta, time
from typing import List, Optional, Dict, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.orm import selectinload
import uuid

from ..models.schemas import (
    RightsComplianceCheck, RightsComplianceResult, UsageType, User
)
from ..db.models import License, UsageRecord, ComplianceAlert, RightsParty
from ..core.config import settings
from ..core.exceptions import RestrictionError, ComplianceError
from ..core.logger import get_logger

logger = get_logger(__name__)


class RestrictionService:
    """Service for enforcing usage restrictions and compliance"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def check_usage_restrictions(self, compliance_check: RightsComplianceCheck) -> RightsComplianceResult:
        """Check all usage restrictions for a compliance request"""
        try:
            logger.info(f"Checking usage restrictions for asset {compliance_check.asset_id}")
            
            # Get applicable licenses
            applicable_licenses = await self._get_applicable_licenses(compliance_check)
            
            if not applicable_licenses:
                return RightsComplianceResult(
                    is_compliant=False,
                    applicable_licenses=[],
                    violations=["No applicable licenses found for this asset"],
                    warnings=[],
                    recommendations=["Obtain appropriate license for this usage"]
                )
            
            # Check each license for restrictions
            compliance_results = []
            for license in applicable_licenses:
                license_result = await self._check_license_restrictions(license, compliance_check)
                compliance_results.append((license, license_result))
            
            # Find the most permissive compliant license
            compliant_licenses = [
                (license, result) for license, result in compliance_results 
                if result["is_compliant"]
            ]
            
            if compliant_licenses:
                # Use the license with the highest remaining limits
                best_license, best_result = max(
                    compliant_licenses,
                    key=lambda x: (
                        x[1].get("remaining_usage_count", float('inf')),
                        x[1].get("remaining_duration", float('inf'))
                    )
                )
                
                return RightsComplianceResult(
                    is_compliant=True,
                    applicable_licenses=[best_license.id],
                    violations=[],
                    warnings=best_result.get("warnings", []),
                    recommendations=best_result.get("recommendations", []),
                    remaining_usage_count=best_result.get("remaining_usage_count"),
                    remaining_duration_seconds=best_result.get("remaining_duration"),
                    royalty_due=best_result.get("royalty_due"),
                    minimum_fee=best_result.get("minimum_fee")
                )
            else:
                # Collect all violations and warnings
                all_violations = []
                all_warnings = []
                all_recommendations = []
                
                for license, result in compliance_results:
                    all_violations.extend(result.get("violations", []))
                    all_warnings.extend(result.get("warnings", []))
                    all_recommendations.extend(result.get("recommendations", []))
                
                return RightsComplianceResult(
                    is_compliant=False,
                    applicable_licenses=[license.id for license, _ in compliance_results],
                    violations=list(set(all_violations)),
                    warnings=list(set(all_warnings)),
                    recommendations=list(set(all_recommendations))
                )
            
        except Exception as e:
            logger.error(f"Failed to check usage restrictions: {str(e)}")
            raise RestrictionError(f"Failed to check usage restrictions: {str(e)}")
    
    async def enforce_temporal_restrictions(
        self, 
        license_id: str, 
        requested_datetime: datetime
    ) -> Dict[str, Any]:
        """Check temporal restrictions (time-based, day-of-week, etc.)"""
        try:
            # Get license
            result = await self.db.execute(
                select(License).where(License.id == license_id)
            )
            license = result.scalar_one_or_none()
            
            if not license:
                return {"allowed": False, "reason": "License not found"}
            
            # Check if license has temporal restrictions in metadata
            temporal_restrictions = license.metadata.get("temporal_restrictions", {}) if license.metadata else {}
            
            restrictions_result = {
                "allowed": True,
                "restrictions_checked": [],
                "violations": [],
                "warnings": []
            }
            
            # Check time-of-day restrictions
            if "allowed_hours" in temporal_restrictions:
                allowed_hours = temporal_restrictions["allowed_hours"]
                current_hour = requested_datetime.hour
                
                if isinstance(allowed_hours, dict):
                    start_hour = allowed_hours.get("start", 0)
                    end_hour = allowed_hours.get("end", 23)
                    
                    if not (start_hour <= current_hour <= end_hour):
                        restrictions_result["allowed"] = False
                        restrictions_result["violations"].append(
                            f"Usage not allowed at {current_hour}:00. Allowed hours: {start_hour}:00-{end_hour}:00"
                        )
                
                restrictions_result["restrictions_checked"].append("time_of_day")
            
            # Check day-of-week restrictions
            if "allowed_days" in temporal_restrictions:
                allowed_days = temporal_restrictions["allowed_days"]
                current_day = requested_datetime.strftime("%A").lower()
                
                if isinstance(allowed_days, list) and current_day not in [day.lower() for day in allowed_days]:
                    restrictions_result["allowed"] = False
                    restrictions_result["violations"].append(
                        f"Usage not allowed on {current_day.title()}. Allowed days: {', '.join(allowed_days)}"
                    )
                
                restrictions_result["restrictions_checked"].append("day_of_week")
            
            # Check blackout periods
            if "blackout_periods" in temporal_restrictions:
                blackout_periods = temporal_restrictions["blackout_periods"]
                
                for period in blackout_periods:
                    start_date = datetime.fromisoformat(period["start"]).date()
                    end_date = datetime.fromisoformat(period["end"]).date()
                    
                    if start_date <= requested_datetime.date() <= end_date:
                        restrictions_result["allowed"] = False
                        restrictions_result["violations"].append(
                            f"Usage not allowed during blackout period: {start_date} to {end_date}"
                        )
                
                restrictions_result["restrictions_checked"].append("blackout_periods")
            
            # Check seasonal restrictions
            if "seasonal_restrictions" in temporal_restrictions:
                seasonal = temporal_restrictions["seasonal_restrictions"]
                current_month = requested_datetime.month
                
                if "blocked_months" in seasonal:
                    blocked_months = seasonal["blocked_months"]
                    if current_month in blocked_months:
                        restrictions_result["allowed"] = False
                        restrictions_result["violations"].append(
                            f"Usage not allowed in month {current_month}. Blocked months: {blocked_months}"
                        )
                
                restrictions_result["restrictions_checked"].append("seasonal")
            
            return restrictions_result
            
        except Exception as e:
            logger.error(f"Failed to check temporal restrictions: {str(e)}")
            return {"allowed": False, "reason": f"Error checking restrictions: {str(e)}"}
    
    async def enforce_usage_quotas(
        self, 
        license_id: str, 
        requested_usage_count: int = 1,
        requested_duration: Optional[int] = None
    ) -> Dict[str, Any]:
        """Check usage quotas and limits"""
        try:
            # Get license
            result = await self.db.execute(
                select(License).where(License.id == license_id)
            )
            license = result.scalar_one_or_none()
            
            if not license:
                return {"allowed": False, "reason": "License not found"}
            
            # Get current usage
            usage_result = await self.db.execute(
                select(
                    func.sum(UsageRecord.usage_count).label("total_usage"),
                    func.sum(UsageRecord.duration_seconds).label("total_duration")
                ).where(UsageRecord.license_id == license_id)
            )
            current_usage = usage_result.first()
            
            total_usage_count = current_usage.total_usage or 0
            total_duration = current_usage.total_duration or 0
            
            quota_result = {
                "allowed": True,
                "current_usage_count": total_usage_count,
                "current_duration": total_duration,
                "violations": [],
                "warnings": [],
                "remaining_usage": None,
                "remaining_duration": None
            }
            
            # Check usage count limit
            if license.max_usage_count:
                remaining_usage = license.max_usage_count - total_usage_count
                quota_result["remaining_usage"] = remaining_usage
                
                if total_usage_count + requested_usage_count > license.max_usage_count:
                    quota_result["allowed"] = False
                    quota_result["violations"].append(
                        f"Usage count limit exceeded. Requested: {requested_usage_count}, "
                        f"Remaining: {remaining_usage}, Limit: {license.max_usage_count}"
                    )
                elif remaining_usage <= license.max_usage_count * 0.1:  # 10% warning
                    quota_result["warnings"].append(
                        f"Usage count approaching limit. Remaining: {remaining_usage} of {license.max_usage_count}"
                    )
            
            # Check duration limit
            if license.max_duration_seconds and requested_duration:
                remaining_duration = license.max_duration_seconds - total_duration
                quota_result["remaining_duration"] = remaining_duration
                
                if total_duration + requested_duration > license.max_duration_seconds:
                    quota_result["allowed"] = False
                    quota_result["violations"].append(
                        f"Duration limit exceeded. Requested: {requested_duration}s, "
                        f"Remaining: {remaining_duration}s, Limit: {license.max_duration_seconds}s"
                    )
                elif remaining_duration <= license.max_duration_seconds * 0.1:  # 10% warning
                    quota_result["warnings"].append(
                        f"Duration approaching limit. Remaining: {remaining_duration}s of {license.max_duration_seconds}s"
                    )
            
            # Check custom quotas from metadata
            custom_quotas = license.metadata.get("custom_quotas", {}) if license.metadata else {}
            
            for quota_type, quota_config in custom_quotas.items():
                if quota_type == "daily_limit":
                    daily_allowed = await self._check_daily_quota(license_id, quota_config, requested_usage_count)
                    if not daily_allowed["allowed"]:
                        quota_result["allowed"] = False
                        quota_result["violations"].extend(daily_allowed["violations"])
                
                elif quota_type == "monthly_limit":
                    monthly_allowed = await self._check_monthly_quota(license_id, quota_config, requested_usage_count)
                    if not monthly_allowed["allowed"]:
                        quota_result["allowed"] = False
                        quota_result["violations"].extend(monthly_allowed["violations"])
            
            return quota_result
            
        except Exception as e:
            logger.error(f"Failed to check usage quotas: {str(e)}")
            return {"allowed": False, "reason": f"Error checking quotas: {str(e)}"}
    
    async def enforce_geographic_restrictions(
        self, 
        license_id: str, 
        requested_country: str,
        requested_region: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check geographic restrictions"""
        try:
            # Get license
            result = await self.db.execute(
                select(License).where(License.id == license_id)
            )
            license = result.scalar_one_or_none()
            
            if not license:
                return {"allowed": False, "reason": "License not found"}
            
            geo_result = {
                "allowed": True,
                "violations": [],
                "warnings": [],
                "geographic_scope": license.geographic_scope
            }
            
            # Check basic geographic scope
            if license.geographic_scope == "worldwide":
                geo_result["allowed"] = True
            
            elif license.geographic_scope == "country_specific":
                if not license.countries or requested_country not in license.countries:
                    geo_result["allowed"] = False
                    geo_result["violations"].append(
                        f"Usage not permitted in {requested_country}. "
                        f"Allowed countries: {', '.join(license.countries or [])}"
                    )
            
            elif license.geographic_scope == "region_specific":
                # Check regional restrictions from metadata
                regional_restrictions = license.metadata.get("regional_restrictions", {}) if license.metadata else {}
                
                if "allowed_regions" in regional_restrictions:
                    allowed_regions = regional_restrictions["allowed_regions"]
                    if requested_region and requested_region not in allowed_regions:
                        geo_result["allowed"] = False
                        geo_result["violations"].append(
                            f"Usage not permitted in region {requested_region}. "
                            f"Allowed regions: {', '.join(allowed_regions)}"
                        )
                
                if "blocked_countries" in regional_restrictions:
                    blocked_countries = regional_restrictions["blocked_countries"]
                    if requested_country in blocked_countries:
                        geo_result["allowed"] = False
                        geo_result["violations"].append(
                            f"Usage specifically blocked in {requested_country}"
                        )
            
            # Check IP-based restrictions if configured
            ip_restrictions = license.metadata.get("ip_restrictions", {}) if license.metadata else {}
            if ip_restrictions:
                geo_result["warnings"].append("IP-based restrictions require runtime verification")
            
            # Check embargo/sanctions restrictions
            embargo_restrictions = license.metadata.get("embargo_restrictions", {}) if license.metadata else {}
            if "embargoed_countries" in embargo_restrictions:
                embargoed_countries = embargo_restrictions["embargoed_countries"]
                if requested_country in embargoed_countries:
                    geo_result["allowed"] = False
                    geo_result["violations"].append(
                        f"Usage blocked due to embargo restrictions in {requested_country}"
                    )
            
            return geo_result
            
        except Exception as e:
            logger.error(f"Failed to check geographic restrictions: {str(e)}")
            return {"allowed": False, "reason": f"Error checking geographic restrictions: {str(e)}"}
    
    async def enforce_platform_restrictions(
        self, 
        license_id: str, 
        requested_platform: str,
        platform_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Check platform-specific restrictions"""
        try:
            # Get license
            result = await self.db.execute(
                select(License).where(License.id == license_id)
            )
            license = result.scalar_one_or_none()
            
            if not license:
                return {"allowed": False, "reason": "License not found"}
            
            platform_restrictions = license.metadata.get("platform_restrictions", {}) if license.metadata else {}
            
            platform_result = {
                "allowed": True,
                "violations": [],
                "warnings": [],
                "platform_scope": platform_restrictions.get("scope", "unrestricted")
            }
            
            # Check allowed platforms
            if "allowed_platforms" in platform_restrictions:
                allowed_platforms = platform_restrictions["allowed_platforms"]
                if requested_platform not in allowed_platforms:
                    platform_result["allowed"] = False
                    platform_result["violations"].append(
                        f"Usage not permitted on platform {requested_platform}. "
                        f"Allowed platforms: {', '.join(allowed_platforms)}"
                    )
            
            # Check blocked platforms
            if "blocked_platforms" in platform_restrictions:
                blocked_platforms = platform_restrictions["blocked_platforms"]
                if requested_platform in blocked_platforms:
                    platform_result["allowed"] = False
                    platform_result["violations"].append(
                        f"Usage specifically blocked on platform {requested_platform}"
                    )
            
            # Check platform-specific quotas
            if "platform_quotas" in platform_restrictions:
                platform_quotas = platform_restrictions["platform_quotas"]
                if requested_platform in platform_quotas:
                    quota_config = platform_quotas[requested_platform]
                    quota_check = await self._check_platform_quota(license_id, requested_platform, quota_config)
                    if not quota_check["allowed"]:
                        platform_result["allowed"] = False
                        platform_result["violations"].extend(quota_check["violations"])
                    platform_result["warnings"].extend(quota_check.get("warnings", []))
            
            # Check content delivery restrictions
            if "delivery_restrictions" in platform_restrictions:
                delivery_restrictions = platform_restrictions["delivery_restrictions"]
                
                # Check quality restrictions
                if platform_metadata and "quality" in delivery_restrictions:
                    max_quality = delivery_restrictions["quality"].get("max_resolution")
                    requested_quality = platform_metadata.get("resolution")
                    
                    if max_quality and requested_quality:
                        if self._compare_quality(requested_quality, max_quality) > 0:
                            platform_result["allowed"] = False
                            platform_result["violations"].append(
                                f"Requested quality {requested_quality} exceeds maximum allowed {max_quality}"
                            )
                
                # Check bitrate restrictions
                if platform_metadata and "bitrate" in delivery_restrictions:
                    max_bitrate = delivery_restrictions["bitrate"].get("max_bitrate_kbps")
                    requested_bitrate = platform_metadata.get("bitrate_kbps")
                    
                    if max_bitrate and requested_bitrate and requested_bitrate > max_bitrate:
                        platform_result["allowed"] = False
                        platform_result["violations"].append(
                            f"Requested bitrate {requested_bitrate} kbps exceeds maximum allowed {max_bitrate} kbps"
                        )
            
            return platform_result
            
        except Exception as e:
            logger.error(f"Failed to check platform restrictions: {str(e)}")
            return {"allowed": False, "reason": f"Error checking platform restrictions: {str(e)}"}
    
    async def check_content_restrictions(
        self, 
        license_id: str, 
        content_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check content-specific restrictions (rating, genre, etc.)"""
        try:
            # Get license
            result = await self.db.execute(
                select(License).where(License.id == license_id)
            )
            license = result.scalar_one_or_none()
            
            if not license:
                return {"allowed": False, "reason": "License not found"}
            
            content_restrictions = license.metadata.get("content_restrictions", {}) if license.metadata else {}
            
            content_result = {
                "allowed": True,
                "violations": [],
                "warnings": []
            }
            
            # Check content rating restrictions
            if "allowed_ratings" in content_restrictions:
                allowed_ratings = content_restrictions["allowed_ratings"]
                content_rating = content_metadata.get("rating")
                
                if content_rating and content_rating not in allowed_ratings:
                    content_result["allowed"] = False
                    content_result["violations"].append(
                        f"Content rating {content_rating} not permitted. "
                        f"Allowed ratings: {', '.join(allowed_ratings)}"
                    )
            
            # Check genre restrictions
            if "allowed_genres" in content_restrictions:
                allowed_genres = content_restrictions["allowed_genres"]
                content_genres = content_metadata.get("genres", [])
                
                if content_genres and not any(genre in allowed_genres for genre in content_genres):
                    content_result["allowed"] = False
                    content_result["violations"].append(
                        f"Content genres {content_genres} not permitted. "
                        f"Allowed genres: {', '.join(allowed_genres)}"
                    )
            
            # Check language restrictions
            if "allowed_languages" in content_restrictions:
                allowed_languages = content_restrictions["allowed_languages"]
                content_language = content_metadata.get("language")
                
                if content_language and content_language not in allowed_languages:
                    content_result["allowed"] = False
                    content_result["violations"].append(
                        f"Content language {content_language} not permitted. "
                        f"Allowed languages: {', '.join(allowed_languages)}"
                    )
            
            # Check content length restrictions
            if "duration_limits" in content_restrictions:
                duration_limits = content_restrictions["duration_limits"]
                content_duration = content_metadata.get("duration_seconds")
                
                if content_duration:
                    min_duration = duration_limits.get("min_seconds")
                    max_duration = duration_limits.get("max_seconds")
                    
                    if min_duration and content_duration < min_duration:
                        content_result["allowed"] = False
                        content_result["violations"].append(
                            f"Content duration {content_duration}s below minimum {min_duration}s"
                        )
                    
                    if max_duration and content_duration > max_duration:
                        content_result["allowed"] = False
                        content_result["violations"].append(
                            f"Content duration {content_duration}s exceeds maximum {max_duration}s"
                        )
            
            return content_result
            
        except Exception as e:
            logger.error(f"Failed to check content restrictions: {str(e)}")
            return {"allowed": False, "reason": f"Error checking content restrictions: {str(e)}"}
    
    # Private helper methods
    async def _get_applicable_licenses(self, compliance_check: RightsComplianceCheck) -> List[License]:
        """Get applicable licenses for a compliance check"""
        try:
            query = select(License).where(
                and_(
                    License.asset_id == compliance_check.asset_id,
                    License.status == "active",
                    License.start_date <= compliance_check.usage_date.date(),
                    or_(
                        License.end_date.is_(None),
                        License.end_date >= compliance_check.usage_date.date()
                    )
                )
            )
            
            result = await self.db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Failed to get applicable licenses: {str(e)}")
            return []
    
    async def _check_license_restrictions(
        self, 
        license: License, 
        compliance_check: RightsComplianceCheck
    ) -> Dict[str, Any]:
        """Check all restrictions for a specific license"""
        try:
            result = {
                "is_compliant": True,
                "violations": [],
                "warnings": [],
                "recommendations": []
            }
            
            # Check temporal restrictions
            temporal_check = await self.enforce_temporal_restrictions(
                license.id, 
                compliance_check.usage_date
            )
            if not temporal_check["allowed"]:
                result["is_compliant"] = False
                result["violations"].extend(temporal_check.get("violations", []))
            result["warnings"].extend(temporal_check.get("warnings", []))
            
            # Check usage quotas
            quota_check = await self.enforce_usage_quotas(
                license.id,
                1,  # Default usage count
                compliance_check.duration_seconds
            )
            if not quota_check["allowed"]:
                result["is_compliant"] = False
                result["violations"].extend(quota_check.get("violations", []))
            result["warnings"].extend(quota_check.get("warnings", []))
            result["remaining_usage_count"] = quota_check.get("remaining_usage")
            result["remaining_duration"] = quota_check.get("remaining_duration")
            
            # Check geographic restrictions
            if compliance_check.country:
                geo_check = await self.enforce_geographic_restrictions(
                    license.id,
                    compliance_check.country
                )
                if not geo_check["allowed"]:
                    result["is_compliant"] = False
                    result["violations"].extend(geo_check.get("violations", []))
                result["warnings"].extend(geo_check.get("warnings", []))
            
            # Check platform restrictions
            if compliance_check.platform:
                platform_check = await self.enforce_platform_restrictions(
                    license.id,
                    compliance_check.platform
                )
                if not platform_check["allowed"]:
                    result["is_compliant"] = False
                    result["violations"].extend(platform_check.get("violations", []))
                result["warnings"].extend(platform_check.get("warnings", []))
            
            # Calculate financial implications
            if license.royalty_rate and hasattr(compliance_check, 'revenue_generated'):
                revenue = getattr(compliance_check, 'revenue_generated', 0) or 0
                result["royalty_due"] = revenue * (license.royalty_rate / 100)
            
            if license.license_fee:
                result["minimum_fee"] = license.license_fee
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to check license restrictions: {str(e)}")
            return {
                "is_compliant": False,
                "violations": [f"Error checking restrictions: {str(e)}"],
                "warnings": [],
                "recommendations": []
            }
    
    async def _check_daily_quota(self, license_id: str, quota_config: Dict, requested_count: int) -> Dict[str, Any]:
        """Check daily usage quota"""
        try:
            today = date.today()
            
            # Get today's usage
            result = await self.db.execute(
                select(func.sum(UsageRecord.usage_count)).where(
                    and_(
                        UsageRecord.license_id == license_id,
                        func.date(UsageRecord.usage_date) == today
                    )
                )
            )
            today_usage = result.scalar() or 0
            
            daily_limit = quota_config.get("limit", 0)
            
            if today_usage + requested_count > daily_limit:
                return {
                    "allowed": False,
                    "violations": [
                        f"Daily usage limit exceeded. Used today: {today_usage}, "
                        f"Requested: {requested_count}, Daily limit: {daily_limit}"
                    ]
                }
            
            return {"allowed": True, "violations": []}
            
        except Exception as e:
            logger.error(f"Failed to check daily quota: {str(e)}")
            return {"allowed": False, "violations": [f"Error checking daily quota: {str(e)}"]}
    
    async def _check_monthly_quota(self, license_id: str, quota_config: Dict, requested_count: int) -> Dict[str, Any]:
        """Check monthly usage quota"""
        try:
            today = date.today()
            month_start = today.replace(day=1)
            
            # Get this month's usage
            result = await self.db.execute(
                select(func.sum(UsageRecord.usage_count)).where(
                    and_(
                        UsageRecord.license_id == license_id,
                        func.date(UsageRecord.usage_date) >= month_start
                    )
                )
            )
            month_usage = result.scalar() or 0
            
            monthly_limit = quota_config.get("limit", 0)
            
            if month_usage + requested_count > monthly_limit:
                return {
                    "allowed": False,
                    "violations": [
                        f"Monthly usage limit exceeded. Used this month: {month_usage}, "
                        f"Requested: {requested_count}, Monthly limit: {monthly_limit}"
                    ]
                }
            
            return {"allowed": True, "violations": []}
            
        except Exception as e:
            logger.error(f"Failed to check monthly quota: {str(e)}")
            return {"allowed": False, "violations": [f"Error checking monthly quota: {str(e)}"]}
    
    async def _check_platform_quota(
        self, 
        license_id: str, 
        platform: str, 
        quota_config: Dict
    ) -> Dict[str, Any]:
        """Check platform-specific quota"""
        try:
            # Get platform usage for this license
            result = await self.db.execute(
                select(func.sum(UsageRecord.usage_count)).where(
                    and_(
                        UsageRecord.license_id == license_id,
                        UsageRecord.platform == platform
                    )
                )
            )
            platform_usage = result.scalar() or 0
            
            platform_limit = quota_config.get("limit", 0)
            
            if platform_usage >= platform_limit:
                return {
                    "allowed": False,
                    "violations": [
                        f"Platform usage limit exceeded for {platform}. "
                        f"Used: {platform_usage}, Limit: {platform_limit}"
                    ]
                }
            
            warnings = []
            if platform_usage >= platform_limit * 0.8:  # 80% warning
                warnings.append(
                    f"Platform usage approaching limit for {platform}. "
                    f"Used: {platform_usage} of {platform_limit}"
                )
            
            return {"allowed": True, "violations": [], "warnings": warnings}
            
        except Exception as e:
            logger.error(f"Failed to check platform quota: {str(e)}")
            return {"allowed": False, "violations": [f"Error checking platform quota: {str(e)}"]}
    
    def _compare_quality(self, requested: str, max_allowed: str) -> int:
        """Compare video quality levels. Returns >0 if requested > max_allowed"""
        quality_levels = {
            "240p": 1, "360p": 2, "480p": 3, "720p": 4, 
            "1080p": 5, "1440p": 6, "4k": 7, "8k": 8
        }
        
        requested_level = quality_levels.get(requested.lower(), 0)
        max_level = quality_levels.get(max_allowed.lower(), 0)
        
        return requested_level - max_level