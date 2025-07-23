"""
Tests for Search Service with Ranking Integration
"""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime, timedelta

from src.services.search_service import SearchService
from src.services.ranking_service import RankingService
from src.models.schemas import SearchQuery, SearchResponse, RankingConfig, RankingType, IndexType
from src.core.exceptions import SearchError


@pytest.fixture
def mock_opensearch_client():
    """Mock OpenSearch client"""
    client = AsyncMock()
    return client


@pytest.fixture
def ranking_service():
    """Create ranking service instance"""
    return RankingService()


@pytest.fixture
def search_service(mock_opensearch_client, ranking_service):
    """Search service with ranking service"""
    return SearchService(mock_opensearch_client, ranking_service)


@pytest.fixture
def sample_search_response():
    """Sample OpenSearch response with varied content"""
    now = datetime.utcnow()
    
    return {
        "took": 10,
        "timed_out": False,
        "hits": {
            "total": {"value": 4, "relation": "eq"},
            "max_score": 3.0,
            "hits": [
                {
                    "_index": "mams_assets",
                    "_id": "old-popular",
                    "_score": 2.0,
                    "_source": {
                        "asset_id": "old-popular",
                        "title": "Popular Classic Video",
                        "description": "A very popular but older video",
                        "asset_type": "video",
                        "created_at": (now - timedelta(days=90)).isoformat() + "Z",
                        "view_count": 10000,
                        "download_count": 500,
                        "file_size": 200_000_000
                    }
                },
                {
                    "_index": "mams_assets",
                    "_id": "recent-relevant",
                    "_score": 3.0,
                    "_source": {
                        "asset_id": "recent-relevant",
                        "title": "Recent Important Video",
                        "description": "A recent video with high relevance",
                        "asset_type": "video",
                        "created_at": (now - timedelta(days=1)).isoformat() + "Z",
                        "view_count": 50,
                        "download_count": 5,
                        "metadata": {"resolution": "4K"},
                        "proxy_paths": ["/proxy/recent.mp4"]
                    }
                },
                {
                    "_index": "mams_assets",
                    "_id": "medium-all",
                    "_score": 1.5,
                    "_source": {
                        "asset_id": "medium-all",
                        "title": "Average Content",
                        "description": "Medium scores across all factors",
                        "asset_type": "document",
                        "created_at": (now - timedelta(days=30)).isoformat() + "Z",
                        "view_count": 500,
                        "download_count": 50
                    }
                },
                {
                    "_index": "mams_assets",
                    "_id": "new-unknown",
                    "_score": 0.8,
                    "_source": {
                        "asset_id": "new-unknown",
                        "title": "Brand New Upload",
                        "description": "Just uploaded, no metrics yet",
                        "asset_type": "image",
                        "created_at": now.isoformat() + "Z",
                        "view_count": 0,
                        "download_count": 0
                    }
                }
            ]
        }
    }


@pytest.mark.asyncio
async def test_search_with_default_ranking(search_service, mock_opensearch_client, sample_search_response):
    """Test search with default hybrid ranking"""
    # Arrange
    query = SearchQuery(query="video content")
    mock_opensearch_client.search.return_value = sample_search_response
    
    # Act
    result = await search_service.search(query)
    
    # Assert
    assert result.total_hits == 4
    # With hybrid ranking, recent-relevant should rank high due to combination of factors
    assert result.hits[0].id == "recent-relevant"


@pytest.mark.asyncio
async def test_search_with_recency_ranking(search_service, mock_opensearch_client, sample_search_response):
    """Test search with recency ranking"""
    # Arrange
    query = SearchQuery(
        query="video",
        ranking_config=RankingConfig(ranking_type=RankingType.RECENCY)
    )
    mock_opensearch_client.search.return_value = sample_search_response
    
    # Act
    result = await search_service.search(query)
    
    # Assert
    assert result.total_hits == 4
    # Should be ordered by recency
    assert result.hits[0].id == "new-unknown"  # Today
    assert result.hits[1].id == "recent-relevant"  # 1 day ago
    assert result.hits[2].id == "medium-all"  # 30 days ago
    assert result.hits[3].id == "old-popular"  # 90 days ago


@pytest.mark.asyncio
async def test_search_with_popularity_ranking(search_service, mock_opensearch_client, sample_search_response):
    """Test search with popularity ranking"""
    # Arrange
    query = SearchQuery(
        query="video",
        ranking_config=RankingConfig(ranking_type=RankingType.POPULARITY)
    )
    mock_opensearch_client.search.return_value = sample_search_response
    
    # Act
    result = await search_service.search(query)
    
    # Assert
    assert result.total_hits == 4
    # old-popular should rank first due to high view/download counts
    assert result.hits[0].id == "old-popular"


@pytest.mark.asyncio
async def test_search_with_custom_weights(search_service, mock_opensearch_client, sample_search_response):
    """Test search with custom hybrid weights"""
    # Arrange
    query = SearchQuery(
        query="video",
        ranking_config=RankingConfig(
            ranking_type=RankingType.HYBRID,
            hybrid_weights={
                "relevance": 0.2,
                "recency": 0.6,
                "popularity": 0.1,
                "quality": 0.1
            }
        )
    )
    mock_opensearch_client.search.return_value = sample_search_response
    
    # Act
    result = await search_service.search(query)
    
    # Assert
    assert result.total_hits == 4
    # With high recency weight, newer items should rank higher
    assert result.hits[0].id in ["new-unknown", "recent-relevant"]


