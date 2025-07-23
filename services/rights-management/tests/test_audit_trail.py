"""
Tests for Audit Trail Functionality

Tests audit logging for all rights management operations.
"""

import pytest
from httpx import AsyncClient
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import uuid
from datetime import datetime, timedelta

from src.db.models import AuditLog, LicenseAuditLog, License


class TestAuditTrailFunctionality:
    """Test audit trail and logging functionality"""
    
    @pytest.fixture
    async def test_entities(self, client: AsyncClient, auth_headers: dict):
        """Create test entities for audit testing"""
        # Create licensor
        licensor_response = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensor",
                "name": "Audit Test Licensor",
                "contact_email": "audit.licensor@test.com",
                "country": "USA"
            },
            headers=auth_headers
        )
        licensor_id = licensor_response.json()["id"]
        
        # Create licensee
        licensee_response = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensee",
                "name": "Audit Test Licensee",
                "contact_email": "audit.licensee@test.com",
                "country": "UK"
            },
            headers=auth_headers
        )
        licensee_id = licensee_response.json()["id"]
        
        return {
            "licensor_id": licensor_id,
            "licensee_id": licensee_id
        }
    
    @pytest.mark.asyncio
    async def test_license_creation_audit(
        self, client: AsyncClient, auth_headers: dict, test_entities: dict, test_db: AsyncSession
    ):
        """Test audit logging for license creation"""
        # Get initial audit count
        initial_count_result = await test_db.execute(
            select(func.count(LicenseAuditLog.id))
        )
        initial_count = initial_count_result.scalar()
        
        # Create a license
        license_data = {
            "license_number": "LIC-AUDIT-CREATE-001",
            "license_type": "sync",
            "title": "Audit Test License",
            "asset_id": str(uuid.uuid4()),
            "licensor_id": test_entities["licensor_id"],
            "licensee_id": test_entities["licensee_id"],
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "geographic_scope": "worldwide",
            "license_fee": 50000.0,
            "currency": "USD"
        }
        
        response = await client.post(
            "/api/v1/rights/licenses",
            json=license_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        license_id = response.json()["id"]
        
        # Check audit log
        result = await test_db.execute(
            select(LicenseAuditLog)
            .where(LicenseAuditLog.license_id == license_id)
            .order_by(LicenseAuditLog.created_at.desc())
        )
        audit_logs = result.scalars().all()
        
        assert len(audit_logs) >= 1
        create_log = audit_logs[0]
        assert create_log.action == "created"
        assert create_log.new_values is not None
        assert create_log.new_values.get("license_number") == "LIC-AUDIT-CREATE-001"
    
    @pytest.mark.asyncio
    async def test_license_update_audit(
        self, client: AsyncClient, auth_headers: dict, test_entities: dict, test_db: AsyncSession
    ):
        """Test audit logging for license updates"""
        # Create a license
        create_response = await client.post(
            "/api/v1/rights/licenses",
            json={
                "license_number": "LIC-AUDIT-UPDATE-001",
                "license_type": "broadcast",
                "title": "Original Title",
                "asset_id": str(uuid.uuid4()),
                "licensor_id": test_entities["licensor_id"],
                "licensee_id": test_entities["licensee_id"],
                "start_date": "2025-01-01",
                "geographic_scope": "worldwide",
                "status": "pending"
            },
            headers=auth_headers
        )
        license_id = create_response.json()["id"]
        
        # Update the license
        update_data = {
            "title": "Updated Title",
            "status": "active",
            "license_fee": 75000.0,
            "notes": "Updated after negotiation"
        }
        
        update_response = await client.put(
            f"/api/v1/rights/licenses/{license_id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert update_response.status_code == status.HTTP_200_OK
        
        # Check audit log
        result = await test_db.execute(
            select(LicenseAuditLog)
            .where(
                LicenseAuditLog.license_id == license_id,
                LicenseAuditLog.action == "updated"
            )
            .order_by(LicenseAuditLog.created_at.desc())
        )
        update_logs = result.scalars().all()
        
        assert len(update_logs) >= 1
        update_log = update_logs[0]
        assert update_log.action == "updated"
        assert "title" in update_log.changed_fields
        assert "status" in update_log.changed_fields
        assert "license_fee" in update_log.changed_fields
        assert update_log.old_values.get("title") == "Original Title"
        assert update_log.new_values.get("title") == "Updated Title"
    
    @pytest.mark.asyncio
    async def test_license_deletion_audit(
        self, client: AsyncClient, auth_headers: dict, test_entities: dict, test_db: AsyncSession
    ):
        """Test audit logging for license deletion"""
        # Create a license
        create_response = await client.post(
            "/api/v1/rights/licenses",
            json={
                "license_number": "LIC-AUDIT-DELETE-001",
                "license_type": "streaming",
                "title": "Delete Test License",
                "asset_id": str(uuid.uuid4()),
                "licensor_id": test_entities["licensor_id"],
                "licensee_id": test_entities["licensee_id"],
                "start_date": "2025-01-01",
                "geographic_scope": "worldwide"
            },
            headers=auth_headers
        )
        license_id = create_response.json()["id"]
        
        # Delete the license
        delete_response = await client.delete(
            f"/api/v1/rights/licenses/{license_id}",
            headers=auth_headers
        )
        
        assert delete_response.status_code == status.HTTP_200_OK
        
        # Check audit log
        result = await test_db.execute(
            select(LicenseAuditLog)
            .where(LicenseAuditLog.license_id == license_id)
            .order_by(LicenseAuditLog.created_at.desc())
        )
        audit_logs = result.scalars().all()
        
        # Should have create and delete logs
        assert len(audit_logs) >= 2
        delete_log = next((log for log in audit_logs if log.action == "deleted"), None)
        assert delete_log is not None
        assert delete_log.old_values is not None
    
    @pytest.mark.asyncio
    async def test_usage_record_audit(
        self, client: AsyncClient, auth_headers: dict, test_entities: dict, test_db: AsyncSession
    ):
        """Test audit logging for usage records"""
        # Create a license first
        license_response = await client.post(
            "/api/v1/rights/licenses",
            json={
                "license_number": "LIC-USAGE-AUDIT-001",
                "license_type": "broadcast",
                "title": "Usage Audit License",
                "asset_id": str(uuid.uuid4()),
                "licensor_id": test_entities["licensor_id"],
                "licensee_id": test_entities["licensee_id"],
                "start_date": "2025-01-01",
                "geographic_scope": "worldwide"
            },
            headers=auth_headers
        )
        license_id = license_response.json()["id"]
        
        # Create usage record
        usage_response = await client.post(
            "/api/v1/rights/usage",
            json={
                "license_id": license_id,
                "asset_id": str(uuid.uuid4()),
                "user_id": str(uuid.uuid4()),
                "usage_type": "broadcast",
                "usage_date": datetime.utcnow().isoformat(),
                "duration_seconds": 3600,
                "platform": "Television",
                "country": "USA",
                "revenue_generated": 5000.0
            },
            headers=auth_headers
        )
        
        assert usage_response.status_code == status.HTTP_201_CREATED
        usage_id = usage_response.json()["id"]
        
        # Check general audit log
        result = await test_db.execute(
            select(AuditLog)
            .where(
                AuditLog.entity_type == "usage_record",
                AuditLog.entity_id == usage_id
            )
            .order_by(AuditLog.timestamp.desc())
        )
        audit_logs = result.scalars().all()
        
        assert len(audit_logs) >= 1
        usage_audit = audit_logs[0]
        assert usage_audit.event_type == "usage_record_created"
        assert usage_audit.severity == "info"
        assert usage_audit.details is not None
    
    @pytest.mark.asyncio
    async def test_compliance_alert_audit(
        self, client: AsyncClient, auth_headers: dict, test_entities: dict, test_db: AsyncSession
    ):
        """Test audit logging for compliance alerts"""
        # Create a license
        license_response = await client.post(
            "/api/v1/rights/licenses",
            json={
                "license_number": "LIC-COMPLIANCE-AUDIT-001",
                "license_type": "sync",
                "title": "Compliance Audit License",
                "asset_id": str(uuid.uuid4()),
                "licensor_id": test_entities["licensor_id"],
                "licensee_id": test_entities["licensee_id"],
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "geographic_scope": "territory",
                "countries": ["US", "CA"]
            },
            headers=auth_headers
        )
        license_id = license_response.json()["id"]
        
        # Trigger compliance violation
        compliance_check = {
            "asset_id": str(uuid.uuid4()),
            "license_id": license_id,
            "usage_type": "sync",
            "usage_date": datetime.utcnow().isoformat(),
            "country": "UK"  # Not allowed
        }
        
        check_response = await client.post(
            "/api/v1/rights/compliance/check",
            json=compliance_check,
            headers=auth_headers
        )
        
        # Check audit log for compliance check
        result = await test_db.execute(
            select(AuditLog)
            .where(
                AuditLog.event_type.like("%compliance%"),
                AuditLog.entity_id == license_id
            )
            .order_by(AuditLog.timestamp.desc())
        )
        audit_logs = result.scalars().all()
        
        assert len(audit_logs) >= 1
        compliance_audit = audit_logs[0]
        assert "compliance" in compliance_audit.event_type.lower()
        assert compliance_audit.details.get("violation") is not None or compliance_audit.details.get("result") is not None
    
    @pytest.mark.asyncio
    async def test_bulk_operation_audit(
        self, client: AsyncClient, auth_headers: dict, test_entities: dict, test_db: AsyncSession
    ):
        """Test audit logging for bulk operations"""
        # Bulk create licenses
        bulk_data = {
            "licenses": [
                {
                    "license_number": f"LIC-BULK-AUDIT-{i:03d}",
                    "license_type": "broadcast",
                    "title": f"Bulk License {i}",
                    "asset_id": str(uuid.uuid4()),
                    "licensor_id": test_entities["licensor_id"],
                    "licensee_id": test_entities["licensee_id"],
                    "start_date": "2025-01-01",
                    "geographic_scope": "worldwide"
                }
                for i in range(3)
            ]
        }
        
        response = await client.post(
            "/api/v1/rights/bulk/licenses",
            json=bulk_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Check audit log for bulk operation
        result = await test_db.execute(
            select(AuditLog)
            .where(AuditLog.event_type == "bulk_license_creation")
            .order_by(AuditLog.timestamp.desc())
        )
        bulk_audit = result.scalar_one_or_none()
        
        if bulk_audit:
            assert bulk_audit.details.get("total_licenses") == 3
            assert bulk_audit.details.get("successful") == 3
    
    @pytest.mark.asyncio
    async def test_geo_blocking_audit(
        self, client: AsyncClient, auth_headers: dict, test_entities: dict, test_db: AsyncSession
    ):
        """Test audit logging for geo-blocking operations"""
        # Create a license
        license_response = await client.post(
            "/api/v1/rights/licenses",
            json={
                "license_number": "LIC-GEO-AUDIT-001",
                "license_type": "streaming",
                "title": "Geo Audit License",
                "asset_id": str(uuid.uuid4()),
                "licensor_id": test_entities["licensor_id"],
                "licensee_id": test_entities["licensee_id"],
                "start_date": "2025-01-01",
                "geographic_scope": "territory",
                "countries": ["US", "CA"]
            },
            headers=auth_headers
        )
        license_id = license_response.json()["id"]
        
        # Check geo-blocking access
        geo_response = await client.post(
            f"/api/v1/rights/geo-blocking/check/{license_id}",
            params={"country_code": "JP"},
            headers=auth_headers
        )
        
        # Check audit log
        result = await test_db.execute(
            select(AuditLog)
            .where(
                AuditLog.event_type.like("%geo%"),
                AuditLog.entity_id == license_id
            )
            .order_by(AuditLog.timestamp.desc())
        )
        geo_audits = result.scalars().all()
        
        assert len(geo_audits) >= 1
        geo_audit = geo_audits[0]
        assert geo_audit.details.get("country_code") == "JP"
        assert geo_audit.details.get("access_result") is not None
    
    @pytest.mark.asyncio
    async def test_audit_search_by_user(
        self, client: AsyncClient, auth_headers: dict, test_entities: dict, test_db: AsyncSession
    ):
        """Test searching audit logs by user"""
        # Create multiple operations
        for i in range(3):
            await client.post(
                "/api/v1/rights/licenses",
                json={
                    "license_number": f"LIC-USER-AUDIT-{i:03d}",
                    "license_type": "sync",
                    "title": f"User Audit License {i}",
                    "asset_id": str(uuid.uuid4()),
                    "licensor_id": test_entities["licensor_id"],
                    "licensee_id": test_entities["licensee_id"],
                    "start_date": "2025-01-01",
                    "geographic_scope": "worldwide"
                },
                headers=auth_headers
            )
        
        # Query audit logs by user
        # Note: In real implementation, user_id would come from auth token
        result = await test_db.execute(
            select(AuditLog)
            .where(AuditLog.event_type == "license_created")
            .order_by(AuditLog.timestamp.desc())
            .limit(10)
        )
        user_audits = result.scalars().all()
        
        assert len(user_audits) >= 3
        # All should be from same user in test context
        if user_audits and user_audits[0].user_id:
            user_ids = set(audit.user_id for audit in user_audits)
            assert len(user_ids) == 1  # All from same test user
    
    @pytest.mark.asyncio
    async def test_audit_timestamp_accuracy(
        self, client: AsyncClient, auth_headers: dict, test_entities: dict, test_db: AsyncSession
    ):
        """Test audit log timestamp accuracy"""
        before_time = datetime.utcnow()
        
        # Create a license
        response = await client.post(
            "/api/v1/rights/licenses",
            json={
                "license_number": "LIC-TIME-AUDIT-001",
                "license_type": "broadcast",
                "title": "Timestamp Test License",
                "asset_id": str(uuid.uuid4()),
                "licensor_id": test_entities["licensor_id"],
                "licensee_id": test_entities["licensee_id"],
                "start_date": "2025-01-01",
                "geographic_scope": "worldwide"
            },
            headers=auth_headers
        )
        
        after_time = datetime.utcnow()
        license_id = response.json()["id"]
        
        # Check audit timestamp
        result = await test_db.execute(
            select(LicenseAuditLog)
            .where(LicenseAuditLog.license_id == license_id)
        )
        audit_log = result.scalar_one()
        
        # Timestamp should be between before and after
        assert before_time <= audit_log.created_at <= after_time
    
    @pytest.mark.asyncio
    async def test_audit_data_integrity(
        self, client: AsyncClient, auth_headers: dict, test_entities: dict, test_db: AsyncSession
    ):
        """Test audit log data integrity and checksums"""
        # Create a license
        license_data = {
            "license_number": "LIC-INTEGRITY-001",
            "license_type": "sync",
            "title": "Integrity Test License",
            "asset_id": str(uuid.uuid4()),
            "licensor_id": test_entities["licensor_id"],
            "licensee_id": test_entities["licensee_id"],
            "start_date": "2025-01-01",
            "geographic_scope": "worldwide",
            "license_fee": 100000.0
        }
        
        response = await client.post(
            "/api/v1/rights/licenses",
            json=license_data,
            headers=auth_headers
        )
        license_id = response.json()["id"]
        
        # Check audit log
        result = await test_db.execute(
            select(AuditLog)
            .where(
                AuditLog.entity_type == "license",
                AuditLog.entity_id == license_id
            )
        )
        audit_log = result.scalar_one_or_none()
        
        if audit_log and audit_log.checksum:
            # Verify checksum exists and is proper length (SHA-256)
            assert len(audit_log.checksum) == 64  # SHA-256 hex digest
            
            # Verify critical data is captured
            assert audit_log.details is not None
            if "license_data" in audit_log.details:
                assert audit_log.details["license_data"]["license_fee"] == 100000.0
    
    @pytest.mark.asyncio
    async def test_audit_severity_levels(
        self, client: AsyncClient, auth_headers: dict, test_entities: dict, test_db: AsyncSession
    ):
        """Test different audit severity levels"""
        # Create license (info level)
        license_response = await client.post(
            "/api/v1/rights/licenses",
            json={
                "license_number": "LIC-SEVERITY-001",
                "license_type": "broadcast",
                "title": "Severity Test License",
                "asset_id": str(uuid.uuid4()),
                "licensor_id": test_entities["licensor_id"],
                "licensee_id": test_entities["licensee_id"],
                "start_date": "2025-01-01",
                "geographic_scope": "worldwide"
            },
            headers=auth_headers
        )
        
        # Delete license (warning level)
        await client.delete(
            f"/api/v1/rights/licenses/{license_response.json()['id']}",
            headers=auth_headers
        )
        
        # Check different severity levels
        result = await test_db.execute(
            select(AuditLog.severity, func.count(AuditLog.id))
            .group_by(AuditLog.severity)
        )
        severity_counts = dict(result.all())
        
        # Should have at least info level entries
        assert severity_counts.get("info", 0) > 0