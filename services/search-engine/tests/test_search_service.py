"""
Tests for the Search Service
"""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime

from src.services.search_service import SearchService
from src.models.schemas import SearchQuery, AdvancedSearchQuery, SearchType, IndexType, SortOrder
from src.core.exceptions import SearchError, InvalidQueryError


@pytest.fixture
def mock_opensearch_client():
    """Mock OpenSearch client"""
    client = AsyncMock()
    return client


@pytest.fixture
def search_service(mock_opensearch_client):
    """Search service with mocked client"""
    return SearchService(mock_opensearch_client)


@pytest.fixture
def sample_search_response():
    """Sample OpenSearch response"""
    return {
        "took": 10,
        "timed_out": False,
        "hits": {
            "total": {"value": 2, "relation": "eq"},
            "max_score": 1.5,
            "hits": [
                {
                    "_index": "mams_assets",
                    "_id": "asset-1",
                    "_score": 1.5,
                    "_source": {
                        "asset_id": "asset-1",
                        "name": "test_video.mp4",
                        "description": "A test video file",
                        "file_path": "/storage/test_video.mp4",
                        "created_at": "2024-01-01T00:00:00Z"
                    },
                    "highlight": {
                        "name": ["<mark>test_video</mark>.mp4"],
                        "description": ["A <mark>test</mark> video file"]
                    }
                },
                {
                    "_index": "mams_metadata",
                    "_id": "asset-2_metadata",
                    "_score": 1.2,
                    "_source": {
                        "asset_id": "asset-2",
                        "title": "Test Document",
                        "keywords": ["test", "document"],
                        "created_at": "2024-01-02T00:00:00Z"
                    },
                    "highlight": {
                        "title": ["<mark>Test</mark> Document"]
                    }
                }
            ]
        },
        "aggregations": {
            "asset_types": {
                "buckets": [
                    {"key": "video", "doc_count": 1},
                    {"key": "document", "doc_count": 1}
                ]
            }
        }
    }


@pytest.mark.asyncio
async def test_basic_search_success(search_service, mock_opensearch_client, sample_search_response):
    """Test successful basic search"""
    # Arrange
    query = SearchQuery(
        query="test",
        size=20,
        from_=0,
        indices=[IndexType.ALL]
    )
    
    mock_opensearch_client.search.return_value = sample_search_response
    
    # Act
    result = await search_service.search(query)
    
    # Assert
    assert result.query == "test"
    assert result.total_hits == 2
    assert result.max_score == 1.5
    assert len(result.hits) == 2
    assert result.hits[0].id == "asset-1"
    assert result.hits[0].score == 1.5
    assert result.hits[0].highlight["name"][0] == "<mark>test_video</mark>.mp4"
    assert result.page == 1
    assert result.per_page == 20
    assert result.total_pages == 1
    assert not result.timed_out
    
    # Verify OpenSearch was called correctly
    mock_opensearch_client.search.assert_called_once()
    call_args = mock_opensearch_client.search.call_args
    assert "mams_assets,mams_metadata,mams_content" in call_args.kwargs["index"]


@pytest.mark.asyncio
async def test_search_with_filters(search_service, mock_opensearch_client):
    """Test search with filters"""
    # Arrange
    query = SearchQuery(
        query="video",
        filters={
            "asset_type": "video",
            "status": ["active", "processing"],
            "file_size": {"gte": 1000000, "lte": 10000000}
        }
    )
    
    mock_opensearch_client.search.return_value = {
        "took": 5,
        "timed_out": False,
        "hits": {
            "total": {"value": 0, "relation": "eq"},
            "max_score": None,
            "hits": []
        }
    }
    
    # Act
    await search_service.search(query)
    
    # Assert
    call_args = mock_opensearch_client.search.call_args
    search_body = call_args.kwargs["body"]
    
    assert "bool" in search_body["query"]
    assert "filter" in search_body["query"]["bool"]
    filters = search_body["query"]["bool"]["filter"]
    
    # Check filters were built correctly
    assert {"term": {"asset_type": "video"}} in filters
    assert {"terms": {"status": ["active", "processing"]}} in filters
    assert {"range": {"file_size": {"gte": 1000000, "lte": 10000000}}} in filters


@pytest.mark.asyncio
async def test_phrase_search(search_service, mock_opensearch_client):
    """Test phrase search type"""
    # Arrange
    query = SearchQuery(
        query="test video",
        search_type=SearchType.PHRASE
    )
    
    mock_opensearch_client.search.return_value = {
        "took": 5,
        "timed_out": False,
        "hits": {"total": {"value": 0}, "hits": []}
    }
    
    # Act
    await search_service.search(query)
    
    # Assert
    call_args = mock_opensearch_client.search.call_args
    search_body = call_args.kwargs["body"]
    
    assert "match_phrase" in search_body["query"]
    assert search_body["query"]["match_phrase"]["_all"]["query"] == "test video"


