"""
Tests for Suggestion Service
"""

import pytest
from unittest.mock import AsyncMock, Mock
import time

from src.services.suggestion_service import SuggestionService
from src.models.schemas import SuggestionQuery, SuggestionResponse, IndexType
from src.core.exceptions import SearchError
from opensearchpy.exceptions import RequestError, OpenSearchException


@pytest.fixture
def mock_opensearch_client():
    """Mock OpenSearch client"""
    client = AsyncMock()
    return client


@pytest.fixture
def suggestion_service(mock_opensearch_client):
    """Create suggestion service instance"""
    return SuggestionService(mock_opensearch_client)


@pytest.fixture
def sample_suggestion_response():
    """Sample OpenSearch suggestion response"""
    return {
        "took": 5,
        "timed_out": False,
        "suggest": {
            "name_suggest": [{
                "text": "vid",
                "offset": 0,
                "length": 3,
                "options": [
                    {
                        "text": "video production",
                        "score": 10.0,
                        "_index": "mams_assets",
                        "_id": "1"
                    },
                    {
                        "text": "video editing",
                        "score": 8.0,
                        "_index": "mams_assets",
                        "_id": "2"
                    },
                    {
                        "text": "video tutorial",
                        "score": 6.0,
                        "_index": "mams_assets",
                        "_id": "3"
                    }
                ]
            }],
            "term_suggest": [{
                "text": "vid",
                "offset": 0,
                "length": 3,
                "options": [
                    {
                        "text": "video",
                        "score": 0.8,
                        "freq": 25
                    }
                ]
            }]
        }
    }


@pytest.fixture
def phrase_suggestion_response():
    """Sample response with phrase suggestions"""
    return {
        "took": 7,
        "timed_out": False,
        "suggest": {
            "name_suggest": [{
                "text": "corporate vido",
                "offset": 0,
                "length": 14,
                "options": []
            }],
            "phrase_suggest": [{
                "text": "corporate vido",
                "offset": 0,
                "length": 14,
                "options": [
                    {
                        "text": "corporate video",
                        "score": 0.95,
                        "highlighted": "corporate <em>video</em>"
                    }
                ]
            }],
            "term_suggest": [
                {
                    "text": "corporate",
                    "offset": 0,
                    "length": 9,
                    "options": []
                },
                {
                    "text": "vido",
                    "offset": 10,
                    "length": 4,
                    "options": [
                        {
                            "text": "video",
                            "score": 0.9,
                            "freq": 20
                        }
                    ]
                }
            ]
        }
    }


@pytest.mark.asyncio
async def test_get_suggestions_basic(suggestion_service, mock_opensearch_client, sample_suggestion_response):
    """Test basic suggestion retrieval"""
    # Arrange
    query = SuggestionQuery(text="vid", size=5)
    mock_opensearch_client.search.return_value = sample_suggestion_response
    
    # Act
    result = await suggestion_service.get_suggestions(query)
    
    # Assert
    assert isinstance(result, SuggestionResponse)
    assert len(result.suggestions) == 4  # 3 completion + 1 term suggestion
    assert result.suggestions[0].text == "video production"
    assert result.suggestions[0].score == 20.0  # Boosted completion score
    assert result.took > 0
    
    # Verify OpenSearch was called correctly
    mock_opensearch_client.search.assert_called_once()
    call_args = mock_opensearch_client.search.call_args
    assert call_args[1]["index"] == "mams_assets"
    assert call_args[1]["size"] == 0


@pytest.mark.asyncio
async def test_get_suggestions_with_different_index(suggestion_service, mock_opensearch_client, sample_suggestion_response):
    """Test suggestions from different index types"""
    # Arrange
    query = SuggestionQuery(text="proj", size=3, index_type=IndexType.PROJECTS)
    mock_opensearch_client.search.return_value = sample_suggestion_response
    
    # Act
    await suggestion_service.get_suggestions(query)
    
    # Assert
    call_args = mock_opensearch_client.search.call_args
    assert call_args[1]["index"] == "mams_projects"


