"""Tests for GDPR compliance dashboard functionality"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.dashboard_service import DashboardService
from src.models.schemas import (
    ComplianceDashboard, ComplianceScore, ComplianceMetric,
    DataClassificationSummary, ConsentMetrics, DataRequestMetrics,
    RetentionMetrics, AuditMetrics, DashboardWidget, RiskIndicator,
    PrivacyLevel, ConsentType, DataRequestType, DataRequestStatus
)
from src.db.models import (
    UserConsent, DataRequest, GDPRAuditLog, DataCategory,
    DataMapping, DataRetentionRule
)


@pytest.mark.asyncio
async def test_get_compliance_overview(
    db_session: AsyncSession,
    dashboard_service: DashboardService,
    sample_user,
    sample_consents,
    sample_data_requests,
    sample_audit_logs
):
    """Test getting comprehensive compliance dashboard"""
    # Get dashboard overview
    dashboard = await dashboard_service.get_compliance_overview(time_range_days=30)
    
    # Verify structure
    assert isinstance(dashboard, ComplianceDashboard)
    assert isinstance(dashboard.compliance_score, ComplianceScore)
    assert 0 <= dashboard.compliance_score.score <= 100
    assert dashboard.compliance_score.grade in ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D', 'F']
    
    # Check key metrics
    assert len(dashboard.key_metrics) > 0
    for metric in dashboard.key_metrics:
        assert isinstance(metric, ComplianceMetric)
        assert metric.name
        assert metric.value >= 0
        assert metric.unit in ['count', 'percentage', 'days']
    
    # Check trends
    assert len(dashboard.trends) == 30  # One per day
    for trend in dashboard.trends:
        assert 0 <= trend.compliance_score <= 100
        assert trend.consent_count >= 0
        assert trend.request_count >= 0
        assert trend.incident_count >= 0
    
    # Check risk indicators
    for risk in dashboard.risk_indicators:
        assert isinstance(risk, RiskIndicator)
        assert risk.severity in ['low', 'medium', 'high']
        assert risk.risk_type
        assert risk.description
        assert risk.mitigation
    
    # Check widgets
    assert len(dashboard.widgets) > 0
    for widget in dashboard.widgets:
        assert isinstance(widget, DashboardWidget)
        assert widget.widget_type
        assert widget.title
        assert widget.data


@pytest.mark.asyncio
async def test_compliance_score_calculation(
    db_session: AsyncSession,
    dashboard_service: DashboardService
):
    """Test compliance score calculation accuracy"""
    # Create test data with known compliance levels
    
    # Perfect compliance scenario
    # Add consents (all active)
    for i in range(10):
        consent = UserConsent(
            id=uuid4(),
            user_id=uuid4(),
            consent_type=ConsentType.MARKETING,
            consent_given=True,
            is_active=True,
            consent_date=datetime.utcnow()
        )
        db_session.add(consent)
    
    # Add completed data requests (all within 30 days)
    for i in range(5):
        request = DataRequest(
            id=uuid4(),
            user_id=uuid4(),
            request_type=DataRequestType.ACCESS,
            status=DataRequestStatus.COMPLETED,
            created_at=datetime.utcnow() - timedelta(days=10),
            completed_at=datetime.utcnow() - timedelta(days=5)
        )
        db_session.add(request)
    
    await db_session.commit()
    
    # Calculate score
    score = await dashboard_service._calculate_compliance_score()
    
    # Should have high score
    assert score.score >= 80
    assert score.grade in ['A', 'A-', 'B+']
    assert 'consent_management' in score.components
    assert 'data_requests' in score.components


@pytest.mark.asyncio
async def test_data_classification_summary(
    db_session: AsyncSession,
    dashboard_service: DashboardService
):
    """Test data classification summary generation"""
    # Create test categories
    categories = []
    for i, level in enumerate(PrivacyLevel):
        category = DataCategory(
            id=uuid4(),
            category_name=f"Category {level.value}",
            privacy_level=level,
            retention_days=365 * (i + 1),
            is_sensitive=i >= 3,
            created_by=str(uuid4())
        )
        categories.append(category)
        db_session.add(category)
    
    # Create mappings
    for i in range(20):
        mapping = DataMapping(
            id=uuid4(),
            table_name=f"table_{i % 5}",
            column_name=f"column_{i}",
            category_id=categories[i % len(categories)].id,
            contains_pii=i % 3 == 0,
            encryption_required=i % 4 == 0,
            created_by=str(uuid4())
        )
        db_session.add(mapping)
    
    await db_session.commit()
    
    # Get summary
    summary = await dashboard_service.get_data_classification_summary()
    
    # Verify summary
    assert isinstance(summary, DataClassificationSummary)
    assert summary.total_categories == 5
    assert summary.total_mappings == 20
    assert summary.sensitive_data_count == 2
    assert summary.encrypted_fields_count == 5
    
    # Check distributions
    assert summary.privacy_level_distribution.labels
    assert summary.privacy_level_distribution.values
    assert len(summary.privacy_level_distribution.labels) == 5
    
    assert summary.pii_distribution.labels == ["Contains PII", "No PII"]
    assert sum(summary.pii_distribution.values) == 20


@pytest.mark.asyncio
async def test_consent_metrics(
    db_session: AsyncSession,
    dashboard_service: DashboardService
):
    """Test consent metrics calculation"""
    # Create active consents
    base_date = datetime.utcnow()
    
    # Active consents
    for i in range(15):
        consent = UserConsent(
            id=uuid4(),
            user_id=uuid4(),
            consent_type=ConsentType.MARKETING if i % 2 == 0 else ConsentType.ANALYTICS,
            consent_given=True,
            is_active=True,
            consent_date=base_date - timedelta(days=i)
        )
        db_session.add(consent)
    
    # Withdrawn consents
    for i in range(5):
        consent = UserConsent(
            id=uuid4(),
            user_id=uuid4(),
            consent_type=ConsentType.MARKETING,
            consent_given=True,
            is_active=False,
            consent_date=base_date - timedelta(days=20),
            withdrawal_date=base_date - timedelta(days=i)
        )
        db_session.add(consent)
    
    await db_session.commit()
    
    # Get metrics
    metrics = await dashboard_service.get_consent_metrics(time_range_days=30)
    
    # Verify metrics
    assert isinstance(metrics, ConsentMetrics)
    assert metrics.total_active_consents == 15
    assert metrics.consents_given == 15
    assert metrics.consents_withdrawn == 5
    assert metrics.withdrawal_rate > 0
    
    # Check distributions
    assert metrics.consent_by_type.labels
    assert metrics.consent_by_type.values
    assert len(metrics.consent_by_type.labels) == 2
    
    # Check trends
    assert metrics.consent_trends.labels
    assert len(metrics.consent_trends.labels) == 30
    assert metrics.consent_trends.datasets


@pytest.mark.asyncio
async def test_data_request_metrics(
    db_session: AsyncSession,
    dashboard_service: DashboardService
):
    """Test data request metrics calculation"""
    base_date = datetime.utcnow()
    
    # Create various requests
    request_types = [DataRequestType.ACCESS, DataRequestType.PORTABILITY, DataRequestType.ERASURE]
    request_statuses = [DataRequestStatus.PENDING, DataRequestStatus.COMPLETED, DataRequestStatus.IN_PROGRESS]
    
    for i in range(30):
        request = DataRequest(
            id=uuid4(),
            user_id=uuid4(),
            request_type=request_types[i % len(request_types)],
            status=request_statuses[i % len(request_statuses)],
            created_at=base_date - timedelta(days=i % 20)
        )
        
        # Add completion time for completed requests
        if request.status == DataRequestStatus.COMPLETED:
            request.completed_at = request.created_at + timedelta(days=i % 10)
        
        db_session.add(request)
    
    # Add overdue request
    overdue_request = DataRequest(
        id=uuid4(),
        user_id=uuid4(),
        request_type=DataRequestType.ACCESS,
        status=DataRequestStatus.PENDING,
        created_at=base_date - timedelta(days=35)
    )
    db_session.add(overdue_request)
    
    await db_session.commit()
    
    # Get metrics
    metrics = await dashboard_service.get_data_request_metrics(time_range_days=30)
    
    # Verify metrics
    assert isinstance(metrics, DataRequestMetrics)
    assert metrics.total_requests == 30
    assert metrics.pending_requests > 0
    assert metrics.overdue_requests == 1
    assert 0 <= metrics.compliance_rate <= 100
    assert metrics.average_completion_time_days >= 0
    
    # Check distributions
    assert metrics.requests_by_type.labels
    assert len(metrics.requests_by_type.labels) == 3
    assert metrics.requests_by_status.labels
    assert len(metrics.requests_by_status.labels) == 3


@pytest.mark.asyncio
async def test_retention_metrics(
    db_session: AsyncSession,
    dashboard_service: DashboardService
):
    """Test retention policy metrics"""
    # Create retention rules
    for i in range(10):
        rule = DataRetentionRule(
            id=uuid4(),
            rule_name=f"Rule {i}",
            description=f"Test rule {i}",
            retention_days=90 * (i + 1),
            action_type='hard_delete' if i % 2 == 0 else 'soft_delete',
            is_active=i < 7,
            created_by=str(uuid4()),
            next_run=datetime.utcnow() + timedelta(days=i)
        )
        db_session.add(rule)
    
    # Create categories with retention
    for i in range(5):
        category = DataCategory(
            id=uuid4(),
            category_name=f"Category {i}",
            privacy_level=PrivacyLevel.CONFIDENTIAL,
            retention_days=365 * (i + 1),
            created_by=str(uuid4())
        )
        db_session.add(category)
    
    await db_session.commit()
    
    # Get metrics
    metrics = await dashboard_service.get_retention_metrics()
    
    # Verify metrics
    assert isinstance(metrics, RetentionMetrics)
    assert metrics.total_retention_rules == 10
    assert metrics.active_retention_rules == 7
    assert metrics.rules_by_action_type.labels
    assert metrics.rules_by_action_type.values
    assert metrics.average_retention_period_days > 0
    assert metrics.retention_by_category.labels
    assert len(metrics.retention_by_category.labels) <= 10


@pytest.mark.asyncio
async def test_audit_metrics(
    db_session: AsyncSession,
    dashboard_service: DashboardService
):
    """Test audit logging metrics"""
    base_date = datetime.utcnow()
    
    # Create audit events
    categories = ['consent', 'data_request', 'admin_action', 'user_activity']
    results = ['success', 'failure']
    users = [str(uuid4()) for _ in range(5)]
    
    for i in range(100):
        event = GDPRAuditLog(
            id=uuid4(),
            event_type=f"event_{i % 10}",
            event_category=categories[i % len(categories)],
            user_id=users[i % len(users)] if i % 3 != 0 else None,
            result=results[i % len(results)],
            created_at=base_date - timedelta(hours=i)
        )
        db_session.add(event)
    
    await db_session.commit()
    
    # Get metrics
    metrics = await dashboard_service.get_audit_metrics(time_range_days=30)
    
    # Verify metrics
    assert isinstance(metrics, AuditMetrics)
    assert metrics.total_audit_events == 100
    assert metrics.events_by_category.labels
    assert len(metrics.events_by_category.labels) == 4
    assert 0 <= metrics.success_rate <= 100
    assert metrics.success_rate + metrics.failure_rate == 100
    assert metrics.top_users_by_activity.labels
    assert metrics.audit_trends.labels


@pytest.mark.asyncio
async def test_risk_indicators(
    db_session: AsyncSession,
    dashboard_service: DashboardService
):
    """Test risk indicator detection"""
    # Create overdue data request
    overdue_request = DataRequest(
        id=uuid4(),
        user_id=uuid4(),
        request_type=DataRequestType.ACCESS,
        status=DataRequestStatus.PENDING,
        created_at=datetime.utcnow() - timedelta(days=35)
    )
    db_session.add(overdue_request)
    
    # Create expired consent
    expired_consent = UserConsent(
        id=uuid4(),
        user_id=uuid4(),
        consent_type=ConsentType.MARKETING,
        consent_given=True,
        is_active=True,
        consent_date=datetime.utcnow() - timedelta(days=400)
    )
    db_session.add(expired_consent)
    
    await db_session.commit()
    
    # Get risk indicators
    risks = await dashboard_service._get_risk_indicators()
    
    # Verify risks detected
    assert len(risks) > 0
    
    # Check for overdue request risk
    overdue_risk = next((r for r in risks if r.risk_type == 'overdue_requests'), None)
    assert overdue_risk is not None
    assert overdue_risk.severity in ['medium', 'high']
    assert overdue_risk.affected_items == 1
    
    # Check risks are sorted by severity
    if len(risks) > 1:
        severity_order = {'high': 0, 'medium': 1, 'low': 2}
        for i in range(1, len(risks)):
            assert severity_order[risks[i-1].severity] <= severity_order[risks[i].severity]


@pytest.mark.asyncio
async def test_dashboard_widgets(
    db_session: AsyncSession,
    dashboard_service: DashboardService,
    sample_data
):
    """Test dashboard widget generation"""
    # Get specific widgets
    widget_types = ['compliance_score', 'data_requests', 'consent_status']
    widgets = await dashboard_service.get_dashboard_widgets(widget_types)
    
    # Verify widgets
    assert len(widgets) == 3
    
    # Check compliance score widget
    score_widget = next((w for w in widgets if w.title == 'Compliance Score'), None)
    assert score_widget is not None
    assert score_widget.widget_type == 'gauge'
    assert 'score' in score_widget.data
    assert 'grade' in score_widget.data
    
    # Check data requests widget
    requests_widget = next((w for w in widgets if w.title == 'Data Requests'), None)
    assert requests_widget is not None
    assert requests_widget.widget_type == 'stats'
    assert 'pending' in requests_widget.data
    assert 'overdue' in requests_widget.data


@pytest.mark.asyncio
async def test_dashboard_export(
    client,
    auth_headers,
    sample_dashboard_data
):
    """Test dashboard export functionality"""
    # Test JSON export
    response = await client.post(
        "/api/v1/dashboard/export",
        json={
            "format": "json",
            "time_range_days": 30,
            "include_charts": True,
            "include_raw_data": True
        },
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data['export_id']
    assert data['file_path']
    assert data['format'] == 'json'
    assert data['size_bytes'] > 0
    
    # Test Excel export
    response = await client.post(
        "/api/v1/dashboard/export",
        json={
            "format": "excel",
            "time_range_days": 7
        },
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data['format'] == 'excel'
    assert data['file_path'].endswith('.xlsx')


@pytest.mark.asyncio
async def test_quick_stats_endpoint(
    client,
    auth_headers,
    sample_dashboard_data
):
    """Test quick stats endpoint"""
    response = await client.get(
        "/api/v1/dashboard/quick-stats",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert 'compliance_score' in data
    assert 'compliance_grade' in data
    assert 'pending_requests' in data
    assert 'critical_risks' in data
    assert 'last_updated' in data
    
    assert 0 <= data['compliance_score'] <= 100
    assert data['compliance_grade'] in ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D', 'F']
    assert data['pending_requests'] >= 0
    assert data['critical_risks'] >= 0


# Fixtures

@pytest.fixture
async def dashboard_service(db_session: AsyncSession):
    """Create dashboard service instance"""
    return DashboardService(db_session)


@pytest.fixture
async def sample_consents(db_session: AsyncSession):
    """Create sample consent data"""
    consents = []
    for i in range(20):
        consent = UserConsent(
            id=uuid4(),
            user_id=uuid4(),
            consent_type=ConsentType.MARKETING if i % 2 == 0 else ConsentType.ANALYTICS,
            consent_given=True,
            is_active=i < 15,
            consent_date=datetime.utcnow() - timedelta(days=i),
            withdrawal_date=datetime.utcnow() if i >= 15 else None
        )
        consents.append(consent)
        db_session.add(consent)
    
    await db_session.commit()
    return consents


@pytest.fixture
async def sample_data_requests(db_session: AsyncSession):
    """Create sample data request data"""
    requests = []
    for i in range(15):
        request = DataRequest(
            id=uuid4(),
            user_id=uuid4(),
            request_type=DataRequestType.ACCESS,
            status=DataRequestStatus.COMPLETED if i < 10 else DataRequestStatus.PENDING,
            created_at=datetime.utcnow() - timedelta(days=i),
            completed_at=datetime.utcnow() - timedelta(days=i-5) if i < 10 else None
        )
        requests.append(request)
        db_session.add(request)
    
    await db_session.commit()
    return requests


@pytest.fixture
async def sample_audit_logs(db_session: AsyncSession):
    """Create sample audit log data"""
    logs = []
    for i in range(50):
        log = GDPRAuditLog(
            id=uuid4(),
            event_type=f"event_{i % 5}",
            event_category='consent' if i % 3 == 0 else 'data_request',
            user_id=str(uuid4()) if i % 2 == 0 else None,
            result='success' if i % 4 != 0 else 'failure',
            created_at=datetime.utcnow() - timedelta(hours=i)
        )
        logs.append(log)
        db_session.add(log)
    
    await db_session.commit()
    return logs


@pytest.fixture
async def sample_dashboard_data(
    db_session: AsyncSession,
    sample_consents,
    sample_data_requests,
    sample_audit_logs
):
    """Create comprehensive sample data for dashboard"""
    # Create categories
    for i in range(5):
        category = DataCategory(
            id=uuid4(),
            category_name=f"Category {i}",
            privacy_level=list(PrivacyLevel)[i % len(PrivacyLevel)],
            retention_days=365 * (i + 1),
            is_sensitive=i >= 3,
            created_by=str(uuid4())
        )
        db_session.add(category)
    
    # Create retention rules
    for i in range(5):
        rule = DataRetentionRule(
            id=uuid4(),
            rule_name=f"Rule {i}",
            description=f"Test rule {i}",
            retention_days=90 * (i + 1),
            action_type='hard_delete',
            is_active=True,
            created_by=str(uuid4())
        )
        db_session.add(rule)
    
    await db_session.commit()
    
    return {
        'consents': sample_consents,
        'requests': sample_data_requests,
        'logs': sample_audit_logs
    }