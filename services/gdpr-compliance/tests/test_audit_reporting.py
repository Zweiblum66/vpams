"""Tests for Audit Reporting Service"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.audit_reporting_service import AuditReportingService
from src.models.schemas import (
    AuditReportType, AuditReportFormat,
    ComplianceScoreCard, RiskAssessment
)
from src.db.models import GDPRAuditLog, DataRequest, UserConsent


@pytest.mark.asyncio
async def test_generate_compliance_overview_report(db_session: AsyncSession):
    """Test generating compliance overview report"""
    # Create test audit logs
    for i in range(10):
        log = GDPRAuditLog(
            event_type="consent" if i < 5 else "data_request",
            action="create",
            actor_id=str(uuid4()),
            actor_type="user",
            success=True,
            event_timestamp=datetime.utcnow() - timedelta(days=i)
        )
        db_session.add(log)
    
    await db_session.commit()
    
    # Generate report
    reporting_service = AuditReportingService(db_session)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    
    report = await reporting_service.generate_report(
        report_type=AuditReportType.COMPLIANCE_OVERVIEW,
        start_date=start_date,
        end_date=end_date,
        format=AuditReportFormat.JSON
    )
    
    assert report.report_type == AuditReportType.COMPLIANCE_OVERVIEW
    assert report.format == AuditReportFormat.JSON
    assert report.data is not None
    assert "summary" in report.data
    assert "event_statistics" in report.data
    assert report.data["summary"]["total_events"] == 10


@pytest.mark.asyncio
async def test_calculate_compliance_score(db_session: AsyncSession):
    """Test compliance score calculation"""
    # Create test data requests
    for i in range(5):
        request = DataRequest(
            request_type="access",
            status="completed",
            requested_at=datetime.utcnow() - timedelta(days=10),
            completed_at=datetime.utcnow() - timedelta(days=5),  # 5 days completion
            user_id=str(uuid4()),
            request_data={}
        )
        db_session.add(request)
    
    await db_session.commit()
    
    # Calculate score
    reporting_service = AuditReportingService(db_session)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    
    score = await reporting_service._calculate_compliance_score(start_date, end_date)
    
    assert isinstance(score, ComplianceScoreCard)
    assert 0 <= score.overall_score <= 100
    assert score.grade in ["A+", "A", "B+", "B", "C+", "C", "D", "F"]
    assert "data_request_handling" in score.category_scores


@pytest.mark.asyncio
async def test_identify_risks(db_session: AsyncSession):
    """Test risk identification"""
    # Create failed deletion logs
    for i in range(3):
        log = GDPRAuditLog(
            event_type="data_deletion_request",
            action="delete",
            actor_id=str(uuid4()),
            actor_type="system",
            success=False,
            error_message="Failed to delete user data",
            event_timestamp=datetime.utcnow() - timedelta(days=i)
        )
        db_session.add(log)
    
    await db_session.commit()
    
    # Identify risks
    reporting_service = AuditReportingService(db_session)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    
    risks = await reporting_service._identify_top_risks(start_date, end_date)
    
    assert len(risks) > 0
    assert any(r.category == "data_deletion" for r in risks)
    
    # Check risk properties
    risk = risks[0]
    assert isinstance(risk, RiskAssessment)
    assert risk.severity in ["critical", "high", "medium", "low"]
    assert risk.impact is not None
    assert risk.mitigation is not None


@pytest.mark.asyncio
async def test_event_statistics(db_session: AsyncSession):
    """Test event statistics calculation"""
    # Create various event types
    event_types = ["consent", "data_request", "data_export", "privacy_policy"]
    for i in range(20):
        log = GDPRAuditLog(
            event_type=event_types[i % len(event_types)],
            action="create",
            actor_id=str(uuid4()),
            actor_type="user",
            success=i % 5 != 0,  # Every 5th event fails
            event_timestamp=datetime.utcnow() - timedelta(hours=i)
        )
        db_session.add(log)
    
    await db_session.commit()
    
    # Get statistics
    reporting_service = AuditReportingService(db_session)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=7)
    
    stats = await reporting_service._get_event_statistics(start_date, end_date)
    
    assert stats["total_events"] == 20
    assert len(stats["events_by_type"]) == len(event_types)
    assert stats["success_rate"] == 80.0  # 16/20 successful
    assert stats["failed_events"] == 4
    assert len(stats["daily_distribution"]) > 0


@pytest.mark.asyncio
async def test_pdf_report_generation(db_session: AsyncSession):
    """Test PDF report generation"""
    # Create minimal test data
    log = GDPRAuditLog(
        event_type="consent",
        action="create",
        actor_id=str(uuid4()),
        actor_type="user",
        success=True,
        event_timestamp=datetime.utcnow()
    )
    db_session.add(log)
    await db_session.commit()
    
    # Generate PDF report
    reporting_service = AuditReportingService(db_session)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=7)
    
    report = await reporting_service.generate_report(
        report_type=AuditReportType.COMPLIANCE_OVERVIEW,
        start_date=start_date,
        end_date=end_date,
        format=AuditReportFormat.PDF
    )
    
    assert report.format == AuditReportFormat.PDF
    assert report.file_content is not None
    assert len(report.file_content) > 0
    assert report.file_content.startswith(b'%PDF')  # PDF header


@pytest.mark.asyncio
async def test_csv_report_generation(db_session: AsyncSession):
    """Test CSV report generation"""
    # Create test data
    for i in range(5):
        log = GDPRAuditLog(
            event_type="consent",
            action="create",
            actor_id=str(uuid4()),
            actor_type="user",
            success=True,
            event_timestamp=datetime.utcnow() - timedelta(days=i)
        )
        db_session.add(log)
    
    await db_session.commit()
    
    # Generate CSV report
    reporting_service = AuditReportingService(db_session)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    
    report = await reporting_service.generate_report(
        report_type=AuditReportType.COMPLIANCE_OVERVIEW,
        start_date=start_date,
        end_date=end_date,
        format=AuditReportFormat.CSV
    )
    
    assert report.format == AuditReportFormat.CSV
    assert report.file_content is not None
    
    # Check CSV content
    csv_content = report.file_content.decode('utf-8')
    lines = csv_content.strip().split('\n')
    assert len(lines) > 1  # Header + data
    assert "Metric,Value" in lines[0]


@pytest.mark.asyncio
async def test_compliance_trends(db_session: AsyncSession):
    """Test compliance trend generation"""
    # Create historical data
    for month in range(6):
        for day in range(10):
            log = GDPRAuditLog(
                event_type="consent",
                action="create",
                actor_id=str(uuid4()),
                actor_type="user",
                success=True,
                event_timestamp=datetime.utcnow() - timedelta(days=month*30 + day)
            )
            db_session.add(log)
    
    await db_session.commit()
    
    # Generate trends
    reporting_service = AuditReportingService(db_session)
    trends = await reporting_service.generate_compliance_trends(6)
    
    assert len(trends) == 6
    for trend in trends:
        assert trend.compliance_score >= 0
        assert trend.total_events > 0
        assert trend.period  # YYYY-MM format


@pytest.mark.asyncio
async def test_user_activity_report(db_session: AsyncSession):
    """Test user activity report generation"""
    # Create activity for specific users
    user_ids = [str(uuid4()) for _ in range(3)]
    
    for i in range(30):
        log = GDPRAuditLog(
            event_type="data_request",
            action="view",
            actor_id=user_ids[i % 3],
            actor_type="user",
            success=True,
            event_timestamp=datetime.utcnow() - timedelta(hours=i)
        )
        db_session.add(log)
    
    await db_session.commit()
    
    # Generate user activity report
    reporting_service = AuditReportingService(db_session)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=7)
    
    report_data = await reporting_service._generate_user_activity_report(
        start_date, end_date, None
    )
    
    assert "most_active_users" in report_data
    assert len(report_data["most_active_users"]) > 0
    assert "hourly_activity_pattern" in report_data
    assert "common_actions" in report_data
    assert report_data["most_active_users"][0]["event_count"] >= report_data["most_active_users"][-1]["event_count"]


@pytest.mark.asyncio
async def test_data_request_metrics(db_session: AsyncSession):
    """Test data request metrics calculation"""
    # Create data requests with different completion times
    request_types = ["access", "portability", "erasure"]
    
    for i in range(15):
        request = DataRequest(
            request_type=request_types[i % 3],
            status="completed",
            requested_at=datetime.utcnow() - timedelta(days=20),
            completed_at=datetime.utcnow() - timedelta(days=20-i),  # Variable completion time
            user_id=str(uuid4()),
            request_data={}
        )
        db_session.add(request)
    
    await db_session.commit()
    
    # Get metrics
    reporting_service = AuditReportingService(db_session)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    
    metrics = await reporting_service._get_data_request_metrics(start_date, end_date)
    
    assert metrics["total_requests"] == 15
    assert len(metrics["requests_by_type"]) == 3
    assert metrics["completion_rate"] > 0
    assert metrics["average_response_time_hours"] > 0