"""
Rights Management Service - Compliance Service
"""

import asyncio
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.orm import selectinload
import uuid

from ..models.schemas import (
    RightsComplianceCheck, RightsComplianceResult,
    ComplianceAlertCreate, ComplianceAlertUpdate, ComplianceAlertResponse,
    PaginatedResponse, User, UsageType
)
from ..db.models import License, UsageRecord, ComplianceAlert, RightsParty
from ..core.config import settings
from ..core.exceptions import ComplianceError, ValidationError
from ..core.logger import get_logger

logger = get_logger(__name__)


class ComplianceService:
    """Service for managing rights compliance and alerts"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def check_compliance(self, compliance_check: RightsComplianceCheck) -> RightsComplianceResult:
        """Check compliance for a specific usage"""
        try:
            logger.info(f"Checking compliance for asset {compliance_check.asset_id}")
            
            # Get applicable licenses for the asset
            applicable_licenses = await self._get_applicable_licenses(compliance_check)
            
            # Initialize result
            result = RightsComplianceResult(
                is_compliant=False,
                applicable_licenses=[],
                violations=[],
                warnings=[],
                recommendations=[]
            )
            
            if not applicable_licenses:
                result.violations.append("No applicable licenses found for this asset")
                return result
            
            # Check each license for compliance
            compliant_licenses = []
            for license in applicable_licenses:
                license_compliance = await self._check_license_compliance(license, compliance_check)
                
                if license_compliance["is_compliant"]:
                    compliant_licenses.append(license)
                    result.applicable_licenses.append(license.id)
                else:
                    result.violations.extend(license_compliance["violations"])
                    result.warnings.extend(license_compliance["warnings"])
            
            # Overall compliance
            result.is_compliant = len(compliant_licenses) > 0
            
            if result.is_compliant:
                # Calculate usage limits and royalties
                await self._calculate_usage_limits(result, compliant_licenses, compliance_check)
                await self._calculate_royalties(result, compliant_licenses, compliance_check)
            else:
                result.recommendations.append("Obtain appropriate license for this usage")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to check compliance: {str(e)}")
            raise ComplianceError(f"Failed to check compliance: {str(e)}")
    
    async def create_compliance_alert(
        self, 
        alert_data: ComplianceAlertCreate, 
        user: User
    ) -> ComplianceAlertResponse:
        """Create a new compliance alert"""
        try:
            alert = ComplianceAlert(**alert_data.dict())
            
            self.db.add(alert)
            await self.db.commit()
            await self.db.refresh(alert)
            
            # Load relationships
            if alert.license_id:
                await self.db.refresh(alert, ["license"])
            
            logger.info(f"Created compliance alert: {alert.id}")
            return ComplianceAlertResponse.from_orm(alert)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create compliance alert: {str(e)}")
            raise ComplianceError(f"Failed to create compliance alert: {str(e)}")
    
    async def get_compliance_alerts(
        self, 
        page: int = 1, 
        limit: int = 20,
        severity: Optional[str] = None,
        is_resolved: Optional[bool] = None,
        alert_type: Optional[str] = None
    ) -> PaginatedResponse:
        """Get compliance alerts with pagination and filtering"""
        try:
            query = select(ComplianceAlert).options(
                selectinload(ComplianceAlert.license)
            )
            
            # Apply filters
            if severity:
                query = query.where(ComplianceAlert.severity == severity)
            
            if is_resolved is not None:
                query = query.where(ComplianceAlert.is_resolved == is_resolved)
            
            if alert_type:
                query = query.where(ComplianceAlert.alert_type == alert_type)
            
            # Get total count
            count_query = select(func.count(ComplianceAlert.id)).select_from(query.subquery())
            total_result = await self.db.execute(count_query)
            total = total_result.scalar()
            
            # Apply pagination and ordering
            offset = (page - 1) * limit
            query = query.order_by(desc(ComplianceAlert.created_at)).offset(offset).limit(limit)
            
            result = await self.db.execute(query)
            alerts = result.scalars().all()
            
            return PaginatedResponse(
                items=[ComplianceAlertResponse.from_orm(alert) for alert in alerts],
                total=total,
                page=page,
                limit=limit,
                pages=(total + limit - 1) // limit
            )
            
        except Exception as e:
            logger.error(f"Failed to get compliance alerts: {str(e)}")
            raise ComplianceError(f"Failed to get compliance alerts: {str(e)}")
    
    async def resolve_alert(self, alert_id: str, resolution_notes: str, user: User) -> bool:
        """Resolve a compliance alert"""
        try:
            result = await self.db.execute(
                select(ComplianceAlert).where(ComplianceAlert.id == alert_id)
            )
            alert = result.scalar_one_or_none()
            
            if not alert:
                return False
            
            alert.is_resolved = True
            alert.resolved_at = datetime.utcnow()
            alert.resolved_by = user.user_id
            alert.resolution_notes = resolution_notes
            
            await self.db.commit()
            
            logger.info(f"Resolved compliance alert: {alert_id}")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to resolve compliance alert: {str(e)}")
            raise ComplianceError(f"Failed to resolve compliance alert: {str(e)}")
    
    async def check_license_expiration(self, days_ahead: int = 30) -> List[ComplianceAlertResponse]:
        """Check for licenses expiring soon"""
        try:
            cutoff_date = date.today() + timedelta(days=days_ahead)
            
            # Get licenses expiring soon
            result = await self.db.execute(
                select(License)
                .options(
                    selectinload(License.licensor),
                    selectinload(License.licensee)
                )
                .where(
                    and_(
                        License.end_date <= cutoff_date,
                        License.end_date >= date.today(),
                        License.status == "active"
                    )
                )
            )
            licenses = result.scalars().all()
            
            alerts = []
            for license in licenses:
                days_until_expiry = (license.end_date - date.today()).days
                
                # Determine severity based on days until expiry
                if days_until_expiry <= 7:
                    severity = "critical"
                elif days_until_expiry <= 14:
                    severity = "high"
                else:
                    severity = "medium"
                
                # Check if alert already exists
                existing_alert = await self.db.execute(
                    select(ComplianceAlert).where(
                        and_(
                            ComplianceAlert.license_id == license.id,
                            ComplianceAlert.alert_type == "license_expiration",
                            ComplianceAlert.is_resolved == False
                        )
                    )
                )
                
                if existing_alert.scalar_one_or_none():
                    continue
                
                # Create new alert
                alert_data = ComplianceAlertCreate(
                    license_id=license.id,
                    alert_type="license_expiration",
                    severity=severity,
                    title=f"License Expiring Soon: {license.license_number}",
                    description=f"License '{license.title}' expires in {days_until_expiry} days on {license.end_date}",
                    metadata={
                        "license_number": license.license_number,
                        "expiry_date": license.end_date.isoformat(),
                        "days_until_expiry": days_until_expiry
                    }
                )
                
                # Create alert (simplified for batch processing)
                alert = ComplianceAlert(**alert_data.dict())
                self.db.add(alert)
                
                alerts.append(ComplianceAlertResponse.from_orm(alert))
            
            await self.db.commit()
            
            logger.info(f"Created {len(alerts)} expiration alerts")
            return alerts
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to check license expiration: {str(e)}")
            raise ComplianceError(f"Failed to check license expiration: {str(e)}")
    
    async def check_usage_limits(self, license_id: str) -> List[ComplianceAlertResponse]:
        """Check usage limits for a license"""
        try:
            # Get license with usage records
            license_result = await self.db.execute(
                select(License).where(License.id == license_id)
            )
            license = license_result.scalar_one_or_none()
            
            if not license:
                return []
            
            # Get usage records for this license
            usage_result = await self.db.execute(
                select(UsageRecord).where(UsageRecord.license_id == license_id)
            )
            usage_records = usage_result.scalars().all()
            
            alerts = []
            
            # Check usage count limit
            if license.max_usage_count:
                total_usage = sum(record.usage_count for record in usage_records)
                remaining_usage = license.max_usage_count - total_usage
                
                if remaining_usage <= 0:
                    # Usage limit exceeded
                    alert_data = ComplianceAlertCreate(
                        license_id=license_id,
                        alert_type="usage_limit_exceeded",
                        severity="critical",
                        title=f"Usage Limit Exceeded: {license.license_number}",
                        description=f"Usage count limit of {license.max_usage_count} has been exceeded. Total usage: {total_usage}",
                        metadata={
                            "license_number": license.license_number,
                            "max_usage_count": license.max_usage_count,
                            "total_usage": total_usage
                        }
                    )
                    
                    alert = ComplianceAlert(**alert_data.dict())
                    self.db.add(alert)
                    alerts.append(ComplianceAlertResponse.from_orm(alert))
                    
                elif remaining_usage <= license.max_usage_count * 0.1:  # 10% remaining
                    # Usage limit warning
                    alert_data = ComplianceAlertCreate(
                        license_id=license_id,
                        alert_type="usage_limit_warning",
                        severity="high",
                        title=f"Usage Limit Warning: {license.license_number}",
                        description=f"Usage count is approaching limit. Remaining: {remaining_usage} of {license.max_usage_count}",
                        metadata={
                            "license_number": license.license_number,
                            "max_usage_count": license.max_usage_count,
                            "remaining_usage": remaining_usage
                        }
                    )
                    
                    alert = ComplianceAlert(**alert_data.dict())
                    self.db.add(alert)
                    alerts.append(ComplianceAlertResponse.from_orm(alert))
            
            # Check duration limit
            if license.max_duration_seconds:
                total_duration = sum(record.duration_seconds or 0 for record in usage_records)
                remaining_duration = license.max_duration_seconds - total_duration
                
                if remaining_duration <= 0:
                    # Duration limit exceeded
                    alert_data = ComplianceAlertCreate(
                        license_id=license_id,
                        alert_type="duration_limit_exceeded",
                        severity="critical",
                        title=f"Duration Limit Exceeded: {license.license_number}",
                        description=f"Duration limit of {license.max_duration_seconds} seconds has been exceeded. Total duration: {total_duration} seconds",
                        metadata={
                            "license_number": license.license_number,
                            "max_duration_seconds": license.max_duration_seconds,
                            "total_duration": total_duration
                        }
                    )
                    
                    alert = ComplianceAlert(**alert_data.dict())
                    self.db.add(alert)
                    alerts.append(ComplianceAlertResponse.from_orm(alert))
            
            await self.db.commit()
            
            logger.info(f"Created {len(alerts)} usage limit alerts for license {license_id}")
            return alerts
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to check usage limits: {str(e)}")
            raise ComplianceError(f"Failed to check usage limits: {str(e)}")
    
    async def check_geographic_restrictions(
        self, 
        license_id: str, 
        country: str
    ) -> RightsComplianceResult:
        """Check geographic restrictions for a license"""
        try:
            license_result = await self.db.execute(
                select(License).where(License.id == license_id)
            )
            license = license_result.scalar_one_or_none()
            
            if not license:
                return RightsComplianceResult(
                    is_compliant=False,
                    applicable_licenses=[],
                    violations=["License not found"],
                    warnings=[],
                    recommendations=[]
                )
            
            result = RightsComplianceResult(
                is_compliant=True,
                applicable_licenses=[license_id],
                violations=[],
                warnings=[],
                recommendations=[]
            )
            
            # Check geographic scope
            if license.geographic_scope == "worldwide":
                result.is_compliant = True
            elif license.geographic_scope == "country_specific":
                if not license.countries or country not in license.countries:
                    result.is_compliant = False
                    result.violations.append(f"Usage not permitted in {country}")
            elif license.geographic_scope == "region_specific":
                # Would need region mapping logic
                result.warnings.append("Region-specific restrictions need manual verification")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to check geographic restrictions: {str(e)}")
            raise ComplianceError(f"Failed to check geographic restrictions: {str(e)}")
    
    async def generate_compliance_report(
        self, 
        start_date: date, 
        end_date: date
    ) -> Dict[str, Any]:
        """Generate compliance report for a date range"""
        try:
            # Get compliance statistics
            alerts_result = await self.db.execute(
                select(ComplianceAlert).where(
                    and_(
                        ComplianceAlert.created_at >= start_date,
                        ComplianceAlert.created_at <= end_date + timedelta(days=1)
                    )
                )
            )
            alerts = alerts_result.scalars().all()
            
            # Group by severity
            severity_counts = {}
            alert_type_counts = {}
            resolved_count = 0
            
            for alert in alerts:
                severity_counts[alert.severity] = severity_counts.get(alert.severity, 0) + 1
                alert_type_counts[alert.alert_type] = alert_type_counts.get(alert.alert_type, 0) + 1
                
                if alert.is_resolved:
                    resolved_count += 1
            
            # Get license statistics
            licenses_result = await self.db.execute(
                select(License).where(
                    and_(
                        License.created_at >= start_date,
                        License.created_at <= end_date + timedelta(days=1)
                    )
                )
            )
            licenses = licenses_result.scalars().all()
            
            # Get usage statistics
            usage_result = await self.db.execute(
                select(UsageRecord).where(
                    and_(
                        UsageRecord.usage_date >= start_date,
                        UsageRecord.usage_date <= end_date + timedelta(days=1)
                    )
                )
            )
            usage_records = usage_result.scalars().all()
            
            report = {
                "report_period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "compliance_alerts": {
                    "total": len(alerts),
                    "resolved": resolved_count,
                    "unresolved": len(alerts) - resolved_count,
                    "by_severity": severity_counts,
                    "by_type": alert_type_counts,
                    "resolution_rate": (resolved_count / len(alerts) * 100) if alerts else 0
                },
                "licenses": {
                    "total": len(licenses),
                    "active": len([l for l in licenses if l.status == "active"]),
                    "expired": len([l for l in licenses if l.status == "expired"]),
                    "expiring_soon": len([l for l in licenses if l.end_date and l.end_date <= date.today() + timedelta(days=30)])
                },
                "usage": {
                    "total_records": len(usage_records),
                    "total_usage_count": sum(r.usage_count for r in usage_records),
                    "total_duration": sum(r.duration_seconds or 0 for r in usage_records),
                    "total_revenue": sum(r.revenue_generated or 0 for r in usage_records)
                }
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate compliance report: {str(e)}")
            raise ComplianceError(f"Failed to generate compliance report: {str(e)}")
    
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
    
    async def _check_license_compliance(
        self, 
        license: License, 
        compliance_check: RightsComplianceCheck
    ) -> Dict[str, Any]:
        """Check compliance for a specific license"""
        try:
            result = {
                "is_compliant": True,
                "violations": [],
                "warnings": []
            }
            
            # Check usage type
            if hasattr(license, 'usage_types') and license.usage_types:
                allowed_usage_types = [ut.id for ut in license.usage_types]
                if compliance_check.usage_type.value not in allowed_usage_types:
                    result["is_compliant"] = False
                    result["violations"].append(f"Usage type '{compliance_check.usage_type.value}' not permitted")
            
            # Check geographic restrictions
            if compliance_check.country:
                if license.geographic_scope == "country_specific":
                    if not license.countries or compliance_check.country not in license.countries:
                        result["is_compliant"] = False
                        result["violations"].append(f"Usage not permitted in {compliance_check.country}")
            
            # Check usage limits
            usage_count = await self.db.execute(
                select(func.sum(UsageRecord.usage_count)).where(
                    UsageRecord.license_id == license.id
                )
            )
            total_usage = usage_count.scalar() or 0
            
            if license.max_usage_count and total_usage >= license.max_usage_count:
                result["is_compliant"] = False
                result["violations"].append("Usage count limit exceeded")
            
            # Check duration limits
            if license.max_duration_seconds and compliance_check.duration_seconds:
                duration_sum = await self.db.execute(
                    select(func.sum(UsageRecord.duration_seconds)).where(
                        UsageRecord.license_id == license.id
                    )
                )
                total_duration = duration_sum.scalar() or 0
                
                if total_duration + compliance_check.duration_seconds > license.max_duration_seconds:
                    result["is_compliant"] = False
                    result["violations"].append("Duration limit would be exceeded")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to check license compliance: {str(e)}")
            return {
                "is_compliant": False,
                "violations": ["Error checking compliance"],
                "warnings": []
            }
    
    async def _calculate_usage_limits(
        self, 
        result: RightsComplianceResult, 
        licenses: List[License], 
        compliance_check: RightsComplianceCheck
    ):
        """Calculate remaining usage limits"""
        try:
            # Find the most restrictive limits
            min_usage_count = None
            min_duration = None
            
            for license in licenses:
                if license.max_usage_count:
                    # Get current usage
                    usage_count = await self.db.execute(
                        select(func.sum(UsageRecord.usage_count)).where(
                            UsageRecord.license_id == license.id
                        )
                    )
                    current_usage = usage_count.scalar() or 0
                    remaining = license.max_usage_count - current_usage
                    
                    if min_usage_count is None or remaining < min_usage_count:
                        min_usage_count = remaining
                
                if license.max_duration_seconds:
                    # Get current duration
                    duration_sum = await self.db.execute(
                        select(func.sum(UsageRecord.duration_seconds)).where(
                            UsageRecord.license_id == license.id
                        )
                    )
                    current_duration = duration_sum.scalar() or 0
                    remaining = license.max_duration_seconds - current_duration
                    
                    if min_duration is None or remaining < min_duration:
                        min_duration = remaining
            
            result.remaining_usage_count = min_usage_count
            result.remaining_duration_seconds = min_duration
            
        except Exception as e:
            logger.error(f"Failed to calculate usage limits: {str(e)}")
    
    async def _calculate_royalties(
        self, 
        result: RightsComplianceResult, 
        licenses: List[License], 
        compliance_check: RightsComplianceCheck
    ):
        """Calculate royalty due"""
        try:
            total_royalty = 0
            min_fee = None
            
            for license in licenses:
                if license.royalty_rate and hasattr(compliance_check, 'revenue_generated'):
                    revenue = getattr(compliance_check, 'revenue_generated', 0) or 0
                    royalty = revenue * (license.royalty_rate / 100)
                    total_royalty += royalty
                
                if license.license_fee:
                    if min_fee is None or license.license_fee < min_fee:
                        min_fee = license.license_fee
            
            result.royalty_due = total_royalty if total_royalty > 0 else None
            result.minimum_fee = min_fee
            
        except Exception as e:
            logger.error(f"Failed to calculate royalties: {str(e)}")