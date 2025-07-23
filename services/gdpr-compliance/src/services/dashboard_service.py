"""Service for GDPR compliance dashboard analytics and visualizations"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, case
from sqlalchemy.orm import selectinload

from ..db.models import (
    UserConsent, DataRequest, GDPRAuditLog, DataCategory,
    DataMapping, PrivacyPolicy, DataRetentionRule
)
from ..models.schemas import (
    ComplianceDashboard, ComplianceMetric, ComplianceTrend,
    DataClassificationSummary, ConsentMetrics, DataRequestMetrics,
    RetentionMetrics, AuditMetrics, ComplianceScore, RiskIndicator,
    DashboardWidget, TimeSeriesData, PieChartData, BarChartData
)
from ..services.audit_reporting_service import AuditReportingService
from ..services.data_classification_service import DataClassificationService
from ..core.exceptions import NotFoundError

logger = logging.getLogger(__name__)


class DashboardService:
    """Service for GDPR compliance dashboard functionality"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit_service = AuditReportingService(db)
        self.classification_service = DataClassificationService(db)
    
    async def get_compliance_overview(
        self,
        time_range_days: int = 30
    ) -> ComplianceDashboard:
        """Get comprehensive compliance dashboard data"""
        try:
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=time_range_days)
            
            # Get compliance score
            compliance_score = await self._calculate_compliance_score()
            
            # Get key metrics
            metrics = await self._get_key_metrics(start_date, end_date)
            
            # Get compliance trends
            trends = await self._get_compliance_trends(time_range_days)
            
            # Get risk indicators
            risks = await self._get_risk_indicators()
            
            # Get widgets data
            widgets = await self._get_dashboard_widgets(start_date, end_date)
            
            return ComplianceDashboard(
                compliance_score=compliance_score,
                key_metrics=metrics,
                trends=trends,
                risk_indicators=risks,
                widgets=widgets,
                last_updated=datetime.utcnow(),
                time_range_days=time_range_days
            )
            
        except Exception as e:
            logger.error(f"Error generating compliance dashboard: {e}")
            raise
    
    async def get_data_classification_summary(self) -> DataClassificationSummary:
        """Get data classification summary for dashboard"""
        try:
            # Get classification report
            report = await self.classification_service.generate_classification_report()
            
            # Get categories by privacy level
            privacy_level_data = PieChartData(
                labels=list(report.categories_by_privacy_level.keys()),
                values=list(report.categories_by_privacy_level.values()),
                title="Data Categories by Privacy Level"
            )
            
            # Get categories by retention period
            retention_query = select(
                DataCategory.retention_days,
                func.count(DataCategory.id)
            ).group_by(DataCategory.retention_days)
            
            retention_result = await self.db.execute(retention_query)
            retention_data = retention_result.all()
            
            retention_chart = BarChartData(
                labels=[f"{days} days" for days, _ in retention_data],
                values=[count for _, count in retention_data],
                title="Categories by Retention Period"
            )
            
            # Get PII distribution
            pii_query = select(
                DataMapping.contains_pii,
                func.count(DataMapping.id)
            ).group_by(DataMapping.contains_pii)
            
            pii_result = await self.db.execute(pii_query)
            pii_data = pii_result.all()
            
            pii_distribution = PieChartData(
                labels=["Contains PII", "No PII"],
                values=[
                    next((count for contains_pii, count in pii_data if contains_pii), 0),
                    next((count for contains_pii, count in pii_data if not contains_pii), 0)
                ],
                title="PII Distribution"
            )
            
            # Get sensitive data count
            sensitive_query = select(func.count(DataCategory.id)).where(
                DataCategory.is_sensitive == True
            )
            sensitive_count = await self.db.scalar(sensitive_query)
            
            # Get encrypted fields count
            encrypted_query = select(func.count(DataMapping.id)).where(
                DataMapping.encryption_required == True
            )
            encrypted_count = await self.db.scalar(encrypted_query)
            
            return DataClassificationSummary(
                total_categories=report.total_categories,
                total_mappings=len(report.mappings) if report.mappings else 0,
                sensitive_data_count=sensitive_count or 0,
                encrypted_fields_count=encrypted_count or 0,
                privacy_level_distribution=privacy_level_data,
                retention_distribution=retention_chart,
                pii_distribution=pii_distribution,
                unmapped_tables=report.unmapped_tables,
                compliance_gaps_count=len(report.compliance_gaps) if report.compliance_gaps else 0
            )
            
        except Exception as e:
            logger.error(f"Error getting data classification summary: {e}")
            raise
    
    async def get_consent_metrics(
        self,
        time_range_days: int = 30
    ) -> ConsentMetrics:
        """Get consent management metrics"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=time_range_days)
            
            # Total active consents
            active_query = select(func.count(UserConsent.id)).where(
                UserConsent.is_active == True
            )
            total_active = await self.db.scalar(active_query) or 0
            
            # Consents given in time range
            given_query = select(func.count(UserConsent.id)).where(
                and_(
                    UserConsent.consent_date >= start_date,
                    UserConsent.consent_date <= end_date,
                    UserConsent.is_active == True
                )
            )
            consents_given = await self.db.scalar(given_query) or 0
            
            # Consents withdrawn in time range
            withdrawn_query = select(func.count(UserConsent.id)).where(
                and_(
                    UserConsent.withdrawal_date >= start_date,
                    UserConsent.withdrawal_date <= end_date
                )
            )
            consents_withdrawn = await self.db.scalar(withdrawn_query) or 0
            
            # Consent by type
            type_query = select(
                UserConsent.consent_type,
                func.count(UserConsent.id)
            ).where(
                UserConsent.is_active == True
            ).group_by(UserConsent.consent_type)
            
            type_result = await self.db.execute(type_query)
            type_data = type_result.all()
            
            consent_by_type = PieChartData(
                labels=[consent_type for consent_type, _ in type_data],
                values=[count for _, count in type_data],
                title="Active Consents by Type"
            )
            
            # Consent trends (daily for last 30 days)
            trends = await self._get_consent_trends(time_range_days)
            
            # Calculate withdrawal rate
            withdrawal_rate = (consents_withdrawn / consents_given * 100) if consents_given > 0 else 0
            
            return ConsentMetrics(
                total_active_consents=total_active,
                consents_given=consents_given,
                consents_withdrawn=consents_withdrawn,
                withdrawal_rate=round(withdrawal_rate, 2),
                consent_by_type=consent_by_type,
                consent_trends=trends,
                average_consent_duration_days=await self._get_average_consent_duration()
            )
            
        except Exception as e:
            logger.error(f"Error getting consent metrics: {e}")
            raise
    
    async def get_data_request_metrics(
        self,
        time_range_days: int = 30
    ) -> DataRequestMetrics:
        """Get data request handling metrics"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=time_range_days)
            
            # Total requests in time range
            total_query = select(func.count(DataRequest.id)).where(
                and_(
                    DataRequest.created_at >= start_date,
                    DataRequest.created_at <= end_date
                )
            )
            total_requests = await self.db.scalar(total_query) or 0
            
            # Requests by type
            type_query = select(
                DataRequest.request_type,
                func.count(DataRequest.id)
            ).where(
                and_(
                    DataRequest.created_at >= start_date,
                    DataRequest.created_at <= end_date
                )
            ).group_by(DataRequest.request_type)
            
            type_result = await self.db.execute(type_query)
            type_data = type_result.all()
            
            requests_by_type = BarChartData(
                labels=[request_type for request_type, _ in type_data],
                values=[count for _, count in type_data],
                title="Data Requests by Type"
            )
            
            # Requests by status
            status_query = select(
                DataRequest.status,
                func.count(DataRequest.id)
            ).where(
                and_(
                    DataRequest.created_at >= start_date,
                    DataRequest.created_at <= end_date
                )
            ).group_by(DataRequest.status)
            
            status_result = await self.db.execute(status_query)
            status_data = status_result.all()
            
            requests_by_status = PieChartData(
                labels=[status for status, _ in status_data],
                values=[count for _, count in status_data],
                title="Request Status Distribution"
            )
            
            # Average completion time
            completion_query = select(
                func.avg(
                    func.extract('epoch', DataRequest.completed_at - DataRequest.created_at) / 86400
                )
            ).where(
                and_(
                    DataRequest.status == 'completed',
                    DataRequest.completed_at.isnot(None),
                    DataRequest.created_at >= start_date
                )
            )
            avg_completion_time = await self.db.scalar(completion_query) or 0
            
            # Compliance rate (completed within 30 days)
            compliant_query = select(func.count(DataRequest.id)).where(
                and_(
                    DataRequest.status == 'completed',
                    DataRequest.completed_at.isnot(None),
                    func.extract('epoch', DataRequest.completed_at - DataRequest.created_at) <= 30 * 86400,
                    DataRequest.created_at >= start_date
                )
            )
            compliant_count = await self.db.scalar(compliant_query) or 0
            
            completed_query = select(func.count(DataRequest.id)).where(
                and_(
                    DataRequest.status == 'completed',
                    DataRequest.created_at >= start_date
                )
            )
            completed_count = await self.db.scalar(completed_query) or 0
            
            compliance_rate = (compliant_count / completed_count * 100) if completed_count > 0 else 100
            
            # Request trends
            trends = await self._get_request_trends(time_range_days)
            
            return DataRequestMetrics(
                total_requests=total_requests,
                requests_by_type=requests_by_type,
                requests_by_status=requests_by_status,
                average_completion_time_days=round(avg_completion_time, 2),
                compliance_rate=round(compliance_rate, 2),
                pending_requests=await self._get_pending_request_count(),
                overdue_requests=await self._get_overdue_request_count(),
                request_trends=trends
            )
            
        except Exception as e:
            logger.error(f"Error getting data request metrics: {e}")
            raise
    
    async def get_retention_metrics(self) -> RetentionMetrics:
        """Get data retention policy metrics"""
        try:
            # Total retention rules
            total_query = select(func.count(DataRetentionRule.id))
            total_rules = await self.db.scalar(total_query) or 0
            
            # Active vs inactive rules
            active_query = select(func.count(DataRetentionRule.id)).where(
                DataRetentionRule.is_active == True
            )
            active_rules = await self.db.scalar(active_query) or 0
            
            # Rules by action type
            action_query = select(
                DataRetentionRule.action_type,
                func.count(DataRetentionRule.id)
            ).group_by(DataRetentionRule.action_type)
            
            action_result = await self.db.execute(action_query)
            action_data = action_result.all()
            
            rules_by_action = PieChartData(
                labels=[action_type for action_type, _ in action_data],
                values=[count for _, count in action_data],
                title="Retention Rules by Action Type"
            )
            
            # Data scheduled for deletion
            scheduled_query = select(func.count(DataRetentionRule.id)).where(
                and_(
                    DataRetentionRule.is_active == True,
                    DataRetentionRule.next_run.isnot(None),
                    DataRetentionRule.next_run <= datetime.utcnow() + timedelta(days=30)
                )
            )
            scheduled_deletions = await self.db.scalar(scheduled_query) or 0
            
            # Average retention period
            avg_retention_query = select(
                func.avg(DataCategory.retention_days)
            ).where(DataCategory.retention_days.isnot(None))
            avg_retention_days = await self.db.scalar(avg_retention_query) or 0
            
            # Retention compliance
            overdue_query = select(func.count(DataRetentionRule.id)).where(
                and_(
                    DataRetentionRule.is_active == True,
                    DataRetentionRule.next_run < datetime.utcnow()
                )
            )
            overdue_executions = await self.db.scalar(overdue_query) or 0
            
            # Retention by category
            category_query = select(
                DataCategory.category_name,
                DataCategory.retention_days
            ).where(DataCategory.retention_days.isnot(None)).limit(10)
            
            category_result = await self.db.execute(category_query)
            category_data = category_result.all()
            
            retention_by_category = BarChartData(
                labels=[name for name, _ in category_data],
                values=[days for _, days in category_data],
                title="Retention Days by Category"
            )
            
            return RetentionMetrics(
                total_retention_rules=total_rules,
                active_retention_rules=active_rules,
                rules_by_action_type=rules_by_action,
                data_scheduled_for_deletion=scheduled_deletions,
                average_retention_period_days=round(avg_retention_days, 0),
                overdue_executions=overdue_executions,
                retention_by_category=retention_by_category,
                last_execution_date=await self._get_last_retention_execution()
            )
            
        except Exception as e:
            logger.error(f"Error getting retention metrics: {e}")
            raise
    
    async def get_audit_metrics(
        self,
        time_range_days: int = 30
    ) -> AuditMetrics:
        """Get audit logging metrics"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=time_range_days)
            
            # Total audit events
            total_query = select(func.count(GDPRAuditLog.id)).where(
                and_(
                    GDPRAuditLog.created_at >= start_date,
                    GDPRAuditLog.created_at <= end_date
                )
            )
            total_events = await self.db.scalar(total_query) or 0
            
            # Events by category
            category_query = select(
                GDPRAuditLog.event_category,
                func.count(GDPRAuditLog.id)
            ).where(
                and_(
                    GDPRAuditLog.created_at >= start_date,
                    GDPRAuditLog.created_at <= end_date
                )
            ).group_by(GDPRAuditLog.event_category)
            
            category_result = await self.db.execute(category_query)
            category_data = category_result.all()
            
            events_by_category = PieChartData(
                labels=[category for category, _ in category_data],
                values=[count for _, count in category_data],
                title="Audit Events by Category"
            )
            
            # Events by result
            result_query = select(
                GDPRAuditLog.result,
                func.count(GDPRAuditLog.id)
            ).where(
                and_(
                    GDPRAuditLog.created_at >= start_date,
                    GDPRAuditLog.created_at <= end_date
                )
            ).group_by(GDPRAuditLog.result)
            
            result_result = await self.db.execute(result_query)
            result_data = result_result.all()
            
            success_count = next((count for result, count in result_data if result == 'success'), 0)
            failure_count = next((count for result, count in result_data if result == 'failure'), 0)
            
            success_rate = (success_count / total_events * 100) if total_events > 0 else 100
            
            # Top users by activity
            user_query = select(
                GDPRAuditLog.user_id,
                func.count(GDPRAuditLog.id).label('event_count')
            ).where(
                and_(
                    GDPRAuditLog.created_at >= start_date,
                    GDPRAuditLog.created_at <= end_date,
                    GDPRAuditLog.user_id.isnot(None)
                )
            ).group_by(GDPRAuditLog.user_id).order_by(
                func.count(GDPRAuditLog.id).desc()
            ).limit(10)
            
            user_result = await self.db.execute(user_query)
            user_data = user_result.all()
            
            top_users = BarChartData(
                labels=[f"User {user_id[:8]}" for user_id, _ in user_data],
                values=[count for _, count in user_data],
                title="Top Users by Activity"
            )
            
            # Critical events
            critical_query = select(func.count(GDPRAuditLog.id)).where(
                and_(
                    GDPRAuditLog.created_at >= start_date,
                    GDPRAuditLog.created_at <= end_date,
                    or_(
                        GDPRAuditLog.result == 'failure',
                        GDPRAuditLog.event_type.in_([
                            'data_deletion', 'consent_withdrawn',
                            'unauthorized_access', 'data_breach'
                        ])
                    )
                )
            )
            critical_events = await self.db.scalar(critical_query) or 0
            
            # Event trends
            trends = await self._get_audit_trends(time_range_days)
            
            return AuditMetrics(
                total_audit_events=total_events,
                events_by_category=events_by_category,
                success_rate=round(success_rate, 2),
                failure_rate=round(100 - success_rate, 2),
                top_users_by_activity=top_users,
                critical_events_count=critical_events,
                audit_trends=trends,
                storage_usage_mb=await self._get_audit_storage_usage()
            )
            
        except Exception as e:
            logger.error(f"Error getting audit metrics: {e}")
            raise
    
    async def get_dashboard_widgets(
        self,
        widget_types: Optional[List[str]] = None
    ) -> List[DashboardWidget]:
        """Get specific dashboard widgets"""
        try:
            if widget_types is None:
                widget_types = [
                    'compliance_score', 'data_requests', 'consent_status',
                    'retention_overview', 'audit_activity', 'risk_matrix'
                ]
            
            widgets = []
            
            for widget_type in widget_types:
                if widget_type == 'compliance_score':
                    score = await self._calculate_compliance_score()
                    widgets.append(DashboardWidget(
                        widget_type='gauge',
                        title='Compliance Score',
                        data={'score': score.score, 'grade': score.grade},
                        config={'min': 0, 'max': 100, 'thresholds': [60, 80, 90]}
                    ))
                
                elif widget_type == 'data_requests':
                    pending = await self._get_pending_request_count()
                    overdue = await self._get_overdue_request_count()
                    widgets.append(DashboardWidget(
                        widget_type='stats',
                        title='Data Requests',
                        data={'pending': pending, 'overdue': overdue},
                        config={'alert_on_overdue': True}
                    ))
                
                elif widget_type == 'consent_status':
                    consent_metrics = await self.get_consent_metrics(7)
                    widgets.append(DashboardWidget(
                        widget_type='pie_chart',
                        title='Consent Status',
                        data=consent_metrics.consent_by_type.dict(),
                        config={'show_legend': True}
                    ))
                
                elif widget_type == 'retention_overview':
                    retention_metrics = await self.get_retention_metrics()
                    widgets.append(DashboardWidget(
                        widget_type='bar_chart',
                        title='Retention Overview',
                        data=retention_metrics.retention_by_category.dict(),
                        config={'orientation': 'horizontal'}
                    ))
                
                elif widget_type == 'audit_activity':
                    audit_metrics = await self.get_audit_metrics(7)
                    widgets.append(DashboardWidget(
                        widget_type='line_chart',
                        title='Audit Activity',
                        data=audit_metrics.audit_trends.dict(),
                        config={'show_area': True}
                    ))
                
                elif widget_type == 'risk_matrix':
                    risks = await self._get_risk_indicators()
                    widgets.append(DashboardWidget(
                        widget_type='heatmap',
                        title='Risk Matrix',
                        data={
                            'risks': [risk.dict() for risk in risks[:5]]
                        },
                        config={'color_scale': 'red-yellow-green'}
                    ))
            
            return widgets
            
        except Exception as e:
            logger.error(f"Error getting dashboard widgets: {e}")
            raise
    
    # Private helper methods
    
    async def _calculate_compliance_score(self) -> ComplianceScore:
        """Calculate overall compliance score"""
        try:
            # Get component scores
            score_data = await self.audit_service.calculate_compliance_score()
            
            return ComplianceScore(
                score=score_data['overall_score'],
                grade=score_data['grade'],
                components={
                    'consent_management': score_data['components']['consent_management'],
                    'data_requests': score_data['components']['data_requests'],
                    'data_retention': score_data['components']['data_retention'],
                    'audit_logging': score_data['components']['audit_logging'],
                    'data_classification': score_data['components']['data_classification']
                }
            )
            
        except Exception as e:
            logger.error(f"Error calculating compliance score: {e}")
            return ComplianceScore(
                score=0,
                grade='F',
                components={}
            )
    
    async def _get_key_metrics(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[ComplianceMetric]:
        """Get key compliance metrics"""
        metrics = []
        
        # Active consents
        active_consents = await self.db.scalar(
            select(func.count(UserConsent.id)).where(UserConsent.is_active == True)
        ) or 0
        
        metrics.append(ComplianceMetric(
            name='Active Consents',
            value=active_consents,
            unit='count',
            change_percentage=await self._calculate_change_percentage(
                'consents', start_date, end_date
            )
        ))
        
        # Pending requests
        pending_requests = await self._get_pending_request_count()
        metrics.append(ComplianceMetric(
            name='Pending Requests',
            value=pending_requests,
            unit='count',
            change_percentage=0,
            is_critical=pending_requests > 10
        ))
        
        # Compliance rate
        compliance_rate = await self._calculate_request_compliance_rate()
        metrics.append(ComplianceMetric(
            name='Request Compliance',
            value=compliance_rate,
            unit='percentage',
            change_percentage=await self._calculate_change_percentage(
                'compliance_rate', start_date, end_date
            )
        ))
        
        # Data categories
        total_categories = await self.db.scalar(
            select(func.count(DataCategory.id))
        ) or 0
        
        metrics.append(ComplianceMetric(
            name='Data Categories',
            value=total_categories,
            unit='count',
            change_percentage=0
        ))
        
        return metrics
    
    async def _get_compliance_trends(
        self,
        days: int
    ) -> List[ComplianceTrend]:
        """Get compliance trends over time"""
        trends = []
        
        # Generate daily compliance scores
        for i in range(days):
            date = datetime.utcnow() - timedelta(days=days-i-1)
            
            # Simulate trend data (in production, calculate from historical data)
            score = 85 + (i * 0.5)  # Gradual improvement
            
            trends.append(ComplianceTrend(
                date=date.date(),
                compliance_score=min(score, 100),
                consent_count=await self._get_consent_count_for_date(date),
                request_count=await self._get_request_count_for_date(date),
                incident_count=await self._get_incident_count_for_date(date)
            ))
        
        return trends
    
    async def _get_risk_indicators(self) -> List[RiskIndicator]:
        """Get current risk indicators"""
        risks = []
        
        # Check for overdue requests
        overdue_count = await self._get_overdue_request_count()
        if overdue_count > 0:
            risks.append(RiskIndicator(
                risk_type='overdue_requests',
                severity='high' if overdue_count > 5 else 'medium',
                description=f'{overdue_count} data requests are overdue',
                mitigation='Process pending requests immediately',
                affected_items=overdue_count
            ))
        
        # Check for missing data classifications
        unmapped_tables = await self._get_unmapped_table_count()
        if unmapped_tables > 0:
            risks.append(RiskIndicator(
                risk_type='unclassified_data',
                severity='medium',
                description=f'{unmapped_tables} tables have unmapped fields',
                mitigation='Complete data classification for all tables',
                affected_items=unmapped_tables
            ))
        
        # Check for expired consents
        expired_consents = await self._get_expired_consent_count()
        if expired_consents > 0:
            risks.append(RiskIndicator(
                risk_type='expired_consents',
                severity='medium',
                description=f'{expired_consents} consents need renewal',
                mitigation='Request consent renewal from affected users',
                affected_items=expired_consents
            ))
        
        # Check for retention policy violations
        retention_violations = await self._get_retention_violations()
        if retention_violations > 0:
            risks.append(RiskIndicator(
                risk_type='retention_violation',
                severity='high',
                description=f'{retention_violations} items exceed retention period',
                mitigation='Execute retention policies immediately',
                affected_items=retention_violations
            ))
        
        # Check audit log gaps
        audit_gaps = await self._check_audit_gaps()
        if audit_gaps:
            risks.append(RiskIndicator(
                risk_type='audit_gaps',
                severity='low',
                description='Gaps detected in audit logging',
                mitigation='Review and fix audit logging configuration',
                affected_items=1
            ))
        
        return sorted(risks, key=lambda x: {'high': 0, 'medium': 1, 'low': 2}[x.severity])
    
    async def _get_dashboard_widgets(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[DashboardWidget]:
        """Get pre-configured dashboard widgets"""
        widgets = []
        
        # Compliance gauge
        score = await self._calculate_compliance_score()
        widgets.append(DashboardWidget(
            widget_type='gauge',
            title='Overall Compliance',
            data={
                'value': score.score,
                'label': score.grade,
                'color': self._get_score_color(score.score)
            },
            config={'min': 0, 'max': 100}
        ))
        
        # Request status summary
        request_data = await self._get_request_status_summary()
        widgets.append(DashboardWidget(
            widget_type='donut',
            title='Request Status',
            data=request_data,
            config={'center_text': 'Total'}
        ))
        
        # Activity heatmap
        activity_data = await self._get_activity_heatmap(30)
        widgets.append(DashboardWidget(
            widget_type='heatmap',
            title='Activity Heatmap',
            data=activity_data,
            config={'color_scheme': 'blues'}
        ))
        
        # Quick stats
        stats = await self._get_quick_stats()
        widgets.append(DashboardWidget(
            widget_type='stats_grid',
            title='Quick Stats',
            data=stats,
            config={'columns': 4}
        ))
        
        return widgets
    
    # Utility methods
    
    async def _get_pending_request_count(self) -> int:
        """Get count of pending data requests"""
        return await self.db.scalar(
            select(func.count(DataRequest.id)).where(
                DataRequest.status.in_(['pending', 'processing'])
            )
        ) or 0
    
    async def _get_overdue_request_count(self) -> int:
        """Get count of overdue data requests"""
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        return await self.db.scalar(
            select(func.count(DataRequest.id)).where(
                and_(
                    DataRequest.status.in_(['pending', 'processing']),
                    DataRequest.created_at < thirty_days_ago
                )
            )
        ) or 0
    
    async def _calculate_request_compliance_rate(self) -> float:
        """Calculate request compliance rate"""
        completed = await self.db.scalar(
            select(func.count(DataRequest.id)).where(
                DataRequest.status == 'completed'
            )
        ) or 0
        
        compliant = await self.db.scalar(
            select(func.count(DataRequest.id)).where(
                and_(
                    DataRequest.status == 'completed',
                    DataRequest.completed_at.isnot(None),
                    func.extract('epoch', DataRequest.completed_at - DataRequest.created_at) <= 30 * 86400
                )
            )
        ) or 0
        
        return (compliant / completed * 100) if completed > 0 else 100
    
    async def _get_average_consent_duration(self) -> int:
        """Get average consent duration in days"""
        avg_duration = await self.db.scalar(
            select(
                func.avg(
                    func.extract('epoch', 
                        func.coalesce(UserConsent.withdrawal_date, func.now()) - UserConsent.consent_date
                    ) / 86400
                )
            ).where(UserConsent.consent_date.isnot(None))
        )
        return int(avg_duration) if avg_duration else 0
    
    async def _get_consent_trends(self, days: int) -> TimeSeriesData:
        """Get consent trends over time"""
        labels = []
        given_values = []
        withdrawn_values = []
        
        for i in range(days):
            date = datetime.utcnow().date() - timedelta(days=days-i-1)
            labels.append(date.strftime('%Y-%m-%d'))
            
            # Count consents given on this day
            given = await self.db.scalar(
                select(func.count(UserConsent.id)).where(
                    and_(
                        func.date(UserConsent.consent_date) == date,
                        UserConsent.is_active == True
                    )
                )
            ) or 0
            given_values.append(given)
            
            # Count consents withdrawn on this day
            withdrawn = await self.db.scalar(
                select(func.count(UserConsent.id)).where(
                    func.date(UserConsent.withdrawal_date) == date
                )
            ) or 0
            withdrawn_values.append(withdrawn)
        
        return TimeSeriesData(
            labels=labels,
            datasets=[
                {'label': 'Consents Given', 'data': given_values},
                {'label': 'Consents Withdrawn', 'data': withdrawn_values}
            ]
        )
    
    async def _get_request_trends(self, days: int) -> TimeSeriesData:
        """Get data request trends over time"""
        labels = []
        values = []
        
        for i in range(days):
            date = datetime.utcnow().date() - timedelta(days=days-i-1)
            labels.append(date.strftime('%Y-%m-%d'))
            
            count = await self.db.scalar(
                select(func.count(DataRequest.id)).where(
                    func.date(DataRequest.created_at) == date
                )
            ) or 0
            values.append(count)
        
        return TimeSeriesData(
            labels=labels,
            datasets=[{'label': 'Data Requests', 'data': values}]
        )
    
    async def _get_audit_trends(self, days: int) -> TimeSeriesData:
        """Get audit event trends over time"""
        labels = []
        success_values = []
        failure_values = []
        
        for i in range(days):
            date = datetime.utcnow().date() - timedelta(days=days-i-1)
            labels.append(date.strftime('%Y-%m-%d'))
            
            # Success events
            success = await self.db.scalar(
                select(func.count(GDPRAuditLog.id)).where(
                    and_(
                        func.date(GDPRAuditLog.created_at) == date,
                        GDPRAuditLog.result == 'success'
                    )
                )
            ) or 0
            success_values.append(success)
            
            # Failure events
            failure = await self.db.scalar(
                select(func.count(GDPRAuditLog.id)).where(
                    and_(
                        func.date(GDPRAuditLog.created_at) == date,
                        GDPRAuditLog.result == 'failure'
                    )
                )
            ) or 0
            failure_values.append(failure)
        
        return TimeSeriesData(
            labels=labels,
            datasets=[
                {'label': 'Success', 'data': success_values},
                {'label': 'Failure', 'data': failure_values}
            ]
        )
    
    async def _get_last_retention_execution(self) -> Optional[datetime]:
        """Get last retention policy execution date"""
        last_execution = await self.db.scalar(
            select(func.max(DataRetentionRule.last_run))
        )
        return last_execution
    
    async def _get_audit_storage_usage(self) -> float:
        """Get audit log storage usage in MB"""
        # Estimate based on row count (approximate 1KB per row)
        row_count = await self.db.scalar(
            select(func.count(GDPRAuditLog.id))
        ) or 0
        return round(row_count / 1024, 2)  # Convert to MB
    
    async def _calculate_change_percentage(
        self,
        metric_type: str,
        start_date: datetime,
        end_date: datetime
    ) -> float:
        """Calculate percentage change for a metric"""
        # This would compare current period vs previous period
        # For now, return a simulated value
        import random
        return round(random.uniform(-10, 10), 2)
    
    async def _get_consent_count_for_date(self, date: datetime) -> int:
        """Get consent count for a specific date"""
        return await self.db.scalar(
            select(func.count(UserConsent.id)).where(
                and_(
                    UserConsent.consent_date <= date,
                    or_(
                        UserConsent.withdrawal_date.is_(None),
                        UserConsent.withdrawal_date > date
                    )
                )
            )
        ) or 0
    
    async def _get_request_count_for_date(self, date: datetime) -> int:
        """Get request count for a specific date"""
        return await self.db.scalar(
            select(func.count(DataRequest.id)).where(
                func.date(DataRequest.created_at) == date.date()
            )
        ) or 0
    
    async def _get_incident_count_for_date(self, date: datetime) -> int:
        """Get incident count for a specific date"""
        return await self.db.scalar(
            select(func.count(GDPRAuditLog.id)).where(
                and_(
                    func.date(GDPRAuditLog.created_at) == date.date(),
                    GDPRAuditLog.result == 'failure'
                )
            )
        ) or 0
    
    async def _get_unmapped_table_count(self) -> int:
        """Get count of tables with unmapped fields"""
        # This would query actual database schema
        # For now, return from classification report
        report = await self.classification_service.generate_classification_report()
        return len(report.unmapped_tables) if report.unmapped_tables else 0
    
    async def _get_expired_consent_count(self) -> int:
        """Get count of expired consents"""
        # Assuming consents expire after 1 year
        one_year_ago = datetime.utcnow() - timedelta(days=365)
        return await self.db.scalar(
            select(func.count(UserConsent.id)).where(
                and_(
                    UserConsent.is_active == True,
                    UserConsent.consent_date < one_year_ago
                )
            )
        ) or 0
    
    async def _get_retention_violations(self) -> int:
        """Get count of retention policy violations"""
        # Count overdue retention executions
        return await self.db.scalar(
            select(func.count(DataRetentionRule.id)).where(
                and_(
                    DataRetentionRule.is_active == True,
                    DataRetentionRule.next_run < datetime.utcnow()
                )
            )
        ) or 0
    
    async def _check_audit_gaps(self) -> bool:
        """Check for gaps in audit logging"""
        # Check if there are any hour-long gaps in the last 24 hours
        twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
        
        # Get hourly counts
        hourly_counts = await self.db.execute(
            select(
                func.date_trunc('hour', GDPRAuditLog.created_at).label('hour'),
                func.count(GDPRAuditLog.id)
            ).where(
                GDPRAuditLog.created_at >= twenty_four_hours_ago
            ).group_by('hour')
        )
        
        hours_with_data = len(hourly_counts.all())
        return hours_with_data < 24  # Gap exists if not all hours have data
    
    def _get_score_color(self, score: float) -> str:
        """Get color based on compliance score"""
        if score >= 90:
            return 'green'
        elif score >= 70:
            return 'yellow'
        elif score >= 50:
            return 'orange'
        else:
            return 'red'
    
    async def _get_request_status_summary(self) -> dict:
        """Get request status summary for donut chart"""
        status_counts = await self.db.execute(
            select(
                DataRequest.status,
                func.count(DataRequest.id)
            ).group_by(DataRequest.status)
        )
        
        return {
            'labels': [status for status, _ in status_counts],
            'values': [count for _, count in status_counts]
        }
    
    async def _get_activity_heatmap(self, days: int) -> dict:
        """Get activity heatmap data"""
        heatmap_data = []
        
        for i in range(days):
            date = datetime.utcnow() - timedelta(days=i)
            
            # Get hourly activity for this day
            hourly_data = await self.db.execute(
                select(
                    func.extract('hour', GDPRAuditLog.created_at).label('hour'),
                    func.count(GDPRAuditLog.id).label('count')
                ).where(
                    func.date(GDPRAuditLog.created_at) == date.date()
                ).group_by('hour')
            )
            
            for hour, count in hourly_data:
                heatmap_data.append({
                    'day': date.strftime('%Y-%m-%d'),
                    'hour': int(hour),
                    'value': count
                })
        
        return {'data': heatmap_data}
    
    async def _get_quick_stats(self) -> dict:
        """Get quick statistics for stats grid"""
        return {
            'items': [
                {
                    'label': 'Active Users',
                    'value': await self._get_active_user_count(),
                    'icon': 'users',
                    'trend': 'up'
                },
                {
                    'label': 'Data Processed',
                    'value': await self._get_data_processed_count(),
                    'icon': 'database',
                    'unit': 'GB'
                },
                {
                    'label': 'Compliance Rate',
                    'value': await self._calculate_request_compliance_rate(),
                    'icon': 'check-circle',
                    'unit': '%'
                },
                {
                    'label': 'Active Policies',
                    'value': await self._get_active_policy_count(),
                    'icon': 'shield',
                    'trend': 'stable'
                }
            ]
        }
    
    async def _get_active_user_count(self) -> int:
        """Get count of users with active consents"""
        return await self.db.scalar(
            select(func.count(func.distinct(UserConsent.user_id))).where(
                UserConsent.is_active == True
            )
        ) or 0
    
    async def _get_data_processed_count(self) -> float:
        """Get amount of data processed (simulated)"""
        # In production, this would query actual storage metrics
        return 42.7
    
    async def _get_active_policy_count(self) -> int:
        """Get count of active policies"""
        return await self.db.scalar(
            select(func.count(DataRetentionRule.id)).where(
                DataRetentionRule.is_active == True
            )
        ) or 0