@pytest.mark.asyncio
async def test_get_suggestions_phrase_correction(suggestion_service, mock_opensearch_client, phrase_suggestion_response):
    """Test phrase suggestions for multi-word queries"""
    # Arrange
    query = SuggestionQuery(text="corporate vido", size=5)
    mock_opensearch_client.search.return_value = phrase_suggestion_response
    
    # Act
    result = await suggestion_service.get_suggestions(query)
    
    # Assert
    suggestions_texts = [s.text for s in result.suggestions]
    assert "corporate video" in suggestions_texts
    assert "video" in suggestions_texts
    
    # Verify phrase suggester was included
    call_args = mock_opensearch_client.search.call_args
    body = call_args[1]["body"]
    assert "phrase_suggest" in body["suggest"]


@pytest.mark.asyncio
async def test_get_suggestions_empty_results(suggestion_service, mock_opensearch_client):
    """Test handling of empty suggestion results"""
    # Arrange
    query = SuggestionQuery(text="xyzabc123", size=5)
    mock_opensearch_client.search.return_value = {
        "took": 3,
        "suggest": {
            "name_suggest": [{"text": "xyzabc123", "options": []}],
            "term_suggest": [{"text": "xyzabc123", "options": []}]
        }
    }
    
    # Act
    result = await suggestion_service.get_suggestions(query)
    
    # Assert
    assert len(result.suggestions) == 0
    assert result.took > 0


@pytest.mark.asyncio
async def test_get_suggestions_deduplication(suggestion_service, mock_opensearch_client):
    """Test that duplicate suggestions are removed"""
    # Arrange
    query = SuggestionQuery(text="vid", size=5)
    mock_opensearch_client.search.return_value = {
        "suggest": {
            "name_suggest": [{
                "options": [
                    {"text": "video", "score": 10.0},
                    {"text": "VIDEO", "score": 9.0}  # Different case
                ]
            }],
            "term_suggest": [{
                "options": [
                    {"text": "video", "score": 8.0}  # Duplicate
                ]
            }]
        }
    }
    
    # Act
    result = await suggestion_service.get_suggestions(query)
    
    # Assert
    assert len(result.suggestions) == 2  # "video" and "VIDEO"
    texts = [s.text for s in result.suggestions]
    assert "video" in texts
    assert "VIDEO" in texts


@pytest.mark.asyncio
async def test_get_suggestions_respects_size_limit(suggestion_service, mock_opensearch_client, sample_suggestion_response):
    """Test that size limit is respected"""
    # Arrange
    query = SuggestionQuery(text="vid", size=2)
    mock_opensearch_client.search.return_value = sample_suggestion_response
    
    # Act
    result = await suggestion_service.get_suggestions(query)
    
    # Assert
    assert len(result.suggestions) == 2  # Limited to requested size


@pytest.mark.asyncio
async def test_get_suggestions_fuzzy_matching(suggestion_service, mock_opensearch_client):
    """Test fuzzy matching in suggestions"""
    # Arrange
    query = SuggestionQuery(text="vdeo", size=5)  # Typo
    mock_opensearch_client.search.return_value = sample_suggestion_response
    
    # Act
    await suggestion_service.get_suggestions(query)
    
    # Assert
    call_args = mock_opensearch_client.search.call_args
    body = call_args[1]["body"]
    completion_config = body["suggest"]["name_suggest"]["completion"]
    assert completion_config["fuzzy"]["fuzziness"] == "AUTO"
    assert completion_config["fuzzy"]["transpositions"] is True


@pytest.mark.asyncio
async def test_get_suggestions_error_handling(suggestion_service, mock_opensearch_client):
    """Test error handling for OpenSearch errors"""
    # Arrange
    query = SuggestionQuery(text="test", size=5)
    mock_opensearch_client.search.side_effect = RequestError(400, "bad_request", {})
    
    # Act & Assert
    with pytest.raises(SearchError) as exc_info:
        await suggestion_service.get_suggestions(query)
    
    assert "Invalid suggestion request" in str(exc_info.value)


@pytest.mark.asyncio
async def test_update_suggestion_data(suggestion_service, mock_opensearch_client):
    """Test updating suggestion data for an asset"""
    # Arrange
    asset_id = "test-asset-123"
    name = "Corporate Training Video"
    
    # Act
    await suggestion_service.update_suggestion_data(asset_id, name)
    
    # Assert
    mock_opensearch_client.update.assert_called_once()
    call_args = mock_opensearch_client.update.call_args
    assert call_args[1]["index"] == "mams_assets"
    assert call_args[1]["id"] == asset_id
    
    # Check the update body
    update_body = call_args[1]["body"]["doc"]["name.suggest"]
    assert "Corporate Training Video" in update_body["input"]
    assert "Corporate" in update_body["input"]
    assert "Training" in update_body["input"]
    assert "Video" in update_body["input"]
    assert update_body["weight"] == 1


