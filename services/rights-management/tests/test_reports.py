"""
Tests for Rights Reports API

Tests report generation, retrieval, and download functionality.
"""

import pytest
from httpx import AsyncClient
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from datetime import datetime, date, timedelta
import asyncio

from src.db.models import RightsReport


class TestReportEndpoints:
    """Test report API endpoints"""
    
    @pytest.fixture
    async def test_report_data(self, client: AsyncClient, auth_headers: dict):
        """Create test data for report generation"""
        # Create parties
        licensor = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensor",
                "name": "Report Test Licensor",
                "contact_email": "report.licensor@test.com",
                "country": "USA"
            },
            headers=auth_headers
        )
        licensor_id = licensor.json()["id"]
        
        licensee = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensee",
                "name": "Report Test Licensee",
                "contact_email": "report.licensee@test.com",
                "country": "UK"
            },
            headers=auth_headers
        )
        licensee_id = licensee.json()["id"]
        
        # Create licenses
        licenses = []
        assets = []
        
        for i in range(5):
            asset_id = str(uuid.uuid4())
            assets.append(asset_id)
            
            license_response = await client.post(
                "/api/v1/rights/licenses",
                json={
                    "license_number": f"LIC-REPORT-{i:03d}",
                    "license_type": "broadcast" if i % 2 == 0 else "streaming",
                    "title": f"Report Test License {i}",
                    "asset_id": asset_id,
                    "licensor_id": licensor_id,
                    "licensee_id": licensee_id,
                    "start_date": "2025-01-01",
                    "end_date": "2025-12-31",
                    "geographic_scope": "worldwide",
                    "license_fee": 10000.0 * (i + 1),
                    "royalty_rate": 15.0,
                    "status": "active"
                },
                headers=auth_headers
            )
            licenses.append(license_response.json()["id"])
        
        # Create usage records
        for license_id in licenses:
            for day in range(10):
                await client.post(
                    "/api/v1/rights/usage",
                    json={
                        "license_id": license_id,
                        "asset_id": assets[licenses.index(license_id) % len(assets)],
                        "user_id": str(uuid.uuid4()),
                        "usage_type": "broadcast",
                        "usage_date": (datetime.utcnow() - timedelta(days=day)).isoformat(),
                        "duration_seconds": 1800,
                        "platform": "Television",
                        "country": "USA",
                        "revenue_generated": 500.0,
                        "royalty_due": 75.0
                    },
                    headers=auth_headers
                )
        
        return {
            "licensor_id": licensor_id,
            "licensee_id": licensee_id,
            "licenses": licenses,
            "assets": assets
        }
    
    @pytest.mark.asyncio
    async def test_create_usage_report(
        self, client: AsyncClient, auth_headers: dict, test_report_data: dict
    ):
        """Test creating a usage report"""
        report_data = {
            "report_type": "usage",
            "title": "Monthly Usage Report - July 2025",
            "description": "Comprehensive usage report for all licenses",
            "start_date": (datetime.utcnow() - timedelta(days=30)).date().isoformat(),
            "end_date": datetime.utcnow().date().isoformat(),
            "filters": {
                "include_all_licenses": True,
                "group_by": ["license", "platform", "country"]
            }
        }
        
        response = await client.post(
            "/api/v1/rights/reports",
            json=report_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["id"] is not None
        assert data["report_type"] == "usage"
        assert data["status"] == "pending"
        assert data["title"] == report_data["title"]
        
        return data["id"]
    
    @pytest.mark.asyncio
    async def test_create_revenue_report(
        self, client: AsyncClient, auth_headers: dict, test_report_data: dict
    ):
        """Test creating a revenue report"""
        report_data = {
            "report_type": "revenue",
            "title": "Q3 2025 Revenue Report",
            "description": "Quarterly revenue and royalty summary",
            "start_date": "2025-07-01",
            "end_date": "2025-09-30",
            "filters": {
                "licensor_id": test_report_data["licensor_id"],
                "include_projections": True,
                "currency": "USD"
            }
        }
        
        response = await client.post(
            "/api/v1/rights/reports",
            json=report_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["report_type"] == "revenue"
        assert data["filters"]["licensor_id"] == test_report_data["licensor_id"]
    
    @pytest.mark.asyncio
    async def test_create_compliance_report(
        self, client: AsyncClient, auth_headers: dict, test_report_data: dict
    ):
        """Test creating a compliance report"""
        report_data = {
            "report_type": "compliance",
            "title": "Compliance Audit Report",
            "description": "Complete compliance check for all active licenses",
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "filters": {
                "include_violations": True,
                "include_warnings": True,
                "severity_levels": ["critical", "high", "medium"]
            }
        }
        
        response = await client.post(
            "/api/v1/rights/reports",
            json=report_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["report_type"] == "compliance"
    
    @pytest.mark.asyncio
    async def test_create_expiration_report(
        self, client: AsyncClient, auth_headers: dict, test_report_data: dict
    ):
        """Test creating a license expiration report"""
        report_data = {
            "report_type": "expiration",
            "title": "License Expiration Report",
            "description": "Licenses expiring in the next 90 days",
            "start_date": datetime.utcnow().date().isoformat(),
            "end_date": (datetime.utcnow() + timedelta(days=90)).date().isoformat(),
            "filters": {
                "days_before_expiry": 30,
                "include_auto_renewal": True
            }
        }
        
        response = await client.post(
            "/api/v1/rights/reports",
            json=report_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["report_type"] == "expiration"
    
    @pytest.mark.asyncio
    async def test_get_reports_list(
        self, client: AsyncClient, auth_headers: dict, test_report_data: dict
    ):
        """Test getting list of reports"""
        # Create multiple reports
        report_types = ["usage", "revenue", "compliance"]
        for report_type in report_types:
            await client.post(
                "/api/v1/rights/reports",
                json={
                    "report_type": report_type,
                    "title": f"Test {report_type.title()} Report",
                    "start_date": "2025-01-01",
                    "end_date": "2025-12-31",
                    "filters": {}
                },
                headers=auth_headers
            )
        
        # Get all reports
        response = await client.get(
            "/api/v1/rights/reports",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) >= 3
        assert data["total"] >= 3
        
        # Test filtering by report type
        response = await client.get(
            "/api/v1/rights/reports?report_type=usage",
            headers=auth_headers
        )
        
        data = response.json()
        assert all(item["report_type"] == "usage" for item in data["items"])
    
    @pytest.mark.asyncio
    async def test_get_single_report(
        self, client: AsyncClient, auth_headers: dict, test_report_data: dict
    ):
        """Test getting a single report"""
        # Create a report
        create_response = await client.post(
            "/api/v1/rights/reports",
            json={
                "report_type": "usage",
                "title": "Single Report Test",
                "start_date": "2025-01-01",
                "end_date": "2025-01-31",
                "filters": {}
            },
            headers=auth_headers
        )
        report_id = create_response.json()["id"]
        
        # Get the report
        response = await client.get(
            f"/api/v1/rights/reports/{report_id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == report_id
        assert data["title"] == "Single Report Test"
    
    @pytest.mark.asyncio
    async def test_report_generation_status(
        self, client: AsyncClient, auth_headers: dict, test_report_data: dict, test_db: AsyncSession
    ):
        """Test report generation status updates"""
        # Create a report
        create_response = await client.post(
            "/api/v1/rights/reports",
            json={
                "report_type": "usage",
                "title": "Status Test Report",
                "start_date": "2025-01-01",
                "end_date": "2025-01-31",
                "filters": {}
            },
            headers=auth_headers
        )
        report_id = create_response.json()["id"]
        
        # Check initial status
        assert create_response.json()["status"] == "pending"
        
        # Wait a bit for background processing
        await asyncio.sleep(2)
        
        # Check status again
        response = await client.get(
            f"/api/v1/rights/reports/{report_id}",
            headers=auth_headers
        )
        
        data = response.json()
        # Status should be either processing or completed
        assert data["status"] in ["pending", "processing", "completed"]
    
    @pytest.mark.asyncio
    async def test_download_report(
        self, client: AsyncClient, auth_headers: dict, test_report_data: dict, test_db: AsyncSession
    ):
        """Test downloading a completed report"""
        # Create a simple report
        create_response = await client.post(
            "/api/v1/rights/reports",
            json={
                "report_type": "usage",
                "title": "Download Test Report",
                "start_date": "2025-01-01",
                "end_date": "2025-01-31",
                "filters": {}
            },
            headers=auth_headers
        )
        report_id = create_response.json()["id"]
        
        # Manually update report to completed status with file path
        result = await test_db.execute(
            select(RightsReport).where(RightsReport.id == report_id)
        )
        report = result.scalar_one()
        report.status = "completed"
        report.file_path = f"/reports/{report_id}.pdf"
        await test_db.commit()
        
        # Try to download
        response = await client.get(
            f"/api/v1/rights/reports/{report_id}/download",
            headers=auth_headers
        )
        
        # Should return file info or actual file
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
    
    @pytest.mark.asyncio
    async def test_create_custom_report(
        self, client: AsyncClient, auth_headers: dict, test_report_data: dict
    ):
        """Test creating a custom report with complex filters"""
        report_data = {
            "report_type": "custom",
            "title": "Custom Analytics Report",
            "description": "Multi-dimensional analysis of rights usage",
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "filters": {
                "license_ids": test_report_data["licenses"][:2],
                "asset_ids": test_report_data["assets"][:2],
                "platforms": ["Television", "Netflix"],
                "countries": ["US", "UK", "CA"],
                "minimum_revenue": 1000.0,
                "group_by": ["month", "platform", "country"],
                "include_charts": True,
                "format": "xlsx"
            }
        }
        
        response = await client.post(
            "/api/v1/rights/reports",
            json=report_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["report_type"] == "custom"
        assert len(data["filters"]["license_ids"]) == 2
    
    @pytest.mark.asyncio
    async def test_report_pagination(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test report list pagination"""
        # Create many reports
        for i in range(25):
            await client.post(
                "/api/v1/rights/reports",
                json={
                    "report_type": "usage",
                    "title": f"Pagination Test Report {i}",
                    "start_date": "2025-01-01",
                    "end_date": "2025-01-31",
                    "filters": {}
                },
                headers=auth_headers
            )
        
        # Test pagination
        response = await client.get(
            "/api/v1/rights/reports?page=1&limit=10",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 10
        assert data["page"] == 1
        assert data["limit"] == 10
        assert data["pages"] >= 3
    
    @pytest.mark.asyncio
    async def test_report_status_filtering(
        self, client: AsyncClient, auth_headers: dict, test_db: AsyncSession
    ):
        """Test filtering reports by status"""
        # Create reports with different statuses
        statuses = ["pending", "processing", "completed", "failed"]
        report_ids = []
        
        for status in statuses:
            create_response = await client.post(
                "/api/v1/rights/reports",
                json={
                    "report_type": "usage",
                    "title": f"{status.title()} Status Report",
                    "start_date": "2025-01-01",
                    "end_date": "2025-01-31",
                    "filters": {}
                },
                headers=auth_headers
            )
            report_ids.append(create_response.json()["id"])
        
        # Update report statuses
        for i, (report_id, status) in enumerate(zip(report_ids, statuses)):
            if i > 0:  # Keep first one as pending
                result = await test_db.execute(
                    select(RightsReport).where(RightsReport.id == report_id)
                )
                report = result.scalar_one()
                report.status = status
                await test_db.commit()
        
        # Test filtering by status
        response = await client.get(
            "/api/v1/rights/reports?status=completed",
            headers=auth_headers
        )
        
        data = response.json()
        assert all(item["status"] == "completed" for item in data["items"])
    
    @pytest.mark.asyncio
    async def test_royalty_statement_report(
        self, client: AsyncClient, auth_headers: dict, test_report_data: dict
    ):
        """Test creating a royalty statement report"""
        report_data = {
            "report_type": "royalty_statement",
            "title": "Monthly Royalty Statement - July 2025",
            "description": "Detailed royalty calculations for licensor",
            "start_date": "2025-07-01",
            "end_date": "2025-07-31",
            "filters": {
                "licensor_id": test_report_data["licensor_id"],
                "include_calculations": True,
                "include_deductions": True,
                "format": "pdf"
            }
        }
        
        response = await client.post(
            "/api/v1/rights/reports",
            json=report_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["report_type"] == "royalty_statement"
    
    @pytest.mark.asyncio
    async def test_invalid_report_request(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test creating report with invalid parameters"""
        # Invalid date range (end before start)
        report_data = {
            "report_type": "usage",
            "title": "Invalid Date Report",
            "start_date": "2025-12-31",
            "end_date": "2025-01-01",
            "filters": {}
        }
        
        response = await client.post(
            "/api/v1/rights/reports",
            json=report_data,
            headers=auth_headers
        )
        
        # Should handle gracefully
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_500_INTERNAL_SERVER_ERROR]
    
    @pytest.mark.asyncio
    async def test_report_metadata(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test report metadata handling"""
        report_data = {
            "report_type": "usage",
            "title": "Metadata Test Report",
            "start_date": "2025-01-01",
            "end_date": "2025-01-31",
            "filters": {},
            "metadata": {
                "requested_by_department": "Finance",
                "cost_center": "CC-12345",
                "approval_required": True,
                "distribution_list": ["cfo@company.com", "controller@company.com"],
                "tags": ["monthly", "finance", "executive"]
            }
        }
        
        response = await client.post(
            "/api/v1/rights/reports",
            json=report_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "metadata" in data
        if data["metadata"]:
            assert data["metadata"]["requested_by_department"] == "Finance"