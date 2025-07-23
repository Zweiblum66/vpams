"""
Tests for Rights Analytics API

Tests analytics endpoints for usage patterns, revenue, and license insights.
"""

import pytest
from httpx import AsyncClient
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal


class TestAnalyticsEndpoints:
    """Test analytics API endpoints"""
    
    @pytest.fixture
    async def test_analytics_data(self, client: AsyncClient, auth_headers: dict):
        """Create comprehensive test data for analytics"""
        # Create parties
        licensor1 = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensor",
                "name": "Analytics Studio One",
                "contact_email": "studio1@analytics.com",
                "country": "USA"
            },
            headers=auth_headers
        )
        licensor1_id = licensor1.json()["id"]
        
        licensor2 = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensor",
                "name": "Analytics Studio Two",
                "contact_email": "studio2@analytics.com",
                "country": "UK"
            },
            headers=auth_headers
        )
        licensor2_id = licensor2.json()["id"]
        
        licensee1 = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensee",
                "name": "Analytics Broadcaster",
                "contact_email": "broadcaster@analytics.com",
                "country": "USA"
            },
            headers=auth_headers
        )
        licensee1_id = licensee1.json()["id"]
        
        licensee2 = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensee",
                "name": "Analytics Streamer",
                "contact_email": "streamer@analytics.com",
                "country": "Global"
            },
            headers=auth_headers
        )
        licensee2_id = licensee2.json()["id"]
        
        # Create assets and licenses
        assets = []
        licenses = []
        
        for i in range(3):
            asset_id = str(uuid.uuid4())
            assets.append(asset_id)
            
            # Create broadcast license
            broadcast_license = await client.post(
                "/api/v1/rights/licenses",
                json={
                    "license_number": f"LIC-ANALYTICS-BROADCAST-{i:03d}",
                    "license_type": "broadcast",
                    "title": f"Broadcast License {i}",
                    "asset_id": asset_id,
                    "licensor_id": licensor1_id if i % 2 == 0 else licensor2_id,
                    "licensee_id": licensee1_id,
                    "start_date": "2025-01-01",
                    "end_date": "2025-12-31",
                    "geographic_scope": "territory",
                    "countries": ["US", "CA"] if i % 2 == 0 else ["UK", "DE"],
                    "license_fee": 50000.0 * (i + 1),
                    "royalty_rate": 15.0,
                    "status": "active"
                },
                headers=auth_headers
            )
            licenses.append(broadcast_license.json()["id"])
            
            # Create streaming license
            streaming_license = await client.post(
                "/api/v1/rights/licenses",
                json={
                    "license_number": f"LIC-ANALYTICS-STREAMING-{i:03d}",
                    "license_type": "streaming",
                    "title": f"Streaming License {i}",
                    "asset_id": asset_id,
                    "licensor_id": licensor2_id if i % 2 == 0 else licensor1_id,
                    "licensee_id": licensee2_id,
                    "start_date": "2025-01-01",
                    "end_date": "2025-06-30" if i == 0 else "2025-12-31",
                    "geographic_scope": "worldwide",
                    "license_fee": 100000.0 * (i + 1),
                    "royalty_rate": 20.0,
                    "minimum_guarantee": 20000.0,
                    "status": "active" if i != 0 else "expired"
                },
                headers=auth_headers
            )
            licenses.append(streaming_license.json()["id"])
        
        # Create usage records with various patterns
        usage_records = []
        platforms = ["Television", "Cable", "Netflix", "Amazon Prime", "Hulu"]
        countries = ["US", "UK", "CA", "DE", "FR", "JP"]
        
        for i, license_id in enumerate(licenses):
            for day in range(30):  # 30 days of usage data
                usage_date = datetime.utcnow() - timedelta(days=day)
                
                # Create 1-3 usage records per day
                for j in range((day % 3) + 1):
                    usage_response = await client.post(
                        "/api/v1/rights/usage",
                        json={
                            "license_id": license_id,
                            "asset_id": assets[i // 2],
                            "user_id": str(uuid.uuid4()),
                            "usage_type": "broadcast" if i % 2 == 0 else "streaming",
                            "usage_date": usage_date.isoformat(),
                            "duration_seconds": 1800 + (j * 600),  # 30-60 minutes
                            "usage_count": 1,
                            "platform": platforms[day % len(platforms)],
                            "country": countries[day % len(countries)],
                            "revenue_generated": 100.0 * (j + 1) * (1 + (day % 5)),
                            "royalty_due": 15.0 * (j + 1) * (1 + (day % 5)),
                            "metadata": {
                                "time_slot": "prime_time" if j == 0 else "regular",
                                "audience_size": 100000 * (j + 1)
                            }
                        },
                        headers=auth_headers
                    )
                    usage_records.append(usage_response.json()["id"])
        
        return {
            "assets": assets,
            "licenses": licenses,
            "usage_records": usage_records,
            "licensors": [licensor1_id, licensor2_id],
            "licensees": [licensee1_id, licensee2_id]
        }
    
    @pytest.mark.asyncio
    async def test_get_usage_analytics_basic(
        self, client: AsyncClient, auth_headers: dict, test_analytics_data: dict
    ):
        """Test basic usage analytics"""
        start_date = (datetime.utcnow() - timedelta(days=7)).date()
        end_date = datetime.utcnow().date()
        
        response = await client.get(
            f"/api/v1/rights/analytics/usage?start_date={start_date}&end_date={end_date}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Check required fields
        assert "total_usage_count" in data
        assert "total_duration_seconds" in data
        assert "total_revenue" in data
        assert "total_royalties" in data
        assert "usage_by_type" in data
        assert "usage_by_country" in data
        assert "usage_by_platform" in data
        assert "daily_usage" in data
        
        # Verify data integrity
        assert data["total_usage_count"] > 0
        assert data["total_revenue"] > 0
        assert len(data["usage_by_type"]) > 0
        assert len(data["usage_by_country"]) > 0
    
    @pytest.mark.asyncio
    async def test_get_usage_analytics_by_asset(
        self, client: AsyncClient, auth_headers: dict, test_analytics_data: dict
    ):
        """Test usage analytics filtered by asset"""
        asset_id = test_analytics_data["assets"][0]
        start_date = (datetime.utcnow() - timedelta(days=30)).date()
        end_date = datetime.utcnow().date()
        
        response = await client.get(
            f"/api/v1/rights/analytics/usage?start_date={start_date}&end_date={end_date}&asset_id={asset_id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["filters"]["asset_id"] == asset_id
        assert data["total_usage_count"] > 0
    
    @pytest.mark.asyncio
    async def test_get_usage_analytics_by_license(
        self, client: AsyncClient, auth_headers: dict, test_analytics_data: dict
    ):
        """Test usage analytics filtered by license"""
        license_id = test_analytics_data["licenses"][0]
        start_date = (datetime.utcnow() - timedelta(days=30)).date()
        end_date = datetime.utcnow().date()
        
        response = await client.get(
            f"/api/v1/rights/analytics/usage?start_date={start_date}&end_date={end_date}&license_id={license_id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["filters"]["license_id"] == license_id
        assert data["total_usage_count"] > 0
    
    @pytest.mark.asyncio
    async def test_get_license_analytics(
        self, client: AsyncClient, auth_headers: dict, test_analytics_data: dict
    ):
        """Test license analytics overview"""
        response = await client.get(
            "/api/v1/rights/analytics/licenses",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Check summary statistics
        assert "total_licenses" in data
        assert "active_licenses" in data
        assert "expired_licenses" in data
        assert "expiring_soon" in data
        
        # Check breakdowns
        assert "by_type" in data
        assert "by_geographic_scope" in data
        assert "by_licensor" in data
        assert "by_licensee" in data
        
        # Check financial metrics
        assert "total_license_value" in data
        assert "total_royalty_rate_average" in data
        assert "licenses_with_minimum_guarantee" in data
        
        # Verify data
        assert data["total_licenses"] >= len(test_analytics_data["licenses"])
        assert data["active_licenses"] > 0
        assert len(data["by_type"]) > 0
    
    @pytest.mark.asyncio
    async def test_revenue_analytics(
        self, client: AsyncClient, auth_headers: dict, test_analytics_data: dict
    ):
        """Test revenue analytics"""
        # Note: This endpoint doesn't exist in the current routes, but would be valuable
        # Test usage analytics revenue breakdown instead
        start_date = (datetime.utcnow() - timedelta(days=30)).date()
        end_date = datetime.utcnow().date()
        
        response = await client.get(
            f"/api/v1/rights/analytics/usage?start_date={start_date}&end_date={end_date}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Check revenue metrics
        assert data["total_revenue"] > 0
        assert data["total_royalties"] > 0
        
        # Revenue should be greater than royalties
        assert data["total_revenue"] > data["total_royalties"]
        
        # Check daily breakdown includes revenue
        if "daily_usage" in data and len(data["daily_usage"]) > 0:
            assert "revenue" in data["daily_usage"][0]
            assert "royalties" in data["daily_usage"][0]
    
    @pytest.mark.asyncio
    async def test_platform_performance_analytics(
        self, client: AsyncClient, auth_headers: dict, test_analytics_data: dict
    ):
        """Test platform performance metrics"""
        start_date = (datetime.utcnow() - timedelta(days=14)).date()
        end_date = datetime.utcnow().date()
        
        response = await client.get(
            f"/api/v1/rights/analytics/usage?start_date={start_date}&end_date={end_date}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Check platform breakdown
        assert "usage_by_platform" in data
        assert len(data["usage_by_platform"]) > 0
        
        # Each platform should have usage metrics
        for platform, metrics in data["usage_by_platform"].items():
            assert "count" in metrics
            assert "duration" in metrics
            assert "revenue" in metrics
            assert metrics["count"] > 0
    
    @pytest.mark.asyncio
    async def test_geographic_distribution_analytics(
        self, client: AsyncClient, auth_headers: dict, test_analytics_data: dict
    ):
        """Test geographic distribution of usage"""
        start_date = (datetime.utcnow() - timedelta(days=30)).date()
        end_date = datetime.utcnow().date()
        
        response = await client.get(
            f"/api/v1/rights/analytics/usage?start_date={start_date}&end_date={end_date}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Check country breakdown
        assert "usage_by_country" in data
        assert len(data["usage_by_country"]) > 0
        
        # Verify country metrics
        total_by_country = 0
        for country, metrics in data["usage_by_country"].items():
            assert len(country) in [2, 3]  # ISO country codes
            assert metrics["count"] > 0
            total_by_country += metrics["count"]
        
        # Total by country should match total usage
        assert total_by_country == data["total_usage_count"]
    
    @pytest.mark.asyncio
    async def test_time_series_analytics(
        self, client: AsyncClient, auth_headers: dict, test_analytics_data: dict
    ):
        """Test time series usage data"""
        start_date = (datetime.utcnow() - timedelta(days=7)).date()
        end_date = datetime.utcnow().date()
        
        response = await client.get(
            f"/api/v1/rights/analytics/usage?start_date={start_date}&end_date={end_date}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Check daily usage data
        assert "daily_usage" in data
        assert len(data["daily_usage"]) > 0
        
        # Verify daily data structure
        for daily_data in data["daily_usage"]:
            assert "date" in daily_data
            assert "usage_count" in daily_data
            assert "duration" in daily_data
            assert "revenue" in daily_data
            assert "royalties" in daily_data
        
        # Data should be ordered by date
        dates = [d["date"] for d in data["daily_usage"]]
        assert dates == sorted(dates)
    
    @pytest.mark.asyncio
    async def test_license_utilization_analytics(
        self, client: AsyncClient, auth_headers: dict, test_analytics_data: dict
    ):
        """Test license utilization metrics"""
        response = await client.get(
            "/api/v1/rights/analytics/licenses",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Check for utilization metrics
        if "license_utilization" in data:
            assert "highly_utilized" in data["license_utilization"]
            assert "moderately_utilized" in data["license_utilization"]
            assert "underutilized" in data["license_utilization"]
    
    @pytest.mark.asyncio
    async def test_compliance_analytics(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test compliance-related analytics"""
        # This tests geo-blocking analytics which includes compliance metrics
        response = await client.get(
            "/api/v1/rights/geo-blocking/analytics",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Check compliance metrics
        assert "total_checks" in data
        assert "blocked_attempts" in data
        assert "allowed_attempts" in data
        
        if data["total_checks"] > 0:
            assert "block_rate" in data
            assert 0 <= data["block_rate"] <= 1
    
    @pytest.mark.asyncio
    async def test_royalty_calculations_analytics(
        self, client: AsyncClient, auth_headers: dict, test_analytics_data: dict
    ):
        """Test royalty calculation analytics"""
        start_date = (datetime.utcnow() - timedelta(days=30)).date()
        end_date = datetime.utcnow().date()
        
        response = await client.get(
            f"/api/v1/rights/analytics/usage?start_date={start_date}&end_date={end_date}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify royalty calculations
        assert data["total_royalties"] > 0
        assert data["total_royalties"] < data["total_revenue"]
        
        # Check royalty breakdown by licensor if available
        if "royalties_by_licensor" in data:
            total_royalties_by_licensor = sum(
                metrics["amount"] for metrics in data["royalties_by_licensor"].values()
            )
            # Total should match within rounding errors
            assert abs(total_royalties_by_licensor - data["total_royalties"]) < 1.0
    
    @pytest.mark.asyncio
    async def test_trend_analysis(
        self, client: AsyncClient, auth_headers: dict, test_analytics_data: dict
    ):
        """Test trend analysis over time"""
        # Get two different time periods for comparison
        period1_start = (datetime.utcnow() - timedelta(days=30)).date()
        period1_end = (datetime.utcnow() - timedelta(days=15)).date()
        
        period2_start = (datetime.utcnow() - timedelta(days=14)).date()
        period2_end = datetime.utcnow().date()
        
        # Get analytics for first period
        response1 = await client.get(
            f"/api/v1/rights/analytics/usage?start_date={period1_start}&end_date={period1_end}",
            headers=auth_headers
        )
        data1 = response1.json()
        
        # Get analytics for second period
        response2 = await client.get(
            f"/api/v1/rights/analytics/usage?start_date={period2_start}&end_date={period2_end}",
            headers=auth_headers
        )
        data2 = response2.json()
        
        # Both requests should succeed
        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK
        
        # Can compare metrics between periods
        assert "total_usage_count" in data1 and "total_usage_count" in data2
        assert "total_revenue" in data1 and "total_revenue" in data2
    
    @pytest.mark.asyncio
    async def test_empty_date_range_analytics(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test analytics with date range that has no data"""
        # Use future dates
        start_date = date(2026, 1, 1)
        end_date = date(2026, 1, 31)
        
        response = await client.get(
            f"/api/v1/rights/analytics/usage?start_date={start_date}&end_date={end_date}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should return zeros for empty period
        assert data["total_usage_count"] == 0
        assert data["total_duration_seconds"] == 0
        assert data["total_revenue"] == 0
        assert data["total_royalties"] == 0