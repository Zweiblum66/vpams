"""
Tests for Rights Party Management API

Tests CRUD operations and business logic for rights parties (licensors, licensees, agents).
"""

import pytest
from httpx import AsyncClient
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from src.db.models import RightsParty, License
from src.models.schemas import RightsPartyCreate, RightsPartyUpdate


class TestRightsPartyEndpoints:
    """Test rights party API endpoints"""
    
    @pytest.mark.asyncio
    async def test_create_rights_party_success(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test successful rights party creation"""
        party_data = {
            "party_type": "licensor",
            "name": "ABC Productions",
            "legal_name": "ABC Productions LLC",
            "contact_email": "legal@abcproductions.com",
            "contact_phone": "+1-555-0123",
            "address": "123 Production St, Hollywood, CA 90028",
            "country": "USA",
            "tax_id": "12-3456789",
            "percentage_share": 100.0,
            "metadata": {
                "company_type": "production",
                "established": "2010"
            }
        }
        
        response = await client.post(
            "/api/v1/rights/parties",
            json=party_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["id"] is not None
        assert data["party_type"] == party_data["party_type"]
        assert data["name"] == party_data["name"]
        assert data["legal_name"] == party_data["legal_name"]
        assert data["contact_email"] == party_data["contact_email"]
        assert data["is_active"] is True
    
    @pytest.mark.asyncio
    async def test_create_duplicate_rights_party(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test creating duplicate rights party fails"""
        party_data = {
            "party_type": "licensee",
            "name": "XYZ Broadcasting",
            "contact_email": "contact@xyzbroadcast.com",
            "country": "USA"
        }
        
        # Create first party
        response1 = await client.post(
            "/api/v1/rights/parties",
            json=party_data,
            headers=auth_headers
        )
        assert response1.status_code == status.HTTP_201_CREATED
        
        # Try to create duplicate
        response2 = await client.post(
            "/api/v1/rights/parties",
            json=party_data,
            headers=auth_headers
        )
        assert response2.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    
    @pytest.mark.asyncio
    async def test_get_rights_parties_pagination(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test getting rights parties with pagination"""
        # Create multiple parties
        for i in range(25):
            party_data = {
                "party_type": "agent" if i % 2 == 0 else "licensor",
                "name": f"Test Party {i}",
                "contact_email": f"party{i}@test.com",
                "country": "USA"
            }
            await client.post(
                "/api/v1/rights/parties",
                json=party_data,
                headers=auth_headers
            )
        
        # Test pagination
        response = await client.get(
            "/api/v1/rights/parties?page=1&limit=10",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 10
        assert data["total"] >= 25
        assert data["page"] == 1
        assert data["limit"] == 10
        assert data["pages"] >= 3
    
    @pytest.mark.asyncio
    async def test_get_rights_parties_filtering(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test filtering rights parties"""
        # Create test parties
        party1 = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensor",
                "name": "Film Studio Alpha",
                "contact_email": "legal@filmstudio.com",
                "country": "USA",
                "is_active": True
            },
            headers=auth_headers
        )
        
        party2 = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensee",
                "name": "Broadcasting Beta",
                "contact_email": "contact@broadcast.com",
                "country": "UK",
                "is_active": True
            },
            headers=auth_headers
        )
        
        # Test party_type filter
        response = await client.get(
            "/api/v1/rights/parties?party_type=licensor",
            headers=auth_headers
        )
        data = response.json()
        assert all(item["party_type"] == "licensor" for item in data["items"])
        
        # Test search filter
        response = await client.get(
            "/api/v1/rights/parties?search=Alpha",
            headers=auth_headers
        )
        data = response.json()
        assert any("Alpha" in item["name"] for item in data["items"])
        
        # Test is_active filter
        response = await client.get(
            "/api/v1/rights/parties?is_active=true",
            headers=auth_headers
        )
        data = response.json()
        assert all(item["is_active"] is True for item in data["items"])
    
    @pytest.mark.asyncio
    async def test_get_single_rights_party(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test getting a single rights party"""
        # Create party
        create_response = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "agent",
                "name": "Media Rights Agency",
                "contact_email": "info@mediaagency.com",
                "country": "USA"
            },
            headers=auth_headers
        )
        party_id = create_response.json()["id"]
        
        # Get party
        response = await client.get(
            f"/api/v1/rights/parties/{party_id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == party_id
        assert data["name"] == "Media Rights Agency"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_rights_party(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test getting non-existent rights party returns 404"""
        fake_id = str(uuid.uuid4())
        response = await client.get(
            f"/api/v1/rights/parties/{fake_id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_update_rights_party(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test updating a rights party"""
        # Create party
        create_response = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensee",
                "name": "Old Company Name",
                "contact_email": "old@company.com",
                "country": "USA"
            },
            headers=auth_headers
        )
        party_id = create_response.json()["id"]
        
        # Update party
        update_data = {
            "name": "New Company Name",
            "contact_email": "new@company.com",
            "contact_phone": "+1-555-9999",
            "metadata": {
                "updated": "2025-07-18"
            }
        }
        
        response = await client.put(
            f"/api/v1/rights/parties/{party_id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "New Company Name"
        assert data["contact_email"] == "new@company.com"
        assert data["contact_phone"] == "+1-555-9999"
        assert data["metadata"]["updated"] == "2025-07-18"
    
    @pytest.mark.asyncio
    async def test_delete_rights_party_soft_delete(
        self, client: AsyncClient, auth_headers: dict, test_db: AsyncSession
    ):
        """Test soft delete when party has licenses"""
        # Create party
        create_response = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensor",
                "name": "Delete Test Licensor",
                "contact_email": "delete@test.com",
                "country": "USA"
            },
            headers=auth_headers
        )
        party_id = create_response.json()["id"]
        
        # Create licensee for the license
        licensee_response = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensee",
                "name": "Delete Test Licensee",
                "contact_email": "licensee@test.com",
                "country": "USA"
            },
            headers=auth_headers
        )
        licensee_id = licensee_response.json()["id"]
        
        # Create a license using this party
        license_data = {
            "license_number": "LIC-2025-001",
            "license_type": "sync",
            "title": "Test License",
            "asset_id": str(uuid.uuid4()),
            "licensor_id": party_id,
            "licensee_id": licensee_id,
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "geographic_scope": "worldwide",
            "license_fee": 10000.0,
            "currency": "USD"
        }
        
        await client.post(
            "/api/v1/rights/licenses",
            json=license_data,
            headers=auth_headers
        )
        
        # Delete party (should soft delete)
        response = await client.delete(
            f"/api/v1/rights/parties/{party_id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify soft delete
        result = await test_db.execute(
            select(RightsParty).where(RightsParty.id == party_id)
        )
        party = result.scalar_one_or_none()
        assert party is not None
        assert party.is_active is False
    
    @pytest.mark.asyncio
    async def test_delete_rights_party_hard_delete(
        self, client: AsyncClient, auth_headers: dict, test_db: AsyncSession
    ):
        """Test hard delete when party has no licenses"""
        # Create party
        create_response = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "agent",
                "name": "Delete Test Agent",
                "contact_email": "deleteagent@test.com",
                "country": "USA"
            },
            headers=auth_headers
        )
        party_id = create_response.json()["id"]
        
        # Delete party (should hard delete)
        response = await client.delete(
            f"/api/v1/rights/parties/{party_id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify hard delete
        result = await test_db.execute(
            select(RightsParty).where(RightsParty.id == party_id)
        )
        party = result.scalar_one_or_none()
        assert party is None
    
    @pytest.mark.asyncio
    async def test_percentage_share_validation(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test percentage share validation"""
        # Test valid percentage
        response = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensor",
                "name": "Valid Percentage Party",
                "contact_email": "valid@percentage.com",
                "country": "USA",
                "percentage_share": 50.0
            },
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_201_CREATED
        
        # Test invalid percentage (>100)
        response = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensor",
                "name": "Invalid Percentage Party",
                "contact_email": "invalid@percentage.com",
                "country": "USA",
                "percentage_share": 150.0
            },
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    
    @pytest.mark.asyncio
    async def test_rights_party_metadata(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test metadata storage and retrieval"""
        metadata = {
            "company_info": {
                "founded": "1995",
                "employees": 250,
                "industry": "Film Production"
            },
            "certifications": ["ISO 9001", "SOC 2"],
            "preferred_payment_method": "wire_transfer"
        }
        
        # Create party with metadata
        response = await client.post(
            "/api/v1/rights/parties",
            json={
                "party_type": "licensor",
                "name": "Metadata Test Company",
                "contact_email": "metadata@test.com",
                "country": "USA",
                "metadata": metadata
            },
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["metadata"] == metadata
        assert data["metadata"]["company_info"]["employees"] == 250
        assert "ISO 9001" in data["metadata"]["certifications"]