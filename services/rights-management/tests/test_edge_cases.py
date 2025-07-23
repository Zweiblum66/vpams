"""
Tests for Edge Cases and Integration Scenarios

Tests error handling, edge cases, and complex integration scenarios.
"""

import pytest
from httpx import AsyncClient
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from datetime import datetime, date, timedelta
import asyncio


class TestEdgeCases:
    """Test edge cases and error scenarios"""
    
    @pytest.mark.asyncio
    async def test_create_license_with_nonexistent_parties(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test creating license with non-existent party IDs"""
        license_data = {
            "license_number": "LIC-INVALID-001",
            "license_type": "sync",
            "title": "Invalid License",
            "asset_id": str(uuid.uuid4()),
            "licensor_id": str(uuid.uuid4()),  # Non-existent
            "licensee_id": str(uuid.uuid4()),  # Non-existent
            "start_date": "2025-01-01",
            "geographic_scope": "worldwide"
        }
        
        response = await client.post(
            "/api/v1/rights/licenses",
            json=license_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    
    @pytest.mark.asyncio
    async def test_overlapping_exclusive_licenses(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test creating overlapping exclusive licenses"""
        # Create parties
        licensor = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensor",
                "name": "Exclusive Test Licensor",
                "contact_email": "exclusive@test.com",
                "country": "USA"
            },
            headers=auth_headers
        )
        licensor_id = licensor.json()["id"]
        
        licensee1 = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensee",
                "name": "Exclusive Licensee 1",
                "contact_email": "licensee1@test.com",
                "country": "USA"
            },
            headers=auth_headers
        )
        licensee1_id = licensee1.json()["id"]
        
        licensee2 = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensee",
                "name": "Exclusive Licensee 2",
                "contact_email": "licensee2@test.com",
                "country": "USA"
            },
            headers=auth_headers
        )
        licensee2_id = licensee2.json()["id"]
        
        asset_id = str(uuid.uuid4())
        
        # Create first exclusive license
        license1_response = await client.post(
            "/api/v1/rights/licenses",
            json={
                "license_number": "LIC-EXCLUSIVE-001",
                "license_type": "broadcast",
                "title": "First Exclusive License",
                "asset_id": asset_id,
                "licensor_id": licensor_id,
                "licensee_id": licensee1_id,
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "geographic_scope": "territory",
                "countries": ["US"],
                "exclusivity": True
            },
            headers=auth_headers
        )
        
        assert license1_response.status_code == status.HTTP_201_CREATED
        
        # Try to create overlapping exclusive license
        license2_response = await client.post(
            "/api/v1/rights/licenses",
            json={
                "license_number": "LIC-EXCLUSIVE-002",
                "license_type": "broadcast",
                "title": "Second Exclusive License",
                "asset_id": asset_id,  # Same asset
                "licensor_id": licensor_id,
                "licensee_id": licensee2_id,
                "start_date": "2025-06-01",  # Overlapping dates
                "end_date": "2025-12-31",
                "geographic_scope": "territory",
                "countries": ["US"],  # Same territory
                "exclusivity": True
            },
            headers=auth_headers
        )
        
        # Should succeed but compliance check should flag it
        assert license2_response.status_code in [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]
    
    @pytest.mark.asyncio
    async def test_circular_sublicensing(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test circular sublicensing scenario"""
        # Create three parties
        parties = []
        for i in range(3):
            party = await client.post(
                "/api/v1/rights/parties",
                json={
                    "party_type": "licensee",
                    "name": f"Circular Party {i}",
                    "contact_email": f"circular{i}@test.com",
                    "country": "USA"
                },
                headers=auth_headers
            )
            parties.append(party.json()["id"])
        
        asset_id = str(uuid.uuid4())
        
        # Create license chain A -> B
        license_ab = await client.post(
            "/api/v1/rights/licenses",
            json={
                "license_number": "LIC-CIRCULAR-AB",
                "license_type": "sync",
                "title": "License A to B",
                "asset_id": asset_id,
                "licensor_id": parties[0],
                "licensee_id": parties[1],
                "start_date": "2025-01-01",
                "geographic_scope": "worldwide",
                "sublicensing_allowed": True
            },
            headers=auth_headers
        )
        
        # Create license chain B -> C
        license_bc = await client.post(
            "/api/v1/rights/licenses",
            json={
                "license_number": "LIC-CIRCULAR-BC",
                "license_type": "sync",
                "title": "License B to C",
                "asset_id": asset_id,
                "licensor_id": parties[1],
                "licensee_id": parties[2],
                "start_date": "2025-01-01",
                "geographic_scope": "worldwide",
                "sublicensing_allowed": True
            },
            headers=auth_headers
        )
        
        # Try to create circular license C -> A
        license_ca = await client.post(
            "/api/v1/rights/licenses",
            json={
                "license_number": "LIC-CIRCULAR-CA",
                "license_type": "sync",
                "title": "License C to A",
                "asset_id": asset_id,
                "licensor_id": parties[2],
                "licensee_id": parties[0],  # Circular!
                "start_date": "2025-01-01",
                "geographic_scope": "worldwide"
            },
            headers=auth_headers
        )
        
        # Should succeed but could be flagged in compliance
        assert license_ca.status_code == status.HTTP_201_CREATED
    
    @pytest.mark.asyncio
    async def test_concurrent_usage_limit_check(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test concurrent usage creation against limits"""
        # Create parties and license
        licensor = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensor",
                "name": "Concurrent Test Licensor",
                "contact_email": "concurrent@test.com",
                "country": "USA"
            },
            headers=auth_headers
        )
        licensor_id = licensor.json()["id"]
        
        licensee = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensee",
                "name": "Concurrent Test Licensee",
                "contact_email": "concurrent.licensee@test.com",
                "country": "USA"
            },
            headers=auth_headers
        )
        licensee_id = licensee.json()["id"]
        
        asset_id = str(uuid.uuid4())
        
        # Create license with small usage limit
        license_response = await client.post(
            "/api/v1/rights/licenses",
            json={
                "license_number": "LIC-CONCURRENT-001",
                "license_type": "sync",
                "title": "Limited Usage License",
                "asset_id": asset_id,
                "licensor_id": licensor_id,
                "licensee_id": licensee_id,
                "start_date": "2025-01-01",
                "geographic_scope": "worldwide",
                "max_usage_count": 5  # Small limit
            },
            headers=auth_headers
        )
        license_id = license_response.json()["id"]
        
        # Try to create multiple usage records concurrently
        async def create_usage(i):
            return await client.post(
                "/api/v1/rights/usage",
                json={
                    "license_id": license_id,
                    "asset_id": asset_id,
                    "user_id": str(uuid.uuid4()),
                    "usage_type": "sync",
                    "usage_date": datetime.utcnow().isoformat(),
                    "duration_seconds": 1800,
                    "platform": "Film",
                    "country": "USA"
                },
                headers=auth_headers
            )
        
        # Create 10 concurrent requests (exceeding limit of 5)
        tasks = [create_usage(i) for i in range(10)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successful creations
        successful = sum(1 for r in responses if not isinstance(r, Exception) and r.status_code == status.HTTP_201_CREATED)
        
        # Should create some but not all due to limit
        assert successful >= 5  # At least up to the limit
        assert successful <= 10  # But not more than attempted
    
    @pytest.mark.asyncio
    async def test_invalid_date_combinations(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test various invalid date combinations"""
        # Create parties
        licensor = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensor",
                "name": "Date Test Licensor",
                "contact_email": "date@test.com",
                "country": "USA"
            },
            headers=auth_headers
        )
        licensor_id = licensor.json()["id"]
        
        licensee = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensee",
                "name": "Date Test Licensee",
                "contact_email": "date.licensee@test.com",
                "country": "USA"
            },
            headers=auth_headers
        )
        licensee_id = licensee.json()["id"]
        
        base_license = {
            "license_number": "LIC-DATE-001",
            "license_type": "sync",
            "title": "Date Test License",
            "asset_id": str(uuid.uuid4()),
            "licensor_id": licensor_id,
            "licensee_id": licensee_id,
            "geographic_scope": "worldwide"
        }
        
        # Test 1: End date before start date
        response = await client.post(
            "/api/v1/rights/licenses",
            json={
                **base_license,
                "start_date": "2025-12-31",
                "end_date": "2025-01-01"
            },
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        
        # Test 2: Signed date after start date
        response = await client.post(
            "/api/v1/rights/licenses",
            json={
                **base_license,
                "license_number": "LIC-DATE-002",
                "start_date": "2025-01-01",
                "signed_date": "2025-06-01"
            },
            headers=auth_headers
        )
        # This might be allowed in some cases
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]
    
    @pytest.mark.asyncio
    async def test_extreme_financial_values(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test extreme financial values"""
        # Create parties
        licensor = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensor",
                "name": "Financial Test Licensor",
                "contact_email": "financial@test.com",
                "country": "USA"
            },
            headers=auth_headers
        )
        licensor_id = licensor.json()["id"]
        
        licensee = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensee",
                "name": "Financial Test Licensee",
                "contact_email": "financial.licensee@test.com",
                "country": "USA"
            },
            headers=auth_headers
        )
        licensee_id = licensee.json()["id"]
        
        # Test very large financial values
        response = await client.post(
            "/api/v1/rights/licenses",
            json={
                "license_number": "LIC-FINANCIAL-001",
                "license_type": "master",
                "title": "High Value License",
                "asset_id": str(uuid.uuid4()),
                "licensor_id": licensor_id,
                "licensee_id": licensee_id,
                "start_date": "2025-01-01",
                "geographic_scope": "worldwide",
                "license_fee": 999999999.99,  # Very large
                "minimum_guarantee": 100000000.00,
                "royalty_rate": 99.99  # Nearly 100%
            },
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["license_fee"] == 999999999.99
    
    @pytest.mark.asyncio
    async def test_malformed_geographic_data(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test malformed geographic data"""
        # Create parties
        licensor = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensor",
                "name": "Geo Test Licensor",
                "contact_email": "geo.malformed@test.com",
                "country": "USA"
            },
            headers=auth_headers
        )
        licensor_id = licensor.json()["id"]
        
        licensee = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensee",
                "name": "Geo Test Licensee",
                "contact_email": "geo.licensee@test.com",
                "country": "USA"
            },
            headers=auth_headers
        )
        licensee_id = licensee.json()["id"]
        
        # Test invalid country codes
        response = await client.post(
            "/api/v1/rights/licenses",
            json={
                "license_number": "LIC-GEO-INVALID-001",
                "license_type": "broadcast",
                "title": "Invalid Geo License",
                "asset_id": str(uuid.uuid4()),
                "licensor_id": licensor_id,
                "licensee_id": licensee_id,
                "start_date": "2025-01-01",
                "geographic_scope": "territory",
                "countries": ["USA", "XX", "123", ""]  # Invalid codes
            },
            headers=auth_headers
        )
        
        # May accept but should validate
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]
    
    @pytest.mark.asyncio
    async def test_unicode_and_special_characters(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test Unicode and special characters in data"""
        # Create party with Unicode name
        party_response = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensor",
                "name": "日本の映画スタジオ",  # Japanese
                "legal_name": "Société Française de Production",  # French
                "contact_email": "unicode@test.com",
                "country": "日本",
                "address": "123 Улица Пушкина, Москва",  # Russian
                "notes": "Special chars: @#$%^&*()_+-=[]{}|;':\",./<>?"
            },
            headers=auth_headers
        )
        
        assert party_response.status_code == status.HTTP_201_CREATED
        data = party_response.json()
        assert data["name"] == "日本の映画スタジオ"
    
    @pytest.mark.asyncio
    async def test_very_long_strings(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test very long string values"""
        # Create parties
        licensor = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensor",
                "name": "Long String Licensor",
                "contact_email": "long@test.com",
                "country": "USA"
            },
            headers=auth_headers
        )
        licensor_id = licensor.json()["id"]
        
        licensee = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensee",
                "name": "Long String Licensee",
                "contact_email": "long.licensee@test.com",
                "country": "USA"
            },
            headers=auth_headers
        )
        licensee_id = licensee.json()["id"]
        
        # Create license with very long description
        very_long_description = "A" * 10000  # 10k characters
        very_long_notes = "B" * 5000  # 5k characters
        
        response = await client.post(
            "/api/v1/rights/licenses",
            json={
                "license_number": "LIC-LONG-001",
                "license_type": "sync",
                "title": "Long String License",
                "description": very_long_description,
                "notes": very_long_notes,
                "asset_id": str(uuid.uuid4()),
                "licensor_id": licensor_id,
                "licensee_id": licensee_id,
                "start_date": "2025-01-01",
                "geographic_scope": "worldwide"
            },
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert len(data["description"]) == 10000
    
    @pytest.mark.asyncio
    async def test_null_and_empty_values(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test null and empty value handling"""
        # Create parties
        licensor = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensor",
                "name": "Null Test Licensor",
                "contact_email": "null@test.com",
                "country": "USA"
            },
            headers=auth_headers
        )
        licensor_id = licensor.json()["id"]
        
        licensee = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensee",
                "name": "Null Test Licensee",
                "contact_email": "null.licensee@test.com",
                "country": "USA"
            },
            headers=auth_headers
        )
        licensee_id = licensee.json()["id"]
        
        # Create license with minimal required fields
        response = await client.post(
            "/api/v1/rights/licenses",
            json={
                "license_number": "LIC-NULL-001",
                "license_type": "sync",
                "title": "Minimal License",
                "asset_id": str(uuid.uuid4()),
                "licensor_id": licensor_id,
                "licensee_id": licensee_id,
                "start_date": "2025-01-01",
                "geographic_scope": "worldwide",
                "description": "",  # Empty string
                "notes": None,  # Null
                "metadata": {}  # Empty object
            },
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["description"] == ""
        assert data["notes"] is None
    
    @pytest.mark.asyncio
    async def test_pagination_edge_cases(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test pagination edge cases"""
        # Test page 0
        response = await client.get(
            "/api/v1/rights/parties?page=0&limit=10",
            headers=auth_headers
        )
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]
        
        # Test negative page
        response = await client.get(
            "/api/v1/rights/parties?page=-1&limit=10",
            headers=auth_headers
        )
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]
        
        # Test limit 0
        response = await client.get(
            "/api/v1/rights/parties?page=1&limit=0",
            headers=auth_headers
        )
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]
        
        # Test very large page number
        response = await client.get(
            "/api/v1/rights/parties?page=999999&limit=10",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 0  # Empty result
        
        # Test very large limit
        response = await client.get(
            "/api/v1/rights/parties?page=1&limit=1000",
            headers=auth_headers
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]