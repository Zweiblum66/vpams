"""
Tests for Metadata Field Search functionality
"""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime

from src.services.search_service import SearchService
from src.models.schemas import MetadataFieldSearchQuery, SortOrder, IndexType
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
def sample_metadata_response():
    """Sample OpenSearch response for metadata search"""
    return {
        "took": 15,
        "timed_out": False,
        "hits": {
            "total": {"value": 3, "relation": "eq"},
            "max_score": 2.5,
            "hits": [
                {
                    "_index": "mams_metadata",
                    "_id": "asset-1_metadata",
                    "_score": 2.5,
                    "_source": {
                        "asset_id": "asset-1",
                        "title": "Test Video Production",
                        "description": "A sample video for testing",
                        "keywords": ["test", "video", "sample"],
                        "creator": "John Doe",
                        "subject": "Testing",
                        "format": "MP4",
                        "language": "en",
                        "created_at": "2024-01-01T00:00:00Z"
                    },
                    "highlight": {
                        "title": ["<mark>Test</mark> <mark>Video</mark> Production"],
                        "keywords": ["<mark>test</mark>", "<mark>video</mark>"]
                    }
                },
                {
                    "_index": "mams_metadata",
                    "_id": "asset-2_metadata",
                    "_score": 2.0,
                    "_source": {
                        "asset_id": "asset-2",
                        "title": "Video Tutorial",
                        "description": "Educational video content",
                        "keywords": ["tutorial", "video", "education"],
                        "creator": "Jane Smith",
                        "subject": "Education",
                        "format": "MOV",
                        "language": "en",
                        "created_at": "2024-01-02T00:00:00Z"
                    },
                    "highlight": {
                        "title": ["<mark>Video</mark> Tutorial"],
                        "keywords": ["<mark>video</mark>"]
                    }
                },
                {
                    "_index": "mams_metadata",
                    "_id": "asset-3_metadata",
                    "_score": 1.8,
                    "_source": {
                        "asset_id": "asset-3",
                        "title": "Test Document",
                        "description": "A test document",
                        "keywords": ["test", "document"],
                        "creator": "Admin",
                        "subject": "Documentation",
                        "format": "PDF",
                        "language": "en",
                        "created_at": "2024-01-03T00:00:00Z"
                    },
                    "highlight": {
                        "keywords": ["<mark>test</mark>"]
                    }
                }
            ]
        },
        "aggregations": {
            "file_formats": {
                "buckets": [
                    {"key": "MP4", "doc_count": 1},
                    {"key": "MOV", "doc_count": 1},
                    {"key": "PDF", "doc_count": 1}
                ]
            },
            "creators": {
                "buckets": [
                    {"key": "John Doe", "doc_count": 1},
                    {"key": "Jane Smith", "doc_count": 1},
                    {"key": "Admin", "doc_count": 1}
                ]
            }
        }
    }


@pytest.mark.asyncio
async def test_metadata_field_search_basic(search_service, mock_opensearch_client, sample_metadata_response):
    """Test basic metadata field search with AND operator"""
    # Arrange
    query = MetadataFieldSearchQuery(
        field_queries=[
            {"field": "title", "value": "video"},
            {"field": "keywords", "value": "test"}
        ],
        operator="AND",
        size=20,
        from_=0
    )
    
    mock_opensearch_client.search.return_value = sample_metadata_response
    
    # Act
    result = await search_service.metadata_field_search(query)
    
    # Assert
    assert result.total_hits == 3
    assert result.max_score == 2.5
    assert len(result.hits) == 3
    assert result.hits[0].id == "asset-1_metadata"
    assert result.hits[0].source["title"] == "Test Video Production"
    assert result.page == 1
    assert result.per_page == 20
    
    # Verify OpenSearch was called correctly
    mock_opensearch_client.search.assert_called_once()
    call_args = mock_opensearch_client.search.call_args
    search_body = call_args.kwargs["body"]
    
    # Check query structure
    assert "bool" in search_body["query"]
    assert "must" in search_body["query"]["bool"]
    assert len(search_body["query"]["bool"]["must"]) == 2


@pytest.mark.asyncio
async def test_metadata_field_search_or_operator(search_service, mock_opensearch_client):
    """Test metadata field search with OR operator"""
    # Arrange
    query = MetadataFieldSearchQuery(
        field_queries=[
            {"field": "format", "value": "MP4"},
            {"field": "format", "value": "MOV"}
        ],
        operator="OR"
    )
    
    mock_opensearch_client.search.return_value = {
        "took": 5,
        "timed_out": False,
        "hits": {"total": {"value": 2}, "hits": []}
    }
    
    # Act
    await search_service.metadata_field_search(query)
    
    # Assert
    call_args = mock_opensearch_client.search.call_args
    search_body = call_args.kwargs["body"]
    
    assert "bool" in search_body["query"]
    assert "should" in search_body["query"]["bool"]
    assert len(search_body["query"]["bool"]["should"]) == 2
    assert search_body["query"]["bool"]["minimum_should_match"] == 1


