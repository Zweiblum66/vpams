"""
Tests for Usage Records Management API

Tests CRUD operations and business logic for usage tracking.
"""

import pytest
from httpx import AsyncClient
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from datetime import datetime, date, timedelta

from src.db.models import UsageRecord, License
from src.models.schemas import UsageRecordCreate, UsageRecordUpdate


class TestUsageRecordEndpoints:
    """Test usage record API endpoints"""
    
    @pytest.fixture
    async def test_license(self, client: AsyncClient, auth_headers: dict):
        """Create test license for usage record tests"""
        # Create licensor
        licensor_response = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensor",
                "name": "Usage Test Licensor",
                "contact_email": "usage.licensor@test.com",
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
                "name": "Usage Test Licensee",
                "contact_email": "usage.licensee@test.com",
                "country": "UK"
            },
            headers=auth_headers
        )
        licensee_id = licensee_response.json()["id"]
        
        # Create license
        asset_id = str(uuid.uuid4())
        license_response = await client.post(
            "/api/v1/rights/licenses",
            json={
                "license_number": "LIC-USAGE-TEST-001",
                "license_type": "broadcast",
                "title": "Usage Test License",
                "asset_id": asset_id,
                "licensor_id": licensor_id,
                "licensee_id": licensee_id,
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "geographic_scope": "worldwide",
                "max_usage_count": 50,
                "max_duration_seconds": 7200,
                "royalty_rate": 15.0
            },
            headers=auth_headers
        )
        
        return {
            "license_id": license_response.json()["id"],
            "asset_id": asset_id,
            "licensor_id": licensor_id,
            "licensee_id": licensee_id
        }
    
    @pytest.mark.asyncio
    async def test_create_usage_record_success(
        self, client: AsyncClient, auth_headers: dict, test_license: dict
    ):
        """Test successful usage record creation"""
        usage_data = {
            "license_id": test_license["license_id"],
            "asset_id": test_license["asset_id"],
            "user_id": str(uuid.uuid4()),
            "usage_type": "broadcast",
            "usage_date": datetime.utcnow().isoformat(),
            "duration_seconds": 3600,
            "usage_count": 1,
            "platform": "Television",
            "channel": "ABC Network",
            "program_title": "Evening News",
            "episode_title": "July 18, 2025 Edition",
            "country": "USA",
            "region": "East Coast",
            "revenue_generated": 5000.0,
            "royalty_due": 750.0,
            "metadata": {
                "time_slot": "prime_time",
                "audience_size": "5M",
                "broadcast_quality": "HD"
            },
            "notes": "Prime time broadcast"
        }
        
        response = await client.post(
            "/api/v1/rights/usage",
            json=usage_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["id"] is not None
        assert data["license_id"] == test_license["license_id"]
        assert data["usage_type"] == "broadcast"
        assert data["duration_seconds"] == 3600
        assert data["revenue_generated"] == 5000.0
        assert data["royalty_due"] == 750.0
    
    @pytest.mark.asyncio
    async def test_create_usage_record_exceeds_limits(
        self, client: AsyncClient, auth_headers: dict, test_license: dict
    ):
        """Test usage record creation that exceeds license limits"""
        # Create usage that exceeds duration limit
        usage_data = {
            "license_id": test_license["license_id"],
            "asset_id": test_license["asset_id"],
            "user_id": str(uuid.uuid4()),
            "usage_type": "broadcast",
            "usage_date": datetime.utcnow().isoformat(),
            "duration_seconds": 10000,  # Exceeds max of 7200
            "usage_count": 1,
            "platform": "Television",
            "country": "USA"
        }
        
        response = await client.post(
            "/api/v1/rights/usage",
            json=usage_data,
            headers=auth_headers
        )
        
        # Should still create but potentially flag for compliance
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["duration_seconds"] == 10000
    
    @pytest.mark.asyncio
    async def test_get_usage_records_with_filters(
        self, client: AsyncClient, auth_headers: dict, test_license: dict
    ):
        """Test getting usage records with various filters"""
        # Create multiple usage records
        user_id = str(uuid.uuid4())
        
        # Broadcast usage
        await client.post(
            "/api/v1/rights/usage",
            json={
                "license_id": test_license["license_id"],
                "asset_id": test_license["asset_id"],
                "user_id": user_id,
                "usage_type": "broadcast",
                "usage_date": datetime.utcnow().isoformat(),
                "duration_seconds": 1800,
                "platform": "Television",
                "country": "USA"
            },
            headers=auth_headers
        )
        
        # Streaming usage
        await client.post(
            "/api/v1/rights/usage",
            json={
                "license_id": test_license["license_id"],
                "asset_id": test_license["asset_id"],
                "user_id": user_id,
                "usage_type": "streaming",
                "usage_date": datetime.utcnow().isoformat(),
                "duration_seconds": 2400,
                "platform": "OTT Platform",
                "country": "UK"
            },
            headers=auth_headers
        )
        
        # Test usage_type filter
        response = await client.get(
            "/api/v1/rights/usage?usage_type=broadcast",
            headers=auth_headers
        )
        data = response.json()
        assert all(item["usage_type"] == "broadcast" for item in data["items"])
        
        # Test platform filter
        response = await client.get(
            "/api/v1/rights/usage?platform=Television",
            headers=auth_headers
        )
        data = response.json()
        assert all(item["platform"] == "Television" for item in data["items"])
        
        # Test license_id filter
        response = await client.get(
            f"/api/v1/rights/usage?license_id={test_license['license_id']}",
            headers=auth_headers
        )
        data = response.json()
        assert len(data["items"]) >= 2
    
    @pytest.mark.asyncio
    async def test_get_single_usage_record(
        self, client: AsyncClient, auth_headers: dict, test_license: dict
    ):
        """Test getting a single usage record"""
        # Create usage record
        create_response = await client.post(
            "/api/v1/rights/usage",
            json={
                "license_id": test_license["license_id"],
                "asset_id": test_license["asset_id"],
                "user_id": str(uuid.uuid4()),
                "usage_type": "streaming",
                "usage_date": datetime.utcnow().isoformat(),
                "duration_seconds": 5400,
                "platform": "Netflix",
                "country": "Global",
                "revenue_generated": 15000.0
            },
            headers=auth_headers
        )
        usage_id = create_response.json()["id"]
        
        # Get usage record
        response = await client.get(
            f"/api/v1/rights/usage/{usage_id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == usage_id
        assert data["platform"] == "Netflix"
        assert data["revenue_generated"] == 15000.0
    
    @pytest.mark.asyncio
    async def test_bulk_create_usage_records(
        self, client: AsyncClient, auth_headers: dict, test_license: dict
    ):
        """Test bulk usage record creation"""
        bulk_data = {
            "usage_records": [
                {
                    "license_id": test_license["license_id"],
                    "asset_id": test_license["asset_id"],
                    "user_id": str(uuid.uuid4()),
                    "usage_type": "broadcast",
                    "usage_date": (datetime.utcnow() - timedelta(days=i)).isoformat(),
                    "duration_seconds": 1800,
                    "usage_count": 1,
                    "platform": "Television",
                    "channel": f"Channel {i}",
                    "country": "USA",
                    "revenue_generated": 1000.0 * i,
                    "royalty_due": 150.0 * i
                }
                for i in range(1, 6)
            ]
        }
        
        response = await client.post(
            "/api/v1/rights/bulk/usage",
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
    async def test_get_asset_usage(
        self, client: AsyncClient, auth_headers: dict, test_license: dict
    ):
        """Test getting all usage records for a specific asset"""
        # Create multiple usage records for the same asset
        for i in range(3):
            await client.post(
                "/api/v1/rights/usage",
                json={
                    "license_id": test_license["license_id"],
                    "asset_id": test_license["asset_id"],
                    "user_id": str(uuid.uuid4()),
                    "usage_type": "broadcast",
                    "usage_date": (datetime.utcnow() - timedelta(days=i)).isoformat(),
                    "duration_seconds": 1800,
                    "platform": f"Platform {i}",
                    "country": "USA"
                },
                headers=auth_headers
            )
        
        # Get asset usage
        response = await client.get(
            f"/api/v1/rights/assets/{test_license['asset_id']}/usage",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 3
        assert all(record["asset_id"] == test_license["asset_id"] for record in data)
    
    @pytest.mark.asyncio
    async def test_usage_record_validation(
        self, client: AsyncClient, auth_headers: dict, test_license: dict
    ):
        """Test usage record validation rules"""
        base_data = {
            "license_id": test_license["license_id"],
            "asset_id": test_license["asset_id"],
            "user_id": str(uuid.uuid4()),
            "usage_type": "broadcast",
            "usage_date": datetime.utcnow().isoformat(),
            "platform": "Test Platform",
            "country": "USA"
        }
        
        # Test negative duration
        invalid_data = {
            **base_data,
            "duration_seconds": -100
        }
        response = await client.post(
            "/api/v1/rights/usage",
            json=invalid_data,
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        
        # Test zero usage count
        invalid_data = {
            **base_data,
            "duration_seconds": 1800,
            "usage_count": 0
        }
        response = await client.post(
            "/api/v1/rights/usage",
            json=invalid_data,
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        
        # Test negative revenue
        invalid_data = {
            **base_data,
            "duration_seconds": 1800,
            "revenue_generated": -1000.0
        }
        response = await client.post(
            "/api/v1/rights/usage",
            json=invalid_data,
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    
    @pytest.mark.asyncio
    async def test_usage_analytics(
        self, client: AsyncClient, auth_headers: dict, test_license: dict
    ):
        """Test usage analytics endpoint"""
        # Create usage records with revenue
        for i in range(5):
            await client.post(
                "/api/v1/rights/usage",
                json={
                    "license_id": test_license["license_id"],
                    "asset_id": test_license["asset_id"],
                    "user_id": str(uuid.uuid4()),
                    "usage_type": "broadcast" if i % 2 == 0 else "streaming",
                    "usage_date": (datetime.utcnow() - timedelta(days=i)).isoformat(),
                    "duration_seconds": 1800,
                    "platform": f"Platform {i}",
                    "country": "USA" if i % 2 == 0 else "UK",
                    "revenue_generated": 1000.0 * (i + 1),
                    "royalty_due": 150.0 * (i + 1)
                },
                headers=auth_headers
            )
        
        # Get usage analytics
        start_date = (datetime.utcnow() - timedelta(days=7)).date()
        end_date = datetime.utcnow().date()
        
        response = await client.get(
            f"/api/v1/rights/analytics/usage?start_date={start_date}&end_date={end_date}&asset_id={test_license['asset_id']}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_usage_count" in data
        assert "total_duration_seconds" in data
        assert "total_revenue" in data
        assert "total_royalties" in data
        assert "usage_by_type" in data
        assert "usage_by_country" in data
        assert "usage_by_platform" in data
    
    @pytest.mark.asyncio
    async def test_usage_record_metadata(
        self, client: AsyncClient, auth_headers: dict, test_license: dict
    ):
        """Test metadata storage in usage records"""
        metadata = {
            "broadcast_details": {
                "signal_quality": "HD",
                "audio_channels": "5.1",
                "subtitles": ["English", "Spanish"],
                "closed_captions": True
            },
            "audience_metrics": {
                "viewers": 2500000,
                "demographics": {
                    "age_18_34": 35,
                    "age_35_54": 45,
                    "age_55_plus": 20
                },
                "engagement_score": 8.5
            },
            "technical_info": {
                "bitrate": "8Mbps",
                "codec": "H.264",
                "resolution": "1920x1080"
            }
        }
        
        # Create usage record with metadata
        response = await client.post(
            "/api/v1/rights/usage",
            json={
                "license_id": test_license["license_id"],
                "asset_id": test_license["asset_id"],
                "user_id": str(uuid.uuid4()),
                "usage_type": "broadcast",
                "usage_date": datetime.utcnow().isoformat(),
                "duration_seconds": 3600,
                "platform": "Television",
                "country": "USA",
                "metadata": metadata
            },
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["metadata"] == metadata
        assert data["metadata"]["audience_metrics"]["viewers"] == 2500000
    
    @pytest.mark.asyncio
    async def test_usage_by_date_range(
        self, client: AsyncClient, auth_headers: dict, test_license: dict
    ):
        """Test filtering usage records by date range"""
        # Create usage records across different dates
        dates = [
            datetime.utcnow() - timedelta(days=10),
            datetime.utcnow() - timedelta(days=5),
            datetime.utcnow() - timedelta(days=2),
            datetime.utcnow()
        ]
        
        for i, usage_date in enumerate(dates):
            await client.post(
                "/api/v1/rights/usage",
                json={
                    "license_id": test_license["license_id"],
                    "asset_id": test_license["asset_id"],
                    "user_id": str(uuid.uuid4()),
                    "usage_type": "streaming",
                    "usage_date": usage_date.isoformat(),
                    "duration_seconds": 1800,
                    "platform": "Streaming Platform",
                    "country": "USA"
                },
                headers=auth_headers
            )
        
        # Test date range filter
        start_date = (datetime.utcnow() - timedelta(days=6)).date()
        end_date = (datetime.utcnow() - timedelta(days=1)).date()
        
        response = await client.get(
            f"/api/v1/rights/usage?start_date={start_date}&end_date={end_date}",
            headers=auth_headers
        )
        
        data = response.json()
        # Should get records from 5 and 2 days ago
        assert len(data["items"]) >= 2
        
        # Verify dates are within range
        for item in data["items"]:
            usage_date = datetime.fromisoformat(item["usage_date"].replace("Z", "+00:00")).date()
            assert start_date <= usage_date <= end_date