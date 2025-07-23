"""
Tests for filtered search functionality
"""

import pytest
import time
from unittest.mock import AsyncMock, Mock, patch
from opensearchpy import AsyncOpenSearch
from opensearchpy.exceptions import RequestError, ConnectionError as OpenSearchConnectionError

from src.services.search_service import SearchService
from src.services.facet_service import FacetService
from src.services.ranking_service import RankingService
from src.models.schemas import (
    FilteredSearchQuery, FilteredSearchResponse, SearchHit,
    FilterCondition, FilterType, FacetConfig, FacetType, FacetResult, FacetBucket,
    IndexType, SearchType, SortOrder
)
from src.core.exceptions import SearchError, InvalidQueryError


@pytest.fixture
def mock_opensearch_client():
    """Create a mock OpenSearch client"""
    client = AsyncMock(spec=AsyncOpenSearch)
    return client


@pytest.fixture
def mock_ranking_service():
    """Create a mock ranking service"""
    service = AsyncMock(spec=RankingService)
    service.rank_results = AsyncMock(side_effect=lambda hits, query, config: hits)
    return service


@pytest.fixture
def search_service(mock_opensearch_client, mock_ranking_service):
    """Create a SearchService instance"""
    return SearchService(mock_opensearch_client, mock_ranking_service)


