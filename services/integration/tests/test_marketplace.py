"""
Tests for API Marketplace functionality
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.marketplace import APIListing, APIListingReview, APIInstallation
from src.services.marketplace import MarketplaceService
from src.api.marketplace import router
from src.core.exceptions import NotFoundError, ValidationError


class TestMarketplaceService:
    """Test marketplace service"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def sample_listing_data(self):
        """Sample API listing data"""
        return {
            "name": "Test API",
            "description": "A test API integration",
            "short_description": "Test API for integration",
            "provider_name": "Test Provider",
            "provider_url": "https://testprovider.com",
            "api_type": "rest",
            "category": "social",
            "version": "1.0.0",
            "base_url": "https://api.testprovider.com",
            "authentication_type": "api_key",
            "auth_config": {"key_header": "X-API-Key"},
            "config_schema": {
                "type": "object",
                "properties": {
                    "api_key": {"type": "string"}
                },
                "required": ["api_key"]
            },
            "documentation_url": "https://docs.testprovider.com",
            "tags": ["social", "messaging"],
            "pricing_model": "freemium"
        }
    
    @pytest.fixture
    def sample_listing(self, sample_listing_data):
        """Sample API listing object"""
        listing = APIListing(**sample_listing_data)
        listing.id = "test-listing-id"
        listing.provider_id = "test-provider-id"
        listing.status = "approved"
        listing.install_count = 10
        listing.rating_average = 4.5
        listing.rating_count = 5
        listing.view_count = 100
        listing.created_at = datetime.utcnow()
        return listing
    
    @pytest.mark.asyncio
    async def test_list_listings(self, mock_db):
        """Test listing API listings"""
        # Mock database response
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        # Mock count
        mock_count_result = Mock()
        mock_count_result.scalar.return_value = 0
        mock_db.execute.side_effect = [mock_count_result, mock_result]
        
        listings, total = await MarketplaceService.list_listings(mock_db)
        
        assert listings == []
        assert total == 0
        assert mock_db.execute.call_count == 2
    
    @pytest.mark.asyncio
    async def test_get_listing(self, mock_db, sample_listing):
        """Test getting specific listing"""
        # Mock database response
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_listing
        mock_db.execute.return_value = mock_result
        
        listing = await MarketplaceService.get_listing(mock_db, "test-listing-id")
        
        assert listing == sample_listing
        assert listing.view_count == 101  # Should increment
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_listing_not_found(self, mock_db):
        """Test getting non-existent listing"""
        # Mock database response
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        listing = await MarketplaceService.get_listing(mock_db, "invalid-id")
        
        assert listing is None
    
    @pytest.mark.asyncio
    async def test_create_listing(self, mock_db, sample_listing_data):
        """Test creating API listing"""
        from src.models.marketplace import APIListingCreate
        
        # Mock category validation
        mock_category_result = Mock()
        mock_category_result.scalar_one_or_none.return_value = Mock()  # Category exists
        mock_db.execute.return_value = mock_category_result
        
        listing_data = APIListingCreate(**sample_listing_data)
        
        with patch.object(MarketplaceService, '_validate_category'):
            listing = await MarketplaceService.create_listing(
                db=mock_db,
                listing_data=listing_data,
                creator_id="test-user-id"
            )
        
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_install_integration(self, mock_db, sample_listing):
        """Test installing integration from marketplace"""
        # Mock getting listing
        with patch.object(MarketplaceService, 'get_listing', return_value=sample_listing):
            # Mock existing installation check
            mock_existing_result = Mock()
            mock_existing_result.scalar_one_or_none.return_value = None
            mock_db.execute.return_value = mock_existing_result
            
            # Mock integration service
            mock_integration = Mock()
            mock_integration.id = "test-integration-id"
            
            with patch('src.services.marketplace.IntegrationService.create_integration', 
                      return_value=mock_integration):
                result = await MarketplaceService.install_integration(
                    db=mock_db,
                    listing_id="test-listing-id",
                    user_id="test-user-id",
                    config={"api_key": "test-key"}
                )
        
        assert "installation_id" in result
        assert "integration_id" in result
        assert result["status"] == "active"
        mock_db.add.assert_called()
        mock_db.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_install_integration_already_installed(self, mock_db, sample_listing):
        """Test installing already installed integration"""
        # Mock getting listing
        with patch.object(MarketplaceService, 'get_listing', return_value=sample_listing):
            # Mock existing installation
            mock_existing_result = Mock()
            mock_existing_result.scalar_one_or_none.return_value = Mock()  # Already exists
            mock_db.execute.return_value = mock_existing_result
            
            with pytest.raises(ValidationError, match="already installed"):
                await MarketplaceService.install_integration(
                    db=mock_db,
                    listing_id="test-listing-id",
                    user_id="test-user-id",
                    config={"api_key": "test-key"}
                )
    
    @pytest.mark.asyncio
    async def test_rate_listing(self, mock_db, sample_listing):
        """Test rating API listing"""
        # Mock getting listing
        with patch.object(MarketplaceService, 'get_listing', return_value=sample_listing):
            # Mock existing review check
            mock_existing_result = Mock()
            mock_existing_result.scalar_one_or_none.return_value = None
            mock_db.execute.return_value = mock_existing_result
            
            # Mock rating update
            with patch.object(MarketplaceService, '_update_listing_rating'):
                result = await MarketplaceService.rate_listing(
                    db=mock_db,
                    listing_id="test-listing-id",
                    user_id="test-user-id",
                    rating=5,
                    review="Great API!"
                )
        
        assert "review_id" in result
        assert result["rating"] == 5
        mock_db.add.assert_called()
        mock_db.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_categories(self, mock_db):
        """Test getting marketplace categories"""
        # Mock database response
        mock_categories = [
            Mock(id="cat1", name="Social", description="Social APIs", 
                 icon="social", color="#FF0000", listing_count=5, featured=True),
            Mock(id="cat2", name="Payment", description="Payment APIs",
                 icon="payment", color="#00FF00", listing_count=3, featured=False)
        ]
        
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_categories
        mock_db.execute.return_value = mock_result
        
        categories = await MarketplaceService.get_categories(mock_db)
        
        assert len(categories) == 2
        assert categories[0]["name"] == "Social"
        assert categories[1]["name"] == "Payment"
    
    @pytest.mark.asyncio
    async def test_get_stats(self, mock_db):
        """Test getting marketplace statistics"""
        # Mock database responses
        mock_db.execute.side_effect = [
            Mock(scalar=Mock(return_value=10)),  # total listings
            Mock(scalar=Mock(return_value=100)),  # total installs
            [Mock(category="social", count=5), Mock(category="payment", count=3)]  # categories
        ]
        
        stats = await MarketplaceService.get_stats(mock_db)
        
        assert stats["total_listings"] == 10
        assert stats["total_installs"] == 100
        assert len(stats["categories"]) == 2
    
    @pytest.mark.asyncio
    async def test_test_integration_rest(self, mock_db, sample_listing):
        """Test testing REST API integration"""
        # Mock getting listing
        with patch.object(MarketplaceService, 'get_listing', return_value=sample_listing):
            # Mock REST API test
            with patch.object(MarketplaceService, '_test_rest_api', 
                             return_value={"status": "success", "message": "Connection successful"}):
                result = await MarketplaceService.test_integration(
                    db=mock_db,
                    listing_id="test-listing-id",
                    config={"api_key": "test-key"},
                    user_id="test-user-id"
                )
        
        assert result["status"] == "success"
        assert "message" in result


