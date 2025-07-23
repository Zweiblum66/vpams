"""
Rights Management Service - Monitoring Service
"""

import asyncio
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.orm import selectinload
import uuid

from ..models.schemas import (
    ComplianceAlertCreate, ComplianceAlertResponse, User
)
from ..db.models import License, UsageRecord, ComplianceAlert, RightsParty
from ..core.config import settings
from ..core.exceptions import MonitoringError
from ..core.logger import get_logger
from .compliance_service import ComplianceService

logger = get_logger(__name__)


class MonitoringService:
    """Service for monitoring rights compliance and generating alerts"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.compliance_service = ComplianceService(db)
    
    async def monitor_license_expirations(self, days_ahead: int = 30) -> List[ComplianceAlertResponse]:
        """Monitor for licenses expiring soon"""
        try:
            logger.info(f"Monitoring license expirations for next {days_ahead} days")
            
            cutoff_date = date.today() + timedelta(days=days_ahead)
            warning_date = date.today() + timedelta(days=7)
            critical_date = date.today() + timedelta(days=3)
            
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
            
            alerts_created = []
            
            for license in licenses:
                days_until_expiry = (license.end_date - date.today()).days
                
                # Determine severity and alert type
                if days_until_expiry <= 0:
                    severity = "critical"
                    alert_type = "license_expired"
                    title = f"License Expired: {license.license_number}"
                    description = f"License '{license.title}' expired on {license.end_date}"
                elif days_until_expiry <= 3:
                    severity = "critical"
                    alert_type = "license_expiring_critical"
                    title = f"License Expiring Critical: {license.license_number}"
                    description = f"License '{license.title}' expires in {days_until_expiry} days on {license.end_date}"
                elif days_until_expiry <= 7:
                    severity = "high"
                    alert_type = "license_expiring_soon"
                    title = f"License Expiring Soon: {license.license_number}"
                    description = f"License '{license.title}' expires in {days_until_expiry} days on {license.end_date}"
                else:
                    severity = "medium"
                    alert_type = "license_expiring_warning"
                    title = f"License Expiring Warning: {license.license_number}"
                    description = f"License '{license.title}' expires in {days_until_expiry} days on {license.end_date}"
                
                # Check if alert already exists
                existing_alert = await self.db.execute(
                    select(ComplianceAlert).where(
                        and_(
                            ComplianceAlert.license_id == license.id,
                            ComplianceAlert.alert_type.in_([
                                "license_expired", "license_expiring_critical",
                                "license_expiring_soon", "license_expiring_warning"
                            ]),
                            ComplianceAlert.is_resolved == False
                        )
                    )
                )
                
                if existing_alert.scalar_one_or_none():
                    continue
                
                # Create new alert
                alert_data = ComplianceAlertCreate(
                    license_id=license.id,
                    asset_id=license.asset_id,
                    alert_type=alert_type,
                    severity=severity,
                    title=title,
                    description=description,
                    metadata={
                        "license_number": license.license_number,
                        "license_title": license.title,
                        "expiry_date": license.end_date.isoformat(),
                        "days_until_expiry": days_until_expiry,
                        "licensor_name": license.licensor.name if license.licensor else None,
                        "licensee_name": license.licensee.name if license.licensee else None
                    }
                )
                
                alert = await self.compliance_service.create_compliance_alert(
                    alert_data, 
                    User(user_id="system", username="system", email="system@mams.com")
                )
                alerts_created.append(alert)
            
            logger.info(f"Created {len(alerts_created)} expiration alerts")
            return alerts_created
            
        except Exception as e:
            logger.error(f"Failed to monitor license expirations: {str(e)}")
            raise MonitoringError(f"Failed to monitor license expirations: {str(e)}")
    
    async def monitor_usage_limits(self) -> List[ComplianceAlertResponse]:
        """Monitor usage limits across all licenses"""
        try:
            logger.info("Monitoring usage limits")
            
            # Get licenses with usage limits
            result = await self.db.execute(
                select(License).where(
                    and_(
                        License.status == "active",
                        or_(
                            License.max_usage_count.is_not(None),
                            License.max_duration_seconds.is_not(None)
                        )
                    )
                )
            )
            licenses = result.scalars().all()
            
            alerts_created = []
            
            for license in licenses:
                license_alerts = await self._check_license_usage_limits(license)
                alerts_created.extend(license_alerts)
            
            logger.info(f"Created {len(alerts_created)} usage limit alerts")
            return alerts_created
            
        except Exception as e:
            logger.error(f"Failed to monitor usage limits: {str(e)}")
            raise MonitoringError(f"Failed to monitor usage limits: {str(e)}")
    
    async def monitor_geographic_compliance(self) -> List[ComplianceAlertResponse]:
        """Monitor geographic compliance violations"""
        try:
            logger.info("Monitoring geographic compliance")
            
            # Get recent usage records with geographic restrictions
            recent_date = datetime.utcnow() - timedelta(days=7)
            
            result = await self.db.execute(
                select(UsageRecord)
                .options(selectinload(UsageRecord.license))
                .where(
                    and_(
                        UsageRecord.usage_date >= recent_date,
                        UsageRecord.country.is_not(None)
                    )
                )
            )
            usage_records = result.scalars().all()
            
            alerts_created = []
            
            for usage_record in usage_records:
                license = usage_record.license
                
                # Check geographic restrictions
                if license and license.geographic_scope == "country_specific":
                    if not license.countries or usage_record.country not in license.countries:
                        # Geographic violation
                        existing_alert = await self.db.execute(
                            select(ComplianceAlert).where(
                                and_(
                                    ComplianceAlert.usage_record_id == usage_record.id,
                                    ComplianceAlert.alert_type == "geographic_violation",
                                    ComplianceAlert.is_resolved == False
                                )
                            )
                        )
                        
                        if existing_alert.scalar_one_or_none():
                            continue
                        
                        alert_data = ComplianceAlertCreate(
                            license_id=license.id,
                            asset_id=usage_record.asset_id,
                            usage_record_id=usage_record.id,
                            alert_type="geographic_violation",
                            severity="high",
                            title=f"Geographic Violation: {license.license_number}",
                            description=f"Usage in {usage_record.country} is not permitted under license '{license.title}'",
                            metadata={
                                "license_number": license.license_number,
                                "violation_country": usage_record.country,
                                "permitted_countries": license.countries,
                                "usage_date": usage_record.usage_date.isoformat(),
                                "platform": usage_record.platform
                            }
                        )
                        
                        alert = await self.compliance_service.create_compliance_alert(
                            alert_data,
                            User(user_id="system", username="system", email="system@mams.com")
                        )
                        alerts_created.append(alert)
            
            logger.info(f"Created {len(alerts_created)} geographic compliance alerts")
            return alerts_created
            
        except Exception as e:
            logger.error(f"Failed to monitor geographic compliance: {str(e)}")
            raise MonitoringError(f"Failed to monitor geographic compliance: {str(e)}")
    
    async def monitor_revenue_thresholds(self, threshold_percentage: float = 90.0) -> List[ComplianceAlertResponse]:
        """Monitor revenue thresholds against minimum guarantees"""
        try:
            logger.info(f"Monitoring revenue thresholds at {threshold_percentage}%")
            
            # Get licenses with minimum guarantees
            result = await self.db.execute(
                select(License).where(
                    and_(
                        License.status == "active",
                        License.minimum_guarantee.is_not(None),
                        License.minimum_guarantee > 0
                    )
                )
            )
            licenses = result.scalars().all()
            
            alerts_created = []
            
            for license in licenses:
                # Calculate total revenue for this license
                revenue_result = await self.db.execute(
                    select(func.sum(UsageRecord.revenue_generated)).where(
                        and_(
                            UsageRecord.license_id == license.id,
                            UsageRecord.revenue_generated.is_not(None)
                        )
                    )
                )
                total_revenue = revenue_result.scalar() or 0
                
                # Check if approaching minimum guarantee
                if total_revenue >= license.minimum_guarantee * (threshold_percentage / 100):
                    # Check if alert already exists
                    existing_alert = await self.db.execute(
                        select(ComplianceAlert).where(
                            and_(
                                ComplianceAlert.license_id == license.id,
                                ComplianceAlert.alert_type == "revenue_threshold_reached",
                                ComplianceAlert.is_resolved == False
                            )
                        )
                    )
                    
                    if existing_alert.scalar_one_or_none():
                        continue
                    
                    percentage_reached = (total_revenue / license.minimum_guarantee) * 100
                    remaining_guarantee = license.minimum_guarantee - total_revenue
                    
                    alert_data = ComplianceAlertCreate(
                        license_id=license.id,
                        asset_id=license.asset_id,
                        alert_type="revenue_threshold_reached",
                        severity="medium" if percentage_reached < 95 else "high",
                        title=f"Revenue Threshold Reached: {license.license_number}",
                        description=f"Revenue has reached {percentage_reached:.1f}% of minimum guarantee. Remaining: {remaining_guarantee}",
                        metadata={
                            "license_number": license.license_number,
                            "minimum_guarantee": license.minimum_guarantee,
                            "current_revenue": total_revenue,
                            "percentage_reached": percentage_reached,
                            "remaining_guarantee": remaining_guarantee,
                            "currency": license.currency
                        }
                    )
                    
                    alert = await self.compliance_service.create_compliance_alert(
                        alert_data,
                        User(user_id="system", username="system", email="system@mams.com")
                    )
                    alerts_created.append(alert)
            
            logger.info(f"Created {len(alerts_created)} revenue threshold alerts")
            return alerts_created
            
        except Exception as e:
            logger.error(f"Failed to monitor revenue thresholds: {str(e)}")
            raise MonitoringError(f"Failed to monitor revenue thresholds: {str(e)}")
    
    async def monitor_sublicensing_violations(self) -> List[ComplianceAlertResponse]:
        """Monitor for potential sublicensing violations"""
        try:
            logger.info("Monitoring sublicensing violations")
            
            # Get licenses that don't allow sublicensing
            result = await self.db.execute(
                select(License).where(
                    and_(
                        License.status == "active",
                        License.sublicensing_allowed == False
                    )
                )
            )
            licenses = result.scalars().all()
            
            alerts_created = []
            
            for license in licenses:
                # Check for usage by different users/platforms that might indicate sublicensing
                usage_result = await self.db.execute(
                    select(UsageRecord).where(
                        and_(
                            UsageRecord.license_id == license.id,
                            UsageRecord.usage_date >= datetime.utcnow() - timedelta(days=30)
                        )
                    )
                )
                usage_records = usage_result.scalars().all()
                
                # Analyze usage patterns
                users = set(record.user_id for record in usage_records)
                platforms = set(record.platform for record in usage_records if record.platform)
                
                # Trigger alert if multiple users or suspicious platform usage
                if len(users) > 5 or len(platforms) > 3:
                    existing_alert = await self.db.execute(
                        select(ComplianceAlert).where(
                            and_(
                                ComplianceAlert.license_id == license.id,
                                ComplianceAlert.alert_type == "potential_sublicensing",
                                ComplianceAlert.is_resolved == False
                            )
                        )
                    )
                    
                    if existing_alert.scalar_one_or_none():
                        continue
                    
                    alert_data = ComplianceAlertCreate(
                        license_id=license.id,
                        asset_id=license.asset_id,
                        alert_type="potential_sublicensing",
                        severity="medium",
                        title=f"Potential Sublicensing: {license.license_number}",
                        description=f"License shows usage by {len(users)} users across {len(platforms)} platforms, which may indicate sublicensing",
                        metadata={
                            "license_number": license.license_number,
                            "user_count": len(users),
                            "platform_count": len(platforms),
                            "platforms": list(platforms),
                            "sublicensing_allowed": license.sublicensing_allowed
                        }
                    )
                    
                    alert = await self.compliance_service.create_compliance_alert(
                        alert_data,
                        User(user_id="system", username="system", email="system@mams.com")
                    )
                    alerts_created.append(alert)
            
            logger.info(f"Created {len(alerts_created)} sublicensing alerts")
            return alerts_created
            
        except Exception as e:
            logger.error(f"Failed to monitor sublicensing violations: {str(e)}")
            raise MonitoringError(f"Failed to monitor sublicensing violations: {str(e)}")
    
    async def run_monitoring_cycle(self) -> Dict[str, Any]:
        """Run a complete monitoring cycle"""
        try:
            logger.info("Starting monitoring cycle")
            
            start_time = datetime.utcnow()
            
            # Run all monitoring checks
            expiration_alerts = await self.monitor_license_expirations()
            usage_limit_alerts = await self.monitor_usage_limits()
            geographic_alerts = await self.monitor_geographic_compliance()
            revenue_alerts = await self.monitor_revenue_thresholds()
            sublicensing_alerts = await self.monitor_sublicensing_violations()
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            total_alerts = (
                len(expiration_alerts) + 
                len(usage_limit_alerts) + 
                len(geographic_alerts) + 
                len(revenue_alerts) + 
                len(sublicensing_alerts)
            )
            
            result = {
                "monitoring_cycle": {
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_seconds": duration,
                    "total_alerts_created": total_alerts
                },
                "alerts_by_type": {
                    "expiration_alerts": len(expiration_alerts),
                    "usage_limit_alerts": len(usage_limit_alerts),
                    "geographic_alerts": len(geographic_alerts),
                    "revenue_alerts": len(revenue_alerts),
                    "sublicensing_alerts": len(sublicensing_alerts)
                },
                "alert_details": {
                    "expiration": [alert.dict() for alert in expiration_alerts],
                    "usage_limits": [alert.dict() for alert in usage_limit_alerts],
                    "geographic": [alert.dict() for alert in geographic_alerts],
                    "revenue": [alert.dict() for alert in revenue_alerts],
                    "sublicensing": [alert.dict() for alert in sublicensing_alerts]
                }
            }
            
            logger.info(f"Monitoring cycle completed: {total_alerts} alerts created in {duration:.2f} seconds")
            return result
            
        except Exception as e:
            logger.error(f"Failed to run monitoring cycle: {str(e)}")
            raise MonitoringError(f"Failed to run monitoring cycle: {str(e)}")
    
    # Private helper methods
    async def _check_license_usage_limits(self, license: License) -> List[ComplianceAlertResponse]:
        """Check usage limits for a specific license"""
        try:
            alerts = []
            
            # Get usage records for this license
            usage_result = await self.db.execute(
                select(UsageRecord).where(UsageRecord.license_id == license.id)
            )
            usage_records = usage_result.scalars().all()
            
            # Check usage count limit
            if license.max_usage_count:
                total_usage = sum(record.usage_count for record in usage_records)
                remaining_usage = license.max_usage_count - total_usage
                usage_percentage = (total_usage / license.max_usage_count) * 100
                
                # Determine alert level
                if remaining_usage <= 0:
                    alert_type = "usage_limit_exceeded"
                    severity = "critical"
                    title = f"Usage Limit Exceeded: {license.license_number}"
                    description = f"Usage count limit of {license.max_usage_count} has been exceeded. Total usage: {total_usage}"
                elif usage_percentage >= 90:
                    alert_type = "usage_limit_warning"
                    severity = "high"
                    title = f"Usage Limit Warning: {license.license_number}"
                    description = f"Usage count is at {usage_percentage:.1f}% of limit. Remaining: {remaining_usage}"
                elif usage_percentage >= 75:
                    alert_type = "usage_limit_notice"
                    severity = "medium"
                    title = f"Usage Limit Notice: {license.license_number}"
                    description = f"Usage count is at {usage_percentage:.1f}% of limit. Remaining: {remaining_usage}"
                else:
                    alert_type = None
                
                if alert_type:
                    # Check if alert already exists
                    existing_alert = await self.db.execute(
                        select(ComplianceAlert).where(
                            and_(
                                ComplianceAlert.license_id == license.id,
                                ComplianceAlert.alert_type == alert_type,
                                ComplianceAlert.is_resolved == False
                            )
                        )
                    )
                    
                    if not existing_alert.scalar_one_or_none():
                        alert_data = ComplianceAlertCreate(
                            license_id=license.id,
                            asset_id=license.asset_id,
                            alert_type=alert_type,
                            severity=severity,
                            title=title,
                            description=description,
                            metadata={
                                "license_number": license.license_number,
                                "max_usage_count": license.max_usage_count,
                                "current_usage": total_usage,
                                "remaining_usage": remaining_usage,
                                "usage_percentage": usage_percentage
                            }
                        )
                        
                        alert = await self.compliance_service.create_compliance_alert(
                            alert_data,
                            User(user_id="system", username="system", email="system@mams.com")
                        )
                        alerts.append(alert)
            
            # Check duration limit
            if license.max_duration_seconds:
                total_duration = sum(record.duration_seconds or 0 for record in usage_records)
                remaining_duration = license.max_duration_seconds - total_duration
                duration_percentage = (total_duration / license.max_duration_seconds) * 100
                
                # Determine alert level
                if remaining_duration <= 0:
                    alert_type = "duration_limit_exceeded"
                    severity = "critical"
                    title = f"Duration Limit Exceeded: {license.license_number}"
                    description = f"Duration limit of {license.max_duration_seconds} seconds has been exceeded. Total duration: {total_duration} seconds"
                elif duration_percentage >= 90:
                    alert_type = "duration_limit_warning"
                    severity = "high"
                    title = f"Duration Limit Warning: {license.license_number}"
                    description = f"Duration usage is at {duration_percentage:.1f}% of limit. Remaining: {remaining_duration} seconds"
                else:
                    alert_type = None
                
                if alert_type:
                    # Check if alert already exists
                    existing_alert = await self.db.execute(
                        select(ComplianceAlert).where(
                            and_(
                                ComplianceAlert.license_id == license.id,
                                ComplianceAlert.alert_type == alert_type,
                                ComplianceAlert.is_resolved == False
                            )
                        )
                    )
                    
                    if not existing_alert.scalar_one_or_none():
                        alert_data = ComplianceAlertCreate(
                            license_id=license.id,
                            asset_id=license.asset_id,
                            alert_type=alert_type,
                            severity=severity,
                            title=title,
                            description=description,
                            metadata={
                                "license_number": license.license_number,
                                "max_duration_seconds": license.max_duration_seconds,
                                "current_duration": total_duration,
                                "remaining_duration": remaining_duration,
                                "duration_percentage": duration_percentage
                            }
                        )
                        
                        alert = await self.compliance_service.create_compliance_alert(
                            alert_data,
                            User(user_id="system", username="system", email="system@mams.com")
                        )
                        alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Failed to check license usage limits: {str(e)}")
            return []