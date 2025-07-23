"""
Tests for Geo-blocking API

Tests geographic restriction functionality and IP-based access control.
"""

import pytest
from httpx import AsyncClient
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from datetime import datetime, date

from src.db.models import License


class TestGeoBlockingEndpoints:
    """Test geo-blocking API endpoints"""
    
    @pytest.fixture
    async def test_license_with_geo_rules(self, client: AsyncClient, auth_headers: dict):
        """Create test license with geo-blocking rules"""
        # Create parties
        licensor_response = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensor",
                "name": "Geo Test Licensor",
                "contact_email": "geo.licensor@test.com",
                "country": "USA"
            },
            headers=auth_headers
        )
        licensor_id = licensor_response.json()["id"]
        
        licensee_response = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensee",
                "name": "Geo Test Licensee",
                "contact_email": "geo.licensee@test.com",
                "country": "UK"
            },
            headers=auth_headers
        )
        licensee_id = licensee_response.json()["id"]
        
        # Create license with geo-blocking metadata
        license_response = await client.post(
            "/api/v1/rights/licenses",
            json={
                "license_number": "LIC-GEO-TEST-001",
                "license_type": "streaming",
                "title": "Geo-blocked License",
                "asset_id": str(uuid.uuid4()),
                "licensor_id": licensor_id,
                "licensee_id": licensee_id,
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "geographic_scope": "territory",
                "countries": ["US", "CA", "UK"],
                "status": "active",
                "metadata": {
                    "geo_blocking": {
                        "block_vpn": True,
                        "rules": [
                            {
                                "rule_id": "rule_001",
                                "rule_type": "country_block",
                                "rule_name": "Block sanctioned countries",
                                "countries": ["IR", "KP", "SY"],
                                "enabled": True
                            },
                            {
                                "rule_id": "rule_002",
                                "rule_type": "ip_block",
                                "rule_name": "Block suspicious IPs",
                                "ip_addresses": ["192.168.1.100", "10.0.0.0/8"],
                                "enabled": True
                            }
                        ]
                    }
                }
            },
            headers=auth_headers
        )
        
        return license_response.json()["id"]
    
    @pytest.mark.asyncio
    async def test_check_geographic_access_allowed(
        self, client: AsyncClient, auth_headers: dict, test_license_with_geo_rules: str
    ):
        """Test checking geographic access for allowed country"""
        response = await client.post(
            f"/api/v1/rights/geo-blocking/check/{test_license_with_geo_rules}",
            params={
                "country_code": "US",
                "region_code": "CA"
            },
            json={
                "user_location": {
                    "timezone": "America/Los_Angeles",
                    "latitude": 34.0522,
                    "longitude": -118.2437
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["access_allowed"] is True
        assert data["country_allowed"] is True
        assert "US" in data["allowed_countries"]
    
    @pytest.mark.asyncio
    async def test_check_geographic_access_blocked_country(
        self, client: AsyncClient, auth_headers: dict, test_license_with_geo_rules: str
    ):
        """Test checking geographic access for blocked country"""
        response = await client.post(
            f"/api/v1/rights/geo-blocking/check/{test_license_with_geo_rules}",
            params={
                "country_code": "JP"  # Not in allowed countries
            },
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["access_allowed"] is False
        assert data["country_allowed"] is False
        assert data["block_reason"] is not None
    
    @pytest.mark.asyncio
    async def test_check_geographic_access_sanctioned_country(
        self, client: AsyncClient, auth_headers: dict, test_license_with_geo_rules: str
    ):
        """Test checking geographic access for sanctioned country"""
        response = await client.post(
            f"/api/v1/rights/geo-blocking/check/{test_license_with_geo_rules}",
            params={
                "country_code": "IR"  # Sanctioned country in block list
            },
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["access_allowed"] is False
        assert "sanctioned" in data["block_reason"].lower() or "blocked" in data["block_reason"].lower()
    
    @pytest.mark.asyncio
    async def test_get_ip_geolocation(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test IP geolocation lookup"""
        # Using a known Google DNS IP for testing
        response = await client.get(
            "/api/v1/rights/geo-blocking/ip-geolocation/8.8.8.8",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "country_code" in data
        assert "country_name" in data
        assert "ip_address" in data
    
    @pytest.mark.asyncio
    async def test_create_geo_blocking_rule(
        self, client: AsyncClient, auth_headers: dict, test_license_with_geo_rules: str
    ):
        """Test creating a new geo-blocking rule"""
        rule_config = {
            "rule_type": "country_allow",
            "rule_name": "European Union Countries",
            "description": "Allow access from EU countries",
            "countries": ["DE", "FR", "IT", "ES", "NL"],
            "enabled": True
        }
        
        response = await client.post(
            f"/api/v1/rights/geo-blocking/rules/{test_license_with_geo_rules}",
            json=rule_config,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "rule_id" in data
    
    @pytest.mark.asyncio
    async def test_update_geo_blocking_rule(
        self, client: AsyncClient, auth_headers: dict, test_license_with_geo_rules: str
    ):
        """Test updating an existing geo-blocking rule"""
        rule_updates = {
            "enabled": False,
            "description": "Temporarily disabled"
        }
        
        response = await client.put(
            f"/api/v1/rights/geo-blocking/rules/{test_license_with_geo_rules}/rule_001",
            json=rule_updates,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
    
    @pytest.mark.asyncio
    async def test_delete_geo_blocking_rule(
        self, client: AsyncClient, auth_headers: dict, test_license_with_geo_rules: str
    ):
        """Test deleting a geo-blocking rule"""
        # First create a rule to delete
        create_response = await client.post(
            f"/api/v1/rights/geo-blocking/rules/{test_license_with_geo_rules}",
            json={
                "rule_type": "ip_block",
                "rule_name": "Test Delete Rule",
                "ip_addresses": ["192.168.1.1"],
                "enabled": True
            },
            headers=auth_headers
        )
        rule_id = create_response.json()["rule_id"]
        
        # Delete the rule
        response = await client.delete(
            f"/api/v1/rights/geo-blocking/rules/{test_license_with_geo_rules}/{rule_id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
    
    @pytest.mark.asyncio
    async def test_get_geo_blocking_rules(
        self, client: AsyncClient, auth_headers: dict, test_license_with_geo_rules: str
    ):
        """Test getting all geo-blocking rules for a license"""
        response = await client.get(
            f"/api/v1/rights/geo-blocking/rules/{test_license_with_geo_rules}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["license_id"] == test_license_with_geo_rules
        assert "rules" in data
        assert len(data["rules"]) >= 2  # Initial rules from fixture
        assert "geo_blocking_config" in data
    
    @pytest.mark.asyncio
    async def test_geo_blocking_analytics(
        self, client: AsyncClient, auth_headers: dict, test_license_with_geo_rules: str
    ):
        """Test geo-blocking analytics"""
        # Generate some geo-blocking checks
        countries = ["US", "UK", "JP", "IR", "DE"]
        for country in countries:
            await client.post(
                f"/api/v1/rights/geo-blocking/check/{test_license_with_geo_rules}",
                params={"country_code": country},
                headers=auth_headers
            )
        
        # Get analytics
        response = await client.get(
            f"/api/v1/rights/geo-blocking/analytics?license_id={test_license_with_geo_rules}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_checks" in data
        assert "blocked_attempts" in data
        assert "allowed_attempts" in data
        assert "checks_by_country" in data
    
    @pytest.mark.asyncio
    async def test_check_access_by_ip(
        self, client: AsyncClient, auth_headers: dict, test_license_with_geo_rules: str
    ):
        """Test checking access based on request IP"""
        # Note: In test environment, client IP will be test/localhost
        response = await client.post(
            f"/api/v1/rights/geo-blocking/check-by-ip?license_id={test_license_with_geo_rules}",
            headers={
                **auth_headers,
                "X-Forwarded-For": "8.8.8.8",  # Simulate proxy header
                "X-Real-IP": "8.8.8.8"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "check_result" in data
        assert "ip_info" in data
        assert data["ip_info"]["ip_address"] == "8.8.8.8"
    
    @pytest.mark.asyncio
    async def test_get_sanctioned_countries(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test getting list of sanctioned countries"""
        response = await client.get(
            "/api/v1/rights/geo-blocking/countries/sanctioned",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "countries" in data
        assert len(data["countries"]) > 0
        assert all("code" in c and "name" in c and "sanctions_type" in c for c in data["countries"])
    
    @pytest.mark.asyncio
    async def test_validate_geo_blocking_rule(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test geo-blocking rule validation"""
        # Valid rule
        valid_rule = {
            "rule_type": "country_block",
            "rule_name": "Block specific countries",
            "countries": ["CN", "RU"],
            "enabled": True
        }
        
        response = await client.post(
            "/api/v1/rights/geo-blocking/validate-rule",
            json=valid_rule,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_valid"] is True
        assert len(data["errors"]) == 0
        
        # Invalid rule - missing required field
        invalid_rule = {
            "rule_type": "country_block",
            # Missing rule_name
            "countries": ["XX"],  # Invalid country code
            "enabled": True
        }
        
        response = await client.post(
            "/api/v1/rights/geo-blocking/validate-rule",
            json=invalid_rule,
            headers=auth_headers
        )
        
        data = response.json()
        assert data["is_valid"] is False
        assert len(data["errors"]) > 0
        assert any("rule_name" in error for error in data["errors"])
    
    @pytest.mark.asyncio
    async def test_get_geo_blocking_rule_types(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test getting available geo-blocking rule types"""
        response = await client.get(
            "/api/v1/rights/geo-blocking/rule-types",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "rule_types" in data
        
        expected_types = [
            "country_block", "country_allow", "ip_block", "ip_allow",
            "region_block", "region_allow", "vpn_block"
        ]
        
        for rule_type in expected_types:
            assert rule_type in data["rule_types"]
            assert "description" in data["rule_types"][rule_type]
            assert "required_fields" in data["rule_types"][rule_type]
    
    @pytest.mark.asyncio
    async def test_vpn_blocking_rule(
        self, client: AsyncClient, auth_headers: dict, test_license_with_geo_rules: str
    ):
        """Test VPN blocking functionality"""
        # Create VPN blocking rule
        vpn_rule = {
            "rule_type": "vpn_block",
            "rule_name": "Block VPN Access",
            "description": "Prevent access from VPN connections",
            "detection_level": "strict",
            "whitelist_ips": ["10.0.0.1", "192.168.1.1"],
            "enabled": True
        }
        
        response = await client.post(
            f"/api/v1/rights/geo-blocking/rules/{test_license_with_geo_rules}",
            json=vpn_rule,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        
        # Check access with VPN flag
        check_response = await client.post(
            f"/api/v1/rights/geo-blocking/check/{test_license_with_geo_rules}",
            params={
                "country_code": "US",
                "ip_address": "1.2.3.4"
            },
            json={
                "user_location": {
                    "is_vpn": True,
                    "vpn_provider": "NordVPN"
                }
            },
            headers=auth_headers
        )
        
        check_data = check_response.json()
        assert check_data["access_allowed"] is False
        assert "vpn" in check_data["block_reason"].lower()
    
    @pytest.mark.asyncio
    async def test_regional_restrictions(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test regional (state/province) level restrictions"""
        # Create license with regional restrictions
        license_response = await client.post(
            "/api/v1/rights/licenses",
            json={
                "license_number": "LIC-REGIONAL-001",
                "license_type": "broadcast",
                "title": "Regional Restricted License",
                "asset_id": str(uuid.uuid4()),
                "licensor_id": str(uuid.uuid4()),
                "licensee_id": str(uuid.uuid4()),
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "geographic_scope": "territory",
                "countries": ["US"],
                "status": "active",
                "metadata": {
                    "geo_blocking": {
                        "rules": [
                            {
                                "rule_id": "region_001",
                                "rule_type": "region_allow",
                                "rule_name": "Allow specific US states",
                                "country": "US",
                                "regions": ["CA", "NY", "TX", "FL"],
                                "enabled": True
                            }
                        ]
                    }
                }
            },
            headers=auth_headers
        )
        
        license_id = license_response.json()["id"]
        
        # Check allowed region
        response = await client.post(
            f"/api/v1/rights/geo-blocking/check/{license_id}",
            params={
                "country_code": "US",
                "region_code": "CA"
            },
            headers=auth_headers
        )
        
        data = response.json()
        assert data["access_allowed"] is True
        
        # Check blocked region
        response = await client.post(
            f"/api/v1/rights/geo-blocking/check/{license_id}",
            params={
                "country_code": "US",
                "region_code": "WA"  # Not in allowed list
            },
            headers=auth_headers
        )
        
        data = response.json()
        assert data["access_allowed"] is False
        assert "region" in data["block_reason"].lower()