class TestMarketplaceAPI:
    """Test marketplace API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Test client"""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)
    
    @pytest.fixture
    def mock_current_user(self):
        """Mock current user"""
        user = Mock()
        user.id = "test-user-id"
        user.email = "test@example.com"
        return user
    
    def test_list_api_listings(self, client):
        """Test listing API listings endpoint"""
        with patch('src.api.marketplace.MarketplaceService.list_listings',
                  return_value=([], 0)):
            with patch('src.api.marketplace.get_db'):
                response = client.get("/marketplace/")
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "meta" in data
    
    def test_get_marketplace_categories(self, client):
        """Test getting marketplace categories"""
        with patch('src.api.marketplace.MarketplaceService.get_categories',
                  return_value=[{"name": "Social", "count": 5}]):
            with patch('src.api.marketplace.get_db'):
                response = client.get("/marketplace/categories")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Social"
    
    def test_get_marketplace_stats(self, client):
        """Test getting marketplace statistics"""
        with patch('src.api.marketplace.MarketplaceService.get_stats',
                  return_value={"total_listings": 10, "total_installs": 100}):
            with patch('src.api.marketplace.get_db'):
                response = client.get("/marketplace/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total_listings"] == 10
    
    def test_get_api_listing(self, client):
        """Test getting specific API listing"""
        mock_listing = Mock()
        mock_listing.id = "test-id"
        mock_listing.name = "Test API"
        
        with patch('src.api.marketplace.MarketplaceService.get_listing',
                  return_value=mock_listing):
            with patch('src.api.marketplace.get_db'):
                response = client.get("/marketplace/test-id")
        
        assert response.status_code == 200
    
    def test_get_api_listing_not_found(self, client):
        """Test getting non-existent API listing"""
        with patch('src.api.marketplace.MarketplaceService.get_listing',
                  return_value=None):
            with patch('src.api.marketplace.get_db'):
                response = client.get("/marketplace/invalid-id")
        
        assert response.status_code == 404
    
    def test_create_api_listing(self, client, mock_current_user):
        """Test creating API listing"""
        listing_data = {
            "name": "Test API",
            "description": "Test description",
            "provider_name": "Test Provider",
            "api_type": "rest",
            "category": "social",
            "version": "1.0.0"
        }
        
        mock_listing = Mock()
        mock_listing.id = "new-listing-id"
        
        with patch('src.api.marketplace.get_current_user', return_value=mock_current_user):
            with patch('src.api.marketplace.check_permission'):
                with patch('src.api.marketplace.MarketplaceService.create_listing',
                          return_value=mock_listing):
                    with patch('src.api.marketplace.get_db'):
                        response = client.post("/marketplace/", json=listing_data)
        
        assert response.status_code == 201
    
    def test_install_api_integration(self, client, mock_current_user):
        """Test installing API integration"""
        config = {"api_key": "test-key"}
        
        with patch('src.api.marketplace.get_current_user', return_value=mock_current_user):
            with patch('src.api.marketplace.check_permission'):
                with patch('src.api.marketplace.MarketplaceService.install_integration',
                          return_value={"installation_id": "test-install-id", "status": "active"}):
                    with patch('src.api.marketplace.get_db'):
                        response = client.post("/marketplace/test-id/install", json=config)
        
        assert response.status_code == 200
        data = response.json()
        assert data["installation_id"] == "test-install-id"
    
    def test_rate_api_listing(self, client, mock_current_user):
        """Test rating API listing"""
        with patch('src.api.marketplace.get_current_user', return_value=mock_current_user):
            with patch('src.api.marketplace.MarketplaceService.rate_listing',
                      return_value={"review_id": "test-review-id", "rating": 5}):
                with patch('src.api.marketplace.get_db'):
                    response = client.post("/marketplace/test-id/rate?rating=5&review=Great API!")
        
        assert response.status_code == 200
        data = response.json()
        assert data["rating"] == 5
    
    def test_test_api_integration(self, client, mock_current_user):
        """Test testing API integration"""
        test_config = {"api_key": "test-key"}
        
        with patch('src.api.marketplace.get_current_user', return_value=mock_current_user):
            with patch('src.api.marketplace.MarketplaceService.test_integration',
                      return_value={"status": "success", "message": "Test passed"}):
                with patch('src.api.marketplace.get_db'):
                    response = client.post("/marketplace/test-id/test", json=test_config)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


