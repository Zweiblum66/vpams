"""
Tests for Compliance Management API

Tests compliance checking, alerts, and reporting functionality.
"""

import pytest
from httpx import AsyncClient
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from datetime import datetime, date, timedelta

from src.db.models import ComplianceAlert, License
from src.models.schemas import RightsComplianceCheck


class TestComplianceEndpoints:
    """Test compliance API endpoints"""
    
    @pytest.fixture
    async def test_setup(self, client: AsyncClient, auth_headers: dict):
        """Create test data for compliance tests"""
        # Create licensor
        licensor_response = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensor",
                "name": "Compliance Test Licensor",
                "contact_email": "compliance.licensor@test.com",
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
                "name": "Compliance Test Licensee",
                "contact_email": "compliance.licensee@test.com",
                "country": "UK"
            },
            headers=auth_headers
        )
        licensee_id = licensee_response.json()["id"]
        
        # Create licenses with different restrictions
        asset_id = str(uuid.uuid4())
        
        # Geographic restricted license
        geo_license_response = await client.post(
            "/api/v1/rights/licenses",
            json={
                "license_number": "LIC-COMP-GEO-001",
                "license_type": "broadcast",
                "title": "Geographic Restricted License",
                "asset_id": asset_id,
                "licensor_id": licensor_id,
                "licensee_id": licensee_id,
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "geographic_scope": "territory",
                "countries": ["US", "CA"],
                "status": "active"
            },
            headers=auth_headers
        )
        
        # Time restricted license
        time_license_response = await client.post(
            "/api/v1/rights/licenses",
            json={
                "license_number": "LIC-COMP-TIME-001",
                "license_type": "streaming",
                "title": "Time Restricted License",
                "asset_id": asset_id,
                "licensor_id": licensor_id,
                "licensee_id": licensee_id,
                "start_date": "2025-01-01",
                "end_date": "2025-06-30",
                "geographic_scope": "worldwide",
                "status": "active"
            },
            headers=auth_headers
        )
        
        # Usage limited license
        usage_license_response = await client.post(
            "/api/v1/rights/licenses",
            json={
                "license_number": "LIC-COMP-USAGE-001",
                "license_type": "sync",
                "title": "Usage Limited License",
                "asset_id": asset_id,
                "licensor_id": licensor_id,
                "licensee_id": licensee_id,
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "geographic_scope": "worldwide",
                "max_usage_count": 10,
                "max_duration_seconds": 3600,
                "status": "active"
            },
            headers=auth_headers
        )
        
        return {
            "asset_id": asset_id,
            "geo_license_id": geo_license_response.json()["id"],
            "time_license_id": time_license_response.json()["id"],
            "usage_license_id": usage_license_response.json()["id"],
            "licensor_id": licensor_id,
            "licensee_id": licensee_id
        }
    
    @pytest.mark.asyncio
    async def test_check_compliance_geographic_valid(
        self, client: AsyncClient, auth_headers: dict, test_setup: dict
    ):
        """Test compliance check for valid geographic usage"""
        compliance_check = {
            "asset_id": test_setup["asset_id"],
            "license_id": test_setup["geo_license_id"],
            "usage_type": "broadcast",
            "usage_date": datetime.utcnow().isoformat(),
            "country": "US",  # Valid country
            "platform": "Television"
        }
        
        response = await client.post(
            "/api/v1/rights/compliance/check",
            json=compliance_check,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_compliant"] is True
        assert len(data["violations"]) == 0
        assert "geographic" in data["checks_performed"]
    
    @pytest.mark.asyncio
    async def test_check_compliance_geographic_invalid(
        self, client: AsyncClient, auth_headers: dict, test_setup: dict
    ):
        """Test compliance check for invalid geographic usage"""
        compliance_check = {
            "asset_id": test_setup["asset_id"],
            "license_id": test_setup["geo_license_id"],
            "usage_type": "broadcast",
            "usage_date": datetime.utcnow().isoformat(),
            "country": "UK",  # Invalid country
            "platform": "Television"
        }
        
        response = await client.post(
            "/api/v1/rights/compliance/check",
            json=compliance_check,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_compliant"] is False
        assert len(data["violations"]) > 0
        assert any(v["violation_type"] == "geographic_restriction" for v in data["violations"])
    
    @pytest.mark.asyncio
    async def test_check_compliance_temporal_expired(
        self, client: AsyncClient, auth_headers: dict, test_setup: dict
    ):
        """Test compliance check for expired license"""
        future_date = datetime(2025, 7, 1)  # After license end date
        
        compliance_check = {
            "asset_id": test_setup["asset_id"],
            "license_id": test_setup["time_license_id"],
            "usage_type": "streaming",
            "usage_date": future_date.isoformat(),
            "country": "US",
            "platform": "OTT Platform"
        }
        
        response = await client.post(
            "/api/v1/rights/compliance/check",
            json=compliance_check,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_compliant"] is False
        assert any(v["violation_type"] == "temporal_restriction" for v in data["violations"])
        assert any("expired" in v["description"].lower() for v in data["violations"])
    
    @pytest.mark.asyncio
    async def test_check_compliance_usage_limits(
        self, client: AsyncClient, auth_headers: dict, test_setup: dict
    ):
        """Test compliance check for usage limits"""
        # First, create usage records to approach the limit
        for i in range(8):
            await client.post(
                "/api/v1/rights/usage",
                json={
                    "license_id": test_setup["usage_license_id"],
                    "asset_id": test_setup["asset_id"],
                    "user_id": str(uuid.uuid4()),
                    "usage_type": "sync",
                    "usage_date": (datetime.utcnow() - timedelta(days=i)).isoformat(),
                    "duration_seconds": 300,
                    "usage_count": 1,
                    "platform": "Film",
                    "country": "USA"
                },
                headers=auth_headers
            )
        
        # Check compliance - should show warning about approaching limit
        compliance_check = {
            "asset_id": test_setup["asset_id"],
            "license_id": test_setup["usage_license_id"],
            "usage_type": "sync",
            "usage_date": datetime.utcnow().isoformat(),
            "country": "US",
            "platform": "Film"
        }
        
        response = await client.post(
            "/api/v1/rights/compliance/check",
            json=compliance_check,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_compliant"] is True  # Still compliant but with warnings
        assert len(data["warnings"]) > 0
        assert any("approaching limit" in w["description"].lower() for w in data["warnings"])
    
    @pytest.mark.asyncio
    async def test_get_compliance_alerts(
        self, client: AsyncClient, auth_headers: dict, test_setup: dict
    ):
        """Test getting compliance alerts"""
        # Generate some compliance violations to create alerts
        for i in range(3):
            await client.post(
                "/api/v1/rights/compliance/check",
                json={
                    "asset_id": test_setup["asset_id"],
                    "license_id": test_setup["geo_license_id"],
                    "usage_type": "broadcast",
                    "usage_date": datetime.utcnow().isoformat(),
                    "country": "JP",  # Invalid country
                    "platform": "Television"
                },
                headers=auth_headers
            )
        
        # Get compliance alerts
        response = await client.get(
            "/api/v1/rights/compliance/alerts",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) > 0
        assert data["total"] > 0
    
    @pytest.mark.asyncio
    async def test_get_compliance_alerts_filtered(
        self, client: AsyncClient, auth_headers: dict, test_db: AsyncSession
    ):
        """Test getting compliance alerts with filters"""
        # Create alerts with different severities
        alert1 = ComplianceAlert(
            license_id=str(uuid.uuid4()),
            asset_id=str(uuid.uuid4()),
            alert_type="usage_limit_exceeded",
            severity="high",
            title="Usage Limit Exceeded",
            description="License usage limit has been exceeded",
            is_resolved=False
        )
        
        alert2 = ComplianceAlert(
            license_id=str(uuid.uuid4()),
            asset_id=str(uuid.uuid4()),
            alert_type="expiration_warning",
            severity="medium",
            title="License Expiring Soon",
            description="License will expire in 30 days",
            is_resolved=False
        )
        
        alert3 = ComplianceAlert(
            license_id=str(uuid.uuid4()),
            asset_id=str(uuid.uuid4()),
            alert_type="geographic_violation",
            severity="critical",
            title="Geographic Violation",
            description="Usage detected in restricted territory",
            is_resolved=True,
            resolved_at=datetime.utcnow(),
            resolution_notes="False positive - VPN usage"
        )
        
        test_db.add_all([alert1, alert2, alert3])
        await test_db.commit()
        
        # Test severity filter
        response = await client.get(
            "/api/v1/rights/compliance/alerts?severity=high",
            headers=auth_headers
        )
        data = response.json()
        assert all(item["severity"] == "high" for item in data["items"])
        
        # Test is_resolved filter
        response = await client.get(
            "/api/v1/rights/compliance/alerts?is_resolved=false",
            headers=auth_headers
        )
        data = response.json()
        assert all(item["is_resolved"] is False for item in data["items"])
    
    @pytest.mark.asyncio
    async def test_resolve_compliance_alert(
        self, client: AsyncClient, auth_headers: dict, test_db: AsyncSession
    ):
        """Test resolving a compliance alert"""
        # Create an alert
        alert = ComplianceAlert(
            license_id=str(uuid.uuid4()),
            asset_id=str(uuid.uuid4()),
            alert_type="usage_limit_exceeded",
            severity="high",
            title="Test Alert",
            description="Test alert for resolution",
            is_resolved=False
        )
        test_db.add(alert)
        await test_db.commit()
        await test_db.refresh(alert)
        
        # Resolve the alert
        response = await client.put(
            f"/api/v1/rights/compliance/alerts/{alert.id}/resolve",
            params={"resolution_notes": "Issue has been addressed and resolved"},
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify resolution
        result = await test_db.execute(
            select(ComplianceAlert).where(ComplianceAlert.id == alert.id)
        )
        resolved_alert = result.scalar_one()
        assert resolved_alert.is_resolved is True
        assert resolved_alert.resolved_at is not None
        assert resolved_alert.resolution_notes == "Issue has been addressed and resolved"
    
    @pytest.mark.asyncio
    async def test_asset_compliance_check(
        self, client: AsyncClient, auth_headers: dict, test_setup: dict
    ):
        """Test compliance check for an entire asset"""
        response = await client.get(
            f"/api/v1/rights/assets/{test_setup['asset_id']}/compliance?usage_type=broadcast&country=UK",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "is_compliant" in data
        assert "checks_performed" in data
        assert "applicable_licenses" in data
    
    @pytest.mark.asyncio
    async def test_compliance_with_multiple_licenses(
        self, client: AsyncClient, auth_headers: dict, test_setup: dict
    ):
        """Test compliance when multiple licenses exist for an asset"""
        # Create an additional worldwide license
        await client.post(
            "/api/v1/rights/licenses",
            json={
                "license_number": "LIC-COMP-WORLD-001",
                "license_type": "broadcast",
                "title": "Worldwide License",
                "asset_id": test_setup["asset_id"],
                "licensor_id": test_setup["licensor_id"],
                "licensee_id": test_setup["licensee_id"],
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "geographic_scope": "worldwide",
                "status": "active"
            },
            headers=auth_headers
        )
        
        # Check compliance for UK (should pass due to worldwide license)
        response = await client.get(
            f"/api/v1/rights/assets/{test_setup['asset_id']}/compliance?usage_type=broadcast&country=UK",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_compliant"] is True
        assert len(data["applicable_licenses"]) > 1
    
    @pytest.mark.asyncio
    async def test_compliance_report_generation(
        self, client: AsyncClient, auth_headers: dict, test_setup: dict
    ):
        """Test compliance report generation"""
        # Generate some compliance data
        for i in range(5):
            await client.post(
                "/api/v1/rights/usage",
                json={
                    "license_id": test_setup["geo_license_id"],
                    "asset_id": test_setup["asset_id"],
                    "user_id": str(uuid.uuid4()),
                    "usage_type": "broadcast",
                    "usage_date": (datetime.utcnow() - timedelta(days=i)).isoformat(),
                    "duration_seconds": 1800,
                    "platform": "Television",
                    "country": "US" if i % 2 == 0 else "UK"  # Mix valid and invalid
                },
                headers=auth_headers
            )
        
        # Generate compliance report
        start_date = (datetime.utcnow() - timedelta(days=7)).date()
        end_date = datetime.utcnow().date()
        
        response = await client.get(
            f"/api/v1/rights/restrictions/compliance-report?asset_id={test_setup['asset_id']}&start_date={start_date}&end_date={end_date}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "report_metadata" in data
        assert "summary" in data
        assert "license_restrictions" in data
        assert "compliance_violations" in data
        assert data["summary"]["total_licenses"] >= 3
    
    @pytest.mark.asyncio
    async def test_compliance_with_custom_restrictions(
        self, client: AsyncClient, auth_headers: dict, test_setup: dict
    ):
        """Test compliance with custom metadata restrictions"""
        # Create license with custom restrictions
        license_response = await client.post(
            "/api/v1/rights/licenses",
            json={
                "license_number": "LIC-COMP-CUSTOM-001",
                "license_type": "streaming",
                "title": "Custom Restricted License",
                "asset_id": test_setup["asset_id"],
                "licensor_id": test_setup["licensor_id"],
                "licensee_id": test_setup["licensee_id"],
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "geographic_scope": "worldwide",
                "status": "active",
                "metadata": {
                    "restrictions": {
                        "allowed_platforms": ["Netflix", "Amazon Prime"],
                        "blackout_dates": [
                            {
                                "start": "2025-12-20",
                                "end": "2025-12-27",
                                "reason": "Holiday blackout"
                            }
                        ],
                        "content_rating_limit": "PG-13",
                        "language_restrictions": ["English", "Spanish"]
                    }
                }
            },
            headers=auth_headers
        )
        
        license_id = license_response.json()["id"]
        
        # Check compliance with allowed platform
        compliance_check = {
            "asset_id": test_setup["asset_id"],
            "license_id": license_id,
            "usage_type": "streaming",
            "usage_date": datetime.utcnow().isoformat(),
            "country": "US",
            "platform": "Netflix",
            "metadata": {
                "content_rating": "PG",
                "language": "English"
            }
        }
        
        response = await client.post(
            "/api/v1/rights/compliance/check",
            json=compliance_check,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_compliant"] is True
        
        # Check compliance with disallowed platform
        compliance_check["platform"] = "Disney+"
        
        response = await client.post(
            "/api/v1/rights/compliance/check",
            json=compliance_check,
            headers=auth_headers
        )
        
        data = response.json()
        assert data["is_compliant"] is False
        assert any("platform" in v["description"].lower() for v in data["violations"])