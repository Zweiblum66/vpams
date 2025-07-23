"""
Tests for Audit Trail Service
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from ..src.models.audit_schemas import (
    AuditTrailCreate, AuditTrailFilter, AuditTrailExport,
    AuditAction, AuditResourceType, AuditBatch, AuditRetentionPolicy
)
from ..src.services.audit_service import AuditService
from ..src.models.audit_models import AuditTrail, AuditArchive


@pytest.fixture
def audit_service():
    """Create audit service instance"""
    return AuditService()


@pytest.fixture
def sample_audit_data():
    """Create sample audit trail data"""
    return AuditTrailCreate(
        action=AuditAction.LICENSE_CREATED,
        resource_type=AuditResourceType.LICENSE,
        resource_id=str(uuid.uuid4()),
        user_id="test_user_123",
        user_email="test@example.com",
        user_name="Test User",
        user_roles=["user", "admin"],
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0...",
        session_id="session_123",
        old_values=None,
        new_values={
            "license_number": "LIC-2024-001",
            "license_type": "broadcast",
            "status": "active"
        },
        changes_summary="Created new broadcast license LIC-2024-001",
        metadata={
            "asset_id": "asset_123",
            "licensor_id": "party_456"
        },
        tags=["license", "create", "broadcast"],
        success=True
    )


class TestAuditService:
    """Test audit service functionality"""
    
    @pytest.mark.asyncio
    async def test_create_audit_trail(self, db_session: AsyncSession, audit_service, sample_audit_data):
        """Test creating an audit trail entry"""
        # Create audit trail
        result = await audit_service.create_audit_trail(db_session, sample_audit_data)
        
        # Verify result
        assert result.id is not None
        assert result.action == sample_audit_data.action
        assert result.resource_type == sample_audit_data.resource_type
        assert result.resource_id == sample_audit_data.resource_id
        assert result.user_id == sample_audit_data.user_id
        assert result.compliance_relevant is True  # LICENSE_CREATED is compliance relevant
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_create_audit_batch(self, db_session: AsyncSession, audit_service):
        """Test creating multiple audit trail entries in a batch"""
        # Create batch data
        batch_id = str(uuid.uuid4())
        entries = []
        
        for i in range(3):
            entry = AuditTrailCreate(
                action=AuditAction.USAGE_RECORDED,
                resource_type=AuditResourceType.USAGE_RECORD,
                resource_id=str(uuid.uuid4()),
                user_id="batch_user",
                user_email="batch@example.com",
                user_name="Batch User",
                user_roles=["user"],
                changes_summary=f"Recorded usage {i+1}",
                success=True
            )
            entries.append(entry)
        
        batch = AuditBatch(
            entries=entries,
            batch_id=batch_id,
            batch_metadata={"source": "bulk_import"}
        )
        
        # Create batch
        results = await audit_service.create_audit_batch(db_session, batch)
        
        # Verify results
        assert len(results) == 3
        for result in results:
            assert result.metadata.get("batch_id") == batch_id
            assert result.metadata.get("source") == "bulk_import"
    
    @pytest.mark.asyncio
    async def test_get_audit_trails_with_filter(self, db_session: AsyncSession, audit_service, sample_audit_data):
        """Test getting audit trails with filtering"""
        # Create multiple audit entries
        await audit_service.create_audit_trail(db_session, sample_audit_data)
        
        # Create another entry with different action
        sample_audit_data.action = AuditAction.LICENSE_UPDATED
        sample_audit_data.resource_id = str(uuid.uuid4())
        await audit_service.create_audit_trail(db_session, sample_audit_data)
        
        # Filter by action
        filter_params = AuditTrailFilter(
            action=AuditAction.LICENSE_CREATED
        )
        
        results, total = await audit_service.get_audit_trails(
            db_session, filter_params, skip=0, limit=10
        )
        
        # Verify results
        assert total >= 1
        assert all(r.action == AuditAction.LICENSE_CREATED for r in results)
    
    @pytest.mark.asyncio
    async def test_get_audit_stats(self, db_session: AsyncSession, audit_service):
        """Test getting audit trail statistics"""
        # Create test data
        actions = [
            AuditAction.LICENSE_CREATED,
            AuditAction.LICENSE_UPDATED,
            AuditAction.LICENSE_CREATED,
            AuditAction.USAGE_RECORDED
        ]
        
        for action in actions:
            audit_data = AuditTrailCreate(
                action=action,
                resource_type=AuditResourceType.LICENSE,
                resource_id=str(uuid.uuid4()),
                user_id="stats_user",
                user_email="stats@example.com",
                user_name="Stats User",
                user_roles=["user"],
                changes_summary=f"Test {action.value}",
                success=True
            )
            await audit_service.create_audit_trail(db_session, audit_data)
        
        # Get stats
        filter_params = AuditTrailFilter()
        stats = await audit_service.get_audit_stats(db_session, filter_params)
        
        # Verify stats
        assert stats.total_entries >= 4
        assert stats.entries_by_action.get(AuditAction.LICENSE_CREATED.value, 0) >= 2
        assert stats.entries_by_action.get(AuditAction.LICENSE_UPDATED.value, 0) >= 1
        assert stats.entries_by_action.get(AuditAction.USAGE_RECORDED.value, 0) >= 1
    
    @pytest.mark.asyncio
    async def test_export_audit_trails(self, db_session: AsyncSession, audit_service, sample_audit_data):
        """Test exporting audit trails"""
        # Create test data
        await audit_service.create_audit_trail(db_session, sample_audit_data)
        
        # Test CSV export
        export_params = AuditTrailExport(
            filter=AuditTrailFilter(),
            format="csv"
        )
        
        csv_data = await audit_service.export_audit_trails(db_session, export_params)
        
        # Verify CSV data
        assert isinstance(csv_data, bytes)
        assert b"action,resource_type" in csv_data  # Check for headers
        assert sample_audit_data.action.value.encode() in csv_data
        
        # Test JSON export
        export_params.format = "json"
        json_data = await audit_service.export_audit_trails(db_session, export_params)
        
        # Verify JSON data
        assert isinstance(json_data, bytes)
        import json
        parsed = json.loads(json_data.decode())
        assert isinstance(parsed, list)
        assert len(parsed) >= 1
    
    @pytest.mark.asyncio
    async def test_archive_audit_trails(self, db_session: AsyncSession, audit_service):
        """Test archiving old audit trails"""
        # Create old audit entries
        old_date = datetime.utcnow() - timedelta(days=400)
        
        # Manually create old entries (bypassing service to set custom timestamp)
        for i in range(3):
            audit_trail = AuditTrail(
                action=AuditAction.LICENSE_CREATED,
                resource_type=AuditResourceType.LICENSE,
                resource_id=str(uuid.uuid4()),
                user_id="old_user",
                user_email="old@example.com",
                timestamp=old_date,
                success=True
            )
            db_session.add(audit_trail)
        
        await db_session.commit()
        
        # Archive old entries
        retention_policy = AuditRetentionPolicy(
            archive_after_days=365
        )
        
        archived_count = await audit_service.archive_audit_trails(
            db_session, retention_policy
        )
        
        # Verify archiving
        assert archived_count == 3
        
        # Check that entries were moved to archive
        archive_query = await db_session.execute(
            select(func.count(AuditArchive.id))
        )
        archive_count = archive_query.scalar()
        assert archive_count == 3
    
    @pytest.mark.asyncio
    async def test_compliance_and_security_flagging(self, db_session: AsyncSession, audit_service):
        """Test that compliance and security relevant actions are properly flagged"""
        # Test compliance relevant action
        compliance_data = AuditTrailCreate(
            action=AuditAction.LICENSE_CREATED,
            resource_type=AuditResourceType.LICENSE,
            resource_id=str(uuid.uuid4()),
            user_id="test_user",
            user_email="test@example.com",
            user_name="Test User",
            user_roles=["user"],
            changes_summary="Created license",
            success=True
        )
        
        result = await audit_service.create_audit_trail(db_session, compliance_data)
        assert result.compliance_relevant is True
        
        # Test security relevant action
        security_data = AuditTrailCreate(
            action=AuditAction.ACCESS_GRANTED,
            resource_type=AuditResourceType.LICENSE,
            resource_id=str(uuid.uuid4()),
            user_id="test_user",
            user_email="test@example.com",
            user_name="Test User",
            user_roles=["user"],
            changes_summary="Granted access",
            success=True
        )
        
        result = await audit_service.create_audit_trail(db_session, security_data)
        assert result.security_relevant is True
    
    @pytest.mark.asyncio
    async def test_calculate_diff(self, audit_service):
        """Test calculating differences between old and new values"""
        old_values = {
            "name": "Old Name",
            "status": "active",
            "value": 100
        }
        
        new_values = {
            "name": "New Name",
            "status": "active",
            "value": 200,
            "description": "Added description"
        }
        
        diffs = audit_service.calculate_diff(old_values, new_values)
        
        # Verify diffs
        assert len(diffs) == 3  # name changed, value changed, description added
        
        # Check specific changes
        name_diff = next(d for d in diffs if d.field == "name")
        assert name_diff.old_value == "Old Name"
        assert name_diff.new_value == "New Name"
        
        value_diff = next(d for d in diffs if d.field == "value")
        assert value_diff.old_value == 100
        assert value_diff.new_value == 200
        
        desc_diff = next(d for d in diffs if d.field == "description")
        assert desc_diff.old_value is None
        assert desc_diff.new_value == "Added description"
    
    @pytest.mark.asyncio
    async def test_search_audit_trails(self, db_session: AsyncSession, audit_service):
        """Test searching audit trails by text"""
        # Create entries with specific text
        search_text = "special_license_123"
        
        audit_data = AuditTrailCreate(
            action=AuditAction.LICENSE_CREATED,
            resource_type=AuditResourceType.LICENSE,
            resource_id=str(uuid.uuid4()),
            user_id="test_user",
            user_email="test@example.com",
            user_name="Test User",
            user_roles=["user"],
            changes_summary=f"Created license {search_text}",
            metadata={"license_number": search_text},
            success=True
        )
        
        await audit_service.create_audit_trail(db_session, audit_data)
        
        # Search for the text
        filter_params = AuditTrailFilter(
            search_text=search_text
        )
        
        results, total = await audit_service.get_audit_trails(
            db_session, filter_params, skip=0, limit=10
        )
        
        # Verify search results
        assert total >= 1
        assert any(search_text in r.changes_summary for r in results)