class TestFilteredSearch:
    """Test filtered search functionality"""
    
    @pytest.mark.asyncio
    async def test_basic_filtered_search(self, search_service, mock_opensearch_client):
        """Test basic filtered search"""
        # Prepare query
        query = FilteredSearchQuery(
            query="test video",
            filters=[
                FilterCondition(field="asset_type", type=FilterType.TERM, value="video")
            ],
            size=10,
            from_=0
        )
        
        # Mock OpenSearch response
        mock_response = {
            "hits": {
                "total": {"value": 5},
                "max_score": 1.5,
                "hits": [
                    {
                        "_id": "1",
                        "_index": "assets",
                        "_score": 1.5,
                        "_source": {"name": "test_video.mp4", "asset_type": "video"},
                        "highlight": {"name": ["<mark>test</mark>_video.mp4"]}
                    }
                ]
            },
            "took": 50,
            "timed_out": False
        }
        
        mock_opensearch_client.search.return_value = mock_response
        
        # Execute search
        result = await search_service.filtered_search(query)
        
        # Verify results
        assert isinstance(result, FilteredSearchResponse)
        assert result.total_hits == 5
        assert len(result.hits) == 1
        assert result.hits[0].id == "1"
        assert result.hits[0].source["asset_type"] == "video"
        assert result.took == 50
        
        # Verify search was called correctly
        mock_opensearch_client.search.assert_called_once()
        call_args = mock_opensearch_client.search.call_args
        assert "assets_index,metadata_index,content_index" in call_args[1]["index"]
        
        # Check query structure
        body = call_args[1]["body"]
        assert "query" in body
        assert "bool" in body["query"]
        assert "filter" in body["query"]["bool"]
    
    @pytest.mark.asyncio
    async def test_filtered_search_with_facets(self, search_service, mock_opensearch_client):
        """Test filtered search with facets"""
        # Prepare query with facets
        query = FilteredSearchQuery(
            query="marketing",
            facets=[
                FacetConfig(name="types", field="asset_type", type=FacetType.TERMS, size=5),
                FacetConfig(name="sizes", field="file_size", type=FacetType.RANGE, ranges=[
                    {"to": 1000000, "key": "small"},
                    {"from": 1000000, "key": "large"}
                ])
            ]
        )
        
        # Mock response with aggregations
        mock_response = {
            "hits": {
                "total": {"value": 10},
                "max_score": 2.0,
                "hits": []
            },
            "aggregations": {
                "types": {
                    "buckets": [
                        {"key": "video", "doc_count": 6},
                        {"key": "image", "doc_count": 4}
                    ]
                },
                "sizes": {
                    "buckets": [
                        {"key": "small", "to": 1000000, "doc_count": 3},
                        {"key": "large", "from": 1000000, "doc_count": 7}
                    ]
                }
            },
            "took": 75,
            "timed_out": False
        }
        
        mock_opensearch_client.search.return_value = mock_response
        
        # Execute search
        result = await search_service.filtered_search(query)
        
        # Verify facets
        assert result.facets is not None
        assert len(result.facets) == 2
        
        # Check terms facet
        types_facet = next(f for f in result.facets if f.name == "types")
        assert types_facet.type == FacetType.TERMS
        assert len(types_facet.buckets) == 2
        assert types_facet.buckets[0].key == "video"
        assert types_facet.buckets[0].doc_count == 6
        
        # Check range facet
        sizes_facet = next(f for f in result.facets if f.name == "sizes")
        assert sizes_facet.type == FacetType.RANGE
        assert len(sizes_facet.buckets) == 2
        assert sizes_facet.buckets[0].key == "small"
        assert sizes_facet.buckets[0].to == 1000000
    
    @pytest.mark.asyncio
    async def test_filtered_search_with_post_filters(self, search_service, mock_opensearch_client):
        """Test filtered search with post-filters"""
        # Prepare query with both filters and post-filters
        query = FilteredSearchQuery(
            query="document",
            filters=[
                FilterCondition(field="status", type=FilterType.TERM, value="published")
            ],
            post_filters=[
                FilterCondition(field="department", type=FilterType.TERM, value="marketing")
            ],
            facets=[
                FacetConfig(name="departments", field="department", type=FacetType.TERMS)
            ]
        )
        
        mock_response = {
            "hits": {"total": {"value": 15}, "max_score": 1.0, "hits": []},
            "aggregations": {
                "departments": {
                    "buckets": [
                        {"key": "marketing", "doc_count": 20},
                        {"key": "sales", "doc_count": 15},
                        {"key": "engineering", "doc_count": 10}
                    ]
                }
            },
            "took": 60,
            "timed_out": False
        }
        
        mock_opensearch_client.search.return_value = mock_response
        
        # Execute search
        result = await search_service.filtered_search(query)
        
        # Verify post-filter was applied
        call_args = mock_opensearch_client.search.call_args[1]["body"]
        assert "post_filter" in call_args
        assert "bool" in call_args["post_filter"]
        
        # Facets should show all departments (not affected by post-filter)
        dept_facet = result.facets[0]
        assert dept_facet.buckets[0].doc_count == 20  # Marketing has 20 in total
    
    @pytest.mark.asyncio
    async def test_filtered_search_with_multiple_filter_types(self, search_service, mock_opensearch_client):
        """Test filtered search with various filter types"""
        query = FilteredSearchQuery(
            query="test",
            filters=[
                FilterCondition(field="status", type=FilterType.TERM, value="active"),
                FilterCondition(field="tags", type=FilterType.TERMS, value=["video", "tutorial"]),
                FilterCondition(field="duration", type=FilterType.RANGE, value={"gte": 60, "lte": 300}),
                FilterCondition(field="thumbnail", type=FilterType.EXISTS, value=True),
                FilterCondition(field="name", type=FilterType.PREFIX, value="VID_"),
                FilterCondition(field="description", type=FilterType.WILDCARD, value="*tutorial*")
            ]
        )
        
        mock_response = {
            "hits": {"total": {"value": 3}, "max_score": 2.5, "hits": []},
            "took": 100,
            "timed_out": False
        }
        
        mock_opensearch_client.search.return_value = mock_response
        
        # Execute search
        result = await search_service.filtered_search(query)
        
        # Verify all filters were applied
        call_args = mock_opensearch_client.search.call_args[1]["body"]
        filters = call_args["query"]["bool"]["filter"]
        assert len(filters) == 6
        
        # Check each filter type
        filter_types = [list(f.keys())[0] for f in filters]
        assert "term" in filter_types
        assert "terms" in filter_types
        assert "range" in filter_types
        assert "exists" in filter_types
        assert "prefix" in filter_types
        assert "wildcard" in filter_types
    
    @pytest.mark.asyncio
    async def test_filtered_search_with_nested_filters(self, search_service, mock_opensearch_client):
        """Test filtered search with nested filters"""
        query = FilteredSearchQuery(
            query="nested test",
            filters=[
                FilterCondition(
                    field="metadata.tags.name",
                    type=FilterType.TERM,
                    value="important",
                    nested_path="metadata.tags"
                )
            ]
        )
        
        mock_response = {
            "hits": {"total": {"value": 2}, "max_score": 1.8, "hits": []},
            "took": 80,
            "timed_out": False
        }
        
        mock_opensearch_client.search.return_value = mock_response
        
        # Execute search
        result = await search_service.filtered_search(query)
        
        # Verify nested filter structure
        call_args = mock_opensearch_client.search.call_args[1]["body"]
        filters = call_args["query"]["bool"]["filter"]
        assert len(filters) == 1
        assert "nested" in filters[0]
        assert filters[0]["nested"]["path"] == "metadata.tags"
    
    @pytest.mark.asyncio
    async def test_filtered_search_with_sorting(self, search_service, mock_opensearch_client):
        """Test filtered search with custom sorting"""
        query = FilteredSearchQuery(
            query="test",
            sort_by="created_at",
            sort_order=SortOrder.DESC
        )
        
        mock_response = {
            "hits": {"total": {"value": 10}, "max_score": None, "hits": []},
            "took": 45,
            "timed_out": False
        }
        
        mock_opensearch_client.search.return_value = mock_response
        
        # Execute search
        result = await search_service.filtered_search(query)
        
        # Verify sorting was applied
        call_args = mock_opensearch_client.search.call_args[1]["body"]
        assert "sort" in call_args
        assert {"created_at": {"order": "desc"}} in call_args["sort"]
    
    @pytest.mark.asyncio
    async def test_filtered_search_with_source_filtering(self, search_service, mock_opensearch_client):
        """Test filtered search with source field filtering"""
        query = FilteredSearchQuery(
            query="test",
            include_source=True,
            source_fields=["id", "name", "asset_type"]
        )
        
        mock_response = {
            "hits": {
                "total": {"value": 1},
                "max_score": 1.0,
                "hits": [{
                    "_id": "1",
                    "_index": "assets",
                    "_score": 1.0,
                    "_source": {"id": "1", "name": "test.mp4", "asset_type": "video"}
                }]
            },
            "took": 30,
            "timed_out": False
        }
        
        mock_opensearch_client.search.return_value = mock_response
        
        # Execute search
        result = await search_service.filtered_search(query)
        
        # Verify source filtering
        call_args = mock_opensearch_client.search.call_args[1]["body"]
        assert "_source" in call_args
        assert call_args["_source"] == ["id", "name", "asset_type"]
    
    @pytest.mark.asyncio
    async def test_filtered_search_without_source(self, search_service, mock_opensearch_client):
        """Test filtered search without source data"""
        query = FilteredSearchQuery(
            query="test",
            include_source=False
        )
        
        mock_response = {
            "hits": {
                "total": {"value": 1},
                "max_score": 1.0,
                "hits": [{
                    "_id": "1",
                    "_index": "assets",
                    "_score": 1.0,
                    "_source": {"should": "be", "ignored": True}
                }]
            },
            "took": 25,
            "timed_out": False
        }
        
        mock_opensearch_client.search.return_value = mock_response
        
        # Execute search
        result = await search_service.filtered_search(query)
        
        # Verify source was excluded
        call_args = mock_opensearch_client.search.call_args[1]["body"]
        assert "_source" in call_args
        assert call_args["_source"] is False
        
        # Result should have empty source
        assert result.hits[0].source == {}
    
    @pytest.mark.asyncio
    async def test_filtered_search_with_default_facets(self, search_service, mock_opensearch_client):
        """Test filtered search with default facets when none specified"""
        query = FilteredSearchQuery(
            query="test",
            facets=None  # Should trigger default facets
        )
        
        mock_response = {
            "hits": {"total": {"value": 5}, "max_score": 1.0, "hits": []},
            "aggregations": {
                "asset_types": {"buckets": [{"key": "video", "doc_count": 3}]},
                "file_extensions": {"buckets": [{"key": "mp4", "doc_count": 2}]},
                "file_size_ranges": {"buckets": []},
                "created_dates": {"buckets": []},
                "mime_types": {"buckets": []},
                "status": {"buckets": []}
            },
            "took": 55,
            "timed_out": False
        }
        
        mock_opensearch_client.search.return_value = mock_response
        
        # Execute search
        result = await search_service.filtered_search(query)
        
        # Should have default facets
        assert result.facets is not None
        assert len(result.facets) > 0
        
        # Check that default facets were requested
        call_args = mock_opensearch_client.search.call_args[1]["body"]
        assert "aggs" in call_args
        assert "asset_types" in call_args["aggs"]
    
    @pytest.mark.asyncio
    async def test_filtered_search_with_highlighting(self, search_service, mock_opensearch_client):
        """Test filtered search with highlighting enabled"""
        query = FilteredSearchQuery(
            query="test video",
            highlight=True
        )
        
        mock_response = {
            "hits": {
                "total": {"value": 1},
                "max_score": 2.0,
                "hits": [{
                    "_id": "1",
                    "_index": "assets",
                    "_score": 2.0,
                    "_source": {"name": "test_video.mp4"},
                    "highlight": {
                        "name": ["<mark>test</mark>_<mark>video</mark>.mp4"],
                        "description": ["This is a <mark>test</mark> <mark>video</mark>"]
                    }
                }]
            },
            "took": 40,
            "timed_out": False
        }
        
        mock_opensearch_client.search.return_value = mock_response
        
        # Execute search
        result = await search_service.filtered_search(query)
        
        # Verify highlighting
        assert result.hits[0].highlight is not None
        assert "name" in result.hits[0].highlight
        assert "<mark>test</mark>" in result.hits[0].highlight["name"][0]
    
    @pytest.mark.asyncio
    async def test_filtered_search_with_pagination(self, search_service, mock_opensearch_client):
        """Test filtered search with pagination"""
        query = FilteredSearchQuery(
            query="test",
            size=20,
            from_=40  # Page 3 with size 20
        )
        
        mock_response = {
            "hits": {"total": {"value": 100}, "max_score": 1.5, "hits": []},
            "took": 35,
            "timed_out": False
        }
        
        mock_opensearch_client.search.return_value = mock_response
        
        # Execute search
        result = await search_service.filtered_search(query)
        
        # Verify pagination
        assert result.page == 3  # (40 / 20) + 1
        assert result.per_page == 20
        assert result.total_pages == 5  # 100 / 20
        assert result.total_hits == 100
    
    @pytest.mark.asyncio
    async def test_filtered_search_with_timeout(self, search_service, mock_opensearch_client):
        """Test filtered search with custom timeout"""
        query = FilteredSearchQuery(
            query="test",
            timeout=5  # 5 seconds
        )
        
        mock_response = {
            "hits": {"total": {"value": 10}, "max_score": 1.0, "hits": []},
            "took": 50,
            "timed_out": False
        }
        
        mock_opensearch_client.search.return_value = mock_response
        
        # Execute search
        await search_service.filtered_search(query)
        
        # Verify timeout was set
        call_args = mock_opensearch_client.search.call_args
        assert call_args[1]["timeout"] == "5s"
    
    @pytest.mark.asyncio
    async def test_filtered_search_connection_error(self, search_service, mock_opensearch_client):
        """Test filtered search with connection error"""
        query = FilteredSearchQuery(query="test")
        
        # Simulate connection error
        mock_opensearch_client.search.side_effect = OpenSearchConnectionError("Connection failed")
        
        # Should raise SearchError
        with pytest.raises(SearchError) as exc_info:
            await search_service.filtered_search(query)
        
        assert "Failed to connect to search service" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_filtered_search_invalid_query_error(self, search_service, mock_opensearch_client):
        """Test filtered search with invalid query error"""
        query = FilteredSearchQuery(
            query="test",
            filters=[
                FilterCondition(field="invalid]field", type=FilterType.TERM, value="test")
            ]
        )
        
        # Simulate query parsing error
        mock_opensearch_client.search.side_effect = RequestError(
            400, "parsing_exception", {"error": "Invalid field name"}
        )
        
        # Should raise InvalidQueryError
        with pytest.raises(InvalidQueryError) as exc_info:
            await search_service.filtered_search(query)
        
        assert "Invalid search query" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_filtered_search_with_ranking(self, search_service, mock_opensearch_client, mock_ranking_service):
        """Test filtered search with custom ranking"""
        query = FilteredSearchQuery(
            query="test",
            sort_by=None  # No explicit sort, so ranking should be applied
        )
        
        # Mock response with multiple hits
        mock_response = {
            "hits": {
                "total": {"value": 3},
                "max_score": 2.0,
                "hits": [
                    {"_id": "1", "_index": "assets", "_score": 1.0, "_source": {"name": "doc1"}},
                    {"_id": "2", "_index": "assets", "_score": 1.5, "_source": {"name": "doc2"}},
                    {"_id": "3", "_index": "assets", "_score": 2.0, "_source": {"name": "doc3"}}
                ]
            },
            "took": 45,
            "timed_out": False
        }
        
        mock_opensearch_client.search.return_value = mock_response
        
        # Mock ranking service to reverse order
        async def mock_rank(hits, query, config):
            return list(reversed(hits))
        
        mock_ranking_service.rank_results.side_effect = mock_rank
        
        # Execute search
        result = await search_service.filtered_search(query)
        
        # Verify ranking was applied
        mock_ranking_service.rank_results.assert_called_once()
        assert result.hits[0].id == "3"  # Reversed order
        assert result.hits[1].id == "2"
        assert result.hits[2].id == "1"