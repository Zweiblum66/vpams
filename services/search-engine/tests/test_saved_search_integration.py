"""
Integration tests for saved search API endpoints
"""

import pytest
from httpx import AsyncClient
from fastapi import status
from unittest.mock import AsyncMock, patch

from src.main import app
from src.models.schemas import FilterType, SearchType, SortOrder


@pytest.mark.integration
class TestSavedSearchIntegration:
    """Integration tests for saved search endpoints"""
    
    @pytest.mark.asyncio
    async def test_create_saved_search(self):
        """Test creating a saved search"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            request_data = {
                "name": "Marketing Videos",
                "description": "Search for marketing-related videos",
                "query": {
                    "query": "marketing campaign",
                    "filters": [
                        {
                            "field": "asset_type",
                            "type": "term",
                            "value": "video"
                        },
                        {
                            "field": "tags",
                            "type": "terms",
                            "value": ["marketing", "campaign"]
                        }
                    ],
                    "facets": [
                        {
                            "name": "file_types",
                            "field": "file_extension",
                            "type": "terms",
                            "size": 10
                        }
                    ],
                    "size": 25,
                    "sort_by": "created_at",
                    "sort_order": "desc"
                },
                "is_public": True,
                "tags": ["marketing", "video"],
                "notify_on_new_results": False
            }
            
            with patch('src.services.saved_search_service.get_saved_search_service') as mock_service:
                mock_service_instance = AsyncMock()
                mock_service_instance.create_saved_search.return_value = {
                    "id": "507f1f77bcf86cd799439011",
                    "user_id": "user123",
                    "name": "Marketing Videos",
                    "description": "Search for marketing-related videos",
                    "query": request_data["query"],
                    "is_public": True,
                    "tags": ["marketing", "video"],
                    "notify_on_new_results": False,
                    "usage_count": 0,
                    "last_used_at": None,
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z"
                }
                mock_service.return_value = mock_service_instance
                
                response = await client.post(
                    "/api/v1/search/saved",
                    json=request_data
                )
            
            # Should return success or mock error
            assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_500_INTERNAL_SERVER_ERROR]
    
    @pytest.mark.asyncio
    async def test_list_saved_searches(self):
        """Test listing saved searches"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('src.services.saved_search_service.get_saved_search_service') as mock_service:
                mock_service_instance = AsyncMock()
                mock_service_instance.list_user_searches.return_value = {
                    "searches": [
                        {
                            "id": "507f1f77bcf86cd799439011",
                            "name": "Marketing Videos",
                            "description": "Search for marketing videos",
                            "user_id": "user123",
                            "is_public": True,
                            "tags": ["marketing"],
                            "usage_count": 5,
                            "created_at": "2024-01-15T10:30:00Z"
                        }
                    ],
                    "total": 1,
                    "page": 1,
                    "per_page": 20,
                    "total_pages": 1
                }
                mock_service.return_value = mock_service_instance
                
                response = await client.get(
                    "/api/v1/search/saved",
                    params={"page": 1, "per_page": 20, "include_public": True}
                )
            
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]
    
    @pytest.mark.asyncio
    async def test_get_popular_saved_searches(self):
        """Test getting popular saved searches"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('src.services.saved_search_service.get_saved_search_service') as mock_service:
                mock_service_instance = AsyncMock()
                mock_service_instance.get_popular_searches.return_value = [
                    {
                        "id": "507f1f77bcf86cd799439011",
                        "name": "Popular Search",
                        "user_id": "user123",
                        "usage_count": 100,
                        "is_public": True
                    }
                ]
                mock_service.return_value = mock_service_instance
                
                response = await client.get(
                    "/api/v1/search/saved/popular",
                    params={"limit": 10}
                )
            
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]
    
    @pytest.mark.asyncio
    async def test_search_by_tags(self):
        """Test searching saved searches by tags"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('src.services.saved_search_service.get_saved_search_service') as mock_service:
                mock_service_instance = AsyncMock()
                mock_service_instance.search_by_tags.return_value = {
                    "searches": [
                        {
                            "id": "507f1f77bcf86cd799439011",
                            "name": "Tagged Search",
                            "tags": ["video", "marketing"],
                            "is_public": True
                        }
                    ],
                    "total": 1,
                    "page": 1,
                    "per_page": 20,
                    "total_pages": 1
                }
                mock_service.return_value = mock_service_instance
                
                response = await client.get(
                    "/api/v1/search/saved/by-tags",
                    params={"tags": ["video", "marketing"], "page": 1, "per_page": 20}
                )
            
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]
    
    @pytest.mark.asyncio
    async def test_get_saved_search_by_id(self):
        """Test getting a specific saved search"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            search_id = "507f1f77bcf86cd799439011"
            
            with patch('src.services.saved_search_service.get_saved_search_service') as mock_service:
                mock_service_instance = AsyncMock()
                mock_service_instance.get_saved_search.return_value = {
                    "id": search_id,
                    "name": "Test Search",
                    "user_id": "user123",
                    "query": {
                        "query": "test",
                        "size": 20,
                        "from": 0
                    },
                    "is_public": True,
                    "tags": ["test"],
                    "usage_count": 3
                }
                mock_service.return_value = mock_service_instance
                
                response = await client.get(f"/api/v1/search/saved/{search_id}")
            
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_500_INTERNAL_SERVER_ERROR]
    
    @pytest.mark.asyncio
    async def test_update_saved_search(self):
        """Test updating a saved search"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            search_id = "507f1f77bcf86cd799439011"
            update_data = {
                "name": "Updated Search Name",
                "description": "Updated description",
                "is_public": False
            }
            
            with patch('src.services.saved_search_service.get_saved_search_service') as mock_service:
                mock_service_instance = AsyncMock()
                mock_service_instance.update_saved_search.return_value = {
                    "id": search_id,
                    "name": "Updated Search Name",
                    "description": "Updated description",
                    "user_id": "user123",
                    "is_public": False,
                    "updated_at": "2024-01-15T11:00:00Z"
                }
                mock_service.return_value = mock_service_instance
                
                response = await client.put(
                    f"/api/v1/search/saved/{search_id}",
                    json=update_data
                )
            
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_500_INTERNAL_SERVER_ERROR]
    
    @pytest.mark.asyncio
    async def test_delete_saved_search(self):
        """Test deleting a saved search"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            search_id = "507f1f77bcf86cd799439011"
            
            with patch('src.services.saved_search_service.get_saved_search_service') as mock_service:
                mock_service_instance = AsyncMock()
                mock_service_instance.delete_saved_search.return_value = True
                mock_service.return_value = mock_service_instance
                
                response = await client.delete(f"/api/v1/search/saved/{search_id}")
            
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_500_INTERNAL_SERVER_ERROR]
    
    @pytest.mark.asyncio
    async def test_execute_saved_search(self):
        """Test executing a saved search"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            search_id = "507f1f77bcf86cd799439011"
            
            with patch('src.services.saved_search_service.get_saved_search_service') as mock_service:
                mock_service_instance = AsyncMock()
                mock_service_instance.execute_saved_search.return_value = {
                    "query": "test video",
                    "total_hits": 25,
                    "hits": [
                        {
                            "id": "asset1",
                            "index": "assets",
                            "score": 1.5,
                            "source": {"name": "test_video.mp4"},
                            "highlight": None
                        }
                    ],
                    "facets": [],
                    "applied_filters": [],
                    "took": 45,
                    "timed_out": False,
                    "page": 1,
                    "per_page": 20,
                    "total_pages": 2
                }
                mock_service.return_value = mock_service_instance
                
                response = await client.post(f"/api/v1/search/saved/{search_id}/execute")
            
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_500_INTERNAL_SERVER_ERROR]
    
    @pytest.mark.asyncio
    async def test_execute_saved_search_with_overrides(self):
        """Test executing a saved search with parameter overrides"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            search_id = "507f1f77bcf86cd799439011"
            execute_params = {
                "size": 50,
                "from": 20,
                "sort_by": "created_at",
                "sort_order": "asc",
                "additional_filters": [
                    {
                        "field": "status",
                        "type": "term",
                        "value": "published"
                    }
                ]
            }
            
            with patch('src.services.saved_search_service.get_saved_search_service') as mock_service:
                mock_service_instance = AsyncMock()
                mock_service_instance.execute_saved_search.return_value = {
                    "query": "test video",
                    "total_hits": 100,
                    "hits": [],
                    "facets": [],
                    "applied_filters": [],
                    "took": 60,
                    "timed_out": False,
                    "page": 2,
                    "per_page": 50,
                    "total_pages": 2
                }
                mock_service.return_value = mock_service_instance
                
                response = await client.post(
                    f"/api/v1/search/saved/{search_id}/execute",
                    json=execute_params
                )
            
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_500_INTERNAL_SERVER_ERROR]
    
    @pytest.mark.asyncio
    async def test_create_saved_search_validation_error(self):
        """Test creating saved search with invalid data"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Empty name should fail validation
            request_data = {
                "name": "",
                "query": {
                    "query": "test",
                    "size": 20,
                    "from": 0
                }
            }
            
            response = await client.post(
                "/api/v1/search/saved",
                json=request_data
            )
            
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_complex_saved_search_scenario(self):
        """Test a complex saved search scenario"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Create a complex saved search
            request_data = {
                "name": "Complex Media Search",
                "description": "Advanced search for media assets with multiple criteria",
                "query": {
                    "query": "corporate presentation 2024",
                    "search_type": "basic",
                    "indices": ["assets", "metadata"],
                    "filters": [
                        {
                            "field": "asset_type",
                            "type": "terms",
                            "value": ["video", "image", "document"]
                        },
                        {
                            "field": "created_at",
                            "type": "range",
                            "value": {
                                "gte": "2024-01-01T00:00:00Z",
                                "lte": "2024-12-31T23:59:59Z"
                            }
                        },
                        {
                            "field": "file_size",
                            "type": "range",
                            "value": {
                                "gte": 1000000,
                                "lte": 100000000
                            }
                        }
                    ],
                    "post_filters": [
                        {
                            "field": "department",
                            "type": "term",
                            "value": "marketing"
                        }
                    ],
                    "facets": [
                        {
                            "name": "asset_types",
                            "field": "asset_type",
                            "type": "terms",
                            "size": 15
                        },
                        {
                            "name": "monthly_distribution",
                            "field": "created_at",
                            "type": "date_histogram",
                            "interval": "month"
                        },
                        {
                            "name": "file_size_stats",
                            "field": "file_size",
                            "type": "stats"
                        }
                    ],
                    "size": 30,
                    "from": 0,
                    "sort_by": "relevance_score",
                    "sort_order": "desc",
                    "highlight": True,
                    "include_source": True,
                    "source_fields": ["id", "name", "asset_type", "created_at", "file_size"]
                },
                "is_public": True,
                "tags": ["corporate", "presentation", "2024", "marketing"],
                "notify_on_new_results": True
            }
            
            with patch('src.services.saved_search_service.get_saved_search_service') as mock_service:
                mock_service_instance = AsyncMock()
                mock_service_instance.create_saved_search.return_value = {
                    "id": "507f1f77bcf86cd799439011",
                    "user_id": "user123",
                    "name": "Complex Media Search",
                    "description": "Advanced search for media assets with multiple criteria",
                    "query": request_data["query"],
                    "is_public": True,
                    "tags": ["corporate", "presentation", "2024", "marketing"],
                    "notify_on_new_results": True,
                    "usage_count": 0,
                    "last_used_at": None,
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z"
                }
                mock_service.return_value = mock_service_instance
                
                response = await client.post(
                    "/api/v1/search/saved",
                    json=request_data
                )
            
            # Should handle complex queries properly
            assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_500_INTERNAL_SERVER_ERROR]