class TestMarketplaceIntegration:
    """Integration tests for marketplace"""
    
    @pytest.mark.asyncio
    async def test_marketplace_workflow(self, mock_db):
        """Test complete marketplace workflow"""
        # 1. Create listing
        listing_data = {
            "name": "Test Integration",
            "description": "Test API integration",
            "provider_name": "Test Provider",
            "api_type": "rest",
            "category": "social",
            "version": "1.0.0",
            "base_url": "https://api.test.com",
            "authentication_type": "api_key"
        }
        
        # Mock category validation
        with patch.object(MarketplaceService, '_validate_category'):
            # Mock create listing
            mock_listing = Mock()
            mock_listing.id = "test-listing-id"
            mock_listing.status = "pending"
            
            mock_db.add = Mock()
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            
            from src.models.marketplace import APIListingCreate
            listing_create = APIListingCreate(**listing_data)
            
            listing = await MarketplaceService.create_listing(
                db=mock_db,
                listing_data=listing_create,
                creator_id="provider-id"
            )
        
        # 2. Approve listing (admin action)
        listing.status = "approved"
        
        # 3. User discovers and installs
        with patch.object(MarketplaceService, 'get_listing', return_value=listing):
            with patch('src.services.marketplace.IntegrationService.create_integration') as mock_create:
                mock_integration = Mock()
                mock_integration.id = "integration-id"
                mock_create.return_value = mock_integration
                
                # Mock existing installation check
                mock_existing_result = Mock()
                mock_existing_result.scalar_one_or_none.return_value = None
                mock_db.execute.return_value = mock_existing_result
                
                result = await MarketplaceService.install_integration(
                    db=mock_db,
                    listing_id="test-listing-id",
                    user_id="user-id",
                    config={"api_key": "user-key"}
                )
        
        # 4. User rates the integration
        with patch.object(MarketplaceService, 'get_listing', return_value=listing):
            with patch.object(MarketplaceService, '_update_listing_rating'):
                # Mock existing review check
                mock_existing_result = Mock()
                mock_existing_result.scalar_one_or_none.return_value = None
                mock_db.execute.return_value = mock_existing_result
                
                await MarketplaceService.rate_listing(
                    db=mock_db,
                    listing_id="test-listing-id",
                    user_id="user-id",
                    rating=5,
                    review="Excellent integration!"
                )
        
        # Verify workflow completed
        assert result["status"] == "active"
        assert "installation_id" in result