@pytest.mark.asyncio
async def test_fuzzy_search(search_service, mock_opensearch_client):
    """Test fuzzy search type"""
    # Arrange
    query = SearchQuery(
        query="tset",  # Misspelled "test"
        search_type=SearchType.FUZZY
    )
    
    mock_opensearch_client.search.return_value = {
        "took": 5,
        "timed_out": False,
        "hits": {"total": {"value": 0}, "hits": []}
    }
    
    # Act
    await search_service.search(query)
    
    # Assert
    call_args = mock_opensearch_client.search.call_args
    search_body = call_args.kwargs["body"]
    
    assert "fuzzy" in search_body["query"]
    assert search_body["query"]["fuzzy"]["_all"]["value"] == "tset"
    assert search_body["query"]["fuzzy"]["_all"]["fuzziness"] == "AUTO"


@pytest.mark.asyncio
async def test_search_with_sorting(search_service, mock_opensearch_client):
    """Test search with custom sorting"""
    # Arrange
    query = SearchQuery(
        query="test",
        sort_by="created_at",
        sort_order=SortOrder.ASC
    )
    
    mock_opensearch_client.search.return_value = {
        "took": 5,
        "timed_out": False,
        "hits": {"total": {"value": 0}, "hits": []}
    }
    
    # Act
    await search_service.search(query)
    
    # Assert
    call_args = mock_opensearch_client.search.call_args
    search_body = call_args.kwargs["body"]
    
    assert "sort" in search_body
    assert {"created_at": {"order": "asc"}} in search_body["sort"]


@pytest.mark.asyncio
async def test_search_with_highlighting(search_service, mock_opensearch_client):
    """Test search with highlighting enabled"""
    # Arrange
    query = SearchQuery(
        query="test",
        highlight=True
    )
    
    mock_opensearch_client.search.return_value = {
        "took": 5,
        "timed_out": False,
        "hits": {"total": {"value": 0}, "hits": []}
    }
    
    # Act
    await search_service.search(query)
    
    # Assert
    call_args = mock_opensearch_client.search.call_args
    search_body = call_args.kwargs["body"]
    
    assert "highlight" in search_body
    assert "fields" in search_body["highlight"]
    assert "*" in search_body["highlight"]["fields"]
    assert search_body["highlight"]["fields"]["*"]["pre_tags"] == ["<mark>"]
    assert search_body["highlight"]["fields"]["*"]["post_tags"] == ["</mark>"]


@pytest.mark.asyncio
async def test_search_with_aggregations(search_service, mock_opensearch_client, sample_search_response):
    """Test search with aggregations"""
    # Arrange
    query = SearchQuery(
        query="test",
        include_aggregations=True
    )
    
    mock_opensearch_client.search.return_value = sample_search_response
    
    # Act
    result = await search_service.search(query)
    
    # Assert
    assert result.aggregations is not None
    assert len(result.aggregations) == 1
    assert result.aggregations[0].name == "asset_types"
    assert len(result.aggregations[0].buckets) == 2
    
    # Verify aggregations were requested
    call_args = mock_opensearch_client.search.call_args
    search_body = call_args.kwargs["body"]
    assert "aggs" in search_body
    assert "asset_types" in search_body["aggs"]


@pytest.mark.asyncio
async def test_advanced_search_success(search_service, mock_opensearch_client):
    """Test successful advanced search"""
    # Arrange
    query = AdvancedSearchQuery(
        must=[
            {"field": "asset_type", "operator": "equals", "value": "video"}
        ],
        should=[
            {"field": "name", "operator": "contains", "value": "test"},
            {"field": "description", "operator": "contains", "value": "sample"}
        ],
        must_not=[
            {"field": "status", "operator": "equals", "value": "deleted"}
        ]
    )
    
    mock_opensearch_client.search.return_value = {
        "took": 5,
        "timed_out": False,
        "hits": {"total": {"value": 1}, "hits": []}
    }
    
    # Act
    result = await search_service.advanced_search(query)
    
    # Assert
    assert result.query == "Advanced search"
    assert result.total_hits == 1
    
    # Verify query structure
    call_args = mock_opensearch_client.search.call_args
    search_body = call_args.kwargs["body"]
    
    assert "bool" in search_body["query"]
    bool_query = search_body["query"]["bool"]
    
    assert "must" in bool_query
    assert len(bool_query["must"]) == 1
    assert {"term": {"asset_type": "video"}} in bool_query["must"]
    
    assert "should" in bool_query
    assert len(bool_query["should"]) == 2
    assert {"match": {"name": "test"}} in bool_query["should"]
    
    assert "must_not" in bool_query
    assert len(bool_query["must_not"]) == 1
    assert {"term": {"status": "deleted"}} in bool_query["must_not"]


