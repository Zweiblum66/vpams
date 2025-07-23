"""
Tests for Search Suggestion Routes
"""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

from src.models.schemas import SuggestionResponse, SuggestionItem


@pytest.mark.asyncio
async def test_get_suggestions_endpoint(async_client: AsyncClient):
    """Test the suggestion endpoint"""
    # Arrange
    mock_response = SuggestionResponse(
        suggestions=[
            SuggestionItem(text="video production", score=10.0),
            SuggestionItem(text="video editing", score=8.0)
        ],
        took=5
    )
    
    with patch("src.api.routes.get_suggestion_service") as mock_get_service:
        mock_service = AsyncMock()
        mock_service.get_suggestions.return_value = mock_response
        mock_get_service.return_value = mock_service
        
        # Act
        response = await async_client.get(
            "/api/v1/search/suggestions",
            params={"text": "vid", "size": 5}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["suggestions"]) == 2
        assert data["suggestions"][0]["text"] == "video production"
        assert data["suggestions"][0]["score"] == 10.0
        assert data["took"] == 5


@pytest.mark.asyncio
async def test_get_suggestions_with_index_type(async_client: AsyncClient):
    """Test suggestions with specific index type"""
    # Arrange
    mock_response = SuggestionResponse(suggestions=[], took=3)
    
    with patch("src.api.routes.get_suggestion_service") as mock_get_service:
        mock_service = AsyncMock()
        mock_service.get_suggestions.return_value = mock_response
        mock_get_service.return_value = mock_service
        
        # Act
        response = await async_client.get(
            "/api/v1/search/suggestions",
            params={"text": "test", "index_type": "projects"}
        )
        
        # Assert
        assert response.status_code == 200
        # Verify the service was called with correct index type
        call_args = mock_service.get_suggestions.call_args[0][0]
        assert call_args.index_type.value == "projects"


@pytest.mark.asyncio
async def test_get_suggestions_validation_errors(async_client: AsyncClient):
    """Test validation errors for suggestions endpoint"""
    # Test empty text
    response = await async_client.get(
        "/api/v1/search/suggestions",
        params={"text": ""}
    )
    assert response.status_code == 422
    
    # Test text too long
    response = await async_client.get(
        "/api/v1/search/suggestions",
        params={"text": "a" * 101}
    )
    assert response.status_code == 422
    
    # Test invalid size
    response = await async_client.get(
        "/api/v1/search/suggestions",
        params={"text": "test", "size": 0}
    )
    assert response.status_code == 422
    
    # Test size too large
    response = await async_client.get(
        "/api/v1/search/suggestions",
        params={"text": "test", "size": 21}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_suggestions_error_handling(async_client: AsyncClient):
    """Test error handling in suggestions endpoint"""
    with patch("src.api.routes.get_suggestion_service") as mock_get_service:
        mock_service = AsyncMock()
        mock_service.get_suggestions.side_effect = Exception("OpenSearch error")
        mock_get_service.return_value = mock_service
        
        # Act
        response = await async_client.get(
            "/api/v1/search/suggestions",
            params={"text": "test"}
        )
        
        # Assert
        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to get suggestions"


@pytest.mark.asyncio
async def test_get_suggestions_default_parameters(async_client: AsyncClient):
    """Test suggestions with default parameters"""
    # Arrange
    mock_response = SuggestionResponse(
        suggestions=[SuggestionItem(text="test result", score=5.0)],
        took=2
    )
    
    with patch("src.api.routes.get_suggestion_service") as mock_get_service:
        mock_service = AsyncMock()
        mock_service.get_suggestions.return_value = mock_response
        mock_get_service.return_value = mock_service
        
        # Act - Only provide required parameter
        response = await async_client.get(
            "/api/v1/search/suggestions",
            params={"text": "test"}
        )
        
        # Assert
        assert response.status_code == 200
        # Verify defaults were used
        call_args = mock_service.get_suggestions.call_args[0][0]
        assert call_args.size == 5  # Default size
        assert call_args.index_type.value == "assets"  # Default index type