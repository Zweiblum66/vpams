"""
Tests for Usage Restrictions API

Tests temporal, platform, content, and other restriction types.
"""

import pytest
from httpx import AsyncClient
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from datetime import datetime, date, timedelta

from src.db.models import License


class TestRestrictionEndpoints:
    """Test restriction API endpoints"""
    
    @pytest.fixture
    async def test_restricted_license(self, client: AsyncClient, auth_headers: dict):
        """Create test license with various restrictions"""
        # Create parties
        licensor_response = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensor",
                "name": "Restriction Test Licensor",
                "contact_email": "restriction.licensor@test.com",
                "country": "USA"
            },
            headers=auth_headers
        )
        licensor_id = licensor_response.json()["id"]
        
        licensee_response = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensee",
                "name": "Restriction Test Licensee",
                "contact_email": "restriction.licensee@test.com",
                "country": "UK"
            },
            headers=auth_headers
        )
        licensee_id = licensee_response.json()["id"]
        
        # Create license with comprehensive restrictions
        asset_id = str(uuid.uuid4())
        license_response = await client.post(
            "/api/v1/rights/licenses",
            json={
                "license_number": "LIC-RESTRICT-001",
                "license_type": "streaming",
                "title": "Highly Restricted License",
                "asset_id": asset_id,
                "licensor_id": licensor_id,
                "licensee_id": licensee_id,
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "geographic_scope": "territory",
                "countries": ["US", "CA", "UK"],
                "max_usage_count": 100,
                "max_duration_seconds": 7200,
                "status": "active",
                "metadata": {
                    "restrictions": {
                        "temporal_restrictions": {
                            "allowed_hours": {"start": 6, "end": 23},
                            "allowed_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
                            "blackout_periods": [
                                {
                                    "start": "2025-12-20",
                                    "end": "2025-12-27",
                                    "reason": "Holiday blackout"
                                }
                            ]
                        },
                        "platform_restrictions": {
                            "allowed_platforms": ["Netflix", "Amazon Prime", "Hulu"],
                            "delivery_restrictions": {
                                "quality": {
                                    "max_resolution": "1080p",
                                    "hdr_allowed": False
                                },
                                "download_allowed": False,
                                "offline_viewing_allowed": False
                            }
                        },
                        "content_restrictions": {
                            "allowed_ratings": ["G", "PG", "PG-13"],
                            "allowed_genres": ["Drama", "Comedy", "Documentary"],
                            "allowed_languages": ["English", "Spanish", "French"],
                            "duration_limits": {
                                "min_seconds": 600,
                                "max_seconds": 10800
                            }
                        }
                    }
                }
            },
            headers=auth_headers
        )
        
        return {
            "license_id": license_response.json()["id"],
            "asset_id": asset_id
        }
    
    @pytest.mark.asyncio
    async def test_check_temporal_restrictions_allowed(
        self, client: AsyncClient, auth_headers: dict, test_restricted_license: dict
    ):
        """Test temporal restrictions during allowed time"""
        # Check during allowed hours on a weekday
        test_datetime = datetime(2025, 7, 21, 14, 30)  # Monday 2:30 PM
        
        response = await client.post(
            f"/api/v1/rights/restrictions/temporal/{test_restricted_license['license_id']}",
            json=test_datetime.isoformat(),
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["access_allowed"] is True
        assert data["within_allowed_hours"] is True
        assert data["within_allowed_days"] is True
    
    @pytest.mark.asyncio
    async def test_check_temporal_restrictions_blocked_hours(
        self, client: AsyncClient, auth_headers: dict, test_restricted_license: dict
    ):
        """Test temporal restrictions during blocked hours"""
        # Check during blocked hours (2 AM)
        test_datetime = datetime(2025, 7, 21, 2, 0)  # Monday 2:00 AM
        
        response = await client.post(
            f"/api/v1/rights/restrictions/temporal/{test_restricted_license['license_id']}",
            json=test_datetime.isoformat(),
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["access_allowed"] is False
        assert data["within_allowed_hours"] is False
        assert "outside allowed hours" in data["block_reason"].lower()
    
    @pytest.mark.asyncio
    async def test_check_temporal_restrictions_weekend(
        self, client: AsyncClient, auth_headers: dict, test_restricted_license: dict
    ):
        """Test temporal restrictions on weekend"""
        # Check on Saturday
        test_datetime = datetime(2025, 7, 26, 14, 0)  # Saturday 2:00 PM
        
        response = await client.post(
            f"/api/v1/rights/restrictions/temporal/{test_restricted_license['license_id']}",
            json=test_datetime.isoformat(),
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["access_allowed"] is False
        assert data["within_allowed_days"] is False
        assert "not allowed on" in data["block_reason"].lower()
    
    @pytest.mark.asyncio
    async def test_check_temporal_restrictions_blackout(
        self, client: AsyncClient, auth_headers: dict, test_restricted_license: dict
    ):
        """Test temporal restrictions during blackout period"""
        # Check during holiday blackout
        test_datetime = datetime(2025, 12, 25, 14, 0)  # Christmas Day
        
        response = await client.post(
            f"/api/v1/rights/restrictions/temporal/{test_restricted_license['license_id']}",
            json=test_datetime.isoformat(),
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["access_allowed"] is False
        assert data["in_blackout_period"] is True
        assert "blackout" in data["block_reason"].lower()
    
    @pytest.mark.asyncio
    async def test_check_usage_quotas_within_limits(
        self, client: AsyncClient, auth_headers: dict, test_restricted_license: dict
    ):
        """Test usage quotas within limits"""
        response = await client.post(
            f"/api/v1/rights/restrictions/quotas/{test_restricted_license['license_id']}",
            params={
                "usage_count": 5,
                "duration_seconds": 3600
            },
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["within_usage_limit"] is True
        assert data["within_duration_limit"] is True
        assert data["remaining_usage_count"] == 95  # 100 - 5
        assert data["remaining_duration_seconds"] == 3600  # 7200 - 3600
    
    @pytest.mark.asyncio
    async def test_check_usage_quotas_exceeds_count(
        self, client: AsyncClient, auth_headers: dict, test_restricted_license: dict
    ):
        """Test usage quotas exceeding count limit"""
        response = await client.post(
            f"/api/v1/rights/restrictions/quotas/{test_restricted_license['license_id']}",
            params={
                "usage_count": 101,  # Exceeds max of 100
                "duration_seconds": 1800
            },
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["within_usage_limit"] is False
        assert "exceeds maximum usage count" in data["violation_details"][0].lower()
    
    @pytest.mark.asyncio
    async def test_check_platform_restrictions_allowed(
        self, client: AsyncClient, auth_headers: dict, test_restricted_license: dict
    ):
        """Test platform restrictions with allowed platform"""
        response = await client.post(
            f"/api/v1/rights/restrictions/platform/{test_restricted_license['license_id']}",
            params={"platform": "Netflix"},
            json={
                "platform_metadata": {
                    "app_version": "2.1.0",
                    "device_type": "smart_tv",
                    "stream_quality": "HD"
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["platform_allowed"] is True
        assert data["delivery_compliant"] is True
    
    @pytest.mark.asyncio
    async def test_check_platform_restrictions_blocked(
        self, client: AsyncClient, auth_headers: dict, test_restricted_license: dict
    ):
        """Test platform restrictions with blocked platform"""
        response = await client.post(
            f"/api/v1/rights/restrictions/platform/{test_restricted_license['license_id']}",
            params={"platform": "Disney+"},  # Not in allowed list
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["platform_allowed"] is False
        assert "not in allowed platforms" in data["block_reason"].lower()
    
    @pytest.mark.asyncio
    async def test_check_platform_delivery_restrictions(
        self, client: AsyncClient, auth_headers: dict, test_restricted_license: dict
    ):
        """Test platform delivery restrictions"""
        response = await client.post(
            f"/api/v1/rights/restrictions/platform/{test_restricted_license['license_id']}",
            params={"platform": "Netflix"},
            json={
                "platform_metadata": {
                    "requested_quality": "4K",  # Exceeds max 1080p
                    "hdr_requested": True,  # HDR not allowed
                    "download_requested": True  # Downloads not allowed
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["platform_allowed"] is True
        assert data["delivery_compliant"] is False
        assert len(data["delivery_violations"]) > 0
        assert any("resolution" in v.lower() for v in data["delivery_violations"])
    
    @pytest.mark.asyncio
    async def test_check_content_restrictions_allowed(
        self, client: AsyncClient, auth_headers: dict, test_restricted_license: dict
    ):
        """Test content restrictions with compliant content"""
        response = await client.post(
            f"/api/v1/rights/restrictions/content/{test_restricted_license['license_id']}",
            json={
                "content_metadata": {
                    "rating": "PG",
                    "genre": "Comedy",
                    "language": "English",
                    "duration_seconds": 5400  # 90 minutes
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["content_compliant"] is True
        assert len(data["violations"]) == 0
    
    @pytest.mark.asyncio
    async def test_check_content_restrictions_rating_violation(
        self, client: AsyncClient, auth_headers: dict, test_restricted_license: dict
    ):
        """Test content restrictions with rating violation"""
        response = await client.post(
            f"/api/v1/rights/restrictions/content/{test_restricted_license['license_id']}",
            json={
                "content_metadata": {
                    "rating": "R",  # Not allowed
                    "genre": "Drama",
                    "language": "English",
                    "duration_seconds": 7200
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["content_compliant"] is False
        assert any("rating" in v["type"] for v in data["violations"])
    
    @pytest.mark.asyncio
    async def test_check_content_restrictions_multiple_violations(
        self, client: AsyncClient, auth_headers: dict, test_restricted_license: dict
    ):
        """Test content restrictions with multiple violations"""
        response = await client.post(
            f"/api/v1/rights/restrictions/content/{test_restricted_license['license_id']}",
            json={
                "content_metadata": {
                    "rating": "NC-17",  # Not allowed
                    "genre": "Horror",  # Not allowed
                    "language": "Japanese",  # Not allowed
                    "duration_seconds": 300  # Too short (< 600)
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["content_compliant"] is False
        assert len(data["violations"]) == 4
    
    @pytest.mark.asyncio
    async def test_get_license_restrictions_summary(
        self, client: AsyncClient, auth_headers: dict, test_restricted_license: dict
    ):
        """Test getting comprehensive restriction summary"""
        response = await client.get(
            f"/api/v1/rights/restrictions/license/{test_restricted_license['license_id']}/summary",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["license_id"] == test_restricted_license["license_id"]
        assert "geographic_scope" in data
        assert "usage_limits" in data
        assert "custom_restrictions" in data
        assert "temporal_restrictions" in data["custom_restrictions"]
        assert "platform_restrictions" in data["custom_restrictions"]
        assert "content_restrictions" in data["custom_restrictions"]
    
    @pytest.mark.asyncio
    async def test_comprehensive_restriction_check(
        self, client: AsyncClient, auth_headers: dict, test_restricted_license: dict
    ):
        """Test comprehensive restriction check via compliance endpoint"""
        compliance_check = {
            "asset_id": test_restricted_license["asset_id"],
            "license_id": test_restricted_license["license_id"],
            "usage_type": "streaming",
            "usage_date": datetime(2025, 7, 21, 14, 0).isoformat(),  # Monday 2 PM
            "country": "US",
            "platform": "Netflix",
            "metadata": {
                "content_rating": "PG",
                "content_genre": "Comedy",
                "content_language": "English",
                "content_duration": 5400,
                "requested_quality": "1080p",
                "download_requested": False
            }
        }
        
        response = await client.post(
            "/api/v1/rights/restrictions/check",
            json=compliance_check,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_compliant"] is True
        assert "temporal" in data["checks_performed"]
        assert "platform" in data["checks_performed"]
        assert "content" in data["checks_performed"]
    
    @pytest.mark.asyncio
    async def test_validate_restriction_config(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test restriction configuration validation"""
        # Valid configuration
        valid_config = {
            "temporal_restrictions": {
                "allowed_hours": {"start": 9, "end": 17},
                "blackout_periods": [
                    {
                        "start": "2025-12-24",
                        "end": "2025-12-26",
                        "reason": "Christmas"
                    }
                ]
            },
            "geographic_restrictions": {
                "countries": ["US", "CA", "UK"]
            },
            "platform_restrictions": {
                "delivery_restrictions": {
                    "quality": {
                        "max_resolution": "4k"
                    }
                }
            }
        }
        
        response = await client.post(
            "/api/v1/rights/restrictions/validate-config",
            json=valid_config,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_valid"] is True
        assert len(data["errors"]) == 0
        
        # Invalid configuration
        invalid_config = {
            "temporal_restrictions": {
                "allowed_hours": {"start": 25, "end": -1},  # Invalid hours
                "blackout_periods": "not a list"  # Wrong type
            }
        }
        
        response = await client.post(
            "/api/v1/rights/restrictions/validate-config",
            json=invalid_config,
            headers=auth_headers
        )
        
        data = response.json()
        assert data["is_valid"] is False
        assert len(data["errors"]) > 0
    
    @pytest.mark.asyncio
    async def test_get_restriction_types(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test getting available restriction types"""
        response = await client.get(
            "/api/v1/rights/restrictions/restrictions/types",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "restriction_types" in data
        
        expected_types = [
            "temporal_restrictions",
            "usage_quotas",
            "geographic_restrictions",
            "platform_restrictions",
            "content_restrictions",
            "financial_restrictions"
        ]
        
        for restriction_type in expected_types:
            assert restriction_type in data["restriction_types"]
            assert "description" in data["restriction_types"][restriction_type]
            assert "supported_configs" in data["restriction_types"][restriction_type]