@pytest.mark.asyncio
async def test_metadata_field_search_with_fuzzy(search_service, mock_opensearch_client):
    """Test metadata field search with fuzzy matching"""
    # Arrange
    query = MetadataFieldSearchQuery(
        field_queries=[
            {"field": "title", "value": "vido"},  # Typo: "video"
            {"field": "creator", "value": "Jon"}   # Typo: "John"
        ],
        operator="AND",
        fuzzy=True
    )
    
    mock_opensearch_client.search.return_value = {
        "took": 10,
        "timed_out": False,
        "hits": {"total": {"value": 1}, "hits": []}
    }
    
    # Act
    await search_service.metadata_field_search(query)
    
    # Assert
    call_args = mock_opensearch_client.search.call_args
    search_body = call_args.kwargs["body"]
    
    # Check fuzzy queries were used
    must_queries = search_body["query"]["bool"]["must"]
    assert all("fuzzy" in q for q in must_queries)
    assert must_queries[0]["fuzzy"]["title"]["value"] == "vido"
    assert must_queries[0]["fuzzy"]["title"]["fuzziness"] == "AUTO"
    assert must_queries[1]["fuzzy"]["creator"]["value"] == "Jon"


@pytest.mark.asyncio
async def test_metadata_field_search_with_boosting(search_service, mock_opensearch_client):
    """Test metadata field search with field boosting"""
    # Arrange
    query = MetadataFieldSearchQuery(
        field_queries=[
            {"field": "title", "value": "video"},
            {"field": "description", "value": "sample"}
        ],
        operator="AND",
        boost_fields={"title": 2.0, "description": 1.5}
    )
    
    mock_opensearch_client.search.return_value = {
        "took": 5,
        "timed_out": False,
        "hits": {"total": {"value": 0}, "hits": []}
    }
    
    # Act
    await search_service.metadata_field_search(query)
    
    # Assert
    call_args = mock_opensearch_client.search.call_args
    search_body = call_args.kwargs["body"]
    
    must_queries = search_body["query"]["bool"]["must"]
    assert must_queries[0]["match"]["title"]["boost"] == 2.0
    assert must_queries[1]["match"]["description"]["boost"] == 1.5


@pytest.mark.asyncio
async def test_metadata_field_search_keyword_fields(search_service, mock_opensearch_client):
    """Test metadata field search with keyword fields"""
    # Arrange
    query = MetadataFieldSearchQuery(
        field_queries=[
            {"field": "creator.keyword", "value": "John Doe"},
            {"field": "subject.keyword", "value": "Testing"}
        ],
        operator="AND"
    )
    
    mock_opensearch_client.search.return_value = {
        "took": 5,
        "timed_out": False,
        "hits": {"total": {"value": 1}, "hits": []}
    }
    
    # Act
    await search_service.metadata_field_search(query)
    
    # Assert
    call_args = mock_opensearch_client.search.call_args
    search_body = call_args.kwargs["body"]
    
    must_queries = search_body["query"]["bool"]["must"]
    # Keyword fields should use term queries for exact matching
    assert all("term" in q for q in must_queries)
    assert must_queries[0]["term"]["creator.keyword"] == "John Doe"
    assert must_queries[1]["term"]["subject.keyword"] == "Testing"


@pytest.mark.asyncio
async def test_metadata_field_search_with_filters(search_service, mock_opensearch_client):
    """Test metadata field search with additional filters"""
    # Arrange
    query = MetadataFieldSearchQuery(
        field_queries=[
            {"field": "title", "value": "video"}
        ],
        filters={
            "language": "en",
            "format": ["MP4", "MOV"],
            "date_created": {"gte": "2024-01-01", "lte": "2024-12-31"}
        }
    )
    
    mock_opensearch_client.search.return_value = {
        "took": 5,
        "timed_out": False,
        "hits": {"total": {"value": 0}, "hits": []}
    }
    
    # Act
    await search_service.metadata_field_search(query)
    
    # Assert
    call_args = mock_opensearch_client.search.call_args
    search_body = call_args.kwargs["body"]
    
    assert "filter" in search_body["query"]["bool"]
    filters = search_body["query"]["bool"]["filter"]
    
    # Check filters were built correctly
    assert {"term": {"language": "en"}} in filters
    assert {"terms": {"format": ["MP4", "MOV"]}} in filters
    assert {"range": {"date_created": {"gte": "2024-01-01", "lte": "2024-12-31"}}} in filters


@pytest.mark.asyncio
async def test_metadata_field_search_with_aggregations(search_service, mock_opensearch_client, sample_metadata_response):
    """Test metadata field search with aggregations enabled"""
    # Arrange
    query = MetadataFieldSearchQuery(
        field_queries=[
            {"field": "keywords", "value": "video"}
        ],
        include_aggregations=True
    )
    
    mock_opensearch_client.search.return_value = sample_metadata_response
    
    # Act
    result = await search_service.metadata_field_search(query)
    
    # Assert
    assert result.aggregations is not None
    assert len(result.aggregations) == 2
    assert result.aggregations[0].name == "file_formats"
    assert len(result.aggregations[0].buckets) == 3
    
    # Verify aggregations were requested
    call_args = mock_opensearch_client.search.call_args
    search_body = call_args.kwargs["body"]
    assert "aggs" in search_body


