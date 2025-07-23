"""
Tests for Phonetic Search API endpoints
"""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

from src.models.schemas import (
    PhoneticAlgorithm, PhoneticMatchType, PhoneticSearchQuery, PhoneticSearchResponse,
    PhoneticSuggestionQuery, PhoneticSuggestionResponse, IndexType, SortOrder
)


@pytest.mark.asyncio
class TestPhoneticSearchAPI:
    """Test phonetic search API endpoints"""
    
    async def test_phonetic_search_basic(self, client: AsyncClient):
        """Test basic phonetic search"""
        data = {
            "query": "John Smith",
            "algorithm": "soundex",
            "match_type": "adaptive",
            "size": 10
        }
        
        with patch('src.services.search_service.SearchService.phonetic_search') as mock_search:
            mock_search.return_value = PhoneticSearchResponse(
                query="John Smith",
                algorithm=PhoneticAlgorithm.SOUNDEX,
                match_type=PhoneticMatchType.ADAPTIVE,
                phonetic_tokens=["J500", "S530"],
                total_hits=5,
                max_score=1.8,
                hits=[
                    {
                        "id": "asset-1",
                        "index": "mams_assets",
                        "score": 1.8,
                        "source": {
                            "asset_id": "asset-1",
                            "name": "John Smith Interview",
                            "description": "Interview with John Smith"
                        },
                        "highlight": {
                            "name": ["<mark>John</mark> <mark>Smith</mark> Interview"]
                        }
                    },
                    {
                        "id": "asset-2",
                        "index": "mams_assets",
                        "score": 1.5,
                        "source": {
                            "asset_id": "asset-2",
                            "name": "Jon Smyth Video",
                            "description": "Video featuring Jon Smyth"
                        },
                        "highlight": {
                            "name": ["<mark>Jon</mark> <mark>Smyth</mark> Video"]
                        }
                    }
                ],
                suggestions=None,
                phonetic_analysis=None,
                took=45,
                timed_out=False,
                page=1,
                per_page=10,
                total_pages=1,
                fallback_used=False,
                exact_matches=1,
                phonetic_matches=1
            )
            
            response = await client.post("/api/v1/search/phonetic", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["query"] == "John Smith"
            assert result["algorithm"] == "soundex"
            assert result["match_type"] == "adaptive"
            assert result["total_hits"] == 5
            assert len(result["hits"]) == 2
            assert result["phonetic_tokens"] == ["J500", "S530"]
            assert result["fallback_used"] is False
            assert result["exact_matches"] == 1
            assert result["phonetic_matches"] == 1
    
    async def test_phonetic_search_with_suggestions(self, client: AsyncClient):
        """Test phonetic search with suggestions"""
        data = {
            "query": "John Smith",
            "algorithm": "soundex",
            "match_type": "adaptive",
            "include_suggestions": True,
            "size": 10
        }
        
        with patch('src.services.search_service.SearchService.phonetic_search') as mock_search:
            mock_search.return_value = PhoneticSearchResponse(
                query="John Smith",
                algorithm=PhoneticAlgorithm.SOUNDEX,
                match_type=PhoneticMatchType.ADAPTIVE,
                phonetic_tokens=["J500", "S530"],
                total_hits=3,
                max_score=1.5,
                hits=[],
                suggestions=[
                    {"text": "Jon Smith", "score": 0.9, "freq": 50},
                    {"text": "John Smyth", "score": 0.8, "freq": 30},
                    {"text": "Joan Smith", "score": 0.7, "freq": 20}
                ],
                phonetic_analysis=None,
                took=35,
                timed_out=False,
                page=1,
                per_page=10,
                total_pages=1,
                fallback_used=False,
                exact_matches=0,
                phonetic_matches=3
            )
            
            response = await client.post("/api/v1/search/phonetic", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["query"] == "John Smith"
            assert result["suggestions"] is not None
            assert len(result["suggestions"]) == 3
            assert result["suggestions"][0]["text"] == "Jon Smith"
            assert result["suggestions"][1]["text"] == "John Smyth"
            assert result["suggestions"][2]["text"] == "Joan Smith"
    
    async def test_phonetic_search_with_analysis(self, client: AsyncClient):
        """Test phonetic search with phonetic analysis"""
        data = {
            "query": "John Smith",
            "algorithm": "metaphone",
            "match_type": "phrase",
            "include_phonetic_analysis": True,
            "size": 10
        }
        
        with patch('src.services.search_service.SearchService.phonetic_search') as mock_search:
            mock_search.return_value = PhoneticSearchResponse(
                query="John Smith",
                algorithm=PhoneticAlgorithm.METAPHONE,
                match_type=PhoneticMatchType.PHRASE,
                phonetic_tokens=["JN", "SM0"],
                total_hits=2,
                max_score=1.2,
                hits=[],
                suggestions=None,
                phonetic_analysis={
                    "original_query": "John Smith",
                    "algorithm_used": "metaphone",
                    "encoded_terms": [
                        {"original": "john", "phonetic_code": "JN", "algorithm": "metaphone"},
                        {"original": "smith", "phonetic_code": "SM0", "algorithm": "metaphone"}
                    ],
                    "query_characteristics": {
                        "word_count": 2,
                        "avg_word_length": 4.5,
                        "has_numbers": False,
                        "has_special_chars": False,
                        "is_likely_name": True,
                        "is_technical_term": False
                    }
                },
                took=40,
                timed_out=False,
                page=1,
                per_page=10,
                total_pages=1,
                fallback_used=False,
                exact_matches=0,
                phonetic_matches=2
            )
            
            response = await client.post("/api/v1/search/phonetic", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["query"] == "John Smith"
            assert result["algorithm"] == "metaphone"
            assert result["match_type"] == "phrase"
            assert result["phonetic_analysis"] is not None
            assert result["phonetic_analysis"]["original_query"] == "John Smith"
            assert result["phonetic_analysis"]["algorithm_used"] == "metaphone"
            assert len(result["phonetic_analysis"]["encoded_terms"]) == 2
            assert result["phonetic_analysis"]["query_characteristics"]["is_likely_name"] is True
    
    async def test_phonetic_search_different_algorithms(self, client: AsyncClient):
        """Test phonetic search with different algorithms"""
        algorithms = ["soundex", "metaphone", "nysiis", "phonex"]
        
        for algorithm in algorithms:
            data = {
                "query": "Smith",
                "algorithm": algorithm,
                "match_type": "single_term",
                "size": 5
            }
            
            with patch('src.services.search_service.SearchService.phonetic_search') as mock_search:
                mock_search.return_value = PhoneticSearchResponse(
                    query="Smith",
                    algorithm=PhoneticAlgorithm(algorithm.upper()),
                    match_type=PhoneticMatchType.SINGLE_TERM,
                    phonetic_tokens=["S530"],  # Simplified for test
                    total_hits=3,
                    max_score=1.0,
                    hits=[],
                    suggestions=None,
                    phonetic_analysis=None,
                    took=25,
                    timed_out=False,
                    page=1,
                    per_page=5,
                    total_pages=1,
                    fallback_used=False,
                    exact_matches=1,
                    phonetic_matches=2
                )
                
                response = await client.post("/api/v1/search/phonetic", json=data)
                
                assert response.status_code == 200
                result = response.json()
                assert result["query"] == "Smith"
                assert result["algorithm"] == algorithm
                assert result["match_type"] == "single_term"
    
    async def test_phonetic_search_different_match_types(self, client: AsyncClient):
        """Test phonetic search with different match types"""
        match_types = ["single_term", "multi_term", "phrase", "cross_field", "adaptive"]
        
        for match_type in match_types:
            data = {
                "query": "John Smith",
                "algorithm": "soundex",
                "match_type": match_type,
                "size": 10
            }
            
            with patch('src.services.search_service.SearchService.phonetic_search') as mock_search:
                mock_search.return_value = PhoneticSearchResponse(
                    query="John Smith",
                    algorithm=PhoneticAlgorithm.SOUNDEX,
                    match_type=PhoneticMatchType(match_type.upper()),
                    phonetic_tokens=["J500", "S530"],
                    total_hits=4,
                    max_score=1.3,
                    hits=[],
                    suggestions=None,
                    phonetic_analysis=None,
                    took=30,
                    timed_out=False,
                    page=1,
                    per_page=10,
                    total_pages=1,
                    fallback_used=False,
                    exact_matches=1,
                    phonetic_matches=3
                )
                
                response = await client.post("/api/v1/search/phonetic", json=data)
                
                assert response.status_code == 200
                result = response.json()
                assert result["query"] == "John Smith"
                assert result["match_type"] == match_type
    
    async def test_phonetic_search_with_custom_fields(self, client: AsyncClient):
        """Test phonetic search with custom fields"""
        data = {
            "query": "John Smith",
            "algorithm": "soundex",
            "match_type": "adaptive",
            "fields": ["name", "title", "creator"],
            "size": 10
        }
        
        with patch('src.services.search_service.SearchService.phonetic_search') as mock_search:
            mock_search.return_value = PhoneticSearchResponse(
                query="John Smith",
                algorithm=PhoneticAlgorithm.SOUNDEX,
                match_type=PhoneticMatchType.ADAPTIVE,
                phonetic_tokens=["J500", "S530"],
                total_hits=2,
                max_score=1.5,
                hits=[],
                suggestions=None,
                phonetic_analysis=None,
                took=25,
                timed_out=False,
                page=1,
                per_page=10,
                total_pages=1,
                fallback_used=False,
                exact_matches=1,
                phonetic_matches=1
            )
            
            response = await client.post("/api/v1/search/phonetic", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["query"] == "John Smith"
            # Note: fields are handled internally, not returned in response
    
    async def test_phonetic_search_with_boost_settings(self, client: AsyncClient):
        """Test phonetic search with custom boost settings"""
        data = {
            "query": "John Smith",
            "algorithm": "soundex",
            "match_type": "adaptive",
            "boost_exact_matches": 3.0,
            "boost_phonetic_matches": 1.5,
            "min_similarity": 0.8,
            "size": 10
        }
        
        with patch('src.services.search_service.SearchService.phonetic_search') as mock_search:
            mock_search.return_value = PhoneticSearchResponse(
                query="John Smith",
                algorithm=PhoneticAlgorithm.SOUNDEX,
                match_type=PhoneticMatchType.ADAPTIVE,
                phonetic_tokens=["J500", "S530"],
                total_hits=1,
                max_score=2.5,
                hits=[],
                suggestions=None,
                phonetic_analysis=None,
                took=20,
                timed_out=False,
                page=1,
                per_page=10,
                total_pages=1,
                fallback_used=False,
                exact_matches=1,
                phonetic_matches=0
            )
            
            response = await client.post("/api/v1/search/phonetic", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["query"] == "John Smith"
            assert result["max_score"] == 2.5
            assert result["exact_matches"] == 1
    
    async def test_phonetic_search_with_fallback(self, client: AsyncClient):
        """Test phonetic search with fallback enabled"""
        data = {
            "query": "!@#$%",  # No valid phonetic tokens
            "algorithm": "soundex",
            "match_type": "adaptive",
            "use_fallback_search": True,
            "size": 10
        }
        
        with patch('src.services.search_service.SearchService.phonetic_search') as mock_search:
            mock_search.return_value = PhoneticSearchResponse(
                query="!@#$%",
                algorithm=PhoneticAlgorithm.SOUNDEX,
                match_type=PhoneticMatchType.ADAPTIVE,
                phonetic_tokens=[],
                total_hits=2,
                max_score=0.8,
                hits=[
                    {
                        "id": "asset-1",
                        "index": "mams_assets",
                        "score": 0.8,
                        "source": {
                            "asset_id": "asset-1",
                            "name": "Special Characters File",
                            "description": "File with special characters"
                        }
                    }
                ],
                suggestions=None,
                phonetic_analysis=None,
                took=15,
                timed_out=False,
                page=1,
                per_page=10,
                total_pages=1,
                fallback_used=True,
                exact_matches=0,
                phonetic_matches=0
            )
            
            response = await client.post("/api/v1/search/phonetic", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["query"] == "!@#$%"
            assert result["fallback_used"] is True
            assert result["total_hits"] == 2
            assert len(result["phonetic_tokens"]) == 0
    
    async def test_phonetic_search_without_fallback(self, client: AsyncClient):
        """Test phonetic search without fallback"""
        data = {
            "query": "!@#$%",
            "algorithm": "soundex",
            "match_type": "adaptive",
            "use_fallback_search": False,
            "size": 10
        }
        
        with patch('src.services.search_service.SearchService.phonetic_search') as mock_search:
            mock_search.return_value = PhoneticSearchResponse(
                query="!@#$%",
                algorithm=PhoneticAlgorithm.SOUNDEX,
                match_type=PhoneticMatchType.ADAPTIVE,
                phonetic_tokens=[],
                total_hits=0,
                max_score=None,
                hits=[],
                suggestions=None,
                phonetic_analysis=None,
                took=5,
                timed_out=False,
                page=1,
                per_page=10,
                total_pages=0,
                fallback_used=False,
                exact_matches=0,
                phonetic_matches=0
            )
            
            response = await client.post("/api/v1/search/phonetic", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["query"] == "!@#$%"
            assert result["fallback_used"] is False
            assert result["total_hits"] == 0
            assert len(result["hits"]) == 0
    
    async def test_phonetic_search_pagination(self, client: AsyncClient):
        """Test phonetic search with pagination"""
        data = {
            "query": "John Smith",
            "algorithm": "soundex",
            "match_type": "adaptive",
            "size": 5,
            "from": 10
        }
        
        with patch('src.services.search_service.SearchService.phonetic_search') as mock_search:
            mock_search.return_value = PhoneticSearchResponse(
                query="John Smith",
                algorithm=PhoneticAlgorithm.SOUNDEX,
                match_type=PhoneticMatchType.ADAPTIVE,
                phonetic_tokens=["J500", "S530"],
                total_hits=25,
                max_score=1.0,
                hits=[],
                suggestions=None,
                phonetic_analysis=None,
                took=30,
                timed_out=False,
                page=3,
                per_page=5,
                total_pages=5,
                fallback_used=False,
                exact_matches=5,
                phonetic_matches=20
            )
            
            response = await client.post("/api/v1/search/phonetic", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["page"] == 3
            assert result["per_page"] == 5
            assert result["total_pages"] == 5
            assert result["total_hits"] == 25
    
    async def test_phonetic_search_sorting(self, client: AsyncClient):
        """Test phonetic search with sorting"""
        data = {
            "query": "John Smith",
            "algorithm": "soundex",
            "match_type": "adaptive",
            "sort_by": "created_at",
            "sort_order": "asc",
            "size": 10
        }
        
        with patch('src.services.search_service.SearchService.phonetic_search') as mock_search:
            mock_search.return_value = PhoneticSearchResponse(
                query="John Smith",
                algorithm=PhoneticAlgorithm.SOUNDEX,
                match_type=PhoneticMatchType.ADAPTIVE,
                phonetic_tokens=["J500", "S530"],
                total_hits=8,
                max_score=1.2,
                hits=[],
                suggestions=None,
                phonetic_analysis=None,
                took=35,
                timed_out=False,
                page=1,
                per_page=10,
                total_pages=1,
                fallback_used=False,
                exact_matches=3,
                phonetic_matches=5
            )
            
            response = await client.post("/api/v1/search/phonetic", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["query"] == "John Smith"
            # Note: sort settings are handled internally, not returned in response
    
    async def test_phonetic_search_validation_errors(self, client: AsyncClient):
        """Test phonetic search validation errors"""
        # Test empty query
        data = {
            "query": "",
            "algorithm": "soundex",
            "match_type": "adaptive"
        }
        
        response = await client.post("/api/v1/search/phonetic", json=data)
        assert response.status_code == 422
        
        # Test invalid algorithm
        data = {
            "query": "John Smith",
            "algorithm": "invalid_algorithm",
            "match_type": "adaptive"
        }
        
        response = await client.post("/api/v1/search/phonetic", json=data)
        assert response.status_code == 422
        
        # Test invalid match type
        data = {
            "query": "John Smith",
            "algorithm": "soundex",
            "match_type": "invalid_match_type"
        }
        
        response = await client.post("/api/v1/search/phonetic", json=data)
        assert response.status_code == 422
        
        # Test invalid boost values
        data = {
            "query": "John Smith",
            "algorithm": "soundex",
            "match_type": "adaptive",
            "boost_exact_matches": -1.0  # Invalid negative boost
        }
        
        response = await client.post("/api/v1/search/phonetic", json=data)
        assert response.status_code == 422
        
        # Test invalid similarity threshold
        data = {
            "query": "John Smith",
            "algorithm": "soundex",
            "match_type": "adaptive",
            "min_similarity": 1.5  # Invalid > 1.0
        }
        
        response = await client.post("/api/v1/search/phonetic", json=data)
        assert response.status_code == 422
    
    async def test_phonetic_search_error_handling(self, client: AsyncClient):
        """Test phonetic search error handling"""
        data = {
            "query": "John Smith",
            "algorithm": "soundex",
            "match_type": "adaptive",
            "size": 10
        }
        
        with patch('src.services.search_service.SearchService.phonetic_search') as mock_search:
            mock_search.side_effect = Exception("Search service error")
            
            response = await client.post("/api/v1/search/phonetic", json=data)
            
            assert response.status_code == 500
            assert "phonetic search error" in response.json()["detail"].lower()


@pytest.mark.asyncio
class TestPhoneticSuggestionsAPI:
    """Test phonetic suggestions API endpoints"""
    
    async def test_phonetic_suggestions_basic(self, client: AsyncClient):
        """Test basic phonetic suggestions"""
        data = {
            "text": "Smith",
            "algorithm": "soundex",
            "size": 5
        }
        
        with patch('src.services.search_service.SearchService.phonetic_suggestions') as mock_suggestions:
            mock_suggestions.return_value = PhoneticSuggestionResponse(
                text="Smith",
                algorithm=PhoneticAlgorithm.SOUNDEX,
                phonetic_code="S530",
                suggestions=[
                    {
                        "text": "Smith",
                        "score": 1.0,
                        "freq": 100,
                        "phonetic_code": "S530",
                        "similarity": 1.0
                    },
                    {
                        "text": "Smyth",
                        "score": 0.8,
                        "freq": 50,
                        "phonetic_code": "S530",
                        "similarity": 0.9
                    },
                    {
                        "text": "Smythe",
                        "score": 0.7,
                        "freq": 30,
                        "phonetic_code": "S530",
                        "similarity": 0.8
                    }
                ],
                took=20,
                metadata={
                    "field": "_all",
                    "algorithm": "soundex",
                    "min_similarity": 0.7,
                    "total_suggestions": 3
                }
            )
            
            response = await client.post("/api/v1/search/phonetic/suggestions", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["text"] == "Smith"
            assert result["algorithm"] == "soundex"
            assert result["phonetic_code"] == "S530"
            assert len(result["suggestions"]) == 3
            assert result["suggestions"][0]["text"] == "Smith"
            assert result["suggestions"][1]["text"] == "Smyth"
            assert result["suggestions"][2]["text"] == "Smythe"
            assert result["metadata"]["total_suggestions"] == 3
    
    async def test_phonetic_suggestions_different_algorithms(self, client: AsyncClient):
        """Test phonetic suggestions with different algorithms"""
        algorithms = ["soundex", "metaphone", "nysiis", "phonex"]
        
        for algorithm in algorithms:
            data = {
                "text": "Smith",
                "algorithm": algorithm,
                "size": 3
            }
            
            with patch('src.services.search_service.SearchService.phonetic_suggestions') as mock_suggestions:
                mock_suggestions.return_value = PhoneticSuggestionResponse(
                    text="Smith",
                    algorithm=PhoneticAlgorithm(algorithm.upper()),
                    phonetic_code="S530",  # Simplified for test
                    suggestions=[
                        {
                            "text": "Smith",
                            "score": 1.0,
                            "freq": 100,
                            "phonetic_code": "S530",
                            "similarity": 1.0
                        }
                    ],
                    took=15,
                    metadata={
                        "field": "_all",
                        "algorithm": algorithm,
                        "min_similarity": 0.7,
                        "total_suggestions": 1
                    }
                )
                
                response = await client.post("/api/v1/search/phonetic/suggestions", json=data)
                
                assert response.status_code == 200
                result = response.json()
                assert result["text"] == "Smith"
                assert result["algorithm"] == algorithm
    
    async def test_phonetic_suggestions_with_field(self, client: AsyncClient):
        """Test phonetic suggestions with specific field"""
        data = {
            "text": "Smith",
            "field": "name",
            "algorithm": "soundex",
            "size": 5
        }
        
        with patch('src.services.search_service.SearchService.phonetic_suggestions') as mock_suggestions:
            mock_suggestions.return_value = PhoneticSuggestionResponse(
                text="Smith",
                algorithm=PhoneticAlgorithm.SOUNDEX,
                phonetic_code="S530",
                suggestions=[
                    {
                        "text": "Smith",
                        "score": 1.0,
                        "freq": 80,
                        "phonetic_code": "S530",
                        "similarity": 1.0
                    }
                ],
                took=18,
                metadata={
                    "field": "name",
                    "algorithm": "soundex",
                    "min_similarity": 0.7,
                    "total_suggestions": 1
                }
            )
            
            response = await client.post("/api/v1/search/phonetic/suggestions", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["text"] == "Smith"
            assert result["metadata"]["field"] == "name"
    
    async def test_phonetic_suggestions_with_similarity_threshold(self, client: AsyncClient):
        """Test phonetic suggestions with similarity threshold"""
        data = {
            "text": "Smith",
            "algorithm": "soundex",
            "size": 5,
            "min_similarity": 0.9
        }
        
        with patch('src.services.search_service.SearchService.phonetic_suggestions') as mock_suggestions:
            mock_suggestions.return_value = PhoneticSuggestionResponse(
                text="Smith",
                algorithm=PhoneticAlgorithm.SOUNDEX,
                phonetic_code="S530",
                suggestions=[
                    {
                        "text": "Smith",
                        "score": 1.0,
                        "freq": 100,
                        "phonetic_code": "S530",
                        "similarity": 1.0
                    },
                    {
                        "text": "Smyth",
                        "score": 0.8,
                        "freq": 50,
                        "phonetic_code": "S530",
                        "similarity": 0.95
                    }
                ],
                took=22,
                metadata={
                    "field": "_all",
                    "algorithm": "soundex",
                    "min_similarity": 0.9,
                    "total_suggestions": 2
                }
            )
            
            response = await client.post("/api/v1/search/phonetic/suggestions", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["text"] == "Smith"
            assert len(result["suggestions"]) == 2
            assert result["metadata"]["min_similarity"] == 0.9
            # All suggestions should have similarity >= 0.9
            for suggestion in result["suggestions"]:
                assert suggestion["similarity"] >= 0.9
    
    async def test_phonetic_suggestions_size_limit(self, client: AsyncClient):
        """Test phonetic suggestions with size limit"""
        data = {
            "text": "Smith",
            "algorithm": "soundex",
            "size": 2
        }
        
        with patch('src.services.search_service.SearchService.phonetic_suggestions') as mock_suggestions:
            mock_suggestions.return_value = PhoneticSuggestionResponse(
                text="Smith",
                algorithm=PhoneticAlgorithm.SOUNDEX,
                phonetic_code="S530",
                suggestions=[
                    {
                        "text": "Smith",
                        "score": 1.0,
                        "freq": 100,
                        "phonetic_code": "S530",
                        "similarity": 1.0
                    },
                    {
                        "text": "Smyth",
                        "score": 0.8,
                        "freq": 50,
                        "phonetic_code": "S530",
                        "similarity": 0.9
                    }
                ],
                took=16,
                metadata={
                    "field": "_all",
                    "algorithm": "soundex",
                    "min_similarity": 0.7,
                    "total_suggestions": 2
                }
            )
            
            response = await client.post("/api/v1/search/phonetic/suggestions", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["text"] == "Smith"
            assert len(result["suggestions"]) == 2
    
    async def test_phonetic_suggestions_no_results(self, client: AsyncClient):
        """Test phonetic suggestions with no results"""
        data = {
            "text": "xyz123abc",
            "algorithm": "soundex",
            "size": 5
        }
        
        with patch('src.services.search_service.SearchService.phonetic_suggestions') as mock_suggestions:
            mock_suggestions.return_value = PhoneticSuggestionResponse(
                text="xyz123abc",
                algorithm=PhoneticAlgorithm.SOUNDEX,
                phonetic_code="X212",
                suggestions=[],
                took=10,
                metadata={
                    "field": "_all",
                    "algorithm": "soundex",
                    "min_similarity": 0.7,
                    "total_suggestions": 0
                }
            )
            
            response = await client.post("/api/v1/search/phonetic/suggestions", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["text"] == "xyz123abc"
            assert result["phonetic_code"] == "X212"
            assert len(result["suggestions"]) == 0
            assert result["metadata"]["total_suggestions"] == 0
    
    async def test_phonetic_suggestions_validation_errors(self, client: AsyncClient):
        """Test phonetic suggestions validation errors"""
        # Test empty text
        data = {
            "text": "",
            "algorithm": "soundex",
            "size": 5
        }
        
        response = await client.post("/api/v1/search/phonetic/suggestions", json=data)
        assert response.status_code == 422
        
        # Test invalid algorithm
        data = {
            "text": "Smith",
            "algorithm": "invalid_algorithm",
            "size": 5
        }
        
        response = await client.post("/api/v1/search/phonetic/suggestions", json=data)
        assert response.status_code == 422
        
        # Test invalid size
        data = {
            "text": "Smith",
            "algorithm": "soundex",
            "size": 0
        }
        
        response = await client.post("/api/v1/search/phonetic/suggestions", json=data)
        assert response.status_code == 422
        
        # Test size too large
        data = {
            "text": "Smith",
            "algorithm": "soundex",
            "size": 25
        }
        
        response = await client.post("/api/v1/search/phonetic/suggestions", json=data)
        assert response.status_code == 422
        
        # Test invalid similarity threshold
        data = {
            "text": "Smith",
            "algorithm": "soundex",
            "size": 5,
            "min_similarity": 1.5
        }
        
        response = await client.post("/api/v1/search/phonetic/suggestions", json=data)
        assert response.status_code == 422
    
    async def test_phonetic_suggestions_error_handling(self, client: AsyncClient):
        """Test phonetic suggestions error handling"""
        data = {
            "text": "Smith",
            "algorithm": "soundex",
            "size": 5
        }
        
        with patch('src.services.search_service.SearchService.phonetic_suggestions') as mock_suggestions:
            mock_suggestions.side_effect = Exception("Suggestions service error")
            
            response = await client.post("/api/v1/search/phonetic/suggestions", json=data)
            
            assert response.status_code == 500
            assert "phonetic suggestions error" in response.json()["detail"].lower()