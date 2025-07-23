"""
Rights Management Service - Analytics Service
"""

import asyncio
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc, text
from sqlalchemy.orm import selectinload
import uuid

from ..models.schemas import (
    UsageAnalytics, LicenseAnalytics, User
)
from ..db.models import License, UsageRecord, ComplianceAlert, RightsParty
from ..core.config import settings
from ..core.exceptions import AnalyticsError
from ..core.logger import get_logger

logger = get_logger(__name__)


class AnalyticsService:
    """Service for rights analytics and reporting"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_usage_analytics(
        self,
        start_date: date,
        end_date: date,
        asset_id: Optional[str] = None,
        license_id: Optional[str] = None,
        usage_type: Optional[str] = None,
        country: Optional[str] = None,
        platform: Optional[str] = None
    ) -> UsageAnalytics:
        """Get usage analytics for a date range"""
        try:
            logger.info(f"Generating usage analytics from {start_date} to {end_date}")
            
            # Base query
            base_query = select(UsageRecord).where(
                and_(
                    UsageRecord.usage_date >= start_date,
                    UsageRecord.usage_date <= end_date + timedelta(days=1)
                )
            )
            
            # Apply filters
            if asset_id:
                base_query = base_query.where(UsageRecord.asset_id == asset_id)
            
            if license_id:
                base_query = base_query.where(UsageRecord.license_id == license_id)
            
            if usage_type:
                base_query = base_query.where(UsageRecord.usage_type == usage_type)
            
            if country:
                base_query = base_query.where(UsageRecord.country == country)
            
            if platform:
                base_query = base_query.where(UsageRecord.platform == platform)
            
            # Get all usage records
            result = await self.db.execute(base_query)
            usage_records = result.scalars().all()
            
            # Calculate totals
            total_usage_count = sum(record.usage_count for record in usage_records)
            total_duration_seconds = sum(record.duration_seconds or 0 for record in usage_records)
            total_revenue = sum(record.revenue_generated or 0 for record in usage_records)
            total_royalties = sum(record.royalty_due or 0 for record in usage_records)
            
            # Group by usage type
            usage_by_type = {}
            revenue_by_type = {}
            for record in usage_records:
                usage_type = record.usage_type
                usage_by_type[usage_type] = usage_by_type.get(usage_type, 0) + record.usage_count
                revenue_by_type[usage_type] = revenue_by_type.get(usage_type, 0) + (record.revenue_generated or 0)
            
            # Group by country
            usage_by_country = {}
            revenue_by_country = {}
            for record in usage_records:
                country = record.country or "Unknown"
                usage_by_country[country] = usage_by_country.get(country, 0) + record.usage_count
                revenue_by_country[country] = revenue_by_country.get(country, 0) + (record.revenue_generated or 0)
            
            # Group by platform
            usage_by_platform = {}
            revenue_by_platform = {}
            for record in usage_records:
                platform = record.platform or "Unknown"
                usage_by_platform[platform] = usage_by_platform.get(platform, 0) + record.usage_count
                revenue_by_platform[platform] = revenue_by_platform.get(platform, 0) + (record.revenue_generated or 0)
            
            # Time series data (daily aggregation)
            usage_over_time = await self._get_usage_time_series(usage_records, start_date, end_date)
            revenue_over_time = await self._get_revenue_time_series(usage_records, start_date, end_date)
            
            return UsageAnalytics(
                total_usage_count=total_usage_count,
                total_duration_seconds=total_duration_seconds,
                total_revenue=total_revenue,
                total_royalties=total_royalties,
                usage_by_type=usage_by_type,
                revenue_by_type=revenue_by_type,
                usage_by_country=usage_by_country,
                revenue_by_country=revenue_by_country,
                usage_by_platform=usage_by_platform,
                revenue_by_platform=revenue_by_platform,
                usage_over_time=usage_over_time,
                revenue_over_time=revenue_over_time
            )
            
        except Exception as e:
            logger.error(f"Failed to get usage analytics: {str(e)}")
            raise AnalyticsError(f"Failed to get usage analytics: {str(e)}")
    
    async def get_license_analytics(self) -> LicenseAnalytics:
        """Get license analytics"""
        try:
            logger.info("Generating license analytics")
            
            # Get all licenses
            licenses_result = await self.db.execute(select(License))
            licenses = licenses_result.scalars().all()
            
            # Basic counts
            total_licenses = len(licenses)
            active_licenses = len([l for l in licenses if l.status == "active"])
            expired_licenses = len([l for l in licenses if l.status == "expired"])
            
            # Expiring soon (within 30 days)
            cutoff_date = date.today() + timedelta(days=30)
            expiring_soon = len([
                l for l in licenses 
                if l.end_date and l.end_date <= cutoff_date and l.status == "active"
            ])
            
            # Group by license type
            licenses_by_type = {}
            for license in licenses:
                license_type = license.license_type
                licenses_by_type[license_type] = licenses_by_type.get(license_type, 0) + 1
            
            # Group by geographic scope
            licenses_by_geography = {}
            for license in licenses:
                geo_scope = license.geographic_scope
                licenses_by_geography[geo_scope] = licenses_by_geography.get(geo_scope, 0) + 1
            
            # Financial metrics
            total_license_fees = sum(license.license_fee or 0 for license in licenses)
            total_minimum_guarantees = sum(license.minimum_guarantee or 0 for license in licenses)
            
            royalty_rates = [license.royalty_rate for license in licenses if license.royalty_rate]
            average_royalty_rate = sum(royalty_rates) / len(royalty_rates) if royalty_rates else 0
            
            # Compliance alerts
            alerts_result = await self.db.execute(select(ComplianceAlert))
            alerts = alerts_result.scalars().all()
            
            compliance_alerts = len(alerts)
            resolved_alerts = len([a for a in alerts if a.is_resolved])
            critical_alerts = len([a for a in alerts if a.severity == "critical" and not a.is_resolved])
            
            return LicenseAnalytics(
                total_licenses=total_licenses,
                active_licenses=active_licenses,
                expired_licenses=expired_licenses,
                expiring_soon=expiring_soon,
                licenses_by_type=licenses_by_type,
                licenses_by_geography=licenses_by_geography,
                total_license_fees=total_license_fees,
                total_minimum_guarantees=total_minimum_guarantees,
                average_royalty_rate=average_royalty_rate,
                compliance_alerts=compliance_alerts,
                resolved_alerts=resolved_alerts,
                critical_alerts=critical_alerts
            )
            
        except Exception as e:
            logger.error(f"Failed to get license analytics: {str(e)}")
            raise AnalyticsError(f"Failed to get license analytics: {str(e)}")
    
    async def get_revenue_analytics(
        self,
        start_date: date,
        end_date: date,
        grouping: str = "monthly"  # daily, weekly, monthly, yearly
    ) -> Dict[str, Any]:
        """Get revenue analytics with flexible grouping"""
        try:
            logger.info(f"Generating revenue analytics from {start_date} to {end_date}")
            
            # Get usage records with revenue
            result = await self.db.execute(
                select(UsageRecord).where(
                    and_(
                        UsageRecord.usage_date >= start_date,
                        UsageRecord.usage_date <= end_date + timedelta(days=1),
                        UsageRecord.revenue_generated.is_not(None)
                    )
                )
            )
            usage_records = result.scalars().all()
            
            # Total revenue and royalties
            total_revenue = sum(record.revenue_generated or 0 for record in usage_records)
            total_royalties = sum(record.royalty_due or 0 for record in usage_records)
            net_revenue = total_revenue - total_royalties
            
            # Group by time period
            revenue_by_period = {}
            royalties_by_period = {}
            
            for record in usage_records:
                period_key = self._get_period_key(record.usage_date, grouping)
                
                revenue_by_period[period_key] = revenue_by_period.get(period_key, 0) + (record.revenue_generated or 0)
                royalties_by_period[period_key] = royalties_by_period.get(period_key, 0) + (record.royalty_due or 0)
            
            # Revenue by asset (top 10)
            revenue_by_asset = {}
            for record in usage_records:
                asset_id = record.asset_id
                revenue_by_asset[asset_id] = revenue_by_asset.get(asset_id, 0) + (record.revenue_generated or 0)
            
            top_assets = sorted(revenue_by_asset.items(), key=lambda x: x[1], reverse=True)[:10]
            
            # Revenue by license (top 10)
            revenue_by_license = {}
            for record in usage_records:
                license_id = record.license_id
                revenue_by_license[license_id] = revenue_by_license.get(license_id, 0) + (record.revenue_generated or 0)
            
            top_licenses = sorted(revenue_by_license.items(), key=lambda x: x[1], reverse=True)[:10]
            
            return {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "grouping": grouping
                },
                "totals": {
                    "total_revenue": total_revenue,
                    "total_royalties": total_royalties,
                    "net_revenue": net_revenue,
                    "royalty_percentage": (total_royalties / total_revenue * 100) if total_revenue > 0 else 0
                },
                "time_series": {
                    "revenue_by_period": revenue_by_period,
                    "royalties_by_period": royalties_by_period
                },
                "top_performers": {
                    "top_assets": [{"asset_id": k, "revenue": v} for k, v in top_assets],
                    "top_licenses": [{"license_id": k, "revenue": v} for k, v in top_licenses]
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get revenue analytics: {str(e)}")
            raise AnalyticsError(f"Failed to get revenue analytics: {str(e)}")
    
    async def get_compliance_analytics(self) -> Dict[str, Any]:
        """Get compliance analytics"""
        try:
            logger.info("Generating compliance analytics")
            
            # Get all compliance alerts
            alerts_result = await self.db.execute(select(ComplianceAlert))
            alerts = alerts_result.scalars().all()
            
            # Basic counts
            total_alerts = len(alerts)
            resolved_alerts = len([a for a in alerts if a.is_resolved])
            unresolved_alerts = total_alerts - resolved_alerts
            
            # Group by severity
            alerts_by_severity = {}
            unresolved_by_severity = {}
            for alert in alerts:
                severity = alert.severity
                alerts_by_severity[severity] = alerts_by_severity.get(severity, 0) + 1
                
                if not alert.is_resolved:
                    unresolved_by_severity[severity] = unresolved_by_severity.get(severity, 0) + 1
            
            # Group by alert type
            alerts_by_type = {}
            for alert in alerts:
                alert_type = alert.alert_type
                alerts_by_type[alert_type] = alerts_by_type.get(alert_type, 0) + 1
            
            # Resolution time analysis
            resolved_alerts_with_time = [
                a for a in alerts 
                if a.is_resolved and a.resolved_at and a.created_at
            ]
            
            resolution_times = []
            for alert in resolved_alerts_with_time:
                resolution_time = (alert.resolved_at - alert.created_at).total_seconds() / 3600  # hours
                resolution_times.append(resolution_time)
            
            avg_resolution_time = sum(resolution_times) / len(resolution_times) if resolution_times else 0
            
            # Recent trends (last 30 days)
            recent_date = datetime.utcnow() - timedelta(days=30)
            recent_alerts = [a for a in alerts if a.created_at >= recent_date]
            
            # Daily alert creation (last 30 days)
            daily_alerts = {}
            for i in range(30):
                day = (datetime.utcnow() - timedelta(days=i)).date()
                daily_alerts[day.isoformat()] = 0
            
            for alert in recent_alerts:
                day = alert.created_at.date()
                if day.isoformat() in daily_alerts:
                    daily_alerts[day.isoformat()] += 1
            
            return {
                "overview": {
                    "total_alerts": total_alerts,
                    "resolved_alerts": resolved_alerts,
                    "unresolved_alerts": unresolved_alerts,
                    "resolution_rate": (resolved_alerts / total_alerts * 100) if total_alerts > 0 else 0
                },
                "breakdown": {
                    "by_severity": alerts_by_severity,
                    "by_type": alerts_by_type,
                    "unresolved_by_severity": unresolved_by_severity
                },
                "resolution_metrics": {
                    "average_resolution_time_hours": avg_resolution_time,
                    "total_resolved": len(resolved_alerts_with_time)
                },
                "trends": {
                    "recent_alerts_30_days": len(recent_alerts),
                    "daily_alert_creation": daily_alerts
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get compliance analytics: {str(e)}")
            raise AnalyticsError(f"Failed to get compliance analytics: {str(e)}")
    
    async def get_asset_performance_analytics(
        self,
        start_date: date,
        end_date: date,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Get asset performance analytics"""
        try:
            logger.info(f"Generating asset performance analytics from {start_date} to {end_date}")
            
            # Get usage records for the period
            result = await self.db.execute(
                select(UsageRecord).where(
                    and_(
                        UsageRecord.usage_date >= start_date,
                        UsageRecord.usage_date <= end_date + timedelta(days=1)
                    )
                )
            )
            usage_records = result.scalars().all()
            
            # Group by asset
            asset_metrics = {}
            for record in usage_records:
                asset_id = record.asset_id
                
                if asset_id not in asset_metrics:
                    asset_metrics[asset_id] = {
                        "usage_count": 0,
                        "total_duration": 0,
                        "total_revenue": 0,
                        "total_royalties": 0,
                        "usage_types": set(),
                        "countries": set(),
                        "platforms": set()
                    }
                
                metrics = asset_metrics[asset_id]
                metrics["usage_count"] += record.usage_count
                metrics["total_duration"] += record.duration_seconds or 0
                metrics["total_revenue"] += record.revenue_generated or 0
                metrics["total_royalties"] += record.royalty_due or 0
                
                if record.usage_type:
                    metrics["usage_types"].add(record.usage_type)
                
                if record.country:
                    metrics["countries"].add(record.country)
                
                if record.platform:
                    metrics["platforms"].add(record.platform)
            
            # Convert sets to counts and calculate derived metrics
            for asset_id, metrics in asset_metrics.items():
                metrics["usage_types_count"] = len(metrics["usage_types"])
                metrics["countries_count"] = len(metrics["countries"])
                metrics["platforms_count"] = len(metrics["platforms"])
                metrics["net_revenue"] = metrics["total_revenue"] - metrics["total_royalties"]
                metrics["avg_revenue_per_usage"] = (
                    metrics["total_revenue"] / metrics["usage_count"] 
                    if metrics["usage_count"] > 0 else 0
                )
                
                # Remove sets (not JSON serializable)
                del metrics["usage_types"]
                del metrics["countries"] 
                del metrics["platforms"]
            
            # Sort by different metrics
            top_by_usage = sorted(
                asset_metrics.items(), 
                key=lambda x: x[1]["usage_count"], 
                reverse=True
            )[:limit]
            
            top_by_revenue = sorted(
                asset_metrics.items(), 
                key=lambda x: x[1]["total_revenue"], 
                reverse=True
            )[:limit]
            
            top_by_duration = sorted(
                asset_metrics.items(), 
                key=lambda x: x[1]["total_duration"], 
                reverse=True
            )[:limit]
            
            return {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "summary": {
                    "total_assets": len(asset_metrics),
                    "total_usage": sum(m["usage_count"] for m in asset_metrics.values()),
                    "total_revenue": sum(m["total_revenue"] for m in asset_metrics.values()),
                    "total_duration": sum(m["total_duration"] for m in asset_metrics.values())
                },
                "top_performers": {
                    "by_usage_count": [
                        {"asset_id": k, **v} for k, v in top_by_usage
                    ],
                    "by_revenue": [
                        {"asset_id": k, **v} for k, v in top_by_revenue
                    ],
                    "by_duration": [
                        {"asset_id": k, **v} for k, v in top_by_duration
                    ]
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get asset performance analytics: {str(e)}")
            raise AnalyticsError(f"Failed to get asset performance analytics: {str(e)}")
    
    # Private helper methods
    async def _get_usage_time_series(
        self, 
        usage_records: List[UsageRecord], 
        start_date: date, 
        end_date: date
    ) -> List[Dict[str, Any]]:
        """Generate daily usage time series"""
        try:
            # Create daily buckets
            daily_usage = {}
            current_date = start_date
            while current_date <= end_date:
                daily_usage[current_date.isoformat()] = 0
                current_date += timedelta(days=1)
            
            # Fill buckets with data
            for record in usage_records:
                day = record.usage_date.date().isoformat()
                if day in daily_usage:
                    daily_usage[day] += record.usage_count
            
            # Convert to time series format
            return [
                {"date": date_str, "usage_count": count}
                for date_str, count in sorted(daily_usage.items())
            ]
            
        except Exception as e:
            logger.error(f"Failed to generate usage time series: {str(e)}")
            return []
    
    async def _get_revenue_time_series(
        self, 
        usage_records: List[UsageRecord], 
        start_date: date, 
        end_date: date
    ) -> List[Dict[str, Any]]:
        """Generate daily revenue time series"""
        try:
            # Create daily buckets
            daily_revenue = {}
            current_date = start_date
            while current_date <= end_date:
                daily_revenue[current_date.isoformat()] = 0
                current_date += timedelta(days=1)
            
            # Fill buckets with data
            for record in usage_records:
                day = record.usage_date.date().isoformat()
                if day in daily_revenue:
                    daily_revenue[day] += record.revenue_generated or 0
            
            # Convert to time series format
            return [
                {"date": date_str, "revenue": amount}
                for date_str, amount in sorted(daily_revenue.items())
            ]
            
        except Exception as e:
            logger.error(f"Failed to generate revenue time series: {str(e)}")
            return []
    
    def _get_period_key(self, usage_date: datetime, grouping: str) -> str:
        """Get period key for grouping"""
        if grouping == "daily":
            return usage_date.date().isoformat()
        elif grouping == "weekly":
            # Get Monday of the week
            monday = usage_date.date() - timedelta(days=usage_date.weekday())
            return monday.isoformat()
        elif grouping == "monthly":
            return f"{usage_date.year}-{usage_date.month:02d}"
        elif grouping == "yearly":
            return str(usage_date.year)
        else:
            return usage_date.date().isoformat()  # Default to daily