@pytest.mark.asyncio
async def test_update_suggestion_data_error_handling(suggestion_service, mock_opensearch_client):
    """Test error handling in update suggestion data"""
    # Arrange
    asset_id = "test-asset"
    name = "Test Asset"
    mock_opensearch_client.update.side_effect = Exception("Update failed")
    
    # Act - Should not raise exception
    await suggestion_service.update_suggestion_data(asset_id, name)
    
    # Assert - Error was logged but not raised
    mock_opensearch_client.update.assert_called_once()


@pytest.mark.asyncio
async def test_get_popular_searches(suggestion_service, mock_opensearch_client):
    """Test getting popular search terms"""
    # Arrange
    mock_opensearch_client.search.return_value = {
        "aggregations": {
            "popular_searches": {
                "buckets": [
                    {"key": "corporate video", "doc_count": 150},
                    {"key": "training material", "doc_count": 120},
                    {"key": "product demo", "doc_count": 90}
                ]
            }
        }
    }
    
    # Act
    popular_terms = await suggestion_service.get_popular_searches(size=3)
    
    # Assert
    assert len(popular_terms) == 3
    assert popular_terms[0] == "corporate video"
    assert popular_terms[1] == "training material"
    assert popular_terms[2] == "product demo"
    
    # Verify query structure
    call_args = mock_opensearch_client.search.call_args
    assert call_args[1]["index"] == "mams_analytics"
    assert call_args[1]["body"]["size"] == 0  # No documents needed
    assert "popular_searches" in call_args[1]["body"]["aggs"]


@pytest.mark.asyncio
async def test_get_popular_searches_empty(suggestion_service, mock_opensearch_client):
    """Test popular searches with no data"""
    # Arrange
    mock_opensearch_client.search.return_value = {"aggregations": {"popular_searches": {"buckets": []}}}
    
    # Act
    popular_terms = await suggestion_service.get_popular_searches()
    
    # Assert
    assert popular_terms == []


@pytest.mark.asyncio
async def test_get_popular_searches_error_handling(suggestion_service, mock_opensearch_client):
    """Test error handling for popular searches"""
    # Arrange
    mock_opensearch_client.search.side_effect = Exception("Analytics index not found")
    
    # Act
    popular_terms = await suggestion_service.get_popular_searches()
    
    # Assert - Returns empty list on error
    assert popular_terms == []


@pytest.mark.asyncio
async def test_suggestion_scoring(suggestion_service, mock_opensearch_client):
    """Test that suggestions are properly scored and sorted"""
    # Arrange
    query = SuggestionQuery(text="video", size=10)
    mock_opensearch_client.search.return_value = {
        "suggest": {
            "name_suggest": [{
                "options": [
                    {"text": "video editing", "score": 5.0},
                    {"text": "video production", "score": 8.0}
                ]
            }],
            "phrase_suggest": [{
                "options": [
                    {"text": "video tutorial", "score": 6.0}
                ]
            }],
            "term_suggest": [{
                "options": [
                    {"text": "videos", "score": 3.0}
                ]
            }]
        }
    }
    
    # Act
    result = await suggestion_service.get_suggestions(query)
    
    # Assert - Should be sorted by score
    assert result.suggestions[0].text == "video production"  # 8.0 * 2.0 = 16.0
    assert result.suggestions[1].text == "video editing"     # 5.0 * 2.0 = 10.0
    assert result.suggestions[2].text == "video tutorial"    # 6.0 * 1.5 = 9.0
    assert result.suggestions[3].text == "videos"           # 3.0


@pytest.mark.asyncio
async def test_single_word_query_no_phrase_suggest(suggestion_service, mock_opensearch_client):
    """Test that single word queries don't include phrase suggester"""
    # Arrange
    query = SuggestionQuery(text="video", size=5)
    mock_opensearch_client.search.return_value = {"suggest": {}}
    
    # Act
    await suggestion_service.get_suggestions(query)
    
    # Assert
    call_args = mock_opensearch_client.search.call_args
    body = call_args[1]["body"]
    assert "phrase_suggest" not in body["suggest"]
    assert "name_suggest" in body["suggest"]
    assert "term_suggest" in body["suggest"]