"""Audit Reporting Service for GDPR Compliance"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, extract
from collections import defaultdict
import json
from io import StringIO, BytesIO
import csv
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from ..db.models import (
    GDPRAuditLog, DataRequest, UserConsent, 
    PrivacyPolicy, DataCategory, DataMapping,
    DataRetentionRule, AnonymizationLog
)
from ..models.schemas import (
    AuditReportType, AuditReportFormat,
    AuditReportRequest, AuditReportResponse,
    ComplianceScoreCard, RiskAssessment,
    EventFrequency, ComplianceTrend
)
from ..core.exceptions import ReportGenerationError


class AuditReportingService:
    """Service for generating comprehensive audit reports"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.styles = getSampleStyleSheet()
    
    async def generate_report(
        self,
        report_type: AuditReportType,
        start_date: datetime,
        end_date: datetime,
        filters: Optional[Dict[str, Any]] = None,
        format: AuditReportFormat = AuditReportFormat.JSON
    ) -> AuditReportResponse:
        """Generate an audit report based on type and parameters"""
        try:
            # Validate date range
            if start_date >= end_date:
                raise ValueError("Start date must be before end date")
            
            # Generate report data based on type
            report_data = await self._generate_report_data(
                report_type, start_date, end_date, filters
            )
            
            # Format report based on requested format
            formatted_report = await self._format_report(
                report_data, report_type, format
            )
            
            return AuditReportResponse(
                report_id=str(uuid.uuid4()),
                report_type=report_type,
                generated_at=datetime.utcnow(),
                period_start=start_date,
                period_end=end_date,
                format=format,
                data=report_data if format == AuditReportFormat.JSON else None,
                file_content=formatted_report if format != AuditReportFormat.JSON else None
            )
            
        except Exception as e:
            raise ReportGenerationError(f"Failed to generate report: {str(e)}")
    
    async def _generate_report_data(
        self,
        report_type: AuditReportType,
        start_date: datetime,
        end_date: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate report data based on type"""
        
        if report_type == AuditReportType.COMPLIANCE_OVERVIEW:
            return await self._generate_compliance_overview(start_date, end_date, filters)
        elif report_type == AuditReportType.USER_ACTIVITY:
            return await self._generate_user_activity_report(start_date, end_date, filters)
        elif report_type == AuditReportType.DATA_REQUESTS:
            return await self._generate_data_requests_report(start_date, end_date, filters)
        elif report_type == AuditReportType.CONSENT_ANALYSIS:
            return await self._generate_consent_analysis(start_date, end_date, filters)
        elif report_type == AuditReportType.RISK_ASSESSMENT:
            return await self._generate_risk_assessment(start_date, end_date, filters)
        elif report_type == AuditReportType.INCIDENT_LOG:
            return await self._generate_incident_log(start_date, end_date, filters)
        else:
            raise ValueError(f"Unsupported report type: {report_type}")
    
    async def _generate_compliance_overview(
        self,
        start_date: datetime,
        end_date: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate compliance overview report"""
        
        # Get event statistics
        event_stats = await self._get_event_statistics(start_date, end_date)
        
        # Get compliance score
        compliance_score = await self._calculate_compliance_score(start_date, end_date)
        
        # Get data request metrics
        request_metrics = await self._get_data_request_metrics(start_date, end_date)
        
        # Get consent metrics
        consent_metrics = await self._get_consent_metrics(start_date, end_date)
        
        # Get top risks
        top_risks = await self._identify_top_risks(start_date, end_date)
        
        return {
            "summary": {
                "reporting_period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "generated_at": datetime.utcnow().isoformat(),
                "total_events": event_stats["total_events"],
                "compliance_score": compliance_score,
                "high_risk_incidents": len(top_risks)
            },
            "event_statistics": event_stats,
            "data_requests": request_metrics,
            "consent_management": consent_metrics,
            "compliance_scorecard": compliance_score,
            "risk_indicators": top_risks,
            "recommendations": await self._generate_recommendations(compliance_score, top_risks)
        }
    
    async def _get_event_statistics(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get event statistics for the period"""
        
        # Query events by type
        result = await self.db.execute(
            select(
                GDPRAuditLog.event_type,
                func.count(GDPRAuditLog.id).label("count")
            ).where(
                and_(
                    GDPRAuditLog.event_timestamp >= start_date,
                    GDPRAuditLog.event_timestamp <= end_date
                )
            ).group_by(GDPRAuditLog.event_type)
        )
        
        events_by_type = {row[0]: row[1] for row in result}
        total_events = sum(events_by_type.values())
        
        # Query events by success status
        success_result = await self.db.execute(
            select(
                GDPRAuditLog.success,
                func.count(GDPRAuditLog.id).label("count")
            ).where(
                and_(
                    GDPRAuditLog.event_timestamp >= start_date,
                    GDPRAuditLog.event_timestamp <= end_date
                )
            ).group_by(GDPRAuditLog.success)
        )
        
        success_stats = {row[0]: row[1] for row in success_result}
        
        # Query events by day
        daily_result = await self.db.execute(
            select(
                func.date_trunc('day', GDPRAuditLog.event_timestamp).label("day"),
                func.count(GDPRAuditLog.id).label("count")
            ).where(
                and_(
                    GDPRAuditLog.event_timestamp >= start_date,
                    GDPRAuditLog.event_timestamp <= end_date
                )
            ).group_by("day").order_by("day")
        )
        
        daily_events = [
            {"date": row[0].isoformat(), "count": row[1]}
            for row in daily_result
        ]
        
        return {
            "total_events": total_events,
            "events_by_type": events_by_type,
            "success_rate": (success_stats.get(True, 0) / total_events * 100) if total_events > 0 else 0,
            "failed_events": success_stats.get(False, 0),
            "daily_distribution": daily_events,
            "peak_day": max(daily_events, key=lambda x: x["count"]) if daily_events else None
        }
    
    async def _calculate_compliance_score(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> ComplianceScoreCard:
        """Calculate compliance score based on various metrics"""
        
        scores = {}
        
        # Data request handling score (response time)
        request_score = await self._calculate_request_handling_score(start_date, end_date)
        scores["data_request_handling"] = request_score
        
        # Consent management score
        consent_score = await self._calculate_consent_management_score(start_date, end_date)
        scores["consent_management"] = consent_score
        
        # Data retention compliance
        retention_score = await self._calculate_retention_compliance_score(start_date, end_date)
        scores["data_retention"] = retention_score
        
        # Security incident score
        security_score = await self._calculate_security_score(start_date, end_date)
        scores["security_practices"] = security_score
        
        # Calculate overall score
        overall_score = sum(scores.values()) / len(scores)
        
        return ComplianceScoreCard(
            overall_score=overall_score,
            category_scores=scores,
            grade=self._get_compliance_grade(overall_score),
            trend="improving" if overall_score > 80 else "declining",
            last_updated=datetime.utcnow()
        )
    
    async def _get_data_request_metrics(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get data request metrics"""
        
        # Query requests by type
        result = await self.db.execute(
            select(
                DataRequest.request_type,
                func.count(DataRequest.id).label("count"),
                func.avg(
                    extract('epoch', DataRequest.completed_at - DataRequest.requested_at)
                ).label("avg_completion_time")
            ).where(
                and_(
                    DataRequest.requested_at >= start_date,
                    DataRequest.requested_at <= end_date
                )
            ).group_by(DataRequest.request_type)
        )
        
        request_metrics = {}
        total_requests = 0
        
        for row in result:
            request_type = row[0]
            count = row[1]
            avg_time = row[2]
            
            request_metrics[request_type] = {
                "count": count,
                "average_completion_hours": (avg_time / 3600) if avg_time else None
            }
            total_requests += count
        
        # Get requests completed within deadline
        deadline_result = await self.db.execute(
            select(func.count(DataRequest.id)).where(
                and_(
                    DataRequest.requested_at >= start_date,
                    DataRequest.requested_at <= end_date,
                    DataRequest.completed_at != None,
                    extract('epoch', DataRequest.completed_at - DataRequest.requested_at) <= 30 * 24 * 3600
                )
            )
        )
        
        completed_on_time = deadline_result.scalar() or 0
        
        return {
            "total_requests": total_requests,
            "requests_by_type": request_metrics,
            "completion_rate": (completed_on_time / total_requests * 100) if total_requests > 0 else 100,
            "average_response_time_hours": sum(
                m["average_completion_hours"] or 0 for m in request_metrics.values()
            ) / len(request_metrics) if request_metrics else 0
        }
    
    async def _get_consent_metrics(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get consent management metrics"""
        
        # Active consents by type
        consent_result = await self.db.execute(
            select(
                UserConsent.consent_type,
                func.count(UserConsent.id).label("count")
            ).where(
                and_(
                    UserConsent.consent_given == True,
                    UserConsent.withdrawn == False,
                    UserConsent.given_at >= start_date,
                    UserConsent.given_at <= end_date
                )
            ).group_by(UserConsent.consent_type)
        )
        
        consents_by_type = {row[0]: row[1] for row in consent_result}
        
        # Withdrawal rate
        withdrawal_result = await self.db.execute(
            select(func.count(UserConsent.id)).where(
                and_(
                    UserConsent.withdrawn == True,
                    UserConsent.withdrawn_at >= start_date,
                    UserConsent.withdrawn_at <= end_date
                )
            )
        )
        
        withdrawals = withdrawal_result.scalar() or 0
        total_consents = sum(consents_by_type.values())
        
        return {
            "active_consents": total_consents,
            "consents_by_type": consents_by_type,
            "withdrawal_count": withdrawals,
            "withdrawal_rate": (withdrawals / (total_consents + withdrawals) * 100) if (total_consents + withdrawals) > 0 else 0,
            "explicit_consent_rate": consents_by_type.get("data_processing", 0) / total_consents * 100 if total_consents > 0 else 0
        }
    
    async def _identify_top_risks(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: int = 5
    ) -> List[RiskAssessment]:
        """Identify top compliance risks"""
        
        risks = []
        
        # Risk 1: Failed data deletion requests
        deletion_failures = await self.db.execute(
            select(func.count(GDPRAuditLog.id)).where(
                and_(
                    GDPRAuditLog.event_type == "data_deletion_request",
                    GDPRAuditLog.success == False,
                    GDPRAuditLog.event_timestamp >= start_date,
                    GDPRAuditLog.event_timestamp <= end_date
                )
            )
        )
        
        failure_count = deletion_failures.scalar() or 0
        if failure_count > 0:
            risks.append(RiskAssessment(
                risk_id="RISK_001",
                category="data_deletion",
                severity="high" if failure_count > 5 else "medium",
                description=f"{failure_count} failed data deletion requests",
                impact="Potential GDPR violation - Right to be forgotten not honored",
                likelihood="certain",
                mitigation="Review deletion process and resolve technical issues",
                detected_at=datetime.utcnow()
            ))
        
        # Risk 2: Overdue data requests
        overdue_requests = await self.db.execute(
            select(func.count(DataRequest.id)).where(
                and_(
                    DataRequest.requested_at >= start_date,
                    DataRequest.requested_at <= end_date,
                    DataRequest.completed_at == None,
                    DataRequest.requested_at < datetime.utcnow() - timedelta(days=30)
                )
            )
        )
        
        overdue_count = overdue_requests.scalar() or 0
        if overdue_count > 0:
            risks.append(RiskAssessment(
                risk_id="RISK_002",
                category="data_requests",
                severity="high",
                description=f"{overdue_count} data requests overdue (>30 days)",
                impact="GDPR violation - 30-day response deadline exceeded",
                likelihood="certain",
                mitigation="Prioritize overdue requests immediately",
                detected_at=datetime.utcnow()
            ))
        
        # Risk 3: Missing consent records
        missing_consent = await self._check_missing_consent_risk(start_date, end_date)
        if missing_consent:
            risks.append(missing_consent)
        
        # Risk 4: Unauthorized access attempts
        unauthorized_access = await self._check_unauthorized_access_risk(start_date, end_date)
        if unauthorized_access:
            risks.append(unauthorized_access)
        
        # Risk 5: Data retention violations
        retention_violations = await self._check_retention_violations(start_date, end_date)
        if retention_violations:
            risks.append(retention_violations)
        
        # Sort by severity and return top risks
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        risks.sort(key=lambda r: severity_order.get(r.severity, 4))
        
        return risks[:limit]
    
    async def _generate_user_activity_report(
        self,
        start_date: datetime,
        end_date: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate user activity report"""
        
        # Get most active users
        active_users = await self.db.execute(
            select(
                GDPRAuditLog.actor_id,
                func.count(GDPRAuditLog.id).label("event_count")
            ).where(
                and_(
                    GDPRAuditLog.event_timestamp >= start_date,
                    GDPRAuditLog.event_timestamp <= end_date,
                    GDPRAuditLog.actor_id != None
                )
            ).group_by(GDPRAuditLog.actor_id)
            .order_by(func.count(GDPRAuditLog.id).desc())
            .limit(20)
        )
        
        top_users = [
            {"user_id": row[0], "event_count": row[1]}
            for row in active_users
        ]
        
        # Get event distribution by hour
        hourly_events = await self.db.execute(
            select(
                extract('hour', GDPRAuditLog.event_timestamp).label("hour"),
                func.count(GDPRAuditLog.id).label("count")
            ).where(
                and_(
                    GDPRAuditLog.event_timestamp >= start_date,
                    GDPRAuditLog.event_timestamp <= end_date
                )
            ).group_by("hour").order_by("hour")
        )
        
        hourly_distribution = [
            {"hour": int(row[0]), "count": row[1]}
            for row in hourly_events
        ]
        
        # Get common actions
        common_actions = await self.db.execute(
            select(
                GDPRAuditLog.action,
                func.count(GDPRAuditLog.id).label("count")
            ).where(
                and_(
                    GDPRAuditLog.event_timestamp >= start_date,
                    GDPRAuditLog.event_timestamp <= end_date
                )
            ).group_by(GDPRAuditLog.action)
            .order_by(func.count(GDPRAuditLog.id).desc())
            .limit(10)
        )
        
        top_actions = [
            {"action": row[0], "count": row[1]}
            for row in common_actions
        ]
        
        return {
            "reporting_period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "most_active_users": top_users,
            "hourly_activity_pattern": hourly_distribution,
            "common_actions": top_actions,
            "peak_activity_hour": max(hourly_distribution, key=lambda x: x["count"])["hour"] if hourly_distribution else None
        }
    
    async def _format_report(
        self,
        report_data: Dict[str, Any],
        report_type: AuditReportType,
        format: AuditReportFormat
    ) -> Optional[bytes]:
        """Format report in requested format"""
        
        if format == AuditReportFormat.JSON:
            return None  # Data already in JSON format
        elif format == AuditReportFormat.CSV:
            return self._format_as_csv(report_data, report_type)
        elif format == AuditReportFormat.PDF:
            return await self._format_as_pdf(report_data, report_type)
        elif format == AuditReportFormat.EXCEL:
            return self._format_as_excel(report_data, report_type)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _format_as_csv(
        self,
        report_data: Dict[str, Any],
        report_type: AuditReportType
    ) -> bytes:
        """Format report as CSV"""
        output = StringIO()
        
        if report_type == AuditReportType.COMPLIANCE_OVERVIEW:
            # Create summary CSV
            writer = csv.writer(output)
            writer.writerow(["Metric", "Value"])
            writer.writerow(["Reporting Period Start", report_data["summary"]["reporting_period"]["start"]])
            writer.writerow(["Reporting Period End", report_data["summary"]["reporting_period"]["end"]])
            writer.writerow(["Total Events", report_data["summary"]["total_events"]])
            writer.writerow(["Compliance Score", f"{report_data['summary']['compliance_score']['overall_score']:.2f}%"])
            writer.writerow(["High Risk Incidents", report_data["summary"]["high_risk_incidents"]])
            
            # Add event statistics
            writer.writerow([])
            writer.writerow(["Event Type", "Count"])
            for event_type, count in report_data["event_statistics"]["events_by_type"].items():
                writer.writerow([event_type, count])
        
        return output.getvalue().encode('utf-8')
    
    async def _format_as_pdf(
        self,
        report_data: Dict[str, Any],
        report_type: AuditReportType
    ) -> bytes:
        """Format report as PDF"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            textColor=colors.HexColor('#2E3440')
        )
        
        title = Paragraph(f"GDPR Compliance - {report_type.value.replace('_', ' ').title()}", title_style)
        story.append(title)
        story.append(Spacer(1, 0.5 * inch))
        
        # Report metadata
        metadata_data = [
            ["Generated At", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")],
            ["Reporting Period", f"{report_data['summary']['reporting_period']['start']} to {report_data['summary']['reporting_period']['end']}"],
            ["Report Type", report_type.value.replace('_', ' ').title()]
        ]
        
        metadata_table = Table(metadata_data, colWidths=[2 * inch, 4 * inch])
        metadata_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.grey),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(metadata_table)
        story.append(Spacer(1, 0.3 * inch))
        
        # Summary section
        summary_style = ParagraphStyle(
            'Summary',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#4C566A')
        )
        
        story.append(Paragraph("Executive Summary", summary_style))
        story.append(Spacer(1, 0.2 * inch))
        
        # Add content based on report type
        if report_type == AuditReportType.COMPLIANCE_OVERVIEW:
            await self._add_compliance_overview_to_pdf(story, report_data)
        
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    
    def _format_as_excel(
        self,
        report_data: Dict[str, Any],
        report_type: AuditReportType
    ) -> bytes:
        """Format report as Excel"""
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Summary sheet
            summary_df = pd.DataFrame([
                ["Report Type", report_type.value],
                ["Generated At", datetime.utcnow().isoformat()],
                ["Period Start", report_data["summary"]["reporting_period"]["start"]],
                ["Period End", report_data["summary"]["reporting_period"]["end"]],
                ["Total Events", report_data["summary"]["total_events"]],
                ["Compliance Score", f"{report_data['summary']['compliance_score']['overall_score']:.2f}%"]
            ], columns=["Metric", "Value"])
            
            summary_df.to_excel(writer, sheet_name="Summary", index=False)
            
            # Event statistics sheet
            if "event_statistics" in report_data:
                events_df = pd.DataFrame(
                    [(k, v) for k, v in report_data["event_statistics"]["events_by_type"].items()],
                    columns=["Event Type", "Count"]
                )
                events_df.to_excel(writer, sheet_name="Event Statistics", index=False)
            
            # Risk assessment sheet
            if "risk_indicators" in report_data:
                risks_data = []
                for risk in report_data["risk_indicators"]:
                    risks_data.append([
                        risk["risk_id"],
                        risk["category"],
                        risk["severity"],
                        risk["description"],
                        risk["impact"],
                        risk["mitigation"]
                    ])
                
                risks_df = pd.DataFrame(
                    risks_data,
                    columns=["Risk ID", "Category", "Severity", "Description", "Impact", "Mitigation"]
                )
                risks_df.to_excel(writer, sheet_name="Risk Assessment", index=False)
        
        output.seek(0)
        return output.getvalue()
    
    async def _add_compliance_overview_to_pdf(
        self,
        story: List,
        report_data: Dict[str, Any]
    ):
        """Add compliance overview content to PDF"""
        
        # Compliance Score
        score_data = [
            ["Category", "Score"],
            ["Overall Compliance", f"{report_data['compliance_scorecard']['overall_score']:.2f}%"],
            ["Data Request Handling", f"{report_data['compliance_scorecard']['category_scores']['data_request_handling']:.2f}%"],
            ["Consent Management", f"{report_data['compliance_scorecard']['category_scores']['consent_management']:.2f}%"],
            ["Data Retention", f"{report_data['compliance_scorecard']['category_scores']['data_retention']:.2f}%"],
            ["Security Practices", f"{report_data['compliance_scorecard']['category_scores']['security_practices']:.2f}%"]
        ]
        
        score_table = Table(score_data, colWidths=[3 * inch, 2 * inch])
        score_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(score_table)
        story.append(Spacer(1, 0.3 * inch))
        
        # Risk Indicators
        if report_data["risk_indicators"]:
            story.append(Paragraph("Risk Indicators", self.styles['Heading2']))
            story.append(Spacer(1, 0.1 * inch))
            
            for risk in report_data["risk_indicators"][:3]:  # Top 3 risks
                risk_text = f"<b>{risk['risk_id']}</b> - {risk['severity'].upper()}: {risk['description']}"
                story.append(Paragraph(risk_text, self.styles['Normal']))
                story.append(Paragraph(f"Impact: {risk['impact']}", self.styles['Normal']))
                story.append(Paragraph(f"Mitigation: {risk['mitigation']}", self.styles['Normal']))
                story.append(Spacer(1, 0.1 * inch))
    
    async def _generate_recommendations(
        self,
        compliance_score: ComplianceScoreCard,
        risks: List[RiskAssessment]
    ) -> List[str]:
        """Generate recommendations based on compliance score and risks"""
        
        recommendations = []
        
        # Score-based recommendations
        if compliance_score.overall_score < 70:
            recommendations.append("Urgent: Overall compliance score is below acceptable threshold. Immediate action required.")
        
        if compliance_score.category_scores.get("data_request_handling", 100) < 80:
            recommendations.append("Improve data request response times to meet GDPR 30-day deadline.")
        
        if compliance_score.category_scores.get("consent_management", 100) < 80:
            recommendations.append("Review consent collection process and ensure explicit consent for all data processing.")
        
        # Risk-based recommendations
        high_risks = [r for r in risks if r.severity in ["critical", "high"]]
        if high_risks:
            recommendations.append(f"Address {len(high_risks)} high/critical risks immediately.")
        
        # General recommendations
        recommendations.extend([
            "Conduct regular GDPR training for all staff handling personal data.",
            "Review and update data retention policies quarterly.",
            "Perform monthly audits of data access logs.",
            "Ensure all third-party processors have valid DPAs in place."
        ])
        
        return recommendations[:5]  # Top 5 recommendations
    
    def _get_compliance_grade(self, score: float) -> str:
        """Get compliance grade based on score"""
        if score >= 95:
            return "A+"
        elif score >= 90:
            return "A"
        elif score >= 85:
            return "B+"
        elif score >= 80:
            return "B"
        elif score >= 75:
            return "C+"
        elif score >= 70:
            return "C"
        elif score >= 65:
            return "D"
        else:
            return "F"
    
    async def _calculate_request_handling_score(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> float:
        """Calculate score for data request handling"""
        
        # Get requests completed within 30 days
        result = await self.db.execute(
            select(
                func.count(DataRequest.id).label("total"),
                func.count(
                    func.case(
                        (extract('epoch', DataRequest.completed_at - DataRequest.requested_at) <= 30 * 24 * 3600, 1),
                        else_=None
                    )
                ).label("on_time")
            ).where(
                and_(
                    DataRequest.requested_at >= start_date,
                    DataRequest.requested_at <= end_date,
                    DataRequest.completed_at != None
                )
            )
        )
        
        row = result.first()
        if row and row.total > 0:
            return (row.on_time / row.total) * 100
        return 100.0  # No requests means perfect score
    
    async def _calculate_consent_management_score(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> float:
        """Calculate consent management score"""
        
        # Check for explicit consents vs implicit
        result = await self.db.execute(
            select(
                func.count(UserConsent.id).label("total"),
                func.count(
                    func.case(
                        (UserConsent.consent_given == True, 1),
                        else_=None
                    )
                ).label("explicit")
            ).where(
                and_(
                    UserConsent.given_at >= start_date,
                    UserConsent.given_at <= end_date
                )
            )
        )
        
        row = result.first()
        if row and row.total > 0:
            return (row.explicit / row.total) * 100
        return 100.0
    
    async def _calculate_retention_compliance_score(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> float:
        """Calculate data retention compliance score"""
        
        # Check if retention policies are being executed
        result = await self.db.execute(
            select(func.count(DataRetentionRule.id)).where(
                DataRetentionRule.is_active == True
            )
        )
        
        active_rules = result.scalar() or 0
        
        # Base score on having active retention rules
        if active_rules == 0:
            return 50.0  # Penalty for no retention rules
        elif active_rules < 5:
            return 75.0  # Some rules but not comprehensive
        else:
            return 95.0  # Good retention policy coverage
    
    async def _calculate_security_score(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> float:
        """Calculate security practices score"""
        
        # Check for security incidents
        result = await self.db.execute(
            select(func.count(GDPRAuditLog.id)).where(
                and_(
                    GDPRAuditLog.event_timestamp >= start_date,
                    GDPRAuditLog.event_timestamp <= end_date,
                    GDPRAuditLog.event_type.in_(["unauthorized_access", "data_breach", "security_incident"])
                )
            )
        )
        
        incidents = result.scalar() or 0
        
        # Deduct points for security incidents
        base_score = 100.0
        score = base_score - (incidents * 5)  # -5 points per incident
        
        return max(score, 0.0)  # Don't go below 0
    
    async def _check_missing_consent_risk(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Optional[RiskAssessment]:
        """Check for missing consent records risk"""
        
        # This would check for data processing without corresponding consent
        # For now, return None as this requires cross-service data
        return None
    
    async def _check_unauthorized_access_risk(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Optional[RiskAssessment]:
        """Check for unauthorized access attempts"""
        
        result = await self.db.execute(
            select(func.count(GDPRAuditLog.id)).where(
                and_(
                    GDPRAuditLog.event_timestamp >= start_date,
                    GDPRAuditLog.event_timestamp <= end_date,
                    GDPRAuditLog.event_type == "unauthorized_access"
                )
            )
        )
        
        unauthorized_count = result.scalar() or 0
        
        if unauthorized_count > 0:
            return RiskAssessment(
                risk_id="RISK_004",
                category="security",
                severity="high" if unauthorized_count > 10 else "medium",
                description=f"{unauthorized_count} unauthorized access attempts detected",
                impact="Potential data breach or insider threat",
                likelihood="possible",
                mitigation="Review access controls and investigate incidents",
                detected_at=datetime.utcnow()
            )
        
        return None
    
    async def _check_retention_violations(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Optional[RiskAssessment]:
        """Check for data retention violations"""
        
        # Check for overdue retention executions
        result = await self.db.execute(
            select(func.count(DataRetentionRule.id)).where(
                and_(
                    DataRetentionRule.is_active == True,
                    DataRetentionRule.next_run < datetime.utcnow() - timedelta(days=7)
                )
            )
        )
        
        overdue_rules = result.scalar() or 0
        
        if overdue_rules > 0:
            return RiskAssessment(
                risk_id="RISK_005",
                category="data_retention",
                severity="medium",
                description=f"{overdue_rules} retention policies overdue for execution",
                impact="Data kept longer than retention policy allows",
                likelihood="certain",
                mitigation="Execute overdue retention policies immediately",
                detected_at=datetime.utcnow()
            )
        
        return None
    
    async def generate_compliance_trends(
        self,
        period_months: int = 6
    ) -> List[ComplianceTrend]:
        """Generate compliance trends over time"""
        
        trends = []
        end_date = datetime.utcnow()
        
        for i in range(period_months):
            # Calculate start and end of month
            month_end = end_date.replace(day=1) - timedelta(days=1)
            month_start = month_end.replace(day=1)
            
            # Get compliance score for the month
            score = await self._calculate_compliance_score(month_start, month_end)
            
            trends.append(ComplianceTrend(
                period=month_start.strftime("%Y-%m"),
                compliance_score=score.overall_score,
                total_events=await self._get_month_event_count(month_start, month_end),
                high_risk_incidents=len(await self._identify_top_risks(month_start, month_end))
            ))
            
            # Move to previous month
            end_date = month_start - timedelta(days=1)
        
        return list(reversed(trends))  # Return in chronological order
    
    async def _get_month_event_count(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> int:
        """Get total event count for a month"""
        
        result = await self.db.execute(
            select(func.count(GDPRAuditLog.id)).where(
                and_(
                    GDPRAuditLog.event_timestamp >= start_date,
                    GDPRAuditLog.event_timestamp <= end_date
                )
            )
        )
        
        return result.scalar() or 0


import uuid  # Add this import at the top