@pytest.mark.asyncio
async def test_search_with_ranking_explanation(search_service, mock_opensearch_client, sample_search_response):
    """Test search with ranking explanations included"""
    # Arrange
    query = SearchQuery(
        query="video",
        ranking_config=RankingConfig(ranking_type=RankingType.HYBRID),
        include_ranking_explanation=True
    )
    mock_opensearch_client.search.return_value = sample_search_response
    
    # Act
    result = await search_service.search(query)
    
    # Assert
    assert result.total_hits == 4
    # All hits should have ranking explanations
    for hit in result.hits:
        assert hit.ranking_explanation is not None
        assert 'original_score' in hit.ranking_explanation
        assert 'factors' in hit.ranking_explanation


@pytest.mark.asyncio
async def test_search_with_explicit_sort_bypasses_ranking(search_service, mock_opensearch_client, sample_search_response):
    """Test that explicit sorting bypasses ranking"""
    # Arrange
    query = SearchQuery(
        query="video",
        sort_by="created_at",
        ranking_config=RankingConfig(ranking_type=RankingType.POPULARITY)
    )
    mock_opensearch_client.search.return_value = sample_search_response
    
    # Act
    result = await search_service.search(query)
    
    # Assert
    # Results should maintain OpenSearch order (not re-ranked)
    assert result.hits[0].id == "old-popular"  # First in OpenSearch response
    assert result.hits[1].id == "recent-relevant"  # Second in OpenSearch response


@pytest.mark.asyncio
async def test_search_without_ranking_service(mock_opensearch_client, sample_search_response):
    """Test search works without ranking service"""
    # Arrange
    search_service = SearchService(mock_opensearch_client, ranking_service=None)
    query = SearchQuery(
        query="video",
        ranking_config=RankingConfig(ranking_type=RankingType.POPULARITY)
    )
    mock_opensearch_client.search.return_value = sample_search_response
    
    # Act
    result = await search_service.search(query)
    
    # Assert
    # Should return results in OpenSearch order
    assert result.total_hits == 4
    assert result.hits[0].id == "old-popular"


@pytest.mark.asyncio
async def test_metadata_search_with_ranking(search_service, mock_opensearch_client, sample_search_response):
    """Test metadata field search with ranking"""
    from src.models.schemas import MetadataFieldSearchQuery
    
    # Arrange
    query = MetadataFieldSearchQuery(
        field_queries=[{"field": "title", "value": "video"}],
        operator="AND"
    )
    mock_opensearch_client.search.return_value = sample_search_response
    
    # Act
    result = await search_service.metadata_field_search(query)
    
    # Assert
    # Default ranking should be applied
    assert result.total_hits == 4


@pytest.mark.asyncio
async def test_advanced_search_with_ranking(search_service, mock_opensearch_client, sample_search_response):
    """Test advanced search with ranking"""
    from src.models.schemas import AdvancedSearchQuery
    
    # Arrange
    query = AdvancedSearchQuery(
        must=[{"field": "asset_type", "operator": "equals", "value": "video"}]
    )
    mock_opensearch_client.search.return_value = sample_search_response
    
    # Act
    result = await search_service.advanced_search(query)
    
    # Assert
    # Default ranking should be applied
    assert result.total_hits == 4


@pytest.mark.asyncio
async def test_empty_search_results_with_ranking(search_service, mock_opensearch_client):
    """Test ranking handles empty results gracefully"""
    # Arrange
    query = SearchQuery(
        query="nonexistent",
        ranking_config=RankingConfig(ranking_type=RankingType.POPULARITY)
    )
    mock_opensearch_client.search.return_value = {
        "took": 5,
        "timed_out": False,
        "hits": {"total": {"value": 0}, "hits": []}
    }
    
    # Act
    result = await search_service.search(query)
    
    # Assert
    assert result.total_hits == 0
    assert result.hits == []


@pytest.mark.asyncio
async def test_custom_ranking_with_asset_type_boost(search_service, mock_opensearch_client, sample_search_response):
    """Test custom ranking with asset type preferences"""
    # Arrange
    query = SearchQuery(
        query="content",
        ranking_config=RankingConfig(
            ranking_type=RankingType.CUSTOM,
            asset_type_boosts={
                "video": 3.0,
                "image": 2.0,
                "document": 1.0,
                "audio": 0.5
            }
        )
    )
    mock_opensearch_client.search.return_value = sample_search_response
    
    # Act
    result = await search_service.search(query)
    
    # Assert
    # Videos should rank higher due to boost
    video_hits = [h for h in result.hits if h.source.get('asset_type') == 'video']
    non_video_hits = [h for h in result.hits if h.source.get('asset_type') != 'video']
    
    # At least one video should rank above non-videos
    if video_hits and non_video_hits:
        video_positions = [result.hits.index(h) for h in video_hits]
        non_video_positions = [result.hits.index(h) for h in non_video_hits]
        assert min(video_positions) < max(non_video_positions)