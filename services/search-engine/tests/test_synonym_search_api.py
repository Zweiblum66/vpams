"""
Tests for Synonym Search API endpoints
"""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

from src.models.schemas import (
    SynonymType, SynonymExpansionStrategy, SynonymConfig, SynonymSearchQuery, SynonymSearchResponse,
    SynonymSuggestionQuery, SynonymSuggestionResponse, SynonymStats, IndexType, SortOrder
)


@pytest.mark.asyncio
class TestSynonymSearchAPI:
    """Test synonym search API endpoints"""
    
    async def test_synonym_search_basic(self, client: AsyncClient):
        """Test basic synonym search"""
        data = {
            "query": "video content",
            "size": 10
        }
        
        with patch('src.services.search_service.SearchService.synonym_search') as mock_search:
            mock_search.return_value = SynonymSearchResponse(
                query="video content",
                expanded_query="video content (movie film clip)",
                total_hits=5,
                max_score=2.1,
                hits=[
                    {
                        "id": "asset-1",
                        "index": "mams_assets",
                        "score": 2.1,
                        "source": {
                            "asset_id": "asset-1",
                            "name": "Video Tutorial",
                            "description": "Educational video content"
                        },
                        "highlight": {
                            "name": ["<mark>Video</mark> Tutorial"]
                        }
                    },
                    {
                        "id": "asset-2",
                        "index": "mams_assets",
                        "score": 1.8,
                        "source": {
                            "asset_id": "asset-2",
                            "name": "Movie Trailer",
                            "description": "Promotional movie content"
                        },
                        "highlight": {
                            "name": ["<mark>Movie</mark> Trailer"]
                        }
                    }
                ],
                synonym_analysis=None,
                took=45,
                timed_out=False,
                page=1,
                per_page=10,
                total_pages=1,
                original_matches=1,
                synonym_matches=1,
                hybrid_matches=0
            )
            
            response = await client.post("/api/v1/search/synonym", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["query"] == "video content"
            assert result["expanded_query"] == "video content (movie film clip)"
            assert result["total_hits"] == 5
            assert len(result["hits"]) == 2
            assert result["original_matches"] == 1
            assert result["synonym_matches"] == 1
            assert result["hybrid_matches"] == 0
    
    async def test_synonym_search_with_config(self, client: AsyncClient):
        """Test synonym search with custom configuration"""
        data = {
            "query": "video content",
            "synonym_config": {
                "synonym_type": "custom",
                "expansion_strategy": "expand",
                "max_synonyms_per_term": 3,
                "custom_synonyms": {
                    "video": ["movie", "film", "clip"]
                },
                "boost_original_terms": 2.0,
                "boost_synonyms": 1.5
            },
            "size": 10
        }
        
        with patch('src.services.search_service.SearchService.synonym_search') as mock_search:
            mock_search.return_value = SynonymSearchResponse(
                query="video content",
                expanded_query="video content (movie film clip)",
                total_hits=3,
                max_score=1.9,
                hits=[],
                synonym_analysis=None,
                took=35,
                timed_out=False,
                page=1,
                per_page=10,
                total_pages=1,
                original_matches=1,
                synonym_matches=2,
                hybrid_matches=0
            )
            
            response = await client.post("/api/v1/search/synonym", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["query"] == "video content"
            assert result["expanded_query"] == "video content (movie film clip)"
            assert result["total_hits"] == 3
    
    async def test_synonym_search_with_analysis(self, client: AsyncClient):
        """Test synonym search with analysis enabled"""
        data = {
            "query": "video content",
            "include_synonym_analysis": True,
            "size": 10
        }
        
        with patch('src.services.search_service.SearchService.synonym_search') as mock_search:
            mock_search.return_value = SynonymSearchResponse(
                query="video content",
                expanded_query="video content (movie film clip)",
                total_hits=4,
                max_score=1.7,
                hits=[],
                synonym_analysis={
                    "original_query": "video content",
                    "expanded_query": "video content (movie film clip)",
                    "term_expansions": [
                        {
                            "original_term": "video",
                            "synonyms": ["movie", "film", "clip"],
                            "synonym_type": "explicit",
                            "source": "explicit",
                            "pos_tag": "NN"
                        }
                    ],
                    "expansion_strategy": "expand",
                    "total_synonyms_added": 3,
                    "expansion_time_ms": 15,
                    "cache_hit_rate": 0.8,
                    "query_characteristics": {
                        "word_count": 2,
                        "avg_word_length": 5.5,
                        "has_numbers": False,
                        "has_special_chars": False,
                        "unique_words": 2,
                        "query_length": 13,
                        "estimated_domain": "media"
                    }
                },
                took=40,
                timed_out=False,
                page=1,
                per_page=10,
                total_pages=1,
                original_matches=1,
                synonym_matches=3,
                hybrid_matches=0
            )
            
            response = await client.post("/api/v1/search/synonym", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["query"] == "video content"
            assert result["synonym_analysis"] is not None
            assert result["synonym_analysis"]["original_query"] == "video content"
            assert result["synonym_analysis"]["total_synonyms_added"] == 3
            assert result["synonym_analysis"]["query_characteristics"]["estimated_domain"] == "media"
    
    async def test_synonym_search_different_types(self, client: AsyncClient):
        """Test synonym search with different synonym types"""
        synonym_types = ["explicit", "wordnet", "custom", "contextual", "hybrid"]
        
        for synonym_type in synonym_types:
            data = {
                "query": "video content",
                "synonym_config": {
                    "synonym_type": synonym_type,
                    "expansion_strategy": "expand"
                },
                "size": 5
            }
            
            with patch('src.services.search_service.SearchService.synonym_search') as mock_search:
                mock_search.return_value = SynonymSearchResponse(
                    query="video content",
                    expanded_query="video content (movie film)",
                    total_hits=3,
                    max_score=1.5,
                    hits=[],
                    synonym_analysis=None,
                    took=30,
                    timed_out=False,
                    page=1,
                    per_page=5,
                    total_pages=1,
                    original_matches=1,
                    synonym_matches=2,
                    hybrid_matches=0
                )
                
                response = await client.post("/api/v1/search/synonym", json=data)
                
                assert response.status_code == 200
                result = response.json()
                assert result["query"] == "video content"
                assert result["total_hits"] == 3
    
    async def test_synonym_search_different_strategies(self, client: AsyncClient):
        """Test synonym search with different expansion strategies"""
        strategies = ["replace", "expand", "boost", "fallback"]
        
        for strategy in strategies:
            data = {
                "query": "video content",
                "synonym_config": {
                    "synonym_type": "explicit",
                    "expansion_strategy": strategy
                },
                "size": 10
            }
            
            with patch('src.services.search_service.SearchService.synonym_search') as mock_search:
                mock_search.return_value = SynonymSearchResponse(
                    query="video content",
                    expanded_query="video content (movie film)",
                    total_hits=4,
                    max_score=1.6,
                    hits=[],
                    synonym_analysis=None,
                    took=35,
                    timed_out=False,
                    page=1,
                    per_page=10,
                    total_pages=1,
                    original_matches=2,
                    synonym_matches=2,
                    hybrid_matches=0
                )
                
                response = await client.post("/api/v1/search/synonym", json=data)
                
                assert response.status_code == 200
                result = response.json()
                assert result["query"] == "video content"
                assert result["total_hits"] == 4
    
    async def test_synonym_search_with_filters(self, client: AsyncClient):
        """Test synonym search with filters"""
        data = {
            "query": "video content",
            "filters": [
                {
                    "field": "asset_type",
                    "type": "term",
                    "value": "video"
                },
                {
                    "field": "duration",
                    "type": "range",
                    "value": {"gte": 60, "lte": 300}
                }
            ],
            "size": 10
        }
        
        with patch('src.services.search_service.SearchService.synonym_search') as mock_search:
            mock_search.return_value = SynonymSearchResponse(
                query="video content",
                expanded_query="video content (movie film clip)",
                total_hits=2,
                max_score=1.8,
                hits=[],
                synonym_analysis=None,
                took=50,
                timed_out=False,
                page=1,
                per_page=10,
                total_pages=1,
                original_matches=1,
                synonym_matches=1,
                hybrid_matches=0
            )
            
            response = await client.post("/api/v1/search/synonym", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["query"] == "video content"
            assert result["total_hits"] == 2
    
    async def test_synonym_search_with_custom_fields(self, client: AsyncClient):
        """Test synonym search with specific fields"""
        data = {
            "query": "video content",
            "fields": ["title", "description", "tags"],
            "size": 10
        }
        
        with patch('src.services.search_service.SearchService.synonym_search') as mock_search:
            mock_search.return_value = SynonymSearchResponse(
                query="video content",
                expanded_query="video content (movie film clip)",
                total_hits=3,
                max_score=1.4,
                hits=[],
                synonym_analysis=None,
                took=25,
                timed_out=False,
                page=1,
                per_page=10,
                total_pages=1,
                original_matches=1,
                synonym_matches=2,
                hybrid_matches=0
            )
            
            response = await client.post("/api/v1/search/synonym", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["query"] == "video content"
            assert result["total_hits"] == 3
    
    async def test_synonym_search_pagination(self, client: AsyncClient):
        """Test synonym search with pagination"""
        data = {
            "query": "video content",
            "size": 5,
            "from": 10
        }
        
        with patch('src.services.search_service.SearchService.synonym_search') as mock_search:
            mock_search.return_value = SynonymSearchResponse(
                query="video content",
                expanded_query="video content (movie film clip)",
                total_hits=25,
                max_score=1.5,
                hits=[],
                synonym_analysis=None,
                took=30,
                timed_out=False,
                page=3,
                per_page=5,
                total_pages=5,
                original_matches=10,
                synonym_matches=15,
                hybrid_matches=0
            )
            
            response = await client.post("/api/v1/search/synonym", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["page"] == 3
            assert result["per_page"] == 5
            assert result["total_pages"] == 5
            assert result["total_hits"] == 25
    
    async def test_synonym_search_sorting(self, client: AsyncClient):
        """Test synonym search with sorting"""
        data = {
            "query": "video content",
            "sort_by": "created_at",
            "sort_order": "asc",
            "size": 10
        }
        
        with patch('src.services.search_service.SearchService.synonym_search') as mock_search:
            mock_search.return_value = SynonymSearchResponse(
                query="video content",
                expanded_query="video content (movie film clip)",
                total_hits=8,
                max_score=1.3,
                hits=[],
                synonym_analysis=None,
                took=40,
                timed_out=False,
                page=1,
                per_page=10,
                total_pages=1,
                original_matches=3,
                synonym_matches=5,
                hybrid_matches=0
            )
            
            response = await client.post("/api/v1/search/synonym", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["query"] == "video content"
            assert result["total_hits"] == 8
    
    async def test_synonym_search_domain_context(self, client: AsyncClient):
        """Test synonym search with domain context"""
        data = {
            "query": "video content",
            "synonym_config": {
                "synonym_type": "contextual",
                "expansion_strategy": "expand",
                "domain_context": "media"
            },
            "size": 10
        }
        
        with patch('src.services.search_service.SearchService.synonym_search') as mock_search:
            mock_search.return_value = SynonymSearchResponse(
                query="video content",
                expanded_query="video content (movie film footage clip)",
                total_hits=6,
                max_score=1.7,
                hits=[],
                synonym_analysis=None,
                took=35,
                timed_out=False,
                page=1,
                per_page=10,
                total_pages=1,
                original_matches=2,
                synonym_matches=4,
                hybrid_matches=0
            )
            
            response = await client.post("/api/v1/search/synonym", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["query"] == "video content"
            assert result["expanded_query"] == "video content (movie film footage clip)"
            assert result["total_hits"] == 6
    
    async def test_synonym_search_validation_errors(self, client: AsyncClient):
        """Test synonym search validation errors"""
        # Test empty query
        data = {
            "query": "",
            "size": 10
        }
        
        response = await client.post("/api/v1/search/synonym", json=data)
        assert response.status_code == 422
        
        # Test invalid size
        data = {
            "query": "video content",
            "size": 0
        }
        
        response = await client.post("/api/v1/search/synonym", json=data)
        assert response.status_code == 422
        
        # Test invalid synonym type
        data = {
            "query": "video content",
            "synonym_config": {
                "synonym_type": "invalid_type"
            }
        }
        
        response = await client.post("/api/v1/search/synonym", json=data)
        assert response.status_code == 422
        
        # Test invalid expansion strategy
        data = {
            "query": "video content",
            "synonym_config": {
                "expansion_strategy": "invalid_strategy"
            }
        }
        
        response = await client.post("/api/v1/search/synonym", json=data)
        assert response.status_code == 422
    
    async def test_synonym_search_error_handling(self, client: AsyncClient):
        """Test synonym search error handling"""
        data = {
            "query": "video content",
            "size": 10
        }
        
        with patch('src.services.search_service.SearchService.synonym_search') as mock_search:
            mock_search.side_effect = Exception("Search service error")
            
            response = await client.post("/api/v1/search/synonym", json=data)
            
            assert response.status_code == 500
            assert "synonym search error" in response.json()["detail"].lower()


@pytest.mark.asyncio
class TestSynonymSuggestionsAPI:
    """Test synonym suggestions API endpoints"""
    
    async def test_synonym_suggestions_basic(self, client: AsyncClient):
        """Test basic synonym suggestions"""
        data = {
            "term": "video",
            "size": 5
        }
        
        with patch('src.services.search_service.SearchService.synonym_suggestions') as mock_suggestions:
            mock_suggestions.return_value = SynonymSuggestionResponse(
                term="video",
                synonyms=[
                    {
                        "term": "movie",
                        "similarity_score": 0.9,
                        "frequency": 150,
                        "synonym_type": "explicit",
                        "source": "explicit",
                        "pos_tag": "NN"
                    },
                    {
                        "term": "film",
                        "similarity_score": 0.85,
                        "frequency": 120,
                        "synonym_type": "explicit",
                        "source": "explicit",
                        "pos_tag": "NN"
                    },
                    {
                        "term": "clip",
                        "similarity_score": 0.8,
                        "frequency": 100,
                        "synonym_type": "explicit",
                        "source": "explicit",
                        "pos_tag": "NN"
                    }
                ],
                synonym_type="hybrid",
                total_synonyms=3,
                took=20,
                metadata={
                    "source": "explicit",
                    "domain_context": None,
                    "pos_tag": None,
                    "min_similarity": 0.7
                }
            )
            
            response = await client.post("/api/v1/search/synonym/suggestions", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["term"] == "video"
            assert len(result["synonyms"]) == 3
            assert result["synonyms"][0]["term"] == "movie"
            assert result["synonyms"][0]["similarity_score"] == 0.9
            assert result["total_synonyms"] == 3
    
    async def test_synonym_suggestions_different_types(self, client: AsyncClient):
        """Test synonym suggestions with different types"""
        synonym_types = ["explicit", "wordnet", "custom", "contextual", "hybrid"]
        
        for synonym_type in synonym_types:
            data = {
                "term": "video",
                "synonym_type": synonym_type,
                "size": 3
            }
            
            with patch('src.services.search_service.SearchService.synonym_suggestions') as mock_suggestions:
                mock_suggestions.return_value = SynonymSuggestionResponse(
                    term="video",
                    synonyms=[
                        {
                            "term": "movie",
                            "similarity_score": 0.9,
                            "frequency": 100,
                            "synonym_type": synonym_type,
                            "source": synonym_type,
                            "pos_tag": "NN"
                        }
                    ],
                    synonym_type=synonym_type,
                    total_synonyms=1,
                    took=15,
                    metadata={
                        "source": synonym_type,
                        "domain_context": None,
                        "pos_tag": None,
                        "min_similarity": 0.7
                    }
                )
                
                response = await client.post("/api/v1/search/synonym/suggestions", json=data)
                
                assert response.status_code == 200
                result = response.json()
                assert result["term"] == "video"
                assert result["synonym_type"] == synonym_type
    
    async def test_synonym_suggestions_with_domain(self, client: AsyncClient):
        """Test synonym suggestions with domain context"""
        data = {
            "term": "video",
            "synonym_type": "contextual",
            "domain_context": "media",
            "size": 5
        }
        
        with patch('src.services.search_service.SearchService.synonym_suggestions') as mock_suggestions:
            mock_suggestions.return_value = SynonymSuggestionResponse(
                term="video",
                synonyms=[
                    {
                        "term": "footage",
                        "similarity_score": 0.92,
                        "frequency": 80,
                        "synonym_type": "contextual",
                        "source": "domain",
                        "pos_tag": "NN",
                        "domain_context": "media"
                    },
                    {
                        "term": "recording",
                        "similarity_score": 0.88,
                        "frequency": 75,
                        "synonym_type": "contextual",
                        "source": "domain",
                        "pos_tag": "NN",
                        "domain_context": "media"
                    }
                ],
                synonym_type="contextual",
                total_synonyms=2,
                took=25,
                metadata={
                    "source": "domain",
                    "domain_context": "media",
                    "pos_tag": None,
                    "min_similarity": 0.7
                }
            )
            
            response = await client.post("/api/v1/search/synonym/suggestions", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["term"] == "video"
            assert result["metadata"]["domain_context"] == "media"
            assert result["synonyms"][0]["domain_context"] == "media"
    
    async def test_synonym_suggestions_with_similarity(self, client: AsyncClient):
        """Test synonym suggestions with similarity threshold"""
        data = {
            "term": "video",
            "synonym_type": "explicit",
            "min_similarity": 0.9,
            "size": 5
        }
        
        with patch('src.services.search_service.SearchService.synonym_suggestions') as mock_suggestions:
            mock_suggestions.return_value = SynonymSuggestionResponse(
                term="video",
                synonyms=[
                    {
                        "term": "movie",
                        "similarity_score": 0.95,
                        "frequency": 150,
                        "synonym_type": "explicit",
                        "source": "explicit",
                        "pos_tag": "NN"
                    },
                    {
                        "term": "film",
                        "similarity_score": 0.92,
                        "frequency": 120,
                        "synonym_type": "explicit",
                        "source": "explicit",
                        "pos_tag": "NN"
                    }
                ],
                synonym_type="explicit",
                total_synonyms=2,
                took=18,
                metadata={
                    "source": "explicit",
                    "domain_context": None,
                    "pos_tag": None,
                    "min_similarity": 0.9
                }
            )
            
            response = await client.post("/api/v1/search/synonym/suggestions", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["term"] == "video"
            assert result["metadata"]["min_similarity"] == 0.9
            
            # Check that all suggestions meet similarity threshold
            for suggestion in result["synonyms"]:
                assert suggestion["similarity_score"] >= 0.9
    
    async def test_synonym_suggestions_with_pos_tag(self, client: AsyncClient):
        """Test synonym suggestions with part-of-speech tag"""
        data = {
            "term": "video",
            "synonym_type": "wordnet",
            "pos_tag": "NN",
            "size": 5
        }
        
        with patch('src.services.search_service.SearchService.synonym_suggestions') as mock_suggestions:
            mock_suggestions.return_value = SynonymSuggestionResponse(
                term="video",
                synonyms=[
                    {
                        "term": "movie",
                        "similarity_score": 0.9,
                        "frequency": 100,
                        "synonym_type": "wordnet",
                        "source": "wordnet",
                        "pos_tag": "NN"
                    }
                ],
                synonym_type="wordnet",
                total_synonyms=1,
                took=20,
                metadata={
                    "source": "wordnet",
                    "domain_context": None,
                    "pos_tag": "NN",
                    "min_similarity": 0.7
                }
            )
            
            response = await client.post("/api/v1/search/synonym/suggestions", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["term"] == "video"
            assert result["metadata"]["pos_tag"] == "NN"
            assert result["synonyms"][0]["pos_tag"] == "NN"
    
    async def test_synonym_suggestions_size_limit(self, client: AsyncClient):
        """Test synonym suggestions with size limit"""
        data = {
            "term": "video",
            "synonym_type": "explicit",
            "size": 2
        }
        
        with patch('src.services.search_service.SearchService.synonym_suggestions') as mock_suggestions:
            mock_suggestions.return_value = SynonymSuggestionResponse(
                term="video",
                synonyms=[
                    {
                        "term": "movie",
                        "similarity_score": 0.9,
                        "frequency": 150,
                        "synonym_type": "explicit",
                        "source": "explicit",
                        "pos_tag": "NN"
                    },
                    {
                        "term": "film",
                        "similarity_score": 0.85,
                        "frequency": 120,
                        "synonym_type": "explicit",
                        "source": "explicit",
                        "pos_tag": "NN"
                    }
                ],
                synonym_type="explicit",
                total_synonyms=2,
                took=15,
                metadata={
                    "source": "explicit",
                    "domain_context": None,
                    "pos_tag": None,
                    "min_similarity": 0.7
                }
            )
            
            response = await client.post("/api/v1/search/synonym/suggestions", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["term"] == "video"
            assert len(result["synonyms"]) == 2
    
    async def test_synonym_suggestions_no_results(self, client: AsyncClient):
        """Test synonym suggestions with no results"""
        data = {
            "term": "xyz123abc",
            "synonym_type": "explicit",
            "size": 5
        }
        
        with patch('src.services.search_service.SearchService.synonym_suggestions') as mock_suggestions:
            mock_suggestions.return_value = SynonymSuggestionResponse(
                term="xyz123abc",
                synonyms=[],
                synonym_type="explicit",
                total_synonyms=0,
                took=10,
                metadata={
                    "source": "explicit",
                    "domain_context": None,
                    "pos_tag": None,
                    "min_similarity": 0.7
                }
            )
            
            response = await client.post("/api/v1/search/synonym/suggestions", json=data)
            
            assert response.status_code == 200
            result = response.json()
            assert result["term"] == "xyz123abc"
            assert len(result["synonyms"]) == 0
            assert result["total_synonyms"] == 0
    
    async def test_synonym_suggestions_validation_errors(self, client: AsyncClient):
        """Test synonym suggestions validation errors"""
        # Test empty term
        data = {
            "term": "",
            "size": 5
        }
        
        response = await client.post("/api/v1/search/synonym/suggestions", json=data)
        assert response.status_code == 422
        
        # Test invalid synonym type
        data = {
            "term": "video",
            "synonym_type": "invalid_type",
            "size": 5
        }
        
        response = await client.post("/api/v1/search/synonym/suggestions", json=data)
        assert response.status_code == 422
        
        # Test invalid size
        data = {
            "term": "video",
            "size": 0
        }
        
        response = await client.post("/api/v1/search/synonym/suggestions", json=data)
        assert response.status_code == 422
        
        # Test size too large
        data = {
            "term": "video",
            "size": 100
        }
        
        response = await client.post("/api/v1/search/synonym/suggestions", json=data)
        assert response.status_code == 422
        
        # Test invalid similarity threshold
        data = {
            "term": "video",
            "min_similarity": 1.5,
            "size": 5
        }
        
        response = await client.post("/api/v1/search/synonym/suggestions", json=data)
        assert response.status_code == 422
    
    async def test_synonym_suggestions_error_handling(self, client: AsyncClient):
        """Test synonym suggestions error handling"""
        data = {
            "term": "video",
            "size": 5
        }
        
        with patch('src.services.search_service.SearchService.synonym_suggestions') as mock_suggestions:
            mock_suggestions.side_effect = Exception("Suggestions service error")
            
            response = await client.post("/api/v1/search/synonym/suggestions", json=data)
            
            assert response.status_code == 500
            assert "synonym suggestions error" in response.json()["detail"].lower()


@pytest.mark.asyncio
class TestSynonymStatsAPI:
    """Test synonym statistics API endpoints"""
    
    async def test_synonym_stats_basic(self, client: AsyncClient):
        """Test basic synonym statistics"""
        
        with patch('src.services.search_service.SearchService.synonym_service') as mock_service:
            mock_service.get_synonym_stats.return_value = SynonymStats(
                total_synonyms=1250,
                total_terms=425,
                avg_synonyms_per_term=2.94,
                most_common_domains=[
                    {"domain": "media", "count": 180},
                    {"domain": "broadcast", "count": 125},
                    {"domain": "production", "count": 90}
                ],
                synonym_usage_stats={
                    "wordnet_usage": 0.45,
                    "custom_usage": 0.30,
                    "domain_usage": 0.25
                },
                cache_stats={
                    "hit_rate": 0.78,
                    "total_requests": 5420,
                    "cache_hits": 4228
                },
                performance_metrics={
                    "avg_expansion_time_ms": 12.5,
                    "avg_synonyms_per_query": 3.2,
                    "expansion_success_rate": 0.85
                }
            )
            
            response = await client.get("/api/v1/search/synonym/stats")
            
            assert response.status_code == 200
            result = response.json()
            assert result["total_synonyms"] == 1250
            assert result["total_terms"] == 425
            assert result["avg_synonyms_per_term"] == 2.94
            assert len(result["most_common_domains"]) == 3
            assert result["most_common_domains"][0]["domain"] == "media"
            assert result["cache_stats"]["hit_rate"] == 0.78
            assert result["performance_metrics"]["avg_expansion_time_ms"] == 12.5
    
    async def test_synonym_stats_error_handling(self, client: AsyncClient):
        """Test synonym stats error handling"""
        
        with patch('src.services.search_service.SearchService.synonym_service') as mock_service:
            mock_service.get_synonym_stats.side_effect = Exception("Stats service error")
            
            response = await client.get("/api/v1/search/synonym/stats")
            
            assert response.status_code == 500
            assert "synonym stats error" in response.json()["detail"].lower()