@pytest.mark.asyncio
async def test_metadata_field_search_sorting(search_service, mock_opensearch_client):
    """Test metadata field search with custom sorting"""
    # Arrange
    query = MetadataFieldSearchQuery(
        field_queries=[
            {"field": "subject", "value": "testing"}
        ],
        sort_by="created_at",
        sort_order=SortOrder.DESC
    )
    
    mock_opensearch_client.search.return_value = {
        "took": 5,
        "timed_out": False,
        "hits": {"total": {"value": 0}, "hits": []}
    }
    
    # Act
    await search_service.metadata_field_search(query)
    
    # Assert
    call_args = mock_opensearch_client.search.call_args
    search_body = call_args.kwargs["body"]
    
    assert "sort" in search_body
    assert {"created_at": {"order": "desc"}} in search_body["sort"]


@pytest.mark.asyncio
async def test_metadata_field_search_highlighting(search_service, mock_opensearch_client, sample_metadata_response):
    """Test metadata field search with highlighting"""
    # Arrange
    query = MetadataFieldSearchQuery(
        field_queries=[
            {"field": "title", "value": "video"},
            {"field": "keywords", "value": "test"}
        ],
        highlight=True
    )
    
    mock_opensearch_client.search.return_value = sample_metadata_response
    
    # Act
    result = await search_service.metadata_field_search(query)
    
    # Assert
    assert result.hits[0].highlight is not None
    assert "title" in result.hits[0].highlight
    assert "keywords" in result.hits[0].highlight
    
    # Verify highlighting was requested
    call_args = mock_opensearch_client.search.call_args
    search_body = call_args.kwargs["body"]
    assert "highlight" in search_body
    assert "title" in search_body["highlight"]["fields"]
    assert "keywords" in search_body["highlight"]["fields"]


@pytest.mark.asyncio
async def test_metadata_field_search_specific_indices(search_service, mock_opensearch_client):
    """Test metadata field search on specific indices"""
    # Arrange
    query = MetadataFieldSearchQuery(
        field_queries=[
            {"field": "title", "value": "test"}
        ],
        indices=[IndexType.METADATA, IndexType.CONTENT]
    )
    
    mock_opensearch_client.search.return_value = {
        "took": 5,
        "timed_out": False,
        "hits": {"total": {"value": 0}, "hits": []}
    }
    
    # Act
    await search_service.metadata_field_search(query)
    
    # Assert
    call_args = mock_opensearch_client.search.call_args
    index = call_args.kwargs["index"]
    
    assert "mams_metadata" in index
    assert "mams_content" in index
    assert "mams_assets" not in index


@pytest.mark.asyncio
async def test_metadata_field_search_validation_errors(search_service):
    """Test metadata field search with validation errors"""
    # Test empty field queries
    with pytest.raises(ValueError, match="At least one field query is required"):
        MetadataFieldSearchQuery(field_queries=[])
    
    # Test invalid operator
    with pytest.raises(ValueError, match="Operator must be AND or OR"):
        MetadataFieldSearchQuery(
            field_queries=[{"field": "title", "value": "test"}],
            operator="XOR"
        )
    
    # Test missing field or value
    with pytest.raises(ValueError, match='Each field query must have "field" and "value" keys'):
        MetadataFieldSearchQuery(
            field_queries=[{"field": "title"}]  # Missing value
        )
    
    # Test empty field or value
    with pytest.raises(ValueError, match="Field and value cannot be empty"):
        MetadataFieldSearchQuery(
            field_queries=[{"field": "", "value": "test"}]
        )


@pytest.mark.asyncio
async def test_metadata_field_search_connection_error(search_service, mock_opensearch_client):
    """Test metadata field search with connection error"""
    # Arrange
    from opensearchpy.exceptions import ConnectionError as OpenSearchConnectionError
    
    query = MetadataFieldSearchQuery(
        field_queries=[{"field": "title", "value": "test"}]
    )
    mock_opensearch_client.search.side_effect = OpenSearchConnectionError("Connection failed")
    
    # Act & Assert
    with pytest.raises(SearchError) as exc_info:
        await search_service.metadata_field_search(query)
    
    assert "Failed to connect to search service" in str(exc_info.value)


@pytest.mark.asyncio
async def test_metadata_field_search_request_error(search_service, mock_opensearch_client):
    """Test metadata field search with request error"""
    # Arrange
    from opensearchpy.exceptions import RequestError
    
    query = MetadataFieldSearchQuery(
        field_queries=[{"field": "invalid_field", "value": "test"}]
    )
    mock_opensearch_client.search.side_effect = RequestError(
        400, "parsing_exception", {"error": "Field does not exist"}
    )
    
    # Act & Assert
    with pytest.raises(InvalidQueryError) as exc_info:
        await search_service.metadata_field_search(query)
    
    assert "Invalid metadata search query" in str(exc_info.value)