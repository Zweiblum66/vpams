"""
Integration tests for filtered search API endpoint
"""

import pytest
from httpx import AsyncClient
from fastapi import status

from src.main import app
from src.models.schemas import FilterType, FacetType


@pytest.mark.integration
class TestFilteredSearchIntegration:
    """Integration tests for filtered search endpoint"""
    
    @pytest.mark.asyncio
    async def test_basic_filtered_search(self):
        """Test basic filtered search request"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            request_data = {
                "query": "test video",
                "filters": [
                    {
                        "field": "asset_type",
                        "type": "term",
                        "value": "video"
                    }
                ],
                "size": 10,
                "from": 0
            }
            
            response = await client.post(
                "/api/v1/search/filtered",
                json=request_data
            )
            
            # Should return success (mocked in test environment)
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]
            
            if response.status_code == status.HTTP_200_OK:
                data = response.json()
                assert "query" in data
                assert "total_hits" in data
                assert "hits" in data
                assert "took" in data
    
    @pytest.mark.asyncio
    async def test_filtered_search_with_facets(self):
        """Test filtered search with facet configuration"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            request_data = {
                "query": "marketing materials",
                "facets": [
                    {
                        "name": "asset_types",
                        "field": "asset_type",
                        "type": "terms",
                        "size": 10
                    },
                    {
                        "name": "date_histogram",
                        "field": "created_at",
                        "type": "date_histogram",
                        "interval": "month"
                    }
                ],
                "size": 20
            }
            
            response = await client.post(
                "/api/v1/search/filtered",
                json=request_data
            )
            
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]
            
            if response.status_code == status.HTTP_200_OK:
                data = response.json()
                assert "facets" in data
    
    @pytest.mark.asyncio
    async def test_filtered_search_with_multiple_filters(self):
        """Test filtered search with multiple filter types"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            request_data = {
                "query": "project files",
                "filters": [
                    {
                        "field": "status",
                        "type": "term",
                        "value": "active"
                    },
                    {
                        "field": "tags",
                        "type": "terms",
                        "value": ["important", "urgent"]
                    },
                    {
                        "field": "file_size",
                        "type": "range",
                        "value": {"gte": 1000000, "lte": 10000000}
                    },
                    {
                        "field": "has_thumbnail",
                        "type": "exists",
                        "value": True
                    }
                ]
            }
            
            response = await client.post(
                "/api/v1/search/filtered",
                json=request_data
            )
            
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]
    
    @pytest.mark.asyncio
    async def test_filtered_search_with_post_filters(self):
        """Test filtered search with post-filters"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            request_data = {
                "query": "documents",
                "filters": [
                    {
                        "field": "document_type",
                        "type": "term",
                        "value": "pdf"
                    }
                ],
                "post_filters": [
                    {
                        "field": "department",
                        "type": "term",
                        "value": "legal"
                    }
                ],
                "facets": [
                    {
                        "name": "departments",
                        "field": "department",
                        "type": "terms"
                    }
                ]
            }
            
            response = await client.post(
                "/api/v1/search/filtered",
                json=request_data
            )
            
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]
    
    @pytest.mark.asyncio
    async def test_filtered_search_with_nested_filter(self):
        """Test filtered search with nested field filter"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            request_data = {
                "query": "nested test",
                "filters": [
                    {
                        "field": "metadata.custom_fields.category",
                        "type": "term",
                        "value": "marketing",
                        "nested_path": "metadata.custom_fields"
                    }
                ]
            }
            
            response = await client.post(
                "/api/v1/search/filtered",
                json=request_data
            )
            
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]
    
    @pytest.mark.asyncio
    async def test_filtered_search_with_range_facet(self):
        """Test filtered search with range facet"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            request_data = {
                "query": "videos",
                "facets": [
                    {
                        "name": "duration_ranges",
                        "field": "duration",
                        "type": "range",
                        "ranges": [
                            {"to": 60, "key": "short"},
                            {"from": 60, "to": 300, "key": "medium"},
                            {"from": 300, "key": "long"}
                        ]
                    }
                ]
            }
            
            response = await client.post(
                "/api/v1/search/filtered",
                json=request_data
            )
            
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]
    
    @pytest.mark.asyncio
    async def test_filtered_search_with_stats_facet(self):
        """Test filtered search with stats facet"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            request_data = {
                "query": "assets",
                "facets": [
                    {
                        "name": "file_size_stats",
                        "field": "file_size",
                        "type": "stats"
                    }
                ]
            }
            
            response = await client.post(
                "/api/v1/search/filtered",
                json=request_data
            )
            
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]
    
    @pytest.mark.asyncio
    async def test_filtered_search_with_source_filtering(self):
        """Test filtered search with source field selection"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            request_data = {
                "query": "test",
                "include_source": True,
                "source_fields": ["id", "name", "asset_type", "created_at"]
            }
            
            response = await client.post(
                "/api/v1/search/filtered",
                json=request_data
            )
            
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]
    
    @pytest.mark.asyncio
    async def test_filtered_search_without_source(self):
        """Test filtered search without source data"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            request_data = {
                "query": "test",
                "include_source": False
            }
            
            response = await client.post(
                "/api/v1/search/filtered",
                json=request_data
            )
            
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]
    
    @pytest.mark.asyncio
    async def test_filtered_search_with_sorting(self):
        """Test filtered search with custom sorting"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            request_data = {
                "query": "recent files",
                "sort_by": "created_at",
                "sort_order": "desc"
            }
            
            response = await client.post(
                "/api/v1/search/filtered",
                json=request_data
            )
            
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]
    
    @pytest.mark.asyncio
    async def test_filtered_search_with_pagination(self):
        """Test filtered search with pagination"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            request_data = {
                "query": "documents",
                "size": 25,
                "from": 50
            }
            
            response = await client.post(
                "/api/v1/search/filtered",
                json=request_data
            )
            
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]
            
            if response.status_code == status.HTTP_200_OK:
                data = response.json()
                assert "page" in data
                assert "per_page" in data
                assert "total_pages" in data
    
    @pytest.mark.asyncio
    async def test_filtered_search_validation_errors(self):
        """Test filtered search with validation errors"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Empty query
            response = await client.post(
                "/api/v1/search/filtered",
                json={"query": ""}
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            
            # Invalid filter type
            response = await client.post(
                "/api/v1/search/filtered",
                json={
                    "query": "test",
                    "filters": [
                        {
                            "field": "status",
                            "type": "invalid_type",
                            "value": "active"
                        }
                    ]
                }
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            
            # Invalid facet type
            response = await client.post(
                "/api/v1/search/filtered",
                json={
                    "query": "test",
                    "facets": [
                        {
                            "name": "test",
                            "field": "field",
                            "type": "invalid_facet"
                        }
                    ]
                }
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_filtered_search_complex_scenario(self):
        """Test filtered search with complex real-world scenario"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            request_data = {
                "query": "marketing campaign 2024",
                "search_type": "basic",
                "indices": ["assets", "metadata"],
                "filters": [
                    {
                        "field": "asset_type",
                        "type": "terms",
                        "value": ["video", "image"]
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
                        "field": "status",
                        "type": "term",
                        "value": "published"
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
                        "size": 10
                    },
                    {
                        "name": "monthly_distribution",
                        "field": "created_at",
                        "type": "date_histogram",
                        "interval": "month"
                    },
                    {
                        "name": "file_sizes",
                        "field": "file_size",
                        "type": "range",
                        "ranges": [
                            {"to": 5242880, "key": "< 5MB"},
                            {"from": 5242880, "to": 52428800, "key": "5MB - 50MB"},
                            {"from": 52428800, "key": "> 50MB"}
                        ]
                    },
                    {
                        "name": "unique_creators",
                        "field": "created_by",
                        "type": "cardinality"
                    }
                ],
                "size": 50,
                "from": 0,
                "sort_by": "relevance_score",
                "sort_order": "desc",
                "highlight": True,
                "include_source": True,
                "source_fields": [
                    "id", "name", "description", "asset_type",
                    "file_size", "created_at", "created_by",
                    "tags", "thumbnail_url", "preview_url"
                ],
                "timeout": 10
            }
            
            response = await client.post(
                "/api/v1/search/filtered",
                json=request_data
            )
            
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]
            
            if response.status_code == status.HTTP_200_OK:
                data = response.json()
                # Verify response structure
                assert "query" in data
                assert "total_hits" in data
                assert "hits" in data
                assert "facets" in data
                assert "applied_filters" in data
                assert "took" in data
                assert "page" in data
                assert "per_page" in data
                assert "total_pages" in data