@pytest.mark.asyncio
async def test_search_specific_indices(search_service, mock_opensearch_client):
    """Test searching specific indices"""
    # Arrange
    query = SearchQuery(
        query="test",
        indices=[IndexType.ASSETS, IndexType.METADATA]
    )
    
    mock_opensearch_client.search.return_value = {
        "took": 5,
        "timed_out": False,
        "hits": {"total": {"value": 0}, "hits": []}
    }
    
    # Act
    await search_service.search(query)
    
    # Assert
    call_args = mock_opensearch_client.search.call_args
    index = call_args.kwargs["index"]
    
    assert "mams_assets" in index
    assert "mams_metadata" in index
    assert "mams_content" not in index


@pytest.mark.asyncio
async def test_search_with_pagination(search_service, mock_opensearch_client):
    """Test search pagination"""
    # Arrange
    query = SearchQuery(
        query="test",
        size=10,
        from_=20  # Page 3 with size 10
    )
    
    mock_opensearch_client.search.return_value = {
        "took": 5,
        "timed_out": False,
        "hits": {
            "total": {"value": 100},
            "hits": []
        }
    }
    
    # Act
    result = await search_service.search(query)
    
    # Assert
    assert result.page == 3  # (20 / 10) + 1
    assert result.per_page == 10
    assert result.total_pages == 10  # 100 / 10
    
    # Verify pagination parameters
    call_args = mock_opensearch_client.search.call_args
    search_body = call_args.kwargs["body"]
    assert search_body["size"] == 10
    assert search_body["from"] == 20


@pytest.mark.asyncio
async def test_search_connection_error(search_service, mock_opensearch_client):
    """Test search with connection error"""
    # Arrange
    query = SearchQuery(query="test")
    mock_opensearch_client.search.side_effect = OpenSearchConnectionError("Connection failed")
    
    # Act & Assert
    with pytest.raises(SearchError) as exc_info:
        await search_service.search(query)
    
    assert "Failed to connect to search service" in str(exc_info.value)


@pytest.mark.asyncio
async def test_search_invalid_query(search_service, mock_opensearch_client):
    """Test search with invalid query"""
    # Arrange
    from opensearchpy.exceptions import RequestError
    
    query = SearchQuery(query="test")
    mock_opensearch_client.search.side_effect = RequestError(400, "parsing_exception", {"error": "Invalid query"})
    
    # Act & Assert
    with pytest.raises(InvalidQueryError) as exc_info:
        await search_service.search(query)
    
    assert "Invalid search query" in str(exc_info.value)


def test_build_condition_operators(search_service):
    """Test different condition operators in advanced search"""
    # Test equals
    condition = search_service._build_condition({"field": "status", "operator": "equals", "value": "active"})
    assert condition == {"term": {"status": "active"}}
    
    # Test not equals
    condition = search_service._build_condition({"field": "status", "operator": "not_equals", "value": "deleted"})
    assert condition == {"bool": {"must_not": {"term": {"status": "deleted"}}}}
    
    # Test contains
    condition = search_service._build_condition({"field": "name", "operator": "contains", "value": "test"})
    assert condition == {"match": {"name": "test"}}
    
    # Test starts_with
    condition = search_service._build_condition({"field": "name", "operator": "starts_with", "value": "test"})
    assert condition == {"prefix": {"name": "test"}}
    
    # Test ends_with
    condition = search_service._build_condition({"field": "name", "operator": "ends_with", "value": "mp4"})
    assert condition == {"wildcard": {"name": "*mp4"}}
    
    # Test range operators
    condition = search_service._build_condition({"field": "size", "operator": "greater_than", "value": 1000})
    assert condition == {"range": {"size": {"gt": 1000}}}
    
    condition = search_service._build_condition({"field": "size", "operator": "less_than", "value": 5000})
    assert condition == {"range": {"size": {"lt": 5000}}}
    
    condition = search_service._build_condition({"field": "size", "operator": "between", "value": {"from": 1000, "to": 5000}})
    assert condition == {"range": {"size": {"gte": 1000, "lte": 5000}}}


def test_get_search_fields(search_service):
    """Test search fields configuration"""
    fields = search_service._get_search_fields()
    
    # Check boosted fields
    assert "name^3" in fields
    assert "title^3" in fields
    assert "description^2" in fields
    
    # Check content fields
    assert "content" in fields
    assert "transcript" in fields
    assert "all_text" in fields
    
    # Check catch-all
    assert "*" in fields