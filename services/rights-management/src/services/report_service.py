"""
Rights Management Service - Report Service
"""

import asyncio
import csv
import json
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.orm import selectinload
import uuid

from ..models.schemas import (
    RightsReportCreate, RightsReportUpdate, RightsReportResponse,
    PaginatedResponse, User
)
from ..db.models import (
    License, UsageRecord, ComplianceAlert, RightsParty, RightsReport
)
from ..core.config import settings
from ..core.exceptions import ReportError
from ..core.logger import get_logger
from .analytics_service import AnalyticsService

logger = get_logger(__name__)


class ReportService:
    """Service for generating and managing rights reports"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.analytics_service = AnalyticsService(db)
        self.report_dir = Path(settings.EXPORT_DIR) / "reports"
        self.report_dir.mkdir(parents=True, exist_ok=True)
    
    async def create_report(self, report_data: RightsReportCreate, user: User) -> RightsReportResponse:
        """Create a new rights report"""
        try:
            logger.info(f"Creating report: {report_data.title}")
            
            # Validate date range
            if report_data.end_date < report_data.start_date:
                raise ReportError("End date must be after start date")
            
            # Create report record
            report = RightsReport(
                **report_data.dict(),
                created_by=user.user_id,
                status="pending"
            )
            
            self.db.add(report)
            await self.db.commit()
            await self.db.refresh(report)
            
            logger.info(f"Created report: {report.id}")
            return RightsReportResponse.from_orm(report)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create report: {str(e)}")
            raise ReportError(f"Failed to create report: {str(e)}")
    
    async def generate_report(self, report_id: str, user: User) -> bool:
        """Generate a report file"""
        try:
            logger.info(f"Generating report: {report_id}")
            
            # Get report
            result = await self.db.execute(
                select(RightsReport).where(RightsReport.id == report_id)
            )
            report = result.scalar_one_or_none()
            
            if not report:
                raise ReportError("Report not found")
            
            # Update status
            report.status = "processing"
            await self.db.commit()
            
            # Generate report based on type
            if report.report_type == "usage_summary":
                file_path = await self._generate_usage_summary_report(report)
            elif report.report_type == "license_inventory":
                file_path = await self._generate_license_inventory_report(report)
            elif report.report_type == "compliance_audit":
                file_path = await self._generate_compliance_audit_report(report)
            elif report.report_type == "revenue_analysis":
                file_path = await self._generate_revenue_analysis_report(report)
            elif report.report_type == "expiration_forecast":
                file_path = await self._generate_expiration_forecast_report(report)
            elif report.report_type == "asset_performance":
                file_path = await self._generate_asset_performance_report(report)
            else:
                raise ReportError(f"Unknown report type: {report.report_type}")
            
            # Update report with file path
            report.file_path = str(file_path)
            report.status = "completed"
            await self.db.commit()
            
            logger.info(f"Report generated successfully: {file_path}")
            return True
            
        except Exception as e:
            # Update report status to failed
            try:
                result = await self.db.execute(
                    select(RightsReport).where(RightsReport.id == report_id)
                )
                report = result.scalar_one_or_none()
                if report:
                    report.status = "failed"
                    report.metadata = report.metadata or {}
                    report.metadata["error"] = str(e)
                    await self.db.commit()
            except:
                pass
            
            logger.error(f"Failed to generate report: {str(e)}")
            raise ReportError(f"Failed to generate report: {str(e)}")
    
    async def get_reports(
        self,
        page: int = 1,
        limit: int = 20,
        report_type: Optional[str] = None,
        status: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> PaginatedResponse:
        """Get reports with pagination and filtering"""
        try:
            query = select(RightsReport)
            
            # Apply filters
            if report_type:
                query = query.where(RightsReport.report_type == report_type)
            
            if status:
                query = query.where(RightsReport.status == status)
            
            if created_by:
                query = query.where(RightsReport.created_by == created_by)
            
            # Get total count
            count_query = select(func.count(RightsReport.id)).select_from(query.subquery())
            total_result = await self.db.execute(count_query)
            total = total_result.scalar()
            
            # Apply pagination and ordering
            offset = (page - 1) * limit
            query = query.order_by(desc(RightsReport.created_at)).offset(offset).limit(limit)
            
            result = await self.db.execute(query)
            reports = result.scalars().all()
            
            return PaginatedResponse(
                items=[RightsReportResponse.from_orm(report) for report in reports],
                total=total,
                page=page,
                limit=limit,
                pages=(total + limit - 1) // limit
            )
            
        except Exception as e:
            logger.error(f"Failed to get reports: {str(e)}")
            raise ReportError(f"Failed to get reports: {str(e)}")
    
    async def get_report(self, report_id: str) -> Optional[RightsReportResponse]:
        """Get a specific report"""
        try:
            result = await self.db.execute(
                select(RightsReport).where(RightsReport.id == report_id)
            )
            report = result.scalar_one_or_none()
            
            if not report:
                return None
            
            return RightsReportResponse.from_orm(report)
            
        except Exception as e:
            logger.error(f"Failed to get report: {str(e)}")
            raise ReportError(f"Failed to get report: {str(e)}")
    
    async def download_report(self, report_id: str, user: User) -> Dict[str, Any]:
        """Download a report file"""
        try:
            result = await self.db.execute(
                select(RightsReport).where(RightsReport.id == report_id)
            )
            report = result.scalar_one_or_none()
            
            if not report:
                raise ReportError("Report not found")
            
            if not report.file_path or not Path(report.file_path).exists():
                raise ReportError("Report file not found")
            
            return {
                "file_path": report.file_path,
                "filename": Path(report.file_path).name,
                "content_type": self._get_content_type(report.file_path),
                "size": Path(report.file_path).stat().st_size
            }
            
        except Exception as e:
            logger.error(f"Failed to download report: {str(e)}")
            raise ReportError(f"Failed to download report: {str(e)}")
    
    # Report generation methods
    async def _generate_usage_summary_report(self, report: RightsReport) -> Path:
        """Generate usage summary report"""
        try:
            # Get usage analytics
            analytics = await self.analytics_service.get_usage_analytics(
                start_date=report.start_date,
                end_date=report.end_date
            )
            
            # Create CSV file
            filename = f"usage_summary_{report.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
            file_path = self.report_dir / filename
            
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Header
                writer.writerow(['Usage Summary Report'])
                writer.writerow([f'Period: {report.start_date} to {report.end_date}'])
                writer.writerow(['Generated:', datetime.utcnow().isoformat()])
                writer.writerow([])
                
                # Summary statistics
                writer.writerow(['Summary Statistics'])
                writer.writerow(['Metric', 'Value'])
                writer.writerow(['Total Usage Count', analytics.total_usage_count])
                writer.writerow(['Total Duration (seconds)', analytics.total_duration_seconds])
                writer.writerow(['Total Revenue', f'${analytics.total_revenue:,.2f}'])
                writer.writerow(['Total Royalties', f'${analytics.total_royalties:,.2f}'])
                writer.writerow([])
                
                # Usage by type
                writer.writerow(['Usage by Type'])
                writer.writerow(['Usage Type', 'Count', 'Revenue'])
                for usage_type, count in analytics.usage_by_type.items():
                    revenue = analytics.revenue_by_type.get(usage_type, 0)
                    writer.writerow([usage_type, count, f'${revenue:,.2f}'])
                writer.writerow([])
                
                # Usage by country
                writer.writerow(['Usage by Country'])
                writer.writerow(['Country', 'Count', 'Revenue'])
                for country, count in analytics.usage_by_country.items():
                    revenue = analytics.revenue_by_country.get(country, 0)
                    writer.writerow([country, count, f'${revenue:,.2f}'])
                writer.writerow([])
                
                # Usage by platform
                writer.writerow(['Usage by Platform'])
                writer.writerow(['Platform', 'Count', 'Revenue'])
                for platform, count in analytics.usage_by_platform.items():
                    revenue = analytics.revenue_by_platform.get(platform, 0)
                    writer.writerow([platform, count, f'${revenue:,.2f}'])
            
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to generate usage summary report: {str(e)}")
            raise ReportError(f"Failed to generate usage summary report: {str(e)}")
    
    async def _generate_license_inventory_report(self, report: RightsReport) -> Path:
        """Generate license inventory report"""
        try:
            # Get all licenses
            result = await self.db.execute(
                select(License)
                .options(
                    selectinload(License.licensor),
                    selectinload(License.licensee)
                )
                .order_by(License.license_number)
            )
            licenses = result.scalars().all()
            
            # Create CSV file
            filename = f"license_inventory_{report.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
            file_path = self.report_dir / filename
            
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Header
                writer.writerow(['License Inventory Report'])
                writer.writerow(['Generated:', datetime.utcnow().isoformat()])
                writer.writerow([])
                
                # License details
                writer.writerow([
                    'License Number', 'Title', 'Status', 'Type', 'Start Date', 'End Date',
                    'Licensor', 'Licensee', 'Geographic Scope', 'License Fee', 'Currency',
                    'Royalty Rate', 'Max Usage Count', 'Exclusivity', 'Asset ID'
                ])
                
                for license in licenses:
                    writer.writerow([
                        license.license_number,
                        license.title,
                        license.status,
                        license.license_type,
                        license.start_date.isoformat() if license.start_date else '',
                        license.end_date.isoformat() if license.end_date else '',
                        license.licensor.name if license.licensor else '',
                        license.licensee.name if license.licensee else '',
                        license.geographic_scope,
                        license.license_fee or '',
                        license.currency,
                        license.royalty_rate or '',
                        license.max_usage_count or '',
                        'Yes' if license.exclusivity else 'No',
                        license.asset_id
                    ])
            
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to generate license inventory report: {str(e)}")
            raise ReportError(f"Failed to generate license inventory report: {str(e)}")
    
    async def _generate_compliance_audit_report(self, report: RightsReport) -> Path:
        """Generate compliance audit report"""
        try:
            # Get compliance alerts for the period
            result = await self.db.execute(
                select(ComplianceAlert)
                .options(selectinload(ComplianceAlert.license))
                .where(
                    and_(
                        ComplianceAlert.created_at >= report.start_date,
                        ComplianceAlert.created_at <= report.end_date + timedelta(days=1)
                    )
                )
                .order_by(desc(ComplianceAlert.created_at))
            )
            alerts = result.scalars().all()
            
            # Create CSV file
            filename = f"compliance_audit_{report.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
            file_path = self.report_dir / filename
            
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Header
                writer.writerow(['Compliance Audit Report'])
                writer.writerow([f'Period: {report.start_date} to {report.end_date}'])
                writer.writerow(['Generated:', datetime.utcnow().isoformat()])
                writer.writerow([])
                
                # Summary
                total_alerts = len(alerts)
                resolved_alerts = len([a for a in alerts if a.is_resolved])
                critical_alerts = len([a for a in alerts if a.severity == 'critical'])
                
                writer.writerow(['Summary'])
                writer.writerow(['Total Alerts', total_alerts])
                writer.writerow(['Resolved Alerts', resolved_alerts])
                writer.writerow(['Critical Alerts', critical_alerts])
                writer.writerow(['Resolution Rate', f'{(resolved_alerts/total_alerts*100):.1f}%' if total_alerts > 0 else '0%'])
                writer.writerow([])
                
                # Alert details
                writer.writerow([
                    'Alert ID', 'Alert Type', 'Severity', 'Title', 'Description',
                    'License Number', 'Asset ID', 'Created Date', 'Resolved',
                    'Resolved Date', 'Resolved By'
                ])
                
                for alert in alerts:
                    writer.writerow([
                        alert.id,
                        alert.alert_type,
                        alert.severity,
                        alert.title,
                        alert.description,
                        alert.license.license_number if alert.license else '',
                        alert.asset_id or '',
                        alert.created_at.isoformat(),
                        'Yes' if alert.is_resolved else 'No',
                        alert.resolved_at.isoformat() if alert.resolved_at else '',
                        alert.resolved_by or ''
                    ])
            
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to generate compliance audit report: {str(e)}")
            raise ReportError(f"Failed to generate compliance audit report: {str(e)}")
    
    async def _generate_revenue_analysis_report(self, report: RightsReport) -> Path:
        """Generate revenue analysis report"""
        try:
            # Get revenue analytics
            revenue_analytics = await self.analytics_service.get_revenue_analytics(
                start_date=report.start_date,
                end_date=report.end_date,
                grouping="monthly"
            )
            
            # Create CSV file
            filename = f"revenue_analysis_{report.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
            file_path = self.report_dir / filename
            
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Header
                writer.writerow(['Revenue Analysis Report'])
                writer.writerow([f'Period: {report.start_date} to {report.end_date}'])
                writer.writerow(['Generated:', datetime.utcnow().isoformat()])
                writer.writerow([])
                
                # Revenue summary
                writer.writerow(['Revenue Summary'])
                writer.writerow(['Metric', 'Amount'])
                totals = revenue_analytics['totals']
                writer.writerow(['Total Revenue', f"${totals['total_revenue']:,.2f}"])
                writer.writerow(['Total Royalties', f"${totals['total_royalties']:,.2f}"])
                writer.writerow(['Net Revenue', f"${totals['net_revenue']:,.2f}"])
                writer.writerow(['Royalty Percentage', f"{totals['royalty_percentage']:.2f}%"])
                writer.writerow([])
                
                # Monthly breakdown
                writer.writerow(['Monthly Revenue Breakdown'])
                writer.writerow(['Month', 'Revenue', 'Royalties', 'Net Revenue'])
                time_series = revenue_analytics['time_series']
                for period in sorted(time_series['revenue_by_period'].keys()):
                    revenue = time_series['revenue_by_period'][period]
                    royalties = time_series['royalties_by_period'].get(period, 0)
                    net = revenue - royalties
                    writer.writerow([period, f'${revenue:,.2f}', f'${royalties:,.2f}', f'${net:,.2f}'])
                writer.writerow([])
                
                # Top performing assets
                writer.writerow(['Top Performing Assets'])
                writer.writerow(['Asset ID', 'Revenue'])
                for asset in revenue_analytics['top_performers']['top_assets']:
                    writer.writerow([asset['asset_id'], f"${asset['revenue']:,.2f}"])
                writer.writerow([])
                
                # Top performing licenses
                writer.writerow(['Top Performing Licenses'])
                writer.writerow(['License ID', 'Revenue'])
                for license in revenue_analytics['top_performers']['top_licenses']:
                    writer.writerow([license['license_id'], f"${license['revenue']:,.2f}"])
            
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to generate revenue analysis report: {str(e)}")
            raise ReportError(f"Failed to generate revenue analysis report: {str(e)}")
    
    async def _generate_expiration_forecast_report(self, report: RightsReport) -> Path:
        """Generate license expiration forecast report"""
        try:
            # Get licenses expiring in the next 12 months
            forecast_date = date.today() + timedelta(days=365)
            
            result = await self.db.execute(
                select(License)
                .options(
                    selectinload(License.licensor),
                    selectinload(License.licensee)
                )
                .where(
                    and_(
                        License.end_date <= forecast_date,
                        License.end_date >= date.today(),
                        License.status == "active"
                    )
                )
                .order_by(License.end_date)
            )
            licenses = result.scalars().all()
            
            # Create CSV file
            filename = f"expiration_forecast_{report.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
            file_path = self.report_dir / filename
            
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Header
                writer.writerow(['License Expiration Forecast Report'])
                writer.writerow(['Generated:', datetime.utcnow().isoformat()])
                writer.writerow([])
                
                # Summary by time period
                now = date.today()
                in_30_days = [l for l in licenses if (l.end_date - now).days <= 30]
                in_90_days = [l for l in licenses if 30 < (l.end_date - now).days <= 90]
                in_180_days = [l for l in licenses if 90 < (l.end_date - now).days <= 180]
                in_365_days = [l for l in licenses if 180 < (l.end_date - now).days <= 365]
                
                writer.writerow(['Expiration Summary'])
                writer.writerow(['Time Period', 'Count', 'Total License Value'])
                writer.writerow(['Next 30 days', len(in_30_days), f'${sum(l.license_fee or 0 for l in in_30_days):,.2f}'])
                writer.writerow(['31-90 days', len(in_90_days), f'${sum(l.license_fee or 0 for l in in_90_days):,.2f}'])
                writer.writerow(['91-180 days', len(in_180_days), f'${sum(l.license_fee or 0 for l in in_180_days):,.2f}'])
                writer.writerow(['181-365 days', len(in_365_days), f'${sum(l.license_fee or 0 for l in in_365_days):,.2f}'])
                writer.writerow([])
                
                # Detailed expiration list
                writer.writerow([
                    'License Number', 'Title', 'Expiration Date', 'Days Until Expiry',
                    'License Fee', 'Licensor', 'Licensee', 'Asset ID', 'Priority'
                ])
                
                for license in licenses:
                    days_until_expiry = (license.end_date - now).days
                    
                    if days_until_expiry <= 30:
                        priority = 'CRITICAL'
                    elif days_until_expiry <= 90:
                        priority = 'HIGH'
                    elif days_until_expiry <= 180:
                        priority = 'MEDIUM'
                    else:
                        priority = 'LOW'
                    
                    writer.writerow([
                        license.license_number,
                        license.title,
                        license.end_date.isoformat(),
                        days_until_expiry,
                        f'${license.license_fee:,.2f}' if license.license_fee else '',
                        license.licensor.name if license.licensor else '',
                        license.licensee.name if license.licensee else '',
                        license.asset_id,
                        priority
                    ])
            
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to generate expiration forecast report: {str(e)}")
            raise ReportError(f"Failed to generate expiration forecast report: {str(e)}")
    
    async def _generate_asset_performance_report(self, report: RightsReport) -> Path:
        """Generate asset performance report"""
        try:
            # Get asset performance analytics
            performance_data = await self.analytics_service.get_asset_performance_analytics(
                start_date=report.start_date,
                end_date=report.end_date,
                limit=50
            )
            
            # Create CSV file
            filename = f"asset_performance_{report.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
            file_path = self.report_dir / filename
            
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Header
                writer.writerow(['Asset Performance Report'])
                writer.writerow([f'Period: {report.start_date} to {report.end_date}'])
                writer.writerow(['Generated:', datetime.utcnow().isoformat()])
                writer.writerow([])
                
                # Summary
                summary = performance_data['summary']
                writer.writerow(['Performance Summary'])
                writer.writerow(['Total Assets', summary['total_assets']])
                writer.writerow(['Total Usage', summary['total_usage']])
                writer.writerow(['Total Revenue', f"${summary['total_revenue']:,.2f}"])
                writer.writerow(['Total Duration (hours)', f"{summary['total_duration'] / 3600:.1f}"])
                writer.writerow([])
                
                # Top performers by usage
                writer.writerow(['Top Performers by Usage Count'])
                writer.writerow([
                    'Asset ID', 'Usage Count', 'Total Revenue', 'Total Duration (hours)',
                    'Countries', 'Platforms', 'Usage Types', 'Avg Revenue per Use'
                ])
                
                for asset in performance_data['top_performers']['by_usage_count']:
                    writer.writerow([
                        asset['asset_id'],
                        asset['usage_count'],
                        f"${asset['total_revenue']:,.2f}",
                        f"{asset['total_duration'] / 3600:.1f}",
                        asset['countries_count'],
                        asset['platforms_count'],
                        asset['usage_types_count'],
                        f"${asset['avg_revenue_per_usage']:,.2f}"
                    ])
                writer.writerow([])
                
                # Top performers by revenue
                writer.writerow(['Top Performers by Revenue'])
                writer.writerow([
                    'Asset ID', 'Total Revenue', 'Usage Count', 'Net Revenue',
                    'Total Royalties', 'Avg Revenue per Use'
                ])
                
                for asset in performance_data['top_performers']['by_revenue']:
                    writer.writerow([
                        asset['asset_id'],
                        f"${asset['total_revenue']:,.2f}",
                        asset['usage_count'],
                        f"${asset['net_revenue']:,.2f}",
                        f"${asset['total_royalties']:,.2f}",
                        f"${asset['avg_revenue_per_usage']:,.2f}"
                    ])
            
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to generate asset performance report: {str(e)}")
            raise ReportError(f"Failed to generate asset performance report: {str(e)}")
    
    def _get_content_type(self, file_path: str) -> str:
        """Get content type for file"""
        extension = Path(file_path).suffix.lower()
        
        content_types = {
            '.csv': 'text/csv',
            '.json': 'application/json',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.pdf': 'application/pdf'
        }
        
        return content_types.get(extension, 'application/octet-stream')