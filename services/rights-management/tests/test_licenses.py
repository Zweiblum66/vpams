"""
Tests for License Management API

Tests CRUD operations and business logic for licenses.
"""

import pytest
from httpx import AsyncClient
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from datetime import date, datetime, timedelta

from src.db.models import License, RightsParty, LicenseAuditLog
from src.models.schemas import LicenseCreate, LicenseUpdate


class TestLicenseEndpoints:
    """Test license API endpoints"""
    
    @pytest.fixture
    async def test_parties(self, client: AsyncClient, auth_headers: dict):
        """Create test rights parties for license tests"""
        # Create licensor
        licensor_response = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensor",
                "name": "Test Licensor Inc",
                "contact_email": "licensor@test.com",
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
                "name": "Test Licensee Corp",
                "contact_email": "licensee@test.com",
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
    async def test_create_license_success(
        self, client: AsyncClient, auth_headers: dict, test_parties: dict
    ):
        """Test successful license creation"""
        license_data = {
            "license_number": "LIC-2025-TEST-001",
            "license_type": "sync",
            "status": "active",
            "title": "Test Sync License",
            "description": "License for synchronization rights",
            "asset_id": str(uuid.uuid4()),
            "licensor_id": test_parties["licensor_id"],
            "licensee_id": test_parties["licensee_id"],
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "signed_date": "2024-12-15",
            "geographic_scope": "territory",
            "countries": ["US", "CA", "UK"],
            "license_fee": 50000.0,
            "currency": "USD",
            "royalty_rate": 15.5,
            "minimum_guarantee": 10000.0,
            "max_usage_count": 100,
            "max_duration_seconds": 3600,
            "exclusivity": True,
            "sublicensing_allowed": False,
            "metadata": {
                "contract_ref": "CONT-2025-001",
                "negotiated_by": "John Doe"
            },
            "notes": "Standard sync license with territorial restrictions"
        }
        
        response = await client.post(
            "/api/v1/rights/licenses",
            json=license_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["id"] is not None
        assert data["license_number"] == license_data["license_number"]
        assert data["license_type"] == license_data["license_type"]
        assert data["status"] == "active"
        assert data["countries"] == license_data["countries"]
        assert data["royalty_rate"] == license_data["royalty_rate"]
        assert data["exclusivity"] is True
    
    @pytest.mark.asyncio
    async def test_create_license_duplicate_number(
        self, client: AsyncClient, auth_headers: dict, test_parties: dict
    ):
        """Test creating license with duplicate number fails"""
        license_data = {
            "license_number": "LIC-DUP-001",
            "license_type": "master",
            "title": "Duplicate Test",
            "asset_id": str(uuid.uuid4()),
            "licensor_id": test_parties["licensor_id"],
            "licensee_id": test_parties["licensee_id"],
            "start_date": "2025-01-01",
            "geographic_scope": "worldwide"
        }
        
        # Create first license
        response1 = await client.post(
            "/api/v1/rights/licenses",
            json=license_data,
            headers=auth_headers
        )
        assert response1.status_code == status.HTTP_201_CREATED
        
        # Try to create duplicate
        response2 = await client.post(
            "/api/v1/rights/licenses",
            json=license_data,
            headers=auth_headers
        )
        assert response2.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    
    @pytest.mark.asyncio
    async def test_get_licenses_with_filters(
        self, client: AsyncClient, auth_headers: dict, test_parties: dict
    ):
        """Test getting licenses with various filters"""
        # Create multiple licenses
        asset_id = str(uuid.uuid4())
        
        # Active sync license
        await client.post(
            "/api/v1/rights/licenses",
            json={
                "license_number": "LIC-FILTER-001",
                "license_type": "sync",
                "status": "active",
                "title": "Active Sync License",
                "asset_id": asset_id,
                "licensor_id": test_parties["licensor_id"],
                "licensee_id": test_parties["licensee_id"],
                "start_date": "2025-01-01",
                "end_date": "2025-06-30",
                "geographic_scope": "worldwide"
            },
            headers=auth_headers
        )
        
        # Expired master license
        await client.post(
            "/api/v1/rights/licenses",
            json={
                "license_number": "LIC-FILTER-002",
                "license_type": "master",
                "status": "expired",
                "title": "Expired Master License",
                "asset_id": asset_id,
                "licensor_id": test_parties["licensor_id"],
                "licensee_id": test_parties["licensee_id"],
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "geographic_scope": "territory",
                "countries": ["US"]
            },
            headers=auth_headers
        )
        
        # Test status filter
        response = await client.get(
            "/api/v1/rights/licenses?status=active",
            headers=auth_headers
        )
        data = response.json()
        assert all(item["status"] == "active" for item in data["items"])
        
        # Test license_type filter
        response = await client.get(
            "/api/v1/rights/licenses?license_type=sync",
            headers=auth_headers
        )
        data = response.json()
        assert all(item["license_type"] == "sync" for item in data["items"])
        
        # Test asset_id filter
        response = await client.get(
            f"/api/v1/rights/licenses?asset_id={asset_id}",
            headers=auth_headers
        )
        data = response.json()
        assert len(data["items"]) >= 2
        assert all(item["asset_id"] == asset_id for item in data["items"])
    
    @pytest.mark.asyncio
    async def test_get_single_license(
        self, client: AsyncClient, auth_headers: dict, test_parties: dict
    ):
        """Test getting a single license"""
        # Create license
        create_response = await client.post(
            "/api/v1/rights/licenses",
            json={
                "license_number": "LIC-SINGLE-001",
                "license_type": "broadcast",
                "title": "Single License Test",
                "asset_id": str(uuid.uuid4()),
                "licensor_id": test_parties["licensor_id"],
                "licensee_id": test_parties["licensee_id"],
                "start_date": "2025-01-01",
                "geographic_scope": "worldwide",
                "license_fee": 25000.0,
                "currency": "EUR"
            },
            headers=auth_headers
        )
        license_id = create_response.json()["id"]
        
        # Get license
        response = await client.get(
            f"/api/v1/rights/licenses/{license_id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == license_id
        assert data["license_number"] == "LIC-SINGLE-001"
        assert data["currency"] == "EUR"
    
    @pytest.mark.asyncio
    async def test_update_license(
        self, client: AsyncClient, auth_headers: dict, test_parties: dict
    ):
        """Test updating a license"""
        # Create license
        create_response = await client.post(
            "/api/v1/rights/licenses",
            json={
                "license_number": "LIC-UPDATE-001",
                "license_type": "streaming",
                "title": "Original Title",
                "asset_id": str(uuid.uuid4()),
                "licensor_id": test_parties["licensor_id"],
                "licensee_id": test_parties["licensee_id"],
                "start_date": "2025-01-01",
                "geographic_scope": "worldwide",
                "status": "pending"
            },
            headers=auth_headers
        )
        license_id = create_response.json()["id"]
        
        # Update license
        update_data = {
            "title": "Updated Title",
            "status": "active",
            "end_date": "2026-12-31",
            "license_fee": 75000.0,
            "royalty_rate": 20.0,
            "notes": "License terms updated after negotiation"
        }
        
        response = await client.put(
            f"/api/v1/rights/licenses/{license_id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["status"] == "active"
        assert data["end_date"] == "2026-12-31"
        assert data["license_fee"] == 75000.0
        assert data["notes"] == update_data["notes"]
    
    @pytest.mark.asyncio
    async def test_delete_license(
        self, client: AsyncClient, auth_headers: dict, test_parties: dict, test_db: AsyncSession
    ):
        """Test deleting a license"""
        # Create license
        create_response = await client.post(
            "/api/v1/rights/licenses",
            json={
                "license_number": "LIC-DELETE-001",
                "license_type": "mechanical",
                "title": "Delete Test License",
                "asset_id": str(uuid.uuid4()),
                "licensor_id": test_parties["licensor_id"],
                "licensee_id": test_parties["licensee_id"],
                "start_date": "2025-01-01",
                "geographic_scope": "worldwide"
            },
            headers=auth_headers
        )
        license_id = create_response.json()["id"]
        
        # Delete license
        response = await client.delete(
            f"/api/v1/rights/licenses/{license_id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify deletion
        result = await test_db.execute(
            select(License).where(License.id == license_id)
        )
        license = result.scalar_one_or_none()
        assert license is None
    
    @pytest.mark.asyncio
    async def test_license_validation_rules(
        self, client: AsyncClient, auth_headers: dict, test_parties: dict
    ):
        """Test license validation rules"""
        base_data = {
            "license_number": "LIC-VAL-001",
            "license_type": "sync",
            "title": "Validation Test",
            "asset_id": str(uuid.uuid4()),
            "licensor_id": test_parties["licensor_id"],
            "licensee_id": test_parties["licensee_id"],
            "geographic_scope": "worldwide"
        }
        
        # Test invalid date range (end before start)
        invalid_data = {
            **base_data,
            "start_date": "2025-12-31",
            "end_date": "2025-01-01"
        }
        response = await client.post(
            "/api/v1/rights/licenses",
            json=invalid_data,
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        
        # Test invalid royalty rate (>100%)
        invalid_data = {
            **base_data,
            "start_date": "2025-01-01",
            "royalty_rate": 150.0
        }
        response = await client.post(
            "/api/v1/rights/licenses",
            json=invalid_data,
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        
        # Test negative financial values
        invalid_data = {
            **base_data,
            "start_date": "2025-01-01",
            "license_fee": -1000.0
        }
        response = await client.post(
            "/api/v1/rights/licenses",
            json=invalid_data,
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    
    @pytest.mark.asyncio
    async def test_bulk_create_licenses(
        self, client: AsyncClient, auth_headers: dict, test_parties: dict
    ):
        """Test bulk license creation"""
        bulk_data = {
            "licenses": [
                {
                    "license_number": f"LIC-BULK-{i:03d}",
                    "license_type": "sync",
                    "title": f"Bulk License {i}",
                    "asset_id": str(uuid.uuid4()),
                    "licensor_id": test_parties["licensor_id"],
                    "licensee_id": test_parties["licensee_id"],
                    "start_date": "2025-01-01",
                    "end_date": "2025-12-31",
                    "geographic_scope": "worldwide",
                    "license_fee": 10000.0 * i
                }
                for i in range(1, 6)
            ]
        }
        
        response = await client.post(
            "/api/v1/rights/bulk/licenses",
            json=bulk_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 5
        assert data["successful"] == 5
        assert data["failed"] == 0
        assert len(data["created_ids"]) == 5
    
    @pytest.mark.asyncio
    async def test_bulk_update_licenses(
        self, client: AsyncClient, auth_headers: dict, test_parties: dict
    ):
        """Test bulk license update"""
        # Create licenses to update
        license_ids = []
        for i in range(3):
            response = await client.post(
                "/api/v1/rights/licenses",
                json={
                    "license_number": f"LIC-BULK-UPDATE-{i:03d}",
                    "license_type": "broadcast",
                    "title": f"Original Title {i}",
                    "asset_id": str(uuid.uuid4()),
                    "licensor_id": test_parties["licensor_id"],
                    "licensee_id": test_parties["licensee_id"],
                    "start_date": "2025-01-01",
                    "geographic_scope": "worldwide",
                    "status": "pending"
                },
                headers=auth_headers
            )
            license_ids.append(response.json()["id"])
        
        # Bulk update
        bulk_update = {
            "license_ids": license_ids,
            "updates": {
                "status": "active",
                "end_date": "2026-06-30",
                "notes": "Bulk activated licenses"
            }
        }
        
        response = await client.put(
            "/api/v1/rights/bulk/licenses",
            json=bulk_update,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 3
        assert data["successful"] == 3
        
        # Verify updates
        for license_id in license_ids:
            response = await client.get(
                f"/api/v1/rights/licenses/{license_id}",
                headers=auth_headers
            )
            license_data = response.json()
            assert license_data["status"] == "active"
            assert license_data["end_date"] == "2026-06-30"
    
    @pytest.mark.asyncio
    async def test_get_asset_licenses(
        self, client: AsyncClient, auth_headers: dict, test_parties: dict
    ):
        """Test getting all licenses for a specific asset"""
        asset_id = str(uuid.uuid4())
        
        # Create multiple licenses for the same asset
        license_types = ["sync", "master", "broadcast", "streaming"]
        for i, license_type in enumerate(license_types):
            await client.post(
                "/api/v1/rights/licenses",
                json={
                    "license_number": f"LIC-ASSET-{i:03d}",
                    "license_type": license_type,
                    "title": f"{license_type.title()} License",
                    "asset_id": asset_id,
                    "licensor_id": test_parties["licensor_id"],
                    "licensee_id": test_parties["licensee_id"],
                    "start_date": "2025-01-01",
                    "geographic_scope": "worldwide"
                },
                headers=auth_headers
            )
        
        # Get asset licenses
        response = await client.get(
            f"/api/v1/rights/assets/{asset_id}/licenses",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 4
        assert set(license["license_type"] for license in data) == set(license_types)
    
    @pytest.mark.asyncio
    async def test_license_audit_trail(
        self, client: AsyncClient, auth_headers: dict, test_parties: dict, test_db: AsyncSession
    ):
        """Test that license changes are tracked in audit log"""
        # Create license
        create_response = await client.post(
            "/api/v1/rights/licenses",
            json={
                "license_number": "LIC-AUDIT-001",
                "license_type": "sync",
                "title": "Audit Test License",
                "asset_id": str(uuid.uuid4()),
                "licensor_id": test_parties["licensor_id"],
                "licensee_id": test_parties["licensee_id"],
                "start_date": "2025-01-01",
                "geographic_scope": "worldwide"
            },
            headers=auth_headers
        )
        license_id = create_response.json()["id"]
        
        # Update license
        await client.put(
            f"/api/v1/rights/licenses/{license_id}",
            json={
                "title": "Updated Audit Test License",
                "status": "active"
            },
            headers=auth_headers
        )
        
        # Check audit logs
        result = await test_db.execute(
            select(LicenseAuditLog)
            .where(LicenseAuditLog.license_id == license_id)
            .order_by(LicenseAuditLog.created_at)
        )
        audit_logs = result.scalars().all()
        
        assert len(audit_logs) >= 2
        assert audit_logs[0].action == "created"
        assert audit_logs[1].action == "updated"
        assert "title" in audit_logs[1].changed_fields
        assert "status" in audit_logs[1].changed_fields